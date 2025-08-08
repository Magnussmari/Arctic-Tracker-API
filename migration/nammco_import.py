import pandas as pd
from pathlib import Path
import sys
import os
from datetime import datetime

# Add config directory to path
sys.path.append(str(Path(__file__).parent.parent / 'config'))

# Import the working Supabase configuration
try:
    from supabase_config import get_supabase_client
    supabase = get_supabase_client()
    print("✅ Supabase client created successfully")
except ImportError:
    print("❌ Error: Could not import supabase_config. Please ensure config/supabase_config.py exists.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error creating Supabase client: {e}")
    sys.exit(1)

# Set this to a species filename (without .csv) to filter, or None for all
SINGLE_SPECIES = None  # Process all files

# Directory containing all NAMMCO CSVs
CSV_DIR = Path("/Users/magnussmari/Arctic-Tracker-API/species_data/nammco")

def create_basic_species(scientific_name):
    """Create a basic species entry if it doesn't exist"""
    try:
        # Parse scientific name into genus and species
        name_parts = scientific_name.strip().split()
        if len(name_parts) < 2:
            print(f"  ❌ Invalid scientific name format: {scientific_name}")
            return None
            
        genus = name_parts[0]
        species_name = name_parts[1]
        
        # Create basic species record
        new_species = {
            'scientific_name': scientific_name,
            'common_name': scientific_name,  # Use scientific name as fallback
            'kingdom': 'ANIMALIA',  # Default for NAMMCO species
            'phylum': 'CHORDATA',   # Default for marine mammals
            'class': 'MAMMALIA',    # Default for NAMMCO species
            'order_name': 'UNKNOWN',
            'family': 'UNKNOWN',
            'genus': genus,
            'species_name': species_name,
            'authority': 'NAMMCO Import'
        }
        
        response = supabase.table('species').insert(new_species).execute()
        
        if response.data and len(response.data) > 0:
            new_species_id = response.data[0]['id']
            print(f"  ✅ Created new species: {scientific_name} (ID: {new_species_id})")
            return new_species_id
        else:
            print(f"  ❌ Failed to create species '{scientific_name}': {response}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error creating species '{scientific_name}': {e}")
        return None

def extract_family_from_filename(filename):
    """Extract taxonomic family information from CSV filename"""
    filename_lower = filename.lower()
    
    # Map common NAMMCO species to their taxonomic families
    family_mappings = {
        'balaenoptera': {'family': 'BALAENOPTERIDAE', 'order': 'CETACEA'},  # Rorqual whales
        'balaena': {'family': 'BALAENIDAE', 'order': 'CETACEA'},  # Right whales
        'megaptera': {'family': 'BALAENOPTERIDAE', 'order': 'CETACEA'},  # Humpback whale
        'physeter': {'family': 'PHYSETERIDAE', 'order': 'CETACEA'},  # Sperm whale
        'monodon': {'family': 'MONODONTIDAE', 'order': 'CETACEA'},  # Narwhal
        'delphinapterus': {'family': 'MONODONTIDAE', 'order': 'CETACEA'},  # Beluga
        'orcinus': {'family': 'DELPHINIDAE', 'order': 'CETACEA'},  # Orca
        'globicephala': {'family': 'DELPHINIDAE', 'order': 'CETACEA'},  # Pilot whales
        'lagenorhynchus': {'family': 'DELPHINIDAE', 'order': 'CETACEA'},  # White-sided dolphins
        'phocoena': {'family': 'PHOCOENIDAE', 'order': 'CETACEA'},  # Porpoises
        'odobenus': {'family': 'ODOBENIDAE', 'order': 'CARNIVORA'},  # Walrus
        'phoca': {'family': 'PHOCIDAE', 'order': 'CARNIVORA'},  # Seals
        'halichoerus': {'family': 'PHOCIDAE', 'order': 'CARNIVORA'},  # Grey seal
        'pagophilus': {'family': 'PHOCIDAE', 'order': 'CARNIVORA'},  # Harp seal
        'cystophora': {'family': 'PHOCIDAE', 'order': 'CARNIVORA'},  # Hooded seal
        'erignathus': {'family': 'PHOCIDAE', 'order': 'CARNIVORA'},  # Bearded seal
        'ursus': {'family': 'URSIDAE', 'order': 'CARNIVORA'},  # Bears
    }
    
    # Check filename for genus matches
    for genus, family_info in family_mappings.items():
        if genus in filename_lower:
            return family_info
    
    # Default for unknown species
    return {'family': 'UNKNOWN', 'order': 'CETACEA'}

