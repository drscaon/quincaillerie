"""OpenUSD validation of the generated files with the validators shipped with OpenUSD.

Runs every validator of the UsdValidation registry (what ``usdchecker`` runs
since OpenUSD 25): composition, stage metadata, geometry and subsets,
material bindings, shader compliance, UsdPhysics rigid bodies, colliders,
joints and articulations. Each file is checked once per variant of every
variant set, since a variant that is not selected is not composed. Packaging
checks (.usdz) are skipped.

MaterialX shaders (``ND_*`` ids) can only be checked when OpenUSD was built
with its MaterialX plugin; the ``usd-core`` wheels from PyPI are not, so
"not found in sdrRegistry" for an ``ND_*`` id is ignored there (the MaterialX
document is validated by the MaterialX library instead).

Command line::

    python -m quincaillerie.validate output/<preset>     # files or folders; exit 1 on any issue
"""

from __future__ import annotations

import sys
from pathlib import Path

from pxr import Sdr, Usd, UsdValidation

SKIP = ("usdUtilsValidators:UsdzPackageValidator", "usdUtilsValidators:RootPackageValidator")
SUFFIXES = (".usd", ".usda", ".usdc")


def _validators():
    reg = UsdValidation.ValidationRegistry()
    names = [m.name for m in reg.GetAllValidatorMetadata() if m.name not in SKIP]
    return reg.GetOrLoadValidatorsByName(names)


def _materialx_in_sdr() -> bool:
    return any(i.startswith("ND_") for i in Sdr.Registry().GetShaderNodeIdentifiers())


def _variant_states(stage) -> list[dict]:
    """The default selection, then one selection per variant of each variant set."""
    states, seen = [{}], set()
    for prim in stage.Traverse():
        vsets = prim.GetVariantSets()
        for name in vsets.GetNames():
            for v in vsets.GetVariantSet(name).GetVariantNames():
                if (name, v) not in seen:
                    seen.add((name, v))
                    states.append({(str(prim.GetPath()), name): v})
    return states


def validate(path: str | Path) -> list[str]:
    """Error and warning messages of the OpenUSD validators on a file (empty: compliant)."""
    path = str(path)
    validators = _validators()
    skip_mtlx = not _materialx_in_sdr()
    out = []
    for state in _variant_states(Usd.Stage.Open(path)):
        stage = Usd.Stage.Open(path)
        stage.SetEditTarget(stage.GetSessionLayer())  # never touch the file's layer, even in memory
        for (prim_path, vset), v in state.items():
            stage.GetPrimAtPath(prim_path).GetVariantSets().GetVariantSet(vset).SetVariantSelection(v)
        for err in UsdValidation.ValidationContext(validators).Validate(stage):
            if err.GetType() not in (
                UsdValidation.ValidationErrorType.Error,
                UsdValidation.ValidationErrorType.Warn,
            ):
                continue
            text = err.GetMessage()
            if skip_mtlx and "'ND_" in text and "not found in sdrRegistry" in text:
                continue
            msg = f"{err.GetType().displayName}: {text}"
            if msg not in out:
                out.append(msg)
    return out


def usd_files(paths) -> list[Path]:
    """The OpenUSD files among ``paths``, folders searched recursively."""
    files = []
    for p in map(Path, paths):
        files += sorted(f for f in p.rglob("*") if f.suffix in SUFFIXES) if p.is_dir() else [p]
    return files


def main(argv: list[str] | None = None) -> int:
    paths = sys.argv[1:] if argv is None else argv
    if not paths:
        print("usage: python -m quincaillerie.validate FILE_OR_FOLDER...", file=sys.stderr)
        return 2
    files, failed = usd_files(paths), 0
    for f in files:
        issues = validate(f)
        failed += bool(issues)
        for msg in issues:
            print(f"{f}: {msg}")
    print(f"{len(files)} OpenUSD files checked, {failed} with issues")
    return 1 if failed or not files else 0


if __name__ == "__main__":
    raise SystemExit(main())
