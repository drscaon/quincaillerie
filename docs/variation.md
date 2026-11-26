# What each instance draws

Every Quincaillerie instance draws its own values, aspect by aspect (see
[openusd.md](openusd.md) for where they are written). This page declares how
each one is drawn, with the default options (`--thread-play class`, every
aspect on, `--defect-rate 0.15`).

The tables below are written from `quincaillerie/declared.py`, and
`tests/test_distributions.py` draws thousands of instances to check that the
sampler follows them: every drawn column must be declared, every value must
lie in its declared range, and the values must follow the declared
distribution (Kolmogorov-Smirnov for numbers, chi-square for choices, at
p > 0.001). Regenerate the tables with `python -m quincaillerie.declared`.

Notes:

- The tests draw an M8 part in `zinc_clear`. A stainless (`stainless_a2`) or
  brass part never rusts, so its `rust` is always 0.
- Every recorded value is the value the part's geometry and colliders use:
  a value a part does not have (a nut's length, a washer's hex) is not
  recorded, and a cell's dent and corrosion crust are in its colliders
  (`tests/test_physical_defects.py` checks both in MuJoCo). Whether each
  value changes how a part behaves is checked by the physical tests
  ([physics.md](physics.md)).
- These ranges are plausible, not measured: see [limits.md](limits.md).

<!-- declared: begin -->
### screw

| Column | Aspect | Drawn as |
|---|---|---|
| `variation:clearance_mm` | tolerance | uniform over the tolerance band of the fit class (`fits.py`) |
| `variation:thread_class` | tolerance | always `6g` |
| `variation:across_flats_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:height_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:length_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:bearing_face_d_mm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:bearing_face_h_mm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:fillet_r_mm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:defect` | defect | `none` 85 %; `crushed_thread` 5 %; `bent` 5 %; `burr` 5 % |
| `variation:defect_z` | defect | uniform, 0.15 to 0.85 (instances with `crushed_thread` or `burr`): a crushed thread: where along the shank, and where around it starts; a burr: where around the tip it starts |
| `variation:defect_angle_deg` | defect | uniform, 40 to 140 (instances with `crushed_thread` or `burr`): how far around the thread the crush or the burr extends |
| `variation:defect_size` | defect | `crushed_thread`: uniform, 0.3 to 0.6; `bent`: uniform, 0.8 to 3; `burr`: uniform, 0.1 to 0.25 (instances with a defect): how deep the crush is, how far the shank bends, how high the burr stands |
| `variation:scratches` | wear | 35 %: uniform, 0 to 0.15; 65 %: uniform, 0.2 to 0.8 |
| `variation:rust` | wear | 85 %: always `0`; 15 %: uniform, 0.2 to 0.9 |
| `variation:oil` | wear | 85 %: always `0`; 15 %: uniform, 0.4 to 1 |
| `variation:dirt` | wear | 65 %: always `0`; 25 %: uniform, 0 to 0.3; 10 %: uniform, 0.2 to 0.8 |
| `variation:seed` | wear | integer, 0 to 2³¹ − 1 |
| `variation:density` | physics | divided by the finish's density: normal, mean 1, sd 0.005 |
| `variation:friction` | wear, physics | finish friction × (1 + 0.8 rust + 0.3 dirt − 0.4 oil), kept within 0.08 to 0.45, then × normal(1, 0.08); always within 0.06 to 0.5 |

### bolt

| Column | Aspect | Drawn as |
|---|---|---|
| `variation:clearance_mm` | tolerance | uniform over the tolerance band of the fit class (`fits.py`) |
| `variation:thread_class` | tolerance | always `6g` |
| `variation:across_flats_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:height_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:length_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:bearing_face_d_mm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:bearing_face_h_mm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:fillet_r_mm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:shank_d_mm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:plain_length_mm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:defect` | defect | `none` 85 %; `crushed_thread` 5 %; `bent` 5 %; `burr` 5 % |
| `variation:defect_z` | defect | uniform, 0.15 to 0.85 (instances with `crushed_thread` or `burr`): a crushed thread: where along the threaded part, and where around it starts; a burr: where around the tip it starts |
| `variation:defect_angle_deg` | defect | uniform, 40 to 140 (instances with `crushed_thread` or `burr`): how far around the thread the crush or the burr extends |
| `variation:defect_size` | defect | `crushed_thread`: uniform, 0.3 to 0.6; `bent`: uniform, 0.8 to 3; `burr`: uniform, 0.1 to 0.25 (instances with a defect): how deep the crush is, how far the shank bends, how high the burr stands |
| `variation:scratches` | wear | 35 %: uniform, 0 to 0.15; 65 %: uniform, 0.2 to 0.8 |
| `variation:rust` | wear | 85 %: always `0`; 15 %: uniform, 0.2 to 0.9 |
| `variation:oil` | wear | 85 %: always `0`; 15 %: uniform, 0.4 to 1 |
| `variation:dirt` | wear | 65 %: always `0`; 25 %: uniform, 0 to 0.3; 10 %: uniform, 0.2 to 0.8 |
| `variation:seed` | wear | integer, 0 to 2³¹ − 1 |
| `variation:density` | physics | divided by the finish's density: normal, mean 1, sd 0.005 |
| `variation:friction` | wear, physics | finish friction × (1 + 0.8 rust + 0.3 dirt − 0.4 oil), kept within 0.08 to 0.45, then × normal(1, 0.08); always within 0.06 to 0.5 |

### nut

