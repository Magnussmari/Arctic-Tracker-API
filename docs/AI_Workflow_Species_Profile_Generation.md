# AI Workflow: Species Profile Generation System

## Overview
The Arctic Tracker uses a sophisticated multi-AI workflow to generate scientifically rigorous species conservation profiles with proper academic citations. This system combines multiple AI platforms to ensure accuracy, completeness, and academic credibility.

## Complete Workflow Pipeline

### 🔄 **Step 1: Species-Specific Prompt Generation**
**Location:** `/docs/Prompts/species/`
**Purpose:** Create tailored research prompts for each Arctic species

#### Process:
1. **Species Selection** from Arctic Tracker 42 species list
2. **Custom Prompt Creation** for each species using templates
3. **Conservation Focus** on Arctic-specific challenges

#### Example Files:
- `Monodon_monoceros_conservation_profile.md` (Narwhal)
- `Ursus_maritimus_conservation_profile.md` (Polar Bear)
- `Balaena_mysticetus_conservation_profile.md` (Bowhead Whale)

#### Prompt Structure:
```markdown
# [Species Scientific Name] Conservation Profile

## Research Focus Areas:
- Population status and trends
- Distribution and habitat requirements
- Conservation threats and challenges
- Management measures and effectiveness
- Climate change impacts
- Human interactions and conflicts

## Specific Questions:
1. What is the current conservation status?
2. What are the primary threats?
3. What conservation measures are in place?
4. How is climate change affecting this species?
5. What are the knowledge gaps?
```

---

