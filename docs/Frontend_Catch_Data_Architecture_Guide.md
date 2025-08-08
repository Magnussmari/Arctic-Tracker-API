# Frontend Integration Guide: New Catch Data Architecture

**Date**: June 11, 2025  
**Version**: 1.0  
**For**: Frontend Development Team  
**Subject**: NAMMCO Catch Data Integration

---

## 📋 Executive Summary

The Arctic Tracker database has been restructured to properly handle NAMMCO catch data with normalized relationships. This guide explains the new database schema and provides implementation guidance for frontend integration.

## 🏗️ New Database Architecture

### Core Tables Structure

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│    species      │    │    countries     │    │  management_areas   │
│                 │    │                  │    │                     │
│ • id (PK)       │    │ • id (PK)        │    │ • id (PK)           │
│ • scientific_name│    │ • country_name   │    │ • area_name         │
│ • common_name   │    │ • nammco_member  │    │ • area_type         │
│ • family        │    │                  │    │ • country_id (FK)   │
│ • genus         │    │                  │    │                     │
│ • order_name    │    │                  │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                       │                        │
         │                       │                        │
         └───────────────────────┼────────────────────────┘
                                 │
                    ┌─────────────────────┐
                    │   catch_records     │
                    │                     │
                    │ • id (PK)           │
                    │ • species_id (FK)   │
                    │ • country_id (FK)   │
                    │ • management_area_id│
                    │ • year              │
                    │ • catch_total       │
                    │ • quota_amount      │
                    │ • data_source       │
                    │ • created_at        │
                    └─────────────────────┘
```

## 📊 Data Overview

### Current NAMMCO Dataset
- **4 Countries**: Faroe Islands, Greenland, Iceland, Norway
- **32 Management Areas**: Organized by country with proper relationships
- **958 Catch Records**: Spanning 1992-2023 across 11 marine mammal species
- **11 Species**: Auto-created with proper taxonomic classification

### Species Coverage
- Balaenoptera acutorostrata (Minke whale): 211 records
- Globicephala melas (Pilot whale): 117 records
- Monodon monoceros (Narwhal): 133 records
- Odobenus rosmarus (Walrus): 99 records
- Phocoena phocoena (Harbor porpoise): 93 records
- Orcinus orca (Orca): 84 records
- Delphinapterus leucas (Beluga): 78 records
- Balaenoptera physalus (Fin whale): 51 records
- Hyperoodon ampullatus (Northern bottlenose whale): 45 records
- Lagenorhynchus acutus (Atlantic white-sided dolphin): 32 records
- Megaptera novaeangliae (Humpback whale): 15 records

## 🔧 Frontend Implementation Guide

### 1. Basic Catch Records Query

```sql
-- Get catch records with all related data
SELECT 
    cr.id,
    cr.year,
    cr.catch_total,
    cr.quota_amount,
    cr.data_source,
    s.scientific_name,
    s.common_name,
    s.family,
    c.country_name,
    c.nammco_member,
    ma.area_name,
    ma.area_type
FROM catch_records cr
LEFT JOIN species s ON cr.species_id = s.id
LEFT JOIN countries c ON cr.country_id = c.id
LEFT JOIN management_areas ma ON cr.management_area_id = ma.id
WHERE cr.data_source = 'NAMMCO'
ORDER BY cr.year DESC, s.scientific_name;
```

### 2. Supabase Client Queries

#### Get All Catch Records with Relationships
```javascript
const { data: catchRecords, error } = await supabase
  .from('catch_records')
  .select(`
    id,
    year,
    catch_total,
    quota_amount,
    data_source,
    species:species_id (
      scientific_name,
      common_name,
      family,
      genus,
      order_name
    ),
    country:country_id (
      country_name,
      nammco_member
    ),
    management_area:management_area_id (
      area_name,
      area_type
    )
  `)
  .eq('data_source', 'NAMMCO')
  .order('year', { ascending: false });
```

#### Filter by Species
```javascript
const { data: narwhalRecords, error } = await supabase
  .from('catch_records')
  .select(`
    *,
    species!inner(scientific_name, common_name),
    country(country_name),
    management_area(area_name)
  `)
  .eq('species.scientific_name', 'Monodon monoceros')
  .eq('data_source', 'NAMMCO');
