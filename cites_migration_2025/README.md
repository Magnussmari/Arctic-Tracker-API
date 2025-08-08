# CITES Migration 2025 - Arctic Species Data Extraction & Migration

## 🎯 Purpose

Extract ONLY Arctic species trade data from the massive CITES v2025.1 database (28M records) to create a focused dataset for the Arctic Tracker project and migrate it to production database.

## 📊 Migration Status: READY TO PROCEED ✅

**Decision**: Migration strongly recommended - 30,989 new records (6.8% increase) with critical 2023-2024 data.

## 🚀 Quick Start

```bash
cd scripts
./run_extraction_pipeline.sh
```

This will:
1. Extract current database architecture
2. Create Arctic species list from database
3. Extract Arctic trade data from CITES files
4. Generate summary reports

## 📁 Project Structure

```
cites_migration_2025/
├── scripts/          # Extraction and migration scripts
├── data/            # Species lists and reference data
├── docs/            # Documentation and reports
├── backups/         # Database backups (create before migration)
├── extracted_data/  # Filtered Arctic species trade data
└── logs/           # Extraction and migration logs
```

## 📊 Current Status & Numbers

### Extraction Complete ✅
- **Source Data**: 56 CSV files, 27,901,870 records
- **Target Species**: 43 Arctic species (100% found)
- **Extracted Records**: 489,148 (1.75% of total)
- **Processing Time**: ~1.5 hours
- **Output Size**: ~95 MB

### Database Comparison ✅
- **Current DB Records**: 458,159
- **New Records to Add**: 30,989 (+6.8%)
- **Species Needing Update**: 33/42 (78.6%)
- **Latest Data**: Through 2024

## 🔧 Scripts

### Core Scripts
1. `extract_db_architecture.py` - Documents current database
2. `create_arctic_species_list.py` - Generates species list for extraction
3. `extract_arctic_trade_data.py` - Main extraction script
4. `run_extraction_pipeline.sh` - Runs complete pipeline

### Usage Examples

```bash
# Run complete pipeline
./run_extraction_pipeline.sh

# Run individual steps
python extract_db_architecture.py
python create_arctic_species_list.py
python extract_arctic_trade_data.py --parallel --workers 4

# Test mode (first 3 files only)
python extract_arctic_trade_data.py --test
```

## 📋 Arctic Species List

The extraction targets 43 Arctic species including:
- Marine mammals (Polar Bear, Narwhal, Beluga, Walrus, etc.)
- Seabirds (Gyrfalcon, Snowy Owl, etc.)
- Fish (Siberian Sturgeon, sharks)
- One plant (Roseroot)

Full list in: `data/arctic_species_list.csv`

## 🔄 Workflow

```
1. Database Analysis
   └── extract_db_architecture.py
       └── outputs: docs/database_architecture.json

2. Species List Creation
   └── create_arctic_species_list.py
       └── outputs: data/arctic_species_list.csv

3. Data Extraction
   └── extract_arctic_trade_data.py
       ├── reads: 56 CITES CSV files
       ├── filters: Arctic species only
       └── outputs: extracted_data/arctic_species_trade_data_v2025.csv

4. Migration Planning
   └── Review extracted data
   └── Plan database updates
```

## ⚠️ Important Notes

1. **Run Order**: Scripts must be run in order (1→2→3)
2. **Dependencies**: Requires Supabase connection (config/supabase_config.py)
3. **Processing**: Uses parallel processing by default (4 workers)
4. **Memory**: Each worker needs ~2GB RAM
5. **Disk Space**: Need ~10GB free space during processing

## ✅ Pre-Migration Checklist

### Completed Tasks ✅
- [x] Extract Arctic species data from CITES v2025.1
- [x] Verify all 43 species found (including Aleutian Canada Goose)
- [x] Compare extracted data with current database
- [x] Generate migration plan and risk assessment
- [x] Create data quality report
- [x] Validate extraction completeness

### Ready for Migration ✅
- [x] **Data Files**: `arctic_species_trade_data_v2025.csv` (489,148 records)
- [x] **Species Summary**: `arctic_species_trade_summary.csv` 
- [x] **Migration Plan**: `docs/migration_plan.md`
- [x] **Comparison Report**: `docs/trade_count_comparison.csv`
- [x] **Decision Report**: `docs/migration_decision_report.md`

### Pre-Migration Tasks ⏳
- [ ] Create comprehensive database backup
- [ ] Set up staging table in Supabase
- [ ] Create rollback scripts
- [ ] Notify stakeholders of migration window
- [ ] Test with 2024 data subset first

### Migration Scripts Needed 🔧
- [ ] `backup_cites_data.py` - Full backup script
- [ ] `create_staging_table.sql` - Staging table DDL
- [ ] `load_to_staging.py` - Data loading script
- [ ] `validate_migration.py` - Post-migration validation
- [ ] `update_trade_summary.py` - Summary table update

## 🔍 Validation

Check extraction success:
```bash
# Count records
wc -l extracted_data/arctic_species_trade_data_v2025.csv

# View summary
cat extracted_data/arctic_species_trade_summary.csv

# Check logs
cat logs/extraction_stats_*.json
```

## 📞 Support

If issues arise:
1. Check logs in `logs/` directory
2. Verify species list exists in `data/`
3. Ensure CITES source files are accessible
4. Confirm database connection works

## 🎯 Next Steps for Migration

### Phase 1: Preparation (2-3 hours)
1. Create database backup script and run full backup
2. Create staging table with same structure as cites_trade_records
3. Set up rollback procedures

### Phase 2: Test Migration (1 hour)
1. Load 2024 data only to staging (~17 species)
2. Validate data integrity
3. Test query performance

### Phase 3: Full Migration (3-4 hours)
1. Load all 489,148 records to staging
2. Validate against source data
3. Run comprehensive checks

### Phase 4: Switchover (30 minutes)
1. Create backup of current table
2. Atomic table rename
3. Rebuild indexes

### Phase 5: Post-Migration (1-2 hours)
1. Update species_trade_summary
2. Validate all systems
3. Document completion

## 📈 Migration Impact

### Species with Significant Updates
1. **Siberian Sturgeon**: +16,340 records (+9.1%)
2. **Gyrfalcon**: +7,818 records (+9.9%)
3. **Peregrine Falcon**: +2,417 records (+7.5%)
4. **Narwhal**: +1,273 records (+5.2%)
5. **Roseroot**: +603 records (+2,319%!)

### Benefits
- Latest 2024 trade data for 17 species
- Updated 2023 data for 16 species
- Complete Arctic species coverage
- Better conservation monitoring

---

**Created**: October 2024  
**Updated**: July 28, 2025  
**CITES Version**: v2025.1  
**Target**: Arctic Tracker Database  
**Status**: READY FOR MIGRATION ✅