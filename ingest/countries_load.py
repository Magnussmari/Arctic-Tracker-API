#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-28
"""Load the countries reference table into a target schema, from a curated source.

SCOPE
-----
This table is NOT a reference list of CITES trading parties. It is a curated
list of 20 countries carrying two pieces of domain semantics that exist nowhere
in any source file: NAMMCO membership and Arctic Council membership. Those are
the reason the table exists, and they are why it is CURATED.

What actually references it (verified against live, 2026-07-28):

    arctic.catch_records.country_id   -> countries.id   (958/958 populated)
    arctic.management_areas.country_id -> countries.id

`cites_trade_records` does NOT reference it. Importer, exporter and origin are
stored as bare ISO alpha-2 text with no foreign key, so the 226 country codes
that appear in trade data without a row here are a GAP IN COVERAGE, not silent
data loss: no join drops them because no join exists.

That gap is still worth stating. The trade data contains 244 distinct country
codes; this table holds 20, of which 18 had a usable code before this loader.
Any future country-level trade analysis needs a complete ISO 3166 reference,
which is not currently in the repository. Deliberately NOT fabricated here:
writing 226 country names from memory is exactly the kind of unsourced fill this
project has committed to not doing. Tracked as an open item instead.

WHAT THIS FIXES
---------------
Greenland and the Faroe Islands both had a NULL country_code in v1 while being
NAMMCO members with trade records against them (GL 47,000 references, FO 407).
Both codes are restored from ISO 3166-1 alpha-2, with the repair recorded per
row in `provenance_note` rather than applied silently.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/countries_load.py --target-schema arctic_v2
"""
import argparse
import csv
import hashlib
import os
import re
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "species_data/curated/countries.csv"
LOADER_VERSION = "countries_load/1.0"

COLUMNS = ["country_name", "country_code", "nammco_member", "arctic_council", "provenance_note"]

ALPHA2 = re.compile(r"^[A-Z]{2}$")

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.countries (
    id               uuid primary key default gen_random_uuid(),
    country_name     text not null,
    country_code     text not null,
    nammco_member    boolean not null,
    arctic_council   boolean not null,
    provenance_note  text,
    source_artifact  text not null,
    source_sha256    text not null,
    provenance_class text not null default 'CURATED',
    loader_version   text not null,
    loaded_at        timestamptz not null default now(),

    -- constraints the live table lacked: it permitted NULL codes, which is how
    -- Greenland and the Faroe Islands ended up unjoinable.
    constraint countries_name_key unique (country_name),
    constraint countries_code_key unique (country_code),
    constraint countries_code_is_alpha2 check (country_code ~ '^[A-Z]{{2}}$'),
    constraint countries_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
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


def read_source(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    missing = [c for c in COLUMNS if c not in rows[0]]
    if missing:
        sys.exit(f"{path} missing columns: {missing}")

    seen_names, seen_codes = set(), set()
    out = []
    for row in rows:
        name = (row["country_name"] or "").strip()
        code = (row["country_code"] or "").strip().upper()
        if not name:
            sys.exit("blank country_name in source")
        # A NULL/blank code is the exact v1 defect this loader exists to close.
        if not code:
            sys.exit(f"blank country_code for {name!r}: every country needs a joinable code")
        if not ALPHA2.match(code):
            sys.exit(f"country_code {code!r} for {name!r} is not ISO 3166-1 alpha-2")
        if name in seen_names:
            sys.exit(f"duplicate country_name: {name!r}")
        if code in seen_codes:
            sys.exit(f"duplicate country_code: {code!r}")
        seen_names.add(name)
        seen_codes.add(code)
        out.append({
            "country_name": name,
            "country_code": code,
            "nammco_member": _bool(row["nammco_member"]),
            "arctic_council": _bool(row["arctic_council"]),
            "provenance_note": (row.get("provenance_note") or "").strip() or None,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--source", type=Path, default=SOURCE)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    rows = read_source(args.source)
    digest = sha256_of(args.source)
    artifact = str(args.source.relative_to(ROOT)) if args.source.is_absolute() else str(args.source)

    repaired = [r for r in rows if r["provenance_note"]]
    print(f"source:  {artifact}")
    print(f"sha256:  {digest}")
    print(f"rows:    {len(rows)}  (NAMMCO {sum(r['nammco_member'] for r in rows)}, "
          f"Arctic Council {sum(r['arctic_council'] for r in rows)})")
    print(f"repairs recorded: {len(repaired)}")
    for r in repaired:
        print(f"  {r['country_name']} -> {r['country_code']}: {r['provenance_note']}")

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
                cur.execute(f"delete from {schema}.countries")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.countries
                        ({', '.join(COLUMNS)}, source_artifact, source_sha256,
                         provenance_class, loader_version) values %s""",
                    [tuple(r[c] for c in COLUMNS) + (artifact, digest, "CURATED", LOADER_VERSION)
                     for r in rows],
                )
                cur.execute(f"select count(*) from {schema}.countries")
                final = cur.fetchone()[0]
    finally:
        conn.close()

    if final != len(rows):
        sys.exit(f"FAIL: loaded {final}, expected {len(rows)}")
    print(f"\nLOADED schema={schema} countries={final}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
