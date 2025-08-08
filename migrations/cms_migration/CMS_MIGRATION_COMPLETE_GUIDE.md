# CMS Migration Complete Guide

**Date**: August 8, 2025  
**Status**: Ready for Execution  
**Estimated Time**: 30-45 minutes

## 🚨 IMPORTANT: Current Status

The CMS (Convention on Migratory Species) data integration has NOT been completed despite previous documentation claiming otherwise. This guide provides the complete step-by-step process to properly integrate CMS data into the Arctic Tracker database.

## Prerequisites

Before starting, ensure you have:
- [ ] Access to Supabase dashboard with admin privileges
- [ ] Python environment with required packages installed
- [ ] Backup of current database (recommended)
- [ ] About 30-45 minutes for the complete process

## Migration Overview

The migration consists of 5 main steps:

1. **Create CMS tables in database** (SQL execution)
2. **Verify table creation** (Quick check)
3. **Load CMS data** (Python script)
4. **Verify data loading** (Python script)
5. **Update article_summary_table** (SQL execution)

## Step-by-Step Instructions

### Step 1: Create CMS Tables in Supabase

**Time: 5-10 minutes**

1. Open your Supabase dashboard
2. Navigate to **SQL Editor**
3. Create a new query
4. Copy the entire contents of `create_cms_listings_table.sql`
5. Paste into the SQL editor
6. Click **Run** to execute

**What this creates:**
- `cms_listings` table with proper schema
- `species_cms_listings` view for easy querying
- Proper indexes and foreign key constraints
- Row Level Security (RLS) policies

**Expected output:**
```
Success. No rows returned
```

**Troubleshooting:**
- If you see "relation already exists", the table might be partially created. Check the Table Editor to see what exists.
- If RLS policies fail, you may need admin role.

### Step 2: Verify Table Creation

**Time: 2 minutes**

In Supabase SQL Editor, run:

```sql
-- Check if table was created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('cms_listings', 'species_cms_listings');

-- Check column structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'cms_listings'
ORDER BY ordinal_position;
```

**Expected output:**
- Should show both `cms_listings` and `species_cms_listings`
- Should show all columns including `agreement`, `listed_under`, etc.

### Step 3: Load CMS Data

**Time: 10-15 minutes**

1. Open terminal in the project directory
2. Navigate to the migration folder:
   ```bash
   cd /Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/migrations/cms_migration
   ```

3. First, do a dry run to test:
   ```bash
   python load_cms_data_to_db.py --dry-run
   ```

   **Expected output:**
   ```
   ============================================================
   CMS DATA LOAD SUMMARY [DRY RUN]
   ============================================================
   Species found in database: 31
   Species not found in database: 0
   Records inserted: 31
   Records updated: 0
   Errors: 0
   ============================================================
   ```

4. If dry run is successful, run the actual load:
   ```bash
   python load_cms_data_to_db.py
   ```

   **Expected output:**
   ```
   ============================================================
   CMS DATA LOAD SUMMARY 
   ============================================================
   Species found in database: 31
   Species not found in database: 0
   Records inserted: 31
   Records updated: 0
   Errors: 0
   ============================================================
   ```

**Troubleshooting:**
- If you see "Could not find the 'agreement' column", the table wasn't created properly. Go back to Step 1.
- If you see authentication errors, check your `.env` file has correct Supabase credentials.
- If species aren't found, ensure the species table is populated.

### Step 4: Verify Data Loading

**Time: 2 minutes**

Run the verification script:

```bash
python verify_cms_data.py
```

**Expected output:**
```
CMS Data Verification Report
============================================================
Generated: 2025-08-08
============================================================

Total CMS listings in database: 31

Species by CMS Appendix:
----------------------------------------
Appendix I: 7 species
Appendix II: 16 species
Appendix I/II: 8 species

Species with both CITES and CMS listings: 28
```

### Step 5: Update Article Summary Table

**Time: 10-15 minutes**

This step populates the CMS fields in the article_summary_table.

1. In Supabase SQL Editor, run this update query:

```sql
-- Update article_summary_table with CMS data
UPDATE article_summary_table ast
SET 
    cms_status_current = subquery.cms_appendix,
    cms_status_change = subquery.cms_change,
    last_updated = CURRENT_TIMESTAMP
FROM (
    SELECT 
        s.id as species_id,
        cms.appendix as cms_appendix,
        CASE 
            WHEN cms.appendix IS NOT NULL THEN 'new_listing'
            ELSE NULL
        END as cms_change
    FROM species s
    LEFT JOIN cms_listings cms ON s.id = cms.species_id
) subquery
WHERE ast.species_id = subquery.species_id;

-- Verify the update
SELECT 
    COUNT(*) as total_records,
    COUNT(cms_status_current) as records_with_cms,
    COUNT(*) - COUNT(cms_status_current) as records_without_cms
FROM article_summary_table;
```

**Expected output:**
- Should show 31 records with CMS status
- Remaining records should have NULL cms_status

## Post-Migration Verification

Run these queries to ensure everything is working:

```sql
-- Check CMS data integration
SELECT 
    s.common_name,
    s.scientific_name,
    ast.cms_status_current,
    ast.cms_status_change,
    cms.native_distribution
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
LEFT JOIN cms_listings cms ON s.id = cms.species_id
WHERE ast.cms_status_current IS NOT NULL
LIMIT 10;

-- Verify iconic species
SELECT 
    common_name,
    cms_status_current
FROM article_summary_table ast
JOIN species s ON ast.species_id = s.id
WHERE s.common_name IN ('Polar Bear', 'Narwhal', 'Beluga', 'Bowhead Whale');
```

## Files in This Migration

1. **create_cms_listings_table.sql** - SQL to create tables and views
2. **load_cms_data_to_db.py** - Python script to load CMS data
3. **verify_cms_data.py** - Python script to verify data integrity
4. **process_cms_species_data.py** - Data processing script (already run)
5. **CMS_MIGRATION_COMPLETE_GUIDE.md** - This guide

## Important Notes

1. **Data Source**: The CMS data comes from the official CMS species list (July 2025)
2. **Species Count**: 31 Arctic species have CMS listings
3. **Not All Species**: 12 Arctic species are NOT in CMS (e.g., Walrus)
4. **Integration**: This adds to existing CITES data, doesn't replace it

## Troubleshooting Guide

### Common Issues and Solutions

**Issue**: Table creation fails
- **Solution**: Check if tables already exist, drop them if needed:
  ```sql
  DROP TABLE IF EXISTS cms_listings CASCADE;
  DROP VIEW IF EXISTS species_cms_listings CASCADE;
  ```

**Issue**: Python scripts can't find modules
- **Solution**: Run from the API root directory or adjust Python path

**Issue**: No CMS data showing in article_summary_table
- **Solution**: Ensure Step 5 update query was run successfully

**Issue**: Authentication errors
- **Solution**: Verify `.env` file has correct Supabase URL and service role key

## Success Indicators

You'll know the migration is successful when:
- [ ] 31 species show CMS listings in the database
- [ ] The article_summary_table has cms_status_current populated
- [ ] Queries for Polar Bear, Narwhal show Appendix II status
- [ ] No errors in any verification scripts

## Next Steps

After successful migration:
1. Test the MCP tools to ensure they can query CMS data
2. Update any frontend components that display conservation status
3. Document the completion in the project log

---

**Support**: If you encounter issues not covered here, check the error logs or consult the Arctic Tracker database team.