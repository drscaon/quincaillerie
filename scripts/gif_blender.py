"""Frames of a physics animation, rendered with Cycles; runs inside Blender (pip `bpy` or blender -P).

drop  scene.usda out_dir n_frames W H samples ex ey ez tx ty tz lens
      import with the Quincaillerie add-on (rigid bodies set up on import), simulate, render
poses scene.usda out_dir 0 W H samples ex ey ez tx ty tz lens poses.json
      plain import, then per frame the poses of the listed prims (a MuJoCo simulation)
"""

import json
import os
import sys

import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src", "quincaillerie", "blender")
sys.path[:0] = [HERE, SRC]

import run  # noqa: E402,F401  (Blender's own pxr first, for the importer's hooks)
from physics import import_with_physics  # noqa: E402
from render_blender import studio  # noqa: E402

FPS = 24


def capture_prim_map(path):
    """Plain import; returns {prim path: object} through an import hook."""
    out = {}

    class Capture(bpy.types.USDHook):
        bl_idname = "quincaillerie_capture"
        bl_label = "capture"

        @staticmethod
        def on_import(context):
            for k, v in context.get_prim_map().items():
                obs = [o for o in v if isinstance(o, bpy.types.Object)]
                if obs:
                    out[str(k)] = obs[0]
            return True

    bpy.utils.register_class(Capture)
    bpy.ops.wm.usd_import(filepath=path, import_guide=False)
    bpy.utils.unregister_class(Capture)
    return out


def coil_followers(prim_map, scene_path):
    """For each holder coil: (coil object, base object, plate object, back face, free end) in the base frame."""
    from pxr import Usd

    st = Usd.Stage.Open(scene_path)
    out = []
    for p in st.Traverse():
        if p.GetName() == "spring_coil":
            base = p.GetParent().GetParent()
            plate = base.GetParent().GetPath().AppendChild("spring_plate")
            coil = prim_map.get(str(p.GetPath()))
            if coil is None:  # merged with its Xform: find the object that uses its mesh
                coil = next((o for o in bpy.data.objects if o.data and o.data.name.startswith("spring_coil")), None)
            out.append(
                (
                    coil,
                    prim_map[str(base.GetPath())],
                    prim_map[str(plate)],
                    p.GetAttribute("quincaillerie:backFace").Get(),
                    p.GetAttribute("quincaillerie:freeLengthEnd").Get(),
                )
            )
    return out


def main():
    a = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    mode, scene_path, out_dir, n = a[0], a[1], a[2], int(a[3])
    W, H, spp = int(a[4]), int(a[5]), int(a[6])
    eye, tgt, lens = tuple(map(float, a[7:10])), tuple(map(float, a[10:13])), float(a[13])
    poses = a[14] if len(a) > 14 else ""
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    if mode == "drop":
        sc.frame_start, sc.frame_end = 1, n
        import_with_physics(scene_path)
        sc.rigidbody_world.point_cache.frame_end = n
        studio(W, H, spp, eye, tgt, lens)
        for f in range(1, n + 1):
            sc.frame_set(f)
            sc.render.filepath = os.path.join(out_dir, f"f_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
        return
    pm = capture_prim_map(scene_path)
    coils = coil_followers(pm, scene_path)
    rest = {id(c[0]): (c[0].matrix_world.copy() if c[0] else None) for c in coils}
    studio(W, H, spp, eye, tgt, lens)
    with open(poses, encoding="utf-8") as f:
        frames = json.load(f)
    bpy.context.view_layer.update()
    for i, fr in enumerate(frames):
        for path, (p, q) in fr.items():
            o = pm[path]
            M = Matrix.Translation(Vector(p)) @ Quaternion(q).to_matrix().to_4x4()
            o.matrix_world = M
        bpy.context.view_layer.update()
        for coil, base, plate, back, free in coils:
            if coil is None:
                continue
            Wb = base.matrix_world
            x = (Wb.inverted() @ plate.matrix_world.translation).x  # plate contact face, base frame
            sx = max(0.05, (x - 0.001 - back) / (free - 0.001 - back))
            S = Matrix.Translation((back, 0, 0)) @ Matrix.Diagonal((sx, 1, 1, 1)) @ Matrix.Translation((-back, 0, 0))
            coil.matrix_world = Wb @ S @ Wb.inverted() @ rest[id(coil)]
        sc.render.filepath = os.path.join(out_dir, f"f_{i + 1:04d}.png")
        bpy.ops.render.render(write_still=True)


main()
