-- Final Step: Update Article Summary Table with CMS Data
-- Run this in Supabase SQL Editor

-- ============================================
-- Update article_summary_table with CMS data
-- ============================================

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

-- ============================================
-- Verify the update worked
-- ============================================

SELECT 
    COUNT(*) as total_records,
    COUNT(cms_status_current) as records_with_cms,
    COUNT(*) - COUNT(cms_status_current) as records_without_cms
FROM article_summary_table;

-- Expected result: 31 records with CMS status

-- ============================================
-- Check CMS status distribution
-- ============================================

SELECT 
    cms_status_current,
    COUNT(*) as species_count
FROM article_summary_table
WHERE cms_status_current IS NOT NULL
GROUP BY cms_status_current
ORDER BY cms_status_current;

-- Expected: 15 species with 'I', 16 species with 'II'

-- ============================================
-- Verify iconic Arctic species
-- ============================================

SELECT 
    s.common_name,
    s.scientific_name,
    ast.cms_status_current,
    ast.cites_status_current,
    CASE 
        WHEN ast.cms_status_current = 'I' THEN 'Endangered migratory species'
        WHEN ast.cms_status_current = 'II' THEN 'Requires international cooperation'
        ELSE 'Not listed in CMS'
    END as cms_description
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
WHERE s.common_name IN ('Polar Bear', 'Narwhal', 'Beluga', 'Bowhead Whale', 'Walrus')
ORDER BY s.common_name;

-- ============================================
-- List all species with CMS status
-- ============================================

SELECT 
    s.common_name,
    s.scientific_name,
    ast.cms_status_current,
    ast.cites_status_current,
    ast.trade_records_count,
    ast.last_recorded_year
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
WHERE ast.cms_status_current IS NOT NULL
ORDER BY ast.cms_status_current, s.common_name;

-- ============================================
-- Conservation Summary Statistics
-- ============================================

SELECT 
    'Total Arctic Species' as category,
    COUNT(*) as count
FROM article_summary_table
UNION ALL
SELECT 
    'Species with CMS Status' as category,
    COUNT(*) as count
FROM article_summary_table
WHERE cms_status_current IS NOT NULL
UNION ALL
SELECT 
    'Species with Both CITES & CMS' as category,
    COUNT(*) as count
FROM article_summary_table
WHERE cms_status_current IS NOT NULL 
AND cites_status_current IS NOT NULL;

-- ============================================
-- Note about I/II species
-- ============================================
-- The following 8 species are listed in both CMS Appendix I and II
-- but have been classified as 'I' (higher protection level) in the database:
-- 1. Balaenoptera borealis (Sei Whale)
-- 2. Balaenoptera physalus (Fin Whale)
-- 3. Branta ruficollis (Red-breasted Goose)
-- 4. Cetorhinus maximus (Basking Shark)
-- 5. Leucogeranus leucogeranus (Siberian Crane)
-- 6. Numenius borealis (Eskimo Curlew)
-- 7. Phocoena phocoena (Harbor Porpoise)
-- 8. Physeter macrocephalus (Sperm Whale)