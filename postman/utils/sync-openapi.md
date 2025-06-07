# OpenAPI Synchronization Strategy

## Overview
This document outlines strategies for keeping OpenAPI specifications synchronized with MDX documentation updates in the Komodo DeFi Framework documentation.

## Approach 1: Automated GitHub Actions Pipeline (Recommended)

### Setup
Create `.github/workflows/sync-openapi.yml`:

```yaml
name: Sync OpenAPI Specs
on:
  push:
    paths:
      - 'src/pages/komodo-defi-framework/api/**/*.mdx'
  pull_request:
    paths:
      - 'src/pages/komodo-defi-framework/api/**/*.mdx'

jobs:
  sync-openapi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.x'
          
      - name: Update method mappings
        run: |
          cd postman/utils
          python map_mdx_methods.py
          
      - name: Check for new/updated methods
        run: |
          # Compare method_pages.json with previous version
          # Detect new methods or changed MDX files
          
      - name: Generate OpenAPI specs
        run: |
          # Run automated OpenAPI generation script
          # (to be created based on the manual process)
          
      - name: Create PR for OpenAPI updates
        if: github.event_name == 'push'
        uses: peter-evans/create-pull-request@v5
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "Auto-update OpenAPI specs for modified MDX files"
          title: "🤖 Auto-generated OpenAPI updates"
          body: |
            Automatically generated OpenAPI specification updates based on MDX documentation changes.
            
            Please review the generated specs for accuracy before merging.
```

### Benefits
- Automatic detection of MDX changes
- Generates draft OpenAPI specs
- Creates PR for human review
- Maintains quality control

## Approach 2: Development Workflow Integration

### Pre-commit Hooks
Add to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: update-method-mappings
        name: Update method mappings
        entry: python postman/utils/map_mdx_methods.py
        language: system
        files: 'src/pages/komodo-defi-framework/api/.*\.mdx$'
        
      - id: validate-openapi-sync
        name: Validate OpenAPI sync status
        entry: python postman/utils/validate_sync.py
        language: system
        files: 'src/pages/komodo-defi-framework/api/.*\.mdx$'
```

### Developer Checklist
When updating MDX documentation:

1. **Update documentation** in `src/pages/komodo-defi-framework/api/`
2. **Run method mapping update**: `cd postman/utils && python map_mdx_methods.py`
3. **Check for new methods**: Review `method_pages.json` diff
4. **Generate/update OpenAPI specs** for affected methods
5. **Test OpenAPI validity**: Use OpenAPI validation tools
6. **Commit both MDX and OpenAPI changes** together

## Approach 3: Automated Generation Script

### Create Generation Tool
`postman/utils/generate_openapi.py`:

```python
#!/usr/bin/env python3
"""
Automated OpenAPI specification generator from MDX documentation.
"""
import json
import os
import sys
from pathlib import Path

def load_method_mappings():
    """Load method to MDX file mappings."""
    with open('method_pages.json', 'r') as f:
        return json.load(f)

def detect_changed_methods(since_commit='HEAD~1'):
    """Detect which methods have changed MDX files."""
    # Use git to detect changed MDX files
    # Map back to methods using method_pages.json
    pass

def generate_openapi_for_method(method_name, mdx_path, version):
    """Generate OpenAPI spec for a single method."""
    # Parse MDX file
    # Extract parameters, responses, examples
    # Generate OpenAPI YAML
    # Use LLM API or template-based generation
    pass

def main():
    if len(sys.argv) > 1:
        # Generate for specific methods
        methods = sys.argv[1:]
    else:
        # Generate for all changed methods
        methods = detect_changed_methods()
    
    for method in methods:
        # Generate OpenAPI spec
        pass

if __name__ == '__main__':
    main()
```

### Usage
```bash
# Generate for specific methods
python generate_openapi.py enable_eth withdraw

# Generate for all changed methods since last commit
python generate_openapi.py

# Generate for methods in specific MDX files
python generate_openapi.py --files src/pages/.../enable_eth/index.mdx
```

## Approach 4: Validation and Quality Assurance

### Validation Script
`postman/utils/validate_sync.py`:

```python
#!/usr/bin/env python3
"""
Validate that OpenAPI specs are in sync with MDX documentation.
"""

def validate_all_methods_have_specs():
    """Check that every method in method_pages.json has an OpenAPI spec."""
    pass

def validate_openapi_syntax():
    """Validate OpenAPI YAML syntax."""
    pass

def validate_examples_match():
    """Check that examples in OpenAPI match MDX examples."""
    pass

def check_missing_specs():
    """Report methods without OpenAPI specs."""
    pass
```

## Recommended Workflow

### For New Methods
1. **Write MDX documentation** with complete examples
2. **Run mapping update**: `python map_mdx_methods.py`
3. **Generate OpenAPI spec**: Use AI assistant or generation tool
4. **Validate**: Check syntax and completeness
5. **Commit together**: MDX + OpenAPI in same commit

### For Updated Methods
1. **Update MDX documentation**
2. **Identify affected OpenAPI specs**
3. **Update OpenAPI specs** accordingly
4. **Validate changes**
5. **Commit together**

### For Large-scale Updates
1. **Use CI/CD pipeline** for automated detection
2. **Generate draft OpenAPI specs** automatically
3. **Human review** for quality and accuracy
4. **Merge after approval**

## Quality Checklist

- [ ] All parameters extracted correctly
- [ ] Response schemas match examples
- [ ] Error handling comprehensive
- [ ] Schema references used where applicable
- [ ] Examples are realistic and valid
- [ ] `x-mdx-doc-path` correctly set
- [ ] OpenAPI syntax valid
- [ ] No missing required fields

## Tools and Dependencies

- **OpenAPI Validator**: For syntax checking
- **JSON Schema Validator**: For response validation
- **Git hooks**: For workflow integration
- **GitHub Actions**: For automation
- **Python scripts**: For generation and validation

## Future Enhancements

1. **LLM Integration**: Use AI for more sophisticated generation
2. **Schema Evolution**: Track breaking changes
3. **Documentation Versioning**: Handle API version changes
4. **Integration Testing**: Validate against actual API responses
5. **Performance Monitoring**: Track generation and validation times 