#!/bin/bash

# Komodo DeFi Framework Documentation Sync Script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the utils directory (where this script should be run from)
cd "$SCRIPT_DIR"

# Activate Python virtual environment
source py/.venv/bin/activate

echo "==================================================================="
echo "============== 🚀 Starting KDF Documentation Sync... =============="
echo "==================================================================="
echo

# Step 1A: Scan KDF Rust Repository
# OUTPUT: Creates kdf_rust_methods_{branch}_YYYYMMDD_HHMMSS.json in utils/py/data/
# CONTAINS: All RPC methods found in the Rust codebase, organized by API version (v1/v2)
# PURPOSE: Establishes the "source of truth" for what methods actually exist in the code
echo "============== 📊 Step 1A: Scanning KDF repository... ==============="
echo "# This step scans the Rust source code and produces:"
echo "#   - utils/py/data/kdf_rust_methods_{branch}_YYYYMMDD_HHMMSS.json"
echo "#   - Contains all RPC methods found in Rust code (v1 & v2)"
if ! python py/kdf_tools.py scan-rust --branch dev --versions v1 v2; then
    echo "❌ Step 1A failed: Repository scanning"
    exit 1
fi
echo

# Step 1B: Scan MDX Documentation Files  
# OUTPUT: Creates kdf_mdx_methods_YYYYMMDD_HHMMSS.json in utils/py/data/
# CONTAINS: All methods found in existing MDX documentation files
# PURPOSE: Establishes what methods are currently documented
echo "============== 📊 Step 1B: Scanning MDX files... ==============="
echo "# This step scans existing documentation and produces:"
echo "#   - utils/py/data/kdf_mdx_methods_YYYYMMDD_HHMMSS.json"
echo "#   - Contains all methods found in MDX/YAML documentation"
echo "#   - utils/py/data/kdf_mdx_method_paths_YYYYMMDD_HHMMSS.json"
echo "#   - Contains method-to-path mapping (generated efficiently during scan)"
echo "#   - Includes gap analysis for debugging and planning"
if ! python py/kdf_tools.py scan-mdx --versions all; then
    echo "❌ Step 1B failed: MDX documentation scanning"
    exit 1
fi
echo

# Step 2: Generate OpenAPI Specifications
# OUTPUT: Creates/updates OpenAPI YAML files in openapi/ directory
# STRUCTURE: Organized by version and method (nested) or flat structure
# PURPOSE: Provides machine-readable API specifications for tools/integrations
echo "============== 🔧 Step 2: Generating OpenAPI specifications... ==============="
echo "# This step processes MDX files and produces:"
echo "#   - openapi/paths/v1/*.yaml and openapi/paths/v2/*.yaml files"
echo "#   - Each method gets its own OpenAPI specification file"
echo "#   - Processes API methods, common structures, and enums"
echo "#   - Generates common schema files with auto-detected enums"
echo "#   - Creates category-specific OpenAPI files (task, lightning, etc.)"
echo "#   - Includes request/response schemas, parameters, examples"
echo "#   - Processes both v1 and v2 in a single run for comprehensive tracking"
if ! python py/kdf_tools.py openapi --version all; then
    echo "❌ Step 2 failed: OpenAPI specification generation"
    exit 1
fi
echo

# Step 3: Extract JSON Examples
# OUTPUT: Creates JSON example files in postman/json/kdf/ directory
# STRUCTURE: Organized by version and method, with multiple examples per method
# PURPOSE: Provides clean JSON examples for Postman collections and testing
echo "============== 📊 Step 3: Extracting JSON examples from MDX files... ==============="
echo "# This step extracts JSON examples and produces:"
echo "#   - postman/json/kdf/v1/ and postman/json/kdf/v2/ directories"
echo "#   - Separate files for request/response examples"
echo "#   - Clean, validated JSON ready for Postman import"
if ! python py/kdf_tools.py json-extract --versions all; then
    echo "❌ Step 3 failed: JSON example extraction"
    exit 1
fi
echo

# Step 4: Generate Postman Collections
# OUTPUT: Creates/updates Postman collection JSON files in postman/collections/
# CONTAINS: Complete Postman collections with requests, examples, and organization
# PURPOSE: Provides ready-to-import Postman collections for API testing
echo "============== 📮 Step 4: Generating Postman collections... ==============="
echo "# This step creates Postman collections and produces:"
echo "#   - postman/collections/KDF_API_V1_Collection.postman_collection.json"
echo "#   - postman/collections/KDF_API_V2_Collection.postman_collection.json"
echo "#   - postman/environments/KDF_API_V1_Environment.postman_environment.json"
echo "#   - postman/environments/KDF_API_V2_Environment.postman_environment.json"
echo "#   - Complete collections with organized folders"
echo "#   - All request/response examples included"
echo "#   - Ready for direct import into Postman"
if ! python py/kdf_tools.py postman --versions all; then
    echo "❌ Step 4 failed: Postman collection generation"
    exit 1
fi
echo

# Step 5: Create Unified Mapping & Analysis
# OUTPUT: Creates/updates unified mapping files showing relationships between all components
# CONTAINS: Cross-references between MDX files, OpenAPI specs, JSON examples, Postman, and comprehensive gap analysis
# PURPOSE: Provides comprehensive view of documentation ecosystem, coverage analysis, and enables advanced tooling
echo "============== 🗺️ Step 5: Creating unified mapping & comprehensive analysis... ==============="
echo "# This step creates comprehensive mappings and produces:"
echo "#   - Unified mapping files showing relationships between:"
echo "#     * MDX documentation files"
echo "#     * OpenAPI specification files"  
echo "#     * JSON example files"
echo "#     * Postman collection entries"
echo "#   - Comprehensive coverage analysis and gap identification:"
echo "#     * Repository vs documentation comparison"
echo "#     * Missing methods identification"
echo "#     * Coverage percentages and statistics"
echo "#     * File path mapping for all methods"
echo "#   - Enables cross-referencing and consistency checking"
echo "#   - Powers advanced tooling and automation"
echo "#   - Includes hotlinks to specific Postman collection requests"
echo "#   - Maps method names to collection folder paths and request IDs"
if ! python py/kdf_tools.py methods-map; then
    echo "❌ Step 5 failed: Unified mapping generation"
    exit 1
fi
echo

# Step 6: Comprehensive Cleanup
# OUTPUT: Removes old timestamped files while preserving the most recent ones
# CONTAINS: Cleanup of all temporary and intermediate files generated during the sync process
# PURPOSE: Maintains a clean workspace while preserving recent files for debugging and comparison
echo "============== 🧹 Step 6: Comprehensive cleanup of old files... ==============="
echo "# This step performs final cleanup and:"
echo "#   - Removes old timestamped files (keeps 3 most recent of each type)"
echo "#   - Cleans up temporary files from all previous steps"
echo "#   - Maintains workspace hygiene while preserving recent files"
echo "#   - Provides summary of cleanup actions performed"
echo "#   - Ensures consistent file management across all operations"
if ! python py/kdf_tools.py cleanup --keep 3; then
    echo "❌ Step 6 failed: Cleanup operation"
    exit 1
fi
echo

echo "===================================================================="
echo "==  ✅ KDF Documentation Sync completed successfully at $(date)"  ==
echo "===================================================================="

