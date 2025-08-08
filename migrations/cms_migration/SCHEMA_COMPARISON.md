# CMS Listings Schema Comparison

## Current Schema (What Exists)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid | ✅ Correct |
| species_id | uuid | ✅ Correct |
| appendix | text | ✅ Correct |
| listing_date | **date** | ❌ Wrong type (should be text) |
| notes | text | ✅ Correct |
| is_current | boolean | ❌ Not needed |
| created_at | timestamp | ✅ Correct |
| updated_at | timestamp | ✅ Correct |

## Required Schema (What We Need)

| Column | Type | Status |
|--------|------|--------|
| id | uuid | ✅ Exists |
| species_id | uuid | ✅ Exists |
| appendix | text | ✅ Exists |
| agreement | text | ❌ **MISSING** |
| listed_under | text | ❌ **MISSING** |
| listing_date | text | ⚠️ Exists but wrong type |
| notes | text | ✅ Exists |
| native_distribution | text[] | ❌ **MISSING** |
| distribution_codes | text[] | ❌ **MISSING** |
| introduced_distribution | text[] | ❌ **MISSING** |
| extinct_distribution | text[] | ❌ **MISSING** |
| distribution_uncertain | text[] | ❌ **MISSING** |
| created_at | timestamp | ✅ Exists |
| updated_at | timestamp | ✅ Exists |

## Key Issues

1. **Missing `agreement` column** - This is what caused the error
2. **Missing distribution arrays** - All 5 array columns are missing
3. **Wrong type for `listing_date`** - It's DATE but should be TEXT
4. **Extra column `is_current`** - Not in our data model
5. **Missing view** - `species_cms_listings` doesn't exist

## Solution

Run `fix_cms_listings_schema_precise.sql` which will:
1. Add all missing columns
2. Convert listing_date from DATE to TEXT
3. Drop the unnecessary is_current column
4. Create the missing view
5. Set up proper permissions and RLS

## Why This Happened

The table was likely created from a different schema definition, possibly:
- An earlier version of the migration
- A manual table creation
- A different data model altogether

This explains why the July 10 "completion" failed - the table structure didn't match what the data loading script expected.