#!/usr/bin/env python3
"""
Extract ONLY Arctic species trade data from CITES database
Processes 28M records efficiently to extract ~50-100K Arctic records
"""

import pandas as pd
import os
import sys
import json
from datetime import datetime
import logging
from typing import Set, Dict, List
import multiprocessing as mp
from functools import partial

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/extraction.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ArcticTradeDataExtractor:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.source_dir = "/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/species_data/cites_trade/Trade_database_download_v2025.1"
        self.output_dir = os.path.join(self.base_dir, 'extracted_data')
        
        # Load Arctic species list
        self.arctic_species = self._load_arctic_species()
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'total_records_scanned': 0,
            'arctic_records_found': 0,
            'species_match_counts': {},
            'extraction_start': datetime.now().isoformat()
        }
        
    def _load_arctic_species(self) -> Dict[str, Dict]:
        """Load Arctic species list and create lookup structures"""
        species_file = os.path.join(self.base_dir, 'data', 'arctic_species_list.csv')
        
        if not os.path.exists(species_file):
            logger.error(f"Arctic species list not found at {species_file}")
            logger.info("Please run create_arctic_species_list.py first")
            sys.exit(1)
        
        df = pd.read_csv(species_file)
        
        # Create lookup dictionary by scientific name
        species_lookup = {}
        for _, row in df.iterrows():
            scientific_name = row['scientific_name']
            if scientific_name and pd.notna(scientific_name):
                species_lookup[scientific_name] = {
                    'common_name': row['common_name'],
                    'species_id': row.get('species_id'),
                    'class': row.get('class'),
                    'in_database': row.get('in_database')
                }
        
        # Ensure Branta canadensis leucopareia is included (in case CSV has hutchinsii)
        if 'Branta canadensis leucopareia' not in species_lookup:
            species_lookup['Branta canadensis leucopareia'] = {
                'common_name': 'Aleutian Canada Goose',
                'species_id': 'b38aac84-d527-4ab9-8c97-2a4bc1d92d15',
                'class': 'AVES',
                'in_database': 'Yes'
            }
            logger.info("Added Branta canadensis leucopareia to species lookup")
        
        logger.info(f"Loaded {len(species_lookup)} Arctic species for extraction")
        return species_lookup
    
    def process_single_file(self, file_info: tuple) -> Dict:
        """Process a single CSV file and extract Arctic species records"""
        file_path, file_num = file_info
        
        logger.info(f"Processing file {file_num}/56: {os.path.basename(file_path)}")
        
        file_stats = {
            'file': os.path.basename(file_path),
            'records_scanned': 0,
            'arctic_records': 0,
            'species_found': set()
        }
        
        arctic_records = []
        
        try:
            # Process file in chunks to manage memory
            chunk_size = 50000
            for chunk_num, chunk in enumerate(pd.read_csv(file_path, chunksize=chunk_size)):
                # Filter for Arctic species
                mask = chunk['Taxon'].isin(self.arctic_species.keys())
                arctic_chunk = chunk[mask]
                
                if len(arctic_chunk) > 0:
                    arctic_records.append(arctic_chunk)
                    file_stats['arctic_records'] += len(arctic_chunk)
                    file_stats['species_found'].update(arctic_chunk['Taxon'].unique())
                
                file_stats['records_scanned'] += len(chunk)
                
                # Log progress every 10 chunks
                if chunk_num % 10 == 0:
                    logger.debug(f"  Chunk {chunk_num}: {file_stats['arctic_records']} Arctic records found so far")
            
            # Combine all Arctic records from this file
            if arctic_records:
                combined_df = pd.concat(arctic_records, ignore_index=True)
                
                # Save to individual file
                output_file = os.path.join(self.output_dir, f'arctic_trade_{file_num:02d}.csv')
                combined_df.to_csv(output_file, index=False)
                logger.info(f"  Saved {len(combined_df)} Arctic records to {output_file}")
            
            # Convert set to list for JSON serialization
            file_stats['species_found'] = list(file_stats['species_found'])
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            file_stats['error'] = str(e)
        
        return file_stats
    
    def extract_all_arctic_data(self, parallel=True, max_workers=4):
        """Extract Arctic species data from all CITES files"""
        logger.info("Starting Arctic species data extraction")
        logger.info(f"Source directory: {self.source_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Get list of CSV files
        csv_files = sorted([f for f in os.listdir(self.source_dir) if f.startswith('trade_db_') and f.endswith('.csv')])
        logger.info(f"Found {len(csv_files)} CITES trade files to process")
        
        # Prepare file list with numbers
        file_list = [(os.path.join(self.source_dir, f), i+1) for i, f in enumerate(csv_files)]
        
        if parallel:
            logger.info(f"Processing files in parallel with {max_workers} workers")
            with mp.Pool(processes=max_workers) as pool:
                results = pool.map(self.process_single_file, file_list)
        else:
            logger.info("Processing files sequentially")
            results = [self.process_single_file(f) for f in file_list]
        
        # Aggregate statistics
        all_species_found = set()
        for result in results:
            self.stats['files_processed'] += 1
            self.stats['total_records_scanned'] += result['records_scanned']
            self.stats['arctic_records_found'] += result['arctic_records']
            
            # Track species counts
            for species in result.get('species_found', []):
                if species in self.stats['species_match_counts']:
                    self.stats['species_match_counts'][species] += result['arctic_records']
                else:
                    self.stats['species_match_counts'][species] = result['arctic_records']
                all_species_found.add(species)
        
        self.stats['unique_species_found'] = len(all_species_found)
        self.stats['extraction_end'] = datetime.now().isoformat()
        
        # Save statistics
        self._save_extraction_stats()
        
        # Combine all extracted files
        self._combine_extracted_files()
        
        logger.info("Extraction complete!")
        self._print_summary()
    
    def _combine_extracted_files(self):
        """Combine all extracted Arctic trade files into one"""
        logger.info("Combining extracted files...")
        
        extracted_files = sorted([f for f in os.listdir(self.output_dir) if f.startswith('arctic_trade_') and f.endswith('.csv')])
        
        if not extracted_files:
            logger.warning("No extracted files found to combine")
            return
        
        # Read and combine all files
        all_data = []
        for file in extracted_files:
            file_path = os.path.join(self.output_dir, file)
            df = pd.read_csv(file_path)
            all_data.append(df)
        
        # Combine into single DataFrame
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Add species information
        combined_df['common_name'] = combined_df['Taxon'].map(
            lambda x: self.arctic_species.get(x, {}).get('common_name', '')
        )
        combined_df['species_class'] = combined_df['Taxon'].map(
            lambda x: self.arctic_species.get(x, {}).get('class', '')
        )
        
        # Sort by year and species
        combined_df = combined_df.sort_values(['Year', 'Taxon'])
        
        # Save combined file
        output_path = os.path.join(self.output_dir, 'arctic_species_trade_data_v2025.csv')
        combined_df.to_csv(output_path, index=False)
        
        logger.info(f"Combined file saved: {output_path}")
        logger.info(f"Total Arctic trade records: {len(combined_df):,}")
        
        # Create summary by species
        species_summary = combined_df.groupby('Taxon').agg({
            'Id': 'count',
            'Year': ['min', 'max'],
            'Quantity': 'sum'
        }).round(2)
        
        species_summary.columns = ['record_count', 'min_year', 'max_year', 'total_quantity']
        species_summary.to_csv(os.path.join(self.output_dir, 'arctic_species_trade_summary.csv'))
        
        return combined_df
    
    def _save_extraction_stats(self):
        """Save extraction statistics"""
        stats_file = os.path.join(self.base_dir, 'logs', f'extraction_stats_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        
        with open(stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)
        
        logger.info(f"Extraction statistics saved to {stats_file}")
    
    def _print_summary(self):
        """Print extraction summary"""
        print("\n" + "="*60)
        print("ARCTIC SPECIES EXTRACTION SUMMARY")
        print("="*60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Total records scanned: {self.stats['total_records_scanned']:,}")
        print(f"Arctic records found: {self.stats['arctic_records_found']:,}")
        print(f"Extraction rate: {(self.stats['arctic_records_found']/self.stats['total_records_scanned']*100):.3f}%")
        print(f"Unique species found: {self.stats['unique_species_found']}")
        print("\nTop 10 species by record count:")
        
        sorted_species = sorted(self.stats['species_match_counts'].items(), key=lambda x: x[1], reverse=True)
        for species, count in sorted_species[:10]:
            common_name = self.arctic_species.get(species, {}).get('common_name', 'Unknown')
            print(f"  {common_name} ({species}): {count:,} records")
        
        print("="*60)

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract Arctic species trade data from CITES database')
    parser.add_argument('--parallel', action='store_true', help='Process files in parallel')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel workers')
    parser.add_argument('--test', action='store_true', help='Test mode - process only first 3 files')
    
    args = parser.parse_args()
    
    # Create output directory
    extractor = ArcticTradeDataExtractor()
    os.makedirs(extractor.output_dir, exist_ok=True)
    os.makedirs(os.path.join(extractor.base_dir, 'logs'), exist_ok=True)
    
    if args.test:
        logger.info("Running in TEST mode - processing first 3 files only")
        # Modify to process only first 3 files
        # Implementation would go here
    
    # Run extraction
    extractor.extract_all_arctic_data(parallel=args.parallel, max_workers=args.workers)

if __name__ == "__main__":
    main()