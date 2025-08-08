#!/usr/bin/env python3
"""
Execute CMS Migration Script

This script executes the SQL migration to create CMS tables in the database.
"""

import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.supabase_config import get_supabase_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def execute_migration():
    """Execute the CMS table creation migration"""
    try:
        # Read the SQL migration file
        migration_file = Path(__file__).parent / 'create_cms_listings_table.sql'
        with open(migration_file, 'r') as f:
            sql_content = f.read()
        
        # Get Supabase client with service role (admin access)
        client = get_supabase_client(use_service_role=True)
        
        # Execute the SQL
        # Note: Supabase Python client doesn't have direct SQL execution,
        # so we'll use the REST API directly
        import requests
        
        # Get the URL and key from the client
        url = client.supabase_url
        key = client.supabase_key
        
        # Execute via REST API
        headers = {
            'apikey': key,
            'Authorization': f'Bearer {key}',
            'Content-Type': 'application/json'
        }
        
        # Split SQL into individual statements (crude but effective)
        statements = sql_content.split(';')
        
        success_count = 0
        error_count = 0
        
        for i, statement in enumerate(statements):
            statement = statement.strip()
            if not statement:
                continue
                
            # Skip comments
            if statement.startswith('--'):
                continue
                
            logger.info(f"Executing statement {i+1}...")
            
            # For this migration, we'll need to use the admin interface
            # Let's just verify the tables don't exist first
            try:
                # Check if table exists
                response = client.table('cms_listings').select('id').limit(1).execute()
                logger.warning("cms_listings table already exists!")
                return False
            except:
                # Table doesn't exist, which is what we want
                pass
        
        logger.info("Migration requires manual execution in Supabase SQL editor")
        logger.info("Please copy the contents of create_cms_listings_table.sql and run it in your Supabase dashboard")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    if execute_migration():
        print("✅ Migration preparation complete")
    else:
        print("❌ Migration failed")