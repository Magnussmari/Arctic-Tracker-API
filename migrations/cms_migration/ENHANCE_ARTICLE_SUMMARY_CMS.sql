-- Enhanced Article Summary Table: Add Missing CMS Fields
-- This script adds comprehensive CMS fields to match CITES coverage
-- Run this in Supabase SQL Editor BEFORE updating CMS data

-- ============================================
-- Step 1: Add Missing CMS Columns
-- ============================================

-- Core CMS metadata
ALTER TABLE article_summary_table 
ADD COLUMN IF NOT EXISTS cms_listing_date TEXT,
ADD COLUMN IF NOT EXISTS cms_listing_years INTEGER,
ADD COLUMN IF NOT EXISTS cms_agreement_type TEXT,
ADD COLUMN IF NOT EXISTS cms_listing_notes TEXT;

-- Distribution metrics (parallel to CITES trade distribution)
ALTER TABLE article_summary_table
ADD COLUMN IF NOT EXISTS cms_native_countries_count INTEGER,
ADD COLUMN IF NOT EXISTS cms_distribution_codes TEXT[],
ADD COLUMN IF NOT EXISTS cms_introduced_countries_count INTEGER,
ADD COLUMN IF NOT EXISTS cms_extinct_countries_count INTEGER;

-- Conservation indicators
ALTER TABLE article_summary_table
ADD COLUMN IF NOT EXISTS cms_conservation_priority TEXT,
ADD COLUMN IF NOT EXISTS cms_population_trend TEXT,
ADD COLUMN IF NOT EXISTS has_cms_action_plan BOOLEAN DEFAULT FALSE;

-- ============================================
-- Step 2: Update Table with Enhanced CMS Data
-- ============================================

UPDATE article_summary_table ast
SET 
    -- Core CMS fields
    cms_status_current = subquery.cms_appendix,
    cms_status_change = subquery.cms_change,
    cms_listing_date = subquery.listing_date,
    cms_listing_years = subquery.listing_years,
    cms_agreement_type = subquery.agreement,
    cms_listing_notes = subquery.notes,
    
    -- Distribution metrics
    cms_native_countries_count = subquery.native_count,
    cms_distribution_codes = subquery.distribution_codes,
    cms_introduced_countries_count = subquery.introduced_count,
    cms_extinct_countries_count = subquery.extinct_count,
    
    -- Conservation priority (based on appendix and distribution)
    cms_conservation_priority = subquery.conservation_priority,
    
    -- Update timestamp
    last_updated = CURRENT_TIMESTAMP
FROM (
    SELECT 
        s.id as species_id,
        cms.appendix as cms_appendix,
        cms.listing_date,
        -- Calculate years since listing (extract year from listing_date string)
        CASE 
            WHEN cms.listing_date IS NOT NULL AND cms.listing_date ~ '\d{4}' 
            THEN 2025 - CAST(SUBSTRING(cms.listing_date FROM '\d{4}') AS INTEGER)
            ELSE NULL
        END as listing_years,
        cms.agreement,
        cms.notes,
        
        -- Distribution counts
        COALESCE(array_length(cms.native_distribution, 1), 0) as native_count,
        cms.distribution_codes,
        COALESCE(array_length(cms.introduced_distribution, 1), 0) as introduced_count,
        COALESCE(array_length(cms.extinct_distribution, 1), 0) as extinct_count,
        
        -- Determine conservation priority based on appendix and distribution
        CASE 
            WHEN cms.appendix = 'I' THEN 'High'
            WHEN cms.appendix = 'II' AND COALESCE(array_length(cms.native_distribution, 1), 0) > 20 THEN 'Medium'
            WHEN cms.appendix = 'II' THEN 'High'
            ELSE NULL
        END as conservation_priority,
        
        -- Status change detection
        CASE 
            WHEN cms.appendix IS NOT NULL THEN 'new_listing'
            ELSE NULL
        END as cms_change
    FROM species s
    LEFT JOIN cms_listings cms ON s.id = cms.species_id
) subquery
WHERE ast.species_id = subquery.species_id;

-- ============================================
-- Step 3: Verification Queries
-- ============================================

-- Check the enhanced CMS data
SELECT 
    s.common_name,
    s.scientific_name,
    ast.cms_status_current as "CMS Appendix",
    ast.cms_listing_date as "Listing Date",
    ast.cms_listing_years as "Years Listed",
    ast.cms_native_countries_count as "Native Countries",
    ast.cms_conservation_priority as "Priority",
    ast.cites_status_current as "CITES Status"
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
WHERE ast.cms_status_current IS NOT NULL
ORDER BY ast.cms_listing_years DESC NULLS LAST, s.common_name
LIMIT 10;

