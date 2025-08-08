# Arctic Tracker API Reference

## Overview

Arctic Tracker uses Supabase as its backend, providing both REST and GraphQL APIs. All endpoints are automatically generated from the PostgreSQL schema with Row Level Security (RLS) policies.

**Base URL**: `https://cexwrbrnoxqtxjbiujiq.supabase.co`

## Authentication

### Anonymous Access (Public Data)
```javascript
const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
```

### Authenticated Access (Write Operations)
```javascript
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);
```

## Core Endpoints

### 1. Species

#### Get All Species
```javascript
const { data, error } = await supabase
  .from('species')
  .select('*')
  .order('common_name');
```

#### Get Species with Full Details
```javascript
const { data, error } = await supabase
  .from('species')
  .select(`
    *,
    iucn_assessments (*),
    cites_listings (*),
    cms_listings (*),
    common_names (*)
  `)
  .eq('id', speciesId)
  .single();
```

#### Search Species
```javascript
const { data, error } = await supabase
  .from('species')
  .select('*')
  .or(`scientific_name.ilike.%${query}%,common_name.ilike.%${query}%`);
```

### 2. Conservation Status

#### Get Current IUCN Status
```javascript
const { data, error } = await supabase
  .from('iucn_assessments')
  .select('*')
  .eq('species_id', speciesId)
  .eq('is_latest', true)
  .single();
```

#### Get CITES Listing
```javascript
const { data, error } = await supabase
  .from('cites_listings')
  .select('*')
  .eq('species_id', speciesId)
  .eq('is_current', true)
  .single();
```

#### Get CMS Status (NEW)
```javascript
const { data, error } = await supabase
  .from('cms_listings')
  .select('*')
  .eq('species_id', speciesId)
  .single();
```

### 3. Trade Data

#### Get Trade Summary
```javascript
const { data, error } = await supabase
  .from('species_trade_summary')
  .select('*')
  .eq('species_id', speciesId)
  .single();
```

#### Get Trade Records (Paginated)
```javascript
const { data, error, count } = await supabase
  .from('cites_trade_records')
  .select('*', { count: 'exact' })
  .eq('species_id', speciesId)
  .range(0, 99)  // First 100 records
  .order('year', { ascending: false });
```

#### Trade by Year
```javascript
const { data, error } = await supabase
  .from('cites_trade_records')
  .select('year, quantity')
  .eq('species_id', speciesId)
  .gte('year', 2010)
  .lte('year', 2024);
```

### 4. Glossary

#### Search Terms
```javascript
const { data, error } = await supabase
  .rpc('search_glossary_terms', { 
    search_query: 'CITES appendix' 
  });
```

#### Get Terms by Category
```javascript
const { data, error } = await supabase
  .from('glossary_terms')
  .select('*')
  .eq('category', 'Conservation')
  .order('priority', { ascending: false });
```

#### Get Contextual Terms
```javascript
const { data, error } = await supabase
  .from('glossary_contextual_terms')
  .select('*')
  .contains('display_contexts', ['species_card']);
```

### 5. NAMMCO Catch Data

#### Get Catch Records
```javascript
const { data, error } = await supabase
  .from('catch_records')
  .select(`
    *,
    countries (*)
  `)
  .eq('species_id', speciesId)
  .order('year', { ascending: false });
```

## Advanced Queries

### Combined Conservation Status
```javascript
const { data, error } = await supabase
  .from('species')
  .select(`
    id,
    scientific_name,
    common_name,
    iucn_assessments!inner (
      status,
      year_published
    ),
    cites_listings!inner (
      appendix,
      listing_date
    ),
    cms_listings!left (
      appendix,
      native_country_count
    )
  `)
  .eq('iucn_assessments.is_latest', true)
  .eq('cites_listings.is_current', true);
```

### Species with Trade Volume
```javascript
const { data, error } = await supabase
  .from('species_trade_summary')
  .select(`
    *,
    species (
      scientific_name,
      common_name,
      default_image_url
    )
  `)
  .order('total_trade_records', { ascending: false })
  .limit(10);
```

