import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from dental_lab.harness import SegmentHarness, AgentServiceBusy, AdapterValidationError, validate_adapter, digest, planning_evidence, recoverable_plan, write, cli_error_message, tool_error_summary
from dental_lab.revisions import engine_digest
from test_harness import profile
from test_core import client
from dental_lab import lab_workflow
from test_lab_workflow import answer

APP=Path(__file__).parents[1]


def harness(tmp_path,monkeypatch):
    h=object.__new__(SegmentHarness)
    h.s=SimpleNamespace(app=APP,agent_timeout_seconds=900)
    h.w=SimpleNamespace(stop=threading.Event())
    h.workflow=lab_workflow.load_workflow(APP)
    h.workspace=tmp_path/'workspace';h.workspace.mkdir()
    h.out=tmp_path/'logs';h.out.mkdir()
    h.state={'attempt':1};h.event=lambda *a:None
    monkeypatch.setattr('dental_lab.harness.find_codex',lambda _: 'codex-test')
    return h


def test_adapter_repair_uses_exact_error_and_rechecks_before_execution(tmp_path,monkeypatch):
    h=harness(tmp_path,monkeypatch);path=h.workspace/'occlusal_safety.py'
    path.write_text('from bar_height import _pchip_value\n')
    def check():
        validate_adapter(path)
        return {'candidate':'unchanged mathematics'}
    h.validate=check;calls=[]
    def repair(phase,prompt):
        calls.append(phase)
        report=json.loads((h.workspace/'Correccion_adaptador.json').read_text())
        assert '_pchip_value' in report['error'] and report['geometry_launched'] is False
        assert '240' in prompt
        path.write_text('from bar_height import pchip_value\n')
        return {'decision':'run'}
    h.think=repair
    assert h.validate_for_execution()=={'candidate':'unchanged mathematics'}
    assert calls==['repair'] and h.state['attempt']==1


@pytest.mark.parametrize('error',[AdapterValidationError,ValueError,InterruptedError])
def test_adapter_repair_is_bounded_and_cannot_bypass_immutable_checks(tmp_path,monkeypatch,error):
    h=harness(tmp_path,monkeypatch);calls=[]
    h.validate=lambda:(_ for _ in ()).throw(error('still invalid'))
    h.think=lambda *a:calls.append(a) or {'decision':'run'}
    with pytest.raises(error):h.validate_for_execution()
    assert len(calls)==(1 if error is AdapterValidationError else 0)


def test_repair_phase_is_bounded_and_never_claims_geometry_verified(tmp_path,monkeypatch):
    h=harness(tmp_path,monkeypatch);calls=[]
    def run(command,log,timeout,**kwargs):
        calls.append(timeout)
        write(command[command.index('-o')+1],answer(h.workflow,'plan'))
    h.process=run
    assert h.think('repair','Repair the helper')['decision']=='run'
    assert calls==[240]
    h.process=lambda *a,**kw:(_ for _ in ()).throw(TimeoutError('repair deadline'))
    with pytest.raises(TimeoutError):h.think('repair','Repair the helper')
    assert json.loads((h.out/'01_repair_Interrupcion.json').read_text())['geometry_launched'] is False


def test_timeout_recovers_saved_work_once_without_accepting_stale_output(tmp_path,monkeypatch):
    h=harness(tmp_path,monkeypatch);calls=[]
    saved=h.workspace/'Medicion_plan.json'
    def run(command,log,timeout,**kwargs):
        calls.append((command,log,timeout,kwargs))
        if len(calls)==1:
            saved.write_text('measured section')
            write(h.workspace/'01_plan.json',{'decision':'accept','summary':'stale incomplete'})
            log.write_text(json.dumps({'item':{'type':'agent_message','text':'Secciones guardadas'}})+'\n')
            raise TimeoutError('time budget')
        assert saved.read_text()=='measured section'
        assert 'Plan_interrumpido.json' in kwargs['prompt']
        write(command[command.index('-o')+1],answer(h.workflow,'plan'))
    h.process=run
    result=h.think('plan','Prepare the case')
    assert result['decision']=='run'
    assert h.state['attempt']==1
    assert [c[2] for c in calls]==[900,240]
    assert calls[0][1]!=calls[1][1]
    assert json.loads((h.workspace/'Plan_interrumpido.json').read_text())['geometry_launched'] is False
    assert json.loads((h.out/'01_plan.json').read_text())['decision']=='run'


