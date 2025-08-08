"""
Configuration Settings for Arctic Species CITES Trade Data Import System

This module provides centralized configuration management using environment variables.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from the config directory
config_dir = Path(__file__).parent
env_path = config_dir / '.env'

if env_path.exists():
    load_dotenv(env_path)
else:
    # Fallback to parent directory .env
    parent_env = config_dir.parent / '.env'
    if parent_env.exists():
        load_dotenv(parent_env)

@dataclass
class DatabaseSettings:
    """Database configuration settings"""
    supabase_url: str
    supabase_anon_key: str
    
    def __post_init__(self):
        if not self.supabase_url or not self.supabase_anon_key:
            raise ValueError("Missing required Supabase credentials")

@dataclass
class APISettings:
    """External API configuration settings"""
    cites_api_key: str
    cites_api_token: str
    iucn_api_token: Optional[str] = None
    
    def __post_init__(self):
        if not self.cites_api_key or not self.cites_api_token:
            raise ValueError("Missing required CITES API credentials")

@dataclass
class ApplicationSettings:
    """Main application settings"""
    database: DatabaseSettings
    api: APISettings
    
    # Data processing settings
    batch_size: int = 1000
    max_retries: int = 3
    rate_limit_delay: float = 1.0
    
    # File paths (relative to rebuild directory)
    data_dir: Path = Path("species_data")
    raw_data_dir: Path = Path("species_data/raw_data")
    cites_trade_dir: Path = Path("species_data/cites_trade")
    processed_dir: Path = Path("species_data/processed")
    docs_dir: Path = Path("docs")
    
    def __post_init__(self):
        # Convert relative paths to absolute paths from rebuild directory
        rebuild_dir = Path(__file__).parent.parent
        self.data_dir = rebuild_dir / self.data_dir
        self.raw_data_dir = rebuild_dir / self.raw_data_dir
        self.cites_trade_dir = rebuild_dir / self.cites_trade_dir
        self.processed_dir = rebuild_dir / self.processed_dir
        self.docs_dir = rebuild_dir / self.docs_dir

def get_settings() -> ApplicationSettings:
    """
    Get application settings from environment variables
    
    Returns:
        ApplicationSettings: Configured application settings
        
    Raises:
        ValueError: If required environment variables are missing
    """
    
    # Database settings
    database = DatabaseSettings(
        supabase_url=os.getenv('SUPABASE_URL', ''),
        supabase_anon_key=os.getenv('SUPABASE_ANON_KEY', '')
    )
    
    # API settings
    api = APISettings(
        cites_api_key=os.getenv('CITES_API_KEY', ''),
        cites_api_token=os.getenv('CITES_API_TOKEN', ''),
        iucn_api_token=os.getenv('IUCN_API_TOKEN')
    )
    
    # Application settings
    settings = ApplicationSettings(
        database=database,
        api=api,
        batch_size=int(os.getenv('BATCH_SIZE', '1000')),
        max_retries=int(os.getenv('MAX_RETRIES', '3')),
        rate_limit_delay=float(os.getenv('RATE_LIMIT_DELAY', '1.0'))
    )
    
    return settings

# Global settings instance
_settings: Optional[ApplicationSettings] = None

def get_cached_settings() -> ApplicationSettings:
    """
    Get cached settings instance (singleton pattern)
    
    Returns:
        ApplicationSettings: Cached application settings
    """
    global _settings
    if _settings is None:
        _settings = get_settings()
    return _settings