"""Small OpenUSD writer shared by every Quincaillerie asset.

Conventions (same as the sister projects): Z up, metres, kilograms, one asset per file with its own
default prim, /World as the default prim of scenes. Physics with the standard UsdPhysics schemas;
PhysX attributes for Isaac Sim are added as applied API schemas, ignored by other engines.
"""

from __future__ import annotations

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade, Vt

NS = "quincaillerie"


def create_stage(path):
    """A new, empty stage saved at path; overwrites a previous file (even one already open)."""
    import os

    path = os.fspath(path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    layer = Sdf.Layer.Find(os.path.abspath(path)) or (Sdf.Layer.FindOrOpen(path) if os.path.exists(path) else None)
    if layer is not None:
        layer.Clear()
        return Usd.Stage.Open(layer)
    return Usd.Stage.CreateNew(path)


def new_stage(path, root_name, kind="component"):
    stage = create_stage(path)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, f"/{root_name}")
    stage.SetDefaultPrim(root.GetPrim())
    Usd.ModelAPI(root.GetPrim()).SetKind(kind)
    return stage, root.GetPrim()


def set_attrs(prim, attrs):
    for k, v in attrs.items():
        name = f"{NS}:{k}"
        if isinstance(v, bool):
            prim.CreateAttribute(name, Sdf.ValueTypeNames.Bool).Set(v)
        elif isinstance(v, (int, np.integer)):
            prim.CreateAttribute(name, Sdf.ValueTypeNames.Int).Set(int(v))
        elif isinstance(v, (float, np.floating)):
            prim.CreateAttribute(name, Sdf.ValueTypeNames.Double).Set(float(v))
        elif isinstance(v, (list, tuple)) and v and isinstance(v[0], str):
            prim.CreateAttribute(name, Sdf.ValueTypeNames.StringArray).Set(list(v))
        elif isinstance(v, (list, tuple, np.ndarray)):
            prim.CreateAttribute(name, Sdf.ValueTypeNames.DoubleArray).Set([float(x) for x in np.ravel(v)])
        else:
            prim.CreateAttribute(name, Sdf.ValueTypeNames.String).Set(str(v))


def xform(stage, path, pos=(0, 0, 0), quat=(1, 0, 0, 0), scale=None):
    x = UsdGeom.Xform.Define(stage, path)
    place(x, pos, quat, scale)
    return x


def place(xf, pos=(0, 0, 0), quat=(1, 0, 0, 0), scale=None):
    xf = UsdGeom.Xformable(xf)
    xf.ClearXformOpOrder()
    xf.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*map(float, pos)))
    w, x, y, z = map(float, quat)
    xf.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(w, Gf.Vec3d(x, y, z)))
    if scale is not None:
        xf.AddScaleOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Vec3d(*map(float, scale)))


def quat_axis_angle(axis, ang):
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    return (np.cos(ang / 2), *(axis * np.sin(ang / 2)))


def material(stage, root_path, name, color, metallic=0.0, roughness=0.5):
    path = f"{root_path}/Looks/{name}"
    if stage.GetPrimAtPath(path):
        return UsdShade.Material(stage.GetPrimAtPath(path))
    mat = UsdShade.Material.Define(stage, path)
    sh = UsdShade.Shader.Define(stage, f"{path}/Surface")
    sh.CreateIdAttr("UsdPreviewSurface")
    sh.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*map(float, color)))
    sh.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(metallic))
    sh.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(roughness))
    mat.CreateSurfaceOutput().ConnectToSource(sh.ConnectableAPI(), "surface")
    return mat


def bind(prim, mat):
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def physics_material(stage, root_path, name, mu, restitution=0.0):
    path = f"{root_path}/PhysicsMaterials/{name}"
    if stage.GetPrimAtPath(path):
        return UsdShade.Material(stage.GetPrimAtPath(path))
    mat = UsdShade.Material.Define(stage, path)
    api = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    api.CreateStaticFrictionAttr(float(mu))
    api.CreateDynamicFrictionAttr(float(mu))
    api.CreateRestitutionAttr(float(restitution))
    return mat


