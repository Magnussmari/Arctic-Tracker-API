#!/usr/bin/env python3
"""
CITES Arctic Species Data Migration Plan Generator
Creates a detailed, step-by-step migration plan with safety checks
"""

import os
import sys
import json
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.supabase_config import get_supabase_client

class MigrationPlanGenerator:
    def __init__(self):
        self.supabase = get_supabase_client()
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.plan = {
            'generated_at': datetime.now().isoformat(),
            'phases': [],
            'risk_assessment': {},
            'rollback_procedures': {},
            'validation_checkpoints': []
        }
        
    def analyze_current_state(self):
        """Analyze current database state"""
        print("📊 Analyzing current database state...")
        
        # Get current record count
        try:
            response = self.supabase.table('cites_trade_records').select('id', count='exact').limit(1).execute()
            current_count = response.count if hasattr(response, 'count') else 0
        except:
            current_count = 0
            
        # Get date range
        try:
            response = self.supabase.table('cites_trade_records').select('year').order('year', desc=True).limit(1).execute()
            max_year = response.data[0]['year'] if response.data else None
        except:
            max_year = None
            
        return {
            'current_record_count': current_count,
            'current_max_year': max_year,
            'last_backup': None  # Would check backup table/logs
        }
        
    def analyze_new_data(self):
        """Analyze extracted Arctic data"""
        print("📊 Analyzing new Arctic species data...")
        
        summary_path = os.path.join(self.base_dir, 'extracted_data', 'arctic_species_trade_summary.csv')
        summary_df = pd.read_csv(summary_path)
        
        # Get full data stats
        data_path = os.path.join(self.base_dir, 'extracted_data', 'arctic_species_trade_data_v2025.csv')
        data_df = pd.read_csv(data_path, nrows=1000)  # Sample for structure
        
        return {
            'new_record_count': int(summary_df['record_count'].sum()),
            'species_count': len(summary_df),
            'year_range': {
                'min': int(summary_df['min_year'].min()),
                'max': int(summary_df['max_year'].max())
            },
            'columns': list(data_df.columns),
            'high_volume_species': summary_df.nlargest(5, 'record_count')[['Taxon', 'record_count']].astype({'record_count': int}).to_dict('records')
        }
        
    def generate_migration_phases(self, current_state, new_data):
        """Generate detailed migration phases"""
        
        phases = [
            {
                'phase': 1,
                'name': 'Pre-Migration Preparation',
                'duration': '2-3 hours',
                'steps': [
                    {
                        'step': '1.1',
                        'action': 'Create comprehensive backup',
                        'command': 'python backup_cites_data.py --full',
                        'validation': 'Verify backup file exists and size matches expected',
                        'rollback': 'N/A - No changes made yet'
                    },
                    {
                        'step': '1.2',
                        'action': 'Create staging table',
                        'sql': '''CREATE TABLE cites_trade_records_staging (
                            LIKE cites_trade_records INCLUDING ALL
                        );''',
                        'validation': 'Table exists with same structure',
                        'rollback': 'DROP TABLE cites_trade_records_staging;'
                    },
                    {
                        'step': '1.3',
                        'action': 'Add missing species (Aleutian cackling goose)',
                        'command': 'python add_missing_species.py',
                        'validation': 'Species exists in species table',
                        'rollback': 'DELETE FROM species WHERE scientific_name = \'Branta hutchinsii leucopareia\';'
                    }
                ]
            },
            {
                'phase': 2,
                'name': 'Test Migration',
                'duration': '1 hour',
                'steps': [
                    {
                        'step': '2.1',
                        'action': 'Load 2024 data to staging',
                        'command': 'python load_to_staging.py --year 2024',
                        'validation': 'Record count matches expected for 2024',
                        'rollback': 'TRUNCATE cites_trade_records_staging;'
                    },
                    {
                        'step': '2.2',
                        'action': 'Validate staged data',
                        'command': 'python validate_staging_data.py --year 2024',
                        'validation': 'All validation checks pass',
                        'rollback': 'TRUNCATE cites_trade_records_staging;'
                    },
                    {
                        'step': '2.3',
                        'action': 'Test query performance',
                        'command': 'python test_query_performance.py',
                        'validation': 'Query times within acceptable range',
                        'rollback': 'N/A - Read only'
                    }
                ]
            },
            {
                'phase': 3,
                'name': 'Full Data Migration',
                'duration': '3-4 hours',
                'steps': [
                    {
                        'step': '3.1',
                        'action': 'Clear staging table',
                        'sql': 'TRUNCATE cites_trade_records_staging;',
                        'validation': 'Staging table empty',
                        'rollback': 'N/A'
                    },
                    {
                        'step': '3.2',
                        'action': 'Load all Arctic data to staging',
                        'command': 'python load_to_staging.py --all --batch-size 10000',
                        'validation': f"Staging has {new_data['new_record_count']} records",
                        'rollback': 'TRUNCATE cites_trade_records_staging;'
                    },
                    {
                        'step': '3.3',
                        'action': 'Validate all staged data',
                        'command': 'python validate_staging_data.py --all',
                        'validation': 'All validation checks pass',
                        'rollback': 'TRUNCATE cites_trade_records_staging;'
                    }
                ]
            },
            {
                'phase': 4,
                'name': 'Data Switchover',
                'duration': '30 minutes',
                'steps': [
                    {
                        'step': '4.1',
                        'action': 'Create backup of current table',
                        'sql': '''CREATE TABLE cites_trade_records_backup AS 
                                SELECT * FROM cites_trade_records;''',
                        'validation': 'Backup table has correct record count',
                        'rollback': 'N/A'
                    },
                    {
                        'step': '4.2',
                        'action': 'Rename tables for switchover',
                        'sql': '''BEGIN;
                                ALTER TABLE cites_trade_records RENAME TO cites_trade_records_old;
                                ALTER TABLE cites_trade_records_staging RENAME TO cites_trade_records;
                                COMMIT;''',
                        'validation': 'New table is active with correct data',
                        'rollback': '''BEGIN;
                                     ALTER TABLE cites_trade_records RENAME TO cites_trade_records_staging;
                                     ALTER TABLE cites_trade_records_old RENAME TO cites_trade_records;
                                     COMMIT;'''
                    },
                    {
                        'step': '4.3',
                        'action': 'Rebuild indexes',
                        'sql': 'REINDEX TABLE cites_trade_records;',
                        'validation': 'All indexes rebuilt successfully',
                        'rollback': 'N/A'
                    }
                ]
            },
            {
                'phase': 5,
                'name': 'Post-Migration Tasks',
                'duration': '1-2 hours',
                'steps': [
                    {
                        'step': '5.1',
                        'action': 'Update species_trade_summary',
                        'command': 'python update_trade_summary.py',
                        'validation': 'Summary table updated with new data',
                        'rollback': 'TRUNCATE species_trade_summary;'
                    },
                    {
                        'step': '5.2',
                        'action': 'Run comprehensive validation',
                        'command': 'python validate_migration.py --comprehensive',
                        'validation': 'All checks pass',
                        'rollback': 'Use phase 4.2 rollback'
                    },
                    {
                        'step': '5.3',
                        'action': 'Update documentation',
                        'command': 'python generate_migration_report.py',
                        'validation': 'Report generated successfully',
                        'rollback': 'N/A'
                    },
                    {
                        'step': '5.4',
                        'action': 'Clean up old tables (after validation period)',
                        'sql': 'DROP TABLE IF EXISTS cites_trade_records_old;',
                        'validation': 'Old table removed',
                        'rollback': 'N/A - Keep backup files'
                    }
                ]
            }
        ]
        
        self.plan['phases'] = phases
        
    def generate_risk_assessment(self):
        """Generate risk assessment"""
        
        self.plan['risk_assessment'] = {
            'high_risk': [
                {
                    'risk': 'Data corruption during migration',
                    'probability': 'Low',
                    'impact': 'High',
                    'mitigation': 'Comprehensive backups, staging validation, atomic switchover'
                },
                {
                    'risk': 'Service downtime',
                    'probability': 'Medium',
                    'impact': 'Medium',
                    'mitigation': 'Use staging table approach, minimize switchover time'
                }
            ],
            'medium_risk': [
                {
                    'risk': 'Performance degradation',
                    'probability': 'Low',
                    'impact': 'Medium',
                    'mitigation': 'Test queries before switchover, rebuild indexes'
                },
                {
                    'risk': 'Missing species mappings',
                    'probability': 'Low',
                    'impact': 'Low',
                    'mitigation': 'Pre-migration species validation'
                }
            ],
            'low_risk': [
                {
                    'risk': 'Incomplete 2024 data',
                    'probability': 'Low',
                    'impact': 'Low',
                    'mitigation': 'Verify with CITES data source'
                }
            ]
        }
        
    def generate_validation_checkpoints(self):
        """Generate validation checkpoints"""
        
        self.plan['validation_checkpoints'] = [
            {
                'checkpoint': 'Pre-Migration',
                'validations': [
                    'Current database backup completed',
                    'Staging table created successfully',
                    'All species mapped correctly',
                    'Disk space adequate (10GB free)'
                ]
            },
            {
                'checkpoint': 'Post-Staging',
                'validations': [
                    f"Record count matches expected",
                    'No duplicate records',
                    'All foreign keys valid',
                    'Date ranges correct',
                    'Species IDs all mapped'
                ]
            },
            {
                'checkpoint': 'Post-Switchover',
                'validations': [
                    'Application queries working',
                    'API endpoints responsive',
                    'Query performance acceptable',
                    'No error logs'
                ]
            },
            {
                'checkpoint': 'Final Validation',
                'validations': [
                    'Trade summary updated',
                    'All statistics regenerated',
                    'Documentation updated',
                    'Backup verified and stored'
                ]
            }
        ]
        
    def save_plan(self):
        """Save migration plan"""
        
        # Save JSON version
        json_path = os.path.join(self.base_dir, 'docs', 'migration_plan.json')
        with open(json_path, 'w') as f:
            json.dump(self.plan, f, indent=2)
            
        # Save Markdown version
        self.save_markdown_plan()
        
        print(f"✅ Migration plan saved to: {json_path}")
        
    def save_markdown_plan(self):
        """Save human-readable markdown plan"""
        
        md_content = f"""# CITES Arctic Species Data Migration Plan

Generated: {self.plan['generated_at']}

## Overview

This plan outlines the safe migration of {self.plan.get('total_records', 'N/A')} Arctic species CITES trade records into the production database.

## Migration Phases

"""
        
        for phase in self.plan['phases']:
            md_content += f"### Phase {phase['phase']}: {phase['name']}\n"
            md_content += f"**Duration**: {phase['duration']}\n\n"
            
            for step in phase['steps']:
                md_content += f"#### Step {step['step']}: {step['action']}\n"
                if 'command' in step:
                    md_content += f"**Command**: `{step['command']}`\n"
                if 'sql' in step:
                    md_content += f"**SQL**:\n```sql\n{step['sql']}\n```\n"
                md_content += f"**Validation**: {step['validation']}\n"
                md_content += f"**Rollback**: {step['rollback']}\n\n"
                
        md_content += "## Risk Assessment\n\n"
        
        for level, risks in self.plan['risk_assessment'].items():
            md_content += f"### {level.replace('_', ' ').title()}\n"
            for risk in risks:
                md_content += f"- **{risk['risk']}**\n"
                md_content += f"  - Probability: {risk['probability']}\n"
                md_content += f"  - Impact: {risk['impact']}\n"
                md_content += f"  - Mitigation: {risk['mitigation']}\n\n"
                
        md_content += "## Validation Checkpoints\n\n"
        
        for checkpoint in self.plan['validation_checkpoints']:
            md_content += f"### {checkpoint['checkpoint']}\n"
            for validation in checkpoint['validations']:
                md_content += f"- [ ] {validation}\n"
            md_content += "\n"
            
        md_content += """## Emergency Contacts

- Database Admin: [Contact Info]
- Application Owner: [Contact Info]
- On-Call Support: [Contact Info]

## Notes

- Always run in TEST environment first
- Keep communication channels open during migration
- Document any deviations from plan
- Verify backups before proceeding
"""
        
        md_path = os.path.join(self.base_dir, 'docs', 'migration_plan.md')
        with open(md_path, 'w') as f:
            f.write(md_content)
            
    def generate_plan(self):
        """Generate complete migration plan"""
        
        print("🚀 Generating CITES Arctic Species Migration Plan...")
        
        # Analyze current state
        current_state = self.analyze_current_state()
        print(f"📊 Current database: {current_state['current_record_count']} records")
        
        # Analyze new data
        new_data = self.analyze_new_data()
        print(f"📊 New Arctic data: {new_data['new_record_count']} records")
        
        # Store summary in plan
        self.plan['summary'] = {
            'current_state': current_state,
            'new_data': new_data,
            'total_records': new_data['new_record_count']
        }
        
        # Generate phases
        self.generate_migration_phases(current_state, new_data)
        
        # Generate risk assessment
        self.generate_risk_assessment()
        
        # Generate validation checkpoints
        self.generate_validation_checkpoints()
        
        # Save plan
        self.save_plan()
        
        print("\n✅ Migration plan generated successfully!")
        print(f"📄 Review the plan at: docs/migration_plan.md")
        print(f"⏱️  Estimated total time: 7-10 hours")
        print(f"📊 Records to migrate: {new_data['new_record_count']:,}")

if __name__ == "__main__":
    generator = MigrationPlanGenerator()
    generator.generate_plan()