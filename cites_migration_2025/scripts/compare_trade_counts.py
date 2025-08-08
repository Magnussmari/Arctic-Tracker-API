#!/usr/bin/env python3
"""
Compare extracted CITES trade counts with current database counts
Determines if migration is needed based on differences
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.supabase_config import get_supabase_client

class TradeCountComparator:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        
    def load_extracted_counts(self) -> pd.DataFrame:
        """Load the extracted trade summary"""
        summary_path = os.path.join(self.base_dir, 'extracted_data', 'arctic_species_trade_summary.csv')
        return pd.read_csv(summary_path)
        
    def get_database_counts(self, species_list: List[str]) -> Dict[str, Dict]:
        """Get current trade counts from database for each species"""
        print("Querying database for current trade counts...\n")
        
        db_counts = {}
        
        for species_name in species_list:
            print(f"Checking {species_name}...")
            
            try:
                # First get species ID
                species_response = self.supabase.table('species').select('id').eq('scientific_name', species_name).execute()
                
                if not species_response.data:
                    db_counts[species_name] = {
                        'status': 'NOT_IN_DB',
                        'count': 0,
                        'min_year': None,
                        'max_year': None
                    }
                    continue
                    
                species_id = species_response.data[0]['id']
                
                # Get trade record count
                count_response = self.supabase.table('cites_trade_records')\
                    .select('id', count='exact')\
                    .eq('species_id', species_id)\
                    .limit(1)\
                    .execute()
                    
                record_count = count_response.count if hasattr(count_response, 'count') else 0
                
                # Get year range
                min_year_response = self.supabase.table('cites_trade_records')\
                    .select('year')\
                    .eq('species_id', species_id)\
                    .order('year')\
                    .limit(1)\
                    .execute()
                    
                max_year_response = self.supabase.table('cites_trade_records')\
                    .select('year')\
                    .eq('species_id', species_id)\
                    .order('year', desc=True)\
                    .limit(1)\
                    .execute()
                    
                min_year = min_year_response.data[0]['year'] if min_year_response.data else None
                max_year = max_year_response.data[0]['year'] if max_year_response.data else None
                
                db_counts[species_name] = {
                    'status': 'OK',
                    'species_id': species_id,
                    'count': record_count,
                    'min_year': min_year,
                    'max_year': max_year
                }
                
            except Exception as e:
                db_counts[species_name] = {
                    'status': 'ERROR',
                    'error': str(e),
                    'count': 0
                }
                
        return db_counts
        
    def compare_counts(self) -> pd.DataFrame:
        """Compare extracted counts with database counts"""
        # Load extracted data
        extracted_df = self.load_extracted_counts()
        
        # Get unique species names
        species_list = extracted_df['Taxon'].unique().tolist()
        
        # Get database counts
        db_counts = self.get_database_counts(species_list)
        
        # Create comparison dataframe
        comparison_data = []
        
        for _, row in extracted_df.iterrows():
            species_name = row['Taxon']
            extracted_count = row['record_count']
            extracted_min_year = row['min_year']
            extracted_max_year = row['max_year']
            
            db_info = db_counts.get(species_name, {})
            db_count = db_info.get('count', 0)
            db_min_year = db_info.get('min_year')
            db_max_year = db_info.get('max_year')
            
            # Calculate differences
            count_diff = extracted_count - db_count
            count_pct_change = ((extracted_count - db_count) / db_count * 100) if db_count > 0 else float('inf')
            
            # Determine if update is needed
            needs_update = False
            update_reasons = []
            
            if count_diff != 0:
                needs_update = True
                update_reasons.append(f"Count diff: {count_diff:+,}")
                
            if db_max_year and extracted_max_year > db_max_year:
                needs_update = True
                update_reasons.append(f"New data up to {extracted_max_year}")
                
            if db_min_year and extracted_min_year < db_min_year:
                needs_update = True
                update_reasons.append(f"Historical data from {extracted_min_year}")
                
            comparison_data.append({
                'species': species_name,
                'db_count': db_count,
                'extracted_count': extracted_count,
                'count_difference': count_diff,
                'pct_change': count_pct_change,
                'db_years': f"{db_min_year or '?'}-{db_max_year or '?'}",
                'extracted_years': f"{extracted_min_year}-{extracted_max_year}",
                'needs_update': needs_update,
                'update_reason': '; '.join(update_reasons) if update_reasons else 'No change'
            })
            
        comparison_df = pd.DataFrame(comparison_data)
        
        # Sort by absolute count difference
        comparison_df['abs_diff'] = comparison_df['count_difference'].abs()
        comparison_df = comparison_df.sort_values('abs_diff', ascending=False)
        comparison_df = comparison_df.drop('abs_diff', axis=1)
        
        return comparison_df
        
    def generate_report(self):
        """Generate comparison report"""
        print("\n" + "="*80)
        print("CITES TRADE DATA COMPARISON REPORT")
        print("="*80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Run comparison
        comparison_df = self.compare_counts()
        
        # Summary statistics
        total_species = len(comparison_df)
        needs_update = comparison_df['needs_update'].sum()
        no_change = total_species - needs_update
        
        total_db_records = comparison_df['db_count'].sum()
        total_extracted_records = comparison_df['extracted_count'].sum()
        total_new_records = total_extracted_records - total_db_records
        
        print(f"SUMMARY")
        print(f"-------")
        print(f"Total species analyzed: {total_species}")
        print(f"Species needing update: {needs_update} ({needs_update/total_species*100:.1f}%)")
        print(f"Species with no change: {no_change} ({no_change/total_species*100:.1f}%)")
        print(f"\nDatabase records: {total_db_records:,}")
        print(f"Extracted records: {total_extracted_records:,}")
        print(f"New records to add: {total_new_records:+,} ({total_new_records/total_db_records*100:+.1f}%)")
        
        # Species with significant changes
        print(f"\n\nTOP 10 SPECIES WITH MOST NEW RECORDS")
        print(f"------------------------------------")
        top_changes = comparison_df.nlargest(10, 'count_difference')
        
        for _, row in top_changes.iterrows():
            if row['count_difference'] > 0:
                print(f"\n{row['species']}:")
                print(f"  Current: {row['db_count']:,} records")
                print(f"  New: {row['extracted_count']:,} records")
                print(f"  Change: {row['count_difference']:+,} ({row['pct_change']:+.1f}%)")
                print(f"  Reason: {row['update_reason']}")
                
        # Species with new data years
        print(f"\n\nSPECIES WITH NEW YEAR RANGES")
        print(f"-----------------------------")
        year_updates = comparison_df[comparison_df['update_reason'].str.contains('New data up to|Historical data from', na=False)]
        
        for _, row in year_updates.head(10).iterrows():
            print(f"\n{row['species']}:")
            print(f"  Database years: {row['db_years']}")
            print(f"  Extracted years: {row['extracted_years']}")
            print(f"  Reason: {row['update_reason']}")
            
        # Save detailed report
        report_path = os.path.join(self.base_dir, 'docs', 'trade_count_comparison.csv')
        comparison_df.to_csv(report_path, index=False)
        print(f"\n\nDetailed comparison saved to: {report_path}")
        
        # Migration recommendation
        print(f"\n\n{'='*80}")
        print("MIGRATION RECOMMENDATION")
        print("="*80)
        
        if needs_update > 0:
            print(f"✅ MIGRATION RECOMMENDED")
            print(f"\nReasons:")
            print(f"- {needs_update} species have new or updated trade data")
            print(f"- {total_new_records:,} new trade records to add")
            print(f"- Latest data includes 2024 records")
            
            if total_new_records > 10000:
                print(f"\n⚠️  Significant update: {total_new_records/total_db_records*100:.1f}% increase in records")
                print(f"   Recommend thorough testing before production migration")
        else:
            print(f"❌ NO MIGRATION NEEDED")
            print(f"\nAll species trade data is up to date in the database.")
            
        print(f"\n{'='*80}\n")
        
        return comparison_df

if __name__ == "__main__":
    comparator = TradeCountComparator()
    comparison_results = comparator.generate_report()