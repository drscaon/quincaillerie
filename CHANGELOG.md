# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.6.0b2] - 2026-11-27 (beta)

### Fixed

- 0.6.0b1 gave its version as 0.5.0b1: `quincaillerie --version`, `quincaillerie.__version__`, and the version written in every file (`primvaria:version`, `assetInfo`) and in the pack (`manifest.json`, `instances.csv`). The version is now read from the installed package, as in the other generators, so it cannot fall behind again. Files written by 0.6.0b1 are otherwise those of this release: regenerate them to get the right version in them.

## [0.6.0b1] - 2026-11-27 (beta)

### Documentation

- The README images show the new screws: socket head cap screws (ISO 4762) and a bolt with its plain shank (ISO 4014) among the fasteners, cap screws in the ten varied instances.
- The README links to Primvaria's note on how standards are used; the pull request checklist gains a line for it.
- The note on the tip chamfer's estimate (`docs/sources.md`) is reworded in our own words.

### Added

- `generate --usdz`: also write the pack's file as one `.usdz` package, with the textures and files it references and its engine layers inside (`primvaria_contract.usdz`, primvaria-contract 0.5.0b1); off by default, so the output is unchanged. Each package passes OpenUSD's validators with their packaging rules and opens in Blender.
- Every material says what it is made of with a semantic label (`semantics:labels:material`, Primvaria contract section 5), as NVIDIA's SimReady profiles ask; the shared ground is labelled `ground` and rendered with its own grey material (`concrete`). Requires primvaria-contract 0.4.0b1. Each library material is labelled with its substance (`steel`, `stainless_steel`, `brass`, `nickel`, `abs`, `pet`).
- Hexagon socket head cap screws, ISO 4762 (`quincaillerie generate cap_screw M8`, kind
  `cap_screw`, files `ISO4762_<size>x<length>`), plain head, property class 8.8, 10.9 or 12.9
  (`--property-class`, default 12.9). A cylindrical head with a hex socket ending in a 120° cone:
  the head's diameter, height, the socket's across flats and depth, the top edge's chamfer and
  the bearing circle under the head are drawn within the table's limits and recorded
  (`primvaria:variation:head_d_mm`, `socket_depth_mm`, `top_chamfer_mm`, ...). The head collides
  as six convex walls around the socket and a solid part under it, so a hex key goes in as
  deep as the socket; `MateFrame_drive` (`drive = hex_socket`) sits at its mouth. Threaded to
  the head up to a length per size, with a plain shank beyond, as a bolt's. One cap screw per
  size joins the catalogue (55 assets). Values from a public excerpt of JIS B 1176, which
  corresponds to ISO 4762.
- Thread class 5g6g for class 12.9 cap screws: the pitch diameter's band is grade 5, 0.8 of
  grade 6 (`fits.thread_class`, `fits.GRADE_5_RATIO`); 8.8 and 10.9 stay 6g. No other part's
  draws change.

- Hex head bolts, ISO 4014 (`quincaillerie generate bolt M8 --length 50`, kind `bolt`, files
  `ISO4014_<size>x<length>`): a plain shank under the head, then the thread over the reference
  length b. The shank's diameter (ds min to d) and where the thread starts (between ls min and
  lg max: lg max = l − b, ls min = lg max − 5 P) are drawn per instance and recorded
  (`primvaria:variation:shank_d_mm`, `plain_length_mm`), with the colliders following them. The
  lengths are those of each size's table (M3: 20 to 30 mm, M12: 50 to 120 mm); one bolt per
  size joins the catalogue (48 assets). Values from a public excerpt of JIS B 1180 (part grade A),
  see `docs/sources.md`.
- Under the head of every screw and bolt: a bearing face (diameter dw from dw min to s min,
  height c) and a fillet (radius r from r min to (da max − d) / 2), drawn per instance, in the
  visual mesh, the mass and the colliders (`primvaria:variation:bearing_face_d_mm`,
  `bearing_face_h_mm`, `fillet_r_mm`). These draws come from a stream of their own: no value
  drawn before changes for a given seed. A part built without a sampler takes the middle of
  each range.

