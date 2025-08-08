# CMS Data Frontend Integration Guide

**Date**: July 10, 2025  
**For**: Arctic Tracker Frontend Development Team  
**New Feature**: Convention on Migratory Species (CMS) Data Integration

## Executive Summary

We've successfully integrated CMS (Convention on the Conservation of Migratory Species) data into the Arctic Tracker database. This adds important conservation status information for 31 of our 42 tracked Arctic species, complementing the existing CITES trade data.

## What is CMS?

The Convention on the Conservation of Migratory Species (CMS), also known as the Bonn Convention, is an international agreement that aims to conserve migratory species throughout their range. Species are listed in two appendices:

- **Appendix I**: Endangered migratory species (strictest protection)
- **Appendix II**: Species that need or would benefit from international cooperation
- **Appendix I/II**: Species listed in both appendices

## Database Changes

### New Table: `cms_listings`

```sql
CREATE TABLE cms_listings (
    id UUID PRIMARY KEY,
    species_id UUID REFERENCES species(id),
    appendix TEXT,              -- 'I', 'II', or 'I/II'
    agreement TEXT,             -- Usually 'CMS'
    listed_under TEXT,          -- Scientific name as listed
    listing_date TEXT,          -- Date of listing
    notes TEXT,                 -- Additional notes
    native_distribution TEXT[], -- Array of countries
    distribution_codes TEXT[],  -- ISO country codes
    introduced_distribution TEXT[],
    extinct_distribution TEXT[],
    distribution_uncertain TEXT[],
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### New View: `species_cms_listings`

A convenient view that joins species with their CMS data:

```sql
SELECT 
    s.id AS species_id,
    s.scientific_name,
    s.common_name,
    s.class,
    s.order_name,
    s.family,
    c.appendix AS cms_appendix,
    c.listing_date AS cms_listing_date,
    c.native_distribution,
    c.distribution_codes,
    array_length(c.native_distribution, 1) AS native_country_count
FROM species s
LEFT JOIN cms_listings c ON s.id = c.species_id;
```

## API Endpoints

### GraphQL Queries

The Supabase auto-generated GraphQL API now includes:

```graphql
# Get all CMS listings
query GetCMSListings {
  cms_listingsCollection {
    edges {
      node {
        id
        species_id
        appendix
        native_distribution
        distribution_codes
      }
    }
  }
}

# Get species with CMS data
query GetSpeciesWithCMS($speciesId: UUID!) {
  speciesCollection(filter: {id: {eq: $speciesId}}) {
    edges {
      node {
        id
        scientific_name
        common_name
        cms_listings {
          appendix
          listing_date
          native_distribution
          native_country_count
        }
      }
    }
  }
}
```

### REST API Endpoints

```javascript
// Get CMS data for a species
const { data, error } = await supabase
  .from('cms_listings')
  .select('*')
  .eq('species_id', speciesId)
  .single();

// Get all species with CMS listings
const { data, error } = await supabase
  .from('species_cms_listings')
  .select('*')
  .not('cms_appendix', 'is', null)
  .order('scientific_name');

// Get species by CMS appendix
const { data, error } = await supabase
  .from('cms_listings')
  .select(`
    *,
    species (
      scientific_name,
      common_name,
      default_image_url
    )
  `)
  .eq('appendix', 'I')
  .order('species.scientific_name');
```

## Frontend Integration Recommendations

### 1. Species Detail Page Enhancement

Add a new "International Agreements" section showing both CITES and CMS status:

```jsx
// Conservation Status Card
<Card>
  <CardHeader>
    <h3>International Conservation Status</h3>
  </CardHeader>
  <CardContent>
    <div className="conservation-badges">
      {citesAppendix && (
        <Badge variant="cites" color={getCITESColor(citesAppendix)}>
          CITES Appendix {citesAppendix}
        </Badge>
      )}
      {cmsAppendix && (
        <Badge variant="cms" color={getCMSColor(cmsAppendix)}>
          CMS Appendix {cmsAppendix}
        </Badge>
      )}
    </div>
  </CardContent>
</Card>
```

### 2. Distribution Map Enhancement

Use the CMS distribution data to create interactive maps:

```jsx
// Distribution Map Component
<DistributionMap>
  <MapLegend>
    <LegendItem color="green">Native Range ({nativeCountries.length} countries)</LegendItem>
    <LegendItem color="orange">Introduced ({introducedCountries.length} countries)</LegendItem>
    <LegendItem color="red">Extinct ({extinctCountries.length} countries)</LegendItem>
  </MapLegend>
  {renderCountries(distribution_codes, 'native')}
</DistributionMap>
```

### 3. Species List Filtering

Add CMS status as a filter option:

```jsx
// Filter Component
<FilterGroup label="Conservation Agreements">
  <FilterCheckbox value="cites" label="CITES Listed" />
  <FilterCheckbox value="cms-i" label="CMS Appendix I" />
  <FilterCheckbox value="cms-ii" label="CMS Appendix II" />
  <FilterCheckbox value="no-cms" label="Not in CMS" />
</FilterGroup>
```

### 4. Conservation Dashboard

Create a summary view showing conservation status:

```jsx
// Conservation Overview
<Grid>
  <StatCard
    title="CMS Appendix I"
    count={7}
    description="Endangered migratory species"
    species={['Bowhead Whale', 'Blue Whale', 'North Atlantic Right Whale']}
  />
  <StatCard
    title="CMS Appendix II"
    count={16}
    description="Species benefiting from cooperation"
    species={['Polar Bear', 'Narwhal', 'Beluga']}
  />
  <StatCard
    title="Both Appendices"
    count={8}
    description="Listed in I and II"
    species={['Sei Whale', 'Fin Whale', 'Sperm Whale']}
  />