def bind_physics(prim, pmat):
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(pmat, UsdShade.Tokens.weakerThanDescendants, "physics")


def split_normals(V, F, crease_deg=35.0):
    """Face-varying normals: each corner averages the normals of the faces around its vertex that are
    within crease_deg of its own face, so hex flats and rims stay sharp and revolved surfaces smooth."""
    V = np.asarray(V, float)
    F = np.asarray(F)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])  # area-weighted
    fu = fn / np.clip(np.linalg.norm(fn, axis=1, keepdims=True), 1e-30, None)
    cosc = np.cos(np.radians(crease_deg))
    corners_v = F.ravel()
    corners_f = np.repeat(np.arange(len(F)), 3)
    order = np.argsort(corners_v, kind="stable")
    sv = corners_v[order]
    sf = corners_f[order]
    starts = np.r_[0, np.nonzero(np.diff(sv))[0] + 1, len(sv)]
    out = np.zeros((len(corners_v), 3))
    for a, b in zip(starts[:-1], starts[1:], strict=True):
        faces = sf[a:b]
        U = fu[faces]
        Nw = fn[faces]
        sim = (U @ U.T) > cosc
        acc = sim.astype(float) @ Nw
        acc /= np.clip(np.linalg.norm(acc, axis=1, keepdims=True), 1e-30, None)
        out[order[a:b]] = acc
    return out


def mesh(stage, path, V, F, mat=None, smooth=True, guide=False, uv=None, crease=None):
    m = UsdGeom.Mesh.Define(stage, path)
    if uv is not None:
        pv = UsdGeom.PrimvarsAPI(m).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        pv.Set(Vt.Vec2fArray.FromNumpy(np.asarray(uv, np.float32)))
    m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(V, np.float32)))
    F = np.asarray(F)
    m.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(F)))
    m.CreateFaceVertexIndicesAttr(Vt.IntArray(F.ravel().tolist()))
    m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    V = np.asarray(V)
    m.CreateExtentAttr([Gf.Vec3f(*V.min(0).tolist()), Gf.Vec3f(*V.max(0).tolist())])
    if crease is not None:
        N = split_normals(V, F, crease)
        m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(N.astype(np.float32)))
        m.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    elif smooth:
        # vertex normals, so viewers shade revolved surfaces smoothly
        fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        N = np.zeros_like(V)
        for k in range(3):
            np.add.at(N, F[:, k], fn)
        N /= np.clip(np.linalg.norm(N, axis=1, keepdims=True), 1e-12, None)
        m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(N.astype(np.float32)))
        m.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    if mat is not None:
        bind(m.GetPrim(), mat)
    if guide:
        m.CreatePurposeAttr(UsdGeom.Tokens.guide)
    return m


def collider_cube(stage, path, center, half, quat=(1, 0, 0, 0), pmat=None, visible=False):
    c = UsdGeom.Cube.Define(stage, path)
    c.CreateSizeAttr(1.0)
    place(c, center, quat, scale=2 * np.asarray(half, float))
    UsdPhysics.CollisionAPI.Apply(c.GetPrim())
    if not visible:
        c.CreatePurposeAttr(UsdGeom.Tokens.guide)
    if pmat is not None:
        bind_physics(c.GetPrim(), pmat)
    return c


def collider_cylinder(stage, path, center, radius, half_height, axis="Z", quat=(1, 0, 0, 0), pmat=None, visible=False):
    c = UsdGeom.Cylinder.Define(stage, path)
    c.CreateRadiusAttr(float(radius))
    c.CreateHeightAttr(float(2 * half_height))
    c.CreateAxisAttr(axis)
    place(c, center, quat)
    UsdPhysics.CollisionAPI.Apply(c.GetPrim())
    if not visible:
        c.CreatePurposeAttr(UsdGeom.Tokens.guide)
    if pmat is not None:
        bind_physics(c.GetPrim(), pmat)
    return c


