#!/usr/bin/env python3
"""Prove the loaders did not alter data in transit (ISC V-5).

WHAT THIS CATCHES THAT NOTHING ELSE DOES
-----------------------------------------
The idempotency check proves a reload produces the same database twice. It
cannot prove the database matches the source file, because both runs go through
the same loader: a loader that consistently corrupts a column passes idempotency
perfectly.

The reconciliation compares the rebuild against the old database, which is the
thing being replaced and therefore not an authority.

This check derives the expected content from the SOURCE FILE, in Python, without
touching the loader, then compares against what the database actually holds. A
loader that lowercased a name, dropped a column, coerced a null to zero or
reordered two fields fails here and passes everywhere else.

Both sides are serialized with the same canonical rules so that a difference in
representation cannot masquerade as a difference in content:

  - values are compared as text, stripped, with empty string and NULL unified
  - numeric values are normalized so 1.50 and 1.5 compare equal
  - rows are sorted by full content, so physical order cannot matter

Usage:
  ARCTIC_DATABASE_URL=... python ingest/verify_source_truth.py [--schema arctic_v2]
"""
import argparse
import csv
import hashlib
import os
import pathlib
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg2

ROOT = Path(__file__).parent.parent
# From the repository the curated sources are under species_data/. Shipped in the
# deposit, this file sits in verification/ and they are under sources/curated/.
# Without the second path it printed "source file missing" and stopped.
_repo_curated = ROOT / "species_data/curated"
CURATED = _repo_curated if _repo_curated.is_dir() else ROOT / "sources" / "curated"
# Some sources are not curated CSVs. A spec may name its own directory; without
# this, source truth could only ever cover the curated tables, which is how the
# IUCN assessments came to have no independent derivation at all after the
# sprint-era verifier was superseded. That table carries the paper's central
# findings.
SOURCE_DIRS = {"iucn": ROOT / "species_data/iucn"}
if not SOURCE_DIRS["iucn"].is_dir():
    SOURCE_DIRS["iucn"] = ROOT / "sources" / "iucn"

# Each entry maps a curated source file to the table it loads, and states which
# source column feeds which database column. Only columns that come FROM the
# source are checked: generated ids, provenance stamps and load timestamps are
# properties of the load, not of the source, and are verified elsewhere.
#
# `key` is the natural key used to line source rows up against database rows.
SPECS = {
    "iucn_assessments": {
        "source": "iucn_assessments_snapshot_2026-07-22.csv",
        "dir": "iucn",
        "key": ["assessment_id"],
        # species_id is deliberately absent. The snapshot carries the surrogate
        # keys of the v1 schema; v2 generated its own and the loader maps them
        # through --lookup-schema. Comparing them would report 370 mismatches on
        # a difference that is the rebuild working as designed. What must match
        # is the assessment content, which is what IUCN published.
        "columns": {
            "assessment_id": "assessment_id",
            "year_published": "year_published",
            "status": "status",
            "scope_code": "scope_code",
            "is_latest": "is_latest",
        },
    },
    "species": {
        "source": "species_taxonomy.csv",
        "key": ["scientific_name"],
        "columns": {
            "scientific_name": "scientific_name",
            "common_name": "common_name",
            "kingdom": "kingdom",
            "phylum": "phylum",
            "class": "class",
            "order_name": "order_name",
            "family": "family",
            "genus": "genus",
            "species_name": "species_name",
            "authority": "authority",
            "sis_id": "sis_id",
        },
    },
    "countries": {
        "source": "countries.csv",
        "key": ["country_name"],
        "columns": {
            "country_name": "country_name",
            "country_code": "country_code",
            "nammco_member": "nammco_member",
            "arctic_council": "arctic_council",
        },
    },
    "glossary_terms": {
        "source": "glossary_terms.csv",
        "key": ["term"],
        "columns": {
            "term": "term",
            "acronym": "acronym",
            "definition": "definition",
            "category": "category",
            "subcategory": "subcategory",
            "priority": "priority",
        },
    },
    "illegal_trade_products": {
        "source": "illegal_trade_products.csv",
        "key": ["product_code"],
        "columns": {
            "product_code": "product_code",
            "product_name": "product_name",
            "product_category": "product_category",
            "main_category": "main_category",
            "is_high_value": "is_high_value",
        },
    },
    "subpopulations": {
        "source": "subpopulations.csv",
        # NOT the name alone: "Mediterranean subpopulation" exists for three
        # different species. A non-unique key silently collapses rows on both
        # sides and hides any difference between them. Found by this check
        # reporting 10 rows for a 12-row table.
        "key": ["scientific_name", "subpopulation_name"],
        "columns": {
            "scientific_name": None,
            "subpopulation_name": "subpopulation_name",
            "sis_id": "sis_id",
            "authority": "authority",
        },
    },
}


