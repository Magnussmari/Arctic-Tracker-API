#!/bin/bash

# Arctic Tracker MCP Server Installation Script

echo "🧊 Installing Arctic Tracker MCP Server..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    echo "Visit: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ required. Current version: $(node --version)"
    exit 1
fi

echo "✅ Node.js $(node --version) detected"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating environment file..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your Supabase credentials"
else
    echo "✅ Environment file already exists"
fi

# Build the project
echo "🔨 Building the project..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "🎉 Arctic Tracker MCP Server installed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your Supabase credentials"
echo "2. Test with: npm run dev"
echo "3. Add to your MCP client configuration"
echo ""
echo "Configuration example for Claude Desktop:"
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
