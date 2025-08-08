#!/usr/bin/env python3
"""
Final investigation of quota data for visualization issues - fixed version
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
    
    # Get species ID for Balaenoptera acutorostrata
    species_response = supabase.table('species').select('id, scientific_name').eq('scientific_name', 'Balaenoptera acutorostrata').execute()
    species_id = species_response.data[0]['id']
    print(f"✅ Species ID: {species_id}")
    
    # 1. Check the data structure and issues
    print("\n" + "="*60)
    print("1. QUOTA DATA STRUCTURE ANALYSIS")
    print("="*60)
    
    # Get all catch records for this species
    catch_response = supabase.table('catch_records').select('*').eq('species_id', species_id).execute()
    df = pd.DataFrame(catch_response.data)
    
    print(f"Total records: {len(df)}")
    print(f"Records with quota_amount: {df['quota_amount'].notna().sum()}")
    print(f"Records with quota (old field): {df['quota'].notna().sum()}")
    
    # Check country_id issues
    print(f"\nCountry ID analysis:")
    print(f"  Records with valid country_id: {df['country_id'].notna().sum()}")
    print(f"  Records with null country_id: {df['country_id'].isna().sum()}")
    
    # Get unique valid country IDs
    valid_country_ids = df[df['country_id'].notna()]['country_id'].unique()
    print(f"  Valid country IDs: {len(valid_country_ids)}")
    
    # Get country names for valid IDs
    for country_id in valid_country_ids:
        try:
            country_response = supabase.table('countries').select('*').eq('id', country_id).execute()
            if country_response.data:
                country = country_response.data[0]
                record_count = len(df[df['country_id'] == country_id])
                print(f"    - {country['country_name']} ({country['country_code']}): {record_count} records")
        except Exception as e:
            print(f"    - Error getting country {country_id}: {e}")
    
    # 2. Check quota data by year
    print("\n" + "="*60)
    print("2. QUOTA DATA BY YEAR")
    print("="*60)
    
    # Filter only records with quota data
    quota_df = df[df['quota_amount'].notna()].copy()
    print(f"Records with quota data: {len(quota_df)}")
    
    # Group by year
    yearly_data = quota_df.groupby('year').agg({
        'catch_total': ['sum', 'count'],
        'quota_amount': ['sum', 'count', 'mean']
    }).round(2)
    
    print("\nYearly quota summary:")
    print(yearly_data.to_string())
    
    # 3. Check the most recent data structure for visualization
    print("\n" + "="*60)
    print("3. RECENT DATA FOR VISUALIZATION")
    print("="*60)
    
    # Get recent records with all needed fields
    recent_data = quota_df[quota_df['year'] >= 2020].copy()
    print(f"Recent records (2020+): {len(recent_data)}")
    
    # Check if the visualization might be looking for specific field names
    print("\nField mapping analysis:")
    print(f"  - 'quota' field (old): {recent_data['quota'].notna().sum()} values")
    print(f"  - 'quota_amount' field (new): {recent_data['quota_amount'].notna().sum()} values")
    print(f"  - 'catch_total' field: {recent_data['catch_total'].notna().sum()} values")
    
    # Sample of recent data
    print(f"\nSample recent records:")
    sample_recent = recent_data.tail(3)[['year', 'catch_total', 'quota_amount', 'country_id', 'data_source']]
    print(sample_recent.to_string(index=False))
    
    # 4. Test a typical visualization query
    print("\n" + "="*60)
    print("4. TESTING VISUALIZATION QUERIES")
    print("="*60)
    
    # Query that a typical visualization might use
    try:
        viz_test = supabase.table('catch_records').select('''
            year,
            catch_total,
            quota_amount
        ''').eq('species_id', species_id).gte('year', 2020).not_.is_('quota_amount', 'null').order('year').execute()
        
        if viz_test.data:
            print(f"✅ Basic visualization query works: {len(viz_test.data)} records")
            
            # Convert to DataFrame for analysis
            viz_df = pd.DataFrame(viz_test.data)
            
            # Check for any obvious issues
            print(f"  Years covered: {sorted(viz_df['year'].unique())}")
            print(f"  Catch total range: {viz_df['catch_total'].min()} - {viz_df['catch_total'].max()}")
            print(f"  Quota range: {viz_df['quota_amount'].min()} - {viz_df['quota_amount'].max()}")
            
            # Check for zero or negative values that might cause visualization issues
            zero_catch = len(viz_df[viz_df['catch_total'] == 0])
            zero_quota = len(viz_df[viz_df['quota_amount'] == 0])
            print(f"  Records with zero catch: {zero_catch}")
            print(f"  Records with zero quota: {zero_quota}")
            
        else:
            print("❌ Visualization query returned no data")
            
    except Exception as e:
        print(f"❌ Visualization query failed: {e}")
    
    # 5. Check if there might be a view or different table being used
    print("\n" + "="*60)
    print("5. CHECKING FOR POTENTIAL VISUALIZATION ISSUES")
    print("="*60)
    
    # Check if quota data exists but might be in wrong format
    print("Potential issues analysis:")
    
    # Check data types
    print(f"  - quota_amount data type: {quota_df['quota_amount'].dtype}")
    print(f"  - catch_total data type: {quota_df['catch_total'].dtype}")
    
    # Check for any unusual values
    print(f"  - Any negative quota values: {(quota_df['quota_amount'] < 0).sum()}")
    print(f"  - Any negative catch values: {(quota_df['catch_total'] < 0).sum()}")
    
    # Check recent years specifically
    recent_years = [2021, 2022, 2023]
    for year in recent_years:
        year_data = quota_df[quota_df['year'] == year]
        if len(year_data) > 0:
            total_catch = year_data['catch_total'].sum()
            total_quota = year_data['quota_amount'].sum()
            print(f"  - {year}: {len(year_data)} records, Total Catch: {total_catch}, Total Quota: {total_quota}")
        else:
            print(f"  - {year}: No data")
    
    # 6. Summary and recommendations
    print("\n" + "="*60)
    print("6. SUMMARY AND DIAGNOSIS")
    print("="*60)
    
    print("FINDINGS:")
    print(f"✅ Quota data IS present in the database")
    print(f"✅ {df['quota_amount'].notna().sum()} out of {len(df)} records have quota_amount values")
    print(f"✅ Data covers years: {sorted(df['year'].unique())}")
    print(f"✅ Quota amounts range from {df['quota_amount'].min()} to {df['quota_amount'].max()}")
    
    print(f"\nPOTENTIAL ISSUES:")
    if df['quota'].notna().sum() == 0 and df['quota_amount'].notna().sum() > 0:
        print(f"⚠️  Data is in 'quota_amount' field, not 'quota' field")
        print(f"    The visualization might be looking for 'quota' field instead of 'quota_amount'")
    
    if df['country_id'].isna().sum() > 0:
        print(f"⚠️  {df['country_id'].isna().sum()} records have NULL country_id")
        print(f"    This might affect country-based filtering in visualization")
    
    print(f"\nRECOMMENDATIONS:")
    print(f"1. Check if visualization code is looking for 'quota' field instead of 'quota_amount'")
    print(f"2. Verify country filtering isn't excluding records with NULL country_id")
    print(f"3. Ensure date range filtering includes the available years: {sorted(df['year'].unique())}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()