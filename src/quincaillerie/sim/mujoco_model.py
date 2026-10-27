"""Build a MuJoCo model (MJCF) from an OpenUSD stage, using only what the files say.

Read: rigid bodies (RigidBodyAPI, MassAPI, kinematicEnabled), colliders (Cube, Cylinder, Mesh with
the convexHull approximation), physics materials (friction), prismatic and revolute joints with
their drives (stiffness, damping, target) and limits. Visual meshes are ignored. A body jointed to
another rigid body is nested under it; kinematic bodies are fixed; other bodies get a free joint.
UsdPhysics units: linear drives in N/m, angular drives per degree, revolute limits in degrees.
"""

from __future__ import annotations

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdPhysics, UsdShade

from ..usd import mat2quat, place, q2m


def _mat(M):
    """Gf.Matrix4d (row-vector convention) -> rotation (column convention), translation, scale."""
    tr = Gf.Transform()
    tr.SetMatrix(M)
    s = np.array(tr.GetScale())
    q = tr.GetRotation().GetQuat()
    w = q.GetReal()
    x, y, z = q.GetImaginary()
    R = q2m((w, x, y, z))
    return R, np.array(tr.GetTranslation()), s


def _m2q(R):
    return mat2quat(R)


AXIS_FIX = {
    "Z": np.eye(3),
    "X": np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float),  # Ry(+90): z -> x
    "Y": np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float),
}  # Rx(-90): z -> y
AXIS_VEC = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}


def _friction(prim, default):
    mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial("physics")
    if mat:
        api = UsdPhysics.MaterialAPI(mat.GetPrim())
        if api:
            v = api.GetDynamicFrictionAttr().Get()
            if v is not None:
                return float(v)
    return default


def f(v):
    """Numbers for MJCF; values below 1e-15 written as 0 (MuJoCo's parser rejects some tiny exponents)."""
    v = np.ravel(np.asarray(v, float))
    v = np.where(np.abs(v) < 1e-15, 0.0, v)
    return " ".join(f"{x:.9g}" for x in v)


