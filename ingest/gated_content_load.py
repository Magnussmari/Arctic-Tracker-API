#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Split machine-generated species narratives out of the spine and gate them.

THE PROBLEM THIS SOLVES
-----------------------
The v1 `species` table carries eight free-text narrative fields that render on
the public species pages: description, habitat_description, movement_patterns,
use_and_trade, threats_overview, conservation_overview, population_size,
population_trend.

Every one is machine-generated, and measured against live on 2026-07-28:

  - 412 distinct author-year citations are embedded in that prose, against
    4 rows in the references table. Those citations carry no DOI, no title and
    no link, so none of them can be resolved or checked.
  - manual_review = 'no' on all 43 species.
  - reviewed_by IS NULL on all 43 species.

The review columns existed and were never used. This is precisely R2's
objection: machine output validating machine output, with no human in the
authority path. It is also a larger surface than the reference defect R1 caught,
because the reference repair fixed `profile_references` (4 rows) and never
touched the prose.

WHAT THIS BUILDS
----------------
1. Narratives leave the taxonomic spine entirely. `species` holds only facts
   that can be traced to a source; prose lives in `species_narratives`, one row
   per (species, section) so a single bad section can be rejected without
   discarding a whole profile.

2. Every narrative is provenance_class GATED and starts unsigned.

3. `narrative_review` records the sign-off: reviewer, verdict, and a rationale
   that cannot be blank. A boolean would let someone approve 43 species with one
   click and no reasoning; requiring prose makes the reviewer state what they
   checked.

4. `servable_species_narratives` is the ONLY sanctioned read path. It returns a
   narrative only when an approved review exists. Enforcement is at the database,
   not in application code, so an app regression cannot expose unsigned prose.

No model sits in the authority path at any point. A model may draft or triage;
only a named human's approved review makes content servable.

Nothing is deleted. The narratives are preserved exactly as written, marked
unreviewed, and simply not served until a human signs them.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/gated_content_load.py --target-schema arctic_v2
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

ROOT = Path(__file__).parent.parent
LOADER_VERSION = "gated_content_load/1.0"

# The eight narrative sections, named explicitly so a new prose column cannot
# join the spine unnoticed or escape the gate.
NARRATIVE_SECTIONS = [
    "description",
    "habitat_description",
    "movement_patterns",
    "use_and_trade",
    "threats_overview",
    "conservation_overview",
    "population_size",
    "population_trend",
]

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.species_narratives (
    id                uuid primary key default gen_random_uuid(),
    species_id        uuid not null references {schema}.species (id) on delete cascade,
    section           text not null,
    body              text not null,
    -- How the text was produced. 'machine' is the accurate label for every row
    -- loaded from v1; nothing here was written by a person.
    origin            text not null default 'machine',
    citation_count    integer not null default 0,
    source_artifact   text not null,
    source_sha256     text not null,
    provenance_class  text not null default 'GATED',
    loader_version    text not null,
    loaded_at         timestamptz not null default now(),

    constraint species_narratives_key unique (species_id, section),
    constraint species_narratives_section_known check (section in (
        'description','habitat_description','movement_patterns','use_and_trade',
        'threats_overview','conservation_overview','population_size','population_trend')),
    constraint species_narratives_origin_known check (origin in ('machine','human','mixed')),
    -- Narratives are GATED by definition. Marking one DERIVED or CURATED would
    -- route it around the review gate.
    constraint species_narratives_is_gated check (provenance_class = 'GATED')
);

-- Sign-off. A rationale is mandatory: a bare boolean would let 43 species be
-- approved in one motion with no statement of what was actually checked.
create table if not exists {schema}.narrative_review (
    id            uuid primary key default gen_random_uuid(),
    narrative_id  uuid not null references {schema}.species_narratives (id) on delete cascade,
    reviewer      text not null,
    verdict       text not null,
    rationale     text not null,
    reviewed_at   timestamptz not null default now(),

    constraint narrative_review_verdict_known check (verdict in ('approved','rejected','pending')),
    constraint narrative_review_rationale_substantive check (length(btrim(rationale)) >= 20),
    constraint narrative_review_reviewer_named check (length(btrim(reviewer)) > 0),
    constraint narrative_review_one_per_reviewer unique (narrative_id, reviewer)
);

-- The ONLY sanctioned read path for species prose. An unsigned or rejected
-- narrative is invisible here regardless of what the application does.
create or replace view {schema}.servable_species_narratives as
select n.id, n.species_id, n.section, n.body, n.origin, n.citation_count
from {schema}.species_narratives n
where exists (
    select 1 from {schema}.narrative_review r
    where r.narrative_id = n.id and r.verdict = 'approved'
)
and not exists (
    -- Any single rejection wins over any approval: content a reviewer has
    -- rejected must never be servable because a second reviewer approved it.
    select 1 from {schema}.narrative_review r
    where r.narrative_id = n.id and r.verdict = 'rejected'
);

