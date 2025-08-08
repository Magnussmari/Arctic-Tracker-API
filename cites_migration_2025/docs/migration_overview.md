# CITES Migration 2025 - Project Overview

## Project Structure

```
cites_migration_2025/
├── scripts/          # All migration scripts
├── data/            # Source data and species lists
├── docs/            # Documentation and plans
├── backups/         # Database backups
├── extracted_data/  # Filtered Arctic species data
└── logs/           # Migration logs and reports
```

## Migration Approach

### Phase 1: Preparation & Analysis
1. Document current database architecture
2. Create definitive Arctic species list
3. Extract ONLY Arctic species data from CITES database
4. Analyze extracted data quality

### Phase 2: Data Processing
1. Clean and validate extracted data
2. Map species names to database IDs
3. Create staging tables
4. Test data import

### Phase 3: Migration
1. Backup current data
2. Import new Arctic species data
3. Validate and verify
4. Update summary tables

## Key Principle
**Extract First, Migrate Second**: We will NOT migrate 28 million records. Instead, we extract only the ~50,000-100,000 records relevant to Arctic species.

## File Locations
- Source CITES Data: `/species_data/cites_trade/Trade_database_download_v2025.1/`
- Migration Project: `/cites_migration_2025/`
- Target Database: Supabase Arctic Tracker