#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Quantify importer/exporter double reporting, reproducibly.

WHY THIS EXISTS
---------------
The figure "23,092 shipment coordinate groups appear under both reporter types"
was quoted in a view comment, two source files, three documents and the response
coverage matrix, and an adversarial review found there was **no committed query
that produced it**. A number on a path to a reviewer that nobody can reproduce
is a liability regardless of whether it is correct.

It also questioned the definition, and re-deriving it showed the quoted number
was measuring the wrong thing entirely.

A first version of this script also got the framing wrong, in a way worth
recording because the arithmetic caught it immediately. It described the
quantity-free grouping as "relaxed" and expected a LARGER count. Dropping a
column from a GROUP BY merges groups, so the coarser grouping necessarily
returns FEWER, larger groups: 9,595 against 23,092. The subtraction produced a
negative number, which is how the error announced itself.

What the two counts actually mean:

  coordinate groups (no quantity): distinct shipment coordinates, i.e. distinct
      (species, year, importer, exporter, term, unit, purpose, source) tuples,
      that appear under BOTH reporter types. This is the count of shipments
      described from both ends.
  exact groups (with quantity): the finer partition, where both sides also
      report the same amount. Higher because one coordinate can carry several
      distinct quantities each reported by both sides.

Neither group count is the number anyone should quote. The actionable figure is
**how many RECORDS sit inside a doubly-reported coordinate**, because those are
the rows a naive sum counts twice. That is what this script reports first.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/report_reporter_overlap.py --schema arctic_v2
"""
import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

ROOT = Path(__file__).parent.parent
OUT = ROOT / "ingest/reports/reporter_overlap.json"

KEY = "species_id, year, importer, exporter, term, unit, purpose, source"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--schema", default="arctic_v2")
    args = ap.parse_args()

    schema = validate_schema(args.schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    conn = psycopg2.connect(url, connect_timeout=60)
    try:
        with conn.cursor() as cur:
            cur.execute(f"""
                select count(*) from (
                  select {KEY}, quantity from {schema}.cites_trade_records
                   group by {KEY}, quantity
                  having count(distinct reporter_type) > 1) x""")
            exact_groups = cur.fetchone()[0]

            cur.execute(f"""
                select count(*) from (
                  select {KEY} from {schema}.cites_trade_records
                   group by {KEY}
                  having count(distinct reporter_type) > 1) x""")
            coordinate_groups = cur.fetchone()[0]

            # The number that matters: records living inside a doubly-reported
            # coordinate. These are the rows a sum across reporter_type counts
            # twice.
            cur.execute(f"""
                with doubled as (
                  select {KEY} from {schema}.cites_trade_records
                   group by {KEY}
                  having count(distinct reporter_type) > 1)
                select count(*) from {schema}.cites_trade_records t
                 join doubled d using (species_id, year, importer, exporter,
                                       term, unit, purpose, source)""")
            affected_records = cur.fetchone()[0]

            cur.execute(f"""
                select reporter_type, count(*) from {schema}.cites_trade_records
                 group by reporter_type order by 1""")
            by_side = dict(cur.fetchall())

            cur.execute(f"select count(*) from {schema}.cites_trade_records")
            total = cur.fetchone()[0]
    finally:
        conn.close()

    report = {
        "schema": schema,
        "total_records": total,
        "records_by_reporter_type": by_side,
        "coordinate_key": KEY,
        "doubly_reported_coordinates": coordinate_groups,
        "exact_key": KEY + ", quantity",
        "exact_groups_both_sides_same_quantity": exact_groups,
        "records_in_a_doubly_reported_coordinate": affected_records,
        "share_of_all_records": round(affected_records / total, 4),
        "note": (
            "Quote records_in_a_doubly_reported_coordinate. The group counts are "
            "partition sizes, not shipment counts, and the coarser grouping is "
            "necessarily the smaller one."
        ),
    }

    print(f"total records                          {total}")
    for side, n in sorted(by_side.items()):
        print(f"  reporter_type {side}                      {n}")
    print(f"\ndoubly-reported shipment coordinates   {coordinate_groups}")
    print(f"  ... of which exact-quantity groups   {exact_groups}")
    print(f"\nRECORDS inside a doubly-reported coord  {affected_records}"
          f"  ({affected_records / total:.1%} of all records)")
    print(f"\nQuote the record count. The group counts are partition sizes.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
