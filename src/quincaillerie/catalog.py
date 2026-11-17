"""What Quincaillerie can generate: metric fasteners, battery cells and their holders.

Every physical value here names its source in sources.py (docs/sources.md): fastener dimensions and
their tolerances from public tables of ISO 4017, ISO 4032 and ISO 7089 (the standards themselves
were not consulted, so every dimension is marked "nominal" in the assets); cell dimensions, their
limits and masses from manufacturers' datasheets; what no datasheet gives (a holder's contact force,
a spring's preload) is marked as an estimate there.
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
# product grade A tolerances (mm): s from s_min to s, k from k_min to k_max, m from m_min to m,
# the washer's h within washer_h
TOLERANCES = {
    "M3": dict(s_min=5.32, k_min=1.875, k_max=2.125, m_min=2.15, washer_h=(0.45, 0.55)),
    "M4": dict(s_min=6.78, k_min=2.675, k_max=2.925, m_min=2.9, washer_h=(0.7, 0.9)),
    "M5": dict(s_min=7.78, k_min=3.35, k_max=3.65, m_min=4.4, washer_h=(0.9, 1.1)),
    "M6": dict(s_min=9.78, k_min=3.85, k_max=4.15, m_min=4.9, washer_h=(1.4, 1.8)),
    "M8": dict(s_min=12.73, k_min=5.15, k_max=5.45, m_min=6.44, washer_h=(1.4, 1.8)),
    "M10": dict(s_min=15.73, k_min=6.22, k_max=6.58, m_min=8.04, washer_h=(1.8, 2.2)),
    "M12": dict(s_min=17.73, k_min=7.32, k_max=7.68, m_min=10.37, washer_h=(2.3, 2.7)),
}
SIZES = list(METRIC)
# preferred lengths of fully threaded hex head screws (mm), and the default length per size
LENGTHS = [6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60]
DEFAULT_LENGTH = {"M3": 12, "M4": 16, "M5": 20, "M6": 20, "M8": 30, "M10": 35, "M12": 40}
# length tolerance of an ISO 4017 screw, product grade A: (longest nominal length, ± mm)
LENGTH_TOLERANCE = (
    (3, 0.2),
    (6, 0.24),
    (10, 0.29),
    (16, 0.35),
    (30, 0.42),
    (50, 0.5),
    (80, 0.6),
    (120, 0.7),
    (150, 0.8),
)


def length_tolerance(length_mm: float) -> float:
    """± mm of a screw of that nominal length (the tolerance of the next listed length up)."""
    for longest, tol in LENGTH_TOLERANCE:
        if length_mm <= longest:
            return tol
    return LENGTH_TOLERANCE[-1][1]


# Battery cells. kind: 'cradle' (cylindrical cell in a cradle with a coil spring), 'nine_volt'
# (PP3 block, keyed terminal block), 'coin' (coin and button cells under a hinged leaf-spring clip).
# Lengths in mm (L includes the + button), mass in g, F the contact force when seated (N),
# pre the spring compression when seated (mm).
CELLS = {
    "AAA": dict(kind="cradle", iec="LR03", volts=1.5, d=10.5, L=44.5, nub_d=3.8, nub_h=0.8, mass=11.5, F=2.5, pre=4.0),
    "AA": dict(kind="cradle", iec="LR6", volts=1.5, d=14.5, L=50.5, nub_d=5.5, nub_h=1.0, mass=23.0, F=3.5, pre=5.0),
    "C": dict(kind="cradle", iec="LR14", volts=1.5, d=26.2, L=50.0, nub_d=7.5, nub_h=1.5, mass=66.2, F=5.0, pre=5.0),
    "D": dict(kind="cradle", iec="LR20", volts=1.5, d=34.2, L=61.5, nub_d=9.5, nub_h=1.5, mass=139.0, F=6.0, pre=6.0),
    "CR123A": dict(
        kind="cradle", iec="CR17345", volts=3.0, d=17.0, L=34.5, nub_d=5.0, nub_h=1.0, mass=16.5, F=3.0, pre=4.0
    ),
    "18650": dict(
        kind="cradle", iec="INR18650", volts=3.6, d=18.4, L=65.0, nub_d=8.0, nub_h=0.5, mass=43.8, F=5.0, pre=5.0
    ),
    "21700": dict(
        kind="cradle", iec="INR21700", volts=3.6, d=21.22, L=70.3, nub_d=8.5, nub_h=0.5, mass=66.8, F=6.0, pre=5.0
    ),
    "9V": dict(kind="nine_volt", iec="6LR61", volts=9.0, W=26.5, T=17.5, L=48.5, mass=45.6, F=4.0, pre=5.0),
    "CR2032": dict(kind="coin", iec="CR2032", volts=3.0, d=20.0, h=3.2, mass=3.0, F=3.0),
    "LR44": dict(kind="coin", iec="LR44", volts=1.5, d=11.6, h=5.4, mass=1.9, F=2.0),
}
# the datasheets' minima (mm): every nominal size above is the datasheet's maximum
CELL_MIN = {
    "AAA": dict(d_min=9.5, L_min=43.3),
    "AA": dict(d_min=13.5, L_min=49.5),
    "C": dict(d_min=24.9, L_min=48.5),
    "D": dict(d_min=32.3, L_min=59.5),
    "CR123A": dict(d_min=16.0, L_min=33.5),
    "18650": dict(d_min=18.26, L_min=64.7),
    "21700": dict(d_min=21.0, L_min=69.95),
    "9V": dict(L_min=46.4, W_min=24.5, T_min=15.5),
    "CR2032": dict(d_min=19.7, h_min=2.9),
    "LR44": dict(d_min=11.3, h_min=5.0),
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
