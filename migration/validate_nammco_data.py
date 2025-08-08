#!/usr/bin/env python3
"""
NAMMCO Data Validation Script
Reads CSV files and shows what data would be assigned to each table
"""

import os
import csv
import sys
from collections import defaultdict
from pathlib import Path

# Add the parent directory to the path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def clean_numeric_value(value):
    """Clean and convert numeric values, handling special cases"""
    if not value or value.strip() == '':
        return None
    
    value = str(value).strip()
    
    # Handle special cases
    if value.lower() in ['n/a', 'na', 'null', '*no reported catches']:
        return None
    if value.lower() == 'no quota':
        return None
    
    # Remove any non-numeric characters except decimal points and negative signs
    cleaned = ''.join(c for c in value if c.isdigit() or c in '.-')
    
    try:
        # Try to convert to integer first, then float
        if '.' in cleaned:
            return float(cleaned)
        else:
            return int(cleaned)
    except ValueError:
        return None

def normalize_country_name(country):
    """Normalize country names"""
    country = country.strip()
    
    # Country normalization mapping
    country_mapping = {
        'greenland': 'Greenland',
        'iceland': 'Iceland',
        'norway': 'Norway',
        'faroe islands': 'Faroe Islands',
        'faroes': 'Faroe Islands',
    }
    
    return country_mapping.get(country.lower(), country)

def parse_year_season(year_season):
    """Parse year or season field"""
    year_season = str(year_season).strip()
    
    # Handle ranges like "2009/2010" or "1992-2005"
    if '/' in year_season:
        parts = year_season.split('/')
        try:
            return int(parts[0])  # Use the first year
        except ValueError:
            return None
    elif '-' in year_season and len(year_season) > 4:
        parts = year_season.split('-')
        try:
            return int(parts[0])  # Use the first year
        except ValueError:
            return None
    else:
        try:
            return int(year_season)
        except ValueError:
            return None

