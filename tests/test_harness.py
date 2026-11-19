import copy
import json
from pathlib import Path
import pytest
from dental_lab.harness import validate_candidate,validate_adapter,SegmentHarness,EDITABLE_CODE,remaining_pending,result_evidence,tool_error_summary,resumable_draft,write
from dental_lab.revisions import engine_digest
from dental_lab.progress import job_progress
from test_core import client

ROOT=Path(__file__).parents[1]


@pytest.mark.parametrize('fresh',[False,True])
@pytest.mark.parametrize('measurement_migration',[False,True])
def test_fresh_generation_keeps_evidence_but_does_not_inherit_draft_geometry(client,monkeypatch,fresh,measurement_migration):
    from dental_lab.worker import Worker
    from dental_lab.harness import digest,ORIENTED_MATERIAL_MIGRATION
    from test_revisions import make_case
    c,app=client;db=app.state.store;s=app.state.settings
    s.app=ROOT;s.geometry_python='fake-geometry';s.agent_harness='codex'
    case=make_case(c,'fresh-construction')
    old=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    db.update_job(old['id'],'needs_review')
    source=db.one('SELECT s.* FROM sources s JOIN cases c ON c.source_id=s.id WHERE c.id=?',(case,))
    source_hash=digest(source['path']);base=dict(profile(),source_sha256=source_hash)
    root=s.data/'runs'/old['id'];attempt=make_draft(root)
    manifest=engine_digest(ROOT/'engine/engine')
    if measurement_migration:
        manifest.pop('ray_material.py')
        manifest['design_checks.py']=ORIENTED_MATERIAL_MIGRATION[0]
    write(root/'outputs/Agente/Perfil_base.json',base)
    write(root/'outputs/Agente/Motor_instalado.json',manifest)
    write(attempt/'Ejecucion.json',{'status':'GEOMETRY_PASS_DESIGN_REVIEW_PENDING','source_sha256':source_hash})
    write(attempt/'perfil_ejecutado.json',dict(base,bar_top_z=2.))
    inherited='# rejected historical adapter\n'
    (attempt/'Codigo/engine/shape_refinement.py').write_text(inherited)
    request=c.post('/api/cases/'+case+'/generate',json={'fresh_start':fresh})
    assert request.status_code==200
    job=db.one('SELECT * FROM jobs WHERE id=?',(request.json()['job_id'],))
    assert bool(db.one('SELECT fresh_start FROM segment_options WHERE job_id=?',(job['id'],))['fresh_start'])==fresh
    harness=SegmentHarness(Worker(s,db,app.state.ingest),job)
    def preparation(command,*args,**kwargs):
        output=Path(command[command.index('--output')+1])
        write(output,base);write(output.with_suffix('.medidas.json'),{})
    harness.process=preparation
    monkeypatch.setattr(app.state.rag,'search',lambda *a,**kw:[])
    harness.prepare()
    candidate=json.loads(harness.profile.read_text(encoding='utf-8'))
    assert candidate['bar_top_z']==(6. if fresh else 2.)
    expected=(ROOT/'engine/engine/shape_refinement.py').read_text(encoding='utf-8') if fresh else inherited
    assert (harness.engine/'engine/shape_refinement.py').read_text(encoding='utf-8')==expected
    for name in ['design_checks.py','ray_material.py']:
        assert digest(harness.engine/'engine'/name)==digest(ROOT/'engine/engine'/name)
    context=json.loads((harness.workspace/'Contexto.json').read_text(encoding='utf-8'))
    assert context['start_mode']==('fresh_from_original' if fresh else 'continue_measured')
    assert context['previous_result']['approval']=='draft_needs_review'
    assert context['previous_result']['meshes_read_only']
    assert context['previous_failed_attempts'][0]['job_id']==old['id']
    assert digest(harness.workspace/'original.stl')==source_hash


