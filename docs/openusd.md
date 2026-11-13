# OpenUSD layout and contract

How a part is laid out in its file, the ground and physics scene, OpenUSD compliance, and what the Primvaria contract writes on every instance.

Part of the [Quincaillerie](../README.md) documentation.

## OpenUSD layout

Z up, metres, kilograms; each asset's root prim is its default prim.

```
/ISO4017_M8x30                 Xform, RigidBodyAPI, MassAPI, quincaillerie:* attributes, variant set "finish"
  /Visual/ISO4017_M8x30_mesh   one mesh, GeomSubset per material
  /Collision/core, head, thread_0000 …   Cylinder / convexHull meshes, purpose guide
  /MateFrame_thread, /MateFrame_drive    +Z = screwing axis; hex drive across flats
  /Looks, /PhysicsMaterials

/Holder_AA
  /base                        RigidBodyAPI (ABS mass), Visual/Holder_AA_base_mesh, Visual/spring_coil, Collision/…
  /spring_plate                RigidBodyAPI, Visual, Collision/minus_plate
  /Joints/spring               PrismaticJoint base -> spring_plate, linear drive = the coil spring (N/m)
```

The underside of a holder is at z = 0 of the asset: it sits on a floor where
it is placed. Angular drives use UsdPhysics units (per degree). The root of
each part says from which distance contacts should be generated, in metres
(`quincaillerie:contactOffset`: 0.1 mm for a threaded part, below twice the
thread clearance; 0.5 mm for cells and holders). It is a request to the
engine, not an engine setting: the Blender add-on takes a tenth of it as its
collision margin, and the PhysX layer copies it.

## PhysX layer

The files hold plain OpenUSD (`UsdGeom`, `UsdShade`, `UsdPhysics`) and
nothing specific to an engine. What only PhysX reads is written beside each
file as a layer over it: `assets/<part>_physx.usda` and `scene_physx.usda`.

| On | Schema | Fasteners | Cells and holders |
|---|---|---|---|
| every rigid body | `PhysxRigidBodyAPI` | 32 position and 4 velocity solver iterations, depenetration velocity capped at 0.05 m/s, no CCD | 16 and 4 iterations, 0.1 m/s, no CCD |
| every collider but the ground | `PhysxCollisionAPI` | contact offset 0.1 mm, rest offset 0 | contact offset 0.5 mm, rest offset 0 |

A layer has its file as its only sublayer and holds `over`s only, so opening
it (Isaac Sim: File > Open) gives the file with these settings, and the file
alone is still complete for every other engine. The scene's layer repeats
nothing: it references the layer of each part on top of the part.
`python -m quincaillerie.physx <folder>` checks the layers of a set; the
OpenUSD validators run on them in CI. Not simulated: see
[Limits](limits.md#limits).

## Ground and physics scene (the same in every Primvaria project)

Every file with physics carries the same two prims, so that assets from
different generators can share one scene and every engine gets the same floor:

| Prim | What it is |
|---|---|
| `/World/PhysicsScene` | gravity 9.81 m/s² along −Z |
| `/World/Ground` | a static box (`UsdGeom.Cube`, `CollisionAPI`), its top face at z = 0, 2 cm thick, covering the content with 0.5 m to spare on each side (1 m × 1 m at least), grey and rendered, no PhysX attributes (engines derive their contact offsets) |
| `/World/GroundMaterial` | its physics material: static friction 0.6, dynamic friction 0.5, restitution 0.1, a wooden or concrete floor |

The code is one file, `ground.py`, identical in Granulaire, Maillage, Filaire
and Quincaillerie; a test checks every generated file against it. The MuJoCo
checks and the Blender rigid-body checks take the ground's friction from the
file (Blender's cloth, in Maillage, has its own collision settings).

## OpenUSD compliance

```bash
python -m quincaillerie.validate output/catalog
```

This runs every validator of OpenUSD's `UsdValidation` registry on each file,
the checks `usdchecker` runs: composition, stage metadata (meters, Z up),
geometry, material bindings, shaders, UsdPhysics rigid bodies and colliders,
joints and articulations. Each file is checked once per variant (every
finish), since a variant that is not selected is not composed. The tests and
CI require no error and no warning, on every part of the catalogue and on
varied, worn and defective instances.

MaterialX networks (`ND_*` shaders) are checked by these validators only with
an OpenUSD build that has its MaterialX plugin; the `usd-core` wheels from
PyPI have none, so this check is skipped there. The `.mtlx` document is
validated against the MaterialX standard library when the `materialx` extra is
installed.

## Primvaria contract

```bash
python -m quincaillerie.conformance output/catalog
```

Quincaillerie is part of [Primvaria](https://primvaria.com) and follows its
[mission](https://github.com/drscaon/primvaria/blob/main/MISSION.md) and its
[OpenUSD contract](https://github.com/drscaon/primvaria/blob/main/docs/contract.md),
version 0, which the four generators share. Every part is an asset any tool can find without knowing Quincaillerie: a model of kind
`component` with `assetInfo` (name, identifier, version) and the attributes
`primvaria:contract`, `primvaria:generator`, `primvaria:version`,
`primvaria:preset` and `primvaria:seed`; in `scene.usda`, `/World` is an `assembly` that references them; `primvaria:preset` is the catalogue entry the instance was drawn from (`ISO4017_M8x30`). The command above checks
the stage units, the model hierarchy and this identity; the tests and CI
require it on every preset.

What was drawn for each instance is in the file too, its ground truth:
`primvaria:variation:aspects` lists the aspects that were switched on
(`tolerance`, `defect`, `wear`, `physics`) and `primvaria:variation:<name>` holds each drawn value
(the `variation:*` columns of `instances.csv`, under the same names: `clearance_mm`, `defect`, `rust`, `spring_factor`…). An aspect that is switched off is still recorded, at its
nominal value, and the other aspects keep their draws.

What was measured on each instance once generated is there as well, as
`primvaria:measured:<name>` (`mass_kg`, `colliders`).
The pack's `instances.csv` is read back from the OpenUSD files, one row per
asset with the same names (`variation:<name>`, `measured:<name>`), and
`manifest.json` says what the pack is; both have the same shape in the four
generators, and the command above fails when the table and the files disagree.

Each part also says what it is with OpenUSD's own semantic labels
(`UsdSemantics.LabelsAPI`), which renderers such as Isaac Sim turn into
segmentation masks: `semantics:labels:class` holds the kind of part (`screw`, `nut`, `washer`, `cell`, `holder`) and the catalogue entry (`ISO4017_M8x30`), and
`semantics:labels:instance` the asset's name. In a scene, the instance label is the name of the prim that places the part. The classes are a
column of `instances.csv` and are listed in `manifest.json`.
