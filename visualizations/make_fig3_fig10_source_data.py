#!/usr/bin/env python3
"""Source Data for manuscript Figures 3 and 10, which had none.

WHY THIS EXISTS
---------------
The Data Availability statement said, of its own deposit: "Figures 3 and 10
plot computed values and have no Source Data file either; that is a gap in the
deposit rather than a property of the figure, and the index records it as one."
A declared gap is still a gap, and the journal's policy makes
Source Data mandatory for a main-text figure that plots computed values. Both
figures turn out to be fully derivable from material the pipeline already
reads, so the gap was a missing twenty lines rather than a missing measurement.

WHAT IS IN HERE
---------------
figureA_source_data.csv  manuscript FIGURE 3  - the 43 species by appendix.
figureB_source_data.csv  manuscript FIGURE 10 - panels A, B and C.

The identifiers are LETTERS on purpose. The pipeline's numbering and the
manuscript's are two different numberings over the same figures - the deposit's
own index has to warn that figure3_source_data.csv is manuscript Figure 8 - and
adding two more numbers to that would deepen exactly the confusion the index
exists to manage. A letter cannot be misread as a figure number. The names
still begin with "figure" because make_all_figures.check() byte-compares
figure*_source_data.csv, and a file outside that glob would sit outside the
verification net, which is where this started.

WHAT IT READS
-------------
The same two files the figure4/figure5 writers already read, so this sits in
their dependency layer and needs no database:

  data/raw/1_DATA_cites_effectiveness.json   per-species cites_appendix
  data/processed/iucn_historic_timeline.json per-species per-scope assessments

Both were cross-checked against the deposit before this was written: the
appendix tally reproduces deposit/sources/curated/cites_listings.csv, and the
transition count reproduces deposit/source_data.zip:figure5_source_data.csv
through the deposit's own verifier - 36 either way.

WHAT IT PROVES ABOUT ITSELF
---------------------------
self_test() asserts every number these two figures' captions publish, so the
generator fails rather than shipping a table that disagrees with the paper:

  Figure 3   43 species, 44 boxes, 17 in Appendix I, 26 in Appendix II, 1 in
             Appendix III. The caption states the 17/26 against the text's
             16/25 and explains the split minke; this reproduces both sides.
  Figure 11B 43 category transitions on the global-and-European series
             (21 October 2026), the count the deposit's trajectory verifier
             holds the manuscript to. Panel A names the latest assessment of
             either scope and, in latest_assessment_scope, which it was; panel
             C is 7 of 34, 13 of 42, 9 of 42 and 7 of 43 at 1996, 2015-2017,
             2019 and 2023.
  Figure 10C 5 species assessed in 1988, by the project's one scale.

NOTE ON THE CAPTION
-------------------
A caption reading "grows from 5 in 1988 to 42 in 2023" differs from the data
by one species. 5 in 1988 is exact. 42 is the 2014-2019 value: the count
reaches 42 in 2014 and 43 in 2020, when Mesoplodon stejnegeri gains its single
comparable global assessment (2020, reported in Section 4.4 of the
manuscript). The generator asserts 43.
"""
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

VIZ = Path(__file__).resolve().parent
ROOT = VIZ.parent
sys.path.insert(0, str(ROOT / "deposit" / "verification"))
import redlist_scale as rl  # the one scale; never a second ladder

EFFECTIVENESS = ROOT / "data/raw/1_DATA_cites_effectiveness.json"
TIMELINE = ROOT / "data/processed/iucn_historic_timeline.json"
# Eight assessments the IUCN record carries with no scope are regional: five
# issue categories only a regional assessment can (NA, RE), three are labelled
# Europe or Mediterranean in IUCN's own record. The timeline files them under
# Global. Since 21 October 2026 the seven European ones count, as European.
SCOPE_CORRECTIONS = ROOT / "species_data/curated/iucn_scope_corrections.csv"
# THE SERIES, from 21 October 2026 (the lead author's decision): Global and
# Europe assessments form ONE series per species, ordered by (year,
# assessment_id), the higher id standing in a year with several. The only
# exclusion is the one assessment that is regional but not European
# (redlist_scale.NOT_EUROPEAN_IDS, the Mediterranean Lamna nasus 2016). The seven
# European assessments the timeline files under Global therefore COUNT, labelled
# Europe in panel A's scope row.
WINDOW = (1982, 2025)
PANEL_C_YEARS = range(1996, 2024)   # the caption's own range