def test_tool_failure_displays_the_cause_and_preserves_the_complete_log(tmp_path):
    log=tmp_path/'Preparacion.log'
    content='Traceback (most recent call last):\n  File "prepare_profile.py", line 213\n    raise ValueError(...)\nValueError: El corredor no tiene espacio suficiente.\n'
    log.write_text(content,encoding='utf-8')
    message=tool_error_summary(log)
    assert 'corredor no tiene espacio' in message
    assert 'Traceback' not in message and 'line 213' not in message
    assert log.read_text(encoding='utf-8')==content


def test_unknown_tool_failure_links_its_log_without_pretending_success(tmp_path):
    log=tmp_path/'Blender.log';log.write_text('native crash 0x01',encoding='utf-8')
    assert 'error' in tool_error_summary(log) and 'Blender.log' in tool_error_summary(log)

def profile():
    return {'source_sha256':'source','bar_top_z':6.,'cone_top_z':6.,'trace_xy':[[1.,2.]]*8,
            'max_connection_error_mm':.001,'connections':[{'center':[1,2,3]}],
            'minimum_supra_mm':.8,'shape_refinement':{'cervical_bevel_mm':.2}}

def test_agent_can_use_explicit_shape_dimension_without_a_parser_rule(tmp_path):
    a=profile();b=copy.deepcopy(a);b['shape_refinement']['cervical_bevel_mm']=.25
    assert validate_candidate(a,b,tmp_path,{})==['shape_refinement']


def test_agent_can_follow_optional_retention_protocol_without_changing_safety(tmp_path):
    a=profile();b=copy.deepcopy(a);b['retention_mode']='none'
    assert validate_candidate(a,b,tmp_path,{})==['retention_mode']
    b['retention_mode']='ignore_errors'
    with pytest.raises(ValueError,match='retenciones'):validate_candidate(a,b,tmp_path,{})

@pytest.mark.parametrize('key,value',[('source_sha256','wrong'),('connections',[]),
                                    ('max_connection_error_mm',1),('minimum_supra_mm',.1)])
def test_model_cannot_change_source_connections_or_validation_thresholds(tmp_path,key,value):
    a=profile();b=copy.deepcopy(a);b[key]=value
    with pytest.raises(ValueError,match='protegidos'):validate_candidate(a,b,tmp_path,{})

@pytest.mark.parametrize('value',[float('nan'),float('inf'),-.2,.6])
def test_invalid_bevel_proposal_rejected(tmp_path,value):
    a=profile();b=copy.deepcopy(a);b['shape_refinement']['cervical_bevel_mm']=value
    with pytest.raises(ValueError):validate_candidate(a,b,tmp_path,{})

def test_agent_cannot_rewrite_validation(tmp_path):
    path=tmp_path/'11_validacion.py';path.write_text('x=1')
    manifest=engine_digest(tmp_path);path.write_text('x=2')
    with pytest.raises(ValueError,match='protegido'):validate_candidate(profile(),profile(),tmp_path,manifest)

@pytest.mark.parametrize('code',['import subprocess','import os','open("x","w")',
                                'import numpy as np\nnp.save("x",[1])',
                                'from numpy import load as innocent',
                                'import numpy.ctypeslib as c',
                                'getattr(x,"save")','x.__class__'])
def test_geometry_adapter_cannot_add_process_file_or_dynamic_execution(tmp_path,code):
    path=tmp_path/'shape_refinement.py';path.write_text(code)
    with pytest.raises(ValueError):validate_adapter(path)

def test_current_numerical_adapters_pass_policy():
    for name in EDITABLE_CODE-{'case_geometry.py'}:validate_adapter(ROOT/'engine/engine'/name)

