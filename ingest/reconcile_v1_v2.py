#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Reconcile the rebuilt schema against the frozen v1 baseline, table by table.

This is ISC V-6, and it is a paper deliverable rather than an engineering
convenience: it is the artifact that answers R1 on reproducibility. Every
difference between what was live and what the rebuild produces has to be
explained here, or the rebuild is not defensible.

The rule is simple and deliberately strict: a delta with no recorded explanation
is a FAILURE, not a footnote. Explanations live in EXPLAINED below, keyed by
table, and each one names the mechanism that produced the difference.

Read-only against both schemas.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/reconcile_v1_v2.py \
      [--v1 arctic_v1_frozen] [--v2 arctic_v2] [--json OUT.json]
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import psycopg2

# Every expected delta, with the mechanism that caused it. A table whose counts
# differ and which is absent here fails the reconciliation.
EXPLAINED = {
    "cites_trade_records": (
        "+18,990: v1 was built from a frozen 'optimized' intermediate that predates "
        "CITES v2025.1 and dropped every permit column. v2 loads the raw v2025.1 "
        "download (export permits 91.5%, import 19.9%, origin 14.5%). Three rows are "
        "excluded as reporting artifacts exceeding numeric(10,2), logged individually "
        "in ingest/reports/cites_dropped_rows.json. v2 also has zero NULL record_id "
        "against v1's 12,060."
    ),
    "illegal_trade_seizures": (
        "-517: v1 held 742 rows of which 694 fail species attribution (congeneric, "
        "genus-only, or family/keyword matches bound to the wrong binomial). v2 keeps "
        "the 225 that pass the deterministic identity gate. Per-species breakdown in "
        "ingest/reports/illegal_trade_decontamination.json."
    ),
    "cites_listings": (
        "-12: byte-identical duplicates of real listings, clustered on five species "
        "(Cetorhinus maximus held one Appendix II listing six times). v1 had no unique "
        "constraint. Each collapse is recorded per row in provenance_note."
    ),
    "timeline_events": (
        "-11: duplicates inherited from the duplicated cites_listings rows, not an "
        "independent defect. Deduplicating the listings at source removed them here."
    ),
    "management_areas": (
        "-6: rows with a NULL country that duplicated properly attributed areas. Each "
        "was verified to have zero referencing catch records before removal; all 958 "
        "catch records point at the 32 retained areas."
    ),
    "cms_listings": (
        "+61: v1 kept only agreement='CMS' and additionally missed two species listed "
        "under a higher taxon (Branta hutchinsii under 'Anatidae spp.', Grus canadensis "
        "under 'Grus spp.'). v2 derives all 11 CMS-family instruments from the source "
        "export and splits 'listed in both appendices' entries into one row each. "
        "Filter agreement='CMS' to reproduce the v1 scope."
    ),
    "species": (
        "0 rows, but the eight narrative prose columns moved out to species_narratives "
        "under the GATED class. The spine now holds only traceable facts."
    ),
}

# Tables that exist only in v2. Not deltas: new structure.
V2_ONLY = {
    "source_releases": (
        "which upstream release each part of the corpus was built from, added "
        "2026-08-11. v1 had no equivalent and could not answer Reviewer 3's "
        "'what was downloaded, and when': the CITES release survived only in a "
        "download directory name and the date only in shard modification times. "
        "Two rows, curator-asserted, never reloaded — obtained_on_basis records "
        "how each date is known, because an inferred date and a published one "
        "are not claims of equal strength."
    ),
    "species_narratives": "machine-written prose lifted out of the spine, GATED",
    "narrative_review": "human sign-off records; empty until a reviewer signs",
    "profile_review": "human sign-off records for conservation profiles; empty until signed",
    "cites_listing_events": (
        "corrected CITES event history from Species+, added 2026-08-11. v1 had "
        "no equivalent: its cites_listings held 59 rows for the 40 species that "
        "resolve, against 99 real listing events, and stored Party reservations "
        "as listings. This table supersedes it for analysis; cites_listings is "
        "retained so the reconciliation baseline still holds."
    ),
    "species_media": (
        "one photograph per species resolved from iNaturalist, added 2026-08-10. "
        "v1 held no media table: it called the iNaturalist API while rendering a page "
        "and stored nothing, which is why an outage broke live pages and why no "
        "licence was ever checked. 43 rows, one per species, of which 31 are "
        "displayable and 12 record why they are not. Enters no manuscript number."
    ),
}

# Tables that legitimately carry no source hash, and why.
#
# These hold relationships and human decisions rather than sourced content. A
# review row's provenance IS its named reviewer, verdict, rationale and
# timestamp; a binding's provenance is the two foreign keys it carries. Demanding
# a source_sha256 on them would be a box-ticking exercise that records nothing
# real, and would dilute the meaning of the column everywhere else.
#
# This exemption is deliberately narrow: it covers only join and sign-off tables,
# never anything that stores content.
NO_SOURCE_HASH = {
    "narrative_review": "human sign-off; provenance is the reviewer, verdict and timestamp",
    "profile_review": "human sign-off; provenance is the reviewer, verdict and timestamp",
    "profile_references": "join table; provenance is the two foreign keys plus binding_status",
    # source_releases records where each upstream source came from and how its
    # date is known. A provenance_class on it would be provenance about
    # provenance; the obtained_on_basis column already carries that, per row and
    # in words. Named here so the report shows a reason rather than a blank,
    # which is what it showed until 2026-08-12 — and a blank in a coverage report
    # reads as an oversight even when it is a decision.
    "source_releases": "provenance metadata itself; obtained_on_basis states, per "
                       "row, how the date is known",
}


