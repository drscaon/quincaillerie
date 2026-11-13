# Defect rate and jam rate

How often does a nut jam on a screw, as a function of `--defect-rate`? Measured in MuJoCo 4.0.1
on M6 × 16 screws (6g fit, low detail), with one sound, nominal nut driven with a light torque.
Data: [`jam_experiment.json`](jam_experiment.json); script:
[`scripts/jam_experiment.py`](../scripts/jam_experiment.py) (about 17 minutes on 2 CPU cores).

## What each defect does to a nut

| Screw | Screws tested | Result |
|---|---|---|
| sound, fit drawn in 6g | 10 | 0 jam: the nut runs head to tip, 9.30–9.89 mm (nominal screw: 9.72 mm) |
| crushed thread | 11 | **11 jam**: driven into the damaged zone, the nut stops after 0.86–2.14 mm, against 2.9–3.0 mm on a sound screw |
| bent shank (0.8–3°) | 7 | 0 jam: 9.41–10.01 mm, as on a sound screw. Over the height of a nut the bend is smaller than the play of the fit |
| burr at the tip | 12 | 0 jam along the thread; the nut is held 0.3 to 1.7 mm short of the tip (7.98–9.05 mm) |

So only a crushed thread jams a nut on the thread. A burr keeps the nut from passing the tip,
which matters for starting or removing a nut, not for running it; the margin to a sound screw is
small (0.25 mm between the worst sound screw and the best burr), so it is reported, not counted.

## The curve

A screw draws a defect with probability `--defect-rate`, and the defect is a crushed thread one
time in three (the other two: bent, burr). Every crushed thread that was tested jammed and no
other screw did, so:

```
jam rate = defect rate / 3
```

| `--defect-rate` | 0 | 0.15 (default) | 0.25 | 0.5 | 0.75 | 1 |
|---|---|---|---|---|---|---|
| screws that jam a nut | 0 % | 5 % | 8 % | 17 % | 25 % | 33 % |

Measured at the two ends: 0 of 10 at rate 0, 11 of 30 (37 %) at rate 1.

## What protects it

- `tests/test_jam_rate.py`: the share of crushed threads the sampler draws grows with the defect
  rate and stays near a third of it; the stored experiment still says what this page says.
- CI, on every push: every crushed thread of a varied M8 batch must jam a nut that runs freely
  on a sound screw (`quincaillerie sim-test --defects`).

## Limits

One size (M6 × 16), one nut, one torque (a light hand on a nut driver), rigid parts: a real nut
driven with a wrench would deform or cut through a crushed crest. Nuts with defects (crushed
thread, oval) were not part of this experiment.
