# Arctic Species Database Architecture Analysis
**Generated:** 2025-05-26 00:31:02
**Analyzer Version:** 2.0.0

## Executive Summary
- **Total Tables:** 14
- **Total Species:** 43
- **Total Families:** 29
- **Species with Both Names:** 43
- **Family Normalization Progress:** 100.0%
- **Data Completion:** 100.0%

## Database Schema Overview
### Tables
- `catch_records` (4 records) 📊 Table
- `cites_listings` (4 records) 📊 Table
- `cites_trade_records` (4 records) 📊 Table
- `common_names` (4 records) 📊 Table
- `conservation_measures` (0 records) 📊 Table
- `distribution_ranges` (0 records) 📊 Table
- `families` (4 records) 📊 Table
- `iucn_assessments` (4 records) 📊 Table
- `profiles` (0 records) 📊 Table
- `species` (4 records) 📊 Table
- `species_threats` (0 records) 📊 Table
- `species_trade_summary` (4 records) 📊 Table
- `subpopulations` (4 records) 📊 Table
- `timeline_events` (4 records) 📊 Table

## Family Normalization Analysis
- **Normalized Families:** 29
- **Families with Order Info:** 29
- **Families with Class Info:** 29
- **Family Distribution by Class:**
  - AVES: 5 families
  - Actinopterygii : 1 families
  - Aves: 3 families
  - CHONDRICHTHYES: 2 families
  - Chondrichthyes: 1 families
  - MAGNOLIOPSIDA: 1 families
  - MAMMALIA: 8 families
  - Mammalia: 7 families
  - ave: 1 families

### Table Structures
#### `catch_records`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | INTEGER | 1 |
| `species_id` | VARCHAR(255) | 5f289c1e-5101-458f-a5ea-a65e5c734569 |
| `country` | VARCHAR(255) | Greenland |
| `year` | INTEGER | 1992 |
| `area` | TEXT | None |
| `catch_total` | INTEGER | 0 |
| `quota` | TEXT | None |
| `source` | VARCHAR(255) | NAMMCO |
| `created_at` | VARCHAR(255) | 2025-04-04T14:56:58.977304+00:00 |

#### `cites_listings`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | VARCHAR(255) | 02034a7c-fa33-4e89-aabe-043d8261ae8a |
| `species_id` | VARCHAR(255) | 5f289c1e-5101-458f-a5ea-a65e5c734569 |
| `appendix` | VARCHAR(255) | II |
| `listing_date` | VARCHAR(255) | 1979-06-28 |
| `notes` | VARCHAR(255) | Listed under Appendix II as part of the Monodon... |
| `is_current` | BOOLEAN | True |

#### `cites_trade_records`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | VARCHAR(255) | 48442bcb-9847-4654-95c0-ae5d7a69249c |
| `species_id` | VARCHAR(255) | 506d9478-6bef-4116-8295-fd1ccc6292c6 |
| `record_id` | VARCHAR(255) | 2416370039 |
| `year` | INTEGER | 2017 |
| `appendix` | VARCHAR(255) | I |
| `taxon` | VARCHAR(255) | Falco rusticolus |
| `class` | VARCHAR(255) | Aves |
| `order_name` | VARCHAR(255) | Falconiformes |
| `family` | VARCHAR(255) | Falconidae |
| `genus` | VARCHAR(255) | Falco |
| `term` | VARCHAR(255) | live |
| `quantity` | FLOAT | 1.0 |
| `unit` | VARCHAR(255) |  |
| `importer` | VARCHAR(255) | BH |
| `exporter` | VARCHAR(255) | NL |
| `origin` | VARCHAR(255) |  |
| `purpose` | VARCHAR(255) | T |
| `source` | VARCHAR(255) | C |
| `reporter_type` | VARCHAR(255) | E |
| `import_permit` | VARCHAR(255) |  |
| `export_permit` | VARCHAR(255) |  |
| `origin_permit` | VARCHAR(255) |  |

