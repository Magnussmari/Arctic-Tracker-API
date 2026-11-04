#!/usr/bin/env python3
"""Figure 12 (What the audit questions measure), redrawn so the figure says what the paper says.

WHAT CHANGED
------------
The submitted version of this figure (then numbered Figure 11) draws a black arrow from the Audit questions node up
into a CITES impact node. That arrow is the causal claim Reviewer 2 asked to
have removed. The text was revised accordingly; this script redraws the artwork
so that the arrow is gone from the figure as well.

WHAT THE PAPER NOW SAYS
-----------------------
The seven questions divide. Q1 to Q6 ask whether a species is listed, whether
the Convention's measures are in place, whether trade is reported and how it is
distributed. They measure implementation, a property of the regime. Q7 asks the
outcome question, and the paper answers it by reporting the post-listing status
trajectory, a property of the species. The two are reported separately and are
not joined, because the design cannot support the join.

So the figure has two panels and nothing connects them. The gap between panel a
and panel b is the figure's argument, in the same way that the empty LLM row is
the argument of Figure 13: the reader is meant to notice that the arrow they
expect is absent, which is why the legend names it.

Drawn to the journal's specification, not the platform's, for the reasons set
out at the top of build_figure13_journal.py: neutral greyscale, 1 unit = 1 pt,
180 mm wide, nothing below the 5 pt floor.

Usage:
  python3 deposit/build_figure12_journal.py
"""
import pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_figure13_journal import (            # noqa: E402
    Canvas, cell_text, wrap, assert_geometry, esc,
    INK, MID, LIGHT, HAIR, BAND, WHITE, W, MM_W,
)

OUT = HERE / "figures" / "figure12-audit-questions-journal.svg"

MARGIN_L = 6
LABEL_W = 92
PAD_R = 14
HEAD_H = 22
PANEL_LB = 16
GAP = 26
LEGEND_H = 74

# Panel a: the six implementation questions, each with the record it reads.
# Grouped by evidence domain, because six separate columns of one question each
# would be six columns saying the same thing about the regime.
IMPLEMENTATION = [
    ("Ratification",        "Q1", "CITES Parties list", "implementation"),
    ("Listing status",      "Q2", "CITES and CMS appendices; Species+",
                                  "implementation"),
    ("Enforcement",         "Q3", "National reports; CITES-LEX; illegal-trade "
                                  "records", "implementation"),
    ("Cooperation",         "Q4", "CITES agreements with CBMP, NAMMCO and "
                                  "Arctic MEAs", "implementation"),
    # Q5 and Q6 are descriptive. They ask what the recorded trade is and how it
    # is distributed; the answer is a distribution, not a yes. Labelling them
    # "implementation" said the regime was being measured where the record was.
    # The visible heading was corrected and the SVG's <desc> was not, so for a
    # month the drawing said one thing and its machine-readable description said
    # the superseded thing - which is the version a screen reader gets. The
    # <desc> now carries the same wording as the visible heading.
    ("Trade recorded",      "Q5", "CITES Trade Database", "trade record"),
    ("Trade distribution",  "Q6", "CITES Trade Database, by party",
                                  "trade record"),
]

# Panel b: the one outcome question, and the one record that answers it.
OUTCOME = ("Status trajectory", "Q7",
           "IUCN Red List assessment history: first and latest comparable "
           "global or European regional assessments")

ROWS_A = [("QUESTION", "what is asked"),
          ("RECORD", "what answers it"),
          ("MEASURES", "the construct")]


def band(c, x, y, w, h, i):
    if i % 2 == 0:
        c.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{BAND}"/>')


