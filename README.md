<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/logo-dark.svg">
    <img alt="Quincaillerie" src="https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/logo.svg" width="420">
  </picture>
</h1>

<p align="center"><strong>Standard hardware assets generator for Physical AI.</strong></p>

<p align="center">
  <a href="https://github.com/drscaon/quincaillerie/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/drscaon/quincaillerie/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://pypi.org/project/quincaillerie/"><img alt="PyPI" src="https://img.shields.io/pypi/v/quincaillerie"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-3776AB">
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green">
  <a href="https://primvaria.com"><img alt="Part of Primvaria" src="https://img.shields.io/badge/suite-Primvaria-0f6e74"></a>
</p>

Quincaillerie (French for *hardware*, the nuts and bolts kind) generates
metric **screws, nuts and washers with modelled threads**, and **battery
cells with the holders they go in**, and exports them to **OpenUSD** as
physics-ready assets: rigid bodies with real masses and inertias, convex
collision pieces that follow the thread's helix, and holders whose spring or
clip is a `UsdPhysics` joint with a drive. A nut screws onto its screw, one
pitch per turn; a cell pushed into its holder compresses the spring with the
force it was designed for, and a 9 V battery put in backwards does not fit.

**No two parts are the same.** A real box of M8 screws is not one screw a
hundred times: some threads fit tighter than others, a few are damaged, some
are rusty or oily, springs get tired. Quincaillerie draws every instance from
those distributions: tolerances, defects, wear and physics, each with its
own random stream, and writes what it drew into the file and into a CSV, as
ground truth. The variation is not paint: a crushed thread really stops a
nut, a tired spring really presses less, a rusty screw really has more
friction.

The assets are checked in **MuJoCo** and in **Blender**: dropped on a floor,
assembled, screwed, inserted, without coming apart. A Blender add-on sets the
rigid bodies and constraints up by itself when a file is imported, so that
pressing Play just works.

