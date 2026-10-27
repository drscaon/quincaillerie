"""Physics checks of generated assets in MuJoCo, read back from the OpenUSD files.

Every check builds a small OpenUSD scene (the assets referenced, a floor collider at z = 0, gravity),
saved under ``<set>/sim_test/scenes/`` so the same scenes can be opened in Blender or Isaac Sim, then
converts it to MuJoCo with ``mujoco_model.convert`` and simulates it on CPU.

* drop: each part dropped, tilted, from 4-5 cm. Passes when it rests on the floor: lowest point
  within 0.35 mm of it, vertical speed below 1 mm/s (round cells may keep rolling).
* nut_on_screw: a nut threaded on its screw, both dropped. The nut must stay on its thread: axial
  shift below half a pitch (no thread skipped), off-axis below 0.3 mm.
* holder: an empty holder placed on the floor settles (below 0.15 mm) and its spring plate or clip
  stays at rest relative to it (drift below 0.05 mm).
* seated: a cell seated in its holder, on the floor; relative to the holder, the cell stays in place
  (below 0.6 mm, the holder's side play) and so does the contact (0.3 mm).
* insertion: a cell carried into its holder and released: seated, spring compressed as designed,
  contact force within 10 % of the design; reversed: seated with the wrong polarity, or refused by
  the keying (9V).
* screwing (optional, slow): a nut turned on a fixed screw advances one pitch per turn within 5 %.
"""

from __future__ import annotations

import glob
import json
import os
import time

import numpy as np
from pxr import Usd, UsdGeom, UsdPhysics

from ..batteries import FLOOR_T, holder_design, insertion_keys, key_pose
from ..catalog import CELLS, METRIC
from ..scenes import add_ref, drop_pose, new_scene, save, seated_overrides
from ..usd import place, q2m, qmul
from .mujoco_model import convert, scene

MM = 1e-3
OPTIONS = '<option timestep="{dt}" integrator="implicitfast" cone="elliptic"/>'
DEFAULT = '<default><geom solref="{tc} 1" solimp="0.95 0.99 0.0002" condim="4"/></default>'


# ------------------------------------------------------------------ the assets of a generated set
def inventory(set_dir):
    """{name: dict(kind, key, file, ...)} for every asset under set_dir/assets."""
    out = {}
    for f in sorted(glob.glob(os.path.join(set_dir, "assets", "*.usd*"))):
        st = Usd.Stage.Open(f)
        root = st.GetDefaultPrim()

        def get(a, r=root):
            attr = r.GetAttribute(f"quincaillerie:{a}")
            return attr.Get() if attr else None

        kind = get("category")
        key = get("size") or get("format")
        out[root.GetName()] = dict(kind=kind, key=key, file=os.path.abspath(f), length=get("length"))
    return out


# ------------------------------------------------------------------ test scenes
def build_test_scenes(set_dir):
    """Write the gravity test scenes of a set; returns [(name, kind, path, info)]."""
    inv = inventory(set_dir)
    sdir = os.path.join(set_dir, "sim_test", "scenes")
    os.makedirs(sdir, exist_ok=True)
    out = []

    def new(name):
        return new_scene(os.path.join(sdir, f"{name}.usda"), floor_size=0.6, floor_visible=True)

    for name, a in inv.items():
        h = 0.05 if a["kind"] == "cell" else 0.04
        if a["kind"] == "holder":
            continue
        st = new(f"drop_{name}")
        pos, q = drop_pose(a["kind"], a["key"], h)
        add_ref(st, "part", a["file"], pos, q)
        out.append((f"drop_{name}", "drop", save(st), dict(part=name)))
    screws = {a["key"]: (n, a) for n, a in inv.items() if a["kind"] == "screw"}
    nuts = {a["key"]: (n, a) for n, a in inv.items() if a["kind"] == "nut"}
    for size in sorted(set(screws) & set(nuts), key=lambda s: METRIC[s]["d"]):
        (_, sa), (_, na) = screws[size], nuts[size]
        t = METRIC[size]
        P, k, L = t["P"] * MM, t["k"] * MM, sa["length"]
        turns = max(2, int(round(0.4 * L / P)))
        z = 0.02 + k
        st = new(f"nut_on_screw_{size}")
        add_ref(st, "screw", sa["file"], (0, 0, z))
        add_ref(st, "nut", na["file"], (0, 0, z + turns * P))
        out.append((f"nut_on_screw_{size}", "nut_on_screw", save(st), dict(size=size, z_nut=turns * P, pitch=P)))
    holders = {a["key"]: (n, a) for n, a in inv.items() if a["kind"] == "holder"}
    cells = {a["key"]: (n, a) for n, a in inv.items() if a["kind"] == "cell"}
    for fmt in [f for f in CELLS if f in holders]:
        st = new(f"holder_{fmt}")
        add_ref(st, "holder", holders[fmt][1]["file"], (0, 0, 0))
        out.append((f"holder_{fmt}", "holder", save(st), dict(format=fmt)))
    for fmt in [f for f in CELLS if f in holders and f in cells]:
        st = new(f"seated_{fmt}")
        add_ref(st, "holder", holders[fmt][1]["file"], (0, 0, 0))
        cpos, cq, movers = seated_overrides(fmt)
        add_ref(st, "cell", cells[fmt][1]["file"], cpos, cq)
        for mname, (p, q) in movers.items():
            place(st.OverridePrim(f"/World/holder/{mname}"), p, q)
        info = dict(format=fmt, cell=list(cpos), mover=mname, mover_pos=list(p))
        out.append((f"seated_{fmt}", "seated", save(st), info))
    return out


