"""Where every physical value of Quincaillerie comes from (PRV-33).

Each value that describes the real world (a dimension, a tolerance, a mass, a voltage, a density, a
friction, a stiffness) names its source: a public table of a standard, a manufacturer's datasheet, an
engineering handbook, or, where none was found, an estimate with what it rests on. Where the source
gives a range (a tolerance, a minimum and a maximum), the value and what the generator draws around it
must lie within it; tests/test_sources.py checks both, and that no value is left without a source.

The standards themselves (ISO 4017, ISO 4014, ISO 4762, ISO 4032, ISO 7089, ISO 965-1, ISO 4753, IEC 60086-2) were not
consulted:
the values come from the public tables and datasheets below, which reproduce them.

    python -m quincaillerie.sources     # the tables of docs/sources.md
"""

from __future__ import annotations

from dataclasses import dataclass

from . import batteries, fits, variation
from .catalog import BOLT, CAP_SCREW, CELL_MIN, CELLS, LENGTH_TOLERANCE, LENGTHS, METRIC, TOLERANCES, UNDER_HEAD

KINDS = ("standard table", "datasheet", "handbook", "estimate")


@dataclass(frozen=True)
class Source:
    kind: str  # one of KINDS
    title: str
    urls: tuple = ()
    note: str = ""  # for an estimate: what it rests on


