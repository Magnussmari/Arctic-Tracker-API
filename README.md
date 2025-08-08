# Arctic Tracker API

A comprehensive backend system for tracking and analyzing conservation data for Arctic species, integrating CITES trade records, IUCN Red List assessments, CMS migratory species data, and NAMMCO catch statistics.

## 🌟 Overview

Arctic Tracker provides a complete data infrastructure for monitoring 42 Arctic species, offering insights into international trade, conservation status, and sustainable management. The system powers a frontend application with real-time data on Arctic biodiversity.

## 🎯 Key Features

### Data Integration
- **CITES Trade Data**: Complete international trade records for all Arctic species
- **IUCN Red List**: Current conservation status and population trends
- **CMS Data**: Migratory species protection status (NEW)
- **NAMMCO Catch Data**: Sustainable use statistics for marine mammals
- **Species Profiles**: AI-enhanced conservation data with scientific citations (NEW)
- **Glossary System**: Educational terminology database (NEW)

### Technical Capabilities
- **Optimized Data Pipeline**: Processes millions of trade records efficiently
- **Real-time API**: Supabase-powered REST and GraphQL endpoints
- **Pre-aggregated Summaries**: Lightning-fast frontend performance
- **Full-text Search**: Comprehensive search across species and terms
- **Automated Updates**: Scripts for keeping data current

## 📂 Project Structure

```
Arctic-Tracker-API/
├── config/               # Configuration and database connections
│   ├── supabase_config.py
│   └── .env             # Environment variables (not in repo)
├── core/                # Data processing scripts
│   ├── extract_species_trade_data.py
│   ├── process_cms_species_data.py    # NEW
│   ├── load_cms_data_to_db.py         # NEW
│   ├── upload_species_profiles.py    # NEW
│   ├── standardize_species_json_files.py # NEW
│   └── generate_trade_summaries.py
├── docs/                # Documentation
│   ├── CMS_Frontend_Integration_Guide.md      # NEW
│   ├── Glossary_Frontend_Integration_Guide.md # NEW
│   ├── Species_Profile_Upload_System.md       # NEW
│   ├── AI_Workflow_Species_Profile_Generation.md # NEW
│   └── Database_Schema_Guide.md
├── migrations/          # Database migrations
│   ├── create_cms_listings_table.sql          # NEW
│   └── create_glossary_table.sql              # NEW
├── species_data/        # Data files
│   ├── Arctic_Tracker_42_Species_List.md
│   ├── processed/       # Processed data ready for loading
│   └── raw_data/        # Original source files
└── tests/              # Test suites
```

## 🗄️ Database Schema

### Core Tables
- **species**: Master species list with taxonomy
- **cites_trade_records**: ~5M+ trade transactions
- **iucn_assessments**: Conservation status history
- **cites_listings**: Current CITES appendix status
- **cms_listings**: Migratory species protection (NEW)
- **glossary_terms**: Conservation terminology (NEW)
- **species_trade_summary**: Pre-calculated analytics

### Key Views
- **species_trade_overview**: Combined species and trade data
- **species_cms_listings**: CMS status with distribution
- **glossary_by_category**: Terms organized by topic

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Supabase account
- PostgreSQL knowledge helpful

### Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd Arctic-Tracker-API
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp config/.env.example config/.env
# Edit .env with your Supabase credentials
```

### Database Setup

1. Run migrations in Supabase SQL editor:
```sql
-- Run files in order:
-- 1. db_architechture_june25.sql
-- 2. migrations/create_cms_listings_table.sql
-- 3. migrations/create_glossary_table.sql
```

2. Load initial data:
```bash
# Load CMS conservation data
python core/load_cms_data_to_db.py

