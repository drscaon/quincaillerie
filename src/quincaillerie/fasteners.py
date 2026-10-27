"""Metric fasteners as OpenUSD assets: hex head screws (ISO 4017), hex nuts (ISO 4032), plain washers
(ISO 7089), M3 to M12, coarse pitch, with modelled threads.

Visual: one mesh per part with the real thread profile and a "finish" variant set (six finishes from
the material library). Physics: one rigid body, mass and inertia integrated from the mesh (steel),
convex collision pieces that follow the helix, so a nut can be screwed on a screw in simulation.
"""

from __future__ import annotations

import numpy as np

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
    physx_tune,
    revolve_profile,
    rigid_body,
    set_attrs,
    uv_box,
    uv_cylindrical,
)

MM = 1e-3
RHO_STEEL = 7850.0  # kg/m3
CLEARANCE = 0.05e-3  # radial clearance of each thread (m), like a 6g/6H fit
STEEL_FRICTION = 0.15
CONTACT_OFFSET = 0.0001  # PhysX contact offset (m), below the thread clearance x 2
SEG_DEG = 10.0  # helix angle covered by one convex collision piece


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


def _combined_mass(parts):
    """parts: [(V, F)] closed meshes -> mass, centre of mass, inertia about it (steel)."""
    props = [mesh_mass_props(V, F, RHO_STEEL) for V, F in parts]
    m = sum(p[1] for p in props)
    com = sum(p[1] * p[2] for p in props) / m
    inertia = np.zeros((3, 3))
    for _, mi, ci, Ii in props:
        r = ci - com
        inertia += Ii + mi * (np.dot(r, r) * np.eye(3) - np.outer(r, r))
    return m, com, inertia


def _finish(stage, root, mesh_path, subsets, finish):
    finish_variants(stage, root, [subsets["finish"]], FINISHES, finish)


def _save(stage):
    physx_tune(stage, CONTACT_OFFSET, pos_iters=32, max_depen=0.05)
    fix_typeless(stage)
    stage.GetRootLayer().Save()


def write_screw(path, size="M8", length=None, finish="zinc_clear"):
    """Fully threaded hex head screw. Head from z=-k to 0, shank from 0 to the length, axis +Z."""
    from .catalog import DEFAULT_LENGTH

    t = METRIC[size]
    length = float(length or DEFAULT_LENGTH[size])
    d, P, s_af, k, L = t["d"] * MM, t["P"] * MM, t["s"] * MM, t["k"] * MM, length * MM
    name = screw_name(size, length)
    R = f"/{name}"
    prof = iso_profile(d, P)
    stage, root = new_stage(path, name)
    steel = physics_material(stage, R, "steel", STEEL_FRICTION)
    Vs, Fs = threaded_bolt_mesh(prof, L, CLEARANCE, nt=96, nz_per_pitch=24)
    Vh, Fh = hex_prism(s_af, -k, 0.0)
    vb = VisualBuilder()
    vb.add(Vs, Fs, "finish", uv_cylindrical(Vs, Fs, "z", vscale=100.0))
    vb.add(Vh, Fh, "finish", uv_box(Vh, Fh, 60.0))
    _, subsets = vb.write(stage, f"{R}/Visual/{name}_mesh", R, variant_mats=("finish",))
    _finish(stage, root, None, subsets, finish)
    m, com, inertia = _combined_mass([(Vs, Fs), (Vh, Fh)])
    ev, q = inertia_principal(inertia)
    rigid_body(root, m, com, ev, q)
    collider_cylinder(stage, f"{R}/Collision/core", (0, 0, L / 2), prof["d3"] / 2 - CLEARANCE, L / 2, "Z", pmat=steel)
    collider_hull(stage, f"{R}/Collision/head", Vh[:12], pmat=steel)
    pieces = segments(prof, 0.0, L, CLEARANCE, "bolt", SEG_DEG)
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
            acrossFlats=s_af,
            headHeight=k,
            propertyClass="8.8",
            finishes=FINISHES,
            threadClearance=CLEARANCE,
            dimensionsStatus="nominal",
            mass=m,
            compatibleWith=[nut_name(size), washer_name(size)],
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
    return dict(name=name, kind="screw", size=size, length_mm=length, mass_g=m * 1e3, colliders=len(pieces) + 2)


