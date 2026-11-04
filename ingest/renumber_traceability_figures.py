#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-10-18
"""Carry the manuscript of 18 October 2026's figure numbering into Supplementary Table 5.

WHY THIS EXISTS
---------------
The co-author's manuscript of 18 October adds CITES reservations by state as
Figure 5, and every figure from the old Figure 5 onward moves up one.
deposit/results_traceability.csv names manuscript figures in its claim and
definition text ("the 15 wild-origin species Figure 6 draws"), and its only
generator, ingest/build_traceability_table.py, knows 29 of its 143 claims and
refuses to run rather than delete the rest. So the numbering cannot be
regenerated through it, and editing 40 cells by hand is the kind of change no
reviewer can check.

This does it by rule, and the rule is content, not arithmetic:

  - the 4 October numbering is recorded here as slug per number, from
    figure_provenance.json as it stood before the renumbering (b06fc44^);
  - the 18 October number for each slug is read from the provenance record
    as it stands now;
  - every target number must have a caption in the final manuscript, or
    nothing is written. The manuscript is not part of the public release:
    set ARCTIC_MANUSCRIPT_DOCX and ARCTIC_LIVE_TEXT_DIR (the directory holding
    the live_text helper) to run this; without them the run stops, says the
    caption check was skipped, and writes nothing;
  - every row that names a Source Data file must, after the change, cite the
    figure that file is bound to - so a second run, which would move Figure 7
    to Figure 8 again, is refused rather than applied twice.

--refill CID[,CID...] then writes the value deposit/verification/
verify_claims_offline.py computes for the named claims, and only those. That
is the documented route for a claim computed from the deposit ("run the
verifier and fill them"), done by the verifier rather than by typing.

Usage:
  python3 ingest/renumber_traceability_figures.py [--refill C81]
  python3 ingest/render_traceability_md.py
"""
import argparse
import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "deposit/results_traceability.csv"
PROV = ROOT / "visualizations/provenance/figure_provenance.json"
import os
_MS_ENV = os.environ.get("ARCTIC_MANUSCRIPT_DOCX")
MANUSCRIPT = pathlib.Path(_MS_ENV) if _MS_ENV else None
_LIVE_ENV = os.environ.get("ARCTIC_LIVE_TEXT_DIR")
LIVE_TEXT_DIR = pathlib.Path(_LIVE_ENV) if _LIVE_ENV else None

# The 4 October numbering, slug per manuscript number (figure_provenance.json
# at b06fc44^). Recorded rather than read from git so this runs from a copy.
OLD = {1: "arctic-definition", 2: "cites-structure", 3: "appendix-membership",
       4: "status-heatmap", 5: "trade-enforcement", 6: "wild-origin-trade",
       7: "iwt-seizures", 8: "trade-partners", 9: "status-trends",
       10: "status-patterns", 11: "pipeline-diagram", 12: "pipeline-journal"}

TEXT_COLUMNS = ("claim", "methods_section", "source_table", "operative_definition")
REF = re.compile(r"\b(Figures?|Fig\.)(\s+)(\d{1,2})\b")
SOURCE_FILE = re.compile(r"(figure[0-9A-Z])_source_data\.csv")


def mapping():
    prov = json.loads(PROV.read_text())
    by_slug = {e["slug"]: e for e in prov["figure_map"]}
    out = {}
    for n, slug in OLD.items():
        if slug not in by_slug:
            sys.exit(f"  ABORT: slug {slug!r} (old Figure {n}) is not in the "
                     f"provenance record, so its new number is unknown")
        out[n] = by_slug[slug]["manuscript_number"]
    bound = {e["figure_id"]: e["manuscript_number"]
             for e in prov["figure_map"] if e.get("figure_id")}
    return out, bound


def captioned():
    sys.path.insert(0, str(LIVE_TEXT_DIR))
    import live_text
    live = live_text.from_docx(MANUSCRIPT)
    return {int(x) for x in re.findall(r"(?m)^Figure (\d{1,2})[:.]", live)}


def self_test():
    m = {6: 7, 7: 8, 3: 3}
    s = REF.sub(lambda g: f"{g[1]}{g[2]}{m[int(g[3])]}",
                "Figure 6 draws; Figure 7's window; Fig. 3")
    assert s == "Figure 7 draws; Figure 8's window; Fig. 3", s
    print("  self-test: PASS (each reference moves once, by its own number)",
          file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refill", default="")
    args = ap.parse_args()
    self_test()

    old_to_new, bound = mapping()
    if MANUSCRIPT is None or LIVE_TEXT_DIR is None:
        print("  skipped: the caption check (the manuscript is not part of the "
              "public release; set ARCTIC_MANUSCRIPT_DOCX and ARCTIC_LIVE_TEXT_DIR). "
              "Nothing was written.", file=sys.stderr)
        return 3
    caps = captioned()
    missing = sorted(set(old_to_new.values()) - caps)
    if missing:
        sys.exit(f"  ABORT: the final manuscript has no caption for Figure(s) "
                 f"{missing}; refusing to number against it")

    with CSV_PATH.open(newline="", encoding="utf8") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames
        rows = list(reader)

    # A second application is refused by the check after each row below:
    # a row bound to one Source Data file must end up citing that file's figure.
    changes = 0
    for r in rows:
        files = set(SOURCE_FILE.findall(r["source_table"]))
        for col in TEXT_COLUMNS:
            for g in REF.finditer(r[col]):
                if int(g[3]) not in old_to_new:
                    sys.exit(f"  ABORT: {r['claim_id']} cites Figure {g[3]}, "
                             f"which the 4 October numbering does not have")
                changes += old_to_new[int(g[3])] != int(g[3])
            r[col] = REF.sub(lambda g: f"{g[1]}{g[2]}{old_to_new[int(g[3])]}", r[col])
        # After: a row bound to one Source Data file cites that file's figure.
        cited = {int(g[3]) for col in TEXT_COLUMNS for g in REF.finditer(r[col])}
        for fid in files:
            if fid in bound and cited and len(files) == 1 and bound[fid] not in cited:
                sys.exit(f"  ABORT: {r['claim_id']} names {fid}_source_data.csv, "
                         f"bound to Figure {bound[fid]}, and would cite "
                         f"{sorted(cited)}. Already renumbered, or the binding "
                         f"moved; nothing written.")

    refilled = []
    if args.refill:
        sys.path.insert(0, str(ROOT / "deposit" / "verification"))
        import verify_claims_offline as v
        got = v.compute()
        want = [c.strip() for c in args.refill.split(",") if c.strip()]
        for r in rows:
            if r["claim_id"] in want:
                mine = got[r["claim_id"]]
                val = f"{mine:.2f}" if isinstance(mine, float) else str(mine)
                if val != r["value"]:
                    refilled.append((r["claim_id"], r["value"], val))
                    r["value"] = val

    with CSV_PATH.open("w", newline="", encoding="utf8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  {changes} figure reference(s) renumbered to the 18 October manuscript")
    for cid, was, now in refilled:
        print(f"  {cid}: {was} -> {now} (computed by verify_claims_offline)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
