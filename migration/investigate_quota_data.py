#!/usr/bin/env python3
"""
Investigate quota data in catch_records table for NAMMCO species
"""

import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
    import os
    
    # Load environment variables
    env_path = Path(__file__).parent.parent / 'config' / '.env'
    load_dotenv(env_path)
    
    # Get credentials
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Missing Supabase credentials")
        sys.exit(1)
    
    # Create client
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Connected to Supabase")
    
    # 1. Check the structure of catch_records table
    print("\n" + "="*50)
    print("1. CHECKING CATCH_RECORDS TABLE STRUCTURE")
    print("="*50)
    
    # Get a sample record to see the structure
    sample_response = supabase.table('catch_records').select('*').limit(1).execute()
    if sample_response.data:
        print("Sample record structure:")
        for key, value in sample_response.data[0].items():
            print(f"  {key}: {value} ({type(value).__name__})")
    
    # 2. Check for Balaenoptera acutorostrata specifically
    print("\n" + "="*50)
    print("2. CHECKING BALAENOPTERA ACUTOROSTRATA DATA")
    print("="*50)
    
    # First, get the species ID
    species_response = supabase.table('species').select('id, scientific_name').eq('scientific_name', 'Balaenoptera acutorostrata').execute()
    
    if not species_response.data:
        print("❌ Balaenoptera acutorostrata not found in species table")
    else:
        species_id = species_response.data[0]['id']
        print(f"✅ Found Balaenoptera acutorostrata with ID: {species_id}")
        
        # Get catch records for this species
        catch_response = supabase.table('catch_records').select('*').eq('species_id', species_id).execute()
        
        if not catch_response.data:
            print("❌ No catch records found for Balaenoptera acutorostrata")
        else:
            print(f"✅ Found {len(catch_response.data)} catch records")
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame(catch_response.data)
            
            print("\nData overview:")
            print(f"  - Total records: {len(df)}")
            print(f"  - Columns: {list(df.columns)}")
            
            # Check for quota-related columns
            quota_columns = [col for col in df.columns if 'quota' in col.lower()]
            print(f"  - Quota-related columns: {quota_columns}")
            
            # Check for any records with quota data
            if quota_columns:
                for col in quota_columns:
                    non_null_count = df[col].notna().sum()
                    print(f"    {col}: {non_null_count} non-null values")
                    if non_null_count > 0:
                        print(f"      Sample values: {df[col].dropna().head(3).tolist()}")
            
            # Show sample records
            print("\nSample records (first 3):")
            for i, record in enumerate(df.head(3).to_dict('records')):
                print(f"  Record {i+1}:")
                for key, value in record.items():
                    if value is not None:
                        print(f"    {key}: {value}")
                print()
    
    # 3. Check for any records with quota data across all species
    print("\n" + "="*50)
    print("3. CHECKING ALL RECORDS WITH QUOTA DATA")
    print("="*50)
    
    # Check if there are any records with quota_amount data
    quota_response = supabase.table('catch_records').select('*').not_.is_('quota_amount', 'null').execute()
    
    if not quota_response.data:
        print("❌ No records found with quota_amount data")
    else:
        print(f"✅ Found {len(quota_response.data)} records with quota_amount data")
        df_quota = pd.DataFrame(quota_response.data)
        
        print("\nQuota data summary:")
        print(f"  - Records with quota data: {len(df_quota)}")
        if 'quota_amount' in df_quota.columns:
            print(f"  - Quota amount range: {df_quota['quota_amount'].min()} - {df_quota['quota_amount'].max()}")
            print(f"  - Average quota: {df_quota['quota_amount'].mean():.2f}")
        
        # Show species with quota data
        if 'species_id' in df_quota.columns:
            species_with_quota = df_quota['species_id'].unique()
            print(f"  - Species with quota data: {len(species_with_quota)}")
            
            # Get species names
            for species_id in species_with_quota[:5]:  # Show first 5
                species_resp = supabase.table('species').select('scientific_name').eq('id', species_id).execute()
                if species_resp.data:
                    species_name = species_resp.data[0]['scientific_name']
                    quota_count = len(df_quota[df_quota['species_id'] == species_id])
                    print(f"    - {species_name}: {quota_count} quota records")
    
    # 4. Check the overall structure of what was imported
    print("\n" + "="*50)
    print("4. OVERALL CATCH_RECORDS SUMMARY")
    print("="*50)
    
    total_response = supabase.table('catch_records').select('id').execute()
    print(f"Total catch records in database: {len(total_response.data)}")
    
    # Get column information
    sample_response = supabase.table('catch_records').select('*').limit(5).execute()
    if sample_response.data:
        df_sample = pd.DataFrame(sample_response.data)
        print(f"\nAvailable columns in catch_records:")
        for col in df_sample.columns:
            non_null = df_sample[col].notna().sum()
            print(f"  - {col}: {non_null}/{len(df_sample)} non-null values")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()