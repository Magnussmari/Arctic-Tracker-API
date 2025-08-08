# Arctic Species API - Core Module

This directory contains the core processing scripts for the Arctic Species API. These scripts handle data extraction, optimization, transformation, and loading for CITES trade data and IUCN assessments.

## 🚀 Key Scripts

### Trade Data Pipeline

| Script | Description |
|--------|-------------|
| [`extract_species_trade_data.py`](./extract_species_trade_data.py) | Extracts species-specific trade data from raw CITES CSV files |
| [`optimize_species_trade_json.py`](./optimize_species_trade_json.py) | Compresses trade data through normalization and lookup tables |
| [`load_optimized_trade_data.py`](./load_optimized_trade_data.py) | Loads optimized trade data into Supabase database |
| [`generate_trade_summaries.py`](./generate_trade_summaries.py) | Creates pre-aggregated summaries to improve frontend performance |
| [`validate_before_load.py`](./validate_before_load.py) | Validates trade data before loading into database |

### IUCN Integration

| Script | Description |
|--------|-------------|
| [`rebuild_iucn_assessments.py`](./rebuild_iucn_assessments.py) | Rebuilds IUCN assessment data for Arctic species |
| [`iucn_client.py`](./iucn_client.py) | Client for accessing the IUCN Red List API |
| [`debug_iucn_api.py`](./debug_iucn_api.py) | Debugging utilities for IUCN API integration |

### Utilities and Fixes

| Script | Description |
|--------|-------------|
| [`update_db_architecture_and_species.py`](./update_db_architecture_and_species.py) | Updates database schema and species information |
| [`fix_swapped_names.py`](./fix_swapped_names.py) | Fixes swapped taxonomic names in the database |

## 📊 Data Processing Flow

```
┌───────────────────┐     ┌─────────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│  EXTRACTION       │     │  OPTIMIZATION       │     │  VALIDATION        │     │  LOADING         │
│                   │     │                     │     │                    │     │                  │
│  • CSV parsing    │     │  • Normalization    │     │  • Data quality    │     │  • DB clearing   │
│  • Filtering      │ ──► │  • Compression      │ ──► │  • Schema checks   │ ──► │  • Batch insert  │
│  • Transformation │     │  • Lookup tables    │     │  • Duplication     │     │  • Verification  │
└───────────────────┘     └─────────────────────┘     └────────────────────┘     └──────────────────┘
```

## 🚦 Performance Optimizations

The scripts in this directory implement several optimizations:

1. **Data Normalization** - Repetitive data is extracted into lookup tables
2. **Batch Processing** - Large datasets are processed in memory-efficient batches
3. **Pagination** - Database operations use pagination to handle large record sets
4. **Pre-aggregation** - Trade data is pre-summarized for faster frontend access
5. **Parallel Processing** - Operations are parallelized where appropriate

## 🧪 Testing

Test scripts are provided to validate the functionality of core modules:

- [`test_iucn_v4.py`](./test_iucn_v4.py) - Tests for IUCN API integration
- [`test_rebuild_config.py`](./test_rebuild_config.py) - Tests for rebuild configuration
- [`test_species_extraction.py`](./test_species_extraction.py) - Tests for species extraction process

## 💻 Usage Examples

### Extract Species Trade Data

```bash
python extract_species_trade_data.py --species "Ursus maritimus" --csv-dir "../species_data/cites_trade"
```

### Optimize Trade Data

```bash
python optimize_species_trade_json.py
```

### Load Optimized Data to Database

```bash
python load_optimized_trade_data.py --backup
```

### Generate Trade Summaries for Frontend

```bash
# All species
python generate_trade_summaries.py

# Priority species only (faster)
python generate_trade_summaries.py --priority-only

# Single species
python generate_trade_summaries.py --species-id "d07c1335-0bf5-445c-bcaa-f7cdbd029637"
```

## 📝 Development Notes

- Most scripts use the same logging configuration (file + console output)
- The Supabase client is initialized through the shared `supabase_config.py` module
- All scripts include proper error handling and graceful exit procedures
- Where appropriate, scripts create backups before destructive operations

## 🔄 Trade Data Compression

The trade data optimization process reduces file sizes by:

1. Extracting taxonomic data into lookup tables
2. Creating mappings for countries, terms, and other categorical data
3. Normalizing repetitive structures
4. Removing redundant information

This results in 60-80% reduction in file size while preserving all information.

## 🌐 Database Integration

All scripts connect to the Supabase database using configuration from:

```
../config/supabase_config.py
```

This module handles authentication, connection pooling, and error handling.

## ✅ Current Status

As of May 24, 2025:
- 43 Arctic species fully processed
- 461,042 trade records successfully loaded
- All species have pre-generated trade summaries
- Frontend performance improved from 3-5s to <500ms per species

---

For more detailed information on the overall rebuild process, see the main [CLAUDE.md](../CLAUDE.md) file in the parent directory.