def collider_hull(stage, path, pts, pmat=None):
    """Convex piece: the point cloud is stored as a mesh of its convex hull, approximation convexHull."""
    from scipy.spatial import ConvexHull

    pts = np.asarray(pts, float)
    h = ConvexHull(pts)
    F = h.simplices.copy()
    c = pts.mean(0)
    n = np.cross(pts[F[:, 1]] - pts[F[:, 0]], pts[F[:, 2]] - pts[F[:, 0]])
    flip = np.einsum("ij,ij->i", n, pts[F].mean(1) - c) < 0
    F[flip] = F[flip][:, ::-1]
    m = mesh(stage, path, pts, F, smooth=False, guide=True)
    UsdPhysics.CollisionAPI.Apply(m.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(m.GetPrim()).CreateApproximationAttr(UsdPhysics.Tokens.convexHull)
    if pmat is not None:
        bind_physics(m.GetPrim(), pmat)
    return m


def rigid_body(prim, mass, com=(0, 0, 0), inertia_diag=None, principal=(1, 0, 0, 0), kinematic=False):
    rb = UsdPhysics.RigidBodyAPI.Apply(prim)
    if kinematic:
        rb.CreateKinematicEnabledAttr(True)
    ma = UsdPhysics.MassAPI.Apply(prim)
    ma.CreateMassAttr(float(mass))
    ma.CreateCenterOfMassAttr(Gf.Vec3f(*map(float, com)))
    if inertia_diag is not None:
        ma.CreateDiagonalInertiaAttr(Gf.Vec3f(*map(float, inertia_diag)))
        w, x, y, z = map(float, principal)
        ma.CreatePrincipalAxesAttr(Gf.Quatf(w, Gf.Vec3f(x, y, z)))
    return rb


def inertia_principal(I):
    """Diagonal inertia and principal-axes quaternion (w, x, y, z) of a 3x3 tensor."""
    ev, R = np.linalg.eigh(I)
    if np.linalg.det(R) < 0:
        R[:, 0] *= -1
    return ev, _mat2quat(R)


def q2m(q):
    """Rotation matrix of a quaternion (w, x, y, z)."""
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
            [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
            [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
        ]
    )


def qmul(a, b):
    """Quaternion product a * b, (w, x, y, z)."""
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
    )


def mat2quat(R):
    return _mat2quat(R)


