"""Metric thread geometry (ISO 68-1 basic profile) in NumPy, without a CAD kernel.

All lengths in metres. Right-hand threads: a point of the helix rises z = P * theta / (2 pi).
The visual meshes carry the real profile; the collision geometry is a set of convex pieces
(`segments`), one per 10 degrees of helix, which is what makes physical screwing possible in
engines that only collide convex shapes.
"""

from __future__ import annotations

import numpy as np


def iso_profile(d, P, allowance=0.0):
    """Basic ISO 68-1 dimensions for an M d x P thread (metres)."""
    H = np.sqrt(3) / 2 * P
    return dict(
        d=d,
        P=P,
        H=H,
        d2=d - 0.649519 * P,  # pitch diameter
        d1=d - 1.082532 * P,  # basic minor diameter (nut)
        d3=d - 1.226869 * P,  # bolt minor diameter (ISO 965, rounded root)
        flat_crest=P / 8,
        flat_root=P / 4,
    )


def ext_profile_r(u, prof, clearance):
    """Radius of the external (bolt) thread surface at axial phase u in [0,1) of a pitch.

    Trapezoid: crest flat P/8 at r=d/2, flanks at 60 deg, root flat at d3/2. Shifted
    inward by `clearance` (radial), as a 'g' tolerance position would.
    """
    P = prof["P"]
    R = prof["d"] / 2 - clearance
    r = prof["d3"] / 2 - clearance
    depth = R - r
    flank = depth * np.tan(np.radians(30))  # axial run of a flank (60 degree thread)
    s = (u % 1.0) * P
    crest = P / 8
    # centre crest at s = 0
    s = np.where(s > P / 2, s - P, s)
    a = np.abs(s)
    return np.where(a <= crest / 2, R, np.where(a <= crest / 2 + flank, R - (a - crest / 2) / flank * depth, r))


def int_profile_r(u, prof, clearance):
    """Radius of the internal (nut) thread surface at axial phase u (groove centred at u=0)."""
    P = prof["P"]
    R = prof["d"] / 2 + clearance
    r = prof["d1"] / 2 + clearance
    depth = R - r
    flank = depth * np.tan(np.radians(30))
    s = (u % 1.0) * P
    s = np.where(s > P / 2, s - P, s)
    a = np.abs(s)
    root = P / 8  # nut root flat at the major diameter (opposite the bolt crest)
    return np.where(a <= root / 2, R, np.where(a <= root / 2 + flank, R - (a - root / 2) / flank * depth, r))


def threaded_bolt_mesh(prof, length, clearance, nt=72, nz_per_pitch=24, head=None):
    """Closed triangle mesh of a fully threaded shank (z from 0 to length) + optional hex head below z=0."""
    P = prof["P"]
    nz = int(np.ceil(length / P * nz_per_pitch)) + 1
    th = np.linspace(0, 2 * np.pi, nt, endpoint=False)
    zs = np.linspace(0, length, nz)
    T, Z = np.meshgrid(th, zs, indexing="ij")
    U = Z / P - T / (2 * np.pi)
    R = ext_profile_r(U, prof, clearance)
    # chamfer the tip to the minor diameter over one pitch
    tip = np.clip((length - Z) / P, 0, 1)
    R = np.minimum(R, prof["d3"] / 2 - clearance + (prof["d"] / 2 - prof["d3"] / 2) * tip)
    V = np.stack([R * np.cos(T), R * np.sin(T), Z], -1).reshape(-1, 3)
    F = []
    for i in range(nt):
        j = (i + 1) % nt
        for k in range(nz - 1):
            a, b, c, d = i * nz + k, j * nz + k, j * nz + k + 1, i * nz + k + 1
            F += [[a, b, c], [a, c, d]]
    n0 = len(V)
    V = np.vstack([V, [[0, 0, 0], [0, 0, length]]])
    for i in range(nt):
        j = (i + 1) % nt
        F.append([n0, j * nz, i * nz])
        F.append([n0 + 1, i * nz + nz - 1, j * nz + nz - 1])
    return V, np.array(F)


