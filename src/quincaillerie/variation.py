"""Variation: every generated instance draws its own tolerances, defects, wear and physics.

A real box of M8 screws is not one screw a hundred times: threads fit tighter or looser within their
tolerance class, a few are damaged, some are rusty or oily, springs lose preload. Policies trained
on one perfect part break on real ones; perception models need the whole range. Each instance draws
from four independent aspects (one random stream each: turning one off leaves the others as they
were):

* tolerance: thread clearance (radial, per side, 1.6 to 8 % of the pitch), across flats, head and nut heights,
  screw length, cell diameter and length within their tolerance bands, holder slot play;
* defect (with probability ``defect_rate``): crushed thread crests that jam a nut, bent shank, burr
  at the tip; out-of-round or crushed nut thread; dished washer; dented cell can, corroded terminal;
* wear: rust, oil, dirt and scratches (baked into per-instance textures), scuffed or faded labels;
  friction follows (rust raises it, oil lowers it);
* physics: density of the alloy (brass and stainless finishes are solid alloys, the others plated
  steel), spring stiffness and preload loss (fatigue), clip torque, cell mass.

Everything drawn is written into the asset (``quincaillerie:variation:*`` attributes) and into
``parts.csv``: the ground truth of each instance.
"""

from __future__ import annotations

import zlib
from dataclasses import asdict, dataclass, field

import numpy as np

ASPECTS = ("tolerance", "defect", "wear", "physics")

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


@dataclass
class FastenerVariation:
    clearance_mm: float = 0.05  # radial clearance of the thread, per side
    across_flats_dmm: float = 0.0  # change of the hex across flats (mm, negative: smaller)
    height_dmm: float = 0.0  # change of head height (screw), nut height or washer thickness (mm)
    length_dmm: float = 0.0  # change of screw length (mm)
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
    _streams: dict = field(default_factory=dict, repr=False)

    def rng(self, aspect, kind):
        key = (aspect, kind)
        if key not in self._streams:
            self._streams[key] = np.random.default_rng([self.seed, ASPECTS.index(aspect), zlib.crc32(kind.encode())])
        return self._streams[key]

    def on(self, aspect):
        return aspect in self.vary

    # ------------------------------------------------------------------ fasteners
    def fastener(self, kind, finish, pitch_mm):
        v = FastenerVariation(friction=FRICTION.get(finish, 0.15), density=DENSITY.get(finish, STEEL_DENSITY))
        r = self.rng("tolerance", kind)
        if self.on("tolerance"):
            # from a tight fit to a loose one; ISO fit deviations grow with the pitch (0.02-0.10 mm at M8)
            v.clearance_mm = float(np.clip(r.uniform(0.016, 0.08) * pitch_mm, 0.015, 0.10))
            v.across_flats_dmm = float(-r.uniform(0.0, 0.25))
            v.height_dmm = float(-r.uniform(0.0, 0.3))
            v.length_dmm = float(r.uniform(-0.4, 0.4))
        r = self.rng("defect", kind)
        if self.on("defect") and r.random() < self.defect_rate:
            choices = {
                "screw": ["crushed_thread", "bent", "burr"],
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
        return v

    # ------------------------------------------------------------------ cells and holders
    def cell(self, fmt, kind):
        v = CellVariation()
        r = self.rng("tolerance", "cell")
        if self.on("tolerance"):
            v.diameter_dmm = float(-r.uniform(0.0, 0.5 if kind != "coin" else 0.3))  # cells are made under nominal
            v.length_dmm = float(-r.uniform(0.0, 0.8 if kind != "coin" else 0.2))
        r = self.rng("defect", "cell")
        if self.on("defect") and r.random() < self.defect_rate:
            v.defect = str(r.choice(["dent", "corroded_terminal"] if kind == "cradle" else ["corroded_terminal"]))
            v.defect_angle_deg = float(r.uniform(0, 360))
            v.defect_z = float(r.uniform(0.2, 0.8))
            v.defect_size = float(r.uniform(0.3, 1.0))
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
    """Flat {variation:name: value} for the USD attributes and the CSV."""
    return {f"variation:{k}": (round(x, 6) if isinstance(x, float) else x) for k, x in asdict(v).items()}