def get_or_create_species(scientific_name, csv_filename=None):
    """Get species ID by scientific name or create if doesn't exist"""
    try:
        # Clean the scientific name
        scientific_name_clean = scientific_name.strip() if scientific_name else ''
        if not scientific_name_clean:
            print(f"  ❌ Empty scientific name provided")
            return None
            
        # First, check if species exists
        response = supabase.table('species').select('id', 'scientific_name').eq('scientific_name', scientific_name_clean).execute()
        
        if response.data and len(response.data) > 0:
            species_id = response.data[0]['id']
            print(f"  ✅ Found existing species: {scientific_name_clean} (ID: {species_id})")
            return species_id
        else:
            # Species not found - try case-insensitive search first
            print(f"  🔍 Exact match not found for '{scientific_name_clean}', trying case-insensitive search...")
            
            # Get all species for case-insensitive comparison
            all_species_response = supabase.table('species').select('id', 'scientific_name').execute()
            if all_species_response.data:
                for species in all_species_response.data:
                    if species['scientific_name'].lower() == scientific_name_clean.lower():
                        species_id = species['id']
                        print(f"  ✅ Found species with case difference: {species['scientific_name']} (ID: {species_id})")
                        return species_id
            
            # Still not found - create new species
            print(f"  🔧 Species '{scientific_name_clean}' not found in database, creating new entry...")
            return create_species_from_csv_data(scientific_name_clean, csv_filename or 'unknown')
            
    except Exception as e:
        print(f"  ❌ Error getting/creating species '{scientific_name}': {e}")
        return None

def create_species_from_csv_data(scientific_name, csv_file_name):
    """Create a basic species entry from NAMMCO CSV data"""
    try:
        # Parse scientific name into genus and species
        name_parts = scientific_name.strip().split()
        if len(name_parts) < 2:
            print(f"  ❌ Invalid scientific name format: {scientific_name}")
            return None
            
        genus = name_parts[0]
        species_name = name_parts[1]
        
        # Determine taxonomic info based on NAMMCO context (marine mammals)
        # Parse family info from CSV filename if available
        family_info = extract_family_from_filename(csv_file_name)
        
        # Create basic species record with marine mammal defaults
        new_species = {
            'scientific_name': scientific_name,
            'common_name': scientific_name,  # Use scientific name as fallback
            'kingdom': 'ANIMALIA',
            'phylum': 'CHORDATA',
            'class': 'MAMMALIA',  # NAMMCO focuses on marine mammals
            'order_name': family_info.get('order', 'CETACEA'),  # Default to whales/dolphins
            'family': family_info.get('family', 'UNKNOWN'),
            'genus': genus,
            'species_name': species_name,
            'authority': 'NAMMCO Import - Auto-created',
            'description': f'Species auto-created during NAMMCO data import from {csv_file_name}',
            'habitat_description': 'Marine environment - Arctic/North Atlantic waters'
        }
        
        # Insert the new species
        response = supabase.table('species').insert(new_species).execute()
        
        if response.data and len(response.data) > 0:
            new_species_id = response.data[0]['id']
            print(f"  ✅ Created new species: {scientific_name} (ID: {new_species_id})")
            return new_species_id
        else:
            print(f"  ❌ Failed to create species '{scientific_name}': {response}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error creating species '{scientific_name}': {e}")
        return None

