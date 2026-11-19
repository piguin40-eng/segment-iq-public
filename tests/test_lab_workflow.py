import copy
import io
import json
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from dental_lab import lab_workflow
from dental_lab.harness import SegmentHarness, response_schema
from dental_lab.worker import Worker
from test_core import client
from test_revisions import make_case

APP = Path(__file__).parents[1]


def answer(workflow, phase='plan'):
    return {'decision':'run' if phase=='plan' else 'accept', 'summary':'Propuesta de prueba',
            'changes':[], 'pending':[], 'evidence':[], 'resolved_pending':[],
            'lab_workflow':{'sha256':workflow['sha256'], 'checks':[
                {'step':step, 'status':'planned' if phase=='plan' else 'pending',
                 'detail':'Medir sobre el STL del caso; no se ha ejecutado en esta prueba.', 'evidence':[]}
                for step in lab_workflow.CHECKS]}}


def test_version_snapshot_is_frozen_and_missing_reference_fails(tmp_path):
    skill=tmp_path/'app/openclaw/skills'/lab_workflow.SKILL
    shutil.copytree(APP/'openclaw/skills'/lab_workflow.SKILL,skill)
    first=lab_workflow.load_workflow(tmp_path/'app')
    lab_workflow.snapshot(first,tmp_path/'run','codex')
    path=skill/'references/procedimiento.md'
    path.write_text(path.read_text(encoding='utf-8')+'\nCorrección nueva.',encoding='utf-8')
    second=lab_workflow.load_workflow(tmp_path/'app')
    assert first['sha256']!=second['sha256']
    assert 'Corrección nueva' not in (tmp_path/'run/references/procedimiento.md').read_text(encoding='utf-8')
    path.unlink()
    with pytest.raises(RuntimeError,match='protocolo obligatorio'):
        lab_workflow.load_workflow(tmp_path/'app')


@pytest.mark.parametrize('phase',['plan','review'])
def test_real_think_path_injects_all_documents_without_rag_and_preserves_pending(tmp_path,monkeypatch,phase):
    h=object.__new__(SegmentHarness)
    h.s=SimpleNamespace(app=APP,agent_timeout_seconds=60)
    import threading
    h.w=SimpleNamespace(stop=threading.Event())
    h.workflow=lab_workflow.load_workflow(APP)
    h.workspace=tmp_path/'workspace';h.workspace.mkdir()
    h.out=tmp_path/'out';h.out.mkdir()
    h.state={'attempt':1};h.event=lambda *args:None
    monkeypatch.setattr('dental_lab.harness.find_codex',lambda _: 'codex-test')
    seen=[]
    def fake_process(command,log,timeout,**kwargs):
        seen.append(kwargs['prompt'])
        (h.workspace/f'01_{phase}.json').write_text(json.dumps(answer(h.workflow,phase)),encoding='utf-8')
    h.process=fake_process
    result=h.think(phase,'Caso nuevo sin referencias RAG.')
    assert all(content in seen[0] for content in h.workflow['files'].values())
    assert h.workflow['sha256'] in seen[0]
    assert len(result['pending'])==(len(lab_workflow.CHECKS) if phase=='review' else 0)
    assert 'lab_workflow' in response_schema()['required']
    assert json.loads((h.out/f'01_{phase}.json').read_text())['lab_workflow']==result['lab_workflow']


@pytest.mark.parametrize('problem',['no_ack','old_version','missing_step','duplicate_step','false_verified','skip_required','wrong_phase'])
def test_agent_cannot_silently_skip_protocol_or_verify_without_evidence(problem):
    w=lab_workflow.load_workflow(APP);a=answer(w,'review')
    rows=a['lab_workflow']['checks']
    if problem=='no_ack':a.pop('lab_workflow')
    elif problem=='old_version':a['lab_workflow']['sha256']='old'
    elif problem=='missing_step':rows.pop()
    elif problem=='duplicate_step':rows[-1]=copy.deepcopy(rows[0])
    elif problem=='false_verified':rows[0]['status']='verified'
    elif problem=='skip_required':rows[0]['status']='not_applicable'
    elif problem=='wrong_phase':rows[0]['status']='planned'
    with pytest.raises(ValueError):lab_workflow.validate_answer(w,a,'review')


def test_optional_retention_can_be_explained_without_claiming_unperformed_work():
    w=lab_workflow.load_workflow(APP);a=answer(w,'review')
    row=next(r for r in a['lab_workflow']['checks'] if r['step']=='retenciones')
    row.update(status='not_applicable',detail='No solicitadas en este caso; el vídeo no las exige universalmente.')
    assert len(lab_workflow.validate_answer(w,a,'review'))==len(lab_workflow.CHECKS)-1


def test_required_files_are_loaded_before_profile_measurement(client,monkeypatch,tmp_path):
    c,app=client;case=make_case(c,'protocolo')
    job=app.state.store.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    s=app.state.settings;s.geometry_python='test-python';s.agent_harness='codex'
    h=SegmentHarness(Worker(s,app.state.store,app.state.ingest),job)
    def fail_measure(*args,**kwargs):raise RuntimeError('Fin de medición de prueba')
    monkeypatch.setattr(h,'process',fail_measure)
    with pytest.raises(RuntimeError,match='medición de prueba'):h.prepare()
    assert (h.out/'Protocolo_obligatorio/Protocolo.json').is_file()
    assert (h.workspace/'protocolo_obligatorio/references/procedimiento.md').is_file()
    assert h.state['lab_workflow']['sha256']==lab_workflow.load_workflow(APP)['sha256']


def test_skill_download_is_authenticated_text_only_and_missing_install_does_not_break_health(client,tmp_path):
    c,app=client
    assert c.get('/api/lab-workflow/download',headers={'Authorization':'bad'}).status_code==401
    status=c.get('/api/lab-workflow').json()
    assert status['available'] and status['video_source_id'] is None
    response=c.get('/api/lab-workflow/download')
    assert response.status_code==200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert set(archive.namelist())=={lab_workflow.SKILL+'/'+name for name in lab_workflow.FILES}
        assert all(name.endswith('.md') for name in archive.namelist())
    app.state.settings.app=tmp_path/'missing-install'
    assert c.get('/api/lab-workflow').json()['available'] is False
    assert c.get('/api/lab-workflow/download').status_code==503
    assert c.get('/health').status_code==200


def test_video_reindex_preserves_reviewed_learning_but_replaces_machine_chunks(client,monkeypatch):
    c,app=client;db=app.state.store
    uploaded=c.post('/api/upload',files={'file':('video.mp4',b'fake video for mocked decoder')}).json()['id']
    db.add_chunks(uploaded,[{'text':'síntesis contrastada importante','kind':'sintesis_video_contrastada','start':10,'end':20},
                            {'text':'OCR antiguo','kind':'ocr_no_revisado'}])
    class Container:
        streams=SimpleNamespace(audio=[])
        def __enter__(self):return self
        def __exit__(self,*args):pass
    monkeypatch.setattr('av.open',lambda *_:Container())
    monkeypatch.setattr(app.state.ingest,'frames',lambda *_:[{'text':'OCR nuevo','kind':'ocr_no_revisado'}])
    app.state.ingest.process(uploaded)
    rows=db.rows('SELECT text FROM chunks WHERE source_id=?',(uploaded,))
    assert {r['text'] for r in rows}=={'síntesis contrastada importante','OCR nuevo'}
