#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-16
"""Reporter side: how much of the record count is doubly-reported? (analysis)

WHAT THIS IS
------------
CITES records are filed by the importer,
the exporter, or both, and the paper's record counts sum all of them. When both
sides report the same shipment it is counted twice. This measures how often that
happens, directly from the corpus.

WHY IT IS ANSWERED FROM THE CORPUS
----------------------------------
A partition identity (E + I = total) is not by itself evidence of
double-counting, and the raw CITES download is not needed: the corpus carries a
`reporter_type` column and every field the raw file has, so the question is
answerable here.

WHAT IT REPORTS
---------------
  - the split of records by reporter side;
  - the number of shipment-keys reported by BOTH sides, and the redundant
    second-side records that implies under a strict natural-key match;
  - the record count against a one-row-per-shipment-key count.

WHAT IT DOES NOT DECIDE
-----------------------
The exact shipment count. That depends on the matching rule (whether two rows
with the same key but different quantities are one shipment or two), which is a
methodological choice for the authors, not a fact in the data. This bounds it and
supplies every number once a rule is chosen.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/analysis_reporter_side.py
"""
from __future__ import annotations

import os
import sys

import psycopg2

SCHEMA = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")
KEY = ("year, species_id, taxon, appendix, term, unit, importer, exporter, "
       "coalesce(origin,''), purpose, source")


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1
    conn = psycopg2.connect(url, connect_timeout=60)
    cur = conn.cursor()
    T = f"{SCHEMA}.cites_trade_records"

    cur.execute(f"select reporter_type, count(*) from {T} group by reporter_type")
    by_side = dict(cur.fetchall())
    total = sum(by_side.values())
    e, i = by_side.get("E", 0), by_side.get("I", 0)

    cur.execute(f"""
        with k as (
          select {KEY},
                 count(*) filter (where reporter_type='I') as ni,
                 count(*) filter (where reporter_type='E') as ne
          from {T} group by {KEY})
        select count(*),
               count(*) filter (where ni>0 and ne>0),
               coalesce(sum(least(ni,ne)) filter (where ni>0 and ne>0), 0)
        from k""")
    keys, both_sided, redundant = cur.fetchone()
    conn.close()

    if total == 0:
        print("CANNOT RUN: the corpus is empty.")
        return 2

    print(f"reporter side, schema {SCHEMA} ({total:,} records)")
    print(f"  exporter-reported: {e:,} ({100*e/total:.1f}%)")
    print(f"  importer-reported: {i:,} ({100*i/total:.1f}%)")
    print(f"  (the published record count sums both sides)")
    print(f"\ndistinct shipment-keys: {keys:,}")
    print(f"  reported by BOTH sides: {both_sided:,}")
    print(f"  redundant second-side records (strict min(I,E) per key): "
          f"{redundant:,} ({100*redundant/total:.1f}% of all records)")
    print(f"\nThe redundant fraction is a lower bound under a strict key match; the "
          f"exact\nshipment count depends on the matching rule the authors choose "
          f"(item 7).")
    # A sanity assertion: the sides must partition the corpus exactly.
    if e + i != total:
        print(f"\nWARNING: E+I ({e+i}) != total ({total}); a row has a reporter_type "
              f"that is neither E nor I. Investigate before quoting these numbers.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
