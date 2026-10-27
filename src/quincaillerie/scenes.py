"""OpenUSD scenes that reference the assets: a floor collider, gravity, and parts placed at rest.

Scenes never copy an asset: they reference its file by a relative path, and author poses, variant
selections and the pose of a holder's moving contact as overrides.
"""

from __future__ import annotations

import os

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdPhysics

from .batteries import FLOOR_T, holder_design
from .catalog import CELLS, METRIC
from .usd import bind_physics, create_stage, physics_material, place, quat_axis_angle

MM = 1e-3
GROUND_FRICTION = 0.4


def new_scene(path, floor=True, floor_size=2.0, floor_visible=False, physics=True):
    """Stage with /World, a physics scene (gravity -Z, 9.81) and a floor collider whose top is z = 0.

    The floor has purpose 'guide' unless floor_visible: it collides but is not rendered.
    physics=False: no physics scene and no floor."""
    st = create_stage(path)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(st, 1.0)
    w = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(w.GetPrim())
    if not physics:
        return st
    ps = UsdPhysics.Scene.Define(st, "/World/PhysicsScene")
    ps.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    ps.CreateGravityMagnitudeAttr(9.81)
    if floor:
        g = UsdGeom.Cube.Define(st, "/World/ground")
        g.CreateSizeAttr(1.0)
        if not floor_visible:
            g.CreatePurposeAttr(UsdGeom.Tokens.guide)
        place(g, (0, 0, -0.01), (1, 0, 0, 0), (floor_size, floor_size, 0.02))
        UsdPhysics.CollisionAPI.Apply(g.GetPrim())
        bind_physics(g.GetPrim(), physics_material(st, "/World", "ground", GROUND_FRICTION))
    return st


def add_ref(st, prim_name, asset_file, pos, quat=(1, 0, 0, 0), finish=None):
    """Reference asset_file (path on disk) under /World/prim_name, relative to the scene's folder."""
    x = UsdGeom.Xform.Define(st, f"/World/{prim_name}")
    scene_dir = os.path.dirname(os.path.abspath(st.GetRootLayer().realPath))
    rel = os.path.relpath(os.path.abspath(asset_file), scene_dir).replace(os.sep, "/")
    x.GetPrim().GetReferences().AddReference(rel if rel.startswith(".") else f"./{rel}")
    place(x, pos, quat)
    if finish:
        vs = x.GetPrim().GetVariantSets().GetVariantSet("finish")
        vs.SetVariantSelection(finish)
    return x


# ------------------------------------------------------------------ rest poses on a floor at z = 0
def rest_pose(kind, key):
    """(position offset, quaternion) of a part resting on the floor, before a translation in x, y."""
    if kind == "screw":
        return (0, 0, METRIC[key]["k"] * MM), (1, 0, 0, 0)  # standing on its head
    if kind in ("nut", "washer", "holder"):
        return (0, 0, 0), (1, 0, 0, 0)
    c = CELLS[key]
    if c["kind"] == "cradle":
        return (0, 0, c["d"] / 2 * MM), (1, 0, 0, 0)  # lying, axis along x
    if c["kind"] == "nine_volt":
        return (0, 0, c["T"] / 2 * MM), (1, 0, 0, 0)
    return (0, 0, c["h"] / 2 * MM), (1, 0, 0, 0)  # coin, + face up


def footprint(kind, key, length=None):
    """Approximate (x, y) size of a part at rest (m), for laying parts out without overlap."""
    if kind in ("screw", "nut", "washer"):
        t = METRIC[key]
        s = max(t["s"], t["washer"][1]) * MM
        return s * 1.2, s * 1.2
    c = CELLS[key]
    if kind == "cell":
        if c["kind"] == "cradle":
            return c["L"] * MM, c["d"] * MM
        if c["kind"] == "nine_volt":
            return (c["L"] + 3) * MM, c["W"] * MM
        return c["d"] * MM, c["d"] * MM
    D = holder_design(key)
    if D["axis"] == "x":
        return (D["x_hi"] - D["x_lo"] + 2) * MM, (2 * D["width"] + 4) * MM
    return (D["r"] * 3.2 + 10) * MM, (2 * D["Rw"] + 5) * MM


def seated_overrides(fmt):
    """Pose of a cell seated in its holder (holder at the origin) and of the holder's moving contact.

    Returns (cell position, cell quaternion, {moving-contact prim name: (position, quaternion)})."""
    D = holder_design(fmt)
    c = CELLS[fmt]
    z0 = FLOOR_T * MM
    if D["axis"] == "x":
        hh = D["half_h"]
        cell = ((0, 0, (hh * MM) + z0), (1, 0, 0, 0))
        plate = ((D["x_seat"] * MM, 0, hh * MM + z0), (1, 0, 0, 0))  # spring compressed by the preload
        return cell[0], cell[1], {"spring_plate": plate}
    q = D["q_seat"]  # the cell lifts the clip by q_seat (rad) about +Y
    cell = ((0, 0, c["h"] / 2 * MM + z0), (1, 0, 0, 0))
    clip = ((D["xp"] * MM, 0, D["zp"] * MM + z0), (np.cos(q / 2), 0, np.sin(q / 2), 0))
    return cell[0], cell[1], {"clip": clip}


def place_seated(st, holder_prim, cell_prim, cell_file, fmt, holder_pos=(0, 0, 0), yaw=0.0):
    """Cell referenced under /World/cell_prim, seated in the holder already at /World/holder_prim."""
    qh = quat_axis_angle((0, 0, 1), yaw)
    from .usd import q2m, qmul

    Rh = q2m(qh)
    cpos, cq, movers = seated_overrides(fmt)
    add_ref(st, cell_prim, cell_file, np.asarray(holder_pos) + Rh @ np.asarray(cpos), qmul(qh, cq))
    for name, (p, q) in movers.items():
        place(st.OverridePrim(f"/World/{holder_prim}/{name}"), p, q)
    return st


def drop_pose(kind, key, height=0.04, tilt=(0.5, 0.35)):
    """A tilted pose some centimetres above the floor, for drop tests."""
    from .usd import qmul

    q = qmul(quat_axis_angle((1, 0, 0), tilt[0]), quat_axis_angle((0, 1, 0), tilt[1]))
    return (0, 0, height), q


def thread_height(size, turns_from_head):
    """Height (m) of a nut on a screw, in the screw frame, at a whole number of pitches."""
    return turns_from_head * METRIC[size]["P"] * MM


def save(st):
    st.GetRootLayer().Save()
    return st.GetRootLayer().realPath


def open_stage(path):
    return Usd.Stage.Open(path)
