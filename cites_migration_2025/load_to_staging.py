#!/usr/bin/env python3
"""
Load CITES v2025.1 Data to Staging Table
Arctic Tracker - CITES Migration 2025

Loads the extracted Arctic species CITES data into the staging table
for validation before final migration.

Usage:
    python load_to_staging.py [--batch-size 5000] [--dry-run]
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime
from typing import Dict, List, Optional
import json
import uuid

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.supabase_config import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/staging_load_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CitesStageLoader:
    """Loads CITES v2025.1 data into staging table"""
    
    def __init__(self, dry_run: bool = False, batch_size: int = 5000):
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.supabase = get_supabase_client(use_service_role=True)
        self.species_mapping = {}
        self.load_stats = {
            'total_records': 0,
            'successful_loads': 0,
            'failed_loads': 0,
            'species_mapped': 0,
            'start_time': None,
            'end_time': None
        }
        
    def load_species_mapping(self) -> None:
        """Load species ID mappings for foreign key resolution"""
        logger.info("Loading species mappings...")
        
        try:
            result = self.supabase.table('species').select('id, scientific_name').execute()
            self.species_mapping = {
                species['scientific_name']: species['id'] 
                for species in result.data
            }
            logger.info(f"Loaded {len(self.species_mapping)} species mappings")
            
        except Exception as e:
            logger.error(f"Error loading species mappings: {e}")
            raise
    
    def load_extracted_data(self, csv_path: str) -> pd.DataFrame:
        """Load the extracted CITES data CSV"""
        logger.info(f"Loading extracted data from {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            self.load_stats['total_records'] = len(df)
            logger.info(f"Loaded {len(df):,} records from extraction")
            
            # Display data overview
            logger.info(f"Data spans years {df['Year'].min()} to {df['Year'].max()}")
            logger.info(f"Unique species: {df['Taxon'].nunique()}")
            logger.info(f"Unique importers: {df['Importer'].nunique()}")
            logger.info(f"Unique exporters: {df['Exporter'].nunique()}")
            
            return df
            
        except Exception as e:
            logger.error(f"Error loading extracted data: {e}")
            raise
    
    def map_species_ids(self, df: pd.DataFrame) -> pd.DataFrame:
        """Map taxon names to species IDs"""
        logger.info("Mapping species IDs...")
        
        # Create species_id column
        df['species_id'] = None
        
        mapped_count = 0
        for index, row in df.iterrows():
            taxon = row['Taxon']
            if taxon in self.species_mapping:
                df.at[index, 'species_id'] = self.species_mapping[taxon]
                mapped_count += 1
        
        self.load_stats['species_mapped'] = mapped_count
        unmapped_count = len(df) - mapped_count
        
        logger.info(f"Species mapping results:")
        logger.info(f"  Mapped: {mapped_count:,} records ({(mapped_count/len(df)*100):.1f}%)")
        logger.info(f"  Unmapped: {unmapped_count:,} records ({(unmapped_count/len(df)*100):.1f}%)")
        
        if unmapped_count > 0:
            unmapped_species = df[df['species_id'].isnull()]['Taxon'].unique()
            logger.warning(f"Unmapped species: {list(unmapped_species)[:10]}...")
            
            # Filter out unmapped records for staging load
            df = df[df['species_id'].notna()].copy()
            logger.info(f"Proceeding with {len(df):,} mappable records")
        
        return df
    
    def prepare_staging_records(self, df: pd.DataFrame) -> List[Dict]:
        """Prepare records for staging table insertion"""
        logger.info("Preparing records for staging insertion...")
        
        staging_records = []
        
        for _, row in df.iterrows():
            # Map CSV columns to staging table columns
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
                'importer_reported_quantity': self._safe_numeric(row['Quantity']),
                'exporter_reported_quantity': self._safe_numeric(row['Quantity']),  # Same value for both
                'term': row['Term'] if pd.notna(row['Term']) else None,
                'unit': row['Unit'] if pd.notna(row['Unit']) else None,
                'purpose': row['Purpose'] if pd.notna(row['Purpose']) else None,
                'source': row['Source'] if pd.notna(row['Source']) else None,
                'data_source': 'CITES v2025.1'
            }
            
            staging_records.append(record)
        
        logger.info(f"Prepared {len(staging_records):,} records for staging")
        return staging_records
    
    def _safe_numeric(self, value) -> Optional[float]:
        """Safely convert value to numeric"""
        if pd.isna(value) or value == '' or str(value).lower() == 'nan':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def clear_staging_table(self) -> None:
        """Clear existing staging table data"""
        if self.dry_run:
            logger.info("DRY RUN: Would clear staging table")
            return
            
        try:
            logger.info("Clearing staging table...")
            # Use a non-existent ID to clear all records
            result = self.supabase.table('cites_trade_records_staging')\
                .delete()\
                .neq('id', '00000000-0000-0000-0000-000000000000')\
                .execute()
            logger.info("Staging table cleared")
            
        except Exception as e:
            logger.error(f"Error clearing staging table: {e}")
            raise
    
    def load_to_staging(self, staging_records: List[Dict]) -> None:
        """Load records into staging table"""
        if self.dry_run:
            logger.info(f"DRY RUN: Would load {len(staging_records):,} records to staging")
            return
        
        logger.info(f"Loading {len(staging_records):,} records to staging table...")
        self.load_stats['start_time'] = datetime.now()
        
        try:
            successful_inserts = 0
            failed_inserts = 0
            
            # Insert in batches
            for i in range(0, len(staging_records), self.batch_size):
                batch = staging_records[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                
                try:
                    result = self.supabase.table('cites_trade_records_staging').insert(batch).execute()
                    successful_inserts += len(batch)
                    
                    if batch_num % 10 == 0 or batch_num == 1:
                        progress = (successful_inserts / len(staging_records)) * 100
                        logger.info(f"Batch {batch_num}: {successful_inserts:,}/{len(staging_records):,} records ({progress:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"Error inserting batch {batch_num}: {e}")
                    failed_inserts += len(batch)
                    continue
            
            self.load_stats['successful_loads'] = successful_inserts
            self.load_stats['failed_loads'] = failed_inserts
            self.load_stats['end_time'] = datetime.now()
            
            duration = self.load_stats['end_time'] - self.load_stats['start_time']
            
            logger.info(f"Staging load completed:")
            logger.info(f"  Successful: {successful_inserts:,}")
            logger.info(f"  Failed: {failed_inserts:,}")
            logger.info(f"  Duration: {duration}")
            
        except Exception as e:
            logger.error(f"Error loading to staging: {e}")
            raise
    
    def validate_staging_load(self) -> bool:
        """Validate the staging table load"""
        logger.info("Validating staging table load...")
        
        try:
            # Get staging summary
            result = self.supabase.table('cites_staging_summary').select('*').execute()
            if not result.data:
                logger.error("No staging summary data found")
                return False
            
            summary = result.data[0]
            
            logger.info("Staging validation results:")
            logger.info(f"  Total records: {summary['total_records']:,}")
            logger.info(f"  Unique species: {summary['unique_species']}")
            logger.info(f"  Year range: {summary['earliest_year']} - {summary['latest_year']}")
            logger.info(f"  Appendix I: {summary['appendix_i_count']:,}")
            logger.info(f"  Appendix II: {summary['appendix_ii_count']:,}")
            logger.info(f"  Appendix III: {summary['appendix_iii_count']:,}")
            
            # Validation checks
            expected_records = self.load_stats['successful_loads']
            actual_records = summary['total_records']
            
            if actual_records != expected_records:
                logger.error(f"Record count mismatch: expected {expected_records:,}, found {actual_records:,}")
                return False
            
            if summary['latest_year'] < 2023:
                logger.warning(f"Latest year is {summary['latest_year']}, expected 2024 data")
            
            logger.info("✅ Staging validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Error validating staging load: {e}")
            return False
    
    def generate_load_report(self) -> None:
        """Generate load report"""
        report = {
            'load_metadata': {
                'timestamp': datetime.now().isoformat(),
                'dry_run': self.dry_run,
                'batch_size': self.batch_size,
                'data_source': 'CITES v2025.1'
            },
            'load_statistics': self.load_stats,
            'data_quality': {
                'species_mapping_rate': f"{(self.load_stats['species_mapped']/max(1, self.load_stats['total_records']))*100:.1f}%",
                'load_success_rate': f"{(self.load_stats['successful_loads']/max(1, self.load_stats['species_mapped']))*100:.1f}%"
            },
            'next_steps': [
                'Run staging validation queries',
                'Compare staging data with current production',
                'Execute final migration when ready'
            ]
        }
        
        report_path = f"logs/staging_load_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Load report saved: {report_path}")

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load CITES v2025.1 data to staging')
    parser.add_argument('--csv-path', default='extracted_data/arctic_species_trade_data_v2025.csv', help='Path to extracted CSV')
    parser.add_argument('--batch-size', type=int, default=5000, help='Batch size for inserts')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    
    args = parser.parse_args()
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    loader = CitesStageLoader(dry_run=args.dry_run, batch_size=args.batch_size)
    
    try:
        # Load reference data
        loader.load_species_mapping()
        
        # Load extracted data
        df = loader.load_extracted_data(args.csv_path)
        
        # Map species IDs
        df = loader.map_species_ids(df)
        
        # Prepare staging records
        staging_records = loader.prepare_staging_records(df)
        
        # Clear staging table
        loader.clear_staging_table()
        
        # Load to staging
        loader.load_to_staging(staging_records)
        
        # Validate load
        if not args.dry_run:
            if not loader.validate_staging_load():
                logger.error("Staging validation failed")
                sys.exit(1)
        
        # Generate report
        loader.generate_load_report()
        
        logger.info("✅ Staging load completed successfully")
        
    except Exception as e:
        logger.error(f"Staging load failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()