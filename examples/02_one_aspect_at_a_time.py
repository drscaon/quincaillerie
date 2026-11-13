"""Change one thing and nothing else: the aspects of Quincaillerie.

What varies from one instance to the next is split into four aspects
(tolerance, defect, wear, physics), each with its own random stream. Turning
one aspect off leaves the draws of the others as they were. With the same
seed you get the same parts with a single difference, which is what you want
when you study what a robot or a perception model is sensitive to.

Here: the same M8 screws twice, the second time without wear (no rust, oil,
dirt or scratches). Fits and defects stay the same, screw for screw.

The draws are shown straight from the sampler, without writing any file. With
files, the same choice is `vary=` in `generate()` and `--no-vary wear` on the
command line.

    python examples/02_one_aspect_at_a_time.py
"""

from quincaillerie.variation import ASPECTS, Sampler

SEED = 2
M8 = dict(pitch_mm=1.25, diameter_mm=8.0)

worn = Sampler(seed=SEED, defect_rate=0.5)
clean = Sampler(seed=SEED, defect_rate=0.5, vary=tuple(a for a in ASPECTS if a != "wear"))

print(f"{'screw':6s} {'rust':>14s} {'friction':>16s} {'clearance (um)':>18s}  defect")
print(f"{'':6s} {'worn':>7s} {'clean':>6s} {'worn':>8s} {'clean':>7s} {'worn':>9s} {'clean':>8s}")
pairs = []
for i in range(6):
    a = worn.fastener("screw", "zinc_clear", **M8)
    b = clean.fastener("screw", "zinc_clear", **M8)
    pairs.append((a, b))
    print(
        f"{i:<6d} {a.rust:7.2f} {b.rust:6.2f} {a.friction:8.3f} {b.friction:7.3f} "
        f"{a.clearance_mm * 1000:9.0f} {b.clearance_mm * 1000:8.0f}  {a.defect} / {b.defect}"
    )

# Wear changed (and friction with it: rust raises it, oil lowers it); the rest did not.
assert all(b.rust == b.oil == b.dirt == b.scratches == 0 for _, b in pairs)
assert all(a.clearance_mm == b.clearance_mm and a.defect == b.defect for a, b in pairs)
print("\nsame seed, wear switched off: clean parts, same fits and defects")
