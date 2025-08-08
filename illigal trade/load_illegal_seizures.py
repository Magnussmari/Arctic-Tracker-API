#!/usr/bin/env python3
"""
Load Illegal Trade Seizure Records
Arctic Tracker Database - Illegal Trade Integration

Loads 919 wildlife crime seizure records mapped to Arctic species
into the illegal_trade_seizures table.

Usage:
    python load_illegal_seizures.py [--dry-run] [--batch-size 100]
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Optional
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
        logging.FileHandler(f'logs/illegal_seizures_load_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IllegalSeizureLoader:
    """Loads seizure records into illegal_trade_seizures table"""
    
    def __init__(self, dry_run: bool = False, batch_size: int = 100):
        self.dry_run = dry_run
        self.batch_size = batch_size
        self.supabase = get_supabase_client()
        self.seizure_records = []
        self.product_id_mapping = {}
        self.species_mapping = {}
        self.load_stats = {
            'total_records': 0,
            'successful_loads': 0,
            'failed_loads': 0,
            'species_found': 0,
            'products_found': 0
        }
        
    def load_reference_data(self) -> None:
        """Load product and species mappings for foreign keys"""
        logger.info("Loading reference data...")
        
        try:
            # Load product mappings
            products_result = self.supabase.table('illegal_trade_products').select('id, product_code').execute()
            self.product_id_mapping = {
                product['product_code']: product['id'] 
                for product in products_result.data
            }
            logger.info(f"Loaded {len(self.product_id_mapping)} product mappings")
            
            # Load species mappings (Arctic species only)
            species_result = self.supabase.table('species').select('id, scientific_name').execute()
            self.species_mapping = {
                species['scientific_name']: species['id'] 
                for species in species_result.data
            }
            logger.info(f"Loaded {len(self.species_mapping)} species mappings")
            
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
            raise
    
    def load_seizure_data(self, csv_path: str) -> None:
        """Load and process seizure records from CSV"""
        logger.info(f"Loading seizure data from {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            self.load_stats['total_records'] = len(df)
            logger.info(f"Loaded {len(df)} seizure records")
            
            # Process each record
            for index, row in df.iterrows():
                try:
                    seizure_record = self._process_seizure_record(row, index)
                    if seizure_record:
                        self.seizure_records.append(seizure_record)
                        
                except Exception as e:
                    logger.warning(f"Error processing record {index}: {e}")
                    self.load_stats['failed_loads'] += 1
            
            logger.info(f"Successfully processed {len(self.seizure_records)} seizure records")
            self._log_processing_summary()
            
        except Exception as e:
            logger.error(f"Error loading seizure data: {e}")
            raise
    
    def _process_seizure_record(self, row: pd.Series, index: int) -> Optional[Dict]:
        """Process a single seizure record"""
        
        # Get species ID
        species_scientific_name = row.get('arctic_scientific_name')
        if not species_scientific_name or species_scientific_name not in self.species_mapping:
            logger.warning(f"Record {index}: Species not found - {species_scientific_name}")
            return None
        
        species_id = self.species_mapping[species_scientific_name]
        self.load_stats['species_found'] += 1
        
        # Get product type ID
        product_code = row.get('standardized_use_id')
        product_type_id = None
        if product_code and product_code in self.product_id_mapping:
            product_type_id = self.product_id_mapping[product_code]
            self.load_stats['products_found'] += 1
        
        # Build seizure record
        seizure_record = {
            'species_id': species_id,
            'source_database': self._clean_string(row.get('db', 'unknown')).upper(),
            'original_record_id': None,  # Not available in current dataset
            'seizure_date': None,  # Not available in current dataset
            'seizure_year': None,  # Not available in current dataset
            'seizure_location': None,  # Not available in current dataset
            'product_type_id': product_type_id,
            'product_category': self._map_product_category(row.get('main_category')),
            'quantity': self._safe_numeric(row.get('quantity')),
            'unit': self._clean_string(row.get('unit')),
            'reported_taxon_name': self._clean_string(row.get('db_taxa_name')),
            'gbif_id': self._clean_string(row.get('gbif_id')),
            'db_taxa_name_clean': self._clean_string(row.get('db_taxa_name_clean')),
            'data_source': 'Stringham et al. 2021'
        }
        
        return seizure_record
    
    def _clean_string(self, value) -> Optional[str]:
        """Clean and validate string values"""
        if pd.isna(value) or value == '' or str(value).lower() == 'nan':
            return None
        return str(value).strip()
    
    def _safe_numeric(self, value) -> Optional[float]:
        """Safely convert to numeric"""
        if pd.isna(value) or value == '' or str(value).lower() == 'nan':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _map_product_category(self, main_category: str) -> Optional[str]:
        """Map main category to standardized product category"""
        if not main_category:
            return None
            
        category_mapping = {
            'dead/raw': 'dead/raw',
            'processed/derived': 'processed/derived',
            'live': 'live'
        }
        
        return category_mapping.get(main_category.lower(), main_category)
    
    def _log_processing_summary(self) -> None:
        """Log summary of data processing"""
        logger.info("\n=== SEIZURE PROCESSING SUMMARY ===")
        logger.info(f"Total records processed: {self.load_stats['total_records']}")
        logger.info(f"Valid seizure records: {len(self.seizure_records)}")
        logger.info(f"Species mappings found: {self.load_stats['species_found']}")
        logger.info(f"Product mappings found: {self.load_stats['products_found']}")
        logger.info(f"Failed processing: {self.load_stats['failed_loads']}")
        
        # Species breakdown
        species_counts = {}
        for record in self.seizure_records:
            species_id = record['species_id']
            species_counts[species_id] = species_counts.get(species_id, 0) + 1
        
        logger.info(f"Unique species in seizures: {len(species_counts)}")
        
        # Find species with most seizures
        if species_counts:
            most_seized = max(species_counts.items(), key=lambda x: x[1])
            species_name = self._get_species_name_by_id(most_seized[0])
            logger.info(f"Most seized species: {species_name} ({most_seized[1]} seizures)")
    
    def _get_species_name_by_id(self, species_id: str) -> str:
        """Get species name by ID for logging"""
        for name, id_val in self.species_mapping.items():
            if id_val == species_id:
                return name
        return f"ID:{species_id}"
    
    def validate_existing_data(self) -> bool:
        """Check if seizures table already has data"""
        try:
            result = self.supabase.table('illegal_trade_seizures').select('count', count='exact').execute()
            existing_count = result.count
            
            if existing_count > 0:
                logger.warning(f"illegal_trade_seizures table already contains {existing_count} records")
                response = input("Continue and add to existing data? [y/N]: ")
                return response.lower() == 'y'
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking existing data: {e}")
            return False
    
    def load_seizures_to_database(self) -> None:
        """Load seizure records into database"""
        if self.dry_run:
            logger.info("DRY RUN: Would load the following seizures:")
            for i, record in enumerate(self.seizure_records[:5]):  # Show first 5
                species_name = self._get_species_name_by_id(record['species_id'])
                logger.info(f"  {i+1}. {species_name} - {record['reported_taxon_name']}")
            logger.info(f"  ... and {len(self.seizure_records) - 5} more seizures")
            return
        
        try:
            logger.info(f"Loading {len(self.seizure_records)} seizures to database...")
            
            # Insert in batches
            successful_inserts = 0
            batch_num = 0
            
            for i in range(0, len(self.seizure_records), self.batch_size):
                batch = self.seizure_records[i:i + self.batch_size]
                batch_num += 1
                
                try:
                    result = self.supabase.table('illegal_trade_seizures').insert(batch).execute()
                    successful_inserts += len(batch)
                    logger.info(f"Inserted batch {batch_num}: {len(batch)} seizures")
                    
                except Exception as e:
                    logger.error(f"Error inserting batch {batch_num}: {e}")
                    # Continue with next batch rather than failing completely
                    self.load_stats['failed_loads'] += len(batch)
            
            self.load_stats['successful_loads'] = successful_inserts
            logger.info(f"Successfully loaded {successful_inserts} seizure records")
            
            # Verify the load
            self._verify_load()
            
        except Exception as e:
            logger.error(f"Error loading seizures to database: {e}")
            raise
    
    def _verify_load(self) -> None:
        """Verify the seizures were loaded correctly"""
        try:
            result = self.supabase.table('illegal_trade_seizures').select('count', count='exact').execute()
            loaded_count = result.count
            
            logger.info(f"Verification: {loaded_count} seizures in database")
            
            # Check species distribution
            species_result = self.supabase.table('illegal_trade_seizures') \
                .select('species_id', count='exact') \
                .execute()
            
            if species_result.data:
                unique_species = len(set(record['species_id'] for record in species_result.data))
                logger.info(f"✓ Seizures cover {unique_species} unique species")
            
            # Check product mappings
            product_result = self.supabase.table('illegal_trade_seizures') \
                .select('product_type_id', count='exact') \
                .is_('product_type_id', 'not.null') \
                .execute()
            
            products_mapped = product_result.count
            logger.info(f"✓ {products_mapped} seizures have product mappings")
            
            logger.info("✓ Seizure load verification completed")
                    
        except Exception as e:
            logger.error(f"Error verifying load: {e}")
    
    def generate_load_report(self) -> None:
        """Generate comprehensive load report"""
        # Analyze loaded data for report
        species_breakdown = {}
        product_breakdown = {}
        source_breakdown = {}
        
        for record in self.seizure_records:
            # Species breakdown
            species_id = record['species_id']
            species_name = self._get_species_name_by_id(species_id)
            species_breakdown[species_name] = species_breakdown.get(species_name, 0) + 1
            
            # Product breakdown
            if record['product_type_id']:
                product_id = record['product_type_id']
                product_breakdown[product_id] = product_breakdown.get(product_id, 0) + 1
            
            # Source breakdown
            source = record['source_database']
            source_breakdown[source] = source_breakdown.get(source, 0) + 1
        
        report = {
            'load_timestamp': datetime.now().isoformat(),
            'load_summary': self.load_stats,
            'dry_run': self.dry_run,
            'batch_size': self.batch_size,
            'species_breakdown': dict(sorted(species_breakdown.items(), key=lambda x: x[1], reverse=True)),
            'source_breakdown': source_breakdown,
            'data_quality': {
                'records_with_species_mapping': self.load_stats['species_found'],
                'records_with_product_mapping': self.load_stats['products_found'],
                'species_mapping_rate': f"{(self.load_stats['species_found']/max(1, len(self.seizure_records)))*100:.1f}%",
                'product_mapping_rate': f"{(self.load_stats['products_found']/max(1, len(self.seizure_records)))*100:.1f}%"
            }
        }
        
        # Save report
        report_path = f"logs/illegal_seizures_load_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Load report saved to: {report_path}")

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load illegal trade seizure records')
    parser.add_argument('--dry-run', action='store_true', help='Run without making database changes')
    parser.add_argument('--csv-path', default='arctic_illegal_trade_records.csv', help='Path to CSV file')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for database inserts')
    
    args = parser.parse_args()
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    loader = IllegalSeizureLoader(dry_run=args.dry_run, batch_size=args.batch_size)
    
    try:
        # Load reference data first
        loader.load_reference_data()
        
        # Load and process seizure data
        loader.load_seizure_data(args.csv_path)
        
        # Validate before loading
        if not args.dry_run:
            if not loader.validate_existing_data():
                logger.info("Load cancelled by user")
                return
        
        # Load seizures
        loader.load_seizures_to_database()
        
        # Generate report
        loader.generate_load_report()
        
        logger.info("✓ Illegal trade seizures load completed successfully")
        
    except Exception as e:
        logger.error(f"Load failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()