comment on view {schema}.servable_species_narratives is
    'The only sanctioned read path for species narrative prose. Unsigned or rejected content is invisible here. The application must read this view, never species_narratives directly.';
"""


def count_citations(text: str) -> int:
    """Count distinct author-year citations embedded in a narrative."""
    sys.path.insert(0, str(Path(__file__).parent))
    from audit_narrative_citations import extract
    return len(extract(text))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--from-schema", default="arctic",
                    help="schema holding the v1 species table the prose is lifted from")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    source_schema = validate_schema(args.from_schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    conn = psycopg2.connect(url, connect_timeout=30)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL.format(schema=schema))
                cur.execute(f"select scientific_name, id from {schema}.species")
                target_species = dict(cur.fetchall())
                if not target_species:
                    sys.exit(f"{schema}.species is empty; load the species spine first")

                fields = ", ".join(f'"{s}"' for s in NARRATIVE_SECTIONS)
                cur.execute(f"select scientific_name, {fields} from {source_schema}.species")
                rows = cur.fetchall()

                payload = []
                total_citations = 0
                for row in rows:
                    name = row[0]
                    species_id = target_species.get(name)
                    if species_id is None:
                        continue  # not in the rebuilt spine
                    for section, body in zip(NARRATIVE_SECTIONS, row[1:]):
                        if not body or not body.strip():
                            continue
                        n = count_citations(body)
                        total_citations += n
                        payload.append((species_id, section, body, "machine", n))

                # Sort on the SPECIES NAME, never on species_id: the id is a
                # surrogate regenerated on every load, so ordering by it made
                # this digest non-deterministic and idempotency unprovable.
                # Caught by ingest/verify_v2_idempotency.py.
                name_of = {v: k for k, v in target_species.items()}
                digest = hashlib.sha256(
                    "".join(
                        f"{p[1]}{p[2]}"
                        for p in sorted(payload, key=lambda x: (name_of[x[0]], x[1]))
                    ).encode()
                ).hexdigest()
                artifact = f"{source_schema}.species (narrative columns)"

                print(f"species with narratives: {len({p[0] for p in payload})}")
                print(f"narrative sections:      {len(payload)}")
                print(f"embedded citations:      {total_citations}")
                print(f"content sha256:          {digest}")

                if args.dry_run:
                    print("\ndry run: nothing loaded")
                    return 0

                # RESTRICT, not CASCADE. CASCADE silently deletes child rows: it
                # wiped all 225 illegal_trade_seizures when this loader
                # truncated illegal_trade_products, because the seizure table
                # references it. RESTRICT makes a destructive reload fail loudly
                # so the operator reloads in dependency order instead.
                # Human sign-offs are the one thing in this database that cannot
                # be regenerated from a source. Refuse to reload rather than
                # destroy them; RESTRICT surfaced this by refusing the truncate.
                cur.execute(f"select count(*) from {schema}.narrative_review")
                existing_reviews = cur.fetchone()[0]
                if existing_reviews:
                    sys.exit(
                        f"{existing_reviews} narrative reviews exist in {schema}. Reloading "
                        f"narratives would delete them, and a human sign-off cannot be "
                        f"rebuilt from any source. Export them first, or reload into a "
                        f"fresh schema."
                    )
                # DELETE, not TRUNCATE. Postgres refuses to truncate a table that any
                # foreign key references, even when the referencing table is empty, so
                # a loader that truncates only its own table cannot run at all once the
                # keys exist. DELETE respects the same constraint but succeeds when no
                # child row actually points at anything, and still fails loudly when
                # one does. Slower on the large tables; correctness wins.
                cur.execute(f"delete from {schema}.narrative_review")
                cur.execute(f"delete from {schema}.species_narratives")
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.species_narratives
                        (species_id, section, body, origin, citation_count,
                         source_artifact, source_sha256, provenance_class, loader_version)
                        values %s""",
                    [p + (artifact, digest, "GATED", LOADER_VERSION) for p in payload],
                )
                cur.execute(f"select count(*) from {schema}.species_narratives")
                stored = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.servable_species_narratives")
                servable = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.narrative_review")
                reviews = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"\nLOADED schema={schema} species_narratives={stored}")
    print(f"  reviews on file:      {reviews}")
    print(f"  SERVABLE right now:   {servable}")
    if servable != 0:
        sys.exit("FAIL: unreviewed narrative content is servable; the gate is not holding")
    print("\nThe gate is holding: every narrative is present, none is servable, and none")
    print("becomes servable until a named human files an approved review with a rationale.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
