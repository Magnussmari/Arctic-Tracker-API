### Arctic Tracker Data Sources

Last updated: Aug 2025

This document explains all datasets stored in the Arctic Tracker database, how they are structured, where they come from, how they are refreshed, and important caveats. The database runs on PostgreSQL (Supabase).

### Core species reference data

- **Tables**: `species`, `families`, `common_names`, `subpopulations`
- **What it is**: Canonical list of Arctic species and taxonomy, multilingual common names, and IUCN subpopulation names (where available).
- **Key fields**:
  - `species`: `scientific_name`, `common_name`, taxonomy fields, optional `sis_id` (IUCN SIS), descriptive fields for profiles
  - `families`: normalized family metadata; `species.family_id` references this
  - `common_names`: per-language names, `is_main` flag
  - `subpopulations`: IUCN subpopulation names and SIS IDs
- **Primary sources**:
  - IUCN (taxonomic backbone, SIS IDs)
  - Internal curation (common names, descriptive fields)
  - iNaturalist ID references when available
- **Refresh/ingestion**:
  - Scripts in `core/` (e.g., `process_cms_species_data.py`, `upload_species_profiles.py`) and migration utilities normalize taxonomy and link families.
- **Caveats**: Some descriptive/profile fields may be incomplete pending profile ingestion.

### IUCN Red List assessments

- **Tables**: `iucn_assessments`
- **What it is**: Historical and latest IUCN Red List categories per species.
- **Key fields**: `status` (LC/NT/VU/EN/CR/EW/EX), `year_published`, `is_latest`, `url`, `assessment_id`, `scope_code/description`
- **Primary source**: IUCN Red List API
- **Refresh/ingestion**:
  - `core/iucn_client.py`, `core/rebuild_iucn_assessments.py`
- **Coverage**: Latest and prior assessments for tracked species
- **Caveats**: Respect IUCN Terms of Use when redistributing.

### CITES listings (Appendices I/II/III)

- **Tables**: `cites_listings`
- **What it is**: Current and historical CITES Appendix listings for species.
- **Key fields**: `appendix`, `listing_date`, `notes`, `is_current`
- **Primary source**: CITES Appendices
- **Refresh/ingestion**: Via migrations/utilities; may include manual validations
- **Coverage**: Historic to present, `is_current=true` marks the current listing
- **Caveats**: Notes may include annotations; date precision varies historically.

### CITES trade records (legal international trade)

- **Tables**: `cites_trade_records`, `species_trade_summary` (derived)
- **What it is**: Transaction-level records from the CITES Trade Database plus pre-aggregated per-species summaries.
- **Key fields (raw)**: `year`, `appendix`, `taxon`, `term`, `quantity`, `unit`, `importer`, `exporter`, `origin`, `purpose`, `source`, `reporter_type`
- **Key fields (summary)**: `total_trade_records`, `overall_min_year/overall_max_year`, `overall_total_quantity`, `annual_summaries`, distinct code lists
- **Primary source**: CITES Trade Database
- **Refresh/ingestion**:
  - `core/extract_species_trade_data.py`, `core/optimize_species_trade_json.py`, `core/load_optimized_trade_data.py`, `core/generate_trade_summaries.py`
- **Coverage**: Typically late 1970s to recent years (e.g., 1977–2022 in current snapshots)
- **Caveats**:
  - Importer vs exporter reported quantities may disagree (standard CITES caveat)
  - Codes follow official CITES code lists (purpose, source, terms)
  - Known frontend aggregation considerations are tracked in `FRONTEND_URGENT_TRADE_COUNT_FIX.md`

### CMS listings (Convention on Migratory Species)

- **Tables**: `cms_listings`; views: `species_cms_listings`
- **What it is**: CMS Appendix I/II listings with native/introduced/extinct distributions.
- **Key fields**: `appendix`, `listed_under`, `listing_date`, `native_distribution`, `distribution_codes`, `introduced_distribution`, `extinct_distribution`, `distribution_uncertain`
- **Primary source**: CMS
- **Refresh/ingestion**:
  - Migration suite in `migrations/cms_migration/` (e.g., `load_cms_data_to_db.py`, `execute_cms_migration.py`, `cms_migration_queries.sql`)
- **Coverage**: Species-level CMS status and country distributions
- **Caveats**: Some `listing_date` values are text per source; distributions are arrays of country names/codes.

### NAMMCO catch and quota data

- **Tables**: `catch_records`, `countries`, `management_areas`
- **Views**: `nammco_catch_summary`, `nammco_species_totals`
- **What it is**: Harvest/catch data for marine mammals around the North Atlantic.
- **Key fields**: `species_id`, `country_id`, `management_area_id`, `year`, `catch_total`, `quota_amount`, `data_source`
- **Primary source**: NAMMCO (North Atlantic Marine Mammal Commission)
- **Refresh/ingestion**:
  - Migration helpers in `migration/` (e.g., `nammco_import.py`, `simple_nammco_import.py`, `generate_nammco_sql.py`, `schema_updates.sql`)
  - CSVs in `species_data/nammco/`
- **Coverage**: Approx. 1992–2023 based on current CSVs; countries include Greenland, Norway, Iceland, Faroe Islands
- **Caveats**: Quota information and management areas vary by species/year; additional normalization is ongoing.

