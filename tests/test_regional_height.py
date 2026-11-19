import sys
from pathlib import Path
import pytest
np=pytest.importorskip('numpy')
trimesh=pytest.importorskip('trimesh')
sys.path.insert(0,str(Path(__file__).parents[1]/'engine'))
from lab_rules import requested_rules
sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
from bar_height import top_height
from design_checks import design_checks
from design_checks import vertical_hits
from design_checks import first_material_exit
from occlusal_safety import separate_with_safety,mesh_of
mf=pytest.importorskip('manifold3d')

def test_mixed_height_and_minimum_instruction_keeps_independent_constraints():
    history={'feedback':[{'id':'a','created':1,'status':'rejected','text':'La inserción debe tener más altura en anterior que en posterior. La supra debe tener siempre grosor mínimo de 0.8 mm.'}]}
    rules=requested_rules(history)
    assert rules['anterior_feedback_ids']==['a']
    assert rules['minimum_feedback_ids']==['a'] and rules['minimum_supra_mm']==.8
    history['feedback'].append({'id':'b','created':2,'status':'correction','text':'Aumentar altura anterior 0,5 mm.'})
    assert requested_rules(history)['anterior_delta_mm']==.5
    assert requested_rules(history)['minimum_supra_mm']==.8


def test_latest_uniform_height_replaces_old_anterior_goal_but_preserves_supra_minimum():
    history={'feedback':[{'id':'old','created':1,'status':'correction',
        'text':'Más altura anterior 0,5 mm. Espesor mínimo de supra 0,8 mm.'},
        {'id':'new','created':2,'status':'correction','text':'La barra a la misma altura según lo posible, homogénea.'}]}
    rules=requested_rules(history)
    assert rules['height_goal']=='homogeneous' and rules['height_goal_feedback_id']=='new'
    assert rules['anterior_feedback_ids']==[] and rules['anterior_delta_mm']==0
    assert rules['minimum_supra_mm']==.8 and rules['minimum_feedback_ids']==['old']
    history['feedback'].append({'id':'later','created':3,'status':'correction','text':'Aumentar altura anterior 0,7 mm.'})
    rules=requested_rules(history)
    assert rules['height_goal']=='anterior_higher' and rules['anterior_delta_mm']==.7
    assert rules['anterior_feedback_ids']==['later']
    history['feedback'][-1]['text']='Más altura en anterior.'
    assert requested_rules(history)['anterior_delta_mm']==1.


def test_negated_uniform_height_does_not_cancel_anterior_goal():
    history={'feedback':[{'id':'old','created':1,'status':'correction','text':'Más altura anterior 0,5 mm.'},
        {'id':'new','created':2,'status':'correction','text':'No quiero la misma altura en toda la barra.'}]}
    assert requested_rules(history)['height_goal']=='anterior_higher'


def test_uniform_height_gate_does_not_require_anterior_taller_or_ignore_thin_supra(tmp_path):
    import json
    from ejecutar import gate
    shape={'watertight':True,'winding_consistent':True,'components':1,'volume_mm3':1.,'genus':0}
    section={'sample_count':12,'anterior_higher_pass':False,'occlusal_target_pass':True}
    report={'meshes':{'primaria':dict(shape),'supra':dict(shape)},'overlap_mm3':0.,
        'connection_rings':[],'design_sections':section,'functional_connection_protection':[]}
    exported={'closed':True,'consistent_winding':True,'volume_mm3':1.,'euler':2}
    (tmp_path/'Validacion_PROPIA.json').write_text(json.dumps(report))
    (tmp_path/'Comprobacion_STL.json').write_text(json.dumps({'Primaria_SUP_PROPIA.stl':exported,'Supra_SUP_PROPIA.stl':exported}))
    config={'arch':'SUP','expected_euler':2,'expected_connections':0,'max_overlap_mm3':.0001,
        'max_connection_error_mm':.001,'anterior_raise_mm':1.25,'minimum_supra_mm':.8,'connections':[]}
    with pytest.raises(RuntimeError,match='altura anterior'):gate(tmp_path,config)
    config['require_anterior_higher']=False
    assert gate(tmp_path,config)['geometry_checks']=='PASS'
    section['occlusal_target_pass']=False
    (tmp_path/'Validacion_PROPIA.json').write_text(json.dumps(report))
    with pytest.raises(RuntimeError,match='espesor oclusal'):gate(tmp_path,config)

def test_smooth_anterior_field_does_not_raise_posterior_or_use_other_case_coordinates():
    config={'bar_top_z':7,'anterior_raise_mm':1.5,'bar_y_bounds':[-25,5]}
    values=top_height(np.array([[0,-25],[0,-10],[0,5],[30,5]]),config)
    assert values==pytest.approx([8.5,7.75,7,7])

