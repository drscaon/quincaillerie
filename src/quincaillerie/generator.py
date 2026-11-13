"""Generate assets, their related elements and a scene laying them out on a floor.

One call writes, under ``<out>/<set name>/``:

* ``assets/``     ``count`` distinct instances of every part, each with its own tolerances, defects,
  wear and physics (``variation.py``), or one nominal file per part with ``vary=()``;
* ``materials/``  the shared material library (USD + MaterialX), its textures, and the baked
  textures of the worn instances (``instances/``);
* ``scene.usda``  every instance at rest on a floor collider, plus the assemblies (a nut threaded on
  its screw over a washer, a cell seated in its holder);
* ``instances.csv``   one row per instance with every drawn and measured value, read back from
  the files: the ground truth; ``manifest.json``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np

from .batteries import write_cell, write_holder
from .catalog import CELLS, DEFAULT_LENGTH, KINDS, METRIC, RELATED, SIZES, asset_name
from .fasteners import write_nut, write_screw, write_washer
from .materials import FINISHES, write_materials
from .pack import write_pack
from .scenes import add_floor, add_ref, footprint, new_scene, place_seated, rest_pose, save, thread_height
from .usd import quat_axis_angle, stamp_identity
from .variation import ASPECTS, Sampler


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


def write_part(part, assets_dir, finish="zinc_clear", variation=None, name=None, detail="normal", collider="thread"):
    """Write one part; `name` (file and root prim) and `variation` for an instance."""
    filename = (name + os.path.splitext(part.filename)[1]) if name else part.filename
    path = os.path.join(assets_dir, filename)
    if part.kind == "screw":
        info = write_screw(path, part.key, part.length, finish, variation, name, detail, collider)
    elif part.kind == "nut":
        info = write_nut(path, part.key, finish, variation, name, detail, collider)
    elif part.kind == "washer":
        info = write_washer(path, part.key, finish, variation, name, detail=detail, collider=collider)
    elif part.kind == "cell":
        info = write_cell(path, part.key, variation, name)
    else:
        info = write_holder(path, part.key, hv=variation, root_name=name)
    info["file"] = f"assets/{filename}"
    info["instance_of"] = part.name
    return info


def draw(sampler, part, finish):
    """The variation of the next instance of a part."""
    if part.kind in ("screw", "nut", "washer"):
        return sampler.fastener(part.kind, finish, METRIC[part.key]["P"], METRIC[part.key]["d"])
    kind = CELLS[part.key]["kind"]
    return sampler.cell(part.key, kind) if part.kind == "cell" else sampler.holder(part.key, kind)


def generate(
    parts,
    out="output",
    set_name=None,
    count=1,
    finish="zinc_clear",
    seed=1,
    scene=True,
    physics=True,
    vary=ASPECTS,
    defect_rate=0.15,
    detail="normal",
    collider="thread",
    thread_play="class",
):
    """Write `count` instances of each part, the material library and a scene. Returns a Result.

    vary: the aspects that vary between instances (tolerance, defect, wear, physics); () writes one
    nominal file per part, placed `count` times in the scene. physics=False writes visual assets
    only: no rigid bodies, colliders, joints or physics scene. collider: "thread" (fasteners screw
    and jam) or "simple" (their envelope alone, for large scenes; see fasteners.COLLIDERS).
    thread_play: how the thread clearance is chosen: "class" (drawn in the 6g / 6H fit), "middle"
    (the middle of the fit for every instance) or "legacy" (the range used before the fit classes)."""
    if finish not in FINISHES:
        raise ValueError(f"unknown finish {finish!r}; expected one of {', '.join(FINISHES)}")
    set_name = set_name or parts[0].name
    root = os.path.join(out, set_name)
    assets = os.path.join(root, "assets")
    os.makedirs(assets, exist_ok=True)
    mat_info = write_materials(os.path.join(root, "materials"))
    res = Result(root)
    vary = tuple(vary)
    if finish not in FINISHES:
        raise ValueError(f"unknown finish {finish!r}")
    sampler = Sampler(seed=seed, vary=vary, defect_rate=defect_rate, thread_play=thread_play)
    instances = {}  # part -> [(name, info)]
    for p in parts:
        n = count if vary else 1
        for i in range(n):
            name = f"{p.name}_{i:03d}" if vary else None
            info = write_part(p, assets, finish, draw(sampler, p, finish), name, detail, collider)
            drawn = {k.removeprefix("variation:"): v for k, v in info.items() if k.startswith("variation:")}
            mass = info.get("mass_g")
            measured = {"mass_kg": mass / 1e3 if mass is not None else None, "colliders": info.get("colliders")}
            stamp_identity(os.path.join(root, info["file"]), p.name, seed, vary, drawn, measured)
            if not physics:
                from pxr import Usd

                from .usd import strip_physics

                strip_physics(Usd.Stage.Open(os.path.join(root, info["file"])))
                info.pop("colliders", None)
            res.parts.append(info)
            instances.setdefault(p, []).append(info)
    if scene:
        res.scene = write_scene(
            os.path.join(root, "scene.usda"), parts, instances, root, count, finish, seed, physics, bool(vary)
        )
    summary = dict(
        set=set_name,
        parts=len(res.parts),
        by_kind={
            k: sum(1 for p in res.parts if p["kind"] == k) for k in KINDS if any(p["kind"] == k for p in res.parts)
        },
        count=count,
        varied=list(vary),
        defect_rate=defect_rate if "defect" in vary else 0.0,
        defects={
            d: sum(1 for p in res.parts if p.get("variation:defect") == d)
            for d in sorted({p.get("variation:defect", "none") for p in res.parts})
        },
        finish=finish,
        collider=collider,
        materials=mat_info,
        scene="scene.usda" if scene else None,
        physics=physics,
    )
    # instances.csv (one row per instance, read back from the files) and manifest.json
    own = ("kind", "size", "format", "length_mm", "family")
    extra = {row["name"]: {k: row[k] for k in own if row.get(k) is not None} for row in res.parts}
    write_pack(root, set_name, seed, vary, summary=summary, extra=extra)
    return res


ROW = 25  # instances of one part side by side in the scene, before a new row


def write_scene(path, parts, instances, root, count=1, finish="zinc_clear", seed=1, physics=True, varied=True):
    """Lay every instance out on the floor, in rows by part (at most ROW of them side by side), with
    random yaw (nominal parts: `count` copies); then the assemblies that the parts allow (screw +
    washer + nut of one size, cell + holder of one format), made of instances without defects. The
    floor covers them all."""
    from .usd import qmul

    rng = np.random.default_rng(seed)
    st = new_scene(path, floor=False, physics=physics)
    by = {(p.kind, p.key): p for p in parts}
    y = reach = 0.0
    for p in parts:
        w, d = footprint(p.kind, p.key, p.length)
        w, d = w + 0.01, d + 0.01
        off, q0 = rest_pose(p.kind, p.key)
        files = [os.path.join(root, i["file"]) for i in instances[p]]
        names = [i["name"] for i in instances[p]]
        for i in range(count):
            yaw = rng.uniform(0, 2 * np.pi) if p.kind in ("screw", "nut", "washer") else 0.0
            q = qmul(quat_axis_angle((0, 0, 1), yaw), q0)
            pos = ((i % ROW) * w + off[0], y + (i // ROW) * d + off[1], off[2])
            fin = None if varied or p.kind not in ("screw", "nut", "washer") else finish
            k = i if varied else 0
            prim = names[k] if varied else f"{p.name}_{i:03d}"
            add_ref(st, prim, files[k], pos, q, fin)
        y += d * ((count - 1) // ROW + 1)
        reach = max(reach, min(count, ROW) * w)

    def sound(part):  # an instance without a defect, for the assemblies
        for info in instances[part]:
            if info.get("variation:defect", "none") == "none":
                return os.path.join(root, info["file"])
        return os.path.join(root, instances[part][0]["file"])

    y += 0.01
    x = 0.0
    for p in parts:
        if p.kind == "screw" and ("nut", p.key) in by:
            t = METRIC[p.key]
            k = t["k"] * 1e-3
            add_ref(st, f"assembly_{p.name}", sound(p), (x, y, k), (1, 0, 0, 0))
            h = 0.0
            if ("washer", p.key) in by:
                pw = by[("washer", p.key)]
                add_ref(st, f"assembly_{pw.name}", sound(pw), (x, y, k), (1, 0, 0, 0))
                h = t["washer"][2] * 1e-3
            pn = by[("nut", p.key)]
            n = int(np.ceil(h / (t["P"] * 1e-3) + 1e-9)) + 1  # first whole pitch above the washer
            add_ref(st, f"assembly_{pn.name}", sound(pn), (x, y, k + thread_height(p.key, n)), (1, 0, 0, 0))
            x += max(t["s"], t["washer"][1]) * 1e-3 * 1.5
        if p.kind == "holder" and ("cell", p.key) in by:
            w, d = footprint("holder", p.key)
            hp = (x + w / 2, y + d / 2, 0.0)
            add_ref(st, f"assembly_{p.name}", sound(p), hp)
            place_seated(
                st, f"assembly_{p.name}", f"assembly_{by[('cell', p.key)].name}", sound(by[("cell", p.key)]), p.key, hp
            )
            x += w + 0.01
    if physics:  # the floor covers every row, however many instances
        add_floor(st, reach=(max(reach, x) + 0.05, y + 0.1))
    path = save(st)
    if physics:  # the scene's PhysX layer references the layer of each part (physx.py)
        from .physx import write_overlay

        write_overlay(path)
    else:
        stem, _ = os.path.splitext(path)
        if os.path.exists(f"{stem}_physx.usda"):
            os.remove(f"{stem}_physx.usda")
    return path
