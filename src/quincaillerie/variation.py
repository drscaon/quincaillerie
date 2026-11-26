"""Variation: every generated instance draws its own tolerances, defects, wear and physics.

A real box of M8 screws is not one screw a hundred times: threads fit tighter or looser within their
tolerance class, a few are damaged, some are rusty or oily, springs lose preload. Policies trained
on one perfect part break on real ones; perception models need the whole range. Each instance draws
from four independent aspects (one random stream each: turning one off leaves the others as they
were):

* tolerance: thread clearance (radial, per side) within the 6g band for screws and the 6H band for nuts
  (see ``fits.py``), across flats, head and nut heights, under the head of a screw or bolt its bearing
  face and fillet, a bolt's plain shank (its diameter, and where the thread starts),
  screw length, cell diameter and length within their tolerance bands, holder slot play;
* defect (with probability ``defect_rate``): crushed thread crests that jam a nut, bent shank, burr
  at the tip; out-of-round or crushed nut thread; dished washer; dented cell can, corroded terminal;
* wear: rust, oil, dirt and scratches (baked into per-instance textures), scuffed or faded labels;
  friction follows (rust raises it, oil lowers it);
* physics: density of the alloy (brass and stainless finishes are solid alloys, the others plated
  steel), spring stiffness and preload loss (fatigue), clip torque, cell mass.

Everything drawn is written into the asset (``primvaria:variation:*`` attributes) and into
``instances.csv``: the ground truth of each instance.
"""

from __future__ import annotations

import zlib
from dataclasses import asdict, dataclass, field

import numpy as np

from . import fits
from .catalog import (
    BOLT,
    CAP_SCREW,
    CELL_MIN,
    CELLS,
    DEFAULT_BOLT_LENGTH,
    DEFAULT_LENGTH,
    METRIC,
    THREADED,
    TOLERANCES,
    UNDER_HEAD,
    fillet_range,
    has_plain_shank,
    length_tolerance,
    plain_range,
    socket_s_max,
)

ASPECTS = ("tolerance", "defect", "wear", "physics")
# How the clearance of a thread is chosen when tolerances vary. The draw is made in every case, so
# the other values of an instance are the same whatever the choice.
#   class:  drawn across the fit class (6g screw, 6H nut), see fits.py;
#   middle: the middle of the fit class for every instance: the same play whatever the seed;
#   legacy: drawn between 1.6 and 8 % of the pitch, as before the fit classes (same seed, same value).
THREAD_PLAY = ("class", "middle", "legacy")

# density (kg/m3) by finish: the coatings are on steel, brass and stainless are solid alloys
DENSITY = {"brass": 8500.0, "stainless_a2": 7930.0}
STEEL_DENSITY = 7850.0
# dry friction of the bare finish, before wear
FRICTION = {
    "zinc_clear": 0.15,
    "zinc_yellow": 0.16,
    "black_oxide": 0.13,
    "stainless_a2": 0.20,
    "steel_plain": 0.17,
    "brass": 0.18,
}


