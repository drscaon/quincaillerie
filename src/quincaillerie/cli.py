"""Command line: quincaillerie list | generate | sim-test | blender-test | blender-addon."""

from __future__ import annotations

import argparse
import sys
import time

from . import __version__
from .catalog import CELLS, DEFAULT_LENGTH, KINDS, LENGTHS, METRIC, RELATED, SIZES
from .materials import FINISHES
from .variation import ASPECTS


def cmd_list(args):
    print("Fasteners (metric coarse thread), sizes:", " ".join(SIZES))
    head = ("size", "pitch", "hex s", "head k", "nut m", "washer d1 x d2 x h")
    print("  {:5s} {:>6s} {:>6s} {:>7s} {:>6s} {:>20s}  default screw".format(*head))
    for s, t in METRIC.items():
        w = "x".join(f"{x:g}" for x in t["washer"])
        row = f"  {s:5s} {t['P']:6.2f} {t['s']:6.1f} {t['k']:7.1f} {t['m']:6.1f} {w:>20s}"
        print(f"{row}  ISO4017_{s}x{DEFAULT_LENGTH[s]}")
    print("  screw lengths (mm):", " ".join(map(str, LENGTHS)), "(any length from 2 pitches to 200 mm)")
    print("  finishes:", " ".join(FINISHES))
    print("Cells and holders, formats:")
    for f, c in CELLS.items():
        dims = (
            f"d {c['d']} x L {c['L']}"
            if "L" in c and "d" in c
            else (f"{c['L']} x {c['W']} x {c['T']}" if c["kind"] == "nine_volt" else f"d {c['d']} x h {c['h']}")
        )
        print(f"  {f:7s} {c['iec']:9s} {c['volts']:4.1f} V  {dims:16s} mm  {c['mass']:6.1f} g  holder: {c['kind']}")
    print("Kinds:", ", ".join(KINDS), "| --with:", "; ".join(f"{k}: {', '.join(v)}" for k, v in RELATED.items()))
    return 0


def cmd_generate(args):
    from .generator import catalog_parts, generate, resolve

    t0 = time.time()
    if args.kind == "all":
        parts = catalog_parts()
        set_name = "catalog"
    else:
        if not args.key:
            print("generate: give a size (screw, nut, washer) or a cell format (cell, holder)", file=sys.stderr)
            return 2
        with_ = [w for w in (args.with_ or "").split(",") if w]
        parts = resolve(args.kind, args.key, args.length, with_)
        set_name = None
    res = generate(
        parts,
        args.out,
        set_name,
        count=args.count,
        finish=args.finish,
        seed=args.seed,
        scene=not args.no_scene,
        physics=not args.no_physics,
        vary=() if args.nominal else tuple(a for a in ASPECTS if a not in (args.no_vary or "").split(",")),
        defect_rate=args.defect_rate,
        detail=args.detail,
    )
    print(f"{len(res.parts)} assets in {res.out_dir}/assets ({time.time() - t0:.1f}s)")
    if len(res.parts) > 12:  # a summary, not every line
        from collections import Counter

        print("  defects:", dict(Counter(p.get("variation:defect", "none") for p in res.parts)))
        res.parts = res.parts[:6]
    for p in res.parts:
        extra = f", {p['colliders']} collision pieces" if "colliders" in p else ""
        print(
            f"  {p['name']:22s} {p['kind']:7s} {p['mass_g']:8.2f} g{extra}"
            if "mass_g" in p
            else f"  {p['name']:22s} {p['kind']}"
        )
    if res.scene:
        print(f"scene: {res.scene}")
    return 0


def cmd_sim_test(args):
    from .sim.checks import sim_test

    rows = sim_test(
        args.dir, insertions=not args.no_insertion, screw=args.screwing, only=args.only, defects=args.defects
    )
    return 0 if all(r["ok"] for r in rows) else 1


def cmd_blender_test(args):
    from .blender.checks import blender_test

    rows = blender_test(args.dir, mode=args.mode, blender=args.blender, only=args.only)
    return 0 if (all(r["ok"] for r in rows) or args.mode == "naive") else 1


def cmd_blender_addon(args):
    from .blender import write_addon

    path = write_addon(args.out)
    if path.endswith(".zip"):
        print(f"written {path}: in Blender, Edit > Preferences > Get Extensions > Install from Disk")
    else:
        print(f"written {path}: in Blender, Edit > Preferences > Add-ons > Install from Disk (legacy add-on),")
        print("or run it from the Scripting workspace, or headless: blender -b -P", path, "-- file.usda")
    print("then File > Import > Universal Scene Description: rigid bodies and joints are set up on import")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="quincaillerie", description="Standard hardware assets generator for Physical AI.")
    p.add_argument("--version", action="version", version=f"quincaillerie {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="sizes, formats, finishes").set_defaults(func=cmd_list)
    g = sub.add_parser("generate", help="write assets, materials and a scene")
    g.add_argument("kind", choices=list(KINDS) + ["all"], help="part kind, or 'all' for the whole catalogue")
    g.add_argument(
        "key", nargs="?", help="size (M3..M12) for screw/nut/washer, format (AA, 18650, CR2032...) for cell/holder"
    )
    g.add_argument("--length", type=float, help="screw length in mm (default: per size)")
    g.add_argument(
        "--with", dest="with_", metavar="KINDS", help="related elements, comma-separated: nut,washer / holder / cell"
    )
    g.add_argument("--count", type=int, default=1, help="distinct instances of each part (default 1)")
    g.add_argument(
        "--nominal", action="store_true", help="no variation: the nominal part (--count copies in the scene)"
    )
    g.add_argument(
        "--no-vary", metavar="ASPECTS", help="aspects that stay nominal, comma-separated: " + ",".join(ASPECTS)
    )
    g.add_argument("--defect-rate", type=float, default=0.15, help="share of instances with a defect (default 0.15)")
    g.add_argument("--detail", choices=["low", "normal", "high"], default="normal", help="visual mesh resolution")
    g.add_argument("--finish", default="zinc_clear", choices=FINISHES, help="default finish of fasteners")
    g.add_argument("--seed", type=int, default=1)
    g.add_argument("--out", default="output")
    g.add_argument("--no-scene", action="store_true", help="assets and materials only")
    g.add_argument("--no-physics", action="store_true", help="visual assets only: no rigid bodies, colliders or joints")
    g.set_defaults(func=cmd_generate)
    s = sub.add_parser("sim-test", help="MuJoCo checks of a generated set")
    s.add_argument("dir")
    s.add_argument("--no-insertion", action="store_true", help="skip the cell insertion tests")
    s.add_argument("--screwing", action="store_true", help="also screw each nut on its screw (slow)")
    s.add_argument("--defects", action="store_true", help="check that crushed threads jam a nut (slow)")
    s.add_argument("--only", help="run the tests whose name contains this text")
    s.set_defaults(func=cmd_sim_test)
    b = sub.add_parser("blender-test", help="the same gravity checks in Blender")
    b.add_argument("dir")
    b.add_argument(
        "--mode", choices=["setup", "naive"], default="setup", help="setup: with the import script; naive: by hand"
    )
    b.add_argument("--blender", help="Blender executable (default: the bpy module, or blender on the PATH)")
    b.add_argument("--only")
    b.set_defaults(func=cmd_blender_test)
    c = sub.add_parser("blender-addon", help="write the Blender add-on (physics set up on USD import)")
    c.add_argument("--out", default="quincaillerie_physics.zip", help=".zip (extension) or .py (add-on or script)")
    c.set_defaults(func=cmd_blender_addon)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