### Changed values

- ISO 4017 screws: the hex now ends at the bearing face, the fillet is added; the mass of an
  M8 × 30 goes down by about 0.4 % (15.40 to 15.35 g) and `--collider simple` writes 4 pieces
  instead of 2. Reproducibility references regenerated; no drawn value changed.
- The tip chamfer stays the estimate it was (minor to major diameter over one pitch), now
  listed in `docs/sources.md`: ISO 4753, which sets it, is not public.

### Changed

- `tests/test_contract.py`, `test_pack.py` and `test_golden.py` import the shared tests of primvaria-contract 0.3.0b1 (`primvaria_contract.testing`) instead of keeping a copy of them; the same tests run, one for one. Requires primvaria-contract 0.3.0b1.
- The code of the Primvaria contract comes from the new package primvaria-contract, which
  this generator now requires, instead of copies kept identical in the four generators.
  `contract`, `pack`, `ground` and `conformance` stay as modules of this package and give
  the same names as before, filled in with this generator's name and version: nothing
  changes for code that imports them or for `python -m quincaillerie.conformance`. The contract
  tests on stages written by hand moved to primvaria-contract; `tests/test_contract.py`
  keeps the tests of this generator's files.
- `quincaillerie.validate` (the OpenUSD validators) comes from primvaria-contract too, which this
  generator now requires at 0.2.0b1 or later; `python -m quincaillerie.validate` works as before. It now also reports a path that does not exist (`not found`) and fails, as Filaire's did.
- CI runs at two levels. On a commit (push to main, pull request): the tests not marked
  `slow` on Ubuntu and Python 3.12 only, and the engine checks on the varied batches only (the whole catalogue before a release). Before a release and with the "Run
  workflow" button: every test, platform and Python, the oldest OpenUSD and every
  preset, as before. `release.yml` runs that full level first and releases nothing
  unless it passes. Tests of 8 s or more are marked `slow` (`pytest -m "not slow"` runs
  the others).

### Fixed

- The nut-on-screw check (MuJoCo and Blender) puts the nut on a bolt (ISO 4014) a whole number of turns above where its thread starts, so that the two threads meet in phase; off phase they overlapped and the parts flew apart in Blender.
- The release workflow installs the package it has just built before writing the Blender add-on (`quincaillerie blender-addon`); since the release runs the full CI first, the command was missing.
- The drop check (MuJoCo) passes a part that keeps rolling when its vertical speed is under a fifth of its rolling speed: a cap screw on its side rolls on its round head and thread, whose crests lift it a little as they pass (an M6 cap screw failed at 1.3 mm/s while rolling at 11 mm/s).
- The output of a library material's colour texture is a `float3`, as UsdPreviewSurface specifies for `UsdUVTexture`; it was written as `color3f`.

## [0.5.0b1] - 2026-11-24 (beta)

### Added

- A Newton layer beside every file with physics, `<file>_newton.usda` (contract section 9,
  a new engine layer): `newton:contactGap` on every collider, from the contact offset the
  asset asks for, and `PhysicsArticulationRootAPI` on battery holders, whose joints Newton
  1.8 accepts only inside an articulation. The files and their PhysX layers are unchanged.
  `python -m quincaillerie.newton` checks the layers.
- `generate --engines LIST`: the engine layers to write (`physx`, `omniphysics`, `newton`,
  comma-separated, or `none`); by default all of them, as the four Primvaria generators do.

### Fixed

- Battery holders have their mass in `instances.csv` (`measured:mass_kg`, base and spring
  plate or clip); the column was empty.

## [0.4.0b1] - 2026-11-20 (beta)

### Breaking changes

- Every part's underside is at z = 0 of its file, as contract section 3
  says (PRV-40): screws stand on their heads (they were moved up by their
  head height), cylindrical cells, 9 V batteries and coin cells lie on their
  undersides (they were centred on their origin). Nuts, washers and holders
  already were. Referenced onto a floor at z = 0, a part now rests on it
  instead of starting inside it. The geometry, colliders, mate frames and
  centre of mass moved together; the values recorded are unchanged.
  `rest_pose` is now the identity for every part, `seated_overrides` puts a
  cell's underside on the bed, and the scenes and checks place nuts and
  washers by each screw's own head height (`scenes.under_head`).