def validate_csv_files():
    """Validate all CSV files and show what would be inserted into each table"""
    
    csv_dir = Path("species_data/nammco")
    
    if not csv_dir.exists():
        print(f"❌ Directory {csv_dir} does not exist!")
        return
    
    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        print(f"❌ No CSV files found in {csv_dir}")
        return
    
    print(f"🔍 Found {len(csv_files)} CSV files to validate")
    print("=" * 80)
    
    # Collections to track what would be inserted
    countries_data = set()
    management_areas_data = set()
    catch_records_data = []
    
    # Track issues
    issues = []
    
    for csv_file in csv_files:
        print(f"\n📄 Processing: {csv_file.name}")
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Check if required columns exist
                required_columns = ['COUNTRY', 'SPECIES (SCIENTIFIC NAME)', 'YEAR OR SEASON', 
                                  'AREA OR STOCK', 'CATCH TOTAL']
                missing_columns = [col for col in required_columns if col not in reader.fieldnames]
                
                if missing_columns:
                    issues.append(f"❌ {csv_file.name}: Missing columns: {missing_columns}")
                    continue
                
                file_records = 0
                file_issues = 0
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                    file_records += 1
                    
                    # Extract and clean data
                    country = normalize_country_name(row['COUNTRY']) if row['COUNTRY'] else None
                    scientific_name = row['SPECIES (SCIENTIFIC NAME)'].strip() if row['SPECIES (SCIENTIFIC NAME)'] else None
                    year = parse_year_season(row['YEAR OR SEASON'])
                    area_stock = row['AREA OR STOCK'].strip() if row['AREA OR STOCK'] else None
                    catch_total = clean_numeric_value(row['CATCH TOTAL'])
                    quota = clean_numeric_value(row.get('QUOTA (IF APPLICABLE)', ''))
                    
                    # Validate required fields
                    if not country:
                        issues.append(f"❌ {csv_file.name} row {row_num}: Missing country")
                        file_issues += 1
                        continue
                    
                    if not scientific_name:
                        issues.append(f"❌ {csv_file.name} row {row_num}: Missing scientific name")
                        file_issues += 1
                        continue
                    
                    if year is None:
                        issues.append(f"❌ {csv_file.name} row {row_num}: Invalid year: '{row['YEAR OR SEASON']}'")
                        file_issues += 1
                        continue
                    
                    if not area_stock:
                        issues.append(f"❌ {csv_file.name} row {row_num}: Missing area/stock")
                        file_issues += 1
                        continue
                    
                    if catch_total is None:
                        issues.append(f"⚠️  {csv_file.name} row {row_num}: No catch total (will be set to 0)")
                        catch_total = 0
                    
                    # Add to collections
                    countries_data.add(country)
                    management_areas_data.add((area_stock, country))
                    
                    catch_records_data.append({
                        'file': csv_file.name,
                        'row': row_num,
                        'country': country,
                        'scientific_name': scientific_name,
                        'year': year,
                        'area_stock': area_stock,
                        'catch_total': catch_total,
                        'quota': quota
                    })
                
                print(f"   ✅ Processed {file_records} records ({file_issues} issues)")
                
        except Exception as e:
            issues.append(f"❌ Error processing {csv_file.name}: {str(e)}")
    
    # Display validation results
    print("\n" + "=" * 80)
    print("📊 VALIDATION RESULTS")
    print("=" * 80)
    
    # Countries table
    print(f"\n🌍 COUNTRIES TABLE ({len(countries_data)} unique countries):")
    for country in sorted(countries_data):
        print(f"   - {country}")
    
    # Management areas table
    print(f"\n📍 MANAGEMENT_AREAS TABLE ({len(management_areas_data)} unique areas):")
    areas_by_country = defaultdict(list)
    for area, country in management_areas_data:
        areas_by_country[country].append(area)
    
    for country in sorted(areas_by_country.keys()):
        print(f"   {country}:")
        for area in sorted(areas_by_country[country]):
            print(f"     - {area}")
    
    # Catch records summary
    print(f"\n📈 CATCH_RECORDS TABLE ({len(catch_records_data)} total records):")
    
    # Group by species
    records_by_species = defaultdict(int)
    records_by_country = defaultdict(int)
    records_by_year = defaultdict(int)
    
    for record in catch_records_data:
        records_by_species[record['scientific_name']] += 1
        records_by_country[record['country']] += 1
        records_by_year[record['year']] += 1
    
    print("   By Species:")
    for species in sorted(records_by_species.keys()):
        print(f"     - {species}: {records_by_species[species]} records")
    
    print("   By Country:")
    for country in sorted(records_by_country.keys()):
        print(f"     - {country}: {records_by_country[country]} records")
    
    print("   Year Range:")
    years = [year for year in records_by_year.keys() if year is not None]
    if years:
        print(f"     - {min(years)} to {max(years)}")
    
    # Show sample records
    print(f"\n📋 SAMPLE CATCH RECORDS (first 5):")
    for i, record in enumerate(catch_records_data[:5]):
        print(f"   {i+1}. {record['country']} | {record['scientific_name']} | {record['year']} | {record['area_stock']} | Catch: {record['catch_total']} | Quota: {record['quota']}")
    
    # Issues summary
    if issues:
        print(f"\n⚠️  ISSUES FOUND ({len(issues)}):")
        for issue in issues[:20]:  # Show first 20 issues
            print(f"   {issue}")
        if len(issues) > 20:
            print(f"   ... and {len(issues) - 20} more issues")
    else:
        print(f"\n✅ NO ISSUES FOUND - Data looks good!")
    
    print(f"\n📊 SUMMARY:")
    print(f"   - {len(countries_data)} unique countries")
    print(f"   - {len(management_areas_data)} unique management areas")
    print(f"   - {len(catch_records_data)} catch records")
    print(f"   - {len(issues)} validation issues")
    
    return len(issues) == 0

if __name__ == "__main__":
    print("🔍 NAMMCO Data Validation")
    print("=" * 80)
    
    success = validate_csv_files()
    
    if success:
        print(f"\n✅ Validation completed successfully!")
        print("   Data is ready for import.")
    else:
        print(f"\n❌ Validation found issues!")
        print("   Please review and fix issues before importing.")
    
    print("\n" + "=" * 80)