def test_sections_detect_thin_occlusal_material_even_when_both_meshes_are_closed():
    source=trimesh.creation.box([10,10,10]);source.apply_translation([0,0,5])
    primary=trimesh.creation.box([8,8,9.5]);primary.apply_translation([0,0,4.75])
    supra=trimesh.creation.box([10,10,.35]);supra.apply_translation([0,0,9.825])
    y=np.linspace(-3,3,12);left=np.column_stack((np.full(12,-2),y));right=np.column_stack((np.full(12,2),y))
    config={'trace_xy':np.concatenate([left,right[::-1]]).tolist(),'minimum_supra_mm':.8}
    result=design_checks(source,primary,supra,config)
    assert source.is_watertight and supra.is_watertight
    assert result['sample_count']==36
    assert result['minimum_sampled_occlusal_mm']==pytest.approx(.35)
    assert not result['occlusal_target_pass'] and not result['global_minimum_verified']

def test_local_safety_fixes_thin_interval_without_lowering_entire_bar():
    body=mf.Manifold.cube([10,10,10]).translate([-5,-5,0])
    # An intermediate void makes min/max Z falsely suggest plenty of thickness.
    void=mf.Manifold.cube([2,2,.35]).translate([-1,-1,6.15]);body=body-void
    inner=mf.Manifold.cube([14,14,8.98]).translate([-7,-7,-3])
    outer=mf.Manifold.cube([14,14,9.13]).translate([-7,-7,-3])
    y=np.linspace(-4,4,17);left=np.column_stack([np.full(17,-3),y]);right=np.column_stack([np.full(17,3),y])
    config={'trace_xy':np.concatenate([left,right[::-1]]).tolist(),'minimum_supra_mm':.8,'cement_gap_mm':.15,'connections':[]}
    primary,supra,report=separate_with_safety(body,inner,outer,config)
    assert report['attempts'][0]['minimum_sampled_mm']<.03
    assert report['attempts'][-1]['minimum_sampled_mm']>=.8
    assert report['attempts'][0]['sample_count']==report['attempts'][-1]['sample_count']
    assert not report.get('unresolved')
    assert (primary^supra).volume()<1e-8
    assert mesh_of(primary).is_watertight and mesh_of(supra).is_watertight
    # The remote edge retains its original top; the correction is local.
    points=mesh_of(primary).ray.intersects_location([[4,4,-4]],[[0,0,1]],multiple_hits=True)[0]
    assert points[:,2].max()==pytest.approx(5.98)


def test_a_thin_original_wall_across_a_void_is_not_a_new_occlusal_separator():
    low=mf.Manifold.cube([10,10,3]);high=mf.Manifold.cube([10,10,.5]).translate([0,0,7])
    # Join outside the sampled corridor, like a wall on the far side of a channel.
    side=mf.Manifold.cube([1,10,7.5]).translate([9,0,0])
    source=mesh_of(low+high+side);primary=mesh_of(low);supra=mesh_of(high+side)
    y=np.linspace(1,9,12);left=np.c_[np.full(12,2),y];right=np.c_[np.full(12,6),y]
    result=design_checks(source,primary,supra,{'trace_xy':np.vstack([left,right[::-1]]).tolist(),'minimum_supra_mm':.8})
    assert result['sample_count']==0
    assert len(result['unpaired_source_sections'])==36
    assert not result.get('occlusal_target_pass',False)
    assert not result['global_minimum_verified']


def test_rays_missing_every_mesh_return_empty_measurements():
    mesh=trimesh.creation.box([1,1,1])
    hits=vertical_hits(mesh,np.array([[5.,5.],[10.,10.]]),-3)
    assert len(hits)==2 and all(len(row)==0 for row in hits)


def test_inclined_chimney_short_vertical_chord_is_checked_in_separator_normal():
    body=mf.Manifold.cube([10,10,10]).translate([-5,-5,0])-mf.Manifold.cylinder(12,1.35,1.35,192).translate([0,0,-1])
    primary=body^mf.Manifold.cube([12,12,4.5]).translate([-6,-6,-1])
    supra=body-mf.Manifold.cube([12,12,4.65]).translate([-6,-6,-1])
    angle=np.deg2rad(12);rotation=trimesh.transformations.rotation_matrix(angle,[0,1,0])
    source,p,s=[mesh_of(m) for m in (body,primary,supra)]
    for m in (source,p,s):m.apply_transform(rotation)
    y=np.linspace(-.04,.04,12)
    left=np.c_[np.full(12,1.39*np.cos(angle)+3.5*np.sin(angle)),y]
    right=np.c_[np.full(12,1.49*np.cos(angle)+3.5*np.sin(angle)),y]
    config={'trace_xy':np.vstack([left,right[::-1]]).tolist(),'minimum_supra_mm':.8}
    result=design_checks(source,p,s,config)
    assert result['sample_count']==36
    assert min(row['vertical_chord_mm'] for row in result['samples'])<.8
    assert result['minimum_sampled_occlusal_mm']==pytest.approx(6.35)
    assert result['occlusal_target_pass'] and not result['global_minimum_verified']


def test_new_separating_surface_without_supra_is_not_silently_excluded():
    source=trimesh.creation.box([10,10,10]);source.apply_translation([0,0,5])
    primary=trimesh.creation.box([10,10,5]);primary.apply_translation([0,0,2.5])
    supra=trimesh.creation.box([1,1,1]);supra.apply_translation([20,20,20])
    y=np.linspace(-3,3,12);left=np.c_[np.full(12,-2),y];right=np.c_[np.full(12,2),y]
    result=design_checks(source,primary,supra,{'trace_xy':np.vstack([left,right[::-1]]).tolist(),'minimum_supra_mm':.8})
    assert result['sample_count']==36 and result['minimum_sampled_occlusal_mm']==0
    assert not result['occlusal_target_pass']