def body_points(stage):
    """Collision sample points of every rigid body, in the body frame: {body name: (N, 3)}."""
    cache = UsdGeom.XformCache()
    out = {}
    for b in [p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]:
        Mb_inv = cache.GetLocalToWorldTransform(b).GetInverse()
        pts = []
        for p in Usd.PrimRange(b):
            if p != b and p.HasAPI(UsdPhysics.RigidBodyAPI):
                continue
            if not p.HasAPI(UsdPhysics.CollisionAPI):
                continue
            M = np.array(cache.GetLocalToWorldTransform(p) * Mb_inv)
            if p.IsA(UsdGeom.Mesh):
                P = np.array(UsdGeom.Mesh(p).GetPointsAttr().Get(), float)
            elif p.IsA(UsdGeom.Cube):
                s = UsdGeom.Cube(p).GetSizeAttr().Get() / 2
                P = np.array([[x, y, z] for x in (-s, s) for y in (-s, s) for z in (-s, s)])
            elif p.IsA(UsdGeom.Cylinder):
                c = UsdGeom.Cylinder(p)
                r, h = c.GetRadiusAttr().Get(), c.GetHeightAttr().Get() / 2
                t = np.linspace(0, 2 * np.pi, 64, endpoint=False)
                ring = np.c_[r * np.cos(t), r * np.sin(t)]
                ax = c.GetAxisAttr().Get()
                P = np.array(
                    [{"Z": (a, b2, zz), "X": (zz, a, b2), "Y": (a, zz, b2)}[ax] for zz in (-h, h) for a, b2 in ring]
                )
            else:
                continue
            pts.append((np.c_[P, np.ones(len(P))] @ M)[:, :3])
        if pts:
            out[b.GetName()] = np.vstack(pts)
    return out


def initial_positions(stage):
    cache = UsdGeom.XformCache()
    return {
        p.GetName(): np.array(cache.GetLocalToWorldTransform(p).ExtractTranslation())
        for p in stage.Traverse()
        if p.HasAPI(UsdPhysics.RigidBodyAPI)
    }


# ------------------------------------------------------------------ MuJoCo runs
def run_mujoco(path, seconds, dt):
    """Simulate a scene; contacts a little stiffer (time constant 10 steps, at least 1 ms)."""
    import mujoco

    st = Usd.Stage.Open(path)
    xml = convert(
        st, options=OPTIONS.format(dt=dt), default=DEFAULT.format(tc=max(0.001, 10 * dt) if dt < 5e-4 else 0.002)
    )
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    names = [m.body(i).name for i in range(1, m.nbody)]
    t0 = time.time()
    for _ in range(int(seconds / dt)):
        mujoco.mj_step(m, d)
    final = {n: (d.xpos[m.body(n).id].copy(), d.xquat[m.body(n).id].copy()) for n in names}
    vel = {n: d.cvel[m.body(n).id][3:].copy() for n in names}
    return dict(final=final, vel=vel, wall=time.time() - t0, finite=bool(np.isfinite(d.qpos).all()))


