# Arctic Tracker Glossary - Terms & Placement Strategy

## Glossary Terms by Category

### Conservation Organizations & Frameworks

1. **CITES** - Convention on International Trade in Endangered Species of Wild Fauna and Flora
2. **IUCN** - International Union for Conservation of Nature
3. **NAMMCO** - North Atlantic Marine Mammal Commission
4. **iNaturalist** - Global biodiversity observation network
5. **CoP** - Conference of the Parties (CITES decision-making body)

### Conservation Status Terms

#### IUCN Red List Categories
1. **LC (Least Concern)** - Species evaluated with low risk of extinction
2. **NT (Near Threatened)** - Close to qualifying for a threatened category
3. **VU (Vulnerable)** - High risk of extinction in the wild
4. **EN (Endangered)** - Very high risk of extinction in the wild
5. **CR (Critically Endangered)** - Extremely high risk of extinction
6. **EW (Extinct in the Wild)** - Known only to survive in cultivation/captivity
7. **EX (Extinct)** - No known individuals remaining

#### CITES Appendices
1. **Appendix I** - Species threatened with extinction; trade permitted only in exceptional circumstances
2. **Appendix II** - Species not necessarily threatened but trade must be controlled
3. **Appendix III** - Species protected in at least one country requesting assistance

### Trade Terms

#### Specimen Types (Terms)
1. **Specimens** - Whole animals, dead or alive
2. **Skins** - Whole, raw or tanned animal skins
3. **Skin pieces** - Parts of skins including scraps
4. **Teeth** - Including tusks and ivory
5. **Hair** - Including wool and fur
6. **Bones** - Including skulls
7. **Meat** - All meat parts and products
8. **Live** - Living specimens
9. **Trophies** - Hunting trophies
10. **Scientific specimens** - Preserved for research

#### Trade Purposes
1. **B - Breeding in captivity or artificial propagation**
2. **E - Educational**
3. **G - Botanical garden**
4. **H - Hunting trophy**
5. **L - Law enforcement/judicial/forensic**
6. **M - Medical (including biomedical research)**
7. **N - Reintroduction or introduction into the wild**
8. **P - Personal**
9. **Q - Circus or traveling exhibition**
10. **S - Scientific**
11. **T - Commercial**
12. **Z - Zoo**

#### Source Codes
1. **W - Wild** - Specimens taken from the wild
2. **R - Ranched** - Specimens from ranching operations
3. **D - Appendix-I animals bred in captivity for commercial purposes**
4. **A - Plants artificially propagated for commercial purposes**
5. **C - Animals bred in captivity** (Appendix II/III)
6. **F - Animals born in captivity (F1 or subsequent generations)**
7. **I - Confiscated or seized specimens**
8. **O - Pre-Convention specimens**
9. **U - Source unknown**
10. **X - Specimens taken in "the marine environment not under jurisdiction"**

### Taxonomic Terms
1. **Kingdom** - Highest taxonomic rank (e.g., Animalia, Plantae)
2. **Phylum** - Major lineage within kingdom (e.g., Chordata)
3. **Class** - Group within phylum (e.g., Mammalia, Aves)
4. **Order** - Group within class (e.g., Carnivora, Cetacea)
5. **Family** - Group within order (e.g., Ursidae, Delphinidae)
6. **Genus** - Group within family (first part of scientific name)
7. **Species** - Basic unit of classification (full scientific name)
8. **Scientific name** - Binomial nomenclature (Genus species)
9. **Common name** - Vernacular name in local language

### Data & Analysis Terms
1. **Trade volume** - Quantity of specimens in trade
2. **Trade records** - Individual documented trade transactions
3. **Reported quantity** - Amount declared in trade documentation
4. **Importer/Exporter** - Countries involved in trade
5. **Timeline events** - Significant conservation milestones
6. **Population trend** - Direction of population change over time
7. **Conservation assessment** - Evaluation of species' conservation status
8. **Catch data** - Harvest/hunting records (especially NAMMCO)

### Geographic & Administrative
1. **Range states** - Countries where species naturally occurs
2. **Party/Parties** - Countries that have joined CITES
3. **Non-Party** - Country not member of CITES
4. **Split-listing** - Different populations with different CITES status
5. **Arctic region** - Circumpolar north (definition varies)

## Placement Strategy

### 1. **Global Glossary Access**
- **Location**: Add "Glossary" to main navigation bar (between "Community" and "About")
- **Icon**: Book or info icon
- **Behavior**: Opens full glossary page with search and categories

### 2. **Contextual Help Icons**
- **Implementation**: Small (i) icons next to technical terms
- **Interaction**: Hover for tooltip, click for full definition
- **Priority locations**:
  - Species cards (next to LC, CITES status)
  - Filter dropdowns
  - Chart legends
  - Table headers

### 3. **First-Time User Onboarding**
- **Trigger**: First visit or "Help" button
- **Content**: Key terms tour with highlights
- **Storage**: Local storage to remember completion

### 4. **Page-Specific Mini-Glossaries**

#### Species Gallery Page
- Terms: Conservation Status, CITES Appendix, Family
- Location: Collapsible panel under filters

#### Species Detail - Trade Tab
- Terms: All trade-related terms
- Location: "Understanding Trade Data" expandable section

#### Research Tools
- Terms: Analysis and methodology terms
- Location: Help section within each tool

### 5. **Smart Term Detection**
- **Feature**: Automatically underline glossary terms
- **Toggle**: User preference to enable/disable
- **Scope**: Limited to first occurrence per page

### 6. **Mobile Considerations**
- **Glossary**: Full-screen modal with categories
- **Terms**: Tap to reveal definition card
- **Navigation**: Sticky alphabet navigation

### 7. **Search Integration**
- **Global search**: Include glossary terms
- **Results**: Show term definitions above species results
- **Autocomplete**: Suggest related terms

## Implementation Recommendations

### Phase 1 (Essential)
1. Create glossary page with all terms
2. Add contextual help for conservation statuses
3. Include mini-glossary on trade data page

### Phase 2 (Enhanced)
1. Implement hover tooltips site-wide
2. Add first-time user tour
3. Create page-specific help sections

### Phase 3 (Advanced)
1. Smart term detection
2. Search integration
3. Multi-language support

## Design Guidelines

### Tooltip Design
```
┌─────────────────────────┐
│ CITES Appendix II    ⓧ │
├─────────────────────────┤
│ Species not necessarily │
│ threatened but trade    │
│ must be controlled to   │
│ avoid utilization       │
│ incompatible with       │
│ survival.              │
│                        │
│ [Learn more →]         │
└─────────────────────────┘
```

### Glossary Page Layout
```
Glossary
━━━━━━━━

Search: [_____________] 🔍

Categories:
[All] [Conservation] [Trade] [Taxonomy] [Geography]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A B C D E F G H I J K L M N O P Q R S T U V W X Y Z

### C

**CITES** - Convention on International Trade in Endangered Species
The primary international agreement ensuring that trade in wild animals 
and plants does not threaten their survival...

**Class** - Taxonomic rank
A major taxonomic rank below phylum and above order...
```

## Accessibility Features
- Screen reader friendly definitions
- Keyboard navigation for tooltips
- High contrast mode support
- Print-friendly glossary version
- Download as PDF option