def appendix_boxes(species):
    """One row per (species, appendix) membership.

    A split listing is one row per appendix, which is why the boxes sum to 44
    for 43 species. Counted once per species the set is 16/25/1 split/1, which
    is the tally in Section 4.2; the figure shows 17 and 26 because the minke
    appears in both. Both readings come out of this table.
    """
    out = []
    for sp in sorted(species, key=lambda s: s["scientific_name"]):
        raw = str(sp.get("cites_appendix") or "").strip()
        parts = [p.strip() for p in raw.split("/") if p.strip()]
        for p in parts:
            out.append((sp["scientific_name"], sp.get("common_name") or "",
                        p, "yes" if len(parts) > 1 else "no", raw))
    return out


def regional_ids():
    """Assessment ids the scope-correction list reads as regional."""
    with open(SCOPE_CORRECTIONS, newline="") as f:
        return {int(r["assessment_id"]) for r in csv.DictReader(f)}


def series_of(timeline):
    """{species: [(year, assessment_id, status, scope)]} inside the window.

    Both scopes, ordered by (year, assessment_id). `scope` is Europe for a
    Europe timeline row and for the seven corrected assessments the timeline
    files under Global; everything else is Global.
    """
    european = {i for i in regional_ids() if str(i) not in rl.NOT_EUROPEAN_IDS}
    series = {}
    for sp in timeline["species_timelines"]:
        rows = []
        for scope, g in sp["scope_timelines"].items():
            if scope not in rl.SERIES_SCOPES:
                continue
            for a in g.get("assessments", []):
                aid = int(a["assessment_id"])
                if str(aid) in rl.NOT_EUROPEAN_IDS:
                    continue
                if not WINDOW[0] <= a["year"] <= WINDOW[1]:
                    continue
                rows.append((a["year"], aid, a["status"],
                             "Europe" if scope == "Europe" or aid in european
                             else "Global"))
        if rows:
            series[sp["scientific_name"]] = sorted(rows)
    return series


def statuses(rows):
    """[(year, status)] in series order, for rl.transitions."""
    return [(y, st) for y, _, st, _ in rows]


def panel_a(series):
    """The latest assessment of either scope per species, comparable or not.

    The higher assessment id stands in a tied year (the series order).
    """
    out = []
    for name in sorted(series):
        year, _, status, scope = series[name][-1]
        out.append((name, status, year, scope,
                    "yes" if rl.rank(status) is not None else "no"))
    return out


def panel_b(series):
    """Category transitions per species, by the project's one scale.

    rl.transitions is the same function the deposit's trajectory verifier uses,
    so these per-species counts sum to the 43 the manuscript reports. Both rows
    of a same-year pair stay in the sequence, as the published method counted
    them, and a non-comparable assessment breaks the chain.
    """
    return [(name, len(rl.transitions(statuses(series[name]))))
            for name in sorted(series)]


def panel_c(series):
    """Assessed species and the EN+CR share, cumulative, by the one scale.

    "Assessed" means the species has at least one comparable assessment (global or European)
    at or before the year. That is the reading under which the caption's 5 in
    1988 reproduces exactly; counting every assessment including off-scale ones
    gives 19 that year and matches nothing.
    """
    out = []
    for y in PANEL_C_YEARS:
        assessed, high = 0, 0
        for name in sorted(series):
            past = [x for x in series[name]
                    if x[0] <= y and rl.rank(x[2]) is not None]
            if not past:
                continue
            assessed += 1
            if past[-1][2] in ("EN", "CR"):
                high += 1
        share = round(100.0 * high / assessed, 1) if assessed else 0.0
        out.append((y, assessed, high, share))
    return out


