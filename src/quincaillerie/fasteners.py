"""Metric fasteners as OpenUSD assets: hex head screws (ISO 4017), hex nuts (ISO 4032), plain washers
(ISO 7089), M3 to M12, coarse pitch, with modelled threads.

Visual: one mesh per part with the real thread profile and a "finish" variant set (six finishes from
the material library, plus the instance's own worn look when it has one). Physics: one rigid body,
mass and inertia integrated from the mesh, convex collision pieces that follow the helix, so a nut
can be screwed on a screw in simulation.

Every writer takes a ``FastenerVariation`` (see ``variation.py``): tolerances move the thread
clearance and the dimensions; defects deform the geometry *and* the collision pieces, so a crushed
thread really jams a nut and a bent screw really wobbles; wear gives the instance its own material
and friction.
"""

from __future__ import annotations

import os

import numpy as np
from pxr import Sdf

from . import physx
from .catalog import METRIC, nut_name, screw_name, washer_name
from .materials import FINISHES
from .threads import iso_profile, mesh_mass_props, nut_mesh, segments, threaded_bolt_mesh
from .usd import (
    VisualBuilder,
    collider_cylinder,
    collider_hull,
    finish_variants,
    fix_typeless,
    inertia_principal,
    mate_frame,
    new_stage,
    physics_material,
    revolve_profile,
    rigid_body,
    set_attrs,
    uv_box,
    uv_cylindrical,
)
from .variation import FastenerVariation, as_attrs

MM = 1e-3
CONTACT_OFFSET = 0.0001  # m: distance from which contacts are generated, below twice the thread clearance
SEG_DEG = 10.0  # helix angle covered by one convex collision piece
DETAIL = {"low": (48, 8), "normal": (72, 14), "high": (96, 24)}  # visual mesh: sides, rings per pitch
# Collision of a fastener. "thread": every turn of the helix as convex pieces, so a nut screws on
# and a crushed thread jams (about a thousand pieces for an M8x30). "simple": the envelope alone,
# a cylinder for the shank, twelve wedges for a nut, eight sectors for a washer: parts fall, pile up
# and can be grasped, a nut slides freely over a shank, and nothing screws or jams.
COLLIDERS = ("thread", "simple")


def _collider(name: str) -> str:
    if name not in COLLIDERS:
        raise ValueError(f"unknown collider {name!r}: {', '.join(COLLIDERS)}")
    return name


def nut_wedges(s_af, bore_r, height):
    """A hex nut as twelve convex wedges around its bore, two per flat: [points].

    Each wedge spans 30 degrees, from a corner of the hexagon to the middle of a flat. Its inner
    face is a chord tangent to the bore circle, so the hole is never narrower than the bore."""
    step = np.pi / 6
    inner = bore_r / np.cos(step / 2)  # the chord between two inner points touches the bore
    out = []
    for i in range(12):
        pts = []
        for a in (i * step + np.pi / 6, (i + 1) * step + np.pi / 6):
            corner = round((a - np.pi / 6) / step) % 2 == 0  # corners at 30 + 60 k degrees
            outer = s_af / np.sqrt(3) if corner else s_af / 2
            for r in (inner, outer):
                pts += [[r * np.cos(a), r * np.sin(a), z] for z in (0.0, height)]
        out.append(np.array(pts))
    return out


def hex_prism(s_af, z0, z1):
    R = s_af / np.sqrt(3)
    ang = np.arange(6) * np.pi / 3 + np.pi / 6
    ring = np.c_[R * np.cos(ang), R * np.sin(ang)]
    V = np.vstack([np.c_[ring, np.full(6, z0)], np.c_[ring, np.full(6, z1)], [[0, 0, z0], [0, 0, z1]]])
    F = []
    for i in range(6):
        j = (i + 1) % 6
        F += [[i, j, 6 + j], [i, 6 + j, 6 + i], [12, j, i], [13, 6 + i, 6 + j]]
    return V, np.array(F)


def _combined_mass(parts, rho):
    """parts: [(V, F)] closed meshes -> mass, centre of mass, inertia about it."""
    props = [mesh_mass_props(V, F, rho) for V, F in parts]
    m = sum(p[1] for p in props)
    com = sum(p[1] * p[2] for p in props) / m
    inertia = np.zeros((3, 3))
    for _, mi, ci, Ii in props:
        r = ci - com
        inertia += Ii + mi * (np.dot(r, r) * np.eye(3) - np.outer(r, r))
    return m, com, inertia


