#!/usr/bin/env python3
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
    print(f"\nFirst 3 records:")
    for i, record in enumerate(records[:3]):
        print(f"Record {i+1}: {record}")
    
    # Show summary
    summary = reader.get_summary()
    print(f"\nSummary: {summary}")