def panel_a(c, y0, grid_w):
    n = len(IMPLEMENTATION)
    slot = (grid_w - LABEL_W - PAD_R) / n
    c.text(MARGIN_L, y0 + 10, "a", size=8.5, weight="700")
    c.text(MARGIN_L + 14, y0 + 10,
           "What the six non-outcome questions measure. Four read the "
           "regime; two read the trade record.", size=7)
    top = y0 + PANEL_LB

    # column heads
    for j, (name, q, _, _m) in enumerate(IMPLEMENTATION):
        cx = LABEL_W + slot * (j + 0.5)
        c.text(cx, top + 9, q, size=7.5, anchor="middle", weight="700")
        for k, line in enumerate(wrap(name, slot - 8, 6.0)):
            c.text(cx, top + 18 + k * 7, line, size=6.0, anchor="middle",
                   fill=MID)
    head = top + HEAD_H + 8

    rows = [[q for _, q, _, _m in IMPLEMENTATION],
            [rec for _, _, rec, _m in IMPLEMENTATION],
            [m for _, _, _r, m in IMPLEMENTATION]]

    # The record box is sized from the text it has to hold. It used to be a
    # fixed 26 pt, which fitted two wrapped lines; Q3 wrapped to three and the
    # third line printed below the box, inside the row underneath it. Nothing
    # in the markup showed that. The render did, immediately.
    bw_a = slot - 8
    wrapped = [wrap(r, bw_a - 6, 5.5) for r in rows[1]]
    box_h = max(len(x) for x in wrapped) * 7 + 12
    heights = [0, box_h + 8, 24]   # two label lines at +11 and +19 both have to sit inside the band

    y = head
    # the QUESTION row is the column head itself, so only two bands are drawn
    for r, (label, sub) in enumerate(ROWS_A[1:], start=1):
        h = heights[r]
        band(c, 0, y, grid_w, h, r)
        c.text(MARGIN_L, y + 11, label, size=6.0, weight="700", spacing="0.06em")
        c.text(MARGIN_L, y + 19, sub, size=5.5, fill=LIGHT)
        for j in range(n):
            cx = LABEL_W + slot * (j + 0.5)
            if r == 1:
                bx, bw = LABEL_W + slot * j + 4, slot - 8
                c.box(bx, y + 4, bw, box_h, stroke=HAIR)
                cell_text(c, cx, y + 13, wrapped[j], size=5.5)
            else:
                c.text(cx, y + 11, rows[r][j], size=6.0, anchor="middle",
                       weight="700")
        y += h
    return y


def panel_b(c, y0, grid_w):
    name, q, rec = OUTCOME
    c.text(MARGIN_L, y0 + 10, "b", size=8.5, weight="700")
    c.text(MARGIN_L + 14, y0 + 10,
           "Outcome. One question about the species, read from one record.",
           size=7)
    top = y0 + PANEL_LB
    cx = LABEL_W + (grid_w - LABEL_W - PAD_R) / 2
    c.text(cx, top + 9, q, size=7.5, anchor="middle", weight="700")
    c.text(cx, top + 18, name, size=6.0, anchor="middle", fill=MID)
    y = top + HEAD_H + 8

    bw_probe = (grid_w - LABEL_W - PAD_R) * 0.78
    band(c, 0, y, grid_w, len(wrap(rec, bw_probe - 8, 5.5)) * 7 + 20, 1)
    c.text(MARGIN_L, y + 11, "RECORD", size=6.0, weight="700", spacing="0.06em")
    c.text(MARGIN_L, y + 19, "what answers it", size=5.5, fill=LIGHT)
    bw = (grid_w - LABEL_W - PAD_R) * 0.78
    bx = cx - bw / 2
    lines = wrap(rec, bw - 8, 5.5)
    bh = len(lines) * 7 + 12
    c.box(bx, y + 4, bw, bh, stroke=HAIR)
    cell_text(c, cx, y + 13, lines, size=5.5)
    y += bh + 8

    c.text(MARGIN_L, y + 11, "MEASURES", size=6.0, weight="700",
           spacing="0.06em")
    c.text(MARGIN_L, y + 19, "the construct", size=5.5, fill=LIGHT)
    c.text(cx, y + 11, "post-listing status trajectory", size=6.0,
           anchor="middle", weight="700")
    return y + 16


def build():
    c = Canvas()
    grid_w = W - PAD_R
    y = 8
    y = panel_a(c, y, grid_w) + GAP

    # The absent connector, stated where it would have been drawn.
    c.add(f'<line x1="{MARGIN_L}" y1="{y - GAP / 2}" x2="{grid_w}" '
          f'y2="{y - GAP / 2}" stroke="{HAIR}" stroke-width="0.6" '
          f'stroke-dasharray="2,3"/>')
    c.text(grid_w, y - GAP / 2 + 9,
           "no connector crosses this line", size=5.5, fill=LIGHT,
           anchor="end")

    y = panel_b(c, y, grid_w) + 10

    c.add(f'<line x1="{MARGIN_L}" y1="{y}" x2="{grid_w}" y2="{y}" '
          f'stroke="{HAIR}" stroke-width="0.6"/>')
    ly = y + 12
    for label, note in [
        ("Q1 to Q7", "the seven standardised audit questions. They are not the "
                     "seven pipeline steps S1 to S7, which are Figure 13."),
        ("Panel a", "four questions read the regime and two read the trade "
                    "record. Neither kind measures a conservation outcome: "
                    "each can hold for a species that is declining."),
        ("Panel b", "the conservation outcome, a property of the species, "
                    "derived from Red List category change and not scored on "
                    "the same instrument."),
        ("No connector", "the panels are not joined. The paper reports both and "
                         "makes no claim that implementation produces the "
                         "trajectory: the dominant Arctic threats lie outside "
                         "the Convention's trade-management mandate."),
    ]:
        c.text(MARGIN_L, ly, label, size=5.5, weight="700")
        lines = wrap(note, grid_w - 92, 5.5)
        for k, line in enumerate(lines):
            c.text(76, ly + k * 7, line, size=5.5, fill=MID)
        ly += max(8, len(lines) * 7 + 2)

    height = round(ly + 6)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" role="img"
     aria-labelledby="fig11-title fig11-desc"
     viewBox="0 0 {W} {height}" width="{MM_W}">
