import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'engine'))
from lab_rules import observation_intents
from dental_lab.revisions import compare_profiles
from test_core import client


@pytest.mark.parametrize('text,expected',[
    ('Más soporte a la supra, más baja la barra y centra siempre los implantes. La barra en medio de las conexiones y más reducida de altura.',-.5),
    ('Bajar la altura de la barra 0,7 mm. La supra debe tener espesor mínimo de 0.8 mm.',-.7),
    ('Menos altura de metal, más profundidad.',-.5),
    ('El metal está demasiado alto.',-.5),
    ('Tiene demasiada altura del metal.',-.5),
    ('Aumentar altura 0,5 mm.',.5),
])
def test_height_is_bound_to_its_own_clause(text,expected):
    assert observation_intents(text)[0]['height']==pytest.approx(expected)


def test_connection_centering_does_not_move_implants_or_discard_unknown_clauses():
    intents,pending=observation_intents('Centra los implantes: la barra debe pasar por las conexiones en el medio. Cambia el acabado a espejo.')
    assert intents['center_connections']
    assert 'height' not in intents
    assert pending==['cambia el acabado a espejo']


def test_connections_through_middle_are_recognized_before_comma():
    intents,_=observation_intents('Las conexiones tienen que pasar por el medio de la barra, repartiendo espesor equilibrado a ambos lados.')
    assert intents['center_connections']
    assert 'center_connections' not in observation_intents('Las conexiones no deben pasar por el medio de la barra.')[0]


def test_nominal_centering_failure_reaches_agent_without_clearing_final_requirement(monkeypatch):
    np=pytest.importorskip('numpy')
    import prepare_profile as prep
    trace=np.array([[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]])
    config={'center_connections':True}
    monkeypatch.setattr(prep,'trace_balance',lambda _: [{'covered':False}])
    def fail(*_):raise ValueError('No hay espacio bilateral para centrar la barra y reservar supra; diagnóstico conservado sin desplazar las conexiones.')
    monkeypatch.setattr(prep,'centered_trace',fail)
    result,report=prep.initial_centering(None,trace,[],config,.95)
    assert np.array_equal(result,trace) and result is not trace
    assert report['status']=='pending_agent_redesign'
    assert config['center_connections'] is True
    def bad_axis(*_):raise ValueError('Eje inválido')
    monkeypatch.setattr(prep,'centered_trace',bad_axis)
    with pytest.raises(ValueError,match='Eje inválido'):prep.initial_centering(None,trace,[],config,.95)


@pytest.mark.parametrize('text',[
    'No reducir la altura de la barra.',
    'Aumentar altura en la pieza 37.',
    'Reducir altura 4 mm.',
    'Más soporte a la supra.',
])
def test_unsupported_or_negated_change_is_not_silently_global(text):
    intents,pending=observation_intents(text)
    assert 'height' not in intents and pending


def test_unchanged_profile_is_not_a_redesign_and_text_alone_does_not_change_it():
    before={'bar_top_z':6.,'trace_xy':[[1,2],[2,3]],'source_sha256':'same'}
    after=dict(before,adaptation_notes='Corregido',bar_top_z=6.+1e-9)
    assert not compare_profiles(before,after)['geometry_parameters_changed']
    after['bar_top_z']=5.5
    assert compare_profiles(before,after)['bar_top_change_mm']==-.5
    assert compare_profiles(before,after)['parameters_changed']==['bar_top_z']


def test_centering_uses_current_measured_axis_and_final_metal_is_checked():
    np=pytest.importorskip('numpy'); trimesh=pytest.importorskip('trimesh')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from bar_centering import centered_trace,primary_balance
    body=trimesh.creation.box([20,16,12]);body.apply_translation([0,0,6])
    t=np.linspace(-9,9,20);outer=np.column_stack([t,np.full(len(t),5.)]);inner=np.column_stack([t,np.full(len(t),-1.)])
    connections=[{'center':[-6,0,0],'normal':[0,0,1]},{'center':[6,0,0],'normal':[0,0,1]}]
    config={'trace_mode':'linear_bridge','bar_top_z':5.5,'connections':connections}
    trace,report=centered_trace(body,np.vstack([outer,inner[::-1]]),connections,config,1.5)
    assert max(r['center_offset_mm'] for r in report['connections'])<1e-8
    assert all(r['covered'] for r in report['connections'])
    old=trimesh.creation.box([20,6,5.5]);old.apply_translation([0,2,2.75])
    new=trimesh.creation.box([20,6,5.5]);new.apply_translation([0,0,2.75])
    assert primary_balance(old,config)['max_center_offset_mm']==pytest.approx(2)
    assert primary_balance(new,config)['max_center_offset_mm']==pytest.approx(0)
    assert connections[0]['center']==[-6,0,0]