def test_attempt_progress_exposes_real_frames_inside_outputs(tmp_path):
    root=tmp_path/'runs/abc/outputs'
    (root/'Agente').mkdir(parents=True)
    (root/'Agente/Estado.json').write_text(json.dumps({'attempt_path':'Intentos/01/outputs','status':'executing','pending':['Comprobar la terminación']}))
    stage=root/'Intentos/01/outputs/Proceso';stage.mkdir(parents=True)
    (stage/'01.png').write_bytes(b'actual-image')
    (stage/'progreso.json').write_text(json.dumps({'current_step':1,'frames':[{'path':'Proceso/01.png','step':1}]}))
    result=job_progress(tmp_path,{'id':'abc','target':'case','status':'running','detail':'agent'})
    assert result['frames'][0]['path']=='Intentos/01/outputs/Proceso/01.png'
    assert result['current_step']==1 and result['agent']['status']=='executing'
    assert result['corrections_pending'][0]['text']=='Comprobar la terminación'

def test_failed_attempt_path_cannot_escape_results(tmp_path):
    root=tmp_path/'runs/abc/outputs/Agente';root.mkdir(parents=True)
    (root/'Estado.json').write_text(json.dumps({'attempt_path':'Intentos/../../../../../escape'}))
    result=job_progress(tmp_path,{'id':'abc','target':'case','status':'running','detail':'agent'})
    assert result['frames']==[]

def test_worker_routes_generation_to_harness_when_enabled(client,monkeypatch):
    from dental_lab.worker import Worker
    _,app=client;s=app.state.settings;s.agent_harness='codex'
    calls=[]
    monkeypatch.setattr(SegmentHarness,'run',lambda self:calls.append(self.job['id']) or 'agent-ran')
    assert Worker(s,app.state.store,app.state.ingest).segment({'id':'job','target':'case'})=='agent-ran'
    assert calls==['job']


def test_worker_keeps_unapproved_draft_separate_from_success_and_failure():
    import time
    from types import SimpleNamespace
    from dental_lab.worker import Worker,DraftNeedsReview
    updates=[]
    job={'id':'draft-job','kind':'segment','target':'case'}
    db=SimpleNamespace(one=lambda *args:job,update_job=lambda *args:updates.append(args),
                       execute=lambda *args:None)
    worker=Worker(None,db,None);worker.scan_at=time.time()+3600
    def segment(_):
        worker.stop.set()
        raise DraftNeedsReview('Falta corregir la extracción')
    worker.segment=segment;worker.loop()
    assert [row[1] for row in updates]==['running','needs_review']


def test_equal_volume_is_not_confused_with_equal_geometry(tmp_path):
    import sys
    trimesh=pytest.importorskip('trimesh');pytest.importorskip('manifold3d')
    sys.path.insert(0,str(ROOT/'engine'))
    from compare_results import compare
    before=tmp_path/'old';after=tmp_path/'new';before.mkdir();after.mkdir()
    for name in ('Primaria_SUP_PROPIA.stl','Supra_SUP_PROPIA.stl'):
        box=trimesh.creation.box([2,2,2]);box.export(before/name)
        box.apply_translation([.2,0,0]);box.export(after/name)
    assert compare(before,after)['geometry_changed']
    assert not compare(before,before)['geometry_changed']


def test_resolved_shape_clause_disappears_but_strength_and_global_thickness_do_not():
    rows=[{'text':t} for t in ['barra recta y más estrecha','no debe romper nunca','grosor mínimo en toda la superficie']]
    review={'resolved_pending':[r['text'] for r in rows],'pending':[]}
    remaining=remaining_pending({'corrections_pending':rows},review)
    assert remaining==rows[1:]


def test_previous_proposal_meshes_are_available_for_equivalent_section_comparison(tmp_path):
    root=tmp_path/'accepted_job';output=root/'outputs/Inferior_independiente';output.mkdir(parents=True)
    (output/'Primaria_SUP_PROPIA.stl').write_bytes(b'previous actual mesh')
    write(output/'Comprobacion_extraccion.json',{'status':'COLLISION_DETECTED'})
    working=root/'work/inf_independiente';working.mkdir(parents=True)
    (working/'Primaria_final.npz').write_bytes(b'working coordinates')
    result=result_evidence(root)
    assert result['job_id']=='accepted_job'
    assert result['meshes_read_only']==[str((output/'Primaria_SUP_PROPIA.stl').resolve())]
    assert result['reports_read_only']==[str((output/'Comprobacion_extraccion.json').resolve())]
    assert result['working_meshes_read_only']==[str((working/'Primaria_final.npz').resolve())]
    assert 'raw_to_work' in result['coordinate_note']


