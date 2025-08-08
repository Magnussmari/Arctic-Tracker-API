#!/usr/bin/env python3
"""
Extract current database architecture for CITES migration planning
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.supabase_config import get_supabase_client

class DatabaseArchitectureExtractor:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docs')
        
    def extract_table_schema(self, table_name):
        """Extract schema information for a specific table"""
        try:
            # Get sample data to infer structure
            response = self.supabase.table(table_name).select('*').limit(1).execute()
            
            if response.data and len(response.data) > 0:
                sample = response.data[0]
                schema = {
                    'table_name': table_name,
                    'columns': {}
                }
                
                for column, value in sample.items():
                    schema['columns'][column] = {
                        'sample_value': str(value)[:100] if value else None,
                        'type': type(value).__name__ if value else 'unknown'
                    }
                
                return schema
            return None
            
        except Exception as e:
            print(f"Error extracting schema for {table_name}: {str(e)}")
            return None
    
    def get_table_counts(self):
        """Get record counts for main tables"""
        counts = {}
        
        tables = [
            'species',
            'cites_trade_records',
            'species_trade_summary',
            'cites_listings',
            'iucn_assessments',
            'common_names'
        ]
        
        for table in tables:
            try:
                response = self.supabase.table(table).select('id', count='exact').limit(1).execute()
                counts[table] = response.count if hasattr(response, 'count') else 'Unknown'
            except:
                counts[table] = 'Error'
        
        return counts
    
    def extract_cites_trade_structure(self):
        """Extract detailed structure of cites_trade_records table"""
        print("Extracting CITES trade records structure...")
        
        # Get schema
        schema = self.extract_table_schema('cites_trade_records')
        
        # Get sample records
        try:
            response = self.supabase.table('cites_trade_records').select('*').limit(5).execute()
            sample_records = response.data if response.data else []
        except:
            sample_records = []
        
        # Get unique values for key fields
        try:
            # Get purposes
            response = self.supabase.table('cites_trade_records').select('purpose').limit(1000).execute()
            purposes = set(r['purpose'] for r in response.data if r.get('purpose'))
            
            # Get sources
            response = self.supabase.table('cites_trade_records').select('source').limit(1000).execute()
            sources = set(r['source'] for r in response.data if r.get('source'))
            
            # Get years range
            response = self.supabase.table('cites_trade_records').select('year').order('year', desc=True).limit(1).execute()
            max_year = response.data[0]['year'] if response.data else None
            
            response = self.supabase.table('cites_trade_records').select('year').order('year').limit(1).execute()
            min_year = response.data[0]['year'] if response.data else None
            
        except:
            purposes = sources = []
            min_year = max_year = None
        
        return {
            'schema': schema,
            'sample_records': sample_records,
            'field_analysis': {
                'purposes': list(purposes)[:20],
                'sources': list(sources)[:20],
                'year_range': {'min': min_year, 'max': max_year}
            }
        }
    
    def generate_architecture_report(self):
        """Generate comprehensive architecture report"""
        print("Generating database architecture report...")
        
        report = {
            'extraction_date': datetime.now().isoformat(),
            'database': 'Arctic Tracker - Supabase',
            'table_counts': self.get_table_counts(),
            'table_schemas': {},
            'relationships': {
                'cites_trade_records': {
                    'foreign_keys': ['species_id -> species.id'],
                    'indexes': ['species_id', 'year', 'exporter', 'importer']
                },
                'species_trade_summary': {
                    'foreign_keys': ['species_id -> species.id'],
                    'indexes': ['species_id', 'year']
                },
                'cites_listings': {
                    'foreign_keys': ['species_id -> species.id'],
                    'indexes': ['species_id', 'listing_date']
                },
                'iucn_assessments': {
                    'foreign_keys': ['species_id -> species.id'],
                    'indexes': ['species_id', 'year_published']
                }
            }
        }
        
        # Extract schemas for main tables
        main_tables = ['species', 'cites_trade_records', 'species_trade_summary', 
                      'cites_listings', 'iucn_assessments']
        
        for table in main_tables:
            schema = self.extract_table_schema(table)
            if schema:
                report['table_schemas'][table] = schema
        
        # Add detailed CITES trade analysis
        report['cites_trade_details'] = self.extract_cites_trade_structure()
        
        # Save report
        output_path = os.path.join(self.output_dir, 'database_architecture.json')
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Architecture report saved to: {output_path}")
        
        # Also create a markdown version
        self.create_markdown_report(report)
        
        return report
    
    def create_markdown_report(self, report):
        """Create human-readable markdown report"""
        md_content = f"""# Arctic Tracker Database Architecture
Generated: {report['extraction_date']}

## Table Overview

| Table | Record Count |
|-------|-------------|
"""
        
        for table, count in report['table_counts'].items():
            count_str = f"{count:,}" if isinstance(count, int) else str(count)
            md_content += f"| {table} | {count_str} |\n"
        
        md_content += "\n## Table Schemas\n\n"
        
        for table_name, schema in report['table_schemas'].items():
            md_content += f"### {table_name}\n\n"
            md_content += "| Column | Type | Sample |\n"
            md_content += "|--------|------|--------|\n"
            
            if schema and 'columns' in schema:
                for col, info in schema['columns'].items():
                    sample = info.get('sample_value', '')
                    if sample and len(sample) > 50:
                        sample = sample[:50] + "..."
                    md_content += f"| {col} | {info.get('type', '')} | {sample} |\n"
            
            md_content += "\n"
        
        # Add CITES trade details
        if 'cites_trade_details' in report:
            details = report['cites_trade_details']
            md_content += "## CITES Trade Records Analysis\n\n"
            
            if 'field_analysis' in details:
                analysis = details['field_analysis']
                md_content += f"**Year Range**: {analysis['year_range']['min']} - {analysis['year_range']['max']}\n\n"
                
                md_content += "**Trade Purposes**: "
                md_content += ", ".join(analysis['purposes'][:10]) + "\n\n"
                
                md_content += "**Source Codes**: "
                md_content += ", ".join(analysis['sources'][:10]) + "\n\n"
        
        # Save markdown
        md_path = os.path.join(self.output_dir, 'database_architecture.md')
        with open(md_path, 'w') as f:
            f.write(md_content)
        
        print(f"Markdown report saved to: {md_path}")

if __name__ == "__main__":
    extractor = DatabaseArchitectureExtractor()
    report = extractor.generate_architecture_report()
    
    print("\n✅ Database architecture extraction complete!")
    print(f"📊 Total tables analyzed: {len(report['table_schemas'])}")
    print(f"📈 CITES trade records: {report['table_counts'].get('cites_trade_records', 'Unknown')}")