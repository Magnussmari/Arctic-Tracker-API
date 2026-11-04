#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-10-22
"""Figure 11 (conservation status patterns), drawn from the deposit alone.

Why this exists. The manuscript's Figure 11 is drawn by the lead author, and
the pipeline only writes its numbers (figureB_source_data.csv), so the
tracker's Figure 11 page had a caption and no figure. This draws the three panels the caption names from deposited
values, so the page has a figure and the figure has a recipe.

What it reads, and why the IUCN licence still holds:

  A  current category, 43 species: the COUNTS per category, from claims
     C23-C28 and C148 in results_traceability.csv. No species is drawn against
     its category; the per-species categories stay withheld.
  B  Red List category changes 1982-2025: how many species changed category
     0, 1, 2, ... times, from panel B of figureB_source_data.csv. The build
     refuses unless the changes sum to the 43 transitions the paper reports.
  C  share of assessed species in EN or CR, 1996-2023, from panel C of the
     same file, with n under each year as the caption promises.

Journal specification, not platform styling: 1 unit = 1 pt, width 180 mm,
nothing below 5 pt. Panel a is coloured in the IUCN Red List category colours,
the palette Figures 1, 4, 5 and 8 use (RE black, as in Figures 4 and 5), so a
category reads the same in every figure. Colour is never the only channel: each bar is named and carries its count.
Panels b and c are not drawn by category and stay neutral; colouring c would
suggest an EN/CR split the source data does not give. Writes figures/figure11-status-patterns-journal.svg
and, when rsvg-convert is present, a 600 dpi PNG.
"""
import collections
import csv
import io
import pathlib
import shutil
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
TRACE = HERE / "results_traceability.csv"
ZIP = HERE / "source_data.zip"
MEMBER = "Source Data/figureB_source_data.csv"
OUT = HERE / "figures" / "figure11-status-patterns-journal.svg"

W, MM_W = 512, "180mm"
INK, MID, LIGHT, HAIR = "#111111", "#555555", "#8C8C8C", "#CCCCCC"
BAR, BAR_HI, WHITE = "#6E6E6E", "#2B2B2B", "#FFFFFF"
IUCN = {"CR": "#D81E05", "EN": "#FC7F3F", "VU": "#F9E814", "NT": "#CCE226",
        "LC": "#60C659", "RE": "#000000"}

ORDER = ["CR", "EN", "VU", "NT", "LC", "RE"]
NAMES = {"CR": "Critically Endangered", "EN": "Endangered", "VU": "Vulnerable",
         "NT": "Near Threatened", "LC": "Least Concern", "RE": "Regionally Extinct"}
CLAIMS = {"CR": "C23", "EN": "C24", "VU": "C25", "NT": "C26", "LC": "C27", "DD": "C28", "RE": "C148"}
TRANSITIONS = 43   # the paper's count of category transitions (global and European series)


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Canvas:
    def __init__(self):
        self.parts = []

    def text(self, x, y, s, size=6.0, fill=INK, anchor="start", weight="400"):
        self.parts.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{fill}" '
                          f'text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>')

    def rect(self, x, y, w, h, fill, stroke=None):
        edge = f' stroke="{stroke}" stroke-width="0.4"' if stroke else ""
        self.parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w, 0):.2f}" height="{max(h, 0):.2f}" '
                          f'fill="{fill}"{edge}/>')

    def line(self, x1, y1, x2, y2, stroke=HAIR, width=0.5):
        self.parts.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                          f'stroke="{stroke}" stroke-width="{width}"/>')


def load():
    claims = {r["claim_id"]: r["value"] for r in csv.DictReader(open(TRACE, newline=""))}
    a = {c: int(claims[CLAIMS[c]]) for c in CLAIMS}
    with zipfile.ZipFile(ZIP) as z:
        rows = list(csv.DictReader(io.StringIO(z.read(MEMBER).decode("utf-8"))))
    b = collections.Counter(int(r["value"]) for r in rows if r["panel"] == "B")
    years = {}
    for r in rows:
        if r["panel"] == "C":
            years.setdefault(int(r["entity"]), {})[r["metric"]] = r["value"]
    c = [(y, int(v["species_assessed"]), int(v["high_risk_en_cr"]), float(v["high_risk_share_pct"]))
         for y, v in sorted(years.items())]
    return a, b, c


def check(a, b, c):
    problems = []
    if sum(a.values()) != 43:
        problems.append(f"panel A counts {sum(a.values())} species, want 43")
    if a["DD"]:
        problems.append("panel A has a DD species and no bar for it")
    if sum(b.values()) != 43:
        problems.append(f"panel B counts {sum(b.values())} species, want 43")
    if sum(k * n for k, n in b.items()) != TRANSITIONS:
        problems.append(f"panel B sums to {sum(k * n for k, n in b.items())} transitions, want {TRANSITIONS}")
    if (c[0][0], c[-1][0]) != (1996, 2023):
        problems.append(f"panel C spans {c[0][0]}-{c[-1][0]}, the caption says 1996 to 2023")
    for y, n, k, pct in c:
        if abs(100 * k / n - pct) > 0.051:
            problems.append(f"panel C {y}: {k}/{n} is not {pct}%")
    return problems


