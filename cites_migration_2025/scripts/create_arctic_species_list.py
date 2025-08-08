#!/usr/bin/env python3
"""
Create comprehensive Arctic species list for CITES data extraction
"""

import pandas as pd
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.supabase_config import get_supabase_client

class ArcticSpeciesListCreator:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        
        # Complete Arctic species list from the CSV
        self.target_species = [
            # From the original target CSV
            ("Aleutian cackling goose", "Branta hutchinsii leucopareia", "AVES"),
            ("Siberian Sturgeon", "Acipenser baerii", "ACTINOPTERYGII"),
            ("Common Thresher Shark", "Alopias vulpinus", "ELASMOBRANCHII"),
            ("Sandhill Crane", "Antigone canadensis", "AVES"),
            ("Short-eared Owl", "Asio flammeus", "AVES"),
            ("Bowhead Whale", "Balaena mysticetus", "MAMMALIA"),
            ("Minke Whale", "Balaenoptera acutorostrata", "MAMMALIA"),
            ("Atlantic White-sided Dolphin", "Lagenorhynchus acutus", "MAMMALIA"),
            ("Baird's Beaked Whale", "Berardius bairdii", "MAMMALIA"),
            ("Basking Shark", "Cetorhinus maximus", "ELASMOBRANCHII"),
            ("Beluga Whale", "Delphinapterus leucas", "MAMMALIA"),
            ("Blue Whale", "Balaenoptera musculus", "MAMMALIA"),
            ("Canada Lynx", "Lynx canadensis", "MAMMALIA"),
            ("Cuvier's beaked whale", "Ziphius cavirostris", "MAMMALIA"),
            ("Dall's Porpoise", "Phocoenoides dalli", "MAMMALIA"),
            ("Eskimo Curlew", "Numenius borealis", "AVES"),
            ("Fin Whale", "Balaenoptera physalus", "MAMMALIA"),
            ("Gray Whale", "Eschrichtius robustus", "MAMMALIA"),
            ("Gyrfalcon", "Falco rusticolus", "AVES"),
            ("Harbour Porpoise", "Phocoena phocoena", "MAMMALIA"),
            ("Humpback Whale", "Megaptera novaeangliae", "MAMMALIA"),
            ("Long-finned Pilot Whale", "Globicephala melas", "MAMMALIA"),
            ("Narwhal", "Monodon monoceros", "MAMMALIA"),
            ("North American River Otter", "Lontra canadensis", "MAMMALIA"),
            ("North Atlantic Right Whale", "Eubalaena glacialis", "MAMMALIA"),
            ("North Pacific Right Whale", "Eubalaena japonica", "MAMMALIA"),
            ("Northern bottlenose whale", "Hyperoodon ampullatus", "MAMMALIA"),
            ("Orca", "Orcinus orca", "MAMMALIA"),
            ("Peregrine Falcon", "Falco peregrinus", "AVES"),
            ("Polar Bear", "Ursus maritimus", "MAMMALIA"),
            ("Porbeagle Shark", "Lamna nasus", "ELASMOBRANCHII"),
            ("Red-Breasted Goose", "Branta ruficollis", "AVES"),
            ("Roseroot", "Rhodiola rosea", "PLANTAE"),
            ("Rough-legged buzzard", "Buteo lagopus", "AVES"),
            ("Sea Otter", "Enhydra lutris", "MAMMALIA"),
            ("Sei Whale", "Balaenoptera borealis", "MAMMALIA"),
            ("Short-tailed Albatross", "Phoebastria albatrus", "AVES"),
            ("Siberian Crane", "Leucogeranus leucogeranus", "AVES"),
            ("Snowy Owl", "Bubo scandiacus", "AVES"),
            ("Sperm Whale", "Physeter macrocephalus", "MAMMALIA"),
            ("Stejneger's beaked whale", "Mesoplodon stejnegeri", "MAMMALIA"),
            ("Walrus", "Odobenus rosmarus", "MAMMALIA"),
            ("White-beaked Dolphin", "Lagenorhynchus albirostris", "MAMMALIA")
        ]
    
    def query_database_species(self):
        """Query database for additional Arctic species information"""
        print("Querying database for Arctic species...")
        
        arctic_species_data = []
        
        for common_name, scientific_name, class_name in self.target_species:
            try:
                # Try to find species in database
                response = self.supabase.table('species').select('*').eq('scientific_name', scientific_name).limit(1).execute()
                
                if not response.data and scientific_name:
                    # Try by common name
                    response = self.supabase.table('species').select('*').ilike('common_name', f'%{common_name}%').limit(1).execute()
                
                if response.data:
                    species = response.data[0]
                    arctic_species_data.append({
                        'common_name': common_name,
                        'scientific_name': scientific_name,
                        'species_id': species.get('id'),
                        'class': class_name,
                        'order': species.get('order_name', ''),
                        'family': species.get('family', ''),
                        'genus': species.get('genus', ''),
                        'in_database': 'Yes',
                        'iucn_status': '',  # Will be filled later
                        'cites_appendix': '',  # Will be filled later
                        'notes': ''
                    })
                    print(f"✓ Found: {common_name}")
                else:
                    arctic_species_data.append({
                        'common_name': common_name,
                        'scientific_name': scientific_name,
                        'species_id': None,
                        'class': class_name,
                        'order': '',
                        'family': '',
                        'genus': scientific_name.split()[0] if scientific_name else '',
                        'in_database': 'No',
                        'iucn_status': '',
                        'cites_appendix': '',
                        'notes': 'Not found in database'
                    })
                    print(f"✗ Not found: {common_name}")
                    
            except Exception as e:
                print(f"Error querying {common_name}: {str(e)}")
                arctic_species_data.append({
                    'common_name': common_name,
                    'scientific_name': scientific_name,
                    'species_id': None,
                    'class': class_name,
                    'order': '',
                    'family': '',
                    'genus': scientific_name.split()[0] if scientific_name else '',
                    'in_database': 'Error',
                    'iucn_status': '',
                    'cites_appendix': '',
                    'notes': f'Query error: {str(e)}'
                })
        
        return arctic_species_data
    
    def add_conservation_status(self, species_data):
        """Add IUCN and CITES status for species"""
        print("\nAdding conservation status...")
        
        for species in species_data:
            if species['species_id']:
                try:
                    # Get IUCN status
                    response = self.supabase.table('iucn_assessments').select('status').eq('species_id', species['species_id']).order('year_published', desc=True).limit(1).execute()
                    if response.data:
                        species['iucn_status'] = response.data[0].get('status', '')
                    
                    # Get CITES status
                    response = self.supabase.table('cites_listings').select('appendix').eq('species_id', species['species_id']).order('listing_date', desc=True).limit(1).execute()
                    if response.data:
                        species['cites_appendix'] = response.data[0].get('appendix', '')
                        
                except Exception as e:
                    print(f"Error getting status for {species['common_name']}: {str(e)}")
        
        return species_data
    
    def create_species_csv(self):
        """Create comprehensive Arctic species CSV"""
        print("Creating Arctic species list...")
        
        # Get species data
        species_data = self.query_database_species()
        
        # Add conservation status
        species_data = self.add_conservation_status(species_data)
        
        # Create DataFrame
        df = pd.DataFrame(species_data)
        
        # Add extraction metadata
        df['extraction_priority'] = 'HIGH'  # All are high priority Arctic species
        df['last_updated'] = datetime.now().strftime('%Y-%m-%d')
        
        # Sort by class and common name
        df = df.sort_values(['class', 'common_name'])
        
        # Save to CSV
        output_path = os.path.join(self.output_dir, 'arctic_species_list.csv')
        df.to_csv(output_path, index=False)
        
        print(f"\n✅ Arctic species list saved to: {output_path}")
        
        # Create summary
        summary = {
            'total_species': len(df),
            'in_database': len(df[df['in_database'] == 'Yes']),
            'not_in_database': len(df[df['in_database'] == 'No']),
            'by_class': df['class'].value_counts().to_dict(),
            'with_iucn_status': len(df[df['iucn_status'] != '']),
            'with_cites_listing': len(df[df['cites_appendix'] != ''])
        }
        
        print("\n📊 Summary:")
        print(f"Total species: {summary['total_species']}")
        print(f"Found in database: {summary['in_database']}")
        print(f"Not in database: {summary['not_in_database']}")
        print("\nBy class:")
        for class_name, count in summary['by_class'].items():
            print(f"  {class_name}: {count}")
        
        return df

if __name__ == "__main__":
    creator = ArcticSpeciesListCreator()
    species_df = creator.create_species_csv()
    
    print("\n📋 Next step: Use this species list to extract CITES trade data")
    print("Run: python extract_arctic_trade_data.py")