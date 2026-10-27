"""Build the README images: logo, fastener and cell renders, GitHub social preview.

Development tool, not part of the package. Needs the dev extras, MuJoCo (loose parts are dropped in
MuJoCo so that they rest as they would), cairosvg for the logo PNG, and Blender as a Python module
(`pip install bpy`, Python 3.13) for the Cycles renders:

    python scripts/readme_images.py [--samples 128] [--out docs/images] [--only fasteners,cells,social]
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from quincaillerie import catalog_parts, generate
from quincaillerie.catalog import CELLS, METRIC, SIZES
from quincaillerie.materials import FINISHES
from quincaillerie.scenes import add_ref, new_scene, place_seated, save
from quincaillerie.usd import place, qmul, quat_axis_angle

HERE = Path(__file__).resolve().parent
MM = 1e-3


def settle(scene_path, seconds=1.5, dt=2e-4):
    """Drop the scene in MuJoCo and write the resting poses back into it (loose parts only)."""
    import mujoco
    from pxr import Usd

    from quincaillerie.sim.mujoco_model import convert

    st = Usd.Stage.Open(str(scene_path))
    xml = convert(
        st,
        options=f'<option timestep="{dt}" integrator="implicitfast" cone="elliptic"/>',
        default='<default><geom solref="0.002 1" solimp="0.95 0.99 0.0002" condim="4"/></default>',
    )
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    for _ in range(int(seconds / dt)):
        mujoco.mj_step(m, d)
    for i in range(1, m.nbody):
        p = st.GetPrimAtPath(f"/World/{m.body(i).name}")
        if p and m.body_jntnum[i] and m.jnt_type[m.body_jntadr[i]] == 0:  # free bodies only
            place(p, d.xpos[i], d.xquat[i])
    st.GetRootLayer().Save()


def fasteners_scene(assets, path):
    """Every size: a screw standing on its head with a washer and a nut; in front, loose parts."""
    loose = new_scene(path.with_name("loose.usda"))
    st = new_scene(path)
    x = -0.105
    for i, s in enumerate(SIZES):
        t = METRIC[s]
        fin = FINISHES[i % len(FINISHES)]
        k, P, h = t["k"] * MM, t["P"] * MM, t["washer"][2] * MM
        L = [p for p in os.listdir(assets) if p.startswith(f"ISO4017_{s}x")][0]
        add_ref(st, f"screw_{s}", assets / L, (x, 0.012, k), quat_axis_angle((0, 0, 1), 0.3 * i), fin)
        add_ref(st, f"washer_{s}", assets / f"ISO7089_{s}.usda", (x, 0.012, k), (1, 0, 0, 0), fin)
        phi = 0.5 + 0.4 * i  # a nut turned by phi sits P phi / 2 pi higher on a right-hand thread
        n = int(np.ceil(h / P)) + 2 + i % 3
        add_ref(
            st,
            f"nut_{s}",
            assets / f"ISO4032_{s}.usdc",
            (x, 0.012, k + n * P + P * phi / (2 * np.pi)),
            quat_axis_angle((0, 0, 1), phi),
            fin,
        )
        rng = np.random.default_rng(i)
        add_ref(
            loose,
            f"lnut_{s}",
            assets / f"ISO4032_{s}.usdc",
            (x - 0.004, -0.018, 0.003),
            quat_axis_angle((0, 0, 1), rng.uniform(0, 6)),
            fin,
        )
        add_ref(
            loose,
            f"lwasher_{s}",
            assets / f"ISO7089_{s}.usda",
            (x + 0.006, -0.036, 0.003),
            (1, 0, 0, 0),
            FINISHES[(i + 2) % 6],
        )
        x += max(t["washer"][1], 12) * MM + 0.011
    for j, (s, fin) in enumerate((("M10", "black_oxide"), ("M8", "brass"), ("M6", "stainless_a2"))):
        L = [p for p in os.listdir(assets) if p.startswith(f"ISO4017_{s}x")][0]
        q = qmul(quat_axis_angle((0, 0, 1), 0.25 - 0.35 * j), quat_axis_angle((0, 1, 0), np.pi / 2))
        add_ref(loose, f"lscrew_{s}", assets / L, (-0.06 + 0.06 * j, -0.065, 0.012), q, fin)
    save(loose)
    settle(path.with_name("loose.usda"))
    st.GetRootLayer().subLayerPaths.append("./loose.usda")  # the settled loose parts
    return save(st)


def cells_scene(assets, path):
    """Cells standing in a row; behind, holders with their cell seated."""
    st = new_scene(path)
    up = quat_axis_angle((0, 1, 0), -np.pi / 2)  # cell axis x -> z: standing on its - end
    x = -0.125
    for i, n in enumerate(["AAA", "AA", "CR123A", "18650", "21700", "C", "D"]):
        c = CELLS[n]
        r = c["d"] / 2 * MM
        q = qmul(quat_axis_angle((0, 0, 1), -1.35 + 0.15 * i), up)
        add_ref(st, f"cell_{n}", assets / f"Cell_{n}.usda", (x + r, -0.080 + 0.004 * (i % 2), c["L"] / 2 * MM), q)
        x += c["d"] * MM + 0.008
    add_ref(
        st,
        "cell_9V",
        assets / "Cell_9V.usda",
        (x + 0.012, -0.078, 0.0485 / 2),
        qmul(quat_axis_angle((0, 0, 1), -0.35), up),
    )
    add_ref(
        st, "cell_CR2032", assets / "Cell_CR2032.usda", (x + 0.045, -0.090, 0.0016), quat_axis_angle((0, 0, 1), 0.4)
    )
    add_ref(st, "cell_LR44", assets / "Cell_LR44.usda", (x + 0.052, -0.065, 0.0027), quat_axis_angle((0, 0, 1), 0.1))
    flip = qmul(quat_axis_angle((0, 0, 1), 1.2), quat_axis_angle((1, 0, 0), np.pi))
    add_ref(st, "cell_CR2032_b", assets / "Cell_CR2032.usda", (x + 0.072, -0.085, 0.0016), flip)
    for n, (hx, hy, yaw) in {
        "AA": (-0.085, 0.010, 0.10),
        "18650": (-0.005, 0.012, 0.05),
        "9V": (0.082, 0.012, -0.05),
        "CR2032": (0.150, 0.0, 0.30),
    }.items():
        add_ref(st, f"holder_{n}", assets / f"Holder_{n}.usda", (hx, hy, 0), quat_axis_angle((0, 0, 1), yaw))
        place_seated(st, f"holder_{n}", f"seated_{n}", assets / f"Cell_{n}.usda", n, (hx, hy, 0), yaw)
    return save(st)


def showcase_scene(assets, path):
    """One of everything, in a wide row for the social preview: screws with washers and nuts, loose
    nuts and washers, standing cells, cells seated in their holders, coin cells."""
    st = new_scene(path)
    for i, (s, fin) in enumerate(
        (("M6", "stainless_a2"), ("M8", "brass"), ("M10", "black_oxide"), ("M12", "zinc_clear"))
    ):
        t = METRIC[s]
        x = -0.152 + 0.027 * i
        k, P, h = t["k"] * MM, t["P"] * MM, t["washer"][2] * MM
        screw = next(p for p in os.listdir(assets) if p.startswith(f"ISO4017_{s}x"))
        add_ref(st, f"screw_{s}", assets / screw, (x, 0.02, k), quat_axis_angle((0, 0, 1), 0.4 * i), fin)
        add_ref(st, f"washer_{s}", assets / f"ISO7089_{s}.usda", (x, 0.02, k), (1, 0, 0, 0), fin)
        phi = 0.6 + 0.5 * i
        n = int(np.ceil(h / P)) + 2 + i % 2
        z = k + n * P + P * phi / (2 * np.pi)
        add_ref(st, f"nut_{s}", assets / f"ISO4032_{s}.usdc", (x, 0.02, z), quat_axis_angle((0, 0, 1), phi), fin)
        lfin = FINISHES[(i + 3) % len(FINISHES)]
        add_ref(
            st,
            f"lnut_{s}",
            assets / f"ISO4032_{s}.usdc",
            (x + 0.006, -0.022, 0),
            quat_axis_angle((0, 0, 1), 0.3 + i),
            lfin,
        )
        add_ref(
            st,
            f"lwasher_{s}",
            assets / f"ISO7089_{s}.usda",
            (x - 0.004, -0.048, 0),
            (1, 0, 0, 0),
            FINISHES[(i + 1) % 6],
        )
    up = quat_axis_angle((0, 1, 0), -np.pi / 2)  # cell axis x -> z: standing on its - end
    for i, (n, x) in enumerate((("AA", -0.035), ("18650", -0.011), ("21700", 0.015), ("C", 0.047), ("D", 0.084))):
        c = CELLS[n]
        q = qmul(quat_axis_angle((0, 0, 1), -1.45 + 0.12 * i), up)
        add_ref(st, f"cell_{n}", assets / f"Cell_{n}.usda", (x, 0.012 - 0.006 * (i % 2), c["L"] / 2 * MM), q)
    add_ref(st, "cell_AAA", assets / "Cell_AAA.usda", (-0.012, -0.045, 0.00525), quat_axis_angle((0, 0, 1), 0.25))
    holders = {"AA": (0.135, 0.035, 0.2), "CR2032": (0.066, -0.052, -0.2), "9V": (0.128, -0.045, 0.2)}
    for n, (hx, hy, yaw) in holders.items():
        add_ref(st, f"holder_{n}", assets / f"Holder_{n}.usda", (hx, hy, 0), quat_axis_angle((0, 0, 1), yaw))
        place_seated(st, f"holder_{n}", f"seated_{n}", assets / f"Cell_{n}.usda", n, (hx, hy, 0), yaw)
    add_ref(st, "coin_LR44", assets / "Cell_LR44.usda", (0.022, -0.062, 0.0027), quat_axis_angle((0, 0, 1), 0.4))
    flip = qmul(quat_axis_angle((0, 0, 1), 1.1), quat_axis_angle((1, 0, 0), np.pi))
    add_ref(st, "coin_CR2032", assets / "Cell_CR2032.usda", (0.036, -0.082, 0.0016), flip)
    return save(st)


def blender(scene, out, size, cam, lens, fstop, samples):
    subprocess.run(
        [sys.executable, str(HERE / "render_blender.py"), str(scene), str(out), *map(str, size), str(samples)]
        + [str(v) for v in cam]
        + [str(lens), str(fstop)],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def social(hero_png: Path, logo_png: Path, out: Path):
    from PIL import Image, ImageDraw, ImageFont

    W, H, band_h = 1280, 640, 190
    img = Image.open(hero_png).convert("RGB")
    top_h = H - band_h  # the render fills the top, the band holds logo and tagline below it
    s = max(W / img.width, top_h / img.height)
    img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    left, top = (img.width - W) // 2, (img.height - top_h) // 2
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    canvas.paste(img.crop((left, top, left + W, top + top_h)), (0, 0))
    logo = Image.open(logo_png).convert("RGBA")
    k = 92 / logo.height
    logo = logo.resize((int(logo.width * k), 92), Image.LANCZOS)
    canvas.paste(logo, (56, H - 172), logo)
    d = ImageDraw.Draw(canvas)
    try:
        import matplotlib

        font = ImageFont.truetype(os.path.join(matplotlib.get_data_path(), "fonts", "ttf", "DejaVuSans.ttf"), 30)
    except (ImportError, OSError):
        font = ImageFont.load_default()
    tagline = "Standard hardware assets generator for Physical AI · OpenUSD · MuJoCo"
    d.text((62, H - 66), tagline, fill=(22, 25, 29), font=font)
    canvas.save(out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--out", default="docs/images")
    ap.add_argument("--only", default="logo,fasteners,cells,social")
    args = ap.parse_args(argv)
    out = Path(args.out)
    only = args.only.split(",")
    if "logo" in only:
        subprocess.run([sys.executable, str(HERE / "make_logo.py"), str(out)], check=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        generate(catalog_parts(), str(tmp), "catalog", scene=False)
        assets = tmp / "catalog" / "assets"
        if "fasteners" in only:
            sc = fasteners_scene(assets, tmp / "catalog" / "fasteners.usda")
            blender(
                sc,
                out / "fasteners.jpg.png",
                (1600, 900),
                (0.0, -0.30, 0.16, 0.0, -0.012, 0.008),
                52,
                5.6,
                args.samples,
            )
        if "cells" in only:
            sc = cells_scene(assets, tmp / "catalog" / "cells.usda")
            blender(
                sc, out / "cells.jpg.png", (1600, 900), (0.02, -0.36, 0.24, 0.015, -0.025, 0.012), 45, 0, args.samples
            )
        if "social" in only:
            sc = showcase_scene(assets, tmp / "catalog" / "showcase.usda")
            blender(
                sc, out / "showcase.png", (2560, 900), (0.012, -0.40, 0.17, 0.012, -0.008, 0.016), 38, 8, args.samples
            )
            social(out / "showcase.png", out / "logo.png", out / "social_preview.png")
            (out / "showcase.png").unlink()
        from PIL import Image

        for name in ("fasteners", "cells"):
            png = out / f"{name}.jpg.png"
            if png.exists():
                Image.open(png).convert("RGB").save(out / f"{name}.jpg", quality=90)
                png.unlink()


if __name__ == "__main__":
    main()
