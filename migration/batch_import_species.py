#!/usr/bin/env python3
"""
Batch Species Profile Import Script

This script processes multiple species profile JSON files in batch.
Designed to handle all 42 Arctic species in the database.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import time

# Add parent directory to path for importing modules
sys.path.append(str(Path(__file__).parent.parent))

# Import the single species import functions
from import_species_json import (
    supabase, 
    process_species_json,
    load_json_file
)

# Configuration
PROCESSED_DIR = Path("species_data/scite/processed")
LOG_FILE = Path("migration/batch_import_log.txt")

def log_message(message: str, also_print: bool = True):
    """Log message to file and optionally print"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    if also_print:
        print(log_entry)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry + '\n')

def get_all_species_from_db() -> List[Dict[str, Any]]:
    """Get all species from database for reference"""
    try:
        response = supabase.table('species').select('id, scientific_name, common_name').execute()
        return response.data or []
    except Exception as e:
        log_message(f"❌ Error fetching species from database: {e}")
        return []

def find_json_files() -> List[Path]:
    """Find all JSON files in the processed directory"""
    if not PROCESSED_DIR.exists():
        log_message(f"❌ Processed directory not found: {PROCESSED_DIR}")
        return []
    
    json_files = list(PROCESSED_DIR.glob("*.json"))
    log_message(f"📁 Found {len(json_files)} JSON files in {PROCESSED_DIR}")
    
    return json_files

def validate_json_file(json_file: Path) -> bool:
    """Validate that JSON file has required structure"""
    try:
        data = load_json_file(json_file)
        
        # Check required top-level keys
        required_keys = ['species_data', 'conservation_profile', 'references']
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            log_message(f"  ❌ Missing required keys in {json_file.name}: {missing_keys}")
            return False
        
        # Check species_data has scientific_name
        if not data['species_data'].get('scientific_name'):
            log_message(f"  ❌ Missing scientific_name in {json_file.name}")
            return False
        
        log_message(f"  ✅ Valid JSON structure: {json_file.name}")
        return True
        
    except Exception as e:
        log_message(f"  ❌ Error validating {json_file.name}: {e}")
        return False

def process_batch(json_files: List[Path], dry_run: bool = False) -> Dict[str, Any]:
    """Process all JSON files in batch"""
    results = {
        'total_files': len(json_files),
        'successful': 0,
        'failed': 0,
        'skipped': 0,
        'errors': [],
        'processed_species': []
    }
    
    log_message(f"\n🚀 Starting batch processing of {len(json_files)} files")
    log_message(f"📋 Dry run mode: {dry_run}")
    
    for i, json_file in enumerate(json_files, 1):
        log_message(f"\n📄 Processing file {i}/{len(json_files)}: {json_file.name}")
        
        try:
            # Validate file structure
            if not validate_json_file(json_file):
                results['skipped'] += 1
                continue
            
            # Load JSON data
            json_data = load_json_file(json_file)
            if not json_data:
                log_message(f"  ❌ Failed to load JSON data from {json_file.name}")
                results['failed'] += 1
                continue
            
            scientific_name = json_data['species_data'].get('scientific_name', 'Unknown')
            log_message(f"  🎯 Target species: {scientific_name}")
            
            if dry_run:
                log_message(f"  🔍 DRY RUN: Would process {scientific_name}")
                results['successful'] += 1
                results['processed_species'].append(scientific_name)
            else:
                # Process the species
                success = process_species_json(json_data)
                
                if success:
                    log_message(f"  ✅ Successfully processed: {scientific_name}")
                    results['successful'] += 1
                    results['processed_species'].append(scientific_name)
                else:
                    log_message(f"  ❌ Failed to process: {scientific_name}")
                    results['failed'] += 1
                    results['errors'].append(f"{json_file.name}: {scientific_name}")
            
            # Small delay between processing to avoid overwhelming the database
            if not dry_run:
                time.sleep(1)
                
        except Exception as e:
            log_message(f"  ❌ Unexpected error processing {json_file.name}: {e}")
            results['failed'] += 1
            results['errors'].append(f"{json_file.name}: {str(e)}")
    
    return results

def generate_species_list() -> List[str]:
    """Generate list of all 42 species scientific names from database"""
    species_list = get_all_species_from_db()
    scientific_names = [s['scientific_name'] for s in species_list]
    
    log_message(f"\n📊 Found {len(scientific_names)} species in database:")
    for i, name in enumerate(sorted(scientific_names), 1):
        log_message(f"  {i:2d}. {name}")
    
    return scientific_names

def create_missing_files_report(processed_species: List[str]) -> None:
    """Create report of species that still need JSON files"""
    all_species = [s['scientific_name'] for s in get_all_species_from_db()]
    missing_species = [s for s in all_species if s not in processed_species]
    
    if missing_species:
        log_message(f"\n📋 Species still needing JSON profiles ({len(missing_species)}):")
        for i, species in enumerate(sorted(missing_species), 1):
            log_message(f"  {i:2d}. {species}")
        
        # Save to file for reference
        missing_file = Path("species_data/scite/missing_profiles.txt")
        with open(missing_file, 'w', encoding='utf-8') as f:
            f.write("# Species Still Needing JSON Profiles\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for species in sorted(missing_species):
                f.write(f"{species}\n")
        
        log_message(f"📄 Missing species list saved to: {missing_file}")
    else:
        log_message(f"\n🎉 All species have been processed!")

def print_summary(results: Dict[str, Any]) -> None:
    """Print final summary of batch processing"""
    log_message(f"\n" + "="*60)
    log_message(f"📊 BATCH PROCESSING SUMMARY")
    log_message(f"="*60)
    log_message(f"📁 Total files found: {results['total_files']}")
    log_message(f"✅ Successfully processed: {results['successful']}")
    log_message(f"❌ Failed to process: {results['failed']}")
    log_message(f"⚠️  Skipped (invalid): {results['skipped']}")
    
    if results['errors']:
        log_message(f"\n❌ Errors encountered:")
        for error in results['errors']:
            log_message(f"  - {error}")
    
    if results['processed_species']:
        log_message(f"\n✅ Successfully processed species:")
        for species in sorted(results['processed_species']):
            log_message(f"  - {species}")

def main():
    """Main batch processing function"""
    # Initialize log file
    log_message("🚀 Starting Arctic Tracker Species Batch Import", also_print=True)
    log_message(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Parse command line arguments
    dry_run = '--dry-run' in sys.argv
    list_species = '--list-species' in sys.argv
    
    if list_species:
        log_message("📋 Generating species list from database...")
        generate_species_list()
        return
    
    # Find JSON files
    json_files = find_json_files()
    if not json_files:
        log_message("❌ No JSON files found to process")
        return
    
    # Process files
    results = process_batch(json_files, dry_run=dry_run)
    
    # Print summary
    print_summary(results)
    
    # Create missing files report
    create_missing_files_report(results['processed_species'])
    
    log_message(f"\n📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_message(f"📄 Full log saved to: {LOG_FILE}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
        print("""
Arctic Tracker Species Batch Import

Usage:
  python migration/batch_import_species.py [options]

Options:
  --dry-run        Validate files without importing to database
  --list-species   List all species in database and exit
  --help, -h       Show this help message

Examples:
  # Dry run to validate all JSON files
  python migration/batch_import_species.py --dry-run
  
  # Import all valid JSON files to database
  python migration/batch_import_species.py
  
  # List all species in database
  python migration/batch_import_species.py --list-species

Files:
  Input:  species_data/scite/processed/*.json
  Log:    migration/batch_import_log.txt
  Report: species_data/scite/missing_profiles.txt
        """)
    else:
        main()