def _mat2quat(R):
    m = R
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        w = 0.25 * s
        x = (m[2, 1] - m[1, 2]) / s
        y = (m[0, 2] - m[2, 0]) / s
        z = (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w = (m[2, 1] - m[1, 2]) / s
        x = 0.25 * s
        y = (m[0, 1] + m[1, 0]) / s
        z = (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w = (m[0, 2] - m[2, 0]) / s
        x = (m[0, 1] + m[1, 0]) / s
        y = 0.25 * s
        z = (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w = (m[1, 0] - m[0, 1]) / s
        x = (m[0, 2] + m[2, 0]) / s
        y = (m[1, 2] + m[2, 1]) / s
        z = 0.25 * s
    q = np.array([w, x, y, z])
    return tuple(q / np.linalg.norm(q))


def prismatic_joint(stage, path, body1, axis, pos0, k, damping, target, lower, upper, body0=None):
    """Slide joint along `axis` with a linear drive acting as a spring: F = k (target - x)."""
    j = UsdPhysics.PrismaticJoint.Define(stage, path)
    if body0 is not None:
        j.CreateBody0Rel().SetTargets([body0])
    j.CreateBody1Rel().SetTargets([body1])
    j.CreateAxisAttr(axis)
    j.CreateLocalPos0Attr(Gf.Vec3f(*map(float, pos0)))
    j.CreateLocalPos1Attr(Gf.Vec3f(0, 0, 0))
    j.CreateLowerLimitAttr(float(lower))
    j.CreateUpperLimitAttr(float(upper))
    d = UsdPhysics.DriveAPI.Apply(j.GetPrim(), "linear")
    d.CreateTypeAttr("force")
    d.CreateStiffnessAttr(float(k))
    d.CreateDampingAttr(float(damping))
    d.CreateTargetPositionAttr(float(target))
    return j


def revolute_joint(
    stage, path, body1, axis, pos0, k_per_deg, damping_per_deg, target_deg, lower_deg, upper_deg, body0=None
):
    """Hinge with an angular drive acting as a torsion spring (UsdPhysics units: per degree)."""
    j = UsdPhysics.RevoluteJoint.Define(stage, path)
    if body0 is not None:
        j.CreateBody0Rel().SetTargets([body0])
    j.CreateBody1Rel().SetTargets([body1])
    j.CreateAxisAttr(axis)
    j.CreateLocalPos0Attr(Gf.Vec3f(*map(float, pos0)))
    j.CreateLocalPos1Attr(Gf.Vec3f(0, 0, 0))
    j.CreateLowerLimitAttr(float(lower_deg))
    j.CreateUpperLimitAttr(float(upper_deg))
    d = UsdPhysics.DriveAPI.Apply(j.GetPrim(), "angular")
    d.CreateTypeAttr("force")
    d.CreateStiffnessAttr(float(k_per_deg))
    d.CreateDampingAttr(float(damping_per_deg))
    d.CreateTargetPositionAttr(float(target_deg))
    return j


def mate_frame(stage, path, pos, quat, attrs):
    x = xform(stage, path, pos, quat)
    set_attrs(x.GetPrim(), attrs)
    return x


def revolve_profile(profile, n=64, axis="z"):
    """Closed surface of revolution from an (r, h) polyline; returns V, F (axis along +z or +x)."""
    P = np.asarray(profile, float)
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = np.array([[r * np.cos(t), r * np.sin(t), h] for t in th for r, h in P])
    k = len(P)
    F = []
    for i in range(n):
        j = (i + 1) % n
        for s in range(k - 1):
            a, b, c, d = i * k + s, j * k + s, j * k + s + 1, i * k + s + 1
            F += [[a, b, c], [a, c, d]]
    F = np.array(F)
    if axis == "x":
        V = V[:, [2, 0, 1]]
        F = F  # (x,y,z) <- (h, r cos, r sin): a rotation, orientation kept
    # drop degenerate triangles (points on the axis)
    A = np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    return V, F[A > 1e-18]


def box_mesh(half):
    hx, hy, hz = half
    V = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    F = np.array(
        [
            [0, 2, 3],
            [0, 3, 1],
            [4, 5, 7],
            [4, 7, 6],
            [0, 1, 5],
            [0, 5, 4],
            [2, 6, 7],
            [2, 7, 3],
            [0, 4, 6],
            [0, 6, 2],
            [1, 3, 7],
            [1, 7, 5],
        ]
    )
    return V, F


# ------------------------------------------------------------------------------------ UVs
def _seam_fix(u):
    """u per corner, shape (nf, 3): faces crossing the 0/1 seam get their small values shifted by 1."""
    span = u.max(1) - u.min(1)
    bad = span > 0.5
    u[bad] = np.where(u[bad] < 0.5, u[bad] + 1.0, u[bad])
    return u


def uv_cylindrical(V, F, axis="z", along=None, vscale=100.0):
    """Per-corner UVs around an axis. along=(h0, h1): u runs along the axis from h0 to h1 and v around
    (labels); otherwise u runs around and v = height * vscale (tiling textures)."""
    P = np.asarray(V, float)[np.asarray(F)]  # (nf, 3, 3)
    if axis == "z":
        ang, h = np.arctan2(P[..., 1], P[..., 0]), P[..., 2]
    else:
        ang, h = np.arctan2(P[..., 2], P[..., 1]), P[..., 0]
    a = _seam_fix(ang / (2 * np.pi) + 0.5)
    if along is not None:
        uv = np.stack([(h - along[0]) / (along[1] - along[0]), 1.0 - a], -1)  # 1 - a: text not mirrored
    else:
        uv = np.stack([a, h * vscale], -1)
    return uv.reshape(-1, 2)


def uv_box(V, F, scale=50.0):
    P = np.asarray(V, float)[np.asarray(F)]
    n = np.abs(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]))
    dom = n.argmax(1)
    uv = np.zeros(P.shape[:2] + (2,))
    for k, (i, j) in enumerate(((1, 2), (0, 2), (0, 1))):
        sel = dom == k
        uv[sel] = P[sel][..., [i, j]] * scale
    return uv.reshape(-1, 2)


def uv_planar(V, F, radius):
    P = np.asarray(V, float)[np.asarray(F)]
    return np.stack([0.5 + P[..., 0] / (2 * radius), 0.5 + P[..., 1] / (2 * radius)], -1).reshape(-1, 2)


LIBRARY = "../materials/quincaillerie_materials.usda"


def lib_material(stage, root_path, name):
    """Asset-local material that references the shared library definition."""
    path = f"{root_path}/Looks/{name}"
    p = stage.GetPrimAtPath(path)
    if not p:
        p = stage.DefinePrim(path, "Material")
        p.GetReferences().AddReference(LIBRARY, f"/Materials/{name}")
    return UsdShade.Material(p)


def finish_variants(stage, root, mesh_paths, finishes, default):
    """Variant set 'finish' rebinding the listed visual meshes to one library material per finish."""
    vs = root.GetVariantSets().AddVariantSet("finish")
    rp = str(root.GetPath())
    for f in finishes:
        lib_material(stage, rp, f)
    for f in finishes:
        vs.AddVariant(f)
        vs.SetVariantSelection(f)
        with vs.GetVariantEditContext():
            for mp in mesh_paths:
                UsdShade.MaterialBindingAPI.Apply(stage.OverridePrim(mp)).Bind(
                    UsdShade.Material(stage.GetPrimAtPath(f"{rp}/Looks/{f}"))
                )
    vs.SetVariantSelection(default)


def fix_typeless(stage):
    """Give every intermediate prim a type: Scope for Looks/PhysicsMaterials/Joints, Xform otherwise,
    so that every DCC (Blender included) keeps the transform hierarchy."""
    for p in stage.Traverse():
        if p.GetTypeName() == "" and p.IsDefined():
            p.SetTypeName("Scope" if p.GetName() in ("Looks", "PhysicsMaterials", "Joints") else "Xform")


# ------------------------------------------------------------------ one visual mesh per rigid body
class VisualBuilder:
    """Collects visual parts and writes ONE Mesh per rigid body, with a GeomSubset per material.
    Every DCC then imports a single object per body (Blender makes one rigid body of it)."""

    def __init__(self):
        self.parts = []

    def add(self, V, F, mat, uv=None, crease=35):
        V = np.asarray(V, float)
        F = np.asarray(F)
        if uv is None:
            uv = np.zeros((len(F) * 3, 2))
        self.parts.append((V, F, mat, np.asarray(uv, float), split_normals(V, F, crease)))

    def write(self, stage, path, root_path, variant_mats=()):
        Vs, Fs, UV, N, mats = [], [], [], [], []
        off = 0
        for V, F, mat, uv, nrm in self.parts:
            Vs.append(V)
            Fs.append(F + off)
            UV.append(uv)
            N.append(nrm)
            mats += [mat] * len(F)
            off += len(V)
        V = np.vstack(Vs)
        F = np.vstack(Fs)
        m = UsdGeom.Mesh.Define(stage, path)
        m.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(V.astype(np.float32)))
        m.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(F)))
        m.CreateFaceVertexIndicesAttr(Vt.IntArray(F.ravel().tolist()))
        m.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        m.CreateExtentAttr([Gf.Vec3f(*V.min(0).tolist()), Gf.Vec3f(*V.max(0).tolist())])
        m.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(np.vstack(N).astype(np.float32)))
        m.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
        pv = UsdGeom.PrimvarsAPI(m).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
        pv.Set(Vt.Vec2fArray.FromNumpy(np.vstack(UV).astype(np.float32)))
        mats = np.array(mats)
        bapi = UsdShade.MaterialBindingAPI.Apply(m.GetPrim())
        subsets = {}
        for mat in dict.fromkeys(mats.tolist()):
            idx = np.nonzero(mats == mat)[0]
            ss = bapi.CreateMaterialBindSubset(mat, Vt.IntArray(idx.tolist()), UsdGeom.Tokens.face)
            subsets[mat] = str(ss.GetPath())
            if mat not in variant_mats:
                UsdShade.MaterialBindingAPI.Apply(ss.GetPrim()).Bind(lib_material(stage, root_path, mat))
        bapi.SetMaterialBindSubsetsFamilyType(UsdGeom.Tokens.partition)
        return m, subsets


