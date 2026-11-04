#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-28
"""Load species common names into a target schema, from a curated source.

WHAT WAS WRONG IN V1
--------------------
Language codes were recorded against three different standards at once. The bulk
used ISO 639-2/T three-letter codes (eng, fra, deu), but twelve languages used
ISO 639-1 two-letter codes (hr, el, is, sq, ar, ja, he, fo, af, sr, en, mi) and
one row used the literal string 'English'. So English appeared under three
distinct identifiers: 'eng', 'en' and 'English'. Any grouping or filtering by
language silently split or dropped those rows.

Every two-letter code was confirmed against the actual names before mapping,
not assumed from the code alone:

    hr -> hrv   Škanjac gaćaš, Morž          (Croatian)
    el -> ell   Χιονογερακίνα                 (Greek)
    is -> isl   Rostungur, Beinhákarl         (Icelandic)
    sq -> sqi   Kashalot, Peshkaqen shtegtar  (Albanian)
    fo -> fao   Hemari, Brugda                (Faroese)
    af -> afr   Haringhaai, Koesterhaai       (Afrikaans)
    sr -> srp   Psina atlantska               (Serbian)
    mi -> mri   Reremai                       (Maori)
    ar -> ara / ja -> jpn / he -> heb         (see transliteration note)
    en -> eng, 'English' -> eng

All 327 names now carry a three-letter ISO 639-3 code across 39 languages.

TRANSLITERATION
---------------
The Arabic, Japanese and Hebrew entries hold Latin transliterations rather than
native script ('Môka-zame' for Japanese, 'Kalb' for Arabic). That is recorded per
row in provenance_note rather than corrected, because converting them would mean
inventing orthography this project has no source for.

COVERAGE GAP, NOT FILLED
------------------------
Only 24 of 43 species have any common name. The 19 without include several
prominent ones: blue whale, killer whale, gray whale, harbour porpoise, sandhill
crane, short-eared owl.

These are deliberately NOT filled in. Common names are trivially available from
general knowledge, which is exactly why writing them here would be unsourced
fill: the whole point of this rebuild is that every row can name its origin. The
gap is reported by this loader and tracked as an open item for a sourced import
(IUCN or GBIF vernacular names), which is the correct fix.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/common_names_load.py --target-schema arctic_v2
"""
import argparse
import csv
import hashlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402

ROOT = Path(__file__).parent.parent
SOURCE = ROOT / "species_data/curated/common_names.csv"
LOADER_VERSION = "common_names_load/1.0"

COLUMNS = ["scientific_name", "name", "language", "is_main", "provenance_note"]
ISO639_3 = re.compile(r"^[a-z]{3}$")

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.common_names (
    id               uuid primary key default gen_random_uuid(),
    species_id       uuid not null references {schema}.species (id) on delete cascade,
    name             text not null,
    language         text not null,
    is_main          boolean not null default false,
    provenance_note  text,
    source_artifact  text not null,
    source_sha256    text not null,
    provenance_class text not null default 'CURATED',
    loader_version   text not null,
    loaded_at        timestamptz not null default now(),

    -- v1 had no unique constraint here at all.
    constraint common_names_species_name_lang_key unique (species_id, name, language),
    constraint common_names_language_is_iso639_3 check (language ~ '^[a-z]{{3}}$'),
    constraint common_names_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

-- At most one main name per species. A partial unique index expresses this
-- exactly; a plain unique constraint could not, since is_main is false on most rows.
create unique index if not exists common_names_one_main_per_species
    on {schema}.common_names (species_id) where is_main;

create index if not exists common_names_language_idx on {schema}.common_names (language);
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

    seen = set()
    mains = defaultdict(int)
    out = []
    for row in rows:
        sci = (row["scientific_name"] or "").strip()
        name = (row["name"] or "").strip()
        lang = (row["language"] or "").strip()
        if not sci or not name:
            sys.exit(f"blank scientific_name or name in source: {row!r}")
        # The v1 defect: a language code from the wrong standard.
        if not ISO639_3.match(lang):
            sys.exit(f"language {lang!r} for {name!r} is not a three-letter ISO 639-3 code")
        key = (sci, name, lang)
        if key in seen:
            sys.exit(f"duplicate common name: {key}")
        seen.add(key)
        is_main = _bool(row["is_main"])
        if is_main:
            mains[sci] += 1
        out.append({
            "scientific_name": sci, "name": name, "language": lang, "is_main": is_main,
            "provenance_note": (row.get("provenance_note") or "").strip() or None,
        })

    for sci, count in mains.items():
        if count > 1:
            sys.exit(f"{sci} has {count} main names; exactly one is allowed")
    covered = {r["scientific_name"] for r in out}
    for sci in covered:
        if mains.get(sci, 0) != 1:
            sys.exit(f"{sci} has no main common name")
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

    languages = sorted({r["language"] for r in rows})
    normalised = sum(1 for r in rows if r["provenance_note"] and "normalised" in r["provenance_note"])
    print(f"source:    {artifact}")
    print(f"sha256:    {digest}")
    print(f"names:     {len(rows)} across {len(languages)} languages")
    print(f"codes normalised from ISO 639-1: {normalised}")

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
                    sys.exit(f"common names reference unknown species: {unknown}")

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
                cur.execute(f"delete from {schema}.common_names")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.common_names
                        (species_id, name, language, is_main, provenance_note,
                         source_artifact, source_sha256, provenance_class, loader_version)
                        values %s""",
                    [(species[r["scientific_name"]], r["name"], r["language"], r["is_main"],
                      r["provenance_note"], artifact, digest, "CURATED", LOADER_VERSION)
                     for r in rows],
                )
                cur.execute(f"select count(*) from {schema}.common_names")
                final = cur.fetchone()[0]
                cur.execute(f"""select count(*) from {schema}.species s
                    where not exists (select 1 from {schema}.common_names c where c.species_id = s.id)""")
                uncovered = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.species")
                total_species = cur.fetchone()[0]
    finally:
        conn.close()

    if final != len(rows):
        sys.exit(f"FAIL: loaded {final}, expected {len(rows)}")
    print(f"\nLOADED schema={schema} common_names={final}")
    # Report the gap every run. A silent gap is how 19 empty species survived v1.
    print(f"COVERAGE GAP: {uncovered} of {total_species} species have no common name "
          f"(not filled: would be unsourced. See module docstring.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
