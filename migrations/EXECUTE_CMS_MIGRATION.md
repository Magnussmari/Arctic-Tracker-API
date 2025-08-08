# Execute CMS Migration - Step by Step Guide

## IMPORTANT: Manual SQL Execution Required

The CMS listings table needs to be created in your Supabase database before loading the data.

## Steps to Execute:

1. **Login to Supabase Dashboard**
   - Go to https://supabase.com/dashboard
   - Navigate to your Arctic Tracker project

2. **Open SQL Editor**
   - Click on "SQL Editor" in the left sidebar
   - Click "New query" button

3. **Copy and Execute the Migration**
   - Copy the entire contents of `create_cms_listings_table.sql`
   - Paste into the SQL editor
   - Click "Run" button

4. **Verify Success**
   - You should see a success message
   - The following should be created:
     - `cms_listings` table
     - `species_cms_listings` view
     - Indexes and RLS policies

5. **Test the Table**
   Run this query to verify:
   ```sql
   SELECT * FROM cms_listings LIMIT 1;
   ```
   
   You should get an empty result (no error).

## After Migration is Complete

Return to the terminal and run:
```bash
cd /Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API
python core/load_cms_data_to_db.py
```

This will load all 31 Arctic species CMS data into the database.