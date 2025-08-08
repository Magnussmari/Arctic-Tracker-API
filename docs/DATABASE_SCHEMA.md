# Arctic Tracker Database Schema Documentation

**Last Updated**: July 2025  
**Database**: PostgreSQL (Supabase)

## Overview

The Arctic Tracker database is designed to efficiently store and query conservation data for 42 Arctic species. It integrates multiple data sources including CITES trade records, IUCN assessments, CMS listings, and NAMMCO catch data.

## Core Tables

### 1. species
Primary table containing all Arctic species information.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| scientific_name | TEXT | Unique scientific name (Genus species) |
| common_name | TEXT | Primary common name |
| kingdom | TEXT | Taxonomic kingdom (Animalia, Plantae) |
| phylum | TEXT | Taxonomic phylum |
| class | TEXT | Taxonomic class |
| order_name | TEXT | Taxonomic order |
| family | TEXT | Taxonomic family |
| genus | TEXT | Genus name |
| species_name | TEXT | Species epithet |
| authority | TEXT | Naming authority |
| sis_id | INTEGER | IUCN SIS ID |
| inaturalist_id | INTEGER | iNaturalist taxon ID |
| default_image_url | TEXT | Species image URL |
| description | TEXT | General description |
| habitat_description | TEXT | Habitat information |
| population_trend | TEXT | Current population trend |
| population_size | TEXT | Estimated population |
| generation_length | NUMERIC(5,2) | Years per generation |
| movement_patterns | TEXT | Migration/movement info |
| threats_overview | TEXT | Main threats |
| conservation_overview | TEXT | Conservation summary |
| family_id | UUID | FK to families table |
| created_at | TIMESTAMPTZ | Record creation time |

**Indexes**: scientific_name (unique), common_name, class, family

### 2. cites_trade_records
CITES international trade transaction records.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| species_id | UUID | FK to species |
| record_id | TEXT | Original CITES record ID |
| year | INTEGER | Trade year |
| appendix | TEXT | CITES appendix (I, II, III) |
| taxon | TEXT | Taxon as recorded |
| class_name | TEXT | Taxonomic class |
| order_name | TEXT | Taxonomic order |
| family_name | TEXT | Taxonomic family |
| genus_name | TEXT | Genus |
| importer_id | INTEGER | FK to lookup_importers |
| exporter_id | INTEGER | FK to lookup_exporters |
| origin_id | INTEGER | FK to lookup_origins |
| importer_reported_quantity | NUMERIC | Quantity reported by importer |
| exporter_reported_quantity | NUMERIC | Quantity reported by exporter |
| term_id | INTEGER | FK to lookup_terms |
| unit_id | INTEGER | FK to lookup_units |
| purpose_id | INTEGER | FK to lookup_purposes |
| source_id | INTEGER | FK to lookup_sources |
| created_at | TIMESTAMPTZ | Record creation time |

**Indexes**: species_id, year, appendix, (species_id, year)

### 3. iucn_assessments
IUCN Red List conservation assessments.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| species_id | UUID | FK to species |
| year_published | INTEGER | Assessment year |
| is_latest | BOOLEAN | Most recent assessment flag |
| possibly_extinct | BOOLEAN | Possibly extinct flag |
| possibly_extinct_in_wild | BOOLEAN | Possibly extinct in wild |
| status | TEXT | IUCN category (LC, NT, VU, EN, CR, EW, EX) |
| url | TEXT | Assessment URL |
| assessment_id | INTEGER | IUCN assessment ID |
| scope_code | TEXT | Geographic scope code |
| scope_description | TEXT | Geographic scope description |

**Indexes**: species_id, year_published, is_latest

### 4. cites_listings
Current and historical CITES appendix listings.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| species_id | UUID | FK to species |
| appendix | TEXT | CITES appendix (I, II, III) |
| listing_date | DATE | Date of listing |
| notes | TEXT | Listing notes/annotations |
| is_current | BOOLEAN | Current listing flag |

**Indexes**: species_id, is_current, appendix