def tolerance_range(
    kind: str, column: str, key: str, length_mm: float | None = None, property_class: str | None = None
) -> tuple[float, float]:
    """(lowest, highest) change from the nominal size (mm) that the cited tolerance allows, for a
    column of a part of that size (M8) or format (AA): see TOLERANCES and CELL_MIN in catalog.py,
    and their sources in docs/sources.md. Under the head and along a plain shank, the sizes
    themselves (mm), not changes."""
    if kind == "cap_screw":
        c, m = CAP_SCREW[key], METRIC[key]
        if column == "across_flats_dmm":  # the hex socket, around its nominal size
            return c["s"][0] - c["socket"], socket_s_max(key, property_class or "12.9") - c["socket"]
        if column == "height_dmm":  # k max is d, the nominal height
            return c["k"][0] - c["k"][1], 0.0
        if column == "length_dmm":
            tol = length_tolerance(length_mm or DEFAULT_LENGTH[key])
            return -tol, tol
        if column == "head_d_mm":
            return c["dk"]
        if column == "socket_depth_mm":  # from t min to the deepest that leaves the wall w min under it
            return c["t_min"], c["k"][0] - c["w_min"]
        if column == "top_chamfer_mm":
            return 0.0, c["v_max"]
        if column == "bearing_face_d_mm":  # the bearing circle under the head, inside its edge
            return c["dw_min"], c["dk"][0]
        if column == "fillet_r_mm":
            return fillet_range(key)
        if column == "shank_d_mm":
            return c["ds_min"], m["d"]
        if column == "plain_length_mm":
            return plain_range(key, length_mm or DEFAULT_LENGTH[key], "cap_screw")
    if kind in ("screw", "bolt", "nut", "washer"):
        t, m = TOLERANCES[key], METRIC[key]
        if kind in THREADED and column in UNDER_HEAD_COLUMNS:  # absolute values (mm), not changes
            u = UNDER_HEAD[key]
            if column == "bearing_face_d_mm":
                return u["dw_min"], t["s_min"]
            if column == "bearing_face_h_mm":
                return u["c"]
            return fillet_range(key)
        if kind == "bolt" and column == "shank_d_mm":
            return BOLT[key]["ds_min"], m["d"]
        if kind == "bolt" and column == "plain_length_mm":
            return plain_range(key, length_mm or DEFAULT_BOLT_LENGTH[key])
        if column == "across_flats_dmm":
            return t["s_min"] - m["s"], 0.0
        if column == "height_dmm":
            if kind in THREADED:
                return t["k_min"] - m["k"], t["k_max"] - m["k"]
            if kind == "nut":
                return t["m_min"] - m["m"], 0.0
            return t["washer_h"][0] - m["washer"][2], t["washer_h"][1] - m["washer"][2]
        if column == "length_dmm":
            default = DEFAULT_BOLT_LENGTH if kind == "bolt" else DEFAULT_LENGTH
            tol = length_tolerance(length_mm or default[key])
            return -tol, tol
    else:
        c, low = CELLS[key], CELL_MIN[key]
        if column == "diameter_dmm":  # the width and the thickness of a 9 V battery: the same tolerance
            return (low["W_min"] - c["W"], 0.0) if c["kind"] == "nine_volt" else (low["d_min"] - c["d"], 0.0)
        if column == "length_dmm":
            return (low["h_min"] - c["h"], 0.0) if c["kind"] == "coin" else (low["L_min"] - c["L"], 0.0)
    raise ValueError(f"no cited tolerance for {column} of a {kind}")


# drawn under the head of a screw or a bolt, from a stream of their own (so that the draws above
# stay as they were): absolute sizes in mm, with a bolt's plain shank
UNDER_HEAD_COLUMNS = ("bearing_face_d_mm", "bearing_face_h_mm", "fillet_r_mm")
SHANK_COLUMNS = ("shank_d_mm", "plain_length_mm")
# a cap screw's head (ISO 4762): its diameter, the socket's depth, the top edge's chamfer, and under
# it the bearing circle and the fillet
CAP_HEAD_COLUMNS = ("head_d_mm", "socket_depth_mm", "top_chamfer_mm", "bearing_face_d_mm", "fillet_r_mm")


def head_columns(kind: str, size: str, length_mm: float | None) -> tuple:
    """The columns drawn from a threaded part's own stream, in the order they are drawn."""
    if kind == "cap_screw":
        length = length_mm or DEFAULT_LENGTH[size]
        return CAP_HEAD_COLUMNS + (SHANK_COLUMNS if has_plain_shank(kind, size, length) else ())
    return UNDER_HEAD_COLUMNS + (SHANK_COLUMNS if kind == "bolt" else ())