def make_draft(root,number='01'):
    metadata=root/'outputs/Agente';attempt=root/'outputs/Intentos'/number
    output=attempt/'outputs/Inferior_independiente';output.mkdir(parents=True)
    (attempt/'Codigo/engine').mkdir(parents=True)
    write(metadata/'Perfil_base.json',{'source_sha256':'source'})
    write(metadata/'Motor_instalado.json',{'validator.py':'trusted'})
    write(metadata/(number+'_review.json'),{'decision':'retry','pending':['Rectificar el techo']})
    write(attempt/'perfil_ejecutado.json',{'source_sha256':'source','bar_top_z':2})
    write(attempt/'Ejecucion.json',{'status':'GEOMETRY_PASS_DESIGN_REVIEW_PENDING','source_sha256':'source'})
    write(output/'Resultado_controles.json',{'geometry_checks':'PASS','design_review':'PENDING'})
    write(output/'Validacion_PROPIA.json',{'measured_minimum':.9})
    for name in ('Primaria_SUP_PROPIA.stl','Supra_SUP_PROPIA.stl','Vista_propia.png'):
        (output/name).write_bytes(b'previous evidence')
    return attempt


def test_resume_keeps_rejection_and_uses_latest_measured_draft(tmp_path):
    root=tmp_path/'job';first=make_draft(root);last=make_draft(root,'02')
    result=resumable_draft(root,'source',{'validator.py':'trusted'})
    assert result['root']==last and result['metadata_root']==root
    assert result['job_id']=='job' and result['attempt']==2
    assert result['approval']=='draft_needs_review'
    assert result['review']['decision']=='retry'
    assert result['review']['pending']==['Rectificar el techo']
    # A newer failed build must not erase earlier useful parameters.
    write(last/'Ejecucion.json',{'status':'FAILED','source_sha256':'source'})
    assert resumable_draft(root,'source',{'validator.py':'trusted'})['root']==first
    assert not (root/'outputs/Inferior_independiente').exists()


@pytest.mark.parametrize('arch',['SUP','INF'])
def test_resume_uses_the_measured_arch_and_requires_both_correct_exports(tmp_path,arch):
    root=tmp_path/'job';attempt=make_draft(root)
    write(root/'outputs/Agente/Perfil_base.json',{'source_sha256':'source','arch':arch})
    write(attempt/'perfil_ejecutado.json',{'source_sha256':'source','arch':arch,'bar_top_z':2})
    output=attempt/'outputs/Inferior_independiente'
    if arch=='INF':
        for stem in ('Primaria','Supra'):
            (output/f'{stem}_SUP_PROPIA.stl').rename(output/f'{stem}_INF_PROPIA.stl')
    result=resumable_draft(root,'source',{'validator.py':'trusted'})
    assert result['root']==attempt and result['approval']=='draft_needs_review'
    assert result['review']['decision']=='retry'
    opposite='INF' if arch=='SUP' else 'SUP'
    (output/f'Supra_{arch}_PROPIA.stl').rename(output/f'Supra_{opposite}_PROPIA.stl')
    assert resumable_draft(root,'source',{'validator.py':'trusted'}) is None


def test_resume_rejects_an_arch_that_differs_from_measured_baseline(tmp_path):
    root=tmp_path/'job';attempt=make_draft(root)
    write(root/'outputs/Agente/Perfil_base.json',{'source_sha256':'source','arch':'INF'})
    write(attempt/'perfil_ejecutado.json',{'source_sha256':'source','arch':'SUP'})
    assert resumable_draft(root,'source',{'validator.py':'trusted'}) is None