SOURCES = {
    "iso4017": Source(
        "standard table",
        "Westfield Fasteners, ISO 4017 hex head set screw specification: table 1 (pitch, s, k, product grade A) "
        "and table 3 (length tolerances)",
        ("https://westfieldfasteners.co.uk/Standards/ScrewBolt-HexHd4017-M-THRfull.pdf",),
    ),
    "jisb1180": Source(
        "standard table",
        "Miki Pulley, hexagon bolts, excerpt from JIS B 1180 (part grade A, the ISO 4014 and ISO 4017 heads): b "
        "(reference, l up to 125 mm), ds, dw, c, r, and the nominal lengths with ls min and lg max; "
        "lg max = l - b, ls min = lg max - 5 P",
        ("https://mikipulley.co.jp/EN/Services/Tech_data/tech09.html",),
    ),
    "jisb1176": Source(
        "standard table",
        "Misumi, hexagon socket head cap screws, excerpts from JIS B 1176 (which corresponds to ISO 4762:2004): b, "
        "dk, k, s (8.8 and 10.9; 12.9), t, w, v, dw, ds, and the nominal lengths with ls min and lg max "
        "(lg max = l - b, ls min = lg max - 5 P; shorter lengths threaded to the head); lengths per size checked "
        "against Engineers Edge's ISO 4762 table. The length tolerance is the product grade A one, as for ISO 4017",
        (
            "https://hu.misumi-ec.com/pdf/fa/2014/P2_1891-1892_F80_EN.pdf",
            "https://engineersedge.com/iso_socket_head_screw.htm",
        ),
    ),
    "iso965_grade5": Source(
        "handbook",
        "Machinery's Handbook, 31st edition, pitch-diameter tolerances of external metric threads, Td2 by grade "
        "(ISO 965-1): grade 5 is 0.8 of grade 6 in every row (e.g. 0.200 / 0.250, 0.224 / 0.280 mm); 5g6g is a "
        "grade 5 pitch diameter in position g, the class ISO 4762 asks for property class 12.9",
        (
            "https://online.flippingbook.com/view/954046886/656",
            "https://amesweb.info/Fasteners/Screws/Metric-Hexagon-Socket-Head-Cap-Screw-Dimensions.aspx",
        ),
    ),
    "iso4014_westfield": Source(
        "standard table",
        "Westfield Fasteners, ISO 4014 partly threaded hex bolts: table 1 (b, c, da, dw, r)",
        ("https://www.westfieldfasteners.co.uk/Standards/ScrewBolt-HexHd4014-M-THRpart.pdf",),
    ),
    "tip_chamfer": Source(
        "estimate",
        "the chamfer at the tip of a screw or bolt",
        note="the standard for the ends of threaded parts (ISO 4753) is not public, and the tables used here give "
        "no size for the chamfer; Quincaillerie cuts it from the thread's minor to its major diameter over one "
        "pitch",
    ),
    "fillet_shape": Source(
        "estimate",
        "the shape of the fillet under the head",
        note="the tables give its radius r (r min, and r max = (da max - d) / 2), not its curve; a straight line "
        "from the bearing face to the shank stands for the arc",
    ),
    "iso4032": Source(
        "standard table",
        "Böllhoff, ISO 4032 hexagon nuts, steel 10, data sheet (m min and max, s min and max)",
        ("https://eshop-ro.boellhoff.com/out/media/pdf/ISO_4032_Stahl_10___en.pdf",),
    ),
    "iso7089": Source(
        "standard table",
        "AMES, metric flat washer dimensions chart, after ISO 7089:2000 (d1, d2, h with their limits)",
        ("https://amesweb.info/Fasteners/Washers/Standard-Metric-Flat-Washer-Sizes-Dimensions-Chart.aspx",),
    ),
    "iso965": Source(
        "handbook",
        "Machinery's Handbook, 31st edition, ISO metric threads: fundamental deviations (es g = −(15 + 11 P) µm, "
        "EI H = 0) and the grade ratios (TD2 grade 6 = 1.32 Td2(6)); Td2 = 90 P^0.4 d^0.1 µm checked against "
        "RoyMech's M20 6g example (170 µm; the formula gives 171)",
        (
            "https://online.flippingbook.com/view/954046886/678/",
            "https://online.flippingbook.com/view/954046886/656",
            "https://roymech.org/Useful_Tables/Screws/Thread_tol.html",
        ),
    ),
    "steel": Source(
        "handbook",
        "Engineering ToolBox, metals and alloys densities: steel 7850 kg/m³, stainless steel 7480 to 8000",
        ("https://www.engineeringtoolbox.com/metal-alloys-densities-d_50.html",),
    ),
    "alloys": Source(
        "handbook",
        "Project Materials, metal density chart: stainless steel 304 7930 kg/m³, brass 8.5 g/cm³",
        (
            "https://blog.projectmaterials.com/steel/density-of-metals",
            "https://blog.projectmaterials.com/category/products/steel/density-of-metals/",
        ),
    ),
    "thread_friction": Source(
        "handbook",
        "Autodesk Inventor, friction factor in the thread of bolted connections: galvanic zinc 0.13 to 0.18 "
        "dry; black or phosphate coating 0.14 to 0.21 dry, 0.12 to 0.15 lubricated",
        (
            "https://help.autodesk.com/cloudhelp/2016/ENU/Inventor-Help/files/GUID-BC1E0039-015D-4F5E-989B-7BAFAF03962B.htm",
        ),
    ),
    "thread_friction_estimate": Source(
        "estimate",
        "dry friction of a plain steel, A2 stainless or brass thread",
        note="no table for these was consulted: set near the plated values (0.13 to 0.18), higher for stainless "
        "steel, which galls",
    ),
    "music_wire": Source(
        "handbook",
        "Master Spring, properties of spring materials: music wire ASTM A228, modulus in torsion 79.3 GPa",
        ("https://www.masterspring.com/wp-content/uploads/2021/12/properties_of_materials.pdf",),
    ),
    "abs": Source(
        "datasheet",
        "ABS technical data sheet: density 1.04 to 1.06 g/cm³ (ISO 1183)",
        ("https://cdn.shopify.com/s/files/1/0811/4978/8498/files/ABS_Technical_Data_Sheet.pdf",),
    ),
    "plastic_friction": Source(
        "estimate",
        "friction of a cell's label and can on an ABS holder",
        note="a typical dry plastic-on-metal friction; no measurement or table was consulted",
    ),
    "holder_design": Source(
        "estimate",
        "a holder's contact force and its spring's compression when the cell is in",
        note="the order of magnitude of coil-spring and leaf-clip battery contacts; no holder datasheet was "
        "consulted. The holders are Quincaillerie's own design, not a product",
    ),
    "cell_nub": Source(
        "estimate",
        "the size of a cell's + button where its datasheet gives none, or only a bound",
        note="from photographs of the cells; within the datasheet's bounds where it gives them",
    ),
    "e92": Source(
        "datasheet",
        "Energizer EN92 (AAA, LR03): dimensions with their limits, typical weight 11.5 g",
        ("https://data.energizer.com/pdfs/EN92EU0126.pdf",),
    ),
    "e91": Source(
        "datasheet",
        "Energizer EN91 (AA, LR6): dimensions with their limits; typical weight 23.0 g (E91)",
        ("https://www.farnell.com/datasheets/1820701.pdf", "https://www.farnell.com/datasheets/1571853.pdf"),
    ),
    "e93": Source(
        "datasheet",
        "Energizer EN93 (C, LR14): dimensions with their limits, typical weight 66.2 g",
        ("https://assets.rs-online.com/v1698850124/Datasheets/8c7d1b3f002ec64ffb1a006ef4798df6.pdf",),
    ),
    "e95": Source(
        "datasheet",
        "Energizer EN95 (D, LR20): dimensions with their limits; typical weight 139 g (Max Plus EP95)",
        ("https://files.batteryjunction.com/frontend/files/EN95.pdf", "https://data.energizer.com/pdfs/ep95.pdf"),
    ),
    "el123": Source(
        "datasheet",
        "Energizer 123 (EL123AP, CR17345): dimensions with their limits; typical weight 16.5 g",
        (
            "https://www.farnell.com/datasheets/1820684.pdf",
            "https://cdn.shopify.com/s/files/1/0481/9678/0183/files/123.pdf",
        ),
    ),
    "inr18650": Source(
        "datasheet",
        "Samsung SDI, introduction of INR18650-25R: diameter 18.33 ± 0.07 mm, height 64.85 ± 0.15 mm, weight "
        "45.0 g max, 43.8 g typical",
        ("https://www.kiwiquads.co.nz/wp-content/uploads/INR18650-25R-datasheet.pdf",),
    ),
    "inr21700": Source(
        "datasheet",
        "Samsung SDI, INR21700-40T specification (abridged): height 70.30 mm max, diameter 21.22 mm max, "
        "weight 70.0 g max",
        ("https://cdn.simpower.co.nz/wp-content/uploads/2021/09/INR21700-40T.pdf",),
    ),
    "inr21700_estimate": Source(
        "estimate",
        "what the INR21700-40T datasheet does not give: its minima and its typical weight",
        ("https://www.akkuteile.de/en/samsung-inr21700-40t-4000mah-35a-li-ion-battery-3-6v-3-7v_100811_3235",),
        note="a dealer's figures (21.15 ± 0.15 mm, 70.15 ± 0.2 mm) for the minima; the weight retailers give "
        "(66.8 g), under the datasheet's maximum",
    ),
    "e522": Source(
        "datasheet",
        "Energizer 522 (9 V, 6LR61): dimensions with their limits; typical weight 45.6 g",
        (
            "https://elcodis.com/parts/2884384/522BP.html",
            "https://dtsheet.com/doc/1429949/9v-energizer-522---energizer-technical-information",
            "https://media.distrelec.com/Web/Downloads/ta/_e/fr522-9V_data_e.pdf",
        ),
    ),
    "cr2032": Source(
        "datasheet",
        "Energizer CR2032: dimensions with their limits; typical weight 3.0 g",
        ("https://data.energizer.com/pdfs/cr2032.pdf", "https://www.radiolocman.com/datasheet/pdf.html?di=169019"),
    ),
    "lr44": Source(
        "datasheet",
        "GP A76 (LR44): Ø11.60 +0/−0.30 mm, 5.40 +0/−0.40 mm, average weight 1.9 g",
        ("https://manualmachine.com/gpbatteries/a76/9622182-datasheet",),
    ),
}