# ------------------------------------------------------------------ PhysX (Isaac Sim) tuning
def physx_collision(prim, contact_offset, rest_offset=0.0):
    """PhysxCollisionAPI attributes (read by Isaac Sim); harmless elsewhere."""
    prim.AddAppliedSchema("PhysxCollisionAPI")
    prim.CreateAttribute("physxCollision:contactOffset", Sdf.ValueTypeNames.Float).Set(float(contact_offset))
    prim.CreateAttribute("physxCollision:restOffset", Sdf.ValueTypeNames.Float).Set(float(rest_offset))


def physx_body(prim, pos_iters=16, vel_iters=4, max_depen=0.1, ccd=False):
    prim.AddAppliedSchema("PhysxRigidBodyAPI")
    prim.CreateAttribute("physxRigidBody:solverPositionIterationCount", Sdf.ValueTypeNames.Int).Set(int(pos_iters))
    prim.CreateAttribute("physxRigidBody:solverVelocityIterationCount", Sdf.ValueTypeNames.Int).Set(int(vel_iters))
    prim.CreateAttribute("physxRigidBody:maxDepenetrationVelocity", Sdf.ValueTypeNames.Float).Set(float(max_depen))
    prim.CreateAttribute("physxRigidBody:enableCCD", Sdf.ValueTypeNames.Bool).Set(bool(ccd))


