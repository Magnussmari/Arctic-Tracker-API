#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Load CMS-family listings from the CMS export. Genuinely DERIVED.

This is the first table in the rebuild with a real external source file:
`species_data/raw_data/cms_listing_100725.csv`, a semicolon-delimited CMS export
covering 2,032 taxa. Nothing here is authored; every row is filtered and parsed
from that file, and the file's SHA-256 is recorded on every row.

TWO FINDINGS AGAINST V1
-----------------------
1. TWO LISTINGS WERE MISSING ENTIRELY. The source carries CMS Appendix II
   listings for Branta hutchinsii (listed under 'Anatidae spp.', 1994) and
   Grus canadensis (listed under 'Grus spp.', 1979). Neither is in the live
   table. Both are listed under a higher-taxon entry rather than their own
   binomial, which is the likely reason an exact-name match missed them. They
   are recovered here.

2. V1 HELD ONLY THE PARENT CMS AGREEMENT. Filtering the source to our 43 species
   gives 82 rows across 11 instruments; the live table holds 31, all with
   agreement='CMS'. The 49 rows dropped belong to CMS daughter agreements that
   are real conservation instruments in their own right:

       ACCOBAMS 12, Pacific Islands Cetaceans 10, ASCOBANS 9,
       Western African Aquatic Mammals 5, Raptors 5, Sharks 3, AEWA 2,
       Southern South American Grassland Birds 1, Siberian Crane 1, ACAP 1

   This loader keeps all of them, because the table already has an `agreement`
   column whose entire purpose is to distinguish them, and because silently
   discarding 60% of what a source provides is the class of undocumented
   curatorial decision this rebuild exists to eliminate. Nothing is conflated:
   a consumer wanting the v1 behaviour filters on agreement='CMS'.

   Whether the paper should analyse daughter-agreement listings is a domain
   question for the authors, not a load-time one. The data is now present and labelled
   so that question can actually be asked.

DATE PARSING
------------
The source's Date field uses three shapes, all present in this corpus:

    '**II** 08/02/2015'                    parent CMS, one appendix listing
    '**I** 23/12/2002\n**II** 23/12/2002'   listed in BOTH appendices: emitted
                                           as TWO rows, not one row labelled
                                           'I/II'
    '01/06/2001'                           a daughter agreement, which is
                                           membership in an instrument and has
                                           no appendix, so appendix is NULL
                                           rather than invented

The appendix is stated twice, in `Listing` and inside `Date`. They are
cross-checked and a disagreement is a hard error rather than a silent
preference for one field over the other.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/cms_load.py --target-schema arctic_v2
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "species_data/raw_data/cms_listing_100725.csv"
ALIASES = ROOT / "ingest/aliases.json"
LOADER_VERSION = "cms_load/1.0"

