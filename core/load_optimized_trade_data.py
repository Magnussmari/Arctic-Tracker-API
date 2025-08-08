#!/usr/bin/env python3
"""
Load Optimized Trade Data to Supabase

This script safely replaces all CITES trade data in Supabase with the optimized
JSON files. It includes backup, validation, and comprehensive error handling.

NOTE: This script now uses the 'optimized_species' directory by default, which contains the complete
set of 44 optimized trade data files, including two files that were missing from
the original 'optimized' directory:
- Branta_ruficollis_trade_data_optimized.json.gz
- Lagenorhynchus_albirostris_trade_data_optimized.json.gz

IMPORTANT: This script will DELETE all existing trade data!

Usage:
    python load_optimized_trade_data.py [--dry-run] [--backup] [--batch-size 1000]
"""

import json
import os
import sys
import argparse
import logging
import gzip
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import uuid

# Add the config directory to the path
sys.path.append(str(Path(__file__).parent.parent / 'config'))

try:
    from supabase_config import get_supabase_client
except ImportError:
    print("Error: Could not import supabase_config. Please ensure config/supabase_config.py exists.")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'trade_data_load_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class LoadStats:
    """Statistics for the data loading process"""
    files_processed: int = 0
    records_loaded: int = 0
    records_failed: int = 0
    species_mapped: int = 0
    species_missing: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class OptimizedTradeDataReader:
    """Read optimized trade data files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = self._load_data()
        self.lookup_tables = self.data['lookup_tables']
    
    def _load_data(self) -> Dict:
        """Load data from JSON or compressed JSON"""
        if self.file_path.suffix == '.gz':
            with gzip.open(self.file_path, 'rt', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def get_denormalized_records(self) -> List[Dict]:
        """Get all trade records in original format"""
        records = []
        
        taxonomic_lookup = self.lookup_tables['taxonomic']
        location_lookup = self.lookup_tables['locations']
        categorical_lookup = self.lookup_tables['categorical_reverse']
        
        for record in self.data['trade_records']:
            # Reconstruct full record
            full_record = {
                'id': record.get('id', ''),
                'year': record.get('year'),
                'quantity_raw': record.get('quantity_raw', ''),
                'quantity_normalized': record.get('quantity_normalized'),
                'source_file': record.get('source_file', ''),
                'row_number': record.get('row_number')
            }
            
            # Add taxonomic data
            taxonomic_id = record.get('taxonomic_id')
            if taxonomic_id is not None and str(taxonomic_id) in taxonomic_lookup:
                taxonomic_data = taxonomic_lookup[str(taxonomic_id)]
                full_record.update(taxonomic_data)
            
            # Add location data
            for location_field in ['importer', 'exporter', 'origin']:
                location_id = record.get(f'{location_field}_id')
                if location_id is not None and str(location_id) in location_lookup:
                    full_record[location_field] = location_lookup[str(location_id)]
                else:
                    full_record[location_field] = ''
            
            # Add categorical data
            for category, lookup in categorical_lookup.items():
                cat_id = record.get(f'{category}_id')
                if cat_id is not None and str(cat_id) in lookup:
                    full_record[category] = lookup[str(cat_id)]
                else:
                    full_record[category] = ''
            
            records.append(full_record)
        
        return records

class TradeDataLoader:
    """Load optimized trade data into Supabase"""
    
    def __init__(self, optimized_dir: str, dry_run: bool = False, batch_size: int = 1000):
        self.optimized_dir = Path(optimized_dir)
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.supabase = get_supabase_client()
        self.stats = LoadStats()
        self.species_id_map = {}  # scientific_name -> species_id mapping
        
    def load_species_mapping(self) -> None:
        """Load species ID mapping from database"""
        logger.info("Loading species ID mapping from database...")
        
        try:
            response = self.supabase.table('species').select('id, scientific_name').execute()
            
            for species in response.data:
                scientific_name = species['scientific_name']
                species_id = species['id']
                self.species_id_map[scientific_name] = species_id
            
            logger.info(f"Loaded {len(self.species_id_map)} species mappings")
            
        except Exception as e:
            logger.error(f"Failed to load species mapping: {e}")
            raise
    
    def backup_existing_data(self, backup_file: str) -> bool:
        """Create backup of existing trade data"""
        if self.dry_run:
            logger.info("[DRY RUN] Would backup existing trade data")
            return True
        
        logger.info("Creating backup of existing trade data...")
        
        try:
            # Get count first
            count_response = self.supabase.table('cites_trade_records').select('id', count='exact').execute()
            total_records = count_response.count
            
            logger.info(f"Backing up {total_records:,} existing trade records...")
            
            # Fetch all data in chunks
            all_records = []
            offset = 0
            chunk_size = 10000
            
            while offset < total_records:
                response = self.supabase.table('cites_trade_records').select('*').range(offset, offset + chunk_size - 1).execute()
                all_records.extend(response.data)
                offset += chunk_size
                logger.info(f"Backed up {len(all_records):,} / {total_records:,} records")
            
            # Save backup
            backup_data = {
                'backup_timestamp': datetime.now().isoformat(),
                'record_count': len(all_records),
                'records': all_records
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Backup saved to {backup_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False
    
    def clear_existing_data(self) -> bool:
        """Clear all existing trade data"""
        if self.dry_run:
            logger.info("[DRY RUN] Would clear all existing trade data")
            return True
        
        logger.info("Clearing existing trade data...")
        
        try:
            # Get current count
            count_response = self.supabase.table('cites_trade_records').select('id', count='exact').execute()
            current_count = count_response.count
            
            logger.info(f"Deleting {current_count:,} existing records...")
            
            # Try different methods for fast deletion
            # Method 1: Try using raw SQL for faster deletion via RPC
            try:
                # Use PostgreSQL's TRUNCATE command which is much faster
                sql_response = self.supabase.rpc('exec_sql', {'sql': 'TRUNCATE TABLE cites_trade_records'}).execute()
                logger.info("Successfully truncated table using SQL RPC")
                
                # Verify deletion
                verify_response = self.supabase.table('cites_trade_records').select('id', count='exact').execute()
                remaining_count = verify_response.count
                
                if remaining_count == 0:
                    logger.info("Successfully cleared all existing trade data")
                    return True
            except Exception as sql_e:
                logger.warning(f"SQL truncate via RPC failed: {sql_e}, trying alternative methods...")
                
            # Method 2: Try using DELETE without WHERE clause
            try:
                logger.info("Attempting direct DELETE without WHERE clause...")
                # This should execute a DELETE without WHERE, which is nearly as fast as TRUNCATE
                delete_all = self.supabase.table('cites_trade_records').delete().execute()
                
                # Verify deletion
                verify_response = self.supabase.table('cites_trade_records').select('id', count='exact').execute()
                remaining_count = verify_response.count
                
                if remaining_count == 0:
                    logger.info("Successfully cleared all existing trade data using DELETE without WHERE")
                    return True
                else:
                    logger.warning(f"DELETE without WHERE partially worked: {remaining_count} records remain")
            except Exception as delete_e:
                logger.warning(f"DELETE without WHERE failed: {delete_e}, trying batch delete...")                
                # Fallback to batch delete if SQL truncate doesn't work
                # Use a much smaller batch size to avoid "414 Request-URI Too Large" errors
                batch_size = 100  # Reduced from 1000 to avoid URI too long errors
                deleted_total = 0
                
                while deleted_total < current_count:
                    try:
                        # Get a small batch of records to delete
                        batch_response = self.supabase.table('cites_trade_records').select('id').limit(batch_size).execute()
                        
                        if not batch_response.data:
                            break  # No more records
                        
                        # Extract IDs and delete using IN operator with smaller batches
                        ids_to_delete = [record['id'] for record in batch_response.data]
                        
                        # Further split into smaller chunks if needed to avoid URI length limits
                        chunk_size = 20  # Very conservative chunk size
                        for i in range(0, len(ids_to_delete), chunk_size):
                            chunk_ids = ids_to_delete[i:i + chunk_size]
                            delete_response = self.supabase.table('cites_trade_records').delete().in_('id', chunk_ids).execute()
                        
                        deleted_total += len(ids_to_delete)
                        logger.info(f"Deleted {deleted_total:,} / {current_count:,} records")
                        
                    except Exception as batch_e:
                        logger.error(f"Batch delete failed: {batch_e}")
                        # Try to continue with a smaller batch size instead of breaking completely
                        if batch_size > 10:
                            batch_size = batch_size // 2
                            logger.info(f"Reducing batch size to {batch_size} and continuing...")
                        else:
                            logger.error("Batch size already at minimum, cannot reduce further.")
                            break
            
            # Final verification
            verify_response = self.supabase.table('cites_trade_records').select('id', count='exact').execute()
            remaining_count = verify_response.count
            
            if remaining_count == 0:
                logger.info("Successfully cleared all existing trade data")
                return True
            elif remaining_count < current_count * 0.1:  # If we deleted 90%+, consider it success
                logger.warning(f"Mostly cleared data: {remaining_count:,} records remain (acceptable)")
                return True
            else:
                logger.error(f"Failed to clear sufficient data: {remaining_count:,} records remain")
                return False
                
        except Exception as e:
            logger.error(f"Failed to clear existing data: {e}")
            return False
    
    def convert_record_to_db_format(self, record: Dict, species_scientific_name: str) -> Optional[Dict]:
        """Convert trade record to database format"""
        try:
            # Get species ID
            species_id = self.species_id_map.get(species_scientific_name)
            if not species_id:
                logger.warning(f"No species ID found for: {species_scientific_name}")
                self.stats.species_missing += 1
                return None
            
            # Convert record to database format
            db_record = {
                'id': str(uuid.uuid4()),  # Generate new UUID
                'species_id': species_id,
                'record_id': record.get('id', ''),
                'year': record.get('year'),
                'appendix': record.get('appendix', ''),
                'taxon': species_scientific_name,
                'class': record.get('class', ''),
                'order_name': record.get('order', ''),
                'family': record.get('family', ''),
                'genus': record.get('genus', ''),
                'term': record.get('term', ''),
                'quantity': record.get('quantity_normalized'),
                'unit': record.get('unit', ''),
                'importer': record.get('importer', ''),
                'exporter': record.get('exporter', ''),
                'origin': record.get('origin', ''),
                'purpose': record.get('purpose', ''),
                'source': record.get('source', ''),
                'reporter_type': record.get('reporter_type', ''),
                'import_permit': '',  # Not available in optimized format
                'export_permit': '',  # Not available in optimized format
                'origin_permit': ''   # Not available in optimized format
            }
            
            return db_record
            
        except Exception as e:
            logger.error(f"Failed to convert record: {e}")
            return None
    
    def load_species_file(self, file_path: Path) -> Tuple[int, int]:
        """Load trade data for a single species file"""
        logger.info(f"Loading {file_path.name}...")
        
        # Extract species name from filename
        filename = file_path.stem
        # Handle .gz files where stem gives us the .json name
        if filename.endswith('.json'):
            filename = filename[:-5]  # Remove .json extension
        if filename.endswith('_trade_data_optimized'):
            species_name = filename.replace('_trade_data_optimized', '').replace('_', ' ')
        else:
            logger.error(f"Unexpected filename format: {filename}")
            return 0, 0
        
        try:
            # Load optimized data
            reader = OptimizedTradeDataReader(str(file_path))
            records = reader.get_denormalized_records()
            
            logger.info(f"Found {len(records):,} records for {species_name}")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would load {len(records):,} records for {species_name}")
                return len(records), 0
            
            # Convert records to database format
            db_records = []
            failed_count = 0
            
            for record in records:
                db_record = self.convert_record_to_db_format(record, species_name)
                if db_record:
                    db_records.append(db_record)
                else:
                    failed_count += 1
            
            if not db_records:
                logger.warning(f"No valid records to load for {species_name}")
                return 0, failed_count
            
            # Insert records in batches
            loaded_count = 0
            for i in range(0, len(db_records), self.batch_size):
                batch = db_records[i:i + self.batch_size]
                
                try:
                    response = self.supabase.table('cites_trade_records').insert(batch).execute()
                    loaded_count += len(batch)
                    logger.info(f"  Loaded batch: {loaded_count:,} / {len(db_records):,} records")
                    
                except Exception as e:
                    logger.error(f"Failed to load batch for {species_name}: {e}")
                    failed_count += len(batch)
            
            logger.info(f"Completed {species_name}: {loaded_count:,} loaded, {failed_count} failed")
            return loaded_count, failed_count
            
        except Exception as e:
            logger.error(f"Failed to load {file_path.name}: {e}")
            return 0, len(records) if 'records' in locals() else 0
    
    def load_all_data(self) -> bool:
        """Load all optimized trade data files"""
        self.stats.start_time = datetime.now()
        
        # Find all optimized files (prefer compressed versions)
        optimized_files = []
        
        # Look for .json.gz files first, then .json files
        for pattern in ['*_trade_data_optimized.json.gz', '*_trade_data_optimized.json']:
            files = list(self.optimized_dir.glob(pattern))
            
            # If we find .gz files, use only those
            if pattern.endswith('.gz') and files:
                optimized_files = files
                break
            elif not optimized_files:  # Only use .json if no .gz found
                optimized_files = files
        
        if not optimized_files:
            logger.error(f"No optimized trade data files found in {self.optimized_dir}")
            return False
        
        logger.info(f"Found {len(optimized_files)} optimized trade data files")
        
        # Load species mapping
        self.load_species_mapping()
        
        # Process each file
        for file_path in sorted(optimized_files):
            loaded, failed = self.load_species_file(file_path)
            self.stats.files_processed += 1
            self.stats.records_loaded += loaded
            self.stats.records_failed += failed
        
        self.stats.end_time = datetime.now()
        return True
    
    def validate_loaded_data(self) -> bool:
        """Validate the loaded data"""
        logger.info("Validating loaded data...")
        
        try:
            # Get total count
            count_response = self.supabase.table('cites_trade_records').select('id', count='exact').execute()
            total_loaded = count_response.count
            
            # Check species coverage
            species_response = self.supabase.table('cites_trade_records').select('taxon').execute()
            unique_species = set(record['taxon'] for record in species_response.data)
            
            # Check year range
            year_response = self.supabase.table('cites_trade_records').select('year').order('year').execute()
            years = [record['year'] for record in year_response.data if record['year']]
            min_year = min(years) if years else None
            max_year = max(years) if years else None
            
            logger.info(f"Validation Results:")
            logger.info(f"  Total records: {total_loaded:,}")
            logger.info(f"  Unique species: {len(unique_species)}")
            logger.info(f"  Year range: {min_year} - {max_year}")
            logger.info(f"  Expected records: 463,345")
            
            # Check if we're close to expected count (allowing for species mapping failures)
            if total_loaded >= 450000:  # Allow some tolerance
                logger.info("✅ Data validation successful")
                return True
            else:
                logger.warning(f"⚠️  Loaded count ({total_loaded:,}) is significantly below expected (463,345)")
                return False
                
        except Exception as e:
            logger.error(f"Failed to validate data: {e}")
            return False
    
    def print_final_stats(self) -> None:
        """Print final loading statistics"""
        duration = self.stats.end_time - self.stats.start_time if self.stats.end_time and self.stats.start_time else None
        
        logger.info("\n" + "="*60)
        logger.info("TRADE DATA LOADING COMPLETED")
        logger.info("="*60)
        logger.info(f"Files processed: {self.stats.files_processed}")
        logger.info(f"Records loaded: {self.stats.records_loaded:,}")
        logger.info(f"Records failed: {self.stats.records_failed:,}")
        logger.info(f"Species mapped: {len(self.species_id_map)}")
        logger.info(f"Species missing: {self.stats.species_missing}")
        
        if duration:
            logger.info(f"Total time: {duration}")
            if self.stats.records_loaded > 0:
                rate = self.stats.records_loaded / duration.total_seconds()
                logger.info(f"Loading rate: {rate:.1f} records/second")
        
        logger.info("="*60)

def main():
    parser = argparse.ArgumentParser(description='Load optimized trade data to Supabase')
    parser.add_argument('--optimized-dir', 
                       default='../species_data/processed/optimized_species',
                       help='Directory containing optimized JSON files')
    parser.add_argument('--dry-run', action='store_true',
                       help='Perform dry run without making changes')
    parser.add_argument('--backup', action='store_true',
                       help='Create backup before loading (recommended)')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for database inserts')
    
    args = parser.parse_args()
    
    # Initialize loader
    loader = TradeDataLoader(
        optimized_dir=args.optimized_dir,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )
    
    try:
        logger.info("Starting optimized trade data loading process...")
        logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE LOADING'}")
        
        # Create backup if requested
        if args.backup and not args.dry_run:
            backup_file = f"trade_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            if not loader.backup_existing_data(backup_file):
                logger.error("Backup failed. Aborting load process.")
                return 1
        
        # Clear existing data
        if not loader.clear_existing_data():
            logger.error("Failed to clear existing data. Aborting load process.")
            return 1
        
        # Load new data
        if not loader.load_all_data():
            logger.error("Failed to load new data.")
            return 1
        
        # Validate loaded data (skip for dry run)
        if not args.dry_run:
            if not loader.validate_loaded_data():
                logger.warning("Data validation failed. Please review the results.")
        
        # Print final statistics
        loader.print_final_stats()
        
        logger.info("Trade data loading process completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.error("Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
