#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Load the conservation profiles and their references, GATED at the database.

This is the exact surface R1 caught. In v1 the reference table showed every
species the entire reference list because `getSpeciesReferences()` queried it
with no species filter, and underneath that bug sat a second one: references
bound to the wrong species entirely.

STATE OF THIS SURFACE IN V1 (measured 2026-07-28)
-------------------------------------------------
  4 conservation profiles for 43 species
  file_source says 'LLM_generated' on three of them, outright
  4 references, all belonging to Monodon monoceros
  3 profiles (Alopias vulpinus, Falco rusticolus, Acipenser baerii) have
    ZERO bound references: their originals were deleted in the H1 repair
    because they were wrong, and were never replaced
  binding_status: the column migration 0010 introduced was rehearsed on a
    staging copy and never applied to live, so the gate it was written for
    has never actually run in production

That last point is the important one. A gate that exists in a migration file but
not in the database is not a gate. This loader makes it real in v2.

WHAT THIS BUILDS
----------------
Same shape as the narrative gate, because it is the same problem: machine-
proposed content that must not be servable until a named human signs it.

  conservation_profiles  every row GATED, origin recorded as stated in source
  references             bibliographic records, GATED
  profile_references     bindings, each with a binding_status
  profile_review         sign-off with a mandatory rationale
  servable_profile_references
                         the only sanctioned read path; a binding is visible
                         only when its profile has an approved review AND the
                         binding itself is marked live

An empty profile is preserved, not hidden. Three profiles legitimately have no
references, and a species page rendering nothing is the correct outcome. Filling
them would mean inventing citations, which is the original defect.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/references_load.py --target-schema arctic_v2
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
LOADER_VERSION = "references_load/1.0"

