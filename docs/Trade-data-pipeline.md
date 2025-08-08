# CITES Trade Data Pipeline

**Last Updated: May 24, 2025**

This document describes the complete data pipeline for processing CITES trade data for Arctic species, from raw CSV files to the optimized database records.

## Naming Conventions

The pipeline follows these naming conventions:

### Files and Classes

| Entity Type | Convention | Example |
|-------------|------------|---------|
| Python Files | `snake_case_descriptive.py` | `extract_species_trade_data.py` |
| Python Classes | `PascalCase` | `SpeciesTradeExtractor` |
| Methods/Functions | `snake_case_verb_noun` | `load_species_mapping()` |
| Private Methods | `_snake_case` with leading underscore | `_safe_int()` |
| Data Files | `Snake_Case_Purpose.json[.gz]` | `Ursus_maritimus_trade_data.json` |
| Log Files | `purpose_timestamp.log` | `trade_data_load_20250524_202153.log` |
| Backup Files | `purpose_backup_timestamp.json` | `trade_data_backup_20250524_201142.json` |

### Database Tables

| Table Name | Convention | Example |
|------------|------------|---------|
| Tables | `snake_case_plural` | `cites_trade_records` |
| Columns | `snake_case` | `scientific_name`, `record_id` |
| Foreign Keys | `entity_id` | `species_id` |
| Primary Keys | `id` (UUID) | `id` |

### Data Fields

The pipeline maintains consistent field naming across all stages:
- Raw CSV fields retain original capitalization: `Taxon`, `Year`, `Appendix`
- Processed fields use lowercase snake_case: `scientific_name`, `quantity_normalized`
- Optimized fields reference IDs: `taxonomic_id`, `location_id`

## Data Flow and File Naming Strategy

The pipeline employs a clear and consistent file naming strategy that reflects data transformation stages:

```
Raw CSV → Extracted JSON → Optimized JSON → Database Records
```

### File Naming Flow:

1. **Raw Source Files**:
   - Original CSV files: `trade_db_[year].csv`
   - Located in: `/species_data/raw_data/Trade_full/`

2. **Extracted Species Files**:
   - Format: `[Species_Name]_trade_data.json`
   - Example: `Ursus_maritimus_trade_data.json`
   - Located in: `/species_data/processed/individual_species/`

3. **Optimized Species Files**:
   - Format: `[Species_Name]_trade_data_optimized.json[.gz]`
   - Example: `Ursus_maritimus_trade_data_optimized.json.gz`
   - Located in: `/species_data/processed/optimized_species/`

4. **Backup Files**:
   - Format: `trade_data_backup_[YYYYMMDD_HHMMSS].json`
   - Example: `trade_data_backup_20250524_201142.json`
   - Located in: `/core/` directory

5. **Log Files**:
   - Format: `[purpose]_[YYYYMMDD_HHMMSS].log`
   - Examples: 
     - `species_trade_extraction.log`
     - `json_optimization.log` 
     - `trade_data_load_20250524_202153.log`
   - Located alongside their respective scripts

This naming strategy provides several benefits:
- **Traceability**: Each file clearly indicates its stage in the pipeline
- **Consistency**: Predictable naming patterns make automation easier
- **Descriptiveness**: Names reflect both content and purpose
- **Versioning**: Timestamps ensure historical records are preserved

## Overview

The CITES trade data pipeline consists of four main phases:

1. **Extraction**: Extract species-specific trade records from massive CITES CSV files
2. **Optimization**: Convert extracted data into an optimized, normalized format
3. **Validation**: Verify data integrity before loading
4. **Loading**: Safely load optimized data into the Supabase database

## Pipeline Components

### 1. Data Extraction (`extract_species_trade_data.py`)

**Purpose**: Extract trade records for Arctic species from the massive CITES trade database CSV files.

**Process**:
1. Reads the species list from `species_names_latest.csv`
2. Scans through all CITES trade database CSV files in `/species_data/raw_data/Trade_full/`
3. Extracts records matching our Arctic species
4. Normalizes problematic quantity values
5. Generates individual JSON files for each species in `/species_data/processed/individual_species/`

**Key Features**:
- Handles massive CSV datasets efficiently
- Normalizes problematic quantity values
- Detects and logs data quality issues
- Generates per-species summary statistics
- Supports both full and incremental extraction modes

**Usage**:
```bash
python extract_species_trade_data.py --mode full
# or for incremental updates
python extract_species_trade_data.py --mode incremental
```

**Output**: 
- Individual JSON files for each species: `/species_data/processed/individual_species/[Species_Name]_trade_data.json`
- Summary reports: `extraction_summary_report.json`
- Issue reports: `quantity_issues_detailed.json`
- List of species without trade data: `species_without_trade.txt`

### 2. Data Optimization (`optimize_species_trade_json.py`)

**Purpose**: Convert the extracted JSON files into an optimized, space-efficient format.

**Process**:
1. Reads each species JSON file from the extraction step
2. Creates lookup tables for repetitive data (taxonomic classifications, locations, categorical values)
3. Normalizes the record structure to reference the lookup tables
4. Generates both optimized JSON and compressed JSON.gz files
5. Creates a utility script for reading the optimized format

**Key Features**:
- Reduces file sizes by 60-80%
- Maintains all original data in a normalized structure
- Creates both uncompressed and compressed versions
- Includes a reader utility for accessing the optimized data
- Generates optimization metrics and reports

**Usage**:
```bash
python optimize_species_trade_json.py
```

**Output**:
- Optimized JSON files: `/species_data/processed/optimized_species/[Species_Name]_trade_data_optimized.json`
- Compressed files: `/species_data/processed/optimized_species/[Species_Name]_trade_data_optimized.json.gz`
- Reader utility: `/species_data/processed/optimized_species/optimized_reader.py`
- Optimization report: `/species_data/processed/optimized_species/optimization_report.json`