def _looks(stage, root, name, subsets, finish, v, path):
    """Finish variants; a worn instance gets its own baked material, selected by default."""
    extra = None
    if v.worn():
        from .wear import instance_material

        set_dir = os.path.dirname(os.path.dirname(os.path.abspath(path)))
        mpath = instance_material(
            stage,
            str(root.GetPath()),
            f"{name}_worn",
            finish,
            dict(rust=v.rust, oil=v.oil, dirt=v.dirt, scratches=v.scratches),
            v.seed,
            os.path.join(set_dir, "materials", "instances"),
            "../materials/instances",
        )
        extra = {"as_generated": mpath}
    finish_variants(stage, root, [subsets["finish"]], FINISHES, "as_generated" if extra else finish, extra)


def _save(stage):
    """Save the part and write its PhysX layer beside it (a thread needs many solver iterations)."""
    stage.GetDefaultPrim().CreateAttribute(physx.ASKED, Sdf.ValueTypeNames.Float).Set(CONTACT_OFFSET)
    fix_typeless(stage)
    stage.GetRootLayer().Save()
    physx.write_overlay(stage.GetRootLayer().realPath, position_iterations=32, max_depenetration=0.05)


def _zone(v, length, P):
    """Damaged zone (z0, z1, theta0, theta1) of a crushed thread: 3 pitches long."""
    zc = float(np.clip(v.defect_z * length, 2 * P, length - 2 * P))
    t0 = (v.defect_z * 37.0) % (2 * np.pi)
    return (zc - 1.5 * P, zc + 1.5 * P, t0, t0 + np.radians(v.defect_angle_deg))


def _widen(v, P):
    """Axial widening of a crushed ridge: the defect size (a fraction of the pitch) beyond the axial
    play of the fit (the radial clearance of both parts, projected on a 60 degree flank), with margin,
    so that it always interferes with a mating thread."""
    play = 2 * 2 * v.clearance_mm * MM * np.tan(np.radians(30))
    return v.defect_size * P + 3 * play  # x3: the nut can also slide sideways by its radial play


def _bend(points, angle_deg, length):
    """Bend the shank (z > 0) in the xz plane: x += kappa z^2 / 2, tip angle angle_deg."""
    kappa = np.radians(angle_deg) / length
    P = np.array(points, float)
    z = np.clip(P[:, 2], 0, None)
    P[:, 0] += kappa * z**2 / 2
    return P


def write_screw(
    path, size="M8", length=None, finish="zinc_clear", v=None, name=None, detail="normal", collider="thread"
):
    """Fully threaded hex head screw. Head from z=-k to 0, shank from 0 to the length, axis +Z.

    collider: "thread" (the helix, in convex pieces) or "simple" (a cylinder at the major diameter)."""
    simple = _collider(collider) == "simple"
    from .catalog import DEFAULT_LENGTH

    v = v or FastenerVariation()
    t = METRIC[size]
    length = float(length or DEFAULT_LENGTH[size])
    d, P = t["d"] * MM, t["P"] * MM
    s_af = (t["s"] + v.across_flats_dmm) * MM
    k = (t["k"] + v.height_dmm) * MM
    L = (length + v.length_dmm) * MM
    clearance = v.clearance_mm * MM
    name = name or screw_name(size, length)
    R = f"/{name}"
    prof = iso_profile(d, P)
    stage, root = new_stage(path, name)
    steel = physics_material(stage, R, "steel", v.friction)
    crush = burr = None
    if v.defect == "crushed_thread":
        crush = (_zone(v, L, P), _widen(v, P), 0.5 * v.defect_size * (d - prof["d3"]) / 2)
    if v.defect == "burr":
        t0 = (v.defect_z * 37.0) % (2 * np.pi)
        burr = (t0, t0 + np.radians(v.defect_angle_deg), v.defect_size * MM)
    nt, nz = DETAIL[detail]
    Vs, Fs = threaded_bolt_mesh(prof, L, clearance, nt=nt, nz_per_pitch=nz, crush=crush, burr=burr)
    Vh, Fh = hex_prism(s_af, -k, 0.0)
    pieces = [] if simple else segments(prof, 0.0, L, clearance, "bolt", SEG_DEG, crush=crush, burr=burr)
    # the simple collider is the shank at its major diameter; the core carries the thread pieces
    core_r = (d / 2 if simple else prof["d3"] / 2) - clearance
    if v.defect == "bent":
        Vs = _bend(Vs, v.defect_size, L)
        pieces = [_bend(p, v.defect_size, L) for p in pieces]
    vb = VisualBuilder()
    vb.add(Vs, Fs, "finish", uv_cylindrical(Vs, Fs, "z", vscale=100.0))
    vb.add(Vh, Fh, "finish", uv_box(Vh, Fh, 60.0))
    _, subsets = vb.write(stage, f"{R}/Visual/{name}_mesh", R, variant_mats=("finish",))
    _looks(stage, root, name, subsets, finish, v, path)
    m, com, inertia = _combined_mass([(Vs, Fs), (Vh, Fh)], v.density)
    ev, q = inertia_principal(inertia)
    rigid_body(root, m, com, ev, q)
    slices = 0
    if v.defect == "bent":  # the core follows the bend: stacked convex slices
        n = slices = max(4, int(np.ceil(L / (2 * P))))
        ring = np.linspace(0, 2 * np.pi, 16, endpoint=False)
        for i in range(n):
            za, zb = L * i / n, L * (i + 1) / n
            pts = [[core_r * np.cos(a), core_r * np.sin(a), z] for z in (za, zb) for a in ring]
            collider_hull(stage, f"{R}/Collision/core_{i:02d}", _bend(pts, v.defect_size, L), pmat=steel)
    else:
        collider_cylinder(stage, f"{R}/Collision/core", (0, 0, L / 2), core_r, L / 2, "Z", pmat=steel)
    collider_hull(stage, f"{R}/Collision/head", Vh[:12], pmat=steel)
    for i, pts in enumerate(pieces):
        collider_hull(stage, f"{R}/Collision/thread_{i:04d}", pts, pmat=steel)
    set_attrs(
        root,
        dict(
            category="screw",
            standard="ISO 4017",
            designation=f"ISO 4017 - {size} x {length:g}",
            size=size,
            pitch=P,
            majorDiameter=d,
            length=L,
            nominalLength=length * MM,
            acrossFlats=s_af,
            headHeight=k,
            propertyClass="8.8",
            finishes=FINISHES,
            threadClearance=clearance,
            collision=collider,
            dimensionsStatus="nominal" if v == FastenerVariation() else "varied within tolerance",
            mass=m,
            compatibleWith=[nut_name(size), washer_name(size)],
            **as_attrs(v),
        ),
    )
    mate_frame(
        stage,
        f"{R}/MateFrame_thread",
        (0, 0, 0),
        (1, 0, 0, 0),
        dict(role="male_thread", pitch=P, majorDiameter=d, hand="right", axis="+Z"),
    )
    mate_frame(
        stage,
        f"{R}/MateFrame_drive",
        (0, 0, -k),
        (0, 1, 0, 0),
        dict(role="drive", drive="external_hex", acrossFlats=s_af, engagement=k),
    )
    _save(stage)
    return dict(
        name=name,
        kind="screw",
        size=size,
        length_mm=length,
        mass_g=m * 1e3,
        colliders=len(pieces) + 1 + (slices or 1),
        **as_attrs(v),
    )