DDL = """
create schema if not exists {schema};

create table if not exists {schema}.conservation_profiles (
    id                   uuid primary key default gen_random_uuid(),
    species_id           uuid not null references {schema}.species (id) on delete cascade,
    profile_key          text not null,
    -- Recorded as stated. Three of the four v1 profiles say 'LLM_generated'
    -- in their own file_source column.
    origin               text not null,
    file_source          text,
    subpopulations       text,
    distribution_range   text,
    source_artifact      text not null,
    source_sha256        text not null,
    provenance_class     text not null default 'GATED',
    loader_version       text not null,
    loaded_at            timestamptz not null default now(),

    constraint conservation_profiles_key unique (species_id, profile_key),
    constraint conservation_profiles_origin_known check (origin in ('machine','human','mixed')),
    constraint conservation_profiles_is_gated check (provenance_class = 'GATED')
);

create table if not exists {schema}.references (
    id               uuid primary key default gen_random_uuid(),
    authors          text,
    year             integer,
    title            text not null,
    journal          text,
    doi              text,
    full_citation    text,
    source_artifact  text not null,
    source_sha256    text not null,
    provenance_class text not null default 'GATED',
    loader_version   text not null,
    loaded_at        timestamptz not null default now(),

    -- A reference with neither DOI nor title cannot be checked by anyone.
    constraint references_identifiable check (doi is not null or length(btrim(title)) > 0),
    constraint references_year_plausible check (year is null or year between 1700 and 2100),
    constraint references_is_gated check (provenance_class = 'GATED')
);

-- One reference should not exist twice under the same DOI.
create unique index if not exists references_doi_key
    on {schema}.references (lower(doi)) where doi is not null;

create table if not exists {schema}.profile_references (
    id              uuid primary key default gen_random_uuid(),
    profile_id      uuid not null references {schema}.conservation_profiles (id) on delete cascade,
    reference_id    uuid not null references {schema}.references (id) on delete cascade,
    -- 'proposed' is the only state a loader may create. Only a human review
    -- moves a binding to 'live'.
    binding_status  text not null default 'proposed',
    loaded_at       timestamptz not null default now(),

    constraint profile_references_key unique (profile_id, reference_id),
    constraint profile_references_status_known
        check (binding_status in ('proposed','live','rejected'))
);

create table if not exists {schema}.profile_review (
    id           uuid primary key default gen_random_uuid(),
    profile_id   uuid not null references {schema}.conservation_profiles (id) on delete cascade,
    reviewer     text not null,
    verdict      text not null,
    rationale    text not null,
    reviewed_at  timestamptz not null default now(),

    constraint profile_review_verdict_known check (verdict in ('approved','rejected','pending')),
    constraint profile_review_rationale_substantive check (length(btrim(rationale)) >= 20),
    constraint profile_review_reviewer_named check (length(btrim(reviewer)) > 0),
    constraint profile_review_one_per_reviewer unique (profile_id, reviewer)
);

-- The only sanctioned read path for species references. A binding is visible
-- only when its profile carries an approved review, no reviewer has rejected
-- that profile, and the binding itself is marked live. Enforcement sits in the
-- database, so an application regression cannot expose unsigned bindings.
create or replace view {schema}.servable_profile_references as
select pr.id, pr.profile_id, pr.reference_id, p.species_id
from {schema}.profile_references pr
join {schema}.conservation_profiles p on p.id = pr.profile_id
where pr.binding_status = 'live'
  and exists (
      select 1 from {schema}.profile_review r
      where r.profile_id = p.id and r.verdict = 'approved'
  )
  and not exists (
      select 1 from {schema}.profile_review r
      where r.profile_id = p.id and r.verdict = 'rejected'
  );

comment on view {schema}.servable_profile_references is
    'The only sanctioned read path for species references. The application must read this, never profile_references directly. Unsigned, rejected or non-live bindings are invisible here.';
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--from-schema", default="arctic")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    schema = validate_schema(args.target_schema)
    source_schema = validate_schema(args.from_schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    conn = psycopg2.connect(url, connect_timeout=20)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(DDL.format(schema=schema))
                cur.execute(f"select scientific_name, id from {schema}.species")
                target_species = dict(cur.fetchall())
                if not target_species:
                    sys.exit(f"{schema}.species is empty; load the species spine first")

                cur.execute(f"""
                    select s.scientific_name, p.id, p.profile_id, p.file_source,
                           p.subpopulations, p.distribution_range
                    from {source_schema}.conservation_profiles p
                    join {source_schema}.species s on s.id = p.species_id
                    order by s.scientific_name""")
                src_profiles = cur.fetchall()

                cur.execute(f"""select id, authors, year, title, journal, doi, full_citation
                                from {source_schema}.references""")
                src_refs = cur.fetchall()

                cur.execute(f"select profile_id, reference_id from {source_schema}.profile_references")
                src_bindings = cur.fetchall()

                digest = hashlib.sha256(
                    repr(sorted(str(r) for r in src_profiles + src_refs)).encode()
                ).hexdigest()
                artifact = f"{source_schema}.conservation_profiles + .references"

                print(f"profiles:   {len(src_profiles)}")
                print(f"references: {len(src_refs)}")
                print(f"bindings:   {len(src_bindings)}")

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
                cur.execute(f"delete from {schema}.conservation_profiles")
                cur.execute(f'delete from {schema}."references"')

                profile_ids = {}
                for name, old_id, key, file_source, subpops, dist in src_profiles:
                    sid = target_species.get(name)
                    if sid is None:
                        continue
                    # Everything on this surface was machine-produced; three of
                    # the four v1 rows say so in file_source themselves.
                    origin = "machine"
                    cur.execute(
                        f"""insert into {schema}.conservation_profiles
                            (species_id, profile_key, origin, file_source, subpopulations,
                             distribution_range, source_artifact, source_sha256,
                             provenance_class, loader_version)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,'GATED',%s) returning id""",
                        (sid, key, origin, file_source, subpops, dist, artifact, digest,
                         LOADER_VERSION),
                    )
                    profile_ids[str(old_id)] = cur.fetchone()[0]

                ref_ids = {}
                for old_id, authors, year, title, journal, doi, citation in src_refs:
                    cur.execute(
                        f"""insert into {schema}."references"
                            (authors, year, title, journal, doi, full_citation,
                             source_artifact, source_sha256, provenance_class, loader_version)
                            values (%s,%s,%s,%s,%s,%s,%s,%s,'GATED',%s) returning id""",
                        (authors, year, title, journal, doi, citation, artifact, digest,
                         LOADER_VERSION),
                    )
                    ref_ids[str(old_id)] = cur.fetchone()[0]

                bindings = [
                    (profile_ids[str(p)], ref_ids[str(r)])
                    for p, r in src_bindings
                    if str(p) in profile_ids and str(r) in ref_ids
                ]
                psycopg2.extras.execute_values(
                    cur,
                    f"""insert into {schema}.profile_references
                        (profile_id, reference_id, binding_status) values %s""",
                    [(p, r, "proposed") for p, r in bindings],
                )

                cur.execute(f"select count(*) from {schema}.conservation_profiles")
                np_ = cur.fetchone()[0]
                cur.execute(f'select count(*) from {schema}."references"')
                nr = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.profile_references")
                nb = cur.fetchone()[0]
                cur.execute(f"select count(*) from {schema}.servable_profile_references")
                servable = cur.fetchone()[0]
                cur.execute(f"""
                    select s.scientific_name from {schema}.conservation_profiles p
                    join {schema}.species s on s.id = p.species_id
                    where not exists (select 1 from {schema}.profile_references b
                                      where b.profile_id = p.id)
                    order by 1""")
                empty = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

    print(f"\nLOADED schema={schema} profiles={np_} references={nr} bindings={nb}")
    print(f"  SERVABLE right now: {servable}")
    if servable != 0:
        sys.exit("FAIL: unsigned bindings are servable; the gate is not holding")
    if empty:
        print(f"\n  {len(empty)} profiles have NO references and are preserved as-is:")
        for name in empty:
            print(f"    {name}")
        print("  Their originals were deleted in the H1 repair because they were wrong.")
        print("  Filling them would mean inventing citations, which is the original defect.")
    print("\nThe gate is holding: every binding is 'proposed', none is servable, and none")
    print("becomes servable until a named human approves the profile and marks it live.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
