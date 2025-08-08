# Arctic Tracker - Complete Species List

**Date**: June 11, 2025  
**Total Species**: 42  
**Database Status**: All species present in database  
**Profile Enhancement**: Ready for batch processing

---

## 🌊 Marine Mammals (22 species)

### Whales - Baleen (6 species)
1. **Balaena mysticetus** - Bowhead Whale
2. **Balaenoptera acutorostrata** - Minke Whale
3. **Balaenoptera borealis** - Sei Whale  
4. **Balaenoptera musculus** - Blue Whale
5. **Balaenoptera physalus** - Fin Whale
6. **Megaptera novaeangliae** - Humpback Whale

### Whales - Toothed (8 species)
7. **Delphinapterus leucas** - Beluga
8. **Monodon monoceros** - Narwhal ✅ *Profile ready*
9. **Physeter macrocephalus** - Sperm Whale
10. **Berardius bairdii** - Baird's Beaked Whale
11. **Hyperoodon ampullatus** - Northern Bottlenose Whale
12. **Mesoplodon stejnegeri** - Stejneger's Beaked Whale
13. **Ziphius cavirostris** - Cuvier's Beaked Whale
14. **Eschrichtius robustus** - Gray Whale

### Right Whales (2 species)
15. **Eubalaena glacialis** - North Atlantic Right Whale
16. **Eubalaena japonica** - North Pacific Right Whale

### Dolphins & Porpoises (4 species)
17. **Globicephala melas** - Long-finned Pilot Whale
18. **Lagenorhynchus acutus** - Atlantic White-sided Dolphin
19. **Lagenorhynchus albirostris** - White-beaked Dolphin
20. **Orcinus orca** - Killer Whale (Orca)

### Porpoises (2 species)
21. **Phocoena phocoena** - Harbour Porpoise
22. **Phocoenoides dalli** - Dall's Porpoise

## 🐾 Terrestrial Mammals (4 species)

### Carnivores (4 species)
23. **Ursus maritimus** - Polar Bear
24. **Lynx canadensis** - Canada Lynx
25. **Lontra canadensis** - North American River Otter
26. **Enhydra lutris** - Sea Otter

### Pinnipeds (1 species)
27. **Odobenus rosmarus** - Walrus

## 🐦 Birds (13 species)

### Raptors (4 species)
28. **Buteo lagopus** - Rough-legged Buzzard
29. **Falco peregrinus** - Peregrine Falcon
30. **Falco rusticolus** - Gyrfalcon
31. **Nyctea scandiaca** - Snowy Owl

### Owls (1 species)
32. **Asio flammeus** - Short-Eared Owl

### Waterfowl (3 species)
33. **Antigone canadensis** - Sandhill Crane
34. **Branta canadensis leucopareia** - Aleutian Canada Goose
35. **Branta ruficollis** - Red-breasted Goose

### Cranes (2 species)
36. **Leucogeranus leucogeranus** - Siberian Crane
37. **Numenius borealis** - Eskimo Curlew

### Seabirds (1 species)
38. **Phoebastria albatrus** - Short-tailed Albatross

## 🐟 Fish & Sharks (2 species)

### Sharks (3 species)
39. **Alopias vulpinus** - Common Thresher Shark
40. **Cetorhinus maximus** - Basking Shark
41. **Lamna nasus** - Porbeagle Shark

### Fish (1 species)
42. **Acipenser baerii** - Siberian Sturgeon

## 🌿 Plants (1 species)

### Arctic Flora (1 species)
43. **Rhodiola rosea** - Roseroot

---

## 📊 Species Categories by Conservation Priority

### NAMMCO Species (High Priority - 18 species)
*Species with active catch monitoring and quotas*

