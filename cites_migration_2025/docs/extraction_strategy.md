# Arctic Species CITES Data Extraction Strategy

## Overview

Instead of migrating 28 million CITES trade records, we extract ONLY the data relevant to Arctic species, reducing the dataset by ~99.5% to approximately 50,000-100,000 records.

## Why This Approach?

1. **Efficiency**: Process only what we need (0.5% of data)
2. **Performance**: Faster queries on smaller dataset
3. **Cost**: Reduced storage and processing costs
4. **Focus**: Arctic species are our primary concern
5. **Safety**: Less risk during migration

## Extraction Process

### Step 1: Database Architecture Documentation
- Extract current database schema
- Document table relationships
- Identify migration requirements
- **Output**: `docs/database_architecture.json/md`

### Step 2: Arctic Species List Creation
- Query database for Arctic species
- Include scientific names for CITES matching
- Add conservation status information
- **Output**: `data/arctic_species_list.csv`

### Step 3: CITES Data Extraction
- Process 56 CSV files (28M records total)
- Extract ONLY records matching Arctic species
- Use parallel processing for speed
- **Output**: `extracted_data/arctic_species_trade_data_v2025.csv`

### Step 4: Data Validation
- Verify species matching
- Check data completeness
- Generate summary statistics
- **Output**: `logs/extraction_stats_[timestamp].json`

## Technical Details

### Species Matching
- Match by scientific name (exact match)
- 43 target Arctic species
- Handles synonyms where known

### Performance Optimization
- Chunk processing (50,000 records at a time)
- Parallel file processing (4 workers)
- Memory-efficient pandas operations

### Expected Results
- **Input**: 28,901,926 total CITES records
- **Output**: ~50,000-100,000 Arctic records
- **Reduction**: >99%
- **Processing Time**: 1-2 hours

## File Structure

```
cites_migration_2025/
├── scripts/
│   ├── extract_db_architecture.py      # Step 1
│   ├── create_arctic_species_list.py   # Step 2
│   ├── extract_arctic_trade_data.py    # Step 3
│   └── run_extraction_pipeline.sh      # Master script
├── data/
│   └── arctic_species_list.csv         # Species to extract
├── extracted_data/
│   ├── arctic_trade_01.csv            # Individual extracts
│   ├── arctic_trade_02.csv
│   └── arctic_species_trade_data_v2025.csv  # Combined result
├── logs/
│   └── extraction_stats_[timestamp].json
└── docs/
    ├── database_architecture.json/md
    └── extraction_strategy.md          # This file
```

## Running the Extraction

```bash
cd cites_migration_2025/scripts
chmod +x run_extraction_pipeline.sh
./run_extraction_pipeline.sh
```

Or run steps individually:
```bash
python extract_db_architecture.py
python create_arctic_species_list.py
python extract_arctic_trade_data.py --parallel --workers 4
```

## Post-Extraction Steps

1. **Validate Data**
   - Check species coverage
   - Verify record counts
   - Test data quality

2. **Prepare for Migration**
   - Map to database schema
   - Create import scripts
   - Plan staging process

3. **Migration**
   - Load to staging tables
   - Validate against current data
   - Switch to production

## Key Advantages

✅ **Focused Dataset**: Only Arctic species data
✅ **Manageable Size**: <100K records vs 28M
✅ **Faster Processing**: Hours instead of days
✅ **Lower Risk**: Smaller migration scope
✅ **Better Performance**: Optimized for our use case

## Success Metrics

- All 43 Arctic species found in CITES data
- >95% species matching rate
- <2 hours extraction time
- Zero data corruption
- Complete audit trail