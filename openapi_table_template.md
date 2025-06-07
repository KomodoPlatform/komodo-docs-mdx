# OpenAPI-Ready Table Templates for KDF API Documentation

## Template 1: Enhanced Parameter Table (Recommended)

### Request Parameters

| Parameter | Type | Required | Default | Format/Constraints | Example | Description |
| --------- | ---- | -------- | ------- | ------------------ | ------- | ----------- |
| chain | `string` | ✓ | - | `enum: [AVALANCHE, BSC, ETH, FANTOM, POLYGON]` | `"ETH"` | The blockchain network |
| token_address | `string` | ✓ | - | `format: hex`, `pattern: ^0x[a-fA-F0-9]{40}$` | `"0x2953399124f0cbb46d2cbacd8a89cf0599974963"` | Token contract address |
| token_id | `string` | ✓ | - | `minLength: 1`, `maxLength: 78` | `"214300044414"` | Unique token identifier |
| protect_from_spam | `boolean` | ✗ | `false` | - | `true` | Replace potential spam URLs with protection message |
| limit | `integer` | ✗ | `10` | `minimum: 1`, `maximum: 100` | `25` | Number of items per page |
| page_number | `integer` | ✗ | `1` | `minimum: 1` | `2` | Page offset for pagination |
| amount | `string` | ✗ | - | `format: decimal`, `pattern: ^[0-9]+(\.[0-9]+)?$` | `"1.5"` | Amount in decimal format |
| timestamp | `string` | ✗ | - | `format: date-time` | `"2023-09-01T04:04:30.867Z"` | ISO 8601 timestamp |

### Response Parameters

| Parameter | Type | Required | Nullable | Format/Constraints | Example | Description |
| --------- | ---- | -------- | -------- | ------------------ | ------- | ----------- |
| token_address | `string` | ✓ | ✗ | `format: hex`, `pattern: ^0x[a-fA-F0-9]{40}$` | `"0x2953399124f0cbb46d2cbacd8a89cf0599974963"` | Token contract address |
| amount | `string` | ✓ | ✗ | `format: decimal` | `"1"` | Token amount owned |
| block_number | `integer` | ✓ | ✗ | `format: int64`, `minimum: 0` | `45776404` | Block height |
| block_number_minted | `integer` | ✗ | ✓ | `format: int64`, `minimum: 0` | `19645247` | Block when NFT was minted |
| name | `string` | ✗ | ✓ | `maxLength: 255` | `"OpenSea Collections"` | NFT collection name |
| contract_type | `string` | ✓ | ✗ | `enum: [ERC721, ERC1155]` | `"ERC1155"` | NFT contract standard |
| possible_spam | `boolean` | ✓ | ✗ | - | `true` | Spam detection flag |
| token_uri | `string` | ✗ | ✓ | `format: uri`, `maxLength: 2048` | `"https://api.opensea.io/..."` | Metadata URI |
| uri_meta | `object` | ✗ | ✓ | `$ref: #/components/schemas/NftMetadata` | `{...}` | NFT metadata object |

---

## Template 2: Compact Format with Inline Metadata

### Request Parameters

| Parameter | Type | Spec | Description |
| --------- | ---- | ---- | ----------- |
| chain | `string` | **Required** • `enum: [AVALANCHE, BSC, ETH, FANTOM, POLYGON]` | The blockchain network |
| token_address | `string` | **Required** • `hex40` • `^0x[a-fA-F0-9]{40}$` | Token contract address |
| token_id | `string` | **Required** • `minLength: 1` • `maxLength: 78` | Unique token identifier |
| protect_from_spam | `boolean` | *Optional* • `default: false` | Replace spam URLs with protection message |
| limit | `integer` | *Optional* • `default: 10` • `min: 1` • `max: 100` | Number of items per page |

### Response Parameters

| Parameter | Type | Spec | Description |
| --------- | ---- | ---- | ----------- |
| token_address | `string` | **Required** • `hex40` | Token contract address |
| amount | `string` | **Required** • `decimal` | Token amount owned |
| block_number | `integer` | **Required** • `int64` • `min: 0` | Block height |
| name | `string` | *Optional* • **nullable** • `maxLength: 255` | NFT collection name |
| contract_type | `string` | **Required** • `enum: [ERC721, ERC1155]` | Contract standard |
| uri_meta | `object` | *Optional* • **nullable** • `→ NftMetadata` | Metadata object |

