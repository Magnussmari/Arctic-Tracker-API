#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Load the species timeline into a target schema.

WHAT THIS TABLE IS
------------------
A polymorphic event log: five kinds of event denormalised into one shape, each
naming the table it came from via (source_type, source_id).

    iucn_assessment    343   <- arctic.iucn_assessments
    cites_listing       70   <- arctic.cites_listings
    cites_suspension    57   <- arctic.cites_suspensions   (TABLE DOES NOT EXIST)
    cites_trade         52   <- arctic.cites_trade_records (source_id always NULL)
    eu_decision          9   <- arctic.eu_decisions        (TABLE DOES NOT EXIST)

FOUR PROBLEMS FOUND, AND WHAT WAS DONE
--------------------------------------
1. DANGLING REFERENCES. 255 of the 341 iucn_assessment events carried a
   source_id that resolves to no row in arctic.iucn_assessments: 75% of that
   event type pointed at nothing. A reference that silently resolves to nothing
   is worse than no reference, because code and readers both assume it is live.
   Those source_ids are set to NULL with the reason recorded per row. The events
   themselves are kept: the event is real even when the pointer rotted.

2. INHERITED DUPLICATION. 11 events were duplicates, and they were NOT an
   independent defect: timeline row counts mirrored cites_listings row counts
   exactly (Cetorhinus maximus 6/6, Lamna nasus 5/5, Physeter macrocephalus 5/5).
   They were faithful copies of already-duplicated listings. Deduplicating
   cites_listings at the root removes them here, which is the point of fixing
   root causes rather than symptoms. Collapse recorded per row.

3. STATUS VOCABULARY COLLISION. The status column mixes IUCN categories (LC, VU,
   EN, CR), CITES appendices (I, II, III, I/II), suspension state and EU decision
   outcomes, which is inherent to a polymorphic table. But it also held
   'Least Concern' once alongside 'LC' 113 times: the same one-value-two-spellings
   defect as the v1 language codes. Normalised, with the rewrite recorded.

4. TWO SOURCE TABLES DO NOT EXIST. 66 events name arctic.cites_suspensions or
   arctic.eu_decisions, neither of which is in the database. Those events are
   therefore the ONLY surviving record of that data. They are preserved
   unchanged and flagged, NOT dropped. Dropping them would destroy information
   that exists nowhere else, and reconstructing the missing tables requires a
   source we do not have. Tracked as an open item.

WHY THIS IS NOT A VIEW
----------------------
The obvious v2 design is a view derived from the source tables, which would make
drift impossible. It does not work here: only 145 of 520 events still have a
resolvable source. The other 375 would vanish. The table stays a table, CURATED,
until the missing sources are recovered; at that point the derivable portion
should become a view and this loader should shrink.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/timeline_load.py --target-schema arctic_v2
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
SOURCE = ROOT / "species_data/curated/timeline_events.csv"
LOADER_VERSION = "timeline_load/1.0"

EVENT_TYPES = {"iucn_assessment", "cites_listing", "cites_suspension", "cites_trade", "eu_decision"}

