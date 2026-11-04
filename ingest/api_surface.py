#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-29
"""Define the application's read surface as a schema of views, and lock it down.

WHY THE READ CONTRACT BELONGS IN THE DATABASE
---------------------------------------------
Two of the defects this rebuild exists to answer were application-layer
failures. `getSpeciesReferences()` queried the references table with no species
filter and every species page showed every reference (R1 found that one). The
review gate that should have prevented unsigned prose from being served was
written as a migration and never applied.

Both share a shape: the guarantee lived in code that could regress, or in a
migration that could go unrun. So the guarantees here are not in the app.

`arctic_api` is a schema containing only views. `arctic_app`, the role the
application connects as, is granted SELECT on that schema and NOTHING on
`arctic_v2`. It therefore cannot read a base table even if someone writes the
query, cannot see unsigned narrative or unsigned reference bindings, and cannot
compute a cross-unit quantity total, because no view offers one.

THREE PROPERTIES THIS ENFORCES
------------------------------
1. **Unsigned content is unreachable.** The narrative and reference views select
   from `servable_species_narratives` and `servable_profile_references`, which
   already require an approved human review with no rejection. The app has no
   path to the underlying tables.

2. **References are always species-scoped.** `species_reference` carries
   `species_id` and cannot be selected without it. The R1 bug, a reference query
   with no species filter, returns nothing useful here rather than everything.

3. **No view exposes a cross-unit quantity total.** `species_trade_summary`
   reports per dimension (mass in kg, counts in specimens, and so on) with the
   row count behind each. There is deliberately no `total_quantity` column
   anywhere in this schema, because summing kilograms and animals produces a
   number with no unit. That is the figure 8 defect, made unrepresentable.

Usage:
  ARCTIC_DATABASE_URL=... python ingest/api_surface.py --target-schema arctic_v2
"""
import argparse
import os
import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent))
from db import validate_schema  # noqa: E402
from units import sql_dimension, sql_normalized_quantity  # noqa: E402

# Roles granted the read surface. The schema is dropped and recreated on every
# run, so any role missing here silently loses access at the next rebuild.
#
# arctic_v2_app is the v2 application's role and holds arctic_api and nothing
# else. arctic_app is the LIVE site's role: it also holds RW on schema `arctic`
# and SELECT on all 27 of its base tables, which is why it is NOT the role the
# v2 app connects as. It is kept here only so the live surface can be repointed
# without a grant change at cutover.
APP_ROLES = ("arctic_v2_app", "arctic_app")
APP_ROLE = APP_ROLES[0]

# The read contract, named. This schema is dropped and recreated on every run, so
# a view accidentally deleted from the DDL would otherwise vanish from the app's
# surface with a green exit code. Naming the expected set turns that into a
# failure. Adding a view here without adding it to the DDL fails the same way.
EXPECTED_VIEWS = {
    "species",
    "glossary_term",
    "species_catch",
    "species_cms_listing",
    "species_iucn",
    "species_listing",
    "species_narrative",
    "species_pending_review",
    "species_reference",
    "species_seizure",
    "species_split_listing",
    "species_subpopulation",
    "species_timeline",
    "species_media",
    "species_listing_event",
    "species_trade_summary",
    "trade_flow",
}