def check_scene(name, kind, path, info):
    st = Usd.Stage.Open(path)
    pts = body_points(st)
    init = initial_positions(st)
    fast = kind == "nut_on_screw" or (kind == "drop" and info["part"].startswith("ISO"))
    dt = 1e-4 if fast else 5e-4
    T = {"drop": 1.5, "nut_on_screw": 1.0, "holder": 1.0, "seated": 1.0}[kind]
    if kind == "drop" and fast:
        T = 1.2
    r = run_mujoco(path, T, dt)
    if not r["finite"]:
        return False, "diverged", r["wall"]
    if kind == "drop":
        pos, quat = r["final"]["part"]
        low = ((pts["part"] @ q2m(quat).T) + pos)[:, 2].min() / MM
        vz = abs(r["vel"]["part"][2]) / MM
        v = np.linalg.norm(r["vel"]["part"]) / MM
        ok = abs(low) < 0.35 and vz < 1.0
        msg = f"lowest point {low:+.3f} mm, vertical speed {vz:.2f} mm/s" + (
            f", rolling at {v:.0f} mm/s" if v > 5 else ""
        )
        return ok, msg, r["wall"]
    if kind == "nut_on_screw":
        pb, qb = r["final"]["screw"]
        pn, _ = r["final"]["nut"]
        rel = q2m(qb).T @ (pn - pb)
        dz = rel[2] / MM - info["z_nut"] / MM
        off = np.hypot(*rel[:2]) / MM
        low = ((pts["screw"] @ q2m(qb).T) + pb)[:, 2].min() / MM
        ok = abs(dz) < 0.5 * info["pitch"] / MM and off < 0.3 and abs(low) < 0.35  # no thread skipped
        return (
            ok,
            f"nut moved {dz:+.3f} mm along the screw, off-axis {off:.3f} mm; screw lowest point {low:+.2f} mm",
            r["wall"],
        )
    if kind == "holder":
        mover = "spring_plate" if "spring_plate" in r["final"] else "clip"
        mb = r["final"]["base"][0] - init["base"]
        dp = np.linalg.norm(r["final"][mover][0] - init[mover] - mb) / MM
        db = np.linalg.norm(mb) / MM
        return dp < 0.05 and db < 0.15, f"{mover} drift {dp:.4f} mm, base settled {db:.3f} mm", r["wall"]
    mover = info["mover"]
    pb, qb = r["final"]["base"]

    def moved(name):  # displacement relative to the holder's base (which starts unrotated)
        return np.linalg.norm(q2m(qb).T @ (r["final"][name][0] - pb) - (init[name] - init["base"])) / MM

    dc, dm = moved("cell"), moved(mover)
    msg = f"cell moved {dc:.3f} mm in its holder, {mover} moved {dm:.3f} mm"
    return dc < 0.6 and dm < 0.3, msg, r["wall"]


# ------------------------------------------------------------------ insertion
HAND = '<body name="hand" mocap="true" pos="{pos}" quat="{quat}"/>'
GRIP = '<equality><weld name="grip" body1="hand" body2="cell" relpose="0 0 0 1 0 0 0" solref="0.004 1"/></equality>'
REV = {"cradle": (0, 0, 0, 1.0), "nine_volt": (0, 1.0, 0, 0), "coin": (0, 1.0, 0, 0)}  # 180 deg about z, x, x


