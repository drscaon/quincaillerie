"""Draw the Quincaillerie logo (SVG, light and dark, plus a PNG) from DejaVu Sans Bold outlines.

The dots of the three i are hardware, in the metals of the material library: a zinc-plated hex
nut, a brass washer and a nickel-plated coin cell. Development tool:

    python scripts/make_logo.py docs/images
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MPath
from matplotlib.textpath import TextPath

INK, INK_DARK = "#16191D", "#E8EAED"
ACCENT, ACCENT_DARK = "#5B4A9E", "#AE9FEA"  # the letters "ai" (as the sister projects colour their "ai")
# the dots are drawn in the metals of the material library (quincaillerie.materials): a zinc-plated
# nut, a brass washer, a nickel-plated coin cell; the + mark is laser-etched (darker nickel)
METALS = {"nut": "zinc_clear", "washer": "brass", "cell": "nickel_can"}


def _srgb(c):
    """Linear base colour -> sRGB 0..1."""
    return tuple(12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055 for x in c)


def _hex(c):
    return "#" + "".join(f"{round(max(0, min(1, x)) * 255):02X}" for x in c)


def _metal_gradient(gid, color):
    """A brushed-metal look: a bright highlight band across a diagonal ramp of the metal's colour."""
    base = np.array(_srgb(color))
    stops = [(0.0, 0.92), (0.3, 1.12), (0.42, 0.80), (0.7, 0.58), (1.0, 0.74)]
    s = "".join(f'<stop offset="{o}" stop-color="{_hex(base * k)}"/>' for o, k in stops)
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1">{s}</linearGradient>'


WORD = "Qu\u0131nca\u0131ller\u0131e"  # dotless i: the dots are drawn as nuts
AI = (5, 6)  # indices of "a" and the second "ı"
SCALE = 1.0


def _d(path: MPath, dx: float, dy: float, s: float, height: float) -> str:
    out = []
    verts, codes = path.vertices, path.codes
    i = 0
    while i < len(verts):
        c = codes[i]
        x, y = verts[i]
        X, Y = dx + x * s, height - (dy + y * s)
        if c == MPath.MOVETO:
            out.append(f"M{X:.2f},{Y:.2f}")
            i += 1
        elif c == MPath.LINETO:
            out.append(f"L{X:.2f},{Y:.2f}")
            i += 1
        elif c == MPath.CURVE3:
            (x2, y2) = verts[i + 1]
            out.append(f"Q{X:.2f},{Y:.2f} {dx + x2 * s:.2f},{height - (dy + y2 * s):.2f}")
            i += 2
        elif c == MPath.CURVE4:
            (x2, y2), (x3, y3) = verts[i + 1], verts[i + 2]
            out.append(
                f"C{X:.2f},{Y:.2f} {dx + x2 * s:.2f},{height - (dy + y2 * s):.2f} "
                f"{dx + x3 * s:.2f},{height - (dy + y3 * s):.2f}"
            )
            i += 3
        elif c == MPath.CLOSEPOLY:
            out.append("Z")
            i += 1
        else:
            i += 1
    return "".join(out)


def _hexagon(cx, cy, r, rot=0.0):
    pts = [(cx + r * np.cos(rot + k * np.pi / 3), cy + r * np.sin(rot + k * np.pi / 3)) for k in range(6)]
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"


def _circle(cx, cy, r):
    # with fill-rule evenodd, a circle inside the hexagon is a hole
    arc = f"A{r:.2f},{r:.2f} 0 1,0"
    return f"M{cx + r:.2f},{cy:.2f} {arc} {cx - r:.2f},{cy:.2f} {arc} {cx + r:.2f},{cy:.2f} Z"


def logo(ink: str, accent: str, suffix: str = "") -> str:
    from matplotlib.font_manager import findfont, get_font

    from quincaillerie.materials import MATERIALS

    fp = FontProperties(family="DejaVu Sans", weight="bold")
    font = get_font(findfont(fp))
    font.set_size(100, 72)
    pen, glyphs, xs = 0.0, [], []
    for ch in WORD:
        glyphs.append((pen, TextPath((0, 0), ch, size=100, prop=fp)))
        adv = font.load_char(ord(ch)).linearHoriAdvance / 65536
        if ch == "\u0131":
            ext = glyphs[-1][1].get_extents()
            xs.append(pen + (ext.x0 + ext.x1) / 2)
        pen += adv
    pad = 24
    s = SCALE
    x0 = min(g.get_extents().x0 + p for p, g in glyphs)
    x1 = max(g.get_extents().x1 + p for p, g in glyphs)
    width = (x1 - x0) * s + 2 * pad
    height = 132.0
    base = 30.0  # baseline height from the bottom
    dx, dy = pad - x0 * s, base
    xs = [dx + x * s for x in xs]
    cy = height - (dy + 74 * s)  # centre of the nuts, where the dots of the i would be

    def letters(keep) -> str:
        return "".join(_d(g, dx + p * s, dy, s, height) for k, (p, g) in enumerate(glyphs) if keep(k))

    parts = [
        f'<path fill="{ink}" d="{letters(lambda k: k not in AI)}"/>',
        f'<path fill="{accent}" d="{letters(lambda k: k in AI)}"/>',
    ]
    nut, washer, cell = xs
    ids = {k: f"metal_{k}{suffix}" for k in METALS}
    defs = "".join(_metal_gradient(ids[k], MATERIALS[m]["color"]) for k, m in METALS.items())
    rim = ' stroke="#00000033" stroke-width="0.8"'  # a thin edge, so the bright metal reads on white
    d = _hexagon(nut, cy, 12.5, np.radians(12)) + _circle(nut, cy, 5.0)
    parts.append(f'<path fill="url(#{ids["nut"]})" fill-rule="evenodd"{rim} d="{d}"/>')
    ring = _circle(washer, cy, 12.5) + _circle(washer, cy, 6.0)
    parts.append(f'<path fill="url(#{ids["washer"]})" fill-rule="evenodd"{rim} d="{ring}"/>')
    parts.append(f'<circle cx="{cell:.2f}" cy="{cy:.2f}" r="12.5" fill="url(#{ids["cell"]})"{rim}/>')
    mark = _hex(np.array(_srgb(MATERIALS["nickel_can"]["color"])) * 0.55)
    parts.append(
        f'<path fill="none" stroke="{mark}" stroke-width="3.0" stroke-linecap="round" '
        f'd="M{cell - 5.5:.2f},{cy:.2f} H{cell + 5.5:.2f} M{cell:.2f},{cy - 5.5:.2f} V{cy + 5.5:.2f}"/>'
    )
    parts.insert(0, f"<defs>{defs}</defs>")
    w = int(np.ceil(width))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {int(height)}" width="{w}" '
        f'height="{int(height)}" role="img" aria-label="Quincaillerie"><title>Quincaillerie</title>'
        + "".join(parts)
        + "</svg>\n"
    )


def main(out: str = "docs/images"):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "logo.svg").write_text(logo(INK, ACCENT), encoding="utf-8")
    (out / "logo-dark.svg").write_text(logo(INK_DARK, ACCENT_DARK, "_dark"), encoding="utf-8")
    try:
        import cairosvg

        cairosvg.svg2png(url=str(out / "logo.svg"), write_to=str(out / "logo.png"), output_height=300)
    except ImportError:
        print("cairosvg not installed: logo.png not written", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:])
