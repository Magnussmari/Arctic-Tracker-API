# Species Profile Enhancement Workflow Guide

**Date**: June 11, 2025  
**Purpose**: Complete workflow for adding detailed species profiles with references to Arctic Tracker

---

## 🎯 Overview

This guide provides a complete workflow for enhancing Arctic Tracker with detailed species profiles, from raw scientific literature to database integration.

## 🔄 Complete Workflow

### Phase 1: Data Preparation
```
Raw Literature → LLM Processing → Structured JSON → Database Import
```

### Phase 2: Processing Pipeline
```
1. Scite Raw Data → 2. LLM + Optimized Prompt → 3. JSON Output → 4. Database Import
```

## 📁 File Structure

```
species_data/
├── scite/
│   ├── raw/                          # Raw scite output files
│   │   ├── scite_narwhal.md          # ✅ Available
│   │   └── scite_[species].md        # Future species
│   ├── processed/                    # LLM-processed JSON files
│   │   ├── narwhal_profile.json      # Target output
│   │   └── [species]_profile.json   # Future species
│   └── prompts/
│       └── system_prompt/
│           ├── Species_system_prompt.md           # Original prompt
│           └── Optimized_Species_JSON_Prompt.md   # ✅ Optimized version
└── nammco/                           # NAMMCO catch data (✅ imported)
```

## 🛠️ Tools Created

### 1. Optimized LLM Prompt
**File**: `species_data/scite/prompts/system_prompt/Optimized_Species_JSON_Prompt.md`

**Purpose**: Converts raw scite output to structured JSON
**Input**: Raw markdown profiles (like `scite_narwhal.md`)
**Output**: Three JSON objects:
- `SPECIES_DATA` - Core species information
- `CONSERVATION_PROFILE` - Extended profile data
- `REFERENCES` - Scientific citations array

### 2. JSON Import Script
**File**: `migration/import_species_json.py`

**Purpose**: Imports LLM-generated JSON into database
**Features**:
- ✅ Updates existing species records
- ✅ Creates new species if needed
- ✅ Imports scientific references
- ✅ Creates conservation profiles
- ✅ Links references to profiles
- ✅ Handles duplicates gracefully

## 📋 Step-by-Step Workflow

### Step 1: Prepare Raw Data
```bash
# Ensure raw scite data is available
ls species_data/scite/raw/scite_narwhal.md
```

### Step 2: Process with LLM
Use your LLM system with the optimized prompt:

**Input**: `species_data/scite/raw/scite_narwhal.md`
**Prompt**: `species_data/scite/prompts/system_prompt/Optimized_Species_JSON_Prompt.md`
**Output**: Save as `species_data/scite/processed/narwhal_profile.json`

**Expected JSON Structure**:
```json
{
  "species_data": {
    "scientific_name": "Monodon monoceros",
    "common_name": "Narwhal",
    "kingdom": "Animalia",
    "phylum": "Chordata",
    "class": "Mammalia",
    "order_name": "Artiodactyla",
    "family": "Monodontidae",
    "genus": "Monodon",
    "species_name": "monoceros",
    "authority": "Linnaeus, 1758",
    "description": "Complete description text...",
    "habitat_description": "Complete habitat text...",
    "population_size": "Complete population size text...",
    "population_trend": "Complete population trend text...",
    "generation_length": 27,
    "movement_patterns": "Complete movement patterns text...",
    "use_and_trade": "Complete use and trade text...",
    "threats_overview": "Complete threats text...",
    "conservation_overview": "Complete conservation text..."
  },
  "conservation_profile": {
    "species_scientific_name": "Monodon monoceros",
    "profile_type": "comprehensive",
    "content": {
      "subpopulations": "Complete subpopulations text...",
      "distribution_range": "Complete distribution text...",
      "source_file": "scite_narwhal.md",
      "parsed_date": "2025-06-11T21:30:00Z",
      "sections_parsed": 11,
      "references_count": 4
    }
  },
  "references": [
    {
      "title": "Evidence of stereotyped contact call use in narwhal...",
      "authors": ["Ames, A.", "Blackwell, S.", "Tervo, O.", "Heide‐Jørgensen, M."],
      "journal": "Plos One",
      "year": 2021,
      "volume": "16",
      "issue": "8",
      "pages": "e0254393",
      "doi": "10.1371/journal.pone.0254393",
      "url": "https://doi.org/10.1371/journal.pone.0254393",
      "reference_type": "journal",
      "full_citation": "Complete citation..."
    }
  ]
}
```

### Step 3: Import to Database
```bash
# Navigate to project directory
cd /Users/magnussmari/Arctic-Tracker-API

# Run import script
python migration/import_species_json.py species_data/scite/processed/narwhal_profile.json
```

