"""The simple colliders of fasteners: the envelope alone, for large scenes."""

import csv
import os

import numpy as np
import pytest
from pxr import Usd, UsdPhysics

from quincaillerie.catalog import METRIC
from quincaillerie.cli import main
from quincaillerie.fasteners import nut_wedges, write_screw
from quincaillerie.generator import generate, resolve

MM = 1e-3


@pytest.fixture(scope="module")
def sets(tmp_path_factory):
    """The same parts and seed with threaded and with simple colliders."""
    out = tmp_path_factory.mktemp("colliders")
    parts = resolve("screw", "M6", 12, ["nut", "washer"])
    kw = dict(count=3, detail="low", seed=4, defect_rate=0.5)
    return {c: generate(parts, str(out / c), "set", collider=c, **kw) for c in ("thread", "simple")}


def _rows(res):
    with open(os.path.join(res.out_dir, "instances.csv")) as f:
        return {r["name"]: r for r in csv.DictReader(f)}


def test_nut_wedges_leave_the_bore_free_and_fill_the_hexagon():
    s_af, bore, height = 13 * MM, 4.05 * MM, 6.5 * MM
    wedges = nut_wedges(s_af, bore, height)
    assert len(wedges) == 12
    for pts in wedges:
        r = np.linalg.norm(pts[:, :2], axis=1)
        inner = pts[np.isclose(r, r.min())][:, :2]
        a, b = np.unique(inner.round(12), axis=0)  # the inner face, seen from above
        assert np.linalg.norm((a + b) / 2) == pytest.approx(bore)  # its chord touches the bore circle
        assert r.max() <= s_af / np.sqrt(3) + 1e-12
        assert set(pts[:, 2].round(12)) == {0.0, round(height, 12)}


def test_simple_colliders_are_few_and_change_nothing_else(sets):
    thread, simple = _rows(sets["thread"]), _rows(sets["simple"])
    assert thread.keys() == simple.keys()
    for name, row in simple.items():
        pieces = {"screw": {2}, "nut": {12}, "washer": {8}}[row["kind"]]
        if row["variation:defect"] == "bent":  # a bent shank follows the bend in slices
            assert int(row["measured:colliders"]) > 2
        else:
            assert int(row["measured:colliders"]) in pieces
        assert int(thread[name]["measured:colliders"]) > int(row["measured:colliders"])
        # the same instance: same draws, same mass
        for key in ("measured:mass_kg", "variation:defect", "variation:clearance_mm"):
            assert row[key] == thread[name][key]


def test_the_asset_says_which_collider_it_has(sets):
    for collider, res in sets.items():
        assets = os.path.join(res.out_dir, "assets")
        for f in sorted(os.listdir(assets)):
            stage = Usd.Stage.Open(os.path.join(assets, f))
            root = stage.GetDefaultPrim()
            assert root.GetAttribute("quincaillerie:collision").Get() == collider
            shapes = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.CollisionAPI)]
            assert shapes and root.HasAPI(UsdPhysics.RigidBodyAPI)


def test_a_simple_screw_is_a_cylinder_at_the_major_diameter(tmp_path):
    info = write_screw(str(tmp_path / "s.usdc"), "M8", 30, collider="simple", detail="low")
    assert info["colliders"] == 2
    stage = Usd.Stage.Open(str(tmp_path / "s.usdc"))
    core = stage.GetPrimAtPath(f"/{stage.GetDefaultPrim().GetName()}/Collision/core")
    radius = core.GetAttribute("radius").Get()
    assert METRIC["M8"]["d"] * MM / 2 * 0.97 < radius < METRIC["M8"]["d"] * MM / 2


def test_unknown_collider(tmp_path):
    with pytest.raises(ValueError, match="unknown collider"):
        write_screw(str(tmp_path / "s.usdc"), "M8", 30, collider="box")


def test_command_line(tmp_path):
    args = ["generate", "screw", "M6", "--count", "2", "--detail", "low", "--collider", "simple"]
    assert main([*args, "--out", str(tmp_path)]) == 0
    rows = list(csv.DictReader(open(tmp_path / "ISO4017_M6x20" / "instances.csv")))
    assert all(int(r["measured:colliders"]) <= 8 for r in rows)


def test_a_large_scene_lays_its_rows_on_a_floor_that_covers_them(tmp_path):
    from pxr import UsdGeom

    res = generate(resolve("washer", "M6"), str(tmp_path), "many", count=60, detail="low", collider="simple")
    stage = Usd.Stage.Open(res.scene)
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_])
    floor = box.ComputeWorldBound(stage.GetPrimAtPath("/World/Ground")).ComputeAlignedRange()
    for prim in stage.GetPrimAtPath("/World").GetChildren():
        if prim.GetName().startswith("ISO7089"):
            x, y, _ = UsdGeom.XformCommonAPI(prim).GetXformVectors(Usd.TimeCode.Default())[0]
            assert floor.GetMin()[0] < x < floor.GetMax()[0] and floor.GetMin()[1] < y < floor.GetMax()[1]
    washers = [p for p in stage.GetPrimAtPath("/World").GetChildren() if p.GetName().startswith("ISO7089")]
    rows = {round(UsdGeom.XformCommonAPI(p).GetXformVectors(Usd.TimeCode.Default())[0][1], 6) for p in washers}
    assert len(washers) == 60 and len(rows) == 3  # 25 to a row
