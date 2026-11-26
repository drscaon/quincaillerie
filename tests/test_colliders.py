"""The simple colliders of fasteners: the envelope alone, for large scenes."""

import csv
import os

import numpy as np
import pytest
from pxr import Gf, Usd, UsdGeom, UsdPhysics

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


@pytest.mark.slow
def test_simple_colliders_are_few_and_change_nothing_else(sets):
    thread, simple = _rows(sets["thread"]), _rows(sets["simple"])
    assert thread.keys() == simple.keys()
    for name, row in simple.items():
        # a screw: core, head, bearing face, fillet; a bolt: and its plain shank
        pieces = {"screw": {4}, "bolt": {5}, "cap_screw": {9, 10}, "nut": {12}, "washer": {8}}[row["kind"]]
        if row["variation:defect"] == "bent":  # a bent shank follows the bend in slices
            assert int(row["measured:colliders"]) > 4
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
    assert info["colliders"] == 4  # core, head, bearing face, fillet
    stage = Usd.Stage.Open(str(tmp_path / "s.usdc"))
    core = stage.GetPrimAtPath(f"/{stage.GetDefaultPrim().GetName()}/Collision/core")
    radius = core.GetAttribute("radius").Get()
    assert METRIC["M8"]["d"] * MM / 2 * 0.97 < radius < METRIC["M8"]["d"] * MM / 2


def test_a_bolt_collides_on_its_plain_shank_then_on_its_thread(tmp_path):
    """ISO 4014 (QUI-06): the shank collider is the drawn plain shank, the thread starts where it ends;
    the bearing face and the fillet under the head have their own colliders."""
    from quincaillerie.fasteners import write_bolt

    info = write_bolt(str(tmp_path / "b.usdc"), "M8", 50, collider="simple", detail="low")
    assert info["colliders"] == 5
    stage = Usd.Stage.Open(str(tmp_path / "b.usdc"))
    root = stage.GetDefaultPrim()
    lp = root.GetAttribute("quincaillerie:plainLength").Get()
    ds = root.GetAttribute("quincaillerie:shankDiameter").Get()
    assert lp == pytest.approx(root.GetAttribute("primvaria:variation:plain_length_mm").Get() * MM)
    shank = stage.GetPrimAtPath(f"/{root.GetName()}/Collision/shank")
    assert shank.GetAttribute("radius").Get() == pytest.approx(ds / 2)
    assert shank.GetAttribute("height").Get() == pytest.approx(lp)
    core = stage.GetPrimAtPath(f"/{root.GetName()}/Collision/core")
    length = root.GetAttribute("quincaillerie:length").Get()
    assert core.GetAttribute("height").Get() == pytest.approx(length - lp)
    face = stage.GetPrimAtPath(f"/{root.GetName()}/Collision/bearing_face")
    dw = root.GetAttribute("quincaillerie:bearingFaceDiameter").Get()
    assert face.GetAttribute("radius").Get() == pytest.approx(dw / 2)


def test_a_hex_key_goes_into_a_cap_screws_socket(tmp_path):
    """ISO 4762 (QUI-08): the head's colliders leave the socket free. A hex key at the socket's
    across flats, a hundredth of a millimetre smaller, lies inside none of the head's convex pieces
    down to the socket's depth, and the solid piece under it stops it there."""
    from scipy.spatial import Delaunay

    from quincaillerie.fasteners import write_cap_screw

    info = write_cap_screw(str(tmp_path / "c.usdc"), "M8", 30, collider="simple", detail="low")
    assert info["colliders"] == 9  # core, head, six socket walls, fillet
    stage = Usd.Stage.Open(str(tmp_path / "c.usdc"))
    root = stage.GetDefaultPrim()
    s_af = root.GetAttribute("primvaria:variation:across_flats_dmm").Get() * MM + 6.0 * MM
    depth = root.GetAttribute("quincaillerie:socketDepth").Get()
    assert depth == pytest.approx(root.GetAttribute("primvaria:variation:socket_depth_mm").Get() * MM)
    frame = stage.GetPrimAtPath(f"/{root.GetName()}/MateFrame_drive")
    z_top = UsdGeom.Xformable(frame).ComputeLocalToWorldTransform(0).ExtractTranslation()[2]  # top of the head
    key_r = (s_af - 0.01 * MM) / np.sqrt(3)
    ang = np.arange(6) * np.pi / 3 + np.pi / 6
    key = np.array(
        [[key_r * np.cos(a), key_r * np.sin(a), z_top + z] for a in ang for z in np.linspace(0, depth * 0.999, 5)]
    )
    deeper = np.array([[0.0, 0.0, z_top + depth * 1.05]])
    hit_deeper = False
    for prim in stage.GetPrimAtPath(f"/{root.GetName()}/Collision").GetChildren():
        if not prim.GetName().startswith(("head", "socket_wall")):
            continue
        pts = np.array(prim.GetAttribute("points").Get(), float)
        xf = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0)
        pts = np.array([xf.Transform(Gf.Vec3d(*p)) for p in pts])
        hull = Delaunay(pts)
        assert not (hull.find_simplex(key, tol=-1e-9) >= 0).any(), prim.GetName()
        hit_deeper |= bool((hull.find_simplex(deeper) >= 0).any())
    assert hit_deeper  # the key bottoms out at the socket's depth


def test_a_cap_screws_socket_has_its_corners_where_its_colliders_have_them():
    """The visual socket and the collision walls are the same hexagon: corners at 30 + 60 k degrees
    (as the hex heads'), flats in between, in the mesh as in the colliders."""
    from quincaillerie.fasteners import _hex_radius, cap_head_colliders, cap_head_mesh

    s_af = 6.0 * MM
    corners = np.radians(30 + 60 * np.arange(6))
    assert np.allclose(_hex_radius(corners, s_af), s_af / np.sqrt(3))
    assert np.allclose(_hex_radius(corners + np.pi / 6, s_af), s_af / 2)
    dk, k, t, v, dw = 13 * MM, 8 * MM, 4 * MM, 0.4 * MM, 12.5 * MM
    V, _ = cap_head_mesh(dk, k, s_af, t, v, dw)
    rim = V[np.isclose(V[:, 2], -k + t) & (np.hypot(V[:, 0], V[:, 1]) > 1e-9)]  # the socket's floor edge
    far = rim[np.isclose(np.hypot(rim[:, 0], rim[:, 1]), s_af / np.sqrt(3))]
    assert len(far) == 6
    assert np.allclose(np.sort(np.degrees(np.arctan2(far[:, 1], far[:, 0])) % 360), 30 + 60 * np.arange(6))
    _, walls = cap_head_colliders(dk, k, s_af, t, v, dw)
    inner = np.concatenate([w[np.isclose(np.hypot(w[:, 0], w[:, 1]), s_af / np.sqrt(3))] for w in walls])
    assert np.allclose(
        np.unique(np.round(np.degrees(np.arctan2(inner[:, 1], inner[:, 0])) % 360, 6)), 30 + 60 * np.arange(6)
    )


def test_unknown_collider(tmp_path):
    with pytest.raises(ValueError, match="unknown collider"):
        write_screw(str(tmp_path / "s.usdc"), "M8", 30, collider="box")


def test_command_line(tmp_path):
    args = ["generate", "screw", "M6", "--count", "2", "--detail", "low", "--collider", "simple"]
    assert main([*args, "--out", str(tmp_path)]) == 0
    rows = list(csv.DictReader(open(tmp_path / "ISO4017_M6x20" / "instances.csv")))
    assert all(int(r["measured:colliders"]) <= 8 for r in rows)


@pytest.mark.slow
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