def test_centering_measures_local_shoulders_not_opposite_arch_arm():
    np=pytest.importorskip('numpy');trimesh=pytest.importorskip('trimesh');mf=pytest.importorskip('manifold3d')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from bar_centering import primary_balance
    local=mf.Manifold.cube([6,6,5],True).translate([20,0,2.5])-mf.Manifold.cylinder(8,.8,.8,64).translate([20,0,-1])
    remote=mf.Manifold.cube([6,6,5],True).translate([-20,0,2.5])
    raw=(local+remote).to_mesh64();mesh=trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False)
    c={'trace_mode':'radial_arch','bar_top_z':5.,'connections':[{'center':[20,0,0],'normal':[0,0,1],
        'radius':.8,'functional_perimeter_radius_mm':1.2}]}
    result=primary_balance(mesh,c)
    assert result['all_bilateral'] and result['max_center_offset_mm']==pytest.approx(0,abs=1e-6)
    assert all(row['inner_space_mm']==pytest.approx(3) for row in result['samples'])


def test_tapered_connection_uses_protected_neck_at_measured_height():
    import trimesh,manifold3d as mf
    from bar_centering import primary_balance
    from connection_protection import protection
    c={'center':[0.,0.,0.],'normal':[0.,0.,1.],'radius':2.1,
       'functional_perimeter_radius_mm':2.5,'protection_radius_mm':2.75,
       'protection_bottom_mm':0.,'protection_top_mm':3.,
       'protection_envelope':[{'height_mm':0.,'radius_mm':2.75},
         {'height_mm':.4,'radius_mm':2.75},{'height_mm':.5,'radius_mm':1.},
         {'height_mm':3.,'radius_mm':1.}]}
    mask=protection(c);volume=mask.volume()
    bore=mf.Manifold.cylinder(5,.7,.7,64).translate([0,0,-1])
    cfg={'connections':[c],'trace_mode':'linear_bridge','bar_top_z':3.2}
    def mesh(solid):
        raw=solid.to_mesh64();return trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False)
    body=mf.Manifold.cube([6,3.6,3.2]).translate([-3,-1.8,0])
    result=primary_balance(mesh((mask+body)-bore),cfg)
    assert result['all_bilateral'] and result['max_center_offset_mm']==pytest.approx(0)
    assert all(row['support_reference']=='local_protected_envelope' for row in result['samples'])
    assert all(1.05<=row['required_inner_space_mm']<1.051 for row in result['samples'])
    assert not primary_balance(mesh(mask-bore),cfg)['all_bilateral']
    offset=primary_balance(mesh((mask+body.translate([0,.6,0]))-bore),cfg)
    assert offset['max_center_offset_mm']==pytest.approx(.6)
    assert mask.volume()==pytest.approx(volume)


def test_worker_does_not_run_blender_for_an_unchanged_redesign(client,monkeypatch):
    import json,shutil
    from test_revisions import make_case
    from dental_lab.worker import Worker
    c,app=client;s=app.state.settings;db=app.state.store
    case=make_case(c,'Misma geometría')
    previous=db.one("SELECT * FROM jobs WHERE kind='segment' AND target=?",(case,))
    db.update_job(previous['id'],'done')
    old=s.data/'runs'/previous['id'];old.mkdir(parents=True)
    profile={'bar_top_z':6.,'trace_xy':[[1,2],[2,3]]}
    (old/'perfil_ejecutado.json').write_text(json.dumps(profile))
    shutil.copytree(s.app/'engine/engine',old/'Codigo/engine')
    job_id=db.queue_segment(case);job=db.one('SELECT * FROM jobs WHERE id=?',(job_id,))
    s.geometry_python='test-only-python';calls=[]
    def prepare(command,**kwargs):
        calls.append(command)
        output=Path(command[command.index('--output')+1]);output.write_text(json.dumps(profile))
        output.with_suffix('.medidas.json').write_text(json.dumps({'corrections_pending':[{'text':'No interpretada'}]}))
    monkeypatch.setattr('dental_lab.worker.subprocess.run',prepare)
    with pytest.raises(RuntimeError,match='No se ha repetido una segmentación idéntica'):
        Worker(s,db,app.state.ingest).segment(job)
    assert len(calls)==1 and 'prepare_profile.py' in calls[0][1]
    assert (old/'perfil_ejecutado.json').is_file()
    assert db.one('SELECT status FROM cases WHERE id=?',(case,))['status']=='review_pending'
    response=c.get('/api/jobs/'+job_id+'/progress').json()
    assert response['redesign_comparison']['previous_job_id']==previous['id']
    assert not response['redesign_comparison']['geometry_parameters_changed']


