#!/usr/bin/env python3
"""
Database Architecture Update and Species Name Retrieval Script

This script performs two main functions:
1. Updates and documents the current database architecture
2. Retrieves and reports on species names (both scientific and common names)

It connects to the Supabase database, analyzes the current schema structure,
and generates comprehensive reports on both the database architecture and
species data.

Usage:
    python update_db_architecture_and_species.py [--output-dir DIR] [--format FORMAT]

Options:
    --output-dir DIR    Directory to save reports (default: ../../data/reports)
    --format FORMAT     Output format: json, csv, markdown, all (default: all)
    --update-schema     Update the main data_architecture_may2025.md file
    --species-only      Only run species name analysis
    --schema-only       Only run schema analysis
"""

import os
import sys
import asyncio
import json
import csv
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import argparse
from collections import defaultdict
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from supabase import create_client, Client
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error: Missing required packages. Install with: pip install supabase python-dotenv pandas")
    print(f"Import error: {e}")
    sys.exit(1)

# Load environment variables
def load_environment():
    """Load environment variables from various possible locations"""
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'config', '.env'),  # Primary: config/.env
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'data', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', '.env'),
        os.path.join(os.path.dirname(__file__), '..', '..', '.env'),
    ]
    
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"✅ Loaded environment from: {env_path}")
            return True
    
    print("⚠️  No .env file found. Make sure SUPABASE_URL and SUPABASE_ANON_KEY are set.")
    return False

