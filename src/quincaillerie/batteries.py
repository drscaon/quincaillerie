"""Battery cells and their holders as OpenUSD assets.

Three holder families:

* cradle: cylindrical cells (AAA, AA, C, D, CR123A, 18650, 21700); a coil spring pushes on the
  - end, the + end rests on a contact plate;
* nine_volt: the 9V (PP3) block, coil spring at the back and a terminal block with two slots sized to
  the two snap terminals, so a reversed battery cannot seat (mechanical keying);
* coin: coin and button cells (CR2032, LR44), slid under a hinged leaf-spring clip.

Each cell and each holder is its own file. A holder is a base (a rigid body of ABS, or a fixed
kinematic body with fixed_base=True: it stays where it is placed and can be animated) and a moving
contact (spring plate or clip) jointed to it.
The spring is the joint's drive: a prismatic joint with a linear drive (N/m), or a revolute joint with
an angular drive (N.m per degree, the UsdPhysics unit). The underside of a holder is at z = 0 of the
asset, so it sits on a floor where it is placed; its seat is on top of its 2 mm floor.
"""

from __future__ import annotations

import numpy as np

from .catalog import CELLS
from .usd import (
    VisualBuilder,
    box_inertia,
    box_mesh,
    collider_cube,
    collider_cylinder,
    finish_variants,
    fix_typeless,
    lib_material,
    mate_frame,
    mesh,
    new_stage,
    physics_material,
    physx_tune,
    prismatic_joint,
    q2m,
    quat_axis_angle,
    revolute_joint,
    revolve_profile,
    rigid_body,
    set_attrs,
    uv_box,
    uv_cylindrical,
    uv_planar,
    xform,
)

MM = 1e-3
G_STEEL = 79e9  # shear modulus of spring steel (Pa)
ABS_DENSITY = 1050.0  # kg/m3
FLOOR_T = 2.0  # mm, thickness of the holder floor (below the seat)
FRICTION = 0.3
CONTACT_OFFSET = 0.0005  # PhysX contact offset (m)


def m(*v):
    """mm -> m tuple."""
    return tuple(np.asarray(v, float) * MM)


def spring_design(F, pre, Dm, n=4):
    """Coil spring giving force F (N) at compression pre (mm), mean diameter Dm (mm), n active coils.

    Returns the stiffness (N/m) and the wire diameter (mm) from k = G d^4 / (8 D^3 n)."""
    k = F / (pre * MM)
    d = (k * 8 * (Dm * MM) ** 3 * n / G_STEEL) ** 0.25
    return k, d / MM


def holder_design(name):
    """Every number of a holder's design (mm unless stated), shared by the asset and the tests."""
    c = CELLS[name]
    kind = c["kind"]
    out = dict(name=name, kind=kind)
    if kind in ("cradle", "nine_volt"):
        L = c["L"]
        half_h = c["d"] / 2 if kind == "cradle" else c["T"] / 2
        x_pos, x_seat = L / 2, -L / 2
        pre = c["pre"]
        x_free = x_seat + pre
        Dm = max(5.0, 0.45 * (c["d"] if kind == "cradle" else c["T"]))
        k, dw = spring_design(c["F"], pre, Dm)
        Ls = 0.6 * Dm + 3.0  # seated spring length
        x_back = x_seat - 1.0 - Ls
        width = (half_h if kind == "cradle" else c["W"] / 2) + 1.5
        out.update(
            L=L,
            half_h=half_h,
            x_pos=x_pos,
            x_seat=x_seat,
            pre=pre,
            x_free=x_free,
            Dm=Dm,
            k=k,
            wire=dw,
            Ls=Ls,
            x_back=x_back,
            travel=Ls - 1.0,
            width=width,
            x_lo=x_back - 2,
            x_hi=x_pos + (6 if kind == "nine_volt" else 4),
            axis="x",
        )
    else:
        r, h = c["d"] / 2, c["h"]
        xp, zp, t, delta = r + 2.0, h + 1.5, 0.3, 0.3  # clip pivot, plate thickness, interference
        alpha = np.arctan((zp - t / 2 - h + delta) / xp)
        theta0 = 0.12  # preload angle against the stop (rad)
        # the plate slopes down towards -x and touches the cell top at its front end, 0.3 r past the
        # centre: that is the lever arm, and the lift needed to clear the cell
        lever = xp + 0.3 * r
        q_seat = (delta + 0.3 * r * np.tan(alpha)) / lever
        out.update(
            r=r,
            h=h,
            cap_h=0.4,
            Rw=r + 0.3,
            xp=xp,
            zp=zp,
            t=t,
            delta=delta,
            alpha=alpha,
            Lc=(xp + 0.3 * r) / np.cos(alpha),
            gam=np.radians(35),
            Ll=3.5,
            theta0=theta0,
            q_seat=q_seat,
            lever=lever,
            kth=c["F"] * lever * MM / (theta0 + q_seat),
            axis="z",
        )
    return out


