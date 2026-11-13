# Physics: fits, colliders and checks

The thread fit classes, thread and simple colliders, the Blender add-on, and the MuJoCo and Blender checks with their results.

Part of the [Quincaillerie](../README.md) documentation.

## Blender

Blender's USD importer reads geometry and materials but ignores UsdPhysics:
imported as is, a holder is three loose objects and a nut a convex lump that
cannot go on a screw. The add-on fixes that once and for all:

1. `quincaillerie blender-addon` writes `quincaillerie_physics.zip`.
2. In Blender (4.4 or later): Edit > Preferences > Get Extensions > Install
   from Disk, pick the zip.
3. File > Import > Universal Scene Description, as usual: every body gets its
   rigid body, every joint its constraint. Press Play.

On import it moves each body's origin to its centre of mass (Blender uses the
origin as centre of mass), makes its collision shape a compound of the USD
shapes (rebuilt from the file, cylinders with 96 sides instead of the
importer's 20), sets mass, friction and small collision margins, turns
joints into Generic Spring constraints with the USD limits, stiffness and
damping, keeps holder coils attached to their spring plate, and sets the
rigid body world to 2000 substeps per second. The same file runs as a script
(`blender -b -P quincaillerie_physics.py -- file.usda`) without installing.

Bullet takes a spring's rest position from the first frame, so a cell placed
already seated in its holder is held by the holder's shape but without the
spring's push: it stays seated, it is not pressed.

## Checks

`quincaillerie sim-test` (MuJoCo, CPU) and `quincaillerie blender-test`
(Blender rigid bodies) build the same small OpenUSD scenes, with the assets
referenced and a floor at z = 0, saved under `sim_test/scenes/`:

| Check | Scene | Pass when |
|---|---|---|
| drop | each part, tilted, dropped from 4–5 cm | rests on the floor: lowest point within 0.35 mm of it, vertical speed below 1 mm/s (round cells may keep rolling) |
| nut_on_screw | a nut on its screw, both dropped | the nut stays on its thread: shift below half a pitch, off-axis below 0.3 mm |
| holder | an empty holder on the floor | the base settles (0.3 mm) and the plate or clip stays put in the base's frame (0.05 mm) |
| seated | a cell in its holder, on the floor | relative to the holder, the cell stays within the holder's side play (+0.6 mm), the contact moves less than 0.3 mm |
| insertion (MuJoCo) | a cell carried into its holder and released, then the same reversed | seated, spring at the compression *this* holder should get from *this* cell (its drawn preload and the cell's drawn length), force within 10 % (coin clips: 15 %, the contact point is estimated); reversed: wrong polarity, or refused by the keying (9 V) |
| screwing (MuJoCo, `--screwing`) | a nut driven 1 turn/s on a fixed screw, then back | advance per turn within 5 % of the pitch |
| jam (MuJoCo, `--defects`) | a sound nut driven with a light torque towards the crushed thread of a screw, and the same on a sound screw | it stops at the damage: it travels at least a quarter pitch less than on the sound screw |

With varied instances, nut-on-screw pairs and assemblies are made of
instances without defects; the defective ones are dropped like the others,
and the crushed threads are checked by the jam test.

### Results

`quincaillerie generate all --nominal` then the checks of the whole
catalogue (41 assets), one CPU core; measured with MuJoCo 3.17, before 4.0 (CI
runs every check on MuJoCo 4), and Blender 5.2 (`bpy`):

| Check | MuJoCo | Blender (add-on) | Blender, rigid bodies added by hand |
|---|---|---|---|
| drop (31 parts) | 31/31 | 31/31 | 31/31 |
| nut on screw (M3–M12) | 7/7, the nut settles 0.10–0.13 mm (its flank clearance) | 7/7 | 0/7: the nut's convex hull fills the hole and is ejected |
| empty holder (10) | 10/10 | 10/10 | 0/10: base and plate fall apart |
| cell seated in its holder (10) | 10/10 | 10/10 | 0/10 |
| insertion (10 formats, both ways) | 20/20 | | |
| screwing (M3–M12) | 7/7: 0.501, 0.70, 0.80, 0.99–1.005, 1.25, 1.50, 1.75 mm per turn | | |

A varied batch, `quincaillerie generate all --count 5 --defect-rate 0.2
--seed 11` (205 instances, 33 of them with a defect: 9 crushed threads, 11
dished washers, 2 bent screws, 2 burrs, 1 oval nut, 2 dented cans, 6 corroded
terminals), then `sim-test --defects` and `blender-test`:

| Check | MuJoCo | Blender (add-on) |
|---|---|---|
| drop (155 parts) | 155/155 | 155/155 |
| nut on screw (2 pairs per size) | 14/14 | 14/14 |
| empty holder (50) | 50/50 | 50/50 |
| cell seated in its holder (50) | 50/50 | 50/50 |
| insertion (50 pairs, both ways) | 100/100, each against its own drawn spring and cell | |
| jam (crushed screws) | 3/3: the nut stops after 0.5–1.2 mm, where it runs 1.5–2.4 mm on a sound screw | |

Insertion: every cradle spring compressed to its design within 0.03 mm, with
its design force within 1 % (AA: 4.98/5.0 mm, 3.48 N for 3.5 N); the 9 V
seats when it is the right way round and is stopped by the terminal slots
when reversed; the coin clips press with 2.81 N (CR2032, 3.0 N designed)
and 1.82 N (LR44, 2.0 N). The checks of the whole catalogue take about four
minutes in MuJoCo and two in Blender; screwing, 1–2 minutes per size.

## Simple colliders

A threaded fastener collides as its helix, in convex pieces: 837 for an
M8 × 30 screw. That is what lets a nut screw on and a crushed thread
jam, and it is heavy for scenes with many parts. When parts only need to
fall, pile up and be grasped, generate them with their envelope alone:

```bash
quincaillerie generate screw M8 --with nut,washer --count 100 --collider simple
quincaillerie sim-test output/ISO4017_M8x30 --scene      # the whole scene settles (MuJoCo)
```

| Part | `thread` | `simple` |
|---|---|---|
| Screw | the helix, a core and the head (837 pieces at M8 × 30) | a cylinder at the major diameter and the head |
| Nut | the internal helix (198 pieces at M8) | twelve wedges around a smooth bore, never narrower than the screw |
| Washer | 24 ring sectors | 8 ring sectors |

The visual mesh, the mass, the inertia, the materials and every drawn value
are the same in both: only the collision changes, and each file says which
it has (`quincaillerie:collision`, and `measured:colliders` in
`instances.csv`). A scene of 100 screws, 100 nuts and 100 washers (303
bodies) settles on the floor in MuJoCo 4.0 in about 25 s on one CPU; the
scene lays the instances out 25 to a row on a floor that covers them all.
`sim-test` skips the tests that need a thread (a nut held on a screw,
screwing, jamming) for parts with simple colliders.

## Thread fit

The play of each thread is drawn inside the usual commercial fit, a 6g screw
in a 6H nut, and recorded as `clearance_mm` and `thread_class`. The limits
are computed from the public formulas of the ISO metric thread tolerance
system ([`fits.py`](https://github.com/drscaon/quincaillerie/blob/main/src/quincaillerie/fits.py)),
not copied from the standard's tables; they land within 5 % of the values
printed in handbooks, which a test checks for M3 to M12.

| Size | Screw 6g, clearance per side (mm) | Nut 6H, clearance per side (mm) |
|---|---|---|
| M3 | 0.015–0.049 | 0.015–0.052 |
| M4 | 0.015–0.056 | 0.015–0.059 |
| M5 | 0.015–0.059 | 0.015–0.062 |
| M6 | 0.015–0.068 | 0.015–0.073 |
| M8 | 0.015–0.075 | 0.015–0.080 |
| M10 | 0.016–0.081 | 0.015–0.086 |
| M12 | 0.017–0.091 | 0.015–0.098 |

`--thread-play` chooses how: `class` (default) draws across the band;
`middle` gives every instance the middle of its band, so the play no longer
depends on the seed; `legacy` draws in the range used before the fit classes
(1.6–8 % of the pitch) and gives, for a seed, exactly the clearances of 0.2.0b1
and earlier. The choice moves the clearance only: every other
drawn value of an instance stays the same.

Two simplifications. The draw is uniform across the band, where a real
production run clusters around its middle. And no part is tighter than
0.015 mm per side, so that the collision pieces can slide: a real 6H nut may
have no play of its own, and the tightest 6g screw has 0.010 to 0.017 mm.
Across flats, heights and lengths are still drawn in plausible ranges, not
from a tolerance class.