def test_lateral_reserve_closes_an_unintended_supra_window():
    np=pytest.importorskip('numpy');mf=pytest.importorskip('manifold3d')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from occlusal_safety import separate_with_safety
    body=mf.Manifold.cube([10,10,10]).translate([-5,-5,0])-mf.Manifold.sphere(3,32).translate([5,0,6])
    inner=mf.Manifold.cube([6,6,8]).translate([-3,-3,-1])
    outer=mf.Manifold.cube([6.3,6.3,8.15]).translate([-3.15,-3.15,-1])
    assert (body-outer).genus()>body.genus()
    t=np.linspace(-2,2,12);a=np.column_stack([t,np.full(12,-1.5)]);b=np.column_stack([t,np.full(12,1.5)])
    config={'trace_xy':np.vstack([a,b[::-1]]).tolist(),'connections':[],'minimum_supra_mm':.8,'cement_gap_mm':.15,'prevent_extra_supra_openings':True}
    primary,supra,report=separate_with_safety(body,inner,outer,config)
    assert report['lateral_repairs'] and report['extra_openings_resolved']
    assert supra.genus()==body.genus()
    assert len(primary.decompose())==len(supra.decompose())==1
    assert abs((primary^supra).volume())<1e-8


def test_retention_rejects_a_perforating_groove_but_keeps_a_shallow_one():
    mf=pytest.importorskip('manifold3d')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from retention_safety import apply_safe_retention
    base=mf.Manifold.cube([10,10,5])
    perforation=mf.Manifold.cylinder(7,.5,.5,32).translate([2,2,-1])
    shallow=mf.Manifold.cube([1,1,1]).translate([7,7,4.5])
    result,removed,report=apply_safe_retention(base,perforation+shallow)
    assert result.genus()==base.genus() and len(result.decompose())==1
    assert len(report['rejected'])==len(report['accepted'])==1
    assert base.volume()-result.volume()==pytest.approx(.5)


def test_vertex_contacts_are_separated_and_survive_stl_in_original_coordinates():
    import io
    np=pytest.importorskip('numpy');trimesh=pytest.importorskip('trimesh')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from mesh_export import separate_vertex_contacts
    a=trimesh.creation.box();b=trimesh.creation.box();b.apply_translation([1,1,1])
    touching=trimesh.util.concatenate([a,b]);touching.merge_vertices()
    assert touching.is_watertight and touching.euler_number==3
    clean,report=separate_vertex_contacts(touching)
    clean.apply_translation([31,-27,51])
    reloaded=trimesh.load(io.BytesIO(clean.export(file_type='stl_ascii').encode()),file_type='stl')
    assert reloaded.is_watertight and reloaded.is_winding_consistent
    assert reloaded.euler_number==4 and len(reloaded.split())==2
    assert abs(clean.volume-touching.volume)<1e-5
    assert report['maximum_shift_mm']<=1e-6


@pytest.mark.parametrize('offset',[(1,1,1),(1,1,0)])
def test_indexed_contacts_survive_stl_without_simplifying_surfaces(offset):
    import io
    np=pytest.importorskip('numpy');trimesh=pytest.importorskip('trimesh')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from mesh_export import separate_export_contacts
    a=trimesh.creation.box();b=trimesh.creation.box();b.apply_translation(offset)
    touching=trimesh.util.concatenate([a,b]);original=touching.vertices.copy()
    transform=trimesh.transformations.rotation_matrix(.33,[0,0,1]);transform[:3,3]=[31,-27,51]
    clean,report=separate_export_contacts(touching,transform)
    assert report['maximum_shift_mm']<=1.000001e-6 and report['separated_vertices']>0
    assert np.array_equal(clean.faces,touching.faces)
    assert abs(clean.volume-touching.volume)<1e-5
    for matrix in (np.eye(4),transform):
        output=clean.copy();output.apply_transform(matrix)
        reloaded=trimesh.load(io.BytesIO(output.export(file_type='stl_ascii').encode()),file_type='stl')
        assert reloaded.is_watertight and reloaded.is_winding_consistent
        assert reloaded.euler_number==4 and len(reloaded.split())==2
    assert np.array_equal(touching.vertices,original)
