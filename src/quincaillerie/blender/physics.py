"""Quincaillerie physics for Blender: rigid bodies and constraints from the UsdPhysics description.

Blender's USD importer reads geometry and materials but not UsdPhysics. Installed as an add-on, this
file hooks into File > Import > Universal Scene Description: every imported file that describes rigid
bodies gets them in Blender, ready to play, with nothing to set by hand:

  * one rigid body per UsdPhysics body, on its visual mesh, whose origin is moved to the USD centre of
    mass (Blender uses the origin as the centre of mass); USD mass, friction of its physics material;
  * its collision shape: a compound of the USD collision shapes (boxes, 96-sided cylinders, convex
    hulls), rebuilt from the file (whether or not "Guides" was ticked), hidden in renders;
  * kinematic bodies -> passive and animated; colliders outside any body (a floor) -> passive;
  * prismatic and revolute joints with drives -> Generic Spring constraints with the USD limits,
    stiffness and damping. Bullet takes a spring's rest position from the first frame, so a spring
    authored compressed (a cell already in its holder) holds the cell by the holder's shape, without
    the preload; an empty holder behaves exactly as authored;
  * the coil of a holder stretches with its spring plate (a driver);
  * the rigid body world: small collision margins and enough substeps for millimetre parts.

Install once: Edit > Preferences > Add-ons > Install from Disk > this file (or the .zip from
`quincaillerie blender-addon`), enable "Quincaillerie physics". Without installing: open this file in
the Scripting workspace, set USD_FILE below and Run Script; or headless:
    blender -b -P quincaillerie_physics.py -- file.usda
Needs Blender 4.4 or later (its Python ships bpy and the OpenUSD module, pxr).
"""

import math
import re
import sys

import bpy
from mathutils import Matrix, Vector

bl_info = {
    "name": "Quincaillerie physics",
    "author": "Daniel Régis Sarmento Caon",
    "version": (0, 1, 0),
    "blender": (4, 4, 0),
    "location": "File > Import > Universal Scene Description",
    "description": "Rigid bodies and constraints from UsdPhysics when importing a USD file",
    "category": "Import-Export",
}

USD_FILE = ""  # when run as a script from Blender's text editor
SUBSTEP_HZ = 2000  # physics rate (substeps per second)
MARGIN = 0.0001  # collision margin (m); a tenth of the PhysX contact offset when the file gives one
ITERATIONS = 40
ANG_DAMPING = 0.1  # stands in for rolling resistance, which Bullet lacks
CYLINDER_SIDES = 96


def _usd():
    from pxr import Usd, UsdGeom, UsdPhysics, UsdShade

    return Usd, UsdGeom, UsdPhysics, UsdShade


def _base(name):
    return re.sub(r"\.\d{3}$", "", name)


def _gf(M):
    """Gf.Matrix4d (row vectors) -> mathutils Matrix (column vectors)."""
    return Matrix([[M[j][i] for j in range(4)] for i in range(4)])


def _friction(prim):
    _, _, UsdPhysics, UsdShade = _usd()
    mat, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial("physics")
    if mat:
        api = UsdPhysics.MaterialAPI(mat.GetPrim())
        v = api.GetDynamicFrictionAttr().Get() if api else None
        if v is not None:
            return float(v)
    return 0.5


def _keep_world(o, parent):
    M = o.matrix_world.copy()
    o.parent = parent
    o.matrix_parent_inverse = parent.matrix_world.inverted() if parent else Matrix.Identity(4)
    o.matrix_world = M


class _NameMap:
    """USD prim path -> imported object, by names, when the importer gives no prim map."""

    def __init__(self, objs):
        self.by_name = {}
        for o in objs:
            self.by_name.setdefault(_base(o.name), []).append(o)

    def objects(self, path):
        comps = [c for c in str(path).split("/") if c]

        def chain(o):
            out = []
            while o is not None:
                out.append(_base(o.name))
                o = o.parent
            return out[::-1]

        def subseq(small, big):
            it = iter(big)
            return all(any(x == y for y in it) for x in small)

        cands = [o for o in self.by_name.get(comps[-1], []) if subseq(chain(o), comps)]
        return sorted(cands, key=lambda o: -len(chain(o)))[:1]


