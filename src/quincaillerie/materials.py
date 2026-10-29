"""Material library: physically based finishes for fasteners, springs, cells and holders.

One library layer (materials/quincaillerie_materials.usda) holds every material twice:

* outputs:surface -> a UsdPreviewSurface network (Blender, usdview, Omniverse, Houdini...);
* outputs:mtlx:surface -> a MaterialX standard_surface network (Omniverse, Houdini, Maya...);

plus a standalone MaterialX document (quincaillerie_materials.mtlx), validated against the MaterialX
standard library when the MaterialX package is installed. Textures (roughness variation, plastic grain
normal map, generic cell labels) are generated procedurally. Base colours are linear; metal colours
approximate measured reflectance at normal incidence. Assets reference the library by a relative path,
so the materials/ folder must sit next to the assets/ folder.
"""

from __future__ import annotations

import os

import numpy as np
from pxr import Gf, Sdf, UsdGeom, UsdPhysics, UsdShade

# name: (base colour, metallic, roughness, extras)
# extras: rough_tex (texture, scale, bias), normal_tex, color_tex, coat (weight, roughness), specular
MATERIALS = {
    # ---- metal finishes (fasteners, contacts, springs, cans)
    "zinc_clear": dict(
        color=(0.74, 0.77, 0.81),
        metallic=1.0,
        roughness=0.30,
        rough_tex=("noise_rough.png", 0.16, 0.22),
        desc="electro-zinc plated steel, clear/blue passivation",
    ),
    "zinc_yellow": dict(
        color=(0.80, 0.67, 0.33),
        metallic=1.0,
        roughness=0.30,
        rough_tex=("noise_rough.png", 0.16, 0.22),
        desc="electro-zinc plated steel, yellow chromate passivation",
    ),
    "black_oxide": dict(
        color=(0.055, 0.055, 0.06),
        metallic=1.0,
        roughness=0.45,
        rough_tex=("noise_rough.png", 0.20, 0.35),
        desc="black oxide (bruni) steel, light oil",
    ),
    "stainless_a2": dict(
        color=(0.63, 0.62, 0.60),
        metallic=1.0,
        roughness=0.22,
        rough_tex=("turned_rough.png", 0.14, 0.15),
        desc="austenitic stainless steel A2",
    ),
    "steel_plain": dict(
        color=(0.56, 0.57, 0.58),
        metallic=1.0,
        roughness=0.38,
        rough_tex=("turned_rough.png", 0.18, 0.28),
        desc="plain steel, lightly oiled",
    ),
    "brass": dict(
        color=(0.91, 0.78, 0.42),
        metallic=1.0,
        roughness=0.24,
        rough_tex=("turned_rough.png", 0.14, 0.17),
        desc="brass CuZn",
    ),
    "nickel_bright": dict(
        color=(0.70, 0.67, 0.62),
        metallic=1.0,
        roughness=0.16,
        rough_tex=("noise_rough.png", 0.08, 0.12),
        desc="bright nickel plating (contacts, clips)",
    ),
    "nickel_can": dict(
        color=(0.68, 0.66, 0.62),
        metallic=1.0,
        roughness=0.26,
        rough_tex=("noise_rough.png", 0.12, 0.20),
        desc="nickel-plated steel cell can",
    ),
    "spring_steel": dict(
        color=(0.52, 0.53, 0.54),
        metallic=1.0,
        roughness=0.24,
        rough_tex=("turned_rough.png", 0.12, 0.18),
        desc="music wire (EN 10270-1), oiled",
    ),
    # ---- plastics
    "abs_black": dict(
        color=(0.018, 0.018, 0.02),
        metallic=0.0,
        roughness=0.52,
        normal_tex="plastic_normal.png",
        rough_tex=("noise_rough.png", 0.12, 0.46),
        specular=0.5,
        desc="black ABS, light mould texture",
    ),
    "abs_grey": dict(
        color=(0.30, 0.31, 0.32),
        metallic=0.0,
        roughness=0.50,
        normal_tex="plastic_normal.png",
        rough_tex=("noise_rough.png", 0.12, 0.44),
        specular=0.5,
        desc="grey ABS, light mould texture",
    ),
    # ---- cells: printed PET wrapper (label texture), varnished
    "label_9V": dict(
        color=(1, 1, 1),
        metallic=0.0,
        roughness=0.30,
        color_tex="label_9V.png",
        coat=(0.6, 0.08),
        desc="printed 9V label",
    ),
    "case_9V": dict(
        color=(0.03, 0.03, 0.035), metallic=0.0, roughness=0.35, coat=(0.4, 0.12), desc="9V case, black plastic"
    ),
}
MATERIALS["corrosion"] = dict(
    color=(0.62, 0.66, 0.55),
    metallic=0.0,
    roughness=0.95,
    rough_tex=("noise_rough.png", 0.1, 0.88),
    desc="potassium carbonate / zinc oxide crust of a leaking cell, white-green",
)
CELL_FORMATS = ["AAA", "AA", "C", "D", "CR123A", "18650", "21700"]
for f in CELL_FORMATS:
    MATERIALS[f"wrapper_{f}"] = dict(
        color=(1, 1, 1),
        metallic=0.0,
        roughness=0.28,
        color_tex=f"label_{f}.png",
        coat=(0.7, 0.06),
        desc=f"printed PET wrapper, {f}",
    )
