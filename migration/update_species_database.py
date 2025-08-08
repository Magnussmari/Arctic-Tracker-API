#!/usr/bin/env python3
"""
Database Architecture Update and Species Name Retrieval Script

This script updates the database architecture for the Arctic Species CITES trade data
import system and retrieves both scientific and common names for species using the
IUCN Red List API v4.

Usage:
    python update_species_database.py [--dry-run] [--limit N]
    
Options:
    --dry-run    Show what would be updated without making changes
    --limit N    Limit processing to N species (for testing)
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

# Add rebuild directory to path for imports
rebuild_dir = Path(__file__).parent.parent
sys.path.insert(0, str(rebuild_dir))

from config import get_cached_settings, get_database_manager, get_api_config
from core.iucn_client import IUCNApiClient

class SpeciesDatabaseUpdater:
    """
    Handles database architecture updates and species name retrieval
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the database updater
        
        Args:
            dry_run (bool): If True, only show what would be updated
        """
        self.dry_run = dry_run
        self.settings = get_cached_settings()
        self.db_manager = get_database_manager()
        self.api_config = get_api_config()
        
    async def create_species_names_table(self) -> bool:
        """
        Create or update the species_names table for storing IUCN data
        
        Returns:
            bool: True if successful, False otherwise
        """
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS species_names (
            id SERIAL PRIMARY KEY,
            species_id INTEGER,
            scientific_name TEXT NOT NULL,
            common_name TEXT,
            genus TEXT,
            species_epithet TEXT,
            authority TEXT,
            kingdom TEXT,
            phylum TEXT,
            class TEXT,
            order_name TEXT,
            family TEXT,
            iucn_taxon_id INTEGER,
            iucn_assessment_id INTEGER,
            conservation_status TEXT,
            conservation_category TEXT,
            assessment_date DATE,
            published_year INTEGER,
            population_trend TEXT,
            marine_system BOOLEAN,
            freshwater_system BOOLEAN,
            terrestrial_system BOOLEAN,
            elevation_upper INTEGER,
            elevation_lower INTEGER,
            depth_upper INTEGER,
            depth_lower INTEGER,
            aoo_km2 DECIMAL,
            eoo_km2 DECIMAL,
            threats_data JSONB,
            habitats_data JSONB,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_source TEXT DEFAULT 'IUCN_v4',
            FOREIGN KEY (species_id) REFERENCES species(id),
            UNIQUE(species_id, iucn_taxon_id)
        );
        
        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_species_names_species_id ON species_names(species_id);
        CREATE INDEX IF NOT EXISTS idx_species_names_scientific_name ON species_names(scientific_name);
        CREATE INDEX IF NOT EXISTS idx_species_names_iucn_taxon_id ON species_names(iucn_taxon_id);
        CREATE INDEX IF NOT EXISTS idx_species_names_conservation_status ON species_names(conservation_status);
        
        -- Add comment to table
        COMMENT ON TABLE species_names IS 'IUCN Red List species information and conservation assessments';
        """
        
        if self.dry_run:
            print("DRY RUN: Would create species_names table with the following SQL:")
            print(create_table_sql)
            return True
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_table_sql)
                    conn.commit()
            print("✓ Successfully created/updated species_names table")
            return True
        except Exception as e:
            print(f"✗ Error creating species_names table: {e}")
            return False
    
    async def get_existing_species(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get existing species from the database that need IUCN data
        
        Args:
            limit (Optional[int]): Limit number of species to process
            
        Returns:
            List[Dict[str, Any]]: List of species data
        """
        query = """
        SELECT s.id as species_id, s.species_name, s.common_name as existing_common_name
        FROM species s
        LEFT JOIN species_names sn ON s.id = sn.species_id
        WHERE sn.species_id IS NULL  -- Only get species not yet in species_names
        ORDER BY s.species_name
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    columns = [desc[0] for desc in cursor.description]
                    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    
            print(f"Found {len(results)} species that need IUCN data")
            return results
            
        except Exception as e:
            print(f"Error fetching species from database: {e}")
            return []
    
    async def process_species_with_iucn(self, species_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process species list and get IUCN data
        
        Args:
            species_list (List[Dict[str, Any]]): List of species to process
            
        Returns:
            List[Dict[str, Any]]: Processed species with IUCN data
        """
        results = []
        
        async with IUCNApiClient() as iucn_client:
            for i, species_data in enumerate(species_list, 1):
                species_name = species_data.get('species_name', '').strip()
                species_id = species_data.get('species_id')
                
                print(f"Processing {i}/{len(species_list)}: {species_name}")
                
                # Extract genus and species
                genus, species_epithet = iucn_client.extract_genus_species(species_name)
                
                if not genus or not species_epithet:
                    print(f"  ⚠ Skipping invalid scientific name: {species_name}")
                    continue
                
                try:
                    # Get species data from IUCN v4 API
                    iucn_data = await iucn_client.get_species_by_name(species_name)
                    
                    if iucn_data and 'result' in iucn_data and iucn_data['result']:
                        for taxon in iucn_data['result']:
                            # Get assessment details if assessment_id is available
                            assessment_details = None
                            assessment_id = taxon.get('assessment_id')
                            
                            if assessment_id:
                                try:
                                    assessment_details = await iucn_client.get_assessment_details(assessment_id)
                                except Exception as e:
                                    print(f"  ⚠ Could not get assessment details for {species_name}: {e}")
                            
                            # Combine taxon and assessment data
                            processed_entry = {
                                'species_id': species_id,
                                'scientific_name': taxon.get('scientific_name', species_name),
                                'common_name': taxon.get('main_common_name'),
                                'genus': genus,
                                'species_epithet': species_epithet,
                                'authority': taxon.get('authority'),
                                'kingdom': taxon.get('kingdom'),
                                'phylum': taxon.get('phylum'),
                                'class': taxon.get('class'),
                                'order_name': taxon.get('order'),
                                'family': taxon.get('family'),
                                'iucn_taxon_id': taxon.get('taxonid'),
                                'iucn_assessment_id': assessment_id,
                                'conservation_status': taxon.get('category'),
                                'conservation_category': taxon.get('category'),
                                'assessment_date': taxon.get('assessment_date'),
                                'published_year': taxon.get('published_year'),
                                'population_trend': taxon.get('population_trend'),
                                'marine_system': taxon.get('marine_system'),
                                'freshwater_system': taxon.get('freshwater_system'),
                                'terrestrial_system': taxon.get('terrestrial_system'),
                                'elevation_upper': taxon.get('elevation_upper'),
                                'elevation_lower': taxon.get('elevation_lower'),
                                'depth_upper': taxon.get('depth_upper'),
                                'depth_lower': taxon.get('depth_lower'),
                                'aoo_km2': taxon.get('aoo_km2'),
                                'eoo_km2': taxon.get('eoo_km2'),
                                'data_source': 'IUCN_v4'
                            }
                            
                            # Add assessment details if available
                            if assessment_details and 'result' in assessment_details:
                                detail_data = assessment_details['result']
                                processed_entry.update({
                                    'threats_data': detail_data.get('threats'),
                                    'habitats_data': detail_data.get('habitats')
                                })
                            
                            results.append(processed_entry)
                            print(f"  ✓ Found IUCN data: {processed_entry['conservation_status']} - {processed_entry['common_name'] or 'No common name'}")
                    
                    else:
                        # Species not found in IUCN
                        not_found_entry = {
                            'species_id': species_id,
                            'scientific_name': species_name,
                            'common_name': species_data.get('existing_common_name'),
                            'genus': genus,
                            'species_epithet': species_epithet,
                            'conservation_status': 'Not Assessed',
                            'conservation_category': 'Not Assessed',
                            'data_source': 'IUCN_v4'
                        }
                        results.append(not_found_entry)
                        print(f"  ℹ Not found in IUCN Red List")
                
                except Exception as e:
                    print(f"  ✗ Error processing {species_name}: {e}")
                    # Add error entry
                    error_entry = {
                        'species_id': species_id,
                        'scientific_name': species_name,
                        'common_name': species_data.get('existing_common_name'),
                        'genus': genus,
                        'species_epithet': species_epithet,
                        'conservation_status': 'Error',
                        'conservation_category': 'Error',
                        'data_source': 'IUCN_v4_Error'
                    }
                    results.append(error_entry)
        
        return results
    
    async def save_species_data(self, species_data: List[Dict[str, Any]]) -> bool:
        """
        Save processed species data to the database
        
        Args:
            species_data (List[Dict[str, Any]]): Processed species data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not species_data:
            print("No species data to save")
            return True
        
        insert_sql = """
        INSERT INTO species_names (
            species_id, scientific_name, common_name, genus, species_epithet,
            authority, kingdom, phylum, class, order_name, family,
            iucn_taxon_id, iucn_assessment_id, conservation_status, conservation_category,
            assessment_date, published_year, population_trend,
            marine_system, freshwater_system, terrestrial_system,
            elevation_upper, elevation_lower, depth_upper, depth_lower,
            aoo_km2, eoo_km2, threats_data, habitats_data, data_source
        ) VALUES (
            %(species_id)s, %(scientific_name)s, %(common_name)s, %(genus)s, %(species_epithet)s,
            %(authority)s, %(kingdom)s, %(phylum)s, %(class)s, %(order_name)s, %(family)s,
            %(iucn_taxon_id)s, %(iucn_assessment_id)s, %(conservation_status)s, %(conservation_category)s,
            %(assessment_date)s, %(published_year)s, %(population_trend)s,
            %(marine_system)s, %(freshwater_system)s, %(terrestrial_system)s,
            %(elevation_upper)s, %(elevation_lower)s, %(depth_upper)s, %(depth_lower)s,
            %(aoo_km2)s, %(eoo_km2)s, %(threats_data)s, %(habitats_data)s, %(data_source)s
        )
        ON CONFLICT (species_id, iucn_taxon_id) 
        DO UPDATE SET
            scientific_name = EXCLUDED.scientific_name,
            common_name = EXCLUDED.common_name,
            conservation_status = EXCLUDED.conservation_status,
            conservation_category = EXCLUDED.conservation_category,
            last_updated = CURRENT_TIMESTAMP
        """
        
        if self.dry_run:
            print(f"DRY RUN: Would save {len(species_data)} species records to database")
            for species in species_data[:3]:  # Show first 3 as examples
                print(f"  Example: {species['scientific_name']} - {species['conservation_status']}")
            if len(species_data) > 3:
                print(f"  ... and {len(species_data) - 3} more")
            return True
        
        try:
            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Convert threats_data and habitats_data to JSON strings if they exist
                    for species in species_data:
                        if species.get('threats_data'):
                            species['threats_data'] = json.dumps(species['threats_data'])
                        if species.get('habitats_data'):
                            species['habitats_data'] = json.dumps(species['habitats_data'])
                    
                    cursor.executemany(insert_sql, species_data)
                    conn.commit()
                    
            print(f"✓ Successfully saved {len(species_data)} species records to database")
            return True
            
        except Exception as e:
            print(f"✗ Error saving species data: {e}")
            return False
    
    async def generate_summary_report(self, processed_data: List[Dict[str, Any]]) -> None:
        """
        Generate a summary report of the processing results
        
        Args:
            processed_data (List[Dict[str, Any]]): Processed species data
        """
        if not processed_data:
            print("No data to summarize")
            return
        
        # Count by conservation status
        status_counts = {}
        common_name_count = 0
        error_count = 0
        
        for species in processed_data:
            status = species.get('conservation_status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if species.get('common_name'):
                common_name_count += 1
            
            if status in ['Error', 'IUCN_v4_Error']:
                error_count += 1
        
        print("\n" + "="*60)
        print("PROCESSING SUMMARY REPORT")
        print("="*60)
        print(f"Total species processed: {len(processed_data)}")
        print(f"Species with common names: {common_name_count}")
        print(f"Processing errors: {error_count}")
        print("\nConservation Status Distribution:")
        
        for status, count in sorted(status_counts.items()):
            percentage = (count / len(processed_data)) * 100
            print(f"  {status}: {count} ({percentage:.1f}%)")
        
        print("="*60)
        
        # Save detailed report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = rebuild_dir / f"species_update_report_{timestamp}.json"
        
        report_data = {
            'timestamp': timestamp,
            'total_processed': len(processed_data),
            'common_names_found': common_name_count,
            'errors': error_count,
            'status_distribution': status_counts,
            'processed_species': processed_data
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        print(f"Detailed report saved to: {report_file}")

async def main():
    """Main function to run the database update script"""
    parser = argparse.ArgumentParser(description='Update species database with IUCN data')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be updated without making changes')
    parser.add_argument('--limit', type=int, 
                       help='Limit processing to N species (for testing)')
    
    args = parser.parse_args()
    
    print("Arctic Species Database Update Script")
    print("=====================================")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    updater = SpeciesDatabaseUpdater(dry_run=args.dry_run)
    
    # Step 1: Create/update database schema
    print("\n1. Creating/updating database schema...")
    if not await updater.create_species_names_table():
        print("Failed to create database schema. Exiting.")
        return 1
    
    # Step 2: Get existing species that need IUCN data
    print("\n2. Fetching species from database...")
    species_list = await updater.get_existing_species(limit=args.limit)
    
    if not species_list:
        print("No species found that need IUCN data. Exiting.")
        return 0
    
    # Step 3: Process species with IUCN API
    print(f"\n3. Processing {len(species_list)} species with IUCN API...")
    processed_data = await updater.process_species_with_iucn(species_list)
    
    # Step 4: Save data to database
    print("\n4. Saving processed data to database...")
    if not await updater.save_species_data(processed_data):
        print("Failed to save data to database.")
        return 1
    
    # Step 5: Generate summary report
    print("\n5. Generating summary report...")
    await updater.generate_summary_report(processed_data)
    
    print("\n✅ Database update completed successfully!")
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