**Expected Output**:
```
✅ Supabase client created successfully
🔧 Loading JSON data from: species_data/scite/processed/narwhal_profile.json

🚀 Processing complete profile for: Monodon monoceros

📚 Importing 4 references...
  ✅ Created new reference: Evidence of stereotyped contact call use in narwhal...
  ✅ Created new reference: Aerial photographic identification of narwhal...
  ✅ Created new reference: Greenland's winter whales: the beluga, the narwhal...
  ✅ Created new reference: Divergent migration routes reveal contrasting...

🐋 Updating species record...
🔄 Processing species: Monodon monoceros
  ✅ Found existing species (ID: 5f289c1e-5101-458f-a5ea-a65e5c734569), updating...
  ✅ Species record processed successfully (ID: 5f289c1e-5101-458f-a5ea-a65e5c734569)

📋 Creating conservation profile...
🔄 Creating conservation profile for: Monodon monoceros
  🔧 Creating new conservation profile...
  ✅ Conservation profile processed successfully
  🔗 Linking 4 references to profile...
  ✅ Reference linking completed

🎉 Successfully processed complete profile for Monodon monoceros

✅ Import completed successfully!
```

### Step 4: Verify Import
Check the database to ensure data was imported correctly:

```bash
# Check species record
python -c "
from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv('config/.env')
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))
result = supabase.table('species').select('scientific_name, description, threats_overview').eq('scientific_name', 'Monodon monoceros').execute()
print('Species data updated:', bool(result.data[0]['description'] and result.data[0]['threats_overview']))
"
```

## 🔄 Scaling to Multiple Species

### Priority Species List (NAMMCO)
1. **Monodon monoceros** (Narwhal) - ✅ Ready for processing
2. **Balaenoptera acutorostrata** (Minke whale)
3. **Odobenus rosmarus** (Walrus)
4. **Orcinus orca** (Orca)
5. **Delphinapterus leucas** (Beluga)
6. **Globicephala melas** (Pilot whale)
7. **Phocoena phocoena** (Harbor porpoise)
8. **Balaenoptera physalus** (Fin whale)
9. **Hyperoodon ampullatus** (Northern bottlenose whale)
10. **Lagenorhynchus acutus** (Atlantic white-sided dolphin)
11. **Megaptera novaeangliae** (Humpback whale)

### Batch Processing Workflow
```bash
# For each species:
# 1. Generate scite profile → species_data/scite/raw/scite_[species].md
# 2. Process with LLM → species_data/scite/processed/[species]_profile.json  
# 3. Import to database → python migration/import_species_json.py [file]
```

## 📊 Database Impact

### Tables Updated
- **species**: Enhanced with detailed descriptions, threats, conservation info
- **references**: New scientific citations added
- **conservation_profiles**: New comprehensive profiles created
- **profile_references**: Links between profiles and citations

### New Data Structure
```
species (enhanced)
├── description (detailed physical characteristics)
├── habitat_description (Arctic habitat preferences)
├── population_size (current estimates)
├── population_trend (trend analysis)
├── generation_length (numeric years)
├── movement_patterns (migration details)
├── use_and_trade (human uses, CITES status)
├── threats_overview (climate change, industrial impacts)
└── conservation_overview (policies, quotas, agreements)

conservation_profiles (new)
├── species_id → species.id
├── profile_type (comprehensive)
└── content (JSON with subpopulations, distribution, metadata)

references (new)
├── title, authors, journal, year
├── doi, url, reference_type
└── full_citation

profile_references (new)
├── profile_id → conservation_profiles.id
└── reference_id → references.id
```

## 🎯 Quality Assurance

### Validation Checklist
- [ ] Scientific name matches existing species record
- [ ] All 11 profile sections extracted
- [ ] Generation length is numeric
- [ ] References properly parsed with DOI links
- [ ] Conservation profile created and linked
- [ ] No duplicate references created

### Error Handling
- **Missing species**: Script creates new species record
- **Duplicate references**: Detected by DOI/title, existing record used
- **Malformed JSON**: Script reports specific errors
- **Database errors**: Detailed error messages with context

## 🚀 Next Steps

### Immediate Actions
1. **Test with Narwhal**: Process `scite_narwhal.md` through complete workflow
2. **Verify Database**: Confirm all data imported correctly
3. **Scale to Priority Species**: Process remaining NAMMCO species
4. **Frontend Integration**: Update UI to display enhanced profiles

### Future Enhancements
- **Automated Processing**: Batch processing scripts
- **Quality Metrics**: Validation and completeness scoring
- **Reference Management**: Citation formatting and linking
- **Profile Versioning**: Track updates and changes over time

---

**Ready to Process**: The complete workflow is now ready for implementation, starting with the Narwhal profile as proof of concept.
