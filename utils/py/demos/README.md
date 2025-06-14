# Demo Scripts and Examples

This directory contains demonstration scripts and migration tools for the Komodo DeFi Framework documentation utilities.

## Scripts

### 🗂️  `demo_nested_structure.py`
**Purpose**: Demonstrates and tests the nested directory structure functionality.

**Usage:**
```bash
# Full demo (shows all functionality)
python demos/demo_nested_structure.py

# Quick validation check
python demos/demo_nested_structure.py --validate

# Just test path mappings
python demos/demo_nested_structure.py --test-only
```

**What it does:**
- Tests path mapping logic
- Compares flat vs nested structures  
- Validates configuration setup
- Helps debug path resolution issues

### 🔄 `migrate_to_nested_structure.py`
**Purpose**: Migration tool for converting from flat to nested directory structures.

**Usage:**
```bash
# See what would be done (dry run)
python demos/migrate_to_nested_structure.py --dry-run

# Perform the migration
python demos/migrate_to_nested_structure.py --migrate

# Rollback to flat structure
python demos/migrate_to_nested_structure.py --rollback
```

**What it does:**
- Analyzes current file structure
- Plans migration from flat to nested layout
- Moves OpenAPI and Postman files to organized structure
- Validates migration results

### 🚀 `repository_integration_example.py`
**Purpose**: Demonstrates integration between repository scanner and other library components.

**Usage:**
```bash
python demos/repository_integration_example.py
```

**What it does:**
- Shows how to use KDFRepositoryScanner
- Demonstrates component integration
- Provides example workflow patterns

## Running from Root Directory

All scripts can be run from the `utils/py/` directory:

```bash
cd utils/py
python demos/demo_nested_structure.py --validate
python demos/migrate_to_nested_structure.py --dry-run
python demos/repository_integration_example.py
```

## Import Notes

These scripts automatically adjust their import paths to work from the `demos/` subdirectory. The import path resolution looks for the `lib/` directory at `../lib/` relative to the script location. 