- Mate frames follow the contract's section 8, measured by the new
  `tests/test_mate_frames.py` (PRV-35):
  - `MateFrame_drive` of a screw and of a nut is where a socket's mouth is
    when it holds the whole hex (under the head, under the nut), so the hex
    goes in along +Z by `quincaillerie:engagement`; it was on the end face.
  - A cylindrical cell's and a 9 V battery's `MateFrame_plus` and
    `MateFrame_minus` point +Z out of the battery, along its axis; they
    pointed up. A coin cell's already did.
  - A holder's `MateFrame_seat` is on its bed, +Z down into it, instead of at
    the seated cell's centre; every cell has its own `MateFrame_seat`, where
    it touches the bed. When the two coincide, the cell is in the pose the
    seated check simulates. The `cellCentre` attribute is gone.

### Changed values

- Values brought within their sources (PRV-33): an 18650 cell is 18.4 ×
  65.0 mm, 43.8 g (was 18.0 mm, 46 g, above the datasheet's maximum); a
  21700, 21.22 × 70.3 mm, 66.8 g (was 21.0 × 70.0, 68 g); a D cell 139 g
  (was 135); a C cell 66.2 g; a CR123A 16.5 g; a CR2032 3.0 g; a 9 V
  battery 45.6 g. Holders follow their cells' sizes.
- Tolerances drawn within each size's or format's own (`catalog.TOLERANCES`,
  `catalog.CELL_MIN`), from the same sources, instead of one range for
  all: across flats from s min to s (was 0 to −0.25 mm, beyond the
  standard for M3 to M6); head height from k min to k max (was 0 to
  −0.3 mm, beyond it for every size); nut height from m min to m; washer
  thickness within h's limits; screw length within its length class (was
  ±0.4 mm, beyond it for lengths up to 16 mm); a cell's diameter and length
  down to the datasheet's minimum (was 0.5 and 0.8 mm, beyond it for the
  18650). The same seed gives the same parts otherwise.
What an instance records is now what its geometry and colliders use (QUI-10).
The same seed gives the same parts, except for the cells' defects:

- A washer records the thickness change it really has (0.3 times what it
  recorded before); its geometry is unchanged.
- No longer recorded, as the part does not have them: a nut's `length_dmm`; a
  washer's `across_flats_dmm`, `length_dmm`, `clearance_mm`, `thread_class`,
  `defect_z` and `defect_angle_deg`; `defect_z` and `defect_angle_deg` of a
  bent screw and of an oval nut; `defect_z` of a corroded cell and of every
  coin and 9 V cell; `defect_angle_deg` of a 9 V cell.
- A corrosion crust takes its drawn size (`defect_size`, the same mean as
  before) and, on a round cell, its drawn angle.

### Changed

- README and docs images rendered again with the sourced values of PRV-33
  (cell sizes and masses, the draws within the standards' tolerances): the
  cells, the variation and the social preview renders, and the drop and
  insertion GIFs, simulated again. The drop GIF no longer shows the shared
  ground, which still collides, but the studio floor, as the stills do; the
  GIFs' default size is the published 640 × 360.
- The insertion check judges a cell by its own size: a cell shorter than
  nominal sits that much further along, and one thinner than nominal may be
  held by its contacts just above the bed. Cells now vary down to their
  datasheet's minimum, which the fixed nominal criteria refused.
- A dented cell's can collider follows the dent (convex pieces, fine where
  the dent is), and a corrosion crust has its own collider: both change how
  the cell rests and seats. `tests/test_physical_defects.py` checks it in
  MuJoCo: a ball rests lower in a dent, a cell stood on its crust falls over.
- The seating and insertion checks take the sound cells, as the screwing
  check takes the sound threads.
