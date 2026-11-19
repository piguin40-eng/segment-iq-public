import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from dental_lab.config import Settings
from dental_lab.server import create_app

@pytest.fixture
def client(tmp_path):
    s=Settings(data=tmp_path,password='test-password-only',semantic=False,vision=False).prepare()
    app=create_app(s,start_worker=False)
    with TestClient(app) as client:
        client.headers['Authorization']='Bearer test-password-only'
        yield client,app

def test_auth_and_cross_origin(client):
    c,a=client
    assert c.get('/api/status',headers={'Authorization':'bad'}).status_code==401
    assert c.post('/api/chat',headers={'Origin':'https://other-site.example'},json={'question':'altura barra'}).status_code==403

def test_upload_dedup_and_no_path_escape(client):
    c,a=client
    r=c.post('/api/upload',files={'file':('../../escape.md',b'Cobertura distal de la pieza 37')});assert r.status_code==200
    id=r.json()['id'];r=c.post('/api/upload',files={'file':('mismo.md',b'Cobertura distal de la pieza 37')})
    assert r.json()['id']==id and not r.json()['new']
    row=a.state.store.one('SELECT * FROM sources WHERE id=?',(id,));assert Path(row['path']).is_relative_to(a.state.settings.data/'originals')
    a.state.ingest.process(id)
    results=c.get('/api/search',params={'q':'pieza 37 cobertura'}).json()
    assert results[0]['source_id']==id and '37' in results[0]['text']
    a.state.ingest.process(id)
    assert a.state.store.one('SELECT count(*) n FROM chunks')['n']==1

def test_feedback_persists_and_is_retrievable(client):
    c,a=client
    r=c.post('/api/feedback',json={'author':'Tecnico de prueba','text':'La barra debe cubrir la pieza distal 37 y tener mas altura.','status':'correction'})
    assert r.status_code==200
    hits=c.get('/api/search',params={'q':'altura barra distal'}).json()
    assert any(h['kind']=='correccion_tecnico' for h in hits)
    assert c.post('/api/feedback',json={'author':'Tecnico','text':'Aprobado','status':'approved'}).status_code==400

def test_case_queues_segmentation_without_profile_and_prevents_duplicates(client):
    c,a=client
    source=c.post('/api/upload',files={'file':('input.stl',b'solid test\nendsolid test')}).json()['id']
    created=c.post('/api/cases',json={'name':'Caso prueba','source_id':source}).json();case=created['id']
    job=a.state.store.one('SELECT * FROM jobs WHERE id=?',(created['job_id'],))
    assert job['kind']=='segment' and job['target']==case and job['status']=='queued'
    assert a.state.store.one('SELECT profile_path FROM cases WHERE id=?',(case,))['profile_path'] is None
    assert c.post('/api/cases/'+case+'/generate').status_code==409
    a.state.store.update_job(job['id'],'failed','Detector needs adaptation')
    assert c.post('/api/cases/'+case+'/generate').status_code==200
    assert c.post('/api/cases/'+case+'/profile',files={'file':('profile.json',b'{}')}).status_code==400

def test_video_timestamp_retained(client):
    c,a=client
    row,_=a.state.ingest.register(_temp_doc(a),'Video de prueba')
    a.state.store.add_chunks(row['id'],[{'text':'Shrinkwrap sobre la barra','kind':'ocr_no_revisado','start':83.5,'end':83.5,'frame':'derived/frame.jpg'}])
    hit=c.get('/api/search',params={'q':'Shrinkwrap'}).json()[0]
    assert hit['start']==83.5 and hit['kind']=='ocr_no_revisado'

def _temp_doc(a):
    p=a.state.settings.data/'tmp.txt';p.write_text('prueba');return p

def test_rejects_volume_described_as_height():
    from dental_lab.rag import dimensional_error
    assert dimensional_error('La altura final fue **1433,81 mm³**.')
    assert not dimensional_error('El volumen es 1433,81 mm³. Falta medir la altura por secciones.')
