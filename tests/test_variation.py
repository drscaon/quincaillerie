"""Variation: instances differ as drawn, reproducibly, and the drawn values reach the geometry,
the physics and the ground truth."""

import csv
import os

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics

from quincaillerie import fits
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
    lo, hi = fits.clearance_range_mm("screw", 1.25, 8.0)
    assert lo <= min(cl) and max(cl) <= hi
    assert all(v.thread_class == "6g" for v in vs)
    assert 0.2 < sum(v.defect != "none" for v in vs) / len(vs) < 0.8
    nominal = Sampler(vary=()).fastener("screw", "brass", 1.25)
    assert nominal.defect == "none" and nominal.clearance_mm == 0.05 and nominal.density == 8500.0
    assert nominal.thread_class == ""  # nothing drawn


# Limits of the 6g / 6H fit for coarse threads, in µm: (allowance of g, screw band, nut band), as
# printed in public handbooks. The module computes them from the formulas, unrounded.
PUBLISHED = {
    "M3": (20, 75, 100),
    "M4": (22, 90, 118),
    "M5": (24, 95, 125),
    "M6": (26, 112, 150),
    "M8": (28, 118, 160),
    "M10": (32, 132, 180),
    "M12": (34, 150, 200),
}


def test_fit_formulas_agree_with_the_published_limits():
    from quincaillerie.catalog import METRIC

    for size, (es, td2, td2_nut) in PUBLISHED.items():
        p, d = METRIC[size]["P"], METRIC[size]["d"]
        assert abs(fits.allowance_g_mm(p) * 1000 - es) <= 1.0, size
        assert abs(fits.screw_band_mm(p, d) * 1000 - td2) <= 0.05 * td2, size
        assert abs(fits.nut_band_mm(p, d) * 1000 - td2_nut) <= 0.05 * td2_nut, size


def test_every_drawn_clearance_is_inside_its_fit_class():
    from quincaillerie.catalog import METRIC

    for size, m in METRIC.items():
        for kind, cls in (("screw", "6g"), ("nut", "6H")):
            s = Sampler(seed=3)
            vs = [s.fastener(kind, "zinc_clear", m["P"], m["d"]) for _ in range(200)]
            lo, hi = fits.clearance_range_mm(kind, m["P"], m["d"])
            cl = [v.clearance_mm for v in vs]
            assert lo <= min(cl) and max(cl) <= hi, (size, kind)
            assert max(cl) - min(cl) > 0.9 * (hi - lo), (size, kind)  # the band is used whole
            assert {v.thread_class for v in vs} == {cls}
            assert lo >= fits.SIM_FLOOR_MM
    washer = Sampler(seed=3).fastener("washer", "zinc_clear", 1.25, 8.0)
    assert washer.thread_class == "" and washer.clearance_mm == 0.05


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
    files = sorted(f for f in os.listdir(os.path.join(varied_set.out_dir, "assets")) if "_physx" not in f)
    assert len(files) == 20 and "ISO4017_M6x12_004.usdc" in files and "Holder_AA_004.usda" in files
    with open(os.path.join(varied_set.out_dir, "instances.csv")) as f:
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
    rows = list(csv.DictReader(open(os.path.join(varied_set.out_dir, "instances.csv"))))
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


def test_every_instance_carries_its_draws(varied_set, small_set):
    from quincaillerie.contract import variation
    from quincaillerie.pack import cell

    with open(os.path.join(varied_set.out_dir, "instances.csv")) as f:
        rows = {r["name"]: r for r in csv.DictReader(f)}
    assets = os.path.join(varied_set.out_dir, "assets")
    for name in ("ISO4017_M6x12_002", "Holder_AA_004", "Cell_AA_001"):
        st = Usd.Stage.Open(os.path.join(assets, next(f for f in os.listdir(assets) if f.startswith(name))))
        drawn = variation(st.GetDefaultPrim())
        assert drawn.pop("aspects") == ["tolerance", "defect", "wear", "physics"]
        assert drawn  # the same names and values as the variation:* columns of instances.csv
        for key, value in drawn.items():
            assert rows[name][f"variation:{key}"] == cell(value)
    # a nominal set has no aspect switched on
    nominal = sorted(os.listdir(os.path.join(small_set.out_dir, "assets")))[0]
    st = Usd.Stage.Open(os.path.join(small_set.out_dir, "assets", nominal))
    drawn = variation(st.GetDefaultPrim())
    assert drawn["aspects"] == [] and drawn["defect"] == "none"  # nominal values, still recorded
    assert not st.GetDefaultPrim().GetAuthoredPropertiesInNamespace("quincaillerie:variation")


def test_thread_play_middle_gives_the_same_clearance_whatever_the_seed():
    mid = fits.clearance_mm("screw", 1.25, 8.0, 0.5)
    drawn = [Sampler(seed=seed, thread_play="middle").fastener("screw", "zinc_clear", 1.25, 8.0) for seed in range(8)]
    assert {v.clearance_mm for v in drawn} == {mid}
    assert {v.thread_class for v in drawn} == {"6g"}
    assert len({v.length_dmm for v in drawn}) == 8  # the other tolerances still vary


def test_thread_play_changes_the_clearance_and_nothing_else():
    from dataclasses import asdict

    def rest(play):
        s = Sampler(seed=7, defect_rate=0.5, thread_play=play)
        rows = [asdict(s.fastener("nut", "zinc_clear", 1.0, 6.0)) for _ in range(30)]
        return [{k: v for k, v in r.items() if k not in ("clearance_mm", "thread_class")} for r in rows]

    assert rest("class") == rest("middle") == rest("legacy")


def test_thread_play_legacy_is_the_range_used_before_the_fit_classes():
    s = Sampler(seed=1, thread_play="legacy")
    vs = [s.fastener("screw", "zinc_clear", 1.25, 8.0) for _ in range(200)]
    assert all(0.016 * 1.25 <= v.clearance_mm <= 0.08 * 1.25 for v in vs)
    assert max(v.clearance_mm for v in vs) > fits.clearance_range_mm("screw", 1.25, 8.0)[1]  # looser than 6g
    assert {v.thread_class for v in vs} == {""}


def test_unknown_thread_play_is_refused():
    import pytest

    with pytest.raises(ValueError, match="thread play"):
        Sampler(thread_play="tight")