def write_nut(path, size="M8", finish="zinc_clear", v=None, name=None, detail="normal", collider="thread"):
    """Hex nut, z from 0 to its height, threaded along +Z.

    collider: "thread" (the helix, in convex pieces) or "simple" (twelve wedges around a smooth bore)."""
    simple = _collider(collider) == "simple"
    v = v or FastenerVariation()
    t = METRIC[size]
    d, P = t["d"] * MM, t["P"] * MM
    s_af = (t["s"] + v.across_flats_dmm) * MM
    H = (t["m"] + v.height_dmm) * MM
    clearance = v.clearance_mm * MM
    name = name or nut_name(size)
    R = f"/{name}"
    prof = iso_profile(d, P)
    stage, root = new_stage(path, name)
    steel = physics_material(stage, R, "steel", v.friction)
    crush = None
    if v.defect == "crushed_thread":
        crush = (_zone(v, H, P), _widen(v, P), 0.5 * v.defect_size * (prof["d"] - prof["d1"]) / 2)
    nt, nz = DETAIL[detail]
    V, F = nut_mesh(prof, s_af, H, clearance, nt=nt, nz_per_pitch=nz, crush=crush)
    if simple:  # a smooth bore at the major diameter: the nut slides over a shank
        pieces = nut_wedges(s_af, d / 2 + clearance, H)
    else:
        pieces = segments(prof, 0.0, H, clearance, "nut", SEG_DEG, s_af=s_af, crush=crush)
    if v.defect == "oval":  # squeezed: one diameter shorter, the other longer
        e = v.defect_size * MM / d
        S = np.diag([1 + e, 1 - e, 1.0])
        V = V @ S
        pieces = [p @ S for p in pieces]
    vb = VisualBuilder()
    vb.add(V, F, "finish", uv_cylindrical(V, F, "z", vscale=100.0))
    _, subsets = vb.write(stage, f"{R}/Visual/{name}_mesh", R, variant_mats=("finish",))
    _looks(stage, root, name, subsets, finish, v, path)
    _, m, com, inertia = mesh_mass_props(V, F, v.density)
    ev, q = inertia_principal(inertia)
    rigid_body(root, m, com, ev, q)
    for i, pts in enumerate(pieces):
        collider_hull(stage, f"{R}/Collision/piece_{i:04d}", pts, pmat=steel)
    set_attrs(
        root,
        dict(
            category="nut",
            collision=collider,
            standard="ISO 4032",
            designation=f"ISO 4032 - {size}",
            size=size,
            pitch=P,
            majorDiameter=d,
            height=H,
            acrossFlats=s_af,
            propertyClass="8",
            finishes=FINISHES,
            threadClearance=clearance,
            dimensionsStatus="nominal" if v == FastenerVariation() else "varied within tolerance",
            mass=m,
            compatibleWith=[f"ISO4017_{size}", washer_name(size)],
            **as_attrs(v),
        ),
    )
    mate_frame(
        stage,
        f"{R}/MateFrame_thread",
        (0, 0, 0),
        (1, 0, 0, 0),
        dict(role="female_thread", pitch=P, majorDiameter=d, hand="right", axis="+Z"),
    )
    mate_frame(
        stage,
        f"{R}/MateFrame_drive",
        (0, 0, H),
        (1, 0, 0, 0),
        dict(role="drive", drive="external_hex", acrossFlats=s_af, engagement=H),
    )
    _save(stage)
    return dict(name=name, kind="nut", size=size, mass_g=m * 1e3, colliders=len(pieces), **as_attrs(v))


