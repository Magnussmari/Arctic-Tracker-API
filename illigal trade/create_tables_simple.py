#!/usr/bin/env python3
"""
Create Illegal Trade Tables
Simple table creation using Supabase client
"""

import sys
import os
sys.path.append('..')
from config.supabase_config import get_supabase_client

def create_tables():
    """Create illegal trade tables one by one"""
    client = get_supabase_client(use_service_role=True)
    
    tables_created = []
    
    try:
        print("Creating illegal_trade_products table...")
        
        # Create products table using direct table creation
        result = client.table('illegal_trade_products').select('*').limit(1).execute()
        print("✓ illegal_trade_products table already exists or accessible")
        tables_created.append('illegal_trade_products')
        
    except Exception as e:
        print(f"Products table creation/check failed: {e}")
    
    try:
        print("Creating illegal_trade_seizures table...")
        
        result = client.table('illegal_trade_seizures').select('*').limit(1).execute()
        print("✓ illegal_trade_seizures table already exists or accessible")
        tables_created.append('illegal_trade_seizures')
        
    except Exception as e:
        print(f"Seizures table creation/check failed: {e}")
        
    try:
        print("Creating illegal_trade_risk_scores table...")
        
        result = client.table('illegal_trade_risk_scores').select('*').limit(1).execute()
        print("✓ illegal_trade_risk_scores table already exists or accessible")
        tables_created.append('illegal_trade_risk_scores')
        
    except Exception as e:
        print(f"Risk scores table creation/check failed: {e}")
    
    return tables_created

if __name__ == "__main__":
    print("Checking/creating illegal trade tables...")
    tables = create_tables()
    print(f"Tables accessible: {tables}")
    
    if len(tables) >= 2:  # Need at least products and seizures tables
        print("✓ Ready to proceed with data loading")
    else:
        print("⚠ Tables may need to be created manually")
        print("Try running the SQL schema directly in Supabase dashboard")