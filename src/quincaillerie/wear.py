"""Worn looks of one instance: rust, oil, dirt, scratches, scuffed labels, baked into small textures.

Each worn instance gets its own material next to the library ones: a UsdPreviewSurface whose base
colour, roughness and metalness are textures baked from the clean finish of the library and the
instance's wear (``variation.FastenerVariation`` / ``CellVariation``). The textures are tileable and
written to ``materials/instances/``; the clean finishes stay available in the "finish" variant set.
"""

from __future__ import annotations

import os

import numpy as np
from pxr import Sdf, UsdShade

from .materials import MATERIALS, _tileable_noise

SIZE = 256
# iron oxides, linear: orange-brown (fresh), dark red-brown, near-black (old, wet)
RUST = (np.array([0.14, 0.038, 0.011]), np.array([0.060, 0.016, 0.007]), np.array([0.020, 0.009, 0.006]))
DIRT = np.array([0.012, 0.010, 0.007])  # grime: dark, warm


def _srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)


def _mask(rng, amount, octaves=6, sharp=8.0):
    """Tileable patches covering about `amount` of the surface."""
    if amount <= 0:
        return np.zeros((SIZE, SIZE))
    n = _tileable_noise(SIZE, octaves, rng)
    t = np.quantile(n, 1 - amount)
    return np.clip((n - t) * sharp + 0.5, 0, 1) * (n > t - 0.5 / sharp)


def _spots(rng, amount):
    """Small spots (high-pass noise) covering about `amount` of the surface: scuffs, specks."""
    if amount <= 0:
        return np.zeros((SIZE, SIZE))
    n = _tileable_noise(SIZE, 8, rng) - 0.8 * _tileable_noise(SIZE, 3, rng)
    t = np.quantile(n, 1 - amount)
    return np.clip((n - t) / (np.ptp(n) * 0.05), 0, 1)


def _scratches(rng, amount):
    img = np.zeros((SIZE, SIZE))
    for _ in range(int(amount * 60)):
        x0, y0 = rng.uniform(0, SIZE, 2)
        a = rng.normal(0, 0.35)  # mostly along u (around the part, as when screwed in a tool)
        L = rng.uniform(10, 60)
        for s in np.linspace(0, L, int(L * 2)):
            x, y = int(x0 + s * np.cos(a)) % SIZE, int(y0 + s * np.sin(a)) % SIZE
            img[y, x] = 1.0
    return img


def _fit(m, shape):
    """A square map resized to the (h, w) of a label image."""
    if m.shape == shape:
        return m
    from PIL import Image

    return np.asarray(Image.fromarray((m * 65535).astype(np.uint16)).resize(shape[::-1], Image.BILINEAR)) / 65535.0


def bake(base, wear, seed, image=None):
    """Base colour (linear), roughness and metalness maps for a material and a wear dict
    (rust, oil, dirt, scratches, label_wear in 0..1). image: the material's colour texture (linear,
    h x w x 3) for printed labels; the maps then have its size."""
    rng = np.random.default_rng(seed)
    if image is None:
        col = np.broadcast_to(np.array(base["color"], float), (SIZE, SIZE, 3)).copy()
    else:
        col = image.astype(float).copy()
    shape = col.shape[:2]
    rough = np.full(shape, float(base["roughness"]))
    metal = np.full(shape, float(base["metallic"]))
    rough += (_fit(_tileable_noise(SIZE, 5, rng), shape) - 0.5) * 0.08
    s = _fit(_scratches(rng, wear.get("scratches", 0.0)), shape)
    if base["metallic"] > 0.5:
        col = col * (1 + 0.25 * s[..., None])
        rough = rough * (1 - 0.5 * s)
    else:
        col = col + 0.15 * s[..., None]
    lw = wear.get("label_wear", 0.0)
    if lw > 0:  # a handled label: faded colours, small scuffs, more of them near the ends of the cell
        grey = col.mean(-1, keepdims=True)
        col = col * (1 - 0.35 * lw) + grey * 0.35 * lw + 0.03 * lw
        u = np.linspace(0, 1, shape[1])[None, :]
        ends = np.exp(-((u / 0.1) ** 2)) + np.exp(-(((1 - u) / 0.1) ** 2))
        m = _fit(_spots(rng, 0.25 * lw), shape) * np.clip(0.25 + ends, 0, 1)
        col = col * (1 - m[..., None]) + np.array([0.75, 0.75, 0.73]) * m[..., None]  # the white under the print
        rough = rough + 0.35 * m
    ra = wear.get("rust", 0.0)
    if ra > 0:
        # patches with soft edges, pitted inside: a coarse mask times a fine speckle
        speck = _fit(_tileable_noise(SIZE, 8, rng), shape)
        r = _fit(_mask(rng, ra, 6, 10.0), shape)  # solid patches
        halo = _fit(_mask(rng, min(1.0, ra * 1.6), 6, 4.0), shape)  # pitting around them
        r = np.clip(np.maximum(r, halo * (speck > 0.6)), 0, 1)
        t1 = _fit(_tileable_noise(SIZE, 5, rng), shape)[..., None]
        t2 = _fit(_tileable_noise(SIZE, 7, rng), shape)[..., None]
        rust = RUST[0] * t1 + RUST[1] * (1 - t1)
        rust = rust * (1 - 0.6 * t2) + RUST[2] * 0.6 * t2
        col = col * (1 - r[..., None]) + rust * r[..., None]
        rough = rough * (1 - r) + (0.75 + 0.2 * speck) * r
        metal = metal * (1 - r) + 0.05 * r
    da = wear.get("dirt", 0.0)
    d = _fit(_spots(rng, 0.35 * da) if image is not None else _mask(rng, da, 6, 6.0), shape) * 0.97
    if d.any():  # grime in patches: darker, rougher, the metal shows through less
        col = col * (1 - d[..., None]) + DIRT * d[..., None]
        rough = rough * (1 - d) + 0.85 * d
        metal = metal * (1 - 0.85 * d)
    o = wear.get("oil", 0.0)
    if o > 0:  # a thin oil film: darker, glossier, a little yellow
        m = _fit(_mask(rng, min(1.0, 0.4 + 0.6 * o), 4, 3.0), shape) * o
        col = col * (1 - 0.35 * m[..., None]) * np.array([1.0, 0.97, 0.85]) ** m[..., None]
        rough = rough * (1 - 0.6 * m)
    return np.clip(col, 0, 1), np.clip(rough, 0.04, 1), np.clip(metal, 0, 1)


