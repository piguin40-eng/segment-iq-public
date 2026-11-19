import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine/engine'))
from retention_mesh import decimation_ratio,triangle_arrays


def test_small_safe_surface_is_not_reduced_to_two_faces():
    assert int(195*decimation_ratio(195))>=32
    assert decimation_ratio(12)==1
    assert decimation_ratio(10000)==.015
    with pytest.raises(ValueError,match='superficie segura'):decimation_ratio(0)


def test_empty_legacy_tool_remains_empty_and_obeys_required_retention_policy():
    import manifold3d as mf
    from retention_safety import apply_retention_policy
    vertices,faces=triangle_arrays(np.array([]),np.array([]))
    assert vertices.shape==faces.shape==(0,3)
    tool=mf.Manifold(mf.Mesh64(vertices,faces))
    assert tool.is_empty()
    with pytest.raises(RuntimeError,match='surcos de retenci'):
        apply_retention_policy(mf.Manifold.cube((5,5,5)),tool,{'retention_mode':'dual_required'})


def test_noncontiguous_tool_is_normalized_without_changing_geometry():
    v=np.arange(24,dtype=float).reshape(4,6)[:,::2]
    f=np.array([[0,1,2],[1,2,3]],dtype=np.int64)
    vertices,faces=triangle_arrays(v,f)
    assert vertices.flags.c_contiguous and faces.flags.c_contiguous
    assert faces.dtype==np.uint64
    np.testing.assert_array_equal(vertices,v)
    np.testing.assert_array_equal(faces,f)


@pytest.mark.parametrize('vertices,faces',[
    ([[0,0,0]],[[0,0,2]]),([[0,0,0]],[[-1,0,0]]),
    ([[0,0,0]],[[0.,0.,0.]]),([[float('nan'),0,0]],[[0,0,0]]),
    ([],[[0,0,0]]),([[0,0,0]],[]),
])
def test_malformed_tools_are_not_silently_repaired(vertices,faces):
    with pytest.raises(ValueError):triangle_arrays(vertices,faces)


def test_nested_stage_typeerror_is_not_hidden_by_subprocess_wrapper(tmp_path):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine'))
    from ejecutar import stage_error
    log=tmp_path/'stage.log'
    log.write_text('Traceback...\nTypeError: invalid triangle array\nConstructor details\n',encoding='utf-8')
    assert stage_error(log)=='TypeError: invalid triangle array'
    assert 'registro' in stage_error(tmp_path/'missing.log')
