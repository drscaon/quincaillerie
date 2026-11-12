"""MuJoCo checks on a few assets (the whole catalogue runs in CI's sim job)."""

import pytest

pytest.importorskip("mujoco")

from quincaillerie.sim.checks import build_test_scenes, check_insertion, check_scene, insertion, inventory  # noqa: E402


@pytest.fixture(scope="module")
def scenes(small_set):
    return {name: (kind, path, info) for name, kind, path, info in build_test_scenes(small_set.out_dir)}


@pytest.mark.parametrize("name", ["drop_ISO7089_M4", "drop_Cell_AA", "holder_AA", "seated_AA", "nut_on_screw_M4"])
def test_gravity(scenes, name):
    kind, path, info = scenes[name]
    ok, msg, _ = check_scene(name, kind, path, info)
    assert ok, msg


@pytest.mark.parametrize("reverse", [False, True])
def test_insertion_aa(small_set, reverse):
    inv = inventory(small_set.out_dir)
    r = insertion(inv["Cell_AA"]["file"], inv["Holder_AA"]["file"], "AA", reverse)
    ok, msg = check_insertion(r)
    assert ok, msg
    assert r["polarity"] == ("reversed" if reverse else "correct")


def test_a_scene_of_simple_fasteners_settles(tmp_path):
    from quincaillerie import generate, resolve
    from quincaillerie.sim.checks import build_test_scenes, settle_scene

    parts = resolve("screw", "M6", 12, ["nut", "washer"])
    res = generate(parts, str(tmp_path), "pile", count=30, detail="low", collider="simple", seed=2)
    ok, msg, _ = settle_scene(res.scene)
    assert ok, msg
    # a nut does not hold on a screw by simple colliders: no such test scene is built
    assert not any(kind == "nut_on_screw" for _, kind, _, _ in build_test_scenes(res.out_dir))
