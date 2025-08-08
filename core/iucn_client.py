"""
IUCN Red List API Client for Arctic Species Project

This module provides a modern, async IUCN API client that integrates with the rebuild
configuration system and provides proper rate limiting and error handling.
"""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
import sys
from pathlib import Path

# Add rebuild directory to path for imports
rebuild_dir = Path(__file__).parent.parent
sys.path.insert(0, str(rebuild_dir))

from config import get_api_config, get_cached_settings

class IUCNApiClient:
    """
    Modern IUCN Red List API client with async support and proper configuration
    """
    
    def __init__(self):
        """Initialize IUCN API client"""
        self.api_config = get_api_config()
        self.settings = get_cached_settings()
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, **params) -> Dict[str, Any]:
        """
        Make a request to the IUCN API with proper rate limiting
        
        Args:
            endpoint (str): API endpoint
            **params: URL parameters
            
        Returns:
            Dict[str, Any]: API response data
        """
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")
        
        # Build URL with authentication
        url = self.api_config.build_api_url('iucn', endpoint, **params)
        headers = self.api_config.get_api_headers('iucn')
        
        # Use the retry mechanism from api_config
        async def make_request():
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    return {'result': []}  # No data found
                else:
                    response.raise_for_status()
        
        result = await self.api_config.make_request_with_retry('iucn', make_request)
        
        if result['success']:
            return result['data']
        else:
            raise Exception(f"IUCN API request failed: {result['error']}")
    
    async def get_api_version(self) -> Dict[str, Any]:
        """
        Get IUCN API version information
        
        Returns:
            Dict[str, Any]: API version information
        """
        return await self._make_request('version')
    
    async def get_species_by_name(self, name: str) -> Dict[str, Any]:
        """
        Search for species by scientific name using IUCN API v4
        
        Args:
            name (str): Scientific name to search for
            
        Returns:
            Dict[str, Any]: Species search results
        """
        return await self._make_request(f'taxa/scientific_name/{name}')
    
    async def get_species_assessments(self, genus: str, species: str, region: str = None) -> Dict[str, Any]:
        """
        Get species assessments from IUCN Red List using v4 API
        
        Args:
            genus (str): Species genus
            species (str): Species name
            region (str, optional): Region code for regional assessments
            
        Returns:
            Dict[str, Any]: Assessment data including status and details
        """
        scientific_name = f"{genus} {species}"
        return await self.get_species_by_name(scientific_name)
    
    async def get_assessment_details(self, assessment_id: int) -> Dict[str, Any]:
        """
        Get detailed assessment information using assessment ID
        
        Args:
            assessment_id (int): IUCN assessment ID
            
        Returns:
            Dict[str, Any]: Detailed assessment data
        """
        return await self._make_request(f'assessment/{assessment_id}')
    
    async def get_species_narrative(self, species_id: int) -> Dict[str, Any]:
        """
        Get species narrative information
        
        Args:
            species_id (int): IUCN species ID
            
        Returns:
            Dict[str, Any]: Species narrative data
        """
        return await self._make_request(f'species/narrative/{species_id}')
    
    async def get_threats(self, species_id: int) -> Dict[str, Any]:
        """
        Get threat information for a species
        
        Args:
            species_id (int): IUCN species ID
            
        Returns:
            Dict[str, Any]: Threat data
        """
        return await self._make_request(f'threats/species/id/{species_id}')
    
    async def get_habitats(self, species_id: int) -> Dict[str, Any]:
        """
        Get habitat information for a species
        
        Args:
            species_id (int): IUCN species ID
            
        Returns:
            Dict[str, Any]: Habitat data
        """
        return await self._make_request(f'habitats/species/id/{species_id}')
    
    def extract_genus_species(self, scientific_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract genus and species from scientific name
        
        Args:
            scientific_name (str): Full scientific name
            
        Returns:
            Tuple[Optional[str], Optional[str]]: (genus, species) or (None, None) if invalid
        """
        parts = scientific_name.strip().split()
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None, None
    
    async def process_species_list(self, species_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a list of species and get their IUCN assessments
        
        Args:
            species_list (List[Dict[str, Any]]): List of species data with 'species_name' field
            
        Returns:
            List[Dict[str, Any]]: Processed assessment data
        """
        results = []
        
        for species_data in species_list:
            species_name = species_data.get('species_name', '').strip()
            genus, species = self.extract_genus_species(species_name)
            
            if not genus or not species:
                print(f"Skipping invalid name: {species_name}")
                continue
                
            print(f"Querying IUCN for: {species_name}")
            
            try:
                assessment_data = await self.get_species_assessments(genus, species)
                
                if assessment_data and 'result' in assessment_data and assessment_data['result']:
                    for assessment in assessment_data['result']:
                        entry = {
                            'species_id': species_data.get('species_id'),
                            'species_name': species_name,
                            'taxonid': assessment.get('taxonid'),
                            'scientific_name': assessment.get('scientific_name'),
                            'kingdom': assessment.get('kingdom'),
                            'phylum': assessment.get('phylum'),
                            'class': assessment.get('class'),
                            'order': assessment.get('order'),
                            'family': assessment.get('family'),
                            'genus': assessment.get('genus'),
                            'main_common_name': assessment.get('main_common_name'),
                            'authority': assessment.get('authority'),
                            'published_year': assessment.get('published_year'),
                            'assessment_date': assessment.get('assessment_date'),
                            'category': assessment.get('category'),
                            'criteria': assessment.get('criteria'),
                            'population_trend': assessment.get('population_trend'),
                            'marine_system': assessment.get('marine_system'),
                            'freshwater_system': assessment.get('freshwater_system'),
                            'terrestrial_system': assessment.get('terrestrial_system'),
                            'assessor': assessment.get('assessor'),
                            'reviewer': assessment.get('reviewer'),
                            'aoo_km2': assessment.get('aoo_km2'),
                            'eoo_km2': assessment.get('eoo_km2'),
                            'elevation_upper': assessment.get('elevation_upper'),
                            'elevation_lower': assessment.get('elevation_lower'),
                            'depth_upper': assessment.get('depth_upper'),
                            'depth_lower': assessment.get('depth_lower'),
                            'errata_flag': assessment.get('errata_flag'),
                            'errata_reason': assessment.get('errata_reason'),
                            'amended_flag': assessment.get('amended_flag'),
                            'amended_reason': assessment.get('amended_reason')
                        }
                        results.append(entry)
                else:
                    # Add a 'Not Listed' entry for species not found
                    entry = {
                        'species_id': species_data.get('species_id'),
                        'species_name': species_name,
                        'category': 'Not Listed',
                        'assessment_date': None,
                        'published_year': None,
                        'main_common_name': None,
                        'authority': None,
                        'population_trend': None
                    }
                    results.append(entry)
                    print(f"No assessment found for {species_name}")
                    
            except Exception as e:
                print(f"Error processing {species_name}: {e}")
                # Add error entry
                entry = {
                    'species_id': species_data.get('species_id'),
                    'species_name': species_name,
                    'category': 'Error',
                    'error': str(e)
                }
                results.append(entry)
        
        return results

# Convenience function for backward compatibility
async def get_iucn_client() -> IUCNApiClient:
    """
    Get an IUCN API client instance
    
    Returns:
        IUCNApiClient: Configured IUCN API client
    """
    return IUCNApiClient()