<title id="fig11-title">Audit questions: implementation and outcome</title>
<desc id="fig11-desc">Two panels with no connector between them. Panel a lists \
the six non-outcome audit questions and the published record that answers each: \
Q1 to Q4 read the regime, which is implementation, and Q5 and Q6 read the trade \
record itself, which is neither implementation nor an outcome. Panel b shows the \
single outcome question and the IUCN Red List assessment history that answers \
it. The absence of any line between the panels is the figure's point: the paper \
reports implementation and post-listing status trajectory separately and does \
not claim that one produces the other.</desc>
<defs>
  <marker id="ar" markerWidth="6" markerHeight="5" refX="5.4" refY="2.5"
          orient="auto"><polygon points="0 0, 6 2.5, 0 5" fill="{MID}"/></marker>
</defs>
<rect width="100%" height="100%" fill="{WHITE}"/>
{chr(10).join(c.parts)}
</svg>
'''
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(svg)
    return c, height, svg


def self_test():
    """The figure's whole claim is an absence, so assert the absence."""
    c, h, svg = build()
    assert not c.arrows, (
        f"SELF-TEST: the figure drew {len(c.arrows)} connector(s). "
        "Figure 12 exists to show that none of them is there.")
    assert "CITES impact" not in svg, \
        "SELF-TEST: the node the arrow pointed at is back"
    assert "Q7" in svg and "Q1" in svg, "SELF-TEST: the questions are missing"
    print("  self-test: PASS (no connector drawn, no impact node, Q1 to Q7 "
          "present)", file=sys.stderr)


def render_png():
    """Write the PNG from the SVG this run produced.

    Until 6 October 2026 the PNG was made by hand, once. The visible panel
    heading was then corrected in the generator and the PNG was not remade, so
    for five days the deposit carried two incompatible artworks for this figure (then Figure 11) -
    and the stale one, the PNG, was the one that contradicted the caption, which
    says Q5 and Q6 read the trade record rather than measuring implementation.
    Regenerating the PNG from the SVG on every run keeps the two in step.

    Rendered at 600 dpi on the 180 mm width, which is the journal's upper bound,
    so the raster is not the thing that limits the figure.
    """
    import shutil
    import subprocess
    png = OUT.with_suffix(".png")
    tool = shutil.which("rsvg-convert") or shutil.which("cairosvg")
    if tool is None:
        return [f"no SVG renderer on this machine, so {png.name} was not "
                f"rewritten and may disagree with {OUT.name}"]
    width = round(180 / 25.4 * 600)
    if tool.endswith("rsvg-convert"):
        cmd = [tool, "-w", str(width), "-o", str(png), str(OUT)]
    else:
        cmd = [tool, str(OUT), "-o", str(png), "--output-width", str(width)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return [f"{png.name} could not be rendered: "
                f"{(r.stderr or r.stdout).strip()[:160]}"]
    print(f"  wrote {png.name}: {width} px wide at 600 dpi on 180 mm",
          file=sys.stderr)
    return []


if __name__ == "__main__":
    self_test()
    canvas, h, svg = build()
    problems = assert_geometry(canvas, h)
    for p in problems:
        print(f"  FAIL  {p}", file=sys.stderr)
    mm_h = round(h / W * 180, 1)
    print(f"  wrote {OUT.name}: {W} x {h} pt = 180.0 x {mm_h} mm", file=sys.stderr)
    print(f"  {len(canvas.boxes)} boxes, {len(canvas.arrows)} connectors",
          file=sys.stderr)
    if not problems:
        problems += render_png()
    sys.exit(1 if problems else 0)
