"""Variation: instances differ as drawn, reproducibly, and the drawn values reach the geometry,
the physics and the ground truth."""

import csv
import os

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics

from quincaillerie.fasteners import _bend, _widen
from quincaillerie.threads import iso_profile, segments
from quincaillerie.variation import ASPECTS, FastenerVariation, Sampler


def _draw(**kw):
    s = Sampler(**kw)
    return [s.fastener("screw", "zinc_clear", 1.25) for _ in range(20)]


def test_same_seed_same_instances_and_independent_aspects():
    a, b = _draw(seed=7), _draw(seed=7)
    assert a == b
    c = _draw(seed=8)
    assert a != c
    no_wear = _draw(seed=7, vary=tuple(x for x in ASPECTS if x != "wear"))
    assert [v.clearance_mm for v in no_wear] == [v.clearance_mm for v in a]  # its own stream
    assert all(v.rust == 0 and v.oil == 0 and v.dirt == 0 for v in no_wear)


def test_ranges():
    vs = _draw(seed=1, defect_rate=0.5) + _draw(seed=2, defect_rate=0.5)
    cl = [v.clearance_mm for v in vs]
    assert 0.02 <= min(cl) and max(cl) <= 0.10
    assert 0.2 < sum(v.defect != "none" for v in vs) / len(vs) < 0.8
    nominal = Sampler(vary=()).fastener("screw", "brass", 1.25)
    assert nominal.defect == "none" and nominal.clearance_mm == 0.05 and nominal.density == 8500.0


def test_crushed_thread_interferes_with_the_mating_thread():
    p = iso_profile(0.008, 0.00125)
    v = FastenerVariation(defect="crushed_thread", defect_size=0.3, defect_z=0.5, defect_angle_deg=90)
    zone = (0.010, 0.014, 0.0, np.pi / 2)
    crushed = segments(p, 0, 0.03, 5e-5, "bolt", crush=(zone, _widen(v, 0.00125), 1e-4))
    sound = segments(p, 0, 0.03, 5e-5, "bolt")
    axial = lambda ps: max(np.ptp(q[:, 2]) for q in ps)  # noqa: E731
    assert axial(crushed) > axial(sound) + 0.3 * 0.00125  # wider ridges in the zone


def test_bend_moves_the_tip():
    pts = np.array([[0, 0, 0.0], [0, 0, 0.03]])
    bent = _bend(pts, 2.0, 0.03)
    assert bent[0, 0] == 0 and abs(bent[1, 0] - np.radians(2.0) * 0.03 / 2) < 1e-12


def test_varied_set_files_and_ground_truth(varied_set):
    files = sorted(os.listdir(os.path.join(varied_set.out_dir, "assets")))
    assert len(files) == 20 and "ISO4017_M6x12_004.usdc" in files and "Holder_AA_004.usda" in files
    with open(os.path.join(varied_set.out_dir, "parts.csv")) as f:
        rows = list(csv.DictReader(f))
    screws = [r for r in rows if r["kind"] == "screw"]
    assert len({r["variation:clearance_mm"] for r in screws}) == 5  # five different fits
    st = Usd.Stage.Open(os.path.join(varied_set.out_dir, "assets", "ISO4017_M6x12_002.usdc"))
    root = st.GetDefaultPrim()
    row = next(r for r in screws if r["name"] == "ISO4017_M6x12_002")
    clear = root.GetAttribute("quincaillerie:threadClearance").Get()
    assert abs(clear - float(row["variation:clearance_mm"]) * 1e-3) < 1e-9
    mat = st.GetPrimAtPath("/ISO4017_M6x12_002/PhysicsMaterials/steel")
    assert abs(UsdPhysics.MaterialAPI(mat).GetDynamicFrictionAttr().Get() - float(row["variation:friction"])) < 1e-6
    holders = [r for r in rows if r["kind"] == "holder"]
    assert len({r["variation:spring_factor"] for r in holders}) == 5


def test_worn_instances_have_their_own_material(varied_set):
    rows = list(csv.DictReader(open(os.path.join(varied_set.out_dir, "parts.csv"))))
    worn = [r for r in rows if r["kind"] == "screw" and float(r["variation:scratches"] or 0) > 0.02]
    assert worn
    st = Usd.Stage.Open(os.path.join(varied_set.out_dir, worn[0]["file"]))
    root = st.GetDefaultPrim()
    vs = root.GetVariantSets().GetVariantSet("finish")
    assert vs.GetVariantSelection() == "as_generated" and "zinc_clear" in vs.GetVariantNames()
    tex = os.listdir(os.path.join(varied_set.out_dir, "materials", "instances"))
    assert f"{worn[0]['name']}_worn_color.png" in tex
    mesh = next(p for p in st.Traverse() if p.IsA(UsdGeom.Mesh) and "Visual" in str(p.GetPath()))
    assert mesh


def test_varied_set_passes_its_checks(varied_set):
    import pytest

    pytest.importorskip("mujoco")
    from quincaillerie.sim.checks import sim_test

    rows = sim_test(varied_set.out_dir, verbose=False, only="AA")  # holders, seated cells, insertions
    assert rows and all(r["ok"] for r in rows), [r for r in rows if not r["ok"]]