def write(outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    species = json.loads(EFFECTIVENESS.read_text())["species_analyses"]
    series = series_of(json.loads(TIMELINE.read_text()))

    with open(outdir / "figureA_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scientific_name", "common_name", "appendix",
                    "split_listed", "appendix_as_recorded"])
        for row in appendix_boxes(species):
            w.writerow(row)

    with open(outdir / "figureB_source_data.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["panel", "entity", "metric", "value"])
        for name, status, year, scope, comparable in panel_a(series):
            w.writerow(["A", name, "latest_category", status])
            w.writerow(["A", name, "latest_assessment_year", year])
            w.writerow(["A", name, "latest_assessment_scope", scope])
            w.writerow(["A", name, "on_ordinal_scale", comparable])
        for name, n in panel_b(series):
            w.writerow(["B", name, "category_transitions_1982_2025", n])
        for y, assessed, high, share in panel_c(series):
            w.writerow(["C", y, "species_assessed", assessed])
            w.writerow(["C", y, "high_risk_en_cr", high])
            w.writerow(["C", y, "high_risk_share_pct", share])


def self_test():
    """Every number these two captions publish, asserted before anything ships."""
    species = json.loads(EFFECTIVENESS.read_text())["species_analyses"]
    boxes = appendix_boxes(species)
    assert len({r[0] for r in boxes}) == 43, \
        f"SELF-TEST: {len({r[0] for r in boxes})} species, not 43"
    assert len(boxes) == 44, f"SELF-TEST: {len(boxes)} boxes, not 44"
    by_app = Counter(r[2] for r in boxes)
    assert by_app["I"] == 17 and by_app["II"] == 26 and by_app["III"] == 1, \
        f"SELF-TEST: the figure's own tally is 17/26/1, got {dict(by_app)}"
    # One entry per species, holding the appendix exactly as recorded, so a
    # split listing counts once rather than twice.
    once = Counter({r[0]: r[4] for r in boxes}.values())
    assert once["I"] == 16 and once["II"] == 25 and once["I/II"] == 1 \
        and once["III"] == 1, \
        f"SELF-TEST: counted once per species Section 4.2 says 16/25/1/1, got {dict(once)}"

    series = series_of(json.loads(TIMELINE.read_text()))
    a = panel_a(series)
    assert len(a) == 43, f"SELF-TEST: panel A covers {len(a)} species, not 43"
    assert not any(i in rl.NOT_EUROPEAN_IDS for r in series.values()
                   for _, i, _, _ in r), "SELF-TEST: the Mediterranean assessment is in"
    b = panel_b(series)
    assert sum(n for _, n in b) == 43, \
        (f"SELF-TEST: panel B sums to {sum(n for _, n in b)}, and the deposit's "
         f"trajectory verifier holds the manuscript to 43 on the series")
    c = {y: assessed for y, assessed, _, _ in panel_c(series)}
    # 1988 is outside the caption's plotted range but is the number it quotes.
    early = sum(1 for name in series
                if any(x[0] <= 1988 and rl.rank(x[2]) is not None
                       for x in series[name]))
    assert early == 5, f"SELF-TEST: the caption says 5 assessed in 1988, got {early}"
    cc = {y: (h, n) for y, n, h, _ in panel_c(series)}
    assert cc[1996] == (7, 34), f"SELF-TEST: 1996 is 7 of 34, got {cc[1996]}"
    assert all(cc[y] == (13, 42) for y in (2015, 2016, 2017)), \
        f"SELF-TEST: 13 of 42 in 2015-2017, got {[cc[y] for y in (2015, 2016, 2017)]}"
    assert cc[2019] == (9, 42), f"SELF-TEST: 2019 is 9 of 42, got {cc[2019]}"
    assert cc[2023] == (7, 43), f"SELF-TEST: 2023 is 7 of 43, got {cc[2023]}"
    assert c[2014] == 42, f"SELF-TEST: 42 is the 2014 value, got {c[2014]}"
    assert len(regional_ids()) == 8, "SELF-TEST: the scope list should name 8"
    print("  self-test: PASS (43 species in 44 boxes, 17/26/1 as the figure shows "
          "and 16/25/1/1 counted once, panel B sums to 43 on the global-and-"
          "European series, 5 assessed in 1988, EN+CR 7 of 34 in 1996, 13 of 42 "
          "at 2015-2017, 9 of 42 in 2019, 7 of 43 in 2023)")


def main():
    self_test()
    out = VIZ / "source_data"
    write(out)
    for name in ("figureA_source_data.csv", "figureB_source_data.csv"):
        p = out / name
        print(f"  wrote {p.relative_to(ROOT)} ({sum(1 for _ in open(p)) - 1} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
