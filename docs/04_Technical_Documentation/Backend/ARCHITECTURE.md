# Arctic Tracker API Backend Architecture

## System Overview

This document provides a visual representation of the Arctic Tracker API backend architecture using Mermaid diagrams.

## Architecture Diagram

```mermaid
%%{init: {"theme": "default", "themeVariables": {"background": "#ffffff"}} }%%
graph TB
    %% External Data Sources
    subgraph "External Data Sources"
        CITES[CITES Trade Database<br/>2GB+ CSV files]
        IUCN[IUCN Red List API v4<br/>Conservation Assessments]
        CMS[CMS Database<br/>Migratory Species Data]
        SCITE[Scite AI<br/>Scientific Research]
    end

    %% Data Processing Pipeline
    subgraph "Data Processing Pipeline"
        subgraph "Extraction Layer"
            EXT1[extract_species_trade_data.py<br/>Extract Arctic species from CITES]
            EXT2[rebuild_iucn_assessments.py<br/>Fetch IUCN conservation data]
            EXT3[process_cms_species_data.py<br/>Process CMS listings]
        end

        subgraph "Optimization Layer"
            OPT1[optimize_species_trade_json.py<br/>Normalize & compress data<br/>60-80% size reduction]
            OPT2[generate_trade_summaries.py<br/>Create pre-aggregated analytics]
        end

        subgraph "Validation Layer"
            VAL1[validate_before_load.py<br/>Data integrity checks]
            VAL2[verify_cms_data.py<br/>CMS data validation]
        end

        subgraph "Loading Layer"
            LOAD1[load_optimized_trade_data.py<br/>Batch insert with backups]
            LOAD2[upload_species_profiles.py<br/>AI-enhanced profiles]
        end
    end

    %% Supabase Backend
    subgraph "Supabase Backend"
        subgraph "PostgreSQL Database"
            subgraph "Core Tables"
                SPECIES[(species<br/>42 Arctic species)]
                TRADE[(cites_trade_records<br/>5+ million records)]
                IUCN_DB[(iucn_assessments<br/>Historical status)]
                CITES_DB[(cites_listings<br/>CITES appendices)]
                CMS_DB[(cms_listings<br/>CMS protection)]
                CATCH[(catch_records<br/>NAMMCO data)]
                SUMMARY[(species_trade_summary<br/>Pre-aggregated data)]
            end

            subgraph "Lookup Tables"
                LOOKUP[lookup_importers<br/>lookup_exporters<br/>lookup_terms<br/>lookup_units<br/>lookup_purposes<br/>lookup_sources]
            end

            subgraph "Support Tables"
                SUPPORT[common_names<br/>families<br/>glossary_terms<br/>article_summary_table]
            end
        end

        subgraph "Supabase Features"
            AUTH[Authentication<br/>Row Level Security]
            API[Auto-generated APIs<br/>REST & GraphQL]
            REALTIME[Real-time<br/>Subscriptions]
            STORAGE[File Storage<br/>Species Images]
        end
    end

    %% MCP Server Integration
    subgraph "MCP Server"
        MCP_TOOLS[MCP Arctic Tracker Server<br/>├── list_arctic_species<br/>├── search_species<br/>├── get_cites_trade_data<br/>├── get_conservation_status<br/>├── get_species_threats<br/>├── get_distribution_data<br/>├── get_trade_summary<br/>└── query_database]
    end

    %% Client Applications
    subgraph "Client Applications"
        WEB[Web Application<br/>React/Next.js]
        AI[AI Assistants<br/>Claude/ChatGPT]
        MOBILE[Mobile Apps<br/>iOS/Android]
        ANALYTICS[Analytics Tools<br/>Data Scientists]
    end

    %% Data Flow Connections
    CITES --> EXT1
    IUCN --> EXT2
    CMS --> EXT3
    SCITE --> LOAD2

    EXT1 --> OPT1
    EXT2 --> VAL1
    EXT3 --> VAL2

    OPT1 --> OPT2
    OPT2 --> VAL1

    VAL1 --> LOAD1
    VAL2 --> LOAD1

    LOAD1 --> TRADE
    LOAD1 --> SPECIES
    LOAD1 --> IUCN_DB
    LOAD1 --> CITES_DB
    LOAD1 --> CMS_DB
    LOAD2 --> SPECIES

    TRADE --> LOOKUP
    TRADE --> SUMMARY

    SPECIES --> IUCN_DB
    SPECIES --> CITES_DB
    SPECIES --> CMS_DB
    SPECIES --> TRADE
    SPECIES --> CATCH
    SPECIES --> SUPPORT

    API --> WEB
    API --> MOBILE
    API --> ANALYTICS
    MCP_TOOLS --> AI

    %% Supabase Internal Connections
    AUTH --> API
    REALTIME --> API
    STORAGE --> API

    %% MCP to Database
    MCP_TOOLS -.-> |Direct SQL Queries| SPECIES
    MCP_TOOLS -.-> |Direct SQL Queries| TRADE
    MCP_TOOLS -.-> |Direct SQL Queries| IUCN_DB

    classDef external fill:#f9f,stroke:#333,stroke-width:2px
    classDef processing fill:#bbf,stroke:#333,stroke-width:2px
    classDef database fill:#bfb,stroke:#333,stroke-width:2px
    classDef feature fill:#fbf,stroke:#333,stroke-width:2px
    classDef client fill:#ffb,stroke:#333,stroke-width:2px

    class CITES,IUCN,CMS,SCITE external
    class EXT1,EXT2,EXT3,OPT1,OPT2,VAL1,VAL2,LOAD1,LOAD2 processing
    class SPECIES,TRADE,IUCN_DB,CITES_DB,CMS_DB,CATCH,SUMMARY,LOOKUP,SUPPORT database
    class AUTH,API,REALTIME,STORAGE,MCP_TOOLS feature
    class WEB,AI,MOBILE,ANALYTICS client
```

