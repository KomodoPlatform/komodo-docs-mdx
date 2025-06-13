#!/bin/bash

# Update OpenAPI Specification Script
# This script runs the mapping.py tool to update the main OpenAPI specification
# with any new or changed endpoint definitions.

set -e

# Change to the script directory
cd "$(dirname "$0")"

echo "🚀 Updating Komodo DeFi Framework OpenAPI Specification..."

# Run the mapping script with OpenAPI update
python mapping.py --update-openapi

echo "✅ OpenAPI specification update completed!"
echo ""
echo "📝 Next steps:"
echo "   1. Review the changes in postman/openapi/openapi.yaml"
echo "   2. Commit the updated files if the changes look correct"
echo "   3. Test the OpenAPI specification with your preferred tools" 