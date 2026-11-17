"""OpenUSD scenes that reference the assets: a floor collider, gravity, and parts placed at rest.

Scenes never copy an asset: they reference its file by a relative path, and author poses, variant
selections and the pose of a holder's moving contact as overrides.
"""

from __future__ import annotations

import os

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics, UsdSemantics

from .batteries import FLOOR_T, holder_design
from .catalog import CELLS, METRIC
from .contract import set_group
from .ground import GROUND_MARGIN, ground, physics_scene
from .usd import create_stage, place, quat_axis_angle

MM = 1e-3


def new_scene(path, floor=True, floor_size=2.0, physics=True):
    """Stage with /World, the shared physics scene and ground (ground.py: gravity 9.81 along -Z,
    a 2 cm box whose top is z = 0, floor_size × floor_size, rendered like every Primvaria ground).
    physics=False: no physics scene and no floor."""
    st = create_stage(path)
    UsdGeom.SetStageMetersPerUnit(st, 1.0)
    UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(st, 1.0)
    w = UsdGeom.Xform.Define(st, "/World")
    st.SetDefaultPrim(w.GetPrim())
    set_group(w.GetPrim(), assembly=True)  # Primvaria contract: the assets under it are components
    if not physics:
        return st
    physics_scene(st)
    if floor:
        add_floor(st, floor_size)
    return st


def add_floor(st, floor_size=2.0, reach=(0.0, 0.0)):
    """The shared ground, floor_size x floor_size around the origin, extended to cover content
    that reaches (x, y) = reach."""
    inner = max(floor_size / 2 - GROUND_MARGIN, 0.0)  # the content's footprint, the margin added
    ground(st, (-inner, -inner), (max(inner, reach[0]), max(inner, reach[1])))


def add_ref(st, prim_name, asset_file, pos, quat=(1, 0, 0, 0), finish=None):
    """Reference asset_file (path on disk) under /World/prim_name, relative to the scene's folder."""
    x = UsdGeom.Xform.Define(st, f"/World/{prim_name}")
    scene_dir = os.path.dirname(os.path.abspath(st.GetRootLayer().realPath))
    rel = os.path.relpath(os.path.abspath(asset_file), scene_dir).replace(os.sep, "/")
    x.GetPrim().GetReferences().AddReference(rel if rel.startswith(".") else f"./{rel}")
    # in a scene the instance is the prim that places the part (its classes come from the part)
    UsdSemantics.LabelsAPI.Apply(x.GetPrim(), "instance").CreateLabelsAttr([prim_name])
    place(x, pos, quat)
    if finish:
        vs = x.GetPrim().GetVariantSets().GetVariantSet("finish")
        vs.SetVariantSelection(finish)
    return x


# ------------------------------------------------------------------ rest poses on a floor at z = 0
def rest_pose(kind, key):
    """(position offset, quaternion) of a part resting on the floor, before a translation in x, y."""
    # every part's underside is at z = 0 of its file (contract, section 3): a screw stands on its
    # head, a cylindrical cell lies with its axis along x, a coin cell + face up, as written
    return (0, 0, 0), (1, 0, 0, 0)


def centre_height(part_file) -> float:
    """Height (m) of a part's centre above its underside, which is z = 0 of its file."""
    stage = Usd.Stage.Open(str(part_file))
    purposes = [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.guide]
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), purposes).ComputeUntransformedBound(stage.GetDefaultPrim())
    rng = box.ComputeAlignedRange()
    return (rng.GetMin()[2] + rng.GetMax()[2]) / 2


def under_head(screw_file) -> float:
    """Height (m) of the face under a screw's head above its underside: where its MateFrame_thread
    is, what a washer or a nut on it rests against."""
    stage = Usd.Stage.Open(str(screw_file))
    frame = stage.GetDefaultPrim().GetChild("MateFrame_thread")
    return UsdGeom.XformCache().GetLocalToWorldTransform(frame).ExtractTranslation()[2]


def origin_for(centre, quat, height):
    """Where to place a part whose centre, ``height`` above its origin, goes to ``centre`` turned
    by ``quat`` (w, x, y, z)."""
    from .usd import q2m

    return np.asarray(centre, float) - q2m(quat) @ np.array([0, 0, height])


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
    z0 = FLOOR_T * MM
    if D["axis"] == "x":
        hh = D["half_h"]
        cell = ((0, 0, z0), (1, 0, 0, 0))  # on the bed: the cell's underside is at z = 0 of its file
        plate = ((D["x_seat"] * MM, 0, hh * MM + z0), (1, 0, 0, 0))  # spring compressed by the preload
        return cell[0], cell[1], {"spring_plate": plate}
    q = D["q_seat"]  # the cell lifts the clip by q_seat (rad) about +Y
    cell = ((0, 0, z0), (1, 0, 0, 0))
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