def insertion(cell_file, holder_file, fmt, reverse=False, record=False):
    """A mocap 'hand' welded to the cell carries it along the scripted keys, then lets go."""
    import mujoco

    D = holder_design(fmt)
    K = insertion_keys(fmt)
    q_rev = np.array(REV[D["kind"]]) if reverse else np.array([1.0, 0, 0, 0])
    keys = K["keys"]
    c0, q0 = key_pose(fmt, keys[0][1], keys[0][2])
    q0 = np.array(qmul(q0, q_rev))
    holder = ("holder", holder_file, (0, 0, 0), (1, 0, 0, 0), {"kinematic": True})  # held in place
    st = scene(None, [holder, ("cell", cell_file, tuple(c0), tuple(q0), {})])
    xml = convert(
        st,
        options=OPTIONS.format(dt=0.0005),
        default=DEFAULT.format(tc=0.002),
        extra_world=HAND.format(pos=" ".join(map(str, c0)), quat=" ".join(map(str, q0))),
        extra_xml=GRIP,
    )
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    cell = m.body("cell").id
    hand = m.body_mocapid[m.body("hand").id]
    qa = m.jnt_qposadr[m.body_jntadr[cell]]
    va = m.jnt_dofadr[m.body_jntadr[cell]]
    mujoco.mj_forward(m, d)
    eq = m.equality("grip").id
    frames = []
    t0 = time.time()
    while d.time < K["T"]:
        t = d.time
        if t < K["t_release"]:
            i = max(j for j in range(len(keys)) if keys[j][0] <= t)
            a, b = keys[i], keys[min(i + 1, len(keys) - 1)]
            u = 0 if b[0] == a[0] else np.clip((t - a[0]) / (b[0] - a[0]), 0, 1)
            u = 0.5 - 0.5 * np.cos(np.pi * u)
            cc, qq = key_pose(fmt, np.array(a[1]) + (np.array(b[1]) - np.array(a[1])) * u, a[2] + (b[2] - a[2]) * u)
            d.mocap_pos[hand], d.mocap_quat[hand] = cc, qmul(qq, q_rev)
        else:
            d.eq_active[eq] = 0
        mujoco.mj_step(m, d)
        if record and int(d.time / 0.05) != int((d.time - m.opt.timestep) / 0.05):
            frames.append(dict(t=float(d.time), qpos=d.qpos.tolist()))
    f6 = np.zeros(6)
    touch = {}
    for i in range(d.ncon):
        con = d.contact[i]
        n1, n2 = m.geom(con.geom1).name, m.geom(con.geom2).name
        mujoco.mj_contactForce(m, d, i, f6)
        for x, y in ((n1, n2), (n2, n1)):
            touch.setdefault(x, {})
            touch[x][y] = touch[x].get(y, 0.0) + abs(f6[0])
    centre = d.qpos[qa : qa + 3] / MM
    centre[2] -= FLOOR_T
    speed = np.linalg.norm(d.qvel[va : va + 3]) / MM
    R = np.zeros(9)
    mujoco.mju_quat2Mat(R, d.qpos[qa + 3 : qa + 7])
    R = R.reshape(3, 3)
    res = dict(format=fmt, reverse=reverse, centre_mm=centre.tolist(), speed_mm_s=float(speed), wall=time.time() - t0)
    if D["kind"] in ("cradle", "nine_volt"):
        tilt = float(np.degrees(np.arcsin(min(1, abs(R[2, 0])))))
        comp = -d.qpos[m.jnt_qposadr[m.joint("spring").id]] / MM
        k = float(m.jnt_stiffness[m.joint("spring").id])
        seated = abs(centre[0]) < 0.6 and abs(centre[2] - D["half_h"]) < 0.4 and tilt < 1.0 and speed < 1.0
        if D["kind"] == "cradle":
            on = touch.get("plus_plate", {})
            F = sum(on.values())
            pol = "correct" if set(on) == {"nub"} else ("reversed" if "can" in on else "no contact")
        else:
            F = sum(
                v
                for g, dct in touch.items()
                if g.startswith(("term_", "slot_"))
                for g2, v in dct.items()
                if g2 in ("can", "plus_snap", "minus_snap")
            )
            pol = "correct, keyed" if seated else "blocked by keying"
        res.update(
            tilt_deg=tilt,
            compression_mm=float(comp),
            design_mm=D["pre"],
            stiffness=k,
            force_N=float(F) if seated else None,
            force_design_N=CELLS[fmt]["F"],
            seated=bool(seated),
            polarity=pol,
        )
    else:
        tilt = float(np.degrees(np.arccos(min(1, abs(R[2, 2])))))
        q = d.qpos[m.jnt_qposadr[m.joint("clip").id]]
        on = {}
        for g in ("clip_plate", "clip_lead"):
            for g2, v in touch.get(g, {}).items():
                on[g2] = on.get(g2, 0.0) + v
        top = "can" if "can" in on else ("cap" if "cap" in on else "none")
        seated = (
            np.hypot(centre[0], centre[1]) < 0.6 and abs(centre[2] - D["h"] / 2) < 0.15 and tilt < 1.0 and speed < 1.0
        )
        res.update(
            tilt_deg=tilt,
            clip_lift_deg=float(np.degrees(q)),
            force_N=float(sum(on.values())),
            force_design_N=CELLS[fmt]["F"],
            seated=bool(seated),
            polarity={"can": "correct (+ under the clip)", "cap": "reversed (- under the clip)"}.get(top, "no contact"),
        )
    if record:
        res["frames"] = frames
        res["xml"] = xml
    return res


def check_insertion(res):
    """Normal insertion: seated, spring at its design compression (+-0.1 mm), force within 10 %.
    Reversed: a 9V must be refused (keyed); other cells seat with the wrong polarity."""
    if res["reverse"]:
        if res["format"] == "9V":
            return not res["seated"], res["polarity"]
        return res["seated"] and "reversed" in res["polarity"], f"seated, {res['polarity']}"
    ok = res["seated"] and res["polarity"].startswith("correct")
    if "compression_mm" in res:
        ok = ok and abs(res["compression_mm"] - res["design_mm"]) < 0.1
        msg = f"spring {res['compression_mm']:.2f}/{res['design_mm']:.1f} mm, F {res['force_N'] or 0:.2f} N"
    else:
        msg = f"clip lifted {res['clip_lift_deg']:.2f} deg, F {res['force_N']:.2f} N"
    ok = ok and res["force_N"] is not None and abs(res["force_N"] - res["force_design_N"]) < 0.1 * res["force_design_N"]
    return ok, f"{msg} (design {res['force_design_N']:.1f} N), {res['polarity']}"