for f in ("CR2032", "LR44"):
    MATERIALS[f"coin_top_{f}"] = dict(
        color=(1, 1, 1),
        metallic=1.0,
        roughness=0.22,
        color_tex=f"coin_{f}.png",
        desc=f"nickel-plated + face of a {f}, laser-marked",
    )

FINISHES = ["zinc_clear", "zinc_yellow", "black_oxide", "stainless_a2", "steel_plain", "brass"]


# ------------------------------------------------------------------------------- textures
def _font(size, bold=True):
    """DejaVu Sans (system or matplotlib's copy), else Pillow's built-in font."""
    from PIL import ImageFont

    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    candidates = [f"/usr/share/fonts/truetype/dejavu/{name}", f"/Library/Fonts/{name}", f"C:/Windows/Fonts/{name}"]
    try:
        import matplotlib

        candidates.insert(0, os.path.join(matplotlib.get_data_path(), "fonts", "ttf", name))
    except ImportError:
        pass
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    try:
        return ImageFont.load_default(size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def _tileable_noise(n, octaves, rng):
    img = np.zeros((n, n))
    for o in range(octaves):
        f = 2 ** (o + 2)
        g = rng.normal(size=(f, f))
        # periodic bicubic-ish upsampling through FFT
        G = np.fft.fft2(g)
        H = np.zeros((n, n), complex)
        h = f // 2
        H[:h, :h] = G[:h, :h]
        H[:h, -h:] = G[:h, -h:]
        H[-h:, :h] = G[-h:, :h]
        H[-h:, -h:] = G[-h:, -h:]
        layer = np.real(np.fft.ifft2(H)) * (n * n) / (f * f)
        img += layer / (1.6**o)
    img = (img - img.min()) / (np.ptp(img) + 1e-12)
    return img


LABELS = {  # IEC designation, nominal voltage, chemistry text, colours (band, background)
    "AAA": ("LR03", "1.5 V", "ALKALINE", (165, 32, 38)),
    "AA": ("LR6", "1.5 V", "ALKALINE", (28, 72, 160)),
    "C": ("LR14", "1.5 V", "ALKALINE", (214, 112, 26)),
    "D": ("LR20", "1.5 V", "ALKALINE", (40, 128, 76)),
    "CR123A": ("CR17345", "3 V", "LITHIUM", (38, 38, 42)),
    "18650": ("INR18650", "3.6 V", "LI-ION", (110, 62, 150)),
    "21700": ("INR21700", "3.6 V", "LI-ION", (24, 136, 150)),
    "9V": ("6LR61", "9 V", "ALKALINE", (210, 150, 30)),
}


def make_textures(out):
    from PIL import Image, ImageDraw

    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(3)
    n = 1024
    noise = _tileable_noise(n, 6, rng)
    Image.fromarray((noise * 255).astype(np.uint8)).save(f"{out}/noise_rough.png")
    # turning marks: fine circumferential lines (vary along v only) + a little noise
    v = np.linspace(0, 1, n, endpoint=False)
    lines = 0.5 + 0.5 * np.sin(2 * np.pi * v * 180 + 1.3 * np.sin(2 * np.pi * v * 7))
    turned = 0.65 * lines[:, None] + 0.35 * _tileable_noise(n, 5, rng)
    turned = (turned - turned.min()) / np.ptp(turned)
    Image.fromarray((turned * 255).astype(np.uint8)).save(f"{out}/turned_rough.png")
    # plastic grain: tangent-space normal map from a fine, low-relief height field (mould texture)
    hgt = 0.7 * _tileable_noise(n, 8, rng) + 0.3 * _tileable_noise(n, 6, rng)
    hp = hgt
    gy, gx = np.gradient(hp)
    k = 0.10 / max(np.abs(gx).max(), np.abs(gy).max())  # steepest slope ~ 6 degrees
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(gx)
    L = np.sqrt(nx**2 + ny**2 + nz**2)
    nm = np.stack([nx / L, ny / L, nz / L], -1) * 0.5 + 0.5
    Image.fromarray((nm * 255).astype(np.uint8)).save(f"{out}/plastic_normal.png")
    # cylindrical cell labels: x = along the cell (- end on the left), y = around the circumference
    for f in CELL_FORMATS:
        iec, volt, chem, col = LABELS[f]
        W, H = 2048, 1024
        img = Image.new("RGB", (W, H), col)
        d = ImageDraw.Draw(img)
        dark = tuple(int(c * 0.55) for c in col)
        d.rectangle([0, 0, W, int(H * 0.06)], fill=dark)
        d.rectangle([0, int(H * 0.94), W, H], fill=dark)
        d.rectangle([int(W * 0.70), 0, int(W * 0.73), H], fill=(235, 235, 235))
        for y0 in (0.12, 0.62):  # the label twice around the cell
            y = int(H * y0)
            d.text((int(W * 0.06), y), f, font=_font(int(H * 0.19)), fill=(255, 255, 255))
            d.text(
                (int(W * 0.06), y + int(H * 0.20)),
                f"{iec}  ·  {volt}  ·  {chem}",
                font=_font(int(H * 0.055), False),
                fill=(235, 235, 235),
            )
            d.text((int(W * 0.78), y + int(H * 0.04)), "+", font=_font(int(H * 0.2)), fill=(255, 255, 255))
            d.text(
                (int(W * 0.40), y + int(H * 0.06)), "QUINCAILLERIE", font=_font(int(H * 0.045)), fill=(255, 255, 255)
            )
            d.text(
                (int(W * 0.40), y + int(H * 0.115)),
                "synthetic test cell",
                font=_font(int(H * 0.04), False),
                fill=(230, 230, 230),
            )
        img.save(f"{out}/label_{f}.png")
    # 9V label (box UV: one face strip), coin markings
    W, H = 1024, 512
    img = Image.new("RGB", (W, H), LABELS["9V"][3])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, int(H * 0.12)], fill=(25, 25, 28))
    d.rectangle([0, int(H * 0.88), W, H], fill=(25, 25, 28))
    d.text((int(W * 0.06), int(H * 0.22)), "9V", font=_font(int(H * 0.36)), fill=(25, 25, 28))
    d.text(
        (int(W * 0.06), int(H * 0.62)),
        "6LR61  ·  ALKALINE  ·  QUINCAILLERIE",
        font=_font(int(H * 0.07), False),
        fill=(25, 25, 28),
    )
    img.save(f"{out}/label_9V.png")
    for f, txt in (("CR2032", "CR2032\n3V  +"), ("LR44", "LR44\n1.5V +")):
        S = 1024
        base = (172, 170, 166)
        img = Image.new("RGB", (S, S), base)
        d = ImageDraw.Draw(img)
        g = (_tileable_noise(S, 5, rng) * 18).astype(np.int16)
        arr = np.array(img).astype(np.int16) + g[..., None] - 9
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img)
        d.multiline_text(
            (S // 2, S // 2),
            txt,
            font=_font(int(S * 0.13)),
            fill=(118, 118, 116),
            anchor="mm",
            align="center",
            spacing=20,
        )
        img.save(f"{out}/coin_{f}.png")


# ---------------------------------------------------------------------------- USD library
def _uv_reader(stage, path):
    r = UsdShade.Shader.Define(stage, path)
    r.CreateIdAttr("UsdPrimvarReader_float2")
    r.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    return r


def _tex(stage, path, file, uv, cs="raw", scale=None, bias=None):
    t = UsdShade.Shader.Define(stage, path)
    t.CreateIdAttr("UsdUVTexture")
    t.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"./textures/{file}")
    t.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set(cs)
    t.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
    t.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
    t.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(uv.ConnectableAPI(), "result")
    if scale is not None:
        t.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(*scale))
        t.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(*bias))
    return t