def instance_material(stage, root_path, name, base_name, wear, seed, tex_dir, tex_rel, library_textures=None):
    """Bake the textures (PNG in tex_dir, referenced as tex_rel/...) and define the material
    {root_path}/Looks/{name}. library_textures: folder of the library's textures, for printed labels.
    Returns its path."""
    from PIL import Image

    base = MATERIALS[base_name]
    image = None
    if "color_tex" in base and library_textures:
        im = np.asarray(Image.open(os.path.join(library_textures, base["color_tex"])).convert("RGB")) / 255.0
        image = np.where(im <= 0.04045, im / 12.92, ((im + 0.055) / 1.055) ** 2.4)  # sRGB -> linear
    col, rough, metal = bake(base, wear, seed, image)
    os.makedirs(tex_dir, exist_ok=True)
    files = {}
    for key, img, srgb in (("color", col, True), ("roughness", rough, False), ("metallic", metal, False)):
        data = _srgb(img) if srgb else img
        fn = f"{name}_{key}.png"
        Image.fromarray((np.clip(data, 0, 1) * 255).astype(np.uint8)).save(os.path.join(tex_dir, fn), optimize=True)
        files[key] = f"{tex_rel}/{fn}"
    P = f"{root_path}/Looks/{name}"
    mat = UsdShade.Material.Define(stage, P)
    mat.GetPrim().SetDocumentation(f"{base_name}, worn: " + ", ".join(f"{k} {v:.2f}" for k, v in wear.items() if v))
    ps = UsdShade.Shader.Define(stage, f"{P}/PreviewSurface")
    ps.CreateIdAttr("UsdPreviewSurface")
    uv = UsdShade.Shader.Define(stage, f"{P}/uv")
    uv.CreateIdAttr("UsdPrimvarReader_float2")
    uv.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    for key, inp, typ, out in (
        ("color", "diffuseColor", Sdf.ValueTypeNames.Color3f, "rgb"),
        ("roughness", "roughness", Sdf.ValueTypeNames.Float, "r"),
        ("metallic", "metallic", Sdf.ValueTypeNames.Float, "r"),
    ):
        t = UsdShade.Shader.Define(stage, f"{P}/{key}_tex")
        t.CreateIdAttr("UsdUVTexture")
        t.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(files[key])
        t.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB" if key == "color" else "raw")
        t.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        t.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        t.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(), "result")
        t.CreateOutput(out, Sdf.ValueTypeNames.Float3 if out == "rgb" else Sdf.ValueTypeNames.Float)
        ps.CreateInput(inp, typ).ConnectToSource(t.ConnectableAPI(), out)
    ps.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.5)
    if "coat" in MATERIALS[base_name]:
        ps.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(float(MATERIALS[base_name]["coat"][0]))
    mat.CreateSurfaceOutput().ConnectToSource(ps.ConnectableAPI(), "surface")
    return P
