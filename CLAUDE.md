# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the rebuild directory for the Arctic Species CITES trade data import system. The project focuses on analyzing and managing CITES (Convention on International Trade in Endangered Species) trade data for Arctic species, with integration to IUCN Red List assessments.

## Directory Structure

The rebuild directory is organized into the following modules:

- `/config` - Configuration files, database connections, and environment variables
- `/core` - Core business logic and data processing scripts
- `/docs` - Project documentation and reports
- `/species_data` - Species data files, CITES trade data, and processed datasets
- `/tests` - Testing infrastructure
- `/validation` - Data validation utilities

## Key Scripts and Command Usage

### Data Pipeline Scripts

#### 1. Extract Species Trade Data
```bash
# Full extraction of all species
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/core
python extract_species_trade_data.py --mode full

# Incremental extraction (only missing species)
python extract_species_trade_data.py --mode incremental
```

#### 2. Optimize Species Trade Data
```bash
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/core
python optimize_species_trade_json.py
```

#### 3. Validate Before Loading
```bash
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/core
python validate_before_load.py
```

#### 4. Load Optimized Trade Data
```bash
# Create backup and load data
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/core
python load_optimized_trade_data.py --backup

# Test run without making changes
python load_optimized_trade_data.py --dry-run

# Customize batch size
python load_optimized_trade_data.py --backup --batch-size 500
```

#### 5. Upload Species Profiles
```bash
# Create logs directory (required before first run)
cd /Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/core
mkdir -p logs

# Dry run to validate JSON files
python upload_species_profiles.py --dry-run

# Live upload of species profiles
python upload_species_profiles.py
```

### Database Utilities

```bash
# Test Supabase connection
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/config
python supabase_config.py

# Update database architecture report
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/core
python update_db_architecture_and_species.py
```

## Database Information

- **Production Supabase Database**: `https://cexwrbrnoxqtxjbiujiq.supabase.co`
- **Connection**: Managed via `config/supabase_config.py` and `.env` credentials
- **Main Tables**: 
  - `species` - Primary species data with taxonomic hierarchy
  - `cites_trade_records` - CITES trade transaction data
  - `iucn_assessments` - IUCN Red List conservation assessments
  - `cites_listings` - CITES appendix classifications
  - `common_names` - Multilingual common name support

## Core Architecture

The system follows a data pipeline architecture:

1. **Extraction**: Extract species-specific trade records from CITES CSV files
2. **Optimization**: Convert extracted data into optimized, normalized format
3. **Validation**: Verify data integrity before loading
4. **Loading**: Safely load optimized data into the Supabase database

Key architectural components:
- Supabase client for database operations
- Data normalization via lookup tables
- Memory-efficient batch processing
- Comprehensive error handling and logging

## File Naming Conventions

- Python Files: `snake_case_descriptive.py` (e.g., `extract_species_trade_data.py`)
- Python Classes: `PascalCase` (e.g., `SpeciesTradeExtractor`)
- Methods/Functions: `snake_case_verb_noun()` (e.g., `load_species_mapping()`)
- Private Methods: `_snake_case()` with leading underscore (e.g., `_safe_int()`)
- Data Files: `Snake_Case_Purpose.json[.gz]` (e.g., `Ursus_maritimus_trade_data.json`)
- Log Files: `purpose_timestamp.log` (e.g., `trade_data_load_20250524_202153.log`)
- Backup Files: `purpose_backup_timestamp.json` (e.g., `trade_data_backup_20250524_201142.json`)

## Important Notes

1. **Large Datasets**: The system handles massive CITES trade CSV files, requiring memory-efficient processing.
2. **Supabase Integration**: All database operations use the Supabase client configured in `config/supabase_config.py`.
3. **Error Handling**: All scripts include comprehensive error handling and logging.
4. **Backup Before Loading**: Always create a backup before loading data with the `--backup` flag.
5. **Data Validation**: Run the validation script before loading to ensure data integrity.

## Current Project Status (July 2025)

- Successfully loaded optimized trade data on May 24, 2025
- Completed data optimization with 60-80% file size reduction
- Created comprehensive documentation in `/docs`
- Completed AI-driven species profile generation workflow (July 10, 2025)
- Successfully uploaded 14 species conservation profiles to database
- Integrated scientific research data from Scite AI with proper citations
- Enhanced species table with detailed conservation information