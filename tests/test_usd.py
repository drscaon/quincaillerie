"""The OpenUSD assets: physics description, one visual mesh per rigid body, materials, variants."""

import os

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade

from quincaillerie.batteries import FLOOR_T, holder_design, spring_design


def _open(res, name):
    f = [p["file"] for p in res.parts if p["name"] == name][0]
    return Usd.Stage.Open(os.path.join(res.out_dir, f))


def _bodies(st):
    return [p for p in st.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]


def test_every_asset_opens_with_its_materials(small_set):
    for p in small_set.parts:
        st = _open(small_set, p["name"])
        assert UsdGeom.GetStageMetersPerUnit(st) == 1.0 and UsdGeom.GetStageUpAxis(st) == "Z"
        for prim in st.Traverse():
            assert prim.GetTypeName() != "", f"typeless prim {prim.GetPath()} (Blender drops its transform)"
            if prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputePurpose() != "guide":
                for ss in UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Imageable(prim)) or [prim]:
                    mat, _ = UsdShade.MaterialBindingAPI(
                        ss.GetPrim() if hasattr(ss, "GetPrim") else ss
                    ).ComputeBoundMaterial()
                    assert mat and mat.GetSurfaceOutput().HasConnectedSource(), f"{ss} has no resolved material"


def test_one_visual_mesh_per_rigid_body(small_set):
    for p in small_set.parts:
        st = _open(small_set, p["name"])
        bodies = _bodies(st)
        assert bodies
        paths = {b.GetPath() for b in bodies}
        for b in bodies:
            ma = UsdPhysics.MassAPI(b)
            assert ma.GetMassAttr().Get() > 0 and min(ma.GetDiagonalInertiaAttr().Get()) > 1e-12
            vis = [
                q
                for q in Usd.PrimRange(b)
                if q.IsA(UsdGeom.Mesh)
                and not q.HasAPI(UsdPhysics.CollisionAPI)
                and q.GetName() != "spring_coil"
                and not any(a.GetPath() in paths for a in [q.GetParent(), q.GetParent().GetParent()] if a != b)
            ]
            assert len(vis) == 1, f"{b.GetPath()}: {len(vis)} visual meshes"
            cols = [q for q in Usd.PrimRange(b) if q.HasAPI(UsdPhysics.CollisionAPI)]
            assert cols and all(UsdGeom.Imageable(c).ComputePurpose() == "guide" for c in cols)


def test_fastener_mass_and_variants(small_set):
    st = _open(small_set, "ISO4017_M4x10")
    root = st.GetDefaultPrim()
    m = UsdPhysics.MassAPI(root).GetMassAttr().Get()
    # steel cylinder of the pitch diameter + hex head: about 1.4 g
    d2, L, s, k = 0.00354, 0.010, 0.007, 0.0028
    approx = 7850 * (np.pi * d2**2 / 4 * L + np.sqrt(3) / 2 * s**2 * k)
    assert abs(m - approx) / approx < 0.08
    vs = root.GetVariantSets().GetVariantSet("finish")
    assert len(vs.GetVariantNames()) == 6 and vs.GetVariantSelection() == "zinc_clear"
    assert root.GetAttribute("quincaillerie:compatibleWith").Get() == ["ISO4032_M4", "ISO7089_M4"]


def test_holder_joints_and_spring(small_set):
    st = _open(small_set, "Holder_AA")
    base = st.GetPrimAtPath("/Holder_AA/base")
    assert not UsdPhysics.RigidBodyAPI(base).GetKinematicEnabledAttr().Get()  # a holder falls like any part
    j = UsdPhysics.PrismaticJoint(st.GetPrimAtPath("/Holder_AA/Joints/spring"))
    assert j.GetBody0Rel().GetTargets()[0] == base.GetPath()
    assert st.GetPrimAtPath(j.GetBody1Rel().GetTargets()[0]).HasAPI(UsdPhysics.RigidBodyAPI)
    k = UsdPhysics.DriveAPI(j.GetPrim(), "linear").GetStiffnessAttr().Get()
    assert abs(k - spring_design(3.5, 5.0, max(5.0, 0.45 * 14.5))[0]) < 1e-6
    # underside at z = 0: the lowest collider of the base touches the asset origin's plane
    cache = UsdGeom.XformCache()
    zs = []
    for c in Usd.PrimRange(base):
        if c.IsA(UsdGeom.Cube):
            M = cache.GetLocalToWorldTransform(c)
            zs += [M.Transform((x, y, z))[2] for x in (-0.5, 0.5) for y in (-0.5, 0.5) for z in (-0.5, 0.5)]
    assert abs(min(zs)) < 1e-9
    assert abs(cache.GetLocalToWorldTransform(base).ExtractTranslation()[2] - FLOOR_T * 1e-3) < 1e-12
    assert holder_design("AA")["x_free"] > holder_design("AA")["x_seat"]


def test_scene_references_resolve(small_set):
    st = Usd.Stage.Open(small_set.scene)
    for p in st.GetPrimAtPath("/World").GetChildren():
        if p.HasAuthoredReferences():
            assert p.GetChildren(), f"{p.GetPath()}: reference not resolved"
    names = [p.GetName() for p in st.GetPrimAtPath("/World").GetChildren()]
    assert sum(n.startswith("ISO4017_M4x10_") for n in names) == 2  # --count 2
    assert "assembly_ISO4032_M4" in names and "assembly_Cell_AA" in names
    bodies = [p for p in st.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    assert len(bodies) == 2 * (4 + 2) + 3 + 3  # each part twice (a holder is 2 bodies), plus the assemblies