class DatabaseArchitectureAnalyzer:
    """
    Comprehensive database architecture analyzer and species name retriever
    """
    
    def __init__(self, output_dir: str = None):
        """Initialize the analyzer with Supabase connection"""
        load_environment()
        
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")
        
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as e:
            print(f"⚠️  Standard client creation failed: {e}")
            print("🔄 Trying alternative client initialization...")
            
            # Try multiple fallback approaches
            client_created = False
            
            # Approach 1: Try creating client manually with required components
            if not client_created:
                try:
                    print("  Trying manual client construction...")
                    from supabase._sync.client import SyncClient
                    from supabase.lib.client_options import ClientOptions
                    
                    # Create client options without proxy
                    options = ClientOptions()
                    self.supabase = SyncClient(
                        supabase_url=self.supabase_url,
                        supabase_key=self.supabase_key,
                        options=options
                    )
                    client_created = True
                    print("  ✅ Success with manual construction")
                except Exception as e1:
                    print(f"  ❌ Failed: {e1}")
            
            # Approach 2: Try with older API style
            if not client_created:
                try:
                    print("  Trying older API style...")
                    from supabase import Client as DirectClient
                    # Try with just the two required parameters
                    self.supabase = DirectClient(
                        supabase_url=self.supabase_url,
                        supabase_key=self.supabase_key
                    )
                    client_created = True
                    print("  ✅ Success with older API style")
                except Exception as e2:
                    print(f"  ❌ Failed: {e2}")
            
            # Approach 3: Try with postgrest client directly
            if not client_created:
                try:
                    print("  Trying with basic HTTP client...")
                    import requests
                    
                    # Create a simple wrapper that mimics the Supabase client interface
                    class SimpleSupabaseClient:
                        def __init__(self, url, key):
                            self.url = url.rstrip('/')
                            self.key = key
                            self.headers = {
                                'apikey': key,
                                'Authorization': f'Bearer {key}',
                                'Content-Type': 'application/json'
                            }
                        
                        def table(self, table_name):
                            return SimpleTable(self.url, self.headers, table_name)
                        
                        def rpc(self, function_name):
                            return SimpleRPC(self.url, self.headers, function_name)
                    
                    class SimpleTable:
                        def __init__(self, url, headers, table_name):
                            self.url = f"{url}/rest/v1/{table_name}"
                            self.headers = headers
                        
                        def select(self, columns='*', count=None):
                            params = {'select': columns}
                            if count:
                                params['count'] = count
                            return SimpleQuery(self.url, self.headers, 'GET', params)
                    
                    class SimpleRPC:
                        def __init__(self, url, headers, function_name):
                            self.url = f"{url}/rest/v1/rpc/{function_name}"
                            self.headers = headers
                        
                        def execute(self):
                            response = requests.post(self.url, headers=self.headers)
                            return SimpleResponse(response)
                    
                    class SimpleQuery:
                        def __init__(self, url, headers, method, params=None):
                            self.url = url
                            self.headers = headers
                            self.method = method
                            self.params = params or {}
                        
                        def limit(self, count):
                            self.params['limit'] = count
                            return self
                        
                        def execute(self):
                            if self.method == 'GET':
                                response = requests.get(self.url, headers=self.headers, params=self.params)
                            else:
                                response = requests.post(self.url, headers=self.headers, json=self.params)
                            return SimpleResponse(response)
                    
                    class SimpleResponse:
                        def __init__(self, response):
                            self.status_code = response.status_code
                            try:
                                self.data = response.json() if response.content else None
                                self.count = len(self.data) if self.data else 0
                            except:
                                self.data = None
                                self.count = 0
                    
                    self.supabase = SimpleSupabaseClient(self.supabase_url, self.supabase_key)
                    client_created = True
                    print("  ✅ Success with basic HTTP client")
                except Exception as e3:
                    print(f"  ❌ Failed: {e3}")
            
            if not client_created:
                raise Exception(f"Failed to create Supabase client with all approaches. Original error: {e}")
        
        # Set up output directory in rebuild structure
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent.parent / "docs" / "reports"
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Data storage
        self.schema_info = {}
        self.species_data = []
        self.families_data = []
        self.table_counts = {}
        self.common_names_data = []
        
    async def get_database_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        try:
            # Try RPC function first
            response = self.supabase.rpc('get_table_names').execute()
            if response.data and len(response.data) > 4:  # If we get more than just the 4 basic tables
                return response.data
            
            print(f"  RPC returned limited tables: {response.data if response.data else 'None'}")
            print("  Trying direct table discovery...")
            
            # Fallback: Try to discover tables by testing known table names
            known_tables = [
                'catch_records', 'cites_listings', 'cites_trade_records', 'common_names',
                'conservation_measures', 'distribution_ranges', 'families', 'iucn_assessments',
                'profiles', 'species', 'species_threats', 'species_trade_summary',
                'subpopulations', 'timeline_events'
            ]
            
            existing_tables = []
            print(f"  Testing {len(known_tables)} known tables...")
            
            for table in known_tables:
                try:
                    response = self.supabase.table(table).select('*').limit(1).execute()
                    if response.data is not None and response.status_code == 200:
                        existing_tables.append(table)
                        print(f"    ✅ Found table: {table}")
                    else:
                        print(f"    ❌ Table not found: {table}")
                except Exception as e:
                    print(f"    ❌ Error testing {table}: {e}")
                    continue
            
            if existing_tables:
                return existing_tables
            else:
                print("  No known tables found, falling back to basic discovery...")
                # If no known tables found, return what we got from RPC
                return response.data if response.data else ['species', 'families', 'common_names']
            
        except Exception as e:
            print(f"Error getting table list: {e}")
            print("Using fallback table list...")
            # Return known tables as fallback
            return ['species', 'families', 'cites_trade_records', 'iucn_assessments', 'cites_listings', 'common_names']
    
    async def analyze_table_structure(self, table_name: str) -> Dict[str, Any]:
        """Analyze the structure of a specific table"""
        print(f"  📊 Analyzing table: {table_name}")
        
        try:
            # Get a sample record to understand the structure
            response = self.supabase.table(table_name).select('*').limit(1).execute()
            
            if not response.data:
                return {
                    'table_name': table_name,
                    'columns': [],
                    'sample_data': None,
                    'record_count': 0,
                    'error': 'No data found'
                }
            
            sample_record = response.data[0]
            
            # Get record count
            count_response = self.supabase.table(table_name).select('*', count='exact').execute()
            record_count = count_response.count if count_response.count else len(response.data)
            
            # Analyze columns
            columns = []
            for column_name, value in sample_record.items():
                column_info = {
                    'name': column_name,
                    'type': self._infer_postgres_type(value),
                    'sample_value': str(value)[:100] if value is not None else None,
                    'is_nullable': value is None
                }
                columns.append(column_info)
            
            self.table_counts[table_name] = record_count
            
            return {
                'table_name': table_name,
                'columns': columns,
                'sample_data': sample_record,
                'record_count': record_count,
                'analyzed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"    ❌ Error analyzing {table_name}: {e}")
            return {
                'table_name': table_name,
                'columns': [],
                'sample_data': None,
                'record_count': 0,
                'error': str(e)
            }
    
    def _infer_postgres_type(self, value) -> str:
        """Infer PostgreSQL data type from Python value"""
        if value is None:
            return "TEXT"
        elif isinstance(value, bool):
            return "BOOLEAN"
        elif isinstance(value, int):
            return "INTEGER"
        elif isinstance(value, float):
            return "FLOAT"
        elif isinstance(value, str):
            if len(value) <= 255:
                return "VARCHAR(255)"
            else:
                return "TEXT"
        elif isinstance(value, dict):
            return "JSONB"
        elif isinstance(value, list):
            return "JSONB"
        else:
            return "TEXT"
    
    async def get_families_analysis(self) -> Dict[str, Any]:
        """Analyze the families table and family normalization"""
        print("\n🏛️ Analyzing families table and normalization...")
        
        try:
            response = self.supabase.table('families').select('*').execute()
            
            if not response.data:
                return {'error': 'No families data found'}
            
            families_list = response.data
            self.families_data = families_list
            
            analysis = {
                'total_families': len(families_list),
                'families_with_order': 0,
                'families_with_class': 0,
                'families_with_description': 0,
                'taxonomic_distribution': defaultdict(int),
                'order_distribution': defaultdict(int),
                'family_names': []
            }
            
            for family in families_list:
                family_name = family.get('family_name')
                order_name = family.get('order_name')
                class_name = family.get('class')
                description = family.get('description')
                
                if family_name:
                    analysis['family_names'].append(family_name)
                
                if order_name:
                    analysis['families_with_order'] += 1
                    analysis['order_distribution'][order_name] += 1
                
                if class_name:
                    analysis['families_with_class'] += 1
                    analysis['taxonomic_distribution'][class_name] += 1
                
                if description:
                    analysis['families_with_description'] += 1
            
            # Convert defaultdicts to regular dicts and sort
            analysis['taxonomic_distribution'] = dict(analysis['taxonomic_distribution'])
            analysis['order_distribution'] = dict(analysis['order_distribution'])
            analysis['family_names'] = sorted(analysis['family_names'])
            
            print(f"  📊 Found {analysis['total_families']} normalized families")
            print(f"  🏷️  Families with order: {analysis['families_with_order']}")
            print(f"  📚 Families with class: {analysis['families_with_class']}")
            
            return analysis
            
        except Exception as e:
            print(f"  ❌ Error analyzing families: {e}")
            return {'error': str(e)}
    
    async def get_species_names_analysis(self) -> Dict[str, Any]:
        """Comprehensive analysis of species names in the database"""
        print("\n🐾 Analyzing species names...")
        
        try:
            # Get all species data
            response = self.supabase.table('species').select('*').execute()
            
            if not response.data:
                return {'error': 'No species data found'}
            
            species_list = response.data
            self.species_data = species_list
            
            # Analyze scientific and common names
            analysis = {
                'total_species': len(species_list),
                'species_with_scientific_names': 0,
                'species_with_common_names': 0,
                'species_with_both_names': 0,
                'species_with_family_id': 0,
                'species_with_legacy_family': 0,
                'unique_families': set(),
                'unique_genera': set(),
                'taxonomic_distribution': defaultdict(int),
                'name_conflicts': [],
                'missing_data': {
                    'no_scientific_name': [],
                    'no_common_name': [],
                    'no_family': [],
                    'no_genus': [],
                    'no_family_id': []
                }
            }
            
            for species in species_list:
                scientific_name = species.get('scientific_name')
                common_name = species.get('common_name')
                family = species.get('family')
                family_id = species.get('family_id')
                genus = species.get('genus')
                class_name = species.get('class')
                
                # Count name availability
                if scientific_name:
                    analysis['species_with_scientific_names'] += 1
                else:
                    analysis['missing_data']['no_scientific_name'].append(species.get('id'))
                
                if common_name:
                    analysis['species_with_common_names'] += 1
                else:
                    analysis['missing_data']['no_common_name'].append(species.get('id'))
                
                if scientific_name and common_name:
                    analysis['species_with_both_names'] += 1
                
                # Analyze family normalization
                if family_id:
                    analysis['species_with_family_id'] += 1
                else:
                    analysis['missing_data']['no_family_id'].append(species.get('id'))
                
                if family:
                    analysis['species_with_legacy_family'] += 1
                    analysis['unique_families'].add(family)
                else:
                    analysis['missing_data']['no_family'].append(species.get('id'))
                
                if genus:
                    analysis['unique_genera'].add(genus)
                else:
                    analysis['missing_data']['no_genus'].append(species.get('id'))
                
                if class_name:
                    analysis['taxonomic_distribution'][class_name] += 1
            
            # Convert sets to lists for JSON serialization
            analysis['unique_families'] = sorted(list(analysis['unique_families']))
            analysis['unique_genera'] = sorted(list(analysis['unique_genera']))
            analysis['taxonomic_distribution'] = dict(analysis['taxonomic_distribution'])
            
            # Calculate normalization progress
            analysis['family_normalization_progress'] = round(
                (analysis['species_with_family_id'] / max(analysis['total_species'], 1)) * 100, 2
            )
            
            print(f"  📈 Found {analysis['total_species']} total species")
            print(f"  🔬 Scientific names: {analysis['species_with_scientific_names']}")
            print(f"  🏷️  Common names: {analysis['species_with_common_names']}")
            print(f"  👥 Both names: {analysis['species_with_both_names']}")
            print(f"  🏛️ Family normalization: {analysis['family_normalization_progress']}%")
            
            return analysis
            
        except Exception as e:
            print(f"  ❌ Error analyzing species names: {e}")
            return {'error': str(e)}
    
    async def get_common_names_data(self) -> Dict[str, Any]:
        """Analyze data from the common_names table if it exists"""
        print("\n🏷️ Analyzing common names table...")
        
        try:
            response = self.supabase.table('common_names').select('*').execute()
            
            if not response.data:
                return {'error': 'No common names data found'}
            
            common_names_list = response.data
            self.common_names_data = common_names_list
            
            analysis = {
                'total_common_names': len(common_names_list),
                'languages': defaultdict(int),
                'species_with_multiple_names': defaultdict(list),
                'main_names_count': 0
            }
            
            for name_record in common_names_list:
                language = name_record.get('language', 'unknown')
                species_id = name_record.get('species_id')
                is_main = name_record.get('is_main', False)
                name = name_record.get('name')
                
                analysis['languages'][language] += 1
                
                if species_id and name:
                    analysis['species_with_multiple_names'][species_id].append(name)
                
                if is_main:
                    analysis['main_names_count'] += 1
            
            # Convert defaultdicts to regular dicts
            analysis['languages'] = dict(analysis['languages'])
            analysis['species_with_multiple_names'] = dict(analysis['species_with_multiple_names'])
            
            print(f"  📊 Found {analysis['total_common_names']} common name records")
            print(f"  🌍 Languages: {list(analysis['languages'].keys())}")
            
            return analysis
            
        except Exception as e:
            print(f"  ❌ Error analyzing common names: {e}")
            return {'error': str(e)}
    
    async def run_full_analysis(self) -> Dict[str, Any]:
        """Run complete database architecture and species analysis"""
        print("🔍 Starting comprehensive database analysis...")
        
        timestamp = datetime.now()
        
        # Get all tables
        tables = await self.get_database_tables()
        print(f"📋 Found {len(tables)} tables: {', '.join(tables)}")
        
        # Analyze each table structure
        print(f"\n📊 Analyzing table structures...")
        table_analyses = {}
        for table in tables:
            table_analyses[table] = await self.analyze_table_structure(table)
        
        # Analyze families if table exists
        families_analysis = {}
        if 'families' in tables:
            families_analysis = await self.get_families_analysis()
        
        # Analyze species names
        species_analysis = await self.get_species_names_analysis()
        
        # Analyze common names if table exists
        common_names_analysis = {}
        if 'common_names' in tables:
            common_names_analysis = await self.get_common_names_data()
        
        # Compile full report
        full_report = {
            'analysis_metadata': {
                'timestamp': timestamp.isoformat(),
                'analyzer_version': '2.0.0',
                'database_url': self.supabase_url,
                'tables_analyzed': len(tables),
                'family_normalization_detected': 'families' in tables
            },
            'database_schema': {
                'tables': tables,
                'table_structures': table_analyses,
                'table_counts': self.table_counts
            },
            'families_analysis': families_analysis,
            'species_analysis': species_analysis,
            'common_names_analysis': common_names_analysis,
            'summary': {
                'total_tables': len(tables),
                'total_species': species_analysis.get('total_species', 0),
                'total_families': families_analysis.get('total_families', 0),
                'species_with_both_names': species_analysis.get('species_with_both_names', 0),
                'family_normalization_progress': species_analysis.get('family_normalization_progress', 0),
                'completion_percentage': round((species_analysis.get('species_with_both_names', 0) / max(species_analysis.get('total_species', 1), 1)) * 100, 2)
            }
        }
        
        self.schema_info = full_report
        return full_report
    
    async def save_reports(self, format_types: List[str] = ['all']):
        """Save analysis reports in specified formats (overwrites existing)"""
        if not self.schema_info:
            print("⚠️  No analysis data available. Run analysis first.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if 'all' in format_types:
            format_types = ['json', 'markdown', 'csv']
        
        print(f"\n💾 Saving reports to: {self.output_dir}")
        
        # Save JSON report (overwrite existing)
        if 'json' in format_types:
            json_path = self.output_dir / "db_architecture_analysis_latest.json"
            with open(json_path, 'w') as f:
                json.dump(self.schema_info, f, indent=2, default=str)
            print(f"  ✅ JSON report: {json_path}")
        
        # Save Markdown report (overwrite existing)
        if 'markdown' in format_types:
            md_path = self.output_dir / "db_architecture_report_latest.md"
            with open(md_path, 'w') as f:
                f.write(self._generate_markdown_report())
            print(f"  ✅ Markdown report: {md_path}")
        
        # Save CSV reports (overwrite existing)
        if 'csv' in format_types:
            await self._save_csv_reports_latest()
    
    async def _save_csv_reports_latest(self):
        """Save CSV reports for species and table data (overwrites existing)"""
        
        # Save species data CSV
        if self.species_data:
            species_csv_path = self.output_dir / "species_names_latest.csv"
            
            # Prepare species data for CSV
            csv_data = []
            for species in self.species_data:
                csv_data.append({
                    'id': species.get('id'),
                    'scientific_name': species.get('scientific_name'),
                    'common_name': species.get('common_name'),
                    'family': species.get('family'),
                    'family_id': species.get('family_id'),
                    'genus': species.get('genus'),
                    'class': species.get('class'),
                    'order_name': species.get('order_name'),
                    'authority': species.get('authority'),
                    'sis_id': species.get('sis_id'),
                    'inaturalist_id': species.get('inaturalist_id')
                })
            
            df = pd.DataFrame(csv_data)
            df.to_csv(species_csv_path, index=False)
            print(f"  ✅ Species CSV: {species_csv_path}")
        
        # Save families data CSV
        if self.families_data:
            families_csv_path = self.output_dir / "families_latest.csv"
            df = pd.DataFrame(self.families_data)
            df.to_csv(families_csv_path, index=False)
            print(f"  ✅ Families CSV: {families_csv_path}")
        
        # Save common names CSV
        if self.common_names_data:
            common_names_csv_path = self.output_dir / "common_names_latest.csv"
            df = pd.DataFrame(self.common_names_data)
            df.to_csv(common_names_csv_path, index=False)
            print(f"  ✅ Common names CSV: {common_names_csv_path}")
        
        # Save table summary CSV
        table_summary_path = self.output_dir / "table_summary_latest.csv"
        table_summary = []
        
        for table_name, count in self.table_counts.items():
            table_summary.append({
                'table_name': table_name,
                'record_count': count,
                'has_data': count > 0
            })
        
        df = pd.DataFrame(table_summary)
        df.to_csv(table_summary_path, index=False)
        print(f"  ✅ Table summary CSV: {table_summary_path}")
    
    def _generate_markdown_report(self) -> str:
        """Generate a comprehensive markdown report"""
        report = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report.append(f"# Arctic Species Database Architecture Analysis")
        report.append(f"**Generated:** {timestamp}")
        report.append(f"**Analyzer Version:** 2.0.0")
        report.append("")
        
        # Summary
        summary = self.schema_info.get('summary', {})
        report.append("## Executive Summary")
        report.append(f"- **Total Tables:** {summary.get('total_tables', 0)}")
        report.append(f"- **Total Species:** {summary.get('total_species', 0)}")
        report.append(f"- **Total Families:** {summary.get('total_families', 0)}")
        report.append(f"- **Species with Both Names:** {summary.get('species_with_both_names', 0)}")
        report.append(f"- **Family Normalization Progress:** {summary.get('family_normalization_progress', 0)}%")
        report.append(f"- **Data Completion:** {summary.get('completion_percentage', 0)}%")
        report.append("")
        
        # Database Schema
        report.append("## Database Schema Overview")
        schema = self.schema_info.get('database_schema', {})
        tables = schema.get('tables', [])
        
        report.append("### Tables")
        for table in tables:
            count = self.table_counts.get(table, 0)
            table_type = "📊 Table" if not table.endswith('_count') and 'with_' not in table else "📈 View"
            report.append(f"- `{table}` ({count:,} records) {table_type}")
        report.append("")
        
        # Family Normalization Status
        families_analysis = self.schema_info.get('families_analysis', {})
        if families_analysis and not families_analysis.get('error'):
            report.append("## Family Normalization Analysis")
            report.append(f"- **Normalized Families:** {families_analysis.get('total_families', 0):,}")
            report.append(f"- **Families with Order Info:** {families_analysis.get('families_with_order', 0):,}")
            report.append(f"- **Families with Class Info:** {families_analysis.get('families_with_class', 0):,}")
            
            taxonomic_dist = families_analysis.get('taxonomic_distribution', {})
            if taxonomic_dist:
                report.append("- **Family Distribution by Class:**")
                for class_name, count in sorted(taxonomic_dist.items()):
                    report.append(f"  - {class_name}: {count:,} families")
            report.append("")
        
        # Table Structures
        report.append("### Table Structures")
        table_structures = schema.get('table_structures', {})
        
        for table_name, structure in table_structures.items():
            if structure.get('error'):
                report.append(f"#### `{table_name}` (Error: {structure['error']})")
                continue
                
            report.append(f"#### `{table_name}`")
            report.append(f"**Records:** {structure.get('record_count', 0):,}")
            report.append("")
            report.append("| Column | Type | Sample Value |")
            report.append("|--------|------|--------------|")
            
            for column in structure.get('columns', []):
                name = column['name']
                col_type = column['type']
                sample = column.get('sample_value', 'NULL')
                if sample and len(sample) > 50:
                    sample = sample[:47] + "..."
                report.append(f"| `{name}` | {col_type} | {sample} |")
            
            report.append("")
        
        # Species Analysis
        species_analysis = self.schema_info.get('species_analysis', {})
        if species_analysis and not species_analysis.get('error'):
            report.append("## Species Names Analysis")
            
            report.append("### Name Coverage")
            report.append(f"- **Scientific Names:** {species_analysis.get('species_with_scientific_names', 0):,}")
            report.append(f"- **Common Names:** {species_analysis.get('species_with_common_names', 0):,}")
            report.append(f"- **Both Names:** {species_analysis.get('species_with_both_names', 0):,}")
            report.append("")
            
            report.append("### Family Normalization Status")
            report.append(f"- **Species with Family ID:** {species_analysis.get('species_with_family_id', 0):,}")
            report.append(f"- **Species with Legacy Family:** {species_analysis.get('species_with_legacy_family', 0):,}")
            report.append(f"- **Normalization Progress:** {species_analysis.get('family_normalization_progress', 0)}%")
            report.append("")
            
            report.append("### Taxonomic Distribution")
            taxonomic_dist = species_analysis.get('taxonomic_distribution', {})
            for class_name, count in sorted(taxonomic_dist.items()):
                report.append(f"- **{class_name}:** {count:,} species")
            report.append("")
            
            report.append("### Unique Taxonomic Groups")
            report.append(f"- **Families:** {len(species_analysis.get('unique_families', []))}")
            report.append(f"- **Genera:** {len(species_analysis.get('unique_genera', []))}")
            report.append("")
        
        # Common Names Analysis
        common_names = self.schema_info.get('common_names_analysis', {})
        if common_names and not common_names.get('error'):
            report.append("## Common Names Analysis")
            report.append(f"- **Total Common Name Records:** {common_names.get('total_common_names', 0):,}")
            report.append(f"- **Main Names:** {common_names.get('main_names_count', 0):,}")
            
            languages = common_names.get('languages', {})
            if languages:
                report.append("- **Languages:**")
                for lang, count in sorted(languages.items()):
                    report.append(f"  - {lang}: {count:,} names")
            report.append("")
        
        return "\n".join(report)
    
    def _generate_column_notes(self, column_name: str, sample_value: str, table_name: str) -> str:
        """Generate descriptive notes for database columns"""
        
        # Primary key detection
        if column_name.lower() in ['id', 'uuid'] or 'id' in column_name.lower():
            if table_name in column_name.lower() or column_name == 'id':
                return "Primary Key"
            else:
                return f"Foreign Key referencing `{column_name.replace('_id', '')}.id`"
        
        # Family normalization specific
        if column_name.lower() == 'family_id':
            return "Foreign Key referencing `families.id` (normalized)"
        elif column_name.lower() == 'family_name':
            return "Normalized family name (unique)"
        elif column_name.lower() == 'family' and table_name == 'species':
            return "Legacy family name (text, being normalized)"
        
        # Common patterns
        if 'created_at' in column_name.lower():
            return "Timestamp of record creation"
        elif 'updated_at' in column_name.lower():
            return "Timestamp of last update"
        elif 'scientific_name' in column_name.lower():
            return "Scientific name of the species"
        elif 'common_name' in column_name.lower():
            return "Common name of the species"
        elif 'year' in column_name.lower():
            return "Year of the record or event"
        elif 'url' in column_name.lower():
            return "URL link"
        elif 'code' in column_name.lower():
            return "Code identifier"
        elif column_name.lower() in ['kingdom', 'phylum', 'class', 'order_name', 'family', 'genus']:
            return f"Taxonomic {column_name.lower()}"
        elif 'is_' in column_name.lower() or column_name.lower().startswith('has_'):
            return "Boolean flag"
        elif 'description' in column_name.lower():
            return "Description text (nullable)"
        elif sample_value and sample_value.lower() in ['true', 'false']:
            return "Boolean field"
        elif sample_value and sample_value.isdigit():
            return "Numeric value"
        else:
            return "Data field (nullable)" if not sample_value else "Data field"

async def main():
    """Main function to run the database analysis
    
    Parses command line arguments and runs the appropriate analysis based on user options.
    """
    parser = argparse.ArgumentParser(description='Database Architecture and Species Analysis Tool')
    parser.add_argument('--output-dir', type=str, help='Directory to save reports')
    parser.add_argument('--format', type=str, choices=['json', 'csv', 'markdown', 'all'], 
                       default='all', help='Output format')
    parser.add_argument('--species-only', action='store_true', 
                       help='Only run species name analysis')
    parser.add_argument('--schema-only', action='store_true', 
                       help='Only run schema analysis')
    
    args = parser.parse_args()
    
    try:
        # Initialize analyzer
        analyzer = DatabaseArchitectureAnalyzer(output_dir=args.output_dir)
        
        # Run analysis
        if args.species_only:
            print("🐾 Running species-only analysis...")
            await analyzer.get_species_names_analysis()
            await analyzer.get_common_names_data()
        elif args.schema_only:
            print("📊 Running schema-only analysis...")
            tables = await analyzer.get_database_tables()
            for table in tables:
                await analyzer.analyze_table_structure(table)
        else:
            print("🔍 Running full analysis...")
            await analyzer.run_full_analysis()
        
        # Save reports
        format_list = [args.format] if args.format != 'all' else ['all']
        await analyzer.save_reports(format_list)
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
