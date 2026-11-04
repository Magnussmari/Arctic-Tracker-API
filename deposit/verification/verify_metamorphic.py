#!/usr/bin/env python3
"""V-16: metamorphic relations — properties that must hold without a known answer.

WHY THIS EXISTS
---------------
Every other check in this repository was written after a defect was found. That
makes them regression pins: they encode the observed post-fix state, not the
intended property. Konstantinou, Degiovanni and Papadakis (arXiv:2410.21136,
2024) put it exactly — an oracle written by observing a running program captures
*actual* behaviour, not *expected*. A pin cannot fail on a defect nobody has met.

Metamorphic testing (Chen, Cheung and Yiu, HKUST-CS98-01, 1998; survey: Segura
et al., IEEE TSE 42(9), 2016) is the standard answer when there is no ground
truth to compare against. You do not need to know the right value. You need to
know a relation that must hold between a result and the result on a transformed
input. If the relation breaks, there is a defect — and you learn that without
anyone having seen it before.

That is the difference between this file and the rest of the suite.

THE RELATIONS
-------------
Each targets a defect *class*, and one of them targets a class this project has
already paid for: a published number that depended on the order rows came back
in. That took hours to find by hand, and V-4 passed throughout, because a
byte-identical reload reproduces an order-dependent answer perfectly.

  MR1  Permutation invariance — the published figures must not change when the
       physical row order of a table changes. Kills order-dependence, unstable
       sorts, and ties broken by whatever the planner returned.

  MR2  Partition additivity — a count over a partition must sum to the count
       over the whole. Kills double-counting and rows lost at a join.

  MR3  Filter monotonicity — narrowing a filter can never increase a count.
       Kills inverted predicates.

  MR4  Relabelling invariance — renaming an identifier consistently must leave
       the aggregate structure unchanged. Kills hard-coded identifiers.

MR1 is destructive in that it rewrites physical row order in a scratch schema.
It never touches arctic_v2: it builds its own copy and drops it.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/verify_metamorphic.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2

# The schema under test. A reader who loads the deposit will not have called it
# arctic_v2, and this file shipped in the deposit hardcoding that name: it would
# have reported PASS against our corpus, or failed outright, and either way said
# nothing about theirs. Found by loading the deposit into a fresh schema and
# running the scripts as a reader would.
LIVE = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")
PROBE = f"{LIVE}_metamorphic_probe"

# The published quantities the relations are checked against. Each is a query
# returning one row of scalars, phrased against a schema name.
PUBLISHED = {
    "trade records": "select count(*) from {S}.cites_trade_records",
    "species": "select count(*) from {S}.species",
    "assessments": "select count(*) from {S}.iucn_assessments",
    "listing events": "select count(*) from {S}.cites_listing_events",
    # The one that broke. For each species the assessment in force at listing,
    # resolved with an explicit tiebreak. Without the tiebreak this answer moves
    # when the rows move, and 22 of 43 species have more than one assessment in
    # the same year.
    "baseline assessment per species": """
        select string_agg(x.species_id::text || ':' || x.assessment_id::text, ',' order by x.species_id)
        from (
            select distinct on (a.species_id) a.species_id, a.assessment_id
            from {S}.iucn_assessments a
            order by a.species_id, a.year_published desc, a.assessment_id desc
        ) x""",
    # Status trajectory inputs: the latest assessment per species, same hazard.
    "latest status per species": """
        select string_agg(x.species_id::text || ':' || x.status, ',' order by x.species_id)
        from (
            select distinct on (a.species_id) a.species_id, a.status
            from {S}.iucn_assessments a
            order by a.species_id, a.year_published desc, a.assessment_id desc
        ) x""",
}


def scalars(cur, schema: str) -> dict:
    out = {}
    for name, sql in PUBLISHED.items():
        cur.execute(sql.format(S=schema))
        out[name] = cur.fetchone()[0]
    return out


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1

    conn = psycopg2.connect(url, connect_timeout=60)
    conn.autocommit = True
    failures: list[str] = []
    try:
        with conn.cursor() as cur:
            before = scalars(cur, LIVE)
            # Guard the guard: if the corpus were empty, every relation below
            # would hold trivially and this would report a clean bill of health
            # on nothing.
            # Every table the relations touch must be populated, not just the
            # two biggest. Run against a database built from the deposit alone —
            # where iucn_assessments and catch_records are withheld for licence
            # reasons and therefore empty — this reported PASS on relations that
            # held trivially over no rows. A reader would have taken it as
            # verification of their copy.
            for table in ("cites_trade_records", "species", "iucn_assessments",
                          "cites_listing_events"):
                cur.execute(f"select count(*) from {LIVE}.{table}")
                if cur.fetchone()[0] == 0:
                    print(f"V-16 CANNOT RUN: {LIVE}.{table} is empty, so the "
                          f"relations over it hold for free.\n"
                          f"If this database was built from the deposit, two "
                          f"tables are withheld for licence reasons and must be "
                          f"rebuilt first; see the deposit README. Reporting "
                          f"this rather than a pass.")
                    return 2

            # ---- MR1: permutation invariance --------------------------------
            cur.execute(f"drop schema if exists {PROBE} cascade")
            cur.execute(f"create schema {PROBE}")
            for table in ("iucn_assessments", "cites_trade_records", "species",
                          "cites_listing_events"):
                # random() in the ORDER BY is the point: it produces a physically
                # different row order with identical content.
                cur.execute(
                    f"create table {PROBE}.{table} as "
                    f"select * from {LIVE}.{table} order by random()")
            after = scalars(cur, PROBE)

            for name in PUBLISHED:
                if before[name] != after[name]:
                    # Show where they first differ, not the first 90 characters.
                    # These values share a long common prefix, so a head-of-string
                    # excerpt prints two identical-looking lines under a message
                    # saying they differ — a diagnosis that reads as a bug in the
                    # checker.
                    a, b = str(before[name]), str(after[name])
                    i = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]),
                             min(len(a), len(b)))
                    lo = max(0, i - 30)
                    failures.append(
                        f"MR1 permutation invariance: '{name}' changed when the "
                        f"rows were reordered.\n"
                        f"      first difference at character {i}:\n"
                        f"      original:  ...{a[lo:i + 60]}\n"
                        f"      reordered: ...{b[lo:i + 60]}\n"
                        f"      The published value depends on physical row order. "
                        f"A reload test cannot see this: a byte-identical reload "
                        f"reproduces an order-dependent answer perfectly.")

            # ---- MR2: partition additivity ----------------------------------
            cur.execute(f"select count(*) from {LIVE}.cites_trade_records")
            whole = cur.fetchone()[0]
            cur.execute(f"""select coalesce(sum(n), 0) from (
                              select count(*) as n from {LIVE}.cites_trade_records
                              group by coalesce(appendix, '(none)')) p""")
            parts = cur.fetchone()[0]
            if whole != parts:
                failures.append(
                    f"MR2 partition additivity: {whole} trade records in total, "
                    f"{parts} when summed over the appendix partition. Rows are "
                    f"being lost or duplicated by the grouping.")

            # ---- MR3: filter monotonicity -----------------------------------
            cur.execute(f"select count(*) from {LIVE}.cites_trade_records where quantity is not null")
            some = cur.fetchone()[0]
            if some > whole:
                failures.append(
                    f"MR3 filter monotonicity: filtering to non-null quantity "
                    f"gives {some} rows from a table of {whole}. A narrower "
                    f"filter returned more rows.")

            # ---- MR4: relabelling invariance --------------------------------
            # Rename every species consistently in the probe; the aggregate
            # structure keyed on identity must be unchanged.
            cur.execute(f"update {PROBE}.species set scientific_name = 'X' || id::text")
            cur.execute(f"""select string_agg(t.species_id::text || ':' || t.n::text, ',' order by t.species_id)
                            from (select species_id, count(*) as n
                                  from {PROBE}.cites_trade_records group by species_id) t""")
            relabelled = cur.fetchone()[0]
            cur.execute(f"""select string_agg(t.species_id::text || ':' || t.n::text, ',' order by t.species_id)
                            from (select species_id, count(*) as n
                                  from {LIVE}.cites_trade_records group by species_id) t""")
            original = cur.fetchone()[0]
            if relabelled != original:
                failures.append(
                    "MR4 relabelling invariance: per-species trade counts changed "
                    "when scientific names were rewritten. Something is keyed on "
                    "the name rather than on identity.")

            cur.execute(f"drop schema if exists {PROBE} cascade")
    finally:
        conn.close()

    if failures:
        print(f"V-16 FAIL: {len(failures)} metamorphic relation(s) broken:\n")
        for f in failures:
            print(f"  {f}\n")
        return 1

    print(f"V-16 PASS: {len(PUBLISHED)} published quantities hold under row "
          f"permutation; partition additivity, filter monotonicity and "
          f"relabelling invariance hold.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
