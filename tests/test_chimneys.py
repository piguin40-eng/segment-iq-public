"""Analytic fixtures contain no laboratory/patient meshes."""
import sys
import json
from pathlib import Path
import pytest
np=pytest.importorskip('numpy')
trimesh=pytest.importorskip('trimesh')
mf=pytest.importorskip('manifold3d')
sys.path.insert(0,str(Path(__file__).parents[1]/'engine'))
from prepare_profile import circular_edges,prepare,corrections,orientation
from connections import group_chimneys
sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
from connection_protection import protection, connection_checks, chimney_axis_check


def bridge(socket_segments=96, centers=(-8,8), solid=False):
    body=mf.Manifold.cube([28,10,10]).translate([-14,-5,0])
    if not solid:
        for x in centers:
            # Wide basal socket (round or hex) and narrow through-chimney.
            cavity=mf.Manifold.cylinder(3.1,2.2,2.2,socket_segments).translate([x,0,-.1])
            cavity=cavity+mf.Manifold.cylinder(11,1.1,1.1,96).translate([x,0,-.1])
            body=body-cavity
    data=body.to_mesh64()
    return trimesh.Trimesh(data.vert_properties[:,:3],data.tri_verts,process=True)


@pytest.mark.parametrize('sides',[96,6])
def test_short_bridge_chimneys_and_entire_socket_perimeter(sides,tmp_path):
    mesh=bridge(sides)
    connections,_=group_chimneys(mesh,circular_edges(mesh))
    assert len(connections)==2
    for c in connections:
        assert min(c['wall_coverage'])>.95
        assert c['protection_radius_mm']>2.2
        assert c['protection_bottom_mm']<0
        assert c['protection_top_mm']>=3
        assert c['chimney_radius_mm']==pytest.approx(1.1,abs=1e-5)
        assert len(c['measured_features'])>=3
        # The protective tool contains all angles of the socket, including hex corners.
        axis=np.asarray(c['normal']);center=np.asarray(c['center'])
        angles=np.linspace(0,2*np.pi,360,endpoint=False)
        points=center+np.column_stack([2.2*np.cos(angles),2.2*np.sin(angles),np.full(360,1.5)])
        p=protection(c).to_mesh64();tool=trimesh.Trimesh(p.vert_properties[:,:3],p.tri_verts,process=False)
        assert tool.contains(points).all()
    src=tmp_path/'bridge.stl';mesh.export(src,file_type='stl_ascii')
    profile,report=prepare(src,'24-25-26',{})
    assert profile['expected_connections']==2 and profile['trace_mode']=='linear_bridge'
    assert profile['arch']=='SUP'
    assert np.linalg.det(np.asarray(profile['raw_to_work'])[:3,:3])==pytest.approx(1)


def test_rigid_transform_preserves_measured_chimney_and_envelope():
    mesh=bridge(6)
    before,_=group_chimneys(mesh,circular_edges(mesh))
    transform=trimesh.transformations.rotation_matrix(.53,[.7,.3,.1]);transform[:3,3]=[31,-27,51]
    mesh.apply_transform(transform)
    after,_=group_chimneys(mesh,circular_edges(mesh))
    assert len(after)==2
    for c in before:
        center=transform[:3,:3]@c['center']+transform[:3,3]
        match=min(after,key=lambda r:np.linalg.norm(np.asarray(r['center'])-center))
        assert np.linalg.norm(np.asarray(match['center'])-center)<1e-5
        assert match['protection_radius_mm']==pytest.approx(c['protection_radius_mm'],abs=1e-5)


def test_three_collinear_implants_produce_serializable_profile_and_measurements(tmp_path):
    mesh=bridge(centers=(-8,0,8))
    path=tmp_path/'bridge-three.stl';mesh.export(path)
    profile,report=prepare(path,'37-36-35-34',{})
    assert profile['trace_mode']=='linear_bridge' and profile['expected_connections']==3
    assert type(profile['center_connections']) is bool and profile['center_connections']
    # Exercise the exact boundary that prevented the worker from starting.
    assert json.loads(json.dumps(profile,allow_nan=False))['center_connections'] is True
    assert json.loads(json.dumps(report,allow_nan=False))['design_constraints']['center_connections'] is True


