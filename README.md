# Komodo Developer Docs Content

Content for the Komodo Developer Docs lives in this repo in `.mdx` format. This repository is then used as a submodule to build and deploy the Komodo Developer Docs website.

## Adding new content

- Read the [Style guide](STYLE_GUIDE.md) to learn the basic standards of writing Komodo Documentation content. This guide also contains a list of components and how they should be used.
- Read the [Contribution guide](CONTRIBUTION_GUIDE.md) for details about submitting a pull request.
- Make sure each new page created is added to the [sidebar file](https://github.com/KomodoPlatform/komodo-docs-mdx/blob/main/src/data/sidebar.json)
- Be mindful of the [Code of Conduct](CODE_OF_CONDUCT.md) when contributing to this repository. We value all contributors and believe that our community is stronger when everyone feels safe, respected, and valued.

## JSON Example Structure

API method examples are organized using a simplified **1:1 method:folder** structure for maximum clarity and ease of management:

### Structure Convention

```
postman/json/kdf/
├── v1/                                    # Legacy API examples
└── v2/                                    # Current API examples
    ├── task-enable_utxo-init/             # Task-based methods (with operation in name)
    │   ├── task-enable_utxo-init-example-1-electrum_mode-request.json
    │   ├── task-enable_utxo-init-example-2-native_mode-request.json
    │   └── task-enable_utxo-init-example-3-kmd_electrum_activation-request.json
    ├── my_balance/                        # Simple methods
    │   ├── my_balance-example-1-basic_request-request.json
    │   └── my_balance-example-2-coin_operation-request.json
    └── orderbook/                         # Trading methods
        ├── orderbook-example-1-basic_request-request.json
        └── orderbook-example-2-btc_kmd_trade-request.json
```

### Naming Conventions

**Method Directories:**
- Use kebab-case with underscores preserved: `task-enable_utxo-init`, `my_balance`, `orderbook`
- Convert filesystem-safe hyphens back to API format: `task-enable_utxo-init` → `task::enable_utxo::init`

**Example Files:**
- Format: `{method-name}-example-{number}-{description}-{type}.json`
- Types: `request`, `response`
- Examples: 
  - `task-enable_utxo-init-example-1-electrum_mode-request.json`
  - `my_balance-example-1-basic_request-request.json`
  - `orderbook-example-2-btc_kmd_trade-request.json`

### Rationale

This simplified structure provides:

1. **Simplicity**: One method = one folder, no confusing operation subfolders
2. **Consistency**: All methods follow the same flat `method/` pattern
3. **Clarity**: Method name is clearly visible in both folder and file names
4. **Maintainability**: No duplicate operations or complex folder hierarchies
5. **Automation**: Scanning and tooling work with predictable flat structure
6. **Integration**: Compatible with Postman, Newman, and other API testing tools

### Adding Examples

When adding new JSON examples:

1. Create the method directory using kebab-case naming (preserve underscores, replace `::` with `-`)
2. Add request/response files directly in the method folder with descriptive names
3. Use the format: `{method-name}-example-{number}-{description}-{type}.json`
4. Run the mapping script to update the unified documentation: `python utils/py/api_example_manager.py`

### API Example Manager

The `utils/py/api_example_manager.py` script helps manage the JSON examples:

- **Extract examples**: Automatically extracts examples from MDX documentation
- **Generate variations**: Creates additional test cases for comprehensive coverage
- **Flatten structure**: Use `--consolidate` to move files from old operation subfolders to the new flat structure
- **Maintain consistency**: Ensures all examples follow the naming conventions
