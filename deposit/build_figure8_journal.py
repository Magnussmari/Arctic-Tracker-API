#!/usr/bin/env python3
"""Figure 8 (IWT seizures; Figure 7 in the submitted numbering), drawn from the deposited seizure table rather than from CITES.

Why this exists. visualizations/scripts/figure7_iwt_seizures.py draws seizures
from the CITES Trade Database where source='I', labels its axes "Items Seized"
and prints "CITES Trade Database (source='I')" in the figure footer. The figure
caption describes a different figure: a count of seizure RECORDS from the
Stringham et al. dataset, n = 225 across 26 species, with no unit of quantity
because the source records none.

This script draws the figure the caption describes, from deposit/tables/illegal_trade_seizures.csv,
which is the deposited table the caption names. It reads nothing else: no
database connection, no live endpoint, no CITES shard.

The caption's three factual claims are re-derived here and the build refuses if
any of them moves: n = 225, 26 species, and every retained record carrying an
empty quantity and an empty unit. A caption that stops matching its own figure
is the defect this file exists to prevent.

Journal specification, not platform styling. Neutral greyscale, 1 unit = 1 pt,
width 180 mm, nothing below 5 pt. The warm platform palette is for the web pages.
"""
import collections, csv, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
SEIZ = REPO / "deposit/tables/illegal_trade_seizures.csv"
SPEC = REPO / "deposit/tables/species.csv"
OUT = HERE / "figures" / "figure8-seizures-journal.svg"

W = 512                      # 180 mm at 1 unit = 1 pt
MM_W = "180mm"
INK, MID, LIGHT, HAIR = "#111111", "#555555", "#8C8C8C", "#CCCCCC"
BAR, BAND, WHITE = "#4A4A4A", "#F2F2F2", "#FFFFFF"

MARGIN_L, PAD_R = 6, 14
NAME_W = 150                 # species name column
ROW_H = 10.5
HEAD_H = 22
PANEL_GAP = 20
FOOT_H = 58
MIN_PT = 5.0


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


class Canvas:
    def __init__(self):
        self.parts, self.texts, self.rects = [], [], []

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=6.0, fill=INK, anchor="start", weight="400",
             style="normal", family="Helvetica, Arial, sans-serif"):
        self.texts.append((size, s))
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" font-family="{family}" '
                 f'font-size="{size}" font-weight="{weight}" font-style="{style}" '
                 f'fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')

    def rect(self, x, y, w, h, fill=WHITE, stroke=None, width=0.6):
        self.rects.append((x, y, w, h))
        st = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ""
        self.add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
                 f'fill="{fill}"{st}/>')

    def line(self, x1, y1, x2, y2, stroke=HAIR, width=0.5):
        self.add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                 f'stroke="{stroke}" stroke-width="{width}"/>')


def load():
    """The 225 retained records, joined to species names, with the caption's
    claims re-derived rather than copied from the caption."""
    if not SEIZ.exists():
        raise SystemExit(f"  ABORT: {SEIZ} is not here; nothing is drawn from memory")
    rows = list(csv.DictReader(SEIZ.open()))
    names = {r["id"]: r["scientific_name"] for r in csv.DictReader(SPEC.open())}

    facts = {"records": len(rows), "species": len({r["species_id"] for r in rows})}
    nonempty_qty = sum(1 for r in rows if r["quantity"].strip())
    nonempty_unit = sum(1 for r in rows if r["unit"].strip())
    if nonempty_qty or nonempty_unit:
        raise SystemExit(
            f"  ABORT: the caption states that no retained record carries a quantity "
            f"or a unit, but {nonempty_qty} carry a quantity and {nonempty_unit} a "
            f"unit. Either the table changed or the caption is now false.")
    missing = {r["species_id"] for r in rows} - set(names)
    if missing:
        raise SystemExit(f"  ABORT: {len(missing)} species_id values are not in "
                         f"species.csv, so bars would be drawn without names")

    per_species = collections.Counter(names[r["species_id"]] for r in rows)
    per_product = collections.Counter(r["product_category"] for r in rows)
    if sum(per_species.values()) != facts["records"]:
        raise SystemExit("  ABORT: the species bars do not sum to the record count")
    if sum(per_product.values()) != facts["records"]:
        raise SystemExit("  ABORT: the product bars do not sum to the record count")
    return facts, per_species, per_product


