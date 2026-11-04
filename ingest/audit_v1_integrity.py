#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-28
"""Reproducible integrity audit of a live Arctic schema (v1 baseline).

Produces the evidence for the audit of the v1 database. Read-only: the
session is opened read-only so this cannot mutate the audited database even if
a future edit introduces a write.

Three checks, each independently meaningful:

1. DUPLICATES  — exact-duplicate rows on the business key of each table. A
   duplicate here is user-visible (species pages render listings and timeline
   events directly), so this is a correctness check, not hygiene.
2. CONSTRAINTS — which tables lack UNIQUE constraints, i.e. where duplicates
   are structurally permitted rather than accidental. This is the root cause of
   check 1 and the thing the v2 rebuild must fix at the schema level.
3. COUNTS      — row counts per table, optionally diffed against a second
   schema (the from-source rebuild) to surface reproduction gaps.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/audit_v1_integrity.py [--schema arctic]
                                  [--compare arctic_sprint] [--json OUT.json]

Exit codes: 0 = audit ran (findings may still be non-empty); 2 = usage/connect
error. A non-empty finding set is NOT a failure exit — this is a reporting
tool, and the gating decision belongs to the caller (and ultimately to a human).
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

import psycopg2

# Business key per table: the tuple that must be unique for the row to mean one
# real-world fact. Deliberately excludes surrogate ids and created_at/updated_at
# (those differ per load and would mask genuine duplicates).
BUSINESS_KEYS = {
    "cites_listings": ["species_id", "appendix", "listing_date"],
    "timeline_events": ["species_id", "event_date", "event_type", "title", "description"],
    "common_names": ["species_id", "name", "language"],
    "countries": ["country_name"],
    "subpopulations": ["species_id", "subpopulation_name"],
    "illegal_trade_products": ["product_code"],
    "split_listings": ["species_id", "population_identifier", "appendix", "listing_date"],
    "cms_listings": ["species_id", "appendix", "listing_date"],
    "management_areas": ["area_name", "country_id", "area_type"],
    "glossary_terms": ["term"],
    "species": ["scientific_name"],
    "iucn_assessments": ["species_id", "assessment_id"],
    "catch_records": ["species_id", "year", "area", "data_source"],
    "illegal_trade_seizures": ["species_id", "source_database", "reported_taxon_name", "gbif_id"],
    "cites_trade_records": ["record_id"],
    "conservation_profiles": ["species_id"],
    "references": ["id"],
    "profile_references": ["profile_id", "reference_id"],
}


def _ident(name: str) -> str:
    """Reject anything that is not a plain identifier, then quote it.

    Schema and column names here come from argv and from the constant above,
    never from the database contents, but validating keeps the rule that no
    string reaches SQL unchecked.
    """
    if not name.replace("_", "").isalnum():
        sys.exit(f"invalid identifier: {name!r}")
    return f'"{name}"'


def connect(url: str):
    try:
        conn = psycopg2.connect(url, connect_timeout=15)
    except Exception as exc:  # noqa: BLE001 - surface the real driver message
        sys.exit(f"connect failed: {type(exc).__name__}: {exc}")
    conn.set_session(readonly=True)
    return conn


def base_tables(cur, schema: str) -> list[str]:
    cur.execute(
        """select table_name from information_schema.tables
           where table_schema = %s and table_type = 'BASE TABLE'
           order by table_name""",
        (schema,),
    )
    return [r[0] for r in cur.fetchall()]


def audit_duplicates(cur, schema: str, tables: list[str]) -> dict:
    """Count genuine duplicate rows on each table's business key.

    Two traps this deliberately avoids, both of which produced false positives
    on the first run of this audit against live `arctic` (2026-07-28):

    1. NULL KEY COLUMNS. `count(distinct (a,b))` ignores rows where the tuple
       contains NULL, so a column that is 100% NULL makes every row look like a
       duplicate. `catch_records.area` is NULL for all 958 live rows (the legacy
       loader never populated it), which reported 632 false duplicates. Rows
       whose key is wholly or partly NULL are counted and reported SEPARATELY as
       `null_key_rows` — an untraceable row is its own defect, not a duplicate.

    2. PARTIAL KEYS. A key narrower than the real-world fact reports legitimate
       distinct records as duplicates. `illegal_trade_seizures` showed 422
       "duplicates" on a four-column key and zero on the full business row.
       Every duplicate count is therefore corroborated against the FULL business
       row before being reported; the key-level count is retained as a weaker
       signal under `key_level_collisions`.
    """
    out = {}
    for table in tables:
        keys = BUSINESS_KEYS.get(table)
        if not keys:
            out[table] = {"skipped": "no business key declared"}
            continue
        qualified = _ident(schema) + "." + _ident(table)
        cols = ", ".join(_ident(k) for k in keys)
        not_null = " and ".join(f"{_ident(k)} is not null" for k in keys)
        try:
            cur.execute(f"select count(*) from {qualified}")
            total = cur.fetchone()[0]

            # Rows whose business key is not fully populated: untraceable, and
            # excluded from the duplicate maths rather than inflating it.
            cur.execute(f"select count(*) from {qualified} where not ({not_null})")
            null_key = cur.fetchone()[0]

            # Key-level collisions, computed only over fully-populated keys.
            cur.execute(
                f"select count(*) - count(distinct ({cols})) from {qualified} where {not_null}"
            )
            key_dups = cur.fetchone()[0]

            # Corroborate against the full business row (every non-surrogate,
            # non-timestamp column), which is what "duplicate fact" really means.
            cur.execute(
                """select column_name from information_schema.columns
                   where table_schema = %s and table_name = %s
                     and column_name not in ('id','created_at','updated_at')
                   order by ordinal_position""",
                (schema, table),
            )
            full_cols = [r[0] for r in cur.fetchall()]
            full_dups = None
            if full_cols:
                fc = ", ".join(_ident(c) for c in full_cols)
                cur.execute(f"select count(*) - count(distinct ({fc})) from {qualified}")
                full_dups = cur.fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            cur.connection.rollback()
            out[table] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
            continue

        entry = {
            "rows": total,
            "business_key": keys,
            "null_key_rows": null_key,
            "key_level_collisions": key_dups,
            # The reported figure: only what survives full-row corroboration.
            "duplicate_rows": full_dups if full_dups is not None else key_dups,
        }
        if entry["duplicate_rows"]:
            cur.execute(
                f"select count(*) c from {qualified} where {not_null} "
                f"group by {cols} having count(*) > 1 order by c desc limit 5"
            )
            entry["worst_group_sizes"] = [r[0] for r in cur.fetchall()]
        out[table] = entry
    return out


def audit_constraints(cur, schema: str) -> dict:
    """Per-table constraint census. Zero UNIQUE means duplicates are permitted."""
    cur.execute(
        """select t.relname,
                  count(*) filter (where c.contype = 'u') as uniques,
                  count(*) filter (where c.contype = 'f') as fkeys,
                  count(*) filter (where c.contype = 'p') as pkeys
           from pg_class t
           join pg_namespace n on n.oid = t.relnamespace
           left join pg_constraint c on c.conrelid = t.oid
           where n.nspname = %s and t.relkind = 'r'
           group by t.relname order by t.relname""",
        (schema,),
    )
    return {
        r[0]: {"unique": r[1], "foreign_keys": r[2], "primary_key": r[3]}
        for r in cur.fetchall()
    }


def audit_counts(cur, schema: str, tables: list[str]) -> dict:
    out = {}
    for table in tables:
        try:
            cur.execute(f"select count(*) from {_ident(schema)}.{_ident(table)}")
            out[table] = cur.fetchone()[0]
        except Exception:  # noqa: BLE001
            cur.connection.rollback()
            out[table] = None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", default="arctic", help="schema to audit (default: arctic)")
    ap.add_argument("--compare", help="second schema to diff row counts against (e.g. arctic_sprint)")
    ap.add_argument("--json", dest="json_out", help="write the full report to this path")
    args = ap.parse_args()

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    conn = connect(url)
    cur = conn.cursor()
    tables = base_tables(cur, args.schema)
    if not tables:
        sys.exit(f"no base tables found in schema {args.schema!r}")

    report = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schema": args.schema,
        "table_count": len(tables),
        "counts": audit_counts(cur, args.schema, tables),
        "duplicates": audit_duplicates(cur, args.schema, tables),
        "constraints": audit_constraints(cur, args.schema),
    }
    if args.compare:
        report["compare_schema"] = args.compare
        report["compare_counts"] = audit_counts(cur, args.compare, tables)

    dup_tables = {
        t: v["duplicate_rows"]
        for t, v in report["duplicates"].items()
        if isinstance(v.get("duplicate_rows"), int) and v["duplicate_rows"] > 0
    }
    null_key_tables = {
        t: v["null_key_rows"]
        for t, v in report["duplicates"].items()
        if isinstance(v.get("null_key_rows"), int) and v["null_key_rows"] > 0
    }
    no_unique = [t for t, v in report["constraints"].items() if v["unique"] == 0]
    report["summary"] = {
        "tables_with_duplicates": dup_tables,
        "total_duplicate_rows": sum(dup_tables.values()),
        "tables_with_untraceable_rows": null_key_tables,
        "total_untraceable_rows": sum(null_key_tables.values()),
        "tables_without_unique_constraint": no_unique,
    }

    print(f"schema {args.schema}: {len(tables)} base tables, "
          f"{sum(v for v in report['counts'].values() if v):,} rows")
    print(f"\nDUPLICATES, full-row corroborated "
          f"({sum(dup_tables.values())} rows across {len(dup_tables)} tables):")
    for t, n in sorted(dup_tables.items(), key=lambda kv: -kv[1]):
        d = report["duplicates"][t]
        note = ""
        if d["key_level_collisions"] != n:
            note = f"   (key-level collisions {d['key_level_collisions']} -> not corroborated)"
        print(f"  {t:28} {n:>5}  of {report['counts'][t]:>6} rows{note}")
    if not dup_tables:
        print("  none")

    print(f"\nUNTRACEABLE ROWS — business key not fully populated "
          f"({sum(null_key_tables.values())} rows):")
    for t, n in sorted(null_key_tables.items(), key=lambda kv: -kv[1]):
        d = report["duplicates"][t]
        print(f"  {t:28} {n:>6}  of {report['counts'][t]:>6} rows   key={'+'.join(d['business_key'])}")
    if not null_key_tables:
        print("  none")
    print(f"\nNO UNIQUE CONSTRAINT ({len(no_unique)} tables — duplicates structurally permitted):")
    for t in no_unique:
        c = report["constraints"][t]
        flag = "  <-- no FKs either" if c["foreign_keys"] == 0 else ""
        print(f"  {t}{flag}")

    if args.compare:
        print(f"\nCOUNT DIFF vs {args.compare}:")
        for t in tables:
            a = report["counts"].get(t)
            b = report["compare_counts"].get(t)
            if b is None or a == b:
                continue
            print(f"  {t:28} {args.schema}={a:<8} {args.compare}={b:<8} delta={b - a:+}")

    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
        print(f"\nwrote {args.json_out}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