### Illegal wildlife trade (seizures) data

- **Tables**: `illegal_trade_products`, `illegal_trade_seizures`, `illegal_trade_risk_scores`
- **Materialized view**: `species_illegal_trade_summary`
- **What it is**: Seizure incidents mapped to Arctic species, product types, and simple risk indicators.
- **Key fields**:
  - Seizures: `seizure_year`, `source_database`, `product_type_id`, `quantity`, `unit`, `reported_taxon_name`, `gbif_id`
  - Risk: `legal_trade_volume`, `illegal_seizure_count`, component scores and `overall_risk_score`
- **Primary source**: Consolidation around Stringham et al. 2021 dataset and similar references
- **Refresh/ingestion**:
  - Schema and loaders in `illigal trade/` (e.g., `create_illegal_trade_schema.sql`, `load_illegal_products.py`, `load_illegal_seizures.py`)
- **Coverage**: Year-level resolution in current design; products categorized into live/dead/raw/processed
- **Caveats**: Dates often limited to year; taxon names may require cleaning; risk scoring is heuristic and documented in schema comments.

### Glossary and educational metadata

- **Tables**: `glossary_terms`; views: `glossary_by_category`, `glossary_contextual_terms`
- **What it is**: Conservation and trade terminology for tooltips and educational UI.
- **Primary source**: Internal curation; seeded via `migrations/insert_glossary_data.sql`
- **Caveats**: Publicly readable; write access limited to editor/admin roles via RLS policies.

### Threats, measures, distributions, and events

- **Tables**: `species_threats`, `conservation_measures`, `distribution_ranges`, `timeline_events`
- **What it is**:
  - Threats and measures: future-facing structure aligned with IUCN classification schemas
  - Distributions: per-region presence/origin/seasonality with optional GeoJSON
  - Timeline events: derived milestones from IUCN assessments, CITES/CMS actions, etc.
- **Sources**: IUCN documentation, internal compilation; some tables may be sparsely populated pending data imports

### User profiles and roles

- **Table**: `profiles`
- **What it is**: Application user profiles and roles (admin/editor) used for authorization and editorial features.
- **Key fields**: `email`, `role`, `full_name`, `created_at`, `updated_at` (FK to `auth.users` in Supabase)
- **Policies**: RLS policies allow users to read/update their own profile; roles gate write access to editorial tables (e.g., glossary)

### Derived views and helper functions

- **Views**: `species_with_status_view`, `species_with_family`, `family_species_count`, `species_trade_overview`, `species_cms_listings`, `nammco_*`, `glossary_*`
- **Functions**: `get_conservation_status_changes_for_arctic_species()`, `get_trade_volume_trend_by_year_for_arctic_species()` and glossary search helpers
- **Purpose**: Power performant frontend queries and analytics without duplicating raw data.

### Data lineage and update pathways

- IUCN: `core/iucn_client.py`, `core/rebuild_iucn_assessments.py`
- CITES trade: `core/extract_species_trade_data.py`, `core/optimize_species_trade_json.py`, `core/load_optimized_trade_data.py`, `core/generate_trade_summaries.py`
- CITES listings: populated via migrations/utilities; maintained alongside species
- CMS listings: `migrations/cms_migration/` suite (`load_cms_data_to_db.py`, `execute_cms_migration.py`)
- NAMMCO: `migration/nammco_import.py`, `migration/simple_nammco_import.py`, `migration/schema_updates.sql` with CSVs under `species_data/nammco/`
- Illegal trade: `illigal trade/` loaders and schema; summary via materialized view and refresh function
- Glossary: `migrations/create_glossary_table.sql`, `migrations/insert_glossary_data.sql`

### Typical coverage windows (current snapshot)

- CITES trade: ~1977–2022 (varies by species)
- IUCN assessments: latest available per species plus history
- CMS listings: current appendix and distributions
- NAMMCO catches: 1992–2023 (for member countries in CSV bundle)
- Illegal trade seizures: year-level coverage per dataset used (see schema comments)

### Access controls and performance notes

- Most read paths are publicly readable; writes restricted by RLS (e.g., editors/admins for glossary, service roles for summaries).
- High-volume queries use summary tables/views; consider partitioning by year for `cites_trade_records` and `catch_records` in large deployments.

### Licenses and attribution (external datasets)

- IUCN Red List: Follow IUCN Terms of Use for data redistribution and citation.
- CITES: Cite the CITES Trade Database; observe data use policies.
- CMS: Attribute CMS for listings and distribution data.
- NAMMCO: Attribute NAMMCO for catch and quota data.
- Illegal trade research: Attribute the original publication(s) (e.g., Stringham et al. 2021) and any aggregators used.

### Quick reference: where to look in this repo

- Schema files: `db_architechture_june25.sql`, `migration/schema_updates.sql`, `migrations/**`
- Loaders/ETL: `core/**`, `migration/**`, `migrations/cms_migration/**`, `illigal trade/**`
- Documentation: `docs/DATABASE_SCHEMA.md`, `docs/DATABASE_UPDATE_GUIDE.md`, `docs/reports/*`

If you need a per-table column reference, see `docs/DATABASE_SCHEMA.md` and `db_architechture_june25.sql`.
