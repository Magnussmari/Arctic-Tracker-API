#!/usr/bin/env python3
"""
Quick Fix Version of Arctic Species Trade Data Pipeline
Implements immediate fixes without database changes
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import os
import sys
import logging
from supabase import create_client, Client

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.supabase_config import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ArcticSpeciesTradeAnalyzerFixed:
    def __init__(self):
        """Initialize the analyzer with species list and connection to database"""
        self.supabase: Client = get_supabase_client()
        
        # Species list from the CSV - with proper name mappings
        self.species_list = [
            "Aleutian cackling goose",
            "Siberian Sturgeon", 
            "Common Thresher Shark",
            "Sandhill Crane",
            "Short-eared Owl",
            "Bowhead Whale",
            "Minke Whale",
            "Atlantic White-sided Dolphin",
            "Baird's Beaked Whale",
            "Basking Shark",
            "Beluga Whale",
            "Blue Whale",
            "Canada Lynx",
            "Cuvier's beaked whale",
            "Dall's Porpoise",
            "Eskimo Curlew",
            "Fin Whale",
            "Gray Whale",
            "Gyrfalcon",
            "Harbour Porpoise",
            "Humpback Whale",
            "Long-finned Pilot Whale",
            "Narwhal",
            "North American River Otter",
            "North Atlantic Right Whale",
            "North Pacific Right Whale",  # Fixed typo from CSV
            "Northern bottlenose whale",
            "Orca",
            "Peregrine Falcon",
            "Polar Bear",
            "Porbeagle Shark",
            "Red-Breasted Goose",
            "Roseroot",
            "Rough-legged buzzard",
            "Sea Otter",
            "Sei Whale",
            "Short-tailed Albatross",
            "Siberian Crane",
            "Snowy Owl",
            "Sperm Whale",
            "Stejneger's beaked whale",
            "Walrus",
            "White-beaked Dolphin"
        ]
        
        # EXPANDED Common name to scientific name mapping
        self.name_mapping = {
            # Original mappings
            "Siberian Sturgeon": "Acipenser baerii",
            "Canada Lynx": "Lynx canadensis",
            "Narwhal": "Monodon monoceros",
            "Polar Bear": "Ursus maritimus",
            "Rough-legged buzzard": "Buteo lagopus",
            "Beluga Whale": "Delphinapterus leucas",
            "White-beaked Dolphin": "Lagenorhynchus albirostris",
            "Walrus": "Odobenus rosmarus",
            "Sperm Whale": "Physeter macrocephalus",
            "Snowy Owl": "Bubo scandiacus",
            "Gyrfalcon": "Falco rusticolus",
            "Peregrine Falcon": "Falco peregrinus",
            "Red-Breasted Goose": "Branta ruficollis",
            "Sea Otter": "Enhydra lutris",
            "North American River Otter": "Lontra canadensis",
            
            # NEW MAPPINGS for missing species
            "Aleutian cackling goose": "Branta hutchinsii leucopareia",
            "Dall's Porpoise": "Phocoenoides dalli",
            "Harbour Porpoise": "Phocoena phocoena",
            "North Pacific Right Whale": "Eubalaena japonica",
            "Roseroot": "Rhodiola rosea",
            
            # Additional mappings for other species
            "Common Thresher Shark": "Alopias vulpinus",
            "Sandhill Crane": "Antigone canadensis",
            "Short-eared Owl": "Asio flammeus",
            "Bowhead Whale": "Balaena mysticetus",
            "Minke Whale": "Balaenoptera acutorostrata",
            "Atlantic White-sided Dolphin": "Lagenorhynchus acutus",
            "Baird's Beaked Whale": "Berardius bairdii",
            "Basking Shark": "Cetorhinus maximus",
            "Blue Whale": "Balaenoptera musculus",
            "Cuvier's beaked whale": "Ziphius cavirostris",
            "Eskimo Curlew": "Numenius borealis",
            "Fin Whale": "Balaenoptera physalus",
            "Gray Whale": "Eschrichtius robustus",
            "Humpback Whale": "Megaptera novaeangliae",
            "Long-finned Pilot Whale": "Globicephala melas",
            "North Atlantic Right Whale": "Eubalaena glacialis",
            "Northern bottlenose whale": "Hyperoodon ampullatus",
            "Orca": "Orcinus orca",
            "Porbeagle Shark": "Lamna nasus",
            "Sei Whale": "Balaenoptera borealis",
            "Short-tailed Albatross": "Phoebastria albatrus",
            "Siberian Crane": "Leucogeranus leucogeranus",
            "Stejneger's beaked whale": "Mesoplodon stejnegeri"
        }
        
        self.arctic_states = ['CA', 'GL', 'US', 'RU', 'NO', 'IS', 'FI', 'SE', 'DK']
        self.purpose_codes = {
            'T': 'Commercial',
            'Z': 'Zoo',
            'S': 'Scientific',
            'E': 'Educational',
            'P': 'Personal',
            'B': 'Breeding',
            'Q': 'Circus/traveling exhibition',
            'H': 'Hunting trophy',
            'M': 'Medical',
            'N': 'Reintroduction',
            'L': 'Law enforcement'
        }
        
        self.source_codes = {
            'W': 'Wild',
            'F': 'Born in captivity',
            'C': 'Captive-bred',
            'D': 'Appendix-I bred for commercial purposes',
            'A': 'Plants artificially propagated',
            'I': 'Confiscated or seized',
            'O': 'Pre-convention',
            'R': 'Ranched',
            'U': 'Unknown'
        }
        
    def get_species_id(self, species_name: str) -> Optional[str]:
        """Query database for species ID using common or scientific name"""
        try:
            normalized_name = species_name.strip()
            
            # First check if we have a scientific name mapping
            scientific_name = self.name_mapping.get(normalized_name)
            
            if scientific_name:
                # Try scientific name first
                response = self.supabase.table('species').select('id').eq('scientific_name', scientific_name).limit(1).execute()
                if response.data and len(response.data) > 0:
                    logger.info(f"Found {species_name} by scientific name: {scientific_name}")
                    return response.data[0]['id']
            
            # Try by common name
            response = self.supabase.table('species').select('id').ilike('common_name', f'%{normalized_name}%').limit(1).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['id']
            
            # Try variations of the name
            name_variations = [
                normalized_name.lower(),
                normalized_name.replace('-', ' '),
                normalized_name.replace("'s", "")
            ]
            
            for variant in name_variations:
                response = self.supabase.table('species').select('id').ilike('common_name', f'%{variant}%').limit(1).execute()
                if response.data and len(response.data) > 0:
                    return response.data[0]['id']
                    
            logger.warning(f"Species not found in database: {species_name} (scientific: {scientific_name})")
            return None
            
        except Exception as e:
            logger.error(f"Error getting species ID for {species_name}: {str(e)}")
            return None
    
    def get_trade_summary_direct(self, species_id: str) -> Dict:
        """Get trade summary by direct query - bypasses empty summary table"""
        try:
            # Get all trade records for the species
            response = self.supabase.table('cites_trade_records').select('year, quantity').eq('species_id', species_id).execute()
            
            if not response.data:
                return {
                    'total_trade_records': 0,
                    'overall_total_quantity': 0,
                    'overall_min_year': None,
                    'overall_max_year': None
                }
            
            # Calculate summary statistics
            total_records = len(response.data)
            total_quantity = sum(r.get('quantity', 0) or 0 for r in response.data)
            years = [r.get('year') for r in response.data if r.get('year')]
            
            return {
                'total_trade_records': total_records,
                'overall_total_quantity': total_quantity,
                'overall_min_year': min(years) if years else None,
                'overall_max_year': max(years) if years else None
            }
            
        except Exception as e:
            logger.error(f"Error getting direct trade summary for species {species_id}: {str(e)}")
            return {
                'total_trade_records': 0,
                'overall_total_quantity': 0,
                'overall_min_year': None,
                'overall_max_year': None
            }
    
    def get_conservation_status(self, species_id: str) -> Dict:
        """Get IUCN and CITES status with FIXED column names"""
        try:
            result = {
                "iucn_status": "",
                "iucn_change": "No change",
                "cites_status": "",
                "cites_change": "No change"
            }
            
            # Get IUCN status
            iucn_response = self.supabase.table('iucn_assessments').select('status, year_published').eq('species_id', species_id).order('year_published', desc=True).limit(2).execute()
            
            if iucn_response.data:
                result["iucn_status"] = iucn_response.data[0].get('status', '')
                
                # Check for status change
                if len(iucn_response.data) > 1:
                    current = iucn_response.data[0].get('status', '')
                    previous = iucn_response.data[1].get('status', '')
                    if current != previous:
                        result["iucn_change"] = "Uplisted" if self._is_uplisted_iucn(previous, current) else "Delisted"
            
            # Get CITES status - FIXED to use 'listing_date' instead of 'effective_date'
            cites_response = self.supabase.table('cites_listings').select('appendix, listing_date').eq('species_id', species_id).order('listing_date', desc=True).limit(2).execute()
            
            if cites_response.data:
                result["cites_status"] = f"Appendix {cites_response.data[0].get('appendix', '')}"
                
                # Check for status change
                if len(cites_response.data) > 1:
                    current = cites_response.data[0].get('appendix', '')
                    previous = cites_response.data[1].get('appendix', '')
                    if current != previous:
                        result["cites_change"] = "Uplisted" if self._is_uplisted_cites(previous, current) else "Delisted"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting conservation status for species {species_id}: {str(e)}")
            return {
                "iucn_status": "",
                "iucn_change": "",
                "cites_status": "",
                "cites_change": ""
            }
    
    def _is_uplisted_iucn(self, previous: str, current: str) -> bool:
        """Determine if IUCN status was uplisted (more threatened)"""
        threat_order = ['LC', 'NT', 'VU', 'EN', 'CR', 'EW', 'EX']
        try:
            prev_idx = threat_order.index(previous)
            curr_idx = threat_order.index(current)
            return curr_idx > prev_idx
        except ValueError:
            return False
    
    def _is_uplisted_cites(self, previous: str, current: str) -> bool:
        """Determine if CITES status was uplisted (more restricted)"""
        # Lower appendix number = more restricted
        try:
            return int(current) < int(previous)
        except:
            return False
    
    def analyze_trade_purposes(self, species_id: str) -> Dict:
        """Analyze most common trade purposes"""
        try:
            # Get all trade records for this species
            response = self.supabase.table('cites_trade_records').select('purpose').eq('species_id', species_id).execute()
            
            if not response.data:
                return {"purpose": "", "percentage": ""}
            
            # Count by purpose
            purpose_counts = {}
            total_records = 0
            
            for record in response.data:
                purpose = record.get('purpose', 'Unknown')
                purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
                total_records += 1
            
            if total_records == 0:
                return {"purpose": "", "percentage": ""}
            
            # Find most common purpose
            most_common_purpose = max(purpose_counts.items(), key=lambda x: x[1])
            purpose_code = most_common_purpose[0]
            purpose_name = self.purpose_codes.get(purpose_code, purpose_code)
            percentage = round((most_common_purpose[1] / total_records) * 100, 1)
            
            return {
                "purpose": purpose_name,
                "percentage": f"{percentage}%"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trade purposes for species {species_id}: {str(e)}")
            return {"purpose": "", "percentage": ""}
    
    def analyze_sources(self, species_id: str) -> Dict:
        """Count wild and pre-convention sources"""
        try:
            response = self.supabase.table('cites_trade_records').select('source').eq('species_id', species_id).execute()
            
            wild_count = 0
            pre_convention_count = 0
            
            if response.data:
                for record in response.data:
                    source = record.get('source', '')
                    if source == 'W':
                        wild_count += 1
                    elif source == 'O':
                        pre_convention_count += 1
            
            return {
                "wild_count": wild_count,
                "pre_convention_count": pre_convention_count
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sources for species {species_id}: {str(e)}")
            return {"wild_count": 0, "pre_convention_count": 0}
    
    def get_latest_trade_data(self, species_id: str) -> float:
        """Get quantity traded in most recent year"""
        try:
            # Get the most recent year's data
            response = self.supabase.table('cites_trade_records').select('year, quantity').eq('species_id', species_id).order('year', desc=True).limit(100).execute()
            
            if not response.data:
                return 0.0
            
            # Group by year and sum quantities
            year_quantities = {}
            for record in response.data:
                year = record.get('year')
                quantity = record.get('quantity', 0) or 0
                if year:
                    year_quantities[year] = year_quantities.get(year, 0) + quantity
            
            if year_quantities:
                latest_year = max(year_quantities.keys())
                return year_quantities[latest_year]
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error getting latest trade data for species {species_id}: {str(e)}")
            return 0.0
    
    def calculate_trade_trend(self, species_id: str) -> str:
        """Calculate trade trend by comparing recent periods"""
        try:
            # Get trade data for recent years
            response = self.supabase.table('cites_trade_records').select('year, quantity').eq('species_id', species_id).gte('year', 2010).execute()
            
            if not response.data or len(response.data) < 5:
                return "insufficient data"
            
            # Group quantities by year
            year_quantities = {}
            for record in response.data:
                year = record.get('year')
                quantity = record.get('quantity', 0) or 0
                if year:
                    year_quantities[year] = year_quantities.get(year, 0) + quantity
            
            if len(year_quantities) < 5:
                return "insufficient data"
            
            # Sort years
            sorted_years = sorted(year_quantities.keys())
            
            # Calculate averages for first and last 3-year periods
            if len(sorted_years) >= 6:
                early_period = sorted_years[:3]
                late_period = sorted_years[-3:]
                
                early_avg = np.mean([year_quantities[y] for y in early_period])
                late_avg = np.mean([year_quantities[y] for y in late_period])
                
                # Determine trend
                if late_avg > early_avg * 1.2:  # 20% increase threshold
                    return "increasing"
                elif late_avg < early_avg * 0.8:  # 20% decrease threshold
                    return "decreasing"
                else:
                    return "stable"
            
            return "stable"
            
        except Exception as e:
            logger.error(f"Error calculating trade trend for species {species_id}: {str(e)}")
            return "unknown"
    
    def analyze_exporters(self, species_id: str) -> Dict:
        """Analyze top exporting countries"""
        try:
            # Get all trade records with exporter info
            response = self.supabase.table('cites_trade_records').select('exporter, quantity').eq('species_id', species_id).execute()
            
            if not response.data:
                return {"arctic": "", "global": ""}
            
            # Aggregate by exporter
            exporter_totals = {}
            total_quantity = 0
            
            for record in response.data:
                exporter = record.get('exporter', 'Unknown')
                quantity = record.get('quantity', 0) or 0
                exporter_totals[exporter] = exporter_totals.get(exporter, 0) + quantity
                total_quantity += quantity
            
            if total_quantity == 0:
                return {"arctic": "", "global": ""}
            
            # Find top arctic exporter
            arctic_exporters = {k: v for k, v in exporter_totals.items() if k in self.arctic_states}
            if arctic_exporters:
                top_arctic = max(arctic_exporters.items(), key=lambda x: x[1])
                arctic_percentage = round((top_arctic[1] / total_quantity) * 100, 1)
                arctic_result = f"{top_arctic[0]} - {arctic_percentage}%"
            else:
                arctic_result = ""
            
            # Find top global exporter
            if exporter_totals:
                top_global = max(exporter_totals.items(), key=lambda x: x[1])
                global_percentage = round((top_global[1] / total_quantity) * 100, 1)
                global_result = f"{top_global[0]} - {global_percentage}%"
            else:
                global_result = ""
            
            return {
                "arctic": arctic_result,
                "global": global_result
            }
            
        except Exception as e:
            logger.error(f"Error analyzing exporters for species {species_id}: {str(e)}")
            return {"arctic": "", "global": ""}
    
    def process_species(self, species_name: str) -> Dict:
        """Process data for a single species with all fixes applied"""
        result = {
            "Species": species_name,
            "Numbers of records": "",
            "Quantity": "",
            "Most recorded trade use": "",
            "% of trades for most recorded trade use": "",
            "Origins of traded specimens trade which are 'wild'": "",
            "Origins of species. Numbers of species traded which are 'Pre-convention'": "",
            "Period covered": "",
            "Last recorded annual quantity traded": "",
            "Overall Trade Trend (increasing, stable or decreasing)": "",
            "Numbers of CITES Trade Suspension(s) which involve Arctic state(s); and names of those states": "",
            "IUCN Status": "",
            "IUCN Status (No change, Uplisted, Delisted)": "",
            "CITES status": "",
            "CITES status (No change, Uplisted, Delisted)": "",
            "CMS status": "",
            "CMS status (No change, Uplisted, Delisted)": "",
            "Top exporter Arctic state - and % of trade they account for": "",
            "Top exporter state - and % of trade they account for": ""
        }
        
        try:
            # Step 1: Get species ID from database
            species_id = self.get_species_id(species_name)
            if not species_id:
                logger.warning(f"Species ID not found for: {species_name}")
                return result
            
            logger.info(f"Processing {species_name} (ID: {species_id})")
            
            # Step 2: Get trade summary data - USING DIRECT QUERY
            trade_summary = self.get_trade_summary_direct(species_id)
            if trade_summary:
                result["Numbers of records"] = str(trade_summary.get("total_trade_records", ""))
                result["Quantity"] = str(trade_summary.get("overall_total_quantity", ""))
                if trade_summary.get('overall_min_year') and trade_summary.get('overall_max_year'):
                    result["Period covered"] = f"{trade_summary['overall_min_year']}-{trade_summary['overall_max_year']}"
            
            # Step 3: Analyze trade purposes
            purpose_analysis = self.analyze_trade_purposes(species_id)
            if purpose_analysis:
                result["Most recorded trade use"] = purpose_analysis["purpose"]
                result["% of trades for most recorded trade use"] = purpose_analysis["percentage"]
            
            # Step 4: Analyze sources
            source_analysis = self.analyze_sources(species_id)
            result["Origins of traded specimens trade which are 'wild'"] = str(source_analysis["wild_count"])
            result["Origins of species. Numbers of species traded which are 'Pre-convention'"] = str(source_analysis["pre_convention_count"])
            
            # Step 5: Get latest trade data
            latest_trade = self.get_latest_trade_data(species_id)
            result["Last recorded annual quantity traded"] = str(int(latest_trade)) if latest_trade else ""
            
            # Step 6: Calculate trade trend
            trend = self.calculate_trade_trend(species_id)
            result["Overall Trade Trend (increasing, stable or decreasing)"] = trend
            
            # Step 7: Get conservation status - WITH FIXED COLUMN NAMES
            conservation = self.get_conservation_status(species_id)
            result["IUCN Status"] = conservation.get("iucn_status", "")
            result["IUCN Status (No change, Uplisted, Delisted)"] = conservation.get("iucn_change", "")
            result["CITES status"] = conservation.get("cites_status", "")
            result["CITES status (No change, Uplisted, Delisted)"] = conservation.get("cites_change", "")
            
            # Step 8: Analyze exporters
            exporters = self.analyze_exporters(species_id)
            result["Top exporter Arctic state - and % of trade they account for"] = exporters["arctic"]
            result["Top exporter state - and % of trade they account for"] = exporters["global"]
            
        except Exception as e:
            logger.error(f"Error processing species {species_name}: {str(e)}")
        
        return result
    
    def generate_report(self) -> pd.DataFrame:
        """Generate complete report for all species"""
        results = []
        
        logger.info(f"Starting report generation for {len(self.species_list)} species")
        
        for i, species in enumerate(self.species_list, 1):
            logger.info(f"Processing {i}/{len(self.species_list)}: {species}")
            species_data = self.process_species(species)
            results.append(species_data)
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Ensure column order matches the original CSV
        column_order = [
            "Species",
            "Numbers of records",
            "Quantity",
            "Most recorded trade use",
            "% of trades for most recorded trade use",
            "Origins of traded specimens trade which are 'wild'",
            "Origins of species. Numbers of species traded which are 'Pre-convention'",
            "Period covered",
            "Last recorded annual quantity traded",
            "Overall Trade Trend (increasing, stable or decreasing)",
            "Numbers of CITES Trade Suspension(s) which involve Arctic state(s); and names of those states",
            "IUCN Status",
            "IUCN Status (No change, Uplisted, Delisted)",
            "CITES status",
            "CITES status (No change, Uplisted, Delisted)",
            "CMS status",
            "CMS status (No change, Uplisted, Delisted)",
            "Top exporter Arctic state - and % of trade they account for",
            "Top exporter state - and % of trade they account for"
        ]
        
        df = df[column_order]
        
        logger.info("Report generation completed")
        return df
    
    def export_to_csv(self, df: pd.DataFrame, filename: str = "arctic_species_trade_FIXED.csv"):
        """Export results to CSV with semicolon separator"""
        output_path = os.path.join(os.path.dirname(__file__), filename)
        df.to_csv(output_path, index=False, sep=";", encoding='utf-8-sig')
        logger.info(f"Data exported to {output_path}")

# Main execution
if __name__ == "__main__":
    try:
        logger.info("Starting Arctic Species Trade Data Pipeline - FIXED VERSION")
        analyzer = ArcticSpeciesTradeAnalyzerFixed()
        report = analyzer.generate_report()
        analyzer.export_to_csv(report)
        print("\n✅ Trade data extraction completed successfully!")
        print("📄 Output file: arctic_species_trade_FIXED.csv")
    except Exception as e:
        logger.error(f"Failed to generate report: {str(e)}")
        raise