#### `common_names`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | VARCHAR(255) | 2f37bab7-bb69-4396-81d4-dbfc728f3973 |
| `species_id` | VARCHAR(255) | f133cabe-d298-4ae4-a03d-5c5899395d52 |
| `name` | VARCHAR(255) | North Atlantic Right Whale |
| `language` | VARCHAR(255) | eng |
| `is_main` | BOOLEAN | True |

#### `conservation_measures` (Error: No data found)
#### `distribution_ranges` (Error: No data found)
#### `families`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | VARCHAR(255) | ec774d8c-35e1-4c5e-9377-bafc9993000e |
| `family_name` | VARCHAR(255) | ACCIPITRIDAE |
| `order_name` | VARCHAR(255) | ACCIPITRIFORMES |
| `class` | VARCHAR(255) | AVES |
| `description` | TEXT | None |
| `created_at` | VARCHAR(255) | 2025-05-25T14:02:22.75238+00:00 |
| `updated_at` | VARCHAR(255) | 2025-05-25T14:02:22.75238+00:00 |

#### `iucn_assessments`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | VARCHAR(255) | e772fc19-3caf-44fd-b7f9-ba7e3fe206c5 |
| `species_id` | VARCHAR(255) | 5f289c1e-5101-458f-a5ea-a65e5c734569 |
| `year_published` | INTEGER | 2023 |
| `is_latest` | BOOLEAN | False |
| `possibly_extinct` | BOOLEAN | False |
| `possibly_extinct_in_wild` | BOOLEAN | False |
| `status` | VARCHAR(255) | LC |
| `url` | VARCHAR(255) | https://www.iucnredlist.org/species/13704/21901... |
| `assessment_id` | INTEGER | 219011698 |
| `scope_code` | VARCHAR(255) | 2 |
| `scope_description` | VARCHAR(255) | Europe |

#### `profiles` (Error: No data found)
#### `species`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | VARCHAR(255) | 332be9c5-d770-467f-886e-6de3832f521e |
| `scientific_name` | VARCHAR(255) | Buteo lagopus |
| `common_name` | VARCHAR(255) | Rough-legged Buzzard |
| `kingdom` | VARCHAR(255) | Animalia |
| `phylum` | VARCHAR(255) | CHORDATA |
| `class` | VARCHAR(255) | AVES |
| `order_name` | VARCHAR(255) | ACCIPITRIFORMES |
| `family` | VARCHAR(255) | ACCIPITRIDAE |
| `genus` | VARCHAR(255) | Buteo |
| `species_name` | VARCHAR(255) | lagopus |
| `authority` | VARCHAR(255) | (Pontoppidan, 1763) |
| `sis_id` | INTEGER | 22695973 |
| `created_at` | VARCHAR(255) | 2025-03-25T12:18:39.485111+00:00 |
| `inaturalist_id` | TEXT | None |
| `default_image_url` | TEXT | None |
| `description` | TEXT | None |
| `habitat_description` | TEXT | None |
| `population_trend` | TEXT | None |
| `population_size` | TEXT | None |
| `generation_length` | TEXT | None |
| `movement_patterns` | TEXT | None |
| `use_and_trade` | TEXT | None |
| `threats_overview` | TEXT | None |
| `conservation_overview` | TEXT | None |
| `family_id` | VARCHAR(255) | ec774d8c-35e1-4c5e-9377-bafc9993000e |