## Data Flow Sequence

```mermaid
%%{init: {"theme": "default", "themeVariables": {"background": "#ffffff"}} }%%
sequenceDiagram
    participant External as External Sources
    participant Extract as Extraction Scripts
    participant Optimize as Optimization Scripts
    participant Validate as Validation Scripts
    participant Load as Loading Scripts
    participant DB as Supabase Database
    participant API as Supabase API
    participant Client as Client Applications

    External->>Extract: Raw data (CSV, API)
    Extract->>Optimize: Extracted JSON files
    Optimize->>Validate: Normalized data
    Validate->>Load: Validated data
    Load->>DB: Batch inserts
    DB->>API: Auto-generated endpoints
    API->>Client: REST/GraphQL responses
    
    Note over DB: 5+ million trade records<br/>42 Arctic species<br/>Pre-aggregated summaries
    Note over API: Row Level Security<br/>Real-time subscriptions<br/>Built-in authentication
```

## Database Schema Overview

```mermaid
%%{init: {"theme": "default", "themeVariables": {"background": "#ffffff"}} }%%
erDiagram
    SPECIES ||--o{ CITES_TRADE_RECORDS : has
    SPECIES ||--o{ IUCN_ASSESSMENTS : has
    SPECIES ||--|| CMS_LISTINGS : has
    SPECIES ||--o{ COMMON_NAMES : has
    SPECIES ||--o{ CATCH_RECORDS : has
    SPECIES }|--|| FAMILIES : belongs_to
    
    CITES_TRADE_RECORDS }o--|| LOOKUP_IMPORTERS : uses
    CITES_TRADE_RECORDS }o--|| LOOKUP_EXPORTERS : uses
    CITES_TRADE_RECORDS }o--|| LOOKUP_TERMS : uses
    CITES_TRADE_RECORDS }o--|| LOOKUP_UNITS : uses
    CITES_TRADE_RECORDS }o--|| LOOKUP_PURPOSES : uses
    CITES_TRADE_RECORDS }o--|| LOOKUP_SOURCES : uses

    SPECIES {
        uuid id PK
        string taxon_id
        string scientific_name
        string taxonomic_authority
        uuid family_id FK
        string genus
        string species_epithet
        string iucn_category
        int population_trend
        jsonb conservation_measures
        jsonb habitat_info
        text ai_summary
    }

    CITES_TRADE_RECORDS {
        uuid id PK
        uuid species_id FK
        int year
        int importer_id FK
        int exporter_id FK
        float quantity
        int term_id FK
        int unit_id FK
        int purpose_id FK
        int source_id FK
    }

    IUCN_ASSESSMENTS {
        uuid id PK
        uuid species_id FK
        string assessment_id
        int year
        string category
        string criteria
        text rationale
    }
```

## Key Features

### 1. **Performance Optimizations**
- Normalized data with lookup tables (60-80% storage reduction)
- Pre-aggregated summaries for instant queries
- Composite indexes on frequently queried columns
- Full-text search capabilities

### 2. **Data Pipeline Automation**
- Automated extraction from multiple sources
- Data validation and integrity checks
- Batch processing for large datasets
- Automatic backup creation

### 3. **Security & Access Control**
- Row Level Security (RLS) policies
- Environment-based configuration
- Service role keys for admin operations
- Input validation and sanitization

### 4. **Integration Capabilities**
- MCP server for AI assistant integration
- Auto-generated REST and GraphQL APIs
- Real-time data subscriptions
- Direct SQL query access for advanced users

## Usage Examples

### Running the Data Pipeline

```bash
# 1. Extract species data from CITES
cd core
python extract_species_trade_data.py --mode full

# 2. Optimize the extracted data
python optimize_species_trade_json.py

# 3. Validate before loading
python validate_before_load.py

# 4. Load to database with backup
python load_optimized_trade_data.py --backup

# 5. Generate trade summaries
python generate_trade_summaries.py
```

### API Endpoints

```bash
# Get all Arctic species with conservation status
GET /rest/v1/species?select=*,iucn_assessments(*),cites_listings(*)

# Get trade records for Polar Bear
GET /rest/v1/cites_trade_records?species_id=eq.{polar_bear_uuid}&year=gte.2020

# Get pre-aggregated trade summary
GET /rest/v1/species_trade_summary?species_id=eq.{species_uuid}
```

### MCP Server Usage

```javascript
// List endangered Arctic species
await mcp.list_arctic_species({
  conservation_status: "EN",
  class: "MAMMALIA"
});

// Search for species by name
await mcp.search_species({
  query: "polar bear",
  search_type: "common_name"
});

// Get trade data with filters
await mcp.get_cites_trade_data({
  species_id: "uuid",
  year: 2023,
  purpose: "T"  // Commercial trade
});
```

## Production Infrastructure

- **Database**: Supabase (PostgreSQL 15)
- **API**: Auto-generated REST & GraphQL
- **File Storage**: Supabase Storage for images
- **Authentication**: Supabase Auth with RLS
- **Monitoring**: Built-in Supabase dashboard
- **Backups**: Automated daily backups

## Maintenance Scripts

The system includes several maintenance and utility scripts:

- `update_db_architecture_and_species.py` - Generate database documentation
- `test_supabase_connection.py` - Verify database connectivity
- `create_backup.py` - Manual backup creation
- `restore_from_backup.py` - Restore data from backups

---

*Last Updated: August 2025*
*Arctic Tracker API v1.0*