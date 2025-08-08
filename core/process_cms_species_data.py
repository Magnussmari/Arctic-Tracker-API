#!/usr/bin/env python3
"""
Process CMS Species Data Script

This script filters the CMS (Convention on the Conservation of Migratory Species) 
listing data to extract only the 42 Arctic species tracked by the Arctic Tracker project.

Usage:
    python process_cms_species_data.py
"""

import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cms_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CMSSpeciesProcessor:
    """Process CMS listing data for Arctic species"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.species_list_file = self.base_dir / "species_data" / "Arctic_Tracker_42_Species_List.md"
        self.cms_file = self.base_dir / "species_data" / "raw_data" / "cms_listing_100725.csv"
        self.output_dir = self.base_dir / "species_data" / "processed"
        
        # Create output directory if needed
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Arctic species set
        self.arctic_species: Set[str] = set()
        
        # Results
        self.cms_species_data: List[Dict] = []
        self.species_found: Set[str] = set()
        self.species_not_found: Set[str] = set()
        
    def load_arctic_species(self) -> None:
        """Load the 42 Arctic species from the markdown file"""
        try:
            with open(self.species_list_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract scientific names using pattern matching
            import re
            # Pattern: number. **Scientific name** - Common name
            pattern = r'\d+\.\s+\*\*([A-Z][a-z]+\s+[a-z]+(?:\s+[a-z]+)?)\*\*\s+-\s+'
            
            matches = re.findall(pattern, content)
            self.arctic_species = set(matches)
            
            # Also check for the one plant species that might be formatted differently
            if "Rhodiola rosea" in content:
                self.arctic_species.add("Rhodiola rosea")
                
            logger.info(f"Loaded {len(self.arctic_species)} Arctic species")
            
        except Exception as e:
            logger.error(f"Error loading Arctic species list: {e}")
            raise
            
    def parse_cms_record(self, row: Dict[str, str]) -> Optional[Dict]:
        """Parse a CMS CSV row into structured data"""
        scientific_name = row.get('ScientificName', '').strip()
        
        if not scientific_name or scientific_name not in self.arctic_species:
            return None
            
        # Parse the listing status
        listing = row.get('Listing', '').strip()
        agreement = row.get('Agreement', '').strip()
        
        # Skip empty listings
        if listing == '""' or not listing:
            return None
            
        # Parse distribution data
        native_dist = row.get('NativeDistributionFullNames', '').strip()
        all_dist_codes = row.get('All_DistributionISOCodes', '').strip()
        
        # Split comma-separated values
        native_countries = [c.strip() for c in native_dist.split(',') if c.strip()]
        iso_codes = [c.strip() for c in all_dist_codes.split(',') if c.strip()]
        
        # Parse other distribution types
        introduced = row.get('Introduced_Distribution', '').strip()
        extinct = row.get('Extinct_Distribution', '').strip()
        uncertain = row.get('Distribution_Uncertain', '').strip()
        
        return {
            'species_name': scientific_name,
            'cms_listing': listing,
            'agreement': agreement,
            'listed_under': row.get('Listed under', '').strip(),
            'date_listed': row.get('Date', '').strip(),
            'notes': row.get('Note', '').strip(),
            'native_distribution': native_countries,
            'all_distribution_codes': iso_codes,
            'introduced_distribution': [c.strip() for c in introduced.split(',') if c.strip()],
            'extinct_distribution': [c.strip() for c in extinct.split(',') if c.strip()],
            'distribution_uncertain': [c.strip() for c in uncertain.split(',') if c.strip()],
            'taxonomic_info': {
                'phylum': row.get('Phylum', '').strip(),
                'class': row.get('Class', '').strip(),
                'order': row.get('Order', '').strip(),
                'family': row.get('Family', '').strip(),
                'genus': row.get('Genus', '').strip(),
                'author': row.get('Author', '').strip()
            }
        }
        
    def process_cms_data(self) -> None:
        """Process the CMS CSV file and extract Arctic species data"""
        try:
            with open(self.cms_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                for row in reader:
                    parsed_data = self.parse_cms_record(row)
                    if parsed_data:
                        self.cms_species_data.append(parsed_data)
                        self.species_found.add(parsed_data['species_name'])
                        
            # Identify species not found in CMS
            self.species_not_found = self.arctic_species - self.species_found
            
            logger.info(f"Processed CMS data: {len(self.species_found)} Arctic species found")
            logger.info(f"Species not in CMS: {len(self.species_not_found)}")
            
        except Exception as e:
            logger.error(f"Error processing CMS file: {e}")
            raise
            
    def consolidate_species_listings(self) -> Dict[str, Dict]:
        """Consolidate multiple CMS listings for the same species"""
        consolidated = {}
        
        for record in self.cms_species_data:
            species = record['species_name']
            
            if species not in consolidated:
                consolidated[species] = record
            else:
                # Merge listings if species has multiple entries
                existing = consolidated[species]
                
                # Combine listing statuses
                if record['cms_listing'] and record['cms_listing'] != '""':
                    if existing['cms_listing'] and existing['cms_listing'] != '""':
                        # Keep the most comprehensive listing (e.g., I/II over just I or II)
                        if '/' in record['cms_listing'] or '/' not in existing['cms_listing']:
                            existing['cms_listing'] = record['cms_listing']
                    else:
                        existing['cms_listing'] = record['cms_listing']
                        
                # Merge notes
                if record['notes']:
                    if existing['notes']:
                        existing['notes'] += f"; {record['notes']}"
                    else:
                        existing['notes'] = record['notes']
                        
        return consolidated
        
    def save_results(self) -> None:
        """Save processed CMS data and summary report"""
        # Consolidate multiple listings
        consolidated_data = self.consolidate_species_listings()
        
        # Sort by species name
        sorted_species = sorted(consolidated_data.values(), key=lambda x: x['species_name'])
        
        # Save JSON data
        output_file = self.output_dir / "cms_arctic_species_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'metadata': {
                    'source': 'Convention on the Conservation of Migratory Species (CMS)',
                    'processed_date': datetime.now().isoformat(),
                    'total_arctic_species': len(self.arctic_species),
                    'species_in_cms': len(self.species_found),
                    'species_not_in_cms': len(self.species_not_found)
                },
                'species_data': sorted_species
            }, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Saved CMS data to {output_file}")
        
        # Generate summary report
        self.generate_summary_report()
        
    def generate_summary_report(self) -> None:
        """Generate a markdown summary report"""
        report_file = self.output_dir / "cms_arctic_species_summary.md"
        
        # Group species by CMS listing
        by_listing = {}
        consolidated = self.consolidate_species_listings()
        
        for species_data in consolidated.values():
            listing = species_data['cms_listing']
            if listing not in by_listing:
                by_listing[listing] = []
            by_listing[listing].append(species_data['species_name'])
            
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# CMS Arctic Species Summary Report\n\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("## Overview\n\n")
            f.write(f"- **Total Arctic Tracker Species**: {len(self.arctic_species)}\n")
            f.write(f"- **Species in CMS**: {len(self.species_found)}\n")
            f.write(f"- **Species not in CMS**: {len(self.species_not_found)}\n\n")
            
            f.write("## Species by CMS Listing Status\n\n")
            
            # Sort listing categories
            listing_order = ['I', 'II', 'I/II']
            other_listings = sorted([l for l in by_listing.keys() if l not in listing_order])
            
            for listing in listing_order + other_listings:
                if listing in by_listing:
                    species_list = sorted(by_listing[listing])
                    f.write(f"### Appendix {listing} ({len(species_list)} species)\n\n")
                    for species in species_list:
                        f.write(f"- {species}\n")
                    f.write("\n")
                    
            f.write("## Arctic Species NOT in CMS\n\n")
            if self.species_not_found:
                for species in sorted(self.species_not_found):
                    f.write(f"- {species}\n")
            else:
                f.write("*All Arctic Tracker species are listed in CMS*\n")
                
        logger.info(f"Generated summary report: {report_file}")
        
    def run(self) -> None:
        """Execute the CMS processing pipeline"""
        logger.info("Starting CMS data processing for Arctic species")
        
        # Load Arctic species list
        self.load_arctic_species()
        
        # Process CMS data
        self.process_cms_data()
        
        # Save results
        self.save_results()
        
        logger.info("CMS processing completed successfully")
        
        # Print summary
        print(f"\n{'='*60}")
        print("CMS PROCESSING SUMMARY")
        print(f"{'='*60}")
        print(f"Arctic species in CMS: {len(self.species_found)}")
        print(f"Arctic species NOT in CMS: {len(self.species_not_found)}")
        print(f"\nOutput files:")
        print(f"- {self.output_dir}/cms_arctic_species_data.json")
        print(f"- {self.output_dir}/cms_arctic_species_summary.md")
        print(f"{'='*60}\n")


def main():
    """Main entry point"""
    processor = CMSSpeciesProcessor()
    processor.run()


if __name__ == "__main__":
    main()