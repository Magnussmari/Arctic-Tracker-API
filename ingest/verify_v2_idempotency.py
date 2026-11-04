#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Content-hash every v2 table so idempotency can be proven, not assumed (ISC V-4).

WHY A NAIVE HASH DOES NOT WORK HERE
-----------------------------------
Every v2 table uses `gen_random_uuid()` for its primary key, and carries a
`loaded_at` timestamp. Both change on every load by design. A hash over whole
rows would therefore differ after a re-run even when the data is bit-identical,
which would make an idempotency check that always fails, and an always-failing
check gets ignored.

Worse, foreign keys are uuids too, so a child row's `species_id` changes
whenever the parent is reloaded. Hashing the raw fk would report a difference
that is purely an artifact of surrogate keys.

WHAT THIS HASHES INSTEAD
------------------------
Business content only, with foreign keys resolved to the natural key they stand
for:

  - surrogate ids, timestamps and loader_version are excluded
  - species_id     -> species.scientific_name
  - country_id     -> countries.country_code
  - profile_id     -> the profile's (species, profile_key)
  - reference_id   -> the reference's doi or title

Rows are then serialised canonically and sorted, so row order cannot affect the
result. Two loads of the same source must produce the same digest; if they do
not, something non-deterministic is in the pipeline and idempotency is a claim
rather than a fact.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/verify_v2_idempotency.py --snapshot before.json
  ...re-run the loaders...
  ARCTIC_DATABASE_URL=... python ingest/verify_v2_idempotency.py --compare before.json
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import psycopg2

# Never part of business content: surrogate keys and load metadata.
EXCLUDED = {"id", "loaded_at", "created_at", "updated_at", "loader_version"}

# Tables outside the determinism test, and why.
#
# species_media is resolved from the iNaturalist API. The remote source is
# mutable: a curator can change a taxon's default photograph between two runs,
# which would fail this gate for a reason that says nothing about our loaders.
# It is truncated with the rest so the teardown can proceed, and reloaded by
# ingest/inaturalist_media_load.py afterwards as a documented post-step.
EXCLUDED_TABLES = {"species_media"}

# Foreign keys resolved to a stable natural key, so a reload that renumbers
# uuids does not read as a data change.
FK_RESOLUTION = {
    "species_id": ("species", "scientific_name"),
    "country_id": ("countries", "country_code"),
    "reference_id": ("references", "coalesce(doi, title)"),
    "profile_id": ("conservation_profiles", "profile_key"),
    "narrative_id": ("species_narratives", "section"),
    "management_area_id": ("management_areas", "area_name"),
    "product_type_id": ("illegal_trade_products", "product_code"),
}


def business_columns(cur, schema: str, table: str) -> list[str]:
    cur.execute(
        """select column_name from information_schema.columns
           where table_schema = %s and table_name = %s order by ordinal_position""",
        (schema, table),
    )
    return [c for (c,) in cur.fetchall() if c not in EXCLUDED]


def build_select(cur, schema: str, table: str, columns: list[str]) -> str:
    """Project business columns, replacing each fk with its natural key."""
    parts = []
    joins = []
    for i, col in enumerate(columns):
        target = FK_RESOLUTION.get(col)
        if target:
            parent, natural = target
            alias = f"fk{i}"
            joins.append(
                f'left join "{schema}"."{parent}" {alias} on {alias}.id = t."{col}"'
            )
            expr = natural if "(" in natural else f'{alias}."{natural}"'
            if "(" in natural:
                # coalesce(doi, title) needs the alias applied to each column
                expr = natural.replace("doi", f'{alias}."doi"').replace("title", f'{alias}."title"')
            parts.append(f"coalesce({expr}::text, '')")
        else:
            parts.append(f'coalesce(t."{col}"::text, \'\')')
    projection = " || '|' || ".join(parts) if parts else "''"
    return f'select {projection} as row_text from "{schema}"."{table}" t ' + " ".join(joins)


def hash_table(cur, schema: str, table: str) -> dict:
    columns = business_columns(cur, schema, table)
    if not columns:
        return {"rows": 0, "sha256": None, "columns": []}
    cur.execute(build_select(cur, schema, table, columns))
    rows = [r[0] for r in cur.fetchall()]
    # Sorting makes the digest independent of physical row order, which changes
    # freely between loads.
    rows.sort()
    digest = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    return {"rows": len(rows), "sha256": digest, "columns": columns}


def snapshot(cur, schema: str) -> dict:
    cur.execute(
        """select table_name from information_schema.tables
           where table_schema = %s and table_type = 'BASE TABLE' order by table_name""",
        (schema,),
    )
    tables = [t for (t,) in cur.fetchall() if t not in EXCLUDED_TABLES]
    return {
        "schema": schema,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tables": {t: hash_table(cur, schema, t) for t in tables},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", default="arctic_v2")
    ap.add_argument("--snapshot", help="write a content-hash snapshot to this path")
    ap.add_argument("--compare", help="compare current state against this snapshot")
    args = ap.parse_args()

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")
    conn = psycopg2.connect(url, connect_timeout=30)
    conn.set_session(readonly=True)
    cur = conn.cursor()

    current = snapshot(cur, args.schema)
    conn.close()

    if args.snapshot:
        with open(args.snapshot, "w") as fh:
            json.dump(current, fh, indent=1, sort_keys=True)
        print(f"wrote {args.snapshot}")

    print(f"{'table':28}{'rows':>9}  content sha256")
    for table, info in sorted(current["tables"].items()):
        digest = (info["sha256"] or "")[:16]
        print(f"{table:28}{info['rows']:>9}  {digest}")

    if not args.compare:
        return 0

    with open(args.compare) as fh:
        before = json.load(fh)

    print(f"\nidempotency check against {args.compare}:")
    drift = []
    for table, info in sorted(current["tables"].items()):
        prior = before["tables"].get(table)
        if prior is None:
            print(f"  {table:28} NEW since snapshot")
            drift.append(table)
            continue
        if prior["sha256"] != info["sha256"]:
            print(f"  {table:28} CHANGED  rows {prior['rows']} -> {info['rows']}")
            drift.append(table)
    for table in before["tables"]:
        if table not in current["tables"]:
            print(f"  {table:28} DISAPPEARED since snapshot")
            drift.append(table)

    if drift:
        print(f"\nV-4 FAILED: {len(drift)} tables changed across identical loads: {drift}")
        print("Something in the pipeline is non-deterministic.")
        return 1
    print(f"\nV-4 PASSED: all {len(current['tables'])} tables byte-identical across reloads.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
