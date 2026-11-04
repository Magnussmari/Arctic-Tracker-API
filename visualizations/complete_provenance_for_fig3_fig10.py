#!/usr/bin/env python3
"""Give Figures 3 and 10 the pipeline records their bindings already assume.

Measured 6 October 2026, from two provenance checks disagreeing:

  audit_letter.py             read figure_map and reported 8 scripted figures
  check_pipeline_accounting   read figures{} and reported 6

Both were reading the same file. `figure_map` had been updated when
make_fig3_fig10_source_data.py produced figureA and figureB, and the `figures`
dict - which is where a pipeline's script, query and status live - had not. So
the record asserted a binding for two figures while carrying no pipeline record
for either, and two checks built on the same file gave different answers.

The script is real: visualizations/make_fig3_fig10_source_data.py, one script
emitting both files. So the repair is to complete the record, not to soften the
claim. This writes the two missing entries with the script that actually
produces them, and refuses if anything it asserts is not true on disk.

The count that follows is EIGHT scripted pipelines, not nine: one script
produces both figures, and counting it twice to make the figures match would be
the same error one level down.

Idempotent. Run it twice and the second run says there is nothing to do.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
REC = HERE / "provenance" / "figure_provenance.json"
SCRIPT = "visualizations/make_fig3_fig10_source_data.py"

NEW = {
    "figureA": {
        "title": "CITES-listed Arctic species and appendices (manuscript Figure 3)",
        "script": SCRIPT,
        "source_data": "visualizations/source_data/figureA_source_data.csv",
    },
    "figureB": {
        "title": "Conservation status patterns; category changes; trajectory "
                 "(manuscript Figure 10)",
        "script": SCRIPT,
        "source_data": "visualizations/source_data/figureB_source_data.csv",
    },
}


def main():
    if not (REPO / SCRIPT).exists():
        sys.exit(f"  ABORT: {SCRIPT} does not exist, so the record must not "
                 f"claim it produces anything")
    rec = json.loads(REC.read_text(encoding="utf8"))
    figs = rec["figures"]
    bound = {e["figure_id"] for e in rec["figure_map"] if e["figure_id"]}

    added = []
    for fid, entry in NEW.items():
        if fid not in bound:
            sys.exit(f"  ABORT: figure_map does not bind {fid}, so adding a "
                     f"pipeline record for it would invent a figure")
        if fid in figs and figs[fid].get("script"):
            continue
        sd = REPO / entry["source_data"]
        if not sd.exists():
            sys.exit(f"  ABORT: {entry['source_data']} is not on disk, so the "
                     f"record must not say the pipeline produced it")
        figs[fid] = {
            "title": entry["title"],
            "script": entry["script"],
            "generator": None,
            "intermediate": None,
            "source_data": entry["source_data"],
            "query": None,
            "status": "generated 2026-10-06; binding not yet independently "
                      "confirmed",
            "data_inputs": None,
        }
        added.append(fid)

    if not added:
        print("  nothing to do: both pipeline records are already present")
        return 0

    scripted = {k for k, v in figs.items() if v.get("script")}
    distinct = {v["script"] for k, v in figs.items() if v.get("script")}
    REC.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf8")
    print(f"  added pipeline record(s): {', '.join(added)}")
    print(f"  the record now carries {len(scripted)} scripted figure(s) from "
          f"{len(distinct)} distinct script(s)")
    produced = sorted(e["manuscript_number"] for e in rec["figure_map"]
                      if e["figure_id"] in scripted)
    print(f"  producing manuscript figures {produced}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
