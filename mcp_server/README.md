# Arctic Tracker MCP Server

A Model Context Protocol (MCP) server specifically designed for the Arctic Tracker API project, providing AI assistants with tools to query and analyze CITES trade data, species information, and conservation status data.

## Features

### Core Tools

- **`list_arctic_species`** - List Arctic species with filtering by taxonomic groups, conservation status, or region
- **`search_species`** - Search for species by scientific name, common name, or family
- **`get_cites_trade_data`** - Query CITES trade records with comprehensive filtering options
- **`get_conservation_status`** - Get IUCN Red List and CITES listing information
- **`get_species_threats`** - Retrieve threat assessments for species
- **`get_distribution_data`** - Get species distribution and range information
- **`get_trade_summary`** - Access pre-aggregated trade summary data
- **`query_database`** - Generic database query tool for any table

### Specialized for Arctic Research

- CITES trade data analysis
- Arctic species distribution mapping
- Conservation status tracking
- Threat assessment queries
- Multi-language common names support
- Subpopulation data integration

## Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Configure your Supabase connection in `.env`:
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

4. Build the server:
```bash
npm run build
```

## Usage

### Development Mode
```bash
npm run dev
```

### Production Mode
```bash
npm run build
npm start
```

### As MCP Server

Add to your MCP client configuration (e.g., Claude Desktop, Cursor):

```json
{
  "mcpServers": {
    "arctic-tracker": {
      "command": "node",
      "args": ["/path/to/arctic-tracker-mcp-server/dist/index.js"],
      "env": {
        "SUPABASE_URL": "your_supabase_url",
        "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key"
      }
    }
  }
}
```

Or use the npm package approach:
```json
{
  "mcpServers": {
    "arctic-tracker": {
      "command": "npx",
      "args": ["arctic-tracker-mcp@latest"],
      "env": {
        "SUPABASE_URL": "your_supabase_url", 
        "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key"
      }
    }
  }
}
```

## Tool Examples

### List Arctic Marine Mammals
```json
{
  "name": "list_arctic_species",
  "arguments": {
    "class": "MAMMALIA",
    "limit": 20
  }
}
```

### Search for Polar Bears
```json
{
  "name": "search_species",
  "arguments": {
    "query": "Ursus maritimus",
    "search_type": "scientific_name"
  }
}
```

### Get CITES Trade Data for a Species
```json
{
  "name": "get_cites_trade_data", 
  "arguments": {
    "species_id": "uuid-here",
    "year": 2023,
    "limit": 100
  }
}
```

### Query Conservation Status
```json
{
  "name": "get_conservation_status",
  "arguments": {
    "species_id": "uuid-here",
    "assessment_type": "IUCN"
  }
}
```

### Get Species Distribution in Specific Arctic Region
```json
{
  "name": "get_distribution_data",
  "arguments": {
    "species_id": "uuid-here",
    "region": "canadian_arctic",
    "include_subpopulations": true
  }
}
```

## Database Schema Integration

This MCP server is designed to work with the Arctic Tracker database schema, including:

- `species` - Core species taxonomic data
- `cites_trade_records` - CITES trade transaction records  
- `cites_listings` - CITES appendix classifications
- `iucn_assessments` - IUCN Red List assessment data
- `species_threats` - Threat assessments
- `distribution_ranges` - Geographic distribution data
- `subpopulations` - Species subpopulation data
- `common_names` - Multilingual species names
- `conservation_measures` - Conservation actions
- `timeline_events` - Historical events
- `catch_records` - Fishing/hunting data
- `species_trade_summary` - Pre-aggregated trade summaries
- `families` - Normalized taxonomic family data

## Security

- Uses Supabase Row Level Security (RLS) policies
- Requires service role key for administrative operations
- Input validation using Zod schemas
- Error handling and sanitization

## Development

### Project Structure
```
src/
├── index.ts          # Main MCP server implementation
└── types/            # TypeScript type definitions (future)

dist/                 # Compiled JavaScript output
```

### Building
```bash
npm run build
```

### Testing
```bash
npm test
```

### Watching for Changes
```bash
npm run watch
```

## Contributing

1. Follow the existing code structure
2. Add appropriate input validation
3. Include error handling
4. Update documentation
5. Test with the Arctic Tracker database

## License

MIT License - see LICENSE file for details.

## Related Projects

- [Arctic Tracker API](../README.md) - Main API project
- [Supabase MCP Server](https://github.com/supabase-community/supabase-mcp) - Official Supabase MCP server
- [Model Context Protocol](https://modelcontextprotocol.io) - MCP specification
