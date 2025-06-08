#!/usr/bin/env python3
"""
Script to update OpenAPI YAML files with common schema structures.
This script will systematically process all v1 and v2 YAML files.
"""

import os
import re
import yaml
import glob
from pathlib import Path

def update_v1_file(file_path):
    """Update v1 file to use RpcV1Request structure and common types"""
    print(f"Processing V1: {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract method name from file
    method_name = Path(file_path).stem
    
    # Replace request body structure for v1
    old_request_pattern = r'''requestBody:
\s*(?:required: true\s*)?
\s*content:
\s*application/json:
\s*schema:
\s*type: object
\s*(?:required:
\s*- [^\n]*
\s*- [^\n]*
\s*)?properties:
\s*userpass:
\s*type: string
\s*description: [^\n]*
\s*method:
\s*type: string
\s*enum: \[[^\]]*\]
\s*description: [^\n]*'''
    
    new_request = f'''requestBody:
      required: true
      content:
        application/json:
          schema:
            allOf:
              - $ref: '../../../components/schemas/Common.yaml#/RpcV1Request'
              - type: object
                properties:
                  method:
                    type: string
                    enum: [{method_name}]
                    description: Method name'''
    
    # Apply request pattern replacement
    content = re.sub(old_request_pattern, new_request, content, flags=re.MULTILINE | re.DOTALL)
    
    # Replace common type patterns
    content = replace_common_types(content)
    
    # Add error responses if missing
    content = add_error_responses(content)
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)

def update_v2_file(file_path):
    """Update v2 file to use RpcV2Request structure and common types"""
    print(f"Processing V2: {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract method name from file
    method_name = Path(file_path).stem
    
    # Basic structure transformation for v2 - this is more complex, needs manual review
    # For now, just apply common type replacements and error responses
    content = replace_common_types(content)
    content = add_error_responses(content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def replace_common_types(content):
    """Replace common patterns with schema references"""
    
    # Replace coin ticker references
    content = re.sub(
        r'type:\s*string\s*\n(\s*)description:\s*.*(?:coin|ticker).*',
        r'$ref: ../../../components/schemas/Common.yaml#/CoinTicker\n\1description: Cryptocurrency ticker symbol',
        content,
        flags=re.IGNORECASE
    )
    
    # Replace trade action enums
    content = re.sub(
        r'type:\s*string\s*\n(\s*)enum:\s*\[buy,\s*sell\]',
        r'$ref: ../../../components/schemas/Common.yaml#/TradeAction',
        content
    )
    
    # Replace amount/volume fields with AmountString
    content = re.sub(
        r'type:\s*string\s*\n(\s*)description:\s*.*(?:amount|volume|price|balance).*',
        r'$ref: ../../../components/schemas/Common.yaml#/AmountString\n\1description: Amount as string to preserve precision',
        content,
        flags=re.IGNORECASE
    )
    
    # Add UUID format to UUID fields
    content = re.sub(
        r'type:\s*string\s*\n(\s*)description:\s*.*[Uu][Uu][Ii][Dd].*',
        r'type: string\n\1format: uuid\n\1description: UUID identifier',
        content
    )
    
    # Add Ethereum address pattern
    content = re.sub(
        r'type:\s*string\s*\n(\s*)description:\s*.*(?:address|contract).*(?:ethereum|eth|erc20).*',
        r'type: string\n\1pattern: "^0x[a-fA-F0-9]{40}$"\n\1description: Ethereum address',
        content,
        flags=re.IGNORECASE
    )
    
    # Add pubkey pattern
    content = re.sub(
        r'type:\s*string\s*\n(\s*)description:\s*.*pubkey.*',
        r'type: string\n\1pattern: "^[0-9a-fA-F]{66}$"\n\1description: Public key',
        content,
        flags=re.IGNORECASE
    )
    
    return content

def add_error_responses(content):
    """Add standard error responses if missing"""
    
    # Add 400 error response content
    if "'400':" in content and "content:" not in content[content.find("'400':"):content.find("'500':")]:
        content = content.replace(
            "'400':\n        description: Bad request",
            """'400':
        description: Bad request
        content:
          application/json:
            schema:
              $ref: '../../../components/schemas/Common.yaml#/RpcErrorResponse'"""
        )
    
    # Add 500 error response content
    if "'500':" in content and "content:" not in content[content.find("'500'"):]:
        content = content.replace(
            "'500':\n        description: Internal server error",
            """'500':
        description: Internal server error
        content:
          application/json:
            schema:
              $ref: '../../../components/schemas/Common.yaml#/RpcErrorResponse'"""
        )
    
    return content

def main():
    """Main function to process all YAML files systematically"""
    base_path = Path('postman/openapi/paths')
    
    # Process v1 files first
    v1_files = sorted(glob.glob('postman/openapi/paths/v1/*.yaml'))
    print(f"Found {len(v1_files)} v1 files to process")
    
    for file_path in v1_files:
        try:
            update_v1_file(file_path)
        except Exception as e:
            print(f"Error processing v1 {file_path}: {e}")
    
    # Process v2 files  
    v2_files = sorted(glob.glob('postman/openapi/paths/v2/*.yaml'))
    print(f"Found {len(v2_files)} v2 files to process")
    
    for file_path in v2_files:
        try:
            update_v2_file(file_path)
        except Exception as e:
            print(f"Error processing v2 {file_path}: {e}")
    
    print("Batch processing complete!")

if __name__ == "__main__":
    main() 