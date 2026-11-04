#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Load the glossary and the illegal-trade product vocabulary into a target schema.

GLOSSARY: A DEAD COLUMN REMOVED
-------------------------------
`glossary_terms.examples` is NULL on all 72 rows. Like `catch_records.area`, it
is a column that was designed and never filled. It is dropped in v2 rather than
carried forward empty. Partially-populated columns are kept as-is because they
carry real data: acronym 34/72, subcategory 42/72, related_terms 20/72.

PRODUCT SEARCH TERMS: A DERIVED FIELD, DERIVED BADLY
----------------------------------------------------
`illegal_trade_products.search_terms` was stored as an array, but it is not
curated data: it is reproducible by splitting `product_name` and
`product_category` on whitespace, which matches exactly for 51 of 60 rows.

It was produced by a naive split that never stripped punctuation, so 52 of the
206 stored tokens (25%) are unusable for search:

    'dead animal' / 'dead (whole animal)'  ->  ['(whole', 'dead', 'animal', 'animal)']
    others: '(bone', 'bone-like)', '(raw)', 'carvings/products', 'carvings/engravings'

A token like 'animal)' can never match a user's query, so a quarter of the search
index was inert. This loader treats search_terms as DERIVED and regenerates it
with a documented tokenizer: casefold, split on any non-alphanumeric character,
drop tokens shorter than two characters, deduplicate, sort. Sorting matters
because it makes the array deterministic, so the same input always hashes the
same way and idempotency can be proven.

The tokenizer is deliberately dumb and reproducible rather than clever. Anything
smarter (stemming, synonyms) would be a judgement call that belongs in a curated
file, not in a load step.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/reference_tables_load.py --target-schema arctic_v2
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
GLOSSARY_SOURCE = ROOT / "species_data/curated/glossary_terms.csv"
PRODUCTS_SOURCE = ROOT / "species_data/curated/illegal_trade_products.csv"
LOADER_VERSION = "reference_tables_load/1.0"

