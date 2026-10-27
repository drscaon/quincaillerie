"""Animated GIFs of the physics for the README.

* drop.gif: assemblies and loose parts dropped on the floor, simulated by Blender's rigid bodies
  (Bullet) right after File > Import > USD with the add-on: a nut stays on its screw, a washer
  between them, a cell stays in its holder, nothing comes apart;
* screwing.gif: a nut driven onto a screw by a torque, simulated in MuJoCo from the USD files: it
  advances one pitch per turn on the modelled thread;
* insertion.gif: cells pushed into their holders and released, simulated in MuJoCo from the USD
  files: the spring plate and the clip move, the coil compresses;
* jam.gif: the same nut driven with the same light torque on a sound screw and on one with crushed
  threads (a drawn defect): it runs down the first and stops at the damage on the second.

All are rendered in Blender (Cycles) from the same OpenUSD assets. Development tool: needs MuJoCo,
Pillow and Blender as a Python module (`pip install bpy`, Python 3.13):

    python scripts/physics_gifs.py [--out docs/images] [--only drop,screwing,insertion] [--samples 24]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

from quincaillerie import catalog_parts, generate
from quincaillerie.batteries import holder_design, insertion_keys, key_pose
from quincaillerie.catalog import METRIC
from quincaillerie.scenes import add_ref, new_scene, save, seated_overrides
from quincaillerie.usd import place, q2m, qmul, quat_axis_angle

HERE = Path(__file__).resolve().parent
MM = 1e-3
FPS = 24


def mat2quat(R):
    from quincaillerie.usd import mat2quat as m2q

    return m2q(R)


def compose(A, local):
    """Pose A (pos, quat) applied to a local pose (pos, quat)."""
    (pa, qa), (pl, ql) = A, local
    return tuple(np.asarray(pa) + q2m(qa) @ np.asarray(pl)), qmul(qa, ql)


def drop_scene(assets: Path, path: Path):
    st = new_scene(path)
    tilt = lambda a, b: qmul(quat_axis_angle((1, 0, 0), a), quat_axis_angle((0, 1, 0), b))  # noqa: E731
    # screw + washer + nut, standing on the head, tilted 25 degrees, 3 cm up
    for name, size, pos, q in (
        ("a", "M12", (-0.055, 0.0, 0.035), tilt(0.45, 0.2)),
        ("b", "M8", (-0.02, 0.03, 0.03), tilt(-0.3, 0.5)),
    ):
        t = METRIC[size]
        k, P, h = t["k"] * MM, t["P"] * MM, t["washer"][2] * MM
        A = (pos, q)
        screw = next(p for p in os.listdir(assets) if p.startswith(f"ISO4017_{size}x"))
        n = int(np.ceil(h / P)) + 3
        for part, f, local, fin in (
            ("screw", screw, ((0, 0, k), (1, 0, 0, 0)), "zinc_clear"),
            ("washer", f"ISO7089_{size}.usda", ((0, 0, k), (1, 0, 0, 0)), "zinc_yellow"),
            ("nut", f"ISO4032_{size}.usdc", ((0, 0, k + n * P), (1, 0, 0, 0)), "zinc_clear"),
        ):
            p, qq = compose(A, local)
            add_ref(st, f"{name}_{part}", assets / f, p, qq, fin)
    # loose parts
    rng = np.random.default_rng(3)
    loose = [
        ("ISO4032_M8.usdc", (0.02, -0.03, 0.02), "brass"),
        ("ISO4032_M10.usdc", (0.045, -0.035, 0.03), "black_oxide"),
        ("ISO7089_M10.usda", (0.0, -0.045, 0.025), "stainless_a2"),
        ("ISO7089_M6.usda", (0.03, -0.055, 0.035), "zinc_clear"),
        ("Cell_CR2032.usda", (-0.04, -0.05, 0.03), None),
        ("Cell_AAA.usda", (0.07, 0.02, 0.04), None),
    ]
    for i, (f, pos, fin) in enumerate(loose):
        add_ref(st, f"loose_{i}", assets / f, pos, tilt(rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8)), fin)
    # an AA cell seated in its holder, the holder dropped 2 cm with a small tilt
    H = ((0.04, 0.045, 0.02), qmul(quat_axis_angle((0, 0, 1), 0.3), tilt(0.12, -0.1)))
    add_ref(st, "holder", assets / "Holder_AA.usda", *H)
    cpos, cq, movers = seated_overrides("AA")
    add_ref(st, "holder_cell", assets / "Cell_AA.usda", *compose(H, (cpos, cq)))
    for name, (p, q) in movers.items():
        place(st.OverridePrim(f"/World/holder/{name}"), p, q)  # in the holder's frame
    return save(st)


# ------------------------------------------------------------------ MuJoCo animations
def _frames_from_mujoco(m, d, step, seconds, prims, record_every, control=None):
    import mujoco

    frames = []
    n = int(seconds / m.opt.timestep)
    for i in range(n):
        if control:
            control(m, d, i * m.opt.timestep)
        mujoco.mj_step(m, d)
        if i % record_every == 0:
            frames.append({p: (d.xpos[b].tolist(), d.xquat[b].tolist()) for p, b in prims.items()})
    return frames


def screwing_animation(assets: Path, path: Path, out_json: Path, size="M10", turns=3.0, seconds=3.0):
    """A nut on the first threads of a fixed screw, driven down by a torque (MuJoCo)."""
    import mujoco
    from pxr import Usd

    from quincaillerie.sim.mujoco_model import convert

    t = METRIC[size]
    P, k = t["P"] * MM, t["k"] * MM
    screw = next(p for p in os.listdir(assets) if p.startswith(f"ISO4017_{size}x"))
    L = float(screw.split("x")[1].split(".")[0]) * MM
    st = new_scene(path)
    add_ref(st, "screw", assets / screw, (0, 0, k))
    n0 = int(round((L - 3 * P) / P))
    add_ref(st, "washer", assets / f"ISO7089_{size}.usda", (0, 0, k), (1, 0, 0, 0), "zinc_yellow")
    add_ref(st, "nut", assets / f"ISO4032_{size}.usdc", (0, 0, k + n0 * P))
    save(st)
    sim = Usd.Stage.Open(str(path))
    from pxr import UsdPhysics

    UsdPhysics.RigidBodyAPI(sim.GetPrimAtPath("/World/screw")).CreateKinematicEnabledAttr(True)
    dt = 1e-4
    xml = convert(
        sim,
        options=f'<option timestep="{dt}" integrator="implicitfast" cone="elliptic"/>',
        default='<default><geom solref="0.0005 1" solimp="0.95 0.99 0.0001" margin="0" condim="4"/></default>',
    )
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    nut = m.body("nut").id
    va = m.jnt_dofadr[m.body_jntadr[nut]]
    omega = -2 * np.pi * turns / seconds  # clockwise seen from above: tightening

    def control(m, d, t):
        kd = m.body_inertia[nut][2] / (dt * 5)
        d.xfrc_applied[nut] = [0, 0, 0, 0, 0, -kd * (d.qvel[va + 5] - omega)]

    prims = {"/World/nut": nut, "/World/washer": m.body("washer").id}
    frames = _frames_from_mujoco(m, d, dt, seconds + 0.5, prims, int(1 / (FPS * dt)), control)
    out_json.write_text(json.dumps(frames))
    return path


def insertion_animation(assets: Path, path: Path, out_json: Path, formats=(("AA", -0.035), ("CR2032", 0.045))):
    """Cells carried into their holders by a hand and released (MuJoCo), two holders side by side."""
    import mujoco

    from quincaillerie.sim.checks import GRIP, HAND, OPTIONS
    from quincaillerie.sim.mujoco_model import convert, scene

    st = new_scene(path)
    all_frames = None
    for fmt, x in formats:
        add_ref(st, f"holder_{fmt}", assets / f"Holder_{fmt}.usda", (x, 0, 0))
        K = insertion_keys(fmt)
        keys = K["keys"]
        c0, q0 = key_pose(fmt, keys[0][1], keys[0][2])
        add_ref(st, f"cell_{fmt}", assets / f"Cell_{fmt}.usda", tuple(np.asarray(c0) + (x, 0, 0)), q0)
        sim = scene(
            None,
            [
                ("holder", str(assets / f"Holder_{fmt}.usda"), (0, 0, 0), (1, 0, 0, 0), {"kinematic": True}),
                ("cell", str(assets / f"Cell_{fmt}.usda"), tuple(c0), tuple(q0), {}),
            ],
        )
        xml = convert(
            sim,
            options=OPTIONS.format(dt=0.0005),
            default='<default><geom solref="0.002 1" solimp="0.95 0.99 0.0002" condim="4"/></default>',
            extra_world=HAND.format(pos=" ".join(map(str, c0)), quat=" ".join(map(str, q0))),
            extra_xml=GRIP,
        )
        m = mujoco.MjModel.from_xml_string(xml)
        d = mujoco.MjData(m)
        hand = m.body_mocapid[m.body("hand").id]
        eq = m.equality("grip").id
        mujoco.mj_forward(m, d)

        def control(m, d, t, keys=keys, K=K, fmt=fmt, hand=hand, eq=eq):
            if t < K["t_release"]:
                i = max(j for j in range(len(keys)) if keys[j][0] <= t)
                a, b = keys[i], keys[min(i + 1, len(keys) - 1)]
                u = 0 if b[0] == a[0] else np.clip((t - a[0]) / (b[0] - a[0]), 0, 1)
                u = 0.5 - 0.5 * np.cos(np.pi * u)
                cc, qq = key_pose(fmt, np.array(a[1]) + (np.array(b[1]) - np.array(a[1])) * u, a[2] + (b[2] - a[2]) * u)
                d.mocap_pos[hand], d.mocap_quat[hand] = cc, qq
            else:
                d.eq_active[eq] = 0

        mover = "spring_plate" if holder_design(fmt)["axis"] == "x" else "clip"
        prims = {f"/World/cell_{fmt}": m.body("cell").id, f"/World/holder_{fmt}/{mover}": m.body(mover).id}
        fr = _frames_from_mujoco(m, d, 0.0005, 3.0, prims, int(1 / (FPS * 0.0005)), control)
        for f in fr:  # the holder is at x in the scene
            for p in f:
                f[p] = ((np.asarray(f[p][0]) + (x, 0, 0)).tolist(), f[p][1])
        if all_frames is None:
            all_frames = fr
        else:
            for a, b in zip(all_frames, fr, strict=False):
                a.update(b)
    save(st)
    out_json.write_text(json.dumps(all_frames))
    return path


def jam_animation(work: Path, path: Path, out_json: Path, size="M12", length=40, turns=4.0, rate=1.6):
    """Two M12 screws, one sound, one with crushed threads; the same nut driven on each with the same
    light torque (MuJoCo). It runs down the sound one and stops at the damage."""
    import mujoco

    from quincaillerie.fasteners import _zone, write_nut, write_screw
    from quincaillerie.materials import write_materials
    from quincaillerie.sim.checks import OPTIONS, TAU
    from quincaillerie.sim.mujoco_model import convert, scene
    from quincaillerie.variation import FastenerVariation

    d = work / "jam"
    write_materials(str(d / "materials"))
    sound = FastenerVariation()
    crushed = FastenerVariation(defect="crushed_thread", defect_size=0.5, defect_z=0.45, defect_angle_deg=150)
    files = {}
    for name, v in (("sound", sound), ("crushed", crushed)):
        files[name] = d / "assets" / f"screw_{name}.usdc"
        write_screw(str(files[name]), size, length, "zinc_clear", v, f"screw_{name}")
    nut = d / "assets" / "nut.usdc"
    write_nut(str(nut), size, "zinc_clear")
    t = METRIC[size]
    P, k, L = t["P"] * MM, t["k"] * MM, length * MM
    z0, z1, t0, t1 = _zone(crushed, L, P)
    zn = int(np.ceil((z1 + 1.0 * P) / P)) * P
    xs = {"sound": -0.018, "crushed": 0.018}
    st = new_scene(path)
    for name, x in xs.items():
        add_ref(st, f"screw_{name}", files[name], (x, 0, k), quat_axis_angle((0, 0, 1), -(t0 + t1) / 2 - np.pi / 2))
        add_ref(st, f"nut_{name}", nut, (x, 0, k + zn))
    save(st)
    frames = None
    dt = 1e-4
    for name, x in xs.items():
        yaw = -(t0 + t1) / 2 - np.pi / 2  # the damage faces the camera
        qs = quat_axis_angle((0, 0, 1), yaw)
        sim = scene(
            None,
            [
                ("bolt", str(files[name]), (0, 0, 0), qs, {"kinematic": True}),
                ("nut", str(nut), (0, 0, zn), (1, 0, 0, 0), {}),
            ],
        )
        xml = convert(
            sim,
            options=OPTIONS.format(dt=dt).replace('"/>', '" gravity="0 0 0"/>'),
            default='<default><geom solref="0.0005 1" solimp="0.95 0.99 0.0001" margin="0" condim="4"/></default>',
        )
        m = mujoco.MjModel.from_xml_string(xml)
        dd = mujoco.MjData(m)
        bid = m.body("nut").id
        va = m.jnt_dofadr[m.body_jntadr[bid]]
        tau_max = TAU * (t["d"] / 8.0) ** 3
        kd = m.body_inertia[bid][2] / (dt * 5)

        def control(m, d, tt, bid=bid, va=va, tau_max=tau_max, kd=kd):
            tau = float(np.clip(-kd * (d.qvel[va + 5] + 2 * np.pi * rate), -tau_max, tau_max))
            d.xfrc_applied[bid] = [0, 0, 0, 0, 0, tau]

        fr = _frames_from_mujoco(m, dd, dt, turns / rate, {f"/World/nut_{name}": bid}, int(1 / (FPS * dt)), control)
        for f in fr:
            for p in f:
                pos, q = f[p]
                f[p] = ((np.asarray(pos) + (x, 0, k)).tolist(), q)
        if frames is None:
            frames = fr
        else:
            for a, b in zip(frames, fr, strict=False):
                a.update(b)
    out_json.write_text(json.dumps(frames))
    return path


# ------------------------------------------------------------------ Blender + GIF
def blender(mode, scene, frames_dir, frames, size, cam, lens, samples, poses=None):
    args = [
        sys.executable,
        str(HERE / "gif_blender.py"),
        mode,
        str(scene),
        str(frames_dir),
        str(frames),
        *map(str, size),
    ]
    args += [str(samples), *map(str, cam), str(lens), str(poses or "")]
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def make_gif(frames_dir: Path, out: Path, hold=24, width=None):
    from PIL import Image

    files = sorted(frames_dir.glob("f_*.png"))
    imgs = [Image.open(f).convert("RGB") for f in files]
    if width:
        imgs = [im.resize((width, int(im.height * width / im.width)), Image.LANCZOS) for im in imgs]
    pal = imgs[len(imgs) // 2].quantize(colors=200, method=Image.Quantize.MEDIANCUT)
    frames = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]
    durations = [int(1000 / FPS)] * len(frames)
    durations[-1] = int(1000 / FPS) * hold  # pause on the last frame
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/images")
    ap.add_argument("--only", default="drop,screwing,insertion,jam")
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--size", default="720,405")
    ap.add_argument("--keep", help="keep the work folder here")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    size = tuple(int(v) for v in args.size.split(","))
    only = args.only.split(",")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(args.keep) if args.keep else Path(tmp)
        tmp.mkdir(parents=True, exist_ok=True)
        generate(catalog_parts(), str(tmp), "catalog", scene=False, vary=())
        assets = tmp / "catalog" / "assets"
        work = tmp / "catalog"
        if "drop" in only:
            sc = drop_scene(assets, work / "drop.usda")
            fd = tmp / "frames_drop"
            blender("drop", sc, fd, int(1.6 * FPS), size, (0.02, -0.23, 0.15, -0.008, 0.0, 0.008), 42, args.samples)
            make_gif(fd, out / "drop.gif")
        if "screwing" in only:
            sc = screwing_animation(assets, work / "screwing.usda", work / "screwing.json")
            fd = tmp / "frames_screwing"
            blender(
                "poses", sc, fd, 0, size, (0.06, -0.15, 0.10, 0.0, 0.0, 0.021), 55, args.samples, work / "screwing.json"
            )
            make_gif(fd, out / "screwing.gif")
        if "insertion" in only:
            sc = insertion_animation(assets, work / "insertion.usda", work / "insertion.json")
            fd = tmp / "frames_insertion"
            blender(
                "poses",
                sc,
                fd,
                0,
                size,
                (0.0, -0.20, 0.15, 0.005, 0.0, 0.016),
                40,
                args.samples,
                work / "insertion.json",
            )
            make_gif(fd, out / "insertion.gif")
        if "jam" in only:
            sc = jam_animation(work, work / "jam.usda", work / "jam.json")
            fd = tmp / "frames_jam"
            blender("poses", sc, fd, 0, size, (0.0, -0.13, 0.075, 0.0, 0.0, 0.026), 55, args.samples, work / "jam.json")
            make_gif(fd, out / "jam.gif")


if __name__ == "__main__":
    main()