def canonical(value) -> str:
    """One representation per value, so formatting cannot look like corruption."""
    if value is None:
        return ""
    text = str(value).strip()
    if text == "":
        return ""
    lowered = text.lower()
    # Booleans arrive as True/False from psycopg2 and as 'True'/'true'/'t' from CSV.
    if lowered in {"true", "t", "yes"}:
        return "true"
    if lowered in {"false", "f", "no"}:
        return "false"
    # Numbers: 1.50 and 1.5 are the same value, and must not hash differently.
    try:
        number = Decimal(text)
        normalised = number.normalize()
        # Decimal.normalize() renders 10541390 as 1.054139E+7. Both sides go
        # through here so the comparison is still correct, but a mismatch report
        # showing 1.054139E+7 reads as spreadsheet damage to the source file,
        # and cost twenty minutes chasing exactly that. Integers stay integers.
        if normalised == normalised.to_integral_value():
            return str(normalised.quantize(Decimal(1)))
        return str(normalised)
    except (InvalidOperation, ValueError):
        return text


def row_digest(values) -> str:
    return hashlib.sha256("\x1f".join(canonical(v) for v in values).encode()).hexdigest()


def read_source_rows(spec: dict) -> dict:
    """Digest each source row, keyed by its natural key. No database involved.

    A column mapped to None is used for keying only and is not compared: the
    database may store a surrogate (species_id) where the source carries the
    natural value (scientific_name).
    """
    path = SOURCE_DIRS.get(spec.get("dir", ""), CURATED) / spec["source"]
    if not path.exists():
        # Missing is not always wrong. The IUCN snapshot cannot travel in the
        # deposit for licence reasons, so a reader running this from the package
        # legitimately has five of the six sources. Aborting told them nothing
        # about the five they could check; this reports the gap and continues.
        raise FileNotFoundError(path)
    order = [c for c, db in spec["columns"].items() if db is not None]
    out = {}
    rows = 0
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            rows += 1
            key = tuple(canonical(row.get(k)) for k in spec["key"])
            out[key] = row_digest([row.get(col) for col in order])
    # A key that collapses rows makes the whole comparison meaningless: both
    # sides lose the same rows and the check passes while proving nothing.
    if len(out) != rows:
        sys.exit(
            f"{spec['source']}: key {spec['key']} is not unique "
            f"({rows} rows collapse to {len(out)}). Widen the key."
        )
    return out


def read_db_rows(cur, schema: str, table: str, spec: dict) -> dict:
    compared = [c for c, db in spec["columns"].items() if db is not None]
    db_columns = [spec["columns"][c] for c in compared]
    # Key columns that have no database counterpart are resolved through the
    # species spine, which is how the natural key is recovered from a surrogate.
    joins, key_exprs = "", []
    for k in spec["key"]:
        mapped = spec["columns"].get(k)
        if mapped is None:
            joins = f' join "{schema}".species sp on sp.id = t.species_id'
            key_exprs.append(f"sp.{k}")
        else:
            key_exprs.append(f't."{mapped}"')
    select = ", ".join(key_exprs + [f't."{c}"' for c in db_columns])
    cur.execute(f'select {select} from "{schema}"."{table}" t{joins}')
    out = {}
    rows = 0
    for record in cur.fetchall():
        rows += 1
        key = tuple(canonical(v) for v in record[: len(spec["key"])])
        out[key] = row_digest(record[len(spec["key"]) :])
    if len(out) != rows:
        sys.exit(f"{table}: key {spec['key']} is not unique in the database "
                 f"({rows} rows collapse to {len(out)})")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--schema", default="arctic_v2")
    ap.add_argument("--table", help="verify a single table")
    args = ap.parse_args()

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")
    conn = psycopg2.connect(url, connect_timeout=30)
    conn.set_session(readonly=True)
    cur = conn.cursor()

    targets = {args.table: SPECS[args.table]} if args.table else SPECS
    failures = []
    print(f"{'table':26}{'source rows':>13}{'db rows':>10}{'mismatched':>12}  result")
    print("-" * 74)

    unavailable = []
    for table, spec in sorted(targets.items()):
        try:
            source = read_source_rows(spec)
        except FileNotFoundError as exc:
            unavailable.append((table, pathlib.Path(str(exc)).name))
            print(f"{table:26}{'source not present here':>36}  SKIPPED")
            continue
        database = read_db_rows(cur, args.schema, table, spec)

        missing = sorted(set(source) - set(database))
        extra = sorted(set(database) - set(source))
        differing = sorted(k for k in set(source) & set(database) if source[k] != database[k])

        bad = len(missing) + len(extra) + len(differing)
        status = "OK" if bad == 0 else "MISMATCH"
        print(f"{table:26}{len(source):>13}{len(database):>10}{bad:>12}  {status}")

        if bad:
            failures.append(table)
            for key in missing[:3]:
                print(f"    in source, absent from database: {key}")
            for key in extra[:3]:
                print(f"    in database, absent from source: {key}")
            for key in differing[:3]:
                print(f"    content differs: {key}")

    conn.close()
    if failures:
        print(f"\nV-5 FAILED on {len(failures)} table(s): {failures}")
        print("The database does not match what the source file says. That is a loader")
        print("defect, not a formatting difference: both sides use the same canonical form.")
        return 1
    print(f"\nV-5 PASSED: every checked table reproduces its source file exactly.")
    print("Derived independently of the loaders, so a loader that consistently")
    print("corrupted a column could not hide behind a passing idempotency check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