def get_or_create_country(country_name):
    """Get country ID by name or create if doesn't exist"""
    if not country_name or country_name.strip() == '':
        return None
        
    try:
        country_clean = country_name.strip()
        
        # Try exact match first
        response = supabase.table('countries').select('id', 'country_name').eq('country_name', country_clean).execute()
        
        if response.data and len(response.data) > 0:
            country_id = response.data[0]['id']
            print(f"  ✅ Found country: {country_clean} (ID: {country_id})")
            return country_id
        else:
            # Try case-insensitive search
            all_countries_response = supabase.table('countries').select('id', 'country_name').execute()
            if all_countries_response.data:
                for country in all_countries_response.data:
                    if country['country_name'].lower() == country_clean.lower():
                        country_id = country['id']
                        print(f"  ✅ Found country with case difference: {country['country_name']} (ID: {country_id})")
                        return country_id
            
            # Create new country
            print(f"  🔧 Creating new country: {country_clean}")
            new_country = {
                'country_name': country_clean,
                'nammco_member': True  # Assume NAMMCO member if in NAMMCO data
            }
            
            insert_response = supabase.table('countries').insert(new_country).execute()
            
            if insert_response.data and len(insert_response.data) > 0:
                new_country_id = insert_response.data[0]['id']
                print(f"  ✅ Created new country: {country_clean} (ID: {new_country_id})")
                return new_country_id
            else:
                print(f"  ❌ Failed to create country '{country_clean}': {insert_response}")
                return None
                
    except Exception as e:
        print(f"  ❌ Error getting/creating country '{country_name}': {e}")
        return None

def get_country_id(country_name):
    """Get country ID by name"""
    return get_or_create_country(country_name)

def get_or_create_area(area_name, country_id=None):
    """Get or create management area"""
    if not area_name or area_name.strip() == '':
        return None
        
    area_clean = area_name.strip()
    
    try:
        # Check if area exists with the same name and country_id
        if country_id:
            response = supabase.table('management_areas').select('id').eq('area_name', area_clean).eq('country_id', country_id).execute()
        else:
            response = supabase.table('management_areas').select('id').eq('area_name', area_clean).is_('country_id', 'null').execute()
        
        if response.data and len(response.data) > 0:
            area_id = response.data[0]['id']
            print(f"  ✅ Found area: {area_clean} (ID: {area_id})")
            return area_id
        else:
            # Create new area
            new_area = {
                'area_name': area_clean,
                'area_type': 'NAMMCO'
            }
            
            if country_id:
                new_area['country_id'] = country_id
            
            insert_response = supabase.table('management_areas').insert(new_area).execute()
            
            if insert_response.data and len(insert_response.data) > 0:
                new_area_id = insert_response.data[0]['id']
                print(f"  ✅ Created new management area: {area_clean} (ID: {new_area_id})")
                return new_area_id
            else:
                print(f"  ❌ Failed to create area '{area_clean}': {insert_response}")
                return None
    except Exception as e:
        print(f"  ❌ Error with area '{area_clean}': {e}")
        return None

