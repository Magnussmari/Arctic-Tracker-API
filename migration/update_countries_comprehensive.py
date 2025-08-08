#!/usr/bin/env python3
"""
Comprehensive Countries Table Update

This script adds all relevant countries for Arctic species conservation,
including Arctic nations, range states, and countries involved in wildlife trade.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

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

# Comprehensive countries list
COUNTRIES_DATA = [
    # Arctic Council Members (8 countries)
    {"country_name": "Canada", "country_code": "CA", "nammco_member": False, "arctic_council": True, "region": "North America"},
    {"country_name": "Denmark", "country_code": "DK", "nammco_member": False, "arctic_council": True, "region": "Europe"},
    {"country_name": "Finland", "country_code": "FI", "nammco_member": False, "arctic_council": True, "region": "Europe"},
    {"country_name": "Iceland", "country_code": "IS", "nammco_member": True, "arctic_council": True, "region": "Europe"},
    {"country_name": "Norway", "country_code": "NO", "nammco_member": True, "arctic_council": True, "region": "Europe"},
    {"country_name": "Russia", "country_code": "RU", "nammco_member": False, "arctic_council": True, "region": "Eurasia"},
    {"country_name": "Sweden", "country_code": "SE", "nammco_member": False, "arctic_council": True, "region": "Europe"},
    {"country_name": "United States", "country_code": "US", "nammco_member": False, "arctic_council": True, "region": "North America"},
    
    # NAMMCO Members (autonomous territories)
    {"country_name": "Greenland", "country_code": "GL", "nammco_member": True, "arctic_council": False, "region": "North America"},
    {"country_name": "Faroe Islands", "country_code": "FO", "nammco_member": True, "arctic_council": False, "region": "Europe"},
    
    # Other Arctic/Sub-Arctic Countries
    {"country_name": "Alaska", "country_code": "US-AK", "nammco_member": False, "arctic_council": False, "region": "North America"},
    {"country_name": "Svalbard", "country_code": "SJ", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    
    # Major Range States for Arctic Species
    {"country_name": "Japan", "country_code": "JP", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "South Korea", "country_code": "KR", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "China", "country_code": "CN", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Mongolia", "country_code": "MN", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    
    # European Countries (species range/migration)
    {"country_name": "United Kingdom", "country_code": "GB", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Ireland", "country_code": "IE", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Netherlands", "country_code": "NL", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Germany", "country_code": "DE", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "France", "country_code": "FR", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Spain", "country_code": "ES", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Portugal", "country_code": "PT", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Italy", "country_code": "IT", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Poland", "country_code": "PL", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Estonia", "country_code": "EE", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Latvia", "country_code": "LV", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Lithuania", "country_code": "LT", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Belarus", "country_code": "BY", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    {"country_name": "Ukraine", "country_code": "UA", "nammco_member": False, "arctic_council": False, "region": "Europe"},
    
    # North American Countries
    {"country_name": "Mexico", "country_code": "MX", "nammco_member": False, "arctic_council": False, "region": "North America"},
    {"country_name": "Guatemala", "country_code": "GT", "nammco_member": False, "arctic_council": False, "region": "Central America"},
    {"country_name": "Belize", "country_code": "BZ", "nammco_member": False, "arctic_council": False, "region": "Central America"},
    {"country_name": "Costa Rica", "country_code": "CR", "nammco_member": False, "arctic_council": False, "region": "Central America"},
    {"country_name": "Panama", "country_code": "PA", "nammco_member": False, "arctic_council": False, "region": "Central America"},
    
    # South American Countries (migration routes)
    {"country_name": "Colombia", "country_code": "CO", "nammco_member": False, "arctic_council": False, "region": "South America"},
    {"country_name": "Ecuador", "country_code": "EC", "nammco_member": False, "arctic_council": False, "region": "South America"},
    {"country_name": "Peru", "country_code": "PE", "nammco_member": False, "arctic_council": False, "region": "South America"},
    {"country_name": "Chile", "country_code": "CL", "nammco_member": False, "arctic_council": False, "region": "South America"},
    {"country_name": "Argentina", "country_code": "AR", "nammco_member": False, "arctic_council": False, "region": "South America"},
    {"country_name": "Brazil", "country_code": "BR", "nammco_member": False, "arctic_council": False, "region": "South America"},
    
    # African Countries (migration routes)
    {"country_name": "Morocco", "country_code": "MA", "nammco_member": False, "arctic_council": False, "region": "Africa"},
    {"country_name": "Senegal", "country_code": "SN", "nammco_member": False, "arctic_council": False, "region": "Africa"},
    {"country_name": "Ghana", "country_code": "GH", "nammco_member": False, "arctic_council": False, "region": "Africa"},
    {"country_name": "Nigeria", "country_code": "NG", "nammco_member": False, "arctic_council": False, "region": "Africa"},
    {"country_name": "South Africa", "country_code": "ZA", "nammco_member": False, "arctic_council": False, "region": "Africa"},
    
    # Asian Countries (range states)
    {"country_name": "India", "country_code": "IN", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Pakistan", "country_code": "PK", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Afghanistan", "country_code": "AF", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Kazakhstan", "country_code": "KZ", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Uzbekistan", "country_code": "UZ", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Kyrgyzstan", "country_code": "KG", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Tajikistan", "country_code": "TJ", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Turkmenistan", "country_code": "TM", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    
    # Oceania (migration routes)
    {"country_name": "Australia", "country_code": "AU", "nammco_member": False, "arctic_council": False, "region": "Oceania"},
    {"country_name": "New Zealand", "country_code": "NZ", "nammco_member": False, "arctic_council": False, "region": "Oceania"},
    
    # Additional Important Countries
    {"country_name": "Turkey", "country_code": "TR", "nammco_member": False, "arctic_council": False, "region": "Eurasia"},
    {"country_name": "Iran", "country_code": "IR", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Iraq", "country_code": "IQ", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Syria", "country_code": "SY", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Israel", "country_code": "IL", "nammco_member": False, "arctic_council": False, "region": "Asia"},
    {"country_name": "Egypt", "country_code": "EG", "nammco_member": False, "arctic_council": False, "region": "Africa"},
    
    # International Waters/Organizations
    {"country_name": "International Waters", "country_code": "INT", "nammco_member": False, "arctic_council": False, "region": "International"},
    {"country_name": "Unknown", "country_code": "UNK", "nammco_member": False, "arctic_council": False, "region": "Unknown"},
]

def get_existing_countries():
    """Get existing countries from database"""
    try:
        response = supabase.table('countries').select('country_name, country_code').execute()
        existing = {country['country_name']: country for country in response.data}
        print(f"📊 Found {len(existing)} existing countries in database")
        return existing
    except Exception as e:
        print(f"❌ Error fetching existing countries: {e}")
        return {}

def add_missing_countries(dry_run=False):
    """Add missing countries to database"""
    existing_countries = get_existing_countries()
    
    new_countries = []
    updated_countries = []
    
    for country_data in COUNTRIES_DATA:
        country_name = country_data['country_name']
        
        if country_name in existing_countries:
            # Check if we need to update existing country
            existing = existing_countries[country_name]
            if existing.get('country_code') != country_data['country_code']:
                updated_countries.append(country_data)
        else:
            # New country to add
            new_countries.append(country_data)
    
    print(f"\n📋 Countries to add: {len(new_countries)}")
    print(f"🔄 Countries to update: {len(updated_countries)}")
    
    if dry_run:
        print("\n🔍 DRY RUN - Countries that would be added:")
        for country in new_countries:
            print(f"  + {country['country_name']} ({country['country_code']}) - {country['region']}")
        
        print("\n🔍 DRY RUN - Countries that would be updated:")
        for country in updated_countries:
            print(f"  ~ {country['country_name']} ({country['country_code']})")
        
        return len(new_countries), len(updated_countries)
    
    # Add new countries
    if new_countries:
        print(f"\n➕ Adding {len(new_countries)} new countries...")
        try:
            response = supabase.table('countries').insert(new_countries).execute()
            print(f"✅ Successfully added {len(response.data)} countries")
        except Exception as e:
            print(f"❌ Error adding countries: {e}")
    
    # Update existing countries
    if updated_countries:
        print(f"\n🔄 Updating {len(updated_countries)} existing countries...")
        for country in updated_countries:
            try:
                response = supabase.table('countries').update(country).eq('country_name', country['country_name']).execute()
                print(f"  ✅ Updated: {country['country_name']}")
            except Exception as e:
                print(f"  ❌ Error updating {country['country_name']}: {e}")
    
    return len(new_countries), len(updated_countries)

def generate_countries_report():
    """Generate a report of all countries by category"""
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE COUNTRIES REPORT")
    print("="*60)
    
    # Group countries by category
    arctic_council = [c for c in COUNTRIES_DATA if c.get('arctic_council', False)]
    nammco_members = [c for c in COUNTRIES_DATA if c.get('nammco_member', False)]
    
    # Group by region
    regions = {}
    for country in COUNTRIES_DATA:
        region = country['region']
        if region not in regions:
            regions[region] = []
        regions[region].append(country)
    
    print(f"\n🌍 Arctic Council Members ({len(arctic_council)}):")
    for country in sorted(arctic_council, key=lambda x: x['country_name']):
        print(f"  • {country['country_name']} ({country['country_code']})")
    
    print(f"\n🐋 NAMMCO Members ({len(nammco_members)}):")
    for country in sorted(nammco_members, key=lambda x: x['country_name']):
        print(f"  • {country['country_name']} ({country['country_code']})")
    
    print(f"\n🗺️  Countries by Region:")
    for region, countries in sorted(regions.items()):
        print(f"\n  {region} ({len(countries)}):")
        for country in sorted(countries, key=lambda x: x['country_name']):
            flags = []
            if country.get('arctic_council'): flags.append("AC")
            if country.get('nammco_member'): flags.append("NAMMCO")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(f"    • {country['country_name']} ({country['country_code']}){flag_str}")
    
    print(f"\n📈 Total Countries: {len(COUNTRIES_DATA)}")

def main():
    """Main function"""
    print("🌍 Arctic Tracker - Comprehensive Countries Update")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Parse command line arguments
    dry_run = '--dry-run' in sys.argv
    report_only = '--report' in sys.argv
    
    if report_only:
        generate_countries_report()
        return
    
    # Add/update countries
    added, updated = add_missing_countries(dry_run=dry_run)
    
    if not dry_run:
        print(f"\n✅ Countries update completed!")
        print(f"   Added: {added} countries")
        print(f"   Updated: {updated} countries")
        
        # Generate final report
        generate_countries_report()
    
    print(f"\n📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
Arctic Tracker - Comprehensive Countries Update

Usage:
  python migration/update_countries_comprehensive.py [options]

Options:
  --dry-run    Show what would be added/updated without making changes
  --report     Generate countries report and exit
  --help, -h   Show this help message

Examples:
  # See what countries would be added
  python migration/update_countries_comprehensive.py --dry-run
  
  # Add all missing countries to database
  python migration/update_countries_comprehensive.py
  
  # Generate countries report
  python migration/update_countries_comprehensive.py --report

Countries Added:
  • Arctic Council members (8 countries)
  • NAMMCO members (4 territories)
  • Major range states for Arctic species
  • Migration route countries
  • Wildlife trade countries
  • Total: ~60 countries
        """)
    else:
        main()
