"""The sampler draws what docs/variation.md declares (PRV-34).

For each part, thousands of instances are drawn with fixed seeds, so the result is the same on every
run. Every column must be declared, every value must lie in its declared support, and the values
must follow the declared distribution: a Kolmogorov-Smirnov test for numbers, a chi-square test for
choices, both at p > 0.001. Declared in quincaillerie.declared, which also writes the documentation.
"""

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from quincaillerie import declared, fits
from quincaillerie.variation import DENSITY, STEEL_DENSITY, Sampler, tolerance_range

N = 4000
P_MIN = 1e-3
PITCH, DIAMETER, FINISH = 1.25, 8.0, "zinc_clear"  # an M8 part in a plated steel finish
SIZE = {"cell (cylinder)": "AA", "cell (coin)": "CR2032"}  # the format each cell part is drawn in
DOC = Path(__file__).parents[1] / "docs" / "variation.md"


def draws(part):
    """N variations of the part, as {column: values}."""
    sampler = Sampler(seed=20261116, defect_rate=declared.RATE)
    if part in ("screw", "bolt", "nut", "washer"):
        rows = [asdict(sampler.fastener(part, FINISH, PITCH, DIAMETER)) for _ in range(N)]
    elif part.startswith("cell"):
        kind = "coin" if "coin" in part else "cradle"
        rows = [asdict(sampler.cell(SIZE[part], kind)) for _ in range(N)]
    else:
        rows = [asdict(sampler.holder("AA", "cradle")) for _ in range(N)]
    # a value the part does not have is None, and is not recorded (variation.as_attrs)
    return {key: np.array([row[key] for row in rows], dtype=object) for key in rows[0]}


def cdf(dist, x, left=False):
    """The cumulative distribution of a declared distribution at x (just below x when left)."""
    kind, *args = dist
    if kind == "constant":
        return np.where(x > args[0], 1.0, 0.0) if left else np.where(x >= args[0], 1.0, 0.0)
    if kind == "uniform":
        return stats.uniform(args[0], args[1] - args[0]).cdf(x)
    if kind == "normal":
        return stats.norm(*args).cdf(x)
    if kind == "beta":
        return stats.beta(*args).cdf(x)
    if kind == "mix":
        return sum(p * cdf(d, x, left) for p, d in args[0])
    raise ValueError(f"no distribution function for {kind!r}")


def ks(values, dist):
    """Kolmogorov-Smirnov p-value of the values against a distribution that may have atoms."""
    x = np.sort(values)
    n = len(x)
    above = np.arange(1, n + 1) / n - cdf(dist, x)
    below = cdf(dist, x, left=True) - np.arange(n) / n
    return stats.kstwo.sf(max(above.max(), below.max()), n)


def support(dist):
    kind, *args = dist
    if kind in ("uniform", "integers"):
        return args[0], args[1]
    if kind in ("clipped", "bounded"):
        return args[-2] if kind == "clipped" else args[0], args[-1] if kind == "clipped" else args[1]
    if kind == "constant":
        return args[0], args[0]
    if kind == "mix":
        ends = [support(d) for _, d in args[0]]
        return min(e[0] for e in ends), max(e[1] for e in ends)
    if kind == "beta":
        return 0.0, 1.0
    return -np.inf, np.inf


def check(column, dist, values, others):
    kind = dist[0]
    if kind == "choice":
        observed = np.array([np.sum(values == v) for v in dist[1]])
        assert observed.sum() == len(values), f"{column}: a value outside {sorted(dist[1])}"
        expected = np.array(list(dist[1].values())) * len(values)
        counts = dict(zip(dist[1], observed, strict=True))
        assert stats.chisquare(observed, expected).pvalue > P_MIN, f"{column}: {counts}"
        return
    if kind == "constant" and isinstance(dist[1], str):
        assert set(values) == {dist[1]}, column
        return
    if kind == "by":
        for value, sub in dist[2].items():
            check(f"{column} ({value})", sub, values[others[dist[1]] == value], others)
        return
    if kind == "band":
        lo, hi = fits.clearance_range_mm(others["kind"], PITCH, DIAMETER)
        check(column, ("uniform", 0.0, 1.0), (values - lo) / (hi - lo), others)
        return
    if kind == "cited":
        part = others["kind"]
        lo, hi = tolerance_range(part, column, "M8" if part in ("screw", "bolt", "nut", "washer") else SIZE[part])
        check(column, ("uniform", 0.0, 1.0), (values - lo) / (hi - lo), others)
        return
    if kind == "relative":
        check(column, dist[1], values / DENSITY.get(FINISH, STEEL_DENSITY), others)
        return
    lo, hi = support(dist)
    assert values.min() >= lo - 1e-12 and values.max() <= hi + 1e-12, f"{column}: outside {lo} to {hi}"
    if kind == "integers":
        assert len(set(values)) > 0.99 * len(values), f"{column}: repeated values"
    elif kind == "clipped":
        _, mean, sd, low, high = dist
        inner = values[(values > low) & (values < high)]
        assert stats.kstest(inner, stats.truncnorm((low - mean) / sd, (high - mean) / sd, mean, sd).cdf).pvalue > P_MIN
    elif kind != "bounded":
        assert ks(values, dist) > P_MIN, f"{column}: does not follow {declared.describe(dist)}"


@pytest.mark.parametrize("part", list(declared.DECLARED))
def test_drawn_as_declared(part):
    columns = draws(part)
    rows = declared.DECLARED[part]
    names = {row[0] for row in rows}
    recorded = {k for k, v in columns.items() if any(x is not None for x in v)}
    undeclared = sorted(recorded - names)
    assert not undeclared, f"{part}: drawn but not declared: {undeclared}"
    defective = columns["defect"] != "none" if "defect" in columns else np.ones(N, bool)
    for column, _aspect, dist, when in rows:
        keep = {"": np.ones(N, bool), "defect": defective}.get(when)
        keep = np.isin(columns["defect"].astype(str), when.split("|")) if keep is None else keep
        others = {**{k: v[keep] for k, v in columns.items()}, "kind": part}
        values = columns[column][keep]
        assert all(x is not None for x in values), f"{part}: {column} is not recorded where it is declared"
        values = values.astype(str) if isinstance(values[0], str) else values.astype(float)
        check(column, dist, values, others)


def test_documentation_is_the_declaration():
    text = DOC.read_text(encoding="utf-8")
    begin, end = "<!-- declared: begin -->\n", "<!-- declared: end -->"
    assert begin in text and end in text, "docs/variation.md has lost its markers"
    block = text[text.index(begin) + len(begin) : text.index(end)].strip()
    assert block == declared.table().strip(), "docs/variation.md is out of date: python -m quincaillerie.declared"