def test_only_reviewed_retention_migration_can_preserve_numeric_adapters():
    from dental_lab.harness import adapter_engine_compatible,RETENTION_CONTACT_MIGRATION
    old,new=RETENTION_CONTACT_MIGRATION
    before={'retention_safety.py':old,'validator.py':'fixed'}
    after=dict(before,**{'retention_safety.py':new})
    assert adapter_engine_compatible(before,after)
    assert not adapter_engine_compatible(after,before)
    assert not adapter_engine_compatible(before,dict(after,**{'validator.py':'changed'}))
    assert not adapter_engine_compatible(before,dict(after,**{'retention_safety.py':'unreviewed'}))


def test_oriented_material_migration_preserves_only_reviewed_recipes_and_new_checks():
    from dental_lab.harness import adapter_engine_compatible,ORIENTED_MATERIAL_MIGRATION,digest
    old,new,helper=ORIENTED_MATERIAL_MIGRATION
    assert digest(ROOT/'engine/engine/design_checks.py')==new
    assert digest(ROOT/'engine/engine/ray_material.py')==helper
    before={'design_checks.py':old,'other_control.py':'fixed'}
    after=dict(before,**{'design_checks.py':new,'ray_material.py':helper})
    assert adapter_engine_compatible(before,after)
    assert not adapter_engine_compatible(after,before)
    assert not adapter_engine_compatible(before,dict(after,**{'ray_material.py':'unknown'}))
    assert not adapter_engine_compatible(before,dict(after,**{'other_control.py':'changed'}))
    assert not adapter_engine_compatible(before,dict(after,**{'extra.py':'unreviewed'}))


def test_small_retention_mesh_migration_keeps_current_immutable_controls():
    from dental_lab.harness import adapter_engine_compatible,RETENTION_MESH_MIGRATION,RETENTION_MESH_HELPER,digest
    before={name:pair[0] for name,pair in RETENTION_MESH_MIGRATION.items()}
    after={name:pair[1] for name,pair in RETENTION_MESH_MIGRATION.items()}
    before['validator.py']=after['validator.py']='fixed'
    after['retention_mesh.py']=RETENTION_MESH_HELPER
    for name in RETENTION_MESH_MIGRATION:
        assert digest(ROOT/'engine/engine'/name)==after[name]
    assert digest(ROOT/'engine/engine/retention_mesh.py')==RETENTION_MESH_HELPER
    assert adapter_engine_compatible(before,after)
    assert not adapter_engine_compatible(after,before)
    assert not adapter_engine_compatible(before,dict(after,**{'validator.py':'changed'}))
    assert not adapter_engine_compatible(before,dict(after,**{'retention_mesh.py':'unknown'}))


def test_supra_export_migration_requires_all_reviewed_stages_and_unchanged_gates():
    from dental_lab.harness import adapter_engine_compatible,SUPRA_EXPORT_MIGRATION,digest
    before={name:pair[0] for name,pair in SUPRA_EXPORT_MIGRATION.items()}
    after={name:pair[1] for name,pair in SUPRA_EXPORT_MIGRATION.items()}
    before['design_checks.py']=after['design_checks.py']='fixed'
    for name in SUPRA_EXPORT_MIGRATION:
        assert digest(ROOT/'engine/engine'/name)==after[name]
    assert adapter_engine_compatible(before,after)
    assert not adapter_engine_compatible(after,before)
    assert not adapter_engine_compatible(before,dict(after,**{'design_checks.py':'changed'}))
    assert not adapter_engine_compatible(before,dict(after,**{'11_validacion.py':before['11_validacion.py']}))