def insertion_keys(name):
    """Scripted insertion of a cell into its holder: (time s, point mm, tilt deg) keys, release time,
    end time. Cradles: the point is the spring-side end of the cell; coins: the cell centre.
    Heights are measured from the seat (the top of the holder floor)."""
    D = holder_design(name)
    if D["axis"] == "x":
        L, hh, x_free, x_seat, x_pos = D["L"], D["half_h"], D["x_free"], D["x_seat"], D["x_pos"]
        th = 35.0
        x3 = min(x_seat - 1.25, x_pos - np.hypot(L, hh) - 1.2)
        keys = [
            (0.0, (x_free + 0.1 * L, 0, hh + 0.75 * L), th),
            (0.5, (x_free + 0.75, 0, hh + 2.25), th),
            (1.0, (x_seat - 1.0 + hh * np.sin(np.radians(th)), 0, hh + 0.75), th),
            (1.6, (x3, 0, hh + 0.35), 0.0),
            (1.8, (x3, 0, hh + 0.15), 0.0),
        ]
        return dict(keys=keys, t_release=1.8, T=3.5)
    r, h = D["r"], D["h"]
    keys = [
        (0.0, (-r - 15, 0, h / 2 + 10), 0.0),
        (0.6, (-r - 6, 0, h / 2 + 0.08), 0.0),
        (0.8, (-r - 6, 0, h / 2 + 0.05), 0.0),
        (1.8, (-0.3, 0, h / 2 + 0.05), 0.0),
        (1.9, (-0.3, 0, h / 2 + 0.03), 0.0),
    ]
    return dict(keys=keys, t_release=1.9, T=3.0)


def key_pose(name, p, theta):
    """Cell centre (m, in the holder frame) and quaternion for a key point (mm) and tilt (deg)."""
    D = holder_design(name)
    p = np.asarray(p, float) * MM + np.array([0, 0, FLOOR_T * MM])
    if D["axis"] == "z":
        return p, np.array([1.0, 0, 0, 0])
    th = np.radians(theta)
    c = p + np.array([np.cos(th), 0, np.sin(th)]) * D["L"] * MM / 2
    return c, np.array([np.cos(th / 2), 0, -np.sin(th / 2), 0])


