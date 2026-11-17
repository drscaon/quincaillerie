"""Every physical value names its source, and lies in the range its source gives (PRV-33).

docs/sources.md is written from quincaillerie.sources; this test fails on a value of the catalogue
with no source, on a source that is neither cited nor an explained estimate, on a value outside the
range its source gives, and on an instance drawn outside it.
"""

import numbers
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from quincaillerie import batteries, sources, variation
from quincaillerie.catalog import CELL_MIN, CELLS, DEFAULT_LENGTH, LENGTH_TOLERANCE, LENGTHS, METRIC, TOLERANCES
from quincaillerie.variation import Sampler

DOC = Path(__file__).parents[1] / "docs" / "sources.md"
BY_PATH = {v.path: v for v in sources.values()}


def _leaves(name, table):
    """The paths of every number in a table, as sources.values() names them."""
    for key, entry in table.items():
        for field, x in entry.items():
            if field == "washer":
                yield from (f"{name}.{key}.washer.{n}" for n in ("d1", "d2", "h"))
            elif field == "washer_h":
                yield from (f"{name}.{key}.washer_h.{n}" for n in ("min", "max"))
            elif isinstance(x, numbers.Number) and not isinstance(x, bool):
                yield f"{name}.{key}.{field}"


def test_every_number_of_the_catalogue_names_its_source():
    expected = [
        *_leaves("METRIC", METRIC),
        *_leaves("TOLERANCES", TOLERANCES),
        *_leaves("CELLS", CELLS),
        *_leaves("CELL_MIN", CELL_MIN),
        *(f"LENGTHS.{length}" for length in LENGTHS),
        *(f"LENGTH_TOLERANCE.{longest}" for longest, _ in LENGTH_TOLERANCE),
        "variation.STEEL_DENSITY",
        *(f"variation.DENSITY.{k}" for k in variation.DENSITY),
        *(f"variation.FRICTION.{k}" for k in variation.FRICTION),
        "batteries.G_STEEL",
        "batteries.ABS_DENSITY",
        "batteries.FRICTION",
    ]
    missing = [path for path in expected if path not in BY_PATH]
    assert not missing, f"no source for {missing}"


def test_values_are_the_code_values():
    assert BY_PATH["batteries.G_STEEL"].value == batteries.G_STEEL / 1e9
    for size, m in METRIC.items():
        assert BY_PATH[f"METRIC.{size}.s"].value == m["s"]
    for fmt, c in CELLS.items():
        assert BY_PATH[f"CELLS.{fmt}.mass"].value == c["mass"]


@pytest.mark.parametrize("key", list(sources.SOURCES))
def test_a_source_is_cited_or_an_explained_estimate(key):
    s = sources.SOURCES[key]
    assert s.kind in sources.KINDS
    if s.kind == "estimate":
        assert s.note, f"{key}: an estimate says what it rests on"
    else:
        assert s.urls and all(u.startswith("https://") for u in s.urls), f"{key}: where to read it"


def test_every_value_lies_in_the_range_its_source_gives():
    for v in sources.values():
        assert v.source in sources.SOURCES, v.path
        if v.low is not None:
            assert v.value >= v.low - 1e-9, v.path
        if v.high is not None:
            assert v.value <= v.high + 1e-9, v.path


def _range(path):
    v = BY_PATH[path]
    return v.low, v.high


@pytest.mark.parametrize("size", list(METRIC))
def test_drawn_fasteners_stay_within_their_standard(size):
    """Head height, across flats, nut height, washer thickness and length, as instances get them."""
    m = METRIC[size]
    sampler = Sampler(seed=7)
    for kind in ("screw", "nut", "washer"):
        rows = [asdict(sampler.fastener(kind, "zinc_clear", m["P"], m["d"])) for _ in range(500)]
        heights = np.array([r["height_dmm"] for r in rows])
        nominal, path = {"screw": (m["k"], "k"), "nut": (m["m"], "m"), "washer": (m["washer"][2], "washer.h")}[kind]
        lo, hi = _range(f"METRIC.{size}.{path}")
        assert lo - 1e-9 <= (nominal + heights).min() and (nominal + heights).max() <= hi + 1e-9, (kind, size)
        if kind != "washer":
            flats = m["s"] + np.array([r["across_flats_dmm"] for r in rows])
            lo, hi = _range(f"METRIC.{size}.s")
            assert lo - 1e-9 <= flats.min() and flats.max() <= hi + 1e-9, (kind, size)
        if kind == "screw":  # the default length's tolerance, from the table of the standard
            longest = min(n for n, _ in LENGTH_TOLERANCE if n >= DEFAULT_LENGTH[size])
            tol = BY_PATH[f"LENGTH_TOLERANCE.{longest}"].value
            assert np.abs([r["length_dmm"] for r in rows]).max() <= tol + 1e-9, size


@pytest.mark.parametrize("fmt", list(CELLS))
def test_drawn_cells_stay_within_their_datasheet(fmt):
    c = CELLS[fmt]
    sampler = Sampler(seed=7)
    rows = [asdict(sampler.cell(fmt, c["kind"])) for _ in range(500)]
    width = "W" if c["kind"] == "nine_volt" else "d"
    length = "h" if c["kind"] == "coin" else "L"
    for column, dim in (("diameter_dmm", width), ("length_dmm", length)):
        drawn = c[dim] + np.array([r[column] for r in rows])
        lo, hi = _range(f"CELLS.{fmt}.{dim}")
        assert lo - 1e-9 <= drawn.min() and drawn.max() <= hi + 1e-9, (fmt, dim)
    if c["kind"] == "nine_volt":  # its thickness takes the same change as its width
        drawn = c["T"] + np.array([r["diameter_dmm"] for r in rows])
        lo, hi = _range(f"CELLS.{fmt}.T")
        assert lo - 1e-9 <= drawn.min() and drawn.max() <= hi + 1e-9


def test_documentation_is_the_sources():
    text = DOC.read_text(encoding="utf-8")
    start, end = "<!-- sources: begin -->\n", "<!-- sources: end -->"
    assert start in text and end in text
    written = text[text.index(start) + len(start) : text.index(end)]
    assert written.strip() == sources.table().strip(), "docs/sources.md: run python -m quincaillerie.sources"
