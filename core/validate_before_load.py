#!/usr/bin/env python3
"""
Pre-Load Validation Script

This script validates the optimized trade data and database state before
running the main loader. It ensures everything is ready for a safe data reload.

NOTE: This script uses the 'optimized_species' directory which contains the complete
set of 44 optimized trade data files, including two files that were missing from
the original 'optimized' directory:
- Branta_ruficollis_trade_data_optimized.json.gz
- Lagenorhynchus_albirostris_trade_data_optimized.json.gz

Usage:
    python validate_before_load.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set
import logging

# Add the config directory to the path
sys.path.append(str(Path(__file__).parent.parent / 'config'))

try:
    from supabase_config import get_supabase_client
except ImportError:
    print("Error: Could not import supabase_config. Please ensure config/supabase_config.py exists.")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PreLoadValidator:
    """Validate system state before loading trade data"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.optimized_dir = Path(__file__).parent.parent / 'species_data' / 'processed' / 'optimized_species'
        self.validation_results = {}
    
    def check_database_connection(self) -> bool:
        """Test database connection"""
        logger.info("🔗 Checking database connection...")
        
        try:
            response = self.supabase.table('species').select('id').limit(1).execute()
            if response.data:
                logger.info("✅ Database connection successful")
                return True
            else:
                logger.error("❌ Database connection failed - no data returned")
                return False
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def check_optimized_files(self) -> Dict:
        """Check optimized trade data files"""
        logger.info("📁 Checking optimized trade data files...")
        
        # Look for compressed files first, then regular JSON
        compressed_files = list(self.optimized_dir.glob('*_trade_data_optimized.json.gz'))
        json_files = list(self.optimized_dir.glob('*_trade_data_optimized.json'))
        
        # Check for reader utility
        reader_exists = (self.optimized_dir / 'optimized_reader.py').exists()
        
        results = {
            'compressed_files': len(compressed_files),
            'json_files': len(json_files),
            'reader_exists': reader_exists,
            'files_ready': len(compressed_files) > 0 or len(json_files) > 0
        }
        
        if results['files_ready']:
            logger.info(f"✅ Found {results['compressed_files']} compressed and {results['json_files']} JSON files")
            if reader_exists:
                logger.info("✅ optimized_reader.py utility found")
            else:
                logger.warning("⚠️  optimized_reader.py utility not found")
        else:
            logger.error("❌ No optimized trade data files found")
        
        return results
    
    def check_species_mapping(self) -> Dict:
        """Check species mapping between files and database"""
        logger.info("🧬 Checking species mapping...")
        
        try:
            # Get species from database
            db_response = self.supabase.table('species').select('scientific_name').execute()
            db_species = {record['scientific_name'] for record in db_response.data}
            
            # Get species from optimized files
            file_species = set()
            
            # Check compressed files first
            files = list(self.optimized_dir.glob('*_trade_data_optimized.json.gz'))
            if not files:
                files = list(self.optimized_dir.glob('*_trade_data_optimized.json'))
            
            for file_path in files:
                # Extract species name from filename
                filename = file_path.stem
                
                # Handle .gz files where stem gives us the .json name
                if filename.endswith('.json'):
                    filename = filename[:-5]  # Remove .json extension
                
                if filename.endswith('_trade_data_optimized'):
                    species_name = filename.replace('_trade_data_optimized', '').replace('_', ' ')
                    file_species.add(species_name)
            
            # Compare
            mapped_species = db_species.intersection(file_species)
            missing_in_db = file_species - db_species
            missing_files = db_species - file_species
            
            results = {
                'total_db_species': len(db_species),
                'total_file_species': len(file_species),
                'mapped_species': len(mapped_species),
                'missing_in_db': list(missing_in_db),
                'missing_files': list(missing_files),
                'mapping_success_rate': len(mapped_species) / len(file_species) * 100 if file_species else 0
            }
            
            logger.info(f"✅ Database species: {results['total_db_species']}")
            logger.info(f"✅ File species: {results['total_file_species']}")
            logger.info(f"✅ Mapped species: {results['mapped_species']} ({results['mapping_success_rate']:.1f}%)")
            
            if missing_in_db:
                logger.warning(f"⚠️  Species in files but not in database: {missing_in_db}")
            
            if missing_files:
                logger.warning(f"⚠️  Species in database but no files: {missing_files}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to check species mapping: {e}")
            return {'error': str(e)}
    
    def check_current_trade_data(self) -> Dict:
        """Check current trade data in database"""
        logger.info("📊 Checking current trade data...")
        
        try:
            # Get total count
            count_response = self.supabase.table('cites_trade_records').select('id', count='exact').execute()
            total_records = count_response.count
            
            # Get species distribution
            species_response = self.supabase.table('cites_trade_records').select('taxon').execute()
            unique_species = set(record['taxon'] for record in species_response.data)
            
            # Get year range
            year_response = self.supabase.table('cites_trade_records').select('year').order('year').execute()
            years = [record['year'] for record in year_response.data if record['year']]
            
            results = {
                'total_records': total_records,
                'unique_species': len(unique_species),
                'min_year': min(years) if years else None,
                'max_year': max(years) if years else None,
                'has_data': total_records > 0
            }
            
            logger.info(f"✅ Current trade records: {results['total_records']:,}")
            logger.info(f"✅ Unique species: {results['unique_species']}")
            if results['min_year'] and results['max_year']:
                logger.info(f"✅ Year range: {results['min_year']} - {results['max_year']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to check current trade data: {e}")
            return {'error': str(e)}
    
    def estimate_load_size(self) -> Dict:
        """Estimate the size of data to be loaded"""
        logger.info("📏 Estimating load size...")
        
        try:
            total_records = 0
            file_count = 0
            
            # Check compressed files first
            files = list(self.optimized_dir.glob('*_trade_data_optimized.json.gz'))
            if not files:
                files = list(self.optimized_dir.glob('*_trade_data_optimized.json'))
            
            # Sample a few files to estimate
            sample_files = files[:3] if len(files) > 3 else files
            
            for file_path in sample_files:
                try:
                    if file_path.suffix == '.gz':
                        import gzip
                        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                            data = json.load(f)
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    
                    file_records = len(data.get('trade_records', []))
                    total_records += file_records
                    file_count += 1
                    
                except Exception as e:
                    logger.warning(f"Could not read {file_path.name}: {e}")
            
            # Estimate total based on sample
            if file_count > 0:
                avg_records_per_file = total_records / file_count
                estimated_total = avg_records_per_file * len(files)
            else:
                estimated_total = 0
            
            results = {
                'files_to_load': len(files),
                'sampled_files': file_count,
                'sampled_records': total_records,
                'estimated_total': int(estimated_total)
            }
            
            logger.info(f"✅ Files to load: {results['files_to_load']}")
            logger.info(f"✅ Estimated records: {results['estimated_total']:,}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to estimate load size: {e}")
            return {'error': str(e)}
    
    def check_disk_space(self) -> Dict:
        """Check available disk space"""
        logger.info("💾 Checking disk space...")
        
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.optimized_dir)
            
            # Convert to GB
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            
            results = {
                'total_gb': round(total_gb, 2),
                'used_gb': round(used_gb, 2),
                'free_gb': round(free_gb, 2),
                'sufficient_space': free_gb > 1.0  # Need at least 1GB free
            }
            
            logger.info(f"✅ Free space: {results['free_gb']:.1f} GB")
            
            if results['sufficient_space']:
                logger.info("✅ Sufficient disk space available")
            else:
                logger.warning("⚠️  Low disk space - consider freeing up space")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to check disk space: {e}")
            return {'error': str(e)}
    
    def run_full_validation(self) -> bool:
        """Run all validation checks"""
        logger.info("🔍 Starting pre-load validation...")
        logger.info("="*60)
        
        # Run all checks
        checks = [
            ('Database Connection', self.check_database_connection()),
            ('Optimized Files', self.check_optimized_files()),
            ('Species Mapping', self.check_species_mapping()),
            ('Current Trade Data', self.check_current_trade_data()),
            ('Load Size Estimation', self.estimate_load_size()),
            ('Disk Space', self.check_disk_space())
        ]
        
        # Collect results
        all_passed = True
        for check_name, result in checks:
            if isinstance(result, dict):
                self.validation_results[check_name.lower().replace(' ', '_')] = result
                # Check for error conditions
                if 'error' in result:
                    all_passed = False
                elif check_name == 'Optimized Files' and not result.get('files_ready'):
                    all_passed = False
                elif check_name == 'Database Connection' and not result:
                    all_passed = False
            elif isinstance(result, bool):
                self.validation_results[check_name.lower().replace(' ', '_')] = result
                if not result:
                    all_passed = False
        
        logger.info("="*60)
        
        if all_passed:
            logger.info("🎉 ALL VALIDATION CHECKS PASSED!")
            logger.info("✅ System is ready for trade data loading")
            
            # Show key metrics
            species_mapping = self.validation_results.get('species_mapping', {})
            load_estimation = self.validation_results.get('load_size_estimation', {})
            current_data = self.validation_results.get('current_trade_data', {})
            
            logger.info("\n📋 LOADING SUMMARY:")
            logger.info(f"   • Current records: {current_data.get('total_records', 0):,}")
            logger.info(f"   • Estimated new records: {load_estimation.get('estimated_total', 0):,}")
            logger.info(f"   • Species to load: {species_mapping.get('mapped_species', 0)}")
            logger.info(f"   • Files to process: {load_estimation.get('files_to_load', 0)}")
            
            logger.info("\n⚠️  IMPORTANT: This will DELETE all existing trade data!")
            logger.info("   Make sure to use --backup flag when running the loader.")
            
        else:
            logger.error("❌ VALIDATION FAILED!")
            logger.error("   Please fix the issues above before running the loader.")
        
        return all_passed

def main():
    validator = PreLoadValidator()
    
    try:
        success = validator.run_full_validation()
        
        if success:
            print("\n" + "="*60)
            print("READY TO LOAD! Run the following command:")
            print("python load_optimized_trade_data.py --backup")
            print("\nOr for a dry run first:")
            print("python load_optimized_trade_data.py --dry-run")
            print("="*60)
            return 0
        else:
            print("\n" + "="*60)
            print("NOT READY TO LOAD - Please fix validation errors first")
            print("="*60)
            return 1
            
    except Exception as e:
        logger.error(f"Validation failed with error: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
