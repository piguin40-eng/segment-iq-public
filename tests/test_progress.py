import json
from test_core import client
from test_revisions import make_case

def test_live_progress_shows_only_completed_frames_and_preserves_failure(client):
    c,app=client;db=app.state.store;case=make_case(c,'Proceso')
    job=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    root=app.state.settings.data/'runs'/job['id']/'outputs'
    folder=root/'Proceso';folder.mkdir(parents=True)
    (folder/'01.png').write_bytes(b'completed frame')
    (root.parent/'outside.png').write_bytes(b'private')
    stored={'engine':'Blender','current_step':2,'error':'No se midió una chimenea',
            'stages':[{'step':1,'label':'Entrada','status':'done'},{'step':2,'label':'Conexiones','status':'failed'}],
            'frames':[{'step':1,'label':'Entrada','path':'Proceso/01.png'},
                      {'step':2,'label':'Incompleta','path':'Proceso/02.png'},
                      {'step':3,'label':'Fuera','path':'../outside.png'}]}
    (folder/'progreso.json').write_text(json.dumps(stored),encoding='utf-8')
    db.update_job(job['id'],'failed','No se midió una chimenea')
    url='/api/jobs/'+job['id']+'/progress'
    assert c.get(url,headers={'Authorization':'invalid'}).status_code==401
    response=c.get(url).json()
    assert response['status']=='failed' and response['current_step']==2
    assert [f['step'] for f in response['frames']]==[1]
    assert response['stages'][1]['status']=='failed'
    assert c.get('/api/jobs/unknown/progress').status_code==404

def test_progress_exposes_pending_corrections_before_generation_finishes(client):
    c,app=client;db=app.state.store;case=make_case(c,'Corrección')
    job=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    prep=app.state.settings.data/'profiles'/job['id'];prep.mkdir()
    (prep/'Perfil_automatico.medidas.json').write_text(json.dumps({'corrections_pending':[{'id':'a','text':'Espesor lateral','reason':'Pendiente de medición'}]}),encoding='utf-8')
    response=c.get('/api/jobs/'+job['id']+'/progress').json()
    assert response['corrections_pending'][0]['id']=='a'
    assert response['frames']==[] and response['status']=='queued'

def test_legacy_job_has_no_invented_frames(client):
    c,app=client;db=app.state.store;case=make_case(c,'Histórico')
    job=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    db.update_job(job['id'],'done')
    response=c.get('/api/jobs/'+job['id']+'/progress').json()
    assert response['frames']==[] and response['stages']==[]
    assert 'anterior' in response['engine']
    assert response['window_frames']==[]


def test_active_agent_plan_replaces_obsolete_parser_adjustments_in_viewer(client):
    c,app=client;db=app.state.store;case=make_case(c,'Plan actual')
    job=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    root=app.state.settings.data/'runs'/job['id']/'outputs'
    (root/'Agente').mkdir(parents=True)
    (root/'Preparacion').mkdir()
    (root/'Preparacion/Perfil_automatico.medidas.json').write_text(json.dumps({
        'corrections_applied':[{'changes':['Subir anterior 2 mm']}],
        'corrections_pending':[{'text':'Frase inicial del parser'}],
        'shape_refinement':{'trace':{'median_total_width_reduction_mm':2}}}))
    (root/'Agente/Estado.json').write_text(json.dumps({'proposed_changes':['Techo continuo y retenciones obligatorias'],
        'pending':['Medir pared distal']}))
    db.update_job(job['id'],'running')
    p=c.get('/api/jobs/'+job['id']+'/progress').json()
    assert p['corrections_applied'][0]['changes']==['Techo continuo y retenciones obligatorias']
    assert p['corrections_pending'][0]['text']=='Medir pared distal'
    assert p['preparation_pending'][0]['text']=='Frase inicial del parser'
    assert p['shape_refinement']=={}

def test_blender_window_frames_are_private_completed_and_distinct_from_renders(client):
    c,app=client;db=app.state.store;case=make_case(c,'Ventana real')
    job=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    root=app.state.settings.data/'runs'/job['id']/'outputs'
    window=root/'Proceso/Blender';window.mkdir(parents=True)
    (window/'0001.png').write_bytes(b'completed window screenshot')
    (root.parent/'private.png').write_bytes(b'private file')
    frames=[{'step':3,'path':'Proceso/Blender/0001.png','label':'Cono medido','created':100,'kind':'blender_window'},
            {'step':3,'path':'Proceso/Blender/0002.png'},
            {'step':3,'path':'../private.png'}]
    (window/'ventana.json').write_text(json.dumps({'frames':frames}),encoding='utf-8')
    # A real screenshot can exist while its stage is still running.
    (root/'Proceso/progreso.json').write_text(json.dumps({'current_step':3,'stages':[{'step':3,'status':'running'}]}))
    url='/api/jobs/'+job['id']+'/progress'
    assert c.get(url,headers={'Authorization':'invalid'}).status_code==401
    p=c.get(url).json()
    assert p['frames']==[] and p['window_frames']==[frames[0]]
    assert p['stages'][0]['status']=='running'
    image_url='/api/jobs/'+job['id']+'/file/Proceso/Blender/0001.png'
    assert c.get(image_url,headers={'Authorization':'invalid'}).status_code==401
    assert c.get(image_url).content==b'completed window screenshot'