@pytest.mark.parametrize('phase,error,count',[('plan',TimeoutError,2),('review',TimeoutError,1),('plan',InterruptedError,1),('plan',RuntimeError,1)])
def test_recovery_is_finite_and_never_retries_cancellation_or_arbitrary_failure(tmp_path,monkeypatch,phase,error,count):
    h=harness(tmp_path,monkeypatch);calls=[]
    def fail(*args,**kwargs):
        calls.append(args)
        raise error('interrupted')
    h.process=fail
    with pytest.raises(error): h.think(phase,'case')
    assert len(calls)==count
    assert not (h.out/f'01_{phase}.json').exists()


def test_process_distinguishes_timeout_and_stop_and_terminates_child(tmp_path,monkeypatch):
    h=harness(tmp_path,monkeypatch)
    # A real child is terminated in finally, instead of surviving the request.
    command=[sys.executable,'-c','import time; time.sleep(30)']
    with pytest.raises(TimeoutError): h.process(command,tmp_path/'timeout.log',0)
    h.w.stop.set()
    with pytest.raises(InterruptedError): h.process(command,tmp_path/'stopped.log',30)


def test_planning_evidence_is_source_bound_and_never_inherits_profile_or_code(tmp_path):
    directory=tmp_path/'metadata';workspace=tmp_path/'work';workspace.mkdir()
    (workspace/'original.stl').write_bytes(b'original')
    original=digest(workspace/'original.stl');manifest={'check.py':'fixed'}
    write(directory/'Perfil_base.json',{'source_sha256':original})
    write(directory/'Motor_instalado.json',manifest)
    write(workspace/'Medicion_plan.json',{'width':2})
    write(workspace/'Perfil.json',{'source_sha256':'tampered'})
    record=planning_evidence(directory,workspace,original,manifest)
    assert record['files_read_only']==[str((workspace/'Medicion_plan.json').resolve())]
    assert planning_evidence(directory,workspace,original,manifest,{'expected_connections':8}) is None
    assert planning_evidence(directory,workspace,'another case',manifest) is None
    assert planning_evidence(directory,workspace,original,{'check.py':'changed'}) is None
    (workspace/'original.stl').write_bytes(b'modified')
    assert planning_evidence(directory,workspace,original,manifest) is None


@pytest.mark.parametrize('recover',[True,False])
def test_busy_model_retries_same_model_with_bounded_backoff_and_distinct_logs(tmp_path,monkeypatch,recover):
    h=harness(tmp_path,monkeypatch);calls=[];delays=[]
    h.w.stop=SimpleNamespace(is_set=lambda:False,wait=lambda delay:delays.append(delay) or False)
    def run(command,log,timeout,**kwargs):
        calls.append((command,log))
        if len(calls)<3 or not recover:raise AgentServiceBusy('capacity')
        write(command[command.index('-o')+1],answer(h.workflow,'plan'))
    h.process=run
    if recover:assert h.think('plan','case')['decision']=='run'
    else:
        with pytest.raises(AgentServiceBusy):h.think('plan','case')
    assert delays==[10,30] and len(calls)==3
    assert len({str(c[1]) for c in calls})==3
    assert len({tuple(c[0][:c[0].index('-o')]) for c in calls})==1