DDL = """
drop schema if exists {api} cascade;
create schema {api};

-- Taxonomic spine plus the one common name flagged as primary. Facts only:
-- every column here traces to a source or a named curator.
create view {api}.species as
select s.id, s.scientific_name, s.common_name, s.kingdom, s.phylum, s.class,
       s.order_name, s.family, s.genus, s.authority, s.sis_id, s.is_arctic,
       s.cites_reported_name, s.divergence_from_cites,
       -- LIMIT 1 with an explicit ORDER BY. The unordered version was the same
       -- nondeterminism this schema condemns elsewhere: it happens to be safe
       -- today because exactly one row per species carries is_main and all 24
       -- are English, but "happens to be safe" is what every other defect here
       -- had in common. 19 of 43 species have no common_names row at all, so
       -- this is NULL for them and `common_name` on the species row is the
       -- fallback a page should use.
       (select cn.name from {v2}.common_names cn
         where cn.species_id = s.id and cn.is_main
         order by cn.language, cn.name limit 1) as primary_common_name
from {v2}.species s;

-- Narrative prose. Sourced from the servable view, so unsigned or rejected
-- content cannot appear here by construction.
create view {api}.species_narrative as
select n.species_id, n.section, n.body, n.origin, n.citation_count
from {v2}.servable_species_narratives n;

-- References, always carrying their species. A query that forgets to filter by
-- species gets rows it cannot attribute, not every reference in the database.
create view {api}.species_reference as
select spr.species_id, r.id as reference_id, r.authors, r.year, r.title,
       r.journal, r.doi, r.full_citation
from {v2}.servable_profile_references spr
join {v2}."references" r on r.id = spr.reference_id;

-- Trade, reported PER DIMENSION and PER REPORTER SIDE.
--
-- Two separate reasons a naive total is wrong here, and the second one was my
-- own mistake in the first version of this view.
--
-- 1. UNITS. There is no total_quantity column in this schema and that is
--    deliberate: a sum across kilograms, litres and individual animals has no
--    unit and cannot be labelled with one. That is the figure 8 defect.
--
-- 2. TERM. A blank unit in CITES means "a count of the term", and the terms are
--    not the same thing. The blank-unit rows here include 88,284 live animals,
--    39,482 skins, 25,450 carvings, 12,575 trophies and 11,797 tusks. Summing
--    them into one "specimens" figure is the unit defect one axis over, and an
--    earlier version of this view did exactly that by omitting term from the
--    GROUP BY. 73 distinct terms are present.
--
-- 3. REPORTER SIDE. The CITES Trade Database records a shipment from both ends.
--    An importer-reported row and an exporter-reported row are two accounts of
--    the same trade, not two trades. 23,092 shipment coordinate groups here
--    (same species, year, importer, exporter, term, unit, purpose, source and
--    quantity) appear under both reporter types. Summing across the column
--    double counts every one of them.
--
--    The first version of this view grouped by species, source and dimension
--    only, and therefore did exactly that. It is the same class of error as the
--    unit sum: adding two things that are not additive because the column
--    separating them was not in the GROUP BY.
--
-- THE UNIT TAXONOMY IS GENERATED, NOT RETYPED. The dimension and conversion
-- expressions come from units.py via sql_dimension() and
-- sql_normalized_quantity(), which are built from the same UNIT_TABLE the
-- Python loaders use and which 22 tests cover. An earlier version of this view
-- hand-rolled a parallel CASE with an `else 'packaging_containers'` catch-all,
-- so any unit the list forgot was summed at factor 1: 'sets', 'pairs',
-- 'shipments', 'bottles' and 'cartons' were being added together, and the
-- observed misspelling 'microgrames' would have been counted as a container
-- rather than as 1e-9 kg. Two disagreeing taxonomies with only the unused one
-- tested is worse than one, so there is now one.
--
-- Unrecognised units land in dimension 'unknown' with a NULL converted value,
-- which makes a missed unit visible as a NULL rather than as a wrong total.
-- `unconvertible_records` counts them per group.
--
-- Which side to prefer is a methodological choice, not a database one.
-- Reviewer 3 asked for that choice to be stated, and the manuscript carries it
-- as an open item. This view therefore takes no position: it reports both sides
-- separately so either convention can be computed, and makes the sum of them
-- unavailable. A caller must name a reporter side exactly as it must name a
-- dimension.
create view {api}.species_trade_summary as
select t.species_id,
       t.source,
       t.reporter_type,
       t.term,
       {dimension_sql} as dimension,
       sum({normalized_sql}) as total_in_canonical_unit,
       count(*) as record_count,
       count(*) filter (where {dimension_sql} = 'unknown') as unconvertible_records,
       min(t.year) as first_year,
       max(t.year) as last_year
from {v2}.cites_trade_records t
group by t.species_id, t.source, t.reporter_type, t.term, 5;

comment on view {api}.species_trade_summary is
    'Trade per species, source, reporter side, TERM and unit dimension. Never sum across reporter_type (two accounts of one shipment) nor across term (a live animal is not a carving) nor across dimension.';

-- Trade as a flow between countries, which the read surface could not express.
--
-- Found 2026-07-30 by a graph-architecture study: NO view in this schema exposed
-- `importer` or `exporter`. The application could render a species' trade totals
-- but could not answer "who traded with whom", and the manuscript makes
-- trade-network claims. That is a reproducibility gap of exactly the kind R3
-- raised, and it existed because the aggregate views were designed around the
-- species page rather than around the paper's claims.
--
-- The same non-additivity rules apply here as everywhere else, and for the same
-- reasons. A flow is keyed by species, the two countries, year, term, unit
-- dimension, purpose, source AND reporter side. None of those may be summed
-- across:
--   two countries      because a flow is directional
--   term               because a live animal is not a carving
--   dimension          because kilograms and animals have no common unit
--   reporter side      because an importer report and an exporter report are two
--                      accounts of one shipment, not two shipments
--
-- `origin` is carried separately from `exporter` because they differ precisely
-- in the re-export case, which is the only case where the distinction matters.
create view {api}.trade_flow as
select t.species_id,
       t.exporter,
       t.importer,
       nullif(t.origin, '') as origin,
       t.origin is not null and t.origin <> '' and t.origin <> t.exporter
         as is_reexport,
       t.year,
       t.term,
       t.purpose,
       t.source,
       t.reporter_type,
       {dimension_sql} as dimension,
       sum({normalized_sql}) as total_in_canonical_unit,
       count(*) as record_count
from {v2}.cites_trade_records t
where t.exporter is not null and t.exporter <> ''
  and t.importer is not null and t.importer <> ''
group by t.species_id, t.exporter, t.importer, 4, 5, t.year, t.term,
         t.purpose, t.source, t.reporter_type, 11;

comment on view {api}.trade_flow is
    'Directional country-to-country trade, keyed by species, year, term, dimension, purpose, source and reporter side. is_reexport marks rows whose origin differs from the exporter. Never sum across countries, term, dimension or reporter side.';

-- CITES listings. `is_current` does not identify a single listing, and code
-- that assumes it does gets a nondeterministic answer.
--
-- Eight species carry more than one row flagged `is_current`, and for all eight
-- EVERY row is flagged: the flag does not discriminate at all. The rows are the
-- same decision recorded at different amendment dates, with annotations such as
-- 'All stocks.' or a reservation note. Across those eight the appendix is
-- constant, but their DATES are not, and for five they span more than a decade:
-- Falco peregrinus 1977 to 2004, Megaptera novaeangliae 1975 to 2000,
-- Physeter macrocephalus 1981 to 2004.
--
-- The appendix is NOT constant in general. Balaenoptera acutorostrata is a
-- genuine CITES split listing: Appendix I except the West Greenland population,
-- which is Appendix II. Its only row flagged current is the 2004 Appendix I
-- entry carrying no annotation, so anything reading the current row alone
-- reports the minke whale as Appendix I and silently drops the West Greenland
-- qualification. That qualification is load-bearing in this dataset, which also
-- holds NAMMCO West Greenland catch records.
--
-- The live application selects with `.find(l => l.is_current)`, which takes
-- whichever row the database returned first under no ORDER BY. The listing year
-- it displays for those species is therefore not stable across queries.
--
-- `first_listed_on` is the earliest listing date for the species and is the
-- answer to "when was this listed". Later rows amend a listing that already
-- existed; they do not start a new one. Any observation window measured from
-- listing must use this column, never an arbitrary current row.
create view {api}.species_listing as
select l.species_id, l.appendix, l.listing_date, l.is_current, l.notes,
       min(l.listing_date) over (partition by l.species_id) as first_listed_on,
       -- Exactly one row per species, deterministically. Four species record
       -- several rows on the same earliest date (Balaenoptera physalus has three
       -- dated 1981-06-06, differing only in annotation), so ordering by date
       -- alone still leaves the choice to the query plan. The annotation and
       -- appendix break the tie, which makes the selection stable rather than
       -- meaningful: the DATE is the fact, and it is identical across the tied
       -- rows either way.
       row_number() over (
         partition by l.species_id
         order by l.listing_date, coalesce(l.notes, ''), l.appendix
       ) = 1 as is_first_listing,
       count(*) over (partition by l.species_id) as listing_row_count
from {v2}.cites_listings l;

comment on view {api}.species_listing is
    'CITES listings. is_current is flagged on every row for 8 species and cannot select one; use first_listed_on for the date a species was listed.';

-- CMS and its daughter agreements, which are not the same thing.
--
-- One table holds two kinds of row. 43 rows are listings under the Convention
-- itself and carry a CMS appendix. 49 rows are memberships of daughter
-- agreements (ACCOBAMS, ASCOBANS, AEWA, Raptors, Sharks, ACAP and others) and
-- carry no appendix, because those instruments have their own annexes and do
-- not use the CMS appendices at all.
--
-- The split is exact: every agreement='CMS' row has an appendix and no other
-- row does. So `is_cms_proper` is a reliable discriminator, not a guess.
--
-- Why this needs saying: the live application selects the current CMS listing
-- as `cmsListings[0]`, with no filter on agreement and no ORDER BY. 27 of the
-- 37 species with any CMS row have more than one, so for most of them the page
-- can show an ACCOBAMS or ASCOBANS membership labelled as the CMS listing, with
-- a null appendix, depending on row order. Four species have only daughter
-- agreement rows and no CMS listing at all, and for those the correct statement
-- is that the species is not CMS-listed but is covered by an agreement.
--
-- Whether the daughter agreements belong in the analysis is an open question
-- for the authors. This view takes no position: it labels them and exposes
-- both.
create view {api}.species_cms_listing as
select l.species_id, l.agreement, l.appendix, l.listing_date, l.listed_under,
       l.notes, l.native_distribution, l.distribution_codes,
       l.agreement = 'CMS' as is_cms_proper
from {v2}.cms_listings l;

comment on view {api}.species_cms_listing is
    'CMS listings and daughter-agreement memberships in one table, discriminated by is_cms_proper. Only CMS-proper rows carry an appendix; a daughter agreement is not a CMS listing.';

-- Glossary, 72 curated terms behind the /glossary route.
create view {api}.glossary_term as
select g.term, g.acronym, g.definition, g.category, g.subcategory,
       g.related_terms, g.display_contexts
from {v2}.glossary_terms g;

-- Split listings: where a species is listed differently by population.
--
-- This table holds the record that `cites_listings.is_current` destroys. For
-- Balaenoptera acutorostrata it carries both halves of the split explicitly,
-- 'Main Population' in Appendix I and 'West Greenland Stock' in Appendix II,
-- where the current-flagged row in cites_listings is the Appendix I entry with
-- its annotation stripped.
--
-- So a species page that renders this view is telling the truth about the minke
-- whale, and one that renders only the current listing is not. The corrected
-- record already existed; it was simply never exposed to the application.
create view {api}.species_split_listing as
select sl.species_id, sl.population_identifier, sl.appendix, sl.listing_date,
       sl.delisting_date, sl.is_current, sl.notes, sl.annotation
from {v2}.split_listings sl;

comment on view {api}.species_split_listing is
    'Populations of one species listed under different appendices. Renders the split that a single current-flagged cites_listings row cannot express.';

-- Named subpopulations assessed separately by the IUCN.
--
-- Twelve subpopulations across six species. They matter for the same reason
-- assessment scope matters: Balaenoptera physalus has a Mediterranean
-- subpopulation assessed in its own right, and a page that shows one status for
-- the species is not describing that subpopulation. Exposed so the page can say
-- a species is assessed at more than one level rather than implying a single
-- verdict.
create view {api}.species_subpopulation as
select sp.species_id, sp.subpopulation_name, sp.sis_id, sp.authority
from {v2}.subpopulations sp;

-- Timeline events, with their corroboration status made explicit.
--
-- All 520 events come from one curated CSV. Three of the five event types can
-- be cross-checked against a table in this database and do check out:
-- cites_listing 59/59, cites_trade 52/52, iucn_assessment 342/343.
--
-- The other two cannot. 57 `cites_suspension` and 9 `eu_decision` events have
-- NO corresponding table here, so they rest entirely on the curator. That is a
-- legitimate provenance class (CURATED) and not a defect, but serving them
-- beside corroborated events with no visible difference would be exactly the
-- failure this rebuild exists to correct: presenting claims of unequal standing
-- as though they were equal.
--
-- `is_corroborated` lets a page say which is which. It is computed rather than
-- stored, so it cannot go stale against the tables it checks.
create view {api}.species_timeline as
select e.species_id, e.event_date, e.year, e.event_type, e.title,
       e.description, e.status,
       e.event_type in ('cites_listing', 'cites_trade', 'iucn_assessment')
         as is_corroborated,
       case e.event_type
         when 'cites_listing'   then 'cites_listings'
         when 'cites_trade'     then 'cites_trade_records'
         when 'iucn_assessment' then 'iucn_assessments'
         else null
       end as corroborating_table
from {v2}.timeline_events e;

comment on view {api}.species_timeline is
    'Curated timeline events. 66 of 520 (cites_suspension, eu_decision) have no corroborating table in this database and are flagged is_corroborated = false.';

-- Counts of content withheld pending review.
--
-- The app cannot read unsigned narratives or bindings, and must not be able to.
-- But a page that simply renders nothing misleads in a different way: the
-- reader cannot tell an absence of evidence from evidence withheld.
--
-- This view exposes COUNTS ONLY, never the withheld text. A page can then say
-- "8 sections await expert review" instead of showing a blank, which is the
-- accurate statement and is exactly what R1 and R2 were asking for: visible
-- provenance rather than silent confidence.
create view {api}.species_pending_review as
select s.id as species_id,
       (select count(*) from {v2}.species_narratives n
         where n.species_id = s.id
           and not exists (select 1 from {v2}.narrative_review r
                            where r.narrative_id = n.id and r.verdict = 'approved'))
         as narratives_pending,
       (select count(*) from {v2}.profile_references pr
          join {v2}.conservation_profiles p on p.id = pr.profile_id
         where p.species_id = s.id and pr.binding_status <> 'live')
         as references_pending,
       (select count(*) from {v2}.conservation_profiles p
         where p.species_id = s.id) as profiles_total
from {v2}.species s;

comment on view {api}.species_pending_review is
    'Counts of content withheld pending human review. Exposes counts only, never the withheld text, so a page can disclose an absence honestly without leaking unreviewed material.';

create view {api}.species_catch as
select c.species_id, c.year, c.area, c.catch_total, c.quota, c.data_source
from {v2}.catch_records c;

-- IUCN Red List assessments, full history rather than the current status alone.
--
-- THE INHERITED `is_latest` FLAG IS NOT SCOPE-AWARE, AND THAT IS A DEFECT.
--
-- An assessment has a scope: global, or a region. `scope_code` is null for a
-- global assessment. 62 species-and-scope combinations exist across the 43
-- species, because 19 species carry a European regional assessment in addition
-- to their global one.
--
-- A 2025-09-08 migration (not part of the public release) was
-- written to flag the newest assessment PER SPECIES PER SCOPE, which would set
-- the flag on 62 rows. Only 43 rows carry it: one per species, newest year
-- wins, scope ignored. The migration was never applied. This is the second
-- instance of the same failure mode as the reference gate, which was also
-- written as a migration, rehearsed, and never run.
--
-- The consequence is not cosmetic. The European assessments are dated 2023 and
-- the global ones mostly 2018, so for 17 species the newest-wins rule flags the
-- REGIONAL row and leaves the global assessment with no flag at all. Every
-- query filtering `is_latest = true` therefore reads a European regional status
-- as though it were the species status. For 9 of those 17 the two differ, in
-- both directions: for some species the regional category is less severe
-- than the global one, for others more severe (up to Regionally Extinct).
--
-- `is_latest` is exposed unchanged, because the loader replays the source
-- faithfully and rewriting it here would hide the defect rather than fix it.
-- `is_latest_in_scope` is computed, and is the column a page should use, having
-- first chosen a scope. Choosing a scope is not optional: there is no such
-- thing as "the" IUCN status for a species assessed at two scopes.
create view {api}.species_iucn as
select a.species_id, a.assessment_id, a.status, a.year_published,
       a.is_latest,
       row_number() over (
         partition by a.species_id, coalesce(a.scope_code, '1')
         order by a.year_published desc, a.assessment_id desc
       ) = 1 as is_latest_in_scope,
       a.possibly_extinct, a.possibly_extinct_in_wild, a.url,
       a.scope_code,
       coalesce(a.scope_description, 'Global') as scope_description,
       a.scope_code is null as is_global
from {v2}.iucn_assessments a;

comment on view {api}.species_iucn is
    'IUCN assessment history. The inherited is_latest flag is not scope-aware and flags a European regional assessment for 17 species; use is_latest_in_scope together with an explicitly chosen scope.';

-- Illegal trade seizures, one row per seizure, joined to the curated product
-- vocabulary so a page shows "raw skin" rather than a uuid.
--
-- Two things this view deliberately does NOT do.
--
-- It offers no aggregate. Every one of the 225 seizure quantities is unitless
-- in the source: `unit` is null on all 225 rows. A count of records is a real
-- number; a sum of quantities is a number whose unit nobody knows. The column
-- is exposed per record so a reader can see what was reported, and there is no
-- total for the same reason there is no cross-unit trade total.
--
-- It carries `reported_taxon_name`, the name the source database used, next to
-- the species this record was attributed to. 919 source rows were decontaminated
-- to 225: the other 694 named a taxon that was not the species they were filed
-- under, and the live site rendered all 919. Showing the reported name is what
-- makes the attribution auditable rather than asserted.
create view {api}.species_seizure as
select s.species_id, s.source_database, s.original_record_id,
       s.seizure_date, s.seizure_year, s.seizure_location,
       s.quantity, s.unit,
       s.product_category, p.product_name, p.main_category,
       s.reported_taxon_name, s.data_source
from {v2}.illegal_trade_seizures s
left join {v2}.illegal_trade_products p on p.id = s.product_type_id;

comment on view {api}.species_seizure is
    'Seizures attributed to a species, carrying the taxon name the source reported so the attribution can be checked. No aggregate is offered: every seizure quantity is unitless in the source.';

-- Photographs, with the right to show them carried as data.
--
-- iNaturalist's default is all rights reserved, and 9 of 43 species fall under
-- it. This view exposes ONLY rows whose licence permits display and which
-- carry the photographer's credit, so a page cannot render a photograph we
-- have no right to render. The same shape as the narrative views: the
-- application is not trusted to remember the rule, because the rule is here.
--
-- A non-exact taxon match is excluded too. A confidently wrong photograph of
-- the wrong animal is worse than a species page with no photograph, and this
-- matches the rest of the pipeline's rule: a record is attributed to a taxon
-- only when the match is exact.
create view {api}.species_media as
select m.species_id,
       m.local_path,
       m.attribution,
       m.license_code,
       m.matched_name,
       m.source
from {v2}.species_media m
where m.is_displayable
  and m.match_exact
  and m.local_path is not null;

comment on view {api}.species_media is
    'Displayable, attributed photographs only. All-rights-reserved images and non-exact taxon matches are held in the base table and are unreachable from here, so the application cannot display an image it lacks the right or the confidence to show.';

-- The corrected CITES event history, from Species+.
--
-- The predecessor view read cites_listings, which held 59 rows for the 40
-- species that resolve against 99 real listing events, and stored Party
-- reservations as listings. A species page therefore showed Iceland's 2000
-- re-accession reservation as though the minke whale had been listed that year.
--
-- Listings and reservations are exposed as one series with is_listing, rather
-- than as two views, because the distinction is the thing a reader needs to
-- see: a reservation is a Party declining to be bound, and showing only
-- listings would hide that Norway and Japan have never accepted the minke
-- whale's Appendix I listing at all.
create view {api}.species_listing_event as
select e.species_id,
       e.event_date,
       e.appendix,
       e.is_listing,
       e.party,
       e.is_current,
       e.note,
       case e.change_type
            when 'a' then 'listed'
            when 'x' then 'delisted'
            when 'r' then 'reservation entered'
            when 'w' then 'reservation withdrawn'
       end as event
from {v2}.cites_listing_events e;

comment on view {api}.species_listing_event is
    'Full CITES event history per species, verified against Species+ on every run by V-12. is_listing separates real appendix changes from Party reservations, which the previous table conflated.';

-- The application role reads this schema and nothing else.
{grants}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target-schema", default="arctic_v2")
    ap.add_argument("--api-schema", default="arctic_api")
    args = ap.parse_args()

    v2 = validate_schema(args.target_schema)
    api = validate_schema(args.api_schema)
    url = os.environ.get("ARCTIC_DATABASE_URL")
    if not url:
        sys.exit("ARCTIC_DATABASE_URL not set (set it in the environment; never hardcode it)")

    conn = psycopg2.connect(url, connect_timeout=30)
    try:
        with conn:
            with conn.cursor() as cur:
                grants = "\n".join(
                    f"grant usage on schema {api} to {r};\n"
                    f"grant select on all tables in schema {api} to {r};\n"
                    f"revoke all on schema {v2} from {r};"
                    for r in APP_ROLES
                )
                cur.execute(DDL.format(api=api, v2=v2, role=APP_ROLE, grants=grants,
                                       dimension_sql=sql_dimension('t.unit'),
                                       normalized_sql=sql_normalized_quantity('t.quantity', 't.unit')))
                cur.execute(
                    """select table_name from information_schema.views
                       where table_schema = %s order by table_name""", (api,))
                views = [v for (v,) in cur.fetchall()]
                cur.execute(
                    """select count(*) from information_schema.columns
                       where table_schema = %s and column_name ilike '%%total_quantity%%'""", (api,))
                banned = cur.fetchone()[0]
    finally:
        conn.close()

    print(f"api schema: {api}")
    for v in views:
        print(f"  {v}")
    print(f"\napp roles: {', '.join(APP_ROLES)}, granted SELECT on {api}")
    missing = EXPECTED_VIEWS - set(views)
    undeclared = set(views) - EXPECTED_VIEWS
    if missing:
        sys.exit(f"FAIL: declared view(s) absent from {api}: {sorted(missing)}")
    if undeclared:
        sys.exit(f"FAIL: undeclared view(s) in {api}: {sorted(undeclared)}; "
                 f"widen EXPECTED_VIEWS deliberately, not by accident")
    print(f"all {len(EXPECTED_VIEWS)} declared views present, none undeclared")
    if banned:
        sys.exit(f"FAIL: {banned} column(s) named total_quantity exist in {api}; "
                 f"a cross-unit total must not be expressible")
    print("no total_quantity column anywhere in the api schema, as intended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
