# Limits and roadmap

Everything Quincaillerie does not do or has not verified, stated plainly, and what comes next.

Part of the [Quincaillerie](../README.md) documentation.

## Limits

- **Nominal, not measured.** Fastener dimensions come from public tables,
  not from the standards; cell masses and spring forces are typical. Screws
  are fully threaded (no plain shank) and have no chamfer under the head.
- **Plausible variation, not measured distributions.** The ranges (fits,
  defect sizes, wear, spring scatter) are realistic orders of magnitude, not
  statistics of a production line. Dents and corrosion crusts are visual
  only; crushed threads, bends, burrs, oval nuts and dished washers change
  the collision too.
- **Collision in pieces.** A thread is ≈ 1000 convex pieces: exact enough to
  screw, heavy for large scenes (a scene of 100 screws is 100 000 shapes).
  Engines that size their contact buffers in advance feel it first: loaded in
  [Newton](https://github.com/newton-physics/newton) (CPU), a scene of 3 M8
  screws, nuts and washers (4 224 shapes) filled its default buffer of
  210 600 contacts and the washers fell through the floor; with 400 000
  they rest, the buffer still full. Raise the engine's contact limits for
  threaded parts, keep them few per scene, or generate the parts that only
  need to fall, pile up and be grasped with `--collider simple`.
- **Simple colliders do not screw or jam.** With `--collider simple` a nut
  slides freely over a shank and a crushed thread no longer stops it: the
  defect is still drawn, recorded and visible, but it is not physical. Bent
  shanks, oval nuts and dished washers keep their effect.
- **Simplified holders.** Generic designs (ABS boxes, a flat spring plate),
  not a product; no electrical contact model.
- **Blender springs start at rest.** See [Blender](physics.md#blender): a cell placed
  already seated is not pressed by the spring.
- **Isaac Sim not tested here.** The files follow the standard `UsdPhysics`
  schemas and carry PhysX attributes, but have not been loaded in Isaac Sim
  (no NVIDIA GPU); drive units and contact offsets may need adjusting there.

## Roadmap

1. Tools that go with the parts: screwdriver bits and screwdrivers, hex keys
   and wrenches matched to the drives (`--with tool`), and tapped bases.
2. More fasteners: socket head cap screws (ISO 4762), countersunk and pan
   head screws, partially threaded shanks, lock and spring washers.
3. A PhysX test in Isaac Sim; CAD export (STEP) of the same parametric parts.
4. Assembly tasks: torque, misalignment tolerances, success labels.
