#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""V-23: the evidence binding a figure to a manuscript number must still hold.

WHY THIS EXISTS
---------------
Each entry in figure_provenance.json carries a `binding_evidence` string saying
why a pipeline is believed to produce a given manuscript figure. For Figure 8 it
reads:

    "figure3_source_data.csv row 1 gives importer AE at 75,190 records. …
     Exact match on 75,190."

That was true when written. After the figure pipeline was moved onto the
manuscript's corpus the same row reads 83,131, and the evidence cited a number
the pipeline no longer produces. The binding is still correct — same script, same
figure — but the proof of it had quietly stopped being a proof.

This is the failure mode the whole provenance file exists to prevent, occurring
inside the provenance file: an assertion about the data, written once, never
re-checked.

WHAT IT ASSERTS
---------------
Every thousands-separated number quoted in a binding_evidence string still
appears in the Source Data file that evidence names. Nothing more: it cannot tell
whether the binding is right, only whether the reason given for it is still true.

A binding whose evidence cites no number is reported, not failed. Several are
bound by argument — "exactly one script emits a heatmap trace" — and an argument
is not checkable here. Counting them keeps that visible instead of letting the
pass rate imply more coverage than there is.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROV = ROOT / "visualizations" / "provenance" / "figure_provenance.json"
SOURCE_DATA = ROOT / "visualizations" / "source_data"

NUM = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")
CSV_REF = re.compile(r"(figure\d+_source_data\.csv)")


def main() -> int:
    if not PROV.exists():
        print(f"V-23 CANNOT RUN: {PROV} is absent.")
        return 2
    entries = json.loads(PROV.read_text()).get("figure_map", [])
    if not entries:
        # Silence must not pass: an empty map would check nothing and report
        # success, which is the defect this file is about.
        print("V-23 CANNOT RUN: figure_provenance.json binds no figures at all.")
        return 2

    # The record's own provenance. On 2026-08-15 this file recorded a commit
    # 109 commits behind HEAD, spanning changes that altered the figures
    # themselves: the corpus switch, Figure 1's appendix panel, Figure 7's
    # hardcoded share. A reader checking out that hash to reproduce would
    # build different figures from the ones described here.
    #
    # The test is not "is the hash current" — it need not be, if nothing
    # relevant changed. It is whether any figure script has changed since,
    # which is what would make the record describe code that no longer exists.
    import json as _json
    import subprocess as _sp
    meta = _json.loads(PROV.read_text())
    provenance_stale = []

    # The authoritative test is a digest of the pipeline source, not the commit.
    # A commit stamped when the figures were built necessarily predates the
    # commit carrying the figure-code change, so comparing commits reports
    # staleness on every ordinary run — which is exactly what happened after the
    # auto-stamp was added on 2026-08-15 to stop this record going stale.
    #
    # The digest asks the real question: is the pipeline on disk the pipeline
    # that produced these figures? That has no ordering problem.
    recorded_digest = meta.get("pipeline_source_sha256")
    if recorded_digest:
        import hashlib as _hl
        viz = ROOT / "visualizations"
        _h = _hl.sha256()
        for f in sorted(list((viz / "scripts").glob("*.py"))
                        + list((viz / "data_processing").glob("*.py"))):
            _h.update(f.name.encode())
            _h.update(f.read_bytes())
        if _h.hexdigest() != recorded_digest:
            provenance_stale.append(
                "the figure pipeline on disk differs from the one that produced "
                "these figures. Re-run 'make figures'.")
    else:
        provenance_stale.append(
            "the record carries no pipeline digest, so what produced these "
            "figures cannot be established. Re-run 'make figures'.")

    checked = stale = argued = 0
    problems: list[str] = []

    for e in entries:
        ev = e.get("binding_evidence") or ""
        fig = e.get("manuscript_number")
        numbers = set(NUM.findall(ev))
        if not numbers:
            argued += 1
            continue

        named = CSV_REF.findall(ev)
        if not named:
            problems.append(f"Figure {fig}: evidence quotes {sorted(numbers)} but "
                            f"names no Source Data file to check them against")
            continue

        for csv_name in set(named):
            path = SOURCE_DATA / csv_name
            if not path.exists():
                problems.append(f"Figure {fig}: evidence cites {csv_name}, "
                                f"which does not exist")
                continue
            body = path.read_text()
            for n in sorted(numbers):
                checked += 1
                # Source Data is written without separators; compare both forms.
                if n not in body and n.replace(",", "") not in body:
                    stale += 1
                    problems.append(
                        f"Figure {fig}: evidence cites {n} from {csv_name}, "
                        f"which no longer contains it")

    print(f"V-23 binding evidence: {len(entries)} binding(s), "
          f"EXAMINED {checked} quoted value(s) across "
          f"{len(entries) - argued} evidence string(s); "
          f"{argued} bound by argument rather than by a number")

    if provenance_stale:
        print(f"\nV-23 FAIL: the provenance record is stale about itself:\n")
        for s in provenance_stale:
            print(f"  {s}")
        print("\nThe commit field says which code produced these figures. If the")
        print("figure code moved on, the record describes something that no longer")
        print("exists, and a reader reproducing from it gets different figures.")
        return 1

    if problems:
        print(f"\nV-23 FAIL: {len(problems)} binding(s) cite evidence that no "
              f"longer holds:\n")
        for p in problems:
            print(f"  {p}")
        print("\nThe binding may still be correct. The reason given for it is not,")
        print("and a provenance record whose evidence has gone stale is worse than")
        print("none: it reads as verified.")
        return 1

    if checked == 0:
        print("\nV-23 FAIL: no binding quotes a checkable number, so this gate "
              "examined nothing and would pass for free.")
        return 1

    print(f"\nV-23 PASS: every number quoted as binding evidence still appears "
          f"in the Source Data it names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
