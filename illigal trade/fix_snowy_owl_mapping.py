#!/usr/bin/env python3
"""
Fix Snowy Owl Mapping in Illegal Trade Data
Arctic Tracker - Data Fix

The Snowy Owl has a taxonomic name mismatch:
- Database: Nyctea scandiaca
- Illegal trade data: Bubo scandiacus

This script loads the missing 38 Snowy Owl records.

Usage:
    python fix_snowy_owl_mapping.py [--dry-run]
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.supabase_config import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/snowy_owl_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def fix_snowy_owl_records(dry_run=False):
    """Load the missing Snowy Owl records"""
    
    client = get_supabase_client()
    
    logger.info("🦉 Fixing Snowy Owl mapping issue...")
    
    # Get Snowy Owl species ID from database
    result = client.table('species').select('id, scientific_name').eq('scientific_name', 'Nyctea scandiaca').execute()
    
    if not result.data:
        logger.error("Snowy Owl (Nyctea scandiaca) not found in species table!")
        return False
    
    snowy_owl_id = result.data[0]['id']
    logger.info(f"Found Snowy Owl in database: {snowy_owl_id}")
    
    # Load the illegal trade CSV
    logger.info("Loading illegal trade data...")
    df = pd.read_csv('arctic_illegal_trade_records.csv')
    
    # Find all Snowy Owl records (various name variations)
    snowy_owl_variants = ['Bubo scandiacus', 'Bubo scandiaca', 'Nyctea scandiaca']
    snowy_owl_records = df[df['arctic_scientific_name'].isin(snowy_owl_variants)]
    
    logger.info(f"Found {len(snowy_owl_records)} Snowy Owl records to load")
    
    # Get product mappings
    products_result = client.table('illegal_trade_products').select('id, product_code').execute()
    product_mapping = {p['product_code']: p['id'] for p in products_result.data}
    
    # Prepare records for insertion
    records_to_insert = []
    
    for _, row in snowy_owl_records.iterrows():
        record = {
            'species_id': snowy_owl_id,
            'source_database': row['db'].upper() if pd.notna(row['db']) else 'WTP',
            'product_type_id': product_mapping.get(row['standardized_use_id']),
            'product_category': row['main_category'] if pd.notna(row['main_category']) else None,
            'reported_taxon_name': row['db_taxa_name'] if pd.notna(row['db_taxa_name']) else None,
            'gbif_id': str(row['gbif_id']) if pd.notna(row['gbif_id']) else None,
            'db_taxa_name_clean': row['db_taxa_name_clean'] if pd.notna(row['db_taxa_name_clean']) else None,
            'data_source': 'Stringham et al. 2021'
        }
        records_to_insert.append(record)
    
    if dry_run:
        logger.info("DRY RUN: Would insert the following records:")
        for i, rec in enumerate(records_to_insert[:5]):
            logger.info(f"  {i+1}. {rec['reported_taxon_name']} - {rec['product_category']}")
        logger.info(f"  ... and {len(records_to_insert)-5} more records")
        return True
    
    # Insert records
    logger.info(f"Inserting {len(records_to_insert)} Snowy Owl records...")
    
    try:
        # Insert in batches
        batch_size = 50
        inserted = 0
        
        for i in range(0, len(records_to_insert), batch_size):
            batch = records_to_insert[i:i+batch_size]
            result = client.table('illegal_trade_seizures').insert(batch).execute()
            inserted += len(batch)
            logger.info(f"Inserted batch: {inserted}/{len(records_to_insert)}")
        
        logger.info(f"✅ Successfully inserted {inserted} Snowy Owl records!")
        
        # Verify the fix
        total_result = client.table('illegal_trade_seizures').select('count', count='exact').execute()
        snowy_result = client.table('illegal_trade_seizures').select('count', count='exact').eq('species_id', snowy_owl_id).execute()
        
        logger.info(f"Total illegal trade records: {total_result.count}")
        logger.info(f"Snowy Owl seizures: {snowy_result.count}")
        
        # Update statistics
        logger.info("\n📊 Updated Illegal Trade Statistics:")
        logger.info(f"  Total seizure records: {total_result.count} (was 881)")
        logger.info(f"  Species with seizures: 29 (was 28)")
        logger.info(f"  Snowy Owl now included with {snowy_result.count} seizures")
        
        return True
        
    except Exception as e:
        logger.error(f"Error inserting records: {e}")
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix Snowy Owl mapping in illegal trade data')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    
    args = parser.parse_args()
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    success = fix_snowy_owl_records(dry_run=args.dry_run)
    
    if success:
        logger.info("🎉 Snowy Owl fix completed successfully!")
        if not args.dry_run:
            logger.info("Remember to update documentation with new totals:")
            logger.info("  - Total illegal trade records: ~919 (881 + 38)")
            logger.info("  - Species in illegal trade: 29 (was 28)")
    else:
        logger.error("❌ Snowy Owl fix failed")
        sys.exit(1)

if __name__ == "__main__":
    main()