import sys
from pathlib import Path
import numpy as np
import pytest
trimesh=pytest.importorskip('trimesh')
pytest.importorskip('manifold3d')
sys.path.insert(0,str(Path(__file__).parents[1]/'engine'))
from inspect_insertion import inspect,direction_for


def test_proposed_direction_is_identified_without_changing_geometry_or_approval():
    assert direction_for({})==([0,0,1],'provisional_working_Z')
    profile={'shape_refinement':{'proposed_insertion_direction_work':[-.01,.005,1]}}
    assert direction_for(profile)==([-.01,.005,1],'profile_proposal_not_approved')
    assert direction_for(profile,[0,0,1])==([0,0,1],'explicit_test_direction')


def test_separate_at_rest_can_collide_during_extraction_without_modifying_meshes():
    fixed=trimesh.creation.box([1,1,1]);moving=fixed.copy();moving.apply_translation([0,0,-2])
    original=moving.vertices.copy()
    report=inspect(fixed,moving)
    assert report['samples'][0]['collision_volume_mm3']==0
    assert report['status']=='COLLISION_DETECTED' and report['maximum_collision_mm3']>.9
    assert report['samples'][-1]['collision_volume_mm3']==0
    assert not report['continuous_path_verified']
    assert np.array_equal(moving.vertices,original)


def test_sampled_free_direction_is_not_reported_as_global_certification():
    fixed=trimesh.creation.box([1,1,1]);moving=fixed.copy();moving.apply_translation([2,0,0])
    report=inspect(fixed,moving,[0,0,3])
    assert report['direction_work']==[0,0,1]
    assert report['status']=='NO_COLLISION_IN_SAMPLED_POSITIONS'
    assert report['maximum_collision_mm3']==0 and not report['continuous_path_verified']


@pytest.mark.parametrize('axis,step',[([0,0,0],.25),([float('nan'),0,1],.25),([0,0,1],0),([0,0,1],float('inf'))])
def test_invalid_sampling_is_rejected(axis,step):
    box=trimesh.creation.box()
    with pytest.raises(ValueError):inspect(box,box,axis,step)
