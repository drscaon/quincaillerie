"""Thread play from the public fit classes of ISO metric threads: 6g screws in 6H nuts.

The usual commercial fit is a 6g screw in a 6H nut. Its limits come from a few public formulas
(ISO 965-1, also printed in engineering handbooks), computed here instead of copying the tables
of the standard; the tables are these values rounded to preferred numbers, a few micrometres away.

* Position g (screw): the whole thread sits below the basic profile by ``-(15 + 11 P)`` µm.
* Position H (nut): no allowance, the thread starts at the basic profile.
* Grade 6, pitch diameter of the screw: ``Td2 = 90 P^0.4 d^0.1`` µm, with d the geometric mean of
  the diameter step the size falls in; of the nut: ``TD2 = 1.32 Td2``.

P and d in millimetres. A pitch diameter that is off by x moves each flank by x / 2 measured on
the radius, which is what the generator calls the clearance (radial, per side).
"""

from __future__ import annotations

import math

SCREW_CLASS = "6g"
NUT_CLASS = "6H"
# diameter steps of the tolerance system (mm): the formulas use each step's geometric mean
DIAMETER_STEPS = ((0.99, 1.4), (1.4, 2.8), (2.8, 5.6), (5.6, 11.2), (11.2, 22.4), (22.4, 45.0))
# The collision pieces need some room to slide: no part is generated tighter than this (mm on the
# radius, per part). It bites at the tight end of both bands: a real 6H nut may have no play of
# its own at all, and the tightest 6g screw has 10 to 17 µm.
SIM_FLOOR_MM = 0.015


def _step_mean(d_mm: float) -> float:
    for lo, hi in DIAMETER_STEPS:
        if lo < d_mm <= hi:
            return math.sqrt(lo * hi)
    raise ValueError(f"no tolerance step for a diameter of {d_mm} mm")


def allowance_g_mm(pitch_mm: float) -> float:
    """How far below the basic profile a 'g' thread starts, on the diameter (mm, positive)."""
    return (15.0 + 11.0 * pitch_mm) / 1000.0


def screw_band_mm(pitch_mm: float, d_mm: float) -> float:
    """Width of the pitch diameter band of a grade 6 screw (mm)."""
    return 90.0 * pitch_mm**0.4 * _step_mean(d_mm) ** 0.1 / 1000.0


def nut_band_mm(pitch_mm: float, d_mm: float) -> float:
    """Width of the pitch diameter band of a grade 6 nut (mm)."""
    return 1.32 * screw_band_mm(pitch_mm, d_mm)


def clearance_range_mm(kind: str, pitch_mm: float, d_mm: float) -> tuple[float, float]:
    """Radial clearance per side of a 6g screw or a 6H nut: (tightest, loosest), in mm."""
    if kind == "screw":
        lo = allowance_g_mm(pitch_mm) / 2
        hi = lo + screw_band_mm(pitch_mm, d_mm) / 2
    elif kind == "nut":
        lo, hi = 0.0, nut_band_mm(pitch_mm, d_mm) / 2
    else:
        raise ValueError(f"no thread on a {kind}")
    return max(lo, SIM_FLOOR_MM), hi


def clearance_mm(kind: str, pitch_mm: float, d_mm: float, u: float) -> float:
    """The clearance at the fraction u (0 tightest, 1 loosest) of the tolerance band."""
    lo, hi = clearance_range_mm(kind, pitch_mm, d_mm)
    return lo + u * (hi - lo)
