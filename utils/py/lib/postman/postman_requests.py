#!/usr/bin/env python3
"""
Postman Request Processing

Handles creation and processing of Postman requests from JSON examples.
Manages request validation, content processing, and metadata generation.
"""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


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


class PostmanRequestProcessor:
    """
    Processes JSON examples into Postman requests.
    Handles validation, templating, and metadata generation.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
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
    
    def _template_nested_params(self, params: Dict[str, Any]):
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
    
    def _generate_request_description(self, api_method: str, method_name: str, 
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
        # Always allow if json_method matches method_name exactly
        if json_method == method_name:
            return True
        
        # For flat directory structure, be more lenient
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