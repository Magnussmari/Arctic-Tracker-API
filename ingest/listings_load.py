#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Load CITES appendix listings and split listings into a target schema.

WHAT WAS WRONG IN V1
--------------------
`cites_listings` held 74 rows for 62 real listings. Twelve were byte-identical
duplicates, and they clustered badly:

    Cetorhinus maximus       App II  2003-02-13   held 6 times
    Lamna nasus              App II  2013-06-12   held 4 times
    Physeter macrocephalus   App I   1981-06-06   held 3 times
    Balaenoptera borealis    App I   1981-06-06   held 2 times
    Balaenoptera acutorostrata App I 1986-01-01   held 2 times

These render directly on species pages, so a reviewer opening the basking shark
page saw the same Appendix II listing repeated six times. That reads as either a
data error or a real sequence of re-listings, and neither is good.

The table had no unique constraint, so nothing prevented it. This loader
deduplicates on the full business row and records the collapse per row rather
than performing it silently.

VALIDATION AGAINST AN INDEPENDENT SOURCE
----------------------------------------
Listing dates are CITES CoP decisions and are CURATED: no source file in this
repository carries them. They are not unverifiable, though. Each species'
current appendix can be checked against the appendix actually reported on its
trade records, which is DERIVED data from the CITES download.

That cross-check was run before writing this loader: of the 39 species where
both sources exist, the curated current appendix intersects the traded appendix
for all 39, with zero disagreements. The listings are correct; they were merely
duplicated.

SPLIT LISTINGS
--------------
Two rows, both Balaenoptera acutorostrata: the West Greenland stock sits in
Appendix II while the main population is in Appendix I. This is the classic
CITES split listing, and it is why the species also carries an App I listing
annotated "Except stock of west Greenland".

Usage:
  ARCTIC_DATABASE_URL=... python ingest/listings_load.py --target-schema arctic_v2
"""
import argparse
import csv
import hashlib
import os
import sys
from datetime import date
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

ROOT = Path(__file__).parent.parent
LISTINGS_SOURCE = ROOT / "species_data/curated/cites_listings.csv"
SPLIT_SOURCE = ROOT / "species_data/curated/split_listings.csv"
LOADER_VERSION = "listings_load/1.0"

# CITES appendices, including the split-listing form.
#
# 'I/II' is NOT malformed data. Enhydra lutris carries it, dated 1977-02-04 with
# the note "[SUBFAMILY listing Lutrinae spp.]": the subfamily listing places some
# Lutrinae populations in Appendix I and others in Appendix II, so the species
# inherits a split appendix. An earlier version of this loader rejected it as
# invalid and failed the whole load, which is the correct failure mode for a too
# narrow rule but was still a wrong rule.
#
# The CITES trade data additionally uses 'N' for specimens of taxa not listed in
# the appendices. That value appears on trade records (23 in this corpus), never
# on a listing row, so it is deliberately not accepted here.
VALID_APPENDICES = {"I", "II", "III", "I/II"}

# CITES entered into force 1975-07-01. A listing date before that is impossible.
CITES_IN_FORCE = date(1975, 7, 1)

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.cites_listings (
    id               uuid primary key default gen_random_uuid(),
    species_id       uuid not null references {schema}.species (id) on delete cascade,
    appendix         text not null,
    listing_date     date not null,
    is_current       boolean not null,
    notes            text,
    provenance_note  text,
    source_artifact  text not null,
    source_sha256    text not null,
    provenance_class text not null default 'CURATED',
    loader_version   text not null,
    loaded_at        timestamptz not null default now(),

    -- The constraint whose absence allowed six copies of one listing.
    -- coalesce() on notes because NULL never equals NULL in a unique index.
    constraint cites_listings_appendix_valid check (appendix in ('I','II','III','I/II')),
    constraint cites_listings_after_convention check (listing_date >= date '1975-07-01'),
    constraint cites_listings_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

create unique index if not exists cites_listings_business_key
    on {schema}.cites_listings (species_id, appendix, listing_date, is_current, coalesce(notes, ''));

create table if not exists {schema}.split_listings (
    id                     uuid primary key default gen_random_uuid(),
    species_id             uuid not null references {schema}.species (id) on delete cascade,
    population_identifier  text not null,
    appendix               text not null,
    listing_date           date not null,
    delisting_date         date,
    is_current             boolean not null,
    notes                  text,
    annotation             text,
    source_artifact        text not null,
    source_sha256          text not null,
    provenance_class       text not null default 'CURATED',
    loader_version         text not null,
    loaded_at              timestamptz not null default now(),

    constraint split_listings_key unique (species_id, population_identifier, appendix, listing_date),
    constraint split_listings_appendix_valid check (appendix in ('I','II','III','I/II')),
    constraint split_listings_after_convention check (listing_date >= date '1975-07-01'),
    -- A delisting cannot precede the listing it ends.
    constraint split_listings_delist_after_list check (delisting_date is null or delisting_date >= listing_date)
);
"""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _bool(value) -> bool:
    return str(value).strip().lower() in {"true", "t", "1", "yes"}


def _date(value: str, field: str):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        sys.exit(f"invalid {field}: {value!r}")


