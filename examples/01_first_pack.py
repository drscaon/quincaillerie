"""Generate a first pack of fasteners and read its ground truth.

A pack is the folder Quincaillerie writes for one set of parts: one OpenUSD
file per instance under assets/, a library of materials, a scene with every
instance placed on the ground, and a table (instances.csv) with one row per
instance. The table is read back from the OpenUSD files, so they cannot
disagree.

Run it (about 10 seconds):

    python examples/01_first_pack.py            # writes under output/examples/
    python examples/01_first_pack.py some/dir   # or under a folder of your choice
"""

import sys

from quincaillerie import CELLS, SIZES, generate, resolve
from quincaillerie.pack import read_manifest, read_table

out = sys.argv[1] if len(sys.argv) > 1 else "output/examples"

# The catalogue: metric fasteners by size, battery cells and holders by format.
print(f"sizes: {', '.join(SIZES)}; cell formats: {', '.join(CELLS)}")

# An M6 x 20 screw with its nut and washer, three instances of each. No two
# instances are alike: each draws its own tolerances, defects, wear and
# physics. The seed fixes every draw: the same call always gives the same parts.
parts = resolve("screw", "M6", length=20, with_=["nut", "washer"])
result = generate(parts, out, count=3, seed=1, detail="low")
folder = result.out_dir
print(f"pack written to {folder}")

# manifest.json says what the pack is; its summary counts kinds and defects.
summary = read_manifest(folder)["summary"]
print(f"parts: {summary['by_kind']}, defects: {summary['defects']}")

# instances.csv is the ground truth of each instance: what was drawn for it
# (variation:*) and what was measured once generated (measured:*).
print(f"\n{'instance':20s} {'kind':7s} {'fit':>4s} {'clearance':>10s} {'defect':>15s} {'rust':>5s} {'mass':>8s}")
for row in read_table(folder):
    clearance_um = float(row["variation:clearance_mm"]) * 1000
    mass_g = float(row["measured:mass_kg"]) * 1000
    fit, defect, rust = row["variation:thread_class"] or "-", row["variation:defect"], float(row["variation:rust"])
    print(
        f"{row['name']:20s} {row['kind']:7s} {fit:>4s} {clearance_um:7.0f} um {defect:>15s} {rust:5.2f} {mass_g:6.2f} g"
    )
