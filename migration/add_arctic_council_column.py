#!/usr/bin/env python3
"""
Add Arctic Council Column to Countries Table

This script adds the arctic_council column and updates countries with Arctic Council membership.
"""

import sys
import os
from pathlib import Path
from datetime import datetime

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

# Arctic Council Members
ARCTIC_COUNCIL_COUNTRIES = [
    {"country_name": "Canada", "country_code": "CA"},
    {"country_name": "Denmark", "country_code": "DK"},
    {"country_name": "Finland", "country_code": "FI"},
    {"country_name": "Iceland", "country_code": "IS"},
    {"country_name": "Norway", "country_code": "NO"},
    {"country_name": "Russia", "country_code": "RU"},
    {"country_name": "Sweden", "country_code": "SE"},
    {"country_name": "United States", "country_code": "US"},
]

# Additional countries to add (non-Arctic Council)
ADDITIONAL_COUNTRIES = [
    {"country_name": "Canada", "country_code": "CA", "nammco_member": False},
    {"country_name": "Denmark", "country_code": "DK", "nammco_member": False},
    {"country_name": "Finland", "country_code": "FI", "nammco_member": False},
    {"country_name": "Russia", "country_code": "RU", "nammco_member": False},
    {"country_name": "Sweden", "country_code": "SE", "nammco_member": False},
    {"country_name": "United States", "country_code": "US", "nammco_member": False},
    {"country_name": "Japan", "country_code": "JP", "nammco_member": False},
    {"country_name": "United Kingdom", "country_code": "GB", "nammco_member": False},
    {"country_name": "Germany", "country_code": "DE", "nammco_member": False},
    {"country_name": "France", "country_code": "FR", "nammco_member": False},
    {"country_name": "Spain", "country_code": "ES", "nammco_member": False},
    {"country_name": "Portugal", "country_code": "PT", "nammco_member": False},
    {"country_name": "Netherlands", "country_code": "NL", "nammco_member": False},
    {"country_name": "Ireland", "country_code": "IE", "nammco_member": False},
    {"country_name": "Italy", "country_code": "IT", "nammco_member": False},
    {"country_name": "Poland", "country_code": "PL", "nammco_member": False},
    {"country_name": "Mexico", "country_code": "MX", "nammco_member": False},
    {"country_name": "Australia", "country_code": "AU", "nammco_member": False},
    {"country_name": "New Zealand", "country_code": "NZ", "nammco_member": False},
    {"country_name": "South Korea", "country_code": "KR", "nammco_member": False},
    {"country_name": "China", "country_code": "CN", "nammco_member": False},
]

def check_arctic_council_column():
    """Check if arctic_council column exists"""
    try:
        # Try to query with arctic_council column
        response = supabase.table('countries').select('arctic_council').limit(1).execute()
        print("✅ arctic_council column already exists")
        return True
    except Exception as e:
        if 'arctic_council' in str(e):
            print("❌ arctic_council column does not exist")
            return False
        else:
            print(f"❌ Error checking column: {e}")
            return False

def add_arctic_council_column():
    """Add arctic_council column using SQL"""
    try:
        # Use raw SQL to add column
        sql = "ALTER TABLE countries ADD COLUMN IF NOT EXISTS arctic_council BOOLEAN DEFAULT FALSE;"
        response = supabase.rpc('execute_sql', {'sql': sql}).execute()
        print("✅ Added arctic_council column")
        return True
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        print("ℹ️  You may need to add this column manually in Supabase dashboard:")
        print("   ALTER TABLE countries ADD COLUMN arctic_council BOOLEAN DEFAULT FALSE;")
        return False

def get_existing_countries():
    """Get existing countries from database"""
    try:
        response = supabase.table('countries').select('country_name, country_code, nammco_member').execute()
        existing = {country['country_name']: country for country in response.data}
        print(f"📊 Found {len(existing)} existing countries in database")
        return existing
    except Exception as e:
        print(f"❌ Error fetching existing countries: {e}")
        return {}