### 5. cms_listings (NEW)
Convention on Migratory Species listings.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| species_id | UUID | FK to species |
| appendix | TEXT | CMS appendix (I, II, I/II) |
| agreement | TEXT | Agreement name |
| listed_under | TEXT | Scientific name as listed |
| listing_date | TEXT | Date information |
| notes | TEXT | Additional notes |
| native_distribution | TEXT[] | Array of countries |
| distribution_codes | TEXT[] | ISO country codes |
| introduced_distribution | TEXT[] | Introduced countries |
| extinct_distribution | TEXT[] | Countries where extinct |
| distribution_uncertain | TEXT[] | Uncertain distribution |
| created_at | TIMESTAMPTZ | Record creation time |
| updated_at | TIMESTAMPTZ | Last update time |

**Indexes**: species_id, appendix

### 6. glossary_terms (NEW)
Conservation terminology definitions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| term | TEXT | Term/phrase (unique) |
| acronym | TEXT | Acronym if applicable |
| definition | TEXT | Full definition |
| category | TEXT | Category (Conservation, Trade, etc.) |
| subcategory | TEXT | Optional subcategory |
| examples | TEXT | Usage examples |
| related_terms | TEXT[] | Related glossary terms |
| priority | INTEGER | Display priority (0-10) |
| display_contexts | TEXT[] | Where to show tooltips |
| created_at | TIMESTAMPTZ | Record creation time |
| updated_at | TIMESTAMPTZ | Last update time |

**Indexes**: term (unique), category, acronym, priority, full-text search

### 7. species_trade_summary
Pre-aggregated trade statistics for performance.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| species_id | UUID | FK to species |
| total_trade_records | INTEGER | Total number of records |
| year_range | TEXT | "YYYY-YYYY" format |
| top_importers | JSONB | Top 10 importing countries |
| top_exporters | JSONB | Top 10 exporting countries |
| top_purposes | JSONB | Main trade purposes |
| top_terms | JSONB | Main specimen types |
| top_sources | JSONB | Main source codes |
| yearly_totals | JSONB | Trade by year |
| purpose_trends | JSONB | Purpose trends over time |
| created_at | TIMESTAMPTZ | Generation timestamp |
| updated_at | TIMESTAMPTZ | Last update |

**Indexes**: species_id (unique)

### 8. catch_records
NAMMCO catch/harvest data for marine mammals.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| species_id | UUID | FK to species |
| country_id | UUID | FK to countries |
| year | INTEGER | Catch year |
| catch_count | INTEGER | Number caught |
| quota | INTEGER | Quota if applicable |
| notes | TEXT | Additional information |
| source | TEXT | Data source |
| created_at | TIMESTAMPTZ | Record creation time |

**Indexes**: species_id, country_id, year

## Lookup Tables

### Trade Data Lookups
Normalized lookup tables for efficient storage:

- **lookup_importers**: Country codes for importers
- **lookup_exporters**: Country codes for exporters  
- **lookup_origins**: Country codes for origin
- **lookup_terms**: Specimen types (skins, live, etc.)
- **lookup_units**: Measurement units
- **lookup_purposes**: Trade purpose codes
- **lookup_sources**: Source codes (W, C, etc.)

Each lookup table has:
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Value (unique) |

### Supporting Tables

#### families
Taxonomic family information.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| family_name | TEXT | Family name (unique) |
| order_name | TEXT | Order |
| class | TEXT | Class |
| species_count | INTEGER | Number of species |

#### countries
Country reference data.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | TEXT | Country name |
| iso_code | TEXT | ISO 2-letter code |
| iso3_code | TEXT | ISO 3-letter code |
| region | TEXT | Geographic region |
| is_arctic | BOOLEAN | Arctic nation flag |

#### common_names
Multilingual common names.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| species_id | UUID | FK to species |
| name | TEXT | Common name |
| language | TEXT | Language code |
| is_primary | BOOLEAN | Primary name for language |

## Views

### species_trade_overview
Combined view of species with trade statistics.