def write_library(path):
    from .usd import create_stage

    stage = create_stage(path)
    # the same stage metadata as the assets that reference the library
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    root = stage.DefinePrim("/Materials", "Scope")
    stage.SetDefaultPrim(root)
    for name, m in MATERIALS.items():
        P = f"/Materials/{name}"
        mat = UsdShade.Material.Define(stage, P)
        mat.GetPrim().SetDocumentation(m.get("desc", ""))
        # --- UsdPreviewSurface
        ps = UsdShade.Shader.Define(stage, f"{P}/PreviewSurface")
        ps.CreateIdAttr("UsdPreviewSurface")
        ps.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(m["metallic"]))
        ps.CreateInput("ior", Sdf.ValueTypeNames.Float).Set(1.5)
        if "coat" in m:
            ps.CreateInput("clearcoat", Sdf.ValueTypeNames.Float).Set(float(m["coat"][0]))
            ps.CreateInput("clearcoatRoughness", Sdf.ValueTypeNames.Float).Set(float(m["coat"][1]))
        uv = None
        if any(k in m for k in ("rough_tex", "normal_tex", "color_tex")):
            uv = _uv_reader(stage, f"{P}/uv")
        if "color_tex" in m:
            t = _tex(stage, f"{P}/base_color_tex", m["color_tex"], uv, "sRGB")
            ps.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(t.ConnectableAPI(), "rgb")
            t.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
        else:
            ps.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*m["color"]))
        if "rough_tex" in m:
            f, sc, bi = m["rough_tex"]
            t = _tex(stage, f"{P}/roughness_tex", f, uv, "raw", (sc, sc, sc, 1), (bi, bi, bi, 0))
            t.CreateOutput("r", Sdf.ValueTypeNames.Float)
            ps.CreateInput("roughness", Sdf.ValueTypeNames.Float).ConnectToSource(t.ConnectableAPI(), "r")
        else:
            ps.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(m["roughness"]))
        if "normal_tex" in m:
            t = _tex(stage, f"{P}/normal_tex", m["normal_tex"], uv, "raw", (2, 2, 2, 1), (-1, -1, -1, 0))
            t.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
            ps.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(t.ConnectableAPI(), "rgb")
        mat.CreateSurfaceOutput().ConnectToSource(ps.ConnectableAPI(), "surface")
        # --- MaterialX standard_surface (render context "mtlx")
        ss = UsdShade.Shader.Define(stage, f"{P}/mtlx_standard_surface")
        ss.CreateIdAttr("ND_standard_surface_surfaceshader")
        ss.CreateInput("base", Sdf.ValueTypeNames.Float).Set(1.0)
        ss.CreateInput("metalness", Sdf.ValueTypeNames.Float).Set(float(m["metallic"]))
        ss.CreateInput("specular_IOR", Sdf.ValueTypeNames.Float).Set(1.5)
        if "coat" in m:
            ss.CreateInput("coat", Sdf.ValueTypeNames.Float).Set(float(m["coat"][0]))
            ss.CreateInput("coat_roughness", Sdf.ValueTypeNames.Float).Set(float(m["coat"][1]))
        if "color_tex" in m:
            ng = UsdShade.NodeGraph.Define(stage, f"{P}/mtlx_graph")
            img = UsdShade.Shader.Define(stage, f"{P}/mtlx_graph/base_color_image")
            img.CreateIdAttr("ND_image_color3")
            img.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"./textures/{m['color_tex']}")
            img.CreateOutput("out", Sdf.ValueTypeNames.Color3f)
            o = ng.CreateOutput("base_color", Sdf.ValueTypeNames.Color3f)
            o.ConnectToSource(img.ConnectableAPI(), "out")
            ss.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).ConnectToSource(o)
        else:
            ss.CreateInput("base_color", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*m["color"]))
        ss.CreateInput("specular_roughness", Sdf.ValueTypeNames.Float).Set(float(m["roughness"]))
        ss.CreateOutput("out", Sdf.ValueTypeNames.Token)
        mat.CreateSurfaceOutput("mtlx").ConnectToSource(ss.ConnectableAPI(), "out")
    stage.GetRootLayer().Save()