### 3. Pre-Load Validation (`validate_before_load.py`)

**Purpose**: Verify system readiness and data integrity before loading data into the database.

**Process**:
1. Checks database connection and access permissions
2. Verifies all optimized data files are available
3. Validates species mapping between files and database
4. Checks current trade data status
5. Estimates load size and verifies sufficient disk space

**Key Features**:
- Comprehensive validation checks
- Early error detection
- Load size estimation
- Species mapping validation
- Database connectivity verification

**Usage**:
```bash
python validate_before_load.py
```

**Output**:
- Validation report in console logs
- Go/no-go recommendation for data loading

### 4. Data Loading (`load_optimized_trade_data.py`)

**Purpose**: Safely replace all CITES trade data in Supabase with the optimized data.

**Process**:
1. Creates a backup of existing trade data (optional)
2. Clears existing trade records using multiple deletion strategies
3. Maps species scientific names to species IDs from the database
4. Loads optimized trade data for each species
5. Validates the loaded data against expected counts
6. Generates comprehensive load statistics

**Key Features**:
- Multiple database deletion strategies for reliability
- Batch processing for large datasets
- Comprehensive error handling
- Optional dry-run mode
- Automatic data backup
- Detailed logging and statistics

**Usage**:
```bash
# Create backup and load data
python load_optimized_trade_data.py --backup

# Test run without making changes
python load_optimized_trade_data.py --dry-run

# Customize batch size
python load_optimized_trade_data.py --backup --batch-size 500
```

**Output**:
- Backup file (when requested): `trade_data_backup_[TIMESTAMP].json`
- Detailed log file: `trade_data_load_[TIMESTAMP].log`

## Data Processing Improvements

The latest pipeline iteration (May 24, 2025) includes several key improvements:

1. **Enhanced Database Deletion**:
   - Multiple fallback strategies for reliable data clearing
   - Adaptive chunk sizes to avoid URI length limitations
   - Improved error handling and recovery

2. **Optimized Data Format**:
   - Normalized repetitive data into lookup tables
   - Reduced file sizes by 60-80%
   - Compressed storage options (gzip)

3. **Improved Memory Efficiency**:
   - Batch processing of large datasets
   - Streaming data handling
   - Chunked database operations

4. **Data Quality Assurance**:
   - Pre-load validation
   - Comprehensive error handling
   - Detailed logging and statistics

## Complete Workflow

The full workflow to process and load CITES trade data:

```bash
# 1. Extract species-specific trade data from CSVs
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/core
python extract_species_trade_data.py --mode full

# 2. Optimize the extracted JSON files
python optimize_species_trade_json.py

# 3. Validate before loading
python validate_before_load.py

# 4. Load the optimized data
python load_optimized_trade_data.py --backup
```

## Dataset Statistics

As of May 24, 2025:

- **Species**: 42 Arctic species with trade data
- **Trade Records**: 553,589 CITES trade records
- **Data Range**: 1975-2023
- **Data Sources**: Complete CITES trade database CSV files
- **File Format**: Optimized JSON with lookup tables
- **Database**: Supabase PostgreSQL at `https://cexwrbrnoxqtxjbiujiq.supabase.co`

## Troubleshooting

### Common Issues

1. **Database Deletion Errors**:
   - 414 Request-URI Too Long: This occurs when trying to delete too many records at once. The improved loader now uses smaller batch sizes and multiple deletion strategies.
   - SQL function errors: The loader tries multiple deletion approaches, including direct DELETE without WHERE clause.

2. **Memory Issues During Extraction**:
   - For very large datasets, use the `--batch-size` parameter to control memory usage.
   - Consider running in incremental mode to process only missing species.

3. **Missing Species Mappings**:
   - Ensure the species list in the database matches those in the extraction file.
   - Check species names for exact spelling matches.

## Future Improvements

- **Incremental Updates**: Add support for incremental updates without clearing the entire database
- **Parallel Processing**: Implement multi-threaded extraction and loading
- **Enhanced Metrics**: Add more detailed statistics on trade patterns
- **API Integration**: Direct integration with CITES API for real-time updates

## Naming Strategy Recommendations

The current naming strategy is generally good and follows consistent patterns, but there are a few recommendations for improvements:

### Strengths

1. **Consistent Patterns**: The codebase follows standard Python naming conventions
2. **Clear Purpose**: File names clearly indicate their purpose
3. **Logical Structure**: The file and directory structure follows a logical flow
4. **Descriptive Names**: Class and method names are descriptive and indicate their purpose

### Recommended Improvements

1. **Log File Standardization**:
   - Consider standardizing log files to always include timestamps in the filename
   - Example: `species_trade_extraction_[TIMESTAMP].log` instead of just `species_trade_extraction.log`

2. **Configuration Naming**:
   - Add a `config_` prefix to configuration files for clarity
   - Example: `config_species_list.csv` instead of just `species_names_latest.csv`

3. **Version Information**:
   - Consider adding version numbers to key files and data formats
   - Example: `trade_data_v2.0_20250524.json`

4. **Script Categorization**:
   - Group scripts with prefixes by their function: `extract_`, `process_`, `load_`, etc.
   - Makes related files sort together in directory listings
   - Example: Rename `validate_before_load.py` to `load_validate_before.py`

5. **Database Column Consistency**:
   - Standardize column naming in database tables
   - Ensure foreign keys consistently follow the `[entity]_id` pattern
   - Use the same name for the same concept across tables

These recommendations would further enhance the already solid naming strategy and improve code maintainability.

---

*This document was last updated on May 24, 2025 after the successful loading of the complete optimized dataset.*