@dataclass
class FastenerVariation:
    clearance_mm: float = 0.05  # radial clearance of the thread, per side
    thread_class: str = ""  # fit class the clearance was drawn in: 6g (screw), 6H (nut), "" (not drawn)
    across_flats_dmm: float = 0.0  # change of the hex across flats (mm, negative: smaller)
    height_dmm: float = 0.0  # change of head height (screw), nut height or washer thickness (mm)
    length_dmm: float = 0.0  # change of screw length (mm)
    # under the head of a screw or bolt (None: the middle of the cited range, see fasteners.under_head)
    bearing_face_d_mm: float | None = None  # diameter of the bearing face, dw
    bearing_face_h_mm: float | None = None  # its height, c
    fillet_r_mm: float | None = None  # radius of the fillet between head and shank, r
    # a bolt's plain shank (None: the middle of the cited range)
    shank_d_mm: float | None = None  # its diameter, ds
    plain_length_mm: float | None = None  # from the bearing face to where the thread starts
    # a cap screw's head (None: the middle of the cited range)
    head_d_mm: float | None = None  # its diameter, dk
    socket_depth_mm: float | None = None  # the hex socket's depth, t
    top_chamfer_mm: float | None = None  # the chamfer of the head's top edge, v
    defect: str = "none"  # none | crushed_thread | bent | burr | oval | dished
    defect_z: float = 0.0  # where along the part (0..1)
    defect_angle_deg: float = 0.0  # angular extent of crushed threads
    defect_size: float = 0.0  # crush depth as a fraction of the pitch, bend angle (deg), ovality (mm), dish (mm)
    rust: float = 0.0  # 0..1 surface covered
    oil: float = 0.0  # 0..1
    dirt: float = 0.0  # 0..1
    scratches: float = 0.0  # 0..1
    density: float = STEEL_DENSITY
    friction: float = 0.15
    seed: int = 0  # texture seed

    def worn(self):
        return max(self.rust, self.oil, self.dirt, self.scratches) > 0.02


@dataclass
class CellVariation:
    diameter_dmm: float = 0.0
    length_dmm: float = 0.0
    mass_factor: float = 1.0
    defect: str = "none"  # none | dent | corroded_terminal
    defect_angle_deg: float = 0.0
    defect_z: float = 0.0
    defect_size: float = 0.0  # dent depth (mm)
    label_wear: float = 0.0  # 0..1 scuffs and fading of the wrapper
    dirt: float = 0.0
    friction: float = 0.3
    seed: int = 0


@dataclass
class HolderVariation:
    spring_factor: float = 1.0  # stiffness relative to the design
    preload_factor: float = 1.0  # remaining preload (fatigue): <1 lowers the contact force
    clip_factor: float = 1.0  # clip torsion stiffness relative to the design
    play_dmm: float = 0.0  # extra side play of the cradle walls (mm)
    friction: float = 0.3
    plastic: str = "abs_black"
    seed: int = 0


