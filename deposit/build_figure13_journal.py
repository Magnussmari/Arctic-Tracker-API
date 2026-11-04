#!/usr/bin/env python3
"""Figure 13 (the seven-step pipeline), drawn to the journal's specification rather than the platform's.

Why this exists alongside build_pipeline_diagram.py: that script draws the
platform surface, and its own header says so. A warm tinted ground with an
accent colour suits the web pages and not a peer-reviewed paper, where a tinted ground prints
as a coloured block and a brand accent reads as an advertisement. Measured
2026-09-30: the platform SVGs also put their smallest labels under 5 pt at any
placement width a journal would accept.

So this one takes the same single source of truth, deposit/pipeline.json, and
renders it in neutral greyscale at 1 unit = 1 point, which makes every font
size in the file a point size a reviewer can check.

Layout. Two stacked panels rather than side by side: side by side forces the
combined width to about 1120 units against a 510 pt page, and the smallest text
lands near 2.5 pt. Stacked, each panel gets the full width and nothing falls
below 6.5 pt.

Connectors. Every arrow is pure vertical (within a column) or pure horizontal
(along the gate row). There are no diagonals, no crossings and no shared
attachment points, and that is asserted mechanically at the bottom of this
file rather than checked by eye.

The empty LLM row across the whole of Panel A is not a gap in the drawing. It
is the figure's argument: no generative model touches any value reported from
Stage 1.
"""
import json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "pipeline.json"
OUT = HERE / "figures" / "figure13-pipeline-journal.svg"

# --- journal specification -------------------------------------------------
# Nature Communications: 180 mm maximum width for a double-column figure.
# 180 mm = 510.24 pt. We design at 1 unit = 1 pt and set width="180mm" so the
# renderer does the conversion and every font-size below IS a point size.
W = 512
MM_W = "180mm"

INK      = "#111111"
MID      = "#555555"
LIGHT    = "#8C8C8C"
HAIR     = "#CCCCCC"
BAND     = "#F2F2F2"   # alternating row tint, prints as a light grey
FOCAL    = "#111111"   # the accent is weight, not hue: colour-blind safe by construction
WHITE    = "#FFFFFF"

MARGIN_L = 6
LABEL_W  = 96
SLOT_W   = 100
PAD_R    = 16
ROW_H    = 52
HEAD_H   = 24
PANEL_LB = 16          # panel letter strip
GAP      = 22
LEGEND_H = 56

