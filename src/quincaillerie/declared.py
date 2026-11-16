"""What every instance draws, declared once: the table of docs/variation.md is written from it, and
tests/test_distributions.py checks that the sampler (variation.py) follows it.

A distribution is a tuple:

* ("uniform", low, high), ("normal", mean, sd), ("beta", a, b), ("integers", low, high): drawn as named;
* ("clipped", mean, sd, low, high): normal, then kept within [low, high];
* ("constant", value): always that value;
* ("choice", {value: probability}): one of the values;
* ("mix", [(probability, distribution), ...]): one component, chosen with its probability;
* ("by", column, {value: distribution}): depends on the value drawn for another column;
* ("band",): uniform over the thread's tolerance band of fits.py (6g screw, 6H nut);
* ("relative", distribution): the value divided by the finish's nominal density follows it;
* ("bounded", low, high, how): derived from other draws, as said in how, and kept within [low, high].

Each part lists (column, aspect, distribution, when). when is "" or "defect" (only for an instance
that drew a defect, at the rate given by --defect-rate, 0.15 by default). The values are those of
the default options: --thread-play class, every aspect on.
"""

from __future__ import annotations

RATE = 0.15  # default --defect-rate

NONE_SHARE = 1 - RATE
SCRATCHES = ("mix", [(0.35, ("uniform", 0.0, 0.15)), (0.65, ("uniform", 0.2, 0.8))])
WEAR = [
    ("scratches", "wear", SCRATCHES, ""),
    ("rust", "wear", ("mix", [(0.85, ("constant", 0.0)), (0.15, ("uniform", 0.2, 0.9))]), ""),
    ("oil", "wear", ("mix", [(0.85, ("constant", 0.0)), (0.15, ("uniform", 0.4, 1.0))]), ""),
    (
        "dirt",
        "wear",
        ("mix", [(0.65, ("constant", 0.0)), (0.25, ("uniform", 0.0, 0.3)), (0.10, ("uniform", 0.2, 0.8))]),
        "",
    ),
    ("seed", "wear", ("integers", 0, 2**31), ""),
]
FRICTION = (
    "bounded",
    0.06,
    0.5,
    "finish friction × (1 + 0.8 rust + 0.3 dirt − 0.4 oil), kept within 0.08 to 0.45, then × normal(1, 0.08)",
)
DEFECT_PLACE = [
    ("defect_z", "defect", ("uniform", 0.15, 0.85), "defect"),
    ("defect_angle_deg", "defect", ("uniform", 40.0, 140.0), "defect"),
]


def defect(kinds):
    return ("choice", {"none": NONE_SHARE, **{k: RATE / len(kinds) for k in kinds}})


DECLARED = {
    "screw": [
        ("clearance_mm", "tolerance", ("band",), ""),
        ("thread_class", "tolerance", ("constant", "6g"), ""),
        ("across_flats_dmm", "tolerance", ("uniform", -0.25, 0.0), ""),
        ("height_dmm", "tolerance", ("uniform", -0.3, 0.0), ""),
        ("length_dmm", "tolerance", ("uniform", -0.4, 0.4), ""),
        ("defect", "defect", defect(["crushed_thread", "bent", "burr"]), ""),
        *DEFECT_PLACE,
        (
            "defect_size",
            "defect",
            (
                "by",
                "defect",
                {
                    "crushed_thread": ("uniform", 0.3, 0.6),
                    "bent": ("uniform", 0.8, 3.0),
                    "burr": ("uniform", 0.1, 0.25),
                },
            ),
            "defect",
        ),
        *WEAR,
        ("density", "physics", ("relative", ("normal", 1.0, 0.005)), ""),
        ("friction", "wear, physics", FRICTION, ""),
    ],
    "nut": [
        ("clearance_mm", "tolerance", ("band",), ""),
        ("thread_class", "tolerance", ("constant", "6H"), ""),
        ("across_flats_dmm", "tolerance", ("uniform", -0.25, 0.0), ""),
        ("height_dmm", "tolerance", ("uniform", -0.3, 0.0), ""),
        ("length_dmm", "tolerance", ("uniform", -0.4, 0.4), ""),
        ("defect", "defect", defect(["crushed_thread", "oval"]), ""),
        *DEFECT_PLACE,
        (
            "defect_size",
            "defect",
            ("by", "defect", {"crushed_thread": ("uniform", 0.3, 0.6), "oval": ("uniform", 0.04, 0.12)}),
            "defect",
        ),
        *WEAR,
        ("density", "physics", ("relative", ("normal", 1.0, 0.005)), ""),
        ("friction", "wear, physics", FRICTION, ""),
    ],
    "washer": [
        ("clearance_mm", "tolerance", ("constant", 0.05), ""),
        ("thread_class", "tolerance", ("constant", ""), ""),
        ("across_flats_dmm", "tolerance", ("uniform", -0.25, 0.0), ""),
        ("height_dmm", "tolerance", ("uniform", -0.3, 0.0), ""),
        ("length_dmm", "tolerance", ("uniform", -0.4, 0.4), ""),
        ("defect", "defect", defect(["dished"]), ""),
        *DEFECT_PLACE,
        ("defect_size", "defect", ("uniform", 0.15, 0.5), "defect"),
        *WEAR,
        ("density", "physics", ("relative", ("normal", 1.0, 0.005)), ""),
        ("friction", "wear, physics", FRICTION, ""),
    ],
    "cell (cylinder)": [
        ("diameter_dmm", "tolerance", ("uniform", -0.5, 0.0), ""),
        ("length_dmm", "tolerance", ("uniform", -0.8, 0.0), ""),
        ("defect", "defect", ("choice", {"none": NONE_SHARE, "dent": RATE / 2, "corroded_terminal": RATE / 2}), ""),
        ("defect_angle_deg", "defect", ("uniform", 0.0, 360.0), "defect"),
        ("defect_z", "defect", ("uniform", 0.2, 0.8), "defect"),
        ("defect_size", "defect", ("uniform", 0.3, 1.0), "defect"),
        ("label_wear", "wear", ("beta", 1.2, 3.0), ""),
        ("dirt", "wear", ("beta", 1.0, 4.0), ""),
        ("seed", "wear", ("integers", 0, 2**31), ""),
        ("mass_factor", "physics", ("normal", 1.0, 0.03), ""),
        ("friction", "physics", ("clipped", 0.3, 0.04, 0.18, 0.45), ""),
    ],
    "cell (coin)": [
        ("diameter_dmm", "tolerance", ("uniform", -0.3, 0.0), ""),
        ("length_dmm", "tolerance", ("uniform", -0.2, 0.0), ""),
        ("defect", "defect", ("choice", {"none": NONE_SHARE, "corroded_terminal": RATE}), ""),
        ("defect_angle_deg", "defect", ("uniform", 0.0, 360.0), "defect"),
        ("defect_z", "defect", ("uniform", 0.2, 0.8), "defect"),
        ("defect_size", "defect", ("uniform", 0.3, 1.0), "defect"),
        ("label_wear", "wear", ("beta", 1.2, 3.0), ""),
        ("dirt", "wear", ("beta", 1.0, 4.0), ""),
        ("seed", "wear", ("integers", 0, 2**31), ""),
        ("mass_factor", "physics", ("normal", 1.0, 0.03), ""),
        ("friction", "physics", ("clipped", 0.3, 0.04, 0.18, 0.45), ""),
    ],
    "holder": [
        ("play_dmm", "tolerance", ("uniform", 0.0, 0.6), ""),
        ("plastic", "wear", ("choice", {"abs_black": 0.7, "abs_grey": 0.3}), ""),
        ("seed", "wear", ("integers", 0, 2**31), ""),
        ("spring_factor", "physics", ("normal", 1.0, 0.08), ""),
        ("preload_factor", "physics", ("mix", [(0.3, ("uniform", 0.7, 1.0)), (0.7, ("uniform", 0.95, 1.0))]), ""),
        ("clip_factor", "physics", ("normal", 1.0, 0.1), ""),
        ("friction", "physics", ("clipped", 0.3, 0.04, 0.18, 0.45), ""),
    ],
}


