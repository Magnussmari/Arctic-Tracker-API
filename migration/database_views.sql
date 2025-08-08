-- This creates a view that pre-joins all the data we need
CREATE OR REPLACE VIEW species_with_status_view AS
SELECT 
    s.*,
    -- Latest IUCN Assessment data
    latest_iucn.status as latest_iucn_status,
    latest_iucn.year_published as latest_iucn_year,
    latest_iucn.is_latest as has_iucn_assessment,
    
    -- Current CITES Listing data  
    current_cites.appendix as current_cites_appendix,
    current_cites.listing_date as current_cites_date,
    current_cites.notes as current_cites_notes,
    current_cites.is_current as has_cites_listing,
    
    -- Primary common name (first alphabetically for consistency)
    primary_cn.name as primary_common_name

FROM species s
LEFT JOIN iucn_assessments latest_iucn ON (
    s.id = latest_iucn.species_id AND latest_iucn.is_latest = true
)
LEFT JOIN cites_listings current_cites ON (
    s.id = current_cites.species_id AND current_cites.is_current = true
)
LEFT JOIN LATERAL (
    SELECT name FROM common_names cn 
    WHERE cn.species_id = s.id 
    ORDER BY cn.name ASC LIMIT 1
) primary_cn ON true
ORDER BY s.scientific_name;

-- Standardize family names: proper case, remove spaces, fix known variants

-- General cleanup: Proper case and trim spaces
UPDATE species 
SET family = INITCAP(TRIM(family))
WHERE family IS NOT NULL;

-- Specific normalization for known families (add more as needed)
UPDATE species 
SET family = 
  CASE 
    WHEN UPPER(TRIM(family)) = 'URSIDAE' THEN 'Ursidae'
    WHEN UPPER(TRIM(family)) = 'PHOCIDAE' THEN 'Phocidae'
    WHEN UPPER(TRIM(family)) = 'ACCIPITRIDAE' THEN 'Accipitridae'
    -- Add other family normalizations as needed
    ELSE INITCAP(TRIM(family))
  END
WHERE family IS NOT NULL;