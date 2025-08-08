#!/usr/bin/env python3
"""
Resume CITES Staging Load
Arctic Tracker - CITES Migration 2025

Resumes loading CITES data to staging table without clearing existing data.
Checks what's already loaded and continues from there.

Usage:
    python resume_staging_load.py [--batch-size 1000]
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.supabase_config import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/staging_resume_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_loaded_record_ids():
    """Get IDs of already loaded records to avoid duplicates"""
    logger.info("Checking already loaded records...")
    client = get_supabase_client()
    
    # Get count first
    result = client.table('cites_trade_records_staging').select('count', count='exact').execute()
    loaded_count = result.count
    logger.info(f"Currently loaded: {loaded_count:,} records")
    
    # Get a sample to check what's loaded
    sample = client.table('cites_trade_records_staging')\
        .select('taxon, year')\
        .order('created_at', desc=True)\
        .limit(5)\
        .execute()
    
    if sample.data:
        logger.info("Recent records:")
        for rec in sample.data:
            logger.info(f"  - {rec['taxon']} ({rec['year']})")
    
    return loaded_count

def load_remaining_records(batch_size=1000):
    """Load only the remaining records"""
    client = get_supabase_client(use_service_role=True)
    
    # Get current count
    current_count = get_loaded_record_ids()
    target_count = 489148
    
    if current_count >= target_count:
        logger.info("✅ All records already loaded!")
        return
    
    remaining = target_count - current_count
    logger.info(f"Need to load {remaining:,} more records")
    
    # Load the full CSV
    logger.info("Loading extracted data...")
    df = pd.read_csv('extracted_data/arctic_species_trade_data_v2025.csv')
    
    # Skip already loaded records (assuming they were loaded in order)
    df_remaining = df.iloc[current_count:]
    logger.info(f"Processing {len(df_remaining):,} remaining records")
    
    # Load species mapping
    logger.info("Loading species mappings...")
    species_result = client.table('species').select('id, scientific_name').execute()
    species_mapping = {s['scientific_name']: s['id'] for s in species_result.data}
    
    # Map species IDs
    df_remaining['species_id'] = df_remaining['Taxon'].map(species_mapping)
    
    # Prepare records
    logger.info("Preparing records for insertion...")
    records = []
    for _, row in df_remaining.iterrows():
        record = {
            'species_id': row['species_id'],
            'year': int(row['Year']),
            'appendix': row['Appendix'] if pd.notna(row['Appendix']) else None,
            'taxon': row['Taxon'],
            'class': row['Class'] if pd.notna(row['Class']) else None,
            'order_name': row['Order'] if pd.notna(row['Order']) else None,
            'family': row['Family'] if pd.notna(row['Family']) else None,
            'genus': row['Genus'] if pd.notna(row['Genus']) else None,
            'importer': row['Importer'] if pd.notna(row['Importer']) else None,
            'exporter': row['Exporter'] if pd.notna(row['Exporter']) else None,
            'origin': row['Origin'] if pd.notna(row['Origin']) else None,
            'importer_reported_quantity': float(row['Quantity']) if pd.notna(row['Quantity']) else None,
            'exporter_reported_quantity': float(row['Quantity']) if pd.notna(row['Quantity']) else None,
            'term': row['Term'] if pd.notna(row['Term']) else None,
            'unit': row['Unit'] if pd.notna(row['Unit']) else None,
            'purpose': row['Purpose'] if pd.notna(row['Purpose']) else None,
            'source': row['Source'] if pd.notna(row['Source']) else None,
            'data_source': 'CITES v2025.1'
        }
        records.append(record)
    
    # Load in batches
    logger.info(f"Loading {len(records):,} records in batches of {batch_size}...")
    start_time = datetime.now()
    loaded = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            result = client.table('cites_trade_records_staging').insert(batch).execute()
            loaded += len(batch)
            
            total_loaded = current_count + loaded
            progress = (total_loaded / target_count) * 100
            
            if batch_num % 10 == 0 or batch_num == 1:
                elapsed = datetime.now() - start_time
                rate = loaded / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
                eta_seconds = (len(records) - loaded) / rate if rate > 0 else 0
                eta_minutes = int(eta_seconds / 60)
                
                logger.info(f"Batch {batch_num}: {total_loaded:,}/{target_count:,} ({progress:.1f}%) - "
                          f"Rate: {rate:.0f} records/sec - ETA: {eta_minutes} minutes")
                
        except Exception as e:
            logger.error(f"Error in batch {batch_num}: {e}")
            # Continue with next batch
    
    # Final check
    final_result = client.table('cites_trade_records_staging').select('count', count='exact').execute()
    final_count = final_result.count
    
    logger.info(f"\n{'='*50}")
    logger.info(f"✅ Loading complete!")
    logger.info(f"Final count: {final_count:,}/{target_count:,}")
    logger.info(f"Time taken: {datetime.now() - start_time}")
    
    if final_count >= target_count:
        logger.info("🎉 All CITES v2025.1 data loaded successfully!")
        logger.info("Ready for validation and final migration")
    else:
        missing = target_count - final_count
        logger.warning(f"⚠️  Still missing {missing:,} records")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Resume CITES staging load')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for inserts')
    
    args = parser.parse_args()
    
    try:
        load_remaining_records(batch_size=args.batch_size)
    except Exception as e:
        logger.error(f"Resume failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()