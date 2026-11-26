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
from .catalog import METRIC, bolt_name, cap_screw_name, nut_name, screw_name, washer_name
from .contract import write_labels
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
    rest_on_floor,
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


def _save(stage, kind):
    """Label the part, save it and write its PhysX layer beside it (a thread needs many solver
    iterations)."""
    root = stage.GetDefaultPrim()
    write_labels(root, (kind, root.GetAttribute("primvaria:preset").Get()))
    stage.GetDefaultPrim().CreateAttribute(physx.ASKED, Sdf.ValueTypeNames.Float).Set(CONTACT_OFFSET)
    rest_on_floor(stage)  # its underside at z = 0 of the asset (contract, section 3)
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


def under_head(size, v, kind="screw", length=None, property_class=None):
    """The applied sizes under the head (and a bolt's shank), in mm: the drawn values, or the middle
    of the cited range for a part built without a sampler. Written back into v, so that the
    recorded values are the ones the part is built with."""
    from dataclasses import replace

    from .variation import head_columns, tolerance_range

    filled = {}
    for column in head_columns(kind, size, length):
        if getattr(v, column) is None:
            lo, hi = tolerance_range(kind, column, size, length, property_class)
            filled[column] = round((lo + hi) / 2, 6)
    return replace(v, **filled) if filled else v


def _solid(radius, z0, z1, n):
    """Closed cylinder from z0 to z1: V, F."""
    return revolve_profile([(0.0, z1), (0.0, z0), (radius, z0), (radius, z1), (0.0, z1)], n)


def _fillet(r_in, r, n):
    """The fillet between the head (at z = 0) and the shank (radius r_in), as a ring of triangular
    section: its outer edge on the bearing face at r_in + r, its top on the shank at z = r. A straight
    line stands for the arc (an estimate; the arc's volume differs by under a fifth of this ring's)."""
    return revolve_profile([(r_in, r), (r_in, 0.0), (r_in + r, 0.0), (r_in, r)], n)


def _hex_radius(theta, s_af):
    """Distance from the axis to a hexagon of across flats s_af at angle theta, its corners at
    30 + 60 k degrees (as hex_prism's)."""
    phi = ((np.asarray(theta) + np.pi / 6) % (np.pi / 3)) - np.pi / 6  # 0 on a flat's normal
    return (s_af / 2) / np.cos(phi)


def cap_head_mesh(dk, k, s_af, t, v, dw, n=72):
    """Closed mesh of an ISO 4762 head, from z=-k (its top) to 0 (its underside): a cylinder of
    diameter dk with its top edge chamfered by v, its bottom edge rounded in to the bearing circle
    dw (a 45 degree chamfer stands for the rounding), and a hex socket of across flats s_af and depth
    t ending in a 120 degree cone, as a drill leaves it. n: sides (a multiple of 12, so that the
    hexagon's corners are vertices)."""
    n = int(np.ceil(n / 12) * 12)
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    eh = (dk - dw) / 2  # height of the rounding under the head
    apex = s_af / 3  # depth of a 120 degree cone over the socket's corners: (s / sqrt 3) / tan 60
    rows = []
    for a in th:
        rh = float(_hex_radius(a, s_af))
        rows.append(
            [
                (0.0, 0.0),
                (dw / 2, 0.0),
                (dk / 2, -eh),
                (dk / 2, -k + v),
                (dk / 2 - v, -k),
                (rh, -k),
                (rh, -k + t),
                (0.0, -k + t + apex),
            ]
        )
    K = len(rows[0])
    V = np.array([[r * np.cos(a), r * np.sin(a), z] for a, row in zip(th, rows, strict=True) for r, z in row])
    F = []
    for i in range(n):
        j = (i + 1) % n
        for q in range(K - 1):
            a_, b_, c_, d_ = i * K + q, j * K + q, j * K + q + 1, i * K + q + 1
            F += [[a_, b_, c_], [a_, c_, d_]]
    F = np.array(F)
    A = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    F = F[A > 1e-18]
    if mesh_mass_props(V, F, 1.0)[0] < 0:  # outward normals
        F = F[:, ::-1]
    return V, F


