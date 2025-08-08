#!/usr/bin/env python3
"""
Upload Species Profiles to Database

This script cycles through species JSON files and uploads only those with research data,
avoiding duplication and providing detailed progress tracking.

Features:
- Detects empty templates vs. files with data
- Avoids duplicate uploads
- Tracks upload progress and errors
- Validates data before upload
- Creates comprehensive upload report
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.supabase_config import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/species_upload_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SpeciesProfileUploader:
    def __init__(self, dry_run: bool = False):
        """
        Initialize the uploader.
        
        Args:
            dry_run: If True, only validate and report, don't actually upload
        """
        self.dry_run = dry_run
        self.client = get_supabase_client(use_service_role=True)
        self.processed_dir = Path("/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/species_data/scite/processed")
        
        # Track statistics
        self.stats = {
            'total_files': 0,
            'empty_templates': 0,
            'files_with_data': 0,
            'already_uploaded': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'errors': []
        }
        
        # Track processed species to avoid duplicates
        self.processed_species = set()
    
    def is_empty_template(self, json_data: Dict) -> bool:
        """
        Determine if a JSON file is an empty template or contains real data.
        
        Args:
            json_data: The loaded JSON data
            
        Returns:
            True if this is an empty template, False if it contains research data
        """
        # Check for empty template markers
        if 'metadata' in json_data and isinstance(json_data['metadata'], dict):
            notes = json_data['metadata'].get('notes', '')
            if 'Empty template' in notes:
                return True
        
        # Check for data structure patterns
        if 'species_data' in json_data:
            # This is a research data file (like narwhal.json)
            species_data = json_data['species_data']
            
            # Check if it has substantial content
            if (species_data.get('description') and 
                len(species_data.get('description', '')) > 100):
                return False
            
            # Check for other substantial fields
            if (species_data.get('habitat_description') and 
                len(species_data.get('habitat_description', '')) > 50):
                return False
        
        elif 'species' in json_data:
            # This is likely an empty template
            species = json_data['species']
            
            # Check if basic fields are empty
            if (not species.get('common_name') and 
                not species.get('taxonomic_info', {}).get('kingdom')):
                return True
        
        return True
    
    def check_if_already_uploaded(self, scientific_name: str) -> bool:
        """
        Check if species profile already exists in database.
        
        Args:
            scientific_name: The scientific name to check
            
        Returns:
            True if already exists, False otherwise
        """
        try:
            # Check if species exists with conservation profile
            response = self.client.table('species').select('id, scientific_name').eq('scientific_name', scientific_name).execute()
            
            if response.data:
                species_id = response.data[0]['id']
                
                # Check if conservation profile exists
                profile_response = self.client.table('conservation_profiles').select('id').eq('species_id', species_id).execute()
                
                if profile_response.data:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if {scientific_name} already uploaded: {e}")
            return False
    
    def validate_species_data(self, json_data: Dict) -> Tuple[bool, List[str]]:
        """
        Validate species data before upload.
        
        Args:
            json_data: The JSON data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check for required fields
        if 'species_data' in json_data:
            species_data = json_data['species_data']
            
            if not species_data.get('scientific_name'):
                errors.append("Missing scientific_name")
            
            if not species_data.get('common_name'):
                errors.append("Missing common_name")
        
        elif 'species' in json_data:
            species = json_data['species']
            
            if not species.get('scientific_name'):
                errors.append("Missing scientific_name")
        
        else:
            errors.append("No species data found in JSON")
        
        # Check for conservation profile
        if 'conservation_profile' not in json_data and 'conservation_status' not in json_data:
            errors.append("No conservation information found")
        
        return len(errors) == 0, errors
    
    def upload_species_profile(self, json_data: Dict, filepath: Path) -> bool:
        """
        Upload a species profile to the database.
        
        Args:
            json_data: The JSON data to upload
            filepath: Path to the source file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.dry_run:
                logger.info(f"[DRY RUN] Would upload: {filepath.name}")
                return True
            
            # Extract species data
            if 'species_data' in json_data:
                species_data = json_data['species_data']
                scientific_name = species_data['scientific_name']
                
                # Get species ID first
                species_response = self.client.table('species').select('id').eq('scientific_name', scientific_name).execute()
                
                if not species_response.data:
                    logger.error(f"Species not found in database: {scientific_name}")
                    return False
                
                species_id = species_response.data[0]['id']
                
                # Update species table with enhanced data from JSON
                species_update = {
                    'common_name': species_data.get('common_name', ''),
                    'description': species_data.get('description', ''),
                    'habitat_description': species_data.get('habitat_description', ''),
                    'population_size': species_data.get('population_size', ''),
                    'population_trend': species_data.get('population_trend', ''),
                    'generation_length': species_data.get('generation_length'),
                    'movement_patterns': species_data.get('movement_patterns', ''),
                    'use_and_trade': species_data.get('use_and_trade', ''),
                    'threats_overview': species_data.get('threats_overview', ''),
                    'conservation_overview': species_data.get('conservation_overview', '')
                }
                
                # Update existing species record
                self.client.table('species').update(species_update).eq('id', species_id).execute()
                
                logger.info(f"✅ Successfully uploaded: {scientific_name}")
                return True
                
            else:
                logger.warning(f"⚠️  Unsupported data format: {filepath.name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to upload {filepath.name}: {e}")
            self.stats['errors'].append(f"{filepath.name}: {str(e)}")
            return False
    
    def process_all_files(self):
        """Process all JSON files in the processed directory."""
        logger.info("Starting species profile upload process...")
        logger.info(f"Processing directory: {self.processed_dir}")
        logger.info(f"Dry run mode: {self.dry_run}")
        
        # Get all JSON files
        json_files = list(self.processed_dir.glob("*.json"))
        self.stats['total_files'] = len(json_files)
        
        logger.info(f"Found {len(json_files)} JSON files")
        
        for filepath in sorted(json_files):
            logger.info(f"\n--- Processing: {filepath.name} ---")
            
            try:
                # Load JSON data
                with open(filepath, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # Check if it's an empty template
                if self.is_empty_template(json_data):
                    logger.info(f"⏭️  Skipping empty template: {filepath.name}")
                    self.stats['empty_templates'] += 1
                    continue
                
                self.stats['files_with_data'] += 1
                
                # Extract scientific name
                scientific_name = None
                if 'species_data' in json_data:
                    scientific_name = json_data['species_data'].get('scientific_name')
                elif 'species' in json_data:
                    scientific_name = json_data['species'].get('scientific_name')
                
                if not scientific_name:
                    logger.warning(f"⚠️  No scientific name found in: {filepath.name}")
                    continue
                
                # Check for duplicates
                if scientific_name in self.processed_species:
                    logger.warning(f"⚠️  Duplicate species in this session: {scientific_name}")
                    continue
                
                # Check if already uploaded
                if self.check_if_already_uploaded(scientific_name):
                    logger.info(f"⏭️  Already uploaded: {scientific_name}")
                    self.stats['already_uploaded'] += 1
                    continue
                
                # Validate data
                is_valid, errors = self.validate_species_data(json_data)
                if not is_valid:
                    logger.error(f"❌ Validation failed for {filepath.name}: {errors}")
                    self.stats['failed_uploads'] += 1
                    continue
                
                # Upload the profile
                if self.upload_species_profile(json_data, filepath):
                    self.stats['successful_uploads'] += 1
                    self.processed_species.add(scientific_name)
                else:
                    self.stats['failed_uploads'] += 1
                    
            except Exception as e:
                logger.error(f"❌ Error processing {filepath.name}: {e}")
                self.stats['failed_uploads'] += 1
                self.stats['errors'].append(f"{filepath.name}: {str(e)}")
    
    def print_summary(self):
        """Print upload summary statistics."""
        logger.info("\n" + "="*60)
        logger.info("UPLOAD SUMMARY")
        logger.info("="*60)
        logger.info(f"Total JSON files found: {self.stats['total_files']}")
        logger.info(f"Empty templates (skipped): {self.stats['empty_templates']}")
        logger.info(f"Files with research data: {self.stats['files_with_data']}")
        logger.info(f"Already uploaded (skipped): {self.stats['already_uploaded']}")
        logger.info(f"Successful uploads: {self.stats['successful_uploads']}")
        logger.info(f"Failed uploads: {self.stats['failed_uploads']}")
        
        if self.stats['errors']:
            logger.info(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                logger.info(f"  - {error}")
        
        logger.info(f"\nMode: {'DRY RUN' if self.dry_run else 'LIVE UPLOAD'}")
        logger.info("="*60)

def main():
    """Main function to run the upload process."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload species profiles to database')
    parser.add_argument('--dry-run', action='store_true', help='Run validation only, no actual uploads')
    parser.add_argument('--force', action='store_true', help='Upload even if already exists (updates)')
    
    args = parser.parse_args()
    
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    # Create uploader and process files
    uploader = SpeciesProfileUploader(dry_run=args.dry_run)
    uploader.process_all_files()
    uploader.print_summary()

if __name__ == "__main__":
    main()