</Grid>
```

## Data Summary

### Arctic Species in CMS by Category

**Marine Mammals (18 species)**
- Appendix I: 4 species (Right Whales, Blue Whale, Humpback)
- Appendix II: 10 species (Beluga, Narwhal, Orcas, etc.)
- Appendix I/II: 4 species (Sei, Fin, Sperm Whales, Harbour Porpoise)

**Birds (5 species)**
- Appendix I: 2 species (Siberian Crane, Short-tailed Albatross)
- Appendix II: 2 species (Peregrine Falcon, Gyrfalcon)
- Appendix I/II: 1 species (Red-breasted Goose)

**Fish & Sharks (4 species)**
- Appendix I: 1 species (Cuvier's Beaked Whale)
- Appendix II: 3 species (Thresher Shark, Porbeagle, Siberian Sturgeon)
- Appendix I/II: 1 species (Basking Shark)

**Terrestrial Mammals (1 species)**
- Appendix II: 1 species (Polar Bear)

### Notable Species NOT in CMS (12 total)
- Walrus (Odobenus rosmarus)
- Sea Otter (Enhydra lutris)
- Canada Lynx (Lynx canadensis)
- Snowy Owl (Nyctea scandiaca)
- Gray Whale (Eschrichtius robustus)
- Minke Whale (Balaenoptera acutorostrata)

## UI/UX Recommendations

### 1. Visual Distinction
- Use different colors/icons for CITES vs CMS badges
- Suggested color scheme:
  - CMS Appendix I: Deep red (#D32F2F)
  - CMS Appendix II: Orange (#F57C00)
  - CMS Appendix I/II: Purple (#7B1FA2)

### 2. Tooltips and Education
Add informative tooltips explaining what CMS listing means:

```jsx
<Tooltip content={
  <div>
    <h4>CMS Appendix {appendix}</h4>
    <p>{appendix === 'I' 
      ? 'Endangered migratory species requiring strict protection'
      : 'Species that would benefit from international cooperation'
    }</p>
    <p>Listed since: {listing_date}</p>
  </div>
}>
  <Badge>CMS {appendix}</Badge>
</Tooltip>
```

### 3. Distribution Visualization
- Interactive world map showing species range
- Highlight migratory routes if available
- Show country count as a metric

### 4. Comparison Features
Enable users to compare CITES and CMS status:
- Side-by-side conservation status
- Timeline showing when species were listed
- Correlation between trade (CITES) and migration (CMS) protection

## Sample React Component

```jsx
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/lib/supabase';

export function SpeciesCMSStatus({ speciesId }) {
  const { data: cmsData, isLoading } = useQuery({
    queryKey: ['cms-listing', speciesId],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('cms_listings')
        .select('*')
        .eq('species_id', speciesId)
        .single();
      
      if (error) throw error;
      return data;
    }
  });

  if (isLoading) return <Skeleton />;
  if (!cmsData) return null;

  return (
    <div className="cms-status">
      <div className="flex items-center gap-2">
        <Badge variant="cms" color={getCMSColor(cmsData.appendix)}>
          CMS Appendix {cmsData.appendix}
        </Badge>
        <span className="text-sm text-gray-500">
          {cmsData.native_distribution.length} countries
        </span>
      </div>
      
      {cmsData.notes && (
        <p className="text-sm mt-2">{cmsData.notes}</p>
      )}
      
      <DistributionList countries={cmsData.native_distribution} />
    </div>
  );
}
```

## Testing Queries

Use these queries in Supabase SQL editor to verify data:

```sql
-- Count species by CMS appendix
SELECT 
    appendix,
    COUNT(*) as species_count
FROM cms_listings
GROUP BY appendix
ORDER BY appendix;

-- Get all Arctic species with both CITES and CMS listings
SELECT 
    s.scientific_name,
    s.common_name,
    ci.appendix as cites_appendix,
    cm.appendix as cms_appendix
FROM species s
LEFT JOIN cites_listings ci ON s.id = ci.species_id AND ci.is_current = true
LEFT JOIN cms_listings cm ON s.id = cm.species_id
WHERE cm.appendix IS NOT NULL OR ci.appendix IS NOT NULL
ORDER BY s.scientific_name;

-- Species with widest distribution
SELECT 
    s.scientific_name,
    s.common_name,
    c.appendix,
    array_length(c.native_distribution, 1) as country_count
FROM species s
JOIN cms_listings c ON s.id = c.species_id
ORDER BY country_count DESC
LIMIT 10;
```

## Next Steps

1. **Immediate Actions**
   - Add CMS status badges to species detail pages
   - Include CMS filter in species list view
   - Update conservation status display components

2. **Future Enhancements**
   - Interactive distribution maps
   - Migration route visualizations
   - CMS/CITES correlation analysis
   - Timeline of conservation listings

3. **Data Updates**
   - Set up periodic checks for CMS listing updates
   - Consider adding historical CMS listing data
   - Integrate with other conservation agreements

## Support

For questions about the CMS data integration:
- Database queries: Check the `cms_listings` table structure
- API issues: Review the Supabase auto-generated docs
- Data accuracy: Refer to the source file `cms_arctic_species_summary.md`

---

**Note**: Remember to update your TypeScript types to include the new CMS fields in your species interfaces.