def box_inertia(mass, size):
    a, b, c = size
    return (mass * (b * b + c * c) / 12, mass * (a * a + c * c) / 12, mass * (a * a + b * b) / 12)


def physx_tune(stage, contact_offset, pos_iters=16, max_depen=0.1):
    for p in stage.Traverse():
        if p.HasAPI(UsdPhysics.CollisionAPI):
            physx_collision(p, contact_offset, 0.0)
        if p.HasAPI(UsdPhysics.RigidBodyAPI):
            physx_body(p, pos_iters, 4, max_depen)


def strip_physics(stage):
    """Remove every physics description from a stage: rigid bodies, masses, colliders, joints,
    physics materials and PhysX attributes (for assets used as visuals only)."""
    remove = []
    for p in stage.Traverse():
        if (
            p.HasAPI(UsdPhysics.CollisionAPI)
            or p.IsA(UsdPhysics.Joint)
            or p.GetName() in ("PhysicsMaterials", "Joints")
        ):
            remove.append(p.GetPath())
            continue
        for api in (UsdPhysics.RigidBodyAPI, UsdPhysics.MassAPI):
            if p.HasAPI(api):
                p.RemoveAPI(api)
        for name in ("PhysxRigidBodyAPI", "PhysxCollisionAPI"):
            if name in p.GetAppliedSchemas():
                p.RemoveAppliedSchema(name)
        for a in p.GetAttributes():
            if a.GetName().startswith(("physics:", "physxRigidBody:", "physxCollision:")):
                p.RemoveProperty(a.GetName())
    for path in sorted(remove, key=lambda x: -len(str(x))):
        if stage.GetPrimAtPath(path):
            stage.RemovePrim(path)
    stage.GetRootLayer().Save()