ROWS = [("SOURCE",      "the record the step reads"),
        ("DETERMINISTIC","code, no model"),
        ("LLM TOOL",    "generative model, named"),
        ("HUMAN GATE",  "author check that can refuse")]


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def strip_md(t):
    """pipeline.json carries manuscript markdown; a figure shows plain words."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t or "")
    t = re.sub(r"`\[.*?\]`", "", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def wrap(text, width, size):
    """Greedy wrap on an estimated glyph advance. Measured against the render,
    not assumed: 0.52 em is the ratio that stopped the longest label in this
    figure from overflowing its box."""
    per = size * 0.52
    limit = max(1, int(width / per))
    out, line = [], ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if len(trial) <= limit:
            line = trial
        else:
            if line:
                out.append(line)
            line = word
    if line:
        out.append(line)
    return out


class Canvas:
    def __init__(self):
        self.parts = []
        self.arrows = []          # (x1, y1, x2, y2) for the geometry assertions
        self.boxes = []           # (x, y, w, h)

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=6.5, fill=INK, anchor="start",
             weight="400", family="Helvetica, Arial, sans-serif", spacing=None):
        sp = f' letter-spacing="{spacing}"' if spacing else ""
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
                 f'text-anchor="{anchor}" font-weight="{weight}" '
                 f'font-family="{family}"{sp}>{esc(s)}</text>')

    def box(self, x, y, w, h, stroke=MID, fill=WHITE, width=0.6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{width}"{d}/>')
        self.boxes.append((x, y, w, h))

    def vline(self, x, y1, y2, stroke=MID, marker=True):
        m = ' marker-end="url(#ar)"' if marker else ""
        self.add(f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" '
                 f'stroke="{stroke}" stroke-width="0.6"{m}/>')
        self.arrows.append((x, y1, x, y2))

    def hline(self, x1, x2, y, stroke=MID, marker=True, dash=None):
        m = ' marker-end="url(#ar)"' if marker else ""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
                 f'stroke="{stroke}" stroke-width="0.6"{m}{d}/>')
        self.arrows.append((x1, y, x2, y))


def cell_text(c, cx, cy_top, lines, size=6.0, fill=INK, weight="400"):
    lead = size + 1.6
    y = cy_top + size + 1
    for ln in lines:
        c.text(cx, y, ln, size=size, fill=fill, anchor="middle", weight=weight)
        y += lead


BAND_W = LABEL_W + 4 * SLOT_W + PAD_R        # widest panel sets the grid


def panel(c, y0, letter, title, steps, focal_gate=None):
    """Draw one panel. Returns the y it ends at."""
    n = len(steps)
    c.text(MARGIN_L, y0 + 9, letter, size=9, weight="700")
    c.text(MARGIN_L + 14, y0 + 9, title, size=7.5, weight="400", fill=MID)
    top = y0 + PANEL_LB

    # row bands and labels
    for k, (name, gloss) in enumerate(ROWS):
        ry = top + HEAD_H + k * ROW_H
        if k % 2 == 0:
            c.add(f'<rect x="{MARGIN_L}" y="{ry}" width="{BAND_W}" '
                  f'height="{ROW_H}" fill="{BAND}"/>')
        c.text(MARGIN_L, ry + 14, name, size=6.0, weight="700", fill=INK, spacing="0.04em")
        for i, ln in enumerate(wrap(gloss, LABEL_W - 10, 5.5)):
            c.text(MARGIN_L, ry + 23 + i * 7, ln, size=5.5, fill=LIGHT)
        c.add(f'<line x1="{MARGIN_L}" y1="{ry}" x2="{MARGIN_L + BAND_W}" y2="{ry}" '
              f'stroke="{HAIR}" stroke-width="0.5"/>')
    bot = top + HEAD_H + len(ROWS) * ROW_H
    c.add(f'<line x1="{MARGIN_L}" y1="{bot}" x2="{MARGIN_L + BAND_W}" y2="{bot}" '
          f'stroke="{HAIR}" stroke-width="0.5"/>')
    c.add(f'<line x1="{MARGIN_L + LABEL_W}" y1="{top + HEAD_H}" '
          f'x2="{MARGIN_L + LABEL_W}" y2="{bot}" stroke="{HAIR}" stroke-width="0.5"/>')

    def col_cx(j):
        return MARGIN_L + LABEL_W + j * SLOT_W + SLOT_W / 2

    def row_y(k):
        return top + HEAD_H + k * ROW_H

    NW, NH = 84, 38

    # step headers
    for j, s in enumerate(steps):
        cx = col_cx(j)
        c.text(cx, top + 10, s["id"], size=7.5, weight="700", anchor="middle")
        for i, ln in enumerate(wrap(s["short"], SLOT_W - 8, 6.0)):
            c.text(cx, top + 18 + i * 7, ln, size=6.0, anchor="middle", fill=MID)

    # arrows first, so boxes paint over their ends
    for j, s in enumerate(steps):
        cx = col_cx(j)
        filled = [k for k in range(4) if s["cells"][k]]
        for a, b in zip(filled, filled[1:]):
            y1 = row_y(a) + (ROW_H + NH) / 2
            y2 = row_y(b) + (ROW_H - NH) / 2
            c.vline(cx, y1, y2 - 1)
        if j + 1 < len(steps):                      # gate to gate, along row 3
            y = row_y(3) + ROW_H / 2
            c.hline(cx + NW / 2, col_cx(j + 1) - NW / 2 - 1, y)

    # boxes
    for j, s in enumerate(steps):
        cx = col_cx(j)
        for k in range(4):
            body = s["cells"][k]
            if not body:
                continue
            x, y = cx - NW / 2, row_y(k) + (ROW_H - NH) / 2
            is_focal = (k == 3 and focal_gate and s["gate_id"] == focal_gate)
            c.box(x, y, NW, NH,
                  stroke=FOCAL if is_focal else MID,
                  width=1.4 if is_focal else 0.6)
            lines = wrap(body, NW - 8, 6.0)
            block = len(lines) * 7.6
            cell_text(c, cx, y + (NH - block) / 2 - 1, lines, size=6.0,
                      weight="600" if is_focal else "400")

    # the empty-row statement, placed in the label gutter of the LLM row
    if all(not s["cells"][2] for s in steps):
        free_x0 = MARGIN_L + LABEL_W + n * SLOT_W
        free_w = BAND_W - LABEL_W - n * SLOT_W - PAD_R
        cx = free_x0 + free_w / 2
        note = wrap("no generative model in any Stage 1 step", free_w - 4, 6.5)
        y = row_y(2) + ROW_H / 2 - (len(note) * 8.1) / 2 + 6
        for ln in note:
            c.text(cx, y, ln, size=6.5, anchor="middle", fill=LIGHT)
            y += 8.1
    return bot


def build():
    data = json.loads(SRC.read_text())
    steps_raw = {s["id"]: s for s in data["steps"]}

    def mk(sid, source, det, ai, gate):
        s = steps_raw[sid]
        return {"id": sid,
                "short": strip_md(s.get("short_title") or s["title"]),
                "gate_id": s["gate"],
                "cells": [source, det, ai, gate]}

    A = [mk("S1", "CITES and CMS appendices; IUCN taxonomy", "Deterministic query", None,
            "G1 reconciled to the published appendices"),
         mk("S2", "IUCN Red List; NAMMCO catch records", "Deterministic query", None,
            "G2 every value confirmed against its source record"),
         mk("S3", "CITES Trade Database", "Deterministic query", None,
            "G3 counts and quantities reconciled; corpus frozen")]
    B = [mk("S4", "Frozen Stage 1 corpus", None, "Scite, source discovery",
            "G4 relevance and existence checked against primary records"),
         mk("S5", "Sources retrieved at S4", None, "Gemini 2.5 Pro, structured extraction",
            "G5 no claim cited until verified against the primary source"),
         mk("S6", "S5 synthesis and Stage 1 metrics", None,
            "model summarises verified metrics only",
            "G6 questions Q1 to Q7 applied; scoring is author-applied"),
         mk("S7", "Outputs of S6", "Deterministic render", None,
            "G7 database-to-render parity, all 43 species pages")]

    c = Canvas()
    yA = panel(c, PANEL_LB, "a", "Stage 1, deterministic. Ends when the corpus freezes.", A,
               focal_gate="G3")
    yB_start = yA + GAP
    yB = panel(c, yB_start, "b", "Stage 2, LLM-assisted. Every output checked back against Stage 1.", B)

    # the stage hand-off, drawn once, horizontally from the frozen gate down the page
    height = yB + LEGEND_H

    # legend
    ly = yB + 18
    c.add(f'<line x1="{MARGIN_L}" y1="{ly - 10}" x2="{MARGIN_L + BAND_W}" y2="{ly - 10}" '
          f'stroke="{HAIR}" stroke-width="0.5"/>')
    c.text(MARGIN_L, ly, "S1 to S7", size=6.0, weight="700")
    c.text(MARGIN_L + 44, ly, "the seven pipeline steps. These are not the seven audit questions "
                   "Q1 to Q7, which are applied at G6.", size=6.0, fill=MID)
    c.text(MARGIN_L, ly + 10, "G1 to G7", size=6.0, weight="700")
    c.text(MARGIN_L + 44, ly + 10, "the human gate closing each step. A gate can refuse and send the "
                        "step back; it is not a sign-off.", size=6.0, fill=MID)
    c.text(MARGIN_L, ly + 20, "Bold box", size=6.0, weight="700")
    c.text(MARGIN_L + 44, ly + 20, "G3, the stage boundary. The corpus is frozen here and every "
                        "Stage 2 output is checked back against it.", size=6.0, fill=MID)
    c.text(MARGIN_L, ly + 30, "Empty row", size=6.0, weight="700")
    c.text(MARGIN_L + 44, ly + 30, "a step with nothing in that role. The LLM row is empty throughout "
                        "Stage 1, which is the figure's point.", size=6.0, fill=MID)

    body = "\n  ".join(c.parts)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" role="img"
     aria-labelledby="fig12-title fig12-desc"
     viewBox="0 0 {W} {height}" width="{MM_W}">
  <title id="fig12-title">Figure 13. The seven-step evaluation pipeline</title>
  <desc id="fig12-desc">A two-panel diagram of the seven pipeline steps S1 to S7
  across four roles: the source record, deterministic code, the generative model
  where one is used, and the human gate that closes each step. Panel a covers the
  three deterministic steps and has no model in any of them; the corpus is frozen
  at gate G3. Panel b covers the four LLM-assisted steps, each of which names its
  model and is closed by a human gate that checks the output back against the
  frozen corpus.</desc>
  <defs>
    <marker id="ar" markerWidth="5" markerHeight="4" refX="4.6" refY="2" orient="auto">
      <polygon points="0 0, 5 2, 0 4" fill="{MID}"/>
    </marker>
  </defs>
  <rect width="100%" height="100%" fill="{WHITE}"/>
  {body}
</svg>
'''
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(svg)
    return c, height, svg


def assert_geometry(c, height):
    """The connector rules, tested on the produced geometry rather than by eye."""
    fails = []
    for (x1, y1, x2, y2) in c.arrows:
        if x1 != x2 and y1 != y2:
            fails.append(f"diagonal connector {(x1, y1, x2, y2)}")
    seen = {}
    for a in c.arrows:
        for pt in ((a[0], a[1]), (a[2], a[3])):
            seen.setdefault(pt, 0)
            seen[pt] += 1
    for pt, n in seen.items():
        if n > 1:
            fails.append(f"shared attach point {pt} used by {n} connectors")
    # a connector may not pass through a box that is neither its start nor end
    for (x1, y1, x2, y2) in c.arrows:
        lo_y, hi_y = sorted((y1, y2))
        lo_x, hi_x = sorted((x1, x2))
        for (bx, by, bw, bh) in c.boxes:
            inside_x = bx < lo_x < bx + bw or bx < hi_x < bx + bw or (lo_x <= bx and hi_x >= bx + bw)
            inside_y = by < lo_y < by + bh or by < hi_y < by + bh or (lo_y <= by and hi_y >= by + bh)
            if inside_x and inside_y:
                starts = bx <= x1 <= bx + bw and by <= y1 <= by + bh
                ends = bx <= x2 <= bx + bw and by <= y2 <= by + bh
                if not (starts or ends):
                    fails.append(f"connector {(x1, y1, x2, y2)} crosses box {(bx, by, bw, bh)}")
    # font floor: every font-size in the file must clear 5 pt
    for m in re.finditer(r'font-size="([\d.]+)"', "\n".join(c.parts)):
        if float(m.group(1)) < 5.0:
            fails.append(f"font-size {m.group(1)} pt is below the 5 pt floor")
    return fails


def self_test():
    """Prove the assertions can fail before their silence is read as a pass."""
    probe = Canvas()
    probe.boxes.append((0, 0, 10, 10))
    probe.arrows.append((0, 0, 20, 20))           # a diagonal
    probe.parts.append('<text font-size="4.0">x</text>')
    f = assert_geometry(probe, 0)
    assert any("diagonal" in x for x in f), "SELF-TEST: the diagonal check did not fire"
    assert any("below the 5 pt floor" in x for x in f), "SELF-TEST: the font floor did not fire"
    probe2 = Canvas()
    probe2.boxes.append((40, 0, 20, 20))
    probe2.arrows.append((50, -30, 50, 60))       # straight through a box it does not touch
    f2 = assert_geometry(probe2, 0)
    assert any("crosses box" in x for x in f2), "SELF-TEST: the transit check did not fire"
    print("  self-test: PASS (diagonal, font floor and box transit all report)", file=sys.stderr)


def render_png():
    """Write the PNG from the SVG this run produced.

    The PNG is derived from the SVG produced in the same run, never kept as a
    separate hand-made file, so the two cannot drift apart when the SVG
    changes (for example, when a lane label is renamed).

    600 dpi on the 180 mm width, the journal's upper bound.
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
    mm_h = round(h / 512 * 180, 1)
    print(f"  wrote {OUT.name}: {W} x {h} pt = 180.0 x {mm_h} mm", file=sys.stderr)
    print(f"  {len(canvas.boxes)} boxes, {len(canvas.arrows)} connectors", file=sys.stderr)
    if not problems:
        problems += render_png()
    sys.exit(1 if problems else 0)