- `scripts/defect_demo.py` renders the three comparisons with MuJoCo on the CPU
  (sound and defective side by side: a nut on a crushed thread, a ball in a
  dent, a cell on its crust) into a video and an image.
- `docs/variation.md` lists no exception any more; the examples show a dash
  for a value a part does not have.

### Added

- `docs/sources.md` and `quincaillerie/sources.py`: every physical value
  names its source (a public table of ISO 4017, ISO 4032, ISO 7089; the
  manufacturer's datasheet of each cell; a handbook for densities, thread
  friction, fits and the spring wire), or is marked as an estimate with what
  it rests on. `tests/test_sources.py` fails on a value without a source,
  outside the range its source gives, or drawn outside it (PRV-33).
- The conformance check (shared by the four generators) checks that an asset
  is whole on its own (contract, section 4): every relationship or connection
  inside an asset root (a material binding, a physics material, a joint's
  bodies) points inside it, in every variant (PRV-40).
- The conformance check (`contract.conformance`, `python -m quincaillerie.conformance`,
  shared by the four generators) checks sections 7 and 8 of the contract: a
  variant set and its variants are named in `snake_case`, have a default
  selection, and the set is one section 7 lists, with its meaning, for the
  asset's generator (`contract.VARIANT_SETS`); no variant changes what identifies the asset (its `assetInfo`,
  `primvaria:*` identity and semantic labels), each variant being selected in
  turn on a copy of the stage; a mate frame is an `Xform` named `MateFrame` or
  `MateFrame_<feature>`, inside an asset, in every variant; nothing is written
  under `primvaria:mate:*`, which is not in the contract yet (PRV-35).
- `docs/variation.md`: how every drawn value is drawn, part by part, written
  from `quincaillerie/declared.py`; `tests/test_distributions.py` draws
  thousands of instances and checks that each column is declared, stays in its
  range and follows its distribution (PRV-34). The page also lists the
  recorded values that do not change the part as recorded (a nut's
  `length_dmm`, a washer's `across_flats_dmm` and `length_dmm`, a washer's
  `height_dmm` applied at 0.3 times its value, and the defect placement of
  cells, applied to a dent only).
- Reproducibility references (`tests/test_golden.py`, shared by the four
  generators): four cases of fixed preset, seed and options whose pack tables
  must give the same drawn and measured values on every Python and platform
  of the CI. Contract, section 6, rule 1 (PRV-32).

### Fixed

- The MuJoCo converter (`sim.mujoco_model.convert`) reads a body that only
  gives its mass, as a Granulaire grain does: MuJoCo works out its inertia
  from its colliders, instead of the schema's zero fallbacks, which MuJoCo
  refused (PRV-40).
- `generate --no-vary` refuses an unknown aspect, instead of ignoring it and
  letting every aspect vary (PRV-35).
- Cell labels are no longer stretched around the cell. Every label was drawn on
  one 2048 × 1024 image whatever the wrapper's proportions, so the print came
  out 1.6 to 3.8 times too tall around the cell (about twice on an AA or an
  18650, nearly four times on a C, a D or a CR123A, whose texts overlapped),
  and 1.25 times on the 9 V block. Each label now has the proportions of the
  surface it is printed on (`catalog.wrapper_span`, `catalog.label_9v_size`,
  which the meshes use too), and its texts shrink to fit the shorter wrappers.
  Visual only: geometry, colliders and masses are unchanged. README images
  rendered again.
- README images: loose parts rest on the floor. `scripts/readme_images.py`
  still lifted them by their half-height, though every asset rests on z = 0
  at its origin since PRV-40: AA cells floated 7.25 mm, 9 V blocks 8.75 mm,
  M10 screws about 0.5 mm, an LR44 2.7 mm, and a flipped CR2032 sank 1.6 mm
  into the floor. Each part is now put down by its lowest point.

## [0.3.0b1] - 2026-11-13 (beta)

### Breaking changes

