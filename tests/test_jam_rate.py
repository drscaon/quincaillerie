"""The defect rate -> jam rate curve of docs/jam-rate.md."""

import json
from pathlib import Path

from quincaillerie.variation import Sampler

RATES = (0.0, 0.15, 0.25, 0.5, 0.75, 1.0)
DATA = Path(__file__).parent.parent / "docs" / "jam_experiment.json"


def _crushed_share(rate, n=3000):
    s = Sampler(seed=5, defect_rate=rate)
    return sum(s.fastener("screw", "zinc_clear", 1.0, 6.0).defect == "crushed_thread" for _ in range(n)) / n


def test_share_of_jamming_screws_grows_with_the_defect_rate():
    shares = [_crushed_share(r) for r in RATES]
    assert shares[0] == 0.0
    assert all(a < b for a, b in zip(shares, shares[1:], strict=False)), shares
    for rate, share in zip(RATES, shares, strict=True):
        assert abs(share - rate / 3) < 0.03, (rate, share)


def test_stored_experiment_says_what_the_page_says():
    """Only crushed threads jam; every one of them does; sound, bent and burred screws let the nut run."""
    screws = json.loads(DATA.read_text())["screws"]
    by = {}
    for s in screws:
        by.setdefault(s["defect"], []).append(s)
    assert set(by) == {"none", "crushed_thread", "bent", "burr"}
    assert len(by["crushed_thread"]) >= 10 and all(s["stopped"] for s in by["crushed_thread"])
    for s in by["crushed_thread"]:
        assert s["travel_mm"] < s["sound_travel_mm"] - 0.25
    free = min(s["travel_mm"] for s in by["none"])
    assert free > 9.0 and min(s["travel_mm"] for s in by["bent"]) > 9.0
    assert max(s["travel_mm"] for s in by["burr"]) < free  # held short of the tip
    assert min(s["travel_mm"] for s in by["burr"]) > 7.5  # but far past any crushed thread
