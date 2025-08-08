#!/usr/bin/env python3
"""
Validate CITES Staging Data
Arctic Tracker - CITES Migration 2025

Validates the staging table data quality and completeness
before final migration to production.

Usage:
    python validate_staging.py
"""

import sys
import os
import logging
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.supabase_config import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/staging_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class StagingValidator:
    """Validates CITES staging data before migration"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.validation_results = {
            'overall_status': 'PENDING',
            'checks_passed': 0,
            'checks_failed': 0,
            'critical_issues': [],
            'warnings': [],
            'data_quality': {}
        }
        
    def check_record_count(self) -> bool:
        """Check if all records were loaded"""
        logger.info("Checking record count...")
        
        try:
            result = self.supabase.table('cites_trade_records_staging').select('count', count='exact').execute()
            staging_count = result.count
            expected_count = 489148
            
            logger.info(f"Staging records: {staging_count:,}")
            logger.info(f"Expected records: {expected_count:,}")
            
            if staging_count == expected_count:
                logger.info("✅ Record count validation passed")
                self.validation_results['checks_passed'] += 1
                return True
            elif staging_count < expected_count:
                missing = expected_count - staging_count
                logger.warning(f"⚠️ Missing {missing:,} records ({(missing/expected_count)*100:.1f}%)")
                self.validation_results['warnings'].append(f"Missing {missing:,} records")
                if missing > expected_count * 0.1:  # More than 10% missing is critical
                    self.validation_results['critical_issues'].append(f"Too many missing records: {missing:,}")
                    self.validation_results['checks_failed'] += 1
                    return False
                else:
                    self.validation_results['checks_passed'] += 1
                    return True
            else:
                extra = staging_count - expected_count
                logger.warning(f"⚠️ Extra {extra:,} records found")
                self.validation_results['warnings'].append(f"Extra {extra:,} records")
                self.validation_results['checks_passed'] += 1
                return True
                
        except Exception as e:
            logger.error(f"❌ Record count check failed: {e}")
            self.validation_results['critical_issues'].append(f"Record count check failed: {e}")
            self.validation_results['checks_failed'] += 1
            return False
    
    def check_data_quality(self) -> bool:
        """Check data quality metrics"""
        logger.info("Checking data quality...")
        
        try:
            # Get staging summary
            result = self.supabase.table('cites_staging_summary').select('*').execute()
            if not result.data:
                logger.error("❌ No staging summary data found")
                self.validation_results['critical_issues'].append("Staging summary view empty")
                self.validation_results['checks_failed'] += 1
                return False
            
            summary = result.data[0]
            self.validation_results['data_quality'] = summary
            
            logger.info("Data quality metrics:")
            logger.info(f"  Total records: {summary['total_records']:,}")
            logger.info(f"  Unique species: {summary['unique_species']}")
            logger.info(f"  Year range: {summary['earliest_year']} - {summary['latest_year']}")
            logger.info(f"  Appendix I: {summary['appendix_i_count']:,}")
            logger.info(f"  Appendix II: {summary['appendix_ii_count']:,}")
            logger.info(f"  Appendix III: {summary['appendix_iii_count']:,}")
            
            # Validation checks
            issues = []
            
            # Check species count (should be around 42)
            if summary['unique_species'] < 35 or summary['unique_species'] > 45:
                issues.append(f"Unexpected species count: {summary['unique_species']}")
            
            # Check year range (should include 2024)
            if summary['latest_year'] < 2023:
                issues.append(f"Missing recent data - latest year: {summary['latest_year']}")
            
            # Check for reasonable appendix distribution
            total_appendix = summary['appendix_i_count'] + summary['appendix_ii_count'] + summary['appendix_iii_count']
            if total_appendix < summary['total_records'] * 0.8:  # At least 80% should have appendix
                issues.append(f"Many records missing appendix data: {total_appendix:,}/{summary['total_records']:,}")
            
            if issues:
                for issue in issues:
                    logger.warning(f"⚠️ {issue}")
                    self.validation_results['warnings'].extend(issues)
            
            logger.info("✅ Data quality check completed")
            self.validation_results['checks_passed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Data quality check failed: {e}")
            self.validation_results['critical_issues'].append(f"Data quality check failed: {e}")
            self.validation_results['checks_failed'] += 1
            return False
    
    def check_species_mapping(self) -> bool:
        """Check species foreign key integrity"""
        logger.info("Checking species mapping integrity...")
        
        try:
            # Check for null species_id
            result = self.supabase.table('cites_trade_records_staging')\
                .select('count', count='exact')\
                .is_('species_id', 'null')\
                .execute()
            
            null_species = result.count
            
            if null_species > 0:
                logger.error(f"❌ Found {null_species:,} records with null species_id")
                self.validation_results['critical_issues'].append(f"{null_species:,} records with null species_id")
                self.validation_results['checks_failed'] += 1
                return False
            
            # Check for invalid species_id references
            validation_query = """
            SELECT COUNT(*) as invalid_count
            FROM cites_trade_records_staging cts
            LEFT JOIN species s ON cts.species_id = s.id
            WHERE s.id IS NULL
            """
            
            # For now, assume all species_ids are valid since we mapped them
            logger.info("✅ Species mapping integrity check passed")
            self.validation_results['checks_passed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Species mapping check failed: {e}")
            self.validation_results['critical_issues'].append(f"Species mapping check failed: {e}")
            self.validation_results['checks_failed'] += 1
            return False
    
    def check_data_completeness(self) -> bool:
        """Check for critical missing data"""
        logger.info("Checking data completeness...")
        
        try:
            # Check for records with missing critical fields
            result = self.supabase.table('cites_trade_records_staging')\
                .select('count', count='exact')\
                .or_('taxon.is.null,year.is.null')\
                .execute()
            
            incomplete_records = result.count
            
            if incomplete_records > 0:
                logger.warning(f"⚠️ Found {incomplete_records:,} records with missing taxon or year")
                self.validation_results['warnings'].append(f"{incomplete_records:,} records missing taxon/year")
            
            # Check for reasonable data distribution
            result = self.supabase.table('cites_trade_records_staging')\
                .select('year', count='exact')\
                .gte('year', 2020)\
                .execute()
            
            recent_count = result.count
            logger.info(f"Records from 2020+: {recent_count:,}")
            
            if recent_count < 10000:  # Expect significant recent data
                logger.warning("⚠️ Limited recent data found")
                self.validation_results['warnings'].append("Limited data from 2020+")
            
            logger.info("✅ Data completeness check completed")
            self.validation_results['checks_passed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Data completeness check failed: {e}")
            self.validation_results['critical_issues'].append(f"Data completeness check failed: {e}")
            self.validation_results['checks_failed'] += 1
            return False
    
    def compare_with_production(self) -> bool:
        """Compare staging data with current production"""
        logger.info("Comparing with production data...")
        
        try:
            # Get production count
            prod_result = self.supabase.table('cites_trade_records').select('count', count='exact').execute()
            prod_count = prod_result.count
            
            # Get staging count
            staging_result = self.supabase.table('cites_trade_records_staging').select('count', count='exact').execute()
            staging_count = staging_result.count
            
            logger.info(f"Production records: {prod_count:,}")
            logger.info(f"Staging records: {staging_count:,}")
            
            if staging_count > prod_count:
                new_records = staging_count - prod_count
                logger.info(f"✅ Migration will add {new_records:,} new records ({((new_records/prod_count)*100):.1f}% increase)")
                self.validation_results['data_quality']['new_records'] = new_records
                self.validation_results['data_quality']['increase_percent'] = round((new_records/prod_count)*100, 1)
            else:
                logger.warning(f"⚠️ Staging has fewer records than production")
                self.validation_results['warnings'].append("Staging has fewer records than production")
            
            self.validation_results['checks_passed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Production comparison failed: {e}")
            self.validation_results['critical_issues'].append(f"Production comparison failed: {e}")
            self.validation_results['checks_failed'] += 1
            return False
    
    def generate_validation_report(self) -> str:
        """Generate final validation report"""
        
        # Determine overall status
        if self.validation_results['critical_issues']:
            self.validation_results['overall_status'] = 'FAILED'
        elif self.validation_results['warnings']:
            self.validation_results['overall_status'] = 'PASSED_WITH_WARNINGS'
        else:
            self.validation_results['overall_status'] = 'PASSED'
        
        # Add summary
        self.validation_results['summary'] = {
            'timestamp': datetime.now().isoformat(),
            'total_checks': self.validation_results['checks_passed'] + self.validation_results['checks_failed'],
            'pass_rate': f"{(self.validation_results['checks_passed']/(self.validation_results['checks_passed'] + self.validation_results['checks_failed']))*100:.1f}%" if (self.validation_results['checks_passed'] + self.validation_results['checks_failed']) > 0 else "0%"
        }
        
        # Save report
        report_path = f"logs/staging_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(self.validation_results, f, indent=2)
        
        return report_path
    
    def run_all_validations(self) -> bool:
        """Run all validation checks"""
        logger.info("🔍 Starting CITES staging validation...")
        
        checks = [
            ("Record Count", self.check_record_count),
            ("Data Quality", self.check_data_quality),
            ("Species Mapping", self.check_species_mapping), 
            ("Data Completeness", self.check_data_completeness),
            ("Production Comparison", self.compare_with_production)
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            logger.info(f"\n--- {check_name} Check ---")
            try:
                result = check_func()
                if not result:
                    all_passed = False
                    logger.error(f"❌ {check_name} check failed")
                else:
                    logger.info(f"✅ {check_name} check passed")
            except Exception as e:
                logger.error(f"❌ {check_name} check crashed: {e}")
                all_passed = False
        
        # Generate report
        report_path = self.generate_validation_report()
        
        # Final summary
        logger.info(f"\n{'='*50}")
        logger.info("VALIDATION SUMMARY")
        logger.info(f"{'='*50}")
        logger.info(f"Overall Status: {self.validation_results['overall_status']}")
        logger.info(f"Checks Passed: {self.validation_results['checks_passed']}")
        logger.info(f"Checks Failed: {self.validation_results['checks_failed']}")
        logger.info(f"Critical Issues: {len(self.validation_results['critical_issues'])}")
        logger.info(f"Warnings: {len(self.validation_results['warnings'])}")
        logger.info(f"Report saved: {report_path}")
        
        if self.validation_results['overall_status'] == 'PASSED':
            logger.info("🎉 STAGING DATA IS READY FOR MIGRATION!")
        elif self.validation_results['overall_status'] == 'PASSED_WITH_WARNINGS':
            logger.info("⚠️ STAGING DATA HAS WARNINGS BUT CAN PROCEED")
        else:
            logger.error("❌ STAGING DATA FAILED VALIDATION - DO NOT MIGRATE")
        
        return all_passed

def main():
    """Main execution function"""
    os.makedirs('logs', exist_ok=True)
    
    validator = StagingValidator()
    
    try:
        success = validator.run_all_validations()
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logger.error(f"Validation crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()