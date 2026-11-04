#!/usr/bin/env python3
"""Draw the S1-S7 pipeline as two data-flow diagrams, from pipeline.json.

WHY THIS EXISTS
---------------
The pipeline is described in four places: the manuscript's locked step table,
Supplementary Table 4, manuscript Figure 13, and the platform. Four descriptions
of one thing are four opportunities to disagree, for example a platform serving a
stale figure-provenance record while another description reports a different
count.

pipeline.json is the single record. It is derived from the locked table and the
deposited Supplementary Table 4, and it carries Table 4's SHA-256 so a reader
can tell whether the mapping drawn here is the mapping deposited. This script is
one consumer of it. Nothing here restates a fact about the pipeline.

LAYOUT
------
The diagram is a data-flow layout: role lanes, numbered step columns, node
cards with input/output chips, one focal step, one focal node, one focal arrow,
single-bend orthogonal routing, and a three-row legend. Geometry is computed
from fixed formulas rather than placed by hand.

The layout holds six steps comfortably. There are seven, and splitting reads
better than crowding. The split is the paper's own: Stage 1 is deterministic and ends when
the corpus freezes at G3; Stage 2 is LLM-assisted and every one of its outputs is
checked back against Stage 1. Drawing them separately is what the architecture
already claims.

The LLM lane in the Stage 1 diagram is empty across all three steps. That is not
a gap in the drawing. It is the strongest form of the sentence "no model
produced any reported value in Stage 1" — the row is there and nothing is in it.

Usage:
  python3 deposit/build_pipeline_diagram.py
"""
from __future__ import annotations

import json
import os
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SSOT = HERE / "pipeline.json"
# The output directory is overridable so a checker can render into a scratch
# directory and compare byte for byte. The first version of that check
# copied this script into the scratch directory instead, which moved HERE
# with it and made the generator look for pipeline.json beside the copy.
OUT = pathlib.Path(os.environ.get("PIPELINE_FIGURES_OUT", HERE / "figures"))

# ── Skin ──────────────────────────────────────────────────────────────────────
# A warm editorial palette. This figure is a platform surface, not a journal
# figure, so it uses the tracker's own styling rather than a journal's
# print specification.
PAPER, INK = "#F5F0E8", "#14110D"
MUTED, SOFT = "#6E6659", "#8A7D68"
ACCENT, LINK = "#B87333", "#1A6E78"
SANS = "Archivo, 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', SFMono-Regular, ui-monospace, Menlo, monospace"

# Data-type chips (§8). Codes chosen for what actually moves in this pipeline.
CHIPS = {
    "WB": ("#6e6479", "Public register"),
    "DB": ("#5e7a9b", "Source dataset"),
    "TB": ("#b8915a", "Frozen table"),
    "FL": ("#9c6b50", "Prose / report"),
}

# ── Geometry, from the type reference §2 ──────────────────────────────────────
LABEL_COL_W, STEP_SLOT_W, RIGHT_PAD = 140, 112, 28
HEADER_H, LANE_H, LEGEND_H = 36, 80, 80
NODE_W, NODE_H = 100, 64

LANES = [
    ("SRC", ["EXTERNAL", "SOURCES"]),
    ("PIPE", ["DETERMINISTIC", "PIPELINE"]),
    ("AI", ["LLM", "TOOL"]),
    ("GATE", ["HUMAN", "GATE"]),
]
LANE_IX = {k: i for i, (k, _) in enumerate(LANES)}
# The badge on each node names its lane. It printed the lane KEY, so the key
# "AI" reached the figure after the paper stopped saying AI (6 Oct 2026). The
# key is a schema identifier read by pipeline.json and the app; what a reader
# sees is a separate decision and lives here.
BADGE = {"SRC": "SRC", "PIPE": "PIPE", "AI": "LLM", "GATE": "GATE"}


def fit(s: str, size: float, width: float = NODE_W - 8) -> str:
    """Trim to what fits the node box, on a word boundary, with an ellipsis.

    The first render clipped "IUCN Red List assessme" and "Conservation-status
    compil" mid-word. A box that cannot hold its label is a layout error, and
    silently letting the glyphs run past the border is the version of it that
    looks like a bug rather than a decision.
    """
    per = size * 0.60                      # Archivo advance, measured against the render
    if len(s) * per <= width:
        return s
    keep = max(1, int(width / per) - 1)
    cut = s[:keep]
    if " " in cut[int(keep * 0.5):]:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;·-") + "\u2026"


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def txt(x, y, s, size, fill, weight="400", anchor="middle", family=SANS, extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"'
            f'{extra}>{esc(s)}</text>\n')


