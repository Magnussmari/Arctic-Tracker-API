#!/usr/bin/env python3
"""
IUCN API Species Assessment Script - Rebuild Version

This script uses the new rebuild architecture to fetch IUCN Red List assessments
for Arctic species missing IUCN data. It integrates with the centralized configuration
system and provides proper error handling and rate limiting.

Usage:
    python rebuild_iucn_assessments.py [--input-file species_status.csv] [--output-file iucn_assessments.json]
"""

import sys
import os
import json
import csv
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any

# Add rebuild directory to path
rebuild_dir = Path(__file__).parent.parent
sys.path.insert(0, str(rebuild_dir))

from config import get_cached_settings
from core.iucn_client import IUCNApiClient

async def load_species_missing_assessments(input_file: str) -> List[Dict[str, Any]]:
    """
    Load species that are missing IUCN assessments from CSV file
    
    Args:
        input_file (str): Path to species status CSV file
        
    Returns:
        List[Dict[str, Any]]: List of species missing IUCN assessments
    """
    missing_species = []
    
    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        return missing_species
    
    try:
        with open(input_file, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Check if species is missing IUCN assessment
                if row.get('has_iucn_assessment', '').strip().lower() == 'false':
                    missing_species.append(row)
        
        print(f"Loaded {len(missing_species)} species missing IUCN assessments from {input_file}")
        
    except Exception as e:
        print(f"Error reading input file: {e}")
    
    return missing_species

async def fetch_iucn_assessments(species_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetch IUCN assessments for a list of species
    
    Args:
        species_list (List[Dict[str, Any]]): List of species to process
        
    Returns:
        List[Dict[str, Any]]: Assessment results
    """
    print(f"\n🔍 Fetching IUCN assessments for {len(species_list)} species...")
    print("=" * 60)
    
    results = []
    
    async with IUCNApiClient() as iucn_client:
        # Test API connection first
        try:
            version_info = await iucn_client.get_api_version()
            print(f"✅ IUCN API Version: {version_info.get('version', 'Unknown')}")
            print(f"📋 Processing species assessments...\n")
        except Exception as e:
            print(f"❌ Failed to connect to IUCN API: {e}")
            return results
        
        # Process species in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(species_list), batch_size):
            batch = species_list[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} ({len(batch)} species)...")
            
            batch_results = await iucn_client.process_species_list(batch)
            results.extend(batch_results)
            
            # Small delay between batches
            if i + batch_size < len(species_list):
                await asyncio.sleep(2)
        
        print(f"\n✅ Completed processing {len(results)} assessment records")
    
    return results

async def save_results(results: List[Dict[str, Any]], output_file: str) -> bool:
    """
    Save assessment results to JSON file
    
    Args:
        results (List[Dict[str, Any]]): Assessment results
        output_file (str): Output file path
        
    Returns:
        bool: True if saved successfully
    """
    try:
        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(results)} assessment records to {output_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving results: {e}")
        return False

def generate_summary_report(results: List[Dict[str, Any]]) -> None:
    """
    Generate a summary report of the assessment results
    
    Args:
        results (List[Dict[str, Any]]): Assessment results
    """
    print(f"\n📊 IUCN ASSESSMENT SUMMARY REPORT")
    print("=" * 50)
    
    # Count by category
    categories = {}
    errors = 0
    not_listed = 0
    
    for result in results:
        category = result.get('category', 'Unknown')
        if category == 'Error':
            errors += 1
        elif category == 'Not Listed':
            not_listed += 1
        else:
            categories[category] = categories.get(category, 0) + 1
    
    print(f"Total assessments processed: {len(results)}")
    print(f"")
    
    if categories:
        print("IUCN Red List Categories:")
        for category, count in sorted(categories.items()):
            print(f"  🔶 {category}: {count}")
    
    if not_listed > 0:
        print(f"  ⚪ Not Listed: {not_listed}")
    
    if errors > 0:
        print(f"  ❌ Errors: {errors}")
    
    print(f"")
    
    # Show most common categories
    if categories:
        most_common = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:3]
        print("Most common conservation statuses:")
        for category, count in most_common:
            percentage = (count / len(results)) * 100
            print(f"  • {category}: {count} ({percentage:.1f}%)")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Fetch IUCN Red List assessments for Arctic species')
    parser.add_argument('--input-file', '-i', 
                       default='../data/species_status.csv',
                       help='Input CSV file with species data')
    parser.add_argument('--output-file', '-o',
                       default='../rebuild/species_data/processed/iucn_assessments_rebuild.json',
                       help='Output JSON file for assessment results')
    parser.add_argument('--limit', '-l', type=int,
                       help='Limit number of species to process (for testing)')
    
    args = parser.parse_args()
    
    print("🌍 Arctic Species IUCN Assessment Fetcher - Rebuild Version")
    print("=" * 65)
    
    try:
        # Load configuration
        settings = get_cached_settings()
        print(f"✅ Configuration loaded successfully")
        
        if not settings.api.iucn_api_token:
            print("❌ Error: IUCN API token not configured")
            print("Please set IUCN_API_TOKEN in your .env file")
            return
        
        # Load species data
        species_list = await load_species_missing_assessments(args.input_file)
        
        if not species_list:
            print("No species found to process. Exiting.")
            return
        
        # Apply limit if specified
        if args.limit:
            species_list = species_list[:args.limit]
            print(f"Limited to {len(species_list)} species for testing")
        
        # Fetch assessments
        results = await fetch_iucn_assessments(species_list)
        
        if results:
            # Save results
            success = await save_results(results, args.output_file)
            
            if success:
                # Generate summary report
                generate_summary_report(results)
                
                print(f"\n🎉 Assessment fetching completed successfully!")
                print(f"📁 Results saved to: {args.output_file}")
            else:
                print(f"\n❌ Failed to save results")
        else:
            print(f"\n⚠️  No results obtained")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())