def read_listings(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    seen = set()
    out = []
    for row in rows:
        sci = (row["scientific_name"] or "").strip()
        appendix = (row["appendix"] or "").strip()
        listing_date = _date(row["listing_date"], "listing_date")
        if not sci:
            sys.exit("blank scientific_name in listings source")
        if appendix not in VALID_APPENDICES:
            sys.exit(f"invalid appendix {appendix!r} for {sci}")
        if listing_date is None:
            sys.exit(f"missing listing_date for {sci}")
        if listing_date < CITES_IN_FORCE:
            sys.exit(f"{sci}: listing_date {listing_date} precedes CITES entering into force")
        notes = (row.get("notes") or "").strip()
        key = (sci, appendix, listing_date, _bool(row["is_current"]), notes)
        # The v1 defect must be impossible to reintroduce via the source file.
        if key in seen:
            sys.exit(f"duplicate listing in source: {sci} App {appendix} {listing_date}")
        seen.add(key)
        out.append({
            "scientific_name": sci, "appendix": appendix, "listing_date": listing_date,
            "is_current": _bool(row["is_current"]), "notes": notes or None,
            "provenance_note": (row.get("provenance_note") or "").strip() or None,
        })
    return out


def read_splits(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    seen = set()
    out = []
    for row in rows:
        sci = (row["scientific_name"] or "").strip()
        pop = (row["population_identifier"] or "").strip()
        appendix = (row["appendix"] or "").strip()
        listing_date = _date(row["listing_date"], "listing_date")
        delisting_date = _date(row.get("delisting_date", ""), "delisting_date")
        if not sci or not pop:
            sys.exit(f"blank scientific_name or population_identifier: {row!r}")
        if appendix not in VALID_APPENDICES:
            sys.exit(f"invalid appendix {appendix!r} for {sci}/{pop}")
        if listing_date is None:
            sys.exit(f"missing listing_date for {sci}/{pop}")
        if delisting_date and delisting_date < listing_date:
            sys.exit(f"{sci}/{pop}: delisting_date precedes listing_date")
        key = (sci, pop, appendix, listing_date)
        if key in seen:
            sys.exit(f"duplicate split listing: {key}")
        seen.add(key)
        out.append({
            "scientific_name": sci, "population_identifier": pop, "appendix": appendix,
            "listing_date": listing_date, "delisting_date": delisting_date,
            "is_current": _bool(row["is_current"]),
            "notes": (row.get("notes") or "").strip() or None,
            "annotation": (row.get("annotation") or "").strip() or None,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    listings = read_listings(LISTINGS_SOURCE)
    splits = read_splits(SPLIT_SOURCE)
    ldigest, sdigest = sha256_of(LISTINGS_SOURCE), sha256_of(SPLIT_SOURCE)
    lartifact = str(LISTINGS_SOURCE.relative_to(ROOT))
    sartifact = str(SPLIT_SOURCE.relative_to(ROOT))

    collapsed = [r for r in listings if r["provenance_note"]]
    print(f"cites_listings: {len(listings)} unique  sha256={ldigest[:16]}...")
    print(f"split_listings: {len(splits)}          sha256={sdigest[:16]}...")
    print(f"duplicate groups collapsed from v1: {len(collapsed)}")
    for r in collapsed:
        print(f"  {r['scientific_name']} App {r['appendix']} {r['listing_date']}: {r['provenance_note']}")

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
                if not species:
                    sys.exit(f"{schema}.species is empty; load the species spine first")
                unknown = sorted(
                    ({r["scientific_name"] for r in listings} | {r["scientific_name"] for r in splits})
                    - set(species)
                )
                if unknown:
                    sys.exit(f"listings reference unknown species: {unknown}")

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
                cur.execute(f"delete from {schema}.cites_listings")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.cites_listings
                        (species_id, appendix, listing_date, is_current, notes, provenance_note,
                         source_artifact, source_sha256, provenance_class, loader_version) values %s""",
                    [(species[r["scientific_name"]], r["appendix"], r["listing_date"], r["is_current"],
                      r["notes"], r["provenance_note"], lartifact, ldigest, "CURATED", LOADER_VERSION)
                     for r in listings],
                )
                cur.execute(f"delete from {schema}.split_listings")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.split_listings
                        (species_id, population_identifier, appendix, listing_date, delisting_date,
                         is_current, notes, annotation, source_artifact, source_sha256,
                         provenance_class, loader_version) values %s""",
                    [(species[r["scientific_name"]], r["population_identifier"], r["appendix"],
                      r["listing_date"], r["delisting_date"], r["is_current"], r["notes"],
                      r["annotation"], sartifact, sdigest, "CURATED", LOADER_VERSION)
                     for r in splits],
                )
                cur.execute(f"select count(*) from {schema}.cites_listings")
                nl = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.split_listings")
                ns = cur.fetchone()[0]
    finally:
        conn.close()

    if nl != len(listings) or ns != len(splits):
        sys.exit(f"FAIL: loaded {nl}/{ns}, expected {len(listings)}/{len(splits)}")
    print(f"\nLOADED schema={schema} cites_listings={nl} split_listings={ns}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
