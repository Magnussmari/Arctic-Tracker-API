#!/usr/bin/env python3
"""
Test script for the rebuild configuration and IUCN API client

This script tests the configuration loading and IUCN API connectivity.
"""

import sys
import asyncio
from pathlib import Path

# Add rebuild directory to path
rebuild_dir = Path(__file__).parent.parent
sys.path.insert(0, str(rebuild_dir))

async def test_configuration():
    """Test configuration loading"""
    print("🔧 Testing Configuration Loading...")
    
    try:
        from config import get_settings, get_api_config, get_db
        
        # Test settings
        settings = get_settings()
        print(f"✅ Settings loaded successfully")
        print(f"   Supabase URL: {settings.database.supabase_url[:50]}...")
        print(f"   IUCN API Token: {'***' + settings.api.iucn_api_token[-4:] if settings.api.iucn_api_token else 'Not set'}")
        
        # Test API config
        api_config = get_api_config()
        iucn_config = api_config.get_endpoint_config('iucn')
        print(f"✅ API config loaded successfully")
        print(f"   IUCN Base URL: {iucn_config.base_url}")
        print(f"   Rate limit: {iucn_config.rate_limit} req/sec")
        
        # Test URL building
        test_url = api_config.build_api_url('iucn', 'version')
        print(f"✅ URL building works: {test_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def test_iucn_api():
    """Test IUCN API connectivity"""
    print(f"\n🌍 Testing IUCN API Connectivity...")
    
    try:
        from core.iucn_client import IUCNApiClient
        
        async with IUCNApiClient() as client:
            # Test version endpoint
            version_info = await client.get_api_version()
            print(f"✅ IUCN API connection successful")
            print(f"   API Version: {version_info.get('version', 'Unknown')}")
            
            # Test species search
            print(f"\n🐻 Testing species lookup: Ursus maritimus")
            assessments = await client.get_species_assessments('Ursus', 'maritimus')
            
            if assessments and 'result' in assessments and assessments['result']:
                assessment = assessments['result'][0]
                print(f"✅ Found assessment for Polar Bear")
                print(f"   Status: {assessment.get('category', 'Unknown')}")
                print(f"   Scientific name: {assessment.get('scientific_name', 'Unknown')}")
                print(f"   Common name: {assessment.get('main_common_name', 'Unknown')}")
            else:
                print(f"⚠️  No assessment found for Ursus maritimus")
            
        return True
        
    except Exception as e:
        print(f"❌ IUCN API test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Arctic Species Rebuild Configuration & API Test")
    print("=" * 55)
    
    # Test configuration
    config_ok = await test_configuration()
    
    if config_ok:
        # Test IUCN API
        api_ok = await test_iucn_api()
        
        print(f"\n📋 TEST RESULTS")
        print("=" * 20)
        print(f"Configuration: {'✅ PASS' if config_ok else '❌ FAIL'}")
        print(f"IUCN API:      {'✅ PASS' if api_ok else '❌ FAIL'}")
        
        if config_ok and api_ok:
            print(f"\n🎉 All tests passed! The rebuild system is ready to use.")
        else:
            print(f"\n⚠️  Some tests failed. Check configuration and API credentials.")
    else:
        print(f"\n❌ Configuration failed. Cannot proceed with API tests.")

if __name__ == "__main__":
    asyncio.run(main())