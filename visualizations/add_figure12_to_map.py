#!/usr/bin/env python3
"""Put manuscript Figure 12 in the provenance map, where it has never been.

The manuscript has twelve numbered figures. The provenance record has eleven,
because Figure 12 - the seven-step pipeline journal - was drawn after the map
was written and nobody went back. Everything downstream inherited the gap: the
deposit's Source Data index lists eleven figures, so the Data Availability
statement's "Eight of the twelve numbered figures" could not be checked against
it, and the check comparing the two asked the statement to say "eleven" - which
would have been the paper agreeing with an incomplete index rather than the
index being completed. Carried as D348 since the index was first read.

Figure 12 is a schematic. It plots no computed values, so it has no Source Data
and that is its finished state, not a gap: `none - no scripted pipeline` is the
wrong phrase for it and the right one is that it has nothing to plot. It is
nonetheless DRAWN by a deposited script, `build_figure12_journal.py`, from
`deposit/pipeline.json`, and the binding evidence says so rather than implying
the figure appeared from nowhere.

18 October 2026: the co-author's manuscript added a Figure 5, so this figure is
now Figure 13 and its artefacts were renamed (build_figure13_journal.py,
figure13-caption.md, figure13-pipeline-journal.svg). This script ran once, on
6 October, and is kept as the record of that change; the NEEDS paths below are
the current names, so a re-run refuses on "already in the map" rather than on
a missing file.

Refuses rather than guesses: it stops if Figure 12 is already in the map, if the
slug is taken, or if the artefacts it names are not deposited.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REC = ROOT / "visualizations/provenance/figure_provenance.json"
NEEDS = ["deposit/build_figure13_journal.py", "deposit/pipeline.json",
         "deposit/figures/figure13-caption.md",
         "deposit/figures/figure13-pipeline-journal.svg"]

ENTRY = {
    "manuscript_number": 12,
    "manuscript_caption_stub": "The seven-step evaluation pipeline, and the "
                               "human gate closing each step",
    "figure_id": None,
    "slug": "pipeline-journal",
    "binding_evidence": (
        "NO BINDING ESTABLISHED, and none to establish. Schematic figure: it "
        "plots no computed values, so it has no Source Data and no pipeline to "
        "bind to. It is drawn by deposit/build_figure12_journal.py from "
        "deposit/pipeline.json, the single source of truth for the step table, "
        "which carries the SHA-256 of the deposited Supplementary Table 4."),
    "confirmed_by": None,
    "confirmed_on": None,
}


def main():
    for rel in NEEDS:
        if not (ROOT / rel).is_file():
            sys.exit(f"  ABORT: the entry would name {rel}, which is not deposited")

    rec = json.loads(REC.read_text())
    fmap = rec["figure_map"]
    if any(e.get("manuscript_number") == 12 for e in fmap):
        print("  Figure 12 is already in the map; nothing written")
        return 0
    if any(e.get("slug") == ENTRY["slug"] for e in fmap):
        sys.exit(f"  ABORT: the slug {ENTRY['slug']!r} is taken")

    fmap.append(ENTRY)
    nums = sorted(e["manuscript_number"] for e in fmap)
    if nums != list(range(1, 13)):
        sys.exit(f"  ABORT: the map would cover {nums}, not 1 to 12")
    REC.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    print(f"  Figure 12 added: slug {ENTRY['slug']}, schematic, no Source Data")
    print(f"  the map now covers manuscript figures 1 to 12")
    return 0


if __name__ == "__main__":
    sys.exit(main())
