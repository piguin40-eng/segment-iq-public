import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).parents[1]/'engine'))
from lab_rules import observation_intents,effective_feedback,shape_rules
from dental_lab.revisions import compare_profiles


def test_each_annotated_shape_request_is_recognised_without_changing_height():
    text='Línea de terminación continua y sin picos. La parte superior de la barra reducir esa pirámide y por último hacer un visel en el final de labarra para que apoye el circonio. Por último labarra más fina.'
    intents,pending=observation_intents(text)
    assert intents=={'smooth_margin':True,'smooth_roof':True,'cervical_bevel':True,'slimmer_bar':True}
    assert not pending


@pytest.mark.parametrize('text',['No suavizar la terminación.','No reducir la pirámide.','No hacer un bisel en la barra.','Bisel de 2 mm en el final de barra.'])
def test_negation_and_unimplemented_explicit_dimensions_remain_pending(text):
    intents,pending=observation_intents(text)
    assert not intents and pending


def test_mirrored_general_and_case_note_is_applied_once_but_later_correction_is_not_discarded():
    first={'id':'general','case_id':'general','author':'Miguel','text':'Bajar barra 0.5 mm.','status':'correction','created':100}
    mirror=dict(first,id='case',case_id='A',text=first['text']+'\nEjecucion asociada: abc',created=100.5)
    later=dict(mirror,id='next',created=200)
    assert [r['id'] for r in effective_feedback({'feedback':[later,first,mirror]})]==['case','next']


def test_a_later_slimming_request_can_refine_again_without_doubling_its_general_mirror():
    a={'id':'g','case_id':'general','author':'Miguel','text':'La barra más fina.','status':'correction','created':100}
    b=dict(a,id='b',case_id='case',created=101)
    assert shape_rules({'feedback':[a,b]})['bar_narrowing_per_side_mm']==pytest.approx(.2)
    c=dict(b,id='c',created=200)
    assert shape_rules({'feedback':[a,b,c]})['bar_narrowing_per_side_mm']==pytest.approx(.4)


def test_new_shape_parameters_trigger_redesign_even_when_nominal_height_is_unchanged():
    old={'bar_top_z':5.5};new=dict(old,shape_refinement=shape_rules({'feedback':[{'id':'a','created':1,'status':'correction','text':'La barra más fina.'}]}))
    comparison=compare_profiles(old,new)
    assert comparison['geometry_parameters_changed'] and comparison['bar_top_change_mm']==0


def test_smoothed_roof_never_raises_existing_valleys():
    np=pytest.importorskip('numpy')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from shape_refinement import smooth_lower_height
    x=np.linspace(-3,3,61);xx,yy=np.meshgrid(x,x);roof=2+np.maximum(0,2-abs(xx)-abs(yy))
    smooth=smooth_lower_height(roof,.1,1.0)
    assert np.all(smooth<=roof+1e-10)
    assert smooth.max()<roof.max()-.8
    assert smooth.min()==pytest.approx(2.)


def test_roof_finish_does_not_propagate_cervical_ledge_into_tilted_roof():
    np=pytest.importorskip('numpy');trimesh=pytest.importorskip('trimesh');mf=pytest.importorskip('manifold3d')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from shape_refinement import rounded_roof
    from occlusal_safety import height_solid
    section=np.array([[-5.,0.],[5.,0.],[5.,7.],[-4.,3.4],[-4.,1.],[-5.,1.]])
    solid=mf.Manifold.extrude(mf.CrossSection([section]),6).rotate([90,0,0]).translate([0,3,0])
    raw=solid.to_mesh64();mesh=trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False)
    t=np.linspace(-5,5,30);a=np.c_[t,np.full(30,3.)];b=np.c_[t,np.full(30,-3.)]
    cfg={'trace_mode':'linear_bridge','trace_xy':np.vstack([a,b[::-1]]).tolist(),
         'bar_top_z':5.,'bar_plane':[.4,0.,5.],'connections':[{'center':[-4,0,0]},{'center':[4,0,0]}]}
    x,y,z,report=rounded_roof(mesh,cfg)
    nominal=5.+.4*x[None,:]
    assert np.allclose(z,nominal-.2,atol=.01)
    finished=solid^height_solid(x,y,z,-2.)
    assert (finished-solid).volume()==pytest.approx(0,abs=1e-8)
    assert report['maximum_roof_reduction_mm']<.25


def test_interimplant_pyramid_is_removed_between_measured_valleys():
    np=pytest.importorskip('numpy')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from shape_refinement import lower_convex_profile
    t=np.arange(7.);z=np.array([5.,3.,4.,5.,4.,3.,5.])
    result=lower_convex_profile(t,z)
    assert np.all(result<=z) and np.allclose(result[1:6],3.)
    assert result[0]==result[-1]==5.


def test_slimmer_trace_keeps_connection_axes_and_cervical_bevel_is_inward():
    np=pytest.importorskip('numpy')
    sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
    from shape_refinement import refine_trace,inset_contour
    from bar_centering import trace_balance
    t=np.linspace(-10,10,48);a=np.column_stack([t,np.full(len(t),3.)]);b=np.column_stack([t,np.full(len(t),-3.)])
    connections=[{'center':[x,0,0],'normal':[0,0,1],'radius':2.4,'functional_perimeter_radius_mm':2.6} for x in [-6,6]]
    config={'trace_mode':'linear_bridge','bar_top_z':5.5,'connections':connections,
        'shape_refinement':{'smooth_margin':True,'bar_narrowing_per_side_mm':.2,'cervical_bevel_mm':.2}}
    trace,report=refine_trace(np.vstack([a,b[::-1]]),connections,config)
    config['trace_xy']=trace.tolist()
    assert report['median_total_width_reduction_mm']>0
    assert all(r['center_offset_mm']<1e-10 and r['covered'] for r in trace_balance(config))
    inset=inset_contour(trace,config,.2)
    assert np.allclose(abs(trace[:,1])-abs(inset[:,1]),.2)
    assert np.allclose(trace[:,0],inset[:,0])
