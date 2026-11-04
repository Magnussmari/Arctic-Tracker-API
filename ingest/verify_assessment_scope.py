#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""V-20: a status must be possible under the scope it was assessed at.

WHY THIS EXISTS
---------------
An earlier pass established that 17 of 43 species carry a Europe-scope IUCN
assessment as their latest, checked whether that changed the headline, and found
the aggregate identical either way. That analysis rested on one assumption which
was never tested: that an assessment with no recorded scope is a global one.

In the corpus, one species' assessment history alternates between a
regional-only outcome and modern global categories: a 1996 pre-2001 category,
then a regional-only outcome in 2007, global categories in 2008 and 2018, and
the regional-only outcome again in 2023. Read as one global series, that is
impossible. The 2023 row carries scope_code '2' (Europe), so it describes the
European population and says nothing about the species' global category.

The 2007 row carries NO scope at all, and that outcome is not a status the
global Red List issues. So at least one of the 349 scope-null assessments is regional, and "null
means global" is false. The 17-species count is a floor, not a total.

WHAT IT ASSERTS
---------------
Two things, both cheap and both able to fail:

  1. No assessment carries a status that its recorded scope cannot produce. RE
     and RG are regional-only statuses; under a global or absent scope they are
     evidence the scope is wrong rather than evidence the species is extinct.

  2. No species' latest assessment is regional while the manuscript speaks about
     it globally, without that being declared. This is the known 17 and is
     reported as a count so it cannot drift silently.

WHAT IT DOES NOT ESTABLISH
--------------------------
That the remaining scope-null assessments are global. Only the ones carrying a
regional-only status are provable from inside the corpus; the rest would need the
Red List API to settle, and that is recorded as a deficit rather than assumed
away in either direction.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/verify_assessment_scope.py
"""
from __future__ import annotations

import os
import sys

import psycopg2

SCHEMA = os.environ.get("ARCTIC_SCHEMA", "arctic_v2")

# Statuses the global Red List does not issue. RE (Regionally Extinct) and RG
# (Regionally Extinct in the Wild) exist only in regional assessments, by the
# definition of the regional guidelines.
#
# NA (Not Applicable) added 2026-10-07. It too exists only under the regional
# guidelines, for a taxon not eligible for assessment at that level, and four
# 2007 rows read as global carry it. With RE alone the gate saw one of the five.
REGIONAL_ONLY = ("RE", "RG", "NA")

# Assessments shown, one by one, to be regional although the corpus records no
# scope. The file carries the evidence for each. The gate reports which of
# them the corpus still reads as global: the right whale's 2007 assessment
# among them moves a published trajectory.
CORRECTIONS = os.path.join(os.path.dirname(__file__), "..", "species_data",
                           "curated", "iucn_scope_corrections.csv")

# Scope codes meaning "global". IUCN uses 1 for Global; the corpus also records
# it as null, which is the ambiguity this gate exists to expose.
GLOBAL_SCOPES = ("1", None)


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1

    conn = psycopg2.connect(url, connect_timeout=60)
    try:
        with conn.cursor() as cur:
            cur.execute(f"select count(*) from {SCHEMA}.iucn_assessments")
            total = cur.fetchone()[0]
            if total == 0:
                # Silence must not pass. An empty table satisfies every
                # assertion below for free.
                print(f"V-20 CANNOT RUN: {SCHEMA}.iucn_assessments is empty, so "
                      f"every statement about scope holds vacuously.")
                return 2

            cur.execute(f"""
                select s.common_name, a.year_published, a.status,
                       a.scope_code, a.is_latest
                  from {SCHEMA}.iucn_assessments a
                  join {SCHEMA}.species s on s.id = a.species_id
                 where a.status = any(%s)
                 order by s.common_name, a.year_published""", (list(REGIONAL_ONLY),))
            regional_status = cur.fetchall()

            cur.execute(f"""
                select count(*) from {SCHEMA}.iucn_assessments
                 where is_latest and scope_code is not null and scope_code <> '1'""")
            regional_latest = cur.fetchone()[0]

            cur.execute(f"select count(*) from {SCHEMA}.iucn_assessments "
                        f"where scope_code is null")
            scope_null = cur.fetchone()[0]

            import csv
            with open(CORRECTIONS, newline="", encoding="utf-8") as f:
                confirmed = {int(r["assessment_id"]): r for r in csv.DictReader(f)}
            cur.execute(f"""
                select a.assessment_id from {SCHEMA}.iucn_assessments a
                 where a.assessment_id = any(%s)
                   and coalesce(a.scope_code, '1') = '1'""", (list(confirmed),))
            still_global = [confirmed[r[0]] for r in cur.fetchall()]
    finally:
        conn.close()

    mislabelled = [r for r in regional_status if r[3] in GLOBAL_SCOPES]

    print(f"V-20 assessment scope: {total} assessments, {scope_null} with no "
          f"recorded scope, {regional_latest} regional assessments used as latest\n")

    if regional_status:
        print(f"  regional-only statuses present ({len(regional_status)}):")
        for name, year, status, scope, latest in regional_status:
            tag = "LATEST" if latest else "      "
            print(f"    {tag}  {name:28s} {year}  {status}  "
                  f"scope={scope if scope is not None else 'NONE'}")
        print()

    if still_global:
        print(f"  confirmed regional, still read as global ({len(still_global)}), "
              f"from species_data/curated/iucn_scope_corrections.csv:")
        for r in still_global:
            print(f"    {r['scientific_name']:28s} {r['year_published']}  {r['status']}  "
                  f"assessment {r['assessment_id']}")
        print()

    if mislabelled or still_global:
        print(f"V-20 FAIL: {len(mislabelled)} assessment(s) carry a regional-only "
              f"status under a global or absent scope, and {len(still_global)} "
              f"confirmed regional assessment(s) are still read as global.")
        print("  A global Red List assessment does not return RE or NA. Either the scope")
        print("  is missing and the row is regional, or the status is wrong. Until")
        print("  it is resolved, 'scope is null' cannot be read as 'global', and")
        print("  any count that treats it that way is unproven.")
        return 1

    print(f"V-20 PASS: every regional-only status carries a regional scope.")
    print(f"  {regional_latest} species are represented by a regional assessment as")
    print(f"  their latest. That is declared, not a defect, but it is the number")
    print(f"  that must not drift without the manuscript saying so.")
    print(f"  DEFICIT: {scope_null} assessments record no scope. Those carrying a")
    print(f"  regional-only status are provably regional; the rest cannot be")
    print(f"  settled from inside the corpus and are not assumed to be global.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
