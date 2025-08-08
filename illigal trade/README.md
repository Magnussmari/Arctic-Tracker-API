# Arctic Species Illegal Trade Analysis

## Overview

This folder contains the analysis of illegal wildlife trade data for Arctic species, based on seizure records from TRAFFIC, US LEMIS, and CITES enforcement databases.

## Key Findings

- **919 seizure records** involving Arctic species
- **36 of 43 Arctic species** found in illegal trade (84%)
- **Top trafficked species**: Polar Bear (195), Siberian Sturgeon (144), Gyrfalcon (114)

## Files

### Analysis Results
- `arctic_illegal_trade_records.csv` - Detailed seizure records for all Arctic species
- `arctic_illegal_trade_summary.csv` - Summary by species with seizure counts and product types
- `illegal_trade_by_use_type.csv` - Analysis of product categories

### Documentation
- `illegal_trade_analysis_plan.md` - Comprehensive analysis plan
- `illegal_trade_findings.md` - Key findings and conservation concerns

### Scripts
- `extract_arctic_illegal_trade.py` - Python script to extract Arctic species from seizure data

### Source Data
- `dataset/` - Original seizure dataset from Stringham et al. (2021)
  - 15,491 wildlife seizure records
  - Taxonomic mapping via GBIF
  - Product categorization

## Top Conservation Concerns

### Critical Risk Species:
1. **Polar Bear** - 195 seizures (skins, gall bladders, claws)
2. **Siberian Sturgeon** - 144 seizures (ENDANGERED, caviar trade)
3. **Gyrfalcon** - 114 seizures (CITES Appendix I, live bird trade)

### CITES Appendix I Species Still Being Trafficked:
- Gyrfalcon (114 seizures)
- Sperm Whale (32 seizures)
- Blue Whale (25 seizures)
- Bowhead Whale (18 seizures)

### High-Value Products:
- **Ivory/Tusks**: Walrus, narwhal, sperm whale
- **Caviar**: Siberian sturgeon
- **Luxury Fur**: Polar bear, lynx
- **Live Birds**: Gyrfalcons, peregrine falcons

## Usage

To run the analysis:
```bash
python extract_arctic_illegal_trade.py
```

This will:
1. Load Arctic species list
2. Search seizure data for matches
3. Generate summary statistics
4. Create output CSV files

## Integration with CITES Migration

These findings should be integrated with the CITES legal trade data to:
- Calculate illegal:legal trade ratios
- Identify species at highest risk
- Add illegal trade flags to species profiles
- Monitor enforcement effectiveness

---

**Created**: July 28, 2025  
**Data Source**: Stringham et al. (2021) - Dataset of seized wildlife and their intended uses  
**Arctic Tracker Integration**: Ready for database integration