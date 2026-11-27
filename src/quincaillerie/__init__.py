"""Quincaillerie: standard hardware assets generator for Physical AI.

Metric screws, nuts and washers with modelled threads, battery cells and their holders with working
springs and clips, exported to OpenUSD with UsdPhysics and checked in MuJoCo and Blender.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("quincaillerie")  # from the installed package: one place for the version
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0+unknown"

from .catalog import CELLS, FORMATS, KINDS, METRIC, SIZES  # noqa: E402
from .generator import Part, catalog_parts, generate, resolve  # noqa: E402

__all__ = [
    "CELLS",
    "FORMATS",
    "KINDS",
    "METRIC",
    "SIZES",
    "Part",
    "catalog_parts",
    "generate",
    "resolve",
    "__version__",
]
