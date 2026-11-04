#!/usr/bin/env python3
"""V-14: every deposited table must load back into the deposited schema.

WHY THIS EXISTS
---------------
The deposit is the version of record. The only thing a reader does with it is
load it and check something, and until 2026-08-12 nobody had ever tried.

Trying it found that two of the twenty-two CSVs would not load at all. The
exporter had read rows into Python and written them with csv.writer, so a
PostgreSQL text[] arrived as a Python list and went to disk as its repr —
['CITES', 'Appendix II'] where the column wants {CITES,"Appendix II"}. The files
were well-formed CSV, every digest matched, every other check passed. The defect
was visible only on the round trip.

So the round trip is now a gate. It builds a throwaway schema from the deposit's
own schema.sql, loads every deposited CSV into it, compares the row counts
against the manifest, and drops it again.

It deliberately uses the deposit's copy of schema.sql rather than the
repository's. A reader has the deposit; if those two ever diverge, the reader's
experience is what matters and this should fail.

Usage:
  ARCTIC_DATABASE_URL=... .venv/bin/python ingest/verify_deposit_roundtrip.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).parent.parent
# Run from the repository, the deposit is ROOT/deposit. Shipped inside the
# deposit, this file sits in deposit/verification/, so ROOT is already the
# deposit and ROOT/deposit does not exist. It said "the deposit has no
# schema.sql" to the one reader it was shipped for.
DEPOSIT = ROOT / "deposit" if (ROOT / "deposit").is_dir() else ROOT
LIVE = "arctic_v2"
PROBE = "arctic_deposit_probe"

# Load parents before children. Foreign keys are disabled during the load, but
# order still matters for readability of any failure, and relying on the
# disable alone would hide a genuinely broken reference.
ORDER = [
    "species", "countries", "common_names", "cites_listings", "split_listings",
    "subpopulations", "management_areas", "glossary_terms",
    "illegal_trade_products", "timeline_events", "cms_listings",
    "species_narratives", "conservation_profiles", "references",
    "profile_references", "species_media", "illegal_trade_seizures",
    "cites_trade_records", "cites_listing_events", "source_releases",
    "narrative_review", "profile_review",
]


def main() -> int:
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        print("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)",
              file=sys.stderr)
        return 1

    schema_file = DEPOSIT / "schema.sql"
    manifest_file = DEPOSIT / "MANIFEST.sha256.json"
    tables_dir = DEPOSIT / "tables"
    for f in (schema_file, manifest_file, tables_dir):
        if not f.exists():
            print(f"V-14 FAIL: the deposit has no {f.name}. Use a complete copy of the deposit.")
            return 1

    manifest = json.loads(manifest_file.read_text())
    csvs = sorted(tables_dir.glob("*.csv"))
    if not csvs:
        # Silence must not pass: an empty tables/ would otherwise load nothing,
        # compare nothing, and report success.
        print("V-14 FAIL: the deposit contains no table CSVs at all.")
        return 1

    sql = schema_file.read_text()
    if sql.count(LIVE) < 10:
        print(f"V-14 FAIL: the deposited schema.sql barely mentions {LIVE}; "
              f"rewriting it would build an empty probe that passes for free.")
        return 1
    probe_sql = re.sub(rf"\b{LIVE}\b", PROBE, sql)

    conn = psycopg2.connect(url, connect_timeout=60)
    conn.autocommit = True
    failures: list[str] = []
    loaded: list[tuple[str, int]] = []
    try:
        with conn.cursor() as cur:
            cur.execute(f"drop schema if exists {PROBE} cascade")
            try:
                cur.execute(probe_sql)
            except Exception as exc:  # noqa: BLE001
                print(f"V-14 FAIL: the deposited schema.sql does not apply.\n  {exc}")
                return 1

            names = {c.stem for c in csvs}
            seq = [n for n in ORDER if n in names] + sorted(names - set(ORDER))

            # Foreign keys are deferred rather than dropped: the deposit omits
            # two tables for licence reasons, so rows in other tables legitimately
            # reference records that are not present. That is a documented state,
            # not a broken export.
            cur.execute("set session_replication_role = replica")
            for name in seq:
                path = tables_dir / f"{name}.csv"
                try:
                    with open(path) as fh:
                        header = fh.readline().strip()
                        fh.seek(0)
                        cur.copy_expert(
                            f"copy {PROBE}.{name} ({header}) from stdin with csv header", fh)
                    cur.execute(f"select count(*) from {PROBE}.{name}")
                    loaded.append((name, cur.fetchone()[0]))
                except Exception as exc:  # noqa: BLE001
                    failures.append(f"{name}.csv will not load: {str(exc).splitlines()[0]}")
            cur.execute("set session_replication_role = origin")

            for name, rows in loaded:
                entry = manifest.get(f"tables/{name}.csv")
                if entry is None:
                    failures.append(f"{name}.csv is in tables/ but not in the manifest")
                elif entry.get("rows") is not None and entry["rows"] != rows:
                    failures.append(
                        f"{name}: manifest says {entry['rows']} rows, "
                        f"{rows} loaded")

            for key in manifest:
                if key.startswith("tables/") and not (DEPOSIT / key).exists():
                    failures.append(f"{key} is in the manifest but not in the deposit")

        with conn.cursor() as cur:
            cur.execute(f"drop schema if exists {PROBE} cascade")
    finally:
        conn.close()

    if failures:
        print(f"V-14 FAIL: the deposit does not round-trip ({len(failures)} problem(s)):")
        for f in failures[:20]:
            print(f"  {f}")
        return 1

    print(f"V-14 PASS: all {len(loaded)} deposited tables load back into the "
          f"deposited schema, {sum(r for _, r in loaded)} rows, row counts "
          f"matching the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