@pytest.mark.parametrize('wall,passes',[(3.8,True),(.4,False)])
def test_retention_normal_does_not_replace_actual_cavity_thickness(wall,passes):
    # The sloped metal groove points toward the source's side edge, whereas
    # the opposing cavity is horizontal. Its own normal has a known thickness.
    source=mesh_of(mf.Manifold.cube([10,10,2.2+wall]).translate([-5,-5,0]))
    section=np.array([[-5.,0.],[5.,0.],[5.,.5],[3.5,2.],[-5.,2.]])
    primary=mesh_of(mf.Manifold.extrude(mf.CrossSection([section]),10).rotate([90,0,0]).translate([0,5,0]))
    supra=mesh_of(mf.Manifold.cube([10,10,wall]).translate([-5,-5,2.2]))
    y=np.linspace(-3,3,12);left=np.c_[np.full(12,3.99),y];right=np.c_[np.full(12,4.01),y]
    config={'trace_xy':np.vstack([left,right[::-1]]).tolist(),'minimum_supra_mm':.8}
    result=design_checks(source,primary,supra,config)
    assert result['sample_count']==36
    assert result['minimum_sampled_occlusal_mm']==pytest.approx(wall)
    assert result['occlusal_target_pass']==passes
    assert result['measurement_method']=='supra_cavity_normal'
    assert max(row['primary_normal_chord_mm'] for row in result['samples'])<.8
    assert all(np.allclose(row['measurement_direction'],[0,0,1]) for row in result['samples'])
    assert not result['global_minimum_verified']


@pytest.mark.parametrize('wall,passes',[(3.8,True),(.4,False)])
def test_overlapping_original_surfaces_do_not_create_a_false_zero_wall(wall,passes):
    def box(bottom,top,width=10):
        m=trimesh.creation.box([width,width,top-bottom])
        m.apply_translation([0,0,(bottom+top)/2]);return m
    # A closed oriented internal shell produces crossings 1 -> 2 -> 1 -> 0,
    # as found in the supplied STL. The first internal face is not an exit.
    internal=box(2.2+wall*.2,2.2+wall*.6,8)
    source=trimesh.util.concatenate([box(0,2.2+wall),internal])
    supra=trimesh.util.concatenate([box(2.2,2.2+wall),internal])
    primary=box(0,2.,8)
    before=source.vertices.copy()
    y=np.linspace(-2,2,9);left=np.c_[np.full(9,-2),y];right=np.c_[np.full(9,2),y]
    result=design_checks(source,primary,supra,{'trace_xy':np.vstack([left,right[::-1]]).tolist(),'minimum_supra_mm':.8})
    assert result['sample_count']==27
    assert result['minimum_sampled_occlusal_mm']==pytest.approx(wall)
    assert result['occlusal_target_pass']==passes
    assert all(r['source_internal_crossings_before_exit']==2 for r in result['samples'])
    assert np.array_equal(source.vertices,before) and not result['global_minimum_verified']


def test_oriented_ray_exit_stops_before_a_void_and_rejects_outside_or_tangent_rays():
    # Inside material, overlapping faces, then a true gap and another shell.
    distances=np.array([1.,1.1,1.2,3.,4.])
    assert first_material_exit(distances,[-1,1,1,-1,1])==2
    assert first_material_exit([1.,2.],[-1,1]) is None
    assert first_material_exit([1.,2.],[0,1]) is None
    assert first_material_exit([3.,1.,2.],[1,-1,1])==0


def test_safety_cut_cannot_disconnect_a_bridge_to_satisfy_thickness():
    body=(mf.Manifold.cube([2,4,6]).translate([-4,-2,0])+
          mf.Manifold.cube([2,4,6]).translate([2,-2,0])+
          mf.Manifold.cube([4,1,1]).translate([-2,-.5,5]))
    inner=mf.Manifold.cube([12,8,6.5]).translate([-6,-4,-1])
    outer=mf.Manifold.cube([12,8,6.65]).translate([-6,-4,-1])
    x=np.linspace(-3.5,3.5,65);left=np.c_[x,np.full(65,.4)];right=np.c_[x,np.full(65,-.4)]
    cfg={'trace_xy':np.vstack([left,right[::-1]]).tolist(),'connections':[],
         'minimum_supra_mm':.8,'cement_gap_mm':.15}
    initial=body^inner
    primary,supra,report=separate_with_safety(body,inner,outer,cfg)
    assert len(initial.decompose())==1 and len(primary.decompose())==1
    assert primary.volume()==pytest.approx(initial.volume())
    assert report['unresolved'] and any(not row['accepted'] for row in report['continuity_guard'])
    assert not design_checks(mesh_of(body),mesh_of(primary),mesh_of(supra),cfg)['occlusal_target_pass']
