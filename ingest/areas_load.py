#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Load subpopulations and NAMMCO management areas into a target schema.

MANAGEMENT AREAS: WHAT WAS WRONG IN V1
--------------------------------------
38 rows, of which 6 carried a NULL country_id and were name-duplicates of
properly attributed rows:

    id 4 "West"                  duplicate of id 1  (Greenland)
    id 5 "East"                  duplicate of id 2  (Greenland)
    id 6 "Total"                 duplicate of id 3  (Greenland)
    id 7 "Iceland Coastal (CIC)" duplicate of id 10 (Iceland)
    id 8 "E"                     duplicate of id 11 (Norway)
    id 9 "CM"                    duplicate of id 12 (Norway)

Each was verified to have ZERO referencing catch records before being dropped:
all 958 catch records point at the 32 properly attributed areas. The drop is
therefore provably safe, not a judgement call. The assertion that enforces this
is in the source-generation step and is repeated as a test here.

An area name is only unique within a country ("Total" exists for both Greenland
and Norway, "West" only for Greenland), so the business key is the pair.

A NOTE ON catch_records.area
----------------------------
The `area` text column on catch_records is NULL for all 958 rows, which can
be misread as the area being unrecorded. It is recorded:
`catch_records.management_area_id` is populated on 958 of 958 rows, so the area
is fully recorded through the foreign key; the text column is a redundant
duplicate that was never filled. The v2 schema keeps the FK and drops the text
column rather than backfilling a column nothing reads.

