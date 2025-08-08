#!/usr/bin/env python3
"""
Load CMS Data to Database Script

This script loads the processed CMS species data into the Supabase database.

Usage:
    python load_cms_data_to_db.py [--dry-run]
"""

import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config.supabase_config import get_supabase_client

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cms_data_load.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CMSDataLoader:
    """Load CMS data into the Supabase database"""
    
    def __init__(self, dry_run: bool = False):
        # Use service role key to bypass RLS policies
        self.supabase = get_supabase_client(use_service_role=True)
        self.dry_run = dry_run
        self.base_dir = Path(__file__).parent.parent.parent  # Go up to API root
        self.cms_data_file = self.base_dir / "species_data" / "processed" / "cms_arctic_species_data.json"
        
        # Statistics
        self.stats = {
            'species_found': 0,
            'species_not_found': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'errors': 0
        }
        
    def load_cms_data(self) -> Dict:
        """Load CMS data from JSON file"""
        try:
            with open(self.cms_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            logger.info(f"Loaded CMS data with {len(data['species_data'])} species")
            return data
            
        except Exception as e:
            logger.error(f"Error loading CMS data file: {e}")
            raise
            
    def get_species_id(self, scientific_name: str) -> Optional[str]:
        """Get species ID from database by scientific name"""
        try:
            response = self.supabase.table('species').select('id').eq('scientific_name', scientific_name).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            else:
                logger.warning(f"Species not found in database: {scientific_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error querying species {scientific_name}: {e}")
            return None
            
    def check_existing_cms_listing(self, species_id: str) -> Optional[Dict]:
        """Check if CMS listing already exists for species"""
        try:
            response = self.supabase.table('cms_listings').select('*').eq('species_id', species_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error checking existing CMS listing: {e}")
            return None
            
    def prepare_cms_record(self, species_data: Dict, species_id: str) -> Dict:
        """Prepare CMS record for database insertion"""
        return {
            'species_id': species_id,
            'appendix': species_data['cms_listing'],
            'agreement': species_data['agreement'],
            'listed_under': species_data['listed_under'],
            'listing_date': species_data['date_listed'],
            'notes': species_data['notes'] if species_data['notes'] else None,
            'native_distribution': species_data['native_distribution'],
            'distribution_codes': species_data['all_distribution_codes'],
            'introduced_distribution': species_data['introduced_distribution'],
            'extinct_distribution': species_data['extinct_distribution'],
            'distribution_uncertain': species_data['distribution_uncertain']
        }
        
    def insert_cms_listing(self, cms_record: Dict) -> bool:
        """Insert CMS listing into database"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would insert CMS listing for species_id: {cms_record['species_id']}")
            return True
            
        try:
            response = self.supabase.table('cms_listings').insert(cms_record).execute()
            
            if response.data:
                logger.info(f"Inserted CMS listing for species_id: {cms_record['species_id']}")
                return True
            else:
                logger.error(f"Failed to insert CMS listing for species_id: {cms_record['species_id']}")
                return False
                
        except Exception as e:
            logger.error(f"Error inserting CMS listing: {e}")
            return False
            
    def update_cms_listing(self, listing_id: str, cms_record: Dict) -> bool:
        """Update existing CMS listing"""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update CMS listing {listing_id}")
            return True
            
        try:
            # Remove species_id from update as it shouldn't change
            update_data = {k: v for k, v in cms_record.items() if k != 'species_id'}
            update_data['updated_at'] = datetime.now().isoformat()
            
            response = self.supabase.table('cms_listings').update(update_data).eq('id', listing_id).execute()
            
            if response.data:
                logger.info(f"Updated CMS listing {listing_id}")
                return True
            else:
                logger.error(f"Failed to update CMS listing {listing_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating CMS listing: {e}")
            return False
            
    def process_species(self, species_data: Dict) -> None:
        """Process a single species CMS data"""
        scientific_name = species_data['species_name']
        
        # Get species ID from database
        species_id = self.get_species_id(scientific_name)
        
        if not species_id:
            self.stats['species_not_found'] += 1
            return
            
        self.stats['species_found'] += 1
        
        # Check if CMS listing already exists
        existing_listing = self.check_existing_cms_listing(species_id)
        
        # Prepare CMS record
        cms_record = self.prepare_cms_record(species_data, species_id)
        
        if existing_listing:
            # Update existing record
            success = self.update_cms_listing(existing_listing['id'], cms_record)
            if success:
                self.stats['records_updated'] += 1
            else:
                self.stats['errors'] += 1
        else:
            # Insert new record
            success = self.insert_cms_listing(cms_record)
            if success:
                self.stats['records_inserted'] += 1
            else:
                self.stats['errors'] += 1
                
    def run(self) -> None:
        """Execute the CMS data loading pipeline"""
        logger.info(f"Starting CMS data load {'[DRY RUN]' if self.dry_run else ''}")
        
        # Load CMS data
        cms_data = self.load_cms_data()
        
        # Process each species
        for species_data in cms_data['species_data']:
            self.process_species(species_data)
            
        # Print summary
        self.print_summary()
        
    def print_summary(self) -> None:
        """Print processing summary"""
        print(f"\n{'='*60}")
        print(f"CMS DATA LOAD SUMMARY {'[DRY RUN]' if self.dry_run else ''}")
        print(f"{'='*60}")
        print(f"Species found in database: {self.stats['species_found']}")
        print(f"Species not found in database: {self.stats['species_not_found']}")
        print(f"Records inserted: {self.stats['records_inserted']}")
        print(f"Records updated: {self.stats['records_updated']}")
        print(f"Errors: {self.stats['errors']}")
        print(f"{'='*60}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Load CMS data into Supabase database')
    parser.add_argument('--dry-run', action='store_true', help='Run without making database changes')
    
    args = parser.parse_args()
    
    loader = CMSDataLoader(dry_run=args.dry_run)
    loader.run()


if __name__ == "__main__":
    main()