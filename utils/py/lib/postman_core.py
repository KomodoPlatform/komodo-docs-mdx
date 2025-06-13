#!/usr/bin/env python3
"""
Postman Core

Consolidated Postman collection generation functionality.
Combines request processing, organization, and generation into a unified module.
"""

import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass

from .logging_utils import get_logger
from .shared_utils import normalize_file_path, convert_method_to_dir_name, format_method_name_for_display
from .base_file_manager import BaseFileManager


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
    """Represents a folder in a Postman collection."""
    name: str
    description: str
    requests: List[PostmanRequest]
    subfolders: List['PostmanFolder']


class PostmanRequestProcessor:
    """
    Processes JSON examples into Postman requests.
    Handles validation, templating, and metadata generation.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = get_logger("postman-request-processor")
    
    def create_postman_request(self, json_data: Dict[str, Any], method_name: str,
                              operation: str, example_description: str, version: str) -> Optional[PostmanRequest]:
        """
        Create a Postman request from JSON data.
        
        Args:
            json_data: The JSON request data
            method_name: The method name
            operation: The operation name
            example_description: Description of the example
            version: API version
            
        Returns:
            PostmanRequest object or None if invalid
        """
        if 'method' not in json_data:
            return None
        
        api_method = json_data['method']
        clean_description = example_description.replace('_', ' ').title()
        request_name = f"{api_method} - {clean_description}"
        
        # Standard headers for KDF API
        headers = [
            {"key": "Content-Type", "value": "application/json"},
            {"key": "Accept", "value": "application/json"}
        ]
        
        # Template the JSON body for variable substitution
        templated_body = self._template_json_body(json_data)
        
        # Generate description and test script
        description = self._generate_request_description(api_method, method_name, operation, version)
        test_script = self._generate_test_script(api_method)
        
        return PostmanRequest(
            name=request_name,
            method="POST",
            url="{{kdf_url}}",
            headers=headers,
            body=templated_body,
            description=description,
            tests=test_script,
            method_name=method_name,
            operation=operation,
            example_description=example_description
        )
    
    def _template_json_body(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
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
            self._template_nested_params(params)
        
        return templated
    
    def _template_nested_params(self, params: Dict[str, Any]) -> None:
        """Template nested parameters recursively."""
        for key, value in params.items():
            if isinstance(value, dict):
                self._template_nested_params(value)
            elif key in ["coin", "base", "rel"] and isinstance(value, str):
                params[key] = f"{{{{{key}}}}}"
    
    def _generate_request_description(self, api_method: str, method_name: str, 
                                    operation: str, version: str) -> str:
        """Generate description for the request."""
        base_description = f"Execute the {api_method} method"
        
        if operation != "default":
            base_description += f" ({operation} operation)"
        
        base_description += f" in KDF API {version.upper()}."
        
        return f"{base_description}\n\nMethod: {method_name}\nOperation: {operation}"
    
    def _generate_test_script(self, api_method: str) -> str:
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
    
    def validate_method_operation_match(self, json_method: str, method_name: str, operation: str) -> bool:
        """
        Validate that JSON method matches expected method and operation.
        
        Args:
            json_method: Method from JSON data
            method_name: Expected method name
            operation: Expected operation
            
        Returns:
            True if valid match, False otherwise
        """
        if operation == 'default':
            return json_method == method_name
        
        # Generate expected patterns
        base_method = method_name.replace('::', '-')
        expected_patterns = [
            f"{base_method}-{operation}",
            json_method  # Allow exact match
        ]
        
        return any(pattern == json_method for pattern in expected_patterns)
    
    def validate_content_for_operation(self, json_data: Dict[str, Any], operation: str) -> bool:
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


class MethodCategorizer:
    """
    Categorizes API methods into logical groups for organization.
    """
    
    def __init__(self):
        self.category_patterns = {
            'coin_activation': ['enable', 'disable', 'activation', 'task::enable'],
            'trading': ['buy', 'sell', 'setprice', 'trade', 'order', 'swap'],
            'wallet': ['balance', 'withdraw', 'address', 'my_', 'get_new_address'],
            'lightning': ['lightning::'],
            'streaming': ['stream::'],
            'task_operations': ['task::'],
            'utility': ['version', 'help', 'metrics', 'peer', 'gossip'],
            'nft': ['nft', 'enable_nft', 'get_nft'],
            'staking': ['staking', 'delegation']
        }
    
    def categorize_method(self, method_name: str) -> str:
        """
        Categorize a method based on its name.
        
        Args:
            method_name: The method name to categorize
            
        Returns:
            Category name
        """
        method_lower = method_name.lower()
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern.lower() in method_lower:
                    return category
        
        return 'utility'  # Default category


class FolderOrganizer:
    """
    Organizes requests into folder structures for Postman collections.
    """
    
    def __init__(self, categorizer: MethodCategorizer):
        self.categorizer = categorizer
        self.logger = get_logger("folder-organizer")
    
    def organize_requests_into_folders(self, categorized_requests: Dict[str, List[PostmanRequest]]) -> List[PostmanFolder]:
        """
        Organize categorized requests into folder structure.
        
        Args:
            categorized_requests: Dictionary mapping categories to request lists
            
        Returns:
            List of organized PostmanFolder objects
        """
        folders = []
        
        for category, requests in categorized_requests.items():
            if not requests:
                continue
            
            # Create main category folder
            folder = self._create_category_folder(category, requests)
            folders.append(folder)
        
        return sorted(folders, key=lambda f: f.name)
    
    def _create_category_folder(self, category: str, requests: List[PostmanRequest]) -> PostmanFolder:
        """
        Create a folder for a specific category.
        
        Args:
            category: Category name
            requests: List of requests in the category
            
        Returns:
            PostmanFolder object
        """
        # Format category name for display
        folder_name = format_method_name_for_display(category)
        
        # Group requests by method for better organization
        method_groups = self._group_requests_by_method(requests)
        
        # Organize into subfolders and direct requests
        subfolders, folder_requests = self._organize_method_groups(method_groups)
        
        return PostmanFolder(
            name=folder_name,
            description=f"API methods related to {folder_name.lower()}",
            requests=sorted(folder_requests, key=lambda x: x.name),
            subfolders=subfolders
        )
    
    def _group_requests_by_method(self, requests: List[PostmanRequest]) -> Dict[str, List[PostmanRequest]]:
        """Group requests by their base method name."""
        method_groups = {}
        
        for request in requests:
            base_method = self._extract_base_method(request.method_name)
            if base_method not in method_groups:
                method_groups[base_method] = []
            method_groups[base_method].append(request)
        
        return method_groups
    
    def _extract_base_method(self, method_name: str) -> str:
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
    
    def _organize_method_groups(self, method_groups: Dict[str, List[PostmanRequest]]) -> tuple:
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
                    name=format_method_name_for_display(method_name),
                    description=f"Examples for the {method_name} method",
                    requests=sorted(method_requests, key=lambda x: x.name),
                    subfolders=[]
                )
                subfolders.append(subfolder)
            else:
                # Add to main folder if few requests
                folder_requests.extend(method_requests)
        
        return subfolders, folder_requests


class CollectionGenerator:
    """
    Generates Postman collections with proper metadata and structure.
    """
    
    def __init__(self):
        self.logger = get_logger("collection-generator")
    
    def generate_postman_collection(self, version: str, folders: List[PostmanFolder],
                                   total_requests: int) -> Dict[str, Any]:
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
            "info": self._generate_collection_info(version, total_requests),
            "item": [],
            "event": [
                {
                    "listen": "prerequest",
                    "script": {
                        "type": "text/javascript",
                        "exec": self._generate_pre_request_script()
                    }
                }
            ],
            "variable": self._generate_collection_variables(version)
        }
        
        # Convert folders to Postman format
        for folder in folders:
            collection["item"].append(self._folder_to_postman_item(folder))
        
        return collection
    
    def _generate_collection_info(self, version: str, total_requests: int) -> Dict[str, Any]:
        """Generate collection metadata."""
        return {
            "name": f"Komodo DeFi Framework API {version.upper()}",
            "description": f"Complete collection of Komodo DeFi Framework API {version.upper()} methods with {total_requests} requests",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": str(uuid.uuid4()),
            "_exporter_id": "kdf-docs-generator"
        }
    
    def _generate_pre_request_script(self) -> List[str]:
        """Generate pre-request script for the collection."""
        return [
            "// Pre-request script for KDF API",
            "// Set up common variables and validation",
            "",
            "// Ensure required variables are set",
            "if (!pm.collectionVariables.get('kdf_url')) {",
            "    throw new Error('kdf_url collection variable must be set');",
            "}",
            "",
            "if (!pm.collectionVariables.get('userpass')) {",
            "    throw new Error('userpass collection variable must be set');",
            "}",
            "",
            "// Set default timeout",
            "pm.timeout = 30000;"
        ]
    
    def _generate_collection_variables(self, version: str) -> List[Dict[str, Any]]:
        """Generate collection variables."""
        return [
            {
                "key": "kdf_url",
                "value": "http://127.0.0.1:7783",
                "type": "string",
                "description": "Base URL for KDF API"
            },
            {
                "key": "userpass",
                "value": "RPC_UserP@SSW0RD",
                "type": "string",
                "description": "Authentication userpass for KDF API"
            },
            {
                "key": "coin",
                "value": "KMD",
                "type": "string",
                "description": "Default coin for testing"
            },
            {
                "key": "base",
                "value": "KMD",
                "type": "string",
                "description": "Base coin for trading"
            },
            {
                "key": "rel",
                "value": "BTC",
                "type": "string",
                "description": "Related coin for trading"
            },
            {
                "key": "amount",
                "value": "0.1",
                "type": "string",
                "description": "Default amount for transactions"
            },
            {
                "key": "address",
                "value": "",
                "type": "string",
                "description": "Address for testing"
            },
            {
                "key": "fee",
                "value": "0.0001",
                "type": "string",
                "description": "Default fee amount"
            }
        ]
    
    def _folder_to_postman_item(self, folder: PostmanFolder) -> Dict[str, Any]:
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
            item["item"].append(self._request_to_postman_item(request))
        
        # Add subfolders
        for subfolder in folder.subfolders:
            item["item"].append(self._folder_to_postman_item(subfolder))
        
        return item
    
    def _request_to_postman_item(self, request: PostmanRequest) -> Dict[str, Any]:
        """
        Convert a PostmanRequest to Postman item format.
        
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
                    "raw": self._format_json_body(request.body),
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                },
                "url": {
                    "raw": request.url,
                    "host": [
                        "{{kdf_url}}"
                    ]
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
    
    def _format_json_body(self, body: Dict[str, Any]) -> str:
        """Format JSON body for Postman."""
        return json.dumps(body, indent=2)


class EnvironmentGenerator:
    """
    Generates Postman environment files with appropriate variables.
    """
    
    def __init__(self):
        self.logger = get_logger("environment-generator")
    
    def generate_environment_file(self, version: str) -> Dict[str, Any]:
        """
        Generate a Postman environment file for a specific version.
        
        Args:
            version: API version
            
        Returns:
            Complete environment dictionary
        """
        return {
            "id": str(uuid.uuid4()),
            "name": f"KDF API {version.upper()} Environment",
            "values": self._generate_environment_variables(version),
            "_postman_variable_scope": "environment",
            "_postman_exported_at": datetime.now().isoformat(),
            "_postman_exported_using": "kdf-docs-generator"
        }
    
    def _generate_environment_variables(self, version: str) -> List[Dict[str, Any]]:
        """Generate environment variables for the specified version."""
        base_variables = [
            {
                "key": "kdf_url",
                "value": "http://127.0.0.1:7783",
                "enabled": True,
                "type": "default"
            },
            {
                "key": "userpass",
                "value": "RPC_UserP@SSW0RD",
                "enabled": True,
                "type": "secret"
            },
            {
                "key": "coin",
                "value": "KMD",
                "enabled": True,
                "type": "default"
            },
            {
                "key": "base",
                "value": "KMD",
                "enabled": True,
                "type": "default"
            },
            {
                "key": "rel",
                "value": "BTC",
                "enabled": True,
                "type": "default"
            },
            {
                "key": "amount",
                "value": "0.1",
                "enabled": True,
                "type": "default"
            }
        ]
        
        # Add version-specific variables
        if version == 'v2':
            base_variables.extend([
                {
                    "key": "enable_utxo_taskid",
                    "value": "",
                    "enabled": True,
                    "type": "default"
                },
                {
                    "key": "init_withdraw_taskid",
                    "value": "",
                    "enabled": True,
                    "type": "default"
                },
                {
                    "key": "scan_new_addresses_taskid",
                    "value": "",
                    "enabled": True,
                    "type": "default"
                }
            ])
        
        return base_variables 