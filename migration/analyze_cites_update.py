#!/usr/bin/env python3
"""
Analyze CITES Trade Data Update v2025.1
Safe analysis of new data without loading entire files
"""

import pandas as pd
import os
import sys
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.supabase_config import get_supabase_client

class CITESUpdateAnalyzer:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.data_dir = "/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/species_data/cites_trade/Trade_database_download_v2025.1"
        self.arctic_species_list = [
            "Ursus maritimus",  # Polar Bear
            "Monodon monoceros",  # Narwhal
            "Delphinapterus leucas",  # Beluga
            "Odobenus rosmarus",  # Walrus
            "Lynx canadensis",  # Canada Lynx
            # Add more Arctic species scientific names
        ]
        
    def analyze_file_structure(self):
        """Quick analysis of file structure and size"""
        print("=== CITES Trade Data v2025.1 Analysis ===\n")
        
        # Check files
        csv_files = sorted([f for f in os.listdir(self.data_dir) if f.endswith('.csv')])
        print(f"Total CSV files: {len(csv_files)}")
        
        # Sample first file
        first_file = os.path.join(self.data_dir, csv_files[0])
        df_sample = pd.read_csv(first_file, nrows=5)
        
        print(f"\nColumns in data: {list(df_sample.columns)}")
        print(f"\nSample data from {csv_files[0]}:")
        print(df_sample.to_string())
        
        # Check total size
        total_lines = 0
        for csv_file in csv_files[:3]:  # Just check first 3 files
            file_path = os.path.join(self.data_dir, csv_file)
            with open(file_path, 'r') as f:
                lines = sum(1 for line in f) - 1  # Subtract header
            total_lines += lines
            print(f"\n{csv_file}: {lines:,} records")
        
        print(f"\nEstimated total records: ~{total_lines * len(csv_files) // 3:,}")
        
    def analyze_arctic_species_coverage(self):
        """Check how many Arctic species are in the new data"""
        print("\n=== Arctic Species Coverage Analysis ===\n")
        
        species_found = {}
        files_checked = 0
        
        # Sample across multiple files
        csv_files = sorted([f for f in os.listdir(self.data_dir) if f.endswith('.csv')])
        
        for i in [0, 10, 20, 30, 40, 50]:  # Sample every 10th file
            if i >= len(csv_files):
                continue
                
            file_path = os.path.join(self.data_dir, csv_files[i])
            print(f"Checking {csv_files[i]}...")
            
            # Read in chunks to avoid memory issues
            chunk_count = 0
            for chunk in pd.read_csv(file_path, chunksize=50000):
                for species in self.arctic_species_list:
                    matches = chunk[chunk['Taxon'] == species]
                    if len(matches) > 0:
                        if species not in species_found:
                            species_found[species] = {
                                'count': 0,
                                'years': set(),
                                'purposes': set(),
                                'exporters': set()
                            }
                        species_found[species]['count'] += len(matches)
                        species_found[species]['years'].update(matches['Year'].dropna().astype(int).unique())
                        species_found[species]['purposes'].update(matches['Purpose'].dropna().unique())
                        species_found[species]['exporters'].update(matches['Exporter'].dropna().unique())
                
                chunk_count += 1
                if chunk_count >= 10:  # Only check first 10 chunks per file
                    break
            
            files_checked += 1
        
        print(f"\nChecked {files_checked} files")
        print(f"Arctic species found: {len(species_found)}")
        
        for species, data in species_found.items():
            print(f"\n{species}:")
            print(f"  - Records found: {data['count']}")
            print(f"  - Year range: {min(data['years']) if data['years'] else 'N/A'} - {max(data['years']) if data['years'] else 'N/A'}")
            print(f"  - Trade purposes: {', '.join(sorted(data['purposes'])[:5])}")
            print(f"  - Top exporters: {', '.join(sorted(data['exporters'])[:5])}")
    
    def check_data_quality(self):
        """Check for data quality issues"""
        print("\n=== Data Quality Check ===\n")
        
        # Sample first file
        csv_files = sorted([f for f in os.listdir(self.data_dir) if f.endswith('.csv')])
        first_file = os.path.join(self.data_dir, csv_files[0])
        
        # Read larger sample
        df_sample = pd.read_csv(first_file, nrows=10000)
        
        # Check for nulls
        print("Missing values per column:")
        null_counts = df_sample.isnull().sum()
        for col, count in null_counts.items():
            if count > 0:
                print(f"  {col}: {count} ({count/len(df_sample)*100:.1f}%)")
        
        # Check year range
        years = df_sample['Year'].dropna().astype(int)
        print(f"\nYear range in sample: {years.min()} - {years.max()}")
        
        # Check unique values
        print(f"\nUnique taxa in sample: {df_sample['Taxon'].nunique()}")
        print(f"Unique importers: {df_sample['Importer'].nunique()}")
        print(f"Unique exporters: {df_sample['Exporter'].nunique()}")
        
    def compare_with_current_data(self):
        """Compare with current database statistics"""
        print("\n=== Comparison with Current Database ===\n")
        
        try:
            # Get current stats
            response = self.supabase.table('cites_trade_records').select('year', count='exact').execute()
            current_count = response.count if hasattr(response, 'count') else 0
            
            print(f"Current database records: {current_count:,}")
            print(f"New dataset records: ~27,901,926")
            print(f"Difference: ~{27901926 - current_count:,} records")
            
            # Get year range
            response = self.supabase.rpc('get_trade_year_range', {}).execute()
            if response.data:
                print(f"\nCurrent year range: {response.data}")
            
        except Exception as e:
            print(f"Error querying current database: {str(e)}")
    
    def generate_migration_summary(self):
        """Generate summary report"""
        summary = {
            "analysis_date": datetime.now().isoformat(),
            "cites_version": "v2025.1",
            "total_files": 56,
            "estimated_records": 27901926,
            "file_structure": {
                "format": "CSV",
                "encoding": "UTF-8",
                "delimiter": ",",
                "columns": [
                    "Id", "Year", "Appendix", "Taxon", "Class", "Order", 
                    "Family", "Genus", "Term", "Quantity", "Unit", 
                    "Importer", "Exporter", "Origin", "Purpose", "Source", 
                    "Reporter.type", "Import.permit.RandomID", "Export.permit.RandomID"
                ]
            },
            "migration_requirements": {
                "storage_needed": "~5GB",
                "processing_time": "24-48 hours",
                "backup_size": "~2GB compressed",
                "risk_level": "HIGH"
            },
            "recommendations": [
                "Full backup before migration",
                "Test with staging environment",
                "Process in parallel for speed",
                "Monitor species matching rate",
                "Validate Arctic species coverage"
            ]
        }
        
        # Save summary
        output_path = os.path.join(
            os.path.dirname(__file__), 
            f"cites_migration_summary_{datetime.now().strftime('%Y%m%d')}.json"
        )
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n=== Migration Summary ===")
        print(f"Summary saved to: {output_path}")
        print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    analyzer = CITESUpdateAnalyzer()
    
    print("Starting CITES Trade Data v2025.1 Analysis...")
    print("This will sample the data without loading entire files.\n")
    
    # Run analysis
    analyzer.analyze_file_structure()
    analyzer.analyze_arctic_species_coverage()
    analyzer.check_data_quality()
    analyzer.compare_with_current_data()
    analyzer.generate_migration_summary()
    
    print("\n✅ Analysis complete!")
    print("\n⚠️  IMPORTANT: Review the migration plan before proceeding with actual migration.")
    print("📄 Migration plan: cites_trade_migration_plan.md")