# '**II** 01/01/1979' -> appendix 'II', date 1979-01-01
DATE_FIELD = re.compile(r"\*\*(?P<appendix>[IVX]+)\*\*\s*(?P<date>\d{2}/\d{2}/\d{4})")
BARE_DATE = re.compile(r"\d{2}/\d{2}/\d{4}")
# A single listing names one appendix. 'I/II' appears in the Listing column to
# mean "listed in both", which the Date field expresses as two entries.
VALID_APPENDICES = {"I", "II"}

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.cms_listings (
    id                      uuid primary key default gen_random_uuid(),
    species_id              uuid not null references {schema}.species (id) on delete cascade,
    agreement               text not null,
    appendix                text,
    listing_date            date not null,
    listed_under            text,
    notes                   text,
    native_distribution     text,
    distribution_codes      text,
    extinct_distribution    text,
    distribution_uncertain  text,
    source_row_id           text not null,
    source_artifact         text not null,
    source_sha256           text not null,
    provenance_class        text not null default 'DERIVED',
    loader_version          text not null,
    loaded_at               timestamptz not null default now(),

    constraint cms_listings_appendix_valid check (appendix is null or appendix in ('I','II')),
    -- CMS entered into force 1983-11-01, but the export dates the original
    -- appendices to the 1979 Bonn Convention text, so 1979 is the floor.
    constraint cms_listings_after_convention check (listing_date >= date '1979-01-01'),
    constraint cms_listings_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

-- Unique index rather than a constraint: the key needs coalesce() because
-- appendix is NULL for daughter agreements, and NULL never equals NULL.
create unique index if not exists cms_listings_key
    on {schema}.cms_listings (species_id, agreement, coalesce(appendix, ''), listing_date);

create index if not exists cms_listings_agreement_idx on {schema}.cms_listings (agreement);
"""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _to_date(text: str, who: str) -> date:
    day, month, year = text.split("/")
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        sys.exit(f"{who}: invalid date {text!r}")


def parse_listings(field: str, listing: str, who: str) -> list[tuple[str | None, date]]:
    """Parse the source's Date field into one or more (appendix, date) listings.

    The export uses three shapes, all present in this corpus:

      '**II** 08/02/2015'                      parent CMS, one appendix listing
      '**I** 23/12/2002\\n**II** 23/12/2002'    listed in BOTH appendices, one
                                               row per appendix, Listing='I/II'
      '01/06/2001'                             a daughter agreement: this is
                                               membership in an instrument, not
                                               an appendix listing, so appendix
                                               is NULL rather than invented

    Returning a list rather than a single value is what makes the split case
    faithful: two appendix listings become two rows, not one row with a
    concatenated label.
    """
    field = (field or "").strip()
    listing = (listing or "").strip()
    if not field:
        sys.exit(f"{who}: empty Date field")

    matches = list(DATE_FIELD.finditer(field))
    if matches:
        out = []
        for match in matches:
            appendix = match.group("appendix")
            if appendix not in VALID_APPENDICES:
                sys.exit(f"{who}: unexpected CMS appendix {appendix!r}")
            out.append((appendix, _to_date(match.group("date"), who)))
        # The source states the appendix twice. They must agree, or the row is
        # not understood: a hard error beats silently preferring one field.
        if listing:
            stated = {a for a, _ in out}
            expected = set(listing.split("/"))
            if stated != expected:
                sys.exit(f"{who}: Listing={listing!r} disagrees with Date appendices {sorted(stated)}")
        return out

    if BARE_DATE.fullmatch(field):
        if listing:
            sys.exit(f"{who}: bare date {field!r} but Listing={listing!r} claims an appendix")
        return [(None, _to_date(field, who))]

    sys.exit(f"{who}: cannot parse Date field {field!r}")


def read_source(path: Path, species_names: set[str]) -> list[dict]:
    aliases = json.loads(ALIASES.read_text())["cites_aliases"]
    out = []
    seen = set()
    with open(path, newline="", encoding="utf8", errors="replace") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            name = (row.get("ScientificName") or "").strip()
            mapped = aliases.get(name, name)
            if mapped not in species_names:
                continue
            who = f"{mapped} ({row.get('Agreement')})"
            agreement = (row.get("Agreement") or "").strip()
            if not agreement:
                sys.exit(f"{who}: blank Agreement")
            for appendix, listing_date in parse_listings(row.get("Date"), row.get("Listing"), who):
                key = (mapped, agreement, appendix, listing_date)
                if key in seen:
                    continue  # same instrument, same appendix, same date: one listing
                seen.add(key)
                out.append({
                "scientific_name": mapped,
                "agreement": agreement,
                "appendix": appendix,
                "listing_date": listing_date,
                "listed_under": (row.get("Listed under") or "").strip() or None,
                "notes": (row.get("Note") or "").strip() or None,
                "native_distribution": (row.get("NativeDistributionFullNames") or "").strip() or None,
                "distribution_codes": (row.get("All_DistributionISOCodes") or "").strip() or None,
                "extinct_distribution": (row.get("Extinct_Distribution") or "").strip() or None,
                "distribution_uncertain": (row.get("Distribution_Uncertain") or "").strip() or None,
                "source_row_id": (row.get("Id") or "").strip(),
            })
    if not out:
        sys.exit(f"no rows matched the species set in {path}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    conn = psycopg2.connect(url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute(f"select scientific_name, id from {schema}.species")
            species = dict(cur.fetchall())
        if not species:
            sys.exit(f"{schema}.species is empty; load the species spine first")

        rows = read_source(SOURCE, set(species))
        digest = sha256_of(SOURCE)
        artifact = str(SOURCE.relative_to(ROOT))

        from collections import Counter
        agreements = Counter(r["agreement"] for r in rows)
        print(f"source:  {artifact}")
        print(f"sha256:  {digest}")
        print(f"rows:    {len(rows)} across {len(agreements)} instruments "
              f"(v1 held 31, agreement='CMS' only)")
        for agreement, n in agreements.most_common():
            print(f"    {agreement:38} {n}")

        if args.dry_run:
            print("\ndry run: nothing loaded")
            return 0

        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL.format(schema=schema))
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
                cur.execute(f"delete from {schema}.cms_listings")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.cms_listings
                        (species_id, agreement, appendix, listing_date, listed_under, notes,
                         native_distribution, distribution_codes, extinct_distribution,
                         distribution_uncertain, source_row_id, source_artifact, source_sha256,
                         provenance_class, loader_version) values %s""",
                    [(species[r["scientific_name"]], r["agreement"], r["appendix"], r["listing_date"],
                      r["listed_under"], r["notes"], r["native_distribution"], r["distribution_codes"],
                      r["extinct_distribution"], r["distribution_uncertain"], r["source_row_id"],
                      artifact, digest, "DERIVED", LOADER_VERSION) for r in rows],
                )
                cur.execute(f"select count(*) from {schema}.cms_listings")
                final = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.cms_listings where agreement = 'CMS'")
                cms_only = cur.fetchone()[0]
    finally:
        conn.close()

    if final != len(rows):
        sys.exit(f"FAIL: loaded {final}, expected {len(rows)}")
    print(f"\nLOADED schema={schema} cms_listings={final} (agreement='CMS': {cms_only})")
    print("NOTE: v1 held only the parent CMS agreement. Daughter-agreement listings are now "
          "present and labelled; filter on agreement='CMS' for the v1 view.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