def nut_mesh(prof, s_af, height, clearance, nt=72, nz_per_pitch=24):
    """Closed mesh of a hex nut with an internal thread; z from 0 to height."""
    P = prof["P"]
    nz = int(np.ceil(height / P * nz_per_pitch)) + 1
    th = np.linspace(0, 2 * np.pi, nt, endpoint=False)
    zs = np.linspace(0, height, nz)
    T, Z = np.meshgrid(th, zs, indexing="ij")
    U = Z / P - T / (2 * np.pi)
    Ri = int_profile_r(U, prof, clearance)
    inner = np.stack([Ri * np.cos(T), Ri * np.sin(T), Z], -1).reshape(-1, 3)
    # hex outer radius as a function of angle (across flats s_af)
    a = (th + np.pi / 6) % (np.pi / 3) - np.pi / 6
    Ro = (s_af / 2) / np.cos(a)
    outer = np.stack(
        [np.repeat((Ro * np.cos(th))[:, None], nz, 1), np.repeat((Ro * np.sin(th))[:, None], nz, 1), Z], -1
    ).reshape(-1, 3)
    V = np.vstack([inner, outer])
    no = len(inner)
    F = []
    for i in range(nt):
        j = (i + 1) % nt
        for k in range(nz - 1):
            a0, b0, c0, d0 = i * nz + k, j * nz + k, j * nz + k + 1, i * nz + k + 1
            F += [[a0, c0, b0], [a0, d0, c0]]  # inner (normals inward)
            F += [[no + a0, no + b0, no + c0], [no + a0, no + c0, no + d0]]  # outer
        # bottom and top rings
        F += [[i * nz, j * nz, no + j * nz], [i * nz, no + j * nz, no + i * nz]]
        t0, t1 = i * nz + nz - 1, j * nz + nz - 1
        F += [[t0, no + t1, t1], [t0, no + t0, no + t1]]
    return V, np.array(F)


def mesh_mass_props(V, F, rho):
    """Volume, mass, centre of mass and inertia (about COM) of a closed mesh."""
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    dv = np.einsum("ij,ij->i", v0, np.cross(v1, v2)) / 6.0
    vol = dv.sum()
    com = ((v0 + v1 + v2) * dv[:, None]).sum(0) / 4.0 / vol
    # second moments, canonical tetrahedron formula
    A = np.stack([v0, v1, v2], 1)  # (n,3,3)
    S = np.einsum("nai,naj->nij", A, A) + np.einsum("ni,nj->nij", A.sum(1), A.sum(1))
    C = (S * (dv / 20.0)[:, None, None]).sum(0)
    C = C - vol * np.outer(com, com)
    I = np.trace(C) * np.eye(3) - C
    return vol, vol * rho, com, I * rho


def segments(prof, z0, z1, clearance, kind, seg_deg=10.0, s_af=None):
    """Convex pieces approximating a threaded part, for engines that need convex collision.

    kind='bolt': core cylinder handled separately; returns helical ridge pieces.
    kind='nut': ring sectors outside the major diameter + inward ridge pieces.
    Each piece: (k,3) point cloud whose convex hull is the piece.
    """
    P = prof["P"]
    nseg = int(round(360 / seg_deg))
    dth = 2 * np.pi / nseg
    pieces = []
    if kind == "bolt":
        R = prof["d"] / 2 - clearance
        r = prof["d3"] / 2 - clearance
        depth = R - r
        flank = depth * np.tan(np.radians(30))
        crest = P / 8
        # ridge cross-section in (radial, axial) about the crest centre
        sec = [(r - 0.0002, -(crest / 2 + flank)), (r - 0.0002, crest / 2 + flank), (R, crest / 2), (R, -crest / 2)]
    else:
        R = prof["d"] / 2 + clearance
        r = prof["d1"] / 2 + clearance
        depth = R - r
        flank = depth * np.tan(np.radians(30))
        root = P / 8
        # nut ridge points inward; centred half a pitch from the groove
        half = P / 2 - root / 2 - flank  # crest flat half-width of the nut ridge
        sec = [(R + 0.0002, -(half + flank)), (R + 0.0002, half + flank), (r, half), (r, -half)]
    # helix phase: bolt crest centre at z = P*theta/2pi + n P ; nut ridge centre offset by P/2
    off = 0.0 if kind == "bolt" else P / 2
    n_start = int(np.floor((z0 - P) / P)) - 1
    n_end = int(np.ceil(z1 / P)) + 1
    for n in range(n_start, n_end):
        for s in range(nseg):
            ta, tb = s * dth, (s + 1) * dth
            pts = []
            for t in np.linspace(ta, tb, 3):
                zc = P * t / (2 * np.pi) + n * P + off
                for rr, dz in sec:
                    pts.append([rr * np.cos(t), rr * np.sin(t), zc + dz])
            pts = np.array(pts)
            # keep only pieces entirely inside the part (no clipping: clipping a slanted
            # flank fattens the convex hull and makes it overlap the mating thread)
            if pts[:, 2].min() < z0 or pts[:, 2].max() > z1:
                continue
            pieces.append(pts)
    if kind == "nut":
        Rout_in = prof["d"] / 2 + clearance
        a_f = s_af / 2
        for s in range(nseg):
            ta, tb = s * dth, (s + 1) * dth
            pts = []
            for t in (ta, tb):
                a = (t + np.pi / 6) % (np.pi / 3) - np.pi / 6
                ro = a_f / np.cos(a)
                for rr in (Rout_in, ro):
                    for z in (z0, z1):
                        pts.append([rr * np.cos(t), rr * np.sin(t), z])
            pieces.append(np.array(pts))
    return pieces