```sql
CREATE VIEW species_trade_overview AS
SELECT 
    s.*,
    COUNT(DISTINCT t.id) as trade_record_count,
    MIN(t.year) as earliest_trade_year,
    MAX(t.year) as latest_trade_year
FROM species s
LEFT JOIN cites_trade_records t ON s.id = t.species_id
GROUP BY s.id;
```

### species_cms_listings
Species with CMS information and country counts.

```sql
CREATE VIEW species_cms_listings AS
SELECT 
    s.id AS species_id,
    s.scientific_name,
    s.common_name,
    s.class,
    c.appendix AS cms_appendix,
    c.listing_date AS cms_listing_date,
    c.native_distribution,
    array_length(c.native_distribution, 1) AS native_country_count
FROM species s
LEFT JOIN cms_listings c ON s.id = c.species_id;
```

### glossary_by_category
Glossary terms grouped by category.

```sql
CREATE VIEW glossary_by_category AS
SELECT 
    category,
    subcategory,
    COUNT(*) as term_count,
    array_agg(
        json_build_object(
            'id', id,
            'term', term,
            'definition', definition
        )
    ) as terms
FROM glossary_terms
GROUP BY category, subcategory;
```

## Functions

### search_glossary_terms(search_query TEXT)
Full-text search for glossary terms.

```sql
CREATE FUNCTION search_glossary_terms(search_query text)
RETURNS TABLE(
    id uuid,
    term text,
    definition text,
    category text,
    rank real
)
```

### get_conservation_status_changes_for_arctic_species()
Analyze conservation status changes over time.

```sql
CREATE FUNCTION get_conservation_status_changes_for_arctic_species()
RETURNS TABLE(
    scientific_name text,
    status text,
    listing_year integer,
    pre_listing_trend text,
    post_listing_trend text,
    change_direction text
)
```

## Indexes Strategy

### Primary Indexes
- All primary keys (UUID)
- Foreign keys for joins
- Unique constraints (scientific_name, term)

### Performance Indexes
- Composite indexes for common queries
- Partial indexes for filtered queries
- GIN indexes for array columns
- Full-text search indexes

### Example Composite Indexes
```sql
CREATE INDEX idx_trade_species_year 
ON cites_trade_records(species_id, year);

CREATE INDEX idx_assessments_latest 
ON iucn_assessments(species_id) 
WHERE is_latest = true;
```

## Row Level Security (RLS)

### Public Read Access
Most tables allow anonymous read access:
```sql
CREATE POLICY "Allow public read" ON species
FOR SELECT TO public USING (true);
```

### Authenticated Write Access
Only authenticated users with appropriate roles can modify:
```sql
CREATE POLICY "Allow editors to update" ON species
FOR UPDATE TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM profiles 
        WHERE id = auth.uid() 
        AND role IN ('admin', 'editor')
    )
);
```

## Data Integrity

### Constraints
- Foreign key constraints with CASCADE/RESTRICT
- CHECK constraints for valid values
- NOT NULL constraints for required fields
- UNIQUE constraints for natural keys

### Triggers
- Updated_at timestamp triggers
- Data validation triggers
- Audit log triggers (future)

## Performance Considerations

### Table Partitioning
Consider partitioning for:
- cites_trade_records by year
- catch_records by year

### Materialized Views
For expensive aggregations:
- Trade statistics by decade
- Species by conservation status

### Query Optimization
- Use prepared statements
- Batch inserts for bulk data
- Connection pooling
- Query result caching

## Backup and Recovery

### Backup Strategy
- Daily automated backups (Supabase)
- Point-in-time recovery available
- Export scripts for local backups

### Data Recovery
```sql
-- Example recovery from backup
pg_restore -d arctic_tracker backup_file.sql
```

## Future Enhancements

### Planned Tables
- audit_log: Track all data changes
- user_favorites: User-saved species
- data_quality_flags: Mark questionable data
- species_images: Multiple images per species

### Planned Indexes
- Spatial indexes for distribution data
- More specialized text search indexes

---

For the latest schema, see [`db_architechture_june25.sql`](../db_architechture_june25.sql)