# ------------------------------------------------------------------ screwing (optional)
def screwing(screw_file, nut_file, size, seconds=3.0):
    """A nut driven at 1 turn/s on a fixed screw, then backwards; advance per turn vs the pitch."""
    import mujoco

    P = METRIC[size]["P"] * MM
    st = scene(
        None,
        [
            ("bolt", screw_file, (0, 0, 0), (1, 0, 0, 0), {"kinematic": True}),
            ("nut", nut_file, (0, 0, 4 * P), (1, 0, 0, 0), {}),
        ],
    )
    dt = 1e-4
    xml = convert(
        st,
        options=OPTIONS.format(dt=dt),
        default='<default><geom solref="0.0005 1" solimp="0.95 0.99 0.0001" margin="0" condim="4"/></default>',
    )
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    bid = m.body("nut").id
    mujoco.mj_forward(m, d)

    def yaw(q):
        w, x, y, z = q
        return np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))

    out = []
    for omega, label in ((-2 * np.pi, "tighten"), (2 * np.pi, "loosen")):
        turned, prev, z0 = 0.0, yaw(d.qpos[3:7]), d.qpos[2]
        kd = m.body_inertia[bid][2] / (dt * 5)
        rows = []
        for i in range(int(seconds / dt)):
            d.xfrc_applied[bid] = [0, 0, 0, 0, 0, -kd * (d.qvel[5] - omega)]
            mujoco.mj_step(m, d)
            y = yaw(d.qpos[3:7])
            turned += (y - prev + np.pi) % (2 * np.pi) - np.pi
            prev = y
            if i % int(0.01 / dt) == 0:
                rows.append((turned / (2 * np.pi), (d.qpos[2] - z0) / MM))
        A = np.array(rows)
        sel = np.abs(A[:, 0]) >= 0.25
        per = float(np.polyfit(A[sel, 0], A[sel, 1], 1)[0])
        out.append(dict(label=label, turns=float(turned / (2 * np.pi)), per_turn_mm=per))
    return out


# ------------------------------------------------------------------ the whole suite
def sim_test(set_dir, insertions=True, screw=False, verbose=True, only=None):
    rows = []

    def add(name, kind, ok, msg, wall):
        rows.append(dict(test=name, kind=kind, ok=bool(ok), info=msg, wall=round(wall, 2)))
        if verbose:
            print(f"{'PASS' if ok else 'FAIL'}  {name:28s} {msg}  ({wall:.1f}s)", flush=True)

    for name, kind, path, info in build_test_scenes(set_dir):
        if only and only not in name:
            continue
        ok, msg, wall = check_scene(name, kind, path, info)
        add(name, kind, ok, msg, wall)
    inv = inventory(set_dir)
    by = {(a["kind"], a["key"]): a for a in inv.values()}
    if insertions:
        for fmt in CELLS:
            if ("cell", fmt) in by and ("holder", fmt) in by and (not only or only in f"insertion_{fmt}"):
                for rev in (False, True):
                    r = insertion(by[("cell", fmt)]["file"], by[("holder", fmt)]["file"], fmt, rev)
                    ok, msg = check_insertion(r)
                    add(f"insertion_{fmt}{'_reversed' if rev else ''}", "insertion", ok, msg, r["wall"])
    if screw:
        for size in METRIC:
            sc = [a for a in inv.values() if a["kind"] == "screw" and a["key"] == size]
            if sc and ("nut", size) in by and (not only or only in f"screwing_{size}"):
                t0 = time.time()
                res = screwing(sc[0]["file"], by[("nut", size)]["file"], size)
                P = METRIC[size]["P"]
                ok = all(abs(abs(x["per_turn_mm"]) - P) <= 0.05 * P and abs(x["turns"]) > 1 for x in res)
                msg = ", ".join(f"{x['label']} {x['turns']:+.2f} turns, {x['per_turn_mm']:+.3f} mm/turn" for x in res)
                add(f"screwing_{size}", "screwing", ok, f"{msg} (pitch {P} mm)", time.time() - t0)
    os.makedirs(os.path.join(set_dir, "sim_test"), exist_ok=True)
    with open(os.path.join(set_dir, "sim_test", "sim_test.json"), "w", encoding="utf-8") as f:
        json.dump(dict(engine="mujoco", passed=sum(r["ok"] for r in rows), total=len(rows), tests=rows), f, indent=1)
    if verbose:
        print(f"{sum(r['ok'] for r in rows)}/{len(rows)} passed")
    return rows