### 🔬 **Step 2: Scientific Research via Scite AI**
**Platform:** [www.scite.ai](https://www.scite.ai)
**Purpose:** Generate evidence-based content with scientific citations

#### Process:
1. **Input:** Species-specific prompt from Step 1
2. **AI Analysis:** Scite AI searches scientific literature
3. **Output:** Comprehensive research report with:
   - Evidence-based content
   - Scientific citations
   - Supporting/contrasting evidence
   - Recent research findings

#### Scite AI Advantages:
- **Citation Context** - Shows how papers cite each other
- **Supporting Evidence** - Identifies supporting citations
- **Contrasting Evidence** - Highlights conflicting research
- **Recent Research** - Includes latest publications
- **Quality Control** - Peer-reviewed sources only

#### Example Output:
```
Narwhal (Monodon monoceros) Conservation Analysis

Population Status:
The narwhal population is estimated at 123,000 individuals (Heide-Jørgensen et al., 2021). 
Recent studies show declining trends in some subpopulations (Laidre et al., 2020).

[Supporting Citation: Heide-Jørgensen, M.P., et al. (2021). "Narwhal abundance estimates..." Marine Mammal Science, 37(2), 456-478.]

Climate Change Impacts:
Sea ice loss is reducing narwhal habitat (Stern & Laidre, 2016).
[Contrasting Evidence: Some studies suggest adaptation potential (Williams et al., 2019)]

References:
1. Heide-Jørgensen, M.P., et al. (2021). Narwhal abundance estimates...
2. Laidre, K.L., et al. (2020). Population trends in Arctic marine mammals...
3. Stern, H.L. & Laidre, K.L. (2016). Sea ice indicators of climate change...
```

---

### 🤖 **Step 3: JSON Structuring via Gemini 2.5 Pro**
**Platform:** Google Gemini 2.5 Pro
**Purpose:** Convert research into structured database format
**Prompt:** `/species_data/scite/prompts/system_prompt/Unified_Species_JSON_Prompt.md`

#### Process:
1. **Input:** Scite AI research output with citations
2. **Prompt Engineering:** Use unified JSON prompt template
3. **AI Processing:** Gemini 2.5 Pro structures the data
4. **Output:** Standardized JSON format for database import

#### Unified JSON Prompt Features:
- **Structured Schema** - Consistent data format
- **Reference Extraction** - Separate citations properly
- **Data Validation** - Ensure completeness
- **Arctic Focus** - Emphasize Arctic-specific content

#### JSON Output Structure:
```json
{
  "species_data": {
    "scientific_name": "Monodon monoceros",
    "common_name": "Narwhal",
    "family": "Monodontidae",
    "conservation_status": "Near Threatened",
    "population_estimate": "123,000",
    "population_trend": "Declining",
    "arctic_distribution": "Arctic Ocean, primarily Canadian Arctic"
  },
  "conservation_profile": {
    "species_scientific_name": "Monodon monoceros",
    "profile_type": "comprehensive",
    "content": {
      "subpopulations": "Multiple subpopulations across Canadian Arctic waters...",
      "distribution_range": "Circumpolar Arctic distribution, concentrated in Canadian waters...",
      "primary_threats": [
        "Climate change and sea ice loss",
        "Shipping traffic increase",
        "Noise pollution",
        "Hunting pressure"
      ],
      "conservation_measures": [
        "CITES Appendix II listing",
        "Canadian Species at Risk Act protection",
        "Indigenous co-management agreements"
      ]
    }
  },
  "references": [
    {
      "title": "Narwhal abundance estimates in the Canadian Arctic",
      "authors": ["Heide-Jørgensen, M.P.", "Laidre, K.L.", "Wiig, Ø."],
      "year": 2021,
      "journal": "Marine Mammal Science",
      "doi": "10.1111/mms.12345",
      "full_citation": "Heide-Jørgensen, M.P., Laidre, K.L., & Wiig, Ø. (2021). Narwhal abundance estimates in the Canadian Arctic. Marine Mammal Science, 37(2), 456-478."
    }
  ]
}
```

---

### 💾 **Step 4: Database Import & Population**
**Script:** `core/upload_species_profiles.py`
**Purpose:** Import structured JSON data into existing Supabase species table

#### Process:
1. **File Detection** - Distinguish research data from empty templates
2. **Duplication Check** - Avoid uploading already processed species
3. **Data Validation** - Verify JSON structure and completeness
4. **Species Enhancement** - Update species table with research data
5. **Progress Tracking** - Detailed logging and error reporting

#### Database Table Updated:
- **`species`** - Enhanced with comprehensive conservation data
  - `description` - Detailed species information
  - `habitat_description` - Habitat and distribution data
  - `population_size` - Current population estimates
  - `population_trend` - Population trajectory
  - `generation_length` - Reproductive cycles
  - `movement_patterns` - Migration and seasonal patterns
  - `use_and_trade` - Commercial and subsistence use
  - `threats_overview` - Primary conservation threats
  - `conservation_overview` - Conservation measures and status

#### Import Commands:
```bash
# Create logs directory (required before first run)
cd /Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/core
mkdir -p logs

# Dry run (validation only)
python upload_species_profiles.py --dry-run

# Live upload of all species with research data
python upload_species_profiles.py

# Check logs for detailed results
tail -f logs/species_upload_*.log
```

#### Upload Results (July 10, 2025):
- **43 JSON files processed**
- **24 empty templates skipped**
- **19 files with research data identified**
- **14 species successfully uploaded**
- **4 duplicates avoided**
- **1 failed upload (fixed and re-uploaded)**

#### Successfully Enhanced Species:
1. **Acipenser baerii** - Siberian Sturgeon
2. **Alopias vulpinus** - Common Thresher Shark
3. **Antigone canadensis** - Sandhill Crane
4. **Asio flammeus** - Short-eared Owl
5. **Balaena mysticetus** - Bowhead Whale
6. **Balaenoptera acutorostrata** - Minke Whale
7. **Balaenoptera borealis** - Sei Whale
8. **Balaenoptera musculus** - Blue Whale
9. **Balaenoptera physalus** - Fin Whale
10. **Berardius bairdii** - Baird's Beaked Whale
11. **Branta canadensis leucopareia** - Aleutian Canada Goose
12. **Branta ruficollis** - Red-breasted Goose
13. **Hyperoodon ampullatus** - Northern Bottlenose Whale
14. **Rhodiola rosea** - Roseroot
15. **Ursus maritimus** - Polar Bear
16. **Ziphius cavirostris** - Cuvier's Beaked Whale

#### Already Uploaded (Skipped):
- **Falco rusticolus** - Gyrfalcon
- **Monodon monoceros** - Narwhal

---

### 📊 **Step 5: Frontend Display & Review**
**Purpose:** Present data for scientific review and validation

#### Features:
- **Species Overview** - Basic information display
- **Conservation Profile** - Detailed conservation data
- **References Tab** - Academic citations with DOI links
- **Data Validation** - Review and correction interface

---

## Workflow Benefits

### 🎯 **Scientific Rigor**
- **Peer-Reviewed Sources** - Only academic publications
- **Citation Tracking** - Full reference management
- **Evidence-Based** - Supporting and contrasting evidence
- **Quality Control** - Multi-AI validation

### 🔄 **Efficiency**
- **Automated Research** - AI-driven literature review
- **Standardized Format** - Consistent data structure
- **Batch Processing** - Multiple species simultaneously
- **Database Integration** - Direct import capability

### 📈 **Scalability**
- **Template-Based** - Easy to add new species
- **Modular Design** - Each step independent
- **Version Control** - Track changes and updates
- **Collaborative** - Multiple researchers can contribute

## File Locations

### Input Files:
- **Species Prompts:** `/docs/Prompts/species/[species_name]_conservation_profile.md`
- **JSON Template:** `/species_data/scite/prompts/system_prompt/Unified_Species_JSON_Prompt.md`

### Output Files:
- **Processed JSON:** `/species_data/scite/processed/[species_name].json`
- **Raw Scite Output:** `/species_data/scite/raw/scite_[species_name].md`

### Scripts:
- **Upload Script:** `/core/upload_species_profiles.py`
- **File Standardization:** `/core/standardize_species_json_files.py`

## Quality Assurance

### Data Validation:
1. **Citation Verification** - DOI links checked
2. **Scientific Accuracy** - Expert review process
3. **Completeness Check** - All required fields populated
4. **Arctic Relevance** - Focus on Arctic-specific content

### Review Process:
1. **AI-Generated Content** - Initial research and structuring
2. **Scientific Review** - Expert validation
3. **Database Import** - Automated data population
4. **Frontend Display** - User interface for review
5. **Iterative Improvement** - Continuous refinement

This multi-AI workflow ensures that Arctic Tracker maintains the highest standards of scientific accuracy while efficiently processing large amounts of conservation data for Arctic species.
