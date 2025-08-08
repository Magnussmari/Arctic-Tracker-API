# Database Mapping and Species Enhancement Plan

**Date**: June 11, 2025  
**Purpose**: Map current database structure and create plan for adding detailed species information with references

---

## 📊 Current Database Structure

### Core Tables Overview

```
🗄️ SPECIES DATA ARCHITECTURE
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SPECIES ECOSYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────────┐    │
│  │   species   │    │    families      │    │   conservation_profiles │    │
│  │             │    │                  │    │                         │    │
│  │ • id (PK)   │◄──►│ • id (PK)        │    │ • id (PK)               │    │
│  │ • sci_name  │    │ • family_name    │    │ • species_id (FK)       │    │
│  │ • common    │    │ • order_name     │    │ • profile_data          │    │
│  │ • family_id │    │ • class          │    │ • created_at            │    │
│  │ • genus     │    │ • description    │    │                         │    │
│  │ • authority │    │                  │    │                         │    │
│  │ • sis_id    │    │                  │    │                         │    │
│  │ • description│   │                  │    │                         │    │
│  │ • habitat   │    │                  │    │                         │    │
│  │ • pop_trend │    │                  │    │                         │    │
│  │ • threats   │    │                  │    │                         │    │
│  │ • conserv.  │    │                  │    │                         │    │
│  └─────────────┘    └──────────────────┘    └─────────────────────────┘    │
│         │                                              │                    │
│         │                                              │                    │
│         ▼                                              ▼                    │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────────┐    │
│  │ references  │    │ profile_references│    │    catch_records        │    │
│  │             │    │                  │    │                         │    │
│  │ • id (PK)   │    │ • profile_id (FK)│    │ • id (PK)               │    │
│  │ • title     │◄──►│ • reference_id   │    │ • species_id (FK)       │    │
│  │ • authors   │    │   (FK)           │    │ • country_id (FK)       │    │
│  │ • journal   │    │ • page_numbers   │    │ • management_area_id    │    │
│  │ • year      │    │ • context        │    │ • year                  │    │
│  │ • doi       │    │                  │    │ • catch_total           │    │
│  │ • url       │    │                  │    │ • quota_amount          │    │
│  │ • type      │    │                  │    │ • data_source           │    │
│  └─────────────┘    └──────────────────┘    └─────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Supporting Tables

```
🌍 GEOGRAPHIC & ASSESSMENT DATA
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   countries     │  │ management_areas│  │ iucn_assessments│  │ cites_listings  │
│                 │  │                 │  │                 │  │                 │
│ • id (PK)       │  │ • id (PK)       │  │ • id (PK)       │  │ • id (PK)       │
│ • country_name  │  │ • area_name     │  │ • species_id    │  │ • species_id    │
│ • nammco_member │  │ • area_type     │  │ • year_published│  │ • appendix      │
│                 │  │ • country_id    │  │ • status        │  │ • listing_date  │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 🎯 Current Species Status

### NAMMCO Species in Database
Based on the query results, we have these key Arctic species:

