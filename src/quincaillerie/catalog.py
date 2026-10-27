"""What Quincaillerie can generate: metric fasteners, battery cells and their holders.

Fastener dimensions are the nominal values found in public tables (manufacturers' catalogues,
reference handbooks). The ISO standards themselves were not consulted, so every dimension is marked
"nominal" in the assets. Cell dimensions are nominal (IEC designations); masses and contact forces are
typical orders of magnitude, not measurements of a product.
"""

from __future__ import annotations

# Metric coarse threads (ISO 261 sizes): major diameter d, pitch P, hex across flats s,
# hex head height k (ISO 4017 hex head screw), nut height m (ISO 4032 hex nut),
# plain washer d1 x d2 x h (ISO 7089, normal series). All in mm.
METRIC = {
    "M3": dict(d=3.0, P=0.5, s=5.5, k=2.0, m=2.4, washer=(3.2, 7.0, 0.5)),
    "M4": dict(d=4.0, P=0.7, s=7.0, k=2.8, m=3.2, washer=(4.3, 9.0, 0.8)),
    "M5": dict(d=5.0, P=0.8, s=8.0, k=3.5, m=4.7, washer=(5.3, 10.0, 1.0)),
    "M6": dict(d=6.0, P=1.0, s=10.0, k=4.0, m=5.2, washer=(6.4, 12.0, 1.6)),
    "M8": dict(d=8.0, P=1.25, s=13.0, k=5.3, m=6.8, washer=(8.4, 16.0, 1.6)),
    "M10": dict(d=10.0, P=1.5, s=16.0, k=6.4, m=8.4, washer=(10.5, 20.0, 2.0)),
    "M12": dict(d=12.0, P=1.75, s=18.0, k=7.5, m=10.8, washer=(13.0, 24.0, 2.5)),
}
SIZES = list(METRIC)
# preferred lengths of fully threaded hex head screws (mm), and the default length per size
LENGTHS = [6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60]
DEFAULT_LENGTH = {"M3": 12, "M4": 16, "M5": 20, "M6": 20, "M8": 30, "M10": 35, "M12": 40}

# Battery cells. kind: 'cradle' (cylindrical cell in a cradle with a coil spring), 'nine_volt'
# (PP3 block, keyed terminal block), 'coin' (coin and button cells under a hinged leaf-spring clip).
# Lengths in mm (L includes the + button), mass in g, F the contact force when seated (N),
# pre the spring compression when seated (mm).
CELLS = {
    "AAA": dict(kind="cradle", iec="LR03", volts=1.5, d=10.5, L=44.5, nub_d=3.8, nub_h=0.8, mass=11.5, F=2.5, pre=4.0),
    "AA": dict(kind="cradle", iec="LR6", volts=1.5, d=14.5, L=50.5, nub_d=5.5, nub_h=1.0, mass=23.0, F=3.5, pre=5.0),
    "C": dict(kind="cradle", iec="LR14", volts=1.5, d=26.2, L=50.0, nub_d=7.5, nub_h=1.5, mass=66.0, F=5.0, pre=5.0),
    "D": dict(kind="cradle", iec="LR20", volts=1.5, d=34.2, L=61.5, nub_d=9.5, nub_h=1.5, mass=135.0, F=6.0, pre=6.0),
    "CR123A": dict(
        kind="cradle", iec="CR17345", volts=3.0, d=17.0, L=34.5, nub_d=5.0, nub_h=1.0, mass=17.0, F=3.0, pre=4.0
    ),
    "18650": dict(
        kind="cradle", iec="INR18650", volts=3.6, d=18.0, L=65.0, nub_d=8.0, nub_h=0.5, mass=46.0, F=5.0, pre=5.0
    ),
    "21700": dict(
        kind="cradle", iec="INR21700", volts=3.6, d=21.0, L=70.0, nub_d=8.5, nub_h=0.5, mass=68.0, F=6.0, pre=5.0
    ),
    "9V": dict(kind="nine_volt", iec="6LR61", volts=9.0, W=26.5, T=17.5, L=48.5, mass=45.0, F=4.0, pre=5.0),
    "CR2032": dict(kind="coin", iec="CR2032", volts=3.0, d=20.0, h=3.2, mass=2.9, F=3.0),
    "LR44": dict(kind="coin", iec="LR44", volts=1.5, d=11.6, h=5.4, mass=1.9, F=2.0),
}
FORMATS = list(CELLS)

KINDS = ("screw", "nut", "washer", "cell", "holder")
# related elements that `--with` can add to a generated part
RELATED = {
    "screw": ("nut", "washer"),
    "nut": ("screw", "washer"),
    "washer": ("screw", "nut"),
    "cell": ("holder",),
    "holder": ("cell",),
}


def screw_name(size: str, length: float) -> str:
    return f"ISO4017_{size}x{length:g}"


def nut_name(size: str) -> str:
    return f"ISO4032_{size}"


def washer_name(size: str) -> str:
    return f"ISO7089_{size}"


def asset_name(kind: str, size_or_format: str, length: float | None = None) -> str:
    if kind == "screw":
        return screw_name(size_or_format, length or DEFAULT_LENGTH[size_or_format])
    if kind == "nut":
        return nut_name(size_or_format)
    if kind == "washer":
        return washer_name(size_or_format)
    if kind == "cell":
        return f"Cell_{size_or_format}"
    if kind == "holder":
        return f"Holder_{size_or_format}"
    raise ValueError(f"unknown kind {kind!r}, expected one of {KINDS}")
