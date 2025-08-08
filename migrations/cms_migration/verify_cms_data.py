#!/usr/bin/env python3
"""
Verify CMS Data Script

This script verifies the CMS data loaded into the database and generates a report.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.supabase_config import get_supabase_client


def verify_cms_data():
    """Verify CMS data in the database"""
    client = get_supabase_client()
    
    print("CMS Data Verification Report")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Count total CMS listings
    response = client.table('cms_listings').select('id', count='exact').execute()
    total_count = response.count
    print(f"\nTotal CMS listings in database: {total_count}")
    
    # 2. Count by appendix
    print("\nSpecies by CMS Appendix:")
    print("-" * 40)
    
    for appendix in ['I', 'II', 'I/II']:
        response = client.table('cms_listings').select('id', count='exact').eq('appendix', appendix).execute()
        count = response.count
        print(f"Appendix {appendix}: {count} species")
    
    # 3. Get species with both CITES and CMS listings
    print("\nSpecies with both CITES and CMS listings:")
    print("-" * 40)
    
    response = client.table('species').select(
        'scientific_name, common_name, '
        'cites_listings!inner(appendix), '
        'cms_listings!inner(appendix)'
    ).execute()
    
    if response.data:
        print(f"Found {len(response.data)} species with both listings")
        for species in response.data[:5]:  # Show first 5
            cites = species['cites_listings'][0]['appendix'] if species['cites_listings'] else 'None'
            cms = species['cms_listings'][0]['appendix'] if species['cms_listings'] else 'None'
            print(f"- {species['scientific_name']} ({species['common_name']})")
            print(f"  CITES: {cites}, CMS: {cms}")
    
    # 4. Species with widest distribution
    print("\nSpecies with widest distribution (top 5):")
    print("-" * 40)
    
    response = client.table('species_cms_listings').select(
        'scientific_name, common_name, native_country_count'
    ).not_.is_('native_country_count', None).order('native_country_count', desc=True).limit(5).execute()
    
    if response.data:
        for species in response.data:
            print(f"- {species['scientific_name']}: {species['native_country_count']} countries")
    
    # 5. Arctic endemic species in CMS
    print("\nArctic endemic species in CMS:")
    print("-" * 40)
    
    arctic_species = ['Ursus maritimus', 'Monodon monoceros', 'Delphinapterus leucas', 
                      'Balaena mysticetus', 'Odobenus rosmarus']
    
    for species_name in arctic_species:
        response = client.table('cms_listings').select(
            'appendix, species!inner(scientific_name)'
        ).eq('species.scientific_name', species_name).execute()
        
        if response.data:
            print(f"- {species_name}: CMS Appendix {response.data[0]['appendix']}")
        else:
            print(f"- {species_name}: Not in CMS")
    
    print("\n" + "=" * 60)
    print("Verification complete!")


if __name__ == "__main__":
    verify_cms_data()