# Load glossary terms
# Execute migrations/insert_glossary_data.sql in Supabase
```

## 📊 Data Processing Pipeline

### 1. Extract Species Trade Data
```bash
cd core
python extract_species_trade_data.py --mode full
```
Processes CITES CSV files (~2GB) to extract Arctic species records.

### 2. Optimize Trade Data
```bash
python optimize_species_trade_json.py
```
Normalizes data using lookup tables (60-80% size reduction).

### 3. Load to Database
```bash
python load_optimized_trade_data.py --backup
```
Safely loads optimized data with automatic backups.

### 4. Generate Summaries
```bash
python generate_trade_summaries.py
```
Creates pre-aggregated data for frontend performance.

## 🔌 API Usage

### REST API Examples

```javascript
// Get species with all conservation data
const { data } = await supabase
  .from('species')
  .select(`
    *,
    iucn_assessments!inner(*),
    cites_listings!inner(*),
    cms_listings(*)
  `)
  .eq('scientific_name', 'Ursus maritimus')
  .single();

// Search glossary terms
const { data } = await supabase
  .rpc('search_glossary_terms', { 
    search_query: 'CITES' 
  });

// Get trade summary for a species
const { data } = await supabase
  .from('species_trade_summary')
  .select('*')
  .eq('species_id', speciesId)
  .single();
```

## 📚 Frontend Integration Guides

### Latest Features
1. **CMS Data Integration** - [Guide](docs/CMS_Frontend_Integration_Guide.md)
   - 31 species with migratory protection status
   - Distribution data for 210 countries
   - Conservation tab enhancements

2. **Glossary System** - [Guide](docs/Glossary_Frontend_Integration_Guide.md)
   - 80+ conservation terms
   - Context-aware tooltips
   - Full-text search capability

3. **Species Profiles** - [Guide](docs/Frontend_Species_Profile_Display_Guide.md)
   - AI-generated conservation profiles
   - Scientific references
   - Threat assessments

## 🛠️ Maintenance Scripts

### Update IUCN Assessments
```bash
python core/rebuild_iucn_assessments.py
```

### Verify Data Integrity
```bash
python core/verify_cms_data.py
python validation/validate_before_load.py
```

### Database Reports
```bash
python core/update_db_architecture_and_species.py
```

## 📈 Performance Optimizations

- **Lookup Tables**: Reduce storage by 60-80%
- **Batch Processing**: Handle millions of records efficiently
- **Indexed Searches**: Full-text search on species and terms
- **Pre-aggregation**: Summary tables for instant analytics
- **Compression**: Gzipped JSON for large datasets

## 🔒 Security

- **Row Level Security**: Granular access control
- **Service Role Keys**: Admin operations only
- **Environment Variables**: Secure credential management
- **Input Validation**: Comprehensive data sanitization

## 📝 Documentation

### For Backend Developers
- [Database Schema](docs/Database_Schema_Guide.md)
- [Trade Data Pipeline](docs/Trade-data-pipeline.md)
- [Migration Guide](migrations/README.md)

### For Frontend Developers
- [CMS Integration](docs/CMS_Frontend_Integration_Guide.md)
- [Glossary Integration](docs/Glossary_Frontend_Integration_Guide.md)
- [Species Profile Display](docs/Frontend_Species_Profile_Display_Guide.md)
- [TypeScript Types](docs/cms_types.ts)

### API Reference
- [Supabase Auto-generated Docs](https://supabase.com/dashboard/project/[project-id]/api)
- [GraphQL Explorer](https://supabase.com/dashboard/project/[project-id]/graphql)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Follow existing code patterns
4. Add tests for new features
5. Submit a pull request

## 📊 Current Statistics

- **Species Tracked**: 42 Arctic species
- **Trade Records**: 5+ million transactions
- **Date Range**: 1975-2024
- **Countries**: 200+ involved in Arctic species trade
- **CMS Species**: 31 with migratory protection
- **Glossary Terms**: 80+ conservation definitions

## 🚧 Recent Updates (July 2025)

- ✅ CMS data integration complete
- ✅ Glossary system implemented
- ✅ Performance optimizations
- ✅ Enhanced documentation
- ✅ TypeScript type definitions

## 📞 Support

For questions or issues:
- Check documentation in `/docs`
- Review CLAUDE.md for AI assistance guidelines
- Contact the development team

---

**Arctic Tracker API** - Protecting Arctic biodiversity through data-driven insights.