def step_cx(j: int) -> float:
    return LABEL_COL_W + j * STEP_SLOT_W + STEP_SLOT_W / 2


def lane_y_top(k: int) -> float:
    return HEADER_H + k * LANE_H


def elbow(x1, y1, x2, y2, r=8) -> str:
    """Horizontal first, then vertical, with a quarter-arc corner. No diagonals."""
    if abs(y1 - y2) < 0.5:
        return f"M{x1},{y1} L{x2},{y2}"
    if abs(x1 - x2) < 0.5:
        return f"M{x1},{y1} L{x2},{y2}"
    sy = 1 if y2 > y1 else -1
    sx = 1 if x2 > x1 else -1
    return (f"M{x1},{y1} L{x2 - sx * r},{y1} "
            f"Q{x2},{y1} {x2},{y1 + sy * r} L{x2},{y2}")


def diagram(title, subtitle, steps, nodes, arrows, focal_step,
            accent_label="Focal hand-off") -> str:
    n_steps, n_lanes = len(steps), len(LANES)
    W = LABEL_COL_W + n_steps * STEP_SLOT_W + RIGHT_PAD
    legend_top = HEADER_H + n_lanes * LANE_H
    H = legend_top + LEGEND_H

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'width="{W}" height="{H}" role="img" '
         f'aria-label="{esc(title)}. {esc(subtitle)}">\n']
    o.append(f'<title>{esc(title)}</title>\n')
    o.append('<defs>\n'
             f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">'
             f'<circle cx="11" cy="11" r="0.8" fill="{INK}" opacity="0.10"/></pattern>\n')
    for mid, col in (("arr-muted", MUTED), ("arr-accent", ACCENT), ("arr-link", LINK)):
        o.append(f'<marker id="{mid}" markerWidth="6" markerHeight="6" refX="5" '
                 f'refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{col}"/>'
                 f'</marker>\n')
    o.append('</defs>\n')

    o.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>\n')
    o.append(f'<rect width="{W}" height="{H}" fill="url(#dots)"/>\n')

    # Lane tint on one lane only; a tint on every lane would be decoration.
    o.append(f'<rect x="0" y="{lane_y_top(LANE_IX["PIPE"])}" width="{W}" '
             f'height="{LANE_H}" fill="{INK}" opacity="0.018"/>\n')

    for k in range(n_lanes + 1):
        y = lane_y_top(k)
        o.append(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="{INK}" '
                 f'stroke-opacity="0.12" stroke-width="0.8"/>\n')
    o.append(f'<line x1="0" y1="{legend_top}" x2="{W}" y2="{legend_top}" '
             f'stroke="{INK}" stroke-opacity="0.12" stroke-width="0.8"/>\n')
    o.append(f'<line x1="{LABEL_COL_W}" y1="{HEADER_H}" x2="{LABEL_COL_W}" '
             f'y2="{legend_top}" stroke="{INK}" stroke-opacity="0.12" '
             f'stroke-width="0.8"/>\n')

    # Step header chips
    for j, s in enumerate(steps):
        cx = step_cx(j)
        focal = j == focal_step
        fill, tcol = ((ACCENT, ACCENT) if focal else (INK, MUTED))
        op = "0.20" if focal else "0.12"
        o.append(f'<rect x="{cx - 16}" y="6" width="32" height="16" rx="8" '
                 f'fill="{fill}" opacity="{op}"/>\n')
        o.append(txt(cx, 14, s["number"], 7, ACCENT if focal else INK, "700",
                     family=MONO, extra=' letter-spacing="0.06em"'))
        o.append(txt(cx, 29, s["label"], 7, tcol, "600",
                     extra=' letter-spacing="0.12em"'))

    # Lane labels
    for k, (_, name) in enumerate(LANES):
        ym = lane_y_top(k) + LANE_H / 2
        o.append(txt(LABEL_COL_W / 2, ym - 4, name[0], 7.5, MUTED, "600",
                     extra=' letter-spacing="0.14em"'))
        o.append(txt(LABEL_COL_W / 2, ym + 8, name[1], 7.5, MUTED, "600",
                     extra=' letter-spacing="0.14em"'))

    # Arrows before nodes (z-order rule)
    for a in arrows:
        (lk1, j1), (lk2, j2) = a["frm"], a["to"]
        style = a["style"]
        col = {"muted": MUTED, "accent": ACCENT, "link": LINK}[style]
        mk = {"muted": "arr-muted", "accent": "arr-accent", "link": "arr-link"}[style]
        wid = 1.2 if style == "accent" else 1.0
        dash = ' stroke-dasharray="4,3"' if a.get("dashed") else ""
        y1 = lane_y_top(LANE_IX[lk1]) + 8 + NODE_H / 2
        y2 = lane_y_top(LANE_IX[lk2]) + 8 + NODE_H / 2
        if j1 == j2:                      # same column, cross lane: straight down
            x = step_cx(j1)
            ya = lane_y_top(LANE_IX[lk1]) + 8 + NODE_H
            yb = lane_y_top(LANE_IX[lk2]) + 8
            o.append(f'<path d="M{x},{ya} L{x},{yb}" fill="none" stroke="{col}" '
                     f'stroke-width="{wid}"{dash} marker-end="url(#{mk})"/>\n')
        else:
            x1 = step_cx(j1) + NODE_W / 2
            x2 = step_cx(j2) - NODE_W / 2
            o.append(f'<path d="{elbow(x1, y1, x2, y2)}" fill="none" '
                     f'stroke="{col}" stroke-width="{wid}"{dash} '
                     f'marker-end="url(#{mk})"/>\n')
        if a.get("label"):
            if j1 == j2:
                # Vertical run: the label goes beside the line, mid-gap, not over
                # the node it leaves. The first render put "corpus frozen" across
                # the S3 title.
                ya = lane_y_top(LANE_IX[lk1]) + 8 + NODE_H
                yb = lane_y_top(LANE_IX[lk2]) + 8
                lx, ly = step_cx(j1) + 10, (ya + yb) / 2
                wpx = len(a["label"]) * 3.6 + 8
                o.append(f'<rect x="{lx - 4}" y="{ly - 7}" width="{wpx}" '
                         f'height="10" fill="{PAPER}"/>\n')
                o.append(txt(lx, ly, a["label"], 6.5, col, "600",
                             anchor="start", family=MONO))
                continue
            lx, ly = (step_cx(j1) + step_cx(j2)) / 2, min(y1, y2) - 12
            wpx = len(a["label"]) * 3.6 + 8
            o.append(f'<rect x="{lx - wpx/2}" y="{ly - 7}" width="{wpx}" '
                     f'height="10" fill="{PAPER}"/>\n')
            o.append(txt(lx, ly, a["label"], 6.5, col, "600", family=MONO))

    # Nodes
    for nd in nodes:
        k, j = LANE_IX[nd["lane"]], nd["step"]
        x, y = step_cx(j) - NODE_W / 2, lane_y_top(k) + 8
        focal = nd.get("focal", False)
        if focal:
            o.append(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" '
                     f'rx="6" fill="{ACCENT}" fill-opacity="0.07" '
                     f'stroke="{ACCENT}" stroke-width="1.2"/>\n')
        else:
            o.append(f'<rect x="{x}" y="{y}" width="{NODE_W}" height="{NODE_H}" '
                     f'rx="6" fill="{PAPER}" stroke="{INK}" stroke-opacity="0.25" '
                     f'stroke-width="1"/>\n')
        o.append(f'<rect x="{x+4}" y="{y+4}" width="20" height="10" rx="3" '
                 f'fill="{ACCENT if focal else INK}" '
                 f'opacity="{0.18 if focal else 0.12}"/>\n')
        o.append(txt(x + 14, y + 11, BADGE[nd["lane"]], 5.5,
                     ACCENT if focal else MUTED, "700", family=MONO))
        o.append(txt(step_cx(j), y + 25, fit(nd["title"], 8), 8,
                     ACCENT if focal else INK, "600"))
        o.append(txt(step_cx(j), y + 36, fit(nd["sub"], 6), 6, MUTED, family=MONO))
        o.append(txt(step_cx(j), y + 47, fit(nd["tool"], 6), 6, SOFT))
        for code, cx0 in ((nd.get("cin"), x + 4), (nd.get("cout"), x + 80)):
            if not code:
                continue
            o.append(f'<rect x="{cx0}" y="{y+54}" width="16" height="8" rx="3" '
                     f'fill="{CHIPS[code][0]}"/>\n')
            o.append(txt(cx0 + 8, y + 60, code, 5, "#ffffff", "700", family=MONO))

    # Legend
    used = sorted({c for nd in nodes for c in (nd.get("cin"), nd.get("cout")) if c})
    r1, r2, r3 = legend_top + 16, legend_top + 37, legend_top + 59
    o.append(txt(LABEL_COL_W - 8, r1, "STEPS", 6.5, MUTED, "700", anchor="end",
                 extra=' letter-spacing="0.12em"'))
    lx = LABEL_COL_W + 12
    for j, s in enumerate(steps):
        focal = j == focal_step
        o.append(f'<rect x="{lx}" y="{r1-8}" width="26" height="12" rx="6" '
                 f'fill="{ACCENT if focal else INK}" '
                 f'opacity="{0.20 if focal else 0.12}"/>\n')
        o.append(txt(lx + 13, r1, s["number"], 6, ACCENT if focal else INK, "700",
                     family=MONO))
        o.append(txt(lx + 32, r1, s["label"].title(), 6.5,
                     ACCENT if focal else MUTED, anchor="start"))
        lx += 34 + len(s["label"]) * 4.2 + 14
    o.append(txt(LABEL_COL_W - 8, r2, "DATA", 6.5, MUTED, "700", anchor="end",
                 extra=' letter-spacing="0.12em"'))
    lx = LABEL_COL_W + 12
    for code in used:
        col, meaning = CHIPS[code]
        o.append(f'<rect x="{lx}" y="{r2-6}" width="16" height="8" rx="3" fill="{col}"/>\n')
        o.append(txt(lx + 8, r2, code, 5, "#ffffff", "700", family=MONO))
        o.append(txt(lx + 22, r2, meaning, 6.5, MUTED, anchor="start"))
        lx += 24 + len(meaning) * 3.9 + 16
    o.append(txt(LABEL_COL_W + 12 + 0, r2 + 0, "", 6, MUTED))
    o.append(txt(LABEL_COL_W - 8, r3, "FLOW", 6.5, MUTED, "700", anchor="end",
                 extra=' letter-spacing="0.12em"'))
    lx = LABEL_COL_W + 12
    styles_used = {a["style"] for a in arrows}

    # A legend entry has to be findable in the drawing, not merely accurate
    # about it. The guard below already refuses to advertise a flow the figure
    # does not use, and that is correct — but the link-styled connector in
    # Stage 2 runs G6 to G7, two horizontally adjacent boxes, so it is the 12
    # pixels of gutter between them. Looking at the rendered figure on
    # 2026-09-01 it could not be found at all: the legend promised a third flow
    # type and the eye had nowhere to land. Naming its endpoints costs a few
    # characters of legend text and turns an invisible stroke into something a
    # reader can go and look at.
    endpoints = {a["style"]: a for a in arrows}
    by_cell = {(n["lane"], n["step"]): n.get("title", "") for n in nodes}

    def named(key: str, lab: str) -> str:
        a = endpoints.get(key)
        if key != "link" or not a:
            return lab
        frm, to = by_cell.get(a["frm"], ""), by_cell.get(a["to"], "")
        return f"{lab} ({frm} to {to})" if frm and to else lab

    for col, mk, lab, key in ((MUTED, "arr-muted", "Data hand-off", "muted"),
                              (ACCENT, "arr-accent", accent_label, "accent"),
                              (LINK, "arr-link", "Published to the platform", "link")):
        if key not in styles_used:
            continue
        lab = named(key, lab)
        o.append(f'<line x1="{lx}" y1="{r3-2}" x2="{lx+26}" y2="{r3-2}" '
                 f'stroke="{col}" stroke-width="1.2" marker-end="url(#{mk})"/>\n')
        o.append(txt(lx + 32, r3, lab, 6.5, MUTED, anchor="start"))
        lx += 34 + len(lab) * 3.9 + 16

    o.append("</svg>\n")
    return "".join(o)


