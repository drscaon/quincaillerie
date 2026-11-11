"""The ground and physics scene shared by every Primvaria project (quincaillerie/ground.py)."""

from pathlib import Path

import pytest
from pxr import Usd

from quincaillerie.ground import conformance, read_ground
from quincaillerie.sim.checks import build_test_scenes


@pytest.mark.parametrize("fixture", ["small_set", "varied_set"])
def test_scenes_follow_the_shared_convention(fixture, request):
    scene = Path(request.getfixturevalue(fixture).out_dir) / "scene.usda"
    stage = Usd.Stage.Open(str(scene))
    assert conformance(stage) == []
    g = read_ground(stage)
    assert g["top"] == pytest.approx(0.0, abs=1e-9)
    assert g["dynamic_friction"] == pytest.approx(0.5)


def test_check_scenes_follow_the_shared_convention(small_set):
    for _, _, path, _ in build_test_scenes(small_set.out_dir)[:3]:
        assert conformance(Usd.Stage.Open(path)) == [], path
