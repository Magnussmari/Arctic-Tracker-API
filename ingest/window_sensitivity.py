#!/usr/bin/env python3
"""V-10b: what the trajectory result does as the observation window and baseline bound move.

WHY THIS EXISTS
---------------
The manuscript marks the observation window N and the baseline bound B
"outcome-determining, must be set + sensitivity grid reported before
resubmission". This script computes that grid. V-10 alone does not: it
compares each species' first comparable global assessment with its last, and
never looks at when the species was listed. Under that rule N and B do not exist.

This is not a recommendation and does not choose N or B. Choosing them is a
domain judgement about how long a listing needs to act and how far from the
listing an assessment can sit and still be a baseline. What this does is say
what each choice costs and whether the finding survives it, so the choice is
made in front of the numbers instead of behind them.

DEFINITIONS USED, which are themselves part of what needs deciding
------------------------------------------------------------------
  listing year   the earliest dated CITES Appendix listing for the species
  baseline       the comparable global assessment nearest the listing year,
                 accepted only if |assessment year - listing year| <= B
  outcome        the latest comparable global assessment at or before
                 listing year + N, and strictly later than the baseline
  scored         a species with both, under the D10 comparability rules that
                 V-10 uses, on the global-and-European series (from 21 October 2026)

A species drops out of a cell when no assessment sits within B of its listing,
or when nothing comparable follows inside N. Those drops are the cost of a
tight window and are reported per cell rather than hidden in a percentage.

Usage:
  ARCTIC_DATABASE_URL=... python3 deposit/verification/window_sensitivity.py
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

WINDOWS = [10, 15, 20, 25, 30, None]     # None = no window, use everything after
BOUNDS = [5, 10, 15]


def self_test() -> bool:
    """A grid built on a broken comparator would print a tidy wrong table."""
    if rl.classify("LC", "EN") != "deteriorated":
        print("SELF-TEST FAIL: LC -> EN does not classify as deteriorated")
        return False
    if rl.classify("EN", "LC") != "improved":
        print("SELF-TEST FAIL: EN -> LC does not classify as improved")
        return False
    if rl.classify("VU", "VU") != "unchanged":
        print("SELF-TEST FAIL: VU -> VU does not classify as unchanged")
        return False
    if rl.comparable("DD"):
        print("SELF-TEST FAIL: DD is treated as a comparable risk rank")
        return False
    return True


def cell(seq, listed, window, bound):
    """Score every species under one (N, B) pair."""
    verdicts = Counter()
    dropped_baseline = dropped_outcome = 0
    for name, rows in seq.items():
        ly = listed.get(name)
        if ly is None:
            dropped_baseline += 1
            continue
        usable = [(y, s) for y, s in rows if rl.comparable(s)]
        if not usable:
            dropped_baseline += 1
            continue
        near = [(y, s) for y, s in usable if abs(y - ly) <= bound]
        if not near:
            dropped_baseline += 1
            continue
        by, bs = min(near, key=lambda t: (abs(t[0] - ly), t[0]))
        after = [(y, s) for y, s in usable
                 if y > by and (window is None or y <= ly + window)]
        if not after:
            dropped_outcome += 1
            continue
        oy, os_ = max(after, key=lambda t: t[0])
        verdicts[rl.classify(bs, os_)] += 1
    scored = sum(verdicts[k] for k in ("improved", "unchanged", "deteriorated"))
    return verdicts, scored, dropped_baseline, dropped_outcome


def main() -> int:
    if not self_test():
        return 2
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--schema", default="arctic_v2")
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

    cur.execute(f"""
        select s.scientific_name, min(extract(year from l.listing_date))::int
        from {schema}.cites_listings l
        join {schema}.species s on s.id = l.species_id
        where l.listing_date is not null
        group by s.scientific_name
    """)
    listed = dict(cur.fetchall())
    conn.close()

    print(f"V-10b window sensitivity, schema {schema}, global and European assessments (21 October 2026)\n")
    print(f"{len(seq)} species with a global or European assessment; "
          f"{len(listed)} with a dated listing\n")
    print("  N = observation window in years after listing")
    print("  B = how far from the listing year a baseline assessment may sit\n")
    print(f"  {'N':>5} {'B':>3} {'scored':>7} {'impr':>5} {'unch':>5} "
          f"{'deter':>6} {'impr-deter':>11}  dropped")
    print("  " + "-" * 74)

    signs = set()
    scored_counts = []
    for w in WINDOWS:
        for b in BOUNDS:
            v, scored, db_, do_ = cell(seq, listed, w, b)
            net = v["improved"] - v["deteriorated"]
            signs.add((net > 0) - (net < 0))
            scored_counts.append(scored)
            label = "all" if w is None else str(w)
            print(f"  {label:>5} {b:>3} {scored:>7} {v['improved']:>5} "
                  f"{v['unchanged']:>5} {v['deteriorated']:>6} {net:>+11}  "
                  f"{db_} no baseline, {do_} no outcome")

    print()
    # The denominator is the finding here, and it is easy to miss beside a
    # stable sign. V-10 scores 38 species because it compares each species'
    # first comparable assessment with its last and never asks when the species
    # was listed. Requiring a baseline near the listing year is what N and B
    # mean, and it removes most of the portfolio.
    lo, hi = min(scored_counts), max(scored_counts)
    print(f"Species scored ranges from {lo} to {hi} across this grid. V-10, "
          f"which uses each species' first and last comparable assessment and "
          f"never looks at the listing year, scores 38. Anchoring the baseline "
          f"to the listing is what N and B do, and it removes between "
          f"{38 - hi} and {38 - lo} of those species: most have no comparable "
          f"assessment within B years of being listed. Whatever is reported "
          f"rests on that smaller set, and the drop belongs beside the result "
          f"rather than in a footnote.\n")
    if len(signs - {0}) > 1:
        print("THE SIGN FLIPS ACROSS THIS GRID. Under some choices of N and B "
              "the listed portfolio improves on balance and under others it "
              "deteriorates, so the effectiveness claim does not survive the "
              "choice and the title and abstract have to de-claim.")
    elif signs <= {0}:
        print("Net movement is zero everywhere in this grid: improvements and "
              "deteriorations balance under every choice.")
    else:
        direction = "improvement" if 1 in signs else "deterioration"
        print(f"The sign is stable across this grid: net {direction} under "
              f"every choice of N and B above. The magnitude moves and the "
              f"number of species scored moves with it, both of which belong "
              f"in the reported grid, but no choice here reverses the finding.")
    print("\nNeither N nor B is chosen here. This says what each choice costs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
