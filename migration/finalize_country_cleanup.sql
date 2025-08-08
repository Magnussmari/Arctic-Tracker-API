-- Final Country Cleanup - Arctic Tracker Database
-- Run this to complete the country references standardization

-- Step 1: Remove the redundant 'country' text column from catch_records
-- (Safe to run since all records use country_id)
ALTER TABLE catch_records DROP COLUMN IF EXISTS country;

-- Step 2: Add foreign key constraint for data integrity
ALTER TABLE catch_records 
ADD CONSTRAINT fk_catch_records_country 
FOREIGN KEY (country_id) REFERENCES countries(id);

-- Step 3: Add foreign key constraint for management_areas
ALTER TABLE management_areas 
ADD CONSTRAINT fk_management_areas_country 
FOREIGN KEY (country_id) REFERENCES countries(id);

-- Step 4: Add performance indexes
CREATE INDEX IF NOT EXISTS idx_catch_records_country_id ON catch_records(country_id);
CREATE INDEX IF NOT EXISTS idx_catch_records_year_country ON catch_records(year, country_id);
CREATE INDEX IF NOT EXISTS idx_management_areas_country_id ON management_areas(country_id);

-- Step 5: Add data quality constraints
ALTER TABLE countries 
ADD CONSTRAINT chk_country_name_not_empty 
CHECK (length(trim(country_name)) > 0);

ALTER TABLE countries 
ADD CONSTRAINT chk_country_code_format 
CHECK (country_code IS NULL OR length(country_code) = 2);

-- Step 6: Create useful views for easy querying
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

-- Step 7: Create country statistics view
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
    COALESCE(trade_stats.total_trade_records, 0) as total_trade_records
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
        COUNT(*) as total_trade_records
    FROM (
        SELECT importer as country_code FROM cites_trade_records WHERE importer IS NOT NULL
        UNION ALL
        SELECT exporter as country_code FROM cites_trade_records WHERE exporter IS NOT NULL
        UNION ALL
        SELECT origin as country_code FROM cites_trade_records WHERE origin IS NOT NULL
    ) trade_data
    GROUP BY country_code
) trade_stats ON c.country_code = trade_stats.country_code;

-- Step 8: Add helpful table comments
COMMENT ON TABLE countries IS 'Master table for all countries referenced in Arctic Tracker data';
COMMENT ON COLUMN countries.country_name IS 'Full country name (e.g., "United States")';
COMMENT ON COLUMN countries.country_code IS 'ISO 2-letter country code (e.g., "US")';
COMMENT ON COLUMN countries.nammco_member IS 'True if country is a NAMMCO member';
COMMENT ON COLUMN countries.arctic_council IS 'True if country is an Arctic Council member';

COMMENT ON VIEW v_catch_records_with_countries IS 'Catch records joined with country information for easy querying';
COMMENT ON VIEW v_country_statistics IS 'Summary statistics for each country showing catch and trade data';

-- Verification queries:

-- 1. Confirm all catch records have country references
SELECT 
    'catch_records_validation' as check_name,
    COUNT(*) as total_records,
    COUNT(country_id) as records_with_country_id,
    COUNT(*) - COUNT(country_id) as records_missing_country_id
FROM catch_records;

-- 2. Show countries by type with statistics
SELECT 
    CASE 
        WHEN arctic_council AND nammco_member THEN 'Arctic Council + NAMMCO'
        WHEN arctic_council THEN 'Arctic Council Only'
        WHEN nammco_member THEN 'NAMMCO Only'
        ELSE 'Other'
    END as country_type,
    COUNT(*) as country_count,
    SUM(total_catch_records) as total_catch_records,
    string_agg(country_name, ', ' ORDER BY country_name) as countries
FROM v_country_statistics
GROUP BY 
    CASE 
        WHEN arctic_council AND nammco_member THEN 'Arctic Council + NAMMCO'
        WHEN arctic_council THEN 'Arctic Council Only'
        WHEN nammco_member THEN 'NAMMCO Only'
        ELSE 'Other'
    END
ORDER BY country_count DESC;

-- 3. Show top countries by catch data
SELECT 
    country_name,
    country_code,
    arctic_council,
    nammco_member,
    total_catch_records,
    total_catch,
    species_with_catch_data
FROM v_country_statistics
WHERE total_catch_records > 0
ORDER BY total_catch_records DESC
LIMIT 10;
