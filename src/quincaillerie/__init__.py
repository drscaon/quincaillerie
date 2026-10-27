"""Quincaillerie: standard hardware assets generator for Physical AI.

Metric screws, nuts and washers with modelled threads, battery cells and their holders with working
springs and clips, exported to OpenUSD with UsdPhysics and checked in MuJoCo and Blender.
"""

__version__ = "0.1.0b1"

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