def cap_head_colliders(dk, k, s_af, t, v, dw, arc=8):
    """Convex pieces of an ISO 4762 head: the solid part under the socket (from the socket's floor
    to the bearing circle), and six walls around the socket, each between one flat of the hexagon
    and the arc of the head outside it. A hex key goes into the socket as deep as t."""
    eh = (dk - dw) / 2
    ring = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    solid = [
        [r * np.cos(a), r * np.sin(a), z] for r, z in ((dk / 2, -k + t), (dk / 2, -eh), (dw / 2, 0.0)) for a in ring
    ]
    walls = []
    R = s_af / np.sqrt(3)
    for j in range(6):
        a0 = np.pi / 6 + j * np.pi / 3
        arcs = np.linspace(a0, a0 + np.pi / 3, arc)
        pts = [[R * np.cos(a), R * np.sin(a), z] for a in (a0, a0 + np.pi / 3) for z in (-k, -k + t)]
        pts += [[dk / 2 * np.cos(a), dk / 2 * np.sin(a), z] for a in arcs for z in (-k + v, -k + t)]
        pts += [[(dk / 2 - v) * np.cos(a), (dk / 2 - v) * np.sin(a), -k] for a in arcs]
        walls.append(np.array(pts))
    return np.array(solid), walls


def write_screw(
    path,
    size="M8",
    length=None,
    finish="zinc_clear",
    v=None,
    name=None,
    detail="normal",
    collider="thread",
    kind="screw",
    property_class=None,
):
    """Hex head screw (ISO 4017, threaded to the head), bolt (kind="bolt": ISO 4014, a plain shank
    under the head, then the thread) or socket head cap screw (kind="cap_screw": ISO 4762, threaded
    to the head up to its size's full_to length, with a plain shank beyond), axis +Z. Built with the
    head from z=-k to 0 and the shank from 0 to the length, then moved up by k when saved: in the
    file it stands on its head, its underside at z = 0 (contract, section 3).

    collider: "thread" (the helix, in convex pieces) or "simple" (a cylinder at the major diameter)."""
    simple = _collider(collider) == "simple"
    from .catalog import CAP_SCREW, DEFAULT_BOLT_LENGTH, DEFAULT_LENGTH, DEFAULT_PROPERTY_CLASS, has_plain_shank

    cap = kind == "cap_screw"
    v = v or FastenerVariation()
    nominal = v == FastenerVariation()
    t = METRIC[size]
    length = float(length or (DEFAULT_BOLT_LENGTH if kind == "bolt" else DEFAULT_LENGTH)[size])
    pclass = (property_class or DEFAULT_PROPERTY_CLASS) if cap else "8.8"
    v = under_head(size, v, kind, length, pclass)
    plain = has_plain_shank(kind, size, length)
    d, P = t["d"] * MM, t["P"] * MM
    if cap:  # the hex is the socket; the head a cylinder of height k max = d
        cs = CAP_SCREW[size]
        s_af = (cs["socket"] + v.across_flats_dmm) * MM
        k = (cs["k"][1] + v.height_dmm) * MM
        dk, depth, chamfer = v.head_d_mm * MM, v.socket_depth_mm * MM, v.top_chamfer_mm * MM
        c = 0.0
    else:
        s_af = (t["s"] + v.across_flats_dmm) * MM
        k = (t["k"] + v.height_dmm) * MM
        c = v.bearing_face_h_mm * MM
    L = (length + v.length_dmm) * MM
    dw, rf = v.bearing_face_d_mm * MM, v.fillet_r_mm * MM
    # a plain shank of diameter ds from the head to Lp, then the thread to the tip
    Lp = v.plain_length_mm * MM if plain else 0.0
    ds = v.shank_d_mm * MM if plain else d
    clearance = v.clearance_mm * MM
    name = name or {"bolt": bolt_name, "cap_screw": cap_screw_name}.get(kind, screw_name)(size, length)
    R = f"/{name}"
    prof = iso_profile(d, P)
    stage, root = new_stage(path, name)
    steel = physics_material(stage, R, "steel", v.friction)
    crush = burr = None
    if v.defect == "crushed_thread":
        crush = (_zone(v, L - Lp, P), _widen(v, P), 0.5 * v.defect_size * (d - prof["d3"]) / 2)
    if v.defect == "burr":
        t0 = (v.defect_z * 37.0) % (2 * np.pi)
        burr = (t0, t0 + np.radians(v.defect_angle_deg), v.defect_size * MM)
    nt, nz = DETAIL[detail]
    Vs, Fs = threaded_bolt_mesh(prof, L - Lp, clearance, nt=nt, nz_per_pitch=nz, crush=crush, burr=burr)
    Vs = Vs + [0.0, 0.0, Lp]
    if cap:
        Vh, Fh = cap_head_mesh(dk, k, s_af, depth, chamfer, dw, nt)
        head = [(Vh, Fh)]
    else:
        Vh, Fh = hex_prism(s_af, -k, -c)
        Vw, Fw = _solid(dw / 2, -c, 0.0, nt)
        head = [(Vh, Fh), (Vw, Fw)]
    # the fillet rests on the thread's crest (threaded to the head) or on the plain shank
    Vf, Ff = _fillet(ds / 2 if plain else d / 2 - clearance, rf, nt)
    shank = [_solid(ds / 2, 0.0, Lp, nt)] if plain else []
    pieces = [] if simple else segments(prof, 0.0, L - Lp, clearance, "bolt", SEG_DEG, crush=crush, burr=burr)
    pieces = [np.asarray(p) + [0.0, 0.0, Lp] for p in pieces]
    # the simple collider is the shank at its major diameter; the core carries the thread pieces
    core_r = (d / 2 if simple else prof["d3"] / 2) - clearance
    if v.defect == "bent":
        Vs = _bend(Vs, v.defect_size, L)
        Vf = _bend(Vf, v.defect_size, L)
        shank = [(_bend(V, v.defect_size, L), F) for V, F in shank]
        pieces = [_bend(p, v.defect_size, L) for p in pieces]
    vb = VisualBuilder()
    vb.add(Vs, Fs, "finish", uv_cylindrical(Vs, Fs, "z", vscale=100.0))
    for V, F in shank:
        vb.add(V, F, "finish", uv_cylindrical(V, F, "z", vscale=100.0))
    vb.add(Vf, Ff, "finish", uv_cylindrical(Vf, Ff, "z", vscale=100.0))
    for V, F in head:
        vb.add(V, F, "finish", uv_box(V, F, 60.0))
    _, subsets = vb.write(stage, f"{R}/Visual/{name}_mesh", R, variant_mats=("finish",))
    _looks(stage, root, name, subsets, finish, v, path)
    m, com, inertia = _combined_mass([(Vs, Fs), *shank, (Vf, Ff), *head], v.density)
    ev, q = inertia_principal(inertia)
    rigid_body(root, m, com, ev, q)

    def radius_at(z):  # of the core collider: the plain shank, then the thread's core
        return ds / 2 if z < Lp else core_r

    slices = 0
    if v.defect == "bent":  # the core follows the bend: stacked convex slices
        n = slices = max(4, int(np.ceil(L / (2 * P))))
        ring = np.linspace(0, 2 * np.pi, 16, endpoint=False)
        for i in range(n):
            za, zb = L * i / n, L * (i + 1) / n
            rr = radius_at((za + zb) / 2)
            pts = [[rr * np.cos(a), rr * np.sin(a), z] for z in (za, zb) for a in ring]
            collider_hull(stage, f"{R}/Collision/core_{i:02d}", _bend(pts, v.defect_size, L), pmat=steel)
    else:
        if plain:
            collider_cylinder(stage, f"{R}/Collision/shank", (0, 0, Lp / 2), ds / 2, Lp / 2, "Z", pmat=steel)
        collider_cylinder(stage, f"{R}/Collision/core", (0, 0, (Lp + L) / 2), core_r, (L - Lp) / 2, "Z", pmat=steel)
    if cap:
        solid, walls = cap_head_colliders(dk, k, s_af, depth, chamfer, dw)
        collider_hull(stage, f"{R}/Collision/head", solid, pmat=steel)
        for j, pts in enumerate(walls):
            collider_hull(stage, f"{R}/Collision/socket_wall_{j}", pts, pmat=steel)
        head_pieces = 1 + len(walls)
    else:
        collider_hull(stage, f"{R}/Collision/head", Vh[:12], pmat=steel)
        collider_cylinder(stage, f"{R}/Collision/bearing_face", (0, 0, -c / 2), dw / 2, c / 2, "Z", pmat=steel)
        head_pieces = 2
    collider_hull(stage, f"{R}/Collision/fillet", Vf, pmat=steel)
    for i, pts in enumerate(pieces):
        collider_hull(stage, f"{R}/Collision/thread_{i:04d}", pts, pmat=steel)
    standard = {"bolt": "ISO 4014", "cap_screw": "ISO 4762"}.get(kind, "ISO 4017")
    extra = dict(plainLength=Lp, shankDiameter=ds, threadLength=L - Lp) if plain else {}
    if cap:
        extra.update(headDiameter=dk, socketDepth=depth, topChamfer=chamfer)
    else:
        extra.update(bearingFaceHeight=c)
    designation = f"{standard} - {size} x {length:g}" + (f" - {pclass}" if cap else "")
    set_attrs(
        root,
        dict(
            category="screw",
            standard=standard,
            designation=designation,
            size=size,
            pitch=P,
            majorDiameter=d,
            length=L,
            nominalLength=length * MM,
            acrossFlats=s_af,
            headHeight=k,
            bearingFaceDiameter=dw,
            filletRadius=rf,
            **extra,
            propertyClass=pclass,
            finishes=FINISHES,
            threadClearance=clearance,
            collision=collider,
            dimensionsStatus="nominal" if nominal else "varied within tolerance",
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
    if cap:  # the socket's mouth on top of the head: a hex key goes in along +Z, as deep as t
        mate_frame(
            stage,
            f"{R}/MateFrame_drive",
            (0, 0, -k),
            (1, 0, 0, 0),
            dict(role="drive", drive="hex_socket", acrossFlats=s_af, engagement=depth),
        )
    else:
        mate_frame(
            stage,
            f"{R}/MateFrame_drive",
            (0, 0, 0),  # where a socket's mouth is when it holds the whole head: the head goes in along +Z
            (0, 1, 0, 0),
            dict(role="drive", drive="external_hex", acrossFlats=s_af, engagement=k),
        )
    _save(stage, kind)
    shank_colliders = 1 if plain and not slices else 0
    return dict(
        name=name,
        kind=kind,
        size=size,
        length_mm=length,
        mass_g=m * 1e3,
        colliders=len(pieces) + head_pieces + 1 + (slices or 1) + shank_colliders,
        **as_attrs(v),
    )


def write_bolt(
    path, size="M8", length=None, finish="zinc_clear", v=None, name=None, detail="normal", collider="thread"
):
    """Hex head bolt, ISO 4014: see write_screw."""
    return write_screw(path, size, length, finish, v, name, detail, collider, kind="bolt")


def write_cap_screw(
    path,
    size="M8",
    length=None,
    finish="black_oxide",
    v=None,
    name=None,
    detail="normal",
    collider="thread",
    property_class=None,
):
    """Hexagon socket head cap screw, ISO 4762: see write_screw."""
    return write_screw(path, size, length, finish, v, name, detail, collider, "cap_screw", property_class)


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
        (0, 0, 0),  # where a socket's mouth is when it holds the whole nut: the nut goes in along +Z
        (1, 0, 0, 0),
        dict(role="drive", drive="external_hex", acrossFlats=s_af, engagement=H),
    )
    _save(stage, "nut")
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
    h += v.height_dmm * MM  # the variation already holds the tighter thickness tolerance
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
    _save(stage, "washer")
    return dict(name=name, kind="washer", size=size, mass_g=m * 1e3, colliders=sectors, **as_attrs(v))
