# Updated CMS Migration Guide - Schema Fix Required

**Date**: August 8, 2025  
**Issue Discovered**: Existing `cms_listings` table has incomplete schema  
**Solution**: Add missing columns before data load

## 🚨 NEW DISCOVERY

The `cms_listings` table already exists in the database but with an incomplete schema. It's missing critical columns including:
- `agreement`
- `listed_under`
- `listing_date`
- `notes`
- All distribution array columns

## Updated Migration Steps

### Step 0: Investigate Current State (NEW)

**Time: 5 minutes**

Run the investigation queries to understand what exists:

1. In Supabase SQL Editor, run each query from `investigate_existing_tables.sql`
2. Document what columns are missing
3. Check if there's any existing data (there shouldn't be)

### Step 1: Fix Table Schema (UPDATED)

**Time: 5 minutes**

Instead of creating new tables, we need to fix the existing schema:

1. Open Supabase SQL Editor
2. Copy contents of `fix_cms_listings_schema.sql`
3. Run the ALTER TABLE commands
4. This will add all missing columns

**Expected output:**
```
ALTER TABLE
COMMENT
[multiple times]
CREATE VIEW
GRANT
```

### Step 2: Verify Schema Fix

**Time: 2 minutes**

Run this verification query:

```sql
-- Should now show all columns including 'agreement'
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' 
AND table_name = 'cms_listings'
ORDER BY ordinal_position;
```

You should see:
- id
- species_id
- appendix
- agreement ✅ (newly added)
- listed_under ✅ (newly added)
- listing_date ✅ (newly added)
- notes ✅ (newly added)
- native_distribution ✅ (newly added)
- distribution_codes ✅ (newly added)
- introduced_distribution ✅ (newly added)
- extinct_distribution ✅ (newly added)
- distribution_uncertain ✅ (newly added)
- created_at
- updated_at ✅ (newly added)

### Step 3: Load CMS Data (Same as before)

**Time: 10-15 minutes**

Now that the schema is fixed, the data load should work:

```bash
cd /Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/migrations/cms_migration

# Dry run first
python load_cms_data_to_db.py --dry-run

# If successful, run actual load
python load_cms_data_to_db.py
```

### Step 4: Verify Data (Same as before)

**Time: 2 minutes**

```bash
python verify_cms_data.py
```

### Step 5: Update Article Summary Table (Same as before)

**Time: 10-15 minutes**

Use the same UPDATE query from `cms_migration_queries.sql`

## About cms_assessments Table

You also have an empty `cms_assessments` table. This is a different table that would store:
- Historical CMS assessment data
- Status changes over time
- Year of assessment

This is NOT the same as `cms_listings` which stores:
- Current CMS appendix listing (I, II, or I/II)
- Species distribution data
- Agreement information

For now, we're only populating `cms_listings`. The `cms_assessments` table can be populated later if historical CMS assessment data becomes available.

## Summary of Changes

1. **Don't drop existing tables** - They're already there
2. **Fix the schema** using ALTER TABLE instead of CREATE TABLE
3. **Then proceed** with data loading as originally planned

## If Things Go Wrong

If you need to start over:

```sql
-- Nuclear option - drop and recreate
DROP TABLE IF EXISTS cms_listings CASCADE;
DROP VIEW IF EXISTS species_cms_listings CASCADE;

-- Then run the original create_cms_listings_table.sql
```

But try the ALTER TABLE approach first as it's safer.

---

**Note**: This discovery explains why the July 10 "completion" failed - the table existed but with the wrong schema, preventing data loading.