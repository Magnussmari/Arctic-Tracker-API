-- 0012: species media, with the licence carried as data rather than assumed.
--
-- The v1 site resolved images against the iNaturalist API at render time. That
-- is slow (a network round trip per species page), fragile (a rate limit or an
-- outage becomes a broken page), and it silently displayed photographs without
-- checking whether their licence permitted it.
--
-- This table fixes all three. Images are resolved once, the licence and the
-- photographer's attribution are stored alongside the file, and the file is
-- served from our own origin. A photograph with no licence code is recorded
-- and NOT displayed: "all rights reserved" is the iNaturalist default, and
-- roughly a fifth of our species fall under it.
--
-- The read layer exposes only rows whose licence permits display, which is the
-- same pattern as unreviewed narrative prose: the application cannot render
-- something it has no right to render, because no view offers it.

create table if not exists arctic_v2.species_media (
    id              uuid primary key default gen_random_uuid(),
    species_id      uuid not null references arctic_v2.species(id) on delete cascade,

    source          text not null,           -- 'inaturalist'
    source_taxon_id integer,                 -- the taxon actually matched
    source_photo_id text,

    -- Licence and credit. Both are required to display; neither is inferred.
    license_code    text,                    -- cc0, cc-by, cc-by-nc, ...
    attribution     text,                    -- the photographer credit, verbatim
    is_displayable  boolean not null default false,

    original_url    text,
    local_path      text,                    -- served from our own origin
    content_sha256  text,                    -- what we actually stored

    matched_name    text,                    -- the name iNaturalist returned
    match_exact     boolean not null default false,

    provenance_class text not null default 'EXTERNAL',
    loader_version  text,
    loaded_at       timestamptz not null default now(),

    unique (species_id, source)
);

comment on table arctic_v2.species_media is
  'One image per species per source, with its licence and photographer credit stored as data. is_displayable is false unless the licence permits display AND the credit is present, so an unlicensed photograph cannot reach a page.';

comment on column arctic_v2.species_media.is_displayable is
  'False for all-rights-reserved photographs (iNaturalist default, no license_code) and for any row missing attribution. The read-surface view filters on this column.';

create index if not exists species_media_species_idx
    on arctic_v2.species_media (species_id);
