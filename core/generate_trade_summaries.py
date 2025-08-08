#!/usr/bin/env python3
"""
Generate Trade Summaries Script

This script populates the species_trade_summary table with pre-aggregated data
to enable massive performance improvements for the frontend. It creates aggregated
summaries of trade data for each species to reduce page load times from 3-5 seconds
to less than 500ms.

Usage:
    python generate_trade_summaries.py [--priority-only] [--species-id SPECIES_ID]
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from uuid import uuid4

# Add the config directory to the path
sys.path.append(str(Path(__file__).parent.parent / 'config'))

try:
    from supabase_config import get_supabase_client
except ImportError:
    print("Error: Could not import supabase_config. Please ensure config/supabase_config.py exists.")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'trade_summary_generation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Priority species scientific names
PRIORITY_SPECIES = [
    "Ursus maritimus",      # Polar Bear
    "Monodon monoceros",    # Narwhal
    "Vulpes lagopus",       # Arctic Fox
    "Rangifer tarandus",    # Caribou/Reindeer
    "Odobenus rosmarus"     # Walrus
]

class TradeSummaryGenerator:
    """Generate trade summaries for species to improve frontend performance"""
    
    def __init__(self):
        # Use service role key for writing to species_trade_summary table
        self.supabase = get_supabase_client(use_service_role=True)
        self.stats = {
            'species_processed': 0,
            'species_with_trade': 0,
            'species_without_trade': 0,
            'successful_summaries': 0,
            'failed_summaries': 0,
            'total_records_analyzed': 0
        }
        
        # Cache for country names to avoid repetitive lookups
        self.country_name_cache = {}
        
    def get_all_species(self) -> List[Dict]:
        """Get all species from the database"""
        logger.info("Fetching all species from database...")
        
        try:
            # Use common_name instead of primary_common_name
            response = self.supabase.table('species').select('id, scientific_name, common_name').execute()
            species_list = response.data
            
            logger.info(f"Found {len(species_list)} species")
            return species_list
            
        except Exception as e:
            logger.error(f"Failed to fetch species: {e}")
            return []
            
    def get_priority_species(self) -> List[Dict]:
        """Get only priority species from the database"""
        logger.info(f"Fetching priority species ({', '.join(PRIORITY_SPECIES)})...")
        
        try:
            # Use common_name instead of primary_common_name
            response = self.supabase.table('species').select('id, scientific_name, common_name').in_('scientific_name', PRIORITY_SPECIES).execute()
            species_list = response.data
            
            logger.info(f"Found {len(species_list)} priority species")
            return species_list
            
        except Exception as e:
            logger.error(f"Failed to fetch priority species: {e}")
            return []
    
    def get_species_by_id(self, species_id: str) -> Optional[Dict]:
        """Get a specific species by ID"""
        logger.info(f"Fetching species with ID: {species_id}")
        
        try:
            # Use common_name instead of primary_common_name
            response = self.supabase.table('species').select('id, scientific_name, common_name').eq('id', species_id).execute()
            
            if response.data:
                return response.data[0]
            else:
                logger.error(f"No species found with ID: {species_id}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch species by ID: {e}")
            return None
    
    def check_existing_summaries(self) -> Set[str]:
        """Check which species already have summaries"""
        logger.info("Checking existing trade summaries...")
        
        try:
            response = self.supabase.table('species_trade_summary').select('species_id').execute()
            
            existing_ids = {item['species_id'] for item in response.data}
            logger.info(f"Found {len(existing_ids)} existing summaries")
            return existing_ids
            
        except Exception as e:
            logger.error(f"Failed to check existing summaries: {e}")
            return set()
            
    def get_country_name(self, country_code: str) -> str:
        """Get country name from country code with caching"""
        if not country_code:
            return "Unknown"
            
        # Check cache first
        if country_code in self.country_name_cache:
            return self.country_name_cache[country_code]
            
        # Some special cases
        if country_code == 'XX':
            self.country_name_cache[country_code] = 'XX'
            return 'XX'
        if country_code == 'XV':
            self.country_name_cache[country_code] = 'XV'
            return 'XV'
        if country_code == 'HS':
            self.country_name_cache[country_code] = 'HS'
            return 'HS'
            
        # Try to get from database (would be ideal, but might not be available)
        try:
            # In a real implementation, we would look up the country name
            # For now, we'll just use the code as the name to avoid API calls
            # This could be enhanced later with a proper country database lookup
            self.country_name_cache[country_code] = country_code
            return country_code
        except Exception:
            # If lookup fails, just use the code
            self.country_name_cache[country_code] = country_code
            return country_code
    
    def get_trade_record_counts(self, species_ids: Optional[List[str]] = None) -> Dict[str, int]:
        """Get trade record counts per species"""
        logger.info("Getting trade record counts per species...")
        
        try:
            # Use a direct count query to get accurate counts per species
            try:
                # Execute a more efficient query to get counts by species_id
                logger.info("Executing direct count query...")
                
                # We'll use separate queries for each species to avoid timeouts
                counts = {}
                total_analyzed = 0
                
                if species_ids:
                    species_to_check = species_ids
                else:
                    # Get all species IDs if not provided
                    species_response = self.supabase.table('species').select('id').execute()
                    species_to_check = [s['id'] for s in species_response.data]
                
                logger.info(f"Counting records for {len(species_to_check)} species...")
                
                # Process in batches to avoid timeouts
                batch_size = 5
                for i in range(0, len(species_to_check), batch_size):
                    batch = species_to_check[i:i+batch_size]
                    logger.info(f"Processing batch {i//batch_size + 1}/{(len(species_to_check) + batch_size - 1)//batch_size}")
                    
                    for species_id in batch:
                        # Get count for this species
                        count_response = self.supabase.table('cites_trade_records').select('id', count='exact').eq('species_id', species_id).execute()
                        record_count = count_response.count if hasattr(count_response, 'count') else 0
                        
                        if record_count > 0:
                            counts[species_id] = record_count
                            total_analyzed += record_count
                            logger.info(f"  Species {species_id}: {record_count} records")
                
                self.stats['total_records_analyzed'] = total_analyzed
                logger.info(f"Found {total_analyzed:,} total records across {len(counts)} species")
                return counts
                
            except Exception as count_e:
                logger.warning(f"Efficient counting failed: {count_e}, falling back to slower method")
                
                # Fallback to standard API query with pagination
                counts = {}
                total_records = 0
                
                # Process each species individually to avoid hitting API limits
                if species_ids:
                    species_to_process = species_ids
                else:
                    # Get all species IDs if not provided
                    species_response = self.supabase.table('species').select('id').execute()
                    species_to_process = [s['id'] for s in species_response.data]
                
                for species_id in species_to_process:
                    # Get count for this species with pagination
                    page_size = 1000
                    offset = 0
                    species_count = 0
                    
                    while True:
                        page_response = self.supabase.table('cites_trade_records') \
                            .select('id') \
                            .eq('species_id', species_id) \
                            .range(offset, offset + page_size - 1) \
                            .execute()
                            
                        page_records = page_response.data
                        if not page_records:
                            break
                            
                        page_count = len(page_records)
                        species_count += page_count
                        offset += page_size
                        
                        # If we got fewer records than the page size, we're done
                        if page_count < page_size:
                            break
                    
                    if species_count > 0:
                        counts[species_id] = species_count
                        total_records += species_count
                        logger.info(f"  Species {species_id}: {species_count} records")
                
                self.stats['total_records_analyzed'] = total_records
                logger.info(f"Analyzed {total_records:,} trade records across {len(counts)} species via API")
                return counts
            
        except Exception as e:
            logger.error(f"Failed to get trade record counts: {e}")
            return {}
    
    def generate_summary_for_species(self, species_id: str, species_name: str) -> bool:
        """Generate a trade summary for a single species"""
        logger.info(f"Generating summary for {species_name} (ID: {species_id})...")
        
        try:
            # Get trade records for this species with pagination
            page_size = 1000
            offset = 0
            all_records = []
            
            # First get total count to better track progress
            count_response = self.supabase.table('cites_trade_records') \
                .select('id', count='exact') \
                .eq('species_id', species_id) \
                .execute()
            
            total_expected = count_response.count if hasattr(count_response, 'count') else 0
            logger.info(f"Expected record count for {species_name}: {total_expected:,}")
            
            # Loop through pages until we get all records
            while True:
                logger.info(f"Fetching records {offset+1}-{offset+page_size}...")
                
                page_response = self.supabase.table('cites_trade_records') \
                    .select('*') \
                    .eq('species_id', species_id) \
                    .range(offset, offset + page_size - 1) \
                    .execute()
                
                page_records = page_response.data
                if not page_records:
                    break
                    
                all_records.extend(page_records)
                offset += page_size
                
                # Log progress
                logger.info(f"  Retrieved {len(all_records):,} records so far ({len(all_records) / max(1, total_expected) * 100:.1f}%)")
                
                # If we got fewer records than the page size, we're done
                if len(page_records) < page_size:
                    break
            
            if not all_records:
                logger.warning(f"No trade records found for {species_name}")
                self.stats['species_without_trade'] += 1
                return False
                
            records = all_records
            logger.info(f"Processing {len(records):,} trade records")
            
            # Calculate year range
            years = [r.get('year') for r in records if r.get('year')]
            min_year = min(years) if years else None
            max_year = max(years) if years else None
            
            # Calculate total quantity
            total_quantity = 0
            for record in records:
                if record.get('quantity'):
                    try:
                        total_quantity += float(record['quantity'])
                    except (ValueError, TypeError):
                        pass
            
            # Aggregate by years - list of years
            distinct_years = sorted(list(set(years)))
            
            # Aggregate by terms - list of terms
            terms_set = set()
            for record in records:
                term = record.get('term', 'Unknown')
                if not term:
                    term = 'Unknown'
                terms_set.add(term)
            distinct_terms = sorted(list(terms_set))
            
            # Aggregate by countries - list of objects with code and name
            importer_dict = {}
            exporter_dict = {}
            for record in records:
                importer = record.get('importer', '')
                exporter = record.get('exporter', '')
                
                if importer:
                    if importer not in importer_dict:
                        importer_dict[importer] = {'code': importer, 'name': self.get_country_name(importer)}
                    
                if exporter:
                    if exporter not in exporter_dict:
                        exporter_dict[exporter] = {'code': exporter, 'name': self.get_country_name(exporter)}
            
            distinct_importers = list(importer_dict.values())
            distinct_exporters = list(exporter_dict.values())
            
            # Generate annual summaries
            annual_summaries = []
            for year in sorted(set(years)):
                year_records = [r for r in records if r.get('year') == year]
                
                # Terms summary
                terms_summary = []
                term_counts = {}
                term_quantities = {}
                
                for record in year_records:
                    term = record.get('term', 'Unknown')
                    if not term:
                        term = 'Unknown'
                        
                    if term not in term_counts:
                        term_counts[term] = 0
                        term_quantities[term] = 0
                        
                    term_counts[term] += 1
                    
                    if record.get('quantity'):
                        try:
                            term_quantities[term] += float(record['quantity'])
                        except (ValueError, TypeError):
                            pass
                
                for term, count in term_counts.items():
                    terms_summary.append({
                        'term': term,
                        'records': count,
                        'quantity': term_quantities[term]
                    })
                
                # Sources summary
                sources_summary = []
                source_counts = {}
                source_quantities = {}
                
                for record in year_records:
                    source = record.get('source', 'unknown')
                    if not source:
                        source = 'unknown'
                        
                    if source not in source_counts:
                        source_counts[source] = 0
                        source_quantities[source] = 0
                        
                    source_counts[source] += 1
                    
                    if record.get('quantity'):
                        try:
                            source_quantities[source] += float(record['quantity'])
                        except (ValueError, TypeError):
                            pass
                
                for source, count in source_counts.items():
                    sources_summary.append({
                        'records': count,
                        'quantity': source_quantities[source],
                        'source_code': source
                    })
                
                # Purposes summary
                purposes_summary = []
                purpose_counts = {}
                purpose_quantities = {}
                
                for record in year_records:
                    purpose = record.get('purpose', 'unknown')
                    if not purpose:
                        purpose = 'unknown'
                        
                    if purpose not in purpose_counts:
                        purpose_counts[purpose] = 0
                        purpose_quantities[purpose] = 0
                        
                    purpose_counts[purpose] += 1
                    
                    if record.get('quantity'):
                        try:
                            purpose_quantities[purpose] += float(record['quantity'])
                        except (ValueError, TypeError):
                            pass
                
                for purpose, count in purpose_counts.items():
                    purposes_summary.append({
                        'records': count,
                        'quantity': purpose_quantities[purpose],
                        'purpose_code': purpose
                    })
                
                # Exporters summary
                exporters_summary = []
                exporter_counts = {}
                exporter_quantities = {}
                
                for record in year_records:
                    exporter = record.get('exporter', '')
                    if not exporter:
                        continue
                        
                    if exporter not in exporter_counts:
                        exporter_counts[exporter] = 0
                        exporter_quantities[exporter] = 0
                        
                    exporter_counts[exporter] += 1
                    
                    if record.get('quantity'):
                        try:
                            exporter_quantities[exporter] += float(record['quantity'])
                        except (ValueError, TypeError):
                            pass
                
                for exporter, count in exporter_counts.items():
                    exporters_summary.append({
                        'records': count,
                        'quantity': exporter_quantities[exporter],
                        'exporter_code': exporter
                    })
                
                # Importers summary
                importers_summary = []
                importer_counts = {}
                importer_quantities = {}
                
                for record in year_records:
                    importer = record.get('importer', '')
                    if not importer:
                        continue
                        
                    if importer not in importer_counts:
                        importer_counts[importer] = 0
                        importer_quantities[importer] = 0
                        
                    importer_counts[importer] += 1
                    
                    if record.get('quantity'):
                        try:
                            importer_quantities[importer] += float(record['quantity'])
                        except (ValueError, TypeError):
                            pass
                
                for importer, count in importer_counts.items():
                    importers_summary.append({
                        'records': count,
                        'quantity': importer_quantities[importer],
                        'importer_code': importer
                    })
                
                # Calculate total quantity for year
                total_quantity_for_year = sum(
                    float(record['quantity']) for record in year_records 
                    if record.get('quantity') is not None
                )
                
                year_summary = {
                    'year': year,
                    'terms_summary': terms_summary,
                    'sources_summary': sources_summary,
                    'purposes_summary': purposes_summary,
                    'exporters_summary': exporters_summary,
                    'importers_summary': importers_summary,
                    'total_records_for_year': len(year_records),
                    'total_quantity_for_year': total_quantity_for_year
                }
                
                annual_summaries.append(year_summary)
            
            # Prepare summary based on actual database schema
            summary = {
                'species_id': species_id,
                'last_updated_at': datetime.now().isoformat(),
                'total_trade_records': len(records),
                'overall_min_year': min_year,
                'overall_max_year': max_year,
                'overall_total_quantity': total_quantity,
                # Store directly as JSON-compatible structures - Supabase will handle serialization
                'distinct_years': distinct_years,
                'distinct_terms': distinct_terms,
                'distinct_importers': distinct_importers,
                'distinct_exporters': distinct_exporters,
                'annual_summaries': annual_summaries
            }
            
            try:
                # Validate JSON structures before saving
                # This helps catch any serialization issues early
                try:
                    # Test JSON serialization 
                    json.dumps(summary)
                except Exception as json_err:
                    logger.error(f"JSON serialization error: {json_err}")
                    # Try to identify the problematic fields
                    for field in ['distinct_years', 'distinct_terms', 'distinct_importers', 
                                 'distinct_exporters', 'annual_summaries']:
                        try:
                            json.dumps(summary[field])
                        except Exception:
                            logger.error(f"Error in field: {field}")
                            # Sanitize the field if possible
                            if field == 'annual_summaries':
                                # Try to sanitize annual summaries by removing problematic records
                                summary[field] = []
                            else:
                                # Reset to empty for other fields
                                summary[field] = []
                    
                # Check if summary already exists directly by species_id
                logger.info(f"Checking if summary exists for species {species_id}")
                existing_response = self.supabase.table('species_trade_summary').select('*').eq('species_id', species_id).execute()
                
                if existing_response.data:
                    # Update existing summary - use species_id as the key
                    logger.info(f"Updating existing summary for species_id: {species_id}")
                    update_response = self.supabase.table('species_trade_summary').update(summary).eq('species_id', species_id).execute()
                    
                    if update_response.data:
                        logger.info(f"Successfully updated summary for {species_name}")
                        self.stats['successful_summaries'] += 1
                        return True
                    else:
                        logger.error(f"Failed to update summary for {species_name}")
                        # Log more details about the error
                        logger.error(f"Update response: {update_response}")
                        self.stats['failed_summaries'] += 1
                        return False
                else:
                    # Insert new summary
                    logger.info(f"Inserting new summary for {species_name}")
                    insert_response = self.supabase.table('species_trade_summary').insert(summary).execute()
                    
                    if insert_response.data:
                        logger.info(f"Successfully created summary for {species_name}")
                        self.stats['successful_summaries'] += 1
                        return True
                    else:
                        logger.error(f"Failed to create summary for {species_name}")
                        # Log more details about the error
                        logger.error(f"Insert response: {insert_response}")
                        self.stats['failed_summaries'] += 1
                        return False
                        
            except Exception as e:
                logger.error(f"Database operation failed for {species_name}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                self.stats['failed_summaries'] += 1
                return False
                
        except Exception as e:
            logger.error(f"Error generating summary for {species_name}: {e}")
            self.stats['failed_summaries'] += 1
            return False
    
    def generate_all_summaries(self, priority_only: bool = False, species_id: Optional[str] = None) -> bool:
        """Generate trade summaries for all or selected species"""
        logger.info("Starting trade summary generation process...")
        
        if species_id:
            # Generate for a single species
            species = self.get_species_by_id(species_id)
            if not species:
                logger.error(f"Could not find species with ID: {species_id}")
                return False
                
            species_list = [species]
            logger.info(f"Generating summary for single species: {species['scientific_name']}")
            
        elif priority_only:
            # Generate for priority species only
            species_list = self.get_priority_species()
            logger.info(f"Generating summaries for {len(species_list)} priority species")
            
        else:
            # Generate for all species
            species_list = self.get_all_species()
            logger.info(f"Generating summaries for all {len(species_list)} species")
        
        # Check existing summaries
        existing_summaries = self.check_existing_summaries()
        
        # Get trade record counts for prioritization
        if species_list:
            species_ids = [s['id'] for s in species_list]
            trade_counts = self.get_trade_record_counts(species_ids)
        else:
            # Empty species list
            logger.warning("No species found to process")
            trade_counts = {}
        
        # Sort species by trade count (highest first)
        species_list_with_counts = []
        for species in species_list:
            species_id = species['id']
            count = trade_counts.get(species_id, 0)
            
            species_list_with_counts.append({
                'id': species_id,
                'scientific_name': species['scientific_name'],
                'common_name': species.get('common_name', ''),
                'trade_count': count
            })
        
        # Sort by trade count (highest first)
        species_list_with_counts.sort(key=lambda x: x['trade_count'], reverse=True)
        
        # Process each species
        for species in species_list_with_counts:
            self.stats['species_processed'] += 1
            
            species_id = species['id']
            display_name = species['common_name'] or species['scientific_name']
            
            # Skip species with no trade records
            if species['trade_count'] == 0:
                logger.info(f"Skipping {display_name} (no trade records)")
                self.stats['species_without_trade'] += 1
                continue
                
            # Generate summary
            self.stats['species_with_trade'] += 1
            logger.info(f"Processing {display_name} ({species['trade_count']:,} records)")
            
            success = self.generate_summary_for_species(species_id, display_name)
            if not success:
                logger.warning(f"Failed to generate summary for {display_name}")
        
        # Print summary statistics
        logger.info("\n" + "="*50)
        logger.info("TRADE SUMMARY GENERATION COMPLETED")
        logger.info("="*50)
        logger.info(f"Species processed: {self.stats['species_processed']}")
        logger.info(f"Species with trade data: {self.stats['species_with_trade']}")
        logger.info(f"Species without trade data: {self.stats['species_without_trade']}")
        logger.info(f"Successful summaries: {self.stats['successful_summaries']}")
        logger.info(f"Failed summaries: {self.stats['failed_summaries']}")
        logger.info(f"Total records analyzed: {self.stats['total_records_analyzed']:,}")
        logger.info("="*50)
        
        return self.stats['failed_summaries'] == 0

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate trade summaries for species')
    
    parser.add_argument('--priority-only', action='store_true',
                        help='Only generate summaries for priority species')
    
    parser.add_argument('--species-id',
                        help='Generate summary for a specific species ID')
    
    args = parser.parse_args()
    
    # Initialize and run generator
    generator = TradeSummaryGenerator()
    success = generator.generate_all_summaries(
        priority_only=args.priority_only,
        species_id=args.species_id
    )
    
    if success:
        logger.info("All summaries generated successfully!")
        return 0
    else:
        logger.warning("Some summaries failed to generate. Check the log for details.")
        return 1

if __name__ == "__main__":
    # Print a notice to the user before starting
    print("\n" + "="*70)
    print("📊 Trade Summary Generator")
    print("="*70)
    print("This script will generate pre-aggregated trade summaries for species.")
    print("These summaries will improve frontend performance significantly.")
    print("The operation is safe and can be run multiple times.\n")
    print("For fastest results, use the priority mode:")
    print("  python generate_trade_summaries.py --priority-only\n")
    print("This will focus on high-traffic species first.")
    print("="*70 + "\n")
    
    sys.exit(main())