@pytest.mark.parametrize('change',['source','engine','execution_source','profile_source','controls','missing_mesh'])
def test_resume_rejects_incompatible_or_incomplete_geometry(tmp_path,change):
    root=tmp_path/'job';attempt=make_draft(root)
    source='source';manifest={'validator.py':'trusted'}
    if change=='source':source='different-case'
    elif change=='engine':manifest={'validator.py':'new-engine'}
    elif change=='execution_source':write(attempt/'Ejecucion.json',{'status':'GEOMETRY_PASS_DESIGN_REVIEW_PENDING','source_sha256':'other'})
    elif change=='profile_source':write(attempt/'perfil_ejecutado.json',{'source_sha256':'other'})
    elif change=='controls':write(attempt/'outputs/Inferior_independiente/Resultado_controles.json',{'geometry_checks':'FAIL'})
    elif change=='missing_mesh':(attempt/'outputs/Inferior_independiente/Supra_SUP_PROPIA.stl').unlink()
    assert resumable_draft(root,source,manifest) is None


def test_measured_draft_can_require_review_without_becoming_approved(tmp_path):
    from types import SimpleNamespace
    from dental_lab.harness import digest
    root=tmp_path/'job';attempt=make_draft(root)
    workspace=tmp_path/'workspace';workspace.mkdir();raw=workspace/'original.stl';raw.write_bytes(b'original')
    base=profile();base['source_sha256']=digest(raw)
    write(root/'outputs/Agente/Perfil_base.json',base);write(root/'outputs/Agente/Motor_instalado.json',{})
    write(attempt/'perfil_ejecutado.json',dict(base,input=str(raw)))
    write(attempt/'Ejecucion.json',{'status':'GEOMETRY_PASS_DESIGN_REVIEW_PENDING','source_sha256':base['source_sha256'],'source':str(raw)})
    events=[]
    harness=object.__new__(SegmentHarness)
    harness.root=root;harness.out=root/'outputs/Agente';harness.workspace=workspace
    harness.source={'path':str(raw)};harness.raw_hash=base['source_sha256'];harness.manifest={}
    harness.job={'id':'job','target':'case'};harness.state={'status':'failed','attempt':3,'events':[]}
    harness.db=SimpleNamespace(execute=lambda *a:events.append(a),update_job=lambda *a:events.append(a))
    assert harness.defer_draft('La barra requiere otro ajuste')
    checkpoint=json.loads((harness.out/'Borrador_no_aprobado.json').read_text(encoding='utf-8'))
    assert checkpoint['approval']=='NOT_ACCEPTED' and checkpoint['attempt']==1
    assert harness.state['status']=='needs_review' and harness.state['design_review']=='NOT_ACCEPTED'
    assert harness.state['attempt_path']=='Intentos/01/outputs'
    assert harness.state['pending']==['Rectificar el techo']
    assert events[-1][1]=='needs_review'
    assert not (root/'outputs/Inferior_independiente').exists()
    assert not (harness.out/'Revision_final.json').exists()
    write(attempt/'perfil_ejecutado.json',dict(base,input='different input'))
    with pytest.raises(ValueError,match='input'):harness.defer_draft('Mismatched input provenance')
    # A changed original cannot be disguised as a completed draft.
    raw.write_bytes(b'changed original')
    assert not harness.defer_draft('source changed')


