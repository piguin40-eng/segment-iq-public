import importlib.util,json,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from test_core import client
from test_revisions import make_case
from dental_lab.worker import Worker


def test_generation_freezes_its_corrections_and_does_not_require_json(client):
    c,app=client;db=app.state.store
    case=make_case(c,'nuevo')
    original=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    body={'case_id':case,'author':'Equipo','text':'Más altura 0,5 mm','request_generation':True}
    assert c.post('/api/feedback',json=body).status_code==409
    assert c.get('/api/feedback').json()==[]
    db.update_job(original['id'],'done')
    response=c.post('/api/feedback',json=body)
    assert response.status_code==200
    result=response.json();job=db.one('SELECT * FROM jobs WHERE id=?',(result['job_id'],))
    assert job['kind']=='segment' and job['status']=='queued'
    c.post('/api/feedback',json={'case_id':case,'author':'Equipo','text':'Más profundidad'})
    _,history=Worker(app.state.settings,db,app.state.ingest).plan_evidence(job)
    assert [r['id'] for r in history['feedback']]==[result['id']]
    assert db.one('SELECT status FROM cases WHERE id=?',(case,))['status']=='queued'


def test_concurrent_generation_requests_create_one_job(client):
    c,app=client;db=app.state.store;case=make_case(c,'concurrencia')
    db.execute("UPDATE jobs SET status='done' WHERE kind='segment' AND target=?",(case,))
    def queue(_):
        try:return db.queue_segment(case)
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(queue,range(8)))
    assert sum(r is not None for r in results)==1
    assert db.one("SELECT count(*) n FROM jobs WHERE kind='segment' AND status='queued' AND target=?",(case,))['n']==1


def test_preparation_failure_keeps_diagnostic_without_requesting_profile(client,monkeypatch):
    c,app=client;db=app.state.store;case=make_case(c,'invalido')
    job=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    app.state.settings.geometry_python='fake-python'
    def fail(*args,**kwargs):raise RuntimeError('STL sin una malla válida')
    monkeypatch.setattr('dental_lab.worker.subprocess.run',fail)
    import pytest
    with pytest.raises(RuntimeError,match='malla válida'):
        Worker(app.state.settings,db,app.state.ingest).segment(job)
    assert db.one('SELECT status FROM cases WHERE id=?',(case,))['status']=='failed'
    files=c.get('/api/jobs/'+job['id']+'/files').json()
    assert any(r['name']=='Diagnostico.txt' for r in files)
    assert any(r['name']=='Historial_de_la_version.json' for r in files)


def test_simple_corrections_are_rebuilt_once_and_regional_requests_are_not_global():
    import pytest
    pytest.importorskip('trimesh')
    spec=importlib.util.spec_from_file_location('prepare',Path(__file__).parents[1]/'engine/prepare_profile.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    history={'feedback':[{'id':'a','created':1,'status':'correction','text':'Más altura 0,5 mm'},
                         {'id':'b','created':2,'status':'correction','text':'Más profundidad en la pieza 37'}]}
    first=module.corrections(history)
    assert first[:2]==(.5,0.) and module.corrections(history)==first
    assert [r['id'] for r in first[2]]==['a'] and [r['id'] for r in first[3]]==['b']
