-- Final CITES v2025.1 Migration
-- Arctic Tracker Database
-- 
-- This script migrates new records from staging to production
-- handling schema differences between tables

-- Step 1: Add new records from staging that don't exist in production
-- We'll use a composite key match to identify truly new records

INSERT INTO cites_trade_records (
    species_id,
    year,
    appendix,
    taxon,
    class,
    order_name,
    family,
    genus,
    term,
    quantity,
    unit,
    importer,
    exporter,
    origin,
    purpose,
    source,
    reporter_type
)
SELECT DISTINCT
    s.species_id,
    s.year,
    s.appendix,
    s.taxon,
    s.class,
    s.order_name,
    s.family,
    s.genus,
    s.term,
    COALESCE(s.importer_reported_quantity, s.exporter_reported_quantity) as quantity,
    s.unit,
    s.importer,
    s.exporter,
    s.origin,
    s.purpose,
    s.source,
    'I' as reporter_type  -- Default to Importer
FROM cites_trade_records_staging s
WHERE NOT EXISTS (
    SELECT 1 
    FROM cites_trade_records p
    WHERE p.species_id = s.species_id
    AND p.year = s.year
    AND COALESCE(p.taxon, '') = COALESCE(s.taxon, '')
    AND COALESCE(p.importer, '') = COALESCE(s.importer, '')
    AND COALESCE(p.exporter, '') = COALESCE(s.exporter, '')
    AND COALESCE(p.term, '') = COALESCE(s.term, '')
    AND COALESCE(p.purpose, '') = COALESCE(s.purpose, '')
    AND COALESCE(p.source, '') = COALESCE(s.source, '')
)
ON CONFLICT DO NOTHING;

-- Step 2: Get migration statistics
WITH migration_stats AS (
    SELECT 
        COUNT(*) as staging_total,
        COUNT(DISTINCT species_id) as species_count,
        MIN(year) as min_year,
        MAX(year) as max_year,
        COUNT(*) FILTER (WHERE year = 2024) as records_2024,
        COUNT(*) FILTER (WHERE year = 2023) as records_2023
    FROM cites_trade_records_staging
)
SELECT 
    'Migration Statistics' as info,
    staging_total as "Total Staging Records",
    species_count as "Species Count",
    min_year || ' - ' || max_year as "Year Range",
    records_2024 as "2024 Records",
    records_2023 as "2023 Records"
FROM migration_stats;

-- Step 3: Verify migration success
WITH post_migration AS (
    SELECT 
        COUNT(*) as total_records,
        COUNT(*) FILTER (WHERE year = 2024) as records_2024,
        COUNT(*) FILTER (WHERE year = 2023) as records_2023,
        COUNT(DISTINCT species_id) as species_count
    FROM cites_trade_records
)
SELECT 
    'Post-Migration Status' as info,
    total_records as "Total Records",
    records_2024 as "2024 Records", 
    records_2023 as "2023 Records",
    species_count as "Species Count"
FROM post_migration;