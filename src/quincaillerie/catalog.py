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


# Under the head of a hex head screw (ISO 4017) or bolt (ISO 4014), product grade A (mm): the
# bearing face's diameter dw (from dw_min up to s_min, so that it stays inside the hex) and height c
# (c_min to c_max), the fillet radius r (r_min to r_max = (da_max - d) / 2, da being the fillet's
# largest diameter). The standards give limits only: a nominal part takes the middle of each range.
UNDER_HEAD = {
    "M3": dict(dw_min=4.57, c=(0.15, 0.40), r_min=0.1, da_max=3.6),
    "M4": dict(dw_min=5.88, c=(0.15, 0.40), r_min=0.2, da_max=4.7),
    "M5": dict(dw_min=6.88, c=(0.15, 0.50), r_min=0.2, da_max=5.7),
    "M6": dict(dw_min=8.88, c=(0.15, 0.50), r_min=0.25, da_max=6.8),
    "M8": dict(dw_min=11.63, c=(0.15, 0.60), r_min=0.4, da_max=9.2),
    "M10": dict(dw_min=14.63, c=(0.15, 0.60), r_min=0.4, da_max=11.2),
    "M12": dict(dw_min=16.63, c=(0.15, 0.60), r_min=0.6, da_max=13.7),
}
# Hex head bolts, ISO 4014 (partially threaded), product grade A: thread length b (reference, for
# nominal lengths up to 125 mm), the plain shank's smallest diameter ds_min (its largest is d) and
# the nominal lengths the table gives for each size. The plain shank is not a free parameter: its
# length lies between ls_min and lg_max, both set by the size and the nominal length (plain_range).
BOLT = {
    "M3": dict(b=12.0, ds_min=2.86, lengths=(20, 25, 30)),
    "M4": dict(b=14.0, ds_min=3.82, lengths=(25, 30, 35, 40)),
    "M5": dict(b=16.0, ds_min=4.82, lengths=(25, 30, 35, 40, 45, 50)),
    "M6": dict(b=18.0, ds_min=5.82, lengths=(30, 35, 40, 45, 50, 55, 60)),
    "M8": dict(b=22.0, ds_min=7.78, lengths=(40, 45, 50, 55, 60, 65, 70, 80)),
    "M10": dict(b=26.0, ds_min=9.78, lengths=(45, 50, 55, 60, 65, 70, 80, 90, 100)),
    "M12": dict(b=30.0, ds_min=11.73, lengths=(50, 55, 60, 65, 70, 80, 90, 100, 110, 120)),
}
DEFAULT_BOLT_LENGTH = {"M3": 25, "M4": 30, "M5": 35, "M6": 40, "M8": 50, "M10": 60, "M12": 70}


# Hexagon socket head cap screws, ISO 4762 (plain head), product grade A, from a public excerpt of
# JIS B 1176 (which corresponds to ISO 4762:2004), in mm: thread length b (reference), head diameter
# dk and height k (min, max; k max = d), the hex socket's nominal across flats (socket) and its
# limits s (min, max for classes 8.8 and 10.9,
# max for 12.9) and depth t (t_min; t stops short of the wall under the socket, w_min), the top
# edge's chamfer v (up to v_max), the bearing diameter dw_min under the head, the shank's smallest
# diameter ds_min, the nominal lengths and the longest one threaded to the head (full_to): a longer
# screw has a plain shank, as a bolt (plain_range).
CAP_SCREW = {
    "M3": dict(
        socket=2.5,
        b=18.0,
        dk=(5.32, 5.5),
        k=(2.86, 3.0),
        s=(2.52, 2.58, 2.56),
        t_min=1.3,
        w_min=1.15,
        v_max=0.3,
        dw_min=5.07,
        ds_min=2.86,
        lengths=(5, 6, 8, 10, 12, 16, 20, 25, 30),
        full_to=20,
    ),
    "M4": dict(
        socket=3.0,
        b=20.0,
        dk=(6.78, 7.0),
        k=(3.82, 4.0),
        s=(3.02, 3.08, 3.08),
        t_min=2.0,
        w_min=1.4,
        v_max=0.4,
        dw_min=6.53,
        ds_min=3.82,
        lengths=(6, 8, 10, 12, 16, 20, 25, 30, 35, 40),
        full_to=25,
    ),
    "M5": dict(
        socket=4.0,
        b=22.0,
        dk=(8.28, 8.5),
        k=(4.82, 5.0),
        s=(4.02, 4.095, 4.095),
        t_min=2.5,
        w_min=1.9,
        v_max=0.5,
        dw_min=8.03,
        ds_min=4.82,
        lengths=(8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50),
        full_to=25,
    ),
    "M6": dict(
        socket=5.0,
        b=24.0,
        dk=(9.78, 10.0),
        k=(5.70, 6.0),
        s=(5.02, 5.14, 5.095),
        t_min=3.0,
        w_min=2.3,
        v_max=0.6,
        dw_min=9.38,
        ds_min=5.82,
        lengths=(10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60),
        full_to=30,
    ),
    "M8": dict(
        socket=6.0,
        b=28.0,
        dk=(12.73, 13.0),
        k=(7.64, 8.0),
        s=(6.02, 6.14, 6.095),
        t_min=4.0,
        w_min=3.3,
        v_max=0.8,
        dw_min=12.33,
        ds_min=7.78,
        lengths=(12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80),
        full_to=35,
    ),
    "M10": dict(
        socket=8.0,
        b=32.0,
        dk=(15.73, 16.0),
        k=(9.64, 10.0),
        s=(8.025, 8.175, 8.115),
        t_min=5.0,
        w_min=4.0,
        v_max=1.0,
        dw_min=15.33,
        ds_min=9.78,
        lengths=(16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100),
        full_to=40,
    ),
    "M12": dict(
        socket=10.0,
        b=36.0,
        dk=(17.73, 18.0),
        k=(11.57, 12.0),
        s=(10.025, 10.175, 10.115),
        t_min=6.0,
        w_min=4.8,
        v_max=1.2,
        dw_min=17.23,
        ds_min=11.73,
        lengths=(20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100, 110, 120),
        full_to=50,
    ),
}
PROPERTY_CLASSES = ("8.8", "10.9", "12.9")
DEFAULT_PROPERTY_CLASS = "12.9"


