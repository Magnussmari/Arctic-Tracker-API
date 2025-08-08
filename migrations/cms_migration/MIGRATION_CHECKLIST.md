# CMS Migration Checklist

**⏱️ Total Time: ~30-45 minutes**

## Pre-Migration
- [ ] Backup database (optional but recommended)
- [ ] Have Supabase dashboard open
- [ ] Terminal ready in migration folder

## Migration Steps

### 1. Create Tables (5-10 min)
- [ ] Open Supabase SQL Editor
- [ ] Copy contents of `create_cms_listings_table.sql`
- [ ] Paste and Run in SQL Editor
- [ ] Verify: "Success. No rows returned"

### 2. Quick Verify (2 min)
- [ ] Run table check query in SQL Editor
- [ ] Confirm both tables exist
- [ ] Confirm all columns present

### 3. Load Data (10-15 min)
- [ ] Terminal: `cd` to migration folder
- [ ] Run: `python load_cms_data_to_db.py --dry-run`
- [ ] Verify: "31 species found, 31 to insert, 0 errors"
- [ ] Run: `python load_cms_data_to_db.py` (actual load)
- [ ] Verify: Same results without [DRY RUN]

### 4. Verify Data (2 min)
- [ ] Run: `python verify_cms_data.py`
- [ ] Confirm: 31 total CMS listings
- [ ] Confirm: 7 Appendix I, 16 Appendix II, 8 Both

### 5. Update Summary Table (10-15 min)
- [ ] Copy UPDATE query from guide
- [ ] Run in SQL Editor
- [ ] Run verification query
- [ ] Confirm: 31 records with CMS status

## Post-Migration Checks
- [ ] Query Polar Bear - should show Appendix II
- [ ] Query Narwhal - should show Appendix II
- [ ] Check article_summary_table has CMS data
- [ ] Test one MCP query for CMS data

## Success Criteria
✅ 31 species with CMS listings  
✅ cms_status_current populated in article_summary_table  
✅ No errors in verification script  
✅ Iconic species (Polar Bear, Narwhal) show correct status

---

**Quick Terminal Commands:**
```bash
# Navigate to folder
cd /Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/migrations/cms_migration

# Dry run
python load_cms_data_to_db.py --dry-run

# Actual load
python load_cms_data_to_db.py

# Verify
python verify_cms_data.py
```

**If Something Goes Wrong:**
See `CMS_MIGRATION_COMPLETE_GUIDE.md` for detailed troubleshooting.