@pytest.mark.parametrize('failed',[True,False])
def test_attempt_evidence_is_available_even_when_executor_rejects_mesh(tmp_path,failed):
    harness=object.__new__(SegmentHarness)
    harness.workspace=tmp_path/'workspace';harness.workspace.mkdir()
    harness.out=tmp_path/'agent';harness.out.mkdir()
    run=tmp_path/'runs/outputs/Intentos/01'
    output=run/'outputs/Inferior_independiente';output.mkdir(parents=True)
    (run/'Ejecucion.json').write_text(json.dumps({'status':'FAILED' if failed else 'GEOMETRY_PASS_DESIGN_REVIEW_PENDING','error':'thin interval' if failed else None}))
    (output/'Validacion_PROPIA.json').write_text(json.dumps({'minimum_sampled_occlusal_mm':.063}))
    (output/'Vista_propia.png').write_bytes(b'actual-view')
    (output/'Primaria_SUP_PROPIA.stl').write_bytes(b'actual-mesh')
    log=harness.out/'01_Blender.log';log.write_text('actual validator diagnostic')
    def execute(*args,**kwargs):
        if failed: raise RuntimeError('executor failed')
    harness.process=execute
    if failed:
        with pytest.raises(RuntimeError,match='executor failed'):harness.execute_attempt([],run,log)
    else:harness.execute_attempt([],run,log)
    evidence=json.loads((harness.workspace/'Ultimo_intento.json').read_text(encoding='utf-8'))
    assert evidence['execution_status']==('FAILED' if failed else 'GEOMETRY_PASS_DESIGN_REVIEW_PENDING')
    assert evidence['meshes_read_only']==[str((output/'Primaria_SUP_PROPIA.stl').resolve())]
    report=next(p for p in evidence['reports'] if p.endswith('Validacion_PROPIA.json'))
    assert json.loads((harness.workspace/report).read_text())['minimum_sampled_occlusal_mm']==.063
    view=next(p for p in evidence['reports'] if p.endswith('Vista_propia.png'))
    assert (harness.workspace/view).read_bytes()==b'actual-view'
    assert not (tmp_path/'runs/outputs/Inferior_independiente').exists()


@pytest.mark.parametrize('failed_gate',[False,True])
def test_completed_geometry_delivers_independent_reports_even_when_gate_failed(tmp_path,failed_gate):
    from types import SimpleNamespace
    harness=object.__new__(SegmentHarness)
    harness.workspace=tmp_path/'workspace';harness.workspace.mkdir()
    harness.out=tmp_path/'agent';harness.out.mkdir()
    harness.trusted=tmp_path/'trusted';harness.trusted.mkdir()
    (harness.trusted/'inspect_insertion.py').write_text('# supervisor-owned inspector')
    (harness.trusted/'inspect_walls.py').write_text('# supervisor-owned wall inspector')
    harness.event=lambda *args:None
    harness.s=SimpleNamespace(geometry_python='geometry-python')
    run=tmp_path/'run/outputs/Intentos/01';work=run/'work/inf_independiente';work.mkdir(parents=True)
    for name in ('entrada.npz','Primaria_final.npz','Supra.npz'):(work/name).write_bytes(b'mesh fixture')
    write(run/'outputs/Inferior_independiente/Validacion_PROPIA.json',{'measured':True})
    calls=[]
    def process(command,*args,**kwargs):
        calls.append(command)
        if command==['build'] and failed_gate:raise RuntimeError('occlusal gate failed')
        if '--output' in command:
            write(command[command.index('--output')+1],{'status':'WALL_DEFECTS_FOUND' if 'inspect_walls.py' in command[1] else 'COLLISION_DETECTED','continuous_path_verified':False})
    harness.process=process
    if failed_gate:
        with pytest.raises(RuntimeError,match='occlusal gate failed'):
            harness.execute_attempt(['build'],run,harness.out/'01_Blender.log')
    else:harness.execute_attempt(['build'],run,harness.out/'01_Blender.log')
    assert len(calls)==3 and calls[1][1]==str(harness.trusted/'inspect_insertion.py')
    assert calls[2][1]==str(harness.trusted/'inspect_walls.py')
    evidence=json.loads((harness.workspace/'Ultimo_intento.json').read_text(encoding='utf-8'))
    report=next(p for p in evidence['reports'] if p.endswith('Comprobacion_extraccion.json'))
    assert json.loads((harness.workspace/report).read_text())['status']=='COLLISION_DETECTED'
    wall=next(p for p in evidence['reports'] if p.endswith('Comprobacion_paredes.json'))
    assert json.loads((harness.workspace/wall).read_text())['status']=='WALL_DEFECTS_FOUND'