def test_busy_model_is_detected_from_structured_cli_failure(tmp_path,monkeypatch):
    h=harness(tmp_path,monkeypatch)
    message='Selected model is at capacity. Please try a different model.'
    payload=json.dumps({'type':'turn.failed','error':{'message':message}})
    command=[sys.executable,'-c','import sys; print('+repr(payload)+'); sys.exit(1)']
    log=tmp_path/'capacity.jsonl'
    with pytest.raises(AgentServiceBusy):h.process(command,log,10,events=True)
    assert cli_error_message(log)==message
    assert message in tool_error_summary(log)


def test_usage_limit_is_not_misclassified_as_transient_model_capacity(tmp_path,monkeypatch):
    h=harness(tmp_path,monkeypatch)
    message='You have hit your usage limit'
    payload=json.dumps({'type':'error','message':message})
    command=[sys.executable,'-c','import sys; print('+repr(payload)+'); sys.exit(1)']
    with pytest.raises(RuntimeError,match=message) as failure:h.process(command,tmp_path/'quota.jsonl',10,events=True)
    assert not isinstance(failure.value,AgentServiceBusy)


@pytest.mark.parametrize('saved_plan',[False,True])
@pytest.mark.parametrize('change',[None,'source','baseline','engine','workflow','feedback','protected','notes_only'])
def test_recovered_candidate_requires_matching_case_instructions_and_protected_geometry(tmp_path,change,saved_plan):
    directory=tmp_path/'runs/job/outputs/Agente';workspace=tmp_path/'work'
    engine=workspace/'engine/engine';engine.mkdir(parents=True)
    (engine/'validator.py').write_text('# immutable')
    (workspace/'original.stl').write_bytes(b'original')
    base=profile();base['source_sha256']=digest(workspace/'original.stl')
    proposed=dict(base,bar_top_z=5.);manifest=engine_digest(engine);feedback=[{'text':'Keep centered'}]
    write(directory/'Perfil_base.json',base);write(directory/'Motor_instalado.json',manifest)
    write(directory/'Estado.json',{'lab_workflow':{'sha256':'protocol'}})
    write(directory/'Historial_de_la_version.json',{'feedback':feedback})
    if saved_plan:write(directory/'01_plan.json',{'decision':'run'})
    else:write(directory/'01_plan_Interrupcion.json',{'phase':'plan'})
    if change=='source':(workspace/'original.stl').write_bytes(b'other')
    if change=='baseline':base=dict(base,minimum_supra_mm=.9)
    if change=='engine':manifest={'validator.py':'another version'}
    if change=='feedback':feedback=[{'text':'New correction'}]
    if change=='protected':proposed['minimum_supra_mm']=.1
    if change=='notes_only':proposed=dict(base,adaptation_notes='description only')
    write(workspace/'Perfil.json',proposed)
    result=recoverable_plan(directory,workspace,base,manifest,'changed' if change=='workflow' else 'protocol',feedback)
    if change is None:
        assert result['approval']=='NONE' and result['profile']==proposed
        assert result['job_id']=='job'
    else:assert result is None


def test_supervisor_recovery_only_constructs_and_does_not_fake_model_approval(tmp_path,monkeypatch):
    h=harness(tmp_path,monkeypatch);h.base=profile();h.validate=lambda:dict(h.base,bar_top_z=5.)
    h.engine=tmp_path/'engine';(h.engine/'engine').mkdir(parents=True);h.manifest={}
    result=h.candidate_plan('PLAN timed out')
    assert result['decision']=='run' and result['origin']=='supervisor_recovery'
    assert 'lab_workflow' not in result and result['pending']
    assert result['resolved_pending']==[]
    assert not (h.out/'Revision_final.json').exists()
    h.validate=lambda:dict(h.base,adaptation_notes='No geometry edit')
    with pytest.raises(TimeoutError):h.candidate_plan('PLAN timed out')


