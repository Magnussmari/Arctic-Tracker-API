-- 0015: record which release of each upstream database the corpus was built from.
--
-- Reviewer 3 asked what was downloaded and when. Before this table, the release
-- was recoverable only from a directory name and the date only from file
-- modification times. A methods
-- section whose provenance lives in a filesystem is not reproducible, and the
-- filesystem is the least durable thing in the pipeline — a copy, a restore or
-- a rsync silently rewrites every mtime we were relying on.
--
-- This table makes the answer a stored fact. It is deliberately narrow: one row
-- per upstream release actually loaded, with the evidence for the date named
-- rather than implied, because "2025-07-28" derived from an mtime is a weaker
-- claim than the same date printed on a release page, and the difference should
-- survive into the deposit.

create table if not exists arctic_v2.source_releases (
    id                  uuid primary key default gen_random_uuid(),
    source_name         text        not null,
    release_label       text        not null,
    obtained_on         date        not null,
    obtained_on_basis   text        not null,
    artifact_path       text        not null,
    artifact_count      integer,
    artifact_bytes      bigint,
    notes               text,
    recorded_at         timestamptz not null default now(),
    unique (source_name, release_label)
);

comment on table arctic_v2.source_releases is
  'Which upstream release each part of the corpus was built from. Answers '
  'Reviewer 3''s "what was downloaded, and when" from stored data rather than '
  'from a directory name.';

comment on column arctic_v2.source_releases.obtained_on_basis is
  'How the date is known. Distinguishes a date published by the source from one '
  'inferred from filesystem metadata, which is weaker and can be destroyed by a '
  'copy or a restore.';

insert into arctic_v2.source_releases
    (source_name, release_label, obtained_on, obtained_on_basis,
     artifact_path, artifact_count, artifact_bytes, notes)
values
    ('CITES Trade Database',
     'v2025.1',
     date '2025-07-28',
     'Inferred from the modification time of all 56 downloaded shards, which '
     'agree to the day. The release label is taken from the download directory '
     'name as issued by the CITES full-database download service. No download '
     'receipt was retained at the time.',
     'species_data/cites_trade/Trade_database_download_v2025.1/trade_db_*.csv',
     56,
     4200000000,
     '21,574 distinct taxon strings in the release; 492,095 records extracted '
     'for the 43 focal species.'),
    ('IUCN Red List',
     'snapshot 2026-07-22',
     date '2026-07-22',
     'The snapshot file carries the date in its own name and was written by our '
     'extraction run on that date.',
     'species_data/iucn/iucn_assessments_snapshot_2026-07-22.csv',
     1,
     null,
     '370 assessments across the 43 focal species, global scope retained '
     'alongside regional.')
on conflict (source_name, release_label) do nothing;

grant select on arctic_v2.source_releases to arctic_v2_app;