# Recorded values that do not change the part as recorded, found while writing this declaration
# (16 November 2026). Listed on the page so that the ground truth does not claim more than the part.
NOT_APPLIED = {
    ("nut", "length_dmm"): "recorded, not applied: a nut has no length",
    ("washer", "across_flats_dmm"): "recorded, not applied: a washer has no hex",
    ("washer", "length_dmm"): "recorded, not applied: a washer has no length",
    ("washer", "height_dmm"): "applied at 0.3 times the recorded value",
    ("cell (cylinder)", "defect_z"): "applied to a dent only, and to the visual mesh only",
    ("cell (cylinder)", "defect_angle_deg"): "applied to a dent only, and to the visual mesh only",
    ("cell (cylinder)", "defect_size"): "applied to a dent only, and to the visual mesh only",
    ("cell (coin)", "defect_z"): "recorded, not applied: the crust sits at the seal",
    ("cell (coin)", "defect_size"): "recorded, not applied: the crust has a fixed size",
}


def _num(x) -> str:
    return f"{x:g}" if isinstance(x, float) else str(x)


def _pct(p: float) -> str:
    return f"{round(p * 100, 2):g} %"


def describe(dist) -> str:
    """A distribution in words, for the documentation."""
    kind, *args = dist
    if kind == "uniform":
        return f"uniform, {_num(args[0])} to {_num(args[1])}"
    if kind == "normal":
        return f"normal, mean {_num(args[0])}, sd {_num(args[1])}"
    if kind == "beta":
        return f"beta({_num(args[0])}, {_num(args[1])})"
    if kind == "integers":
        return "integer, 0 to 2³¹ − 1" if args == [0, 2**31] else f"integer, {args[0]} to {args[1] - 1}"
    if kind == "clipped":
        return f"normal, mean {_num(args[0])}, sd {_num(args[1])}, kept within {_num(args[2])} to {_num(args[3])}"
    if kind == "constant":
        return f"always `{_num(args[0])}`"
    if kind == "choice":
        return "; ".join(f"`{v}` {_pct(p)}" for v, p in args[0].items())
    if kind == "mix":
        return "; ".join(f"{_pct(p)}: {describe(d)}" for p, d in args[0])
    if kind == "by":
        return "; ".join(f"`{v}`: {describe(d)}" for v, d in args[1].items())
    if kind == "band":
        return "uniform over the tolerance band of the fit class (`fits.py`)"
    if kind == "relative":
        return "divided by the finish's density: " + describe(args[0])
    if kind == "bounded":
        return f"{args[2]}; always within {_num(args[0])} to {_num(args[1])}"
    raise ValueError(f"unknown distribution {kind!r}")


def table() -> str:
    """The Markdown tables of docs/variation.md, one per part."""
    out = []
    for part, rows in DECLARED.items():
        out += [f"### {part}", "", "| Column | Aspect | Drawn as |", "|---|---|---|"]
        for column, aspect, dist, when in rows:
            note = " (instances with a defect)" if when == "defect" else ""
            if (part, column) in NOT_APPLIED:
                note += f". **{NOT_APPLIED[part, column]}**"
            out.append(f"| `variation:{column}` | {aspect} | {describe(dist)}{note} |")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    print(table())
