#!/usr/bin/env python3
"""
Minimal test of Supabase connection without proxy issues
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    print("🔧 Testing direct Supabase import...")
    
    from supabase import create_client, Client
    from dotenv import load_dotenv
    import os
    
    print("✅ Supabase import successful")
    
    # Load environment variables
    env_path = Path(__file__).parent.parent / 'config' / '.env'
    load_dotenv(env_path)
    
    print("✅ Environment loaded")
    
    # Get credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        sys.exit(1)
    
    print(f"✅ Got credentials: URL={supabase_url[:30]}...")
    
    # Create client
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Supabase client created successfully")
    
    # Test connection
    response = supabase.table('species').select('id, scientific_name').execute()
    
    if response.data:
        print(f"✅ Database connection successful - found {len(response.data)} species")
        for species in response.data[:3]:
            print(f"    - {species['scientific_name']}")
    else:
        print("❌ No data returned")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
