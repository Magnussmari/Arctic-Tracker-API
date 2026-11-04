#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Load NAMMCO catch records into a target schema, with v2 constraints.

This reuses the already-verified parsing in nammco_load.rows_from_csvs rather
than reimplementing it: that generator handles the NAMMCO sentinels, the
season/range year forms ('2004/2005' -> 2004), the scraper comment lines and the
unmapped-species log, and it reproduces the live row count exactly (958/958).
Only the lookup schema was parameterised so it can resolve against the rebuild.

WHAT V1 LOST
------------
Three separate losses, all in the same table, all silent:

1. ZERO CONFLATED WITH UNKNOWN. NAMMCO reports '*No reported catches' as an
   explicit zero. The legacy loader wrote NULL for those rows, so live holds 109
   NULL catch_total against the rebuild's 26. **83 explicit zero-catch reports
   became indistinguishable from missing data.** These are different scientific
   claims: a reported zero says the fishery was observed and took nothing; NULL
   says nobody knows. Any catch time-series that averages or interpolates over
   NULLs is affected by which of the two it is looking at.

2. AREA NEVER POPULATED. All 958 live rows have area NULL. The source carries it
   on every row, and the rebuild restores 958/958. Without it a catch record
   cannot be checked against the management area it belongs to.

3. QUOTA NEVER POPULATED. All 958 live rows have quota NULL. The source carries
   it on 486, and the rebuild restores those. The remaining 472 are genuinely
   absent in source ('n/a', 'no quota', 'none', '-' are documented unknowns and
   stay NULL rather than being coerced to zero, which would invent a quota of
   nought where none was set).

The distinction in point 3 is the same one as point 1, applied the other way:
an absent quota must NOT become 0, and an explicit zero catch must NOT become
NULL. Both directions matter and the source distinguishes them.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/catch_records_load.py --target-schema arctic_v2
"""
import argparse
import hashlib
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402
import nammco_load  # noqa: E402

ROOT = Path(__file__).parent.parent
NAMMCO_DIR = ROOT / "species_data/nammco"
LOADER_VERSION = "catch_records_load/1.0"

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.catch_records (
    id                  uuid primary key default gen_random_uuid(),
    species_id          uuid not null references {schema}.species (id) on delete cascade,
    year                integer not null,
    area                text not null,
    catch_total         integer,
    quota               integer,
    source              text not null,
    country_id          uuid references {schema}.countries (id),
    data_source         text not null,
    -- Discriminates genuinely contradictory duplicate rows in the NAMMCO
    -- export (see the source-contradiction note in the module docstring).
    -- Without it the natural key would silently discard one of them.
    source_occurrence   integer not null default 1,
    source_artifact     text not null,
    source_sha256       text not null,
    provenance_class    text not null default 'DERIVED',
    loader_version      text not null,
    loaded_at           timestamptz not null default now(),

    -- v1 had no unique constraint on this table at all.
    constraint catch_records_key unique (species_id, year, area, country_id, data_source, source_occurrence),
    -- A negative catch or quota is not a thing.
    constraint catch_records_catch_nonneg check (catch_total is null or catch_total >= 0),
    constraint catch_records_quota_nonneg check (quota is null or quota >= 0),
    constraint catch_records_year_plausible check (year between 1900 and 2100),
    constraint catch_records_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

create index if not exists catch_records_species_year_idx
    on {schema}.catch_records (species_id, year);
"""


def source_digest() -> str:
    """Hash of every NAMMCO export, combined, so the set is pinned not just one file."""
    h = hashlib.sha256()
    for path in sorted(NAMMCO_DIR.glob("*_catches_2025-06-11.csv")):
        h.update(path.name.encode())
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    digest = source_digest()
    artifact = "species_data/nammco/*_catches_2025-06-11.csv"

    conn = psycopg2.connect(url, connect_timeout=30)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL.format(schema=schema))
                cur.execute(f"select count(*) from {schema}.species")
                if cur.fetchone()[0] == 0:
                    sys.exit(f"{schema}.species is empty; load the species spine first")

                # Reuse the verified generator, resolving ids against the target schema.
                rows = list(nammco_load.rows_from_csvs(cur, lookup_schema=schema))
                if not rows:
                    sys.exit("no catch records parsed from the NAMMCO exports")

                # Number the occurrences of each natural key so contradictory
                # source rows are both preserved and distinguishable.
                import collections as _c
                occ = _c.Counter()
                numbered = []
                contradictions = []
                first_seen = {}
                for r in rows:
                    k = (r[0], r[1], r[2], r[6], r[7])
                    occ[k] += 1
                    if occ[k] == 1:
                        first_seen[k] = r
                    else:
                        prior = first_seen[k]
                        if (prior[3], prior[4]) != (r[3], r[4]):
                            contradictions.append((k, prior, r))
                    numbered.append(tuple(r) + (occ[k],))
                rows = numbered

                zeros = sum(1 for r in rows if r[3] == 0)
                nulls = sum(1 for r in rows if r[3] is None)
                with_area = sum(1 for r in rows if r[2])
                with_quota = sum(1 for r in rows if r[4] is not None)
                print(f"parsed:      {len(rows)} catch records")
                print(f"  explicit zero catch: {zeros}  (v1 stored these as NULL)")
                print(f"  genuinely unknown:   {nulls}")
                print(f"  with area:           {with_area}  (v1 had 0)")
                print(f"  with quota:          {with_quota}  (v1 had 0)")
                if contradictions:
                    print(f"\nSOURCE CONTRADICTIONS: {len(contradictions)} natural keys carry "
                          f"two rows with DIFFERENT values in the NAMMCO export.")
                    cur.execute(f"select id, scientific_name from {schema}.species")
                    names = {str(i): n for i, n in cur.fetchall()}
                    for k, a, b in contradictions:
                        print(f"  {names.get(str(k[0]), k[0])} {k[1]} area={k[2]!r}: "
                              f"catch {a[3]!r}/quota {a[4]!r}  vs  catch {b[3]!r}/quota {b[4]!r}")
                    print("  Both rows are PRESERVED and numbered via source_occurrence. "
                          "Which is authoritative is a domain call for the authors, not a load-time one.")

                if args.dry_run:
                    print("\ndry run: nothing loaded")
                    return 0

                # RESTRICT, not CASCADE. CASCADE silently deletes child rows: it
                # wiped all 225 illegal_trade_seizures when this loader
                # truncated illegal_trade_products, because the seizure table
                # references it. RESTRICT makes a destructive reload fail loudly
                # so the operator reloads in dependency order instead.
                # DELETE, not TRUNCATE. Postgres refuses to truncate a table that any
                # foreign key references, even when the referencing table is empty, so
                # a loader that truncates only its own table cannot run at all once the
                # keys exist. DELETE respects the same constraint but succeeds when no
                # child row actually points at anything, and still fails loudly when
                # one does. Slower on the large tables; correctness wins.
                cur.execute(f"delete from {schema}.catch_records")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.catch_records
                        (species_id, year, area, catch_total, quota, source, country_id,
                         data_source, source_occurrence, source_artifact, source_sha256,
                         provenance_class, loader_version) values %s""",
                    [tuple(r) + (artifact, digest, "DERIVED", LOADER_VERSION) for r in rows],
                )
                cur.execute(f"select count(*) from {schema}.catch_records")
                final = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"\nLOADED schema={schema} catch_records={final}")
    print(f"source sha256 (all NAMMCO exports): {digest}")
    if final != len(rows):
        sys.exit(f"FAIL: loaded {final}, expected {len(rows)}; no row may be dropped silently")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
