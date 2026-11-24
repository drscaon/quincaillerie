"""What Newton needs and cannot guess is a layer over each file, not part of the file."""

import glob
import os

import pytest
from pxr import Usd, UsdPhysics

from quincaillerie import contract, generate, newton, resolve
from quincaillerie.cli import main
from quincaillerie.validate import validate


@pytest.fixture(scope="module")
def pack(tmp_path_factory):
    parts = resolve("screw", "M6", length=16, with_=["nut", "washer"]) + resolve("holder", "AA")
    return generate(parts, tmp_path_factory.mktemp("set"), count=1, seed=1, detail="low").out_dir


def _layers(folder, suffix):
    return sorted(glob.glob(os.path.join(folder, "**", f"*{suffix}.usda"), recursive=True))


def test_every_part_and_the_scene_have_a_newton_layer(pack):
    mains = [
        f
        for f in glob.glob(os.path.join(pack, "**", "*.usd*"), recursive=True)
        if not contract.is_engine_layer(f) and "materials" not in f
    ]
    assert _layers(pack, "_newton") == sorted(str(newton.overlay_path(f)) for f in mains)
    for layer in _layers(pack, "_newton"):
        assert newton.check(layer) == [], layer
        assert validate(layer) == [], layer
        assert contract.check(layer) == [], layer
    assert newton.main([pack]) == 0


def test_the_files_hold_no_newton_data(pack):
    for f in glob.glob(os.path.join(pack, "**", "*.usd*"), recursive=True):
        if not contract.is_engine_layer(f):
            assert contract.engine_data(Usd.Stage.Open(f)) == [], f


def test_every_collider_gets_the_contact_gap_its_asset_asks_for(pack):
    for layer in _layers(pack, "_newton"):
        stage = Usd.Stage.Open(layer)
        for prim in stage.Traverse():
            if prim.HasAPI(UsdPhysics.CollisionAPI) and prim.GetPath() != newton.GROUND:
                assert prim.GetAttribute(newton.GAP).Get() == pytest.approx(newton.physx._contact_offset(prim))


def test_a_holder_is_an_articulation_in_its_newton_layer_only(pack):
    (holder,) = glob.glob(os.path.join(pack, "assets", "Holder_AA_*[0-9].usda"))
    assert not Usd.Stage.Open(holder).GetDefaultPrim().HasAPI(UsdPhysics.ArticulationRootAPI)
    assert Usd.Stage.Open(str(newton.overlay_path(holder))).GetDefaultPrim().HasAPI(UsdPhysics.ArticulationRootAPI)
    scene = Usd.Stage.Open(os.path.join(pack, "scene_newton.usda"))
    roots = [p for p in scene.Traverse() if p.HasAPI(UsdPhysics.ArticulationRootAPI)]
    assert roots and all("Holder_AA" in str(p.GetPath()) for p in roots)  # the holder alone, not the scene


def test_check_finds_a_collider_without_a_gap(pack, tmp_path):
    (nut,) = glob.glob(os.path.join(pack, "assets", "ISO4032_M6_*[0-9].usd*"))
    stage = Usd.Stage.Open(str(newton.overlay_path(nut)))
    collider = next(p for p in stage.Traverse() if p.HasAttribute(newton.GAP))
    collider.RemoveProperty(newton.GAP)
    stage.GetRootLayer().Export(str(tmp_path / os.path.basename(newton.overlay_path(nut))))
    os.symlink(nut, tmp_path / os.path.basename(nut))
    problems = newton.check(tmp_path / os.path.basename(newton.overlay_path(nut)))
    assert any("do not go together" in p for p in problems)


@pytest.mark.parametrize(("engines", "physx", "newton_"), [("none", 0, 0), ("physx", 1, 0), ("newton", 0, 1)])
def test_engines_chooses_the_layers(tmp_path, engines, physx, newton_):
    assert main(["generate", "nut", "M4", "--out", str(tmp_path), "--no-scene", "--engines", engines]) == 0
    assert len(_layers(tmp_path, "_physx")) == physx
    assert len(_layers(tmp_path, "_newton")) == newton_


def test_engines_refuses_an_unknown_engine():
    with pytest.raises(ValueError, match="unknown engine"):
        contract.engine_list("physx,bullet")
    assert contract.engine_list("none") == ()
    assert contract.engine_list("newton, physx") == ("newton", "physx")