def main() -> int:
    ssot = json.loads(SSOT.read_text())
    steps = {s["id"]: s for s in ssot["steps"]}
    OUT.mkdir(exist_ok=True)

    # ── Stage 1 ───────────────────────────────────────────────────────────────
    s1_steps = [{"number": "01", "label": "IDENTIFY"},
                {"number": "02", "label": "COMPILE"},
                {"number": "03", "label": "INTEGRATE"}]
    s1_nodes, s1_arrows = [], []
    for j, sid in enumerate(("S1", "S2", "S3")):
        st = steps[sid]
        s1_nodes.append({"lane": "SRC", "step": j, "title": st["source_name"],
                         "sub": "external register", "tool": "custodian record",
                         "cout": "WB" if j == 0 else "DB"})
        s1_nodes.append({"lane": "PIPE", "step": j, "title": f"{st['id']} {st['short_title']}",
                         "sub": ", ".join(st["audit_questions"]) or "no audit question",
                         "tool": "deterministic query",
                         "cin": "WB" if j == 0 else "DB",
                         "cout": "TB" if sid == "S3" else "DB",
                         "focal": sid == "S3"})
        s1_nodes.append({"lane": "GATE", "step": j, "title": st["gate"],
                         "sub": "author-verified", "tool": "reconciled to source",
                         "cin": "TB" if sid == "S3" else "DB"})
        s1_arrows.append({"frm": ("SRC", j), "to": ("PIPE", j), "style": "muted"})
        s1_arrows.append({"frm": ("PIPE", j), "to": ("GATE", j),
                          "style": "accent" if sid == "S3" else "muted",
                          "label": "corpus frozen" if sid == "S3" else None})
        if j:
            s1_arrows.append({"frm": ("PIPE", j - 1), "to": ("PIPE", j), "style": "muted"})

    (OUT / "pipeline-stage1.svg").write_text(diagram(
        "Stage 1: deterministic", "No model produces any value in this stage",
        s1_steps, s1_nodes, s1_arrows, focal_step=2,
        accent_label="Corpus frozen, Stage 1 ends"))

    # ── Stage 2 ───────────────────────────────────────────────────────────────
    s2_steps = [{"number": "04", "label": "RETRIEVE"}, {"number": "05", "label": "SYNTHESISE"},
                {"number": "06", "label": "CLASSIFY"}, {"number": "07", "label": "PUBLISH"}]
    s2_nodes, s2_arrows = [], []
    for j, sid in enumerate(("S4", "S5", "S6", "S7")):
        st = steps[sid]
        s2_nodes.append({"lane": "AI", "step": j, "title": st["tool_name"],
                         "sub": "model-assisted" if sid in ("S4", "S5") else "summary only",
                         "tool": "walled off" if sid == "S7" else "LLM tool",
                         "cin": "TB" if j == 0 else "FL", "cout": "FL"})
        s2_nodes.append({"lane": "GATE", "step": j, "title": st["gate"],
                         "sub": ", ".join(st["audit_questions"]) or "no audit question",
                         "tool": "author-scored" if sid == "S6" else "author-checked",
                         "cin": "FL", "cout": "TB" if sid == "S6" else "FL",
                         "focal": sid == "S6"})
        s2_arrows.append({"frm": ("AI", j), "to": ("GATE", j),
                          "style": "accent" if sid == "S6" else "muted",
                          "label": "scored by authors" if sid == "S6" else None})
        if j:
            s2_arrows.append({"frm": ("AI", j - 1), "to": ("AI", j), "style": "muted"})
    s2_nodes.append({"lane": "PIPE", "step": 0, "title": "Frozen corpus",
                     "sub": "Stage 1 output", "tool": "corpus frozen at G3",
                     "cout": "TB"})
    s2_arrows.append({"frm": ("PIPE", 0), "to": ("AI", 0), "style": "muted"})
    s2_arrows.append({"frm": ("GATE", 2), "to": ("GATE", 3), "style": "link"})

    (OUT / "pipeline-stage2.svg").write_text(diagram(
        "Stage 2: LLM-assisted", "Every output is checked back against Stage 1",
        s2_steps, s2_nodes, s2_arrows, focal_step=2,
        accent_label="Scored by the authors, not the model"))

    # PNG beside each SVG, because a diagram that has to be pasted into a
    # document or a slide is pasted as a raster and somebody will otherwise
    # export one by hand, which is a copy that drifts. Rendered at 3x so it
    # survives a retina screen and a printed page.
    #
    # rsvg-convert is not assumed: a reader cloning this repository has the SVGs
    # either way, and a missing rasteriser is reported rather than failing the
    # build. The SVGs are the artefact of record; the PNGs are a convenience.
    import shutil
    import subprocess
    raster = shutil.which("rsvg-convert")
    for f in ("pipeline-stage1.svg", "pipeline-stage2.svg"):
        print(f"  wrote figures/{f}  ({(OUT / f).stat().st_size:,} bytes)")
        if raster:
            png = OUT / f.replace(".svg", ".png")
            subprocess.run([raster, "-z", "3", "-o", str(png), str(OUT / f)],
                           check=True)
            print(f"  wrote figures/{png.name}  ({png.stat().st_size:,} bytes)")
    if not raster:
        print("  rsvg-convert not found: PNGs not refreshed. The SVGs are the "
              "record; install librsvg to regenerate the rasters.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
