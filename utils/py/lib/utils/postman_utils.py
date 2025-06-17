#!/usr/bin/env python3
"""
Postman Utilities

Stateless utility functions for Postman operations.
Extracted from postman pipeline modules to follow standard architecture.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class PostmanFolder:
    """Represents a Postman folder containing related requests."""
    name: str
    description: str
    requests: List[Any]  # PostmanRequest objects
    subfolders: List['PostmanFolder']


class PostmanUtilities:
    """
    Stateless utility functions for Postman collection and environment generation.
    
    Extracted from the postman pipeline modules to provide reusable functionality
    following the standard architecture pattern.
    """
    
    @staticmethod
    def template_json_body(json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Template JSON body by replacing values with Postman variables.
        
        Args:
            json_data: Original JSON data
            
        Returns:
            Templated JSON with Postman variables
        """
        # Deep copy to avoid modifying original
        templated = json.loads(json.dumps(json_data))
        
        # Standard replacements
        templated["userpass"] = "{{userpass}}"
        
        # Common field replacements
        field_mappings = {
            "coin": "{{coin}}",
            "base": "{{base}}",
            "rel": "{{rel}}",
            "amount": "{{amount}}",
            "max_volume": "{{amount}}",
            "fee": "{{fee}}",
            "address": "{{address}}",
            "chain_id": "{{chain_id}}",
            "account_id": "{{account_id}}"
        }
        
        for field, template in field_mappings.items():
            if field in templated and templated[field] and not str(templated[field]).startswith("{{"):
                templated[field] = template
        
        # Handle task_id with context-specific templates
        if "task_id" in templated:
            method = templated.get("method", "")
            if "enable_utxo" in method:
                templated["task_id"] = "{{enable_utxo_taskid}}"
            elif "withdraw" in method:
                templated["task_id"] = "{{init_withdraw_taskid}}"
            elif "scan_for_new_addresses" in method:
                templated["task_id"] = "{{scan_new_addresses_taskid}}"
        
        # Handle nested params
        params = templated.get("params", {})
        if isinstance(params, dict):
            PostmanUtilities._template_nested_params(params)
        
        return templated
    
    @staticmethod
    def _template_nested_params(params: Dict[str, Any]):
        """Template nested parameters within the params object."""
        nested_mappings = {
            "src_amount": "{{amount}}",
            "slippage": "{{slippage}}",
            "gas_price": "{{gas_price}}",
            "gas_limit": "{{gas_limit}}",
            "protocols": "{{protocols}}",
            "parts": "{{parts}}",
            "main_route_parts": "{{main_route_parts}}",
            "complexity_level": "{{complexity_level}}"
        }
        
        for field, template in nested_mappings.items():
            if field in params and params[field] is not None:
                params[field] = template
    
    @staticmethod
    def organize_requests_into_folders(categorized_requests: Dict[str, List[Any]]) -> List[PostmanFolder]:
        """
        Organize categorized requests into a folder structure.
        
        Args:
            categorized_requests: Dictionary mapping categories to request lists
            
        Returns:
            List of organized folders
        """
        # Import the categorizer configuration
        method_categories = {
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
        
        folders = []
        
        for category, requests in categorized_requests.items():
            if not requests:
                continue
            
            category_config = method_categories.get(category, {
                'name': category.title(),
                'description': f'{category.title()} operations'
            })
            
            # Group requests by base method name
            method_groups = PostmanUtilities._group_requests_by_method(requests)
            
            # Organize into subfolders and direct requests
            subfolders, folder_requests = PostmanUtilities._organize_method_groups(method_groups)
            
            # Create main category folder
            folder = PostmanFolder(
                name=category_config['name'],
                description=category_config['description'],
                requests=sorted(folder_requests, key=lambda x: x.name),
                subfolders=sorted(subfolders, key=lambda x: x.name)
            )
            folders.append(folder)
        
        return sorted(folders, key=lambda x: x.name)
    
    @staticmethod
    def _group_requests_by_method(requests: List[Any]) -> Dict[str, List[Any]]:
        """Group requests by their base method name."""
        method_groups = {}
        
        for request in requests:
            base_method = PostmanUtilities._extract_base_method(request.method_name)
            if base_method not in method_groups:
                method_groups[base_method] = []
            method_groups[base_method].append(request)
        
        return method_groups
    
    @staticmethod
    def _extract_base_method(method_name: str) -> str:
        """Extract the base method name without operations."""
        if '::' in method_name:
            parts = method_name.split('::')
            if len(parts) > 1:
                return parts[0]
        elif '_' in method_name:
            parts = method_name.split('_')
            if len(parts) > 1:
                return parts[0]
        
        return method_name
    
    @staticmethod
    def _organize_method_groups(method_groups: Dict[str, List[Any]]) -> tuple:
        """
        Organize method groups into subfolders and direct requests.
        
        Returns:
            Tuple of (subfolders, direct_requests)
        """
        subfolders = []
        folder_requests = []
        
        for method_name, method_requests in method_groups.items():
            # Create subfolder for methods with many requests
            if len(method_requests) > 3:
                subfolder = PostmanFolder(
                    name=PostmanUtilities._format_method_name(method_name),
                    description=f"Examples for the {method_name} method",
                    requests=sorted(method_requests, key=lambda x: x.name),
                    subfolders=[]
                )
                subfolders.append(subfolder)
            else:
                # Add to main folder if few requests
                folder_requests.extend(method_requests)
        
        return subfolders, folder_requests
    
    @staticmethod
    def _format_method_name(method_name: str) -> str:
        """Format method name for display in folder names."""
        return method_name.replace('_', ' ').title()
    
    @staticmethod
    def generate_postman_collection(version: str, folders: List[PostmanFolder], 
                                   total_requests: int) -> Dict:
        """
        Generate a complete Postman collection.
        
        Args:
            version: API version
            folders: Organized folder structure
            total_requests: Total number of requests
            
        Returns:
            Complete Postman collection dictionary
        """
        collection = {
            "info": PostmanUtilities._generate_collection_info(version, total_requests),
            "item": [],
            "event": [
                {
                    "listen": "prerequest",
                    "script": {
                        "type": "text/javascript",
                        "exec": PostmanUtilities._generate_pre_request_script()
                    }
                }
            ],
            "variable": PostmanUtilities._generate_collection_variables(version)
        }
        
        # Convert folders to Postman format
        for folder in folders:
            collection["item"].append(PostmanUtilities._folder_to_postman_item(folder))
        
        return collection
    
    @staticmethod
    def generate_environment_file(version: str) -> Dict:
        """
        Generate a complete Postman environment file.
        
        Args:
            version: API version
            
        Returns:
            Complete environment dictionary
        """
        return {
            "id": str(uuid.uuid4()),
            "name": f"KDF {version.upper()} Environment",
            "values": PostmanUtilities._generate_environment_variables(version),
            "_postman_variable_scope": "environment"
        }
    
    @staticmethod
    def _generate_collection_info(version: str, total_requests: int) -> Dict:
        """Generate collection info section."""
        return {
            "name": f"Komodo DeFi Framework {version.upper()} API",
            "description": PostmanUtilities._generate_collection_description(version, total_requests),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": str(uuid.uuid4()),
            "version": {
                "major": 1,
                "minor": 0,
                "patch": 0
            }
        }
    
    @staticmethod
    def _generate_collection_description(version: str, total_requests: int) -> str:
        """Generate comprehensive collection description."""
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
    
    @staticmethod
    def _generate_pre_request_script() -> List[str]:
        """Generate pre-request script for all requests."""
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
    
    @staticmethod
    def _generate_collection_variables(version: str) -> List[Dict[str, str]]:
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
    
    @staticmethod
    def _generate_environment_variables(version: str) -> List[Dict]:
        """Generate comprehensive set of environment variables."""
        # Core connection variables
        core_vars = PostmanUtilities._get_core_variables(version)
        
        # Trading variables
        trading_vars = PostmanUtilities._get_trading_variables()
        
        # Task management variables
        task_vars = PostmanUtilities._get_task_variables()
        
        # 1inch integration variables
        oneinch_vars = PostmanUtilities._get_oneinch_variables()
        
        return core_vars + trading_vars + task_vars + oneinch_vars
    
    @staticmethod
    def _get_core_variables(version: str) -> List[Dict]:
        """Get core connection and authentication variables."""
        return [
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
            {
                "key": "api_version",
                "value": version,
                "description": f"API version: {version}",
                "enabled": True
            },
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
            }
        ]
    
    @staticmethod
    def _get_trading_variables() -> List[Dict]:
        """Get trading-related variables."""
        return [
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
        ]
    
    @staticmethod
    def _get_task_variables() -> List[Dict]:
        """Get task management variables."""
        return [
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
            }
        ]
    
    @staticmethod
    def _get_oneinch_variables() -> List[Dict]:
        """Get 1inch integration variables."""
        return [
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
            }
        ]
    
    @staticmethod
    def generate_request_description(api_method: str, method_name: str, 
                                   operation: str, version: str) -> str:
        """Generate comprehensive request description."""
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
    
    @staticmethod
    def generate_test_script(api_method: str) -> str:
        """Generate comprehensive test script for the request."""
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
    
    @staticmethod
    def validate_method_operation_match(json_method: str, method_name: str, operation: str) -> bool:
        """
        Validate that JSON method matches expected method and operation.
        
        Args:
            json_method: Method from JSON data
            method_name: Expected method name
            operation: Expected operation
            
        Returns:
            True if valid match, False otherwise
        """
        # Always allow if json_method matches method_name exactly
        if json_method == method_name:
            return True
        
        # Extract base method name from JSON
        json_base = json_method.split('::')[0] if '::' in json_method else json_method
        method_base = method_name.split('::')[0] if '::' in method_name else method_name
        
        # Allow if base methods match
        if json_base == method_base:
            return True
        
        # For task methods, check if the core method matches
        if json_method.startswith('task::') and method_name.startswith('task::'):
            json_parts = json_method.split('::')
            method_parts = method_name.split('::')
            
            if len(json_parts) >= 2 and len(method_parts) >= 2:
                # Check if the main method part matches (e.g., 'enable_utxo')
                if json_parts[1] == method_parts[1]:
                    return True
        
        # Legacy: Allow original validation pattern for backwards compatibility
        if operation != 'request':
            base_method = method_name.replace('::', '-')
            expected_patterns = [
                f"{base_method}-{operation}",
                json_method
            ]
            return any(pattern == json_method for pattern in expected_patterns)
        
        # Default: more lenient matching
        return True
    
    @staticmethod
    def validate_content_for_operation(json_data: Dict[str, Any], operation: str) -> bool:
        """
        Validate that JSON content is appropriate for the operation.
        
        Args:
            json_data: JSON request data
            operation: Operation name
            
        Returns:
            True if content is valid for operation
        """
        params = json_data.get('params', {})
        
        # Status operations should not have activation_params
        if operation == 'status':
            if 'activation_params' in params:
                return False
            return True
        
        # Init operations can have activation_params
        elif operation == 'init':
            return True
        
        # Cancel and user_action operations should not have activation_params
        elif operation in ['cancel', 'user_action']:
            if 'activation_params' in params:
                return False
            return True
        
        # Default: allow other operations
        return True
    
    @staticmethod
    def _folder_to_postman_item(folder: PostmanFolder) -> Dict:
        """
        Convert a PostmanFolder to Postman collection item format.
        
        Args:
            folder: The folder to convert
            
        Returns:
            Postman item dictionary
        """
        item = {
            "name": folder.name,
            "description": folder.description,
            "item": []
        }
        
        # Add direct requests
        for request in folder.requests:
            item["item"].append(PostmanUtilities._request_to_postman_item(request))
        
        # Add subfolders
        for subfolder in folder.subfolders:
            item["item"].append(PostmanUtilities._folder_to_postman_item(subfolder))
        
        return item
    
    @staticmethod
    def _request_to_postman_item(request: Any) -> Dict:
        """
        Convert a PostmanRequest to Postman collection item format.
        
        Args:
            request: The request to convert
            
        Returns:
            Postman request item dictionary
        """
        return {
            "name": request.name,
            "request": {
                "method": request.method,
                "header": request.headers,
                "body": {
                    "mode": "raw",
                    "raw": PostmanUtilities._format_json_body(request.body),
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
    
    @staticmethod
    def _format_json_body(body: Dict) -> str:
        """Format JSON body with proper indentation."""
        return json.dumps(body, indent=2) 