It is built for **Physical AI**: robots that assemble, sort, screw and swap
batteries are trained and tested in simulation, and they need small parts with
exact geometry and physics, not a cylinder named "bolt". Everything can run on
CPU. Quincaillerie is part of [**Primvaria**](https://primvaria.com), with
[Granulaire](https://github.com/drscaon/granulaire) (granular assets),
[Maillage](https://github.com/drscaon/maillage) (textiles) and
[Filaire](https://github.com/drscaon/filaire) (cables), and follows the same
approach: distributions instead of one shape, measured outputs, honest limits.

![Screws, washers and nuts M3 to M12 in six finishes, rendered in Blender](https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/fasteners.jpg)

*ISO 4017 screws, ISO 7089 washers and ISO 4032 nuts, M3 to M12, in the six
finishes of the material library. The nuts sit on the thread at the height
their rotation gives them; the loose parts in front were dropped in MuJoCo
and rest where they fell. Imported from the OpenUSD files into Blender and
rendered with Cycles.*

## Every instance is different

![Ten instances of an M10 screw, nut and washer, eight AA cells and three 9V blocks, each drawn with its own variation](https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/variation.jpg)

*`quincaillerie generate screw M10 --with nut,washer --count 10` and the same
for AA and 9 V cells: each part is a distinct file. Rust, grime, oil and
scratches; scuffed and faded labels; a dished washer, oval and crushed nuts,
crushed and bent screws (not all visible from here); and, invisible in a
picture, a different thread fit, alloy density, friction and spring for each.*

| Aspect | Fasteners | Cells | Holders |
|---|---|---|---|
| **tolerance** | thread clearance per side within the fit class: 6g for screws, 6H for nuts (at M8: 0.015–0.075 mm and 0.015–0.080 mm, see [Thread fit](https://github.com/drscaon/quincaillerie/blob/main/docs/physics.md#thread-fit)), across flats, head and nut height, length | diameter and length under nominal, within the IEC bands | side play of the cradle (0–0.6 mm) |
| **defect** (`--defect-rate`, 15 %) | crushed thread (crests pushed sideways over 40–140°: jams a nut), bent shank (0.8–3°), burr at the tip; oval or crushed nut; dished washer | dented can, corroded terminal (crust) | |
| **wear** | new, used, oily, rusty, dirty: rust, oil, grime and scratches baked into the instance's own textures; friction follows (rust ×1.8 at most, oil ×0.6) | scuffed and faded label, grime | grey or black ABS |
| **physics** | density of the alloy (brass and stainless are solid alloys, the rest plated steel), friction | mass ±3 %, friction | spring stiffness ±8 %, tired springs (preload down to 70 %), clip torque ±10 %, friction |

Each aspect has its own random stream: `--no-vary wear` keeps the same
tolerances and defects with clean parts; the same seed gives the same parts.
Everything drawn is in `instances.csv` and in each file as
`primvaria:variation:*` attributes; the clean finishes stay available in
the `finish` variant set of a worn part. `--nominal` gives the reference part.

![The same nut driven onto a sound M12 screw and onto one with crushed threads](https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/jam.gif)

*The defects are physical. The same nut, the same light torque (a hand on a
nut driver), simulated in MuJoCo from the files: it runs down the sound
screw (left) and stops at the crushed thread of the other (right).
`quincaillerie sim-test --defects` checks this for every crushed screw of a
batch.*

Only crushed threads jam a nut: one screw in three with a defect, so the jam
rate is a third of `--defect-rate` (5 % at the default 15 %). Measured on 40
screws: [Defect rate and jam rate](https://github.com/drscaon/quincaillerie/blob/main/docs/jam-rate.md).

## The physics, in motion

| Dropped in Blender | Screwed in MuJoCo | Inserted in MuJoCo |
|---|---|---|
| ![Assemblies and parts dropped on the floor in Blender](https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/drop.gif) | ![A nut driven down an M10 screw](https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/screwing.gif) | ![An AA cell and a CR2032 pushed into their holders](https://raw.githubusercontent.com/drscaon/quincaillerie/main/docs/images/insertion.gif) |
| Two screw + washer + nut assemblies, an AA cell in its holder and loose parts, imported with File > Import > USD (add-on enabled) and dropped: Blender's rigid bodies, nothing set by hand. The nuts stay on their threads, the cell stays in its holder. | A nut driven by a torque on an M10 screw: it advances 1.5 mm per turn on the modelled thread, the washer waits below. | An AA cell and a CR2032 carried into their holders and released: the spring plate slides back and the coil compresses, the clip lifts and holds the coin cell. |

All three are rendered in Blender (Cycles) from the generated OpenUSD files:
[`scripts/physics_gifs.py`](https://github.com/drscaon/quincaillerie/blob/main/scripts/physics_gifs.py).

## What it does

- **Fasteners**, metric coarse thread, M3 to M12: hex head screws (ISO 4017,
  fully threaded, any length), hex nuts (ISO 4032), plain washers (ISO 7089).
  The visual mesh carries the ISO 68-1 thread profile; the collision is a
  core cylinder plus one convex piece per 10° of helix (≈ 800 per screw, 200
  per nut) with 0.05 mm of radial clearance, so a nut really screws on.
  Six finishes as a variant set: clear and yellow zinc, black oxide,
  stainless A2, plain steel, brass.
- **Cells and holders**: AAA, AA, C, D, CR123A, 18650, 21700 in cradles with
  a coil spring; the 9 V block in a holder whose terminal slots are keyed;
  CR2032 and LR44 under a hinged leaf-spring clip. The spring stiffness and
  wire come from the contact force and preload (k = G d⁴ / 8 D³ n); the clip
  torsion from the force at its lever arm.
- **Variation**: `--count N` distinct instances of each part, with drawn
  tolerances, defects, wear and physics (see above), and their ground truth.
- **Related elements** on request (`--with`): a screw with its nut and
  washer, a cell with its holder, and a scene with every instance resting on
  a floor, plus the assemblies (made of instances without defects).
- **OpenUSD**: one file per part, one rigid body per moving part with *one*
  visual mesh (so every DCC imports one object per body), mass, centre of
  mass and principal inertia, convex collision shapes, physics materials,
  joints with drives, mate frames (thread axis, drive, terminals, cell seat),
  PhysX attributes for Isaac Sim. A shared material library in
  UsdPreviewSurface and MaterialX.
- **Checks** (`quincaillerie sim-test`, `quincaillerie blender-test`): the
  same scenes, read back from the files, in MuJoCo and in Blender.
- **A Blender add-on** (`quincaillerie blender-addon`): rigid bodies and
  constraints set up on every USD import.
- `--no-physics` for visual-only assets.

## Engines

Every file is OpenUSD with standard `UsdPhysics` schemas. Where each engine
stands, as on the [Primvaria engine matrix](https://primvaria.com/#engines):

| Engine | Status |
|---|---|
| OpenUSD validators (`usdchecker`) | **tested**: every part of the catalogue and varied instances, in CI |
| Blender | **tested**: drop and assemblies through the add-on (`quincaillerie blender-test`) |
| MuJoCo | **tested**: drop, screwing, jammed threads, insertion (`quincaillerie sim-test`) |
| NVIDIA Isaac Sim (PhysX) | not tested yet (needs an NVIDIA RTX GPU); `UsdPhysics` and PhysX attributes |

## Installation

From PyPI:

```bash
pip install "quincaillerie[sim]"
```

From a clone, for development:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[sim]"            # add ",dev" for tests and linting, ",materialx" for the .mtlx file
```

Requires Python 3.11+. Dependencies: NumPy, SciPy, Pillow and the OpenUSD
bindings (`usd-core` 26.5+); MuJoCo for the checks. The Blender checks need Blender
as a Python module (`pip install bpy`, Python 3.13) or a Blender executable.

Earlier `usd-core` wheels generate the same files, but their OpenUSD
validators do not load (25.5 ships without the validator
libraries, 25.8 and 25.11 without the UsdPreviewSurface definitions), and CI
tests both 26.5 and the newest release.

## Usage

```bash
quincaillerie list                                          # sizes, formats, finishes
quincaillerie generate screw M8 --length 30 --with nut,washer --count 100
quincaillerie generate cell 18650 --with holder --count 20 --defect-rate 0.3
quincaillerie generate screw M8 --count 50 --no-vary wear   # clean parts, varied fits and defects
quincaillerie generate nut M10 --nominal                    # the reference part
quincaillerie generate holder 9V --with cell --no-physics   # visuals only
quincaillerie generate all --nominal                        # the whole catalogue (41 assets)
quincaillerie sim-test output/ISO4017_M8x30 --defects       # MuJoCo checks (+ crushed threads jam)
quincaillerie blender-test output/catalog                   # the same in Blender
quincaillerie blender-addon                                 # quincaillerie_physics.zip
```

`python -m quincaillerie ...` works too. From Python:

```python
from quincaillerie import generate, resolve

parts = resolve("screw", "M6", length=25, with_=["nut", "washer"])
generate(parts, "output", count=100, defect_rate=0.2)  # -> output/ISO4017_M6x25/
generate(parts, "output", vary=("tolerance", "physics"))  # clean, undamaged, varied fits
```

Four short scripts in [`examples/`](https://github.com/drscaon/quincaillerie/tree/main/examples)
show the rest, each explained by its own comments: a first pack and its
ground truth, one aspect switched off, reading the files with OpenUSD alone,
and a nut screwed on in MuJoCo.

## Outputs (under `output/<set>/`)

| File | Content |
|---|---|
| `assets/*.usdc`, `assets/*.usda` | one file per instance, `ISO4017_M8x30_007.usdc` (Blender: File > Import > USD) |
| `materials/` | `quincaillerie_materials.usda` (UsdPreviewSurface + MaterialX), `.mtlx`, textures; `instances/`: the baked textures of worn instances |
| `scene.usda` | every instance on the shared ground (see below), plus the assemblies |
| `instances.csv` | one row per instance, read back from the files: its identity, **every drawn value** (`variation:<name>`) and **every measured value** (`measured:<name>`), then its kind, size or format: the ground truth |
| `manifest.json` | what the pack is (contract, generator, version, preset, seed, aspects, files) and its summary: counts by kind and by defect, the options used |
| `sim_test/` | test scenes and reports (`sim-test`, `blender-test`) |

## Limits

The short version; the full list is in [Limits and roadmap](https://github.com/drscaon/quincaillerie/blob/main/docs/limits.md).

- Dimensions are nominal, from public tables; variation ranges are plausible
  orders of magnitude, **not measured distributions**.
- A thread is about 1000 convex pieces: exact enough to screw, heavy for
  large scenes. `--collider simple` is light, but then nothing screws or jams.
- Holders are generic designs, with no electrical contact model.
- Checked in MuJoCo and Blender; **not tested in Isaac Sim yet**.

## Development

```bash
git clone https://github.com/drscaon/quincaillerie.git && cd quincaillerie
pip install -e ".[dev]"
pytest
```

Conventions and continuous integration: [Development](https://github.com/drscaon/quincaillerie/blob/main/docs/development.md).

## Documentation

| Page | What it holds |
|---|---|
| [Usage in depth](https://github.com/drscaon/quincaillerie/blob/main/docs/usage.md) | Every option of `quincaillerie generate` and the catalogue of sizes and cell formats. |
| [OpenUSD layout and contract](https://github.com/drscaon/quincaillerie/blob/main/docs/openusd.md) | How a part is laid out in its file, the ground and physics scene, OpenUSD compliance, and what the Primvaria contract writes on every instance. |
| [Physics: fits, colliders and checks](https://github.com/drscaon/quincaillerie/blob/main/docs/physics.md) | The thread fit classes, thread and simple colliders, the Blender add-on, and the MuJoCo and Blender checks with their results. |
| [Defect rate and jam rate](https://github.com/drscaon/quincaillerie/blob/main/docs/jam-rate.md) | Which defects stop a nut, measured on 40 screws in MuJoCo, and the resulting curve. |
| [Limits and roadmap](https://github.com/drscaon/quincaillerie/blob/main/docs/limits.md) | Everything Quincaillerie does not do or has not verified, stated plainly, and what comes next. |
| [Development](https://github.com/drscaon/quincaillerie/blob/main/docs/development.md) | Branch and release conventions, how the README images are made, continuous integration. |

## License

[MIT](https://github.com/drscaon/quincaillerie/blob/main/LICENSE) © 2026 Daniel Régis Sarmento Caon

The logo is drawn from DejaVu Sans Bold outlines (Bitstream Vera license),
converted to paths, so it displays without the font installed.

---

Quincaillerie is part of [**Primvaria**](https://primvaria.com), physics-ready variability for Physical AI, in OpenUSD: `pip install primvaria` installs the whole suite ([source](https://github.com/drscaon/primvaria)).