def write_mtlx(path):
    import MaterialX as mx

    doc = mx.createDocument()
    for name, m in MATERIALS.items():
        sh = doc.addNode("standard_surface", f"SR_{name}", "surfaceshader")
        sh.setInputValue("base", 1.0)
        sh.setInputValue("metalness", float(m["metallic"]))
        sh.setInputValue("specular_roughness", float(m["roughness"]))
        sh.setInputValue("specular_IOR", 1.5)
        if "coat" in m:
            sh.setInputValue("coat", float(m["coat"][0]))
            sh.setInputValue("coat_roughness", float(m["coat"][1]))
        if "color_tex" in m:
            img = doc.addNode("image", f"IMG_{name}", "color3")
            img.setInputValue("file", f"textures/{m['color_tex']}", "filename")
            sh.addInput("base_color", "color3").setConnectedNode(img)
        else:
            sh.setInputValue("base_color", mx.Color3(*m["color"]))
        mat = doc.addMaterialNode(f"M_{name}", sh)
        mat.setDocString(m.get("desc", ""))
    doc.importLibrary(_stdlib())
    ok, msg = doc.validate()
    mx.writeToXmlFile(doc, path, _write_opts())
    return ok, msg


def _stdlib():
    import MaterialX as mx

    lib = mx.createDocument()
    search = mx.getDefaultDataSearchPath()
    mx.loadLibraries(mx.getDefaultDataLibraryFolders(), search, lib)
    return lib


def _write_opts():
    import MaterialX as mx

    o = mx.XmlWriteOptions()
    o.elementPredicate = lambda e: not e.hasSourceUri()
    return o


LIBRARY_FILE = "quincaillerie_materials.usda"


def write_materials(out_dir):
    """Textures, USD library and (if MaterialX is installed) the .mtlx document, under out_dir.

    Returns a dict: number of materials, and MaterialX validation (None when not installed)."""
    os.makedirs(out_dir, exist_ok=True)
    make_textures(os.path.join(out_dir, "textures"))
    write_library(os.path.join(out_dir, LIBRARY_FILE))
    try:
        import MaterialX  # noqa: F401
    except ImportError:
        mtlx = None
    else:
        mtlx = write_mtlx(os.path.join(out_dir, "quincaillerie_materials.mtlx"))[0]
    return dict(materials=len(MATERIALS), materialx_valid=mtlx)
