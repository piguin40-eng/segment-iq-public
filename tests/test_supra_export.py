import sys
from pathlib import Path
import numpy as np
import pytest
import trimesh

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine/engine'))
from mesh_export import prepare_indexed_export


@pytest.mark.parametrize('offset',[(1,1,1),(1,1,0)])
def test_coincident_supra_contacts_survive_both_frames_without_topology_changes(offset):
    a=trimesh.creation.box();b=trimesh.creation.box();b.apply_translation(offset)
    mesh=trimesh.util.concatenate([a,b]);vertices=mesh.vertices.copy();faces=mesh.faces.copy()
    transform=trimesh.transformations.rotation_matrix(.33,[.2,.4,1]);transform[:3,3]=[31,-27,51]
    result,report=prepare_indexed_export(mesh,transform,expected_euler=4)
    assert report['vertex_contacts']['separated_vertices']>0
    assert report['vertex_contacts']['maximum_shift_mm']<=1.000001e-6
    assert abs(report['volume_change_mm3'])<1e-5
    for frame in report['roundtrip'].values():
        assert frame['closed'] and frame['consistent_winding'] and frame['euler']==4
    np.testing.assert_array_equal(mesh.vertices,vertices)
    np.testing.assert_array_equal(result.faces,faces)
    assert len(result.split())==2  # No deletion or joining of material fragments.


def test_clean_mesh_is_unchanged_and_real_defects_are_not_repaired():
    mesh=trimesh.creation.box()
    result,report=prepare_indexed_export(mesh,np.eye(4),expected_euler=2)
    np.testing.assert_array_equal(result.vertices,mesh.vertices)
    assert report['vertex_contacts']['separated_vertices']==0
    with pytest.raises(RuntimeError,match='topologia no prevista'):
        prepare_indexed_export(mesh,np.eye(4),expected_euler=0)
    mesh.update_faces(np.arange(len(mesh.faces)-1))
    with pytest.raises(RuntimeError,match='volumen cerrado'):
        prepare_indexed_export(mesh,np.eye(4))