1. **Balaenoptera physalus** (Fin Whale) - ID: e77df55d-294b-431f-9b0f-1d2da69518f6
2. **Odobenus rosmarus** (Walrus) - ID: 286e0896-1b69-4de9-a5b2-6561d82443e6
3. **Lagenorhynchus acutus** (Atlantic White-sided Dolphin) - ID: a844b4b6-16a9-45f1-b901-48e3703919d3
4. **Ziphius cavirostris** (Cuvier's beaked whale) - ID: f2eae94d-b2f3-4023-906c-c3d8c1103c8e

### Species with Detailed Profiles Available
- **Monodon monoceros** (Narwhal) - Comprehensive profile ready for import

## 📋 Species Enhancement Plan

### Phase 1: Database Schema Verification
✅ **Completed**: Database mapping shows proper structure exists
- `conservation_profiles` table exists but empty
- `references` table exists but empty  
- `profile_references` junction table exists
- Species table has fields for detailed information

### Phase 2: Reference System Setup

#### 2.1 References Table Structure
The `references` table should contain:
```sql
CREATE TABLE references (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  authors TEXT[] NOT NULL,
  journal TEXT,
  year INTEGER,
  volume TEXT,
  issue TEXT,
  pages TEXT,
  doi TEXT,
  url TEXT,
  reference_type TEXT, -- 'journal', 'book', 'report', 'website'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### 2.2 Conservation Profiles Table Structure
```sql
CREATE TABLE conservation_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  species_id UUID REFERENCES species(id) ON DELETE CASCADE,
  profile_type TEXT DEFAULT 'comprehensive', -- 'comprehensive', 'summary', 'assessment'
  content JSONB, -- Structured profile data
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Phase 3: Data Import Strategy

#### 3.1 Narwhal Profile Import (First Species)
**Source**: `species_data/scite/raw/narwhal.md`

**Data Mapping**:
```json
{
  "species_id": "find_monodon_monoceros_id",
  "profile_data": {
    "description": "Physical characteristics and basic biology",
    "habitat_description": "Arctic habitat preferences and distribution",
    "population_size": "~80,000 individuals (2019)",
    "population_trend": "Stable in some regions, declining in others",
    "generation_length": "27 years",
    "movement_patterns": "Seasonal migrations, site fidelity",
    "threats_overview": "Climate change, industrial activities, hunting",
    "use_and_trade": "Indigenous subsistence, CITES Appendix II",
    "conservation_overview": "International agreements, quotas, monitoring"
  }
}
```

**References to Extract**:
1. Ames, A., et al. (2021) - Evidence of stereotyped contact call use
2. Charry, B., et al. (2018) - Aerial photographic identification  
3. Higdon, J. (2009) - Greenland's winter whales
4. Shuert, C., et al. (2023) - Divergent migration routes

#### 3.2 Import Script Requirements
Create `migration/import_species_profiles.py` with:
- Parse markdown profiles
- Extract and normalize references
- Update species table with detailed information
- Create conservation profile records
- Link references to profiles

### Phase 4: Implementation Steps

#### Step 1: Create Import Script
```python
# migration/import_species_profiles.py
def parse_profile_markdown(file_path):
    """Parse markdown profile and extract structured data"""
    
def extract_references(content):
    """Extract and parse reference citations"""
    
def update_species_record(species_id, profile_data):
    """Update species table with detailed information"""
    
def create_conservation_profile(species_id, profile_data):
    """Create conservation profile record"""
    
def import_references(references):
    """Import references and return reference IDs"""
    
def link_profile_references(profile_id, reference_ids):
    """Create profile-reference associations"""
```

#### Step 2: Species-by-Species Import
1. **Start with Narwhal** (Monodon monoceros)
2. **Continue with other NAMMCO species** that have profiles
3. **Expand to all Arctic species** with available data

#### Step 3: Data Validation
- Verify species IDs match correctly
- Ensure reference formatting is consistent
- Check profile data completeness
- Validate foreign key relationships

### Phase 5: Frontend Integration

#### 5.1 New API Endpoints Needed
```javascript
// Get species with full profile
GET /api/species/{id}/profile

// Get species references
GET /api/species/{id}/references

// Get conservation profile
GET /api/species/{id}/conservation-profile
```

#### 5.2 Frontend Components
- Species detail page with tabbed sections
- Reference citation display
- Conservation status timeline
- Population trend visualizations

## 🚀 Immediate Next Steps

### 1. Verify Database Schema
Check if `conservation_profiles` and `references` tables have the correct structure:

```sql
-- Check table structures
\d conservation_profiles
\d references  
\d profile_references
```

### 2. Find Narwhal Species ID
```sql
SELECT id, scientific_name, common_name 
FROM species 
WHERE scientific_name = 'Monodon monoceros';
```

### 3. Create Import Script
Build the import script to process the narwhal profile as a proof of concept.

### 4. Test Import Process
Import narwhal data and verify all relationships work correctly.

### 5. Scale to Other Species
Once narwhal import is successful, expand to other species with available profiles.

## 📁 Available Species Data

### Current Profile Files
- `species_data/scite/raw/narwhal.md` - Comprehensive narwhal profile
- Additional profiles can be added to this directory

### NAMMCO Species Needing Profiles
Based on catch data, these species need detailed profiles:
- Balaenoptera acutorostrata (Minke whale)
- Balaenoptera physalus (Fin whale) 
- Delphinapterus leucas (Beluga)
- Globicephala melas (Pilot whale)
- Hyperoodon ampullatus (Northern bottlenose whale)
- Lagenorhynchus acutus (Atlantic white-sided dolphin)
- Megaptera novaeangliae (Humpback whale)
- Odobenus rosmarus (Walrus)
- Orcinus orca (Orca)
- Phocoena phocoena (Harbor porpoise)
- Phocoenoides dalli (Dall's porpoise)
- Physeter macrocephalus (Sperm whale)

---

**Next Action**: Create the import script and begin with narwhal profile import as proof of concept.
