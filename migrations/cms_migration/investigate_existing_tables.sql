-- Investigation Queries for Existing CMS Tables
-- Run these in Supabase SQL Editor to understand current state

-- 1. Check what columns exist in the current cms_listings table
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'cms_listings'
ORDER BY ordinal_position;

-- 2. Check if cms_listings has any data
SELECT COUNT(*) as record_count FROM cms_listings;

-- 3. Check the cms_assessments table structure
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'cms_assessments'
ORDER BY ordinal_position;

-- 4. Check if cms_assessments has any data
SELECT COUNT(*) as record_count FROM cms_assessments;

-- 5. Check what tables exist with 'cms' in the name
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public' 
AND table_name LIKE '%cms%'
ORDER BY table_name;

-- 6. Check if the view exists
SELECT 
    table_name
FROM information_schema.views
WHERE table_schema = 'public' 
AND table_name = 'species_cms_listings';