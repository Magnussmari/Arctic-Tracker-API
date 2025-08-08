# Species Data Directory

This directory contains all species-related data files and processing utilities for the Arctic Species CITES trade data import system.

## Directory Structure

### `/cites_trade/`
**Purpose**: CITES trade database files and related data
- **Location for**: The massive CITES trade CSV files
- **Contains**: 
  - Raw CITES trade database CSV files
  - Trade-specific data exports
  - Country code mappings
  - Purpose/source code references

### `/raw_data/`
**Purpose**: Original, unprocessed data files
- **Contains**:
  - Original CITES species lists
  - IUCN Red List data exports
  - Arctic species classifications
  - Taxonomy reference files

### `/processed/`
**Purpose**: Cleaned and processed data files
- **Contains**:
  - Processed species data
  - Cleaned trade records
  - Merged datasets
  - Analysis-ready files

## Recommended File Placement

### CITES Trade Database CSV Files → `/cites_trade/`
```
/rebuild/species_data/cites_trade/
├── cites_trade_database_2024.csv
├── cites_trade_database_2023.csv
├── country_codes.csv
├── purpose_codes.csv
└── source_codes.csv
```

### Original Species Data → `/raw_data/`
```
/rebuild/species_data/raw_data/
├── arctic_species_list.csv
├── iucn_red_list_export.csv
├── cites_species_database.csv
└── taxonomy_references.csv
```

### Processed Files → `/processed/`
```
/rebuild/species_data/processed/
├── cleaned_trade_data.csv
├── species_with_iucn_status.csv
├── arctic_cites_species.csv
└── analysis_datasets/
```

## Data Processing Workflow

1. **Raw Data** → Place original files in `/raw_data/`
2. **Trade Data** → Place CITES trade CSV files in `/cites_trade/`
3. **Processing** → Scripts process data and output to `/processed/`
4. **Import** → Import scripts read from `/processed/` to database

## File Naming Convention

- Use descriptive names with dates: `cites_trade_2024_full.csv`
- Include data source: `iucn_redlist_arctic_species_2024.csv`
- Version processed files: `processed_trade_data_v1.2.csv`

## Data Security Notes

- Large CSV files should be compressed when not in use
- Ensure proper backup of original raw data files
- Document data sources and update dates
- Keep checksums for data integrity verification

---

*This organization follows the modular rebuild architecture and separates concerns between raw data, trade data, and processed outputs.*