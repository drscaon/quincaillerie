"""Prove that the thread is a thread: turn a nut and watch it advance.

The check builds a MuJoCo model from the two OpenUSD files (the thread of each
part is collided by small convex pieces that follow the helix), turns the nut
on a fixed screw at one turn per second, then turns it back. If the geometry
is right, the nut moves along the screw by one pitch per turn: 1 mm for M6.
Nothing in the model says "this is a screw joint"; the motion comes from the
contacts alone.

Needs MuJoCo:  pip install "quincaillerie[sim]"
Takes about 30 seconds.

    python examples/04_screwing_in_mujoco.py
"""

import sys

from quincaillerie import METRIC, generate, resolve
from quincaillerie.sim.checks import inventory, screwing

SIZE = "M6"
out = sys.argv[1] if len(sys.argv) > 1 else "output/examples"

# The nominal parts (no variation), so the result is the reference behaviour.
result = generate(resolve("screw", SIZE, length=16, with_=["nut"]), out, vary=(), detail="low", scene=False)
parts = inventory(result.out_dir)
screw = next(p for p in parts.values() if p["kind"] == "screw")
nut = next(p for p in parts.values() if p["kind"] == "nut")

pitch_mm = METRIC[SIZE]["P"]
ok = True
for run in screwing(screw["file"], nut["file"], SIZE, seconds=1.0):
    per_turn = abs(run["per_turn_mm"])
    good = abs(per_turn - pitch_mm) < 0.1 * pitch_mm
    ok &= good
    print(
        f"{run['label']:8s} {abs(run['turns']):.2f} turns, {per_turn:.3f} mm per turn (pitch: {pitch_mm} mm)  {'PASS' if good else 'FAIL'}"
    )

sys.exit(0 if ok else 1)