def _collider_geometry(prim, M):
    """Vertices (transformed by M, a mathutils Matrix) and faces of a USD collider."""
    _, UsdGeom, _, _ = _usd()
    if prim.IsA(UsdGeom.Cube):
        s = UsdGeom.Cube(prim).GetSizeAttr().Get() / 2
        V = [(x, y, z) for x in (-s, s) for y in (-s, s) for z in (-s, s)]
        F = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    elif prim.IsA(UsdGeom.Cylinder):
        cy = UsdGeom.Cylinder(prim)
        r, h, ax = cy.GetRadiusAttr().Get(), cy.GetHeightAttr().Get(), cy.GetAxisAttr().Get()
        n = CYLINDER_SIDES  # Blender's importer makes 20 sides: a lying cell would sink 0.35 mm
        V = []
        for z in (-h / 2, h / 2):
            for i in range(n):
                a, b = r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)
                V.append({"X": (z, a, b), "Y": (b, z, a), "Z": (a, b, z)}[ax])
        F = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
        F += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    elif prim.IsA(UsdGeom.Mesh):
        m = UsdGeom.Mesh(prim)
        V = [tuple(p) for p in m.GetPointsAttr().Get()]
        counts, idx = m.GetFaceVertexCountsAttr().Get(), m.GetFaceVertexIndicesAttr().Get()
        F, k = [], 0
        for c in counts:
            F.append(tuple(idx[k : k + c]))
            k += c
    else:
        return None, None
    return [tuple(M @ Vector(v)) for v in V], F


