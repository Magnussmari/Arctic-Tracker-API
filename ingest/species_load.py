#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-28
"""Load the species taxonomic spine into a target schema, from a curated source.

WHY THIS IS CURATED, NOT DERIVED
--------------------------------
The obvious move would be to derive the taxonomy from the CITES download, since
every trade record carries Class/Order/Family/Genus. That does not work, and the
reason is worth stating because a reviewer will ask.

Comparing live taxonomy against the CITES-reported taxonomy (2026-07-28) gives
9 mismatches across 43 species, in two kinds:

  1. Name changes, handled by ingest/aliases.json:
       Antigone canadensis          -> Grus canadensis
       Nyctea scandiaca             -> Bubo scandiacus
       Grus leucogeranus            -> Leucogeranus leucogeranus
       Branta canadensis leucopareia-> Branta hutchinsii

  2. Rank-level divergences where the accepted taxonomy differs from what CITES
     reports. These are curatorial decisions, and one of them is a correction of
     an outright error in the source: CITES places Crassulaceae in Rosales, but
     Crassulaceae is Saxifragales under APG IV.

Because the spine embeds judgement, it is CURATED: the source of truth is a
versioned file in the repository, not the database and not a derivation. Every
divergence from CITES must carry a written reason, and a test enforces that no
divergence is undocumented.

WHAT THIS FIXES
---------------
The live `species` table has zero unique constraints and zero foreign keys: the
taxonomic spine the whole dataset hangs off cannot reject a duplicate and does
not guarantee that a referenced species_id resolves. This loader creates the
table with those constraints in place.

The eight narrative prose fields on the live table are NOT loaded here. They are
machine-generated, carry 412 in-prose citations against 4 rows in the references
table, and have never been reviewed (manual_review='no' and reviewed_by NULL on
all 43 rows). They are GATED content and belong in their own table behind a
signature, not in the taxonomic spine.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/species_load.py --target-schema arctic_v2
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
SOURCE = ROOT / "species_data/curated/species_taxonomy.csv"
LOADER_VERSION = "species_load/1.0"

# Columns that make up the taxonomic spine. Narrative fields are deliberately absent.
COLUMNS = [
    "scientific_name", "common_name", "kingdom", "phylum", "class",
    "order_name", "family", "genus", "species_name", "authority",
    "sis_id", "is_arctic", "cites_reported_name", "divergence_from_cites",
]

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.species (
    id                     uuid primary key default gen_random_uuid(),
    scientific_name        text not null,
    common_name            text not null,
    kingdom                text not null,
    phylum                 text not null,
    class                  text not null,
    order_name             text not null,
    family                 text not null,
    genus                  text not null,
    species_name           text not null,
    authority              text,
    sis_id                 integer,
    is_arctic              boolean not null,
    -- provenance: which CITES name this maps from, and why the accepted
    -- taxonomy differs from what CITES reports. Empty means no divergence.
    cites_reported_name    text,
    divergence_from_cites  text,
    -- provenance columns carried by every v2 table
    source_artifact        text not null,
    source_sha256          text not null,
    provenance_class       text not null default 'CURATED',
    loader_version         text not null,
    loaded_at              timestamptz not null default now(),

    -- the constraints the live table lacks
    constraint species_scientific_name_key unique (scientific_name),
    constraint species_binomial_shape check (scientific_name ~ '^[A-Z][a-z]+ [a-z-]+$'),
    constraint species_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

create index if not exists species_genus_idx  on {schema}.species (genus);
create index if not exists species_family_idx on {schema}.species (family);
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
    missing = [c for c in COLUMNS if c not in rows[0]]
    if missing:
        sys.exit(f"{path} missing columns: {missing}")

    seen = set()
    for row in rows:
        name = (row["scientific_name"] or "").strip()
        if not name:
            sys.exit("blank scientific_name in source")
        if name in seen:
            sys.exit(f"duplicate scientific_name in source: {name!r}")
        seen.add(name)
        # An undocumented divergence must never load: it is precisely the
        # unexplained curatorial decision this file exists to prevent.
        if "UNDOCUMENTED" in (row["divergence_from_cites"] or ""):
            sys.exit(f"undocumented divergence from CITES for {name!r}; document it before loading")
    return rows


def coerce(row: dict) -> dict:
    out = dict(row)
    sis = (row.get("sis_id") or "").strip()
    out["sis_id"] = int(sis) if sis else None
    out["authority"] = (row.get("authority") or "").strip() or None
    arctic = str(row.get("is_arctic", "")).strip().lower()
    out["is_arctic"] = arctic in {"true", "t", "1", "yes"}
    for key in ("cites_reported_name", "divergence_from_cites"):
        out[key] = (row.get(key) or "").strip() or None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--dry-run", action="store_true", help="validate the source and print, load nothing")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    rows = [coerce(r) for r in read_source(args.source)]
    digest = sha256_of(args.source)
    artifact = str(args.source.relative_to(ROOT)) if args.source.is_absolute() else str(args.source)

    diverging = [r for r in rows if r["divergence_from_cites"]]
    print(f"source:   {artifact}")
    print(f"sha256:   {digest}")
    print(f"species:  {len(rows)}")
    print(f"documented divergences from CITES: {len(diverging)}")
    for r in diverging:
        print(f"  {r['scientific_name']}: {r['divergence_from_cites'][:100]}")

    if args.dry_run:
        print("\ndry run: nothing loaded")
        return 0

    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    conn = psycopg2.connect(url, connect_timeout=15)
    try:
        # One transaction for the whole table: a mid-load failure rolls back to
        # the prior good state rather than leaving a half-populated spine.
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
                cur.execute(f"delete from {schema}.species")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.species
                        ({', '.join(COLUMNS)}, source_artifact, source_sha256,
                         provenance_class, loader_version)
                        values %s""",
                    [
                        tuple(r[c] for c in COLUMNS) + (artifact, digest, "CURATED", LOADER_VERSION)
                        for r in rows
                    ],
                )
                cur.execute(f"select count(*) from {schema}.species")
                final = cur.fetchone()[0]
    finally:
        conn.close()

    if final != len(rows):
        sys.exit(f"FAIL: loaded {final}, expected {len(rows)}")
    print(f"\nLOADED schema={schema} species={final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
