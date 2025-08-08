# Configuration Management

This directory contains all configuration files and environment settings for the Arctic Species CITES trade data import system.

## Configuration Files

### `.env`
Main environment variables file containing:
- **Supabase Configuration**: Database connection credentials
- **CITES API Configuration**: API keys and tokens for CITES data access
- **Other API Keys**: Additional service credentials

### `database.py`
Database configuration and connection management

### `settings.py`
Application settings and constants

### `api_config.py`
API endpoint configurations and rate limiting settings

## Environment Variables

### Required Variables
```bash
# Supabase Database
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# CITES API Access
CITES_API_KEY=your_cites_api_key
CITES_API_TOKEN=your_cites_api_token

# Optional: IUCN API
IUCN_API_TOKEN=your_iucn_api_token
```

### Setup Instructions

1. Copy `.env.example` to `.env`
2. Fill in your actual credentials
3. Never commit `.env` to version control
4. Use the config manager to access settings

## Usage

```python
from rebuild.config.settings import get_settings

settings = get_settings()
supabase_url = settings.supabase_url
cites_api_key = settings.cites_api_key
```

## Security Notes

- Keep `.env` file secure and never share credentials
- Use environment-specific configuration files
- Rotate API keys regularly
- Monitor API usage and rate limits