```

#### Filter by Country
```javascript
const { data: greenlandRecords, error } = await supabase
  .from('catch_records')
  .select(`
    *,
    species(scientific_name, common_name),
    country!inner(country_name),
    management_area(area_name)
  `)
  .eq('country.country_name', 'Greenland')
  .eq('data_source', 'NAMMCO');
```

#### Get Summary Statistics
```javascript
// Get catch totals by species
const { data: speciesSummary, error } = await supabase
  .from('catch_records')
  .select(`
    species(scientific_name, common_name),
    catch_total.sum(),
    count()
  `)
  .eq('data_source', 'NAMMCO')
  .not('catch_total', 'is', null);

// Get records by year range
const { data: yearlyData, error } = await supabase
  .from('catch_records')
  .select(`
    year,
    catch_total.sum(),
    count()
  `)
  .eq('data_source', 'NAMMCO')
  .gte('year', 2020)
  .lte('year', 2023);
```

### 3. Management Areas by Country

```javascript
// Get all management areas organized by country
const { data: areasByCountry, error } = await supabase
  .from('management_areas')
  .select(`
    id,
    area_name,
    area_type,
    country:country_id (
      country_name,
      nammco_member
    )
  `)
  .eq('area_type', 'NAMMCO')
  .order('country.country_name');
