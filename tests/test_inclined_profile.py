"""Inclined analytic anatomy must not masquerade as extra anterior metal."""
import copy
import sys
from pathlib import Path
import pytest
np=pytest.importorskip('numpy')
pytest.importorskip('trimesh')
sys.path.insert(0,str(Path(__file__).parents[1]/'engine'))
from prepare_profile import propose_bar_height,supported_trace
from lab_rules import requested_rules
from bar_height import top_height
from bar_centering import axis_at_bar_top
from trace_support import fit_trace_plane,TraceSupportError


def fixture(slope=(0.,0.),thickness=8.):
    y=np.linspace(-25,10,48)
    xy=np.vstack([np.column_stack([np.full(48,x),y]) for x in (-5.,5.)])
    bottom=xy@np.array(slope)
    connections=[{'center':[x,y,x*slope[0]+y*slope[1]],'normal':[0.,0.,1.]}
                 for x in (-5.,5.) for y in (-20.,5.)]
    rules=requested_rules({'feedback':[{'id':'anterior','created':1,'status':'correction',
        'text':'La inserción debe tener más altura en anterior que en posterior. Grosor mínimo de supra 0.8 mm.'}]})
    return xy,bottom,bottom+thickness,connections,rules


def test_inclined_case_uses_measured_plane_without_raising_the_three_mm_limit():
    xy,bottom,tops,connections,rules=fixture((.12,-.4))
    original=copy.deepcopy(connections)
    top,increase,bounds,plane,report=propose_bar_height(xy,bottom,tops,connections,rules,-.5,False)
    assert report['horizontal_anterior_raise_mm']>3
    assert report['method']=='measured_cervical_plane'
    assert plane[:2]==pytest.approx([.12,-.4])
    assert increase==pytest.approx(1.)
    cfg={'bar_top_z':top,'bar_plane':plane,'anterior_raise_mm':increase,'bar_y_bounds':bounds}
    heights=top_height(xy,cfg)
    assert np.min(heights-bottom)>=1.2
    assert np.min(tops-heights)>=1.5
    assert connections==original
    assert np.ptp(heights-bottom)<=1.000001


def test_horizontal_legacy_profile_is_unchanged_and_height_delta_remains_authoritative():
    xy,bottom,tops,connections,rules=fixture()
    top,increase,bounds,plane,report=propose_bar_height(xy,bottom,tops,connections,rules,0,False)
    assert report['method']=='horizontal' and plane[:2]==[0.,0.]
    assert top==pytest.approx(4.8) and increase==pytest.approx(1.)
    cfg={'bar_top_z':top,'bar_plane':plane,'anterior_raise_mm':increase,'bar_y_bounds':bounds}
    before=top_height(xy,cfg)
    cfg['bar_top_z']-=.5
    assert np.allclose(top_height(xy,cfg),before-.5)


def test_thin_inclined_case_is_still_rejected_instead_of_bypassing_clearance():
    xy,bottom,tops,connections,rules=fixture((.12,-.4),2.)
    with pytest.raises(ValueError,match='espacio entre asientos'):
        propose_bar_height(xy,bottom,tops,connections,rules,0,False)


def test_plane_recovery_also_works_without_an_anterior_correction():
    xy,bottom,tops,connections,_=fixture((.12,-.4))
    result=propose_bar_height(xy,bottom,tops,connections,requested_rules({}),0,False)
    assert result[1]==0 and result[-1]['method']=='measured_cervical_plane'


def test_inclined_axis_meets_the_actual_plane_and_regional_field():
    connection={'center':[5.,-20.,2.],'normal':[.12,.2,.97241967]}
    original=copy.deepcopy(connection)
    config={'bar_top_z':4.,'bar_plane':[.12,-.4,4.],'anterior_raise_mm':1.2,'bar_y_bounds':[-25.,10.]}
    point=axis_at_bar_top(connection,config)
    assert point[2]==pytest.approx(float(top_height(point[:2],config)),abs=1e-7)
    assert np.linalg.norm(np.cross(point-connection['center'],connection['normal']))<1e-7
    assert connection==original


def test_refined_border_inside_a_chimney_is_reprojected_onto_continuous_material():
    mf=pytest.importorskip('manifold3d');import trimesh
    body=mf.Manifold.cube([20,12,10]).translate([-10,-6,0])
    body=body-mf.Manifold.cylinder(12,2,2,64).translate([0,0,-1])
    data=body.to_mesh64();mesh=trimesh.Trimesh(data.vert_properties[:,:3],data.tri_verts,process=False)
    x=np.linspace(-9,9,11);outer=np.c_[x,np.full(11,3.)];inner=np.c_[x,np.full(11,-3.)]
    trace=np.vstack([outer,inner[::-1]]);trace[5,1]=0
    cfg={'trace_mode':'linear_bridge','bar_top_z':5,'bar_plane':[0,0,5]}
    result,bottom,top,report=supported_trace(mesh,trace,cfg,1.5,lambda t:np.array([-6.,6.]))
    assert len(report['adjustments'])==1 and report['all_supported']
    assert abs(result[5,1])>2
    assert np.allclose(bottom,0) and np.allclose(top,10)
    assert np.array_equal(result[:,0],trace[:,0])


def test_corridor_plane_recovers_continuous_material_without_changing_source_or_reserves():
    import trimesh
    mesh=trimesh.creation.box([20,12,3.2]);mesh.apply_translation([0,0,1.6])
    mesh.vertices[:,2]+=.15*mesh.vertices[:,0]
    original=mesh.vertices.copy()
    x=np.linspace(-9,9,12);trace=np.vstack([np.c_[x,np.full(12,3.)],np.c_[x,np.full(12,-3.)][::-1]])
    connections=[{'center':[x,0,.15*x],'normal':[0,0,1]} for x in (-6,6)]
    cfg={'trace_mode':'linear_bridge','bar_top_z':1.5,'bar_plane':[0,0,1.5]}
    updated,borders,report=fit_trace_plane(mesh,trace,connections,cfg,1.5,lambda t:np.array([-6.,6.]))
    result,bottom,top,support=supported_trace(mesh,borders,updated,1.5,lambda t:np.array([-6.,6.]))
    heights=top_height(result,updated)
    assert support['all_supported'] and len(result)==len(trace)
    assert np.min(heights-bottom)>1.2 and np.min(top-heights)>1.5
    assert np.array_equal(mesh.vertices,original) and cfg['bar_plane']==[0,0,1.5]
    assert not report['constraints_relaxed'] and not report['source_geometry_changed']


def test_corridor_plane_does_not_bridge_a_void_or_reduce_required_thickness():
    import trimesh
    low=trimesh.creation.box([20,12,1.]);high=low.copy();high.apply_translation([0,0,8])
    mesh=trimesh.util.concatenate([low,high])
    x=np.linspace(-9,9,12);trace=np.vstack([np.c_[x,np.full(12,3.)],np.c_[x,np.full(12,-3.)][::-1]])
    cfg={'trace_mode':'linear_bridge','bar_top_z':4.,'bar_plane':[0,0,4.]}
    with pytest.raises(TraceSupportError,match='sin espesor continuo'):
        fit_trace_plane(mesh,trace,[{'center':[0,0,0]}],cfg,1.5,lambda t:np.array([-6.,6.]))
