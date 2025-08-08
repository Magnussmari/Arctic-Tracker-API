#!/usr/bin/env python3
"""
Backup CITES Trade Data
Arctic Tracker - CITES Migration 2025

Creates a complete backup of the current cites_trade_records table
before performing the migration to v2025.1 data.

Usage:
    python backup_cites_data.py [--output-file backup.csv]
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime
from typing import Optional
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.supabase_config import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/cites_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CitesBackupCreator:
    """Creates backup of CITES trade data before migration"""
    
    def __init__(self, output_file: Optional[str] = None):
        self.supabase = get_supabase_client()
        self.backup_file = output_file or f"backups/cites_trade_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.backup_stats = {
            'total_records': 0,
            'backup_size_mb': 0,
            'start_time': None,
            'end_time': None,
            'species_count': 0
        }
        
    def create_backup_directory(self) -> None:
        """Ensure backup directory exists"""
        os.makedirs('backups', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
    def get_current_record_count(self) -> int:
        """Get current count of CITES records"""
        try:
            result = self.supabase.table('cites_trade_records').select('count', count='exact').execute()
            return result.count
        except Exception as e:
            logger.error(f"Error getting record count: {e}")
            return 0
    
    def backup_cites_data(self, batch_size: int = 10000) -> bool:
        """Create backup of CITES trade data"""
        logger.info("🔄 Starting CITES trade data backup...")
        self.backup_stats['start_time'] = datetime.now()
        
        try:
            # Get total count first
            total_records = self.get_current_record_count()
            self.backup_stats['total_records'] = total_records
            
            if total_records == 0:
                logger.warning("No records found in cites_trade_records table")
                return False
            
            logger.info(f"Backing up {total_records:,} CITES trade records...")
            
            # Initialize CSV file with headers
            all_records = []
            records_processed = 0
            
            # Fetch data in batches
            offset = 0
            while offset < total_records:
                logger.info(f"Fetching batch {offset//batch_size + 1}: records {offset:,} to {min(offset + batch_size, total_records):,}")
                
                # Get batch of records
                result = self.supabase.table('cites_trade_records')\
                    .select('*')\
                    .range(offset, offset + batch_size - 1)\
                    .execute()
                
                batch_records = result.data
                if not batch_records:
                    break
                
                all_records.extend(batch_records)
                records_processed += len(batch_records)
                offset += batch_size
                
                # Progress update
                progress = (records_processed / total_records) * 100
                logger.info(f"Progress: {progress:.1f}% ({records_processed:,}/{total_records:,} records)")
            
            # Convert to DataFrame and save
            logger.info("Converting to CSV format...")
            df = pd.DataFrame(all_records)
            
            # Save to CSV
            df.to_csv(self.backup_file, index=False)
            
            # Calculate backup stats
            file_size_mb = os.path.getsize(self.backup_file) / (1024 * 1024)
            self.backup_stats['backup_size_mb'] = round(file_size_mb, 2)
            self.backup_stats['species_count'] = df['species_id'].nunique()
            self.backup_stats['end_time'] = datetime.now()
            
            duration = self.backup_stats['end_time'] - self.backup_stats['start_time']
            
            logger.info(f"✅ Backup completed successfully!")
            logger.info(f"   📄 File: {self.backup_file}")
            logger.info(f"   📊 Records: {records_processed:,}")
            logger.info(f"   🏷️  Species: {self.backup_stats['species_count']}")
            logger.info(f"   💾 Size: {file_size_mb:.2f} MB")
            logger.info(f"   ⏱️  Duration: {duration}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return False
    
    def validate_backup(self) -> bool:
        """Validate the backup file"""
        logger.info("Validating backup file...")
        
        try:
            # Check file exists
            if not os.path.exists(self.backup_file):
                logger.error(f"Backup file not found: {self.backup_file}")
                return False
            
            # Load and check record count
            df = pd.read_csv(self.backup_file)
            backup_record_count = len(df)
            
            # Compare with database
            current_count = self.get_current_record_count()
            
            if backup_record_count != current_count:
                logger.error(f"Record count mismatch: backup={backup_record_count:,}, database={current_count:,}")
                return False
            
            # Check required columns
            required_columns = ['id', 'species_id', 'year', 'appendix', 'taxon', 'quantity']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Missing required columns: {missing_columns}")
                return False
            
            # Check for null species_id (critical foreign key)
            null_species = df['species_id'].isnull().sum()
            if null_species > 0:
                logger.warning(f"Found {null_species} records with null species_id")
            
            logger.info("✅ Backup validation passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Backup validation failed: {e}")
            return False
    
    def create_backup_manifest(self) -> None:
        """Create manifest file with backup metadata"""
        manifest = {
            'backup_metadata': {
                'created_at': self.backup_stats['start_time'].isoformat() if self.backup_stats['start_time'] else None,
                'completed_at': self.backup_stats['end_time'].isoformat() if self.backup_stats['end_time'] else None,
                'backup_file': self.backup_file,
                'purpose': 'Pre-migration backup for CITES v2025.1 update'
            },
            'data_summary': self.backup_stats,
            'migration_context': {
                'source_version': 'CITES v2024 and earlier',
                'target_version': 'CITES v2025.1',
                'expected_new_records': 30989,
                'migration_date': datetime.now().strftime('%Y-%m-%d')
            },
            'restore_instructions': {
                'command': f'COPY cites_trade_records FROM \'{self.backup_file}\' CSV HEADER;',
                'note': 'Truncate table before restore if full restoration needed'
            }
        }
        
        manifest_file = self.backup_file.replace('.csv', '_manifest.json')
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(f"📋 Backup manifest created: {manifest_file}")

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backup CITES trade data before migration')
    parser.add_argument('--output-file', help='Custom output file path')
    parser.add_argument('--batch-size', type=int, default=10000, help='Batch size for data retrieval')
    
    args = parser.parse_args()
    
    backup_creator = CitesBackupCreator(output_file=args.output_file)
    
    try:
        # Create backup directory
        backup_creator.create_backup_directory()
        
        # Create backup
        success = backup_creator.backup_cites_data(batch_size=args.batch_size)
        if not success:
            logger.error("Backup creation failed")
            sys.exit(1)
        
        # Validate backup
        if not backup_creator.validate_backup():
            logger.error("Backup validation failed")
            sys.exit(1)
        
        # Create manifest
        backup_creator.create_backup_manifest()
        
        logger.info("🎉 CITES backup process completed successfully!")
        logger.info(f"Backup ready for migration: {backup_creator.backup_file}")
        
    except Exception as e:
        logger.error(f"Backup process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()