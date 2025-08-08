-- CMS Migration SQL Queries
-- Use these queries in order during the migration process

-- ============================================
-- STEP 2: Verify Table Creation
-- ============================================

-- Check if tables were created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('cms_listings', 'species_cms_listings');

-- Check column structure (should show agreement, listed_under, etc.)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'cms_listings'
ORDER BY ordinal_position;

-- ============================================
-- STEP 5: Update Article Summary Table
-- ============================================

-- Update article_summary_table with CMS data
UPDATE article_summary_table ast
SET 
    cms_status_current = subquery.cms_appendix,
    cms_status_change = subquery.cms_change,
    last_updated = CURRENT_TIMESTAMP
FROM (
    SELECT 
        s.id as species_id,
        cms.appendix as cms_appendix,
        CASE 
            WHEN cms.appendix IS NOT NULL THEN 'new_listing'
            ELSE NULL
        END as cms_change
    FROM species s
    LEFT JOIN cms_listings cms ON s.id = cms.species_id
) subquery
WHERE ast.species_id = subquery.species_id;

-- Verify the update worked
SELECT 
    COUNT(*) as total_records,
    COUNT(cms_status_current) as records_with_cms,
    COUNT(*) - COUNT(cms_status_current) as records_without_cms
FROM article_summary_table;

-- ============================================
-- POST-MIGRATION VERIFICATION
-- ============================================

-- Check CMS data integration with species names
SELECT 
    s.common_name,
    s.scientific_name,
    ast.cms_status_current,
    ast.cms_status_change,
    array_length(cms.native_distribution, 1) as countries_count
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
LEFT JOIN cms_listings cms ON s.id = cms.species_id
WHERE ast.cms_status_current IS NOT NULL
ORDER BY s.common_name
LIMIT 10;

-- Verify iconic Arctic species have CMS status
SELECT 
    s.common_name,
    s.scientific_name,
    ast.cms_status_current,
    ast.cites_status_current,
    CASE 
        WHEN ast.cms_status_current = 'I' THEN 'Endangered migratory species'
        WHEN ast.cms_status_current = 'II' THEN 'Requires international cooperation'
        WHEN ast.cms_status_current = 'I/II' THEN 'Listed in both appendices'
        ELSE 'Not listed in CMS'
    END as cms_description
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
WHERE s.common_name IN ('Polar Bear', 'Narwhal', 'Beluga', 'Bowhead Whale', 'Walrus')
ORDER BY s.common_name;

-- Get summary statistics
SELECT 
    cms_status_current,
    COUNT(*) as species_count
FROM article_summary_table
WHERE cms_status_current IS NOT NULL
GROUP BY cms_status_current
ORDER BY cms_status_current;

-- Find species with widest distribution
SELECT 
    s.common_name,
    s.scientific_name,
    cms.appendix,
    array_length(cms.native_distribution, 1) as native_countries,
    array_length(cms.distribution_codes, 1) as total_distribution
FROM cms_listings cms
JOIN species s ON cms.species_id = s.id
ORDER BY array_length(cms.distribution_codes, 1) DESC NULLS LAST
LIMIT 10;

-- ============================================
-- TROUBLESHOOTING QUERIES
-- ============================================

-- If you need to check what's in cms_listings
SELECT COUNT(*) as total_cms_records FROM cms_listings;

-- If you need to see raw CMS data
SELECT 
    s.common_name,
    cms.*
FROM cms_listings cms
JOIN species s ON cms.species_id = s.id
LIMIT 5;

-- If the update didn't work, check for data type issues
SELECT 
    s.common_name,
    cms.appendix,
    ast.cms_status_current,
    ast.species_id
FROM species s
LEFT JOIN cms_listings cms ON s.id = cms.species_id
LEFT JOIN article_summary_table ast ON s.id = ast.species_id
WHERE cms.appendix IS NOT NULL AND ast.cms_status_current IS NULL
LIMIT 10;

-- ============================================
-- ROLLBACK QUERIES (if needed)
-- ============================================

-- To clear CMS data from article_summary_table (if you need to retry)
UPDATE article_summary_table
SET 
    cms_status_current = NULL,
    cms_status_change = NULL
WHERE cms_status_current IS NOT NULL;

-- To completely remove CMS tables (nuclear option)
-- DROP TABLE IF EXISTS cms_listings CASCADE;
-- DROP VIEW IF EXISTS species_cms_listings CASCADE;