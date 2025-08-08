"""
Core module for Arctic Species CITES Trade Data Import System

This module contains the core business logic and data processing components including:
- IUCN Red List API client
- CITES API integration
- Data processing utilities
- Species management logic

Usage:
    from rebuild.core import IUCNApiClient, get_iucn_client
    from rebuild.core.iucn_client import IUCNApiClient
"""

from .iucn_client import IUCNApiClient, get_iucn_client

__all__ = [
    'IUCNApiClient',
    'get_iucn_client'
]