---

## Template 3: YAML Frontmatter + Enhanced Tables

```yaml
---
openapi:
  operationId: get_nft_metadata
  tags: [NFT]
  summary: Get NFT metadata
  description: Retrieves metadata for a specific NFT
  method: POST
  path: /
  requestBody:
    required: true
    content:
      application/json:
        schema:
          type: object
          required: [userpass, method, mmrpc, params]
  responses:
    '200':
      description: NFT metadata retrieved successfully
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/GetNftMetadataResponse'
---
```

### Request Parameters (`params` object)

| Parameter | Type | Required | Constraints | Description |
| --------- | ---- | :------: | ----------- | ----------- |
| chain | `string` | ✓ | `AVALANCHE \| BSC \| ETH \| FANTOM \| POLYGON` | Blockchain network |
| token_address | `string` | ✓ | `/^0x[a-fA-F0-9]{40}$/` | Token contract address |
| token_id | `string` | ✓ | `length: 1-78` | Token identifier |
| protect_from_spam | `boolean` | ✗ | `default: false` | Spam protection flag |

---

## Template 4: Schema-First Approach

### Schema Definition
```json
{
  "GetNftMetadataRequest": {
    "type": "object",
    "required": ["chain", "token_address", "token_id"],
    "properties": {
      "chain": {
        "type": "string",
        "enum": ["AVALANCHE", "BSC", "ETH", "FANTOM", "POLYGON"],
        "description": "The blockchain network"
      },
      "token_address": {
        "type": "string",
        "pattern": "^0x[a-fA-F0-9]{40}$",
        "description": "Token contract address"
      },
      "token_id": {
        "type": "string",
        "minLength": 1,
        "maxLength": 78,
        "description": "Unique token identifier"
      },
      "protect_from_spam": {
        "type": "boolean",
        "default": false,
        "description": "Replace potential spam URLs"
      }
    }
  }
}
```

### Human-Readable Table

| Parameter | Schema Path | Description |
| --------- | ----------- | ----------- |
| chain | `GetNftMetadataRequest.properties.chain` | The blockchain network (required) |
| token_address | `GetNftMetadataRequest.properties.token_address` | Token contract address (required) |
| token_id | `GetNftMetadataRequest.properties.token_id` | Unique token identifier (required) |
| protect_from_spam | `GetNftMetadataRequest.properties.protect_from_spam` | Replace potential spam URLs (optional) |

---

## Template 5: Annotation-Based Approach

### Request Parameters

<!-- openapi:component:GetNftMetadataParams -->
| Parameter | Type | Required | Validation | Description |
| --------- | ---- | :------: | ---------- | ----------- |
| chain | `string` | ✓ | `@enum(AVALANCHE,BSC,ETH,FANTOM,POLYGON)` | The blockchain network |
| token_address | `string` | ✓ | `@pattern(^0x[a-fA-F0-9]{40}$)` `@format(hex)` | Token contract address |
| token_id | `string` | ✓ | `@minLength(1)` `@maxLength(78)` | Unique token identifier |
| protect_from_spam | `boolean` | ✗ | `@default(false)` | Replace potential spam URLs |
<!-- /openapi -->

---

## Legend & Conventions

### Symbols Used
- ✓ = Required parameter
- ✗ = Optional parameter  
- **nullable** = Can be null
- `→ SchemaName` = Reference to schema object

### Type Formats
- `hex40` = 40-character hexadecimal string (0x + 38 chars)
- `decimal` = Decimal number as string
- `int64` = 64-bit integer
- `date-time` = ISO 8601 datetime
- `uri` = Valid URI format

### Constraint Formats
- `enum: [A, B, C]` = Enumerated values
- `pattern: regex` = Regular expression pattern
- `min/max: N` = Numeric range
- `minLength/maxLength: N` = String length
- `format: type` = OpenAPI format specifier

---

## Conversion Script Targets

This template structure enables:

1. **Direct OpenAPI Schema Generation**
2. **Validation Rule Extraction** 
3. **Example Generation**
4. **Type Safety Checking**
5. **Documentation Consistency**
6. **Automated Testing**

Each approach has trade-offs between:
- **Readability** vs **Machine Parseability**
- **Maintenance Overhead** vs **Automation Benefits**
- **Backward Compatibility** vs **Enhanced Features** 