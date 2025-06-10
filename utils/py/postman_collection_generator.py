#!/usr/bin/env python3
"""
Postman Collection Generator

This script generates comprehensive Postman collections from our organized JSON examples.
It creates production-ready collections with proper folder organization, environment variables,
test scripts, and documentation links.
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from mapping import MethodMapper

DATA_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')

@dataclass
class PostmanRequest:
    """Represents a Postman request with all metadata."""
    name: str
    method: str
    url: str
    headers: List[Dict[str, str]]
    body: Dict[str, Any]
    description: str
    tests: str
    method_name: str
    operation: str
    example_description: str


@dataclass
class PostmanFolder:
    """Represents a Postman folder containing related requests."""
    name: str
    description: str
    requests: List[PostmanRequest]
    subfolders: List['PostmanFolder']


class PostmanCollectionGenerator:
    """
    Generates Postman collections from organized JSON examples.
    Creates comprehensive collections with proper organization and testing.
    """
    
    def __init__(self, base_path: str = ".", verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        self.mapper = MethodMapper(base_path, verbose)
        self.json_dirs = {
            'v1': '../../postman/json/kdf/v1',
            'v2': '../../postman/json/kdf/v2',
        }
        self.output_dir = "../../postman/collections"
        
        # Method categorization for folder organization
        self.method_categories = {
            'activation': {
                'name': 'Coin & Token Activation',
                'description': 'Methods for activating coins, tokens, and blockchain protocols',
                'patterns': ['enable', 'activation', 'task::enable']
            },
            'lightning': {
                'name': 'Lightning Network',
                'description': 'Lightning Network channel and payment management',
                'patterns': ['lightning::', 'task::enable_lightning']
            },
            'trading': {
                'name': 'Trading & Orders',
                'description': 'Order placement, trading, and market operations',
                'patterns': ['buy', 'sell', 'setprice', 'cancel_order', 'orderbook', 'trade', 'swap', 'best_orders']
            },
            'wallet': {
                'name': 'Wallet Management',
                'description': 'Wallet operations, balances, and transaction management',
                'patterns': ['balance', 'withdraw', 'my_tx_history', 'get_wallet', 'get_public_key']
            },
            'streaming': {
                'name': 'Real-time Streaming',
                'description': 'WebSocket streaming endpoints for real-time data',
                'patterns': ['stream::']
            },
            'tasks': {
                'name': 'Task Management',
                'description': 'Asynchronous task operations and status monitoring',
                'patterns': ['task::', 'init', 'status', 'cancel', 'user_action']
            },
            'utility': {
                'name': 'Utility & Information',
                'description': 'General utility methods and system information',
                'patterns': ['version', 'metrics', 'get_', 'convert', 'sign_', 'verify_']
            }
        }
    
    def categorize_method(self, method_name: str) -> str:
        """Categorize a method based on its name patterns."""
        method_lower = method_name.lower()
        
        # Check each category's patterns
        for category, config in self.method_categories.items():
            for pattern in config['patterns']:
                if pattern.lower() in method_lower:
                    return category
        
        return 'utility'  # Default category
    
    def scan_json_examples(self, version: str) -> Dict[str, List[PostmanRequest]]:
        """
        Scan JSON examples and convert them to PostmanRequest objects.
        Returns dict organized by method categories.
        """
        if version not in self.json_dirs:
            raise ValueError(f"Unsupported version: {version}")
        
        base_dir = self.json_dirs[version]
        if not os.path.exists(base_dir):
            if self.verbose:
                print(f"Warning: Examples directory {base_dir} does not exist")
            return {}
        
        categorized_requests = {category: [] for category in self.method_categories.keys()}
        
        # Walk through the organized structure
        for method_dir in os.listdir(base_dir):
            method_path = os.path.join(base_dir, method_dir)
            if not os.path.isdir(method_path):
                continue
            
            method_name = method_dir.replace('-', '::')
            category = self.categorize_method(method_name)
            
            # Process each operation directory
            for operation_dir in os.listdir(method_path):
                operation_path = os.path.join(method_path, operation_dir)
                if not os.path.isdir(operation_path):
                    continue
                
                operation = operation_dir
                
                # Process each JSON example file
                for json_file in os.listdir(operation_path):
                    if not json_file.endswith('.json'):
                        continue
                    
                    json_path = os.path.join(operation_path, json_file)
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        
                        # Skip if no method field (likely a response)
                        if 'method' not in json_data:
                            continue
                        
                        # Extract description from filename
                        # Format: method-operation-example-1-description-request.json
                        parts = json_file.replace('.json', '').split('-')
                        if len(parts) >= 5:
                            example_description = parts[-2]  # description part
                        else:
                            example_description = "basic_request"
                        
                        # Validate that the JSON method matches the expected operation
                        json_method = json_data.get('method', '')
                        if self._validate_method_operation_match(json_method, method_name, operation) and \
                           self._validate_content_for_operation(json_data, operation):
                            # Create PostmanRequest
                            request = self.create_postman_request(
                                json_data, method_name, operation, example_description, version
                            )
                            
                            if request:
                                categorized_requests[category].append(request)
                        else:
                            # Skip mismatched files instead of just warning
                            if self.verbose:
                                content_valid = self._validate_content_for_operation(json_data, operation)
                                method_valid = self._validate_method_operation_match(json_method, method_name, operation)
                                
                                print(f"Skipping mismatched file: {json_path}")
                                print(f"  Expected: {method_name} with operation '{operation}'")
                                print(f"  Found: {json_method}")
                                print(f"  Method valid: {method_valid}, Content valid: {content_valid}")
                                if not content_valid and operation == 'status':
                                    print(f"  Issue: Status method has activation_params (should only have task_id)")
                                print(f"  This prevents data corruption")
                            continue
                            
                    except Exception as e:
                        if self.verbose:
                            print(f"Error processing {json_path}: {e}")
        
        return categorized_requests
    
    def _validate_method_operation_match(self, json_method: str, method_name: str, operation: str) -> bool:
        """Validate that JSON method matches the expected method and operation."""
        # For 'default' operations, the JSON method should match the base method name
        # 'default' is only a folder organization convention, not part of the method name
        if operation == 'default':
            # For default operations, JSON method should match method_name exactly
            # e.g. directory "stream-disable" -> method_name "stream::disable" -> expect JSON "stream::disable"
            return json_method == method_name
        
        # For specific operations (init, status, cancel, user_action), 
        # the JSON method should include the operation
        base_method = method_name.replace('::', '-')
        
        # Expected patterns for methods with specific operations
        expected_patterns = [
            f"{base_method}-{operation}",  # e.g. task-enable_bch-status
            json_method  # Allow exact matches
        ]
        
        return any(pattern == json_method for pattern in expected_patterns)
    
    def _validate_content_for_operation(self, json_data: Dict[str, Any], operation: str) -> bool:
        """Validate that the content is appropriate for the operation type."""
        params = json_data.get('params', {})
        
        if operation == 'status':
            # Status operations should have task_id, NOT activation_params
            if 'activation_params' in params:
                return False
            # Status should typically have task_id (though some might have other simple params)
            return True
        
        elif operation == 'init':
            # Init operations typically have activation_params or other complex setup
            return True
        
        elif operation in ['cancel', 'user_action']:
            # These typically have task_id or simple parameters
            if 'activation_params' in params:
                return False
            return True
        
        # For default operations, allow all content
        return True
    
    def create_postman_request(self, json_data: Dict[str, Any], method_name: str, 
                              operation: str, example_description: str, version: str) -> Optional[PostmanRequest]:
        """Create a PostmanRequest from JSON data."""
        if 'method' not in json_data:
            return None
        
        api_method = json_data['method']
        
        # Generate request name - avoid duplication
        clean_description = example_description.replace('_', ' ').title()
        
        # For 'default' operations, just use the API method name
        # For specific operations, the API method already includes the operation
        request_name = f"{api_method} - {clean_description}"
        
        # Generate URL using kdf_url (includes IP/domain and port)
        url = f"{{{{kdf_url}}}}"
        
        # Standard headers
        headers = [
            {"key": "Content-Type", "value": "application/json"},
            {"key": "Accept", "value": "application/json"}
        ]
        
        # Template the JSON body with Postman variables
        templated_body = self.template_json_body(json_data)
        
        # Generate description with documentation links
        description = self.generate_request_description(api_method, method_name, operation, version)
        
        # Generate test script
        test_script = self.generate_test_script(api_method)
        
        return PostmanRequest(
            name=request_name,
            method="POST",  # KDF API uses POST for all requests
            url=url,
            headers=headers,
            body=templated_body,
            description=description,
            tests=test_script,
            method_name=method_name,
            operation=operation,
            example_description=example_description
        )
    
    def template_json_body(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Template JSON request body with Postman variables."""
        # Create a deep copy to avoid modifying the original
        templated = json.loads(json.dumps(json_data))
        
        # Always ensure userpass is templated
        templated["userpass"] = "{{userpass}}"
        
        # Template common coin parameters if they exist
        if "coin" in templated:
            templated["coin"] = "{{coin}}"
        
        # Template trading pair parameters
        if "base" in templated:
            templated["base"] = "{{base}}"
        if "rel" in templated:
            templated["rel"] = "{{rel}}"
            
        # Template amount parameters
        if "amount" in templated:
            templated["amount"] = "{{amount}}"
        if "max_volume" in templated:
            templated["max_volume"] = "{{amount}}"
            
        # Template fee parameters
        if "fee" in templated:
            templated["fee"] = "{{fee}}"
            
        # Template task IDs for task-based methods
        if "task_id" in templated:
            method = templated.get("method", "")
            if "enable_utxo" in method:
                templated["task_id"] = "{{enable_utxo_taskid}}"
            elif "withdraw" in method:
                templated["task_id"] = "{{init_withdraw_taskid}}"
            elif "scan_for_new_addresses" in method:
                templated["task_id"] = "{{scan_new_addresses_taskid}}"
        
        # Template 1inch API parameters if present
        params = templated.get("params", {})
        if isinstance(params, dict):
            if "src_amount" in params:
                params["src_amount"] = "{{amount}}"
            if "slippage" in params:
                params["slippage"] = "{{slippage}}"
            if "gas_price" in params and params["gas_price"] is not None:
                params["gas_price"] = "{{gas_price}}"
            if "gas_limit" in params and params["gas_limit"] is not None:
                params["gas_limit"] = "{{gas_limit}}"
            if "protocols" in params and params["protocols"] is not None:
                params["protocols"] = "{{protocols}}"
            if "parts" in params and params["parts"] is not None:
                params["parts"] = "{{parts}}"
            if "main_route_parts" in params and params["main_route_parts"] is not None:
                params["main_route_parts"] = "{{main_route_parts}}"
            if "complexity_level" in params and params["complexity_level"] is not None:
                params["complexity_level"] = "{{complexity_level}}"
        
        # Template address parameters
        if "address" in templated and templated["address"] and not templated["address"].startswith("{{"):
            templated["address"] = "{{address}}"
            
        # Template chain_id for blockchain operations
        if "chain_id" in templated:
            templated["chain_id"] = "{{chain_id}}"
        if "account_id" in templated:
            templated["account_id"] = "{{account_id}}"
            
        return templated
    
    def generate_request_description(self, api_method: str, method_name: str, 
                                   operation: str, version: str) -> str:
        """Generate comprehensive description for a request."""
        desc_parts = [
            f"**Method**: `{api_method}`",
            f"**Operation**: `{operation}`",
            f"**API Version**: {version.upper()}",
            "",
            "**Description**:",
            f"This request demonstrates the `{api_method}` method"
        ]
        
        if operation != 'default':
            desc_parts.append(f"with the `{operation}` operation")
        
        desc_parts.extend([
            "",
            "**Documentation**:",
            f"- [API Documentation](https://developers.komodoplatform.com/basic-docs/komodo-defi-framework/api/{version}/)",
            "",
            "**Usage Notes**:",
            "- Replace `{{kdf_url}}` with your KDF instance endpoint",
            "- Update `userpass` with your configured RPC password",
            "- Modify parameters as needed for your use case"
        ])
        
        return "\n".join(desc_parts)
    
    def generate_test_script(self, api_method: str) -> str:
        """Generate test script for request validation."""
        return f'''// Test script for {api_method}
pm.test("Status code is 200", function () {{
    pm.response.to.have.status(200);
}});

pm.test("Response has result", function () {{
    const response = pm.response.json();
    pm.expect(response).to.have.property('result');
}});

pm.test("No error in response", function () {{
    const response = pm.response.json();
    pm.expect(response).to.not.have.property('error');
}});

pm.test("Response time is reasonable", function () {{
    pm.expect(pm.response.responseTime).to.be.below(30000);
}});'''
    
    def organize_requests_into_folders(self, categorized_requests: Dict[str, List[PostmanRequest]]) -> List[PostmanFolder]:
        """Organize requests into a folder structure."""
        folders = []
        
        for category, requests in categorized_requests.items():
            if not requests:
                continue
            
            category_config = self.method_categories[category]
            
            # Group requests by method within each category
            method_groups = {}
            for request in requests:
                base_method = request.method_name.split('::')[0] if '::' in request.method_name else request.method_name
                if base_method not in method_groups:
                    method_groups[base_method] = []
                method_groups[base_method].append(request)
            
            # Create subfolders for each method if there are many requests
            subfolders = []
            folder_requests = []
            
            for method_name, method_requests in method_groups.items():
                if len(method_requests) > 3:  # Create subfolder for methods with many examples
                    subfolder = PostmanFolder(
                        name=method_name.replace('_', ' ').title(),
                        description=f"Examples for the {method_name} method",
                        requests=sorted(method_requests, key=lambda x: x.name),
                        subfolders=[]
                    )
                    subfolders.append(subfolder)
                else:
                    folder_requests.extend(method_requests)
            
            # Create main category folder
            folder = PostmanFolder(
                name=category_config['name'],
                description=category_config['description'],
                requests=sorted(folder_requests, key=lambda x: x.name),
                subfolders=sorted(subfolders, key=lambda x: x.name)
            )
            folders.append(folder)
        
        return sorted(folders, key=lambda x: x.name)
    
    def generate_postman_collection(self, version: str) -> Dict[str, Any]:
        """Generate complete Postman collection for a specific API version."""
        # Scan examples and organize them
        categorized_requests = self.scan_json_examples(version)
        folders = self.organize_requests_into_folders(categorized_requests)
        
        # Count total requests
        total_requests = sum(len(cat_requests) for cat_requests in categorized_requests.values())
        
        # Collection metadata
        collection = {
            "info": {
                "name": f"Komodo DeFi Framework {version.upper()} API",
                "description": self.generate_collection_description(version, total_requests),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                "_postman_id": str(uuid.uuid4()),
                "version": {
                    "major": 1,
                    "minor": 0,
                    "patch": 0
                }
            },
            "item": [],
            "event": [
                {
                    "listen": "prerequest",
                    "script": {
                        "type": "text/javascript",
                        "exec": self.generate_pre_request_script()
                    }
                }
            ],
            "variable": self.generate_collection_variables(version)
        }
        
        # Add folders and requests
        for folder in folders:
            collection["item"].append(self.folder_to_postman_item(folder))
        
        return collection
    
    def generate_collection_description(self, version: str, total_requests: int) -> str:
        """Generate collection description."""
        return f"""# Komodo DeFi Framework {version.upper()} API Collection

This collection contains {total_requests} example requests for the Komodo DeFi Framework {version.upper()} API.

## 🚀 Getting Started

1. **Set Environment Variables**:
   - `kdf_url`: Your KDF instance endpoint (e.g., `http://127.0.0.1:7783`)
   - `userpass`: Your configured RPC password

2. **Authentication**:
   - All requests use the `userpass` parameter for authentication
   - Update the default password in the environment variables

3. **Request Format**:
   - All requests use POST method with JSON payload
   - Set `Content-Type: application/json` header

## 📚 Documentation

- [Official API Documentation](https://developers.komodoplatform.com/basic-docs/komodo-defi-framework/api/{version}/)
- [Setup Guide](https://developers.komodoplatform.com/basic-docs/komodo-defi-framework/setup/)
- [GitHub Repository](https://github.com/KomodoPlatform/komodo-defi-framework)

## 🧪 Testing

Each request includes comprehensive test scripts that validate:
- Response status codes
- Response structure
- Error handling
- Performance metrics

Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    def generate_pre_request_script(self) -> List[str]:
        """Generate pre-request script for the collection."""
        return [
            "// Pre-request script for KDF API",
            "// Ensure required variables are set",
            "",
            "if (!pm.environment.get('kdf_url')) {",
            "    console.warn('⚠️ kdf_url environment variable not set');",
            "}",
            "",
            "if (!pm.environment.get('userpass')) {",
            "    console.warn('⚠️ userpass environment variable not set');",
            "}",
            "",
            "// Set timestamp for request tracking",
            "pm.globals.set('request_timestamp', new Date().toISOString());"
        ]
    
    def generate_collection_variables(self, version: str) -> List[Dict[str, str]]:
        """Generate collection-level variables."""
        return [
            {
                "key": "kdf_url",
                "value": "http://127.0.0.1:7783",
                "description": "KDF instance URL with IP/domain and port"
            },
            {
                "key": "userpass", 
                "value": "RPC_UserP@SSW0RD",
                "description": "RPC authentication password (update this!)"
            },
            {
                "key": "api_version",
                "value": version,
                "description": f"API version: {version}"
            }
        ]
    
    def folder_to_postman_item(self, folder: PostmanFolder) -> Dict[str, Any]:
        """Convert PostmanFolder to Postman collection item."""
        item = {
            "name": folder.name,
            "description": folder.description,
            "item": []
        }
        
        # Add direct requests
        for request in folder.requests:
            item["item"].append(self.request_to_postman_item(request))
        
        # Add subfolders
        for subfolder in folder.subfolders:
            item["item"].append(self.folder_to_postman_item(subfolder))
        
        return item
    
    def request_to_postman_item(self, request: PostmanRequest) -> Dict[str, Any]:
        """Convert PostmanRequest to Postman collection item."""
        return {
            "name": request.name,
            "request": {
                "method": request.method,
                "header": request.headers,
                "body": {
                    "mode": "raw",
                    "raw": json.dumps(request.body, indent=2),
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                },
                "url": {
                    "raw": request.url,
                    "host": ["{{kdf_url}}"]
                },
                "description": request.description
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": request.tests.split('\n')
                    }
                }
            ]
        }
    
    def generate_environment_file(self, version: str) -> Dict[str, Any]:
        """Generate Postman environment file with comprehensive variables."""
        return {
            "id": str(uuid.uuid4()),
            "name": f"KDF {version.upper()} Environment",
            "values": [
                # Core connection settings
                {
                    "key": "kdf_url",
                    "value": "http://127.0.0.1:7783",
                    "description": "KDF instance URL with IP/domain and port",
                    "enabled": True
                },
                {
                    "key": "url",
                    "value": "127.0.0.1",
                    "description": "KDF instance IP or domain",
                    "enabled": True
                },
                {
                    "key": "port",
                    "value": "7783",
                    "description": "KDF instance port",
                    "enabled": True
                },
                {
                    "key": "userpass", 
                    "value": "RPC_UserP@SSW0RD",
                    "description": "RPC authentication password (update this!)",
                    "type": "secret",
                    "enabled": True
                },
                
                # API version
                {
                    "key": "api_version",
                    "value": version,
                    "description": f"API version: {version}",
                    "enabled": True
                },
                
                # Task management variables
                {
                    "key": "enable_utxo_taskid",
                    "value": "",
                    "description": "Task ID for UTXO enable operations",
                    "enabled": True
                },
                {
                    "key": "scan_new_addresses_taskid",
                    "value": "",
                    "description": "Task ID for address scanning operations",
                    "enabled": True
                },
                {
                    "key": "init_withdraw_taskid",
                    "value": "",
                    "description": "Task ID for withdrawal operations",
                    "enabled": True
                },
                
                # Version and address info
                {
                    "key": "mm2_version",
                    "value": "",
                    "description": "KDF/MM2 version number",
                    "enabled": True
                },
                {
                    "key": "address",
                    "value": "127.0.0.1:7783",
                    "description": "Full KDF address (IP:port)",
                    "enabled": True
                },
                
                # Trading parameters
                {
                    "key": "coin",
                    "value": "KMD",
                    "description": "Primary coin ticker",
                    "enabled": True
                },
                {
                    "key": "electrum_coin",
                    "value": "KMD",
                    "description": "Electrum-based coin ticker",
                    "enabled": True
                },
                {
                    "key": "base",
                    "value": "KMD",
                    "description": "Base coin for trading pairs",
                    "enabled": True
                },
                {
                    "key": "rel",
                    "value": "BTC",
                    "description": "Related coin for trading pairs",
                    "enabled": True
                },
                {
                    "key": "amount",
                    "value": "1.0",
                    "description": "Trading amount",
                    "enabled": True
                },
                {
                    "key": "slippage",
                    "value": "0.5",
                    "description": "Acceptable slippage percentage",
                    "enabled": True
                },
                {
                    "key": "fee",
                    "value": "0",
                    "description": "Trading fee",
                    "enabled": True
                },
                
                # 1inch DEX API parameters
                {
                    "key": "ONE_INCH_API_TEST_AUTH",
                    "value": "",
                    "description": "1inch API authentication token",
                    "type": "secret",
                    "enabled": True
                },
                {
                    "key": "protocols",
                    "value": "null",
                    "description": "1inch protocols parameter",
                    "enabled": True
                },
                {
                    "key": "gas_price",
                    "value": "null",
                    "description": "Gas price for Ethereum transactions",
                    "enabled": True
                },
                {
                    "key": "complexity_level",
                    "value": "null",
                    "description": "1inch complexity level",
                    "enabled": True
                },
                {
                    "key": "parts",
                    "value": "null",
                    "description": "1inch split parts parameter",
                    "enabled": True
                },
                {
                    "key": "main_route_parts",
                    "value": "null",
                    "description": "1inch main route parts",
                    "enabled": True
                },
                {
                    "key": "gas_limit",
                    "value": "null",
                    "description": "Gas limit for transactions",
                    "enabled": True
                },
                {
                    "key": "include_tokens_info",
                    "value": "true",
                    "description": "Include token information in responses",
                    "enabled": True
                },
                {
                    "key": "include_protocols",
                    "value": "true",
                    "description": "Include protocol information",
                    "enabled": True
                },
                {
                    "key": "include_gas",
                    "value": "true",
                    "description": "Include gas estimation",
                    "enabled": True
                },
                {
                    "key": "connector_tokens",
                    "value": "null",
                    "description": "1inch connector tokens",
                    "enabled": True
                },
                {
                    "key": "excluded_protocols",
                    "value": "null",
                    "description": "Protocols to exclude from 1inch",
                    "enabled": True
                },
                {
                    "key": "permit",
                    "value": "null",
                    "description": "Permit parameter for 1inch",
                    "enabled": True
                },
                {
                    "key": "compatibility",
                    "value": "null",
                    "description": "Compatibility mode",
                    "enabled": True
                },
                {
                    "key": "receiver",
                    "value": "null",
                    "description": "Receiver address",
                    "enabled": True
                },
                {
                    "key": "referrer",
                    "value": "null",
                    "description": "Referrer address",
                    "enabled": True
                },
                {
                    "key": "disable_estimate",
                    "value": "false",
                    "description": "Disable gas estimation",
                    "enabled": True
                },
                {
                    "key": "allow_partial_fill",
                    "value": "true",
                    "description": "Allow partial order fills",
                    "enabled": True
                },
                {
                    "key": "use_permit2",
                    "value": "false",
                    "description": "Use permit2 for approvals",
                    "enabled": True
                },
                
                # Blockchain parameters
                {
                    "key": "chain_id",
                    "value": "1",
                    "description": "Blockchain chain ID (1 = Ethereum mainnet)",
                    "enabled": True
                },
                {
                    "key": "account_id",
                    "value": "0",
                    "description": "Account ID for HD wallets",
                    "enabled": True
                }
            ],
            "_postman_variable_scope": "environment"
        }
    
    def save_collection(self, collection: Dict[str, Any], version: str) -> str:
        """Save collection to file with lowercase filename format."""
        output_dir = Path(self.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"kdf-{version}-postman-collection.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def save_environment(self, environment: Dict[str, Any], version: str) -> str:
        """Save environment to file with lowercase filename format."""
        # Use separate directory for environments
        output_dir = Path("../../postman/environments")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"kdf-{version}-environment.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(environment, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def generate_collections(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Tuple[str, str]]:
        """Generate collections for specified versions."""
        results = {}
        
        for version in versions:
            if self.verbose:
                print(f"\n🔨 Generating {version.upper()} collection...")
            
            try:
                # Generate collection
                collection = self.generate_postman_collection(version)
                collection_path = self.save_collection(collection, version)
                
                # Generate environment
                environment = self.generate_environment_file(version)
                environment_path = self.save_environment(environment, version)
                
                results[version] = (collection_path, environment_path)
                
                if self.verbose:
                    total_requests = sum(len(item.get('item', [])) for item in collection['item'])
                    print(f"✅ {version.upper()}: {total_requests} requests in {len(collection['item'])} folders")
                    print(f"   Collection: {collection_path}")
                    print(f"   Environment: {environment_path}")
                    
            except Exception as e:
                print(f"❌ Error generating {version} collection: {e}")
                results[version] = (None, None)
        
        return results
    
    def generate_summary_report(self, results: Dict[str, Tuple[str, str]]) -> str:
        """Generate summary report of collection generation."""
        report_lines = [
            "🎯 Postman Collection Generation Summary",
            "=" * 50,
            ""
        ]
        
        total_collections = 0
        total_environments = 0
        
        for version, (collection_path, env_path) in results.items():
            if collection_path and env_path:
                total_collections += 1
                total_environments += 1
                report_lines.extend([
                    f"✅ {version.upper()} API:",
                    f"    Collection: {Path(collection_path).name}",
                    f"   🌍 Environment: {Path(env_path).name}",
                    ""
                ])
            else:
                report_lines.extend([
                    f"❌ {version.upper()} API: Generation failed",
                    ""
                ])
        
        report_lines.extend([
            f"📊 Results:",
            f"   Collections generated: {total_collections}",
            f"   Environments generated: {total_environments}",
            "",
            "🚀 Next Steps:",
            "1. Import the collection files into Postman",
            "2. Import the environment files",
            "3. Update the 'userpass' environment variable",
            "4. Set the 'kdf_url' to your KDF instance",
            "5. Start testing the API!",
            "",
            "📚 Documentation:",
            "- Collection includes comprehensive test scripts",
            "- Each request has detailed descriptions",
            "- Environment variables are pre-configured",
            "- Folders organize methods by functionality"
        ])
        
        return "\n".join(report_lines)


def main():
    """Main function to generate Postman collections."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Postman collections from organized JSON examples')
    parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'], default=['v1', 'v2'],
                       help='API versions to generate collections for')
    parser.add_argument('--verbose', '-v', action='store_true', default=True,
                       help='Enable verbose output')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')
    
    args = parser.parse_args()
    
    # Change to script directory for relative paths
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    verbose = args.verbose and not args.quiet
    
    generator = PostmanCollectionGenerator(verbose=verbose)
    
    if not args.quiet:
        print("🚀 Starting Postman Collection Generation...")
        print(f"📋 Processing versions: {', '.join(args.versions)}")
    
    # Generate collections
    results = generator.generate_collections(args.versions)
    
    # Print summary
    if not args.quiet:
        print("\n" + "="*60)
        print(generator.generate_summary_report(results))
        print("="*60)
        print("\n🎉 Postman collection generation completed!")
    
    return 0


if __name__ == "__main__":
    exit(main()) 