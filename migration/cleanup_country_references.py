#!/usr/bin/env python3
"""
Country References Cleanup Script

This script standardizes country references across all tables in the Arctic Tracker database.
It handles multiple country reference formats and consolidates them to use the countries table.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path for importing modules
sys.path.append(str(Path(__file__).parent.parent))

# Direct Supabase import
try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
    
    # Load environment variables
    env_path = Path(__file__).parent.parent / 'config' / '.env'
    load_dotenv(env_path)
    
    # Get credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials in .env file")
        sys.exit(1)
    
    # Create client
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Supabase client created successfully")
    
except Exception as e:
    print(f"❌ Error creating Supabase client: {e}")
    sys.exit(1)

# Country code mappings (ISO 2-letter codes to full names)
COUNTRY_CODE_MAPPINGS = {
    # CITES country codes found in trade data
    'SA': 'Saudi Arabia',
    'IE': 'Ireland', 
    'US': 'United States',
    'CA': 'Canada',
    'NO': 'Norway',
    'IS': 'Iceland',
    'GL': 'Greenland',
    'FO': 'Faroe Islands',
    'DK': 'Denmark',
    'FI': 'Finland',
    'SE': 'Sweden',
    'RU': 'Russia',
    'JP': 'Japan',
    'KR': 'South Korea',
    'CN': 'China',
    'GB': 'United Kingdom',
    'DE': 'Germany',
    'FR': 'France',
    'ES': 'Spain',
    'PT': 'Portugal',
    'NL': 'Netherlands',
    'IT': 'Italy',
    'PL': 'Poland',
    'MX': 'Mexico',
    'AU': 'Australia',
    'NZ': 'New Zealand',
    'BR': 'Brazil',
    'AR': 'Argentina',
    'CL': 'Chile',
    'PE': 'Peru',
    'CO': 'Colombia',
    'EC': 'Ecuador',
    'ZA': 'South Africa',
    'MA': 'Morocco',
    'EG': 'Egypt',
    'TR': 'Turkey',
    'IN': 'India',
    'PK': 'Pakistan',
    'AF': 'Afghanistan',
    'KZ': 'Kazakhstan',
    'UZ': 'Uzbekistan',
    'KG': 'Kyrgyzstan',
    'TJ': 'Tajikistan',
    'TM': 'Turkmenistan',
    'MN': 'Mongolia',
    'IR': 'Iran',
    'IQ': 'Iraq',
    'SY': 'Syria',
    'IL': 'Israel',
    'BY': 'Belarus',
    'UA': 'Ukraine',
    'EE': 'Estonia',
    'LV': 'Latvia',
    'LT': 'Lithuania',
    'GT': 'Guatemala',
    'BZ': 'Belize',
    'CR': 'Costa Rica',
    'PA': 'Panama',
    'SN': 'Senegal',
    'GH': 'Ghana',
    'NG': 'Nigeria'
}

def get_all_countries() -> Dict[str, Dict[str, Any]]:
    """Get all countries from the countries table"""
    try:
        response = supabase.table('countries').select('*').execute()
        countries = {}
        
        for country in response.data:
            # Index by country name
            countries[country['country_name']] = country
            # Also index by country code if available
            if country.get('country_code'):
                countries[country['country_code']] = country
        
        print(f"📊 Loaded {len(response.data)} countries from database")
        return countries
        
    except Exception as e:
        print(f"❌ Error fetching countries: {e}")
        return {}

def find_or_create_country(country_identifier: str, countries_cache: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Find country ID by name or code, create if not exists"""
    try:
        # First try direct lookup
        if country_identifier in countries_cache:
            return countries_cache[country_identifier]['id']
        
        # Try mapping from country code
        if country_identifier in COUNTRY_CODE_MAPPINGS:
            country_name = COUNTRY_CODE_MAPPINGS[country_identifier]
            if country_name in countries_cache:
                return countries_cache[country_name]['id']
            
            # Create new country
            print(f"  🔧 Creating new country: {country_name} ({country_identifier})")
            new_country = {
                'country_name': country_name,
                'country_code': country_identifier,
                'nammco_member': False,
                'arctic_council': country_identifier in ['CA', 'DK', 'FI', 'IS', 'NO', 'RU', 'SE', 'US']
            }
            
            response = supabase.table('countries').insert(new_country).execute()
            if response.data and len(response.data) > 0:
                new_id = response.data[0]['id']
                countries_cache[country_name] = response.data[0]
                countries_cache[country_identifier] = response.data[0]
                return new_id
        
        # If all else fails, create with the identifier as name
        print(f"  🔧 Creating unknown country: {country_identifier}")
        new_country = {
            'country_name': country_identifier,
            'country_code': country_identifier if len(country_identifier) == 2 else None,
            'nammco_member': False,
            'arctic_council': False
        }
        
        response = supabase.table('countries').insert(new_country).execute()
        if response.data and len(response.data) > 0:
            new_id = response.data[0]['id']
            countries_cache[country_identifier] = response.data[0]
            return new_id
            
        return None
        
    except Exception as e:
        print(f"  ❌ Error finding/creating country '{country_identifier}': {e}")
        return None

