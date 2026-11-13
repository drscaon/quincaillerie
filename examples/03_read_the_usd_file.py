"""Read what Quincaillerie wrote, with OpenUSD alone.

You do not need Quincaillerie to use a pack. Everything is in the OpenUSD
files, under the attribute namespace of the Primvaria contract:

    primvaria:generator, primvaria:preset, primvaria:seed   what made this asset
    primvaria:variation:<name>                              what was drawn for it
    primvaria:measured:<name>                               what was measured on it

This script generates two nuts, then opens their files with pxr only, as a
simulator or a data pipeline would.

    python examples/03_read_the_usd_file.py
"""

import sys
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics

from quincaillerie import generate, resolve

out = sys.argv[1] if len(sys.argv) > 1 else "output/examples"
result = generate(resolve("nut", "M8"), out, count=2, seed=7, detail="low", scene=False)
files = sorted(Path(result.out_dir, "assets").glob("*.usdc"))

# ---- from here on, no Quincaillerie: only OpenUSD ----
for usd_file in files:
    stage = Usd.Stage.Open(str(usd_file))
    part = stage.GetDefaultPrim()  # one instance per file, as its default prim
    units = UsdGeom.GetStageMetersPerUnit(stage)
    made_by = part.GetAttribute("primvaria:generator").Get()
    aspects = part.GetAttribute("primvaria:variation:aspects").Get()
    print(f"{usd_file.name}: made by {made_by}, {units} m per unit, aspects that varied: {', '.join(aspects)}")

    fit = part.GetAttribute("primvaria:variation:thread_class").Get()
    clearance = part.GetAttribute("primvaria:variation:clearance_mm").Get()
    defect = part.GetAttribute("primvaria:variation:defect").Get()
    mass = part.GetAttribute("primvaria:measured:mass_kg").Get()
    print(f"  fit {fit}, clearance {clearance * 1000:.0f} um per side, defect: {defect}, mass {mass * 1000:.2f} g")

    # The finishes are a standard variant set: pick one without regenerating.
    finishes = part.GetVariantSet("finish").GetVariantNames()
    print(f"  finishes to choose from: {', '.join(finishes)}")

    # The physics is standard UsdPhysics. The thread is collided by many small
    # convex pieces, which is what lets a nut really screw onto a screw.
    colliders = sum(1 for p in Usd.PrimRange(part) if p.HasAPI(UsdPhysics.CollisionAPI))
    body = "a rigid body" if part.HasAPI(UsdPhysics.RigidBodyAPI) else "no rigid body on the root"
    print(f"  {body}, {colliders} collision pieces")