def bars(c, y0, letter, title, counts, nmax, row_h, label_size=5.8):
    """One panel of horizontal bars, longest first. The value sits outside the
    bar end, never on top of it, so a dark bar never swallows its own number."""
    c.text(MARGIN_L, y0 + 8, letter, size=8.0, weight="700")
    c.text(MARGIN_L + 12, y0 + 8, title, size=7.0, weight="600")
    top = y0 + HEAD_H
    x0 = MARGIN_L + NAME_W + 6
    track = W - PAD_R - 26 - x0
    for i, (name, n) in enumerate(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))):
        y = top + i * row_h
        if i % 2 == 0:
            c.rect(MARGIN_L, y, W - MARGIN_L - PAD_R, row_h, fill=BAND)
        c.text(MARGIN_L + NAME_W, y + row_h - 3.0, name, size=label_size,
               anchor="end", style="italic" if " " in name and name[0].isupper() else "normal")
        bw = max(0.8, track * n / nmax)
        c.rect(x0, y + 2.0, bw, row_h - 4.6, fill=BAR)
        c.text(x0 + bw + 3, y + row_h - 3.2, str(n), size=label_size, fill=MID)
    bottom = top + len(counts) * row_h
    c.line(x0, bottom + 1, x0 + track, bottom + 1, stroke=MID, width=0.6)
    c.text(x0, bottom + 9.5, "number of seizure records", size=5.8, fill=MID)
    return bottom + 14


def build():
    facts, per_species, per_product = load()
    c = Canvas()
    nmax = max(per_species.values())
    y = 4
    y = bars(c, y, "a", f"Seizure records per species (n = {facts['records']} "
                        f"records, {facts['species']} species)", per_species, nmax, ROW_H)
    y += PANEL_GAP
    y = bars(c, y, "b", "Seizure records per product category", per_product,
             max(per_product.values()), 13.0, label_size=6.2)

    y += 10
    c.line(MARGIN_L, y, W - PAD_R, y, stroke=HAIR)
    y += 11
    for line in [
        "Source: Stringham et al. (2021) illegal wildlife trade records, as deposited in "
        "illegal_trade_seizures.csv.",
        "The axis is a count of records. No unit of quantity is shown because the source "
        "records none: all 225 retained",
        "records have an empty quantity and an empty unit, so no mass, volume or number of "
        "individuals can be derived.",
        "The source file holds 919 rows; 694 were excluded because the taxon named in the "
        "record is not the species the",
        "record was filed under, including 82 misattributed to Falco rusticolus alone. Each "
        "retained record carries the",
        "taxon name as the source reported it, so the attribution can be checked rather "
        "than trusted.",
    ]:
        c.text(MARGIN_L, y, line, size=5.4, fill=MID)
        y += 7.4
    h = y + 4

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{MM_W}" '
           f'viewBox="0 0 {W} {h:.0f}" font-family="Helvetica, Arial, sans-serif">'
           f'<rect width="{W}" height="{h:.0f}" fill="{WHITE}"/>'
           + "".join(c.parts) + "</svg>")
    return c, svg, h, facts


def assert_geometry(c, h):
    """Mechanical checks, because none of these is visible in the code."""
    fails = []
    for size, s in c.texts:
        if size < MIN_PT:
            fails.append(f"{size} pt label below the {MIN_PT} pt floor: {s[:40]!r}")
    for (x, y, w, hh) in c.rects:
        if x < 0 or y < 0 or x + w > W + 0.01 or y + hh > h + 0.01:
            fails.append(f"rect {(round(x,1), round(y,1), round(w,1), round(hh,1))} "
                         f"leaves the canvas {W}x{h:.0f}")
    if h / W > 1.6:
        fails.append(f"aspect {h/W:.2f} is taller than a journal page tolerates")
    return fails


def self_test():
    c = Canvas()
    c.text(0, 0, "too small", size=4.0)
    c.rect(-5, 0, 10, 10)
    fails = assert_geometry(c, 100)
    assert any("4.0 pt label" in f for f in fails), "SELF-TEST: the font floor is blind"
    assert any("leaves the canvas" in f for f in fails), "SELF-TEST: the bounds check is blind"
    print("  self-test: PASS (font floor and canvas bounds both fire)", file=sys.stderr)


def main():
    self_test()
    c, svg, h, facts = build()
    fails = assert_geometry(c, h)
    if fails:
        print("  ABORT: geometry", file=sys.stderr)
        for f in fails:
            print(f"    {f}", file=sys.stderr)
        return 2
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg)
    mm_h = round(h / 512 * 180, 1)
    print(f"  {facts['records']} records, {facts['species']} species, "
          f"all with empty quantity and unit", file=sys.stderr)
    print(f"  wrote {OUT.name}: {W} x {h:.0f} pt = 180.0 x {mm_h} mm", file=sys.stderr)
    print(f"  smallest label: {min(s for s, _ in c.texts)} pt", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