```

## 📈 Visualization Recommendations

### 1. Time Series Charts
```javascript
// Data structure for catch trends over time
const timeSeriesData = catchRecords.map(record => ({
  year: record.year,
  catch_total: record.catch_total || 0,
  quota_amount: record.quota_amount || 0,
  species: record.species.common_name,
  country: record.country.country_name
}));
```

### 2. Geographic Distribution
```javascript
// Data structure for country-based visualization
const countryData = catchRecords.reduce((acc, record) => {
  const country = record.country.country_name;
  if (!acc[country]) {
    acc[country] = {
      country: country,
      total_catch: 0,
      species_count: new Set(),
      areas: new Set()
    };
  }
  acc[country].total_catch += record.catch_total || 0;
  acc[country].species_count.add(record.species.scientific_name);
  acc[country].areas.add(record.management_area?.area_name);
  return acc;
}, {});
```

### 3. Species Comparison
```javascript
// Data structure for species-based charts
const speciesData = catchRecords.reduce((acc, record) => {
  const species = record.species.scientific_name;
  if (!acc[species]) {
    acc[species] = {
      scientific_name: species,
      common_name: record.species.common_name,
      family: record.species.family,
      total_catch: 0,
      record_count: 0,
      countries: new Set(),
      year_range: { min: Infinity, max: -Infinity }
    };
  }
  acc[species].total_catch += record.catch_total || 0;
  acc[species].record_count += 1;
  acc[species].countries.add(record.country.country_name);
  acc[species].year_range.min = Math.min(acc[species].year_range.min, record.year);
  acc[species].year_range.max = Math.max(acc[species].year_range.max, record.year);
  return acc;
}, {});
```

## 🔍 Filtering and Search Implementation

### 1. Multi-level Filtering
```javascript
const buildCatchRecordsQuery = (filters) => {
  let query = supabase
    .from('catch_records')
    .select(`
      *,
      species(scientific_name, common_name, family),
      country(country_name),
      management_area(area_name)
    `)
    .eq('data_source', 'NAMMCO');

  if (filters.species) {
    query = query.eq('species.scientific_name', filters.species);
  }
  
  if (filters.country) {
    query = query.eq('country.country_name', filters.country);
  }
  
  if (filters.yearStart && filters.yearEnd) {
    query = query.gte('year', filters.yearStart).lte('year', filters.yearEnd);
  }
  
  if (filters.hasQuota !== undefined) {
    if (filters.hasQuota) {
      query = query.not('quota_amount', 'is', null);
    } else {
      query = query.is('quota_amount', null);
    }
  }

  return query;
};
```

### 2. Search Functionality
```javascript
const searchCatchRecords = async (searchTerm) => {
  const { data, error } = await supabase
    .from('catch_records')
    .select(`
      *,
      species(scientific_name, common_name),
      country(country_name),
      management_area(area_name)
    `)
    .or(`
      species.scientific_name.ilike.%${searchTerm}%,
      species.common_name.ilike.%${searchTerm}%,
      country.country_name.ilike.%${searchTerm}%,
      management_area.area_name.ilike.%${searchTerm}%
    `)
    .eq('data_source', 'NAMMCO');
    
  return data;
};
```

## 📱 UI Component Suggestions

### 1. Catch Records Table Component
```jsx
const CatchRecordsTable = ({ filters }) => {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRecords = async () => {
      setLoading(true);
      const query = buildCatchRecordsQuery(filters);
      const { data, error } = await query;
      
      if (!error) {
        setRecords(data);
      }
      setLoading(false);
    };

    fetchRecords();
  }, [filters]);

  return (
    <table>
      <thead>
        <tr>
          <th>Year</th>
          <th>Species</th>
          <th>Country</th>
          <th>Management Area</th>
          <th>Catch Total</th>
          <th>Quota</th>
        </tr>
      </thead>
      <tbody>
        {records.map(record => (
          <tr key={record.id}>
            <td>{record.year}</td>
            <td>{record.species?.common_name}</td>
            <td>{record.country?.country_name}</td>
            <td>{record.management_area?.area_name}</td>
            <td>{record.catch_total || 'N/A'}</td>
            <td>{record.quota_amount || 'No quota'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};
```

### 2. Species Filter Component
```jsx
const SpeciesFilter = ({ onSpeciesChange, selectedSpecies }) => {
  const [species, setSpecies] = useState([]);

  useEffect(() => {
    const fetchSpecies = async () => {
      const { data } = await supabase
        .from('species')
        .select('scientific_name, common_name')
        .in('id', 
          // Get species IDs that have catch records
          supabase.from('catch_records')
            .select('species_id')
            .eq('data_source', 'NAMMCO')
        );
      setSpecies(data);
    };

    fetchSpecies();
  }, []);

  return (
    <select 
      value={selectedSpecies} 
      onChange={(e) => onSpeciesChange(e.target.value)}
    >
      <option value="">All Species</option>
      {species.map(s => (
        <option key={s.scientific_name} value={s.scientific_name}>
          {s.common_name} ({s.scientific_name})
        </option>
      ))}
    </select>
  );
};
```

## ⚠️ Important Notes

### Data Quality Considerations
1. **Missing Values**: Some catch totals may be null (set to 0 during import)
2. **Quota Data**: Not all records have quota information
3. **Year Ranges**: Different species have different year ranges (1992-2023)
4. **Management Areas**: Some areas are country-specific, others are regional

### Performance Optimization
1. **Indexing**: Ensure indexes on frequently queried fields (year, species_id, country_id)
2. **Pagination**: Implement pagination for large result sets
3. **Caching**: Consider caching summary statistics and dropdown options
4. **Lazy Loading**: Load detailed data only when needed

### Error Handling
```javascript
const handleCatchRecordsError = (error) => {
  console.error('Catch records error:', error);
  
  if (error.code === 'PGRST116') {
    // No rows returned
    return [];
  } else if (error.code === 'PGRST301') {
    // Invalid query
    throw new Error('Invalid search parameters');
  } else {
    throw new Error('Failed to fetch catch records');
  }
};
```

## 🚀 Migration from Old Structure

If migrating from a previous structure:

1. **Update all queries** to use the new relationship structure
2. **Replace direct field access** with joined data
3. **Update filtering logic** to work with normalized tables
4. **Test all visualization components** with the new data structure
5. **Update any hardcoded country/area names** to use the normalized values

## 📞 Support

For questions about this new architecture:
- **Database Issues**: Contact backend team
- **Query Optimization**: Review with database administrator
- **Data Validation**: Check validation scripts in `/migration/validate_nammco_data.py`

---

**Last Updated**: June 11, 2025  
**Next Review**: After frontend implementation completion