def test_isolated_circles_do_not_reverse_verified_chimney_polarity():
    mesh=bridge()
    rings=circular_edges(mesh)
    baseline,_=group_chimneys(mesh,rings)
    # Separate single circular features cannot identify a channel or decide
    # which end of the verified channels is the basal connection.
    distractors=[{'center':[x,20.,30.],'normal':[0,0,1],
                  'radius':1.5,'vertices':96} for x in range(-20,21,4)]
    measured,_=group_chimneys(mesh,rings+distractors)
    assert len(measured)==len(baseline)==2
    for original in baseline:
        match=min(measured,key=lambda c:np.linalg.norm(np.array(c['center'])-original['center']))
        assert match['center']==pytest.approx(original['center'])
        assert match['normal']==pytest.approx(original['normal'])
        assert match['protection_top_mm']==pytest.approx(original['protection_top_mm'])


def test_full_arch_orientation_preserves_signed_connection_features():
    # Crown centroid lies below the measured bases, as can occur with an
    # inclined arch. Reorientation must remain a rigid change of coordinates.
    mesh=trimesh.creation.box([40,30,10])
    seats=[{'center':[x,y,12.], 'normal':[0.,0.,1.],
            'protection_bottom_mm':-.2,'protection_top_mm':3.,
            'measured_features':[{'height_mm':0.,'radius_mm':2.2},
                                 {'height_mm':3.,'radius_mm':1.1}]}
           for x,y in [(-15,5),(-8,-12),(8,-12),(15,5)]]
    transform,measured=orientation(mesh,seats)
    assert np.linalg.det(transform[:3,:3])==pytest.approx(1)
    for c in seats:
        base=transform[:3,:3]@c['center']+transform[:3,3]
        match=min(measured,key=lambda row:np.linalg.norm(np.array(row['center'])-base))
        assert match['center']==pytest.approx(base)
        assert match['normal']==pytest.approx(transform[:3,:3]@c['normal'])
        assert match['normal'][2]>0
        for feature in c['measured_features']:
            height=feature['height_mm']
            expected=transform[:3,:3]@(np.array(c['center'])+height*np.array(c['normal']))+transform[:3,3]
            assert np.array(match['center'])+height*np.array(match['normal'])==pytest.approx(expected)


def test_solid_boss_is_not_accepted_as_an_open_chimney():
    mesh=bridge(solid=True)
    candidates=[dict(center=[0,0,z],normal=[0,0,1],radius=r,vertices=96) for z,r in [(0,2.2),(3,1.1)]]
    with pytest.raises(ValueError,match='chimenea abierta'):
        group_chimneys(mesh,candidates)


def test_remote_material_beyond_an_open_channel_does_not_hide_connections():
    mesh=bridge()
    # A distant part of the anatomy intersects the infinite axial ray but
    # leaves both measured channels and their exits completely open.
    roof=trimesh.creation.box([28,10,1]);roof.apply_translation([0,0,20])
    combined=trimesh.util.concatenate([mesh,roof])
    baseline,_=group_chimneys(mesh,circular_edges(mesh))
    measured,_=group_chimneys(combined,circular_edges(mesh))
    assert len(baseline)==len(measured)==2
    for original in baseline:
        match=min(measured,key=lambda c:np.linalg.norm(np.array(c['center'])-original['center']))
        assert match['center']==pytest.approx(original['center'])
        assert match['normal']==pytest.approx(original['normal'])
        assert min(match['wall_coverage'])>.95


def test_material_inside_the_measured_channel_still_rejects_it():
    mesh=bridge()
    blockers=[trimesh.creation.box([2,2,.2]) for _ in range(2)]
    for x,block in zip((-8,8),blockers):block.apply_translation([x,0,5])
    blocked=trimesh.util.concatenate([mesh]+blockers)
    with pytest.raises(ValueError,match='chimenea abierta'):
        group_chimneys(blocked,circular_edges(mesh))


def test_axis_validator_distinguishes_remote_original_anatomy_from_added_caps():
    mesh=bridge();connections,_=group_chimneys(mesh,circular_edges(mesh));c=connections[0]
    roof=trimesh.creation.box([28,10,1]);roof.apply_translation([0,0,20])
    source=trimesh.util.concatenate([mesh,roof])
    clean=chimney_axis_check(source,(source,),c)
    assert clean['chimney_axis_material_hits']==0
    assert len(clean['unchanged_remote_anatomy_hits_mm'])==2
    assert not clean['source_axis_interpretation_ambiguous']
    for z in (5,15):
        # Both a cap inside the measured channel and new material beyond its
        # opening remain failures; only unchanged remote source is classified.
        cap=trimesh.creation.box([1,1,.2]);cap.apply_translation([*c['center'][:2],z])
        blocked=trimesh.util.concatenate([source,cap])
        result=chimney_axis_check(source,(blocked,),c)
        assert result['chimney_axis_material_hits']==2
        key='local_axis_material_hits_mm' if z==5 else 'new_remote_axis_hits_mm'
        assert len(result[key])==2