- The PhysX schemas and attributes (`PhysxRigidBodyAPI`, `PhysxCollisionAPI`)
  are no longer in the files: they are a layer over each file,
  `assets/<part>_physx.usda` and `scene_physx.usda` (which references the
  layers of its parts), to open instead of the file in Isaac Sim (`physx.py`,
  `python -m quincaillerie.physx` to check a set). The files hold plain
  OpenUSD and `UsdPhysics` only. Each part says from which distance contacts
  should be generated in `quincaillerie:contactOffset`, which the Blender
  add-on reads for its margin (it read the PhysX attribute).
- `usd.physx_collision`, `usd.physx_body` and `usd.physx_tune` are removed.
- The thread clearance of a screw or a nut is drawn inside the usual fit, a 6g
  screw in a 6H nut, computed from the public formulas of the ISO metric
  thread tolerance system (`fits.py`), where it was drawn between 1.6 and 8 %
  of the pitch. The same seed gives other clearances than before;
  `--thread-play legacy` gives the former ones, exactly. Every other drawn
  value is unchanged.
- Pack files (Primvaria contract): `parts.csv` and `summary.json` are replaced by
  `instances.csv` and `manifest.json`, the same in the four generators. The
  table is read back from the OpenUSD files, one row per asset: identity,
  aspects, `variation:<name>` and `measured:<name>` columns, then the
  generator's own; the former summary is the manifest's `summary`.
- The drawn values of an instance are written as `primvaria:variation:<name>`
  attributes (Primvaria contract, variation model); the
  `quincaillerie:variation:<name>` attributes are gone. The names are
  unchanged.

### Added