# ----------------------------------------------------------------------------------- cells
def write_cell(path, name):
    c = CELLS[name]
    kind = c["kind"]
    root_name = f"Cell_{name}"
    stage, root = new_stage(path, root_name)
    R = f"/{root_name}"
    pm = physics_material(stage, R, "cell", FRICTION)
    mass = c["mass"] * 1e-3
    vb = VisualBuilder()
    if kind == "cradle":
        L, r, nr, nh = c["L"], c["d"] / 2, c["nub_d"] / 2, c["nub_h"]
        h1 = L / 2 - nh
        parts = [
            ("nickel_can", [(0, -L / 2), (r - 0.4, -L / 2), (r, -L / 2 + 0.4), (r, -L / 2 + 0.8)], None),
            (
                f"wrapper_{name}",
                [(r + 0.02, -L / 2 + 0.8), (r + 0.02, h1 - 2.0)],
                ((-L / 2 + 0.8) * MM, (h1 - 2.0) * MM),
            ),
            ("nickel_can", [(r, h1 - 2.0), (r, h1 - 0.5), (r - 0.5, h1), (nr + 0.6, h1)], None),
            ("nickel_can", [(nr + 0.6, h1), (nr, h1), (nr, h1 + nh - 0.2), (nr - 0.3, h1 + nh), (0, h1 + nh)], None),
        ]
        for mat, prof, along in parts:
            V, F = revolve_profile(np.asarray(prof) * MM, 96, axis="x")
            uv = uv_cylindrical(V, F, "x", along=along) if along else uv_cylindrical(V, F, "x", vscale=100.0)
            vb.add(V, F, mat, uv, 40)
        collider_cylinder(stage, f"{R}/Collision/can", m(-nh / 2, 0, 0), r * MM, (L - nh) / 2 * MM, "X", pmat=pm)
        collider_cylinder(stage, f"{R}/Collision/nub", m(L / 2 - nh / 2, 0, 0), nr * MM, nh / 2 * MM, "X", pmat=pm)
        rr, LL = r * MM, L * MM
        rigid_body(
            root,
            mass,
            (0, 0, 0),
            (0.5 * mass * rr**2, mass * (3 * rr**2 + LL**2) / 12, mass * (3 * rr**2 + LL**2) / 12),
        )
        mate_frame(stage, f"{R}/MateFrame_plus", m(L / 2, 0, 0), (1, 0, 0, 0), dict(role="terminal", polarity="+"))
        mate_frame(stage, f"{R}/MateFrame_minus", m(-L / 2, 0, 0), (0, 0, 0, 1), dict(role="terminal", polarity="-"))
        dims = dict(diameter=c["d"] * MM, length=L * MM)
    elif kind == "nine_volt":
        L, W, T = c["L"], c["W"], c["T"]
        V, F = box_mesh(m(L / 2, W / 2, T / 2))
        vb.add(V, F, "case_9V", uv_box(V, F, 60.0), 30)
        V, F = box_mesh(m(L * 0.35, W / 2 + 0.02, T / 2 - 2))
        V = V + np.array(m(-L * 0.1, 0, 0))
        P = V[F].reshape(-1, 3)
        uvl = np.c_[(P[:, 0] - V[:, 0].min()) / np.ptp(V[:, 0]), (P[:, 2] - V[:, 2].min()) / np.ptp(V[:, 2])]
        vb.add(V, F, "label_9V", uvl, 30)
        collider_cube(stage, f"{R}/Collision/can", (0, 0, 0), m(L / 2, W / 2, T / 2), pmat=pm)
        for nm, yy, rr in (("plus_snap", 6.35, 3.0), ("minus_snap", -6.35, 4.0)):
            V, F = revolve_profile(np.asarray([(0, 0), (rr, 0), (rr, 3.0), (0, 3.0)]) * MM, 48, axis="x")
            V = V + np.array(m(L / 2, yy, 0))
            vb.add(V, F, "nickel_bright", uv_box(V, F, 200.0), 40)
            collider_cylinder(stage, f"{R}/Collision/{nm}", m(L / 2 + 1.5, yy, 0), rr * MM, 1.5 * MM, "X", pmat=pm)
        Lm, Wm, Tm = L * MM, W * MM, T * MM
        rigid_body(
            root,
            mass,
            (0, 0, 0),
            (mass * (Wm**2 + Tm**2) / 12, mass * (Lm**2 + Tm**2) / 12, mass * (Lm**2 + Wm**2) / 12),
        )
        mate_frame(
            stage,
            f"{R}/MateFrame_plus",
            m(L / 2 + 3, 6.35, 0),
            (1, 0, 0, 0),
            dict(role="terminal", polarity="+", snap="male"),
        )
        mate_frame(
            stage,
            f"{R}/MateFrame_minus",
            m(L / 2 + 3, -6.35, 0),
            (1, 0, 0, 0),
            dict(role="terminal", polarity="-", snap="female"),
        )
        dims = dict(length=L * MM, width=W * MM, thickness=T * MM)
    else:  # coin, + face up
        r, h = c["d"] / 2, c["h"]
        cap_h, cr = 0.4, 0.8 * r
        prof = [(cr, -h / 2), (r - 0.3, -h / 2 + cap_h), (r, -h / 2 + cap_h + 0.3), (r, h / 2 - 0.2), (r - 0.2, h / 2)]
        V, F = revolve_profile(np.asarray(prof) * MM, 128)
        vb.add(V, F, "nickel_can", uv_cylindrical(V, F, "z", vscale=100.0), 40)
        V, F = revolve_profile(np.asarray([(r - 0.2, h / 2), (0, h / 2)]) * MM, 128)
        vb.add(V, F, f"coin_top_{name}", uv_planar(V, F, (r - 0.2) * MM), 40)
        V, F = revolve_profile(np.asarray([(0, -h / 2), (cr, -h / 2)]) * MM, 128)
        vb.add(V, F, "stainless_a2", uv_planar(V, F, cr * MM), 40)
        collider_cylinder(stage, f"{R}/Collision/can", m(0, 0, cap_h / 2), r * MM, (h - cap_h) / 2 * MM, "Z", pmat=pm)
        collider_cylinder(stage, f"{R}/Collision/cap", m(0, 0, -(h - cap_h) / 2), cr * MM, cap_h / 2 * MM, "Z", pmat=pm)
        rr, hh = r * MM, h * MM
        rigid_body(
            root,
            mass,
            (0, 0, 0),
            (mass * (3 * rr**2 + hh**2) / 12, mass * (3 * rr**2 + hh**2) / 12, 0.5 * mass * rr**2),
        )
        mate_frame(stage, f"{R}/MateFrame_plus", m(0, 0, h / 2), (1, 0, 0, 0), dict(role="terminal", polarity="+"))
        mate_frame(stage, f"{R}/MateFrame_minus", m(0, 0, -h / 2), (0, 1, 0, 0), dict(role="terminal", polarity="-"))
        dims = dict(diameter=c["d"] * MM, height=h * MM)
    vb.write(stage, f"{R}/Visual/{root_name}_mesh", R)
    set_attrs(
        root,
        dict(
            category="cell",
            format=name,
            iec=c["iec"],
            nominalVoltage=c["volts"],
            dimensionsStatus="nominal",
            massStatus="typical",
            mass=mass,
            compatibleWith=[f"Holder_{name}"],
            **dims,
        ),
    )
    physx_tune(stage, CONTACT_OFFSET, 16, 0.1)
    fix_typeless(stage)
    stage.GetRootLayer().Save()
    return dict(name=root_name, kind="cell", format=name, mass_g=c["mass"])