#### `species_threats` (Error: No data found)
#### `species_trade_summary`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `species_id` | VARCHAR(255) | 0ae6a6b2-65cf-402b-a500-347627b68c76 |
| `last_updated_at` | VARCHAR(255) | 2025-05-24T23:05:20.045676+00:00 |
| `total_trade_records` | INTEGER | 171 |
| `overall_min_year` | INTEGER | 1977 |
| `overall_max_year` | INTEGER | 2022 |
| `overall_total_quantity` | FLOAT | 536.0 |
| `distinct_years` | JSONB | [1977, 1978, 1979, 1980, 1982, 1983, 1984, 1985... |
| `distinct_terms` | JSONB | ['bodies', 'eggs', 'eggs (live)', 'feathers', '... |
| `distinct_importers` | JSONB | [{'code': 'US', 'name': 'US'}, {'code': 'DE', '... |
| `distinct_exporters` | JSONB | [{'code': 'DE', 'name': 'DE'}, {'code': 'SU', '... |
| `annual_summaries` | JSONB | [{'year': 1977, 'terms_summary': [{'term': 'egg... |

#### `subpopulations`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | VARCHAR(255) | a2b0c210-5636-46da-8046-ae0902f3c4b7 |
| `species_id` | VARCHAR(255) | 4c358cc2-d0d3-4a34-a3fe-bca2b85db100 |
| `scientific_name` | VARCHAR(255) | Balaena mysticetus Bering-Chukchi-Beaufort Sea ... |
| `subpopulation_name` | VARCHAR(255) | Bering-Chukchi-Beaufort Sea subpopulation |
| `sis_id` | INTEGER | 2468 |
| `authority` | VARCHAR(255) | Linnaeus, 1758 |

#### `timeline_events`
**Records:** 4

| Column | Type | Sample Value |
|--------|------|--------------|
| `id` | VARCHAR(255) | 4610cec6-311a-4270-bce5-ace26104a931 |
| `species_id` | VARCHAR(255) | 5f289c1e-5101-458f-a5ea-a65e5c734569 |
| `event_date` | VARCHAR(255) | 2023-01-01 |
| `year` | INTEGER | 2023 |
| `event_type` | VARCHAR(255) | iucn_assessment |
| `title` | VARCHAR(255) | IUCN Red List Assessment (2023) |
| `description` | VARCHAR(255) | IUCN assessment with scope: Europe |
| `status` | VARCHAR(255) | LC |
| `source_type` | VARCHAR(255) | iucn_assessments |
| `source_id` | TEXT | None |

## Species Names Analysis
### Name Coverage
- **Scientific Names:** 43
- **Common Names:** 43
- **Both Names:** 43

### Family Normalization Status
- **Species with Family ID:** 43
- **Species with Legacy Family:** 43
- **Normalization Progress:** 100.0%

### Taxonomic Distribution
- **AVES:** 6 species
- **Actinopterygii :** 1 species
- **Aves:** 4 species
- **CHONDRICHTHYES:** 2 species
- **Chondrichthyes:** 1 species
- **MAGNOLIOPSIDA:** 1 species
- **MAMMALIA:** 13 species
- **Mammalia:** 14 species
- **ave:** 1 species

### Unique Taxonomic Groups
- **Families:** 29
- **Genera:** 36

## Common Names Analysis
- **Total Common Name Records:** 326
- **Main Names:** 23
- **Languages:**
  - af: 2 names
  - ar: 3 names
  - bul: 8 names
  - cat: 1 names
  - ces: 8 names
  - dan: 9 names
  - deu: 13 names
  - el: 8 names
  - en: 1 names
  - eng: 22 names
  - est: 9 names
  - fin: 10 names
  - fo: 2 names
  - fra: 20 names
  - gle: 8 names
  - he: 2 names
  - hr: 10 names
  - hun: 9 names
  - iku: 3 names
  - is: 4 names
  - ita: 11 names
  - ja: 2 names
  - lav: 8 names
  - lit: 9 names
  - mi: 1 names
  - mlt: 9 names
  - nld: 13 names
  - nor: 12 names
  - pol: 8 names
  - por: 13 names
  - ron: 7 names
  - rus: 3 names
  - slk: 8 names
  - slv: 9 names
  - spa: 20 names
  - sq: 4 names
  - sr: 1 names
  - swe: 20 names
  - tur: 3 names
  - zho: 13 names
