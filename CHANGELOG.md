# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Breaking changes

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