def setup_physics(stage, prim_map=None, scene=None):
    """Build Blender rigid bodies and constraints for the UsdPhysics bodies of an imported stage.

    prim_map: {prim path: [Blender data]} from the importer; without it, objects are found by name.
    Returns {USD body path: Blender object}."""
    Usd, UsdGeom, UsdPhysics, _ = _usd()
    sc = scene or bpy.context.scene
    bodies = [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]
    if not bodies:
        return {}
    body_set = {p.GetPath() for p in bodies}
    if prim_map is None:
        names = _NameMap(list(bpy.data.objects))

        def objs_of(path):
            return names.objects(path)

    else:
        # the importer merges an Xform and its only Mesh child into one object: the object is mapped
        # to the Xform, its mesh data to the Mesh prim
        users = {}
        for o in bpy.data.objects:
            if o.data is not None:
                users.setdefault(o.data.as_pointer(), []).append(o)
        pmap = {}
        for k, v in prim_map.items():
            objs = [o for o in v if isinstance(o, bpy.types.Object)]
            for d in v:
                if isinstance(d, bpy.types.Mesh) and not any(o.data == d for o in objs):
                    objs += users.get(d.as_pointer(), [])
            pmap[str(k)] = objs

        def objs_of(path):
            return [o for o in pmap.get(str(path), []) if o.name in bpy.data.objects]

    cache = UsdGeom.XformCache()
    done = [o for b in bodies for q in Usd.PrimRange(b) for o in objs_of(q.GetPath()) if "usd_rigid_body" in o]
    if done:  # already set up (two hooks registered: the add-on and a script)
        return {}

    def owner(p):
        q = p.GetParent()
        while q and not q.IsPseudoRoot():
            if q.GetPath() in body_set:
                return q
            q = q.GetParent()
        return None

    bpy.context.view_layer.update()  # world matrices of the objects just imported
    # correction from stage world to Blender world (import scale, parent objects)
    C = Matrix.Identity(4)
    for p in stage.Traverse():
        obs = [o for o in objs_of(p.GetPath()) if o.type == "MESH"]
        if p.IsA(UsdGeom.Mesh) and obs and not p.HasAPI(UsdPhysics.CollisionAPI):
            C = obs[0].matrix_world @ _gf(cache.GetLocalToWorldTransform(p)).inverted()
            break

    def world(prim):
        return C @ _gf(cache.GetLocalToWorldTransform(prim))

    # imported collision guides are replaced by colliders rebuilt from the file
    for p in stage.Traverse():
        if p.HasAPI(UsdPhysics.CollisionAPI):
            for o in objs_of(p.GetPath()):
                bpy.data.objects.remove(o, do_unlink=True)

    if sc.rigidbody_world is None:
        with bpy.context.temp_override(scene=sc):
            bpy.ops.rigidbody.world_add()
    rw = sc.rigidbody_world
    rw.substeps_per_frame = max(10, math.ceil(SUBSTEP_HZ / sc.render.fps))
    rw.solver_iterations = ITERATIONS
    rw.use_split_impulse = True
    if rw.collection is None:
        rw.collection = bpy.data.collections.new("RigidBodyWorld")
    rw.point_cache.frame_end = max(rw.point_cache.frame_end, sc.frame_end)
    target = sc.collection

    def add_rb(o, rtype, margin=MARGIN):
        if o.name not in rw.collection.objects:
            rw.collection.objects.link(o)
        if o.rigid_body is None:
            with bpy.context.temp_override(scene=sc, object=o, active_object=o, selected_objects=[o]):
                bpy.ops.rigidbody.object_add(type=rtype)
        rb = o.rigid_body
        rb.type = rtype
        rb.use_margin = True
        rb.collision_margin = margin
        rb.restitution = 0.0
        rb.use_deactivation = False
        rb.linear_damping = 0.0
        rb.angular_damping = ANG_DAMPING
        return rb

    def new_object(name, V, F, M_world):
        me = bpy.data.meshes.new(name)
        me.from_pydata(V, [], F)
        me.update()
        o = bpy.data.objects.new(name, me)
        target.objects.link(o)
        o.matrix_world = M_world
        return o

    # joint positions at import (Bullet's spring rest position is the first frame's pose)
    joint_q = {}
    joints = [p for p in stage.Traverse() if p.IsA(UsdPhysics.PrismaticJoint) or p.IsA(UsdPhysics.RevoluteJoint)]
    axes = {"X": Vector((1, 0, 0)), "Y": Vector((0, 1, 0)), "Z": Vector((0, 0, 1))}
    for jp in joints:
        J = UsdPhysics.Joint(jp)
        b0, b1 = J.GetBody0Rel().GetTargets(), J.GetBody1Rel().GetTargets()
        if not b1:
            continue
        W0 = world(stage.GetPrimAtPath(b0[0])) if b0 else C.copy()
        pivot = W0 @ Vector(J.GetLocalPos0Attr().Get())
        ax_l = axes[jp.GetAttribute("physics:axis").Get()]
        W1 = world(stage.GetPrimAtPath(b1[0]))
        if jp.IsA(UsdPhysics.PrismaticJoint):
            q = ((W1 @ Vector(J.GetLocalPos1Attr().Get())) - pivot).dot((W0.to_3x3() @ ax_l).normalized())
            tgt = UsdPhysics.DriveAPI(jp, "linear").GetTargetPositionAttr().Get() or 0.0
        else:
            rel = W0.to_quaternion().inverted() @ W1.to_quaternion()
            ax, ang = rel.to_axis_angle()
            q = math.degrees(ang) * (1 if ax.dot(ax_l) >= 0 else -1) if ang > 1e-9 else 0.0
            tgt = UsdPhysics.DriveAPI(jp, "angular").GetTargetPositionAttr().Get() or 0.0
        joint_q[jp.GetPath()] = (q, tgt)

    # bodies
    out = {}
    for b in bodies:
        kin = bool(UsdPhysics.RigidBodyAPI(b).GetKinematicEnabledAttr().Get())
        meshes, cols = [], []
        for p in Usd.PrimRange(b):
            if p != b and (p.GetPath() in body_set or owner(p) != b):
                continue
            if p.HasAPI(UsdPhysics.CollisionAPI):
                cols.append(p)
            elif (
                p.IsA(UsdGeom.Mesh)
                and UsdGeom.Imageable(p).ComputePurpose() != UsdGeom.Tokens.guide
                and p.GetName() != "spring_coil"
            ):
                meshes.append(p)
        Wb = world(b)
        ma = UsdPhysics.MassAPI(b)
        com_w = Wb @ Vector(ma.GetCenterOfMassAttr().Get() or (0, 0, 0))
        M_body = Matrix.Translation(com_w) @ Wb.to_3x3().normalized().to_4x4()
        vis = next((o for p in meshes for o in objs_of(p.GetPath()) if o.type == "MESH"), None)
        if vis is None:  # no visual mesh: an empty mesh object carries the body
            vis = new_object(f"{b.GetName()}_body", [], [], M_body)
        else:
            if vis.data.users > 1:
                vis.data = vis.data.copy()
            vis.data.transform(M_body.inverted() @ vis.matrix_world)  # origin at the centre of mass
            _keep_world(vis, None)
            vis.matrix_world = M_body
        bpy.context.view_layer.update()
        rb = add_rb(vis, "PASSIVE" if kin else "ACTIVE")
        rb.kinematic = kin
        rb.mass = float(ma.GetMassAttr().Get() or 0.01)
        rb.collision_shape = "COMPOUND"
        rb.collision_margin = 0.0
        fr = []
        inv = M_body.inverted()
        for c in cols:
            V, F = _collider_geometry(c, inv @ world(c))
            if V is None:
                continue
            co = new_object(f"{vis.name}_col_{c.GetName()}", V, F, M_body)
            _keep_world(co, vis)
            off = c.GetAttribute("physxCollision:contactOffset")
            margin = min(MARGIN, off.Get() / 10) if off and off.Get() else MARGIN
            crb = add_rb(co, "ACTIVE", margin)
            crb.collision_shape = "CONVEX_HULL"
            crb.mass = 1e-6
            co.display_type, co.hide_render = "WIRE", True
            fr.append(_friction(c))
        rb.friction = min(fr) if fr else 0.5
        vis["usd_rigid_body"] = str(b.GetPath())
        out[b.GetPath()] = vis

    # colliders outside any body (a floor): passive
    for p in stage.Traverse():
        if p.HasAPI(UsdPhysics.CollisionAPI) and owner(p) is None and p.GetPath() not in body_set:
            V, F = _collider_geometry(p, Matrix.Identity(4))
            if V is None:
                continue
            o = new_object(p.GetName(), V, F, world(p))
            rb = add_rb(o, "PASSIVE")
            rb.collision_shape = "BOX" if p.IsA(UsdGeom.Cube) else "CONVEX_HULL"
            rb.friction = _friction(p)
            if UsdGeom.Imageable(p).ComputePurpose() == UsdGeom.Tokens.guide:
                o.hide_render, o.display_type = True, "WIRE"

    # joints -> Generic Spring constraints
    for jp in joints:
        J = UsdPhysics.Joint(jp)
        b0, b1 = J.GetBody0Rel().GetTargets(), J.GetBody1Rel().GetTargets()
        o0, o1 = (out.get(b0[0]) if b0 else None), (out.get(b1[0]) if b1 else None)
        if o1 is None or jp.GetPath() not in joint_q:
            continue
        W0 = world(stage.GetPrimAtPath(b0[0])) if b0 else C.copy()
        pivot = W0 @ Vector(J.GetLocalPos0Attr().Get())
        e = bpy.data.objects.new(f"joint_{jp.GetName()}", None)
        target.objects.link(e)
        e.empty_display_size = 0.005
        e.matrix_world = Matrix.Translation(pivot) @ W0.to_3x3().normalized().to_4x4()
        with bpy.context.temp_override(scene=sc, object=e, active_object=e, selected_objects=[e]):
            bpy.ops.rigidbody.constraint_add(type="GENERIC_SPRING")
        c = e.rigid_body_constraint
        c.object1, c.object2 = o0, o1
        c.spring_type = "SPRING2"
        for a in "xyz":
            for kind in ("lin", "ang"):
                setattr(c, f"use_limit_{kind}_{a}", True)
                setattr(c, f"limit_{kind}_{a}_lower", 0.0)
                setattr(c, f"limit_{kind}_{a}_upper", 0.0)
        ax = jp.GetAttribute("physics:axis").Get().lower()
        lo, hi = jp.GetAttribute("physics:lowerLimit").Get(), jp.GetAttribute("physics:upperLimit").Get()
        q0, tgt = joint_q[jp.GetPath()]
        if jp.IsA(UsdPhysics.PrismaticJoint):
            d = UsdPhysics.DriveAPI(jp, "linear")
            setattr(c, f"limit_lin_{ax}_lower", lo - q0)
            setattr(c, f"limit_lin_{ax}_upper", hi - q0)
            setattr(c, f"use_spring_{ax}", True)
            setattr(c, f"spring_stiffness_{ax}", d.GetStiffnessAttr().Get() or 0.0)
            setattr(c, f"spring_damping_{ax}", d.GetDampingAttr().Get() or 0.0)
        else:
            d = UsdPhysics.DriveAPI(jp, "angular")
            setattr(c, f"limit_ang_{ax}_lower", math.radians(lo - q0))
            setattr(c, f"limit_ang_{ax}_upper", math.radians(hi - q0))
            setattr(c, f"use_spring_ang_{ax}", True)
            setattr(c, f"spring_stiffness_ang_{ax}", (d.GetStiffnessAttr().Get() or 0.0) * 180 / math.pi)
            setattr(c, f"spring_damping_ang_{ax}", (d.GetDampingAttr().Get() or 0.0) * 180 / math.pi)
        if o0 is not None:
            _keep_world(e, o0)  # the joint marker follows its first body in the viewport
        e["usd_joint"] = str(jp.GetPath())
        e["start_offset_from_drive_target"] = q0 - tgt

    # coils follow their spring plate
    for p in stage.Traverse():
        if p.GetName() != "spring_coil" or not p.IsA(UsdGeom.Mesh):
            continue
        base = p.GetParent().GetParent()
        plate = next((q for q in base.GetParent().GetChildren() if q.GetName() == "spring_plate"), None)
        coil = next((o for o in objs_of(p.GetPath()) if o.type == "MESH"), None)
        if coil is None or plate is None or plate.GetPath() not in out:
            continue
        base_obj, plate_obj = out.get(base.GetPath()), out[plate.GetPath()]
        back = p.GetAttribute("quincaillerie:backFace").Get()
        free = p.GetAttribute("quincaillerie:freeLengthEnd").Get()
        Wh = world(base)
        plate_local = Wh.inverted() @ plate_obj.matrix_world.translation
        M_coil = Wh @ Matrix.Translation(Vector((back, 0, 0)))  # origin at the back face, base frame
        if coil.data.users > 1:
            coil.data = coil.data.copy()
        coil.data.transform(M_coil.inverted() @ coil.matrix_world)
        _keep_world(coil, None)
        coil.matrix_world = M_coil
        anchor = bpy.data.objects.new(f"{coil.name}_anchor", None)
        target.objects.link(anchor)
        anchor.matrix_world = Wh @ Matrix.Translation(Vector((back, 0, plate_local.z)))  # on the coil axis
        if base_obj is not None:
            _keep_world(coil, base_obj)
            _keep_world(anchor, base_obj)
        rest = (free - 0.001) - back
        drv = coil.driver_add("scale", 0).driver
        drv.type = "SCRIPTED"
        v = drv.variables.new()
        v.name, v.type = "dist", "LOC_DIFF"
        v.targets[0].id, v.targets[1].id = anchor, plate_obj
        # the plate's origin is its centre of mass, 0.5 mm behind its contact face (1 mm plate)
        drv.expression = f"max(0.05, (dist - 0.0005) / {rest:.9g})"
    return out


# ------------------------------------------------------------------ add-on: hook into the importer
_registered = False


class QUINCAILLERIE_USDHook(bpy.types.USDHook):
    bl_idname = "quincaillerie_physics"
    bl_label = "Quincaillerie physics"
    bl_description = "Rigid bodies and constraints from UsdPhysics"

    @staticmethod
    def on_import(context):
        stage = context.get_stage()
        if stage is None:
            return False
        try:
            prim_map = context.get_prim_map()
        except AttributeError:  # Blender before 4.4
            prim_map = None
        setup_physics(stage, prim_map)
        return True


def register():
    global _registered
    if not _registered:
        bpy.utils.register_class(QUINCAILLERIE_USDHook)
        _registered = True


def unregister():
    global _registered
    if _registered:
        bpy.utils.unregister_class(QUINCAILLERIE_USDHook)
        _registered = False


def import_with_physics(path):
    """File > Import > USD with the physics set up (registers the import hook if needed)."""
    register()
    bpy.ops.wm.usd_import(filepath=path)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    f = argv[0] if argv else USD_FILE
    if f:
        import_with_physics(f)
    else:
        register()  # run from the text editor: every USD import of this session gets its physics
