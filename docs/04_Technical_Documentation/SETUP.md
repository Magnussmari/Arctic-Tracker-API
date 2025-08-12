# Arctic Tracker API - Setup Guide

This guide will help you set up the Arctic Tracker API development environment from scratch.

## Prerequisites

### Required Software
- Python 3.8 or higher
- pip (Python package manager)
- Git
- PostgreSQL client tools (optional, for direct DB access)

### Required Accounts
- [Supabase](https://supabase.com) account with a project
- [IUCN Red List API](https://apiv3.iucnredlist.org/) account (optional)

## Step 1: Clone the Repository

```bash
git clone [repository-url]
cd Arctic-Tracker-API
```

## Step 2: Set Up Python Environment

### Using venv (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### Using conda (Alternative)
```bash
conda create -n arctic-tracker python=3.8
conda activate arctic-tracker
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Key Dependencies
- `supabase`: Supabase Python client
- `python-dotenv`: Environment variable management
- `pandas`: Data processing
- `requests`: HTTP requests
- `psycopg2-binary`: PostgreSQL adapter

## Step 4: Configure Environment Variables

1. Copy the example environment file:
```bash
cp config/.env.example config/.env
```

2. Edit `config/.env` with your credentials:
```bash
# Required fields
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

### Getting Supabase Credentials

1. Log in to [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to Settings → API
4. Copy:
   - Project URL → `SUPABASE_URL`
   - `anon` public key → `SUPABASE_ANON_KEY`
   - `service_role` secret key → `SUPABASE_SERVICE_ROLE_KEY`

⚠️ **Security Note**: Never commit `.env` files to version control!

## Step 5: Set Up Database

### Option A: Use Existing Database
If connecting to an existing Arctic Tracker database, skip to Step 6.

### Option B: Create New Database

1. In Supabase Dashboard, go to SQL Editor

2. Run the migration scripts in order:
```sql
-- 1. Main schema
-- Copy contents of db_architechture_june25.sql

-- 2. CMS tables
-- Copy contents of migrations/create_cms_listings_table.sql

-- 3. Glossary tables
-- Copy contents of migrations/create_glossary_table.sql
```

3. Load initial glossary data:
```sql
-- Copy contents of migrations/insert_glossary_data.sql
```

## Step 6: Verify Setup

### Test Database Connection
```bash
python config/supabase_config.py
```

Expected output:
```
Testing Supabase connection...
✅ Connection successful!
```

### Run Basic Query Test
```python
# test_connection.py
import sys
sys.path.append('.')
from config.supabase_config import get_supabase_client

client = get_supabase_client()
response = client.table('species').select('count', count='exact').execute()
print(f"Species in database: {response.count}")
```

## Step 7: Load Sample Data (Optional)

### Load CMS Conservation Data
```bash
cd core
python process_cms_species_data.py  # Process raw CMS data
python load_cms_data_to_db.py       # Load to database
```

### Verify Data Load
```bash
python verify_cms_data.py
```

## Step 8: Development Workflow

### Running Scripts
Most data processing scripts are in the `core/` directory:

```bash
cd core

# Extract trade data
python extract_species_trade_data.py --mode incremental

# Generate summaries
python generate_trade_summaries.py
```

### Using Jupyter Notebooks (Optional)
```bash
pip install jupyter
jupyter notebook
```

## Common Issues & Solutions

### Issue: ModuleNotFoundError
**Solution**: Ensure you're in the virtual environment and run from project root:
```bash
cd /path/to/Arctic-Tracker-API
python core/script_name.py
```

### Issue: Supabase Connection Failed
**Solution**: Check your `.env` file has correct credentials and no extra spaces.

### Issue: Permission Denied (Row Level Security)
**Solution**: Use service role key for write operations:
```python
client = get_supabase_client(use_service_role=True)
```

### Issue: Large Data Files Missing
**Solution**: CITES trade CSV files are not in the repository. Contact the team for access to:
- `/species_data/raw_data/Trade_full/` directory
- Complete trade database CSV files

## Development Tools

### Recommended VS Code Extensions
- Python
- Pylance
- PostgreSQL
- Thunder Client (API testing)
- GitLens

### Database Management
- [Supabase Dashboard](https://supabase.com/dashboard) - Web interface
- [TablePlus](https://tableplus.com/) - Desktop client
- [pgAdmin](https://www.pgadmin.org/) - Traditional option

## Testing

### Run Unit Tests
```bash
python -m pytest tests/
```

### Run Integration Tests
```bash
python -m pytest tests/integration/ --integration
```

## Next Steps

1. Review the [API Reference](docs/API_REFERENCE.md)
2. Explore [Frontend Integration Guides](docs/)
3. Check [Data Pipeline Documentation](docs/Trade-data-pipeline.md)
4. Join the development team chat

## Support

If you encounter issues:

1. Check existing documentation in `/docs`
2. Review closed issues on GitHub
3. Contact the development team
4. Consult CLAUDE.md for AI assistance guidelines

---

Welcome to Arctic Tracker development! 🐻‍❄️