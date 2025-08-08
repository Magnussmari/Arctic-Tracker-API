# Arctic Tracker Database Architecture Fix Plan
## Safe Migration Strategy - No Breaking Changes

---

## 🎯 Objective
Fix the Arctic Tracker database to properly support trade data extraction while maintaining system stability and data integrity.

---

## 📋 Phase 1: Quick Fixes (No Database Changes)
**Timeline: 1-2 hours**
**Risk: Zero - Code changes only**

### 1.1 Fix Pipeline Column Reference
```python
# In trade_pipeline.py, line ~349
# Change from:
.order('effective_date', desc=True)
# To:
.order('listing_date', desc=True)
```

### 1.2 Create Missing Species Mapping
```python
# Add to name_mapping dictionary:
"Aleutian cackling goose": "Branta hutchinsii leucopareia",
"Dall's Porpoise": "Phocoenoides dalli",
"Harbour Porpoise": "Phocoena phocoena",
"North Pacific Right Whale": "Eubalaena japonica",
"Roseroot": "Rhodiola rosea"
```

### 1.3 Create Temporary Data Extraction Script
Create `temporary_data_fixer.py` to handle missing data while we fix the database:
```python
# Script to extract data directly from CITES records
# Uses optimized queries to get counts and summaries
# Outputs to CSV for immediate use
```

---

## 📋 Phase 2: Database Analysis & Backup
**Timeline: 2-3 hours**
**Risk: None - Read-only operations**

### 2.1 Complete Database Audit
```sql
-- Check all table structures
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- Count records in each table
SELECT 
  schemaname,
  tablename,
  n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

### 2.2 Create Full Backup
```bash
# Backup entire database
pg_dump -h [host] -U [user] -d [database] > arctic_tracker_backup_$(date +%Y%m%d_%H%M%S).sql

# Backup specific tables
pg_dump -h [host] -U [user] -d [database] \
  -t species -t cites_trade_records -t species_trade_summary \
  > arctic_tracker_tables_backup_$(date +%Y%m%d_%H%M%S).sql
```

### 2.3 Document Current State
- Record counts for all tables
- Document all foreign key relationships
- List all indexes
- Save all view definitions

---

## 📋 Phase 3: Non-Breaking Database Additions
**Timeline: 3-4 hours**
**Risk: Low - Adding only, no modifications**

### 3.1 Add Missing Indexes (Performance Fix)
```sql
-- Add indexes for common queries (if not exist)
CREATE INDEX IF NOT EXISTS idx_cites_trade_species_year 
ON cites_trade_records(species_id, year);

CREATE INDEX IF NOT EXISTS idx_cites_trade_exporter 
ON cites_trade_records(species_id, exporter);

CREATE INDEX IF NOT EXISTS idx_cites_listings_species_date 
ON cites_listings(species_id, listing_date);
```

### 3.2 Create Materialized Views (Don't modify tables)
```sql
-- Create materialized view for species trade summary
CREATE MATERIALIZED VIEW mv_species_trade_summary AS
SELECT 
  species_id,
  COUNT(*) as total_records,
  COALESCE(SUM(quantity), 0) as total_quantity,
  MIN(year) as min_year,
  MAX(year) as max_year,
  COUNT(DISTINCT year) as years_traded,
  COUNT(DISTINCT exporter) as unique_exporters,
  COUNT(DISTINCT importer) as unique_importers
FROM cites_trade_records
GROUP BY species_id;

-- Create index on materialized view
CREATE INDEX idx_mv_species_trade_summary_species 
ON mv_species_trade_summary(species_id);
```

### 3.3 Add Missing Species (Safe Insert)
```sql
-- First verify species don't exist
SELECT * FROM species WHERE scientific_name IN (
  'Branta hutchinsii leucopareia',
  'Phocoenoides dalli',
  'Phocoena phocoena',
  'Eubalaena japonica',
  'Rhodiola rosea'
);

-- Then insert if not exists
INSERT INTO species (
  id, scientific_name, common_name, kingdom, phylum, 
  class, order_name, family, genus, species_name
) VALUES 
  (gen_random_uuid(), 'Branta hutchinsii leucopareia', 'Aleutian cackling goose', 
   'Animalia', 'CHORDATA', 'AVES', 'ANSERIFORMES', 'ANATIDAE', 'Branta', 'hutchinsii leucopareia'),
  -- ... other species
ON CONFLICT (scientific_name) DO NOTHING;
```

---

## 📋 Phase 4: Data Population (Safe Updates)
**Timeline: 2-3 hours**
**Risk: Low - Only populating empty tables**

### 4.1 Populate species_trade_summary Table
```sql
-- First check if table is truly empty
SELECT COUNT(*) FROM species_trade_summary;

