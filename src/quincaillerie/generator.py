"""Generate assets, their related elements and a scene laying them out on a floor.

One call writes, under ``<out>/<set name>/``:

* ``assets/``     one OpenUSD file per part (``.usdc`` for threaded parts, ``.usda`` otherwise);
* ``materials/``  the shared material library (USD + MaterialX) and its textures;
* ``scene.usda``  every part ``count`` times, at rest on a floor collider, plus the assemblies
  (a nut threaded on its screw over a washer, a cell seated in its holder);
* ``parts.csv``, ``summary.json``.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field

import numpy as np

from .batteries import write_cell, write_holder
from .catalog import CELLS, DEFAULT_LENGTH, KINDS, METRIC, RELATED, SIZES, asset_name
from .fasteners import write_nut, write_screw, write_washer
from .materials import FINISHES, write_materials
from .scenes import add_ref, footprint, new_scene, place_seated, rest_pose, save, thread_height
from .usd import quat_axis_angle


@dataclass(frozen=True)
class Part:
    kind: str
    key: str  # size (M8) or cell format (AA)
    length: float | None = None  # screws, mm

    @property
    def name(self) -> str:
        return asset_name(self.kind, self.key, self.length)

    @property
    def filename(self) -> str:
        return self.name + (".usdc" if self.kind in ("screw", "nut") else ".usda")


@dataclass
class Result:
    out_dir: str
    parts: list = field(default_factory=list)  # dicts returned by the writers
    scene: str | None = None


def resolve(kind, key, length=None, with_=()):
    """The parts of a request: the main part and the related elements asked with `with_`."""
    if kind not in KINDS:
        raise ValueError(f"unknown kind {kind!r}; expected one of {', '.join(KINDS)}")
    fast = kind in ("screw", "nut", "washer")
    if fast and key not in METRIC:
        raise ValueError(f"unknown size {key!r}; expected one of {', '.join(SIZES)}")
    if not fast and key not in CELLS:
        raise ValueError(f"unknown cell format {key!r}; expected one of {', '.join(CELLS)}")
    for w in with_:
        if w not in RELATED[kind]:
            raise ValueError(f"--with {w}: a {kind} can come with {', '.join(RELATED[kind])}")
    if kind == "screw":
        length = float(length or DEFAULT_LENGTH[key])
        if not 2 * METRIC[key]["P"] <= length <= 200:
            raise ValueError(f"screw length {length:g} mm out of range")
    parts = [Part(kind, key, length if kind == "screw" else None)]
    for w in with_:
        parts.append(Part(w, key, (length or DEFAULT_LENGTH[key]) if w == "screw" else None))
    return parts


def catalog_parts():
    """Every part of the catalogue: per size a screw (default length), a nut, a washer; every cell
    and its holder."""
    out = []
    for s in SIZES:
        out += [Part("screw", s, float(DEFAULT_LENGTH[s])), Part("nut", s), Part("washer", s)]
    for f in CELLS:
        out += [Part("cell", f), Part("holder", f)]
    return out


def write_part(part, assets_dir, finish="zinc_clear"):
    path = os.path.join(assets_dir, part.filename)
    if part.kind == "screw":
        return write_screw(path, part.key, part.length, finish)
    if part.kind == "nut":
        return write_nut(path, part.key, finish)
    if part.kind == "washer":
        return write_washer(path, part.key, finish)
    if part.kind == "cell":
        return write_cell(path, part.key)
    return write_holder(path, part.key)


def generate(parts, out="output", set_name=None, count=1, finish="zinc_clear", seed=1, scene=True, physics=True):
    """Write the parts, the material library and a scene. Returns a Result.

    physics=False writes visual assets only: no rigid bodies, colliders, joints or physics scene."""
    if finish not in FINISHES:
        raise ValueError(f"unknown finish {finish!r}; expected one of {', '.join(FINISHES)}")
    set_name = set_name or parts[0].name
    root = os.path.join(out, set_name)
    assets = os.path.join(root, "assets")
    os.makedirs(assets, exist_ok=True)
    mat_info = write_materials(os.path.join(root, "materials"))
    res = Result(root)
    for p in parts:
        info = write_part(p, assets, finish)
        if not physics:
            from pxr import Usd

            from .usd import strip_physics

            strip_physics(Usd.Stage.Open(os.path.join(assets, p.filename)))
            info.pop("colliders", None)
        info["file"] = f"assets/{p.filename}"
        res.parts.append(info)
    if scene:
        res.scene = write_scene(os.path.join(root, "scene.usda"), parts, assets, count, finish, seed, physics)
    with open(os.path.join(root, "parts.csv"), "w", newline="", encoding="utf-8") as f:
        keys = ["name", "kind", "size", "format", "length_mm", "mass_g", "colliders", "family", "file"]
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for row in res.parts:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
    summary = dict(
        set=set_name,
        parts=len(res.parts),
        by_kind={
            k: sum(1 for p in res.parts if p["kind"] == k) for k in KINDS if any(p["kind"] == k for p in res.parts)
        },
        count_in_scene=count,
        finish=finish,
        materials=mat_info,
        scene="scene.usda" if scene else None,
        physics=physics,
    )
    with open(os.path.join(root, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1)
    return res


def write_scene(path, parts, assets_dir, count=1, finish="zinc_clear", seed=1, physics=True):
    """Lay every part out `count` times on the floor, in rows by kind, with random yaw; then the
    assemblies that the parts allow (screw + washer + nut of one size, cell + holder of one format)."""
    rng = np.random.default_rng(seed)
    st = new_scene(path, physics=physics)
    rows = []
    by = {(p.kind, p.key): p for p in parts}
    for p in parts:
        w, d = footprint(p.kind, p.key, p.length)
        rows.append((p, w + 0.01, d + 0.01))
    y = 0.0
    for p, w, d in rows:
        off, q0 = rest_pose(p.kind, p.key)
        for i in range(count):
            yaw = rng.uniform(0, 2 * np.pi) if p.kind in ("screw", "nut", "washer") else 0.0
            from .usd import qmul

            q = qmul(quat_axis_angle((0, 0, 1), yaw), q0)
            pos = (i * w + off[0], y + off[1], off[2])
            fin = finish if p.kind in ("screw", "nut", "washer") else None
            add_ref(st, f"{p.name}_{i:03d}", os.path.join(assets_dir, p.filename), pos, q, fin)
        y += d
    # assemblies
    y += 0.01
    x = 0.0
    for p in parts:
        if p.kind == "screw" and ("nut", p.key) in by:
            t = METRIC[p.key]
            k = t["k"] * 1e-3
            add_ref(st, f"assembly_{p.name}", os.path.join(assets_dir, p.filename), (x, y, k), (1, 0, 0, 0), finish)
            h = 0.0
            if ("washer", p.key) in by:
                pw = by[("washer", p.key)]
                add_ref(
                    st, f"assembly_{pw.name}", os.path.join(assets_dir, pw.filename), (x, y, k), (1, 0, 0, 0), finish
                )
                h = t["washer"][2] * 1e-3
            pn = by[("nut", p.key)]
            n = int(np.ceil(h / (t["P"] * 1e-3) + 1e-9)) + 1  # first whole pitch above the washer
            add_ref(
                st,
                f"assembly_{pn.name}",
                os.path.join(assets_dir, pn.filename),
                (x, y, k + thread_height(p.key, n)),
                (1, 0, 0, 0),
                finish,
            )
            x += max(t["s"], t["washer"][1]) * 1e-3 * 1.5
        if p.kind == "holder" and ("cell", p.key) in by:
            w, d = footprint("holder", p.key)
            hp = (x + w / 2, y + d / 2, 0.0)
            add_ref(st, f"assembly_{p.name}", os.path.join(assets_dir, p.filename), hp)
            pc = by[("cell", p.key)]
            place_seated(
                st, f"assembly_{p.name}", f"assembly_{pc.name}", os.path.join(assets_dir, pc.filename), p.key, hp
            )
            x += w + 0.01
    return save(st)