# Source tables that exist in the schema. An event naming anything else is kept
# but can never carry a resolvable source_id.
RESOLVABLE_SOURCES = {"iucn_assessments", "cites_listings"}
ORPHANED_SOURCES = {"cites_suspensions", "eu_decisions"}

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.timeline_events (
    id                uuid primary key default gen_random_uuid(),
    species_id        uuid not null references {schema}.species (id) on delete cascade,
    event_date        date not null,
    year              integer not null,
    event_type        text not null,
    title             text not null,
    description       text,
    status            text,
    source_type       text,
    source_id         uuid,
    provenance_note   text,
    source_artifact   text not null,
    source_sha256     text not null,
    provenance_class  text not null default 'CURATED',
    loader_version    text not null,
    loaded_at         timestamptz not null default now(),

    constraint timeline_events_type_valid check (event_type in
        ('iucn_assessment','cites_listing','cites_suspension','cites_trade','eu_decision')),
    -- year must agree with event_date; v1 stored both with nothing enforcing it.
    constraint timeline_events_year_matches_date check (year = extract(year from event_date)),
    constraint timeline_events_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

-- The business key. v1 had no unique constraint, which is how it inherited 11
-- duplicates from cites_listings without complaint.
create unique index if not exists timeline_events_business_key
    on {schema}.timeline_events (
        species_id, event_date, event_type, title,
        coalesce(description, ''), coalesce(status, '')
    );

create index if not exists timeline_events_species_date_idx
    on {schema}.timeline_events (species_id, event_date);
"""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_source(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    seen = set()
    out = []
    for row in rows:
        sci = (row["scientific_name"] or "").strip()
        title = (row["title"] or "").strip()
        etype = (row["event_type"] or "").strip()
        if not sci or not title:
            sys.exit(f"blank scientific_name or title: {row!r}")
        if etype not in EVENT_TYPES:
            sys.exit(f"unknown event_type {etype!r} for {sci}")
        try:
            event_date = date.fromisoformat((row["event_date"] or "").strip())
        except ValueError:
            sys.exit(f"invalid event_date for {sci}: {row['event_date']!r}")
        try:
            year = int(row["year"])
        except (TypeError, ValueError):
            sys.exit(f"invalid year for {sci}: {row['year']!r}")
        # v1 stored year and event_date independently with nothing tying them.
        if year != event_date.year:
            sys.exit(f"{sci}: year {year} disagrees with event_date {event_date}")

        source_type = (row.get("source_type") or "").strip() or None
        source_id = (row.get("source_id") or "").strip() or None
        # A source_id may only survive if its table actually exists. Anything
        # else was already nulled upstream; this is the guard against it coming back.
        if source_id and source_type not in RESOLVABLE_SOURCES:
            sys.exit(f"{sci}: source_id set for unresolvable source_type {source_type!r}")

        description = (row.get("description") or "").strip()
        status = (row.get("status") or "").strip()
        key = (sci, event_date, etype, title, description, status)
        if key in seen:
            sys.exit(f"duplicate timeline event in source: {sci} {event_date} {title!r}")
        seen.add(key)
        out.append({
            "scientific_name": sci, "event_date": event_date, "year": year,
            "event_type": etype, "title": title, "description": description or None,
            "status": status or None, "source_type": source_type, "source_id": source_id,
            "provenance_note": (row.get("provenance_note") or "").strip() or None,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    rows = read_source(SOURCE)
    digest = sha256_of(SOURCE)
    artifact = str(SOURCE.relative_to(ROOT))

    resolvable = sum(1 for r in rows if r["source_id"])
    orphaned = sum(1 for r in rows if r["source_type"] in ORPHANED_SOURCES)
    nulled = sum(1 for r in rows if r["provenance_note"] and "source_id dropped" in r["provenance_note"])
    collapsed = sum(1 for r in rows if r["provenance_note"] and "collapsed to 1" in r["provenance_note"])

    print(f"source:  {artifact}")
    print(f"sha256:  {digest}")
    print(f"events:  {len(rows)}  (v1 held 531)")
    print(f"  with a resolvable source_id:      {resolvable}")
    print(f"  source_ids nulled as dangling:    {nulled}")
    print(f"  duplicates collapsed:             {collapsed}")
    print(f"  events whose source table is GONE: {orphaned} "
          f"(cites_suspensions, eu_decisions: preserved, only surviving record)")

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
                unknown = sorted({r["scientific_name"] for r in rows} - set(species))
                if unknown:
                    sys.exit(f"timeline references unknown species: {unknown}")

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
                cur.execute(f"delete from {schema}.timeline_events")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.timeline_events
                        (species_id, event_date, year, event_type, title, description, status,
                         source_type, source_id, provenance_note, source_artifact, source_sha256,
                         provenance_class, loader_version) values %s""",
                    [(species[r["scientific_name"]], r["event_date"], r["year"], r["event_type"],
                      r["title"], r["description"], r["status"], r["source_type"], r["source_id"],
                      r["provenance_note"], artifact, digest, "CURATED", LOADER_VERSION)
                     for r in rows],
                )
                cur.execute(f"select count(*) from {schema}.timeline_events")
                final = cur.fetchone()[0]
    finally:
        conn.close()

    if final != len(rows):
        sys.exit(f"FAIL: loaded {final}, expected {len(rows)}")
    print(f"\nLOADED schema={schema} timeline_events={final}")
    print("OPEN ITEM: arctic.cites_suspensions and arctic.eu_decisions do not exist. "
          f"{orphaned} events are the only surviving record of that data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
