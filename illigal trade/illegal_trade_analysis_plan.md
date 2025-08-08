# Arctic Species Illegal Trade Analysis Plan

## Overview

Analyze the illegal trade dataset to identify seizures and illegal activities involving our 43 Arctic species, cross-referencing with CITES trade data to identify potential illegal trade patterns.

## Dataset Information

**Source**: Dataset of seized wildlife and their intended uses
- **Authors**: Oliver C. Stringham et al., University of Adelaide
- **Date**: 2020-2021
- **Databases**: TRAFFIC, LEMIS (US Fish & Wildlife), CITES

## Initial Findings

Preliminary search found **135 records** involving Arctic species in illegal trade, including:
- **Walrus** (Odobenus rosmarus): Tusks and teeth seized
- **Polar Bear** (Ursus maritimus): Skins seized
- **Narwhal** (Monodon monoceros): Teeth (tusks) seized
- **Canada Lynx** (Lynx canadensis): Skins seized
- **Gyrfalcon** (Falco rusticolus): Live birds seized
- **Peregrine Falcon** (Falco peregrinus): Live birds and eggs seized

## Analysis Plan

### Phase 1: Data Extraction & Mapping (2-3 hours)

1. **Extract All Arctic Species Illegal Trade Records**
   - Search for all 43 Arctic species in seizure data
   - Map scientific names to our species list
   - Handle taxonomic variations (e.g., Lynx lynx canadensis)

2. **Categorize Illegal Trade Types**
   - Live animals
   - Dead/parts (skins, tusks, teeth, meat)
   - Products (ivory carvings, leather goods)
   - Traditional medicine
   - Eggs

3. **Extract Metadata**
   - Database source (TRAFFIC, LEMIS, CITES)
   - Use types and categories
   - Associated search terms

### Phase 2: Data Analysis (2-3 hours)

1. **Species Risk Assessment**
   - Count seizures by species
   - Identify most trafficked Arctic species
   - Map trade types by species

2. **Trade Pattern Analysis**
   - Compare illegal vs legal trade volumes
   - Identify species with high illegal:legal ratios
   - Timeline analysis (if dates available)

3. **Product Type Analysis**
   - Most common illegal products
   - High-value items (ivory, skins, live animals)
   - Traditional use vs commercial trade

### Phase 3: Cross-Reference with CITES Data (2 hours)

1. **Legal Trade Baseline**
   - Use our extracted CITES data (489,148 records)
   - Calculate legal trade volumes by species
   - Identify normal trade patterns

2. **Anomaly Detection**
   - Species with seizures but little legal trade
   - Unusual product types in illegal trade
   - Geographic patterns (if available)

3. **Conservation Risk Scoring**
   - High illegal trade + declining population = Critical
   - CITES Appendix I species in trade = High risk
   - Volume-based risk assessment

### Phase 4: Reporting & Visualization (2 hours)

1. **Create Illegal Trade Report**
   - Summary statistics
   - Species risk rankings
   - Key findings and patterns

2. **Data Visualizations**
   - Illegal trade by species (bar chart)
   - Product type distribution (pie chart)
   - Risk matrix (illegal trade vs conservation status)

3. **Integration Recommendations**
   - Add illegal trade flag to species profiles
   - Create alerts for high-risk species
   - Monitor trade anomalies

## Key Questions to Answer

1. **Which Arctic species are most affected by illegal trade?**
2. **What products drive illegal trade in Arctic species?**
3. **How does illegal trade volume compare to legal CITES trade?**
4. **Which species show concerning illegal:legal trade ratios?**
5. **Are CITES Appendix I species appearing in illegal trade?**

## Data Structure for Analysis

### Input Files
- `01_taxa_use_combos.csv` - Main seizure data
- `02_gbif_taxonomic_key.csv` - Taxonomic mapping
- `05_use_search_words.csv` - Product search terms
- Our Arctic species list with IDs

### Output Files
1. `arctic_illegal_trade_records.csv`
   - All illegal trade records for Arctic species
   - Mapped to our species IDs

2. `illegal_trade_summary_by_species.csv`
   - Seizure counts
   - Product types
   - Risk scores

3. `illegal_legal_trade_comparison.csv`
   - Legal CITES volume
   - Illegal seizure count
   - Ratio analysis

## Implementation Steps

### Step 1: Create Extraction Script
```python
# arctic_illegal_trade_extractor.py
- Load Arctic species list
- Search illegal trade data
- Handle name variations
- Extract and categorize
```

### Step 2: Analysis Script
```python
# analyze_illegal_trade_patterns.py
- Calculate statistics
- Compare with CITES data
- Generate risk scores
- Create visualizations
```

### Step 3: Report Generation
```python
# generate_illegal_trade_report.py
- Compile findings
- Create markdown report
- Generate charts
- Export data files
```

## Risk Categories

### Critical Risk Species
- High illegal trade volume
- CITES Appendix I
- Declining population

### High Risk Species
- Moderate illegal trade
- Valuable products (ivory, fur)
- Limited legal trade

### Monitor Species
- Low illegal trade
- Stable populations
- Regular legal trade

## Timeline

- **Day 1 (Today)**: Planning and setup
- **Day 2**: Data extraction and analysis
- **Day 3**: Report generation and integration

## Expected Outcomes

1. **Comprehensive illegal trade assessment** for all Arctic species
2. **Risk rankings** to prioritize conservation efforts
3. **Data files** for database integration
4. **Actionable insights** for monitoring and enforcement
5. **Baseline metrics** for tracking illegal trade trends

---

**Created**: July 28, 2025
**Purpose**: Arctic Species Illegal Trade Analysis
**Integration**: Arctic Tracker Database