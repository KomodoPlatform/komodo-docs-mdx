#!/bin/bash

source py/.venv/bin/activate

# Step 1: Get the foundational data from repository
python py/kdf_tools.py scan --branch dev --versions v1 v2 --force-refresh

# Step 2: Compare repository vs existing documentation (identify gaps)
python py/kdf_tools.py compare --branch dev --versions v1 v2

# Step 3: Generate fresh OpenAPI specs from MDX documentation
python py/kdf_tools.py openapi --version all

# Step 4: Generate fresh Postman collections (uses the new OpenAPI specs)
python py/kdf_tools.py postman --versions all

# Step 5: Create unified mapping that incorporates all the fresh data
python py/kdf_tools.py map