#!/usr/bin/env python3
"""
Debug IUCN API v4 Endpoints

This script helps debug the IUCN API v4 integration by testing different
endpoints and authentication methods.
"""

import asyncio
import aiohttp
import sys
from pathlib import Path

# Add rebuild directory to path for imports
rebuild_dir = Path(__file__).parent.parent
sys.path.insert(0, str(rebuild_dir))

from config import get_api_config, get_cached_settings

async def debug_iucn_api():
    """Debug IUCN API endpoints and authentication"""
    
    print("IUCN API v4 Debug Script")
    print("=" * 40)
    
    settings = get_cached_settings()
    api_config = get_api_config()
    
    print(f"IUCN Token: {settings.api.iucn_api_token[:10]}..." if settings.api.iucn_api_token else "No token found")
    
    # Test different endpoint combinations
    test_endpoints = [
        # v4 endpoints with correct base URL
        ('v4', 'https://api.iucnredlist.org/api/v4/version'),
        ('v4', 'https://api.iucnredlist.org/api/v4/taxa/scientific_name/Ursus%20maritimus'),
        ('v4', 'https://api.iucnredlist.org/api/v4/species/Ursus%20maritimus'),
        
        # Test some assessment endpoints
        ('v4', 'https://api.iucnredlist.org/api/v4/assessment/103968'),  # Known assessment ID
    ]
    
    async with aiohttp.ClientSession() as session:
        for version, base_url in test_endpoints:
            print(f"\n{version.upper()} Testing: {base_url}")
            
            # Test without token
            try:
                async with session.get(base_url) as response:
                    print(f"   Without token: Status {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
                    else:
                        text = await response.text()
                        print(f"   Error: {text[:100]}...")
            except Exception as e:
                print(f"   Without token error: {e}")
            
            # Test with token as parameter
            if settings.api.iucn_api_token:
                token_url = f"{base_url}{'&' if '?' in base_url else '?'}token={settings.api.iucn_api_token}"
                try:
                    async with session.get(token_url) as response:
                        print(f"   With token param: Status {response.status}")
                        if response.status == 200:
                            data = await response.json()
                            print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
                            if 'result' in data and data['result']:
                                print(f"   Result count: {len(data['result'])}")
                                if isinstance(data['result'], list) and data['result']:
                                    first_result = data['result'][0]
                                    if isinstance(first_result, dict):
                                        print(f"   First result keys: {list(first_result.keys())}")
                        else:
                            text = await response.text()
                            print(f"   Error: {text[:100]}...")
                except Exception as e:
                    print(f"   With token param error: {e}")
            
            # Test with token in headers (v4 might use header auth)
            if settings.api.iucn_api_token:
                headers = {'Authorization': f'Bearer {settings.api.iucn_api_token}'}
                try:
                    async with session.get(base_url, headers=headers) as response:
                        print(f"   With token header: Status {response.status}")
                        if response.status == 200:
                            data = await response.json()
                            print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
                            if 'result' in data and data['result']:
                                print(f"   Result count: {len(data['result'])}")
                                if isinstance(data['result'], list) and data['result']:
                                    first_result = data['result'][0]
                                    if isinstance(first_result, dict):
                                        print(f"   First result keys: {list(first_result.keys())}")
                        else:
                            text = await response.text()
                            print(f"   Error: {text[:100]}...")
                except Exception as e:
                    print(f"   With token header error: {e}")
            
            # Test with token as X-API-Key header
            if settings.api.iucn_api_token:
                headers = {'X-API-Key': settings.api.iucn_api_token}
                try:
                    async with session.get(base_url, headers=headers) as response:
                        print(f"   With X-API-Key header: Status {response.status}")
                        if response.status == 200:
                            data = await response.json()
                            print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
                            if 'result' in data and data['result']:
                                print(f"   Result count: {len(data['result'])}")
                                if isinstance(data['result'], list) and data['result']:
                                    first_result = data['result'][0]
                                    if isinstance(first_result, dict):
                                        print(f"   First result keys: {list(first_result.keys())}")
                        else:
                            text = await response.text()
                            print(f"   Error: {text[:100]}...")
                except Exception as e:
                    print(f"   With X-API-Key header error: {e}")
    
    print("\n" + "=" * 40)
    print("Debug completed!")

if __name__ == "__main__":
    asyncio.run(debug_iucn_api())
