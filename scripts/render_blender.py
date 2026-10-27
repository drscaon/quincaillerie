"""Path-traced render (Blender Cycles, CPU) of a Quincaillerie OpenUSD scene, materials as authored.

A dark grey cyclorama, soft area lights, AgX. Development tool (needs `pip install bpy`):

    python scripts/render_blender.py scene.usda out.png W H samples ex ey ez tx ty tz lens_mm [fstop]

EXPOSURE (environment variable, default -1.3) sets the view exposure.
"""

import math
import os
import sys

import bpy
from mathutils import Vector


def backdrop(radius=0.12, depth=0.6, width=1.2, y=0.05, grey=0.22):
    """Curved backdrop: a floor that bends up into a wall behind the subject."""
    import bmesh  # available once bpy is imported

    me = bpy.data.meshes.new("backdrop")
    bd = bpy.data.objects.new("backdrop", me)
    bpy.context.scene.collection.objects.link(bd)
    bm = bmesh.new()
    nx, ny = 2, 60
    rows = []
    for j in range(ny + 1):
        s = j / ny * (depth + math.pi * radius / 2 + 0.4)
        if s < depth:
            yy, z = -depth / 2 + s, 0.0
        elif s < depth + math.pi * radius / 2:
            a = (s - depth) / radius
            yy, z = depth / 2 + radius * math.sin(a), radius * (1 - math.cos(a))
        else:
            yy, z = depth / 2 + radius, radius + (s - depth - math.pi * radius / 2)
        rows.append([bm.verts.new((-width / 2 + i * width / nx, yy, z)) for i in range(nx + 1)])
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]))
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    bd.location.y = y
    mat = bpy.data.materials.new("backdrop")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (grey, grey, grey * 1.04, 1)
    bsdf.inputs["Roughness"].default_value = 0.65
    me.materials.append(mat)
    return bd


def area(name, loc, size, energy, color=(1, 1, 1), size_y=None):
    sc = bpy.context.scene
    light = bpy.data.lights.new(name, "AREA")
    light.energy, light.color, light.shape, light.size = energy, color, "RECTANGLE", size
    light.size_y = size_y or size
    o = bpy.data.objects.new(name, light)
    sc.collection.objects.link(o)
    o.location = loc
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (Vector((0, 0, 0.01)) - Vector(loc)).to_track_quat("-Z", "Y")
    return o


def render(scene_path, out, W, H, spp, eye, tgt, lens, fstop=0.0):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.usd_import(filepath=scene_path, import_guide=False, import_proxy=False)
    studio(W, H, spp, eye, tgt, lens, fstop)
    sc = bpy.context.scene
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)


def studio(W, H, spp, eye, tgt, lens, fstop=0.0):
    """Backdrop, lights, camera and Cycles settings around what is in the scene."""
    sc = bpy.context.scene
    backdrop()
    area("key", (-0.40, -0.25, 0.45), 0.30, 18, (1.0, 0.97, 0.92), 0.12)
    area("fill", (0.45, -0.35, 0.20), 0.30, 3, (0.92, 0.95, 1.0))
    area("rim", (0.15, 0.40, 0.30), 0.70, 22, (1, 1, 1), 0.05)
    area("top", (0.0, -0.10, 0.70), 0.9, 2, (1, 1, 1), 0.04)
    world = bpy.data.worlds.new("world")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.55, 0.56, 0.58, 1)
    bg.inputs["Strength"].default_value = 0.06
    cam = bpy.data.cameras.new("cam")
    cam.lens, cam.clip_start, cam.clip_end = lens, 0.002, 10
    co = bpy.data.objects.new("cam", cam)
    sc.collection.objects.link(co)
    sc.camera = co
    eye, tgt = Vector(eye), Vector(tgt)
    co.location = eye
    co.rotation_mode = "QUATERNION"
    co.rotation_quaternion = (tgt - eye).to_track_quat("-Z", "Y")
    if fstop > 0:
        cam.dof.use_dof = True
        cam.dof.focus_distance = (tgt - eye).length
        cam.dof.aperture_fstop = fstop
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = spp
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces, sc.cycles.glossy_bounces = 8, 6
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = float(os.environ.get("EXPOSURE", "-1.3"))
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass


if __name__ == "__main__":
    a = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    render(
        a[0],
        a[1],
        int(a[2]),
        int(a[3]),
        int(a[4]),
        tuple(map(float, a[5:8])),
        tuple(map(float, a[8:11])),
        float(a[11]),
        float(a[12]) if len(a) > 12 else 0.0,
    )
