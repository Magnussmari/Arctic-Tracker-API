#!/usr/bin/env python3
"""V-32: pipeline.json must still describe the pipeline it was derived from.

WHY THIS EXISTS
---------------
pipeline.json is the single record of the S1-S7 pipeline. The platform's
/pipeline page reads it, and both stage diagrams are generated from it, so a
stale record is a wrong diagram and a wrong page at the same time.

The record carries the SHA-256 of the deposited Supplementary Table 4 it was
built from. If that table changes and the record is not rebuilt, the
audit-question bindings drawn on the platform are the old ones. That is the
failure this checks, and it is checkable precisely because the record wrote
down what it was derived from.

Needs no database. It compares deposited files with each other.

Usage:
  python3 deposit/verification/verify_pipeline_record.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# This file lives in two places and must behave the same in both: shipped at
# deposit/verification/, where a reader runs it and the deposit is the parent,
# and maintained at ingest/, which build_deposit.py copies from and where the
# deposit is a sibling directory. The two copies are required to be byte
# identical — the builder refuses to run when they drift — so the path cannot be
# written for one of them. Resolved by looking for the record rather than
# assuming where it is: run from ingest/ with the parent-directory form, this
# reported "missing: pipeline.json" and could only ever fail.
def _deposit() -> Path:
    for cand in (HERE.parent, HERE.parent / "deposit", HERE / "deposit"):
        if (cand / "pipeline.json").exists():
            return cand
    return HERE.parent  # report the missing file against the shipped location


DEPOSIT = _deposit()
RECORD = DEPOSIT / "pipeline.json"
TABLE4 = DEPOSIT / "supplementary/supplementary_table_4_step_question_mapping.csv"
FIGURES = DEPOSIT / "figures"


def main() -> int:
    for p in (RECORD, TABLE4):
        if not p.exists():
            print(f"missing: {p.relative_to(DEPOSIT)}")
            return 2

    rec = json.loads(RECORD.read_text())
    problems: list[str] = []

    # A checker that cannot tell two digests apart passes everything.
    if hashlib.sha256(b"a").hexdigest() == hashlib.sha256(b"b").hexdigest():
        print("SELF-TEST FAIL: the digest does not distinguish inputs")
        return 2

    # 1. The record must have been built from the table that is deposited now.
    actual = hashlib.sha256(TABLE4.read_bytes()).hexdigest()
    if rec.get("source_table_4_sha256") != actual:
        problems.append(
            f"built from Supplementary Table 4 {str(rec.get('source_table_4_sha256'))[:12]}…, "
            f"deposited is {actual[:12]}… — rebuild with build_pipeline_diagram.py")

    # 2. The bindings in the record must be the bindings in the table.
    from_table: dict[str, set[str]] = {}
    for row in csv.DictReader(TABLE4.open()):
        # "S4-S6" is a range: reading only the S-numbers it names dropped S5.
        for a, z in re.findall(r"S(\d)(?:\s*[-–]\s*S(\d))?", row["producing_steps"]):
            for i in range(int(a), int(z or a) + 1):
                from_table.setdefault(f"S{i}", set()).add(row["question"])
    for step in rec["steps"]:
        want = sorted(from_table.get(step["id"], set()))
        got = sorted(step.get("audit_questions", []))
        if want != got:
            problems.append(f"{step['id']}: record binds {got or 'nothing'}, "
                            f"Table 4 binds {want or 'nothing'}")

    # 3. Every step must carry the display fields the diagram and page read, and
    #    none of them may be an unminted placeholder.
    # ai_tool and data_source are checked too. They are not drawn, so a
    # placeholder in them is invisible to the figures, and both carried one
    # for weeks while every display field was clean: the Methods box is
    # generated from ai_tool, so "[MINT: 2.5 Pro build/date]" was one pass
    # away from the journal.
    for step in rec["steps"]:
        for field in ("short_title", "tool_name", "source_name", "gate",
                      "ai_tool", "data_source"):
            v = step.get(field)
            if not v:
                problems.append(f"{step['id']}: {field} is empty; the diagram "
                                f"would draw a blank box")
            elif "[MINT" in str(v) or "[TOM/" in str(v):
                problems.append(f"{step['id']}: {field} still carries an "
                                f"unminted placeholder {v!r}")

    # 4. The committed figures must be what the record renders to, right now.
    #    Checking that a figure names the right gates catches a figure drawn from
    #    a different pipeline; it does not catch a record that changed after the
    #    figure was drawn, which is the drift that actually happens. The
    #    generator is byte-deterministic, verified across repeated runs, so
    #    re-rendering into a scratch directory and comparing is exact.
    import os
    import subprocess
    import sys
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        env = dict(os.environ, PIPELINE_FIGURES_OUT=td)
        r = subprocess.run([sys.executable, str(DEPOSIT / "build_pipeline_diagram.py")],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            problems.append(f"the generator does not run: "
                            f"{(r.stderr or r.stdout).strip().splitlines()[-1][:90]}")
        else:
            for name in ("pipeline-stage1.svg", "pipeline-stage2.svg"):
                fresh, committed = Path(td) / name, FIGURES / name
                if committed.exists() and fresh.exists() and \
                        fresh.read_bytes() != committed.read_bytes():
                    problems.append(
                        f"{name} is not what pipeline.json renders to today — "
                        f"the record moved and the figure did not. Run "
                        f"build_pipeline_diagram.py")

    # 5. The drawn figures must exist and must name every step they cover.
    for name, ids in (("pipeline-stage1.svg", ("S1", "S2", "S3")),
                      ("pipeline-stage2.svg", ("S4", "S5", "S6", "S7"))):
        f = FIGURES / name
        if not f.exists():
            problems.append(f"{name} has not been generated")
            continue
        svg = f.read_text()
        for sid in ids:
            gate = next(s["gate"] for s in rec["steps"] if s["id"] == sid)
            if gate not in svg:
                problems.append(f"{name} does not draw {gate}")

    n = len(rec["steps"])
    print(f"V-32 pipeline record: {n} steps, "
          f"{sum(len(s['audit_questions']) for s in rec['steps'])} question "
          f"bindings, 2 figures, checked against Supplementary Table 4")
    if problems:
        print(f"\nTHE RECORD AND THE DEPOSIT DISAGREE ({len(problems)}):\n")
        for p_ in problems:
            print(f"  {p_}")
        print("\nThe platform draws this record. A stale record is a wrong "
              "diagram on a page that says it cannot be wrong.")
        return 1
    print("the record, the deposited table and the drawn figures agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
