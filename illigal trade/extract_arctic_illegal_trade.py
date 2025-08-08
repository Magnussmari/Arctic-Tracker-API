#!/usr/bin/env python3
"""
Extract illegal trade records for Arctic species from seizure dataset
Maps to our Arctic species list and categorizes trade types
"""

import pandas as pd
import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Set

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class ArcticIllegalTradeExtractor:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.illegal_trade_dir = "/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/illigal trade/dataset/data"
        self.output_dir = os.path.join(self.base_dir, 'illegal_trade_analysis')
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Load Arctic species
        self.arctic_species = self._load_arctic_species()
        
        # Create search patterns for Arctic species
        self.search_patterns = self._create_search_patterns()
        
    def _load_arctic_species(self) -> pd.DataFrame:
        """Load our Arctic species list"""
        species_file = os.path.join(self.base_dir, 'data', 'arctic_species_list.csv')
        df = pd.read_csv(species_file)
        print(f"Loaded {len(df)} Arctic species")
        return df
        
    def _create_search_patterns(self) -> Dict[str, List[str]]:
        """Create search patterns for each Arctic species"""
        patterns = {}
        
        for _, species in self.arctic_species.iterrows():
            species_id = species['species_id']
            patterns[species_id] = []
            
            # Add scientific name
            if pd.notna(species['scientific_name']):
                patterns[species_id].append(species['scientific_name'].lower())
                
                # Add genus
                genus = species['scientific_name'].split()[0]
                patterns[species_id].append(genus.lower())
                
            # Add common name
            if pd.notna(species['common_name']):
                patterns[species_id].append(species['common_name'].lower())
                
            # Add special cases
            if species['scientific_name'] == 'Branta canadensis leucopareia':
                patterns[species_id].extend(['branta hutchinsii', 'aleutian cackling goose'])
                
            if species['scientific_name'] == 'Lynx canadensis':
                patterns[species_id].append('lynx lynx canadensis')
                
            if species['scientific_name'] == 'Ursus maritimus':
                patterns[species_id].extend(['polar bear', 'white bear'])
                
            if species['scientific_name'] == 'Monodon monoceros':
                patterns[species_id].extend(['narwhal', 'narwhale'])
                
            if species['scientific_name'] == 'Odobenus rosmarus':
                patterns[species_id].extend(['walrus', 'rosmarus rosmarus'])
                
        return patterns
        
    def extract_illegal_trade_data(self):
        """Extract all illegal trade records for Arctic species"""
        print("\nExtracting illegal trade data...")
        
        # Load illegal trade data
        trade_file = os.path.join(self.illegal_trade_dir, '01_taxa_use_combos.csv')
        illegal_df = pd.read_csv(trade_file)
        print(f"Loaded {len(illegal_df)} illegal trade records")
        
        # Find Arctic species records
        arctic_records = []
        
        for species_id, patterns in self.search_patterns.items():
            # Search for each pattern
            mask = pd.Series([False] * len(illegal_df))
            
            for pattern in patterns:
                # Search in both clean and original taxa names
                mask |= illegal_df['db_taxa_name_clean'].str.lower().str.contains(pattern, na=False)
                mask |= illegal_df['db_taxa_name'].str.lower().str.contains(pattern, na=False)
                
            # Get matching records
            matches = illegal_df[mask].copy()
            
            if len(matches) > 0:
                # Add our species info
                species_info = self.arctic_species[self.arctic_species['species_id'] == species_id].iloc[0]
                matches['arctic_species_id'] = species_id
                matches['arctic_scientific_name'] = species_info['scientific_name']
                matches['arctic_common_name'] = species_info['common_name']
                matches['iucn_status'] = species_info.get('iucn_status', '')
                matches['cites_appendix'] = species_info.get('cites_appendix', '')
                
                arctic_records.append(matches)
                print(f"Found {len(matches)} records for {species_info['common_name']} ({species_info['scientific_name']})")
                
        # Combine all Arctic records
        if arctic_records:
            arctic_illegal_df = pd.concat(arctic_records, ignore_index=True)
            print(f"\nTotal Arctic species illegal trade records: {len(arctic_illegal_df)}")
            
            # Remove duplicates (same record matched by multiple patterns)
            arctic_illegal_df = arctic_illegal_df.drop_duplicates(
                subset=['db', 'db_taxa_name', 'standardized_use_id']
            )
            print(f"After removing duplicates: {len(arctic_illegal_df)}")
            
            # Save detailed records
            output_file = os.path.join(self.output_dir, 'arctic_illegal_trade_records.csv')
            arctic_illegal_df.to_csv(output_file, index=False)
            print(f"\nSaved to: {output_file}")
            
            # Create summary
            self._create_summary(arctic_illegal_df)
            
            return arctic_illegal_df
        else:
            print("No Arctic species found in illegal trade data")
            return pd.DataFrame()
            
    def _create_summary(self, df: pd.DataFrame):
        """Create summary statistics"""
        print("\nCreating summary statistics...")
        
        # Summary by species
        species_summary = df.groupby(['arctic_species_id', 'arctic_scientific_name', 'arctic_common_name', 
                                      'iucn_status', 'cites_appendix']).agg({
            'db': 'count',
            'standardized_use_type': lambda x: list(x.unique()),
            'main_category': lambda x: list(x.unique()),
            'db_taxa_name': lambda x: list(x.unique())
        }).reset_index()
        
        species_summary.columns = ['species_id', 'scientific_name', 'common_name', 'iucn_status', 
                                  'cites_appendix', 'seizure_count', 'use_types', 'main_categories', 'name_variants']
        
        # Convert lists to strings
        species_summary['use_types'] = species_summary['use_types'].apply(lambda x: ', '.join(x))
        species_summary['main_categories'] = species_summary['main_categories'].apply(lambda x: ', '.join(x))
        species_summary['name_variants'] = species_summary['name_variants'].apply(lambda x: ', '.join(set(x)))
        
        # Sort by seizure count
        species_summary = species_summary.sort_values('seizure_count', ascending=False)
        
        # Save summary
        summary_file = os.path.join(self.output_dir, 'arctic_illegal_trade_summary.csv')
        species_summary.to_csv(summary_file, index=False)
        print(f"Saved summary to: {summary_file}")
        
        # Print top species
        print("\nTop 10 Arctic species in illegal trade:")
        for _, row in species_summary.head(10).iterrows():
            print(f"  {row['common_name']} ({row['scientific_name']}): {row['seizure_count']} seizures")
            print(f"    Uses: {row['use_types']}")
            
        # Summary by use type
        use_summary = df.groupby('standardized_use_type').agg({
            'arctic_species_id': 'count',
            'arctic_common_name': lambda x: list(x.unique())[:5]  # Top 5 species
        }).reset_index()
        
        use_summary.columns = ['use_type', 'record_count', 'top_species']
        use_summary['top_species'] = use_summary['top_species'].apply(lambda x: ', '.join(x))
        use_summary = use_summary.sort_values('record_count', ascending=False)
        
        use_file = os.path.join(self.output_dir, 'illegal_trade_by_use_type.csv')
        use_summary.to_csv(use_file, index=False)
        
        print("\nTop illegal trade uses:")
        for _, row in use_summary.head(10).iterrows():
            print(f"  {row['use_type']}: {row['record_count']} records")
            
        # Database source summary
        db_summary = df.groupby('db').size().reset_index(name='count')
        print("\nRecords by database:")
        for _, row in db_summary.iterrows():
            db_name = {'wtp': 'TRAFFIC', 'lemis': 'US LEMIS', 'cites': 'CITES'}.get(row['db'], row['db'])
            print(f"  {db_name}: {row['count']} records")
            
    def create_risk_assessment(self):
        """Create risk assessment based on illegal trade data"""
        # This would be implemented after running the extraction
        pass

if __name__ == "__main__":
    extractor = ArcticIllegalTradeExtractor()
    illegal_trade_df = extractor.extract_illegal_trade_data()