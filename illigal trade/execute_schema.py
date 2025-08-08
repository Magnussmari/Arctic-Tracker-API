#!/usr/bin/env python3
"""
Execute Illegal Trade Schema Creation
Arctic Tracker Database - Direct SQL Execution

Executes the illegal trade schema using direct PostgreSQL connection.
"""

import sys
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / 'config' / '.env'
load_dotenv(env_path)

def get_postgres_connection():
    """Get direct PostgreSQL connection"""
    # Construct connection string from Supabase URL
    supabase_url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not supabase_url:
        raise ValueError("SUPABASE_URL not found")
    
    # Extract components from Supabase URL
    # Format: https://project.supabase.co
    project_id = supabase_url.replace('https://', '').replace('.supabase.co', '')
    
    # PostgreSQL connection details for Supabase
    conn_params = {
        'host': f'db.{project_id}.supabase.co',
        'port': 5432,
        'database': 'postgres',
        'user': 'postgres',
        'password': os.getenv('SUPABASE_DB_PASSWORD')  # Different from service key
    }
    
    if not conn_params['password']:
        # Try alternative password env vars
        conn_params['password'] = os.getenv('DB_PASSWORD')
        if not conn_params['password']:
            raise ValueError("Database password not found. Set SUPABASE_DB_PASSWORD or DB_PASSWORD")
    
    return psycopg2.connect(**conn_params)

def execute_schema():
    """Execute the schema creation"""
    print("Executing illegal trade schema creation...")
    
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        
        # Read schema file
        with open('create_illegal_trade_schema.sql', 'r') as f:
            schema_sql = f.read()
        
        # Execute the entire schema
        cursor.execute(schema_sql)
        conn.commit()
        
        print("✓ Schema created successfully")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE 'illegal_trade_%'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        print(f"Created tables: {[t[0] for t in tables]}")
        
        # Verify materialized view
        cursor.execute("""
            SELECT schemaname, matviewname FROM pg_matviews 
            WHERE matviewname = 'species_illegal_trade_summary'
        """)
        
        views = cursor.fetchall()
        if views:
            print("✓ Materialized view created")
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"PostgreSQL error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = execute_schema()
    sys.exit(0 if success else 1)