def audit(cur, v1: str, v2: str) -> dict:
    cur.execute(
        """select table_name from information_schema.tables
           where table_schema = %s and table_type = 'BASE TABLE' order by table_name""",
        (v1,),
    )
    v1_tables = [r[0] for r in cur.fetchall()]
    cur.execute(
        """select table_name from information_schema.tables
           where table_schema = %s and table_type = 'BASE TABLE' order by table_name""",
        (v2,),
    )
    v2_tables = [r[0] for r in cur.fetchall()]

    rows = []
    for table in sorted(set(v1_tables) | set(v2_tables)):
        n1 = n2 = None
        if table in v1_tables:
            cur.execute(f'select count(*) from "{v1}"."{table}"')
            n1 = cur.fetchone()[0]
        if table in v2_tables:
            cur.execute(f'select count(*) from "{v2}"."{table}"')
            n2 = cur.fetchone()[0]
        delta = None if n1 is None or n2 is None else n2 - n1
        rows.append({
            "table": table, "v1": n1, "v2": n2, "delta": delta,
            "explanation": EXPLAINED.get(table) or V2_ONLY.get(table),
            "v2_only": table in V2_ONLY,
        })
    return {"tables": rows, "v1_schema": v1, "v2_schema": v2}


def provenance_check(cur, v2: str) -> dict:
    """Every row in every v2 table must carry a provenance class and source hash."""
    cur.execute(
        """select table_name from information_schema.tables
           where table_schema = %s and table_type = 'BASE TABLE' order by table_name""",
        (v2,),
    )
    out = {}
    for (table,) in [(r[0],) for r in cur.fetchall()]:
        cur.execute(
            """select count(*) from information_schema.columns
               where table_schema = %s and table_name = %s and column_name = 'provenance_class'""",
            (v2, table),
        )
        if not cur.fetchone()[0]:
            out[table] = (
                f"exempt: {NO_SOURCE_HASH[table]}" if table in NO_SOURCE_HASH
                else "no provenance_class column"
            )
            continue
        cur.execute(f'''select count(*) from "{v2}"."{table}"
                        where provenance_class is null or source_sha256 is null''')
        missing = cur.fetchone()[0]
        cur.execute(f'select provenance_class, count(*) from "{v2}"."{table}" group by 1')
        classes = dict(cur.fetchall())
        out[table] = {"rows_missing_provenance": missing, "classes": classes}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--v1", default="arctic_v1_frozen")
    ap.add_argument("--v2", default="arctic_v2")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")
    conn = psycopg2.connect(url, connect_timeout=20)
    conn.set_session(readonly=True)
    cur = conn.cursor()

    report = audit(cur, args.v1, args.v2)
    report["provenance"] = provenance_check(cur, args.v2)
    report["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print(f"{'table':28}{'v1':>9}{'v2':>9}{'delta':>9}  status")
    unexplained = []
    for row in report["tables"]:
        v1 = "-" if row["v1"] is None else f"{row['v1']:,}"
        v2 = "-" if row["v2"] is None else f"{row['v2']:,}"
        delta = "" if row["delta"] is None else f"{row['delta']:+,}"
        if row["v2_only"]:
            status = "NEW in v2"
        elif row["delta"] == 0:
            status = "exact"
        elif row["explanation"]:
            status = "explained"
        else:
            status = "UNEXPLAINED"
            unexplained.append(row["table"])
        print(f"{row['table']:28}{v1:>9}{v2:>9}{delta:>9}  {status}")

    print("\nprovenance coverage:")
    gaps = []
    for table, info in sorted(report["provenance"].items()):
        if isinstance(info, str):
            if info.startswith("exempt:"):
                print(f"  {table:28} {info}")
                continue
            gaps.append(table)
            print(f"  {table:28} {info}")
        elif info["rows_missing_provenance"]:
            gaps.append(table)
            print(f"  {table:28} {info['rows_missing_provenance']} rows missing provenance")
    if not gaps:
        print("  every table carries provenance_class and source_sha256 on every row")

    print("\nexplanations:")
    for row in report["tables"]:
        if row["explanation"] and row["delta"] not in (0, None):
            print(f"\n  {row['table']} ({row['delta']:+,})")
            for line in row["explanation"].split(". "):
                if line.strip():
                    print(f"    {line.strip().rstrip('.')}.")

    report["unexplained"] = unexplained
    report["provenance_gaps"] = gaps
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True, default=str)
        print(f"\nwrote {args.json_out}")

    conn.close()
    if unexplained:
        print(f"\nRECONCILIATION FAILED: {len(unexplained)} unexplained deltas: {unexplained}")
        return 1
    print("\nRECONCILIATION PASSED: every delta is explained and every row carries provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