def build(a, b, c):
    cv = Canvas()
    top, ph = 14, 104
    # ── a: current category ───────────────────────────────────────────────
    cv.text(0, top, "a", 8, weight="700")
    cv.text(10, top, "Current Red List category, 43 species", 6.5, weight="700")
    lx, bx, bw = 0, 100, 140
    row = 13
    amax = max(a[k] for k in ORDER)
    for i, k in enumerate(ORDER):
        y = top + 14 + i * row
        cv.text(lx, y + 7, f"{k}  {NAMES[k]}", 5.8, MID)
        w = bw * a[k] / amax
        # a hairline edge keeps the pale VU and NT bars visible on white paper
        cv.rect(bx, y, w, 9, IUCN[k], MID)
        cv.text(bx + w + 3, y + 7, a[k], 5.8)
    thr = a["CR"] + a["EN"] + a["VU"]
    cv.text(lx, top + 14 + len(ORDER) * row + 8,
            f"IUCN Red List category colours. Threatened (CR, EN, VU): {thr} of 43. "
            "No species was Data Deficient.", 5.2, LIGHT)

    # ── b: number of category changes ─────────────────────────────────────
    x0 = 290
    cv.text(x0, top, "b", 8, weight="700")
    cv.text(x0 + 10, top, "Red List category changes, 1982–2025", 6.5, weight="700")
    ks = list(range(0, max(b) + 1))
    base, hmax, colw = top + 14 + ph - 30, ph - 40, 34
    bmax = max(b.values())
    for i, k in enumerate(ks):
        x = x0 + 18 + i * (colw + 8)
        h = hmax * b.get(k, 0) / bmax
        cv.rect(x, base - h, colw, h, BAR)
        cv.text(x + colw / 2, base - h - 3, b.get(k, 0), 5.8, anchor="middle")
        cv.text(x + colw / 2, base + 8, k, 5.8, MID, anchor="middle")
    cv.line(x0 + 14, base, x0 + 18 + len(ks) * (colw + 8) - 4, base, LIGHT)
    cv.text(x0 + 18, base + 17, "category changes per species (axis); species (bar)", 5.2, LIGHT)
    cv.text(x0 + 18, base + 25, f"{TRANSITIONS} transitions in all, global and European assessments", 5.2, LIGHT)

    # ── c: share in EN or CR ──────────────────────────────────────────────
    t2 = top + ph + 30
    cv.text(0, t2, "c", 8, weight="700")
    cv.text(10, t2, "Share of assessed species in EN or CR, 1996–2023", 6.5, weight="700")
    cx0, cx1 = 26, W - 4
    cbase, chmax, ymax = t2 + 112, 90, 35.0
    for v in (0, 10, 20, 30):
        y = cbase - chmax * v / ymax
        cv.line(cx0, y, cx1, y, HAIR if v else LIGHT)
        cv.text(cx0 - 4, y + 2, f"{v}%", 5.2, MID, anchor="end")
    step = (cx1 - cx0) / len(c)
    peak = max(p for *_, p in c)
    for i, (y, n, k, pct) in enumerate(c):
        x = cx0 + i * step + step * 0.15
        h = chmax * pct / ymax
        cv.rect(x, cbase - h, step * 0.7, h, BAR_HI if pct == peak else BAR)
        if pct == peak or i in (0, len(c) - 1):
            cv.text(x + step * 0.35, cbase - h - 3, f"{k}/{n}", 5.0, anchor="middle")
        if (y % 3 == 0 and i < len(c) - 2) or i == len(c) - 1:
            cv.text(x + step * 0.35, cbase + 8, y, 5.2, MID, anchor="middle")
        cv.text(x + step * 0.35, cbase + 16, n, 5.0, LIGHT, anchor="middle")
    cv.text(cx0 - 4, cbase + 16, "n", 5.0, LIGHT, anchor="end")
    cv.text(cx0, cbase + 27, "Labels give species in EN or CR over species assessed, at both ends and at the peak.",
            5.2, LIGHT)
    h = cbase + 34
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{MM_W}" height="{h * 180 / W:.1f}mm" '
           f'viewBox="0 0 {W} {h:.0f}" font-family="Helvetica, Arial, sans-serif">'
           f'<rect width="{W}" height="{h:.0f}" fill="{WHITE}"/>' + "".join(cv.parts) + "</svg>\n")
    return svg


def self_test():
    a, b, c = {k: 0 for k in CLAIMS}, collections.Counter({1: 43}), [(1996, 10, 1, 10.0), (2023, 10, 1, 10.0)]
    a["LC"] = 43
    assert check(a, b, c) == [], "SELF-TEST: a consistent input must pass"
    b2 = collections.Counter({1: 42, 2: 1})
    assert check(a, b2, c), "SELF-TEST: 44 transitions must refuse"
    a2 = dict(a, DD=1, LC=42)
    assert check(a2, b, c), "SELF-TEST: a DD species must refuse"


def main():
    self_test()
    a, b, c = load()
    problems = check(a, b, c)
    if problems:
        print("FAIL: Figure 11 does not match the paper:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 1
    OUT.write_text(build(a, b, c))
    print(f"  wrote {OUT.relative_to(HERE)}: A {dict((k, a[k]) for k in ORDER)}, B {dict(sorted(b.items()))}, "
          f"C {c[0][0]}-{c[-1][0]}")
    raster = shutil.which("rsvg-convert")
    if raster:
        png = OUT.with_suffix(".png")
        # 180 mm at 600 dpi = 4252 px, the same as the other journal figures
        subprocess.run([raster, "-w", "4252", "-o", str(png), str(OUT)], check=True)
        print(f"  wrote {png.relative_to(HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
