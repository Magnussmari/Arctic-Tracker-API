#!/usr/bin/env python3
"""
Extract Species Trade Data Script

This script processes the species list and creates individual JSON files
containing all trade data for each species. It handles large datasets
and problematic quantity values.

NOTE: This script now checks for existing optimized files in the 'optimized_species' directory,
which contains the complete set of 44 optimized trade data files, including two files
that were missing from the original 'optimized' directory:
- Branta_ruficollis_trade_data_optimized.json.gz
- Lagenorhynchus_albirostris_trade_data_optimized.json.gz

Usage:
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/core && python extract_species_trade_data.py --mode full --help
cd /Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/core && python extract_species_trade_data.py --mode incremental
    python extract_species_trade_data.py [--species-file path] [--trade-dir path] [--output-dir path]
"""

import csv
import json
import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
import glob

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('species_trade_extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SpeciesTradeExtractor:
    """Extract and organize trade data for individual species"""
    
    def __init__(self, species_file: str, trade_dir: str, output_dir: str, mode: str = 'full'):
        self.species_file = Path(species_file)
        self.trade_dir = Path(trade_dir)
        self.output_dir = Path(output_dir)
        self.mode = mode
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'species_processed': 0,
            'species_with_trade': 0,
            'species_without_trade': 0,
            'total_trade_records': 0,
            'quantity_issues': 0,
            'files_processed': 0
        }
        
        # Track species without trade data
        self.species_without_trade: List[str] = []
        
        # Track quantity issues
        self.quantity_issues: List[Dict] = []
    
    def load_species_list(self) -> Set[str]:
        """Load the list of species to search for"""
        species_set = set()
        
        try:
            with open(self.species_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    scientific_name = row.get('scientific_name', '').strip()
                    if scientific_name:
                        species_set.add(scientific_name)
                        
        except Exception as e:
            logger.error(f"Error loading species file {self.species_file}: {e}")
            raise
            
        logger.info(f"Loaded {len(species_set)} species from {self.species_file}")
        return species_set
    
    def get_existing_species_files(self) -> Set[str]:
        """Get list of species that already have optimized files"""
        existing_species = set()
        
        # Check both JSON and compressed versions in the optimized_species directory
        optimized_dir = Path(self.output_dir).parent / "optimized_species"
        
        if optimized_dir.exists():
            # Look for both .json and .json.gz files
            for pattern in ['*_trade_data_optimized.json', '*_trade_data_optimized.json.gz']:
                for file_path in optimized_dir.glob(pattern):
                    filename = file_path.stem
                    # Handle .gz files where stem gives us the .json name
                    if filename.endswith('.json'):
                        filename = filename[:-5]  # Remove .json extension
                    
                    if filename.endswith('_trade_data_optimized'):
                        species_name = filename.replace('_trade_data_optimized', '').replace('_', ' ')
                        existing_species.add(species_name)
                        
        logger.info(f"Found {len(existing_species)} species with existing optimized files")
        return existing_species
    
    def filter_species_by_mode(self, species_set: Set[str]) -> Set[str]:
        """Filter species based on extraction mode"""
        if self.mode == 'incremental':
            existing_species = self.get_existing_species_files()
            missing_species = species_set - existing_species
            logger.info(f"Incremental mode: Processing {len(missing_species)} species without optimized files")
            logger.info(f"Skipping {len(existing_species)} species with existing files")
            return missing_species
        else:
            logger.info(f"Full mode: Processing all {len(species_set)} species")
            return species_set
    
    def normalize_quantity(self, quantity_str: str, unit: str, taxon: str, file_name: str) -> Optional[float]:
        """
        Normalize quantity values, handling problematic large numbers
        
        Args:
            quantity_str: Raw quantity string from CSV
            unit: Unit of measurement
            taxon: Species name for logging
            file_name: Source file for logging
            
        Returns:
            Normalized quantity as float or None if invalid
        """
        if not quantity_str or quantity_str.strip() == '':
            return None
            
        try:
            # Clean the quantity string
            clean_qty = quantity_str.replace(',', '').strip()
            
            # Try to convert to decimal first for precision
            qty_decimal = Decimal(clean_qty)
            qty_float = float(qty_decimal)
            
            # Check for suspiciously large numbers (> 1 billion)
            if qty_float > 1_000_000_000:
                self.quantity_issues.append({
                    'taxon': taxon,
                    'file': file_name,
                    'original_quantity': quantity_str,
                    'unit': unit,
                    'normalized_quantity': qty_float,
                    'issue': 'extremely_large_value'
                })
                self.stats['quantity_issues'] += 1
                
                # Convert to more reasonable units if possible
                if unit.lower() in ['microgrammes', 'microgram', 'μg']:
                    # Convert micrograms to grams
                    qty_float = qty_float / 1_000_000
                    unit = 'g'
                    logger.warning(f"Converted {taxon} quantity from {quantity_str} μg to {qty_float} g")
                
            return qty_float
            
        except (ValueError, InvalidOperation, OverflowError) as e:
            self.quantity_issues.append({
                'taxon': taxon,
                'file': file_name,
                'original_quantity': quantity_str,
                'unit': unit,
                'error': str(e),
                'issue': 'conversion_error'
            })
            self.stats['quantity_issues'] += 1
            logger.warning(f"Could not convert quantity '{quantity_str}' for {taxon}: {e}")
            return None
    
    def process_trade_file(self, trade_file: Path, species_set: Set[str], species_data: Dict[str, List]) -> None:
        """Process a single trade data CSV file"""
        logger.info(f"Processing {trade_file.name}...")
        
        try:
            with open(trade_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row_num, row in enumerate(reader, 1):
                    taxon = row.get('Taxon', '').strip()
                    
                    # Check if this species is in our target list
                    if taxon in species_set:
                        # Normalize quantity
                        quantity_raw = row.get('Quantity', '')
                        unit_raw = row.get('Unit', '')
                        quantity_normalized = self.normalize_quantity(
                            quantity_raw, unit_raw, taxon, trade_file.name
                        )
                        
                        # Create trade record
                        trade_record = {
                            'id': row.get('Id', ''),
                            'year': self._safe_int(row.get('Year')),
                            'appendix': row.get('Appendix', ''),
                            'class': row.get('Class', ''),
                            'order': row.get('Order', ''),
                            'family': row.get('Family', ''),
                            'genus': row.get('Genus', ''),
                            'term': row.get('Term', ''),
                            'quantity_raw': quantity_raw,
                            'quantity_normalized': quantity_normalized,
                            'unit': unit_raw,
                            'importer': row.get('Importer', ''),
                            'exporter': row.get('Exporter', ''),
                            'origin': row.get('Origin', ''),
                            'purpose': row.get('Purpose', ''),
                            'source': row.get('Source', ''),
                            'reporter_type': row.get('Reporter.type', ''),
                            'source_file': trade_file.name,
                            'row_number': row_num
                        }
                        
                        species_data[taxon].append(trade_record)
                        self.stats['total_trade_records'] += 1
                    
                    # Log progress every 100k rows
                    if row_num % 100000 == 0:
                        logger.info(f"  Processed {row_num:,} rows from {trade_file.name}")
                        
        except Exception as e:
            logger.error(f"Error processing {trade_file}: {e}")
            raise
    
    def _safe_int(self, value: str) -> Optional[int]:
        """Safely convert string to int"""
        try:
            return int(value) if value and value.strip() else None
        except ValueError:
            return None
    
    def extract_all_trade_data(self) -> Dict[str, List]:
        """Extract trade data for all species from all trade files"""
        species_set = self.load_species_list()
        
        # Filter species based on extraction mode
        species_set = self.filter_species_by_mode(species_set)
        
        if not species_set:
            logger.info("No species to process after filtering")
            return {}
        
        species_data = defaultdict(list)
        
        # Find all trade CSV files
        trade_files = list(self.trade_dir.glob('trade_db_*.csv'))
        trade_files.sort()
        
        logger.info(f"Found {len(trade_files)} trade data files")
        
        # Process each trade file
        for i, trade_file in enumerate(trade_files, 1):
            logger.info(f"Processing file {i}/{len(trade_files)}: {trade_file.name}")
            self.process_trade_file(trade_file, species_set, species_data)
            self.stats['files_processed'] += 1
        
        return dict(species_data)
    
    def generate_species_json_files(self, species_data: Dict[str, List]) -> None:
        """Generate individual JSON files for each species"""
        logger.info("Generating individual JSON files for species...")
        
        species_set = self.load_species_list()
        # Apply the same filtering as in extract_all_trade_data
        species_set = self.filter_species_by_mode(species_set)
        
        for species in species_set:
            self.stats['species_processed'] += 1
            
            if species in species_data and species_data[species]:
                # Species has trade data
                self.stats['species_with_trade'] += 1
                
                # Calculate summary statistics
                trade_records = species_data[species]
                summary = self._calculate_species_summary(species, trade_records)
                
                # Create output data
                output_data = {
                    'species': species,
                    'summary': summary,
                    'trade_records': trade_records,
                    'extraction_metadata': {
                        'extraction_date': datetime.now().isoformat(),
                        'total_records': len(trade_records),
                        'source_files': list(set(record['source_file'] for record in trade_records)),
                        'date_range': {
                            'earliest_year': min((r['year'] for r in trade_records if r['year']), default=None),
                            'latest_year': max((r['year'] for r in trade_records if r['year']), default=None)
                        }
                    }
                }
                
                # Save to JSON file
                safe_filename = self._make_safe_filename(species)
                output_file = self.output_dir / f"{safe_filename}_trade_data.json"
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Created {output_file.name} with {len(trade_records)} records")
                
            else:
                # Species has no trade data
                self.stats['species_without_trade'] += 1
                self.species_without_trade.append(species)
                logger.warning(f"No trade data found for: {species}")
    
    def _calculate_species_summary(self, species: str, trade_records: List[Dict]) -> Dict[str, Any]:
        """Calculate summary statistics for a species"""
        if not trade_records:
            return {}
        
        # Basic counts
        total_records = len(trade_records)
        
        # Years
        years = [r['year'] for r in trade_records if r['year']]
        year_range = f"{min(years)}-{max(years)}" if years else "Unknown"
        
        # Countries
        importers = set(r['importer'] for r in trade_records if r['importer'])
        exporters = set(r['exporter'] for r in trade_records if r['exporter'])
        
        # Terms traded
        terms = defaultdict(int)
        for record in trade_records:
            if record['term']:
                terms[record['term']] += 1
        
        # Quantities by unit
        quantities_by_unit = defaultdict(list)
        for record in trade_records:
            if record['quantity_normalized'] and record['unit']:
                quantities_by_unit[record['unit']].append(record['quantity_normalized'])
        
        # Calculate totals by unit
        quantity_totals = {}
        for unit, quantities in quantities_by_unit.items():
            quantity_totals[unit] = {
                'total': sum(quantities),
                'count': len(quantities),
                'average': sum(quantities) / len(quantities),
                'min': min(quantities),
                'max': max(quantities)
            }
        
        return {
            'total_records': total_records,
            'year_range': year_range,
            'years_with_data': sorted(list(set(years))),
            'importing_countries': sorted(list(importers)),
            'exporting_countries': sorted(list(exporters)),
            'terms_traded': dict(terms),
            'quantity_summary': quantity_totals,
            'top_terms': sorted(terms.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def _make_safe_filename(self, species_name: str) -> str:
        """Convert species name to safe filename"""
        # Replace spaces and special characters
        safe_name = species_name.replace(' ', '_')
        safe_name = ''.join(c for c in safe_name if c.isalnum() or c in ['_', '-'])
        return safe_name
    
    def generate_summary_report(self) -> None:
        """Generate a summary report of the extraction process"""
        report = {
            'extraction_summary': {
                'extraction_date': datetime.now().isoformat(),
                'statistics': self.stats,
                'species_without_trade': self.species_without_trade,
                'quantity_issues_sample': self.quantity_issues[:10],  # First 10 issues
                'total_quantity_issues': len(self.quantity_issues)
            }
        }
        
        # Save summary report
        summary_file = self.output_dir / 'extraction_summary_report.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Save detailed quantity issues if any
        if self.quantity_issues:
            issues_file = self.output_dir / 'quantity_issues_detailed.json'
            with open(issues_file, 'w', encoding='utf-8') as f:
                json.dump(self.quantity_issues, f, indent=2, ensure_ascii=False)
        
        # Save species without trade data
        if self.species_without_trade:
            no_trade_file = self.output_dir / 'species_without_trade.txt'
            with open(no_trade_file, 'w', encoding='utf-8') as f:
                for species in sorted(self.species_without_trade):
                    f.write(f"{species}\n")
        
        logger.info(f"Summary report saved to {summary_file}")
        logger.info(f"Found trade data for {self.stats['species_with_trade']} species")
        logger.info(f"No trade data for {self.stats['species_without_trade']} species")
        logger.info(f"Total trade records: {self.stats['total_trade_records']:,}")
        logger.info(f"Quantity issues encountered: {self.stats['quantity_issues']}")
    
    def run(self) -> None:
        """Run the complete extraction process"""
        logger.info("Starting species trade data extraction...")
        logger.info(f"Species file: {self.species_file}")
        logger.info(f"Trade data directory: {self.trade_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        try:
            # Extract trade data
            species_data = self.extract_all_trade_data()
            
            # Generate JSON files
            self.generate_species_json_files(species_data)
            
            # Generate summary report
            self.generate_summary_report()
            
            logger.info("Species trade data extraction completed successfully!")
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description='Extract trade data for individual species')
    
    parser.add_argument(
        '--species-file',
        default='/Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/docs/reports/species_names_latest.csv',
        help='Path to species CSV file'
    )
    
    parser.add_argument(
        '--mode',
        choices=['full', 'incremental'],
        default='full',
        help='Extraction mode: full (all species) or incremental (only missing species)'
    )
    
    parser.add_argument(
        '--trade-dir',
        default='/Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/species_data/raw_data/Trade_full',
        help='Directory containing trade data CSV files'
    )
    
    parser.add_argument(
        '--output-dir',
        default='/Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/species_data/processed/individual_species',
        help='Output directory for species JSON files'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not Path(args.species_file).exists():
        print(f"Error: Species file not found: {args.species_file}")
        sys.exit(1)
    
    if not Path(args.trade_dir).exists():
        print(f"Error: Trade data directory not found: {args.trade_dir}")
        sys.exit(1)
    
    # Run extraction
    extractor = SpeciesTradeExtractor(
        species_file=args.species_file,
        trade_dir=args.trade_dir,
        output_dir=args.output_dir,
        mode=args.mode
    )
    
    extractor.run()


if __name__ == "__main__":
    main()
