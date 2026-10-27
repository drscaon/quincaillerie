"""The gravity checks in Blender: the same scenes and thresholds as the MuJoCo checks.

Each scene is simulated in its own Blender process (``run.py``), either through the bpy module of
this Python (``pip install bpy``) or through a Blender executable (``--blender /path/to/blender``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np

from ..sim.checks import build_test_scenes

MM = 1e-3
RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run.py")
SECONDS = {"drop": 3.0, "nut_on_screw": 1.0, "holder": 1.0, "seated": 1.0}


def blender_command(blender=None):
    """How to run run.py: [python, run.py] when bpy is importable here, else [blender, -b, -P, run.py, --]."""
    if blender:
        return [blender, "-b", "--factory-startup", "-P", RUN, "--"]
    try:
        import importlib.util

        if importlib.util.find_spec("bpy") is not None:
            return [sys.executable, RUN]
    except (ImportError, ValueError):
        pass
    exe = shutil.which("blender")
    if exe:
        return [exe, "-b", "--factory-startup", "-P", RUN, "--"]
    raise RuntimeError("Blender not found: pip install bpy (Python 3.13), or pass --blender /path/to/blender")


def _find(bodies, mode, prim, sub=None):
    """The Blender body standing for /World/prim[/sub]."""
    path = f"/World/{prim}" + (f"/{sub}" if sub else "")
    for name, b in bodies.items():
        if mode == "setup" and b.get("usd") == path:
            return name, b
    for name, b in bodies.items():  # naive: by the USD hierarchy the importer kept
        ch = b["chain"]
        if prim in ch and (sub is None or sub in ch) and "spring_coil" not in name:
            if sub is None and any(s in ch for s in ("spring_plate", "clip")):
                continue
            if sub is None and prim == "holder" and not name.startswith("Holder_"):
                continue
            return name, b
    return None, None


def _speed(b, fps, vertical=False):
    t = b["traj"]
    if len(t) < 2:
        return 0.0
    dv = np.array(t[-1]) - np.array(t[-2])
    return float(abs(dv[2]) if vertical else np.linalg.norm(dv)) / (12 / fps)


def evaluate(kind, info, D):
    bodies, mode, fps = D["bodies"], D["mode"], D["fps"]
    M = lambda b, k: np.array(b[k])  # noqa: E731
    if kind == "drop":
        name, b = _find(bodies, mode, "part")
        parts = [x for x in bodies.values() if "part" in x["chain"] or x.get("usd") == "/World/part"]
        sep = 0.0  # naive: meshes of one part must keep their relative pose
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                r0 = np.linalg.inv(M(parts[i], "first")) @ M(parts[j], "first")
                r1 = np.linalg.inv(M(parts[i], "last")) @ M(parts[j], "last")
                sep = max(sep, float(np.linalg.norm(r1[:3, 3] - r0[:3, 3])))
        low = min(x["lowest"] for x in parts) / MM
        vz = max(_speed(x, fps, True) for x in parts) / MM
        v = max(_speed(x, fps) for x in parts) / MM
        ok = abs(low) < 0.35 and vz < 1.0 and sep < 1e-4
        msg = f"lowest point {low:+.3f} mm, vertical speed {vz:.2f} mm/s" + (
            f", rolling at {v:.0f} mm/s" if v > 5 else ""
        )
        if len(parts) > 1:
            msg += f", parts separated {sep / MM:.2f} mm"
        return ok, msg
    if kind == "nut_on_screw":
        _, bs = _find(bodies, mode, "screw")
        _, bn = _find(bodies, mode, "nut")
        if bs is None or bn is None:
            return False, "screw or nut not found"
        r0 = np.linalg.inv(M(bs, "first")) @ M(bn, "first")
        r1 = np.linalg.inv(M(bs, "last")) @ M(bn, "last")
        dz = (r1[2, 3] - r0[2, 3]) / MM
        off = float(np.hypot(*(r1[:2, 3] - r0[:2, 3]))) / MM
        low = bs["lowest"] / MM
        ok = abs(dz) < 0.5 * info["pitch"] / MM and off < 0.3 and abs(low) < 0.35  # no thread skipped
        return ok, f"nut moved {dz:+.3f} mm along the screw, off-axis {off:.3f} mm; screw lowest point {low:+.2f} mm"
    if kind == "holder":
        for sub in ("spring_plate", "clip"):
            name, b = _find(bodies, mode, "holder", sub)
            if b is not None:
                break
        _, base = _find(bodies, mode, "holder", "base") if mode == "setup" else _find(bodies, mode, "holder")
        if b is None:
            return False, "moving contact not found"
        if base is None:
            return False, "base not found"
        mb = M(base, "last")[:3, 3] - M(base, "first")[:3, 3]
        r0 = np.linalg.inv(M(base, "first")) @ M(b, "first")  # the contact in the base's frame
        r1 = np.linalg.inv(M(base, "last")) @ M(b, "last")
        dp = float(np.linalg.norm(r1[:3, 3] - r0[:3, 3])) / MM
        db = float(np.linalg.norm(mb)) / MM
        return dp < 0.05 and db < 0.3, f"{sub} drift {dp:.4f} mm, base settled {db:.3f} mm"
    mover = info["mover"]
    _, bc = _find(bodies, mode, "cell")
    _, bm = _find(bodies, mode, "holder", mover)
    _, bb = _find(bodies, mode, "holder", "base") if mode == "setup" else _find(bodies, mode, "holder")
    if bc is None or bm is None or bb is None:
        return False, "cell, base or contact not found"

    def moved(b):  # displacement relative to the holder's base
        r0 = np.linalg.inv(M(bb, "first")) @ M(b, "first")
        r1 = np.linalg.inv(M(bb, "last")) @ M(b, "last")
        return float(np.linalg.norm(r1[:3, 3] - r0[:3, 3])) / MM

    dc, dm = moved(bc), moved(bm)
    lim = info.get("side_play", 0.0) + 0.6
    return dc < lim and dm < 0.3, f"cell moved {dc:.3f} mm in its holder (play {lim:.1f}), {mover} moved {dm:.3f} mm"


def blender_test(set_dir, mode="setup", blender=None, verbose=True, only=None):
    cmd = blender_command(blender)
    work = os.path.join(set_dir, "sim_test", f"blender_{mode}")
    os.makedirs(work, exist_ok=True)
    rows = []
    for name, kind, path, info in build_test_scenes(set_dir):
        if only and only not in name:
            continue
        out = os.path.join(work, f"{name}.json")
        t0 = time.time()
        p = subprocess.run(cmd + [path, out, mode, str(SECONDS[kind])], capture_output=True, text=True, timeout=1800)
        wall = time.time() - t0
        if p.returncode != 0 or not os.path.exists(out):
            ok, msg = False, "Blender run failed: " + (p.stderr.strip().splitlines() or ["?"])[-1]
        else:
            with open(out, encoding="utf-8") as f:
                D = json.load(f)
            finite = all(np.isfinite(np.array(b["last"])).all() for b in D["bodies"].values())
            ok, msg = evaluate(kind, info, D) if finite else (False, "diverged")
        rows.append(dict(test=name, kind=kind, ok=bool(ok), info=msg, wall=round(wall, 1)))
        if verbose:
            print(f"{'PASS' if ok else 'FAIL'}  {name:28s} {msg}  ({wall:.1f}s)", flush=True)
    with open(os.path.join(set_dir, "sim_test", f"blender_{mode}.json"), "w", encoding="utf-8") as f:
        json.dump(
            dict(engine="blender", mode=mode, passed=sum(r["ok"] for r in rows), total=len(rows), tests=rows),
            f,
            indent=1,
        )
    if verbose:
        print(f"{sum(r['ok'] for r in rows)}/{len(rows)} passed (Blender, {mode})")
    return rows
