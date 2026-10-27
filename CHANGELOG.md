# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
