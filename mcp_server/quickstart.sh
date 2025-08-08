#!/bin/bash

# Arctic Tracker MCP Server Quick Start

echo "🧊 Arctic Tracker MCP Server Quick Start"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "package.json" ]; then
    echo "❌ Please run this script from the mcp_server directory"
    exit 1
fi

echo "📁 Current directory: $(pwd)"

# Run the installation script
if [ -f "install.sh" ]; then
    echo "🚀 Running installation..."
    ./install.sh
else
    echo "⚠️  install.sh not found, running manual setup..."
    npm install
    npm run build
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  Environment file (.env) not found!"
    echo "Please create .env file with your Supabase credentials:"
    echo ""
    echo "SUPABASE_URL=https://your-project.supabase.co"
    echo "SUPABASE_SERVICE_ROLE_KEY=your_service_role_key"
    echo ""
    echo "You can copy from .env.example:"
    echo "cp .env.example .env"
    echo ""
    read -p "Press Enter after you've configured .env file..."
fi

# Test the connection
echo ""
echo "🔍 Testing connection to Arctic Tracker database..."
npm run test

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Success! Your Arctic Tracker MCP Server is ready!"
    echo ""
    echo "Next steps:"
    echo "1. Add the server to your MCP client (see CONFIGURATION.md)"
    echo "2. Use Arctic Tracker tools in your AI assistant"
    echo ""
    echo "Example configuration for Claude Desktop:"
    echo '{'
    echo '  "mcpServers": {'
    echo '    "arctic-tracker": {'
    echo '      "command": "node",'
    echo '      "args": ["'$(pwd)'/dist/index.js"],'
    echo '      "env": {'
    echo '        "SUPABASE_URL": "your_supabase_url",'
    echo '        "SUPABASE_SERVICE_ROLE_KEY": "your_service_role_key"'
    echo '      }'
    echo '    }'
    echo '  }'
    echo '}'
    echo ""
else
    echo ""
    echo "❌ Connection test failed. Please check your .env configuration."
    echo "See CONFIGURATION.md for detailed setup instructions."
fi
