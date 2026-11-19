import sys
from pathlib import Path
import pytest
mf=pytest.importorskip('manifold3d')
sys.path.insert(0,str(Path(__file__).parents[1]/'engine/engine'))
from retention_safety import apply_retention_policy,retention_mode


def test_video_protocol_can_preserve_an_intact_bar_without_optional_grooves():
    base=mf.Manifold.cube([10,10,5])
    result,removed,report=apply_retention_policy(base,None,{'retention_mode':'none'})
    assert result.volume()==base.volume() and removed.is_empty()
    assert report['status']=='not_applied_by_design' and not report['accepted']


def test_optional_grooves_do_not_fail_when_only_a_perforating_cut_exists():
    base=mf.Manifold.cube([10,10,5])
    tool=mf.Manifold.cylinder(7,.5,.5,32).translate([2,2,-1])
    result,removed,report=apply_retention_policy(base,tool,{'retention_mode':'dual_optional'})
    assert result.volume()==base.volume() and removed.is_empty()
    assert report['status']=='no_safe_grooves' and len(report['rejected'])==1
    with pytest.raises(RuntimeError,match='No quedan surcos'):
        apply_retention_policy(base,tool,{'retention_mode':'dual_required'})


@pytest.mark.parametrize('mode',['none','dual_optional','dual_required'])
def test_retention_choice_never_hides_an_already_disconnected_primary(mode):
    base=mf.Manifold.cube([2,2,2])+mf.Manifold.cube([1,1,1]).translate([4,0,0])
    with pytest.raises(RuntimeError,match='fragmentos antes'):
        apply_retention_policy(base,mf.Manifold(),{'retention_mode':mode})


def test_legacy_profiles_remain_explicitly_required_and_unknown_modes_fail():
    assert retention_mode({})=='dual_required'
    with pytest.raises(ValueError):retention_mode({'retention_mode':'skip_safety'})


def test_shallow_groove_survives_serialization_and_matches_original_tool_difference():
    import numpy as np
    base=mf.Manifold.cube([10,10,5])
    tool=mf.Manifold.cylinder(12,.4,.4,48).rotate([0,90,0]).translate([-1,5,5.1])
    expected=base-tool
    result,removed,report=apply_retention_policy(base,tool,{'retention_mode':'dual_required'})
    assert report['accepted'] and not report['rejected']
    assert result.volume()==pytest.approx(expected.volume(),abs=1e-7)
    assert result.genus()==base.genus() and len(result.decompose())==1
    assert mf.Manifold(result.to_mesh64()).simplify(1e-7).genus()==base.genus()
    # The padding clips existing tool only: no removal outside it.
    assert (removed-tool).volume()<1e-7
