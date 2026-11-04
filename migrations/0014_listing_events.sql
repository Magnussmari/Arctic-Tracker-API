-- 0014: separate CITES listing events from Party reservations.
--
-- cites_listings held 59 rows for the 40 species that resolve in Species+,
-- against 99 real listing events, and conflated two different kinds of event.
-- Iceland's 2000-04-02 re-accession reservations were stored as listings on
-- three cetaceans; Balaenoptera acutorostrata had three genuine listings and
-- seventeen reservation events, of which three had been loaded as listings.
--
-- The distinguishing field is Species+ change_type, not the presence of a
-- Party: Appendix III listings DO name the listing Party under Article XVI,
-- and all 25 of ours do.
create table if not exists arctic_v2.cites_listing_events (
    id               uuid primary key default gen_random_uuid(),
    species_id       uuid not null references arctic_v2.species(id) on delete cascade,

    event_date       date,
    appendix         text,
    change_type      text not null,          -- a=addition x=deletion r=reservation w=withdrawal
    is_listing       boolean not null,       -- change_type in (a,x)
    party            text,                   -- named for App III listings AND for reservations
    is_current       boolean,
    note             text,

    source_taxon_id  integer,
    source_artifact  text,
    source_sha256    text,
    provenance_class text not null default 'EXTERNAL',
    loader_version   text,
    loaded_at        timestamptz not null default now()
);

comment on table arctic_v2.cites_listing_events is
  'Full CITES event history from Species+, with listings and reservations distinguished by change_type. Supersedes cites_listings, which conflated them and was short by 40 events.';
comment on column arctic_v2.cites_listing_events.is_listing is
  'True only for change_type a or x. A reservation is a Party declining to be bound; it does not move a species between appendices.';

create index if not exists cites_listing_events_species_idx
    on arctic_v2.cites_listing_events (species_id, event_date);
