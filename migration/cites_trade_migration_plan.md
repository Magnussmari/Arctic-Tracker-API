# CITES Trade Data Migration Plan v2025.1
## Safe Migration Strategy for ~28 Million Records

---

## 🚨 CRITICAL INFORMATION

- **Data Volume**: ~28 million trade records across 56 CSV files
- **File Size**: Each file contains ~500,000 records (except last file)
- **Update Type**: Full replacement of existing CITES trade data
- **Risk Level**: HIGH - Production data modification
- **Estimated Time**: 24-48 hours for complete migration

---

## 📊 Data Overview

### Source Data Structure
```csv
Id, Year, Appendix, Taxon, Class, Order, Family, Genus, Term, 
Quantity, Unit, Importer, Exporter, Origin, Purpose, Source, 
Reporter.type, Import.permit.RandomID, Export.permit.RandomID, ...
```

### Target Tables
- `cites_trade_records` - Main trade data
- `species_trade_summary` - Aggregated summaries
- Related: `species`, `cites_listings`

---

## 🛡️ Phase 1: Pre-Migration Safety (Day 1)
**Timeline: 4-6 hours**
**Risk: None - Read-only operations**

### 1.1 Complete Database Backup
```bash
# Full database backup
pg_dump -h [supabase-host] -U postgres -d postgres \
  --verbose --no-owner --no-acl \
  > arctic_tracker_full_backup_$(date +%Y%m%d_%H%M%S).sql

# Specific tables backup
pg_dump -h [supabase-host] -U postgres -d postgres \
  -t cites_trade_records -t species_trade_summary \
  -t species -t cites_listings \
  > cites_trade_backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backups
gzip arctic_tracker_full_backup_*.sql
```

### 1.2 Export Current Data Stats
```sql
-- Record current statistics for validation
CREATE TABLE migration_stats_pre AS
SELECT 
  'cites_trade_records' as table_name,
  COUNT(*) as record_count,
  COUNT(DISTINCT species_id) as unique_species,
  MIN(year) as min_year,
  MAX(year) as max_year,
  NOW() as snapshot_time
FROM cites_trade_records;

-- Export to CSV
COPY migration_stats_pre TO '/tmp/migration_stats_pre.csv' CSV HEADER;
```

### 1.3 Create Migration Tracking Table
```sql
CREATE TABLE IF NOT EXISTS cites_migration_log (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  file_name VARCHAR(255),
  records_processed INTEGER,
  records_inserted INTEGER,
  records_updated INTEGER,
  records_failed INTEGER,
  species_matched INTEGER,
  species_unmatched INTEGER,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  status VARCHAR(50),
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔍 Phase 2: Data Analysis & Mapping (Day 1)
**Timeline: 3-4 hours**
**Risk: None - Analysis only**

### 2.1 Species Mapping Analysis
```python
# Script: analyze_species_mapping.py
import pandas as pd
import os

def analyze_species_coverage():
    """Check how many species in new data exist in our database"""
    
    # Sample first file for unique species
    df_sample = pd.read_csv('trade_db_1.csv', nrows=10000)
    unique_taxa = df_sample['Taxon'].unique()
    
    # Check against database
    matched = 0
    unmatched = []
    
    for taxon in unique_taxa:
        # Query database for species
        result = supabase.table('species').select('id').eq('scientific_name', taxon).execute()
        if result.data:
            matched += 1
        else:
            unmatched.append(taxon)
    
    return {
        'total_unique': len(unique_taxa),
        'matched': matched,
        'unmatched': len(unmatched),
        'unmatched_list': unmatched[:100]  # First 100
    }
```

### 2.2 Data Quality Checks
```python
# Check for data issues
def validate_csv_structure():
    issues = []
    
    for i in range(1, 57):
        file_path = f'trade_db_{i}.csv'
        df = pd.read_csv(file_path, nrows=100)
        
        # Check required columns
        required_cols = ['Id', 'Year', 'Taxon', 'Quantity', 'Importer', 'Exporter']
        missing = [col for col in required_cols if col not in df.columns]
        
        if missing:
            issues.append(f"File {file_path}: Missing columns {missing}")
    
    return issues
```

---

## 🔄 Phase 3: Migration Strategy Development (Day 1)
**Timeline: 2-3 hours**
**Risk: None - Planning only**

### 3.1 Create Staging Tables
```sql
-- Create staging table identical to production
CREATE TABLE cites_trade_records_staging (
  LIKE cites_trade_records INCLUDING ALL
);

