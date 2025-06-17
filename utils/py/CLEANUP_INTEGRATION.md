# Integrated Cleanup Functionality

The cleanup functionality has been fully integrated into the main `kdf_tools.py` CLI to prevent stale YAML, Postman collections, and JSON examples from causing issues during documentation generation.

## Quick Start

### Recommended: Complete Regeneration
```bash
# Clean and regenerate everything (recommended for most use cases)
python kdf_tools.py regenerate-all

# Preview what would be done
python kdf_tools.py regenerate-all --dry-run

# Force regeneration even if cleanup fails
python kdf_tools.py regenerate-all --force
```

### Individual Commands with Auto-Cleanup
```bash
# Generate OpenAPI files with automatic cleanup
python kdf_tools.py openapi --version v2 --clean-before

# Generate Postman collections with automatic cleanup  
python kdf_tools.py postman --versions v2 --clean-before
```

### Manual Cleanup (if needed)
```bash
# Clean up all generated files
python kdf_tools.py cleanup-generated

# Preview cleanup without making changes
python kdf_tools.py cleanup-generated --dry-run

# Clean specific categories only
python kdf_tools.py cleanup-generated --categories openapi postman_collections

# Clean up stale files older than 7 days
python kdf_tools.py cleanup-stale
```

## What Gets Cleaned

### Categories
- **openapi**: OpenAPI YAML files and schemas (`openapi/paths`, `openapi/components/schemas`)  
- **postman_collections**: Postman collections and JSON examples (`postman/collections`, `postman/json`)
- **generated_data**: Generated mapping and data files (`utils/py/data`, `utils/js/data`)
- **search_indices**: Search index files (`utils/_searchIndex.json`, `utils/_fileData.json`)

### Preserved Files
- README files
- Template files  
- MDX/Markdown source files
- Configuration files (like `openapi/openapi.yaml`, `postman/NOTES.md`)

## Makefile Integration

```bash
# Use the integrated commands through Make
make tools-regenerate-all          # Complete regeneration
make tools-regenerate-all-dry      # Preview regeneration
make tools-openapi-clean           # OpenAPI with cleanup
make tools-postman-clean           # Postman with cleanup
```

## Benefits

1. **Prevents Stale Data Issues**: Automatically removes outdated generated files
2. **Integrated Workflow**: No need to remember separate cleanup commands
3. **Safe by Default**: Creates backups before cleaning (unless `--no-backup`)
4. **Granular Control**: Choose what to regenerate with skip flags
5. **Dry Run Support**: Preview changes before applying them

## Migration from Separate Scripts

If you were previously using separate cleanup scripts:
- Replace manual cleanup + generation with `regenerate-all`
- Add `--clean-before` flags to existing `openapi` and `postman` commands
- Use the new integrated Makefile targets 