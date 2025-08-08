# CMS Migration Decision Tree

## Start Here

### 1. Does cms_listings table exist?

Run in SQL Editor:
```sql
SELECT EXISTS (
    SELECT 1 FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name = 'cms_listings'
);
```

- **YES** → Go to step 2
- **NO** → Use `create_cms_listings_table.sql` (original plan)

### 2. Does cms_listings have the 'agreement' column?

Run in SQL Editor:
```sql
SELECT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema = 'public' 
    AND table_name = 'cms_listings'
    AND column_name = 'agreement'
);
```

- **YES** → Schema is correct, go to step 4
- **NO** → Go to step 3

### 3. Fix the schema

Run `fix_cms_listings_schema.sql` to add missing columns

### 4. Is cms_listings empty?

Run in SQL Editor:
```sql
SELECT COUNT(*) FROM cms_listings;
```

- **0 records** → Safe to load data, go to step 5
- **Has records** → STOP! Investigate what data exists

### 5. Load the data

Run the Python scripts:
```bash
python load_cms_data_to_db.py --dry-run
python load_cms_data_to_db.py
```

### 6. Update article_summary_table

Run the UPDATE query from `cms_migration_queries.sql`

## Quick Reference

Based on your error, you're at **Step 3** - the table exists but needs schema fixes.

**Your path**: Fix Schema → Load Data → Update Summary Table