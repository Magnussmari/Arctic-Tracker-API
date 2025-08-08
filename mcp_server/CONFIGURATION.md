# Arctic Tracker MCP Server Configuration Guide

This guide shows how to configure the Arctic Tracker MCP Server with popular AI tools and IDEs.

## Prerequisites

1. **Supabase Project**: Ensure your Arctic Tracker Supabase project is running
2. **Environment Setup**: Configure your `.env` file with Supabase credentials
3. **Build the Server**: Run `npm run build` in the mcp_server directory

## Configuration Examples

### Claude Desktop

Edit your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "arctic-tracker": {
      "command": "node",
      "args": ["/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/mcp_server/dist/index.js"],
      "env": {
        "SUPABASE_URL": "your_supabase_project_url",
        "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key"
      }
    }
  }
}
```

### Cursor IDE

1. Open Cursor Settings
2. Navigate to Extensions → MCP
3. Add new server configuration:

```json
{
  "mcpServers": {
    "arctic-tracker": {
      "command": "node",
      "args": ["/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/mcp_server/dist/index.js"],
      "env": {
        "SUPABASE_URL": "your_supabase_project_url",
        "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key"
      }
    }
  }
}
```

### VS Code with Copilot

Create or edit `.vscode/mcp.json` in your project root:

```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "supabase-url",
      "description": "Supabase Project URL",
      "password": false
    },
    {
      "type": "promptString", 
      "id": "supabase-key",
      "description": "Supabase Service Role Key",
      "password": true
    }
  ],
  "servers": {
    "arctic-tracker": {
      "command": "node",
      "args": ["/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/mcp_server/dist/index.js"],
      "env": {
        "SUPABASE_URL": "${input:supabase-url}",
        "SUPABASE_SERVICE_ROLE_KEY": "${input:supabase-key}"
      }
    }
  }
}
```

### Windsurf (Codeium)

1. Open Windsurf
2. Navigate to Cascade assistant
3. Click the hammer (MCP) icon → Configure
4. Add the server configuration:

```json
{
  "mcpServers": {
    "arctic-tracker": {
      "command": "node",
      "args": ["/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/mcp_server/dist/index.js"],
      "env": {
        "SUPABASE_URL": "your_supabase_project_url",
        "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key"
      }
    }
  }
}
```

### Cline (VS Code Extension)

Add to your VS Code settings.json or Cline configuration:

```json
{
  "mcpServers": {
    "arctic-tracker": {
      "command": "node",
      "args": ["/Users/magnussmari/Arctic_Tracker(version_1.0)/Arctic-Tracker-API/mcp_server/dist/index.js"],
      "env": {
        "SUPABASE_URL": "your_supabase_project_url",
        "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key"
      }
    }
  }
}
```

## Environment Variables

Create a `.env` file in the mcp_server directory:

```env
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Optional - for read-only access
SUPABASE_ANON_KEY=your_anon_key_here

# Optional - for debugging
NODE_ENV=development
DEBUG=true
```

## Getting Your Supabase Credentials

1. **Supabase URL**: Go to your Supabase dashboard → Settings → API → Project URL
2. **Service Role Key**: Go to your Supabase dashboard → Settings → API → Project API keys → service_role (secret)
3. **Anon Key**: Go to your Supabase dashboard → Settings → API → Project API keys → anon (public)

## Verification

After configuration, verify the setup:

1. **Test Connection**:
   ```bash
   cd mcp_server
   node test-connection.js
   ```

2. **Start in Development Mode**:
   ```bash
   npm run dev
   ```

3. **Check MCP Client**: Look for the Arctic Tracker server in your MCP client's server list with a green status indicator.

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Verify Supabase credentials in `.env`
   - Check that your Supabase project is active
   - Ensure service role key has proper permissions

2. **Module Not Found**
   - Run `npm install` in the mcp_server directory
   - Ensure Node.js 18+ is installed
   - Run `npm run build` to compile TypeScript

3. **MCP Client Not Detecting Server**
   - Restart your MCP client after adding configuration
   - Check file paths in configuration are absolute and correct
   - Verify JSON configuration syntax

4. **Permission Denied**
   - Ensure the compiled `dist/index.js` file exists
   - Check that Node.js has execution permissions
   - Verify Supabase Row Level Security policies

### Testing Individual Tools

Once connected, test the tools in your AI assistant:

```
List arctic marine mammals:
Use the list_arctic_species tool with class="MAMMALIA"

Search for polar bears:
Use the search_species tool with query="Ursus maritimus"

Get CITES trade data:
Use the get_cites_trade_data tool with appropriate filters

Check conservation status:
Use the get_conservation_status tool for IUCN and CITES data
```

## Performance Tips

1. **Use Filters**: Always use appropriate filters to limit result sets
2. **Pagination**: Use limit and offset parameters for large datasets  
3. **Specific Queries**: Use the most specific tool for your use case
4. **Caching**: Consider implementing caching for frequently accessed data

## Security Considerations

1. **Service Role Key**: Keep your service role key secure and never commit it to version control
2. **Row Level Security**: Ensure RLS policies are properly configured in Supabase
3. **Network Access**: Consider IP restrictions for production deployments
4. **Monitoring**: Monitor API usage and implement rate limiting if needed

For more information, see the main [README.md](./README.md) file.
