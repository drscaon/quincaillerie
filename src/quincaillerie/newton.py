"""Newton settings, as an OpenUSD layer over a file.

The main files hold plain OpenUSD and the standard `UsdPhysics` schemas. What Newton needs and
cannot guess from them is written here, in `<file>_newton.usda`: a layer whose only sublayer is
the main file and which adds, as `over`s:

* every collider but the shared ground: `newton:contactGap`, the distance from which contacts are
  generated, equal to the contact offset the asset asks for (`quincaillerie:contactOffset` on its
  root, as in the PhysX layer). Newton's own default, 0.1 m, is meant for robots and floods its
  contact buffer with parts this small;
* every asset whose joints are not in an articulation (a battery holder's spring plate or clip):
  `PhysicsArticulationRootAPI` on its root. UsdPhysics simulates such joints as constraints;
  Newton 1.8 accepts only joints that belong to an articulation.

A scene references its parts: its layer references the layer of each part on top of the part.
Open the layer instead of the file to get both. Engines other than Newton ignore it.

    python -m quincaillerie.newton output/ISO4017_M8x30     # check the layers of a pack

The check here is structural; Primvaria's CI opens the layers in Newton (scripts/newton_check.py).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from . import physx

SUFFIX = "_newton"
GROUND = physx.GROUND
GAP = "newton:contactGap"
_F = Sdf.ValueTypeNames


def overlay_path(usd: Path) -> Path:
    return Path(usd).with_name(f"{Path(usd).stem}{SUFFIX}.usda")


def _loose_joints(prim) -> bool:
    """Whether an asset has joints of its own and no articulation."""
    inside = list(Usd.PrimRange(prim))
    return any(p.IsA(UsdPhysics.Joint) for p in inside) and not any(
        p.HasAPI(UsdPhysics.ArticulationRootAPI) for p in inside
    )


def _tune(prim) -> None:
    """The Newton opinions of one prim, written at the current edit target."""
    if prim.HasAPI(UsdPhysics.CollisionAPI) and prim.GetPath() != GROUND:
        prim.CreateAttribute(GAP, _F.Float).Set(physx._contact_offset(prim))


def _layered_references(prim, folder: Path) -> list[str]:
    """The files a prim references that have a Newton layer of their own: the paths of those layers."""
    listed = prim.GetMetadata("references")
    out = []
    for ref in listed.GetAddedOrExplicitItems() if listed else ():
        if ref.assetPath and overlay_path(folder / ref.assetPath).exists():
            out.append(overlay_path(Path(ref.assetPath)).as_posix())
    return [p if p.startswith(".") else f"./{p}" for p in out]


def write_overlay(usd) -> Path:
    """Write `<file>_newton.usda` beside an OpenUSD file and return its path."""
    usd = Path(usd)
    out = overlay_path(usd)
    out.unlink(missing_ok=True)
    layer = Sdf.Layer.CreateNew(str(out))
    layer.subLayerPaths.append(f"./{usd.name}")
    stage = Usd.Stage.Open(layer)
    base = Usd.Stage.Open(str(usd))
    UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.GetStageMetersPerUnit(base))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.GetStageUpAxis(base))
    UsdPhysics.SetStageKilogramsPerUnit(stage, UsdPhysics.GetStageKilogramsPerUnit(base))
    root = base.GetDefaultPrim()
    stage.SetDefaultPrim(stage.GetPrimAtPath(root.GetPath()))
    holders = []
    walk = iter(Usd.PrimRange(stage.GetPseudoRoot()))
    for prim in walk:
        layers = _layered_references(prim, usd.parent)
        if layers:  # a part of a scene: its own layer already says it all
            for path in layers:
                prim.GetReferences().AddReference(path, position=Usd.ListPositionFrontOfPrependList)
            walk.PruneChildren()
            continue
        if prim.HasVariantSets():
            holders.append(prim)
        if not physx._in_variant(prim):
            _tune(prim)
    top = stage.GetPrimAtPath(root.GetPath())  # composed with the parts' layers, in a scene
    if _loose_joints(top):
        UsdPhysics.ArticulationRootAPI.Apply(top)
    session = stage.GetSessionLayer()
    for holder in holders:  # what a variant brings: written inside that variant
        sets = holder.GetVariantSets()
        for name in sets.GetNames():
            vset = sets.GetVariantSet(name)
            for variant in vset.GetVariantNames():
                with Usd.EditContext(stage, session):
                    vset.SetVariantSelection(variant)
                with Usd.EditContext(stage, vset.GetVariantEditTarget(layer)):
                    for prim in Usd.PrimRange(holder):
                        if physx._in_variant(prim, f"{{{name}={variant}}}"):
                            _tune(prim)
    session.Clear()
    layer.Save()
    return out


def check(path) -> list[str]:
    """Structural problems of a Newton layer (empty: none)."""
    path = Path(path)
    layer = Sdf.Layer.FindOrOpen(str(path))
    stem = path.stem.removesuffix(SUFFIX)
    main = next((path.with_name(stem + ext) for ext in (".usdc", ".usda") if path.with_name(stem + ext).exists()), None)
    if main is None:
        return [f"no file {stem}.usdc or {stem}.usda beside it"]
    if list(layer.subLayerPaths) != [f"./{main.name}"]:
        return [f"its only sublayer must be ./{main.name}"]
    problems = []
    base = Usd.Stage.Open(str(main))
    if any(a.GetName().startswith("newton:") for p in base.Traverse() for a in p.GetAttributes()):
        problems.append(f"{main.name} holds Newton data itself")
    stage = Usd.Stage.Open(str(path))
    base_paths = {p.GetPath() for p in Usd.PrimRange.AllPrims(base.GetPseudoRoot())}
    extra = [p.GetPath() for p in Usd.PrimRange.AllPrims(stage.GetPseudoRoot()) if p.GetPath() not in base_paths]
    if extra:
        problems.append(f"defines prims the file does not have: {extra[0]}")
    for prim in stage.Traverse():
        collider = prim.HasAPI(UsdPhysics.CollisionAPI) and prim.GetPath() != GROUND
        gap = prim.GetAttribute(GAP).Get() if prim.HasAttribute(GAP) else None
        if collider != (gap is not None):
            problems.append(f"{prim.GetPath()}: collider and {GAP} do not go together")
        elif gap is not None and not gap > 0:
            problems.append(f"{prim.GetPath()}: {GAP} must be positive")
    for joint in (p for p in stage.Traverse() if p.IsA(UsdPhysics.Joint)):
        up = joint.GetParent()
        while up and not up.IsPseudoRoot() and not up.HasAPI(UsdPhysics.ArticulationRootAPI):
            up = up.GetParent()
        if not up or up.IsPseudoRoot():
            problems.append(f"{joint.GetPath()}: a joint outside an articulation")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check the Newton layers (*_newton.usda) of packs or files.")
    ap.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args(argv)
    files = []
    for p in args.paths:
        files += sorted(p.rglob(f"*{SUFFIX}.usda")) if p.is_dir() else [p]
    if not files:
        print("no Newton layer found")
        return 1
    bad = 0
    for f in files:
        problems = check(f)
        bad += bool(problems)
        print(f"{'FAIL' if problems else 'ok  '} {f}")
        for line in problems[:10]:
            print(f"     {line}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
