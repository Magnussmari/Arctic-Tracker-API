# CMS Migration Action Plan

## Your Current Situation

✅ **Good News:**
- Both `cms_listings` and `cms_assessments` tables are empty (0 records)
- No risk of data loss
- Tables exist but just need schema adjustments

❌ **The Problem:**
- `cms_listings` has wrong schema
- Missing the `agreement` column (causing your error)
- Missing all distribution array columns
- `listing_date` is DATE type instead of TEXT

## Step-by-Step Fix

### 1. Fix the Schema (5 minutes)

Run in Supabase SQL Editor:
```sql
-- Copy and run the entire contents of:
-- fix_cms_listings_schema_precise.sql
```

This will:
- Add missing columns (agreement, distribution arrays, etc.)
- Fix listing_date type
- Remove is_current column
- Create the view
- Set up permissions

### 2. Verify Schema is Fixed (2 minutes)

After running the fix, this query should show all columns:
```sql
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'cms_listings' 
ORDER BY ordinal_position;
```

You should see 14 columns including `agreement`.

### 3. Load the Data (10 minutes)

```bash
cd /Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/migrations/cms_migration

# Test first
python load_cms_data_to_db.py --dry-run

# Then load
python load_cms_data_to_db.py
```

### 4. Verify Data Loaded (2 minutes)

```bash
python verify_cms_data.py
```

Should show 31 species loaded.

### 5. Update Article Summary Table (5 minutes)

Run the UPDATE query from `cms_migration_queries.sql`

## Total Time: ~25 minutes

## If Something Goes Wrong

Since the table is empty, worst case you can:
```sql
DROP TABLE cms_listings CASCADE;
-- Then run create_cms_listings_table.sql
```

But the ALTER approach should work fine.

---

**Ready?** Start with `fix_cms_listings_schema_precise.sql`!