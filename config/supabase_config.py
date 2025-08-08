#!/usr/bin/env python3
"""
Supabase Configuration

This module provides a configured Supabase client for the Arctic Species database.
It reads credentials from the .env file in the same directory.
"""

import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

def get_supabase_client(use_service_role: bool = False) -> Client:
    """
    Create and return a configured Supabase client.
    
    Args:
        use_service_role: If True, use the service role key instead of anon key
        
    Returns:
        Client: Configured Supabase client
        
    Raises:
        ValueError: If required environment variables are missing
        Exception: If client creation fails
    """
    # Load environment variables from .env file
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    
    # Get Supabase credentials
    supabase_url = os.getenv('SUPABASE_URL')
    
    # Choose which key to use based on the parameter
    if use_service_role:
        supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        if not supabase_key:
            # Try alternative key names
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        if not supabase_key:
            supabase_key = os.getenv('SUPABASE_ADMIN_KEY')
        if not supabase_key:
            raise ValueError("No service role key found. Please set SUPABASE_SERVICE_ROLE_KEY in .env")
    else:
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    # Validate credentials
    if not supabase_url:
        raise ValueError("SUPABASE_URL not found in environment variables")
    
    if not supabase_key:
        raise ValueError("Supabase key not found in environment variables")
    
    try:
        # Create and return the client
        supabase: Client = create_client(supabase_url, supabase_key)
        return supabase
    except Exception as e:
        raise Exception(f"Failed to create Supabase client: {e}")

def test_connection() -> bool:
    """
    Test the Supabase connection.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        client = get_supabase_client()
        # Test with a simple query
        response = client.table('species').select('id').limit(1).execute()
        return response.data is not None
    except Exception as e:
        print(f"Connection test failed: {e}")
        return False

if __name__ == '__main__':
    # Test the connection when run directly
    print("Testing Supabase connection...")
    if test_connection():
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed!")
