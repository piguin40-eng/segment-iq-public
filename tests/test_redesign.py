import json
from test_core import client
from test_revisions import make_case


def test_saved_corrections_redesign_the_same_case_without_resubmission(client):
    c,app=client;db=app.state.store
    case=make_case(c,'trabajo');other=make_case(c,'otro trabajo')
    previous=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    db.update_job(previous['id'],'done')
    general=c.post('/api/feedback',json={'author':'Equipo','text':'Más altura de barra en las propuestas.'}).json()['id']
    local=c.post('/api/feedback',json={'case_id':case,'author':'Equipo','text':'Aumentar altura 0,5 mm.'}).json()['id']
    unrelated=c.post('/api/feedback',json={'case_id':other,'author':'Equipo','text':'Menos altura en este otro caso.'}).json()['id']
    source=db.one('SELECT source_id FROM cases WHERE id=?',(case,))['source_id']
    response=c.post('/api/cases/'+case+'/redesign')
    assert response.status_code==200
    job=response.json()['job_id']
    assert response.json()['case_id']==case
    frozen=json.loads(db.one('SELECT feedback_ids FROM plan_context WHERE job_id=?',(job,))['feedback_ids'])
    assert set(frozen)=={general,local} and unrelated not in frozen
    assert len(c.get('/api/feedback').json())==3
    assert db.one('SELECT count(*) n FROM cases')['n']==2
    assert db.one('SELECT source_id FROM cases WHERE id=?',(case,))['source_id']==source
    assert db.one('SELECT status FROM jobs WHERE id=?',(previous['id'],))['status']=='done'
    assert c.post('/api/cases/'+case+'/redesign').status_code==409
    versions=c.get('/api/cases/'+case+'/versions').json()
    assert [v['id'] for v in versions]==[job,previous['id']]
    assert all(v['target']==case and v['kind']=='segment' for v in versions)


def test_redesign_requires_relevant_correction_and_existing_case(client):
    c,app=client;db=app.state.store
    case=make_case(c,'sin correcciones');other=make_case(c,'con correccion')
    db.execute("UPDATE jobs SET status='done' WHERE kind='segment'")
    c.post('/api/feedback',json={'case_id':other,'author':'Equipo','text':'Más altura en otro trabajo.'})
    assert c.post('/api/cases/'+case+'/redesign').status_code==400
    assert c.post('/api/cases/missing/redesign').status_code==404
    assert c.get('/api/cases/missing/versions').status_code==404
    assert db.one("SELECT count(*) n FROM jobs WHERE kind='segment'")['n']==2
