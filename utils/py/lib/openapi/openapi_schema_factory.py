#!/usr/bin/env python3
"""
OpenAPI Schema Creator

This module contains the OpenApiSchemaFactory class, which is responsible for building
various components of the OpenAPI specification, such as request bodies,
response schemas, and parameter definitions. It helps to decouple the schema
generation logic from the main converter class.
"""

import re
from typing import Dict, List, Optional, Any

from ..constants import UnifiedParameterInfo as Parameter


class OpenApiSchemaFactory:
    """
    A factory for creating OpenAPI schema components.
    This class abstracts the logic for building request bodies, responses,
    and parameter schemas based on parsed MDX documentation.
    """
    # Compiled regex for performance
    _ARRAY_OF_REF_REGEX = re.compile(r'array of `?([\w_]+)`?', re.IGNORECASE)
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

    @staticmethod
    def create_request_body_schema(method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates the request body schema, including 'userpass', 'method', and 'params'.
        """
        method_name = method_info['method_name']
        parameters = method_info.get('parameters', [])

        # Create schema for the 'params' object
        params_schema = OpenApiSchemaFactory._create_params_schema(parameters)

        # Build the full request body schema
        request_body_schema = {
            "type": "object",
            "required": ["userpass", "method"],
            "properties": {
                "userpass": {
                    "type": "string",
                    "description": "User password for authentication.",
                    "example": "RPC_UserP@SSW0RD"
                },
                "method": {
                    "type": "string",
                    "description": "Name of the method to be called.",
                    "enum": [method_name]
                }
            }
        }

        # Add 'params' to properties if there are any parameters
        if params_schema["properties"]:
            request_body_schema["properties"]["params"] = params_schema
            if params_schema.get("required"):
                request_body_schema["required"].append("params")

        return request_body_schema

    @staticmethod
    def create_response_schema(method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates the full response schema, including both success and error responses.
        """
        method_name = method_info['method_name']
        response_parameters = method_info.get('response_parameters', [])

        # Define the basic structure for the result object
        result_object_schema = {
            "type": "object",
            "properties": {}
        }

        # Populate the result object with response parameters
        if response_parameters:
            for param in response_parameters:
                param_name = param.get('name', '').strip('`')
                if not param_name:
                    continue

                param_schema = {
                    "description": param.get('description', '')
                }

                # Use reference for enums/structures or define type
                param_type = param.get('type', 'string')
                if param_type.startswith("#/"):
                    param_schema["$ref"] = param_type
                else:
                    param_schema["type"] = OpenApiSchemaFactory._map_type(param_type)

                result_object_schema["properties"][param_name] = param_schema

        # Define the overall success response schema
        component_name = f"{method_name.replace('::', '_')}_Response"
        success_response_schema = {
            "$ref": f"#/components/schemas/{component_name}"
        }

        # Basic error response schema
        error_response_schema = {
            "$ref": "#/components/schemas/ErrorResponse"
        }

        return {
            "200": {
                "description": f"Successful response for {method_name}",
                "content": {
                    "application/json": {
                        "schema": success_response_schema,
                        "example": OpenApiSchemaFactory.generate_success_example(method_info)
                    }
                }
            },
            "default": {
                "description": "Unexpected error",
                "content": {
                    "application/json": {
                        "schema": error_response_schema
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
    def create_parameter_schema(param_type: str, param_desc: str, default_value: str = "") -> Dict[str, Any]:
        """
        Creates a detailed schema for a single parameter.
        """
        param_schema = {"description": param_desc}
        
        # Handle various type definitions
        array_match = OpenApiSchemaFactory._ARRAY_OF_REF_REGEX.search(param_type)
        if array_match:
            item_name = array_match.group(1)
            param_schema['type'] = 'array'
            param_schema['items'] = {"$ref": f"#/components/schemas/{item_name}"}
        elif 'array of' in param_type.lower():
            item_type = param_type.lower().split('of')[-1].strip().rstrip('s')
            param_schema['type'] = 'array'
            param_schema['items'] = {'type': OpenApiSchemaFactory._map_type(item_type)}
        elif "enum" in param_desc.lower():
            enum_ref = OpenApiSchemaFactory._extract_enum_references_from_description(param_desc)
            if enum_ref:
                param_schema['$ref'] = f"#/components/schemas/{enum_ref}"
            else:
                param_schema['type'] = OpenApiSchemaFactory._map_type(param_type)
        elif param_type.startswith('`') and param_type.endswith('`'):
            ref_name = param_type.strip('`')
            param_schema['$ref'] = f"#/components/schemas/{ref_name}"
        else:
            param_schema['type'] = OpenApiSchemaFactory._map_type(param_type)
        
        if default_value:
            param_schema['default'] = default_value.strip('`')
            
        return param_schema

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