def washer_mesh(d1, d2, h, n=96):
    c = min(0.15 * h, 0.2 * (d2 - d1) / 2)  # small edge break on the outer rim
    prof = [(d1 / 2, 0), (d2 / 2 - c, 0), (d2 / 2, c), (d2 / 2, h - c), (d2 / 2 - c, h), (d1 / 2, h), (d1 / 2, 0)]
    return revolve_profile(np.asarray(prof), n)


def _dish(points, d1, d2, height):
    """Dished (coned) washer: z rises with the radius, by `height` at the rim."""
    P = np.array(points, float)
    r = np.hypot(P[:, 0], P[:, 1])
    P[:, 2] += height * np.clip((r - d1 / 2) / (d2 / 2 - d1 / 2), 0, 1)
    return P


def write_washer(
    path, size="M8", finish="zinc_clear", v=None, name=None, sectors=24, detail="normal", collider="thread"
):
    """Plain washer, z from 0 to its thickness. Collision: `sectors` convex ring sectors (8 with
    collider="simple")."""
    if _collider(collider) == "simple":
        sectors = 8
    v = v or FastenerVariation()
    d1, d2, h = (x * MM for x in METRIC[size]["washer"])
    h += v.height_dmm * MM * 0.3  # thickness tolerance is tighter than a head's
    name = name or washer_name(size)
    R = f"/{name}"
    stage, root = new_stage(path, name)
    steel = physics_material(stage, R, "steel", v.friction)
    V, F = washer_mesh(d1, d2, h, DETAIL[detail][0] + 24)
    dish = v.defect_size * MM if v.defect == "dished" else 0.0
    if dish:
        V = _dish(V, d1, d2, dish)
    vb = VisualBuilder()
    vb.add(V, F, "finish", uv_cylindrical(V, F, "z", vscale=100.0))
    _, subsets = vb.write(stage, f"{R}/Visual/{name}_mesh", R, variant_mats=("finish",))
    _looks(stage, root, name, subsets, finish, v, path)
    _, m, com, inertia = mesh_mass_props(V, F, v.density)
    ev, q = inertia_principal(inertia)
    rigid_body(root, m, com, ev, q)
    # the hull of a ring sector bulges past the outer circle by at most r2 (1 - cos(dth/2)): use the
    # chord inside, so the washer never collides beyond its outline
    dth = 2 * np.pi / sectors
    r1, r2 = d1 / 2, d2 / 2
    for i in range(sectors):
        pts = []
        for a in np.linspace(i * dth, (i + 1) * dth, 3):
            for r in (r1 / np.cos(dth / 4), r2):
                for z in (0.0, h):
                    pts.append([r * np.cos(a), r * np.sin(a), z])
        pts = _dish(pts, d1, d2, dish) if dish else np.array(pts)
        collider_hull(stage, f"{R}/Collision/sector_{i:02d}", pts, pmat=steel)
    set_attrs(
        root,
        dict(
            category="washer",
            collision=collider,
            standard="ISO 7089",
            designation=f"ISO 7089 - {size}",
            size=size,
            innerDiameter=d1,
            outerDiameter=d2,
            thickness=h,
            finishes=FINISHES,
            dimensionsStatus="nominal" if v == FastenerVariation() else "varied within tolerance",
            mass=m,
            compatibleWith=[f"ISO4017_{size}", nut_name(size)],
            **as_attrs(v),
        ),
    )
    mate_frame(stage, f"{R}/MateFrame_bore", (0, 0, 0), (1, 0, 0, 0), dict(role="bore", diameter=d1, axis="+Z"))
    _save(stage)
    return dict(name=name, kind="washer", size=size, mass_g=m * 1e3, colliders=sectors, **as_attrs(v))
