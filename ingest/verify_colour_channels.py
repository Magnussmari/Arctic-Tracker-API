#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-13
"""V-15: no figure may encode a category by colour alone.

WHY THIS EXISTS
---------------
The paper states that categorical distinctions in the figures carry a second,
non-colour channel. The conservation-status figures use the IUCN Red List
category palette — correctly, since it is what the field reads — and it is a
red-to-green ramp, which compresses adjacent categories under deuteranopia.

The palette is not the thing to change. Being the only channel is. This asserts
that every figure carrying IUCN categories also draws them as text.
"""
from __future__ import annotations

import itertools
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SCRIPTS = ROOT / "visualizations" / "scripts"

IUCN = {"CR": "#D81E05", "EN": "#FC7F3F", "VU": "#F9E814",
        "NT": "#CCE226", "LC": "#60C659"}
INDISTINGUISHABLE = 20.0


def _mul(m, v):
    return tuple(sum(m[i][j] * v[j] for j in range(3)) for i in range(3))


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c):
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


_M = ((0.31399, 0.63951, 0.04649), (0.15537, 0.75789, 0.08670), (0.01775, 0.10945, 0.87259))
_MI = ((5.47221, -4.6419, 0.16963), (-1.1252, 2.29317, -0.1678), (0.02980, -0.1932, 1.16364))
_SIM = {"deuteranopia": ((1, 0, 0), (0.49421, 0, 1.24827), (0, 0, 1)),
        "protanopia": ((0, 2.02344, -2.52581), (0, 1, 0), (0, 0, 1))}


def simulate(hexc: str, kind: str):
    h = hexc.lstrip("#")
    rgb = tuple(_lin(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))
    return tuple(_gam(c) for c in _mul(_MI, _mul(_SIM[kind], _mul(_M, rgb))))


def _lab(rgb):
    X, Y, Z = _mul(((0.4124, 0.3576, 0.1805), (0.2126, 0.7152, 0.0722),
                    (0.0193, 0.1192, 0.9505)),
                   tuple(_lin(c) if c > 1e-9 else 0 for c in rgb))
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(X / 0.95047), f(Y / 1.0), f(Z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(a, b):
    return math.dist(_lab(a), _lab(b))


def main() -> int:
    if not SCRIPTS.is_dir():
        print(f"V-15 FAIL: {SCRIPTS} is absent.")
        return 1

    collapsing = {}
    for kind in _SIM:
        pairs = [(a, b, delta_e(simulate(IUCN[a], kind), simulate(IUCN[b], kind)))
                 for a, b in itertools.combinations(IUCN, 2)]
        collapsing[kind] = [p for p in pairs if p[2] < INDISTINGUISHABLE]

    worst = min(d for ps in collapsing.values() for *_, d in ps) if any(collapsing.values()) else None
    if worst is None:
        # Guard the guard: if the palette ever simulates as fully separable,
        # either the constants changed or the simulation broke. Do not quietly
        # pass — that would retire a real requirement on a silent result.
        print("V-15 FAIL: the IUCN palette simulates as fully distinguishable, "
              "which it is not. The simulation is wrong.")
        return 1

    # Every script drawing IUCN categories must draw them as text as well.
    failures = []
    checked = 0
    # The scripts the runner actually drives, read from the runner. Globbing
    # figure*.py caught figure1_simple.py, which is a leftover that produces no
    # published figure — a real colour-only plot that nobody publishes is not a
    # defect in the paper. Derive the list; do not keep a second copy of it.
    runner = (ROOT / "visualizations" / "make_all_figures.py").read_text()
    driven = set(re.findall(r'\("figure\d+",\s*"([^"]+\.py)"\)', runner))
    if not driven:
        print("V-15 FAIL: could not read the figure list out of make_all_figures.py. "
              "Refusing to check an empty set, which would pass for free.")
        return 1

    for f in sorted(SCRIPTS.glob("figure*.py")):
        if f.name not in driven:
            continue
        src = f.read_text()
        # In scope if the figure encodes IUCN *categories*, not if it happens to
        # use the IUCN hex values.
        #
        # Matching on hex was how this gate missed the one figure it was built
        # for. figure5_status_heatmap.py defines its own colour ramp, so it
        # scored zero palette hits and was skipped entirely — and the seeded
        # test therefore passed while the heatmap had its cell labels stripped.
        # The check was looking where I expected the defect to be.
        codes = sum(1 for c in IUCN if re.search(rf"['\"]{c}['\"]", src))
        ramps = re.search(r"colorscale|marker\s*=\s*dict\(\s*color|color_discrete", src)
        if codes < 3 or not ramps:
            continue
        checked += 1
        # Only marks that put text on the plotted data count.
        #
        # A bare `text=` was too loose: it matched the colourbar title
        # `text="IUCN Threat Status"`, so a heatmap with the labels stripped out
        # of its cells still passed. Seeding caught it. A legend or an axis
        # title tells you what the colours mean in general; it does not tell you
        # which category this cell is.
        #
        # hovertext does not count either: it does not exist in a printed
        # figure, and the manuscript figure is printed.
        # The distinction that actually separates the two cases is a variable
        # versus a string literal. A colourbar or axis title is text="Something";
        # per-datum text is text=cell_text or text=change_values. The first tells
        # a reader what the colours mean in general, the second tells them which
        # category this mark is. Only the second is a channel.
        drawn = re.search(r"""texttemplate|add_annotation|\btext=(?!["'])""", src)
        if not drawn:
            failures.append(f.name)

    print(f"V-15 colour channels: {checked} figure script(s) use the IUCN category palette")
    for kind, ps in collapsing.items():
        worst_pair = min(ps, key=lambda p: p[2])
        print(f"  under {kind}: {len(ps)} of 10 category pairs collapse "
              f"(worst {worst_pair[0]}/{worst_pair[1]} deltaE={worst_pair[2]:.1f})")

    if failures:
        print(f"\nV-15 FAIL: these draw IUCN categories with colour as the only "
              f"channel:\n  " + "\n  ".join(failures))
        print("\nA reader with deuteranopia cannot read them. Draw the category "
              "code as text.")
        return 1

    print("V-15 PASS: every figure using the palette also draws the category as text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
