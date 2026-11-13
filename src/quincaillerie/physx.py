"""PhysX settings (Isaac Sim), as an OpenUSD layer over a file.

The main files hold plain OpenUSD: `UsdGeom`, `UsdShade` and the standard `UsdPhysics`
schemas, which every engine reads. What only PhysX reads is kept out of them and written
here, in `<file>_physx.usda`: a layer whose only sublayer is the main file and which adds,
as `over`s, the PhysX schemas and attributes:

* every rigid body: `PhysxRigidBodyAPI` with the solver iteration counts and a cap on the
  depenetration velocity (a thread needs more iterations and a lower cap than a cell);
* every collider but the shared ground: `PhysxCollisionAPI` with the contact offset the asset
  asks for (`quincaillerie:contactOffset` on its root) and a rest offset of 0.

A scene references its parts: its layer does not repeat their settings, it references the
layer of each part on top of the part.

Open the layer instead of the file to get both (Isaac Sim: File > Open). Opinions on what
lives inside a variant are written inside the same variant, so they follow the selection.

    python -m quincaillerie.physx output/ISO4017_M8x30     # check the layers of a pack

Not simulated here: PhysX needs Isaac Sim and an NVIDIA RTX GPU. The check is structural.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pxr import Sdf, Usd, UsdGeom, UsdPhysics

SUFFIX = "_physx"
GROUND = "/World/Ground"  # the shared ground carries no engine data (ground.py)
CONTACT_OFFSET = 0.0005  # m: contacts are generated from this distance on (an asset may ask for less)
ASKED = "quincaillerie:contactOffset"  # on the root of an asset: the contact offset it needs (m)
REST_OFFSET = 0.0  # m
POSITION_ITERATIONS = 16
VELOCITY_ITERATIONS = 4
MAX_DEPENETRATION_VELOCITY = 0.1  # m/s
_F = Sdf.ValueTypeNames


def overlay_path(usd: Path) -> Path:
    return Path(usd).with_name(f"{Path(usd).stem}{SUFFIX}.usda")


def is_overlay(path: Path) -> bool:
    return Path(path).stem.endswith(SUFFIX)


def _contact_offset(prim) -> float:
    """The contact offset the asset a collider belongs to asks for."""
    while prim and not prim.IsPseudoRoot():
        asked = prim.GetAttribute(ASKED)
        if asked and asked.Get():
            return float(asked.Get())
        prim = prim.GetParent()
    return CONTACT_OFFSET


def _tune(prim, position_iterations: int, max_depenetration: float) -> None:
    """The PhysX opinions of one prim, written at the current edit target."""
    if prim.HasAPI(UsdPhysics.RigidBodyAPI):
        prim.AddAppliedSchema("PhysxRigidBodyAPI")
        prim.CreateAttribute("physxRigidBody:solverPositionIterationCount", _F.Int).Set(position_iterations)
        prim.CreateAttribute("physxRigidBody:solverVelocityIterationCount", _F.Int).Set(VELOCITY_ITERATIONS)
        prim.CreateAttribute("physxRigidBody:maxDepenetrationVelocity", _F.Float).Set(max_depenetration)
        prim.CreateAttribute("physxRigidBody:enableCCD", _F.Bool).Set(False)
    if prim.HasAPI(UsdPhysics.CollisionAPI) and prim.GetPath() != GROUND:
        prim.AddAppliedSchema("PhysxCollisionAPI")
        prim.CreateAttribute("physxCollision:contactOffset", _F.Float).Set(_contact_offset(prim))
        prim.CreateAttribute("physxCollision:restOffset", _F.Float).Set(REST_OFFSET)


def _layered_references(prim, folder: Path) -> list[str]:
    """The files a prim references that have a PhysX layer of their own: the paths of those layers."""
    listed = prim.GetMetadata("references")
    out = []
    for ref in listed.GetAddedOrExplicitItems() if listed else ():
        if ref.assetPath and overlay_path(folder / ref.assetPath).exists():
            out.append(overlay_path(Path(ref.assetPath)).as_posix())
    return [p if p.startswith(".") else f"./{p}" for p in out]


def _in_variant(prim, selection: str = "") -> bool:
    """Whether a prim is defined inside variants only (and so exists only when one is selected);
    with a selection such as "{finish=brass}", whether that very variant defines it. A prim that
    a variant merely adds opinions to (a material binding) is not in a variant."""
    defs = [spec.path for spec in prim.GetPrimStack() if spec.specifier == Sdf.SpecifierDef]
    if any(not p.ContainsPrimVariantSelection() for p in defs):
        return False
    return any(selection in str(p) for p in defs)


def write_overlay(
    usd, position_iterations: int = POSITION_ITERATIONS, max_depenetration: float = MAX_DEPENETRATION_VELOCITY
) -> Path:
    """Write `<file>_physx.usda` beside an OpenUSD file and return its path."""
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
    stage.SetDefaultPrim(stage.GetPrimAtPath(base.GetDefaultPrim().GetPath()))
    # what exists whatever the variants: written on the prims themselves
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
        if not _in_variant(prim):
            _tune(prim, position_iterations, max_depenetration)
    # what a variant brings: written inside that variant, one selection at a time (the
    # selections are tried in the session layer, which is not saved)
    session = stage.GetSessionLayer()
    for holder in holders:
        sets = holder.GetVariantSets()
        for name in sets.GetNames():
            vset = sets.GetVariantSet(name)
            for variant in vset.GetVariantNames():
                with Usd.EditContext(stage, session):
                    vset.SetVariantSelection(variant)
                with Usd.EditContext(stage, vset.GetVariantEditTarget(layer)):
                    for prim in Usd.PrimRange(holder):
                        if _in_variant(prim, f"{{{name}={variant}}}"):
                            _tune(prim, position_iterations, max_depenetration)
    session.Clear()
    layer.Save()
    return out


def _authored(prim) -> set[str]:
    """API schemas as authored: the PhysX ones are not registered without Isaac Sim's plug-ins."""
    names: set[str] = set()
    for spec in prim.GetPrimStack():
        listed = spec.GetInfo("apiSchemas") if spec.HasInfo("apiSchemas") else None
        if listed:
            names.update(listed.GetAppliedItems())
    return names