def cleanup_catch_records(countries_cache: Dict[str, Dict[str, Any]]) -> bool:
    """Clean up country references in catch_records table"""
    try:
        print("\n🎣 Cleaning up catch_records table...")
        
        # Get all catch records with country text but no country_id
        response = supabase.table('catch_records').select('id, country, country_id').execute()
        records = response.data
        
        print(f"📊 Found {len(records)} catch records to analyze")
        
        updates_needed = []
        for record in records:
            if record.get('country') and not record.get('country_id'):
                country_text = record['country'].strip()
                country_id = find_or_create_country(country_text, countries_cache)
                
                if country_id:
                    updates_needed.append({
                        'id': record['id'],
                        'country_id': country_id
                    })
        
        print(f"🔄 Need to update {len(updates_needed)} catch records")
        
        # Update records in batches
        batch_size = 100
        for i in range(0, len(updates_needed), batch_size):
            batch = updates_needed[i:i + batch_size]
            for update in batch:
                try:
                    supabase.table('catch_records').update({
                        'country_id': update['country_id']
                    }).eq('id', update['id']).execute()
                except Exception as e:
                    print(f"  ⚠️  Warning: Failed to update catch record {update['id']}: {e}")
        
        print(f"✅ Updated catch records with country IDs")
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning catch_records: {e}")
        return False

def cleanup_cites_trade_records(countries_cache: Dict[str, Dict[str, Any]]) -> bool:
    """Clean up country references in CITES trade records"""
    try:
        print("\n📦 Cleaning up cites_trade_records table...")
        
        # Get unique country codes from CITES data
        response = supabase.table('cites_trade_records').select('importer, exporter, origin').execute()
        records = response.data
        
        print(f"📊 Found {len(records)} CITES trade records to analyze")
        
        # Collect unique country codes
        country_codes = set()
        for record in records:
            if record.get('importer'):
                country_codes.add(record['importer'])
            if record.get('exporter'):
                country_codes.add(record['exporter'])
            if record.get('origin'):
                country_codes.add(record['origin'])
        
        country_codes.discard('')  # Remove empty strings
        print(f"🌍 Found {len(country_codes)} unique country codes: {sorted(country_codes)}")
        
        # Ensure all country codes have corresponding countries
        missing_countries = []
        for code in country_codes:
            if code not in countries_cache:
                country_id = find_or_create_country(code, countries_cache)
                if not country_id:
                    missing_countries.append(code)
        
        if missing_countries:
            print(f"⚠️  Could not resolve country codes: {missing_countries}")
        else:
            print(f"✅ All CITES country codes resolved")
        
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning cites_trade_records: {e}")
        return False