def write_nut(path, size="M8", finish="zinc_clear"):
    """Hex nut, z from 0 to its height, threaded along +Z."""
    t = METRIC[size]
    d, P, s_af, H = t["d"] * MM, t["P"] * MM, t["s"] * MM, t["m"] * MM
    name = nut_name(size)
    R = f"/{name}"
    prof = iso_profile(d, P)
    stage, root = new_stage(path, name)
    steel = physics_material(stage, R, "steel", STEEL_FRICTION)
    V, F = nut_mesh(prof, s_af, H, CLEARANCE, nt=96, nz_per_pitch=24)
    vb = VisualBuilder()
    vb.add(V, F, "finish", uv_cylindrical(V, F, "z", vscale=100.0))
    _, subsets = vb.write(stage, f"{R}/Visual/{name}_mesh", R, variant_mats=("finish",))
    _finish(stage, root, None, subsets, finish)
    _, m, com, inertia = mesh_mass_props(V, F, RHO_STEEL)
    ev, q = inertia_principal(inertia)
    rigid_body(root, m, com, ev, q)
    pieces = segments(prof, 0.0, H, CLEARANCE, "nut", SEG_DEG, s_af=s_af)
    for i, pts in enumerate(pieces):
        collider_hull(stage, f"{R}/Collision/piece_{i:04d}", pts, pmat=steel)
    set_attrs(
        root,
        dict(
            category="nut",
            standard="ISO 4032",
            designation=f"ISO 4032 - {size}",
            size=size,
            pitch=P,
            majorDiameter=d,
            height=H,
            acrossFlats=s_af,
            propertyClass="8",
            finishes=FINISHES,
            threadClearance=CLEARANCE,
            dimensionsStatus="nominal",
            mass=m,
            compatibleWith=[f"ISO4017_{size}", washer_name(size)],
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
    return dict(name=name, kind="nut", size=size, mass_g=m * 1e3, colliders=len(pieces))


def washer_mesh(d1, d2, h, n=96):
    c = min(0.15 * h, 0.2 * (d2 - d1) / 2)  # small edge break on the outer rim
    prof = [(d1 / 2, 0), (d2 / 2 - c, 0), (d2 / 2, c), (d2 / 2, h - c), (d2 / 2 - c, h), (d1 / 2, h), (d1 / 2, 0)]
    return revolve_profile(np.asarray(prof), n)


def write_washer(path, size="M8", finish="zinc_clear", sectors=24):
    """Plain washer, z from 0 to its thickness. Collision: `sectors` convex ring sectors."""
    d1, d2, h = (x * MM for x in METRIC[size]["washer"])
    name = washer_name(size)
    R = f"/{name}"
    stage, root = new_stage(path, name)
    steel = physics_material(stage, R, "steel", STEEL_FRICTION)
    V, F = washer_mesh(d1, d2, h)
    vb = VisualBuilder()
    vb.add(V, F, "finish", uv_cylindrical(V, F, "z", vscale=100.0))
    _, subsets = vb.write(stage, f"{R}/Visual/{name}_mesh", R, variant_mats=("finish",))
    _finish(stage, root, None, subsets, finish)
    _, m, com, inertia = mesh_mass_props(V, F, RHO_STEEL)
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
        collider_hull(stage, f"{R}/Collision/sector_{i:02d}", np.array(pts), pmat=steel)
    set_attrs(
        root,
        dict(
            category="washer",
            standard="ISO 7089",
            designation=f"ISO 7089 - {size}",
            size=size,
            innerDiameter=d1,
            outerDiameter=d2,
            thickness=h,
            finishes=FINISHES,
            dimensionsStatus="nominal",
            mass=m,
            compatibleWith=[f"ISO4017_{size}", nut_name(size)],
        ),
    )
    mate_frame(stage, f"{R}/MateFrame_bore", (0, 0, 0), (1, 0, 0, 0), dict(role="bore", diameter=d1, axis="+Z"))
    _save(stage)
    return dict(name=name, kind="washer", size=size, mass_g=m * 1e3, colliders=sectors)