| Column | Aspect | Drawn as |
|---|---|---|
| `variation:clearance_mm` | tolerance | uniform over the tolerance band of the fit class (`fits.py`) |
| `variation:thread_class` | tolerance | always `6H` |
| `variation:across_flats_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:height_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:defect` | defect | `none` 85 %; `crushed_thread` 7.5 %; `oval` 7.5 % |
| `variation:defect_z` | defect | uniform, 0.15 to 0.85 (instances with `crushed_thread`): where along the bore the crushed thread is, and where around it starts |
| `variation:defect_angle_deg` | defect | uniform, 40 to 140 (instances with `crushed_thread`): how far around the bore the crush extends |
| `variation:defect_size` | defect | `crushed_thread`: uniform, 0.3 to 0.6; `oval`: uniform, 0.04 to 0.12 (instances with a defect) |
| `variation:scratches` | wear | 35 %: uniform, 0 to 0.15; 65 %: uniform, 0.2 to 0.8 |
| `variation:rust` | wear | 85 %: always `0`; 15 %: uniform, 0.2 to 0.9 |
| `variation:oil` | wear | 85 %: always `0`; 15 %: uniform, 0.4 to 1 |
| `variation:dirt` | wear | 65 %: always `0`; 25 %: uniform, 0 to 0.3; 10 %: uniform, 0.2 to 0.8 |
| `variation:seed` | wear | integer, 0 to 2³¹ − 1 |
| `variation:density` | physics | divided by the finish's density: normal, mean 1, sd 0.005 |
| `variation:friction` | wear, physics | finish friction × (1 + 0.8 rust + 0.3 dirt − 0.4 oil), kept within 0.08 to 0.45, then × normal(1, 0.08); always within 0.06 to 0.5 |

### washer

| Column | Aspect | Drawn as |
|---|---|---|
| `variation:height_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:defect` | defect | `none` 85 %; `dished` 15 % |
| `variation:defect_size` | defect | uniform, 0.15 to 0.5 (instances with a defect): the height of the cone at the rim |
| `variation:scratches` | wear | 35 %: uniform, 0 to 0.15; 65 %: uniform, 0.2 to 0.8 |
| `variation:rust` | wear | 85 %: always `0`; 15 %: uniform, 0.2 to 0.9 |
| `variation:oil` | wear | 85 %: always `0`; 15 %: uniform, 0.4 to 1 |
| `variation:dirt` | wear | 65 %: always `0`; 25 %: uniform, 0 to 0.3; 10 %: uniform, 0.2 to 0.8 |
| `variation:seed` | wear | integer, 0 to 2³¹ − 1 |
| `variation:density` | physics | divided by the finish's density: normal, mean 1, sd 0.005 |
| `variation:friction` | wear, physics | finish friction × (1 + 0.8 rust + 0.3 dirt − 0.4 oil), kept within 0.08 to 0.45, then × normal(1, 0.08); always within 0.06 to 0.5 |

### cell (cylinder)

| Column | Aspect | Drawn as |
|---|---|---|
| `variation:diameter_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:length_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:defect` | defect | `none` 85 %; `dent` 7.5 %; `corroded_terminal` 7.5 % |
| `variation:defect_angle_deg` | defect | uniform, 0 to 360 (instances with a defect): the angle of the dent, or of the crust on the minus face |
| `variation:defect_z` | defect | uniform, 0.2 to 0.8 (instances with `dent`): where the dent is along the can |
| `variation:defect_size` | defect | uniform, 0.3 to 1 (instances with a defect): the dent's depth in mm, or the crust's size relative to its mean |
| `variation:label_wear` | wear | beta(1.2, 3) |
| `variation:dirt` | wear | beta(1, 4) |
| `variation:seed` | wear | integer, 0 to 2³¹ − 1 |
| `variation:mass_factor` | physics | normal, mean 1, sd 0.03 |
| `variation:friction` | physics | normal, mean 0.3, sd 0.04, kept within 0.18 to 0.45 |

### cell (coin)

| Column | Aspect | Drawn as |
|---|---|---|
| `variation:diameter_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:length_dmm` | tolerance | uniform over the tolerance its standard or datasheet allows ([sources](sources.md)) |
| `variation:defect` | defect | `none` 85 %; `corroded_terminal` 15 % |
| `variation:defect_angle_deg` | defect | uniform, 0 to 360 (instances with a defect): where the crust is around the seal |
| `variation:defect_size` | defect | uniform, 0.3 to 1 (instances with a defect): the crust's size relative to its mean |
| `variation:label_wear` | wear | beta(1.2, 3) |
| `variation:dirt` | wear | beta(1, 4) |
| `variation:seed` | wear | integer, 0 to 2³¹ − 1 |
| `variation:mass_factor` | physics | normal, mean 1, sd 0.03 |
| `variation:friction` | physics | normal, mean 0.3, sd 0.04, kept within 0.18 to 0.45 |

### holder

| Column | Aspect | Drawn as |
|---|---|---|
| `variation:play_dmm` | tolerance | uniform, 0 to 0.6 |
| `variation:plastic` | wear | `abs_black` 70 %; `abs_grey` 30 % |
| `variation:seed` | wear | integer, 0 to 2³¹ − 1 |
| `variation:spring_factor` | physics | normal, mean 1, sd 0.08 |
| `variation:preload_factor` | physics | 30 %: uniform, 0.7 to 1; 70 %: uniform, 0.95 to 1 |
| `variation:clip_factor` | physics | normal, mean 1, sd 0.1 |
| `variation:friction` | physics | normal, mean 0.3, sd 0.04, kept within 0.18 to 0.45 |
<!-- declared: end -->
