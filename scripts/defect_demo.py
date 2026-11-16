"""Visual check that Quincaillerie's defects are physical: MuJoCo, rendered on the CPU.

Three side-by-side comparisons, each a sound part on the left and a defective one on the right:

1. a nut driven with a light torque down an M8 x 30 screw: it runs to the head on the sound
   screw and stops at the crushed thread;
2. a 1 mm ball dropped on an AA cell lying on the floor: it rests on top of the sound can, and
   1 mm lower in the dent;
3. an AA cell stood on its minus terminal: the sound one stands, the corroded one falls over on
   its crust.

The parts are written by Quincaillerie itself and simulated from their OpenUSD files, as in the
tests (tests/test_jam_rate.py, tests/test_physical_defects.py). MuJoCo draws the colliders, so
the images show what the engine sees. Writes defects.mp4 and
defects.png into the folder given (default: the current folder). Needs mujoco, and EGL or OSMesa
for rendering without a display: MUJOCO_GL=egl python scripts/defect_demo.py out/
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "egl")

import mujoco  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from quincaillerie.batteries import write_cell  # noqa: E402
from quincaillerie.catalog import METRIC  # noqa: E402
from quincaillerie.fasteners import _zone, write_nut, write_screw  # noqa: E402
from quincaillerie.sim.checks import DEFAULT, OPTIONS, TAU  # noqa: E402
from quincaillerie.sim.mujoco_model import convert, scene  # noqa: E402
from quincaillerie.variation import CellVariation, FastenerVariation  # noqa: E402

FPS = 25
W, H = 480, 400
LIGHT = '<light pos="0.05 -0.08 0.12" dir="-0.4 0.6 -1" diffuse="0.9 0.9 0.9" castshadow="false"/>'
FLOOR = '<geom name="floor" type="plane" size="1 1 0.01" rgba="0.82 0.84 0.86 1"/>'
MM = 1e-3


def model(stage, dt, extra="", gravity=True, default=None):
    options = OPTIONS.format(dt=dt)
    if not gravity:
        options = options.replace('"/>', '" gravity="0 0 0"/>')
    xml = convert(stage, options=options, default=default or DEFAULT.format(tc=0.002), extra_world=LIGHT + extra)
    xml = xml.replace("<mujoco", '<mujoco><visual><global offwidth="960" offheight="800"/></visual></mujoco><mujoco', 1)
    xml = xml.replace("</mujoco><mujoco", "", 1)
    m = mujoco.MjModel.from_xml_string(xml)
    return m, mujoco.MjData(m)


def colour(m, body, rgba):
    for g in range(m.ngeom):
        if m.geom_bodyid[g] == m.body(body).id:
            m.geom_rgba[g] = rgba


def camera(lookat, distance, azimuth, elevation):
    cam = mujoco.MjvCamera()
    cam.lookat[:] = lookat
    cam.distance, cam.azimuth, cam.elevation = distance, azimuth, elevation
    return cam


def film(m, d, seconds, dt, cam, step=None):
    """Frames at FPS while the simulation runs; step(m, d) is called before each mj_step."""
    renderer = mujoco.Renderer(m, H, W)
    frames, every = [], max(1, round(1 / FPS / dt))
    for i in range(int(seconds / dt)):
        if step:
            step(m, d)
        mujoco.mj_step(m, d)
        if i % every == 0:
            renderer.update_scene(d, camera=cam)
            frames.append(renderer.render().copy())
    renderer.close()
    return frames


# ------------------------------------------------------------------ 1. nut on a screw
def nut_run(folder, defect):
    size, length = "M8", 30
    P = METRIC[size]["P"] * MM
    v = FastenerVariation(defect=defect, defect_z=0.5, defect_angle_deg=120.0, defect_size=0.6)
    screw, nut = folder / f"screw_{defect}.usda", folder / "nut.usda"
    write_screw(str(screw), size, length, v=v, detail="low")
    if not nut.exists():
        write_nut(str(nut), size, detail="low")
    z0, z1, _, _ = _zone(FastenerVariation(defect_z=0.5, defect_angle_deg=120.0), length * MM, P)
    zn = int(np.ceil((z1 + 0.6 * P) / P)) * P  # above the crushed zone, then tightened towards the head
    stage = scene(
        None,
        [
            ("bolt", str(screw), (0, 0, 0), (1, 0, 0, 0), {"kinematic": True}),
            ("nut", str(nut), (0, 0, zn), (1, 0, 0, 0), {}),
        ],
    )
    dt = 1e-4
    contact = '<default><geom solref="0.0005 1" solimp="0.95 0.99 0.0001" margin="0" condim="4"/></default>'
    m, d = model(stage, dt, gravity=False, default=contact)
    colour(m, "bolt", (0.62, 0.66, 0.70, 1))
    colour(m, "nut", (0.85, 0.65, 0.20, 1))
    bid = m.body("nut").id
    va = m.jnt_dofadr[m.body_jntadr[bid]]
    omega, tau_max = -2 * np.pi * 2.0, TAU  # 2 turns/s towards the head, a light hand (M8)
    kd = m.body_inertia[bid][2] / (dt * 5)

    def drive(m, d):
        d.xfrc_applied[bid] = [0, 0, 0, 0, 0, float(np.clip(-kd * (d.qvel[va + 5] - omega), -tau_max, tau_max))]

    frames = film(m, d, 3.0, dt, camera((0, 0, length * MM / 2), 0.075, 90, -12), drive)
    return frames, (zn - d.qpos[m.jnt_qposadr[m.body_jntadr[bid]] + 2]) / MM


# ------------------------------------------------------------------ 2. ball on a can
def ball_run(folder, defect):
    cv = CellVariation(defect=defect, defect_z=0.5, defect_angle_deg=90.0, defect_size=1.0, seed=3)
    cell = folder / f"cell_dent_{defect}.usda"
    write_cell(str(cell), "AA", cv)
    r = 0.00725
    stage = scene(None, [("cell", str(cell), (0, 0, r + 0.0002), (1, 0, 0, 0), None)])
    ball = (
        '<body name="ball" pos="0.0004 0 {z}"><freejoint/>'
        '<geom type="sphere" size="0.001" mass="0.0002" rgba="0.85 0.15 0.15 1"/></body>'
    )
    m, d = model(stage, 5e-4, FLOOR + ball.format(z=2 * r + 0.004))
    colour(m, "cell", (0.55, 0.60, 0.68, 1))
    frames = film(m, d, 1.2, 5e-4, camera((0, 0, r), 0.06, 60, -25))
    return frames, (d.xpos[m.body("ball").id][2] - d.xpos[m.body("cell").id][2]) / MM


# ------------------------------------------------------------------ 3. cell on its terminal
def stand_run(folder, defect):
    cv = CellVariation(defect=defect, defect_angle_deg=0.0, defect_size=1.0, seed=3)
    cell = folder / f"cell_crust_{defect}.usda"
    write_cell(str(cell), "AA", cv)
    q = (np.cos(-np.pi / 4), 0, np.sin(-np.pi / 4), 0)
    stage = scene(None, [("cell", str(cell), (0, 0, 0.0505 / 2 + 0.002), q, None)])
    m, d = model(stage, 5e-4, FLOOR)
    colour(m, "cell", (0.55, 0.60, 0.68, 1))
    frames = film(m, d, 1.5, 5e-4, camera((0, 0, 0.02), 0.16, 120, -15))
    return frames, d.xpos[m.body("cell").id][2] / MM


# ------------------------------------------------------------------ assembly
def font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def panel(frame, title, note):
    img = Image.fromarray(frame)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 54), fill=(255, 255, 255))
    draw.text((12, 6), title, fill=(20, 20, 20), font=font(20))
    draw.text((12, 31), note, fill=(70, 70, 70), font=font(15))
    return img


def pair(left, right, titles, notes):
    n = max(len(left), len(right))
    out = []
    for i in range(n):
        a = panel(left[min(i, len(left) - 1)], titles[0], notes[0])
        b = panel(right[min(i, len(right) - 1)], titles[1], notes[1])
        img = Image.new("RGB", (2 * W + 8, H), (255, 255, 255))
        img.paste(a, (0, 0))
        img.paste(b, (W + 8, 0))
        out.append(img)
    return out


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp())
    (sa, ta), (sb, tb) = nut_run(folder, "none"), nut_run(folder, "crushed_thread")
    (ba, ha), (bb, hb) = ball_run(folder, "none"), ball_run(folder, "dent")
    (ca, za), (cb, zb) = stand_run(folder, "none"), stand_run(folder, "corroded_terminal")
    titles = [
        (
            ("Sound M8 screw", "Crushed thread (120°, 0.6 pitch)"),
            (f"nut travels {ta:.1f} mm", f"nut travels {tb:.1f} mm, then jams"),
        ),
        (
            ("Sound AA can", "AA can with a 1 mm dent"),
            (f"ball ends {ha:.2f} mm above the axis", f"ball ends {hb:.2f} mm above the axis"),
        ),
        (
            ("Sound AA on its minus face", "AA with a corrosion crust"),
            (f"centre at {za:.1f} mm: it stands", f"centre at {zb:.1f} mm: it falls over"),
        ),
    ]
    clips = [pair(a, b, *t) for (a, b), t in zip(((sa, sb), (ba, bb), (ca, cb)), titles, strict=True)]
    frames = [f for clip in clips for f in clip + [clip[-1]] * FPS]  # one second on each result
    video = out / "defects.mp4"
    with tempfile.TemporaryDirectory() as tmp:
        for i, f in enumerate(frames):
            f.save(f"{tmp}/{i:05d}.png")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-framerate",
                str(FPS),
                "-i",
                f"{tmp}/%05d.png",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "23",
                "-pix_fmt",
                "yuv420p",
                str(video),
            ],
            check=True,
        )
    sheet = Image.new("RGB", (2 * W + 8, 3 * H + 16), (255, 255, 255))
    for k, clip in enumerate(clips):
        sheet.paste(clip[-1], (0, k * (H + 8)))
    sheet.save(out / "defects.png")
    print(f"nut: {ta:.1f} mm sound, {tb:.1f} mm crushed; ball: {ha:.2f} / {hb:.2f} mm; cell: {za:.1f} / {zb:.1f} mm")
    print(f"wrote {video} and {out / 'defects.png'}")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
