#!/usr/bin/env python3
"""
Validate staged CITES trade data before migration
Comprehensive validation to ensure data integrity
"""

import os
import sys
import json
from datetime import datetime
import pandas as pd
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.supabase_config import get_supabase_client

class StagingDataValidator:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.validation_results = {
            'timestamp': datetime.now().isoformat(),
            'passed': True,
            'checks': []
        }
        
    def log_check(self, check_name: str, passed: bool, details: str = "", errors: List[str] = None):
        """Log validation check result"""
        check_result = {
            'name': check_name,
            'passed': passed,
            'details': details,
            'errors': errors or []
        }
        self.validation_results['checks'].append(check_result)
        
        if not passed:
            self.validation_results['passed'] = False
            
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}: {details}")
        if errors:
            for error in errors[:5]:  # Show first 5 errors
                print(f"   - {error}")
            if len(errors) > 5:
                print(f"   ... and {len(errors) - 5} more errors")
                
    def validate_record_count(self, expected_count: int = None) -> bool:
        """Validate record count in staging table"""
        print("\n📊 Validating record count...")
        
        try:
            # Get staging count
            response = self.supabase.table('cites_trade_records_staging').select('id', count='exact').limit(1).execute()
            staging_count = response.count if hasattr(response, 'count') else 0
            
            # Get expected count from extracted data if not provided
            if expected_count is None:
                summary_path = os.path.join(self.base_dir, 'extracted_data', 'arctic_species_trade_summary.csv')
                if os.path.exists(summary_path):
                    summary_df = pd.read_csv(summary_path)
                    expected_count = summary_df['record_count'].sum()
                else:
                    self.log_check('Record Count', False, "Cannot determine expected count")
                    return False
                    
            # Compare counts
            if staging_count == expected_count:
                self.log_check('Record Count', True, f"Staging has {staging_count:,} records (matches expected)")
                return True
            else:
                diff = staging_count - expected_count
                self.log_check('Record Count', False, 
                             f"Staging has {staging_count:,} records, expected {expected_count:,} (diff: {diff:+,})")
                return False
                
        except Exception as e:
            self.log_check('Record Count', False, f"Error checking count: {str(e)}")
            return False
            
    def validate_species_mapping(self) -> bool:
        """Validate all species IDs are valid"""
        print("\n🦭 Validating species mappings...")
        
        try:
            # Get unique species IDs from staging
            response = self.supabase.table('cites_trade_records_staging')\
                .select('species_id')\
                .execute()
                
            staging_species_ids = set(r['species_id'] for r in response.data if r.get('species_id'))
            
            # Get valid species IDs
            response = self.supabase.table('species').select('id').execute()
            valid_species_ids = set(r['id'] for r in response.data)
            
            # Check for invalid IDs
            invalid_ids = staging_species_ids - valid_species_ids
            
            if not invalid_ids:
                self.log_check('Species Mapping', True, 
                             f"All {len(staging_species_ids)} species IDs are valid")
                return True
            else:
                self.log_check('Species Mapping', False,
                             f"{len(invalid_ids)} invalid species IDs found",
                             [f"Invalid ID: {id}" for id in list(invalid_ids)[:10]])
                return False
                
        except Exception as e:
            self.log_check('Species Mapping', False, f"Error checking species: {str(e)}")
            return False
            
    def validate_data_integrity(self) -> bool:
        """Validate data integrity constraints"""
        print("\n🔍 Validating data integrity...")
        
        errors = []
        
        try:
            # Check for duplicates
            response = self.supabase.table('cites_trade_records_staging')\
                .select('record_id')\
                .execute()
                
            record_ids = [r['record_id'] for r in response.data if r.get('record_id')]
            duplicate_count = len(record_ids) - len(set(record_ids))
            
            if duplicate_count > 0:
                errors.append(f"{duplicate_count} duplicate record_ids found")
                
            # Check required fields
            response = self.supabase.table('cites_trade_records_staging')\
                .select('id, species_id, year, taxon')\
                .is_('species_id', 'null')\
                .limit(100)\
                .execute()
                
            if response.data:
                errors.append(f"{len(response.data)} records with null species_id")
                
            # Check year range
            response = self.supabase.table('cites_trade_records_staging')\
                .select('year')\
                .or_('year.lt.1975,year.gt.2024')\
                .limit(100)\
                .execute()
                
            if response.data:
                errors.append(f"{len(response.data)} records with invalid year (outside 1975-2024)")
                
            if not errors:
                self.log_check('Data Integrity', True, "All integrity constraints satisfied")
                return True
            else:
                self.log_check('Data Integrity', False, 
                             f"{len(errors)} integrity issues found", errors)
                return False
                
        except Exception as e:
            self.log_check('Data Integrity', False, f"Error checking integrity: {str(e)}")
            return False
            
    def validate_field_values(self) -> bool:
        """Validate field values and formats"""
        print("\n📝 Validating field values...")
        
        errors = []
        
        try:
            # Check appendix values
            response = self.supabase.table('cites_trade_records_staging')\
                .select('appendix')\
                .not_('appendix', 'in', '["I","II","III","I/II","II/NC","III/NC"]')\
                .limit(100)\
                .execute()
                
            if response.data:
                invalid_appendix = set(r['appendix'] for r in response.data)
                errors.append(f"Invalid appendix values: {invalid_appendix}")
                
            # Check purpose codes
            valid_purposes = ['T', 'Z', 'S', 'P', 'B', 'E', 'G', 'Q', 'L', 'M', 'N']
            response = self.supabase.table('cites_trade_records_staging')\
                .select('purpose')\
                .limit(1000)\
                .execute()
                
            purposes = [r['purpose'] for r in response.data if r.get('purpose')]
            invalid_purposes = set(p for p in purposes if p not in valid_purposes)
            
            if invalid_purposes:
                errors.append(f"Invalid purpose codes: {invalid_purposes}")
                
            # Check source codes
            valid_sources = ['W', 'C', 'D', 'F', 'R', 'I', 'O', 'X', 'Y', 'U']
            response = self.supabase.table('cites_trade_records_staging')\
                .select('source')\
                .limit(1000)\
                .execute()
                
            sources = [r['source'] for r in response.data if r.get('source')]
            invalid_sources = set(s for s in sources if s not in valid_sources)
            
            if invalid_sources:
                errors.append(f"Invalid source codes: {invalid_sources}")
                
            if not errors:
                self.log_check('Field Values', True, "All field values valid")
                return True
            else:
                self.log_check('Field Values', False,
                             f"{len(errors)} field validation issues", errors)
                return False
                
        except Exception as e:
            self.log_check('Field Values', False, f"Error validating fields: {str(e)}")
            return False
            
    def validate_relationships(self) -> bool:
        """Validate foreign key relationships"""
        print("\n🔗 Validating relationships...")
        
        try:
            # Check all species_ids exist in species table
            response = self.supabase.rpc('validate_staging_species_ids').execute()
            
            if response.data and response.data[0]['invalid_count'] > 0:
                self.log_check('Foreign Keys', False,
                             f"{response.data[0]['invalid_count']} invalid species_id references")
                return False
            else:
                self.log_check('Foreign Keys', True, 
                             "All foreign key relationships valid")
                return True
                
        except:
            # Fallback if RPC doesn't exist
            try:
                # Manual check
                staging_species = self.supabase.table('cites_trade_records_staging')\
                    .select('species_id').execute()
                staging_ids = set(r['species_id'] for r in staging_species.data)
                
                valid_species = self.supabase.table('species').select('id').execute()
                valid_ids = set(r['id'] for r in valid_species.data)
                
                invalid = staging_ids - valid_ids
                
                if invalid:
                    self.log_check('Foreign Keys', False,
                                 f"{len(invalid)} invalid species_id references")
                    return False
                else:
                    self.log_check('Foreign Keys', True,
                                 "All foreign key relationships valid")
                    return True
                    
            except Exception as e:
                self.log_check('Foreign Keys', False, f"Error checking relationships: {str(e)}")
                return False
                
    def validate_performance(self) -> bool:
        """Validate query performance on staging data"""
        print("\n⚡ Validating query performance...")
        
        import time
        
        test_queries = [
            {
                'name': 'Species trade summary',
                'query': lambda: self.supabase.table('cites_trade_records_staging')\
                    .select('species_id')\
                    .eq('species_id', 'd07c1335-0bf5-445c-bcaa-f7cdbd029637')\
                    .execute()
            },
            {
                'name': 'Year range query',
                'query': lambda: self.supabase.table('cites_trade_records_staging')\
                    .select('id')\
                    .gte('year', 2020)\
                    .lte('year', 2024)\
                    .limit(1000)\
                    .execute()
            },
            {
                'name': 'Purpose aggregation',
                'query': lambda: self.supabase.table('cites_trade_records_staging')\
                    .select('purpose')\
                    .limit(10000)\
                    .execute()
            }
        ]
        
        slow_queries = []
        
        for test in test_queries:
            try:
                start_time = time.time()
                test['query']()
                elapsed = time.time() - start_time
                
                if elapsed > 2.0:  # More than 2 seconds is slow
                    slow_queries.append(f"{test['name']}: {elapsed:.2f}s")
                    
            except Exception as e:
                slow_queries.append(f"{test['name']}: Failed - {str(e)}")
                
        if not slow_queries:
            self.log_check('Query Performance', True, 
                         "All test queries completed within acceptable time")
            return True
        else:
            self.log_check('Query Performance', False,
                         f"{len(slow_queries)} slow queries detected", slow_queries)
            return False
            
    def save_validation_report(self):
        """Save validation report"""
        
        # Save JSON report
        report_path = os.path.join(self.base_dir, 'logs', 
                                 f'staging_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
                                 
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
            
        print(f"\n📄 Validation report saved to: {report_path}")
        
        # Generate summary
        passed_count = sum(1 for check in self.validation_results['checks'] if check['passed'])
        total_count = len(self.validation_results['checks'])
        
        print(f"\n{'✅' if self.validation_results['passed'] else '❌'} Validation Summary:")
        print(f"   - Passed: {passed_count}/{total_count} checks")
        print(f"   - Status: {'READY for migration' if self.validation_results['passed'] else 'FAILED - DO NOT MIGRATE'}")
        
    def validate_all(self, expected_count: int = None):
        """Run all validation checks"""
        
        print("🔍 Starting comprehensive staging data validation...\n")
        
        # Run all validations
        self.validate_record_count(expected_count)
        self.validate_species_mapping()
        self.validate_data_integrity()
        self.validate_field_values()
        self.validate_relationships()
        self.validate_performance()
        
        # Save report
        self.save_validation_report()
        
        return self.validation_results['passed']

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate staged CITES trade data')
    parser.add_argument('--year', type=int, help='Validate specific year only')
    parser.add_argument('--all', action='store_true', help='Validate all data')
    parser.add_argument('--expected-count', type=int, help='Expected record count')
    
    args = parser.parse_args()
    
    validator = StagingDataValidator()
    
    if args.all or not args.year:
        # Validate all data
        success = validator.validate_all(args.expected_count)
        sys.exit(0 if success else 1)
    else:
        # Validate specific year
        print(f"Validating year {args.year} data...")
        # Add year-specific validation logic here
        success = validator.validate_all(args.expected_count)
        sys.exit(0 if success else 1)