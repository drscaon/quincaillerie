# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
