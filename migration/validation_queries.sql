-- Validation queries for NAMMCO data import
-- Run these after importing to verify data integrity

-- 1. Overall import statistics
SELECT 
    'Total NAMMCO Records' as metric,
    COUNT(*) as value
FROM catch_records 
WHERE data_source = 'NAMMCO'

UNION ALL

SELECT 
    'Unique Species',
    COUNT(DISTINCT species_id)
FROM catch_records 
WHERE data_source = 'NAMMCO'

UNION ALL

SELECT 
    'Unique Countries',
    COUNT(DISTINCT country_id)
FROM catch_records 
WHERE data_source = 'NAMMCO'

UNION ALL

SELECT 
    'Management Areas',
    COUNT(DISTINCT management_area_id)
FROM catch_records 
WHERE data_source = 'NAMMCO' AND management_area_id IS NOT NULL;

-- 2. Records by country
SELECT 
    'Records by Country' as section,
    c.country_name,
    COUNT(*) as record_count,
    SUM(cr.catch_total) as total_catch
FROM catch_records cr
JOIN countries c ON cr.country_id = c.id
WHERE cr.data_source = 'NAMMCO'
GROUP BY c.country_name
ORDER BY record_count DESC;

-- 3. Records by species (top 10)
SELECT 
    'Top Species by Records' as section,
    s.name as species_name,
    COUNT(*) as record_count,
    SUM(cr.catch_total) as total_catch
FROM catch_records cr
JOIN species s ON cr.species_id = s.id
WHERE cr.data_source = 'NAMMCO'
GROUP BY s.name
ORDER BY record_count DESC
LIMIT 10;

-- 4. Year range validation
SELECT 
    'Year Range' as metric,
    MIN(year) || ' - ' || MAX(year) as value
FROM catch_records 
WHERE data_source = 'NAMMCO' 
AND year ~ '^[0-9]{4}$';

-- 5. Data quality checks
SELECT 
    'Data Quality Issues' as section,
    'Records with NULL catch_total' as issue,
    COUNT(*) as count
FROM catch_records 
WHERE data_source = 'NAMMCO' AND catch_total IS NULL

UNION ALL

SELECT 
    'Data Quality Issues',
    'Records with zero catch',
    COUNT(*)
FROM catch_records 
WHERE data_source = 'NAMMCO' AND catch_total = 0

UNION ALL

SELECT 
    'Data Quality Issues',
    'Records with quotas',
    COUNT(*)
FROM catch_records 
WHERE data_source = 'NAMMCO' AND quota_amount IS NOT NULL

UNION ALL

SELECT 
    'Data Quality Issues',
    'Records with no quota notes',
    COUNT(*)
FROM catch_records 
WHERE data_source = 'NAMMCO' AND quota_notes = 'No quota';

-- 6. Management areas summary
SELECT 
    'Management Areas' as section,
    ma.area_type,
    COUNT(DISTINCT ma.id) as unique_areas,
    COUNT(cr.id) as total_records
FROM management_areas ma
LEFT JOIN catch_records cr ON ma.id = cr.management_area_id AND cr.data_source = 'NAMMCO'
GROUP BY ma.area_type
ORDER BY total_records DESC;

-- 7. Check for potential duplicates
SELECT 
    'Potential Duplicates' as section,
    s.name as species_name,
    c.country_name,
    year,
    COUNT(*) as duplicate_count
FROM catch_records cr
JOIN species s ON cr.species_id = s.id
JOIN countries c ON cr.country_id = c.id
WHERE cr.data_source = 'NAMMCO'
GROUP BY s.name, c.country_name, year, management_area_id
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- 8. Sample data check
SELECT 
    'Sample Records' as section,
    s.name as species,
    c.country_name as country,
    ma.area_name as area,
    cr.year,
    cr.catch_total,
    cr.quota_amount,
    cr.quota_notes
FROM catch_records cr
JOIN species s ON cr.species_id = s.id
JOIN countries c ON cr.country_id = c.id
LEFT JOIN management_areas ma ON cr.management_area_id = ma.id
WHERE cr.data_source = 'NAMMCO'
ORDER BY cr.created_at DESC
LIMIT 10;