def test_axis_validator_keeps_legacy_full_axis_without_measured_channel():
    mesh=bridge();connections,_=group_chimneys(mesh,circular_edges(mesh));c=dict(connections[0])
    c.pop('chimney_axial_span_mm')
    roof=trimesh.creation.box([28,10,1]);roof.apply_translation([0,0,20])
    source=trimesh.util.concatenate([mesh,roof])
    assert chimney_axis_check(source,(source,),c)['chimney_axis_material_hits']==2


def test_connection_above_arch_centroid_keeps_its_true_basal_end():
    left=mf.Manifold.cube([12,10,8]).translate([-15,-5,0])
    right=mf.Manifold.cube([12,12,8]).translate([3,-6,12])
    body=left+right+mf.Manifold.cube([10,3,12]).translate([-5,-1.5,4])
    for x,z in [(-9,0),(9,12)]:
        socket=mf.Manifold.cylinder(z+4,2.2,2.2,96).translate([x,0,-1])
        channel=mf.Manifold.cylinder(40,1.1,1.1,96).translate([x,0,-1])
        body=body-socket-channel
    d=body.to_mesh64();mesh=trimesh.Trimesh(d.vert_properties[:,:3],d.tri_verts,process=True)
    # Explicit analytic rings isolate axis polarity from tessellation details.
    candidates=[{'center':[x,0,h],'normal':[0,0,1],'radius':r,'vertices':96}
                for x,z in [(-9,0),(9,12)] for h,r in [(z,2.2),(z+3,2.2),(z+3,1.1),(z+8,1.1)]]
    connections,_=group_chimneys(mesh,candidates)
    assert len(connections)==2
    high=max(connections,key=lambda c:c['center'][2])
    assert mesh.centroid[2]<12
    assert high['center']==pytest.approx([9,0,12])
    assert high['normal'][2]>.99
    assert high['protection_bottom_mm']>-.21


def test_protection_includes_a_measured_upper_annular_step_not_only_first_neck():
    body=mf.Manifold.cube([12,10,10]).translate([-6,-5,0])
    body=body-mf.Manifold.cylinder(3.1,2.2,2.2,96).translate([0,0,-.1])
    body=body-mf.Manifold.cylinder(11,1.1,1.1,96).translate([0,0,-.1])
    body=body-mf.Manifold.cylinder(7,1.5,1.5,96).translate([0,0,4.2])
    d=body.to_mesh64();mesh=trimesh.Trimesh(d.vert_properties[:,:3],d.tri_verts,process=True)
    connections,_=group_chimneys(mesh,circular_edges(mesh))
    c=connections[0]
    assert c['measured_neck_mm']==pytest.approx(3)
    assert c['protection_top_mm']==pytest.approx(4.35)
    assert max(c['measured_annular_shoulders_mm'])==pytest.approx(4.2)
    radii=np.asarray([r['radius_mm'] for r in c['protection_envelope']])
    assert np.all(np.diff(radii)<=0)
    assert c['protection_top_mm']<mesh.bounds[1,2]
    solid=protection(c);tool=solid.to_mesh64()
    mask=trimesh.Trimesh(tool.vert_properties[:,:3],tool.tri_verts,process=False)
    assert mask.contains([[1.48,0,4.2]])[0]


def test_perimeter_check_detects_damage_away_from_basal_ring():
    source=bridge(6);connections,_=group_chimneys(source,circular_edges(source))
    solid=mf.Manifold(mf.Mesh64(np.float64(source.vertices),np.uint64(source.faces)))
    notch=mf.Manifold.cube([.4,.4,1]).translate([10.1,-.2,1])
    data=(solid-notch).to_mesh64()
    damaged=trimesh.Trimesh(data.vert_properties[:,:3],data.tri_verts,process=False)
    checks=connection_checks(source,damaged,source,connections)
    assert max(c['missing_volume_mm3'] for c in checks)>.01
    assert all(c['chimney_axis_material_hits']==0 for c in checks)


def test_lab_perimeter_instruction_does_not_claim_unimplemented_height_changes():
    history={'feedback':[
        {'id':'protection','created':1,'status':'correction','text':'Detecta la chimenea y protege todo el perímetro de la interfase o conexión directa'},
        {'id':'regional','created':2,'status':'rejected','text':'Más altura anterior y grosor mínimo de supra 0.8 mm'}]}
    height,width,applied,pending=corrections(history)
    assert (height,width)==(0,0)
    assert [r['id'] for r in applied]==['protection']
    assert [r['id'] for r in pending]==['regional']
