"""What only PhysX reads is a layer over each file, not part of the file."""

import glob
import os

import pytest
from pxr import Sdf, Usd, UsdPhysics

from quincaillerie import generate, physx, resolve
from quincaillerie.sim.checks import inventory
from quincaillerie.validate import validate


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    parts = resolve("screw", "M6", length=16, with_=["nut", "washer"])
    return generate(parts, tmp_path_factory.mktemp("set"), count=2, seed=1, detail="low").out_dir


def _files(pack):
    files = sorted(glob.glob(os.path.join(pack, "**", "*.usd*"), recursive=True))
    return [f for f in files if not physx.is_overlay(f)], [f for f in files if physx.is_overlay(f)]


def test_the_files_hold_no_engine_data(pack):
    mains, _ = _files(pack)
    assert len(mains) == 8  # 6 parts, the materials and the scene
    for f in mains:
        assert physx.engine_data(Usd.Stage.Open(f)) == [], f


def test_every_part_and_the_scene_have_a_physx_layer(pack):
    mains, layers = _files(pack)
    expected = [str(physx.overlay_path(f)) for f in mains if "materials" not in f]
    assert layers == sorted(expected)
    for layer in layers:
        assert physx.check(layer) == [], layer
        assert validate(layer) == [], layer  # the OpenUSD validators
    assert physx.main([pack]) == 0


def test_a_thread_asks_for_a_smaller_contact_offset_than_a_cell(pack, tmp_path):
    screw = next(a for a in inventory(pack).values() if a["kind"] == "screw")
    stage = Usd.Stage.Open(str(physx.overlay_path(screw["file"])))
    root = stage.GetDefaultPrim()
    assert root.GetAttribute(physx.ASKED).Get() == pytest.approx(0.0001)
    assert root.GetAttribute("physxRigidBody:solverPositionIterationCount").Get() == 32
    colliders = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI)]
    assert len(colliders) > 100
    assert {round(c.GetAttribute("physxCollision:contactOffset").Get(), 6) for c in colliders} == {0.0001}
    cells = generate(resolve("cell", "AA"), tmp_path, count=1, scene=False).out_dir
    cell = next(iter(inventory(cells).values()))
    stage = Usd.Stage.Open(str(physx.overlay_path(cell["file"])))
    body = next(p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI))
    assert body.GetAttribute("physxRigidBody:solverPositionIterationCount").Get() == 16
    collider = next(p for p in stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI))
    assert collider.GetAttribute("physxCollision:contactOffset").Get() == pytest.approx(0.0005)


def test_the_scene_layer_references_the_layers_of_its_parts(pack):
    layer = os.path.join(pack, "scene_physx.usda")
    text = open(layer).read()
    assert "physxCollision" not in text  # nothing repeated: the parts' own layers say it
    assert list(Sdf.Layer.FindOrOpen(layer).subLayerPaths) == ["./scene.usda"]
    for name in inventory(pack):
        assert f"@./assets/{name}_physx.usda@" in text
    stage = Usd.Stage.Open(layer)
    bodies = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    assert len(bodies) >= 6
    assert all("PhysxRigidBodyAPI" in physx._authored(b) for b in bodies)
    assert not stage.GetPrimAtPath(physx.GROUND).GetAttribute("physxCollision:contactOffset")


def test_layers_are_not_assets(pack):
    """The inventory of a set and its table list the parts, not their layers."""
    assert sorted(inventory(pack)) == sorted(os.path.splitext(os.path.basename(f))[0] for f in _files(pack)[0][:6])


def test_no_layer_without_physics(tmp_path):
    out = generate(resolve("nut", "M6"), tmp_path, count=1, detail="low", physics=False).out_dir
    assert glob.glob(os.path.join(out, "**", "*_physx.usda"), recursive=True) == []
    assert (
        not Usd.Stage.Open(glob.glob(os.path.join(out, "assets", "*.usdc"))[0])
        .GetDefaultPrim()
        .GetAttribute(physx.ASKED)
    )