def engine_data(stage) -> list[str]:
    """What a stage holds that only PhysX reads: 'path: name' lines (empty for a main file)."""
    found = []
    for prim in stage.Traverse():
        found += [f"{prim.GetPath()}: {s}" for s in sorted(_authored(prim)) if s.startswith("Physx")]
        found += [f"{prim.GetPath()}: {a.GetName()}" for a in prim.GetAttributes() if a.GetName().startswith("physx")]
    return found


def check(path) -> list[str]:
    """Structural problems of a PhysX layer (empty: none)."""
    path = Path(path)
    layer = Sdf.Layer.FindOrOpen(str(path))
    stem = path.stem.removesuffix(SUFFIX)
    main = next((path.with_name(stem + ext) for ext in (".usdc", ".usda") if path.with_name(stem + ext).exists()), None)
    if main is None:
        return [f"no file {stem}.usdc or {stem}.usda beside it"]
    problems = []
    if list(layer.subLayerPaths) != [f"./{main.name}"]:
        problems.append(f"its only sublayer must be ./{main.name}")
        return problems
    base = Usd.Stage.Open(str(main))
    if engine_data(base):
        problems.append(f"{main.name} holds PhysX data itself")
    stage = Usd.Stage.Open(str(path))
    base_paths = {p.GetPath() for p in Usd.PrimRange.AllPrims(base.GetPseudoRoot())}
    extra = [p.GetPath() for p in Usd.PrimRange.AllPrims(stage.GetPseudoRoot()) if p.GetPath() not in base_paths]
    if extra:
        problems.append(f"defines prims the file does not have: {extra[0]}")
    # only the variant sets that bring prims of their own need each of their variants looked at
    holders = [p for p in stage.Traverse() if p.HasVariantSets() and any(_in_variant(q) for q in Usd.PrimRange(p))]
    session = stage.GetSessionLayer()
    selections = [{}]  # the file's own selections, then each variant of each set in turn
    for holder in holders:
        for name in holder.GetVariantSets().GetNames():
            for variant in holder.GetVariantSet(name).GetVariantNames():
                selections.append({(holder.GetPath(), name): variant})
    for chosen in selections:
        session.Clear()
        with Usd.EditContext(stage, session):
            for (holder, name), variant in chosen.items():
                stage.GetPrimAtPath(holder).GetVariantSet(name).SetVariantSelection(variant)
        label = ", ".join(f"{n}={v}" for (_, n), v in chosen.items()) or "default"
        for prim in Usd.PrimRange.AllPrims(stage.GetPseudoRoot()):
            if not prim.IsDefined():
                problems.append(f"[{label}] {prim.GetPath()}: an opinion on a prim that does not exist")
                continue
            body, collider = prim.HasAPI(UsdPhysics.RigidBodyAPI), prim.HasAPI(UsdPhysics.CollisionAPI)
            schemas = _authored(prim)
            if body != ("PhysxRigidBodyAPI" in schemas):
                problems.append(f"[{label}] {prim.GetPath()}: rigid body and PhysxRigidBodyAPI do not go together")
            if (collider and prim.GetPath() != GROUND) != ("PhysxCollisionAPI" in schemas):
                problems.append(f"[{label}] {prim.GetPath()}: collider and PhysxCollisionAPI do not go together")
            if "PhysxCollisionAPI" in schemas:
                off = prim.GetAttribute("physxCollision:contactOffset").Get()
                rest = prim.GetAttribute("physxCollision:restOffset").Get()
                if off is None or rest is None or not off > rest >= 0:
                    problems.append(f"[{label}] {prim.GetPath()}: contact offset must be above the rest offset")
    session.Clear()
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check the PhysX layers (*_physx.usda) of packs or files.")
    ap.add_argument("paths", nargs="+", type=Path)
    args = ap.parse_args(argv)
    files = []
    for p in args.paths:
        files += sorted(p.rglob(f"*{SUFFIX}.usda")) if p.is_dir() else [p]
    if not files:
        print("no PhysX layer found")
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
