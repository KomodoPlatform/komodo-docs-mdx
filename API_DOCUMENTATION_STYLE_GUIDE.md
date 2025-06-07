# Komodo DeFi Framework API Documentation Style Guide

This document defines the formatting standards and conventions used in the Komodo DeFi Framework API documentation to ensure consistency, readability, and machine-parseability for OpenAPI specification generation.

## Table of Contents

- [Request Arguments Table Format](#request-arguments-table-format)
- [Column Alignment Standards](#column-alignment-standards)
- [Required/Optional Symbols](#requiredoptional-symbols)
- [Default Value Formatting](#default-value-formatting)
- [Enum System and Cross-References](#enum-system-and-cross-references)
- [Table Structure Guidelines](#table-structure-guidelines)
- [Examples](#examples)

## Request Arguments Table Format

### Standard Table Structure

All Request Arguments tables must follow this format:

```markdown
### Request Arguments

| Parameter | Type | Required | Default | Description |
| --------- | ---- | :------: | :-----: | ----------- |
| param1    | type |    ✓     |   `-`   | description |
| param2    | type |    ✗     | `value` | description |
```

### Required Columns

1. **Parameter** - Parameter name (use escaped underscores: `param\_name`)
2. **Type** - Data type (string, number, bool, object, etc.)
3. **Required** - Required/Optional indicator (see symbols below)
4. **Default** - Default value or `-` for no default
5. **Description** - Clear description with enum references where applicable

### Optional Default Column Rules

- **Include Default column** when parameters have actual default values
- **Omit Default column** when all parameters are required with no defaults (cleaner for OpenAPI parsing)
- **Use Required column only** for methods with no parameters: `| (none) | | - | |`

## Column Alignment Standards

### Alignment Syntax

- **Parameter, Type, Description**: Left-aligned (default)
- **Required**: Center-aligned using `:------:`
- **Default**: Center-aligned using `:-----:`

### Correct Alignment Example

```markdown
| Parameter | Type   | Required | Default | Description |
| --------- | ------ | :------: | :-----: | ----------- |
| coin      | string |    ✓     |   `-`   | description |
```

### Spacing Standards

- Use **5 spaces** for center-aligned content: `|     ✓    |`
- Consistent spacing ensures proper visual alignment

## Required/Optional Symbols

### Symbol Conventions

- **✓** - Required parameter
- **✗** - Optional parameter  
- **-** - Not applicable (for methods with no parameters)

### Usage Rules

- Always use symbols, never text like "Required" or "Optional"
- Center-align symbols in the Required column
- Use consistent spacing: 5 spaces before/after symbol

## Default Value Formatting

### Value Format Rules

1. **No default**: Use `-`
2. **String defaults**: Use backticks - `` `"value"` ``
3. **Boolean defaults**: Use backticks - `` `true` `` or `` `false` ``
4. **Numeric defaults**: Use backticks - `` `10` `` or `` `0.5` ``
5. **Special values**: Use backticks - `` `null` ``

### Examples

```markdown
| Parameter | Required | Default | Description |
| --------- | :------: | :-----: | ----------- |
| coin      |    ✓     |   `-`   | Required parameter |
| limit     |    ✗     |  `10`   | Optional with default |
| max       |    ✗     | `false` | Boolean with default |
| price     |    ✗     |   `-`   | Optional, no default |
```

## Enum System and Cross-References

### Enum Naming Convention

Enums in `common_structures/index.mdx` follow this pattern:
- Base name + "Enum" suffix
- Examples: `SwapMethodEnum`, `ActionEnum`, `OrderTypeEnum`

### Enum Definition Format

```markdown
### SwapMethodEnum

Used in [trade\_preimage](/komodo-defi-framework/api/legacy/trade_preimage/) method to specify the swap operation type:

| Value      | Description                                                  |
| ---------- | ------------------------------------------------------------ |
| `buy`      | Create a buy order (taker wants to receive the base coin)    |
| `sell`     | Create a sell order (taker wants to sell the base coin)      |
| `setprice` | Create a maker order (provide liquidity at a specific price) |
```

### Cross-Reference Format

When referencing enums in parameter descriptions:

```markdown
| swap_method | string | ✓ | - | A standard [SwapMethod](/komodo-defi-framework/api/common_structures/#swap-method-enum) enum. The name of the method whose preimage is requested. |
```

### Link Format Rules

- Use kebab-case for anchor links: `#swap-method-enum`
- Always include full path: `/komodo-defi-framework/api/common_structures/`
- Escape underscores in method names: `trade\_preimage`

## Table Structure Guidelines

### When to Include Default Column

**Include Default Column:**
```markdown
| Parameter | Type | Required | Default | Description |
| --------- | ---- | :------: | :-----: | ----------- |
| limit     | int  |    ✗     |  `10`   | Has default value |
| max       | bool |    ✗     | `false` | Has default value |
```

**Omit Default Column:**
```markdown
| Parameter | Type   | Required | Description |
| --------- | ------ | :------: | ----------- |
| coin      | string |    ✓     | Required parameter only |
| base      | string |    ✓     | Required parameter only |
```

### No Parameters Format

For methods with no parameters:

```markdown
| Parameter | Type | Required | Description |
| --------- | ---- | :------: | ----------- |
| (none)    |      |    -     |             |
```

## Examples

### Example 1: Mixed Required/Optional with Defaults

```markdown
### Request Arguments

| Parameter    | Type                       | Required | Default | Description |
| ------------ | -------------------------- | :------: | :-----: | ----------- |
| base         | string                     |     ✓    |   `-`   | The base currency of the request |
| rel          | string                     |     ✓    |   `-`   | The rel currency of the request |
| swap_method  | string                     |     ✓    |   `-`   | A standard [SwapMethod](/komodo-defi-framework/api/common_structures/#swap-method-enum) enum |
| volume       | numeric string or rational |     ✗    |   `-`   | The amount to trade (optional) |
| max          | bool                       |     ✗    | `false` | Whether to use maximum volume |
```

### Example 2: All Required Parameters (No Default Column)

```markdown
### Request Arguments

| Parameter | Type   | Required | Description |
| --------- | ------ | :------: | ----------- |
| pubkey    | string |     ✓    | The pubkey to ban |
| reason    | string |     ✓    | The reason for banning |
```

### Example 3: No Parameters

```markdown
### Request Arguments

| Parameter | Type | Required | Description |
| --------- | ---- | :------: | ----------- |
| (none)    |      |     -    |             |
```

### Example 4: Enum Reference

```markdown
| action | string | ✓ | - | A standard [Action](/komodo-defi-framework/api/common_structures/#action-enum) enum. Whether to `buy` or `sell` the selected coin |
```

## Benefits for OpenAPI Generation

This standardized format provides:

1. **Machine-readable parameter requirements** - Clear Required/Optional distinction
2. **Standardized default values** - Consistent format for automation
3. **Enum consolidation** - Centralized enum definitions reduce duplication
4. **Cross-reference system** - Links between methods and common structures
5. **Clean table structure** - Optimal for parsing into OpenAPI schemas
6. **Consistent spacing** - Proper visual alignment across all tables

## Validation Checklist

Before submitting API documentation updates, verify:

- [ ] Required/Default columns use center alignment (`:------:` and `:-----:`)
- [ ] Required column uses ✓/✗ symbols with 5-space padding
- [ ] Default values are in backticks or use `-` for no default
- [ ] Enum parameters reference common structures with proper links
- [ ] Underscores in parameter names are escaped (`param\_name`)
- [ ] Link anchors use kebab-case (`#swap-method-enum`)
- [ ] Default column omitted when all parameters required with no defaults
- [ ] Consistent spacing maintained across all tables

## Common Enums Available

Current standardized enums in `/komodo-defi-framework/api/common_structures/`:

- `SwapMethodEnum` - buy, sell, setprice
- `ActionEnum` - buy, sell  
- `OrderTypeEnum` - Maker, Taker
- `OrderStatusEnum` - Created, Updated, Fulfilled, Cancelled, etc.
- `UnbanTypeEnum` - All, Few
- `BanTypeEnum` - Manual, FailedSwap

Always check the common structures file for the latest available enums before creating new ones. 