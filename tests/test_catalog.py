import pytest

from quincaillerie import CELLS, METRIC, resolve
from quincaillerie.catalog import asset_name


def test_names():
    assert asset_name("screw", "M8", 30) == "ISO4017_M8x30"
    assert asset_name("nut", "M8") == "ISO4032_M8"
    assert asset_name("washer", "M10") == "ISO7089_M10"
    assert asset_name("holder", "18650") == "Holder_18650"


def test_metric_table_is_consistent():
    for s, t in METRIC.items():
        assert s == f"M{t['d']:g}"
        assert t["s"] > t["d"] and t["k"] < t["d"] and 0.6 * t["d"] < t["m"] < t["d"]
        d1, d2, h = t["washer"]
        assert t["d"] < d1 < d2 and h > 0


def test_cells_have_what_their_holder_needs():
    for c in CELLS.values():
        need = {"cradle": ("d", "L", "nub_d", "nub_h", "pre"), "nine_volt": ("W", "T", "L", "pre"), "coin": ("d", "h")}
        assert all(k in c for k in need[c["kind"]] + ("mass", "F", "volts", "iec"))


def test_resolve_with_related():
    parts = resolve("screw", "M6", 25, ["nut", "washer"])
    assert [p.name for p in parts] == ["ISO4017_M6x25", "ISO4032_M6", "ISO7089_M6"]
    assert [p.filename.split(".")[-1] for p in parts] == ["usdc", "usdc", "usda"]
    assert [p.name for p in resolve("holder", "9V", with_=["cell"])] == ["Holder_9V", "Cell_9V"]


@pytest.mark.parametrize(
    "args", [("screw", "M7"), ("cell", "AAAA"), ("screw", "M8", None, ["holder"]), ("bolt", "M8"), ("screw", "M8", 0.5)]
)
def test_resolve_rejects(args):
    with pytest.raises(ValueError):
        resolve(*args)