- Semantic labels on every asset, with OpenUSD's `UsdSemantics.LabelsAPI`:
  `semantics:labels:class` (the kind of part (`screw`, `nut`, `washer`, `cell`, `holder`) and the catalogue entry (`ISO4017_M8x30`)) and
  `semantics:labels:instance` (the asset's name). `instances.csv` gains a
  `classes` column and `manifest.json` lists the classes of the pack; the
  conformance check requires the labels (`contract.write_labels`,
  `contract.labels`).
- `python -m quincaillerie.conformance` refuses engine data in a file (schemas and
  attributes of PhysX or OmniPhysics belong in an engine layer, contract
  section 9) and checks that an engine layer lies over the file it is named
  after and over nothing else. `contract.py` and `tests/test_contract.py`
  stay the same in the four generators.
- `--thread-play` (`generate(..., thread_play=)`): `class` (default, drawn in
  the 6g / 6H fit), `middle` (the middle of the fit for every instance,
  whatever the seed) or `legacy`. The fit is recorded as `thread_class`, in
  the files and in `instances.csv`.
- Defect rate and jam rate (`docs/jam-rate.md`, `scripts/jam_experiment.py`,
  data in `docs/jam_experiment.json`): on 40 M6 screws driven in MuJoCo, every
  crushed thread jams a nut and no sound, bent or burred screw does, so the
  jam rate is a third of `--defect-rate`. Tests protect the curve.
  `sim.checks.through()` drives a nut from the head of a screw to its tip.
- `examples/`: four short scripts, each explained by its own comments (a first
  pack and its ground truth, one aspect switched off, reading the files with
  OpenUSD alone, a nut screwed on in MuJoCo); a test runs each one.
- `--collider simple` (`generate(..., collider="simple")`): fasteners collide
  as their envelope alone, 2 pieces for a screw, 12 for a nut and 8 for a
  washer, where a threaded M8 × 30 screw takes 837. For scenes with many parts
  that only fall, pile up and are grasped; nothing screws or jams. The mesh,
  the mass and the drawn values are unchanged, and each file says which
  collider it has (`quincaillerie:collision`).
- `sim-test --scene`: the whole `scene.usda` of a set settles under gravity in
  MuJoCo. A scene of 100 screws, nuts and washers with simple colliders (303
  bodies) comes to rest in about 25 s.
- The scene lays instances out 25 to a row, on a floor that covers them all
  (it was one row per part on a 2 m floor).
- What was measured on each instance is written in the file as
  `primvaria:measured:<name>` (`mass_kg`, `colliders`).
- `python -m quincaillerie.conformance` also checks every pack it finds: the table must
  say what the files say. `pack.py` and `tests/test_pack.py` are shared by the
  four generators.
- Ground truth of the variation, in the file (Primvaria contract, variation
  model): `primvaria:variation:aspects`, the aspects that were switched on, and
  one `primvaria:variation:<name>` per drawn value (`clearance_mm`, `defect`, `rust`, `spring_factor`…).
  `python -m quincaillerie.conformance` requires the aspects on every asset.
- `CONTRIBUTING.md`, issue templates (bug report, part request),
  `SECURITY.md` and `CITATION.cff`.
- Primvaria OpenUSD contract, version 0
  ([docs/contract.md](https://github.com/drscaon/primvaria/blob/main/docs/contract.md)):
  every part is an asset any tool can find without knowing Quincaillerie: a model of kind `component` with `assetInfo` (name,
  identifier, version) and the attributes `primvaria:contract`,
  `primvaria:generator`, `primvaria:version`, `primvaria:preset` and
  `primvaria:seed`; in `scene.usda`, `/World` is an `assembly` that references them; `primvaria:preset` is the catalogue entry the instance was drawn from (`ISO4017_M8x30`).
- `python -m quincaillerie.conformance`: checks files against the contract (stage
  units, model hierarchy, identity). Run in the tests and, in CI, on every
  preset.

### Changed

- The README's table of outputs says that `instances.csv` holds each asset's classes, with a link to the
  semantic labels.
- The README is less than half its former length; the detail moved, unchanged,
  to `docs/`: `usage.md`, `openusd.md`, `physics.md`, `limits.md`,
  `development.md`.
  [primvaria.com/quincaillerie](https://primvaria.com/quincaillerie/) is built
  from these files.
- Continuous integration runs the checks shared by the four generators
  (Primvaria's reusable workflow).

## [0.2.0b1] - 2026-11-11 (beta)

### Breaking changes

- Python 3.11 or later (was 3.10): MuJoCo 4 requires it, and Python 3.10 reached
  its end of life in October 2026.
- `usd-core` 26.5 or later (was 24.0): the OpenUSD validators do not load from
  earlier wheels (25.5 lacks the validator libraries, 25.8 and 25.11 the
  UsdPreviewSurface definitions), and 24.x has no `UsdValidation` at all. A CI
  job runs the tests on exactly 26.5.
- MuJoCo 4 (`mujoco>=4.0`, was 3.2) for the `sim` and `dev` extras; MuJoCo 3 is no
  longer supported.
- The ground and physics scene are the same in every Primvaria project (`ground.py`, the
  same file in each): `/World/PhysicsScene`, gravity 9.81 m/s² along −Z; `/World/Ground`,
  a 2 cm box (`UsdGeom.Cube`) whose top is z = 0, covering the content with 0.5 m to
  spare, rendered, no PhysX attributes; `/World/GroundMaterial`, static friction 0.6,
  dynamic 0.5, restitution 0.1. A test checks every generated file against it.
  Quincaillerie's ground was `/World/ground` (lower case), hidden (purpose guide), with
  friction 0.4, no bounce and its material in `PhysicsMaterials/ground`; it is now
  `/World/Ground`, rendered (the README renders hide it, as Filaire's do).
  `scenes.new_scene()` lost its `floor_visible` argument.

### Added

- `python -m quincaillerie.validate FILE_OR_FOLDER`: every OpenUSD `UsdValidation` validator
  (what `usdchecker` runs) on each file and each variant; the tests and a CI job
  (every preset) require no error and no warning.

### Fixed

- UV primvar readers write `inputs:varname` as a `string`, as UsdPreviewSurface
  specifies (was a `token`).
- The material library layer has the stage metadata of the assets
  (meters, Z up, kilograms).

### Changed

- README: how the number of thread colliders weighs on engines that size their
  contact buffers in advance (measured in Newton), and what to do.
- README: the same header as the other Primvaria projects (PyPI and suite
  badges), an Engines table matching the suite's engine matrix, and links to
  primvaria.com.

## [0.1.0b3] - 2026-10-29 (beta)

First release on PyPI.

### Changed

- Released on PyPI (`pip install quincaillerie`) by the release workflow, through Trusted Publishing.
- README images and links use absolute URLs, so that they show on PyPI; the README links to Primvaria, the suite the project belongs to.

## [0.1.0b2] - 2026-10-27 (beta)

Second beta: varied instances.

### Added
- Variation: `--count N` now writes N distinct instances of each part, each
  drawn from four independent aspects: tolerance (thread fit, dimensions,
  holder play), defect (crushed thread, bent shank, burr, oval or crushed
  nut, dished washer, dented can, corroded terminal; `--defect-rate`), wear
  (rust, oil, grime, scratches, scuffed labels, baked into per-instance
  textures, with the matching friction) and physics (alloy density,
  friction, spring stiffness and fatigue, clip torque, cell mass).
  `--no-vary`, `--nominal`; the same seed gives the same parts.
- Ground truth: every drawn value in `parts.csv` and as
  `quincaillerie:variation:*` attributes; worn parts keep the clean finishes
  in their variant set.
- `quincaillerie sim-test --defects`: a sound nut driven with a light torque
  must stop at the crushed thread of a screw. Insertion checks use what each
  holder and cell were drawn with.
- `--detail low|normal|high` for the visual meshes.
- README: variation section, a render of varied instances and an animation
  of a nut stopping on a crushed thread.

### Changed
- `--count` used to place copies of one file; `--nominal` keeps that.
- Default visual mesh of threaded parts lighter (`normal`, 3.4 MB for an
  M8 × 30 screw instead of 7.5 MB, `high` as before).

## [0.1.0b1] - 2026-10-27 (beta)

First beta.

### Added
- Metric fasteners, M3 to M12, coarse pitch: hex head screws (ISO 4017, fully
  threaded, any length), hex nuts (ISO 4032), plain washers (ISO 7089), with
  the ISO 68-1 thread profile in the visual mesh and convex collision pieces
  that follow the helix (one per 10°, 0.05 mm radial clearance), so that a
  nut screws on in simulation. Six finishes as a variant set.
- Battery cells and their holders: AAA, AA, C, D, CR123A, 18650, 21700 in
  cradles with a coil spring; the 9 V block in a keyed terminal holder;
  CR2032 and LR44 under a hinged leaf-spring clip. Springs and clips are
  UsdPhysics prismatic and revolute joints whose drives are designed from the
  contact force and preload. The underside of a holder is at z = 0.
- OpenUSD export: one rigid body per moving part with one visual mesh, mass,
  centre of mass and principal inertia from the meshes, physics materials,
  mate frames, PhysX attributes for Isaac Sim; a shared material library
  (UsdPreviewSurface + MaterialX, procedural textures, generic cell labels).
- `quincaillerie generate` with related elements (`--with nut,washer`,
  `--with holder`), a scene with `--count` copies of each part at rest on a
  floor plus the assemblies, `--no-physics` for visual-only assets,
  `parts.csv` and `summary.json`; `generate all` for the whole catalogue.
- MuJoCo checks read from the OpenUSD files (`quincaillerie sim-test`):
  drop, nut on screw, empty holder, seated cell, insertion both ways (spring
  compression and contact force against the design, keying of the 9 V), and
  screwing (advance per turn against the pitch).
- Blender add-on (`quincaillerie blender-addon`): rigid bodies, compound
  colliders, masses, friction, Generic Spring constraints and coil drivers
  set up on every File > Import > USD; the same file runs as a script.
  `quincaillerie blender-test` runs the gravity checks in Blender through it.
- README with results, Blender renders, three animations (drop in Blender,
  screwing and insertion in MuJoCo), logo and GitHub social preview; scripts
  to rebuild them.
- Test suite (pytest), lint and format (ruff), continuous integration with the
  MuJoCo and Blender checks of the whole catalogue, release workflow with the
  Blender add-on attached, Dependabot, GitHub Flow `pre-push` hook.
