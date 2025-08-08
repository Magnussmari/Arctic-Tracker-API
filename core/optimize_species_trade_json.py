#!/usr/bin/env python3
"""
Optimize Species Trade JSON Files

This script processes the existing large JSON files and creates optimized versions
by normalizing repetitive data structures and using lookup tables.

The optimized format significantly reduces file sizes while maintaining all data.

Usage:
    python optimize_species_trade_json.py [--input-dir path] [--output-dir path]
"""

import json
import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict, Counter
import gzip

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('json_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradeDataOptimizer:
    """Optimize trade data JSON files by normalizing repetitive structures"""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            'files_processed': 0,
            'original_total_size': 0,
            'optimized_total_size': 0,
            'compression_ratio': 0,
            'total_records': 0
        }
    
    def extract_lookup_tables(self, trade_records: List[Dict]) -> Tuple[Dict, List[Dict]]:
        """
        Extract lookup tables for repetitive data and create normalized records
        
        Returns:
            Tuple of (lookup_tables, normalized_records)
        """
        # Identify fields that are good candidates for normalization
        static_fields = ['appendix', 'class', 'order', 'family', 'genus']
        location_fields = ['importer', 'exporter', 'origin']
        categorical_fields = ['term', 'purpose', 'source', 'reporter_type', 'unit']
        
        # Build lookup tables
        lookup_tables = {}
        
        # Static taxonomic data (usually same for all records of a species)
        static_combinations = set()
        for record in trade_records:
            combo = tuple(record.get(field, '') for field in static_fields)
            static_combinations.add(combo)
        
        # Create static data lookup
        static_lookup = {}
        for i, combo in enumerate(sorted(static_combinations)):
            static_lookup[i] = dict(zip(static_fields, combo))
        lookup_tables['taxonomic'] = static_lookup
        
        # Country/location lookup
        all_locations = set()
        for record in trade_records:
            for field in location_fields:
                value = record.get(field, '')
                if value:
                    all_locations.add(value)
        
        location_lookup = {loc: i for i, loc in enumerate(sorted(all_locations))}
        location_reverse = {i: loc for loc, i in location_lookup.items()}
        lookup_tables['locations'] = location_reverse
        
        # Categorical data lookup
        categorical_lookup = {}
        for field in categorical_fields:
            values = set(record.get(field, '') for record in trade_records)
            values.discard('')  # Remove empty strings
            categorical_lookup[field] = {val: i for i, val in enumerate(sorted(values))}
        lookup_tables['categorical'] = categorical_lookup
        
        # Create reverse lookup for categorical
        categorical_reverse = {}
        for field, mapping in categorical_lookup.items():
            categorical_reverse[field] = {i: val for val, i in mapping.items()}
        lookup_tables['categorical_reverse'] = categorical_reverse
        
        # Normalize records
        normalized_records = []
        for record in trade_records:
            # Find taxonomic data index
            static_combo = tuple(record.get(field, '') for field in static_fields)
            taxonomic_id = None
            for tid, data in static_lookup.items():
                if tuple(data[field] for field in static_fields) == static_combo:
                    taxonomic_id = tid
                    break
            
            # Create normalized record
            normalized = {
                'id': record.get('id', ''),
                'year': record.get('year'),
                'taxonomic_id': taxonomic_id,
                'term_id': categorical_lookup.get('term', {}).get(record.get('term', ''), None),
                'quantity_raw': record.get('quantity_raw', ''),
                'quantity_normalized': record.get('quantity_normalized'),
                'unit_id': categorical_lookup.get('unit', {}).get(record.get('unit', ''), None),
                'importer_id': location_lookup.get(record.get('importer', ''), None),
                'exporter_id': location_lookup.get(record.get('exporter', ''), None),
                'origin_id': location_lookup.get(record.get('origin', ''), None),
                'purpose_id': categorical_lookup.get('purpose', {}).get(record.get('purpose', ''), None),
                'source_id': categorical_lookup.get('source', {}).get(record.get('source', ''), None),
                'reporter_type_id': categorical_lookup.get('reporter_type', {}).get(record.get('reporter_type', ''), None),
                'source_file': record.get('source_file', ''),
                'row_number': record.get('row_number')
            }
            
            # Remove None values to save space
            normalized = {k: v for k, v in normalized.items() if v is not None}
            normalized_records.append(normalized)
        
        return lookup_tables, normalized_records
    
    def create_optimized_summary(self, species: str, trade_records: List[Dict], lookup_tables: Dict) -> Dict:
        """Create optimized summary statistics"""
        if not trade_records:
            return {}
        
        # Use the original summary calculation but with some optimizations
        total_records = len(trade_records)
        
        # Years
        years = [r.get('year') for r in trade_records if r.get('year')]
        year_stats = {
            'range': f"{min(years)}-{max(years)}" if years else "Unknown",
            'unique_years': sorted(list(set(years))),
            'total_years': len(set(years))
        }
        
        # Countries (use lookup table)
        location_reverse = lookup_tables['locations']
        importer_ids = set(r.get('importer_id') for r in trade_records if r.get('importer_id') is not None)
        exporter_ids = set(r.get('exporter_id') for r in trade_records if r.get('exporter_id') is not None)
        
        countries = {
            'importing_countries': sorted([location_reverse[i] for i in importer_ids]),
            'exporting_countries': sorted([location_reverse[i] for i in exporter_ids]),
            'total_importing': len(importer_ids),
            'total_exporting': len(exporter_ids)
        }
        
        # Terms traded (use lookup table)
        categorical_reverse = lookup_tables['categorical_reverse']
        term_ids = [r.get('term_id') for r in trade_records if r.get('term_id') is not None]
        term_counts = Counter(term_ids)
        
        terms_summary = {
            'unique_terms': len(term_counts),
            'top_terms': [
                {
                    'term': categorical_reverse['term'].get(term_id, 'Unknown'),
                    'count': count
                }
                for term_id, count in term_counts.most_common(5)
            ]
        }
        
        # Quantities by unit
        quantities_by_unit = defaultdict(list)
        unit_reverse = categorical_reverse.get('unit', {})
        
        for record in trade_records:
            qty = record.get('quantity_normalized')
            unit_id = record.get('unit_id')
            if qty is not None and unit_id is not None:
                unit_name = unit_reverse.get(unit_id, 'Unknown')
                quantities_by_unit[unit_name].append(qty)
        
        quantity_summary = {}
        for unit, quantities in quantities_by_unit.items():
            if quantities:
                quantity_summary[unit] = {
                    'total': sum(quantities),
                    'count': len(quantities),
                    'average': sum(quantities) / len(quantities),
                    'min': min(quantities),
                    'max': max(quantities)
                }
        
        return {
            'total_records': total_records,
            'years': year_stats,
            'countries': countries,
            'terms': terms_summary,
            'quantities': quantity_summary
        }
    
    def optimize_species_file(self, input_file: Path) -> None:
        """Optimize a single species JSON file"""
        logger.info(f"Optimizing {input_file.name}...")
        
        # Load original data
        with open(input_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        species = original_data['species']
        trade_records = original_data['trade_records']
        original_metadata = original_data.get('extraction_metadata', {})
        
        # Extract lookup tables and normalize records
        lookup_tables, normalized_records = self.extract_lookup_tables(trade_records)
        
        # Create optimized summary
        optimized_summary = self.create_optimized_summary(species, normalized_records, lookup_tables)
        
        # Create optimized data structure
        optimized_data = {
            'format_version': '2.0_optimized',
            'species': species,
            'lookup_tables': lookup_tables,
            'summary': optimized_summary,
            'trade_records': normalized_records,
            'metadata': {
                'optimization_date': datetime.now().isoformat(),
                'original_records': len(trade_records),
                'optimized_records': len(normalized_records),
                'original_extraction': original_metadata,
                'compression_info': {
                    'taxonomic_combinations': len(lookup_tables['taxonomic']),
                    'unique_locations': len(lookup_tables['locations']),
                    'categorical_mappings': {k: len(v) for k, v in lookup_tables['categorical'].items()}
                }
            }
        }
        
        # Save optimized version
        output_file = self.output_dir / f"{input_file.stem}_optimized.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(optimized_data, f, separators=(',', ':'), ensure_ascii=False)
        
        # Save compressed version too
        compressed_file = self.output_dir / f"{input_file.stem}_optimized.json.gz"
        with gzip.open(compressed_file, 'wt', encoding='utf-8') as f:
            json.dump(optimized_data, f, separators=(',', ':'), ensure_ascii=False)
        
        # Calculate size reduction
        original_size = input_file.stat().st_size
        optimized_size = output_file.stat().st_size
        compressed_size = compressed_file.stat().st_size
        
        reduction_percent = ((original_size - optimized_size) / original_size) * 100
        compression_percent = ((original_size - compressed_size) / original_size) * 100
        
        logger.info(f"  Original: {original_size:,} bytes")
        logger.info(f"  Optimized: {optimized_size:,} bytes ({reduction_percent:.1f}% reduction)")
        logger.info(f"  Compressed: {compressed_size:,} bytes ({compression_percent:.1f}% reduction)")
        
        # Update stats
        self.stats['original_total_size'] += original_size
        self.stats['optimized_total_size'] += optimized_size
        self.stats['total_records'] += len(trade_records)
    
    def create_data_reader_utility(self) -> None:
        """Create a utility script to read optimized data"""
        reader_script = '''#!/usr/bin/env python3
"""
Optimized Trade Data Reader

Utility to read and work with optimized trade data JSON files.
"""

import json
import gzip
from pathlib import Path
from typing import Dict, List, Any

class OptimizedTradeDataReader:
    """Read and denormalize optimized trade data"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = self._load_data()
        self.lookup_tables = self.data['lookup_tables']
    
    def _load_data(self) -> Dict:
        """Load data from JSON or compressed JSON"""
        if self.file_path.suffix == '.gz':
            with gzip.open(self.file_path, 'rt', encoding='utf-8') as f:
                return json.load(f)
        else:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def get_denormalized_records(self) -> List[Dict]:
        """Get all trade records in original format"""
        records = []
        
        taxonomic_lookup = self.lookup_tables['taxonomic']
        location_lookup = self.lookup_tables['locations']
        categorical_lookup = self.lookup_tables['categorical_reverse']
        
        for record in self.data['trade_records']:
            # Reconstruct full record
            full_record = {
                'id': record.get('id', ''),
                'year': record.get('year'),
                'quantity_raw': record.get('quantity_raw', ''),
                'quantity_normalized': record.get('quantity_normalized'),
                'source_file': record.get('source_file', ''),
                'row_number': record.get('row_number')
            }
            
            # Add taxonomic data
            taxonomic_id = record.get('taxonomic_id')
            if taxonomic_id is not None and taxonomic_id in taxonomic_lookup:
                full_record.update(taxonomic_lookup[taxonomic_id])
            
            # Add locations
            for field, field_id in [('importer', 'importer_id'), ('exporter', 'exporter_id'), ('origin', 'origin_id')]:
                location_id = record.get(field_id)
                if location_id is not None and location_id in location_lookup:
                    full_record[field] = location_lookup[location_id]
                else:
                    full_record[field] = ''
            
            # Add categorical data
            for field in ['term', 'purpose', 'source', 'reporter_type', 'unit']:
                field_id = f"{field}_id"
                value_id = record.get(field_id)
                if value_id is not None and field in categorical_lookup and value_id in categorical_lookup[field]:
                    full_record[field] = categorical_lookup[field][value_id]
                else:
                    full_record[field] = ''
            
            records.append(full_record)
        
        return records
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        return self.data.get('summary', {})
    
    def get_metadata(self) -> Dict:
        """Get metadata"""
        return self.data.get('metadata', {})
    
    def get_species(self) -> str:
        """Get species name"""
        return self.data.get('species', '')

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python optimized_reader.py <optimized_json_file>")
        sys.exit(1)
    
    reader = OptimizedTradeDataReader(sys.argv[1])
    
    print(f"Species: {reader.get_species()}")
    print(f"Total records: {len(reader.data['trade_records'])}")
    
    # Show first few records in original format
    records = reader.get_denormalized_records()
    print(f"\\nFirst 3 records:")
    for i, record in enumerate(records[:3]):
        print(f"Record {i+1}: {record}")
    
    # Show summary
    summary = reader.get_summary()
    print(f"\\nSummary: {summary}")
'''
        
        reader_file = self.output_dir / 'optimized_reader.py'
        with open(reader_file, 'w', encoding='utf-8') as f:
            f.write(reader_script)
        
        logger.info(f"Created data reader utility: {reader_file}")
    
    def optimize_all_files(self) -> None:
        """Optimize all JSON files in the input directory"""
        logger.info(f"Looking for JSON files in {self.input_dir}")
        
        # Find all trade data JSON files
        json_files = list(self.input_dir.glob('*_trade_data.json'))
        json_files.sort()
        
        logger.info(f"Found {len(json_files)} JSON files to optimize")
        
        for i, json_file in enumerate(json_files, 1):
            logger.info(f"Processing file {i}/{len(json_files)}: {json_file.name}")
            self.optimize_species_file(json_file)
            self.stats['files_processed'] += 1
        
        # Calculate overall compression ratio
        if self.stats['original_total_size'] > 0:
            self.stats['compression_ratio'] = (
                (self.stats['original_total_size'] - self.stats['optimized_total_size']) / 
                self.stats['original_total_size']
            ) * 100
        
        # Create reader utility
        self.create_data_reader_utility()
        
        # Generate optimization report
        self._generate_optimization_report()
    
    def _generate_optimization_report(self) -> None:
        """Generate a report of the optimization process"""
        report = {
            'optimization_summary': {
                'optimization_date': datetime.now().isoformat(),
                'files_processed': self.stats['files_processed'],
                'total_records_processed': self.stats['total_records'],
                'size_reduction': {
                    'original_total_size_bytes': self.stats['original_total_size'],
                    'optimized_total_size_bytes': self.stats['optimized_total_size'],
                    'size_reduction_bytes': self.stats['original_total_size'] - self.stats['optimized_total_size'],
                    'compression_ratio_percent': round(self.stats['compression_ratio'], 2)
                },
                'file_size_human_readable': {
                    'original_total': f"{self.stats['original_total_size'] / (1024*1024):.1f} MB",
                    'optimized_total': f"{self.stats['optimized_total_size'] / (1024*1024):.1f} MB",
                    'saved_space': f"{(self.stats['original_total_size'] - self.stats['optimized_total_size']) / (1024*1024):.1f} MB"
                }
            }
        }
        
        report_file = self.output_dir / 'optimization_report.json'
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Optimization completed!")
        logger.info(f"Files processed: {self.stats['files_processed']}")
        logger.info(f"Original size: {self.stats['original_total_size'] / (1024*1024):.1f} MB")
        logger.info(f"Optimized size: {self.stats['optimized_total_size'] / (1024*1024):.1f} MB")
        logger.info(f"Space saved: {self.stats['compression_ratio']:.1f}%")
        logger.info(f"Report saved to: {report_file}")


def main():
    """Main function with command-line interface"""
    parser = argparse.ArgumentParser(description='Optimize species trade data JSON files')
    
    parser.add_argument(
        '--input-dir',
        default='/Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/species_data/processed/individual_species',
        help='Directory containing original JSON files'
    )
    
    parser.add_argument(
        '--output-dir',
        default='/Users/magnussmari/Arctic_tracker/arctic-species-api_local/rebuild/species_data/processed/optimized_species',
        help='Output directory for optimized JSON files'
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not Path(args.input_dir).exists():
        print(f"Error: Input directory not found: {args.input_dir}")
        sys.exit(1)
    
    # Run optimization
    optimizer = TradeDataOptimizer(
        input_dir=args.input_dir,
        output_dir=args.output_dir
    )
    
    optimizer.optimize_all_files()


if __name__ == "__main__":
    main()
