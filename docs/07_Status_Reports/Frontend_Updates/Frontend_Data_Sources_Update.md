# Frontend Data Sources Update Required

**Date**: July 30, 2025  
**Issue**: Homepage shows "5+ Data Sources" but we actually have 8-9 sources

## Correct Data Sources Count: 8 Primary Sources

### Primary Data Sources (8):
1. **CITES Trade Database** - Legal wildlife trade records
2. **IUCN Red List** - Conservation status assessments  
3. **NAMMCO** - Marine mammal catch data
4. **Stringham et al. 2021** - Illegal wildlife trade dataset
5. **CMS** - Convention on Migratory Species listings
6. **Scite AI** - Scientific literature and citations
7. **Arctic Species List** - Core species tracking
8. **GBIF** - Taxonomic validation

### Additional Referenced Sources (1):
9. **iNaturalist** - Species IDs (stored but not actively used)

## Recommended Frontend Updates

### Option 1: Exact Count
```html
<div class="data-sources">
  <h3>8</h3>
  <p>Authoritative Data Sources</p>
</div>
```

### Option 2: Detailed Display
```html
<div class="data-sources">
  <h3>8 Data Sources</h3>
  <ul>
    <li>CITES Trade Database</li>
    <li>IUCN Red List</li>
    <li>NAMMCO Catch Data</li>
    <li>Illegal Trade Records</li>
    <li>Scientific Literature</li>
    <li>+ 3 more sources</li>
  </ul>
</div>
```

### Option 3: Interactive Tooltip
```javascript
const dataSources = [
  { name: "CITES", description: "International trade records" },
  { name: "IUCN Red List", description: "Conservation status" },
  { name: "NAMMCO", description: "Marine mammal management" },
  { name: "Illegal Trade Data", description: "Wildlife seizure records" },
  { name: "CMS", description: "Migratory species conventions" },
  { name: "Scite AI", description: "Scientific research" },
  { name: "Arctic Species List", description: "Core species tracking" },
  { name: "GBIF", description: "Taxonomic standards" }
];

// Display: "8 Data Sources" with hover tooltip showing all sources
```

## Data Source Breakdown by Type

- **Trade Data**: CITES (legal), Stringham et al. (illegal)
- **Conservation**: IUCN Red List, CMS
- **Management**: NAMMCO
- **Scientific**: Scite AI, GBIF
- **Core Data**: Arctic Species List

## Implementation Note
Update the frontend to show "8 Data Sources" instead of "5+" to accurately reflect the comprehensive data integration in Arctic Tracker.