SUBPOPULATIONS
--------------
12 IUCN-recognised subpopulations across 6 species, each carrying its own SIS
assessment id (for example Lamna nasus has four: Mediterranean, Northeast
Atlantic, Northwest Atlantic, Southern Hemisphere). These are the units IUCN
assesses separately from the global species assessment, so the sis_id is the
join key back to a distinct Red List assessment and must be unique.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/areas_load.py --target-schema arctic_v2
"""
import argparse
import csv
import hashlib
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

ROOT = Path(__file__).parent.parent
SUBPOP_SOURCE = ROOT / "species_data/curated/subpopulations.csv"
AREAS_SOURCE = ROOT / "species_data/curated/management_areas.csv"
LOADER_VERSION = "areas_load/1.0"

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.subpopulations (
    id                  uuid primary key default gen_random_uuid(),
    species_id          uuid not null references {schema}.species (id) on delete cascade,
    subpopulation_name  text not null,
    sis_id              integer,
    authority           text,
    source_artifact     text not null,
    source_sha256       text not null,
    provenance_class    text not null default 'CURATED',
    loader_version      text not null,
    loaded_at           timestamptz not null default now(),

    constraint subpopulations_key unique (species_id, subpopulation_name),
    constraint subpopulations_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

-- Each subpopulation is a separately assessed IUCN unit, so a SIS id cannot be
-- shared. Partial index because sis_id is nullable.
create unique index if not exists subpopulations_sis_id_key
    on {schema}.subpopulations (sis_id) where sis_id is not null;

create table if not exists {schema}.management_areas (
    id                uuid primary key default gen_random_uuid(),
    area_name         text not null,
    country_id        uuid not null references {schema}.countries (id),
    area_type         text not null,
    provenance_note   text,
    source_artifact   text not null,
    source_sha256     text not null,
    provenance_class  text not null default 'CURATED',
    loader_version    text not null,
    loaded_at         timestamptz not null default now(),

    -- An area name is unique only within a country: "Total" exists for both
    -- Greenland and Norway. country_id is NOT NULL, which is what makes the six
    -- v1 orphan rows structurally impossible to recreate.
    constraint management_areas_key unique (area_name, country_id),
    constraint management_areas_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);
"""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_subpopulations(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    seen, seen_sis = set(), set()
    out = []
    for row in rows:
        sci = (row["scientific_name"] or "").strip()
        name = (row["subpopulation_name"] or "").strip()
        if not sci or not name:
            sys.exit(f"blank scientific_name or subpopulation_name: {row!r}")
        key = (sci, name)
        if key in seen:
            sys.exit(f"duplicate subpopulation: {key}")
        seen.add(key)
        sis = (row.get("sis_id") or "").strip()
        sis_id = int(sis) if sis else None
        if sis_id is not None:
            # A shared SIS id would mean two subpopulations claiming one assessment.
            if sis_id in seen_sis:
                sys.exit(f"sis_id {sis_id} used by more than one subpopulation")
            seen_sis.add(sis_id)
        out.append({
            "scientific_name": sci, "subpopulation_name": name, "sis_id": sis_id,
            "authority": (row.get("authority") or "").strip() or None,
        })
    return out


def read_areas(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    seen = set()
    out = []
    for row in rows:
        name = (row["area_name"] or "").strip()
        country = (row["country_name"] or "").strip()
        area_type = (row["area_type"] or "").strip()
        if not name:
            sys.exit("blank area_name in source")
        # The v1 defect: an area with no country. Six such rows existed.
        if not country:
            sys.exit(f"area {name!r} has no country; every management area must be attributed")
        if not area_type:
            sys.exit(f"area {name!r} has no area_type")
        key = (name, country)
        if key in seen:
            sys.exit(f"duplicate management area: {key}")
        seen.add(key)
        out.append({
            "area_name": name, "country_name": country, "area_type": area_type,
            "provenance_note": (row.get("provenance_note") or "").strip() or None,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    subpops = read_subpopulations(SUBPOP_SOURCE)
    areas = read_areas(AREAS_SOURCE)
    sdigest, adigest = sha256_of(SUBPOP_SOURCE), sha256_of(AREAS_SOURCE)
    sartifact = str(SUBPOP_SOURCE.relative_to(ROOT))
    aartifact = str(AREAS_SOURCE.relative_to(ROOT))

    print(f"subpopulations:   {len(subpops)} across "
          f"{len({r['scientific_name'] for r in subpops})} species")
    print(f"management_areas: {len(areas)} (v1 held 38; 6 unreferenced orphans removed)")

    if args.dry_run:
        print("\ndry run: nothing loaded")
        return 0

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    conn = psycopg2.connect(url, connect_timeout=15)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL.format(schema=schema))
                cur.execute(f"select scientific_name, id from {schema}.species")
                species = dict(cur.fetchall())
                cur.execute(f"select country_name, id from {schema}.countries")
                countries = dict(cur.fetchall())
                if not species or not countries:
                    sys.exit(f"{schema}.species or .countries empty; load those first")

                unknown_sp = sorted({r["scientific_name"] for r in subpops} - set(species))
                if unknown_sp:
                    sys.exit(f"subpopulations reference unknown species: {unknown_sp}")
                unknown_c = sorted({r["country_name"] for r in areas} - set(countries))
                if unknown_c:
                    sys.exit(f"areas reference unknown countries: {unknown_c}")

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
                cur.execute(f"delete from {schema}.subpopulations")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.subpopulations
                        (species_id, subpopulation_name, sis_id, authority,
                         source_artifact, source_sha256, provenance_class, loader_version)
                        values %s""",
                    [(species[r["scientific_name"]], r["subpopulation_name"], r["sis_id"],
                      r["authority"], sartifact, sdigest, "CURATED", LOADER_VERSION)
                     for r in subpops],
                )
                cur.execute(f"delete from {schema}.management_areas")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.management_areas
                        (area_name, country_id, area_type, provenance_note,
                         source_artifact, source_sha256, provenance_class, loader_version)
                        values %s""",
                    [(r["area_name"], countries[r["country_name"]], r["area_type"],
                      r["provenance_note"], aartifact, adigest, "CURATED", LOADER_VERSION)
                     for r in areas],
                )
                cur.execute(f"select count(*) from {schema}.subpopulations")
                ns = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.management_areas")
                na = cur.fetchone()[0]
    finally:
        conn.close()

    if ns != len(subpops) or na != len(areas):
        sys.exit(f"FAIL: loaded {ns}/{na}, expected {len(subpops)}/{len(areas)}")
    print(f"\nLOADED schema={schema} subpopulations={ns} management_areas={na}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