def test_window_capture_failure_does_not_invent_frames_or_fail_geometry(client):
    c,app=client;db=app.state.store;case=make_case(c,'Captura interrumpida')
    job=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    folder=app.state.settings.data/'runs'/job['id']/'outputs/Proceso/Blender';folder.mkdir(parents=True)
    (folder/'ventana.json').write_text('{partial')
    (folder/'captura_error.txt').write_text('Render unavailable')
    db.update_job(job['id'],'done')
    p=c.get('/api/jobs/'+job['id']+'/progress').json()
    assert p['status']=='done' and p['window_capture_error']
    assert p['window_frames']==[]


def test_retry_reports_and_frames_use_the_same_attempt_not_a_stale_published_report(client):
    c,app=client;db=app.state.store;case=make_case(c,'Segundo intento')
    job=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    root=app.state.settings.data/'runs'/job['id']/'outputs'
    (root/'Agente').mkdir(parents=True)
    (root/'Agente/Estado.json').write_text(json.dumps({'attempt_path':'Intentos/02/outputs'}))
    old=root/'Inferior_independiente';old.mkdir()
    (old/'Validacion_PROPIA.json').write_text(json.dumps({'design_sections':{'minimum_sampled_occlusal_mm':.1}}))
    active=root/'Intentos/02/outputs/Inferior_independiente';active.mkdir(parents=True)
    (active/'Validacion_PROPIA.json').write_text(json.dumps({'design_sections':{'minimum_sampled_occlusal_mm':1.2}}))
    (active/'B4D_ejecucion.json').write_text(json.dumps({'status':'PASS','cement_gap_mm':.15}))
    (active/'Retenciones_medidas.json').write_text(json.dumps({'mode':'none'}))
    (active/'Comprobacion_extraccion.json').write_text(json.dumps({'status':'COLLISION_DETECTED','continuous_path_verified':False}))
    p=c.get('/api/jobs/'+job['id']+'/progress').json()
    assert p['measured_sections']['minimum_sampled_occlusal_mm']==1.2
    assert p['b4d']['status']=='PASS' and p['retentions']['mode']=='none'
    assert p['extraction']['status']=='COLLISION_DETECTED' and not p['extraction']['continuous_path_verified']
    # A new attempt with no measurements must not display the old minimum.
    (root/'Agente/Estado.json').write_text(json.dumps({'attempt_path':'Intentos/03/outputs'}))
    p=c.get('/api/jobs/'+job['id']+'/progress').json()
    assert p['measured_sections'] is None and p['b4d'] is None
    assert p['extraction'] is None


def test_unapproved_checkpoint_selects_valid_draft_instead_of_later_failure():
    from dental_lab.progress import result_file_groups
    files=[{'name':'Vista_propia.png','path':f'Intentos/{n:02d}/outputs/Inferior_independiente/Vista_propia.png'} for n in (1,2)]
    groups=result_file_groups(files,selected_attempt=1)
    previews=[f for f in groups if f['display_group']=='preview']
    assert len(previews)==1 and previews[0]['path'].startswith('Intentos/01/')
    assert 'pendiente de revisión' in previews[0]['proposal_label']
    assert not any(f['display_group']=='preview' for f in result_file_groups(files,selected_attempt=3))


def test_live_safety_summary_preserves_failures_and_refreshes_without_sending_clouds(tmp_path):
    import os
    from dental_lab.progress import safety_snapshot
    report=tmp_path/'Seguridad_oclusal_local.json'
    detail={'global_minimum_verified':False,'unresolved':True,
        'extra_openings_resolved':False,
        'attempts':[{'attempt':0,'phase':'baseline','minimum_sampled_mm':.12,
                     'sample_count':4000,'thin_sections':[{'xy':[1,2]}]*1000}],
        'surface_wall_checks':[{'samples':[{'point':[1,2,3]}]*4000}]}
    report.write_text(json.dumps(detail))
    stamp=report.stat().st_mtime_ns
    summary=safety_snapshot(report)
    assert summary['unresolved'] and not summary['global_minimum_verified']
    assert summary['extra_openings_resolved'] is False
    assert summary['attempts'][0]['minimum_sampled_mm']==.12
    assert summary['attempts'][0]['thin_section_count']==1000
    assert len(json.dumps(summary))<1000
    assert json.loads(report.read_text())==detail
    detail['attempts'][0]['minimum_sampled_mm']=.19
    report.write_text(json.dumps(detail))
    os.utime(report,ns=(stamp+1000000,stamp+1000000))
    assert safety_snapshot(report)['attempts'][0]['minimum_sampled_mm']==.19
