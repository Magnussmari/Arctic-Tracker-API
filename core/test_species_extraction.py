#!/usr/bin/env python3
"""
Test Species Trade Data Extraction

This is a test version that processes only a few trade files to validate the approach.
"""

import csv
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_extraction():
    """Test the extraction process with a small dataset"""
    
    # Paths
    species_file = "/Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/docs/reports/species_names_20250524_173653.csv"
    trade_dir = "/Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/species_data/raw_data/Trade_full"
    output_dir = "/Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/species_data/processed/test_output"
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Load a few species from the list
    species_set = set()
    with open(species_file, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for i, row in enumerate(reader):
            if i >= 10:  # Only test with first 10 species
                break
            scientific_name = row.get('scientific_name', '').strip()
            if scientific_name:
                species_set.add(scientific_name)
    
    logger.info(f"Testing with {len(species_set)} species: {species_set}")
    
    # Process only first 3 trade files
    trade_files = sorted(Path(trade_dir).glob('trade_db_*.csv'))[:3]
    species_data = defaultdict(list)
    
    for trade_file in trade_files:
        logger.info(f"Processing {trade_file.name}...")
        
        try:
            with open(trade_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row_num, row in enumerate(reader, 1):
                    taxon = row.get('Taxon', '').strip()
                    
                    if taxon in species_set:
                        # Process this record
                        trade_record = {
                            'id': row.get('Id', ''),
                            'year': row.get('Year', ''),
                            'taxon': taxon,
                            'quantity': row.get('Quantity', ''),
                            'unit': row.get('Unit', ''),
                            'term': row.get('Term', ''),
                            'importer': row.get('Importer', ''),
                            'exporter': row.get('Exporter', ''),
                            'source_file': trade_file.name,
                            'row_number': row_num
                        }
                        
                        species_data[taxon].append(trade_record)
                        logger.info(f"Found trade record for {taxon}: {trade_record}")
                    
                    # Process only first 50k rows for testing
                    if row_num >= 50000:
                        logger.info(f"Stopping at {row_num} rows for testing")
                        break
                        
        except Exception as e:
            logger.error(f"Error processing {trade_file}: {e}")
    
    # Report results
    logger.info(f"Found trade data for {len(species_data)} species:")
    for species, records in species_data.items():
        logger.info(f"  {species}: {len(records)} records")
    
    # Save a sample JSON file
    if species_data:
        first_species = list(species_data.keys())[0]
        sample_data = {
            'species': first_species,
            'trade_records': species_data[first_species],
            'test_metadata': {
                'extraction_date': datetime.now().isoformat(),
                'total_records': len(species_data[first_species]),
                'note': 'This is a test extraction'
            }
        }
        
        output_file = Path(output_dir) / f"{first_species.replace(' ', '_')}_test.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Sample file saved: {output_file}")
    
    # Check for species without trade data
    species_without_trade = species_set - set(species_data.keys())
    if species_without_trade:
        logger.info(f"Species without trade data: {species_without_trade}")

if __name__ == "__main__":
    test_extraction()
