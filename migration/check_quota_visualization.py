#!/usr/bin/env python3
"""
Further investigation of quota data for visualization issues
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
    
    # Create client
    supabase: Client = create_client(supabase_url, supabase_key)
    print("✅ Connected to Supabase")
    
    # 1. Check recent data for Balaenoptera acutorostrata with quota
    print("\n" + "="*60)
    print("1. DETAILED QUOTA DATA FOR BALAENOPTERA ACUTOROSTRATA")
    print("="*60)
    
    # Get species ID
    species_response = supabase.table('species').select('id, scientific_name').eq('scientific_name', 'Balaenoptera acutorostrata').execute()
    species_id = species_response.data[0]['id']
    
    # Get catch records with quota data, ordered by year descending
    catch_response = supabase.table('catch_records').select('*').eq('species_id', species_id).not_.is_('quota_amount', 'null').order('year', desc=True).limit(10).execute()
    
    print(f"Recent 10 records with quota data:")
    df = pd.DataFrame(catch_response.data)
    
    for i, record in enumerate(df.to_dict('records')):
        print(f"\nRecord {i+1}:")
        print(f"  Year: {record['year']}")
        print(f"  Catch Total: {record['catch_total']}")
        print(f"  Quota Amount: {record['quota_amount']}")
        print(f"  Country ID: {record['country_id']}")
        print(f"  Management Area ID: {record['management_area_id']}")
        print(f"  Source: {record['data_source']}")
    
    # 2. Check country information
    print("\n" + "="*60)
    print("2. CHECKING COUNTRY INFORMATION")
    print("="*60)
    
    # Get unique country IDs from catch records
    country_ids = df['country_id'].unique()
    print(f"Unique country IDs in catch records: {len(country_ids)}")
    
    for country_id in country_ids:
        country_response = supabase.table('countries').select('*').eq('id', country_id).execute()
        if country_response.data:
            country = country_response.data[0]
            record_count = len(df[df['country_id'] == country_id])
            print(f"  - {country['country_name']} ({country['country_code']}): {record_count} records")
    
    # 3. Check if there are any views or aggregated tables
    print("\n" + "="*60)
    print("3. CHECKING FOR POTENTIAL VISUALIZATION QUERIES")
    print("="*60)
    
    # Check what years have data
    years_with_data = sorted(df['year'].unique(), reverse=True)
    print(f"Years with quota data: {years_with_data}")
    
    # Group by year to see quota vs catch trends
    yearly_summary = df.groupby('year').agg({
        'catch_total': 'sum',
        'quota_amount': 'sum',
        'id': 'count'
    }).rename(columns={'id': 'record_count'})
    
    print("\nYearly summary (Total Catch vs Total Quota):")
    print(yearly_summary.to_string())
    
    # 4. Check if quota field vs quota_amount field issue
    print("\n" + "="*60)
    print("4. CHECKING QUOTA FIELD DIFFERENCES")
    print("="*60)
    
    # Check all catch records to see the difference between quota and quota_amount
    all_catch_response = supabase.table('catch_records').select('quota, quota_amount').eq('species_id', species_id).execute()
    all_df = pd.DataFrame(all_catch_response.data)
    
    print(f"Total records for Balaenoptera acutorostrata: {len(all_df)}")
    print(f"Records with 'quota' field (not null): {all_df['quota'].notna().sum()}")
    print(f"Records with 'quota_amount' field (not null): {all_df['quota_amount'].notna().sum()}")
    
    if all_df['quota'].notna().sum() > 0:
        print(f"Sample 'quota' values: {all_df['quota'].dropna().head(5).tolist()}")
    
    if all_df['quota_amount'].notna().sum() > 0:
        print(f"Sample 'quota_amount' values: {all_df['quota_amount'].dropna().head(5).tolist()}")
    
    # 5. Check if there are any database views that might be used for visualization
    print("\n" + "="*60)
    print("5. TESTING POTENTIAL VISUALIZATION QUERIES")
    print("="*60)
    
    # Test a query that might be used for visualization - recent data with quota
    viz_query = supabase.table('catch_records').select('''
        year,
        catch_total,
        quota_amount,
        countries(country_name, country_code)
    ''').eq('species_id', species_id).gte('year', 2020).not_.is_('quota_amount', 'null').order('year', desc=True).execute()
    
    if viz_query.data:
        print(f"✅ Visualization query successful - {len(viz_query.data)} records found")
        print("Sample records for visualization:")
        for record in viz_query.data[:3]:
            print(f"  {record['year']}: Catch={record['catch_total']}, Quota={record['quota_amount']}, Country={record['countries']['country_name'] if record['countries'] else 'Unknown'}")
    else:
        print("❌ Visualization query returned no data")
    
    # 6. Check management areas if they exist
    print("\n" + "="*60)
    print("6. CHECKING MANAGEMENT AREAS")
    print("="*60)
    
    # Check unique management area IDs
    mgmt_areas = df['management_area_id'].dropna().unique()
    print(f"Management areas with data: {mgmt_areas}")
    
    if len(mgmt_areas) > 0:
        # Try to get management area details
        try:
            mgmt_response = supabase.table('management_areas').select('*').execute()
            if mgmt_response.data:
                print(f"Management areas table has {len(mgmt_response.data)} entries")
                for area in mgmt_response.data[:5]:
                    print(f"  - ID: {area['id']}, Name: {area.get('area_name', 'No name')}")
        except Exception as e:
            print(f"Could not query management_areas table: {e}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()