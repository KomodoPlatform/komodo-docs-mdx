#!/bin/bash

# Komodo DeFi Framework Documentation Sync Script
# Now with support for nested directory structures!

source py/.venv/bin/activate

# Configuration
USE_NESTED_STRUCTURE=${USE_NESTED_STRUCTURE:-true}  # Set to 'false' for legacy flat structure
STRUCTURE_FLAG=""

if [ "$USE_NESTED_STRUCTURE" = "true" ]; then
    echo "🗂️  Using NESTED directory structure (organized by functional area)"
    STRUCTURE_FLAG="--nested-structure"
else
    echo "📁 Using FLAT directory structure (legacy compatibility)"
    STRUCTURE_FLAG="--flat-structure"
fi

echo "🚀 Starting KDF Documentation Sync..."
echo "=" * 50

# Step 1: Get the foundational data from repository
echo "📊 Step 1: Scanning KDF repository..."
python py/kdf_tools.py scan --branch dev --versions v1 v2 --force-refresh

# Step 2: Compare repository vs existing documentation (identify gaps)
echo "🔍 Step 2: Comparing repository vs documentation..."
python py/kdf_tools.py compare --branch dev --versions v1 v2

# Step 3: Generate fresh OpenAPI specs from MDX documentation
echo "🔧 Step 3: Generating OpenAPI specifications..."
python py/kdf_tools.py $STRUCTURE_FLAG openapi --version all

# Step 4: Extract JSON examples from MDX files
echo "📊 Step 4: Extracting JSON examples from MDX files..."
python py/kdf_tools.py $STRUCTURE_FLAG json-extract --versions all

# Step 5: Generate fresh Postman collections (uses the new JSON examples)
echo "📮 Step 5: Generating Postman collections..."
python py/kdf_tools.py $STRUCTURE_FLAG postman --versions all

# Step 6: Create unified mapping that incorporates all the fresh data
echo "🗺️  Step 6: Creating unified mapping..."
python py/kdf_tools.py map

echo ""
echo "✅ KDF Documentation Sync completed!"
echo ""
echo "📈 Results Summary:"
echo "  - Repository methods scanned and compared"
echo "  - OpenAPI specs generated with $([ "$USE_NESTED_STRUCTURE" = "true" ] && echo "NESTED" || echo "FLAT") structure"
echo "  - JSON examples extracted and organized"
echo "  - Postman collections updated"
echo "  - Unified mapping created"
echo ""
echo "🔮 Future Changes:"
echo "  - Version migrations (v2-dev → v2): Automatic"
echo "  - New categories: Easy to add via configuration"
echo "  - Structure changes: Backward compatible"
echo ""
echo "🛠️  To switch structures:"
echo "  - Nested: export USE_NESTED_STRUCTURE=true"
echo "  - Flat: export USE_NESTED_STRUCTURE=false"