def update_arctic_council_status():
    """Update Arctic Council status for existing countries"""
    try:
        arctic_council_names = [country['country_name'] for country in ARCTIC_COUNCIL_COUNTRIES]
        
        # Set Arctic Council members to true
        for country in ARCTIC_COUNCIL_COUNTRIES:
            try:
                response = supabase.table('countries').update({
                    'arctic_council': True,
                    'country_code': country['country_code']
                }).eq('country_name', country['country_name']).execute()
                
                if response.data:
                    print(f"  ✅ Updated {country['country_name']} as Arctic Council member")
                else:
                    print(f"  ⚠️  {country['country_name']} not found, will add as new country")
            except Exception as e:
                print(f"  ❌ Error updating {country['country_name']}: {e}")
        
        # Set all other countries to false (if they exist)
        try:
            response = supabase.table('countries').update({
                'arctic_council': False
            }).not_.in_('country_name', arctic_council_names).execute()
            print(f"  ✅ Set non-Arctic Council countries to false")
        except Exception as e:
            print(f"  ❌ Error updating non-Arctic Council countries: {e}")
            
    except Exception as e:
        print(f"❌ Error updating Arctic Council status: {e}")

def add_missing_countries():
    """Add missing countries to database"""
    existing_countries = get_existing_countries()
    
    new_countries = []
    for country in ADDITIONAL_COUNTRIES:
        if country['country_name'] not in existing_countries:
            # Add arctic_council status
            is_arctic_council = country['country_name'] in [c['country_name'] for c in ARCTIC_COUNCIL_COUNTRIES]
            country_record = {
                'country_name': country['country_name'],
                'country_code': country['country_code'],
                'nammco_member': country['nammco_member'],
                'arctic_council': is_arctic_council
            }
            new_countries.append(country_record)
    
    if new_countries:
        print(f"\n➕ Adding {len(new_countries)} new countries...")
        try:
            response = supabase.table('countries').insert(new_countries).execute()
            print(f"✅ Successfully added {len(response.data)} countries")
            
            for country in new_countries:
                ac_status = "🌍 Arctic Council" if country['arctic_council'] else ""
                nammco_status = "🐋 NAMMCO" if country['nammco_member'] else ""
                status = f" [{ac_status} {nammco_status}]".strip()
                print(f"  + {country['country_name']} ({country['country_code']}){status}")
                
        except Exception as e:
            print(f"❌ Error adding countries: {e}")
    else:
        print("ℹ️  No new countries to add")

def generate_countries_report():
    """Generate a report of all countries"""
    try:
        response = supabase.table('countries').select('*').execute()
        countries = response.data
        
        arctic_council = [c for c in countries if c.get('arctic_council', False)]
        nammco_members = [c for c in countries if c.get('nammco_member', False)]
        
        print("\n" + "="*50)
        print("📊 COUNTRIES REPORT")
        print("="*50)
        
        print(f"\n🌍 Arctic Council Members ({len(arctic_council)}):")
        for country in sorted(arctic_council, key=lambda x: x['country_name']):
            nammco = " + NAMMCO" if country.get('nammco_member') else ""
            print(f"  • {country['country_name']} ({country.get('country_code', 'N/A')}){nammco}")
        
        print(f"\n🐋 NAMMCO Members ({len(nammco_members)}):")
        for country in sorted(nammco_members, key=lambda x: x['country_name']):
            arctic = " + Arctic Council" if country.get('arctic_council') else ""
            print(f"  • {country['country_name']} ({country.get('country_code', 'N/A')}){arctic}")
        
        print(f"\n📈 Total Countries: {len(countries)}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")

def main():
    """Main function"""
    print("🌍 Arctic Tracker - Add Arctic Council Column")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if column exists
    column_exists = check_arctic_council_column()
    
    if not column_exists:
        print("\n🔧 Adding arctic_council column...")
        if not add_arctic_council_column():
            print("❌ Failed to add column. Please add manually and run script again.")
            return
    
    # Update Arctic Council status
    print("\n🔄 Updating Arctic Council status...")
    update_arctic_council_status()
    
    # Add missing countries
    print("\n➕ Adding missing countries...")
    add_missing_countries()
    
    # Generate report
    generate_countries_report()
    
    print(f"\n📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
Arctic Tracker - Add Arctic Council Column

Usage:
  python migration/add_arctic_council_column.py

This script will:
1. Add arctic_council column to countries table (if not exists)
2. Update Arctic Council member status for existing countries
3. Add missing countries with proper Arctic Council status
4. Generate a report of all countries

Arctic Council Members (8):
• Canada, Denmark, Finland, Iceland, Norway, Russia, Sweden, United States

Note: If the script cannot add the column automatically, you can add it manually:
ALTER TABLE countries ADD COLUMN arctic_council BOOLEAN DEFAULT FALSE;
        """)
    else:
        main()
