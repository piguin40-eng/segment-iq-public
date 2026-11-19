import sys
from pathlib import Path
import numpy as np
import pytest
trimesh=pytest.importorskip('trimesh')
mf=pytest.importorskip('manifold3d')
sys.path.insert(0,str(Path(__file__).parents[1]/'engine'))
from inspect_walls import inspect,first_hit


def mesh(solid):
    raw=solid.to_mesh64();return trimesh.Trimesh(raw.vert_properties[:,:3],raw.tri_verts,process=False)


def test_side_wall_defect_is_detected_with_real_cavity_normals():
    source=mf.Manifold.cube((6,6,6),True)
    primary=mf.Manifold.cube((4,4,4),True).translate((.5,0,0))
    cavity=mf.Manifold.cube((4.2,4.2,4.2),True).translate((.5,0,0))
    p=mesh(primary);before=p.vertices.copy()
    report=inspect(mesh(source),p,mesh(source-cavity),samples=1000)
    assert report['thin_wall_count']>0
    assert report['minimum_sampled_wall_mm']==pytest.approx(.4,abs=1e-5)
    assert all(row['normal_into_supra_work'][0]>.99 for row in report['worst_wall_clusters'])
    assert not report['global_minimum_verified']
    assert np.array_equal(p.vertices,before)


def test_uniform_shell_passes_samples_without_claiming_global_verification():
    source=mf.Manifold.cube((6,6,6),True);primary=mf.Manifold.cube((4,4,4),True)
    report=inspect(mesh(source),mesh(primary),mesh(source-mf.Manifold.cube((4.2,4.2,4.2),True)),samples=1000)
    assert report['status']=='NO_DEFECT_IN_SAMPLED_WALLS'
    assert report['measured_wall_count']==1000
    assert report['minimum_sampled_wall_mm']==pytest.approx(.9)
    assert report['missing_cavity_count']==0 and not report['global_minimum_verified']


def test_missing_supra_cannot_be_replaced_by_material_in_a_distant_original_component():
    local=mf.Manifold.cube((6,6,6),True);remote=local.translate((15,0,0))
    primary=mf.Manifold.cube((4,4,4),True)
    report=inspect(mesh(local+remote),mesh(primary),mesh(remote),samples=500)
    assert report['missing_cavity_count']==500
    assert report['measured_wall_count']==0
    assert report['status']=='WALL_DEFECTS_FOUND'


def test_first_hit_uses_the_nearest_positive_surface():
    a=trimesh.creation.box((2,2,2));b=a.copy();b.apply_translation((5,0,0))
    locations,faces,d=first_hit(trimesh.util.concatenate((a,b)),np.array([[-3.,0,0]]),np.array([[1.,0,0]]))
    assert d[0]==pytest.approx(2.) and locations[0,0]==pytest.approx(-1.)


def test_material_exit_ignores_internal_overlap_but_stops_before_real_gap():
    a=trimesh.creation.box((4,4,4));b=trimesh.creation.box((2,2,2));b.apply_translation((1.5,0,0))
    remote=a.copy();remote.apply_translation((10,0,0))
    joined=trimesh.util.concatenate((a,b,remote))
    origins=np.array([[0.,0,0]]);directions=np.array([[1.,0,0]])
    _,_,first=first_hit(joined,origins,directions)
    _,_,exit=first_hit(joined,origins,directions,material_exit=True)
    assert first[0]==pytest.approx(.5)
    assert exit[0]==pytest.approx(2.5)


def test_overlap_inside_uniform_shell_does_not_discard_wall_measurements():
    source=mf.Manifold.cube((6,6,6),True);primary=mf.Manifold.cube((4,4,4),True)
    cavity=mf.Manifold.cube((4.2,4.2,4.2),True)
    internal=mesh(mf.Manifold.cube((5.6,5.6,5.6),True)-mf.Manifold.cube((4.8,4.8,4.8),True))
    report=inspect(trimesh.util.concatenate((mesh(source),internal)),mesh(primary),
        trimesh.util.concatenate((mesh(source-cavity),internal)),samples=1000)
    assert report['status']=='NO_DEFECT_IN_SAMPLED_WALLS'
    assert report['measured_wall_count']==1000 and report['invalid_wall_ray_count']==0
    assert report['minimum_sampled_wall_mm']==pytest.approx(.9)
    assert not report['global_minimum_verified']