-- If empty, populate from trade records
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
GROUP BY species_id, year
ON CONFLICT DO NOTHING;
```

### 4.2 Create Purpose Summary Table
```sql
-- New table for trade purpose analysis
CREATE TABLE IF NOT EXISTS trade_purpose_summary (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  species_id UUID REFERENCES species(id),
  purpose VARCHAR(10),
  record_count INTEGER,
  percentage DECIMAL(5,2),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Populate it
INSERT INTO trade_purpose_summary (species_id, purpose, record_count)
SELECT species_id, purpose, COUNT(*)
FROM cites_trade_records
GROUP BY species_id, purpose;
```

---

## 📋 Phase 5: Add CMS Integration
**Timeline: 4-6 hours**
**Risk: Low - New tables only**

### 5.1 Create CMS Tables
```sql
-- CMS listings table
CREATE TABLE IF NOT EXISTS cms_listings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  species_id UUID REFERENCES species(id),
  appendix VARCHAR(10),
  listing_date DATE,
  is_current BOOLEAN DEFAULT true,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- CMS status history
CREATE TABLE IF NOT EXISTS cms_status_history (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  species_id UUID REFERENCES species(id),
  status VARCHAR(50),
  effective_date DATE,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 📋 Phase 6: Testing & Validation
**Timeline: 2-3 hours**
**Risk: None - Testing only**

### 6.1 Test Pipeline with Fixed Code
```bash
# Run pipeline with single species first
python trade_pipeline_test.py --species "Polar Bear"

# Compare results with expected data
# Verify all fields populate correctly
```

### 6.2 Performance Testing
```sql
-- Test query performance
EXPLAIN ANALYZE
SELECT * FROM mv_species_trade_summary
WHERE species_id = '[test_species_id]';
```

### 6.3 Data Validation
```python
# Script to validate data completeness
# Compare counts between tables
# Check for orphaned records
# Verify foreign key integrity
```

---

## 📋 Phase 7: Gradual Rollout
**Timeline: 1 week**
**Risk: Minimal - Staged deployment**

### Week 1: Development Environment
- Deploy all fixes to dev
- Run complete test suite
- Monitor for 48 hours

### Week 2: Staging Environment
- Deploy to staging
- Run parallel extraction (old vs new)
- Compare results

### Week 3: Production
- Deploy during low-usage window
- Keep old code as fallback
- Monitor closely for 72 hours

---

## 🛠️ Implementation Checklist

### Immediate Actions (Today)
- [ ] Fix column reference in trade_pipeline.py
- [ ] Add species name mappings
- [ ] Create database backup
- [ ] Test pipeline with fixes

### This Week
- [ ] Create materialized views
- [ ] Add missing indexes
- [ ] Populate summary tables
- [ ] Insert missing species

### Next Week
- [ ] Implement CMS tables
- [ ] Create monitoring scripts
- [ ] Deploy to staging
- [ ] Document all changes

---

## 🚨 Rollback Plan

### If Issues Occur:
1. **Code Rollback**: Git revert to previous version
2. **Database Rollback**: 
   ```sql
   -- Drop new objects only
   DROP MATERIALIZED VIEW IF EXISTS mv_species_trade_summary;
   DROP TABLE IF EXISTS trade_purpose_summary;
   -- Restore from backup if needed
   ```
3. **Use Original Pipeline**: Keep old code available as `trade_pipeline_legacy.py`

---

## 📊 Success Metrics

### Target Outcomes:
- ✅ All 43 species return complete data
- ✅ Query performance < 1 second per species
- ✅ No breaking changes to existing systems
- ✅ 100% data accuracy vs source CSV
- ✅ Automated tests pass 100%

### Monitoring:
- Database query performance logs
- Pipeline execution time
- Error rate monitoring
- Data completeness checks

---

## 🔒 Safety Guarantees

1. **No Existing Table Modifications** - Only additions
2. **All Changes Reversible** - Complete rollback plan
3. **Backward Compatible** - Old code continues to work
4. **Comprehensive Testing** - Each phase fully tested
5. **Incremental Deployment** - Gradual rollout strategy

---

## 📝 Notes

- Keep original CSV as source of truth for validation
- Document every change in migration log
- Maintain parallel systems during transition
- Create automated tests for each fix
- Monitor Supabase quotas during migration

This plan ensures we fix all issues while maintaining system stability and providing a clear path to rollback if needed.