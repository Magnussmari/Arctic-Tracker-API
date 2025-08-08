"""
API Configuration for External Services

This module manages API configurations and rate limiting for external services.
"""

import time
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .settings import get_cached_settings

@dataclass
class APIEndpoint:
    """Configuration for an API endpoint"""
    base_url: str
    rate_limit: float  # requests per second
    timeout: int = 30
    max_retries: int = 3

class APIConfigManager:
    """
    Manages API configurations and rate limiting
    """
    
    def __init__(self):
        """Initialize API configuration manager"""
        self.settings = get_cached_settings()
        self.last_request_times: Dict[str, float] = {}
        
        # Define API endpoints
        self.endpoints = {
            'cites': APIEndpoint(
                base_url='https://api.cites.org/api/v1',
                rate_limit=1.0,  # 1 request per second
                timeout=30,
                max_retries=3
            ),
            'iucn': APIEndpoint(
                base_url='https://api.iucnredlist.org/api/v4',
                rate_limit=0.5,  # 0.5 requests per second (more conservative)
                timeout=30,
                max_retries=3
            )
        }
    
    async def rate_limit(self, api_name: str) -> None:
        """
        Apply rate limiting for an API
        
        Args:
            api_name (str): Name of the API (e.g., 'cites', 'iucn')
        """
        if api_name not in self.endpoints:
            return
        
        endpoint = self.endpoints[api_name]
        current_time = time.time()
        
        if api_name in self.last_request_times:
            time_since_last = current_time - self.last_request_times[api_name]
            min_interval = 1.0 / endpoint.rate_limit
            
            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                await asyncio.sleep(sleep_time)
        
        self.last_request_times[api_name] = time.time()
    
    def get_api_headers(self, api_name: str) -> Dict[str, str]:
        """
        Get headers for API requests
        
        Args:
            api_name (str): Name of the API
            
        Returns:
            Dict[str, str]: Headers for the API request
        """
        headers = {
            'User-Agent': 'Arctic-Species-Tracker/1.0',
            'Accept': 'application/json'
        }
        
        if api_name == 'cites':
            headers.update({
                'X-Authentication-Token': self.settings.api.cites_api_token,
                'Authorization': f'Bearer {self.settings.api.cites_api_key}'
            })
        elif api_name == 'iucn':
            # IUCN API doesn't use headers for authentication
            # Token is passed as URL parameter instead
            pass
        
        return headers
    
    def get_endpoint_config(self, api_name: str) -> Optional[APIEndpoint]:
        """
        Get endpoint configuration
        
        Args:
            api_name (str): Name of the API
            
        Returns:
            Optional[APIEndpoint]: Endpoint configuration or None if not found
        """
        return self.endpoints.get(api_name)
    
    def build_api_url(self, api_name: str, endpoint: str, **params) -> str:
        """
        Build API URL with proper authentication parameters
        
        Args:
            api_name (str): Name of the API
            endpoint (str): API endpoint path
            **params: Additional URL parameters
            
        Returns:
            str: Complete API URL with authentication
        """
        config = self.get_endpoint_config(api_name)
        if not config:
            raise ValueError(f"Unknown API: {api_name}")
        
        base_url = config.base_url.rstrip('/')
        endpoint = endpoint.lstrip('/')
        url = f"{base_url}/{endpoint}"
        
        # Handle IUCN API token parameter
        if api_name == 'iucn' and self.settings.api.iucn_api_token:
            params['token'] = self.settings.api.iucn_api_token
        
        # Add parameters to URL
        if params:
            param_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            url += f"?{param_string}"
        
        return url
    
    async def make_request_with_retry(
        self, 
        api_name: str, 
        request_func, 
        *args, 
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make an API request with retry logic and rate limiting
        
        Args:
            api_name (str): Name of the API
            request_func: Function to make the request
            *args, **kwargs: Arguments for the request function
            
        Returns:
            Dict[str, Any]: Response data or error information
        """
        endpoint = self.get_endpoint_config(api_name)
        if not endpoint:
            return {'success': False, 'error': f'Unknown API: {api_name}'}
        
        for attempt in range(endpoint.max_retries + 1):
            try:
                # Apply rate limiting
                await self.rate_limit(api_name)
                
                # Make the request
                response = await request_func(*args, **kwargs)
                
                return {
                    'success': True,
                    'data': response,
                    'attempt': attempt + 1
                }
                
            except Exception as e:
                if attempt == endpoint.max_retries:
                    return {
                        'success': False,
                        'error': str(e),
                        'attempts': attempt + 1
                    }
                
                # Wait before retrying (exponential backoff)
                wait_time = (2 ** attempt) * self.settings.rate_limit_delay
                await asyncio.sleep(wait_time)
        
        return {'success': False, 'error': 'Max retries exceeded'}

# Global API config manager instance
_api_manager: Optional[APIConfigManager] = None

def get_api_config() -> APIConfigManager:
    """
    Get API configuration manager instance (singleton pattern)
    
    Returns:
        APIConfigManager: API configuration manager instance
    """
    global _api_manager
    if _api_manager is None:
        _api_manager = APIConfigManager()
    return _api_manager