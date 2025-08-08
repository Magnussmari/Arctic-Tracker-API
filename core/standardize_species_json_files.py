#!/usr/bin/env python3
"""
Standardize species JSON file names and create empty templates for missing species.

This script:
1. Renames existing JSON files to use simple Scientific_name.json format
2. Creates empty JSON template files for all species not yet researched
"""

import os
import json
import shutil
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# List of all 42 Arctic species
ARCTIC_SPECIES = [
    # Marine Mammals - Baleen Whales
    "Balaena mysticetus",
    "Balaenoptera acutorostrata", 
    "Balaenoptera borealis",
    "Balaenoptera musculus",
    "Balaenoptera physalus",
    "Megaptera novaeangliae",
    
    # Marine Mammals - Toothed Whales
    "Delphinapterus leucas",
    "Monodon monoceros",
    "Physeter macrocephalus",
    "Berardius bairdii",
    "Hyperoodon ampullatus",
    "Mesoplodon stejnegeri",
    "Ziphius cavirostris",
    "Eschrichtius robustus",
    
    # Marine Mammals - Right Whales
    "Eubalaena glacialis",
    "Eubalaena japonica",
    
    # Marine Mammals - Dolphins & Porpoises
    "Globicephala melas",
    "Lagenorhynchus acutus",
    "Lagenorhynchus albirostris",
    "Orcinus orca",
    "Phocoena phocoena",
    "Phocoenoides dalli",
    
    # Terrestrial Mammals
    "Ursus maritimus",
    "Lynx canadensis",
    "Lontra canadensis",
    "Enhydra lutris",
    "Odobenus rosmarus",
    
    # Birds - Raptors
    "Buteo lagopus",
    "Falco peregrinus",
    "Falco rusticolus",
    "Nyctea scandiaca",
    
    # Birds - Others
    "Asio flammeus",
    "Antigone canadensis",
    "Branta canadensis leucopareia",
    "Branta ruficollis",
    "Leucogeranus leucogeranus",
    "Numenius borealis",
    "Phoebastria albatrus",
    
    # Fish & Sharks
    "Alopias vulpinus",
    "Cetorhinus maximus",
    "Lamna nasus",
    "Acipenser baerii",
    
    # Plants
    "Rhodiola rosea"
]

# Map existing files to their proper scientific names
FILE_MAPPINGS = {
    "narhwal.json": "Monodon monoceros",  # Note: misspelling in original
    "bowhead.json": "Balaena mysticetus",
    "Hyperoodon_ampullatus_conservation_profile.json": "Hyperoodon ampullatus",
    "Siberian_sturgeon.json": "Acipenser baerii",
    "Falco_rusticolus.json": "Falco rusticolus",
    "short_eared_owl.json": "Asio flammeus",
    "thresher_shark.json": "Alopias vulpinus",
    "scrane.json": "Leucogeranus leucogeranus"  # Siberian crane
}

def create_empty_json_template():
    """Create an empty JSON template for species profiles."""
    return {
        "species": {
            "scientific_name": "",
            "common_name": "",
            "taxonomic_info": {
                "kingdom": "",
                "phylum": "",
                "class": "",
                "order": "",
                "family": "",
                "genus": "",
                "species": ""
            }
        },
        "conservation_status": {
            "iucn_status": "",
            "cites_listing": "",
            "cms_appendix": "",
            "population_trend": "",
            "assessment_year": None
        },
        "distribution": {
            "arctic_range": [],
            "breeding_range": [],
            "wintering_range": [],
            "depth_range": {},
            "habitat_types": []
        },
        "ecology": {
            "diet": [],
            "feeding_behavior": "",
            "breeding_season": "",
            "lifespan": "",
            "generation_time": "",
            "social_structure": ""
        },
        "threats": [],
        "conservation_measures": [],
        "population_data": {
            "global_population": "",
            "regional_populations": {},
            "monitoring_methods": []
        },
        "cultural_significance": {
            "indigenous_names": {},
            "traditional_uses": [],
            "cultural_importance": ""
        },
        "economic_importance": {
            "commercial_value": "",
            "subsistence_value": "",
            "ecotourism_value": ""
        },
        "research_needs": [],
        "references": [],
        "metadata": {
            "profile_version": "1.0",
            "last_updated": "",
            "data_sources": [],
            "notes": "Empty template - awaiting research data"
        }
    }