### Geographic Distribution
```javascript
const { data, error } = await supabase
  .from('cms_listings')
  .select(`
    species_id,
    native_distribution,
    distribution_codes,
    species (
      scientific_name,
      common_name
    )
  `)
  .gt('array_length(native_distribution, 1)', 50);
```

## RPC Functions

### Full-Text Search
```javascript
// Search glossary
const { data, error } = await supabase
  .rpc('search_glossary_terms', { 
    search_query: 'endangered species' 
  });

// Get related terms
const { data, error } = await supabase
  .rpc('get_related_glossary_terms', { 
    term_id: 'uuid-here' 
  });
```

## Real-time Subscriptions

### Species Updates
```javascript
const subscription = supabase
  .channel('species-changes')
  .on('postgres_changes', 
    { 
      event: '*', 
      schema: 'public', 
      table: 'species' 
    }, 
    (payload) => {
      console.log('Species changed:', payload);
    }
  )
  .subscribe();
```

### Trade Data Updates
```javascript
const subscription = supabase
  .channel('trade-updates')
  .on('postgres_changes',
    {
      event: 'INSERT',
      schema: 'public',
      table: 'cites_trade_records',
      filter: `species_id=eq.${speciesId}`
    },
    (payload) => {
      console.log('New trade record:', payload);
    }
  )
  .subscribe();
```

## Error Handling

```javascript
try {
  const { data, error } = await supabase
    .from('species')
    .select('*');
    
  if (error) {
    console.error('Database error:', error.message);
    // Handle specific error codes
    if (error.code === '42501') {
      console.error('Row Level Security violation');
    }
  }
} catch (err) {
  console.error('Network error:', err);
}
```

## Pagination

```javascript
const PAGE_SIZE = 20;

async function getSpeciesPage(page = 0) {
  const from = page * PAGE_SIZE;
  const to = from + PAGE_SIZE - 1;
  
  const { data, error, count } = await supabase
    .from('species')
    .select('*', { count: 'exact' })
    .range(from, to)
    .order('common_name');
    
  return {
    data,
    totalPages: Math.ceil(count / PAGE_SIZE),
    currentPage: page
  };
}
```

## Performance Tips

### 1. Select Only Needed Fields
```javascript
// Good - specific fields
const { data } = await supabase
  .from('species')
  .select('id, scientific_name, common_name');

// Avoid - selecting everything
const { data } = await supabase
  .from('species')
  .select('*');
```

### 2. Use Indexes
```javascript
// Indexed columns perform better
const { data } = await supabase
  .from('cites_trade_records')
  .select('*')
  .eq('species_id', id)  // Indexed
  .eq('year', 2024);     // Indexed
```

### 3. Limit Nested Queries
```javascript
// Better - use pre-aggregated data
const { data } = await supabase
  .from('species_trade_summary')
  .select('*')
  .eq('species_id', id);

// Slower - calculating on the fly
const { data } = await supabase
  .from('cites_trade_records')
  .select('quantity')
  .eq('species_id', id);
```

## Rate Limits

- Anonymous requests: 500 per minute
- Authenticated requests: 2000 per minute
- Realtime connections: 200 concurrent

## TypeScript Types

See the following files for TypeScript definitions:
- [`cms_types.ts`](./cms_types.ts) - CMS data types
- [`glossary_types.ts`](./glossary_types.ts) - Glossary types

## GraphQL Alternative

Access the GraphQL endpoint at:
```
https://cexwrbrnoxqtxjbiujiq.supabase.co/graphql/v1
```

Example query:
```graphql
query GetSpeciesWithConservation {
  speciesCollection(
    filter: { class: { eq: "Mammalia" } }
    orderBy: { common_name: AscNullsLast }
  ) {
    edges {
      node {
        id
        scientific_name
        common_name
        iucn_assessments(filter: { is_latest: { eq: true } }) {
          edges {
            node {
              status
              year_published
            }
          }
        }
      }
    }
  }
}
```

## Support

- [Supabase Documentation](https://supabase.com/docs)
- [Arctic Tracker Frontend Guides](./README.md)
- Database schema: [`db_architechture_june25.sql`](../db_architechture_june25.sql)