def insert_catch_record(species_id, country_id, area_id, year, catch_total, quota_amount=None, quota_notes=None, notes=None):
    """Insert catch record into database"""
    try:
        # Validate required fields
        if not species_id:
            print(f"  ❌ Missing species_id for catch record")
            return False
            
        if not year:
            print(f"  ❌ Missing year for catch record")
            return False
        
        # Clean and validate data
        try:
            year_int = int(year)
            
            # Handle catch_total
            if catch_total and str(catch_total).strip() != '' and str(catch_total).lower() != 'nan':
                catch_total_int = int(float(catch_total))  # Convert via float first to handle decimals
            else:
                catch_total_int = None
            
            # Handle quota_amount with NaN check
            if quota_amount and str(quota_amount).strip() != '' and str(quota_amount).lower() != 'nan':
                quota_amount_int = int(float(quota_amount))  # Convert via float first to handle decimals
            else:
                quota_amount_int = None
                
        except (ValueError, TypeError) as ve:
            print(f"  ❌ Invalid numeric data: year={year}, catch_total={catch_total}, quota={quota_amount}: {ve}")
            return False
        
        catch_record = {
            'species_id': species_id,
            'year': year_int,
            'data_source': 'NAMMCO'
        }
        
        # Add optional fields only if they have values
        if country_id:
            catch_record['country_id'] = country_id
        if area_id:
            catch_record['management_area_id'] = area_id
        if catch_total_int is not None:
            catch_record['catch_total'] = catch_total_int
        if quota_amount_int is not None:
            catch_record['quota_amount'] = quota_amount_int
        if quota_notes and str(quota_notes).strip():
            catch_record['quota_notes'] = str(quota_notes).strip()
        if notes and str(notes).strip():
            catch_record['notes'] = str(notes).strip()
        
        response = supabase.table('catch_records').insert(catch_record).execute()
        
        if response.data and len(response.data) > 0:
            record_id = response.data[0]['id']
            print(f"  ✅ Inserted catch record (ID: {record_id}) - Year: {year_int}, Catch: {catch_total_int}")
            return True
        else:
            print(f"  ❌ Failed to insert catch record: {response}")
            return False
    except Exception as e:
        print(f"  ❌ Error inserting catch record: {e}")
        return False

def get_column_value(row, column_variants):
    """Get value from row using multiple possible column names"""
    for col_name in column_variants:
        if col_name in row.index and pd.notna(row[col_name]):
            return row[col_name]
    return None

def test_database_connection():
    """Test database connection and basic operations"""
    try:
        print("🔧 Testing database connection...")
        
        # Test basic table access
        response = supabase.table('species').select('id', 'scientific_name').limit(5).execute()
        
        if response.data:
            print(f"  ✅ Database connection successful")
            print(f"  📊 Found {len(response.data)} sample species:")
            for species in response.data[:3]:
                print(f"    - {species['scientific_name']} (ID: {species['id']})")
            return True
        else:
            print("  ❌ Database connection failed - no data returned")
            return False
            
    except Exception as e:
        print(f"  ❌ Database connection test failed: {e}")
        return False

def validate_species_creation():
    """Validate that species creation is working properly"""
    print("🔧 Testing species creation functionality...")
    
    # Test creating a sample species
    test_species_name = "Testus specieus"
    
    try:
        # First check it doesn't exist
        response = supabase.table('species').select('id').eq('scientific_name', test_species_name).execute()
        
        if response.data:
            print(f"  🧹 Cleaning up existing test species...")
            # Clean up if it exists
            supabase.table('species').delete().eq('scientific_name', test_species_name).execute()
        
        # Now test creation
        species_id = create_species_from_csv_data(test_species_name, "test_file.csv")
        
        if species_id:
            print(f"  ✅ Species creation test successful (ID: {species_id})")
            
            # Clean up test species
            supabase.table('species').delete().eq('id', species_id).execute()
            print(f"  🧹 Cleaned up test species")
            return True
        else:
            print(f"  ❌ Species creation test failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Species creation test error: {e}")
        return False

