import json
from pathlib import Path
from test_core import client
from dental_lab.worker import Worker


def make_case(c, name):
    source = c.post('/api/upload', files={'file': (name+'.stl', ('solid '+name+'\nendsolid').encode())}).json()['id']
    return c.post('/api/cases', json={'name':name, 'source_id':source}).json()['id']


def test_correction_attachments_and_revision_snapshot(client, monkeypatch):
    c, app = client
    db = app.state.store
    case = make_case(c, 'inferior')
    other = make_case(c, 'superior')
    reference = c.post('/api/upload', files={'file': ('referencia.md', b'Zona distal marcada para comparar con la barra propia.')} ).json()['id']
    app.state.ingest.process(reference)
    c.post('/api/feedback', json={'case_id':other, 'author':'Equipo', 'text':'Solo otro caso: conservar espesor especial.'})
    body = {'case_id':case,'author':'Equipo','text':'Aumentar altura en la zona de la 37.','attachment_ids':[reference,reference],'request_plan':True}
    result = c.post('/api/feedback',json=body)
    assert result.status_code == 200
    result = result.json()
    feedback = next(f for f in c.get('/api/feedback').json() if f['id']==result['id'])
    assert feedback['plan_id'] == result['job_id']
    assert [a['id'] for a in feedback['attachments']] == [reference]
    assert db.one('SELECT profile_path FROM cases WHERE id=?',(case,))['profile_path'] is None
    later = c.post('/api/feedback',json={'case_id':case,'author':'Equipo','text':'Corrección posterior: nueva observación.'}).json()['id']
    assert c.post('/api/cases/'+case+'/plan').status_code == 409

    job = db.one('SELECT * FROM jobs WHERE id=?',(result['job_id'],))
    worker = Worker(app.state.settings,db,app.state.ingest)
    evidence, history = worker.plan_evidence(job)
    assert [f['id'] for f in history['feedback']] == [result['id']]
    assert later not in history['model_context_feedback_ids']
    assert any('altura' in e['text'] for e in evidence)
    assert any(e['source_id']==reference for e in evidence)
    assert not any('otro caso' in e['text'] for e in evidence)

    # Exercise plan output with real storage and stub only external geometry/LLM execution.
    app.state.settings.geometry_python='test-python'
    def measure(command, **kwargs):
        Path(command[-1]).write_text('{"volume_mm3":100}',encoding='utf-8')
    monkeypatch.setattr('dental_lab.worker.subprocess.run',measure)
    def chat(question,case_sources):
        assert 'no modifica aún el STL' in question
        assert any('37' in source['text'] for source in case_sources)
        return {'answer':'Revisar altura de la barra [1].','citations':case_sources,'mode':'RAG local'}
    monkeypatch.setattr(app.state.rag,'chat',chat)
    worker.plan(job)
    saved=json.loads((app.state.settings.data/'runs'/job['id']/'outputs'/'Historial_de_la_revision.json').read_text(encoding='utf-8'))
    assert saved['geometry_modified'] is False
    assert saved['model_context_feedback_ids']==[result['id']]
    assert db.one('SELECT count(*) n FROM jobs WHERE kind="segment"')['n']==2


def test_invalid_attachment_or_scope_does_not_save_feedback(client):
    c, app=client
    case=make_case(c,'prueba')
    body={'case_id':case,'author':'Equipo','text':'Falta altura en la barra.','attachment_ids':['missing'],'request_plan':True}
    assert c.post('/api/feedback',json=body).status_code==400
    assert c.get('/api/feedback').json()==[]
    body.update(case_id='general',attachment_ids=[])
    assert c.post('/api/feedback',json=body).status_code==400
    assert app.state.store.one('SELECT count(*) n FROM jobs WHERE kind="plan"')['n']==0


def test_busy_plan_preserves_save_only_path_and_blocks_duplicate_review(client):
    c, app=client
    case=make_case(c,'caso')
    c.post('/api/cases/'+case+'/plan')
    body={'case_id':case,'author':'Equipo','text':'Más profundidad de barra.','request_plan':True}
    assert c.post('/api/feedback',json=body).status_code==409
    assert c.get('/api/feedback').json()==[]
    body['request_plan']=False
    assert c.post('/api/feedback',json=body).status_code==200
    assert len(c.get('/api/feedback').json())==1


def test_case_retrieval_excludes_unscoped_feedback(client):
    c,app=client
    c.post('/api/feedback',json={'author':'Equipo','text':'La altura de la barra depende del caso.'})
    assert any(r['kind']=='correccion_tecnico' for r in app.state.rag.search('altura barra'))
    assert not any(r['kind']=='correccion_tecnico' for r in app.state.rag.search('altura barra',exclude_feedback=True))
    source=app.state.store.one('SELECT source_id FROM feedback_details')['source_id']
    app.state.ingest.process(source)
    assert not any(r['source_id']==source for r in app.state.rag.search('altura barra',exclude_feedback=True))
