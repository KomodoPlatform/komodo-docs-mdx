# MDX Example Standards for Komodo DeFi Framework API

## Overview
This document establishes standards for JSON examples in MDX documentation to prevent duplication and ensure consistency.

## ✅ Example Standards

### 1. **One Unique Example Per Use Case**
- Each example should demonstrate a **distinct use case or parameter variation**
- Avoid creating multiple examples with identical content
- If examples are identical, consolidate into a single representative example

### 2. **Meaningful Example Names**
Use descriptive names that reflect the actual content:

✅ **Good:**
```markdown
## Example: BTC Electrum Activation
```

❌ **Bad:**
```markdown
## Example 1
## Example 2  
## Example 3  
```

### 3. **Content-Based Variation**
Only create multiple examples when they demonstrate:
- **Different parameter values** (different coins, networks, etc.)
- **Different activation modes** (electrum vs native)
- **Different hardware wallet flows** (Trezor PIN entry vs confirmation)
- **Different error scenarios**

### 4. **Example Structure**
```markdown
## Example: [Descriptive Name]

Brief description of what this example demonstrates.

### Request
```json
{
  // JSON example here
}
```

### Response
```json
{
  // Expected response
}
```
```

## ❌ Anti-Patterns to Avoid

### 1. **Identical Content with Different Numbers**
```markdown
❌ Example 1: task_operation
❌ Example 2: task_operation  
❌ Example 3: task_operation
```
All with identical JSON content.

### 2. **Meaningless Variations**
```markdown
❌ Example: BTC activation (task_id: 1)
❌ Example: BTC activation (task_id: 2)
❌ Example: BTC activation (task_id: 3)
```
Unless the task_id difference is semantically meaningful.

### 3. **Numbered Examples Without Purpose**
Only use numbered examples when there's a logical sequence or distinct variations.

## ✅ Best Practices

### 1. **Consolidation Over Multiplication**
- Prefer **one comprehensive example** over multiple identical ones
- Use **inline comments** to explain variations
- Create **separate examples** only for distinct scenarios

### 2. **Semantic Example Names**
- `btc_electrum_activation` ✅
- `eth_native_mode` ✅ 
- `trezor_pin_entry` ✅
- `basic_request` ❌ (too generic)

### 3. **Parameter Documentation**
Instead of multiple examples, document parameter variations:

```markdown
## Example: Coin Activation

This example shows basic coin activation. Key parameters:
- `ticker`: Can be "BTC", "ETH", "KMD", etc.
- `mode`: "Electrum" or "Native"
- `servers`: Required for Electrum mode

```json
{
  "method": "task::enable_utxo::init",
  "params": {
    "ticker": "BTC",  // ← Can be any supported coin
    "activation_params": {
      "mode": {
        "rpc": "Electrum",  // ← Or "Native"
        "rpc_data": {
          "servers": [...]  // ← Required for Electrum
        }
      }
    }
  }
}
```
```

### 4. **Content Validation**
Before adding new examples:
1. **Check existing examples** for similar content
2. **Identify unique value** the new example provides
3. **Consolidate or differentiate** as appropriate

## 🔧 Implementation

### 1. **Review Process**
- Before committing new examples, run the deduplication script:
  ```bash
  cd utils/py
  python3 deduplicate_examples.py --dry-run
  ```

### 2. **Automated Checks**
- Use the deduplication script in CI/CD pipelines
- Alert on high duplicate ratios (>10% duplicates)

### 3. **Documentation Updates**
- Update existing MDX files to follow these standards
- Consolidate identical examples during routine maintenance

## 🎯 Goals

1. **Reduce maintenance burden** - fewer files to update
2. **Improve user experience** - clearer, more focused examples  
3. **Prevent storage waste** - eliminate redundant content
4. **Enhance clarity** - each example serves a clear purpose

## 📚 Related Tools

- `utils/py/deduplicate_examples.py` - Remove duplicate JSON files
- `utils/py/api_example_manager.py` - Extract and manage examples
- Content-based deduplication prevents future duplicates

---

**Remember:** Quality over quantity. One clear, well-documented example is better than ten identical ones. 