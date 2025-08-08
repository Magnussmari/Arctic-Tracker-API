# NAMMCO Data Import Guide

## Overview

This document describes how to import NAMMCO (North Atlantic Marine Mammal Commission) catch data into the Arctic Tracker database.

## Prerequisites

1. **Supabase Client Setup**: Ensure the latest supabase client is installed
2. **Database Connection**: Valid Supabase credentials in `config/.env`
3. **CSV Files**: NAMMCO catch data files in `species_data/nammco/` directory

## Installation/Setup

If you encounter "proxy" argument errors, update the supabase client:

```bash
pip install --upgrade supabase postgrest
```

## File Structure

NAMMCO CSV files should be placed in:
```
species_data/nammco/
├── Balaenoptera_acutorostrata_catches_2025-06-11.csv
├── Balaenoptera_borealis_catches_2025-06-11.csv
├── [other species files]
```

## CSV Format Expected

Each CSV file should contain columns:
- `COUNTRY` - Country conducting the catch
- `SPECIES (SCIENTIFIC NAME)` - Scientific name of species
- `SPECIES (COMMON NAME)` - Common name (optional)
- `YEAR OR SEASON` - Year of catch
- `AREA OR STOCK` - Management area or stock designation
- `CATCH TOTAL` - Number of animals caught
- `QUOTA (IF APPLICABLE)` - Quota amount if available

## Running the Import

1. **Navigate to migration directory**:
   ```bash
   cd /Users/magnussmari/Arctic-Tracker-API/migration
   ```

2. **Test with single species** (recommended first run):
   ```python
   # In nammco_import.py, set:
   SINGLE_SPECIES = "Balaenoptera_acutorostrata_catches_2025-06-11"
   ```

3. **Run the import**:
   ```bash
   python nammco_import.py
   ```

4. **Import all species**:
   ```python
   # In nammco_import.py, set:
   SINGLE_SPECIES = None
   ```

## What the Script Does

1. **Database Connection Test**: Verifies Supabase connectivity
2. **Species Creation Test**: Validates species auto-creation functionality
3. **Auto-Creation**: Creates missing species, countries, and management areas
4. **Data Import**: Imports catch records with proper relationships
5. **Validation**: Handles data cleaning and error reporting

## Data Mapping

- **Species**: Auto-created with marine mammal taxonomic defaults
- **Countries**: Auto-created and marked as NAMMCO members
- **Management Areas**: Auto-created with area_type='NAMMCO'
- **Catch Records**: Linked to species, country, area with NAMMCO data source

## Import Results

The script provides detailed output including:
- Database connection status
- Records processed per file
- Auto-created entities (species, countries, areas)
- Error handling for invalid data
- Final summary statistics

## Known Issues & Solutions

### Quota Visualization Issue

**Problem**: Quota data not showing in visualization
**Cause**: Data imported to `quota_amount` field but visualization expects `quota` field
**Solution**: Update visualization to query `quota_amount` or copy data to `quota` field

### Field Mapping

- Quota data stored in: `quota_amount`
- Legacy field (may be used by frontend): `quota`
- Data source identifier: `data_source = 'NAMMCO'`

## Database Schema Impact

The import creates/updates these tables:
- `species` - New species entries with taxonomic classification
- `countries` - NAMMCO member countries
- `management_areas` - Arctic management zones
- `catch_records` - Historical catch data with quotas

## Troubleshooting

1. **Proxy Errors**: Update supabase/postgrest packages
2. **Connection Failures**: Check `.env` credentials
3. **Missing Files**: Verify CSV directory path
4. **Data Validation**: Check CSV column names and data formats

## Example Output

```
✅ Supabase client created successfully
🚀 Starting NAMMCO data import with auto-species creation...
✅ Database connection successful
✅ Species creation test successful
📄 Processing 1 file(s)
📂 Processing: Balaenoptera_acutorostrata_catches_2025-06-11.csv
📊 Found 212 records
✅ Successfully processed 212 records
🎉 Import complete! Total records processed: 212
```