-- Create error tracking table
CREATE TABLE cites_trade_import_errors (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  file_name VARCHAR(255),
  line_number INTEGER,
  raw_data TEXT,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 3.2 Develop Migration Script
```python
# migration_script.py
import pandas as pd
import numpy as np
from supabase import create_client
import logging
from datetime import datetime

class CITESMigration:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.batch_size = 1000
        self.species_cache = {}
        
    def process_file(self, file_path, file_number):
        """Process single CSV file"""
        start_time = datetime.now()
        
        # Log start
        self.log_migration_start(file_path)
        
        try:
            # Process in chunks
            for chunk in pd.read_csv(file_path, chunksize=10000):
                self.process_chunk(chunk, file_number)
                
        except Exception as e:
            self.log_migration_error(file_path, str(e))
            raise
            
        # Log completion
        self.log_migration_complete(file_path, start_time)
    
    def process_chunk(self, chunk, file_number):
        """Process chunk of records"""
        records_to_insert = []
        
        for _, row in chunk.iterrows():
            # Map species
            species_id = self.get_species_id(row['Taxon'])
            if not species_id:
                self.log_unmatched_species(row['Taxon'])
                continue
            
            # Create record
            record = {
                'id': f"{row['Id']}-v2025",  # Unique ID
                'species_id': species_id,
                'year': int(row['Year']) if pd.notna(row['Year']) else None,
                'appendix': row['Appendix'],
                'term': row['Term'],
                'quantity': float(row['Quantity']) if pd.notna(row['Quantity']) else None,
                'unit': row['Unit'],
                'importer': row['Importer'],
                'exporter': row['Exporter'],
                'origin': row['Origin'],
                'purpose': row['Purpose'],
                'source': row['Source'],
                'reporter_type': row['Reporter.type'],
                'created_at': datetime.now().isoformat()
            }
            
            records_to_insert.append(record)
            
            # Batch insert
            if len(records_to_insert) >= self.batch_size:
                self.insert_batch(records_to_insert)
                records_to_insert = []
        
        # Insert remaining
        if records_to_insert:
            self.insert_batch(records_to_insert)
```

---

## 🚀 Phase 4: Test Migration (Day 2)
**Timeline: 6-8 hours**
**Risk: Low - Staging environment only**

### 4.1 Small-Scale Test
```bash
# Test with first file only
python migration_script.py --test --file trade_db_1.csv --table cites_trade_records_staging
```

### 4.2 Validation Queries
```sql
-- Compare counts
SELECT 
  (SELECT COUNT(*) FROM cites_trade_records_staging) as staging_count,
  (SELECT COUNT(*) FROM cites_trade_records) as production_count;

-- Check data quality
SELECT 
  COUNT(*) as total,
  COUNT(species_id) as with_species,
  COUNT(year) as with_year,
  COUNT(quantity) as with_quantity
FROM cites_trade_records_staging;
```

### 4.3 Performance Testing
```sql
-- Test query performance
EXPLAIN ANALYZE
SELECT * FROM cites_trade_records_staging
WHERE species_id = '[test_id]' AND year >= 2020;

-- Create indexes if needed
CREATE INDEX idx_staging_species_year 
ON cites_trade_records_staging(species_id, year);
```

---

## 💾 Phase 5: Production Migration (Day 2-3)
**Timeline: 12-24 hours**
**Risk: HIGH - Production data modification**

### 5.1 Migration Execution Plan
```bash
# 1. Notify users of maintenance window
# 2. Set database to maintenance mode if possible

# 3. Final backup
pg_dump -h [host] -U postgres -d postgres -t cites_trade_records \
  > final_backup_before_migration_$(date +%Y%m%d_%H%M%S).sql

# 4. Run migration in screen/tmux session
screen -S cites_migration
python migration_script.py --production --parallel 4
```

### 5.2 Parallel Processing Strategy
```python
# Parallel migration for faster processing
from multiprocessing import Pool
import os

def migrate_file(file_info):
    file_path, file_number = file_info
    migrator = CITESMigration()
    migrator.process_file(file_path, file_number)
    return f"Completed {file_path}"

# Create file list
files = [(f"trade_db_{i}.csv", i) for i in range(1, 57)]

# Process in parallel
with Pool(processes=4) as pool:
    results = pool.map(migrate_file, files)
```

### 5.3 Switchover Strategy
```sql
-- Option 1: Rename tables (fastest)
BEGIN;
ALTER TABLE cites_trade_records RENAME TO cites_trade_records_old;
ALTER TABLE cites_trade_records_staging RENAME TO cites_trade_records;
COMMIT;

-- Option 2: Truncate and copy (safer)
BEGIN;
TRUNCATE TABLE cites_trade_records;
INSERT INTO cites_trade_records SELECT * FROM cites_trade_records_staging;
COMMIT;
```

---

## ✅ Phase 6: Post-Migration Validation (Day 3)
**Timeline: 4-6 hours**
**Risk: None - Validation only**

### 6.1 Data Integrity Checks
```sql
-- Record count validation
SELECT 
  'Expected' as source, 27901926 as count
UNION ALL
SELECT 
  'Actual' as source, COUNT(*) as count
FROM cites_trade_records;

-- Species coverage
SELECT 
  COUNT(DISTINCT species_id) as unique_species,
  COUNT(*) as total_records,
  MIN(year) as earliest_year,
  MAX(year) as latest_year
FROM cites_trade_records;

-- Check for orphaned records
SELECT COUNT(*) as orphaned_records
FROM cites_trade_records c
LEFT JOIN species s ON c.species_id = s.id
WHERE s.id IS NULL;
```

### 6.2 Regenerate Summary Tables
```sql
-- Rebuild species trade summary
TRUNCATE TABLE species_trade_summary;

INSERT INTO species_trade_summary (
  species_id, year, total_records, total_quantity, 
  min_year, max_year, summary_type
)
SELECT 
  species_id,
  year,
  COUNT(*) as total_records,
  COALESCE(SUM(quantity), 0) as total_quantity,
  year as min_year,
  year as max_year,
  'annual' as summary_type
FROM cites_trade_records
GROUP BY species_id, year;

-- Create index for performance
CREATE INDEX idx_summary_species_year 
ON species_trade_summary(species_id, year);
```

### 6.3 Run Test Queries
```python
# Test the pipeline with new data
python quick_fix_trade_pipeline.py --test --species "Polar Bear"

# Compare results with expected values
```

---

## 🔄 Phase 7: Cleanup & Documentation (Day 3)
**Timeline: 2-3 hours**
**Risk: None**

### 7.1 Cleanup
```sql
-- After validation, remove old data
DROP TABLE IF EXISTS cites_trade_records_old;
DROP TABLE IF EXISTS cites_trade_records_staging;

-- Archive migration logs
CREATE TABLE cites_migration_archive AS 
SELECT * FROM cites_migration_log;
```

### 7.2 Documentation
- Document migration completion
- Update data dictionary
- Record any species mapping issues
- Create runbook for future migrations

---

## 🚨 Rollback Procedures

### Immediate Rollback (if using rename method)
```sql
BEGIN;
ALTER TABLE cites_trade_records RENAME TO cites_trade_records_failed;
ALTER TABLE cites_trade_records_old RENAME TO cites_trade_records;
COMMIT;
```

### Restore from Backup
```bash
# Restore from backup
gunzip -c final_backup_before_migration_[timestamp].sql.gz | \
  psql -h [host] -U postgres -d postgres
```

---

## 📊 Success Criteria

1. ✅ All 27.9M records successfully migrated
2. ✅ Species matching rate > 95%
3. ✅ No data loss from previous version
4. ✅ Query performance maintained or improved
5. ✅ All Arctic species have updated trade data
6. ✅ Summary tables regenerated successfully
7. ✅ Pipeline produces accurate results

---

## ⚠️ Risk Mitigation

1. **Full backups** at every stage
2. **Staging environment** testing first
3. **Parallel processing** for speed
4. **Transaction wrapping** for atomicity
5. **Continuous monitoring** during migration
6. **Rollback plan** ready at all times
7. **User notification** about maintenance window

---

## 📅 Recommended Schedule

### Day 1 (Preparation)
- Morning: Backups and analysis
- Afternoon: Script development and testing

### Day 2 (Migration)
- Early morning: Final preparations
- Morning: Begin staging migration
- Afternoon: Validation and production migration start
- Evening: Monitor overnight processing

### Day 3 (Completion)
- Morning: Final validation
- Afternoon: Cleanup and documentation
- Evening: Normal operations resume

---

This plan ensures safe migration of the new CITES trade data while maintaining data integrity and providing multiple rollback options.