def convert(
    stage,
    options="",
    default="",
    slide_armature=0.01,
    hinge_armature=2e-6,
    mu_default=0.3,
    extra_world="",
    extra_xml="",
):
    """MJCF text of every rigid body, collider and joint of the stage."""
    cache = UsdGeom.XformCache()
    prims = list(stage.Traverse())
    bodies = [p for p in prims if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    body_set = {p.GetPath() for p in bodies}
    joints = {}
    for p in prims:
        if p.IsA(UsdPhysics.PrismaticJoint) or p.IsA(UsdPhysics.RevoluteJoint):
            b1 = UsdPhysics.Joint(p).GetBody1Rel().GetTargets()
            if b1:
                joints[b1[0]] = p

    def owner(p):
        q = p
        while q and q.GetPath() != q.GetPath().absoluteRootPath:
            if q.GetPath() in body_set:
                return q
            q = q.GetParent()
        return None

    geoms = {b.GetPath(): [] for b in bodies}
    geoms[None] = []
    assets = []
    names = set()

    def uniq(n):
        k, i = n, 1
        while k in names:
            i += 1
            k = f"{n}_{i}"
        names.add(k)
        return k

    for p in prims:
        if not p.HasAPI(UsdPhysics.CollisionAPI):
            continue
        b = owner(p)
        Mg = cache.GetLocalToWorldTransform(p)
        if b is not None:
            Mb = cache.GetLocalToWorldTransform(b)
            Mrel = Mg * Mb.GetInverse()
        else:
            Mrel = Mg
        R, t, s = _mat(Mrel)
        mu = _friction(p, mu_default)
        nm = uniq(p.GetName())
        if p.IsA(UsdGeom.Cube):
            size = UsdGeom.Cube(p).GetSizeAttr().Get()
            half = s * size / 2
            g = (
                f'<geom name="{nm}" type="box" size="{f(half)}" pos="{f(t)}" quat="{f(_m2q(R))}" '
                f'friction="{mu} 0.005 0.0001"/>'
            )
        elif p.IsA(UsdGeom.Cylinder):
            cy = UsdGeom.Cylinder(p)
            ax = cy.GetAxisAttr().Get()
            Rt = R @ AXIS_FIX[ax]
            g = (
                f'<geom name="{nm}" type="cylinder" '
                f'size="{cy.GetRadiusAttr().Get():.9g} {cy.GetHeightAttr().Get() / 2:.9g}" '
                f'pos="{f(t)}" quat="{f(_m2q(Rt))}" friction="{mu} 0.005 0.0001"/>'
            )
        elif p.IsA(UsdGeom.Mesh):
            pts = np.array(UsdGeom.Mesh(p).GetPointsAttr().Get(), float)
            M = np.array(Mrel)
            P = np.c_[pts, np.ones(len(pts))] @ M
            an = f"m_{nm}"
            assets.append(f'<mesh name="{an}" vertex="{f(P[:, :3])}"/>')
            g = f'<geom name="{nm}" type="mesh" mesh="{an}" friction="{mu} 0.005 0.0001"/>'
        else:
            continue
        geoms[b.GetPath() if b is not None else None].append(g)

    # body tree: a body jointed to another rigid body (body0) is nested under it
    parent = {}
    for b1, jp in joints.items():
        b0 = UsdPhysics.Joint(jp).GetBody0Rel().GetTargets()
        if b0 and b0[0] in body_set:
            parent[b1] = b0[0]
    children = {}
    for b in bodies:
        children.setdefault(parent.get(b.GetPath()), []).append(b)

    def emit(b, parent_M):
        M = cache.GetLocalToWorldTransform(b)
        Mrel = M * parent_M.GetInverse() if parent_M is not None else M
        R, t, _ = _mat(Mrel)
        ma = UsdPhysics.MassAPI(b)
        mass = ma.GetMassAttr().Get()
        com = np.array(ma.GetCenterOfMassAttr().Get() or (0, 0, 0))
        di = ma.GetDiagonalInertiaAttr().Get()
        pa = ma.GetPrincipalAxesAttr().Get()
        pq = (pa.GetReal(), *pa.GetImaginary()) if pa is not None else (1, 0, 0, 0)
        inertial = (
            f'<inertial pos="{f(com)}" mass="{mass:.9g}" diaginertia="{f(di)}" quat="{f(pq)}"/>'
            if di is not None
            else f'<inertial pos="{f(com)}" mass="{mass:.9g}" diaginertia="1e-9 1e-9 1e-9"/>'
        )
        kin = UsdPhysics.RigidBodyAPI(b).GetKinematicEnabledAttr().Get()
        jx = ""
        if b.GetPath() in joints:
            jp = joints[b.GetPath()]
            if jp.IsA(UsdPhysics.PrismaticJoint):
                J = UsdPhysics.PrismaticJoint(jp)
                d = UsdPhysics.DriveAPI(jp, "linear")
                k = d.GetStiffnessAttr().Get() or 0.0
                c = d.GetDampingAttr().Get() or 0.0
                tg = d.GetTargetPositionAttr().Get() or 0.0
                lo, hi = J.GetLowerLimitAttr().Get(), J.GetUpperLimitAttr().Get()
                jx = (
                    f'<joint name="{jp.GetName()}" type="slide" axis="{f(AXIS_VEC[J.GetAxisAttr().Get()])}" '
                    f'stiffness="{k:.9g}" damping="{c:.9g}" springref="{tg:.9g}" range="{lo:.9g} {hi:.9g}" '
                    f'limited="true" armature="{slide_armature}"/>'
                )
            else:
                J = UsdPhysics.RevoluteJoint(jp)
                d = UsdPhysics.DriveAPI(jp, "angular")
                k = (d.GetStiffnessAttr().Get() or 0.0) * 180 / np.pi
                c = (d.GetDampingAttr().Get() or 0.0) * 180 / np.pi
                tg = np.radians(d.GetTargetPositionAttr().Get() or 0.0)
                lo, hi = np.radians(J.GetLowerLimitAttr().Get()), np.radians(J.GetUpperLimitAttr().Get())
                jx = (
                    f'<joint name="{jp.GetName()}" type="hinge" axis="{f(AXIS_VEC[J.GetAxisAttr().Get()])}" '
                    f'stiffness="{k:.9g}" damping="{c:.9g}" springref="{tg:.9g}" range="{lo:.9g} {hi:.9g}" '
                    f'limited="true" solreflimit="0.001 1" armature="{hinge_armature}"/>'
                )
        elif not kin and b.GetPath() not in parent:
            jx = "<freejoint/>"
        kids = "".join(emit(cb, M) for cb in children.get(b.GetPath(), []))
        inside = jx + inertial + "".join(geoms[b.GetPath()]) + kids
        return f'<body name="{b.GetName()}" pos="{f(t)}" quat="{f(_m2q(R))}">{inside}</body>'

    out = [emit(b, None) for b in children.get(None, [])]
    xml = (
        f'<mujoco><compiler angle="radian" autolimits="true"/>{options}{default}<asset>{"".join(assets)}</asset>'
        f"<worldbody>{''.join(geoms[None])}{''.join(out)}{extra_world}</worldbody>{extra_xml}</mujoco>"
    )
    return xml


def scene(path_or_none, items):
    """In-memory scene: items = [(prim_name, asset_file, pos, quat, overrides dict)]."""
    st = Usd.Stage.CreateInMemory() if path_or_none is None else Usd.Stage.CreateNew(path_or_none)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(st, 1.0)
    w = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(w.GetPrim())
    UsdPhysics.Scene.Define(st, "/World/PhysicsScene")
    for name, asset, pos, quat, ov in items:
        x = UsdGeom.Xform.Define(st, f"/World/{name}")
        x.GetPrim().GetReferences().AddReference(asset)
        place(x, pos, quat)
        for k, v in (ov or {}).items():
            if k == "kinematic":  # the part itself if it is a body, else its "base" (a holder)
                p = (
                    x.GetPrim()
                    if x.GetPrim().HasAPI(UsdPhysics.RigidBodyAPI)
                    else st.GetPrimAtPath(f"/World/{name}/base")
                )
                UsdPhysics.RigidBodyAPI(p).CreateKinematicEnabledAttr(bool(v))
    return st
