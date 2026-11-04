#!/usr/bin/env python3
"""Renumber the provenance map for the manuscript of 18 October 2026.

The co-author added a figure: CITES reservations by state is now Figure 5, and
every figure from the old Figure 5 onward moves up by one, so the map covers 1
to 13 instead of 1 to 12. The map is keyed by slug for exactly this reason, so
the renumbering moves one field per entry and nothing else.

What it changes:
  - manuscript_number + 1 for every entry at 5 or above;
  - a new entry for Figure 5, slug "reservations", bound to figureC, whose
    Source Data is computed from the deposited Species+ event history by
    make_figC_reservations_source_data.py and asserted cell by cell against the
    figure the co-author drew;
  - Figure 11 (status patterns, figureB): the evidence now records that panel C
    is computed with the eight regional assessments removed, which moves its
    EN+CR peak from 13 to 12, and that the caption's 43 in 2023 now agrees;
  - Figure 3 (appendix membership, figureA): the caption now states the 17/26/1
    boxes and their sum of 44 itself, which the evidence records.

Refuses rather than guesses: it stops if the map already covers 13 figures, if
the slug is taken, or if the source data it names is missing.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REC = ROOT / "visualizations/provenance/figure_provenance.json"
NEEDS = ["visualizations/make_figC_reservations_source_data.py",
         "visualizations/source_data/figureC_source_data.csv"]

FIG5 = {
    "manuscript_number": 5,
    "manuscript_caption_stub": "CITES reservations held by Arctic states, by appendix",
    "figure_id": "figureC",
    "slug": "reservations",
    "binding_evidence": (
        "figureC_source_data.csv is computed from deposit/tables/"
        "cites_listing_events.csv, the Species+ event history, by "
        "visualizations/make_figC_reservations_source_data.py. Its self-test "
        "asserts every cell the figure draws: Iceland 14 (7 Appendix I, 7 "
        "Appendix II), Norway 5 (4 and 1, with the fin and sei whale "
        "reservations partial by their own stock notes), Greenland 1, Finland 0, "
        "Sweden 0, and none for Canada, the United States or Russia, which the "
        "figure omits. Species+ enters the porbeagle reservation for the Party "
        "Denmark; the figure's column names Greenland, and the Source Data keeps "
        "both names. The artwork is the co-author's; the script computes the "
        "numbers and draws nothing."),
    "confirmed_by": ("Source Data generated 2026-10-18 by "
                     "visualizations/make_figC_reservations_source_data.py, whose "
                     "self-test asserts all twenty cells the figure draws"),
    "confirmed_on": None,
    "evidence_rechecked_on": "2026-10-18",
}

FIG11_EVIDENCE = (
    "figureB_source_data.csv carries the three panels in long form, computed "
    "from global assessments only: the eight assessments the IUCN record "
    "carries with no scope that are regional (species_data/curated/"
    "iucn_scope_corrections.csv) are removed, which is the reading the tracker "
    "uses. Panel A gives 4 CR, 5 EN, 9 VU, 3 NT, 21 LC and 1 DD, as the text "
    "states. Panel B's per-species transition counts sum to 36. Panel C "
    "reproduces 7 EN or CR species in 1996 and 9 from 2019, and peaks at 12 in "
    "2015 to 2017. With the porbeagle's European 2015 assessment read as global the "
    "peak is 13, which is the figure the text of 18 October still states; the "
    "number of assessed species grows from 5 in 1988 to 43 in 2023, as the "
    "caption now says.")

FIG3_NOTE = (
    " The caption of 18 October states the convention itself: the boxes count "
    "the split-listed minke whale in both Appendix I and Appendix II, so they "
    "read 17, 26 and 1 and sum to 44 rather than 43.")


def main():
    for rel in NEEDS:
        if not (ROOT / rel).is_file():
            sys.exit(f"  ABORT: the entry would name {rel}, which is not there")
    rec = json.loads(REC.read_text())
    fmap = rec["figure_map"]
    if len(fmap) >= 13 or any(e["slug"] == FIG5["slug"] for e in fmap):
        print("  the map already has Figure 5 (reservations); nothing written")
        return 0
    for e in fmap:
        if e["manuscript_number"] >= 5:
            e["manuscript_number"] += 1
        if e["slug"] == "status-patterns":
            e["binding_evidence"] = FIG11_EVIDENCE
            e["evidence_rechecked_on"] = "2026-10-18"
        if e["slug"] == "appendix-membership" and FIG3_NOTE not in e["binding_evidence"]:
            e["binding_evidence"] += FIG3_NOTE
            e["evidence_rechecked_on"] = "2026-10-18"
    fmap.append(FIG5)
    nums = sorted(e["manuscript_number"] for e in fmap)
    if nums != list(range(1, 14)):
        sys.exit(f"  ABORT: the map would cover {nums}, not 1 to 13")
    REC.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    for e in sorted(fmap, key=lambda e: e["manuscript_number"]):
        print(f"  Figure {e['manuscript_number']:>2}  {e['slug']:22} {e['figure_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