def process_csv_file(csv_file):
    """Process a single CSV file"""
    print(f"\n📂 Processing: {csv_file.name}")
    
    try:
        # Read CSV with better error handling
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"  📊 Found {len(df)} records")
        print(f"  📋 Columns: {list(df.columns)}")
        
        if len(df) == 0:
            print(f"  ⚠️  Empty file, skipping")
            return 0
        
        # Show sample data for debugging
        print(f"  📄 Sample row:")
        if len(df) > 0:
            sample_row = df.iloc[0]
            for col in df.columns:
                print(f"    {col}: {sample_row[col]}")
        
        # Extract species name from CSV data
        species_column_variants = ['SPECIES (SCIENTIFIC NAME)', 'Scientific Name', 'Species', 'Taxon']
        species_name = None
        
        for col_variant in species_column_variants:
            if col_variant in df.columns:
                species_name = df[col_variant].iloc[0]
                print(f"  🔍 Found species column '{col_variant}': {species_name}")
                break
        
        if not species_name:
            print(f"  ❌ Could not find species column. Available columns: {list(df.columns)}")
            return 0
            
        print(f"  🎯 Target species: {species_name}")
        
        # Get or create species ID (now with auto-creation)
        species_id = get_or_create_species(species_name, csv_file.stem)
        if not species_id:
            print(f"  ❌ Cannot process without species ID, skipping file")
            return 0
            
        processed_count = 0
        error_count = 0
        
        # Process each row with better error handling
        for idx, row in df.iterrows():
            try:
                # Extract data from row using flexible column mapping
                country = get_column_value(row, ['COUNTRY', 'Country', 'Nation'])
                area = get_column_value(row, ['AREA OR STOCK', 'Area', 'Stock', 'Management Area'])
                year = get_column_value(row, ['YEAR OR SEASON', 'Year', 'Season'])
                catch_total = get_column_value(row, ['CATCH TOTAL', 'Catch', 'Total Catch', 'Harvest'])
                quota = get_column_value(row, ['QUOTA (IF APPLICABLE)', 'Quota', 'Limit'])
                
                # Validate required data
                if not year:
                    print(f"    ⚠️  Row {idx}: Missing year, skipping")
                    continue
                    
                if not catch_total and not quota:
                    print(f"    ⚠️  Row {idx}: No catch or quota data, skipping")
                    continue
                
                # Clean and validate year
                try:
                    year_clean = int(float(str(year).strip()))
                    if year_clean < 1900 or year_clean > 2030:
                        print(f"    ⚠️  Row {idx}: Invalid year {year_clean}, skipping")
                        continue
                except (ValueError, TypeError):
                    print(f"    ⚠️  Row {idx}: Cannot parse year '{year}', skipping")
                    continue
                
                # Get or create country ID (now with auto-creation)
                country_id = get_or_create_country(country) if country else None
                
                # Get or create area ID
                area_id = get_or_create_area(area, country_id) if area else None
                
                # Insert record
                if insert_catch_record(species_id, country_id, area_id, year_clean, catch_total, quota):
                    processed_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                print(f"  ⚠️  Error processing row {idx}: {e}")
                error_count += 1
                continue
        
        print(f"  ✅ Successfully processed {processed_count} records")
        if error_count > 0:
            print(f"  ⚠️  {error_count} records had errors")
        return processed_count
        
    except Exception as e:
        print(f"  ❌ Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return 0

def process_csv_file_old(csv_file):
    """Process a single CSV file - old incomplete version"""
    print(f"\n📂 Processing: {csv_file.name}")
    
    # This is the incomplete function that was at the end
    # It's been replaced with the complete version above
    
    try:
        # Read CSV with better error handling
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"  📊 Found {len(df)} records")
        print(f"  📋 Columns: {list(df.columns)}")
        
        if len(df) == 0:
            print(f"  ⚠️  Empty file, skipping")
            return 0
        
        # Show sample data for debugging
        print(f"  📄 Sample row:")
        if len(df) > 0:
            sample_row = df.iloc[0]
            for col in df.columns:
                print(f"    {col}: {sample_row[col]}")
        
        # Extract species name from CSV data
        species_column_variants = ['SPECIES (SCIENTIFIC NAME)', 'Scientific Name', 'Species', 'Taxon']
        species_name = None
        
        for col_variant in species_column_variants:
            if col_variant in df.columns:
                species_name = df[col_variant].iloc[0]
                print(f"  🔍 Found species column '{col_variant}': {species_name}")
                break
        
        if not species_name:
            print(f"  ❌ Could not find species column. Available columns: {list(df.columns)}")
            return 0
            
        print(f"  🎯 Target species: {species_name}")
        
        # Get or create species ID (now with auto-creation)
        species_id = get_or_create_species(species_name, csv_file.stem)
        if not species_id:
            print(f"  ❌ Cannot process without species ID, skipping file")
            return 0
            
        processed_count = 0
        error_count = 0
        
        # Process each row with better error handling
        for idx, row in df.iterrows():
            try:
                # Extract data from row using flexible column mapping
                country = get_column_value(row, ['COUNTRY', 'Country', 'Nation'])
                area = get_column_value(row, ['AREA OR STOCK', 'Area', 'Stock', 'Management Area'])
                year = get_column_value(row, ['YEAR OR SEASON', 'Year', 'Season'])
                catch_total = get_column_value(row, ['CATCH TOTAL', 'Catch', 'Total Catch', 'Harvest'])
                quota = get_column_value(row, ['QUOTA (IF APPLICABLE)', 'Quota', 'Limit'])
                
                # Validate required data
                if not year:
                    print(f"    ⚠️  Row {idx}: Missing year, skipping")
                    continue
                    
                if not catch_total and not quota:
                    print(f"    ⚠️  Row {idx}: No catch or quota data, skipping")
                    continue
                
                # Clean and validate year
                try:
                    year_clean = int(float(str(year).strip()))
                    if year_clean < 1900 or year_clean > 2030:
                        print(f"    ⚠️  Row {idx}: Invalid year {year_clean}, skipping")
                        continue
                except (ValueError, TypeError):
                    print(f"    ⚠️  Row {idx}: Cannot parse year '{year}', skipping")
                    continue
                
                # Get or create country ID (now with auto-creation)
                country_id = get_or_create_country(country) if country else None
                
                # Get or create area ID
                area_id = get_or_create_area(area, country_id) if area else None
                
                # Insert record
                if insert_catch_record(species_id, country_id, area_id, year_clean, catch_total, quota):
                    processed_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                print(f"  ⚠️  Error processing row {idx}: {e}")
                error_count += 1
                continue
        
        print(f"  ✅ Successfully processed {processed_count} records")
        if error_count > 0:
            print(f"  ⚠️  {error_count} records had errors")
        return processed_count
        
    except Exception as e:
        print(f"  ❌ Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return 0

def import_nammco_data():
    """Main import function"""
    print("🚀 Starting NAMMCO data import with auto-species creation...")
    
    # Test database connection first
    if not test_database_connection():
        print("❌ Database connection failed, aborting import")
        return
    
    # Test species creation functionality
    if not validate_species_creation():
        print("❌ Species creation validation failed, aborting import")
        return
    
    print(f"📁 CSV Directory: {CSV_DIR}")
    
    if not CSV_DIR.exists():
        print(f"❌ CSV directory not found: {CSV_DIR}")
        return
    
    total_processed = 0
    
    # Get list of CSV files
    csv_files = list(CSV_DIR.glob("*.csv"))
    print(f"📄 Found {len(csv_files)} CSV files")
    
    # Filter for single species if specified
    if SINGLE_SPECIES:
        csv_files = [f for f in csv_files if f.stem == SINGLE_SPECIES]
        print(f"🎯 Filtering for single species: {SINGLE_SPECIES}")
        print(f"📄 Processing {len(csv_files)} file(s)")
    
    if not csv_files:
        print("❌ No CSV files to process")
        return
    
    # Process each CSV file
    for csv_file in csv_files:
        count = process_csv_file(csv_file)
        total_processed += count
    
    print(f"\n🎉 Import complete! Total records processed: {total_processed}")
    
    # Show summary of created species
    print(f"\n📊 Import Summary:")
    print(f"  - Total catch records processed: {total_processed}")
    print(f"  - Auto-creation enabled for missing species and countries")
    print(f"  - All data should now be properly linked to species in the database")

if __name__ == "__main__":
    import_nammco_data()