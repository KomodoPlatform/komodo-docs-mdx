#!/usr/bin/env python3
"""
OpenAPI Schema Creator

This module contains the OpenApiSchemaFactory class, which is responsible for building
various components of the OpenAPI specification, such as request bodies,
response schemas, and parameter definitions. It helps to decouple the schema
generation logic from the main converter class.
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..constants import UnifiedParameterInfo as Parameter
from ..utils import get_logger
from ..constants.config import get_config


class OpenApiSchemaFactory:
    """
    A factory for creating OpenAPI schema components.
    This class abstracts the logic for building request bodies, responses,
    and parameter schemas based on parsed MDX documentation.
    """
    # Compiled regex for performance
    _ARRAY_OF_REF_REGEX = re.compile(r'array of `([\w_]+)`', re.IGNORECASE)
    _ENUM_REF_REGEX = re.compile(r'\[([\w\s]+)\]\((.*?)\)')
    _ENUM_ANCHOR_REGEX = re.compile(r'#([\w-]+enum)$', re.IGNORECASE)

    _TYPE_MAPPING = {
        'string': 'string',
        'integer': 'integer',
        'int': 'integer',
        'number': 'number',
        'float': 'number',
        'boolean': 'boolean',
        'bool': 'boolean',
        'array': 'array',
        'object': 'object'
    }

    def __init__(self, config=None, path_mapper=None):
        self.config = config or get_config()
        self.logger = get_logger(__name__)
        # Storing path_mapper if provided
        self.path_mapper = path_mapper
        
        if self.path_mapper is None:
            self.logger.warning("PathMapper not provided to OpenApiSchemaFactory. Reference generation will be disabled.")
            
    def _get_ref_path(self, schema_name: str, current_file_path: str) -> Optional[str]:
        if not self.path_mapper:
            return None
        
        schema_file_path = self.path_mapper.get_schema_path(schema_name)
        if schema_file_path and schema_file_path.exists():
            try:
                # Calculate relative path from the current file's directory
                current_dir = Path(current_file_path).parent
                relative_path = os.path.relpath(schema_file_path, current_dir)
                # Format for OpenAPI reference
                return str(relative_path).replace("\\", "/")
            except ValueError:
                # This can happen if paths are on different drives (on Windows)
                # or other path resolution issues.
                return None
        return None

    def create_parameter_schema(self, param: Dict, file_path: str):
        schema = {"description": param.get("Description", "")}
        param_type = param.get("Type", "string").lower()

        # A more precise regex to find known common structure names within the description.
        # This looks for specific keywords like 'Pagination', 'HistoryTarget', etc.
        # to avoid false positives.
        known_structures = [
            "Pagination", "HistoryTarget", "SyncStatus", "ErrorResponse", 
            "Order", "Swap", "Taker", "Maker", "Activation" 
        ] # This list can be expanded
        
        # Build a regex pattern to match any of the known structures
        pattern = r'\b(' + '|'.join(known_structures) + r')\b'
        match = re.search(pattern, param.get("Description", ""))
        
        if match:
            ref_name = match.group(1)
            ref_path = self._get_ref_path(ref_name, file_path)
            if ref_path:
                # If a valid reference path is found, check if it's an array
                if "array" in param_type:
                    return {
                        "type": "array",
                        "items": {"$ref": ref_path}
                    }
                return {"$ref": ref_path}

        # Fallback to simple type mapping if no ref found
        if "string" in param_type:
            schema["type"] = "string"
        elif "integer" in param_type or "int" in param_type:
            schema["type"] = "integer"
        elif "number" in param_type or "float" in param_type:
            schema["type"] = "number"
        elif "boolean" in param_type or "bool" in param_type:
            schema["type"] = "boolean"
        elif "array" in param_type:
            schema["type"] = "array"
            # A simple array of strings is assumed if no item type is defined
            schema["items"] = {"type": "string"}
        elif "object" in param_type:
            schema["type"] = "object"
        else:
            schema["type"] = "string"
            
        default_val = param.get("Default", "")
        if default_val and default_val != '-':
             schema['default'] = default_val.strip('`')

        return schema

    def create_request_body_schema(self, method_info: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Creates the request body schema for a given method.
        """
        required_params = []
        properties = {}
        
        # Add 'userpass' and 'method' as standard required properties
        properties['userpass'] = {
            'type': 'string',
            'description': 'User password for authentication.',
            'example': 'RPC_UserP@SSW0RD'
        }
        properties['method'] = {
            'type': 'string',
            'description': 'Name of the method to be called.',
            'enum': [method_info.get('method_name')]
        }
        required_params.extend(['userpass', 'method'])
        
        # Process parameters from method_info
        params = method_info.get('parameters', [])
        if params:
            param_properties = {}
            param_required = []
            for param in params:
                param_name = param.name
                if not param_name:
                    continue
                
                if param.required:
                    param_required.append(param_name)
                
                # Map to the keys expected by create_parameter_schema
                schema_param = {
                    "Parameter": param.name,
                    "Type": param.type,
                    "Description": param.description,
                    "Default": param.default_value
                }
                param_properties[param_name] = self.create_parameter_schema(schema_param, file_path)

            properties['params'] = {
                "type": "object",
                "properties": param_properties
            }
            if param_required:
                 properties['params']['required'] = param_required

            required_params.append('params')

        return {
            'type': 'object',
            'required': required_params,
            'properties': properties
        }
        
    def create_response_schema(self, method_info: Dict[str, Any], file_path: str) -> Dict[str, Any]:
        """
        Creates the response schema for a given method.
        This includes a '200' success response with a schema definition and example,
        and a 'default' error response.
        """
        method_name = method_info.get('method_name', 'unknown_method')
        
        response_properties = {}
        for param in method_info.get('response_parameters', []):
            print(f"param: {param}")
            param_name = param.get('name')
            if param_name:
                # Map to the keys expected by create_parameter_schema
                schema_param = {
                    "Parameter": param_name,
                    "Type": param.get('type'),
                    "Description": param.get('description'),
                    "Default": "" # Not relevant for responses
                }
                response_properties[param_name] = self.create_parameter_schema(schema_param, file_path)

        return {
            "200": {
                "description": f"Successful response for {method_name}",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": response_properties
                        },
                        "example": method_info.get('success_response_example', {})
                    }
                }
            },
            "default": {
                "description": "Unexpected error",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": self._get_ref_path("ErrorResponse", file_path) or '#/components/schemas/ErrorResponse'
                        }
                    }
                }
            }
        }

    @staticmethod
    def generate_success_example(method_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a sample success response for documentation purposes."""
        response_params = method_info.get('response_parameters', [])
        result = {}
        for param in response_params:
            name = param.get('name')
            ptype = param.get('type', 'string').lower()
            if 'string' in ptype:
                result[name] = "string_value"
            elif 'integer' in ptype:
                result[name] = 123
            elif 'boolean' in ptype:
                result[name] = True
            else:
                result[name] = {}
        return {
            "mmrpc": "2.0",
            "result": result,
            "id": 0
        }

    @staticmethod
    def _create_params_schema(parameters: List[Parameter]) -> Dict[str, Any]:
        """
        Creates the JSON schema for the 'params' object within the request body.
        """
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        # Sort parameters alphabetically for consistent order
        parameters.sort(key=lambda p: p.name)

        for param in parameters:
            param_schema = {
                "description": param.description
            }

            # Use reference for enums or define type
            if param.type and param.type.startswith("#/"):
                param_schema["$ref"] = param.type
            else:
                param_schema["type"] = OpenApiSchemaFactory._map_type(param.type)

            # Add default value if present
            if param.default_value is not None:
                param_schema["default"] = param.default_value

            # Add inline enum values if present
            if param.enum_values:
                param_schema["enum"] = param.enum_values

            schema["properties"][param.name] = param_schema

            if param.required:
                schema["required"].append(param.name)

        # Remove 'required' field if it's empty
        if not schema["required"]:
            del schema["required"]

        return schema

    @staticmethod
    def _map_type(mdx_type: str) -> str:
        """Maps an MDX type to an OpenAPI type."""
        mdx_type_lower = mdx_type.lower()
        for key, value in OpenApiSchemaFactory._TYPE_MAPPING.items():
            if key in mdx_type_lower:
                return value
        return 'string'

    @staticmethod
    def _extract_enum_references_from_description(description: str) -> Optional[str]:
        """
        Extracts references to common enums from the description.
        """
        match = OpenApiSchemaFactory._ENUM_REF_REGEX.search(description)
        if match:
            link_url = match.group(2)
            if '#-enum' in link_url.lower() or 'enums' in link_url.lower():
                anchor_match = OpenApiSchemaFactory._ENUM_ANCHOR_REGEX.search(link_url)
                if anchor_match:
                    return anchor_match.group(1)
        return None 