# Split on anything that is not a letter or digit. This is what the v1 tokenizer
# should have done: it split on whitespace only, leaving brackets and slashes
# glued to the tokens.
_TOKEN_SPLIT = re.compile(r"[^0-9a-z]+")
MIN_TOKEN_LENGTH = 2

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.glossary_terms (
    id                uuid primary key default gen_random_uuid(),
    term              text not null,
    acronym           text,
    definition        text not null,
    category          text not null,
    subcategory       text,
    related_terms     text[],
    priority          integer not null,
    display_contexts  text[],
    source_artifact   text not null,
    source_sha256     text not null,
    provenance_class  text not null default 'CURATED',
    loader_version    text not null,
    loaded_at         timestamptz not null default now(),

    constraint glossary_terms_term_key unique (term),
    constraint glossary_terms_priority_range check (priority between 1 and 10),
    constraint glossary_terms_definition_substantive check (length(definition) >= 20),
    constraint glossary_terms_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

create table if not exists {schema}.illegal_trade_products (
    id                uuid primary key default gen_random_uuid(),
    product_code      text not null,
    product_name      text not null,
    product_category  text not null,
    main_category     text not null,
    is_high_value     boolean not null,
    -- DERIVED from product_name + product_category by this loader's tokenizer.
    -- Never hand-edited: regenerating it must always give the same array.
    search_terms      text[] not null,
    source_artifact   text not null,
    source_sha256     text not null,
    provenance_class  text not null default 'CURATED',
    loader_version    text not null,
    loaded_at         timestamptz not null default now(),

    constraint illegal_trade_products_code_key unique (product_code),
    constraint illegal_trade_products_search_terms_nonempty check (cardinality(search_terms) > 0),
    constraint illegal_trade_products_provenance_class check (provenance_class in ('DERIVED','CURATED','GATED'))
);

create index if not exists illegal_trade_products_search_idx
    on {schema}.illegal_trade_products using gin (search_terms);
"""


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def tokenize(*parts: str) -> list[str]:
    """Derive search tokens from free text.

    Deterministic by construction: casefold, split on non-alphanumerics, drop
    tokens under MIN_TOKEN_LENGTH, deduplicate, sort. The sort is what makes the
    output stable across runs, which is what lets idempotency be proven rather
    than assumed.
    """
    tokens = set()
    for part in parts:
        for token in _TOKEN_SPLIT.split((part or "").casefold()):
            if len(token) >= MIN_TOKEN_LENGTH:
                tokens.add(token)
    return sorted(tokens)


def _bool(value) -> bool:
    return str(value).strip().lower() in {"true", "t", "1", "yes"}


def _array(value: str) -> list[str] | None:
    value = (value or "").strip()
    return [p for p in value.split("|") if p] if value else None


def read_glossary(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    seen = set()
    out = []
    for row in rows:
        term = (row["term"] or "").strip()
        definition = (row["definition"] or "").strip()
        if not term:
            sys.exit("blank term in glossary source")
        if len(definition) < 20:
            sys.exit(f"definition for {term!r} is too short to be substantive")
        if term in seen:
            sys.exit(f"duplicate glossary term: {term!r}")
        seen.add(term)
        try:
            priority = int(row["priority"])
        except (TypeError, ValueError):
            sys.exit(f"invalid priority for {term!r}: {row['priority']!r}")
        if not 1 <= priority <= 10:
            sys.exit(f"priority {priority} for {term!r} is outside 1-10")
        out.append({
            "term": term,
            "acronym": (row.get("acronym") or "").strip() or None,
            "definition": definition,
            "category": (row["category"] or "").strip(),
            "subcategory": (row.get("subcategory") or "").strip() or None,
            "related_terms": _array(row.get("related_terms", "")),
            "priority": priority,
            "display_contexts": _array(row.get("display_contexts", "")),
        })
    return out


def read_products(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"{path} is empty")
    seen = set()
    out = []
    for row in rows:
        code = (row["product_code"] or "").strip()
        name = (row["product_name"] or "").strip()
        category = (row["product_category"] or "").strip()
        if not code or not name or not category:
            sys.exit(f"blank product_code, product_name or product_category: {row!r}")
        if code in seen:
            sys.exit(f"duplicate product_code: {code!r}")
        seen.add(code)
        search_terms = tokenize(name, category)
        if not search_terms:
            sys.exit(f"product {code!r} yields no usable search tokens")
        out.append({
            "product_code": code, "product_name": name, "product_category": category,
            "main_category": (row["main_category"] or "").strip(),
            "is_high_value": _bool(row["is_high_value"]),
            "search_terms": search_terms,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    glossary = read_glossary(GLOSSARY_SOURCE)
    products = read_products(PRODUCTS_SOURCE)
    gdigest, pdigest = sha256_of(GLOSSARY_SOURCE), sha256_of(PRODUCTS_SOURCE)
    gartifact = str(GLOSSARY_SOURCE.relative_to(ROOT))
    partifact = str(PRODUCTS_SOURCE.relative_to(ROOT))

    all_tokens = {t for p in products for t in p["search_terms"]}
    dirty = [t for t in all_tokens if not t.isalnum()]
    print(f"glossary_terms:         {len(glossary)} (v1 `examples` column dropped, 0/72 populated)")
    print(f"illegal_trade_products: {len(products)}")
    print(f"search tokens derived:  {len(all_tokens)} distinct, "
          f"{len(dirty)} containing non-alphanumerics (v1 had 52 of 206)")

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
                cur.execute(f"delete from {schema}.glossary_terms")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.glossary_terms
                        (term, acronym, definition, category, subcategory, related_terms,
                         priority, display_contexts, source_artifact, source_sha256,
                         provenance_class, loader_version) values %s""",
                    [(r["term"], r["acronym"], r["definition"], r["category"], r["subcategory"],
                      r["related_terms"], r["priority"], r["display_contexts"],
                      gartifact, gdigest, "CURATED", LOADER_VERSION) for r in glossary],
                )
                cur.execute(f"delete from {schema}.illegal_trade_products")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.illegal_trade_products
                        (product_code, product_name, product_category, main_category,
                         is_high_value, search_terms, source_artifact, source_sha256,
                         provenance_class, loader_version) values %s""",
                    [(r["product_code"], r["product_name"], r["product_category"],
                      r["main_category"], r["is_high_value"], r["search_terms"],
                      partifact, pdigest, "CURATED", LOADER_VERSION) for r in products],
                )
                cur.execute(f"select count(*) from {schema}.glossary_terms")
                ng = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.illegal_trade_products")
                np_ = cur.fetchone()[0]
    finally:
        conn.close()

    if ng != len(glossary) or np_ != len(products):
        sys.exit(f"FAIL: loaded {ng}/{np_}, expected {len(glossary)}/{len(products)}")
    print(f"\nLOADED schema={schema} glossary_terms={ng} illegal_trade_products={np_}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
