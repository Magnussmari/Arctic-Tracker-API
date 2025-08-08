-- Country Schema Cleanup SQL
-- Run this AFTER running the country references cleanup script
-- This removes redundant columns and adds proper constraints

-- Step 1: Remove redundant country text column from catch_records
-- (Only run this after confirming all country data is migrated to country_id)
-- ALTER TABLE catch_records DROP COLUMN IF EXISTS country;

-- Step 2: Add foreign key constraints for data integrity
ALTER TABLE catch_records 
ADD CONSTRAINT fk_catch_records_country 
FOREIGN KEY (country_id) REFERENCES countries(id);

-- Step 3: Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_catch_records_country_id ON catch_records(country_id);
CREATE INDEX IF NOT EXISTS idx_catch_records_year_country ON catch_records(year, country_id);

-- Step 4: Add constraints to ensure data quality
ALTER TABLE countries 
ADD CONSTRAINT chk_country_name_not_empty 
CHECK (length(trim(country_name)) > 0);

ALTER TABLE countries 
ADD CONSTRAINT chk_country_code_format 
CHECK (country_code IS NULL OR length(country_code) = 2);

-- Step 5: Create view for easy country lookups with catch data
CREATE OR REPLACE VIEW v_catch_records_with_countries AS
SELECT 
    cr.id,
    cr.species_id,
    cr.year,
    cr.catch_total,
    cr.quota_amount,
    cr.management_area_id,
    cr.data_source,
    c.country_name,
    c.country_code,
    c.nammco_member,
    c.arctic_council,
    s.scientific_name,
    s.common_name
FROM catch_records cr
LEFT JOIN countries c ON cr.country_id = c.id
LEFT JOIN species s ON cr.species_id = s.id;

-- Step 6: Create view for CITES trade with country names
CREATE OR REPLACE VIEW v_cites_trade_with_countries AS
SELECT 
    ctr.id,
    ctr.species_id,
    ctr.year,
    ctr.term,
    ctr.quantity,
    ctr.unit,
    ctr.purpose,
    ctr.source,
    imp.country_name as importer_country,
    imp.country_code as importer_code,
    exp.country_name as exporter_country,
    exp.country_code as exporter_code,
    orig.country_name as origin_country,
    orig.country_code as origin_code,
    s.scientific_name,
    s.common_name
FROM cites_trade_records ctr
LEFT JOIN countries imp ON imp.country_code = ctr.importer
LEFT JOIN countries exp ON exp.country_code = ctr.exporter
LEFT JOIN countries orig ON orig.country_code = ctr.origin
LEFT JOIN species s ON ctr.species_id = s.id;

-- Step 7: Create summary view for country statistics
CREATE OR REPLACE VIEW v_country_statistics AS
SELECT 
    c.id,
    c.country_name,
    c.country_code,
    c.nammco_member,
    c.arctic_council,
    COALESCE(catch_stats.total_catch_records, 0) as total_catch_records,
    COALESCE(catch_stats.total_catch, 0) as total_catch,
    COALESCE(catch_stats.species_count, 0) as species_with_catch_data,
    COALESCE(trade_stats.total_trade_records, 0) as total_trade_records,
    COALESCE(trade_stats.trade_species_count, 0) as species_in_trade
FROM countries c
LEFT JOIN (
    SELECT 
        country_id,
        COUNT(*) as total_catch_records,
        SUM(COALESCE(catch_total, 0)) as total_catch,
        COUNT(DISTINCT species_id) as species_count
    FROM catch_records 
    WHERE country_id IS NOT NULL
    GROUP BY country_id
) catch_stats ON c.id = catch_stats.country_id
LEFT JOIN (
    SELECT 
        country_code,
        COUNT(*) as total_trade_records,
        COUNT(DISTINCT species_id) as trade_species_count
    FROM (
        SELECT importer as country_code, species_id FROM cites_trade_records WHERE importer IS NOT NULL
        UNION ALL
        SELECT exporter as country_code, species_id FROM cites_trade_records WHERE exporter IS NOT NULL
        UNION ALL
        SELECT origin as country_code, species_id FROM cites_trade_records WHERE origin IS NOT NULL
    ) trade_data
    GROUP BY country_code
) trade_stats ON c.country_code = trade_stats.country_code;

-- Step 8: Add helpful comments to tables
COMMENT ON TABLE countries IS 'Master table for all countries referenced in Arctic Tracker data';
COMMENT ON COLUMN countries.country_name IS 'Full country name (e.g., "United States")';
COMMENT ON COLUMN countries.country_code IS 'ISO 2-letter country code (e.g., "US")';
COMMENT ON COLUMN countries.nammco_member IS 'True if country is a NAMMCO member';
COMMENT ON COLUMN countries.arctic_council IS 'True if country is an Arctic Council member';

COMMENT ON VIEW v_catch_records_with_countries IS 'Catch records joined with country information for easy querying';
COMMENT ON VIEW v_cites_trade_with_countries IS 'CITES trade records with resolved country names';
COMMENT ON VIEW v_country_statistics IS 'Summary statistics for each country showing catch and trade data';

-- Step 9: Grant appropriate permissions (adjust as needed)
-- GRANT SELECT ON v_catch_records_with_countries TO public;
-- GRANT SELECT ON v_cites_trade_with_countries TO public;
-- GRANT SELECT ON v_country_statistics TO public;

-- Verification queries to run after cleanup:

-- Check that all catch records have valid country references
SELECT 
    'catch_records' as table_name,
    COUNT(*) as total_records,
    COUNT(country_id) as records_with_country_id,
    COUNT(*) - COUNT(country_id) as records_missing_country_id
FROM catch_records;

-- Check country code coverage in CITES data
SELECT 
    'cites_coverage' as check_type,
    COUNT(DISTINCT importer) + COUNT(DISTINCT exporter) + COUNT(DISTINCT origin) as unique_country_codes,
    COUNT(DISTINCT c1.id) + COUNT(DISTINCT c2.id) + COUNT(DISTINCT c3.id) as resolved_countries
FROM cites_trade_records ctr
LEFT JOIN countries c1 ON c1.country_code = ctr.importer
LEFT JOIN countries c2 ON c2.country_code = ctr.exporter  
LEFT JOIN countries c3 ON c3.country_code = ctr.origin;

-- Show countries by type
SELECT 
    CASE 
        WHEN arctic_council AND nammco_member THEN 'Arctic Council + NAMMCO'
        WHEN arctic_council THEN 'Arctic Council Only'
        WHEN nammco_member THEN 'NAMMCO Only'
        ELSE 'Other'
    END as country_type,
    COUNT(*) as count,
    string_agg(country_name, ', ' ORDER BY country_name) as countries
FROM countries 
GROUP BY 
    CASE 
        WHEN arctic_council AND nammco_member THEN 'Arctic Council + NAMMCO'
        WHEN arctic_council THEN 'Arctic Council Only'
        WHEN nammco_member THEN 'NAMMCO Only'
        ELSE 'Other'
    END
ORDER BY count DESC;
