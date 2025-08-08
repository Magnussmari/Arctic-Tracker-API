# Arctic Tracker Database Update Guide

## Overview

This guide provides step-by-step instructions to update your existing Arctic Tracker database schema and import the scraped NAMMCO catch data.

## Current Data Status

Based on the file manifest, you have **18 species** with **958 total records** ready for import:

- **11 species with catch data** (948 records)
- **7 species with zero catches** (10 empty files)
- Data covers years 1992-2023
- Countries: Greenland, Norway, Iceland, Faroe Islands

## Step 1: Database Schema Updates

### Current Schema Issues
Your existing `catch_records` table has limitations:
- Uses UUID references for species without proper taxonomy
- Missing management area structure
- Limited quota handling
- No data quality tracking

### Required Schema Changes

#### 1. Add Species Taxonomy Table
```sql
-- Create proper species taxonomy
CREATE TABLE IF NOT EXISTS species_taxonomy (
    id SERIAL PRIMARY KEY,
    species_id UUID REFERENCES species(id),
    kingdom VARCHAR(100),
    phylum VARCHAR(100),
    class VARCHAR(100),
    order_name VARCHAR(100),
    family VARCHAR(100),
    genus VARCHAR(100),
    species VARCHAR(100),
    subspecies VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. Add Countries Table
```sql
CREATE TABLE IF NOT EXISTS countries (
    id SERIAL PRIMARY KEY,
    country_name VARCHAR(100) UNIQUE NOT NULL,
    country_code VARCHAR(3),
    nammco_member BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert NAMMCO member countries
INSERT INTO countries (country_name, nammco_member) VALUES
('Greenland', TRUE),
('Norway', TRUE),
('Iceland', TRUE),
('Faroe Islands', TRUE)
ON CONFLICT (country_name) DO UPDATE SET nammco_member = EXCLUDED.nammco_member;
```

#### 3. Add Management Areas Table
```sql
CREATE TABLE IF NOT EXISTS management_areas (
    id SERIAL PRIMARY KEY,
    area_name VARCHAR(200) NOT NULL,
    country_id INTEGER REFERENCES countries(id),
    area_type VARCHAR(50), -- 'zone', 'region', 'stock', 'total', etc.
    parent_area_id INTEGER REFERENCES management_areas(id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(area_name, country_id)
);
```

#### 4. Add Quotas Table
```sql
CREATE TABLE IF NOT EXISTS quotas (
    id SERIAL PRIMARY KEY,
    species_id UUID REFERENCES species(id),
    country_id INTEGER REFERENCES countries(id),
    management_area_id INTEGER REFERENCES management_areas(id),
    year_or_season VARCHAR(20),
    quota_amount INTEGER,
    quota_status VARCHAR(50), -- 'active', 'no_quota', 'suspended'
    notes TEXT,
    source VARCHAR(50) DEFAULT 'NAMMCO',
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 5. Update Catch Records Table
```sql
-- Add new columns to existing catch_records table
ALTER TABLE catch_records 
ADD COLUMN IF NOT EXISTS management_area_id INTEGER REFERENCES management_areas(id),
ADD COLUMN IF NOT EXISTS quota_id INTEGER REFERENCES quotas(id),
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'NAMMCO',
ADD COLUMN IF NOT EXISTS data_quality_score INTEGER CHECK (data_quality_score BETWEEN 1 AND 5),
ADD COLUMN IF NOT EXISTS verification_status VARCHAR(20) DEFAULT 'imported',
ADD COLUMN IF NOT EXISTS notes TEXT;

-- Update country column to reference countries table
ALTER TABLE catch_records 
ADD COLUMN IF NOT EXISTS country_id INTEGER REFERENCES countries(id);

-- Update country_id based on existing country names
UPDATE catch_records SET country_id = c.id 
FROM countries c 
WHERE catch_records.country = c.country_name;
```

#### 6. Create Indexes for Performance
```sql
CREATE INDEX IF NOT EXISTS idx_catch_records_species_year ON catch_records(species_id, year);
CREATE INDEX IF NOT EXISTS idx_catch_records_country_year ON catch_records(country_id, year);
CREATE INDEX IF NOT EXISTS idx_catch_records_area ON catch_records(management_area_id);
CREATE INDEX IF NOT EXISTS idx_quotas_species_year ON quotas(species_id, year_or_season);
```

## Step 2: Species Data Preparation

### Create Species Mapping
First, map your existing species UUIDs to the NAMMCO scientific names:

```sql
-- Create a temporary mapping table
CREATE TEMPORARY TABLE species_mapping AS
SELECT 
    s.id as species_uuid,
    s.name as current_name,
    CASE 
        WHEN s.name ILIKE '%narwhal%' THEN 'Monodon monoceros'
        WHEN s.name ILIKE '%walrus%' THEN 'Odobenus rosmarus'
        WHEN s.name ILIKE '%beluga%' THEN 'Delphinapterus leucas'
        WHEN s.name ILIKE '%minke%' THEN 'Balaenoptera acutorostrata'
        WHEN s.name ILIKE '%pilot%' THEN 'Globicephala melas'
        WHEN s.name ILIKE '%porpoise%' THEN 'Phocoena phocoena'
        WHEN s.name ILIKE '%humpback%' THEN 'Megaptera novaeangliae'
        WHEN s.name ILIKE '%fin whale%' THEN 'Balaenoptera physalus'
        WHEN s.name ILIKE '%killer%' OR s.name ILIKE '%orca%' THEN 'Orcinus orca'
        WHEN s.name ILIKE '%bottlenose%' THEN 'Hyperoodon ampullatus'
        WHEN s.name ILIKE '%white-sided%' THEN 'Lagenorhynchus acutus'
        -- Add more mappings as needed
        ELSE NULL
    END as scientific_name
FROM species s;
```

## Step 3: Data Import Process

### Import Order
1. **Countries** (already done above)
2. **Species** (update existing or create new)
3. **Management Areas** (from CSV AREA OR STOCK column)
4. **Quotas** (from CSV QUOTA column)
5. **Catch Records** (main data import)

### Import Script Structure

Create a simple Python import script:

```python
import pandas as pd
import psycopg2
from pathlib import Path

def import_nammco_data():
    # Database connection
    conn = psycopg2.connect("your_connection_string")
    cur = conn.cursor()
    
    csv_dir = Path("output/csv")
    
    for csv_file in csv_dir.glob("*.csv"):
        print(f"Processing {csv_file.name}")
        
        # Read CSV
        df = pd.read_csv(csv_file)
        
        # Skip empty files
        if len(df) == 0:
            continue
            
        # Process each row
        for _, row in df.iterrows():
            if pd.isna(row.get('COUNTRY')):
                continue
                
            # 1. Get/Create species
            species_id = get_or_create_species(cur, 
                row['SPECIES (SCIENTIFIC NAME)'], 
                row['SPECIES (COMMON NAME)'])
            
            # 2. Get country ID
            country_id = get_country_id(cur, row['COUNTRY'])
            
            # 3. Get/Create management area
            area_id = get_or_create_area(cur, 
                row.get('AREA OR STOCK', ''), 
                country_id)
            
            # 4. Create quota if applicable
            quota_id = create_quota(cur, species_id, country_id, 
                area_id, row['YEAR OR SEASON'], 
                row.get('QUOTA (IF APPLICABLE)', ''))
            
            # 5. Insert catch record
            insert_catch_record(cur, species_id, country_id, 
                area_id, quota_id, row)
    
    conn.commit()
    conn.close()
```

## Step 4: File-by-File Import Status

Based on your current data:

### High Priority (Species with Substantial Data)
1. **Balaenoptera acutorostrata** (Common minke whale) - 211 records
2. **Globicephala melas** (Long-finned pilot whale) - 117 records  
3. **Monodon monoceros** (Narwhal) - 133 records
4. **Odobenus rosmarus** (Atlantic walrus) - 99 records
5. **Phocoena phocoena** (Harbour porpoise) - 93 records
6. **Orcinus orca** (Killer whale) - 84 records
7. **Delphinapterus leucas** (Beluga) - 78 records

### Medium Priority (Moderate Data)
8. **Balaenoptera physalus** (Fin whale) - 51 records
9. **Hyperoodon ampullatus** (Northern bottlenose whale) - 45 records
10. **Lagenorhynchus acutus** (Atlantic white-sided dolphin) - 32 records
11. **Megaptera novaeangliae** (Humpback whale) - 15 records

### Low Priority (Zero Catch Species)
12. **Physeter macrocephalus** (Sperm Whale) - 0 records
13. **Balaenoptera musculus** (Blue Whale) - 0 records
14. **Mesoplodon stejnegeri** (Stejneger's Beaked Whale) - 0 records
15. **Phocoenoides dalli** (Dall's Porpoise) - 0 records
16. **Balaenoptera borealis** (Sei Whale) - 0 records
17. **Ziphius cavirostris** (Cuvier's Beaked Whale) - 0 records
18. **Berardius bairdii** (Baird's Beaked Whale) - 0 records

## Step 5: Data Validation

After import, run these validation queries:

```sql
-- Check import totals
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT species_id) as unique_species,
    COUNT(DISTINCT country_id) as unique_countries,
    MIN(year) as earliest_year,
    MAX(year) as latest_year
FROM catch_records 
WHERE data_source = 'NAMMCO';

-- Check species distribution
SELECT 
    s.name,
    COUNT(*) as record_count
FROM catch_records cr
JOIN species s ON cr.species_id = s.id
WHERE cr.data_source = 'NAMMCO'
GROUP BY s.name
ORDER BY record_count DESC;

-- Check for data quality issues
SELECT 
    data_quality_score,
    COUNT(*) as count
FROM catch_records 
WHERE data_source = 'NAMMCO'
GROUP BY data_quality_score;
```

## Step 6: Cleanup and Optimization

After successful import:

1. **Remove old data** if replacing existing NAMMCO data
2. **Update application queries** to use new schema
3. **Test frontend** with new data structure
4. **Create backup** of updated database

## Quick Start Commands

```bash
# 1. Update database schema
psql -d arctic_tracker -f schema_updates.sql

# 2. Run import script
python import_nammco_simple.py

# 3. Validate data
psql -d arctic_tracker -f validation_queries.sql
```

## Summary

- **Total Records to Import**: 958 across 18 species
- **Database Changes**: 4 new tables, 6 new columns
- **Import Time**: Estimated 5-10 minutes
- **Key Focus**: Species with substantial data (11 species, 948 records)

This approach keeps it simple: update schema, import CSV files one by one, validate results.
