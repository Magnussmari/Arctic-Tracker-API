#!/usr/bin/env python3
"""
Test IUCN API v4 Integration

This script tests the updated IUCN API v4 integration with a few sample species
to verify that the authentication and endpoints are working correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add rebuild directory to path for imports
rebuild_dir = Path(__file__).parent.parent
sys.path.insert(0, str(rebuild_dir))

from core.iucn_client import IUCNApiClient

async def test_iucn_v4_api():
    """Test IUCN API v4 endpoints"""
    
    # Test species - Arctic examples
    test_species = [
        "Ursus maritimus",      # Polar bear
        "Rangifer tarandus",    # Caribou/Reindeer  
        "Vulpes lagopus",       # Arctic fox
        "Odobenus rosmarus",    # Walrus
        "Lepus arcticus"        # Arctic hare
    ]
    
    print("Testing IUCN Red List API v4 Integration")
    print("=" * 50)
    
    async with IUCNApiClient() as client:
        # Test API version
        try:
            print("1. Testing API version endpoint...")
            version_info = await client.get_api_version()
            print(f"   ✓ API Version: {version_info}")
        except Exception as e:
            print(f"   ✗ API Version failed: {e}")
        
        print(f"\n2. Testing species lookup for {len(test_species)} Arctic species...")
        
        for i, species_name in enumerate(test_species, 1):
            print(f"\n   {i}. Testing: {species_name}")
            
            try:
                # Test species by name (v4 endpoint)
                species_data = await client.get_species_by_name(species_name)
                
                if species_data and 'result' in species_data and species_data['result']:
                    for taxon in species_data['result']:
                        scientific_name = taxon.get('scientific_name', 'Unknown')
                        common_name = taxon.get('main_common_name', 'No common name')
                        category = taxon.get('category', 'Unknown')
                        assessment_id = taxon.get('assessment_id')
                        
                        print(f"      ✓ Found: {scientific_name}")
                        print(f"        Common name: {common_name}")
                        print(f"        Status: {category}")
                        
                        # Test assessment details if available
                        if assessment_id:
                            try:
                                assessment_details = await client.get_assessment_details(assessment_id)
                                if assessment_details and 'result' in assessment_details:
                                    print(f"        Assessment ID: {assessment_id} ✓")
                                else:
                                    print(f"        Assessment ID: {assessment_id} (no details)")
                            except Exception as e:
                                print(f"        Assessment details failed: {e}")
                else:
                    print(f"      ℹ No data found in IUCN Red List")
                    
            except Exception as e:
                print(f"      ✗ Error: {e}")
    
    print("\n" + "=" * 50)
    print("IUCN API v4 test completed!")

if __name__ == "__main__":
    asyncio.run(test_iucn_v4_api())