def test_timeout_candidate_still_runs_the_executor_and_cannot_skip_a_failed_geometry_gate(tmp_path,monkeypatch):
    h=harness(tmp_path,monkeypatch);h.base=profile();h.validate=lambda:dict(h.base,bar_top_z=5.)
    h.engine=tmp_path/'engine';(h.engine/'engine').mkdir(parents=True);h.manifest={}
    h.root=tmp_path/'run';h.profile=h.workspace/'Perfil.json';h.raw_hash='source'
    h.job={'id':'job','target':'case'};h.case={'id':'case'};h.images=[]
    h.db=SimpleNamespace(execute=lambda *a:None)
    h.state['max_attempts']=1;h.fresh_start=False;h.previous_plan=None;h.previous_draft=None
    h.previous=None;h.previous_root=None;h.previous_profile={};h.attempt_signatures=set()
    h.s.geometry_python='geometry';h.s.blender='blender';h.s.b4d_root='';h.s.live_blender=False
    h.prepare=lambda:None;h.defer_draft=lambda _:False
    h.think=lambda *a,**kw:(_ for _ in ()).throw(TimeoutError('PLAN deadline'))
    calls=[]
    def execute(*args):
        calls.append(args)
        raise RuntimeError('Actual geometry gate rejected thin walls')
    h.execute_attempt=execute
    h.publish=lambda *a:pytest.fail('A rejected geometry must not be published')
    with pytest.raises(RuntimeError,match='thin walls'):h.run()
    assert len(calls)==1 and '--profile' in calls[0][0]
    assert json.loads((h.out/'01_plan.json').read_text())['origin']=='supervisor_recovery'


@pytest.mark.parametrize('fresh',[False,True])
def test_prepare_recovers_only_numeric_candidate_and_respects_new_construction(client,monkeypatch,fresh):
    import shutil
    from dental_lab.worker import Worker
    from test_revisions import make_case
    c,app=client;s=app.state.settings;db=app.state.store
    s.app=APP;s.geometry_python='fake';s.agent_harness='codex'
    case=make_case(c,'interrupted-plan')
    old=db.one("SELECT * FROM jobs WHERE target=? AND kind='segment'",(case,));db.update_job(old['id'],'failed')
    source=db.one('SELECT s.* FROM sources s JOIN cases c ON c.source_id=s.id WHERE c.id=?',(case,))
    base=dict(profile(),source_sha256=digest(source['path']))
    directory=s.data/'runs'/old['id']/'outputs/Agente';workspace=s.data/'agent_work'/old['id'];workspace.mkdir(parents=True)
    shutil.copytree(APP/'engine',workspace/'engine',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(source['path'],workspace/'original.stl')
    manifest=engine_digest(APP/'engine/engine')
    write(directory/'Perfil_base.json',base);write(directory/'Motor_instalado.json',manifest)
    write(directory/'Estado.json',{'lab_workflow':{'sha256':lab_workflow.load_workflow(APP)['sha256']}})
    write(directory/'01_plan_Interrupcion.json',{'phase':'plan'})
    write(workspace/'Perfil.json',dict(base,bar_top_z=5.))
    request=c.post('/api/cases/'+case+'/generate',json={'fresh_start':fresh})
    job=db.one('SELECT * FROM jobs WHERE id=?',(request.json()['job_id'],))
    worker=Worker(s,db,app.state.ingest)
    monkeypatch.setattr(app.state.rag,'search',lambda *a,**kw:[])
    _,history=worker.plan_evidence(job);write(directory/'Historial_de_la_version.json',history)
    h=SegmentHarness(worker,job)
    def prepare(command,*a,**kw):
        output=Path(command[command.index('--output')+1]);write(output,base);write(output.with_suffix('.medidas.json'),{})
    h.process=prepare;h.prepare()
    assert h.validate()['bar_top_z']==(6. if fresh else 5.)
    assert bool(h.previous_plan)==(not fresh)
    if h.previous_plan:assert h.previous_plan['approval']=='NONE'
    assert not (h.root/'outputs/Inferior_independiente').exists()
