#!/usr/bin/env python3
"""
Manual SQL NAMMCO Insert

Since the Supabase Python client has proxy issues, let's manually construct 
the SQL and use the database directly via SQL commands.
"""

import pandas as pd
from pathlib import Path

# Configuration
CSV_DIR = Path("/Users/magnussmari/Arctic-Tracker-API/species_data/nammco")
TEST_FILE = "Balaenoptera_acutorostrata_catches_2025-06-11.csv"

def generate_sql_for_csv(file_path):
    """Generate SQL statements for CSV data"""
    print(f"📂 Processing: {file_path.name}")
    
    try:
        df = pd.read_csv(file_path)
        print(f"📊 Loaded {len(df)} rows")
        
        # Extract species info
        species_name = df['SPECIES (SCIENTIFIC NAME)'].iloc[0]
        print(f"🎯 Species: {species_name}")
        
        # Generate species insert SQL
        genus, species = species_name.split(' ', 1)
        
        species_sql = f"""
-- Insert species if not exists
INSERT INTO species (scientific_name, common_name, kingdom, phylum, class, order_name, family, genus, species_name, authority)
SELECT '{species_name}', '{species_name}', 'ANIMALIA', 'CHORDATA', 'MAMMALIA', 'CETACEA', 'BALAENOPTERIDAE', '{genus}', '{species}', 'NAMMCO Import'
WHERE NOT EXISTS (SELECT 1 FROM species WHERE scientific_name = '{species_name}');
"""
        
        print("\n-- Species SQL:")
        print(species_sql)
        
        # Get unique countries
        countries = df['COUNTRY'].dropna().unique()
        
        country_sql = "\n-- Insert countries if not exist:\n"
        for country in countries:
            country_sql += f"""
INSERT INTO countries (country_name, nammco_member)
SELECT '{country}', true
WHERE NOT EXISTS (SELECT 1 FROM countries WHERE country_name = '{country}');
"""
        
        print(country_sql)
        
        # Generate catch records SQL
        print("\n-- Catch records SQL:")
        print(f"""
-- Insert catch records for {species_name}
WITH species_ref AS (
  SELECT id FROM species WHERE scientific_name = '{species_name}'
),
country_refs AS (
  SELECT id, country_name FROM countries WHERE country_name IN ({', '.join([f"'{c}'" for c in countries])})
)
INSERT INTO catch_records (species_id, country_id, year, catch_total, data_source)
SELECT 
  species_ref.id,
  country_refs.id,
  year_data.year,
  year_data.catch_total,
  'NAMMCO'
FROM species_ref
CROSS JOIN (VALUES""")
        
        # Generate data values
        values = []
        for idx, row in df.iterrows():
            if pd.notna(row['YEAR OR SEASON']) and pd.notna(row['CATCH TOTAL']):
                year = int(row['YEAR OR SEASON'])
                catch = int(float(row['CATCH TOTAL']))
                country = row['COUNTRY'] if pd.notna(row['COUNTRY']) else 'NULL'
                
                if country != 'NULL':
                    values.append(f"  ({year}, {catch}, '{country}')")
        
        for i, value in enumerate(values):
            if i == 0:
                print(value)
            else:
                print(f", {value}")
        
        print(f""") AS year_data(year, catch_total, country_name)
LEFT JOIN country_refs ON country_refs.country_name = year_data.country_name;
""")
        
        print(f"\n✅ Generated SQL for {len(values)} records")
        
        # Write to file
        sql_file = file_path.with_suffix('.sql')
        with open(sql_file, 'w') as f:
            f.write(species_sql)
            f.write(country_sql)
            f.write(f"""
-- Insert catch records for {species_name}
WITH species_ref AS (
  SELECT id FROM species WHERE scientific_name = '{species_name}'
),
country_refs AS (
  SELECT id, country_name FROM countries WHERE country_name IN ({', '.join([f"'{c}'" for c in countries])})
)
INSERT INTO catch_records (species_id, country_id, year, catch_total, data_source)
SELECT 
  species_ref.id,
  country_refs.id,
  year_data.year,
  year_data.catch_total,
  'NAMMCO'
FROM species_ref
CROSS JOIN (VALUES
""")
            for i, value in enumerate(values):
                if i == 0:
                    f.write(value)
                else:
                    f.write(f",\n{value}")
            
            f.write(f""") AS year_data(year, catch_total, country_name)
LEFT JOIN country_refs ON country_refs.country_name = year_data.country_name;
""")
        
        print(f"💾 SQL saved to: {sql_file}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("🚀 Generating SQL for NAMMCO data...")
    
    csv_file = CSV_DIR / TEST_FILE
    if csv_file.exists():
        generate_sql_for_csv(csv_file)
        print(f"""
🎉 SQL generated! 

To run this:
1. Open Supabase Dashboard SQL Editor
2. Copy and paste the SQL from {csv_file.with_suffix('.sql')}
3. Run it

Or use the command line:
psql -h db.cexwrbrnoxqtxjbiujiq.supabase.co -p 5432 -U postgres -d postgres -f {csv_file.with_suffix('.sql')}
""")
    else:
        print(f"❌ File not found: {csv_file}")

if __name__ == "__main__":
    main()
