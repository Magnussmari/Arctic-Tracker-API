#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-09-01
"""How much of the trade corpus records a unit, and how much is convention.

REPORT, not a gate. It judges nothing. It measures one thing the choice of
quantity measure depends on and that nothing else counts.

WHY THIS EXISTS
---------------
The platform's species pages group trade into dimensions and label the largest
one "count, measured in specimens". That label was reached two ways at once:

  a unit of "number of specimens", which the record states, and
  a BLANK unit, which CITES uses to mean a count of the term.

The convention is correct and standard. But the page said those records "report
a quantity in specimens", and for the blank-unit majority no unit is reported at
all — the site is applying a convention and printing the result as though the
record had said it. The same shape as rendering an absent IUCN scope as the word
"Global", and roughly ten times the volume.

The page no longer states a share, because the application role cannot read the
raw `unit` column — arctic_v2 is denied to it and neither API view exposes the
field. That is the withholding working as designed, and it means the platform
cannot verify a percentage about its own corpus. So the number lives here, where
the credential exists and where it is recomputed on every run rather than
remembered.

Usage:
  ARCTIC_DATABASE_URL=... python3 ingest/report_unit_provenance.py
"""
from __future__ import annotations

import os
import sys

import psycopg2

SCHEMA = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("T-26 CANNOT RUN: ARCTIC_DATABASE_URL is not set.")
        return 2

    with psycopg2.connect(url) as conn, conn.cursor() as cur:
        cur.execute(f"""
            select
              count(*)                                                       as total,
              count(*) filter (where unit is null or btrim(unit) = '')       as blank,
              count(*) filter (
                where lower(btrim(coalesce(unit, ''))) = 'number of specimens'
              )                                                              as specimens,
              count(distinct nullif(btrim(coalesce(unit, '')), ''))          as named_units
            from {SCHEMA}.cites_trade_records
        """)
        total, blank, specimens, named = cur.fetchone()

        if not total:
            print("T-26: the trade table is empty, so nothing was measured. "
                  "That is not a passing state for a report about it.")
            return 2

        counted = blank + specimens
        cur.execute(f"""
            select term, count(*) as n
              from {SCHEMA}.cites_trade_records
             where unit is null or btrim(unit) = ''
             group by term order by n desc limit 6
        """)
        terms = cur.fetchall()

    print(f"T-26 unit provenance: {total:,} trade records, "
          f"{named} distinct named units")
    print(f"  unit stated                     {total - blank:>9,}  "
          f"({(total - blank) / total:.1%})")
    print(f"  unit blank, read as a count     {blank:>9,}  "
          f"({blank / total:.1%})")
    print()
    print(f"  the platform shows both as the count dimension. Of that "
          f"dimension, {blank / counted:.1%} is the CITES blank-unit")
    print(f"  convention applied rather than a unit any record states.")
    print()
    print("  what the blank-unit rows are counts OF, most frequent first:")
    for term, n in terms:
        print(f"    {str(term or '(no term)'):<22} {n:>9,}")
    print()
    print("  A count of live animals and a count of carvings are not the same")
    print("  quantity, which is why the platform will not sum this dimension")
    print("  without naming the term.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
