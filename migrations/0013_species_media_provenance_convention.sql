-- 0013: align species_media to the project's provenance column convention.
--
-- V-6 requires every content table to carry provenance_class, source_artifact
-- and source_sha256. species_media shipped with `content_sha256` and no
-- source_artifact, so the reconciliation gate failed on the very next run.
--
-- The gate was right and the table was wrong. For a downloaded photograph the
-- source artifact IS the remote file, so original_url and the digest of the
-- bytes we stored are exactly the two things the convention asks for; they were
-- simply under the wrong names.
alter table arctic_v2.species_media
    add column if not exists source_artifact text,
    add column if not exists source_sha256   text;

update arctic_v2.species_media
   set source_artifact = coalesce(source_artifact, original_url),
       source_sha256   = coalesce(source_sha256, content_sha256);

comment on column arctic_v2.species_media.source_artifact is
  'The remote photograph URL: the artifact these bytes came from.';
comment on column arctic_v2.species_media.source_sha256 is
  'SHA-256 of the bytes actually stored, which for a downloaded file is the digest of the source artifact as we received it.';