def remove_redundant_country_columns() -> bool:
    """Remove redundant country text columns after cleanup"""
    try:
        print("\n🧹 Analyzing redundant country columns...")
        
        # Check if catch_records.country column can be removed
        response = supabase.table('catch_records').select('country, country_id').execute()
        records = response.data
        
        has_country_text = any(record.get('country') for record in records)
        has_country_ids = any(record.get('country_id') for record in records)
        
        print(f"📊 Catch records analysis:")
        print(f"  - Records with country text: {sum(1 for r in records if r.get('country'))}")
        print(f"  - Records with country_id: {sum(1 for r in records if r.get('country_id'))}")
        
        if has_country_ids and not has_country_text:
            print("✅ Ready to remove redundant 'country' column from catch_records")
            print("   SQL: ALTER TABLE catch_records DROP COLUMN IF EXISTS country;")
        elif has_country_text:
            print("⚠️  Still have country text data - cleanup needed first")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing redundant columns: {e}")
        return False

def generate_cleanup_report(countries_cache: Dict[str, Dict[str, Any]]) -> None:
    """Generate comprehensive cleanup report"""
    try:
        print("\n" + "="*60)
        print("📊 COUNTRY REFERENCES CLEANUP REPORT")
        print("="*60)
        
        # Countries summary
        all_countries = [c for c in countries_cache.values() if 'id' in c]
        arctic_council = [c for c in all_countries if c.get('arctic_council')]
        nammco_members = [c for c in all_countries if c.get('nammco_member')]
        
        print(f"\n🌍 Countries Database:")
        print(f"  Total countries: {len(all_countries)}")
        print(f"  Arctic Council members: {len(arctic_council)}")
        print(f"  NAMMCO members: {len(nammco_members)}")
        
        # Table analysis
        tables_with_countries = [
            'catch_records',
            'cites_trade_records',
            'distribution_ranges',
            'management_areas'
        ]
        
        print(f"\n📋 Tables with country references:")
        for table in tables_with_countries:
            try:
                response = supabase.table(table).select('*').limit(1).execute()
                if response.data:
                    columns = list(response.data[0].keys())
                    country_columns = [col for col in columns if 'country' in col.lower()]
                    print(f"  {table}: {country_columns}")
            except:
                print(f"  {table}: Could not analyze")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        print(f"  1. Use country_id (UUID) for all country references")
        print(f"  2. Remove redundant country text columns after migration")
        print(f"  3. Add foreign key constraints: country_id → countries.id")
        print(f"  4. Create indexes on country_id columns for performance")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")

def main():
    """Main cleanup function"""
    print("🧹 Arctic Tracker - Country References Cleanup")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Parse command line arguments
    dry_run = '--dry-run' in sys.argv
    report_only = '--report' in sys.argv
    
    # Load countries cache
    print("\n📚 Loading countries database...")
    countries_cache = get_all_countries()
    
    if report_only:
        generate_cleanup_report(countries_cache)
        return
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    
    # Step 1: Clean up catch records
    if not dry_run:
        cleanup_catch_records(countries_cache)
    else:
        print("\n🔍 DRY RUN: Would clean up catch_records table")
    
    # Step 2: Clean up CITES trade records
    if not dry_run:
        cleanup_cites_trade_records(countries_cache)
    else:
        print("\n🔍 DRY RUN: Would clean up cites_trade_records table")
    
    # Step 3: Analyze redundant columns
    remove_redundant_country_columns()
    
    # Step 4: Generate final report
    generate_cleanup_report(countries_cache)
    
    print(f"\n📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
Arctic Tracker - Country References Cleanup

Usage:
  python migration/cleanup_country_references.py [options]

Options:
  --dry-run    Analyze issues without making changes
  --report     Generate cleanup report and exit
  --help, -h   Show this help message

Examples:
  # Analyze current state
  python migration/cleanup_country_references.py --dry-run
  
  # Generate report only
  python migration/cleanup_country_references.py --report
  
  # Perform cleanup
  python migration/cleanup_country_references.py

Issues Addressed:
  • catch_records: Both 'country' (text) and 'country_id' (UUID) columns
  • cites_trade_records: Country codes ('SA', 'IE') need mapping to countries table
  • Missing countries: Creates new country records as needed
  • Redundant columns: Identifies columns that can be removed after cleanup

Result:
  • Standardized country references using countries.id
  • All country codes mapped to proper country records
  • Recommendations for schema cleanup
        """)
    else:
        main()
