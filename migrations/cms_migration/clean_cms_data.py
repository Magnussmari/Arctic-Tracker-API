#!/usr/bin/env python3
"""
Clean CMS Data Script

This script cleans the CMS data to handle species listed in both Appendix I and II.
Best practice: Normalize the data to match database constraints.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_cms_data():
    """Clean the CMS data to handle I/II appendix values"""
    
    # Load the original data
    base_dir = Path(__file__).parent.parent.parent
    input_file = base_dir / "species_data" / "processed" / "cms_arctic_species_data.json"
    output_file = base_dir / "species_data" / "processed" / "cms_arctic_species_data_cleaned.json"
    
    logger.info(f"Loading CMS data from: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Track changes
    species_modified = []
    
    # Clean the data
    for species in data['species_data']:
        if species['cms_listing'] == 'I/II':
            # Log the species being modified
            species_modified.append(species['species_name'])
            
            # For species listed in both appendices, we'll use the higher protection level (I)
            # This is a common practice in conservation databases
            logger.info(f"Converting {species['species_name']} from I/II to I (higher protection level)")
            
            # Update the listing
            species['cms_listing'] = 'I'
            
            # Add a note about the dual listing if not already present
            if species['notes']:
                species['notes'] = f"Listed in both Appendix I and II. {species['notes']}"
            else:
                species['notes'] = "Listed in both Appendix I and II."
    
    # Update metadata
    data['metadata']['processed_date'] = datetime.now().isoformat()
    data['metadata']['data_cleaned'] = True
    data['metadata']['species_modified'] = len(species_modified)
    data['metadata']['cleaning_notes'] = "Species listed as I/II converted to I (higher protection level)"
    
    # Save cleaned data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\nCMS Data Cleaning Summary")
    print("=" * 50)
    print(f"Total species processed: {len(data['species_data'])}")
    print(f"Species modified: {len(species_modified)}")
    print("\nSpecies converted from I/II to I:")
    for species in species_modified:
        print(f"  - {species}")
    print(f"\nCleaned data saved to: {output_file}")
    
    return output_file


def create_update_script(cleaned_file: Path):
    """Create an updated loading script that uses the cleaned data"""
    
    script_path = Path(__file__).parent / "load_cms_data_cleaned.py"
    
    # Read the original loading script
    original_script = Path(__file__).parent / "load_cms_data_to_db.py"
    with open(original_script, 'r') as f:
        content = f.read()
    
    # Update the data file path
    content = content.replace(
        'self.cms_data_file = self.base_dir / "species_data" / "processed" / "cms_arctic_species_data.json"',
        'self.cms_data_file = self.base_dir / "species_data" / "processed" / "cms_arctic_species_data_cleaned.json"'
    )
    
    # Save the updated script
    with open(script_path, 'w') as f:
        f.write(content)
    
    logger.info(f"Created updated loading script: {script_path}")
    return script_path


if __name__ == "__main__":
    # Clean the data
    cleaned_file = clean_cms_data()
    
    # Create updated loading script
    loading_script = create_update_script(cleaned_file)
    
    print(f"\nNext steps:")
    print(f"1. Review the cleaned data: {cleaned_file}")
    print(f"2. Run the updated loading script: python {loading_script.name}")