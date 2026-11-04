-- 0016_seed_source_releases.sql
--
-- Seed source_releases for every external upstream source.
--
-- 0015 created the table with rows for CITES and IUCN only. This migration adds
-- the other four upstream sources (NAMMCO, the CMS Appendices, the Species+
-- listing history and the illegal-trade seizure compilation), so every source
-- records which release was used and when it was obtained.
--
-- Seeding them in a migration means a rebuild reproduces them.
--
-- Every basis statement says how the date is known: only
-- the IUCN snapshot carries its own date. The rest are inferred from filenames
-- or filesystem metadata, and one of them cannot be re-derived at all because
-- the scraper that produced it no longer exists.

-- The seed's ON CONFLICT needs a unique key on source_name alone. 0015 created
-- unique (source_name, release_label), which does not constrain re-seeding: the
-- same source with a different label would insert a second row. One row per
-- source is the intent, so it is stated.
alter table arctic_v2.source_releases
  drop constraint if exists source_releases_source_name_key;
alter table arctic_v2.source_releases
  add constraint source_releases_source_name_key unique (source_name);

insert into arctic_v2.source_releases
  (source_name, release_label, obtained_on, obtained_on_basis,
   artifact_path, artifact_count, artifact_bytes, notes)
values
  ('Arctic illegal-trade seizure records', 'compiled 2025-07-28', '2025-07-28', 'Inferred from the modification time of the compiled file. This is a curated compilation rather than a published release, so no upstream release identifier exists; the underlying seizure sources are cited individually in the manuscript.', 'illegal_trade/arctic_illegal_trade_records.csv', '1', null, '919 seizure records before scope filtering.'),
  ('CITES Trade Database', 'v2025.1', '2025-07-28', 'Inferred from the modification time of all 56 downloaded shards, which agree to the day. The release label is taken from the download directory name as issued by the CITES full-database download service. No download receipt was retained at the time.', 'species_data/cites_trade/Trade_database_download_v2025.1/trade_db_*.csv', '56', '4200000000', '21,574 distinct taxon strings in the release; 492,095 records extracted for the 43 focal species.'),
  ('CMS Appendices', 'download 2025-07-10', '2025-07-10', 'Two independent signals agree: the filename encodes 100725 as DDMMYY, and the file''s modification time is 2025-07-10. Agreement of two weak signals is still weaker than a download receipt, which was not kept; recorded as inferred rather than published.', 'species_data/raw_data/cms_listing_100725.csv', '1', null, '2,032 rows covering the CMS Appendices.'),
  ('IUCN Red List', 'snapshot 2026-07-22', '2026-07-22', 'The snapshot file carries the date in its own name and was written by our extraction run on that date.', 'species_data/iucn/iucn_assessments_snapshot_2026-07-22.csv', '1', null, '370 assessments across the 43 focal species, global scope retained alongside regional.'),
  ('NAMMCO catch database', 'scrape 2025-06-11', '2025-06-11', 'Carried in every source filename (*_catches_2025-06-11.csv), 18 files agreeing to the day. No download receipt was kept, and the Selenium scraper that produced them was lost in an October 2025 repository cleanup, so this date cannot be re-derived by re-running anything.', 'species_data/nammco/*_catches_2025-06-11.csv', '18', null, '958 catch records, 18 marine-mammal species. Coverage bounds are documented in the deposit README. Not redistributable.'),
  ('Species+ API (CITES listing history)', 'queried 2026-08-12', '2026-08-12', 'The query date is the load timestamp on cites_listing_events, which is the same run that wrote the rows. Species+ serves a live view rather than versioned releases, so there is no release identifier to record and the date is the only version information that exists.', 'speciesplus.net/api/v1/taxon_concepts', null, null, '290 listing events across the focal species. Reservations counted separately; V-12 reconciles this table against the official record.')
on conflict (source_name) do nothing;