def main():
    """Main function to standardize JSON files."""
    # Set up paths
    processed_dir = Path("/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/species_data/scite/processed")
    
    if not processed_dir.exists():
        print(f"Error: Directory {processed_dir} does not exist!")
        return
    
    print("Starting JSON file standardization...")
    print(f"Working directory: {processed_dir}")
    print(f"Total Arctic species: {len(ARCTIC_SPECIES)}")
    
    # Track what we've processed
    processed_species = set()
    renamed_files = []
    created_files = []
    
    # Step 1: Rename existing files
    print("\n--- Step 1: Renaming existing files ---")
    
    for old_file in processed_dir.glob("*.json"):
        old_name = old_file.name
        
        # Check if this file needs renaming
        if old_name in FILE_MAPPINGS:
            scientific_name = FILE_MAPPINGS[old_name]
            new_name = f"{scientific_name.replace(' ', '_')}.json"
            new_path = processed_dir / new_name
            
            # Rename the file
            shutil.move(str(old_file), str(new_path))
            renamed_files.append(f"{old_name} → {new_name}")
            processed_species.add(scientific_name)
            print(f"  Renamed: {old_name} → {new_name}")
        else:
            # Extract scientific name from existing proper format
            if old_name.endswith("_conservation_profile.json"):
                # Remove the suffix
                scientific_name = old_name.replace("_conservation_profile.json", "").replace("_", " ")
            elif "_" in old_name and not old_name.startswith("_"):
                # Assume it's already in Scientific_name.json format
                scientific_name = old_name.replace(".json", "").replace("_", " ")
            else:
                print(f"  Warning: Unknown file format: {old_name}")
                continue
            
            # Check if it's one of our Arctic species
            if scientific_name in ARCTIC_SPECIES:
                processed_species.add(scientific_name)
                print(f"  Already properly named: {old_name}")
    
    # Step 2: Create empty templates for missing species
    print("\n--- Step 2: Creating empty templates for missing species ---")
    
    for species in ARCTIC_SPECIES:
        if species not in processed_species:
            # Create filename
            filename = f"{species.replace(' ', '_')}.json"
            filepath = processed_dir / filename
            
            # Create empty template
            template = create_empty_json_template()
            template["species"]["scientific_name"] = species
            
            # Save the file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            
            created_files.append(filename)
            print(f"  Created: {filename}")
    
    # Summary report
    print("\n--- Summary Report ---")
    print(f"Total species: {len(ARCTIC_SPECIES)}")
    print(f"Files renamed: {len(renamed_files)}")
    print(f"Empty templates created: {len(created_files)}")
    print(f"Total JSON files now: {len(list(processed_dir.glob('*.json')))}")
    
    # List all current files
    print("\n--- Current files in processed directory ---")
    all_files = sorted([f.name for f in processed_dir.glob("*.json")])
    for i, filename in enumerate(all_files, 1):
        status = "[EMPTY]" if filename in [f for f in created_files] else "[DATA]"
        print(f"{i:2d}. {status} {filename}")
    
    # Check for any extra files not in our species list
    print("\n--- Validation ---")
    current_files = {f.stem.replace("_", " ") for f in processed_dir.glob("*.json")}
    extra_files = current_files - set(ARCTIC_SPECIES)
    missing_species = set(ARCTIC_SPECIES) - current_files
    
    if extra_files:
        print(f"Warning: Found files for non-Arctic species: {extra_files}")
    if missing_species:
        print(f"Error: Missing files for species: {missing_species}")
    else:
        print("✅ All 42 Arctic species have JSON files!")

if __name__ == "__main__":
    main()