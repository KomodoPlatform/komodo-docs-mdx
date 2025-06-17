#!/usr/bin/env python3
"""
OpenAPI Manager

Comprehensive OpenAPI management including:
- Converting MDX files to OpenAPI specifications
- Managing existing OpenAPI specification files
- Updating main specs and generating focused specs
- Handling OpenAPI paths and operations

MERGED: Combined MDXToOpenAPIConverter functionality with existing OpenAPIManager
"""

import json
import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict

# Import path utilities
from ..utils.path_utils import PathMapper

@dataclass
class Parameter:
    """Represents an API parameter."""
    name: str
    type: str
    description: str
    required: bool
    location: str = "query"
    enum_values: Optional[List[str]] = None  # Add enum support
    default_value: Optional[str] = None      # Add default value support
    enum_reference: Optional[str] = None      # Add enum reference support

@dataclass
class Response:
    """Represents an API response."""
    status_code: str
    description: str
    schema: Optional[Dict[str, Any]] = None

@dataclass
class MethodInfo:
    """Contains complete information about an API method."""
    name: str
    mdx_path: str
    summary: str
    description: str
    parameters: List[Parameter]
    responses: List[Response]
    request_body_schema: Optional[Dict[str, Any]] = None

class MDXParser:
    """Parser for MDX files to extract API method information."""
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        # Track common structures across all parsed methods
        self.common_structures = defaultdict(int)
        self.enum_patterns = defaultdict(set)
    
    def parse_mdx_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse an MDX file and extract method information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract method name from the ## heading
            method_match = re.search(r'^##\s+([^\s{]+)', content, re.MULTILINE)
            if not method_match:
                return None
            
            # Clean up method name by removing escape backslashes
            method_name = method_match.group(1).replace('\\_', '_')
            
            # Extract title and description from exports
            title_match = re.search(r'export const title = ["\']([^"\']+)["\']', content)
            desc_match = re.search(r'export const description = ["\']([^"\']+)["\']', content)
            
            title = title_match.group(1) if title_match else f"Komodo DeFi Framework Method: {method_name}"
            description = desc_match.group(1) if desc_match else f"Method description for {method_name}"
            
            # Extract parameters from parameter tables
            parameters = self._extract_parameters_from_mdx(content)
            
            # Extract response parameters (for future use)
            response_parameters = self._extract_response_parameters_from_mdx(content)
            
            return {
                'method_name': method_name,
                'title': title,
                'description': description,
                'parameters': parameters,
                'response_parameters': response_parameters,
                'file_path': str(file_path)
            }
            
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _extract_response_parameters_from_mdx(self, content: str) -> List[Dict[str, Any]]:
        """Extract response parameters from MDX response tables."""
        response_params = []
        
        # Look for response parameter tables
        table_patterns = [
            r'### Response Parameter[s]?\s*Table\s*\n\n(.*?)(?=\n###|\n##|\Z)',
            r'### Response Parameters\s*\n\n(.*?)(?=\n###|\n##|\Z)',
            r'### Response\s*\n\n(.*?)(?=\n###|\n##|\Z)'  # Add pattern for "### Response"
        ]
        
        for pattern in table_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                response_params.extend(self._parse_response_parameter_table(match))
        
        return response_params
    
    def _parse_response_parameter_table(self, table_content: str) -> List[Dict[str, Any]]:
        """Parse a response parameter table."""
        parameters = []
        
        # Split into lines and find table rows
        lines = table_content.strip().split('\n')
        
        # Find the header row and separator
        header_idx = -1
        separator_idx = -1
        
        for i, line in enumerate(lines):
            if '|' in line and ('Parameter' in line or 'parameter' in line):
                header_idx = i
            elif '|' in line and ('---' in line or '|-' in line):
                separator_idx = i
                break
        
        if header_idx == -1 or separator_idx == -1:
            return parameters
        
        # Parse header to understand column structure
        header_line = lines[header_idx].strip()
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        
        # Remove leading/trailing empty columns
        if headers and not headers[0]:
            headers = headers[1:]
        if headers and not headers[-1]:
            headers = headers[:-1]
        
        # Find column indices
        param_col = -1
        type_col = -1
        desc_col = -1
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if 'parameter' in header_lower:
                param_col = i
            elif 'type' in header_lower:
                type_col = i
            elif 'description' in header_lower:
                desc_col = i
        
        # Parse data rows
        for i in range(separator_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line or not line.startswith('|'):
                continue
                
            # Split the row into columns
            columns = [col.strip() for col in line.split('|')]
            
            # Remove leading/trailing empty columns
            if columns and not columns[0]:
                columns = columns[1:]
            if columns and not columns[-1]:
                columns = columns[:-1]
            
            if len(columns) < max(param_col, type_col, desc_col) + 1:
                continue
            
            # Extract parameter information
            param_name = columns[param_col] if param_col >= 0 and param_col < len(columns) else ""
            param_type = columns[type_col] if type_col >= 0 and type_col < len(columns) else ""
            param_desc = columns[desc_col] if desc_col >= 0 and desc_col < len(columns) else ""
            
            if param_name and param_type:
                parameters.append({
                    'name': param_name.strip('`').replace('\\_', '_'),
                    'type': param_type,
                    'description': param_desc
                })
        
        return parameters

    def _create_placeholder_method_info(self, method_name: str, mdx_path: str) -> MethodInfo:
        return MethodInfo(
            name=method_name,
            mdx_path=mdx_path,
            summary=f"Komodo DeFi Framework Method: {method_name}",
            description=f"Method description for {method_name}",
            parameters=[],
            responses=[
                Response("200", "Success"),
                Response("400", "Bad request"),
                Response("500", "Internal server error")
            ]
        )
    
    def _parse_content(self, content: str, method_name: str, mdx_path: str) -> MethodInfo:
        title_match = re.search(r'export const title = ["\']([^"\']+)["\']', content)
        description_match = re.search(r'export const description =\s*["\']([^"\']+)["\']', content)
        summary = title_match.group(1) if title_match else f"Komodo DeFi Framework Method: {method_name}"
        
        if description_match:
            description = description_match.group(1)
        else:
            desc_match = re.search(r'#[^#\n]*\n\n(.+?)(?:\n\n|\n<|$)', content, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
            else:
                description = f"The {method_name} method for Komodo DeFi Framework API."
        
        # Clean up description in a single chain
        description = re.sub(r'<[^>]+>', '', description)
        description = re.sub(r'\n+', ' ', description).strip()
        
        parameters = self._parse_parameters_table(content)
        responses = self._parse_responses_table(content)
        request_body_schema = self._extract_request_body_schema(content, method_name)
        
        return MethodInfo(
            name=method_name,
            mdx_path=mdx_path,
            summary=summary,
            description=description,
            parameters=parameters,
            responses=responses,
            request_body_schema=request_body_schema
        )
    
    def _parse_parameters_table(self, content: str) -> List[Parameter]:
        parameters = []
        
        # Look for request parameters section
        request_section = re.search(r'###\s+Request\s+Parameters?\s*\n(.*?)(?=\n###|\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
        if not request_section:
            # Fallback to older formats
            args_section = re.search(r'##\s+Arguments?\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
            if not args_section:
                args_section = re.search(r'##\s+Parameters?\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
            request_section = args_section
        
        if request_section:
            table_content = request_section.group(1)
            
            # Enhanced regex to capture more table formats including default values
            # Support both 4-column and 5-column tables
            rows = re.findall(r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)(?:\|([^|]*))?\|', table_content)
            
            for row in rows:
                # Skip header rows
                if any('Parameter' in cell or 'Type' in cell or '---' in cell for cell in row if cell):
                    continue
                
                if len(row) >= 4:
                    param_name = row[0].strip()
                    param_type = row[1].strip()
                    required_indicator = row[2].strip()
                    
                    # Handle both 4-column and 5-column formats
                    if len(row) >= 5 and row[4] and row[4].strip():
                        # 5-column format: Parameter | Type | Required | Default | Description
                        default_value = row[3].strip() if row[3] and row[3].strip() not in ['-', ''] else None
                        param_desc = row[4].strip()
                    else:
                        # 4-column format: Parameter | Type | Required | Description
                        default_value = None
                        param_desc = row[3].strip()
                    
                    # Skip empty rows
                    if not param_name or param_name in ['', '-']:
                        continue
                    
                    # Determine if required
                    required = self._is_parameter_required(required_indicator, param_desc, default_value)
                    
                    # Extract enum values and clean type
                    enum_values, clean_type = self._extract_enum_from_type(param_type)
                    openapi_type = self._map_type(clean_type)
                    
                    # Extract default value from description if not in separate column
                    if not default_value:
                        default_value = self._extract_default_from_description(param_desc)
                    
                    # Clean up default value formatting
                    if default_value:
                        default_value = default_value.strip('`"\'')
                    
                    # Track enum patterns for reuse
                    if enum_values:
                        enum_key = f"{openapi_type}_{tuple(sorted(enum_values))}"
                        self.enum_patterns[enum_key].add(param_name)
                    
                    parameters.append(Parameter(
                        name=param_name,
                        type=openapi_type,
                        description=param_desc,
                        required=required,
                        enum_values=enum_values,
                        default_value=default_value
                    ))
        
        return parameters
    
    def _is_parameter_required(self, required_indicator: str, description: str, default_value: Optional[str]) -> bool:
        """Determine if a parameter is required based on various indicators."""
        # Check explicit required indicator
        if required_indicator.strip() in ['✓', 'true', 'yes', 'required']:
            return True
        if required_indicator.strip() in ['✗', 'false', 'no', 'optional']:
            return False
        
        # If there's a default value, it's typically optional
        if default_value:
            return False
        
        # Check description for optional indicators
        desc_lower = description.lower()
        optional_indicators = ['optional', 'defaults to', 'default:', 'if not specified']
        if any(indicator in desc_lower for indicator in optional_indicators):
            return False
        
        # Default to required if unclear
        return True
    
    def _extract_enum_from_type(self, param_type: str) -> Tuple[Optional[List[str]], str]:
        """Extract enum values from parameter type if present."""
        # Pattern 1: "string (buy | sell)"
        enum_pattern1 = r'^(\w+)\s*\(\s*([^)]+)\s*\)$'
        match1 = re.search(enum_pattern1, param_type.strip())
        if match1:
            base_type = match1.group(1)
            enum_part = match1.group(2)
            enum_values = [val.strip().strip('"\'') for val in enum_part.split('|')]
            return enum_values, base_type
        
        # Pattern 2: "buy | sell" (just enum values)
        if '|' in param_type and not any(base_type in param_type.lower() for base_type in ['string', 'int', 'number', 'bool']):
            enum_values = [val.strip().strip('"\'') for val in param_type.split('|')]
            return enum_values, 'string'  # Default to string for pure enum
        
        # Pattern 3: "string: buy, sell" or "string (buy, sell)"
        enum_pattern3 = r'^(\w+)\s*[:(]\s*([^)]+)\s*[)]?$'
        match3 = re.search(enum_pattern3, param_type.strip())
        if match3 and ',' in match3.group(2):
            base_type = match3.group(1)
            enum_part = match3.group(2)
            enum_values = [val.strip().strip('"\'') for val in enum_part.split(',')]
            return enum_values, base_type
        
        return None, param_type
    
    def _extract_default_from_description(self, description: str) -> Optional[str]:
        """Extract default value from parameter description."""
        # Pattern 1: "defaults to X" or "default: X"
        default_patterns = [
            r'defaults?\s+to\s+[`"]?([^`".,\s]+)[`"]?',
            r'default:?\s*[`"]?([^`".,\s]+)[`"]?',
            r'\(default:?\s*[`"]?([^`".,)]+)[`"]?\)',
        ]
        
        for pattern in default_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _parse_responses_table(self, content: str) -> List[Response]:
        responses = []
        response_section = re.search(r'##\s+Response\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
        if response_section:
            responses.append(Response("200", "Success"))
        else:
            responses.extend([
                Response("200", "Success"),
                Response("400", "Bad request"),
                Response("500", "Internal server error")
            ])
        return responses
    
    def _extract_request_body_schema(self, content: str, method_name: str) -> Optional[Dict[str, Any]]:
        json_blocks = re.findall(r'```json\s*\n(.*?)\n\s*```', content, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block.strip())
                if isinstance(data, dict) and 'method' in data:
                    schema = {
                        "type": "object",
                        "properties": {}
                    }
                    for key, value in data.items():
                        schema["properties"][key] = {
                            "type": self._infer_type_from_value(value),
                            "description": f"The {key} parameter"
                        }
                        if key == "method":
                            schema["properties"][key]["enum"] = [method_name]
                    return schema
            except json.JSONDecodeError:
                continue
        return None
    
    def _map_type(self, mdx_type: str) -> str:
        type_mapping = {
            'string': 'string',
            'str': 'string',
            'integer': 'integer',
            'int': 'integer',
            'number': 'number',
            'float': 'number',
            'boolean': 'boolean',
            'bool': 'boolean',
            'array': 'array',
            'object': 'object',
            'null': 'null'
        }
        lower_type = mdx_type.lower().strip()
        return type_mapping.get(lower_type, 'string')
    
    def _infer_type_from_value(self, value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "string"

    def _extract_parameters_from_mdx(self, content: str) -> List[Parameter]:
        """Extract parameters from MDX parameter tables."""
        parameters = []
        
        # Look for parameter tables (both "Request Parameter" and "Request Arguments")
        table_patterns = [
            r'### Request Parameter[s]?\s*Table\s*\n\n(.*?)(?=\n###|\n##|\Z)',
            r'### Request Arguments\s*\n\n(.*?)(?=\n###|\n##|\Z)',
            r'### Request Parameters\s*\n\n(.*?)(?=\n###|\n##|\Z)'
        ]
        
        for pattern in table_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                parameters.extend(self._parse_parameter_table(match))
        
        return parameters
    
    def _parse_parameter_table(self, table_content: str) -> List[Parameter]:
        """Parse a parameter table and extract parameter information."""
        parameters = []
        
        # Split into lines and find table rows
        lines = table_content.strip().split('\n')
        
        # Find the header row and separator
        header_idx = -1
        separator_idx = -1
        
        for i, line in enumerate(lines):
            if '|' in line and ('Parameter' in line or 'parameter' in line):
                header_idx = i
            elif '|' in line and '---' in line or '|-' in line:
                separator_idx = i
                break
        
        if header_idx == -1 or separator_idx == -1:
            return parameters
        
        # Parse header to understand column structure
        header_line = lines[header_idx].strip()
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        
        # Remove leading/trailing empty columns
        if not headers[0]:
            headers = headers[1:]
        if not headers[-1]:
            headers = headers[:-1]
        
        # Find column indices
        param_col = -1
        type_col = -1
        required_col = -1
        default_col = -1
        desc_col = -1
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if 'parameter' in header_lower:
                param_col = i
            elif 'type' in header_lower:
                type_col = i
            elif 'required' in header_lower:
                required_col = i
            elif 'default' in header_lower:
                default_col = i
            elif 'description' in header_lower:
                desc_col = i
        
        # Parse data rows
        for i in range(separator_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line or not line.startswith('|'):
                continue
                
            # Split the row into columns
            columns = [col.strip() for col in line.split('|')]
            
            # Remove leading/trailing empty columns
            if columns and not columns[0]:
                columns = columns[1:]
            if columns and not columns[-1]:
                columns = columns[:-1]
            
            if len(columns) < max(param_col, type_col, desc_col) + 1:
                continue
            
            # Extract parameter information
            param_name = columns[param_col] if param_col >= 0 and param_col < len(columns) else ""
            param_type = columns[type_col] if type_col >= 0 and type_col < len(columns) else ""
            param_desc = columns[desc_col] if desc_col >= 0 and desc_col < len(columns) else ""
            
            # Determine if required
            is_required = False
            if required_col >= 0 and required_col < len(columns):
                required_val = columns[required_col].strip()
                is_required = '✓' in required_val or 'true' in required_val.lower()
            
            # Extract default value
            default_value = None
            if default_col >= 0 and default_col < len(columns):
                default_value = columns[default_col].strip()
            
            # Extract enum values from description
            enum_values = self._extract_enum_from_description(param_desc)
            
            # Extract enum references from description (like [BanTypeEnum](/path))
            enum_reference = self._extract_enum_references_from_description(param_desc)
            
            if param_name and param_type:
                param_obj = Parameter(
                    name=param_name.strip('`').replace('\\_', '_'),  # Remove backticks and escape underscores
                    type=param_type,
                    description=param_desc,
                    required=is_required,
                    enum_values=enum_values,
                    default_value=default_value
                )
                
                # Store enum reference if found
                if enum_reference:
                    param_obj.enum_reference = enum_reference
                
                parameters.append(param_obj)
        
        return parameters
    
    def _extract_enum_from_description(self, description: str) -> Optional[List[str]]:
        """Extract enum values from parameter descriptions."""
        if not description:
            return None
        
        # First check for enum references like [BanTypeEnum](/path/to/enum)
        enum_ref_pattern = r'\[(\w*Enum)\]\([^)]+\)'
        enum_ref_matches = re.findall(enum_ref_pattern, description)
        if enum_ref_matches:
            # For enum references, we don't extract specific values here
            # but we note that this parameter references an enum
            return None  # Will be handled by schema references
        
        enum_patterns = [
            # Pattern: Possible values: `value1`, `value2`, `value3`
            r'Possible values?:\s*([`"][^`"]+[`"][,\s]*)+',
            # Pattern: Values can be: value1, value2, value3
            r'Values? can be:\s*([^.]+)',
            # Pattern: Either `value1` or `value2`
            r'Either\s+[`"]([^`"]+)[`"]\s+or\s+[`"]([^`"]+)[`"]',
            # Pattern: `value1`, `value2`, or `value3`
            r'[`"]([^`"]+)[`"](?:,\s*[`"]([^`"]+)[`"])*(?:,?\s*or\s+[`"]([^`"]+)[`"])?'
        ]
        
        for pattern in enum_patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            if matches:
                enum_values = []
                for match in matches:
                    if isinstance(match, tuple):
                        enum_values.extend([v for v in match if v])
                    else:
                        # Extract individual values from the match
                        values = re.findall(r'[`"]([^`"]+)[`"]', match)
                        enum_values.extend(values)
                
                if enum_values:
                    return list(set(enum_values))  # Remove duplicates
        
        return None
    
    def _extract_enum_references_from_description(self, description: str) -> Optional[str]:
        """Extract enum reference names from parameter descriptions."""
        if not description:
            return None
        
        # Pattern for enum references like [BanTypeEnum](/path/to/enum)
        enum_ref_pattern = r'\[(\w*Enum)\]\([^)]+\)'
        enum_ref_matches = re.findall(enum_ref_pattern, description)
        if enum_ref_matches:
            return enum_ref_matches[0]  # Return the first enum reference found
        
        return None

class OpenAPIConverter:
    """Converts method information to OpenAPI specifications."""
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.common_schemas = {}  # Track schemas for reuse
        
        from ..constants import get_config
        config = get_config()
        self.path_mapper = PathMapper(config)
    
    def generate_openapi_spec(self, method_info: Dict[str, Any], version: str = "v2") -> Dict[str, Any]:
        """Generate OpenAPI specification for a single method."""
        method_name = method_info['method_name']
        
        # Create the OpenAPI path specification
        spec = {
            "/api/v2/method": {
                "post": {
                    "operationId": method_name.replace("::", "-"),
                    "summary": method_info.get('title', f"Komodo DeFi Framework Method: {method_name}"),
                    "description": method_info.get('description', f"Method description for {method_name}"),
                    "tags": ["Komodo DeFi Framework API V2"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": self._create_request_body_schema(method_info)
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": self._create_response_schema(method_info)
                                }
                            }
                        },
                        "400": {"description": "Bad request"},
                        "500": {"description": "Internal server error"}
                    }
                }
            }
        }
        
        return spec
    
    def _create_request_body_schema(self, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create request body schema with parameter validation."""
        properties = {
            "method": {
                "type": "string",
                "enum": [method_info['method_name']],
                "description": "The method name"
            },
            "userpass": {
                "type": "string", 
                "description": "RPC password for authentication",
                "example": "RPC_UserP@SSW0RD"
            },
            "mmrpc": {
                "type": "string",
                "enum": ["2.0"],
                "description": "The JSON-RPC version",
                "example": "2.0"
            }
        }
        
        required_fields = ["method", "userpass", "mmrpc"]
        
        # Add parameters if they exist
        if method_info.get('parameters'):
            params_schema = self._create_params_schema(method_info['parameters'])
            if params_schema:
                properties["params"] = params_schema
                required_fields.append("params")
        
        return {
            "type": "object",
            "properties": properties,
            "required": required_fields
        }
    
    def _create_params_schema(self, parameters: List[Parameter]) -> Dict[str, Any]:
        """Create parameters schema from extracted parameters."""
        if not parameters:
            return None
        
        properties = {}
        required_fields = []
        
        for param in parameters:
            param_schema = {
                "description": param.description
            }
            
            # Check for structure references in the description first
            structure_reference = self._extract_structure_references_from_description(param.description)
            
            if structure_reference:
                # Create reference to common structure schema
                param_schema = {
                    "$ref": f"#/components/schemas/{structure_reference}",
                    "description": param.description
                }
            # Add enum reference if detected (like BanTypeEnum)
            elif hasattr(param, 'enum_reference') and param.enum_reference:
                # Create a reference to the common schema
                param_schema = {
                    "$ref": f"#/components/schemas/{param.enum_reference}",
                    "description": param.description
                }
            else:
                # Set type based on parameter type
                if param.type.lower() in ['string', 'str']:
                    param_schema["type"] = "string"
                elif param.type.lower() in ['integer', 'int', 'number']:
                    param_schema["type"] = "integer"
                elif param.type.lower() in ['boolean', 'bool']:
                    param_schema["type"] = "boolean"
                elif param.type.lower() in ['array', 'list']:
                    param_schema["type"] = "array"
                    param_schema["items"] = {"type": "string"}  # Default to string items
                elif param.type.lower() in ['object', 'dict']:
                    param_schema["type"] = "object"
                else:
                    # Handle complex types like "numeric string or rational"
                    if 'string' in param.type.lower():
                        param_schema["type"] = "string"
                    elif 'number' in param.type.lower() or 'numeric' in param.type.lower():
                        param_schema["type"] = "number"
                    else:
                        param_schema["type"] = "string"  # Default fallback
                
                # Add enum values if detected
                if param.enum_values:
                    param_schema["enum"] = param.enum_values
                    # Add example from first enum value
                    param_schema["example"] = param.enum_values[0]
                
                # Add default value if specified
                if param.default_value is not None:
                    param_schema["default"] = param.default_value
            
            properties[param.name] = param_schema
            
            if param.required:
                required_fields.append(param.name)
        
        schema = {
            "type": "object",
            "properties": properties
        }
        
        if required_fields:
            schema["required"] = required_fields
        
        return schema

    def _create_response_schema(self, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create response schema with enum references from response parameters."""
        # Get response parameters from method_info
        response_params = method_info.get('response_parameters', [])
        
        if not response_params:
            # Default response schema
            return {
                "type": "object",
                "properties": {
                    "mmrpc": {
                        "type": "string",
                        "enum": ["2.0"],
                        "description": "The JSON-RPC version"
                    },
                    "result": {
                        "type": "object",
                        "description": "The response result"
                    },
                    "id": {
                        "type": ["integer", "string", "null"],
                        "description": "The request ID"
                    }
                }
            }
        
        # Build response schema from response parameters
        result_properties = {}
        
        for param in response_params:
            param_name = param.get('name', '')
            param_type = param.get('type', 'string')
            param_desc = param.get('description', '')
            
            # Check for structure references in the description
            structure_reference = self._extract_structure_references_from_description(param_desc)
            
            if structure_reference:
                # Create reference to common schema
                result_properties[param_name] = {
                    "$ref": f"#/components/schemas/{structure_reference}",
                    "description": param_desc
                }
            else:
                # Check for enum references in the description
                enum_reference = self._extract_enum_references_from_description(param_desc)
                
                if enum_reference:
                    # Create reference to enum schema
                    result_properties[param_name] = {
                        "$ref": f"#/components/schemas/{enum_reference}",
                        "description": param_desc
                    }
                else:
                    # Regular parameter
                    result_properties[param_name] = {
                        "type": self._map_response_type(param_type),
                        "description": param_desc
                    }
        
        return {
            "type": "object",
            "properties": {
                "mmrpc": {
                    "type": "string",
                    "enum": ["2.0"],
                    "description": "The JSON-RPC version"
                },
                "result": {
                    "type": "object",
                    "properties": result_properties,
                    "description": "The response result"
                },
                "id": {
                    "type": ["integer", "string", "null"],
                    "description": "The request ID"
                }
            }
        }
    
    def _extract_structure_references_from_description(self, description: str) -> Optional[str]:
        """Extract structure reference names from parameter descriptions."""
        if not description:
            return None
        
        # Pattern for structure references like [AddressInfo](/path/to/structure)
        # Look for capitalized structure names that are not enums
        structure_ref_pattern = r'\[([A-Z][a-zA-Z0-9_]*(?:Info|Details|Data|Config|Request|Response|Path|Method))\]\([^)]+\)'
        structure_ref_matches = re.findall(structure_ref_pattern, description)
        if structure_ref_matches:
            return structure_ref_matches[0]  # Return the first structure reference found
        
        # Also check for other common structure patterns
        general_structure_pattern = r'\[([A-Z][a-zA-Z0-9_]*)\]\([^)]+\)'
        general_matches = re.findall(general_structure_pattern, description)
        for match in general_matches:
            # Skip if it's clearly an enum (ends with Enum)
            if match.endswith('Enum'):
                continue
            # Skip if it's a method name (contains ::)
            if '::' in match:
                continue
            return match
        
        return None

    def _map_response_type(self, response_type: str) -> str:
        """Map response parameter types to OpenAPI types."""
        type_mapping = {
            'string': 'string',
            'integer': 'integer',
            'number': 'number',
            'boolean': 'boolean',
            'array': 'array',
            'object': 'object',
            'map of objects': 'object'
        }
        
        # Handle complex types
        lower_type = response_type.lower()
        for key, value in type_mapping.items():
            if key in lower_type:
                return value
        
        return 'string'  # Default fallback

    def _extract_enum_references_from_description(self, description: str) -> Optional[str]:
        """Extract enum reference names from parameter descriptions."""
        if not description:
            return None
        
        # Pattern for enum references like [BanTypeEnum](/path/to/enum)
        enum_ref_pattern = r'\[(\w*Enum)\]\([^)]+\)'
        enum_ref_matches = re.findall(enum_ref_pattern, description)
        if enum_ref_matches:
            return enum_ref_matches[0]  # Return the first enum reference found
        
        return None

    def write_openapi_file(self, spec: Dict[str, Any], method_name: str, version: str, 
                          output_dir: str = None, dry_run: bool = False, mdx_path: str = "") -> str:
        # Use nested structure based on MDX path
        path_mapping = self.path_mapper.get_method_path_mapping(method_name, mdx_path, version)
        file_path = Path(path_mapping.openapi_path)
        
        # Create directory structure
        if not dry_run:
            self.path_mapper.create_directory_structure(path_mapping, dry_run=False)

        if dry_run:
            print(f"[DRY RUN] Would write to: {file_path}")
            return str(file_path)

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            print(f"Generated: {file_path}")
            return str(file_path)
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return ""
    
    def _generate_filename(self, method_name: str) -> str:
        return method_name.replace("::", "_").lower()

    def generate_common_schemas(self, all_enums: Dict[str, Set[str]], output_base: Path):
        """Generate individual schema files for documented enums and reusable components, organized by source page."""
        try:
            schemas_path = output_base / "components" / "schemas"
            schemas_path.mkdir(parents=True, exist_ok=True)
            
            # Extract manually defined enums from the enums documentation
            manual_enums = self._extract_manual_enums_from_docs()
            
            # Create individual files for manually defined enums ONLY
            if manual_enums:
                enums_file = schemas_path / "Enums.yaml"
                with open(enums_file, 'w', encoding='utf-8') as f:
                    yaml.dump(manual_enums, f, default_flow_style=False, sort_keys=False)
                print(f"✅ Generated documented enums schema: {enums_file}")
            
            # Output auto-detected enums to JSON file for review (DO NOT create schemas)
            if all_enums:
                self._output_undocumented_enums_for_review(all_enums, output_base)
            
            # Generate individual structure files from common_structures
            self._generate_individual_structure_files(schemas_path)
            
            print(f"✅ Generated common schemas in: {schemas_path}")
            print(f"   📝 Documented enums: {len(manual_enums)}")
            print(f"   🔍 Auto-detected enums (for review): {len(all_enums)}")
            
        except Exception as e:
            print(f"❌ Error generating common schemas: {e}")
    
    def _output_undocumented_enums_for_review(self, all_enums: Dict[str, Set[str]], output_base: Path):
        """Output auto-detected enums to a JSON file for review, grouped by method."""
        try:
            # Group auto-detected enums by the methods that use them
            undocumented_enums = {}
            
            # Access all_methods from the parent OpenAPIManager instance
            # This method is called from OpenAPIManager, so we need to get the methods from there
            # For now, let's create a simpler report based on the enum data we have
            
            enum_report = {}
            for enum_name, enum_values in all_enums.items():
                enum_report[enum_name] = {
                    "enum_values": sorted(list(enum_values)),
                    "suggested_type": "string",
                    "status": "auto_detected_needs_documentation",
                    "note": "This enum was auto-detected from parameter tables and should be reviewed for inclusion in the official enums documentation"
                }
            
            # Write to JSON file for review
            output_file = output_base / "undocumented_enums.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enum_report, f, indent=2, sort_keys=True)
            
            print(f"📋 Generated undocumented enums report: {output_file}")
            print(f"   🔍 Auto-detected enums for review: {len(enum_report)}")
            
        except Exception as e:
            print(f"⚠️  Error generating undocumented enums report: {e}")
    
    def _generate_individual_structure_files(self, schemas_path: Path):
        """Generate individual YAML files for each common structure."""
        try:
            # Look for structure files in common_structures
            structures_base = self.base_path / "src" / "pages" / "komodo-defi-framework" / "api" / "common_structures"
            
            if not structures_base.exists():
                return
            
            # Process each structure directory
            for structure_dir in structures_base.iterdir():
                if structure_dir.is_dir() and structure_dir.name != "enums":
                    self._create_structure_schema_file(structure_dir, schemas_path)
                    
        except Exception as e:
            print(f"⚠️  Error generating individual structure files: {e}")
    
    def _create_structure_schema_file(self, structure_dir: Path, schemas_path: Path):
        """Create a schema file for a specific structure."""
        try:
            structure_name = structure_dir.name.title()
            index_file = structure_dir / "index.mdx"
            
            if not index_file.exists():
                return
            
            # Parse the structure documentation
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse actual structure definitions from the MDX content
            structures = self._parse_structure_definitions(content)
            
            if not structures:
                print(f"⚠️  No structures found in {structure_name}")
                return
            
            # Write the structure schema file
            output_file = schemas_path / f"{structure_name}.yaml"
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(structures, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Generated structure schema: {output_file} ({len(structures)} structures)")
            
        except Exception as e:
            print(f"⚠️  Error creating schema for {structure_dir.name}: {e}")

    def _parse_structure_definitions(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Parse structure definitions from MDX content."""
        structures = {}
        
        # Pattern to match structure definitions: ### StructureName
        structure_pattern = r'###\s+([A-Z][a-zA-Z0-9_]*)\s*\n(.*?)(?=\n###|\n##|\Z)'
        structure_matches = re.findall(structure_pattern, content, re.DOTALL)
        
        for structure_name, structure_content in structure_matches:
            # Skip if this looks like a heading rather than a structure
            if any(skip_word in structure_name.lower() for skip_word in ['example', 'note', 'warning']):
                continue
            
            # Parse the structure's parameter table
            structure_schema = self._parse_structure_table(structure_content, structure_name)
            
            if structure_schema:
                structures[structure_name] = structure_schema
        
        return structures
    
    def _parse_structure_table(self, structure_content: str, structure_name: str) -> Dict[str, Any]:
        """Parse a structure's parameter table into OpenAPI schema."""
        # Split content into lines for better table parsing
        lines = structure_content.strip().split('\n')
        
        properties = {}
        required_fields = []
        description_lines = []
        
        # Extract description from the content before the table
        table_start = -1
        for i, line in enumerate(lines):
            if '|' in line and ('Parameter' in line or 'parameter' in line):
                table_start = i
                break
        
        if table_start > 0:
            # Get description from lines before the table
            desc_lines = lines[:table_start]
            desc_text = ' '.join(desc_lines).strip()
            # Clean up description
            desc_text = re.sub(r'<[^>]+>', '', desc_text)  # Remove HTML tags
            desc_text = re.sub(r'\n+', ' ', desc_text).strip()
            if desc_text and not desc_text.startswith('|'):
                description_lines.append(desc_text)
        
        if table_start == -1:
            return None
        
        # Find table structure
        header_line = None
        separator_line = None
        data_start = -1
        
        for i in range(table_start, len(lines)):
            line = lines[i].strip()
            if not line:
                continue
                
            if '|' in line:
                if 'Parameter' in line or 'parameter' in line:
                    header_line = line
                    header_idx = i
                elif '---' in line or ':-' in line:
                    separator_line = line
                    data_start = i + 1
                    break
        
        if not header_line or data_start == -1:
            return None
        
        # Parse header to understand column structure
        header_cells = [cell.strip() for cell in header_line.split('|') if cell.strip()]
        
        # Find column indices
        param_col = -1
        type_col = -1
        required_col = -1
        default_col = -1
        desc_col = -1
        
        for i, header in enumerate(header_cells):
            header_lower = header.lower()
            if 'parameter' in header_lower:
                param_col = i
            elif 'type' in header_lower:
                type_col = i
            elif 'required' in header_lower:
                required_col = i
            elif 'default' in header_lower:
                default_col = i
            elif 'description' in header_lower:
                desc_col = i
        
        # Parse data rows
        for i in range(data_start, len(lines)):
            line = lines[i].strip()
            if not line or not line.startswith('|') or not line.endswith('|'):
                continue
            
            # Split the row into columns, removing empty first/last elements
            cells = [cell.strip() for cell in line.split('|')]
            if cells and not cells[0]:
                cells = cells[1:]
            if cells and not cells[-1]:
                cells = cells[:-1]
            
            if len(cells) < 3:  # Need at least parameter, type, description
                continue
            
            # Extract parameter information based on column positions
            param_name = cells[param_col] if param_col < len(cells) else ""
            param_type = cells[type_col] if type_col < len(cells) else ""
            
            # Handle required column
            is_required = False
            if required_col >= 0 and required_col < len(cells):
                required_val = cells[required_col].strip()
                is_required = '✓' in required_val or 'true' in required_val.lower()
            
            # Handle default column
            default_value = ""
            if default_col >= 0 and default_col < len(cells):
                default_value = cells[default_col].strip()
            
            # Handle description column
            param_desc = ""
            if desc_col >= 0 and desc_col < len(cells):
                param_desc = cells[desc_col].strip()
            elif len(cells) > max(param_col, type_col) + 1:
                # If no explicit description column, use the last column
                param_desc = cells[-1].strip()
            
            # Handle different table formats (some tables have 4 columns, some have 5)
            if not param_desc and len(cells) >= 4:
                if default_col == -1:
                    # 4-column format: Parameter | Type | Required | Description
                    param_desc = default_value
                    default_value = ""
            
            # Skip empty or invalid rows
            if not param_name or param_name in ['', '-'] or 'Parameter' in param_name:
                continue
            
            # Clean parameter name
            param_name = param_name.strip('`').replace('\\_', '_')
            
            # Create parameter schema
            param_schema = self._create_parameter_schema(param_type, param_desc, default_value)
            
            properties[param_name] = param_schema
            
            if is_required:
                required_fields.append(param_name)
        
        if not properties:
            return None
        
        # Build the complete schema
        schema = {
            "type": "object",
            "properties": properties
        }
        
        if required_fields:
            schema["required"] = required_fields
        
        if description_lines:
            schema["description"] = " ".join(description_lines)
        else:
            schema["description"] = f"Schema definition for {structure_name}"
        
        return schema
    
    def _create_parameter_schema(self, param_type: str, param_desc: str, default_value: str = "") -> Dict[str, Any]:
        """Create OpenAPI schema for a parameter based on its type and description."""
        schema = {"description": param_desc}
        
        # Handle references to other structures
        ref_pattern = r'\[([A-Z][a-zA-Z0-9_]*)\]\([^)]+\)'
        ref_matches = re.findall(ref_pattern, param_desc)
        
        if ref_matches:
            # This parameter references another structure
            referenced_structure = ref_matches[0]
            schema = {
                "$ref": f"#/components/schemas/{referenced_structure}",
                "description": param_desc
            }
            return schema
        
        # Map parameter types to OpenAPI types
        param_type_lower = param_type.lower().strip()
        
        if 'string' in param_type_lower:
            schema["type"] = "string"
            # Check for enum values in parentheses
            enum_match = re.search(r'\(([^)]+)\)', param_type)
            if enum_match:
                enum_values = [v.strip().strip('`"\'') for v in enum_match.group(1).split('|')]
                schema["enum"] = enum_values
        elif 'integer' in param_type_lower or 'int' in param_type_lower:
            schema["type"] = "integer"
        elif 'number' in param_type_lower or 'float' in param_type_lower or 'numeric' in param_type_lower:
            schema["type"] = "number"
        elif 'boolean' in param_type_lower or 'bool' in param_type_lower:
            schema["type"] = "boolean"
        elif 'array' in param_type_lower or 'list' in param_type_lower:
            schema["type"] = "array"
            # Try to determine array item type
            if 'string' in param_type_lower:
                schema["items"] = {"type": "string"}
            elif 'object' in param_type_lower:
                schema["items"] = {"type": "object"}
            else:
                schema["items"] = {"type": "string"}  # Default
        elif 'object' in param_type_lower:
            schema["type"] = "object"
        else:
            # Default to string for unknown types
            schema["type"] = "string"
        
        # Add default value if specified
        if default_value and default_value not in ['-', '`-`', '']:
            clean_default = default_value.strip('`"\'')
            if schema["type"] == "boolean":
                schema["default"] = clean_default.lower() == 'true'
            elif schema["type"] == "integer":
                try:
                    schema["default"] = int(clean_default)
                except ValueError:
                    pass
            elif schema["type"] == "number":
                try:
                    schema["default"] = float(clean_default)
                except ValueError:
                    pass
            else:
                schema["default"] = clean_default
        
        return schema

    def _extract_manual_enums_from_docs(self) -> Dict[str, Dict[str, Any]]:
        """Extract manually defined enums from the enums documentation."""
        manual_enums = {}
        
        # Look for the enums documentation file
        enums_file = self.base_path / "src" / "pages" / "komodo-defi-framework" / "api" / "common_structures" / "enums" / "index.mdx"
        
        if not enums_file.exists():
            return manual_enums
        
        try:
            with open(enums_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract enum definitions using regex
            # Pattern: ### EnumName followed by table with Value column
            enum_pattern = r'###\s+(\w+Enum)\s*\n.*?\n\n(.*?)(?=\n###|\n##|\Z)'
            enum_matches = re.findall(enum_pattern, content, re.DOTALL)
            
            for enum_name, enum_content in enum_matches:
                enum_values = self._parse_enum_values_from_table(enum_content)
                if enum_values:
                    manual_enums[enum_name] = {
                        "type": "string",
                        "enum": enum_values,
                        "description": f"Manually defined enum for {enum_name.replace('Enum', '').lower()} values"
                    }
            
        except Exception as e:
            print(f"⚠️  Error extracting manual enums: {e}")
        
        return manual_enums
    
    def _parse_enum_values_from_table(self, table_content: str) -> List[str]:
        """Parse enum values from a markdown table."""
        enum_values = []
        
        lines = table_content.strip().split('\n')
        
        # Find table rows with | Value | Description |
        for line in lines:
            if '|' in line and not ('---' in line or 'Value' in line or 'Description' in line):
                columns = [col.strip() for col in line.split('|')]
                if len(columns) >= 3:  # | Value | Description |
                    value = columns[1].strip().strip('`')
                    if value and value not in ['-', '']:
                        enum_values.append(value)
        
        return enum_values

    def _generate_category_specs(self, all_methods: Dict[str, Dict], version: str):
        """Generate category-specific OpenAPI specifications."""
        try:
            # Group methods by category
            categories = defaultdict(list)
            
            for method_name, method_info in all_methods.items():
                # Extract category from method name (e.g., "coin_activation::enable_bch" -> "coin_activation")
                if "::" in method_name:
                    category = method_name.split("::")[0]
                else:
                    category = "general"
                
                categories[category].append(method_info)
            
            # Generate a spec file for each category
            for category, methods in categories.items():
                self._generate_category_spec_file(category, methods, version)
                
        except Exception as e:
            print(f"❌ Error generating category specs: {e}")
    
    def _generate_category_spec_file(self, category: str, methods: List[Dict], version: str):
        """Generate OpenAPI spec file for a specific category."""
        try:
            output_file = self.base_path / "openapi" / f"{category}_generated.yaml"
            
            # Create category-specific OpenAPI spec
            spec = {
                "openapi": "3.0.3",
                "info": {
                    "title": f"Komodo DeFi Framework {category.title()} API",
                    "version": "2.0.0",
                    "description": f"Focused OpenAPI specification for {category} endpoints in the Komodo DeFi Framework.\n\nFor the complete API specification, see the main openapi.yaml file."
                },
                "servers": [
                    {
                        "url": "/",
                        "description": "Local Komodo DeFi Framework instance"
                    }
                ],
                "tags": [
                    {
                        "name": category.replace("_", " ").title(),
                        "description": f"Methods for {category.replace('_', ' ')}"
                    }
                ],
                "paths": {},
                "components": {
                    "securitySchemes": {
                        "userpass": {
                            "type": "apiKey",
                            "in": "header", 
                            "name": "userpass",
                            "description": "The API key for authentication. Use the 'userpass' value from your \nKomodo DeFi Framework instance configuration.\n"
                        }
                    },
                    "schemas": {
                        "Common": {"$ref": "./components/schemas/Common.yaml"},
                        "Activation": {"$ref": "./components/schemas/Activation.yaml"}
                    }
                },
                "security": [{"userpass": []}]
            }
            
            # Add paths for each method
            for method_info in methods:
                method_name = method_info['method_name']
                # Create a simplified path reference
                path_key = f"/v2/{method_name.replace('::', '_')}"
                spec["paths"][path_key] = {
                    "$ref": f"./paths/v2/{method_name.replace('::', '/')}.yaml"
                }
            
            # Write the spec file
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Generated category spec: {output_file}")
            
        except Exception as e:
            print(f"❌ Error generating {category} spec: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about generated OpenAPI specs."""
        stats = {
            "total_methods": len(self.all_methods),
            "methods_with_enums": 0,
            "common_schemas": 0,
            "enum_patterns": {}
        }
        
        # Count methods with enums
        for method_info in self.all_methods.values():
            # method_info is a dictionary, not a MethodInfo object
            parameters = method_info.get('parameters', [])
            method_has_enums = False
            
            for param in parameters:
                # param is a Parameter object with enum_values attribute
                if hasattr(param, 'enum_values') and param.enum_values:
                    method_has_enums = True
                    enum_key = tuple(sorted(param.enum_values))
                    if enum_key not in stats["enum_patterns"]:
                        stats["enum_patterns"][enum_key] = 0
                    stats["enum_patterns"][enum_key] += 1
            
            if method_has_enums:
                stats["methods_with_enums"] += 1
        
        # Check for generated common schemas
        generated_schemas_file = self.base_path / "openapi" / "paths" / "components" / "schemas" / "Enums.yaml"
        if generated_schemas_file.exists():
            try:
                with open(generated_schemas_file, 'r') as f:
                    generated_schemas = yaml.safe_load(f)
                    # Count non-comment entries
                    stats["common_schemas"] = len([k for k in generated_schemas.keys() if not k.startswith('#')])
            except Exception:
                pass
        
        return stats

    def _generate_openapi_tracking_files(self, version: str, success_count: int, error_count: int, 
                                       all_enums: Dict[str, Set[str]], structures_count: int, 
                                       enums_count: int, source_dirs: List[str]) -> None:
        """Generate tracking JSON files for the OpenAPI generation process."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = self.base_path / "utils" / "py" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate method paths tracking file
            self._generate_openapi_method_paths_file(timestamp, data_dir)
            
            # Generate methods tracking file
            self._generate_openapi_methods_file(timestamp, data_dir, version, success_count, 
                                              error_count, all_enums, structures_count, 
                                              enums_count, source_dirs)
            
        except Exception as e:
            print(f"⚠️  Error generating tracking files: {e}")
    
    def _generate_openapi_method_paths_file(self, timestamp: str, data_dir: Path) -> None:
        """Generate kdf_openapi_method_paths_{timestamp}.json file."""
        try:
            # Collect method paths from all processed methods
            method_paths = {"v1": {}, "v2": {}}
            total_documented_methods = 0
            
            for composite_key, method_info in self.all_methods.items():
                file_path = method_info.get('file_path', '')
                
                # Extract version and method name from composite key
                if composite_key.startswith("v1::"):
                    version_key = "v1"
                    method_name = composite_key[4:]  # Remove "v1::" prefix
                elif composite_key.startswith("v2::"):
                    version_key = "v2"
                    method_name = composite_key[4:]  # Remove "v2::" prefix
                else:
                    # Skip common structures and other non-versioned entries
                    continue
                
                # Construct path to generated OpenAPI YAML file instead of MDX source
                # Convert MDX path to OpenAPI YAML path based on the nested structure
                # Example: src/pages/.../api/v20/coin_activation/task_managed/enable_eth/init/index.mdx
                # Becomes: openapi/paths/v2/coin_activation/task_managed/enable_eth/init/index.yaml
                
                # Extract the relative path from the MDX structure and convert to OpenAPI structure
                if version_key == "v1":
                    # v1 methods are in legacy directory
                    if '/legacy/' in file_path:
                        # Extract path after /legacy/ and before /index.mdx
                        relative_part = file_path.split('/legacy/')[1].replace('/index.mdx', '')
                        openapi_path = f"../../openapi/paths/v1/{relative_part}/index.yaml"
                    else:
                        continue
                else:  # v2
                    # v2 methods are in v20 or v20-dev directories
                    if '/v20/' in file_path:
                        relative_part = file_path.split('/v20/')[1].replace('/index.mdx', '')
                        openapi_path = f"../../openapi/paths/v2/{relative_part}/index.yaml"
                    elif '/v20-dev/' in file_path:
                        relative_part = file_path.split('/v20-dev/')[1].replace('/index.mdx', '')
                        openapi_path = f"../../openapi/paths/v2/{relative_part}/index.yaml"
                    else:
                        continue
                
                method_paths[version_key][method_name] = openapi_path
                total_documented_methods += 1
            
            # Sort method paths alphabetically within each version
            for version_key in method_paths:
                method_paths[version_key] = dict(sorted(method_paths[version_key].items()))
            
            # Create the tracking data structure
            tracking_data = {
                "scan_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "scanner_version": "OpenAPIManager v1.0.0",
                    "scanner_type": "OPENAPI_METHOD_PATH_MAPPING",
                    "total_versions": 2,
                    "total_methods_with_openapi_paths": len(self.all_methods),
                    "versions_processed": ["v1", "v2"],
                    "includes_gap_analysis": False,
                    "generated_during_openapi_generation": True,
                    "total_documented_methods": total_documented_methods
                },
                "method_paths": method_paths,
                "openapi_generation_info": {
                    "output_format": "OpenAPI 3.0.3 YAML",
                    "includes_common_structures": True,
                    "includes_documented_enums": True,
                    "structure_organization": "nested_by_functional_area",
                    "paths_point_to": "OpenAPI YAML output files (not MDX source files)"
                }
            }
            
            # Write the file
            output_file = data_dir / f"kdf_openapi_method_paths_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, sort_keys=False)
            
            print(f"📋 Generated OpenAPI method paths tracking: {output_file}")
            
        except Exception as e:
            print(f"⚠️  Error generating OpenAPI method paths file: {e}")
    
    def _generate_openapi_methods_file(self, timestamp: str, data_dir: Path, version: str,
                                     success_count: int, error_count: int, all_enums: Dict[str, Set[str]],
                                     structures_count: int, enums_count: int, source_dirs: List[str]) -> None:
        """Generate kdf_openapi_methods_{timestamp}.json file."""
        try:
            # Organize methods by version
            methods_by_version = {"v1": [], "v2": []}
            
            for composite_key, method_info in self.all_methods.items():
                # Extract version and method name from composite key
                if composite_key.startswith("v1::"):
                    method_name = composite_key[4:]  # Remove "v1::" prefix
                    methods_by_version["v1"].append(method_name)
                elif composite_key.startswith("v2::"):
                    method_name = composite_key[4:]  # Remove "v2::" prefix
                    methods_by_version["v2"].append(method_name)
                # Skip common structures for method counting
            
            # Sort method lists
            for version_key in methods_by_version:
                methods_by_version[version_key].sort()
            
            # Create the tracking data structure
            tracking_data = {
                "scan_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "scanner_version": "OpenAPIManager v1.0.0",
                    "scanner_type": "OPENAPI_METHODS",
                    "total_versions": 2,
                    "total_methods": len(self.all_methods),
                    "includes_openapi_generation_stats": True
                },
                "repository_data": {
                    "v1": {
                        "branch": "openapi_generation",
                        "version": "v1",
                        "source_type": "OPENAPI_GENERATED",
                        "methods": methods_by_version["v1"],
                        "last_updated": datetime.now().isoformat(),
                        "extraction_patterns_used": [
                            "MDX file parsing",
                            "Parameter table extraction",
                            "Response schema generation",
                            "Common structure references"
                        ]
                    },
                    "v2": {
                        "branch": "openapi_generation", 
                        "version": "v2",
                        "source_type": "OPENAPI_GENERATED",
                        "methods": methods_by_version["v2"],
                        "last_updated": datetime.now().isoformat(),
                        "extraction_patterns_used": [
                            "MDX file parsing",
                            "Parameter table extraction", 
                            "Response schema generation",
                            "Common structure references"
                        ]
                    }
                },
                "generation_statistics": {
                    "total_files_processed": success_count,
                    "total_errors": error_count,
                    "common_structures_processed": structures_count,
                    "documented_enums_processed": enums_count,
                    "auto_detected_enums": len(all_enums),
                    "source_directories": source_dirs,
                    "output_format": "OpenAPI 3.0.3 YAML",
                    "schema_organization": "individual_files_by_category"
                }
            }
            
            # Write the file
            output_file = data_dir / f"kdf_openapi_methods_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, sort_keys=False)
            
            print(f"📋 Generated OpenAPI methods tracking: {output_file}")
            
        except Exception as e:
            print(f"⚠️  Error generating OpenAPI methods file: {e}")

class OpenAPIManager:
    """
    Comprehensive OpenAPI Manager
    
    Handles both:
    1. Converting MDX files to OpenAPI specifications (MDX -> OpenAPI)
    2. Managing existing OpenAPI specification files (spec management)
    
    MERGED: Combined MDXToOpenAPIConverter and original OpenAPIManager functionality
    """
    
    def __init__(self, base_path: str = ".", main_openapi_file: str = None, 
                 yaml_dirs: Dict[str, str] = None, verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        
        # MDX to OpenAPI conversion components
        self.parser = MDXParser(base_path)
        self.converter = OpenAPIConverter(base_path)
        
        # OpenAPI spec management components
        self.main_openapi_file = main_openapi_file or "../../openapi/openapi.yaml"
        self.yaml_dirs = yaml_dirs or {
            'v1': '../../openapi/paths/v1',
            'v2': '../../openapi/paths/v2'
        }
        
        # Initialize async processor for performance
        self.async_processor = None
        
        # Initialize mapper for method mapping functionality
        self.mapper = None
        
        self.all_methods = {}  # Store all parsed methods for common schema generation

    def generate_openapi_spec(self, version: str = "v2") -> str:
        """
        Generate OpenAPI specifications for the specified version.
        
        Args:
            version: API version to generate specs for
            
        Returns:
            Status message indicating success or failure
        """
        try:
            success_count = 0
            error_count = 0
            
            # Use centralized version mapping configuration
            from ..constants.config import get_config
            config = get_config()
            
            # Get source directories from centralized configuration
            source_versions = config.get_openapi_sources(version)
            output_version = config.get_canonical_version(version)
            
            # Always include common structures and enums for all versions
            common_structures_dirs = ["common_structures"]
            all_source_dirs = source_versions + common_structures_dirs
            
            output_path = self.base_path / "openapi" / "paths" / output_version
            
            print(f"📂 Processing version: {version}")
            print(f"📁 Source directories: {', '.join(source_versions)}")
            print(f"📁 Common structures: {', '.join(common_structures_dirs)}")
            print(f"📁 Output directory: {output_path}")
            
            # Ensure output directory exists
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Process each MDX file from all source directories
            # Store as instance variables for statistics
            self.all_methods = {}
            all_enums = defaultdict(set)
            total_mdx_files = 0
            structures_count = 0
            enums_count = 0
            
            for source_dir in all_source_dirs:
                source_path = self.base_path / "src" / "pages" / "komodo-defi-framework" / "api" / source_dir
                
                if not source_path.exists():
                    print(f"⚠️  Source path not found: {source_path} (skipping)")
                    continue
                
                # Find all MDX files in this source directory
                mdx_files = list(source_path.rglob("index.mdx"))
                total_mdx_files += len(mdx_files)
                
                # Categorize files for better reporting
                if source_dir == "common_structures":
                    structures_count = len(mdx_files)
                    print(f"📋 Found {len(mdx_files)} structure/enum files in {source_dir}")
                else:
                    print(f"🔍 Found {len(mdx_files)} method files in {source_dir}")
                
                for mdx_file in mdx_files:
                    try:
                        # Parse the MDX file
                        method_info = self.parser.parse_mdx_file(mdx_file)
                        if not method_info:
                            continue
                        
                        # Store method info for common schema generation and statistics
                        method_name = method_info['method_name']
                        
                        # Determine version based on source directory to create unique keys
                        if source_dir in ["legacy"]:
                            version_key = "v1"
                            composite_key = f"v1::{method_name}"
                        elif source_dir in ["v20", "v20-dev"]:
                            version_key = "v2"
                            composite_key = f"v2::{method_name}"
                        else:
                            # For common structures, use the method name as-is
                            composite_key = method_name
                            version_key = None
                        
                        # Store with composite key to avoid v1/v2 collisions
                        self.all_methods[composite_key] = method_info
                        
                        # Collect enum values for common schema generation
                        for param in method_info.get('parameters', []):
                            if param.enum_values:
                                enum_name = f"{param.name.title()}Enum"
                                all_enums[enum_name].update(param.enum_values)
                        
                        # Generate OpenAPI spec for this method/structure
                        openapi_spec = self.converter.generate_openapi_spec(method_info, output_version)
                        
                        # Determine output file path (preserve relative structure from source)
                        if source_dir == "common_structures":
                            # For common structures, place them in a structures subdirectory
                            relative_path = mdx_file.relative_to(source_path)
                            output_file = output_path / "structures" / relative_path.parent / "index.yaml"
                        else:
                            # For methods, use the normal structure
                            relative_path = mdx_file.relative_to(source_path)
                            output_file = output_path / relative_path.parent / "index.yaml"
                        
                        # Ensure output directory exists
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Write the OpenAPI spec
                        with open(output_file, 'w', encoding='utf-8') as f:
                            yaml.dump(openapi_spec, f, default_flow_style=False, sort_keys=False)
                        
                        success_count += 1
                        
                        # Count enums specifically
                        if source_dir == "common_structures" and "enums" in str(mdx_file):
                            enums_count += 1
                            print(f"📝 Generated enum spec: {output_file}")
                        elif source_dir == "common_structures":
                            print(f"🏗️  Generated structure spec: {output_file}")
                        else:
                            print(f"✅ Generated method spec: {output_file}")
                        
                    except Exception as e:
                        error_count += 1
                        print(f"❌ Error processing {mdx_file}: {e}")
            
            # Generate common schemas if we found enums
            if all_enums:
                self.converter.generate_common_schemas(all_enums, output_path.parent)
            
            # Generate tracking files for this OpenAPI generation run
            self._generate_openapi_tracking_files(
                version=output_version,
                success_count=success_count,
                error_count=error_count,
                all_enums=all_enums,
                structures_count=structures_count,
                enums_count=enums_count,
                source_dirs=all_source_dirs
            )
            
            result_msg = f"✅ OpenAPI generation completed!\n"
            result_msg += f"   📊 Successfully processed: {success_count} files\n"
            result_msg += f"   ❌ Errors: {error_count} files\n"
            result_msg += f"   🔧 Generated {len(all_enums)} common enum schemas\n"
            result_msg += f"   📁 Total MDX files found: {total_mdx_files}\n"
            result_msg += f"   🏗️  Structure files: {structures_count}\n"
            result_msg += f"   📝 Enum files: {enums_count}\n"
            result_msg += f"   📂 Source directories: {', '.join(all_source_dirs)}\n"
            result_msg += f"   📁 Output directory: {output_path}"
            
            return result_msg
            
        except Exception as e:
            error_msg = f"❌ OpenAPI generation failed: {str(e)}"
            print(error_msg)
            return error_msg

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about generated OpenAPI specs - placeholder for compatibility."""
        return {
            "total_methods": 0,
            "methods_with_enums": 0,
            "common_schemas": 0,
            "enum_patterns": {}
        }

    def _generate_openapi_tracking_files(self, version: str, success_count: int, error_count: int, 
                                       all_enums: Dict[str, Set[str]], structures_count: int, 
                                       enums_count: int, source_dirs: List[str]) -> None:
        """Generate tracking JSON files for the OpenAPI generation process."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = self.base_path / "utils" / "py" / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate method paths tracking file
            self._generate_openapi_method_paths_file(timestamp, data_dir)
            
            # Generate methods tracking file
            self._generate_openapi_methods_file(timestamp, data_dir, version, success_count, 
                                              error_count, all_enums, structures_count, 
                                              enums_count, source_dirs)
            
        except Exception as e:
            print(f"⚠️  Error generating tracking files: {e}")
    
    def _generate_openapi_method_paths_file(self, timestamp: str, data_dir: Path) -> None:
        """Generate kdf_openapi_method_paths_{timestamp}.json file."""
        try:
            # Collect method paths from all processed methods
            method_paths = {"v1": {}, "v2": {}}
            total_documented_methods = 0
            
            for composite_key, method_info in self.all_methods.items():
                file_path = method_info.get('file_path', '')
                
                # Extract version and method name from composite key
                if composite_key.startswith("v1::"):
                    version_key = "v1"
                    method_name = composite_key[4:]  # Remove "v1::" prefix
                elif composite_key.startswith("v2::"):
                    version_key = "v2"
                    method_name = composite_key[4:]  # Remove "v2::" prefix
                else:
                    # Skip common structures and other non-versioned entries
                    continue
                
                # Construct path to generated OpenAPI YAML file instead of MDX source
                # Convert MDX path to OpenAPI YAML path based on the nested structure
                # Example: src/pages/.../api/v20/coin_activation/task_managed/enable_eth/init/index.mdx
                # Becomes: openapi/paths/v2/coin_activation/task_managed/enable_eth/init/index.yaml
                
                # Extract the relative path from the MDX structure and convert to OpenAPI structure
                if version_key == "v1":
                    # v1 methods are in legacy directory
                    if '/legacy/' in file_path:
                        # Extract path after /legacy/ and before /index.mdx
                        relative_part = file_path.split('/legacy/')[1].replace('/index.mdx', '')
                        openapi_path = f"../../openapi/paths/v1/{relative_part}/index.yaml"
                    else:
                        continue
                else:  # v2
                    # v2 methods are in v20 or v20-dev directories
                    if '/v20/' in file_path:
                        relative_part = file_path.split('/v20/')[1].replace('/index.mdx', '')
                        openapi_path = f"../../openapi/paths/v2/{relative_part}/index.yaml"
                    elif '/v20-dev/' in file_path:
                        relative_part = file_path.split('/v20-dev/')[1].replace('/index.mdx', '')
                        openapi_path = f"../../openapi/paths/v2/{relative_part}/index.yaml"
                    else:
                        continue
                
                method_paths[version_key][method_name] = openapi_path
                total_documented_methods += 1
            
            # Sort method paths alphabetically within each version
            for version_key in method_paths:
                method_paths[version_key] = dict(sorted(method_paths[version_key].items()))
            
            # Create the tracking data structure
            tracking_data = {
                "scan_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "scanner_version": "OpenAPIManager v1.0.0",
                    "scanner_type": "OPENAPI_METHOD_PATH_MAPPING",
                    "total_versions": 2,
                    "total_methods_with_openapi_paths": len(self.all_methods),
                    "versions_processed": ["v1", "v2"],
                    "includes_gap_analysis": False,
                    "generated_during_openapi_generation": True,
                    "total_documented_methods": total_documented_methods
                },
                "method_paths": method_paths,
                "openapi_generation_info": {
                    "output_format": "OpenAPI 3.0.3 YAML",
                    "includes_common_structures": True,
                    "includes_documented_enums": True,
                    "structure_organization": "nested_by_functional_area",
                    "paths_point_to": "OpenAPI YAML output files (not MDX source files)"
                }
            }
            
            # Write the file
            output_file = data_dir / f"kdf_openapi_method_paths_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, sort_keys=False)
            
            print(f"📋 Generated OpenAPI method paths tracking: {output_file}")
            
        except Exception as e:
            print(f"⚠️  Error generating OpenAPI method paths file: {e}")
    
    def _generate_openapi_methods_file(self, timestamp: str, data_dir: Path, version: str,
                                     success_count: int, error_count: int, all_enums: Dict[str, Set[str]],
                                     structures_count: int, enums_count: int, source_dirs: List[str]) -> None:
        """Generate kdf_openapi_methods_{timestamp}.json file."""
        try:
            # Organize methods by version
            methods_by_version = {"v1": [], "v2": []}
            
            for composite_key, method_info in self.all_methods.items():
                # Extract version and method name from composite key
                if composite_key.startswith("v1::"):
                    method_name = composite_key[4:]  # Remove "v1::" prefix
                    methods_by_version["v1"].append(method_name)
                elif composite_key.startswith("v2::"):
                    method_name = composite_key[4:]  # Remove "v2::" prefix
                    methods_by_version["v2"].append(method_name)
                # Skip common structures for method counting
            
            # Sort method lists
            for version_key in methods_by_version:
                methods_by_version[version_key].sort()
            
            # Create the tracking data structure
            tracking_data = {
                "scan_metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "scanner_version": "OpenAPIManager v1.0.0",
                    "scanner_type": "OPENAPI_METHODS",
                    "total_versions": 2,
                    "total_methods": len(self.all_methods),
                    "includes_openapi_generation_stats": True
                },
                "repository_data": {
                    "v1": {
                        "branch": "openapi_generation",
                        "version": "v1",
                        "source_type": "OPENAPI_GENERATED",
                        "methods": methods_by_version["v1"],
                        "last_updated": datetime.now().isoformat(),
                        "extraction_patterns_used": [
                            "MDX file parsing",
                            "Parameter table extraction",
                            "Response schema generation",
                            "Common structure references"
                        ]
                    },
                    "v2": {
                        "branch": "openapi_generation", 
                        "version": "v2",
                        "source_type": "OPENAPI_GENERATED",
                        "methods": methods_by_version["v2"],
                        "last_updated": datetime.now().isoformat(),
                        "extraction_patterns_used": [
                            "MDX file parsing",
                            "Parameter table extraction", 
                            "Response schema generation",
                            "Common structure references"
                        ]
                    }
                },
                "generation_statistics": {
                    "total_files_processed": success_count,
                    "total_errors": error_count,
                    "common_structures_processed": structures_count,
                    "documented_enums_processed": enums_count,
                    "auto_detected_enums": len(all_enums),
                    "source_directories": source_dirs,
                    "output_format": "OpenAPI 3.0.3 YAML",
                    "schema_organization": "individual_files_by_category"
                }
            }
            
            # Write the file
            output_file = data_dir / f"kdf_openapi_methods_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(tracking_data, f, indent=2, sort_keys=False)
            
            print(f"📋 Generated OpenAPI methods tracking: {output_file}")
            
        except Exception as e:
            print(f"⚠️  Error generating OpenAPI methods file: {e}")

    # ... existing tracking methods ...