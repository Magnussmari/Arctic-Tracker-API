"""
Database Configuration and Connection Management

This module handles database connections and provides utilities for database operations.
"""

import asyncio
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
from .settings import get_cached_settings

class DatabaseManager:
    """
    Manages database connections and provides common database operations
    """
    
    def __init__(self):
        """Initialize database manager with settings"""
        self.settings = get_cached_settings()
        self._client: Optional[Client] = None
    
    @property
    def client(self) -> Client:
        """
        Get Supabase client (lazy initialization)
        
        Returns:
            Client: Supabase client instance
        """
        if self._client is None:
            self._client = create_client(
                self.settings.database.supabase_url,
                self.settings.database.supabase_anon_key
            )
        return self._client
    
    async def test_connection(self) -> bool:
        """
        Test database connection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Try a simple query to test connection
            response = self.client.table('cites_trade_records').select('id').limit(1).execute()
            return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    async def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """
        Get information about a database table
        
        Args:
            table_name (str): Name of the table to inspect
            
        Returns:
            Dict[str, Any]: Table information including schema and row count
        """
        try:
            # Get row count
            count_response = self.client.table(table_name).select('id', count='exact').execute()
            row_count = count_response.count
            
            # Get sample data to understand schema
            sample_response = self.client.table(table_name).select('*').limit(1).execute()
            schema = {}
            if sample_response.data:
                schema = {key: type(value).__name__ for key, value in sample_response.data[0].items()}
            
            return {
                'table_name': table_name,
                'row_count': row_count,
                'schema': schema,
                'sample_data': sample_response.data[0] if sample_response.data else None
            }
            
        except Exception as e:
            return {
                'table_name': table_name,
                'error': str(e),
                'row_count': 0,
                'schema': {}
            }
    
    async def get_all_tables(self) -> List[str]:
        """
        Get list of all tables in the database
        
        Returns:
            List[str]: List of table names
        """
        # This is a simplified version - in practice you might need to query
        # the information_schema or use Supabase's admin API
        known_tables = [
            'cites_trade_records',
            'cites_species', 
            'iucn_assessments',
            'species',
            'taxonomy'
        ]
        
        existing_tables = []
        for table in known_tables:
            try:
                response = self.client.table(table).select('id').limit(1).execute()
                existing_tables.append(table)
            except:
                continue
                
        return existing_tables
    
    async def execute_query(self, table: str, operation: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a database query with error handling
        
        Args:
            table (str): Table name
            operation (str): Operation type (select, insert, update, delete)
            **kwargs: Query parameters
            
        Returns:
            Dict[str, Any]: Query result with metadata
        """
        try:
            table_ref = self.client.table(table)
            
            if operation == 'select':
                response = table_ref.select(kwargs.get('columns', '*')).execute()
            elif operation == 'insert':
                response = table_ref.insert(kwargs.get('data', {})).execute()
            elif operation == 'update':
                response = table_ref.update(kwargs.get('data', {})).execute()
            elif operation == 'delete':
                response = table_ref.delete().execute()
            else:
                raise ValueError(f"Unsupported operation: {operation}")
            
            return {
                'success': True,
                'data': response.data,
                'count': getattr(response, 'count', len(response.data) if response.data else 0)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': None,
                'count': 0
            }

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_db() -> DatabaseManager:
    """
    Get database manager instance (singleton pattern)
    
    Returns:
        DatabaseManager: Database manager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager