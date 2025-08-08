#!/usr/bin/env python3
"""
Load Illegal Trade Product Types
Arctic Tracker Database - Illegal Trade Integration

Extracts unique product types from illegal trade data and loads them
into the illegal_trade_products lookup table.

Usage:
    python load_illegal_products.py [--dry-run]
"""

import sys
import os
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Set
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.supabase_config import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/illegal_products_load_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IllegalProductLoader:
    """Loads standardized product types into illegal_trade_products table"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.supabase = get_supabase_client()
        self.products_data = []
        
        # High-value product categories (based on analysis)
        self.high_value_products = {
            'ivory product', 'ivory carvings/products', 'tusk', 'ivory',
            'bone product', 'horn', 'antler', 'carvings', 'jewelry',
            'live specimen', 'pet/display animal'
        }
        
    def load_product_data(self, csv_path: str) -> None:
        """Load and analyze product types from CSV"""
        logger.info(f"Loading illegal trade data from {csv_path}")
        
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} seizure records")
            
            # Extract unique product combinations
            product_combinations = df.groupby([
                'standardized_use_id', 
                'standardized_use_type',
                'subcategory',
                'main_category'
            ]).size().reset_index(name='seizure_count')
            
            logger.info(f"Found {len(product_combinations)} unique product types")
            
            # Process each unique product type
            for _, row in product_combinations.iterrows():
                product_data = {
                    'product_code': row['standardized_use_id'],
                    'product_name': row['standardized_use_type'],
                    'product_category': row['subcategory'],
                    'main_category': row['main_category'],
                    'is_high_value': self._is_high_value_product(row['standardized_use_type'], row['subcategory']),
                    'search_terms': self._generate_search_terms(row['standardized_use_type'], row['subcategory']),
                    'seizure_count': int(row['seizure_count'])  # For validation
                }
                self.products_data.append(product_data)
                
            # Sort by seizure count for logging
            self.products_data.sort(key=lambda x: x['seizure_count'], reverse=True)
            
            logger.info(f"Processed {len(self.products_data)} unique product types")
            self._log_product_summary()
            
        except Exception as e:
            logger.error(f"Error loading product data: {e}")
            raise
    
    def _is_high_value_product(self, product_name: str, subcategory: str) -> bool:
        """Determine if product is high-value based on name and category"""
        product_lower = product_name.lower()
        subcategory_lower = subcategory.lower() if subcategory else ""
        
        for high_value_term in self.high_value_products:
            if high_value_term in product_lower or high_value_term in subcategory_lower:
                return True
        return False
    
    def _generate_search_terms(self, product_name: str, subcategory: str) -> List[str]:
        """Generate search terms for product optimization"""
        terms = set()
        
        # Add main product name words
        if product_name:
            terms.update(product_name.lower().split())
        
        # Add subcategory words
        if subcategory and subcategory != product_name:
            terms.update(subcategory.lower().split())
        
        # Remove common stop words
        stop_words = {'and', 'or', 'the', 'of', 'in', 'for', 'with', 'to', 'from'}
        terms = terms - stop_words
        
        return list(terms)
    
    def _log_product_summary(self) -> None:
        """Log summary of product types"""
        logger.info("\n=== PRODUCT TYPE SUMMARY ===")
        
        # Count by main category
        category_counts = {}
        high_value_count = 0
        
        for product in self.products_data:
            category = product['main_category']
            category_counts[category] = category_counts.get(category, 0) + 1
            if product['is_high_value']:
                high_value_count += 1
        
        logger.info(f"By main category:")
        for category, count in category_counts.items():
            logger.info(f"  {category}: {count} products")
        
        logger.info(f"High-value products: {high_value_count}")
        
        # Log top 10 most seized products
        logger.info(f"\nTop 10 most seized product types:")
        for i, product in enumerate(self.products_data[:10]):
            logger.info(f"  {i+1}. {product['product_name']}: {product['seizure_count']} seizures")
    
    def validate_existing_data(self) -> bool:
        """Check if products table already has data"""
        try:
            result = self.supabase.table('illegal_trade_products').select('count', count='exact').execute()
            existing_count = result.count
            
            if existing_count > 0:
                logger.warning(f"illegal_trade_products table already contains {existing_count} records")
                response = input("Continue and overwrite existing data? [y/N]: ")
                return response.lower() == 'y'
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking existing data: {e}")
            return False
    
    def clear_existing_data(self) -> None:
        """Clear existing product data"""
        if not self.dry_run:
            try:
                logger.info("Clearing existing illegal_trade_products data...")
                result = self.supabase.table('illegal_trade_products').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                logger.info("Existing data cleared")
            except Exception as e:
                logger.error(f"Error clearing existing data: {e}")
                raise
    
    def load_products_to_database(self) -> None:
        """Load product types into database"""
        if self.dry_run:
            logger.info("DRY RUN: Would load the following products:")
            for product in self.products_data[:5]:  # Show first 5
                logger.info(f"  {product['product_code']}: {product['product_name']}")
            logger.info(f"  ... and {len(self.products_data) - 5} more products")
            return
        
        try:
            logger.info(f"Loading {len(self.products_data)} products to database...")
            
            # Prepare data for insertion (remove seizure_count as it's not in schema)
            insert_data = []
            for product in self.products_data:
                insert_record = {k: v for k, v in product.items() if k != 'seizure_count'}
                insert_data.append(insert_record)
            
            # Insert in batches
            batch_size = 50
            successful_inserts = 0
            
            for i in range(0, len(insert_data), batch_size):
                batch = insert_data[i:i + batch_size]
                
                try:
                    result = self.supabase.table('illegal_trade_products').insert(batch).execute()
                    successful_inserts += len(batch)
                    logger.info(f"Inserted batch {i//batch_size + 1}: {len(batch)} products")
                    
                except Exception as e:
                    logger.error(f"Error inserting batch {i//batch_size + 1}: {e}")
                    raise
            
            logger.info(f"Successfully loaded {successful_inserts} product types")
            
            # Verify the load
            self._verify_load()
            
        except Exception as e:
            logger.error(f"Error loading products to database: {e}")
            raise
    
    def _verify_load(self) -> None:
        """Verify the products were loaded correctly"""
        try:
            result = self.supabase.table('illegal_trade_products').select('count', count='exact').execute()
            loaded_count = result.count
            
            logger.info(f"Verification: {loaded_count} products in database")
            
            if loaded_count != len(self.products_data):
                logger.warning(f"Count mismatch: Expected {len(self.products_data)}, found {loaded_count}")
            else:
                logger.info("✓ Product count verification passed")
            
            # Test a few specific products
            test_products = ['u_id_065', 'u_id_055', 'u_id_023']  # Common product codes
            for code in test_products:
                result = self.supabase.table('illegal_trade_products').select('*').eq('product_code', code).execute()
                if result.data:
                    product = result.data[0]
                    logger.info(f"✓ Found {code}: {product['product_name']}")
                else:
                    logger.warning(f"✗ Missing product code: {code}")
                    
        except Exception as e:
            logger.error(f"Error verifying load: {e}")
    
    def generate_load_report(self) -> None:
        """Generate summary report"""
        report = {
            'load_timestamp': datetime.now().isoformat(),
            'total_products_loaded': len(self.products_data),
            'dry_run': self.dry_run,
            'product_categories': {},
            'high_value_products': 0,
            'top_10_products': []
        }
        
        # Category breakdown
        for product in self.products_data:
            category = product['main_category']
            report['product_categories'][category] = report['product_categories'].get(category, 0) + 1
            if product['is_high_value']:
                report['high_value_products'] += 1
        
        # Top 10 products
        report['top_10_products'] = [
            {
                'code': p['product_code'],
                'name': p['product_name'],
                'category': p['main_category'],
                'seizure_count': p['seizure_count'],
                'high_value': p['is_high_value']
            }
            for p in self.products_data[:10]
        ]
        
        # Save report
        report_path = f"logs/illegal_products_load_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Load report saved to: {report_path}")

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load illegal trade product types')
    parser.add_argument('--dry-run', action='store_true', help='Run without making database changes')
    parser.add_argument('--csv-path', default='arctic_illegal_trade_records.csv', help='Path to CSV file')
    
    args = parser.parse_args()
    
    # Ensure logs directory exists
    os.makedirs('logs', exist_ok=True)
    
    loader = IllegalProductLoader(dry_run=args.dry_run)
    
    try:
        # Load and process data
        loader.load_product_data(args.csv_path)
        
        # Validate before loading
        if not args.dry_run:
            if not loader.validate_existing_data():
                logger.info("Load cancelled by user")
                return
            
            # Clear existing data if confirmed
            loader.clear_existing_data()
        
        # Load products
        loader.load_products_to_database()
        
        # Generate report
        loader.generate_load_report()
        
        logger.info("✓ Illegal trade products load completed successfully")
        
    except Exception as e:
        logger.error(f"Load failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()