@dataclass
class Sampler:
    """Draws variations; one random stream per aspect and kind, so options stay independent."""

    seed: int = 1
    vary: tuple = ASPECTS
    defect_rate: float = 0.15
    thread_play: str = "class"  # how the thread clearance is chosen, see THREAD_PLAY
    _streams: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self.thread_play not in THREAD_PLAY:
            raise ValueError(f"unknown thread play {self.thread_play!r}; expected one of {', '.join(THREAD_PLAY)}")

    def rng(self, aspect, kind):
        key = (aspect, kind)
        if key not in self._streams:
            self._streams[key] = np.random.default_rng([self.seed, ASPECTS.index(aspect), zlib.crc32(kind.encode())])
        return self._streams[key]

    def on(self, aspect):
        return aspect in self.vary

    # ------------------------------------------------------------------ fasteners
    def fastener(self, kind, finish, pitch_mm, diameter_mm=None, length_mm=None, property_class=None):
        """diameter_mm: nominal thread diameter; by default the coarse-pitch size with that pitch.
        length_mm: a screw's nominal length, which sets its length tolerance (default: the size's).
        property_class: a cap screw's (8.8, 10.9 or 12.9; default 12.9): its thread class and the
        limits of its socket."""
        if diameter_mm is None:
            diameter_mm = next(m["d"] for m in METRIC.values() if m["P"] == pitch_mm)
        size = next(key for key, m in METRIC.items() if m["d"] == diameter_mm)

        def within(column, u):  # the fraction u of the size's cited tolerance
            lo, hi = tolerance_range(kind, column, size, length_mm, property_class)
            return float(lo + u * (hi - lo))

        v = FastenerVariation(friction=FRICTION.get(finish, 0.15), density=DENSITY.get(finish, STEEL_DENSITY))
        r = self.rng("tolerance", kind)
        if self.on("tolerance"):
            u = r.uniform(0.0, 1.0)  # where in its tolerance band: 0 tightest, 1 loosest
            if self.thread_play == "legacy":
                v.clearance_mm = float(np.clip((0.016 + 0.064 * u) * pitch_mm, 0.015, 0.10))
            elif kind in (*THREADED, "nut"):  # a 6g (5g6g) screw, a 6H nut (see fits.py)
                u = 0.5 if self.thread_play == "middle" else u
                v.clearance_mm = float(fits.clearance_mm(kind, pitch_mm, diameter_mm, u, property_class))
                v.thread_class = fits.thread_class(kind, property_class)
            # across the size's tolerances, from the standards' tables (catalog.TOLERANCES)
            v.across_flats_dmm = within("across_flats_dmm", r.uniform(0.0, 1.0))
            v.height_dmm = within("height_dmm", r.uniform(0.0, 1.0))
            u = r.uniform(0.0, 1.0)  # drawn for every part: the next draws stay the same
            v.length_dmm = within("length_dmm", u) if kind in THREADED else 0.0
        if kind in THREADED:  # a stream of their own: the draws of the stream above stay the same
            r = self.rng("tolerance", f"{kind}:under_head")
            for column in head_columns(kind, size, length_mm):
                u = r.uniform(0.0, 1.0) if self.on("tolerance") else 0.5
                setattr(v, column, within(column, u))
        r = self.rng("defect", kind)
        if self.on("defect") and r.random() < self.defect_rate:
            choices = {
                "screw": ["crushed_thread", "bent", "burr"],
                "bolt": ["crushed_thread", "bent", "burr"],
                "cap_screw": ["crushed_thread", "bent", "burr"],
                "nut": ["crushed_thread", "oval"],
                "washer": ["dished"],
            }
            v.defect = str(r.choice(choices[kind]))
            v.defect_z = float(r.uniform(0.15, 0.85))
            v.defect_angle_deg = float(r.uniform(40, 140))
            v.defect_size = {
                "crushed_thread": float(r.uniform(0.3, 0.6)),  # of the pitch: crest pushed sideways
                "bent": float(r.uniform(0.8, 3.0)),  # degrees
                "burr": float(r.uniform(0.1, 0.25)),  # mm beyond the major diameter
                "oval": float(r.uniform(0.04, 0.12)),  # mm of ovality
                "dished": float(r.uniform(0.15, 0.5)),  # mm of cone height
            }[v.defect]
            if v.defect in ("bent", "oval", "dished"):  # a bend, an ovality, a dish: no place, no angle
                v.defect_z = v.defect_angle_deg = None
        r = self.rng("wear", kind)
        if self.on("wear"):
            state = r.choice(["new", "used", "oily", "rusty", "dirty"], p=[0.35, 0.25, 0.15, 0.15, 0.10])
            v.seed = int(r.integers(0, 2**31))
            v.scratches = float(r.uniform(0.0, 0.15) if state == "new" else r.uniform(0.2, 0.8))
            if state == "rusty" and finish not in ("stainless_a2", "brass"):
                v.rust = float(r.uniform(0.2, 0.9))
            if state == "oily":
                v.oil = float(r.uniform(0.4, 1.0))
            if state in ("dirty", "used"):
                v.dirt = float(r.uniform(0.2, 0.8) if state == "dirty" else r.uniform(0.0, 0.3))
            v.friction = float(np.clip(v.friction * (1 + 0.8 * v.rust + 0.3 * v.dirt - 0.4 * v.oil), 0.08, 0.45))
        r = self.rng("physics", kind)
        if self.on("physics"):
            v.density = float(v.density * r.normal(1.0, 0.005))
            v.friction = float(np.clip(v.friction * r.normal(1.0, 0.08), 0.06, 0.5))
        # what a part does not have is not recorded (the values are still drawn, so that the
        # other values of the stream stay the same): a nut's length is its height, a washer has
        # no hex, no length and no thread
        if kind == "nut":
            v.length_dmm = None
        elif kind == "washer":
            v.across_flats_dmm = v.length_dmm = v.clearance_mm = v.thread_class = None
            v.defect_z = v.defect_angle_deg = None  # its one defect, a dish, has neither
        return v

    # ------------------------------------------------------------------ cells and holders
    def cell(self, fmt, kind):
        v = CellVariation()
        r = self.rng("tolerance", "cell")
        if self.on("tolerance"):
            # between the datasheet's maximum (the nominal size) and its minimum (catalog.CELL_MIN)
            lo, _ = tolerance_range("cell", "diameter_dmm", fmt)
            v.diameter_dmm = float(lo * r.uniform(0.0, 1.0))
            lo, _ = tolerance_range("cell", "length_dmm", fmt)
            v.length_dmm = float(lo * r.uniform(0.0, 1.0))
        r = self.rng("defect", "cell")
        if self.on("defect") and r.random() < self.defect_rate:
            v.defect = str(r.choice(["dent", "corroded_terminal"] if kind == "cradle" else ["corroded_terminal"]))
            v.defect_angle_deg = float(r.uniform(0, 360))
            v.defect_z = float(r.uniform(0.2, 0.8))
            v.defect_size = float(r.uniform(0.3, 1.0))
            # a dent has a place along the can, an angle and a depth; the corrosion crust sits on
            # a terminal, at its angle on a round cell, with its size: what does not apply is not recorded
            if v.defect == "corroded_terminal":
                v.defect_z = None
        if kind in ("coin", "nine_volt"):  # the crust has its place on these: no place along the cell
            v.defect_z = None
        if kind == "nine_volt":  # nor an angle
            v.defect_angle_deg = None
        r = self.rng("wear", "cell")
        if self.on("wear"):
            v.seed = int(r.integers(0, 2**31))
            v.label_wear = float(r.beta(1.2, 3.0))
            v.dirt = float(r.beta(1.0, 4.0))
        r = self.rng("physics", "cell")
        if self.on("physics"):
            v.mass_factor = float(r.normal(1.0, 0.03))
            v.friction = float(np.clip(r.normal(0.3, 0.04), 0.18, 0.45))
        return v

    def holder(self, fmt, kind):
        v = HolderVariation()
        r = self.rng("tolerance", "holder")
        if self.on("tolerance"):
            v.play_dmm = float(r.uniform(0.0, 0.6))
        r = self.rng("wear", "holder")
        if self.on("wear"):
            v.plastic = str(r.choice(["abs_black", "abs_grey"], p=[0.7, 0.3]))
            v.seed = int(r.integers(0, 2**31))
        r = self.rng("physics", "holder")
        if self.on("physics"):
            v.spring_factor = float(r.normal(1.0, 0.08))
            v.preload_factor = float(r.uniform(0.7, 1.0) if r.random() < 0.3 else r.uniform(0.95, 1.0))
            v.clip_factor = float(r.normal(1.0, 0.1))
            v.friction = float(np.clip(r.normal(0.3, 0.04), 0.18, 0.45))
        return v


def as_attrs(v):
    """Flat {variation:name: value} for the USD attributes and the CSV; a value of None is a value
    the part does not have, and is left out."""
    return {
        f"variation:{k}": (round(x, 6) if isinstance(x, float) else x) for k, x in asdict(v).items() if x is not None
    }