CELL_SOURCE = {
    "AAA": "e92",
    "AA": "e91",
    "C": "e93",
    "D": "e95",
    "CR123A": "el123",
    "18650": "inr18650",
    "21700": "inr21700",
    "9V": "e522",
    "CR2032": "cr2032",
    "LR44": "lr44",
}


@dataclass(frozen=True)
class Value:
    path: str  # where it is in the code: METRIC.M8.s, CELLS.AA.mass
    value: float
    unit: str
    source: str  # a key of SOURCES
    low: float | None = None  # the range the source gives, when it gives one
    high: float | None = None


def _fasteners() -> list[Value]:
    out = []
    for size, m in METRIC.items():
        t = TOLERANCES[size]
        out += [
            Value(f"METRIC.{size}.d", m["d"], "mm", "iso4017"),
            Value(f"METRIC.{size}.P", m["P"], "mm", "iso4017"),
            Value(f"METRIC.{size}.s", m["s"], "mm", "iso4017", t["s_min"], m["s"]),
            Value(f"METRIC.{size}.k", m["k"], "mm", "iso4017", t["k_min"], t["k_max"]),
            Value(f"METRIC.{size}.m", m["m"], "mm", "iso4032", t["m_min"], m["m"]),
            Value(f"METRIC.{size}.washer.d1", m["washer"][0], "mm", "iso7089"),
            Value(f"METRIC.{size}.washer.d2", m["washer"][1], "mm", "iso7089"),
            Value(f"METRIC.{size}.washer.h", m["washer"][2], "mm", "iso7089", *t["washer_h"]),
            Value(f"TOLERANCES.{size}.s_min", t["s_min"], "mm", "iso4017"),
            Value(f"TOLERANCES.{size}.k_min", t["k_min"], "mm", "iso4017"),
            Value(f"TOLERANCES.{size}.k_max", t["k_max"], "mm", "iso4017"),
            Value(f"TOLERANCES.{size}.m_min", t["m_min"], "mm", "iso4032"),
            Value(f"TOLERANCES.{size}.washer_h.min", t["washer_h"][0], "mm", "iso7089"),
            Value(f"TOLERANCES.{size}.washer_h.max", t["washer_h"][1], "mm", "iso7089"),
        ]
    for size, u in UNDER_HEAD.items():
        out += [
            Value(f"UNDER_HEAD.{size}.dw_min", u["dw_min"], "mm", "jisb1180"),
            Value(f"UNDER_HEAD.{size}.c.min", u["c"][0], "mm", "jisb1180"),
            Value(f"UNDER_HEAD.{size}.c.max", u["c"][1], "mm", "jisb1180"),
            Value(f"UNDER_HEAD.{size}.r_min", u["r_min"], "mm", "jisb1180"),
            Value(f"UNDER_HEAD.{size}.da_max", u["da_max"], "mm", "iso4014_westfield"),
        ]
    for size, c in CAP_SCREW.items():
        out += [
            Value(f"CAP_SCREW.{size}.socket", c["socket"], "mm", "jisb1176", None, c["s"][0]),
            Value(f"CAP_SCREW.{size}.b", c["b"], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.dk.min", c["dk"][0], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.dk.max", c["dk"][1], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.k.min", c["k"][0], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.k.max", c["k"][1], "mm", "jisb1176", None, METRIC[size]["d"]),
            Value(f"CAP_SCREW.{size}.s.min", c["s"][0], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.s.max_8.8_10.9", c["s"][1], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.s.max_12.9", c["s"][2], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.t_min", c["t_min"], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.w_min", c["w_min"], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.v_max", c["v_max"], "mm", "jisb1176"),
            Value(f"CAP_SCREW.{size}.dw_min", c["dw_min"], "mm", "jisb1176", None, c["dk"][0]),
            Value(f"CAP_SCREW.{size}.ds_min", c["ds_min"], "mm", "jisb1176", None, METRIC[size]["d"]),
            Value(f"CAP_SCREW.{size}.full_to", c["full_to"], "mm", "jisb1176"),
        ]
        out += [Value(f"CAP_SCREW.{size}.lengths.{length}", length, "mm", "jisb1176") for length in c["lengths"]]
    for size, b in BOLT.items():
        out += [
            Value(f"BOLT.{size}.b", b["b"], "mm", "jisb1180"),
            Value(f"BOLT.{size}.ds_min", b["ds_min"], "mm", "jisb1180", None, METRIC[size]["d"]),
        ]
        out += [Value(f"BOLT.{size}.lengths.{length}", length, "mm", "jisb1180") for length in b["lengths"]]
    out += [Value(f"LENGTHS.{length}", length, "mm", "iso4017") for length in LENGTHS]
    out += [Value(f"LENGTH_TOLERANCE.{longest}", tol, "mm", "iso4017") for longest, tol in LENGTH_TOLERANCE]
    return out


def _cells() -> list[Value]:
    out = []
    for fmt, c in CELLS.items():
        src, low = CELL_SOURCE[fmt], CELL_MIN[fmt]
        for dim in ("d", "L", "W", "T", "h"):
            if dim in c:
                minimum = low[f"{dim}_min"]
                lo_src = "inr21700_estimate" if fmt == "21700" else src
                out.append(Value(f"CELLS.{fmt}.{dim}", c[dim], "mm", src, minimum, c[dim]))
                out.append(Value(f"CELL_MIN.{fmt}.{dim}_min", minimum, "mm", lo_src))
        out.append(Value(f"CELLS.{fmt}.volts", c["volts"], "V", src))
        mass_src = "inr21700_estimate" if fmt == "21700" else src
        top = {"18650": 45.0, "21700": 70.0}.get(fmt)
        out.append(Value(f"CELLS.{fmt}.mass", c["mass"], "g", mass_src, 0.0 if top else None, top))
        if "nub_d" in c:
            # the datasheets give the largest + button and its least height; the flat-top cells, neither
            nub = {"AAA": (3.8, 0.8), "AA": (5.5, 1.0), "C": (7.5, 1.5), "D": (9.5, 1.5), "CR123A": (None, 1.0)}
            d_max, h_min = nub.get(fmt, (None, None))
            out.append(Value(f"CELLS.{fmt}.nub_d", c["nub_d"], "mm", src if d_max else "cell_nub", 0.0, d_max))
            out.append(Value(f"CELLS.{fmt}.nub_h", c["nub_h"], "mm", src if h_min else "cell_nub", h_min))
        out.append(Value(f"CELLS.{fmt}.F", c["F"], "N", "holder_design"))
        if "pre" in c:
            out.append(Value(f"CELLS.{fmt}.pre", c["pre"], "mm", "holder_design"))
    return out


def _materials() -> list[Value]:
    friction = {"zinc_clear": (0.13, 0.18), "zinc_yellow": (0.13, 0.18), "black_oxide": (0.12, 0.15)}
    out = [
        Value("variation.STEEL_DENSITY", variation.STEEL_DENSITY, "kg/m³", "steel"),
        Value("variation.DENSITY.stainless_a2", variation.DENSITY["stainless_a2"], "kg/m³", "alloys", 7480, 8000),
        Value("variation.DENSITY.brass", variation.DENSITY["brass"], "kg/m³", "alloys"),
        Value("batteries.G_STEEL", batteries.G_STEEL / 1e9, "GPa", "music_wire"),
        Value("batteries.ABS_DENSITY", batteries.ABS_DENSITY, "kg/m³", "abs", 1040, 1060),
        Value("batteries.FRICTION", batteries.FRICTION, "", "plastic_friction"),
    ]
    for finish, mu in variation.FRICTION.items():
        lo, hi = friction.get(finish, (None, None))
        src = "thread_friction" if finish in friction else "thread_friction_estimate"
        out.append(Value(f"variation.FRICTION.{finish}", mu, "", src, lo, hi))
    return out


def _threads() -> list[Value]:
    return [
        Value("fits: es of a g thread, constant", 15.0, "µm", "iso965"),
        Value("fits: es of a g thread, per mm of pitch", 11.0, "µm", "iso965"),
        Value("fits: Td2 grade 6, factor", 90.0, "µm", "iso965"),
        Value("fits: TD2 grade 6 / Td2 grade 6", 1.32, "", "iso965"),
        Value("fits.GRADE_5_RATIO", fits.GRADE_5_RATIO, "", "iso965_grade5"),
        *[Value(f"fits.DIAMETER_STEPS.{lo}-{hi}", hi, "mm", "iso965") for lo, hi in fits.DIAMETER_STEPS],
    ]


def values() -> list[Value]:
    """Every physical value of the generator, with its source."""
    return _fasteners() + _cells() + _materials() + _threads()


# Numbers in the code that are not about the real world, and so have no source: what they are.
NOT_PHYSICAL = {
    "DEFAULT_LENGTH, DEFAULT_BOLT_LENGTH": "the length generated when none is asked for: a choice, among the "
    "standard lengths",
    "fasteners.under_head": "a part built without a sampler takes the middle of each range the tables give "
    "(bearing face, fillet, plain shank): the standards give limits only",
    "batteries.FLOOR_T": "the thickness of the holders' floor: Quincaillerie's own holder design",
    "batteries.CONTACT_OFFSET, fasteners.CONTACT_OFFSET": "the distance at which contacts are generated: a "
    "simulation setting",
    "fits.SIM_FLOOR_MM": "the least clearance generated, so that the collision pieces can slide: a simulation "
    "setting (contract, docs/physics.md)",
    "fasteners.DETAIL, SEG_DEG": "mesh resolution",
    "materials.MATERIALS": "render appearance (colour, roughness), not a physical property",
    "declared.DECLARED (wear, defect, physics spreads)": "how much instances vary where no source gives a "
    "spread: declared and tested in docs/variation.md, estimates by construction",
}


def _fmt(x) -> str:
    return "" if x is None else f"{x:g}"


def table() -> str:
    """The Markdown tables of docs/sources.md."""
    out = ["| Value | | Unit | Range the source gives | Source |", "|---|---|---|---|---|"]
    for v in values():
        span = f"{_fmt(v.low)} to {_fmt(v.high)}" if v.low is not None or v.high is not None else ""
        span = span.replace(" to ", " to ") if span != " to " else ""
        out.append(f"| `{v.path}` | {v.value:g} | {v.unit} | {span} | [{v.source}](#{v.source}) |")
    out += ["", "### Sources", ""]
    for key, s in SOURCES.items():
        links = ", ".join(f"<{u}>" for u in s.urls)
        note = f" Estimate: {s.note}" if s.note else ""
        out.append(f'- <a id="{key}"></a>**{key}** ({s.kind}): {s.title}.{note}' + (f" {links}" if links else ""))
    out += ["", "### Numbers that are not physical values", ""]
    out += [f"- `{name}`: {why}." for name, why in NOT_PHYSICAL.items()]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(table())
