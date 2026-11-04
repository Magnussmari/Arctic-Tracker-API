#!/usr/bin/env python3
"""V-10: the status-trajectory finding, derived once, under D10.

Replaces every ad-hoc scale in this repository. Prints the numbers the
manuscript should state, the species excluded and why, and the genuine
transitions. Scope is pinned to GLOBAL: the is_latest flag points at a European
regional assessment for 17 of 43 species, so a tally built on it is a different
and wrong number.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

import psycopg2

# Importing a sibling here writes __pycache__ INTO the deposit, and
# verify_deposit_accounted.py rejects bytecode in a citable archive. Running
# these scripts in place is the intended use, so the run must not leave
# residue behind, or the archive gate would fail merely because the verifiers
# had been run.
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import validate_schema           # noqa: E402
import redlist_scale as rl               # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--schema", default="arctic_v2")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    schema = validate_schema(args.schema)

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment)")

    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(f"""
        select s.scientific_name, a.status, a.year_published
        from {schema}.iucn_assessments a
        join {schema}.species s on s.id = a.species_id
        where {rl.series_sql('a')} and a.year_published is not null
        order by s.scientific_name, a.year_published, a.assessment_id
    """)
    seq: dict[str, list] = {}
    for name, status, year in cur.fetchall():
        seq.setdefault(name, []).append((year, status))

    total = len(seq)
    verdicts = Counter()
    excluded, scored, all_trans = [], [], []

    for name, rows in seq.items():
        usable = [(y, s) for y, s in rows if rl.comparable(s)]
        if len(usable) < 2:
            why = (rl.reason_excluded(rows[0][1]) if not usable
                   else "only one comparable assessment, so no trajectory exists")
            excluded.append((name, rows[0][1], rows[-1][1], why))
            verdicts["excluded"] += 1
            continue
        v = rl.classify(usable[0][1], usable[-1][1])
        verdicts[v] += 1
        scored.append((name, usable[0], usable[-1], v))
        all_trans.extend(rl.transitions(rows))

    n_scored = verdicts["improved"] + verdicts["deteriorated"] + verdicts["unchanged"]

    print(f"V-10 status trajectories under D10, schema {schema}, global and European assessments (21 October 2026)\n")
    print(f"{total} species with a global or European assessment")
    print(f"{n_scored} carry a comparable trajectory; {verdicts['excluded']} excluded\n")

    if n_scored:
        for k in ("unchanged", "improved", "deteriorated"):
            print(f"  {k:14} {verdicts[k]:3}  ({round(100*verdicts[k]/n_scored)}%)")

    ti = Counter(d for _, _, d in all_trans)
    print(f"\ngenuine transitions between comparable assessments: {len(all_trans)}")
    print(f"  improvements   {ti['improved']}")
    print(f"  deteriorations {ti['deteriorated']}")

    print(f"\nexcluded species ({len(excluded)}), each with the reason:")
    for name, first, last, why in excluded:
        print(f"  {name:34} {str(first):6}->{str(last):6}  {why}")

    if args.verbose and scored:
        print("\nscored species:")
        for name, (y0, s0), (y1, s1), v in scored:
            print(f"  {name:34} {s0} {y0} -> {s1} {y1}  {v}")

    print("\nThe exclusions are the finding, not a shortfall. Each excluded species "
          "has a baseline that cannot be compared to a modern category without "
          "asserting a change no assessor made.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
