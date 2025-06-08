# Komodo Developer Docs Content

Content for the Komodo Developer Docs lives in this repo in `.mdx` format. This repository is then used as a submodule to build and deploy the Komodo Developer Docs website.

## Adding new content

- Read the [Style guide](STYLE_GUIDE.md) to learn the basic standards of writing Komodo Documentation content. This guide also contains a list of components and how they should be used.
- Read the [Contribution guide](CONTRIBUTION_GUIDE.md) for details about submitting a pull request.
- Make sure each new page created is added to the [sidebar file](https://github.com/KomodoPlatform/komodo-docs-mdx/blob/main/src/data/sidebar.json)
- Be mindful of the [Code of Conduct](CODE_OF_CONDUCT.md) when contributing to this repository. We value all contributors and believe that our community is stronger when everyone feels safe, respected, and valued.

## JSON Example Structure

API method examples are organized using a standardized two-level directory structure for consistency and automation compatibility:

### Structure Convention

```
postman/json/kdf/
├── v1/                                    # Legacy API examples
└── v2/                                    # Current API examples
    ├── task-enable-utxo/                  # Task-based methods
    │   ├── init/                          # Specific operations
    │   │   ├── example-1-trezor-mode-request.json
    │   │   └── example-1-trezor-mode-response.json
    │   ├── status/
    │   ├── cancel/
    │   └── user-action/
    ├── my_balance/                        # Simple methods
    │   └── default/                       # Standard operation folder
    │       ├── example-1-basic-request.json
    │       └── example-1-basic-response.json
    └── orderbook/
        └── default/
```

### Naming Conventions

**Method Directories:**
- Use kebab-case: `task-enable-utxo`, `my_balance`, `orderbook`
- Convert to API method names: `task-enable-utxo` → `task::enable_utxo`

**Operation Directories:**
- **Task methods**: Use actual operations (`init`, `status`, `cancel`, `user_action`)
- **Simple methods**: Use `default` as the operation name
- Replace hyphens with underscores: `user-action` → `user_action`

**Example Files:**
- Format: `example-{number}-{description}-{type}.json`
- Types: `request`, `response`
- Examples: `example-1-trezor-mode-request.json`, `example-2-success-response.json`

### Rationale

This standardized structure provides:

1. **Consistency**: All methods follow the same `method/operation/` pattern
2. **Automation**: Scanning and tooling can rely on predictable structure  
3. **Scalability**: Easy to add new operations or examples to any method
4. **Integration**: Compatible with Postman, Newman, and other API testing tools
5. **Documentation**: Clear separation between different method operations and examples

### Adding Examples

When adding new JSON examples:

1. Create the method directory using kebab-case naming
2. Create appropriate operation subdirectories (`init`/`status`/etc. for tasks, `default` for simple methods)
3. Add request/response pairs with descriptive names
4. Run the mapping script to update the unified documentation: `python utils/py/mapping.py --mapping-only`