# --------------------------------------------------------------------------------- holders
def tube_mesh(pts, rad, sides=10):
    """Closed tube of radius rad along a polyline (parallel-transport frames)."""
    P = np.asarray(pts, float)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    a = np.array([0, 0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0, 0])
    x = np.cross(T[0], a)
    x /= np.linalg.norm(x)
    rings = []
    th = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    for i in range(len(P)):
        x = x - T[i] * (x @ T[i])
        x /= np.linalg.norm(x)
        y = np.cross(T[i], x)
        rings.append(P[i] + rad * (np.cos(th)[:, None] * x + np.sin(th)[:, None] * y))
    V = np.vstack(rings)
    F = []
    for i in range(len(P) - 1):
        for j in range(sides):
            a0 = i * sides + j
            b0 = i * sides + (j + 1) % sides
            F += [[a0, b0, b0 + sides], [a0, b0 + sides, a0 + sides]]
    n0 = len(V)
    V = np.vstack([V, P[0], P[-1]])
    k = (len(P) - 1) * sides
    for j in range(sides):
        F.append([n0, (j + 1) % sides, j])
        F.append([n0 + 1, k + j, k + (j + 1) % sides])
    return V, np.array(F)


def write_holder(path, name, fixed_base=False):
    c = CELLS[name]
    kind = c["kind"]
    D = holder_design(name)
    root_name = f"Holder_{name}"
    stage, root = new_stage(path, root_name)
    R = f"/{root_name}"
    B = f"{R}/base"
    xform(stage, B, m(0, 0, FLOOR_T))
    pm = physics_material(stage, R, "holder", FRICTION)
    vb = VisualBuilder()
    boxes = []  # (centre, half) in metres, for the base mass

    def solid(nm, center, half, look="plastic", quat=(1, 0, 0, 0)):
        collider_cube(stage, f"{B}/Collision/{nm}", m(*center), m(*half), quat, pmat=pm)
        V, F = box_mesh(m(*half))
        V = V @ q2m(quat).T + np.asarray(m(*center))
        vb.add(V, F, look, uv_box(V, F, 250.0 if look == "plastic" else 60.0), 30)
        boxes.append((np.asarray(m(*center)), np.asarray(m(*half))))

    if kind in ("cradle", "nine_volt"):
        hh, width, x_lo, x_hi = D["half_h"], D["width"], D["x_lo"], D["x_hi"]
        x_pos, x_back, x_free, k = D["x_pos"], D["x_back"], D["x_free"], D["k"]
        solid("floor", ((x_lo + x_hi) / 2, 0, -1), ((x_hi - x_lo) / 2, width + 2, 1))
        wall_h = 0.62 * 2 * hh
        solid("wall_l", ((x_lo + x_hi) / 2, width + 1, wall_h / 2), ((x_hi - x_lo) / 2, 1, wall_h / 2))
        solid("wall_r", ((x_lo + x_hi) / 2, -(width + 1), wall_h / 2), ((x_hi - x_lo) / 2, 1, wall_h / 2))
        solid("back_wall", (x_back - 1, 0, 0.95 * hh), (1, width, 0.95 * hh))
        if kind == "cradle":
            solid("plus_plate", (x_pos + 1, 0, 0.83 * hh), (1, width - 0.5, 0.83 * hh), "nickel_bright")
            solid("plus_back", (x_pos + 3, 0, 0.83 * hh), (1, width, 0.83 * hh))
        else:
            zc = hh
            yA, rA, yB, rB = 6.35, 3.0, -6.35, 4.0  # + snap (small) and - snap (large)
            wA, wB = rA + 0.3, rB + 0.3
            top = zc + 5.0
            x0, x1 = x_pos, x_pos + 4
            cx, hx = (x0 + x1) / 2, (x1 - x0) / 2
            ys = [-width, yB - wB, yB + wB, yA - wA, yA + wA, width]
            for i, (a, b) in enumerate(((0, 1), (2, 3), (4, 5))):
                solid(f"term_s{i}", (cx, (ys[a] + ys[b]) / 2, top / 2), (hx, (ys[b] - ys[a]) / 2, top / 2))
            bB, bA = zc - rB - 0.3, zc - rA - 0.3
            solid("slot_minus", (cx, yB, bB / 2), (hx, wB, bB / 2), "nickel_bright")
            solid("slot_plus", (cx, yA, bA / 2), (hx, wA, bA / 2), "nickel_bright")
            solid("term_end", (x1 + 1, 0, top / 2), (1, width, top / 2))
        # spring plate: rigid body on a prismatic joint whose linear drive is the coil spring
        sp = xform(stage, f"{R}/spring_plate", m(x_free, 0, hh + FLOOR_T))
        psize = (1.0, 2 * (width - 1), 1.6 * hh)
        rigid_body(sp.GetPrim(), 0.001, m(-0.5, 0, 0), box_inertia(0.001, m(*psize)))
        collider_cube(
            stage, f"{R}/spring_plate/Collision/minus_plate", m(-0.5, 0, 0), m(0.5, width - 1, 0.8 * hh), pmat=pm
        )
        pv = VisualBuilder()
        V, F = box_mesh(m(0.5, width - 1, 0.8 * hh))
        V = V + np.array(m(-0.5, 0, 0))
        pv.add(V, F, "nickel_bright", uv_box(V, F, 60.0), 30)
        pv.write(stage, f"{R}/spring_plate/Visual/spring_plate_mesh", R)
        prismatic_joint(
            stage,
            f"{R}/Joints/spring",
            f"{R}/spring_plate",
            "X",
            m(x_free, 0, hh),
            k,
            0.05 * k**0.5,
            0.0,
            -(D["pre"] + D["travel"]) * MM,
            0.5 * MM,
            body0=B,
        )
        # coil (visual only), drawn at its free length (empty holder)
        rc, rw, turns = D["Dm"] / 2, max(D["wire"] / 2, 0.3), 6.0
        tt = np.linspace(0, turns * 2 * np.pi, 420)
        s = tt / (2 * np.pi)
        Lc = (x_free - 1) - x_back - 2 * rw
        xs = np.where(
            s < 1,
            s * 2 * rw,
            np.where(s > turns - 1, Lc - (turns - s) * 2 * rw, 2 * rw + (s - 1) / (turns - 2) * (Lc - 4 * rw)),
        )
        pts = np.c_[x_back + rw + xs, rc * np.cos(tt), hh + rc * np.sin(tt)]
        V, F = tube_mesh(pts, rw, 10)
        coil = mesh(
            stage,
            f"{B}/Visual/spring_coil",
            V * MM,
            F,
            lib_material(stage, R, "spring_steel"),
            uv=uv_cylindrical(V * MM, F, "x", vscale=200.0),
        )
        set_attrs(
            coil.GetPrim(),
            dict(
                wireDiameter=D["wire"] * MM,
                meanDiameter=D["Dm"] * MM,
                activeCoils=4,
                totalCoils=6,
                freeLengthEnd=x_free * MM,
                backFace=x_back * MM,
                stiffness=k,
                note="visual only; follows the spring_plate (stretch along X between backFace and the plate)",
            ),
        )
        info = dict(springStiffness=k, springPreload=D["pre"] * MM, springWire=D["wire"] * MM, contactForce=c["F"])
        mate_frame(
            stage,
            f"{B}/MateFrame_seat",
            (0, 0, hh * MM),
            (1, 0, 0, 0),
            dict(role="cell_seat", axis="+X towards the + contact", cellCentre=True),
        )
    else:
        r, h, Rw = D["r"], D["h"], D["Rw"]
        solid("floor", (-r * 0.6, 0, -1), (r * 1.6 + 4, Rw + 2.5, 1))
        V, F = box_mesh(m(r * 0.35, r * 0.35, 0.02))
        V = V + np.array(m(0, 0, 0.01))
        vb.add(V, F, "nickel_bright", uv_box(V, F, 60.0), 30)
        wall_h = h + 0.6
        for i, a in enumerate(np.radians(np.arange(-80, 81, 16))):
            solid(
                f"ring{i}",
                ((Rw + 0.75) * np.cos(a), (Rw + 0.75) * np.sin(a), wall_h / 2),
                (0.75, Rw * np.tan(np.radians(8)) + 0.15, wall_h / 2),
                quat=quat_axis_angle((0, 0, 1), a),
            )
        for sy in (1, -1):
            solid(
                f"rail{'l' if sy > 0 else 'r'}",
                (-r * 0.9, sy * (Rw + 0.75), wall_h / 2),
                (r * 0.9 + 1, 0.75, wall_h / 2),
            )
        xp, zp, t, alpha, Lc = D["xp"], D["zp"], D["t"], D["alpha"], D["Lc"]
        gam, Ll, theta0, kth = D["gam"], D["Ll"], D["theta0"], D["kth"]
        u = np.array([-np.cos(alpha), 0, -np.sin(alpha)])
        pc = u * Lc / 2
        front = u * Lc
        v = np.array([-np.cos(gam), 0, np.sin(gam)])
        pl = front + v * Ll / 2
        solid("clip_post", (xp + 1.2, 0, zp / 2 + 0.3), (1.0, 0.25 * r + 0.5, zp / 2 + 0.3))
        cl = xform(stage, f"{R}/clip", m(xp, 0, zp + FLOOR_T))
        cm = 0.0004
        rigid_body(cl.GetPrim(), cm, m(*pc), box_inertia(cm, m(Lc, 0.5 * r, t)), quat_axis_angle((0, 1, 0), -alpha))
        cv = VisualBuilder()
        for nm, cc, hh3, qq in (
            ("clip_plate", pc, (Lc / 2, 0.25 * r, t / 2), quat_axis_angle((0, 1, 0), -alpha)),
            ("clip_lead", pl, (Ll / 2, 0.25 * r, t / 2), quat_axis_angle((0, 1, 0), gam)),
        ):
            collider_cube(stage, f"{R}/clip/Collision/{nm}", m(*cc), m(*hh3), qq, pmat=pm)
            V, F = box_mesh(m(*hh3))
            V = V @ q2m(qq).T + np.asarray(m(*cc))
            cv.add(V, F, "nickel_bright", uv_box(V, F, 60.0), 30)
        cv.write(stage, f"{R}/clip/Visual/clip_mesh", R)
        d2r = np.pi / 180
        revolute_joint(
            stage,
            f"{R}/Joints/clip",
            f"{R}/clip",
            "Y",
            m(xp, 0, zp),
            kth * d2r,
            kth * 0.002 * d2r,
            -np.degrees(theta0),
            0.0,
            30.0,
            body0=B,
        )
        info = dict(clipTorsionStiffness=kth, clipPreloadAngle=theta0, contactForce=c["F"])
        mate_frame(
            stage, f"{B}/MateFrame_seat", (0, 0, h / 2 * MM), (1, 0, 0, 0), dict(role="cell_seat", axis="+Z = + face")
        )
    _, subsets = vb.write(stage, f"{B}/Visual/{root_name}_base_mesh", R, variant_mats=("plastic",))
    # base: mass and inertia of its ABS boxes
    vols = np.array([8 * np.prod(hb) for _, hb in boxes])
    cen = np.array([cb for cb, _ in boxes])
    halves = np.array([hb for _, hb in boxes])
    mb = ABS_DENSITY * vols.sum()
    com = (cen * vols[:, None]).sum(0) / vols.sum()
    ext = np.ptp(np.vstack([cen - halves, cen + halves]), axis=0)
    rigid_body(stage.GetPrimAtPath(B), mb, com, box_inertia(mb, ext), kinematic=fixed_base)
    finish_variants(stage, root, [subsets["plastic"]], ["abs_black", "abs_grey"], "abs_black")
    set_attrs(
        root,
        dict(
            category="holder",
            format=name,
            family=kind,
            dimensionsStatus="generic design",
            compatibleWith=[f"Cell_{name}"],
            seatHeight=FLOOR_T * MM,
            **info,
        ),
    )
    physx_tune(stage, CONTACT_OFFSET, 16, 0.1)
    fix_typeless(stage)
    stage.GetRootLayer().Save()
    return dict(name=root_name, kind="holder", format=name, family=kind)