-- ============================================
-- Step 4: Create Comprehensive Conservation View
-- ============================================

-- Species with both CITES and CMS listings, showing comprehensive data
SELECT 
    s.common_name,
    s.scientific_name,
    -- CITES Information
    ast.cites_status_current as "CITES",
    ast.trade_records_count as "Trade Records",
    ast.last_recorded_year as "Last Trade",
    ast.trade_trend as "Trade Trend",
    -- CMS Information  
    ast.cms_status_current as "CMS",
    ast.cms_listing_date as "CMS Date",
    ast.cms_listing_years as "Years Listed",
    ast.cms_native_countries_count as "Range States",
    ast.cms_conservation_priority as "CMS Priority",
    -- Combined Status
    CASE 
        WHEN ast.cites_status_current = 'I' AND ast.cms_status_current = 'I' THEN 'Critical - Both Conventions'
        WHEN ast.cites_status_current = 'I' OR ast.cms_status_current = 'I' THEN 'High Priority'
        WHEN ast.cites_status_current IS NOT NULL AND ast.cms_status_current IS NOT NULL THEN 'Dual Protection'
        ELSE 'Single Convention'
    END as "Conservation Status"
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
WHERE ast.cms_status_current IS NOT NULL 
   OR ast.cites_status_current IS NOT NULL
ORDER BY 
    CASE 
        WHEN ast.cites_status_current = 'I' AND ast.cms_status_current = 'I' THEN 1
        WHEN ast.cites_status_current = 'I' OR ast.cms_status_current = 'I' THEN 2
        WHEN ast.cites_status_current IS NOT NULL AND ast.cms_status_current IS NOT NULL THEN 3
        ELSE 4
    END,
    s.common_name;

-- ============================================
-- Step 5: Summary Statistics with Enhanced CMS Data
-- ============================================

-- CMS listing timeline analysis
SELECT 
    'Longest CMS Protection' as metric,
    MAX(cms_listing_years) || ' years' as value
FROM article_summary_table
WHERE cms_listing_years IS NOT NULL
UNION ALL
SELECT 
    'Average Years Listed in CMS' as metric,
    ROUND(AVG(cms_listing_years), 1) || ' years' as value
FROM article_summary_table
WHERE cms_listing_years IS NOT NULL
UNION ALL
SELECT 
    'Species with Wide Distribution (>20 countries)' as metric,
    COUNT(*)::TEXT as value
FROM article_summary_table
WHERE cms_native_countries_count > 20
UNION ALL
SELECT 
    'High Priority CMS Species' as metric,
    COUNT(*)::TEXT as value
FROM article_summary_table
WHERE cms_conservation_priority = 'High';

-- ============================================
-- Step 6: Arctic "Big 5" with Full Conservation Data
-- ============================================

SELECT 
    s.common_name as "Species",
    -- Basic Info
    ast.iucn_status_current as "IUCN",
    ast.cites_status_current as "CITES",
    ast.cms_status_current as "CMS",
    -- Trade Data
    ast.trade_records_count as "Trade Records",
    ast.trade_trend as "Trade Trend",
    -- CMS Specific
    ast.cms_listing_date as "CMS Since",
    ast.cms_native_countries_count as "Range Countries",
    ast.cms_conservation_priority as "CMS Priority",
    -- Risk Assessment
    CASE 
        WHEN ast.iucn_status_current IN ('CR', 'EN', 'VU') 
         AND ast.cites_status_current = 'I' 
         AND ast.cms_status_current = 'I' THEN '🔴 Critical'
        WHEN ast.iucn_status_current IN ('CR', 'EN', 'VU') 
         AND (ast.cites_status_current = 'I' OR ast.cms_status_current = 'I') THEN '🟠 High Risk'
        WHEN ast.cites_status_current IS NOT NULL 
         AND ast.cms_status_current IS NOT NULL THEN '🟡 Monitored'
        ELSE '🟢 Lower Risk'
    END as "Risk Level"
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
WHERE s.common_name IN ('Polar Bear', 'Narwhal', 'Beluga', 'Bowhead Whale', 'Walrus')
ORDER BY 
    CASE s.common_name
        WHEN 'Polar Bear' THEN 1
        WHEN 'Narwhal' THEN 2
        WHEN 'Beluga' THEN 3
        WHEN 'Bowhead Whale' THEN 4
        WHEN 'Walrus' THEN 5
    END;