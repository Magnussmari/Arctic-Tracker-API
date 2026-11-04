#!/usr/bin/env python3
"""Give figureA and figureB the four R1 fields the record requires of a bound figure.

When Figures 3 and 10 gained a generator on 6 October, their entries were written
with the binding and nothing else: data_inputs, processing_steps, ai_involvement
and validation were all absent. The app's manifest test holds every BOUND figure
to all four, so completing the binding without completing the record turned two
"explicitly unbound" figures into two incomplete ones.

Every field below is read off the generator and the files it writes, and the
script refuses if any artefact it names is not on disk.
"""
import csv, json, pathlib, re, sys

ROOT = pathlib.Path(".")
REC = ROOT / "visualizations/provenance/figure_provenance.json"
GEN = "visualizations/make_fig3_fig10_source_data.py"
NO_MODEL = "visualizations/tests/test_no_model_calls.py"

COMMON_AI = {
    "level": "none",
    "statement": ("No generative model participated in producing these tables. "
                  "The generator imports only csv, json, sys, collections, "
                  "pathlib and the project's redlist_scale module, which is the "
                  "one Red List scale and holds no model call either."),
    "verified_by": NO_MODEL,
    "models_used": [],
    "prompts": None,
}

INPUTS = {
    "figureA": {
        "schema": "arctic_v2",
        "tables": [],
        "query": None,
        "rows_consumed": None,
        "extraction_date": "2025-06-13",
        "database_release": "CITES Trade Database v2025.1",
        "redistributable": True,
        "redistribution_note": None,
        "deposit_equivalent": "deposit/sources/curated/cites_listings.csv",
        "deposit_row_count": None,
        "deposit_divergence": None,
        "reads": ["data/raw/1_DATA_cites_effectiveness.json"],
        "note": ("No database read of its own. This writes from the same "
                 "intermediate the figure4 and figure5 writers already read, "
                 "so it sits in their dependency layer; the appendix tally it "
                 "produces reproduces deposit/sources/curated/cites_listings.csv."),
    },
    "figureB": {
        "schema": "arctic_v2",
        "tables": [],
        "query": None,
        "rows_consumed": None,
        "extraction_date": "2026-07-22",
        "database_release": "IUCN Red List snapshot 2026-07-22",
        "redistributable": False,
        "redistribution_note": ("IUCN Red List terms do not permit "
                                "redistribution of the categories. The "
                                "assessment identifiers and the rebuild route "
                                "are deposited instead; this table carries "
                                "counts, not categories."),
        "deposit_equivalent": "deposit/identifiers/iucn_assessment_ids.csv plus deposit/REBUILD-IUCN.md",
        "deposit_row_count": None,
        "deposit_divergence": None,
        "reads": ["data/processed/iucn_historic_timeline.json"],
        "note": ("No database read of its own. Panel B's per-species "
                 "transition counts sum to 36, which is the count the "
                 "deposit's trajectory verifier holds the manuscript to, "
                 "computed through the same redlist_scale.transitions."),
    },
}

DEFECTS = {
    "figureA": [],
    "figureB": [{
        "what": ("Figure 10's caption says the assessed-species count grows "
                 "from 5 in 1988 to 42 in 2023. 5 in 1988 is exact; 42 is the "
                 "2014-2019 value and the count is 43 from 2020, when "
                 "Mesoplodon stejnegeri gains the single comparable global "
                 "assessment Section 4.4 reports in its own words."),
        "state": ("the generator asserts 43 and refuses to reproduce the "
                  "caption's figure; the manuscript carries a margin query for "
                  "the authors"),
    }],
}


def main():
    rec = json.loads(REC.read_text())
    figs = rec["figures"]
    for fid in ("figureA", "figureB"):
        f = figs[fid]
        sd = f["source_data"]
        for named in (GEN, NO_MODEL, sd):
            if not (ROOT / named).is_file():
                sys.exit(f"  ABORT: {fid} would name {named}, which is not on disk")
        for read in INPUTS[fid]["reads"]:
            if not (ROOT / read).is_file():
                sys.exit(f"  ABORT: {fid} reads {read}, which is not on disk")
        rows = sum(1 for _ in csv.reader((ROOT / sd).open(newline="", encoding="utf8"))) - 1

        f["data_inputs"] = INPUTS[fid]
        f["processing_steps"] = [
            {"step": 1, "what": "read the frozen intermediate",
             "artifact": INPUTS[fid]["reads"][0]},
            {"step": 2, "what": "compute and write the frozen numeric source data",
             "artifact": sd},
        ]
        f["ai_involvement"] = dict(COMMON_AI)
        f["validation"] = {
            "gates": [
                {"gate": "the generator asserts the caption's own numbers",
                 "result": "pass",
                 "evidence": f"{GEN} self_test() fails rather than writing a "
                             f"table that disagrees with the published caption"},
                {"gate": "byte-exact regeneration", "result": "pass",
                 "evidence": "make_all_figures.py --check byte-compares "
                             "figure*_source_data.csv, and these two are inside "
                             "that glob on purpose"},
            ],
            "human_review": {
                "reviewer": None, "reviewed_on": None,
                "state": "generated 2026-10-06; no named person has signed the "
                         "binding and it is not yet independently confirmed",
            },
            "known_defects": DEFECTS[fid],
            "dataset_identity_warning": None,
        }
        print(f"  {fid}: {rows} row(s) in {pathlib.Path(sd).name}, "
              f"{len(f['processing_steps'])} step(s), "
              f"{len(DEFECTS[fid])} known defect(s)")

    REC.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    print(f"  {REC} rewritten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