**Marine Mammals:**
- Balaena mysticetus (Bowhead Whale)
- Balaenoptera acutorostrata (Minke Whale)
- Balaenoptera physalus (Fin Whale)
- Delphinapterus leucas (Beluga)
- Monodon monoceros (Narwhal) ✅
- Odobenus rosmarus (Walrus)
- Orcinus orca (Orca)
- Globicephala melas (Pilot Whale)
- Hyperoodon ampullatus (Northern Bottlenose Whale)
- Lagenorhynchus acutus (Atlantic White-sided Dolphin)
- Megaptera novaeangliae (Humpback Whale)
- Phocoena phocoena (Harbour Porpoise)
- Phocoenoides dalli (Dall's Porpoise)
- Physeter macrocephalus (Sperm Whale)
- Berardius bairdii (Baird's Beaked Whale)
- Mesoplodon stejnegeri (Stejneger's Beaked Whale)
- Ziphius cavirostris (Cuvier's Beaked Whale)
- Balaenoptera borealis (Sei Whale)

### IUCN Red List Species (Medium Priority - 15 species)
*Species with formal conservation assessments*

**Critically Endangered:**
- Eubalaena glacialis (North Atlantic Right Whale)
- Numenius borealis (Eskimo Curlew)

**Endangered:**
- Eubalaena japonica (North Pacific Right Whale)
- Phoebastria albatrus (Short-tailed Albatross)

**Vulnerable:**
- Ursus maritimus (Polar Bear)
- Balaenoptera musculus (Blue Whale)
- Physeter macrocephalus (Sperm Whale)

**Near Threatened:**
- Cetorhinus maximus (Basking Shark)
- Lamna nasus (Porbeagle Shark)

### Arctic Endemic Species (High Priority - 8 species)
*Species primarily found in Arctic regions*

- Ursus maritimus (Polar Bear)
- Monodon monoceros (Narwhal)
- Delphinapterus leucas (Beluga)
- Balaena mysticetus (Bowhead Whale)
- Odobenus rosmarus (Walrus)
- Nyctea scandiaca (Snowy Owl)
- Falco rusticolus (Gyrfalcon)
- Rhodiola rosea (Roseroot)

---

## 🔄 Processing Status

### ✅ Completed Profiles (1 species)
- **Monodon monoceros** (Narwhal) - Full profile with 4 references

### 📋 Ready for Processing (41 species)
All remaining species are in the database and ready for profile enhancement.

### 📁 File Structure for Processing

```
species_data/scite/
├── raw/                          # Raw scite output
│   ├── scite_narwhal.md         # ✅ Available
│   ├── scite_polar_bear.md      # Future
│   ├── scite_beluga.md          # Future
│   └── ...                      # 39 more species
├── processed/                   # LLM-processed JSON
│   ├── narwhal_profile.json     # Target
│   ├── polar_bear_profile.json  # Future
│   └── ...                      # 41 more species
└── prompts/
    └── system_prompt/
        └── Optimized_Species_JSON_Prompt.md  # ✅ Ready
```

---

## 🚀 Batch Processing Commands

### List All Species
```bash
python migration/batch_import_species.py --list-species
```

### Dry Run (Validate JSON files)
```bash
python migration/batch_import_species.py --dry-run
```

### Import All Profiles
```bash
python migration/batch_import_species.py
```

### Single Species Import
```bash
python migration/import_species_json.py species_data/scite/processed/[species]_profile.json
```

---

## 📈 Expected Enhancement Impact

### Database Enhancement
- **42 species** with detailed conservation profiles
- **~168 scientific references** (avg 4 per species)
- **11 profile sections** per species
- **Complete taxonomic information**
- **NAMMCO catch data integration**

### Frontend Enhancement
- **Species detail pages** with tabbed interface
- **Conservation status displays** with IUCN/CITES badges
- **Interactive catch data visualizations**
- **Scientific reference management**
- **Cross-species comparisons**

### Research Value
- **Comprehensive Arctic biodiversity database**
- **Citation-backed conservation information**
- **Trend analysis capabilities**
- **Management decision support**
- **Educational resource platform**

---

**Ready for Implementation**: All 42 species are catalogued and ready for profile enhancement using the established workflow.