def socket_s_max(size: str, property_class: str = DEFAULT_PROPERTY_CLASS) -> float:
    """The largest across flats of a cap screw's hex socket: the table gives one for 12.9 and one
    for the other classes."""
    s = CAP_SCREW[size]["s"]
    return s[2] if property_class == "12.9" else s[1]


def plain_range(size: str, length_mm: float, kind: str = "bolt") -> tuple[float, float]:
    """(ls_min, lg_max) of an ISO 4014 bolt or a long ISO 4762 cap screw (mm): lg_max = l - b,
    ls_min = lg_max - 5 P. The plain shank ends between the two; the thread runs from there to the
    tip."""
    b = (CAP_SCREW if kind == "cap_screw" else BOLT)[size]["b"]
    lg = length_mm - b
    return lg - 5 * METRIC[size]["P"], lg


def has_plain_shank(kind: str, size: str, length_mm: float) -> bool:
    """A bolt always has one; a cap screw when it is longer than its size's fully threaded lengths."""
    return kind == "bolt" or (kind == "cap_screw" and length_mm > CAP_SCREW[size]["full_to"])


def fillet_range(size: str) -> tuple[float, float]:
    """(r_min, r_max) of the fillet under the head (mm), r_max = (da_max - d) / 2."""
    u = UNDER_HEAD[size]
    return u["r_min"], (u["da_max"] - METRIC[size]["d"]) / 2


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


def wrapper_span(c: dict) -> tuple[float, float, float]:
    """Where a cylindrical cell's printed wrapper lies (mm): from x0 to x1 along the cell (- end at
    -L/2), at radius r. The cell's mesh and its label texture both take it from here, so the label
    is drawn at the wrapper's own proportions."""
    L, r, nh = c["L"], c["d"] / 2, c["nub_h"]
    return -L / 2 + 0.8, L / 2 - nh - 2.0, r + 0.02


def label_9v_size(c: dict) -> tuple[float, float]:
    """The 9V block's printed label (mm): its length along the block and its height."""
    return 0.7 * c["L"], c["T"] - 4.0


KINDS = ("screw", "bolt", "cap_screw", "nut", "washer", "cell", "holder")
# the fasteners with an external thread: an ISO 4017 screw (threaded to the head), an ISO 4014 bolt,
# an ISO 4762 socket head cap screw
THREADED = ("screw", "bolt", "cap_screw")
FASTENERS = ("screw", "bolt", "cap_screw", "nut", "washer")
# related elements that `--with` can add to a generated part
RELATED = {
    "screw": ("nut", "washer"),
    "bolt": ("nut", "washer"),
    "cap_screw": ("nut", "washer"),
    "nut": ("screw", "bolt", "cap_screw", "washer"),
    "washer": ("screw", "bolt", "cap_screw", "nut"),
    "cell": ("holder",),
    "holder": ("cell",),
}


def screw_name(size: str, length: float) -> str:
    return f"ISO4017_{size}x{length:g}"


def bolt_name(size: str, length: float) -> str:
    return f"ISO4014_{size}x{length:g}"


def cap_screw_name(size: str, length: float) -> str:
    return f"ISO4762_{size}x{length:g}"


def nut_name(size: str) -> str:
    return f"ISO4032_{size}"


def washer_name(size: str) -> str:
    return f"ISO7089_{size}"


def asset_name(kind: str, size_or_format: str, length: float | None = None) -> str:
    if kind == "screw":
        return screw_name(size_or_format, length or DEFAULT_LENGTH[size_or_format])
    if kind == "bolt":
        return bolt_name(size_or_format, length or DEFAULT_BOLT_LENGTH[size_or_format])
    if kind == "cap_screw":
        return cap_screw_name(size_or_format, length or DEFAULT_LENGTH[size_or_format])
    if kind == "nut":
        return nut_name(size_or_format)
    if kind == "washer":
        return washer_name(size_or_format)
    if kind == "cell":
        return f"Cell_{size_or_format}"
    if kind == "holder":
        return f"Holder_{size_or_format}"
    raise ValueError(f"unknown kind {kind!r}, expected one of {KINDS}")
