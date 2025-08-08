#!/bin/bash
# Arctic Species CITES Data Extraction Pipeline
# This script coordinates the entire extraction process

echo "======================================"
echo "Arctic Species Data Extraction Pipeline"
echo "======================================"
echo ""

# Set working directory
cd /Users/magnussmari/Arctic_Tracker\(version_1.0\)/Arctic-Tracker-API/cites_migration_2025/scripts

# Step 1: Extract Database Architecture
echo "Step 1: Extracting current database architecture..."
python extract_db_architecture.py
if [ $? -ne 0 ]; then
    echo "❌ Failed to extract database architecture"
    exit 1
fi
echo "✅ Database architecture extracted"
echo ""

# Step 2: Create Arctic Species List
echo "Step 2: Creating Arctic species list..."
python create_arctic_species_list.py
if [ $? -ne 0 ]; then
    echo "❌ Failed to create species list"
    exit 1
fi
echo "✅ Arctic species list created"
echo ""

# Step 3: Extract Arctic Trade Data
echo "Step 3: Extracting Arctic species trade data from CITES database..."
echo "⚠️  This will process 56 files (~28M records) and may take 1-2 hours"
echo ""

# Ask for confirmation
read -p "Do you want to proceed with extraction? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Extraction cancelled"
    exit 1
fi

# Run extraction with parallel processing
python extract_arctic_trade_data.py --parallel --workers 4

if [ $? -ne 0 ]; then
    echo "❌ Failed to extract trade data"
    exit 1
fi

echo "✅ Arctic trade data extracted successfully!"
echo ""

# Step 4: Generate Summary Report
echo "Step 4: Generating extraction summary..."
echo ""
echo "Extraction Results:"
echo "-------------------"

# Check output
if [ -f ../extracted_data/arctic_species_trade_data_v2025.csv ]; then
    RECORD_COUNT=$(wc -l < ../extracted_data/arctic_species_trade_data_v2025.csv)
    echo "✅ Total Arctic trade records extracted: $((RECORD_COUNT-1))"
    echo "📄 Output file: ../extracted_data/arctic_species_trade_data_v2025.csv"
else
    echo "❌ Combined output file not found"
fi

echo ""
echo "======================================"
echo "Extraction Pipeline Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Review extracted data in: ../extracted_data/"
echo "2. Check extraction logs in: ../logs/"
echo "3. Proceed with data validation and migration planning"