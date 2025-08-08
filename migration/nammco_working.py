#!/usr/bin/env python3
"""
Working NAMMCO Import Script

Uses the same config approach as other working scripts in the project.
"""

import pandas as pd
import os
import sys
from pathlib import Path

# Add config directory to path (same as other working scripts)
sys.path.append(str(Path(__file__).parent.parent / 'config'))

print("🚀 Starting NAMMCO import...")

# Use the same config approach as load_optimized_trade_data.py
try:
    from supabase_config import get_supabase_client
    # Try with service role for better permissions and potentially bypass proxy issues
    supabase = get_supabase_client(use_service_role=True)
    print("✅ Connected to Supabase using service role")
except Exception as e:
    # Fallback to regular key
    try:
        supabase = get_supabase_client(use_service_role=False)
        print("✅ Connected to Supabase using anon key")
    except Exception as e2:
        print(f"❌ Connection failed: {e2}")
        exit(1)

# Configuration
CSV_DIR = Path("/Users/magnussmari/Arctic-Tracker-API/species_data/nammco")
TEST_FILE = "Balaenoptera_acutorostrata_catches_2025-06-11.csv"

def create_species(name):
    """Create a new species entry"""
    parts = name.strip().split()
    if len(parts) < 2:
        return None
    
    species_data = {
        'scientific_name': name,
        'common_name': name,
        'kingdom': 'ANIMALIA',
        'phylum': 'CHORDATA', 
        'class': 'MAMMALIA',
        'order_name': 'CETACEA',
        'family': 'BALAENOPTERIDAE',
        'genus': parts[0],
        'species_name': parts[1],
        'authority': 'NAMMCO Import'
    }
    
    try:
        result = supabase.table('species').insert(species_data).execute()
        if result.data:
            species_id = result.data[0]['id']
            print(f"  ✅ Created species: {name} (ID: {species_id})")
            return species_id
    except Exception as e:
        print(f"  ❌ Failed to create species {name}: {e}")
    
    return None

def get_or_create_species(name):
    """Get species ID or create if missing"""
    # Try to find existing
    try:
        result = supabase.table('species').select('id').eq('scientific_name', name).execute()
        if result.data:
            species_id = result.data[0]['id']
            print(f"  ✅ Found species: {name} (ID: {species_id})")
            return species_id
    except Exception as e:
        print(f"  ⚠️ Error searching for species: {e}")
    
    # Create new
    print(f"  🔧 Creating new species: {name}")
    return create_species(name)

def create_country(name):
    """Create a new country entry"""
    country_data = {
        'country_name': name,
        'nammco_member': True
    }
    
    try:
        result = supabase.table('countries').insert(country_data).execute()
        if result.data:
            country_id = result.data[0]['id']
            print(f"  ✅ Created country: {name} (ID: {country_id})")
            return country_id
    except Exception as e:
        print(f"  ❌ Failed to create country {name}: {e}")
    
    return None

def get_or_create_country(name):
    """Get country ID or create if missing"""
    if not name:
        return None
        
    # Try to find existing
    try:
        result = supabase.table('countries').select('id').eq('country_name', name).execute()
        if result.data:
            country_id = result.data[0]['id']
            print(f"  ✅ Found country: {name} (ID: {country_id})")
            return country_id
    except Exception as e:
        print(f"  ⚠️ Error searching for country: {e}")
    
    # Create new
    print(f"  🔧 Creating new country: {name}")
    return create_country(name)

def insert_catch_record(species_id, country_id, year, catch_total):
    """Insert catch record"""
    record_data = {
        'species_id': species_id,
        'year': int(year),
        'data_source': 'NAMMCO'
    }
    
    if country_id:
        record_data['country_id'] = country_id
    
    if catch_total and str(catch_total).strip() and str(catch_total).lower() != 'nan':
        try:
            record_data['catch_total'] = int(float(catch_total))
        except:
            pass
    
    try:
        result = supabase.table('catch_records').insert(record_data).execute()
        if result.data:
            record_id = result.data[0]['id']
            print(f"    ✅ Inserted record (ID: {record_id}) - Year: {year}, Catch: {catch_total}")
            return True
    except Exception as e:
        print(f"    ❌ Failed to insert record: {e}")
    
    return False

def process_csv(file_path):
    """Process a single CSV file"""
    print(f"\n📂 Processing: {file_path.name}")
    
    try:
        df = pd.read_csv(file_path)
        print(f"  📊 Loaded {len(df)} rows")
        print(f"  📋 Columns: {list(df.columns)}")
        
        if len(df) == 0:
            print("  ⚠️ Empty file")
            return 0
        
        # Show first few rows for debugging
        print(f"  📄 First row data:")
        first_row = df.iloc[0]
        for col in df.columns:
            print(f"    {col}: {first_row[col]}")
        
        # Find species name
        species_name = None
        for col in ['SPECIES (SCIENTIFIC NAME)', 'Scientific Name', 'Species']:
            if col in df.columns:
                species_name = df[col].iloc[0]
                print(f"  🔍 Found species in column '{col}': {species_name}")
                break
        
        if not species_name:
            print("  ❌ No species name found")
            return 0
        
        print(f"  🎯 Target species: {species_name}")
        
        # Get or create species
        species_id = get_or_create_species(species_name)
        if not species_id:
            print("  ❌ Could not get species ID")
            return 0
        
        # Process each row
        processed = 0
        for idx, row in df.iterrows():
            try:
                # Get basic data with more flexible column matching
                country = None
                year = None
                catch = None
                
                # Try multiple column name variations
                for col in ['COUNTRY', 'Country', 'country']:
                    if col in df.columns and pd.notna(row[col]):
                        country = row[col]
                        break
                
                for col in ['YEAR OR SEASON', 'Year', 'year', 'YEAR']:
                    if col in df.columns and pd.notna(row[col]):
                        year = row[col]
                        break
                        
                for col in ['CATCH TOTAL', 'Catch', 'catch', 'CATCH', 'Total']:
                    if col in df.columns and pd.notna(row[col]):
                        catch = row[col]
                        break
                
                if not year:
                    continue
                
                # Clean year
                try:
                    year = int(float(str(year)))
                    if year < 1900 or year > 2030:
                        continue
                except:
                    continue
                
                # Get country ID
                country_id = get_or_create_country(country) if country else None
                
                # Insert record
                if insert_catch_record(species_id, country_id, year, catch):
                    processed += 1
                    
            except Exception as e:
                print(f"    ⚠️ Row {idx} error: {e}")
                continue
        
        print(f"  ✅ Processed {processed} records")
        return processed
        
    except Exception as e:
        print(f"  ❌ File error: {e}")
        import traceback
        traceback.print_exc()
        return 0

def main():
    """Main function"""
    print(f"📁 Looking in: {CSV_DIR}")
    
    if not CSV_DIR.exists():
        print(f"❌ Directory not found: {CSV_DIR}")
        return
    
    # Find CSV files
    csv_files = list(CSV_DIR.glob("*.csv"))
    print(f"📄 Found {len(csv_files)} CSV files")
    
    # Test with single file first
    test_files = [f for f in csv_files if f.name == TEST_FILE]
    
    if test_files:
        print(f"🎯 Testing with: {TEST_FILE}")
        total = process_csv(test_files[0])
        print(f"\n🎉 Test complete! Processed {total} records")
    else:
        print(f"❌ Test file not found: {TEST_FILE}")
        print("Available files:")
        for f in csv_files[:5]:
            print(f"  - {f.name}")

if __name__ == "__main__":
    main()
