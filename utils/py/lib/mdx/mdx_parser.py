#!/usr/bin/env python3
"""
MDX Parser

This module contains the MDXParser class, responsible for parsing MDX files
to extract API method information, including parameters, descriptions, and titles.
It is designed to handle the specific structure of Komodo DeFi Framework documentation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass

# Import path utilities
from ..constants.config import get_config
from ..utils.path_utils import EnhancedPathMapper
from ..constants import UnifiedParameterInfo as Parameter, UnifiedMethodInfo as MethodInfo


# Create a simple Response class for backward compatibility
@dataclass
class Response:
    """Simple response class for OpenAPI generation."""
    status_code: str
    description: str


class MDXParser:
    """Parser for MDX files to extract API method information."""
    def __init__(self):
        self.config = get_config()
        self.path_mapper = EnhancedPathMapper()
        self.base_path = Path(self.config.workspace_root)
        # Track common structures across all parsed methods
        self.common_structures = defaultdict(int)
        self.enum_patterns = defaultdict(set)

    def parse_mdx_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        # TEST COMMENT
        """Parse an MDX file and extract method information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if 'common_structures/enums' in str(file_path):
                return self._parse_enum_file(content, file_path)
            elif 'common_structures' in str(file_path):
                return self._parse_structure_file(content, file_path)
            else:
                return self._parse_method_file(content, file_path)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def _parse_enum_file(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parses an MDX file containing an enum definition."""
        enum_name_match = re.search(r'#\s+([a-zA-Z0-9_]+)', content)
        if enum_name_match:
            enum_name = enum_name_match.group(1)
            self.enum_patterns[enum_name] = set() # Placeholder for actual enum values
            return {"type": "enum", "name": enum_name, "file_path": str(file_path)}
        return None

    def _parse_structure_file(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parses an MDX file containing a common structure definition."""
        structure_name_match = re.search(r'#\s+([a-zA-Z0-9_]+)', content)
        if structure_name_match:
            structure_name = structure_name_match.group(1)
            self.common_structures[structure_name] += 1
            return {"type": "structure", "name": structure_name, "file_path": str(file_path)}
        return None

    def _parse_method_file(self, content: str, file_path: Path) -> Optional[Dict[str, Any]]:
        """Parse an MDX file for method information."""
        # If the file is tagged as an overview, skip it.
        if "tag : 'overview'" in content:
            return None

        method_match = re.search(r'^##\s+([^\s{]+)', content, re.MULTILINE)
        if not method_match:
            return None

        method_name = method_match.group(1).replace('\\_', '_')

        title_match = re.search(r'export const title = ["\']([^"\']+)["\']', content)
        desc_match = re.search(r'export const description = ["\']([^"\']+)["\']', content)

        title = title_match.group(1) if title_match else f"Komodo DeFi Framework Method: {method_name}"
        description = desc_match.group(1) if desc_match else f"Method description for {method_name}"

        parameters = self._extract_parameters_from_mdx(content)
        response_parameters = self._extract_response_parameters_from_mdx(content)

        return {
            'type': 'method',
            'method_name': method_name,
            'title': title,
            'description': description,
            'parameters': parameters,
            'response_parameters': response_parameters,
            'file_path': str(file_path)
        }

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
            parameters = self._parse_parameter_table(table_content)
            
        return parameters

    def _parse_parameter_table(self, table_content: str) -> List[Parameter]:
        """Parse a parameter table."""
        parameters = []
        
        # Split into lines and find table rows
        lines = table_content.strip().split('\n')
        
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
            
        # Parse header
        header_line = lines[header_idx].strip()
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        
        if headers and not headers[0]:
            headers = headers[1:]
        if headers and not headers[-1]:
            headers = headers[:-1]
            
        param_col, type_col, req_col, def_col, desc_col = -1, -1, -1, -1, -1
        
        for i, header in enumerate(headers):
            h_lower = header.lower()
            if 'parameter' in h_lower:
                param_col = i
            elif 'type' in h_lower:
                type_col = i
            elif 'required' in h_lower:
                req_col = i
            elif 'default' in h_lower:
                def_col = i
            elif 'description' in h_lower:
                desc_col = i
                
        # Parse data rows
        for i in range(separator_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line or not line.startswith('|'):
                continue
                
            columns = [col.strip() for col in line.split('|')]
            if columns and not columns[0]:
                columns = columns[1:]
            if columns and not columns[-1]:
                columns = columns[:-1]
            
            if len(columns) < 3:
                continue
            
            param_name = columns[param_col] if param_col != -1 and param_col < len(columns) else ""
            param_type = columns[type_col] if type_col != -1 and type_col < len(columns) else ""
            required_indicator = columns[req_col] if req_col != -1 and req_col < len(columns) else ""
            description = columns[desc_col] if desc_col != -1 and desc_col < len(columns) else ""
            
            # Handle both 4 and 5 column tables
            if def_col != -1 and def_col < len(columns):
                default_value = columns[def_col]
            else:
                default_value = self._extract_default_from_description(description)
            
            if not param_name or not param_type:
                continue
                
            is_required = self._is_parameter_required(required_indicator, description, default_value)
            
            # Extract enums
            enum_values, cleaned_type = self._extract_enum_from_type(param_type)
            if not enum_values:
                enum_values = self._extract_enum_from_description(description)
                
            # Extract enum references from description
            enum_ref = self._extract_enum_references_from_description(description)
            if enum_ref:
                cleaned_type = f"#/components/schemas/{enum_ref}"

            # Get the correct default value
            actual_default = default_value or self._extract_default_from_description(description)

            # Check for common structures and update counter
            if 'common structure' in description.lower():
                self.common_structures[param_name.strip('`')] += 1
            
            parameters.append(Parameter(
                name=param_name.strip('`').replace('\\_', '_'),
                type=cleaned_type,
                required=is_required,
                description=description,
                default_value=actual_default,
                enum_values=enum_values,
                enum_reference=enum_ref
            ))
            
        return parameters

    def _is_parameter_required(self, required_indicator: str, description: str, default_value: Optional[str]) -> bool:
        """Determine if a parameter is required."""
        if '✓' in required_indicator:
            return True
        if '✗' in required_indicator:
            return False
        
        # Fallback logic for older formats
        desc_lower = description.lower()
        if 'required' in desc_lower and 'not required' not in desc_lower:
            return True
        if 'optional' in desc_lower or default_value:
            return False
            
        return True

    def _extract_enum_from_type(self, param_type: str) -> Tuple[Optional[List[str]], str]:
        """Extract enum values from the type string, e.g., 'string (one of: "value1", "value2")'."""
        match = re.search(r'\((?:one of|enum):\s*(.*?)\)', param_type, re.IGNORECASE)
        if match:
            enum_part = match.group(1)
            # Find all quoted values
            enum_values = re.findall(r'["\'](.*?)["\']', enum_part)
            # Clean up the type string
            cleaned_type = re.sub(r'\s*\((?:one of|enum):.*?\)', '', param_type).strip()
            return enum_values, cleaned_type
        return None, param_type

    def _extract_default_from_description(self, description: str) -> Optional[str]:
        """Extract default value from description text."""
        match = re.search(r'default(?: is)?\s*`([^`]+)`', description, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _parse_responses_table(self, content: str) -> List[Response]:
        """Parse the responses section to extract status codes and descriptions."""
        # This is a placeholder for more sophisticated parsing
        return [
            Response("200", "Success"),
            Response("400", "Bad request"),
            Response("500", "Internal server error")
        ]

    def _extract_request_body_schema(self, content: str, method_name: str) -> Optional[Dict[str, Any]]:
        """Extracts the JSON request body schema from a code block in the MDX file."""
        # Find JSON code blocks that are likely request examples
        json_blocks = re.findall(r'```json\s*({.*?})\s*```', content, re.DOTALL)
        
        for block in json_blocks:
            try:
                data = json.loads(block)
                # Heuristic: check if the 'method' field matches
                if data.get('method') == method_name:
                    return data
            except json.JSONDecodeError:
                continue
        
        return None

    def _map_type(self, mdx_type: str) -> str:
        """Maps an MDX type to an OpenAPI type."""
        mdx_type_lower = mdx_type.lower()
        if 'string' in mdx_type_lower:
            return 'string'
        if 'integer' in mdx_type_lower or 'int' in mdx_type_lower or 'u64' in mdx_type_lower or 'i32' in mdx_type_lower:
            return 'integer'
        if 'number' in mdx_type_lower or 'float' in mdx_type_lower or 'double' in mdx_type_lower:
            return 'number'
        if 'boolean' in mdx_type_lower or 'bool' in mdx_type_lower:
            return 'boolean'
        if 'array' in mdx_type_lower or 'list' in mdx_type_lower:
            return 'array'
        if 'object' in mdx_type_lower or 'json' in mdx_type_lower:
            return 'object'
        return 'string'  # Default to string

    def _infer_type_from_value(self, value: Any) -> str:
        """Infers the OpenAPI type from a Python value."""
        if isinstance(value, bool):
            return 'boolean'
        if isinstance(value, int):
            return 'integer'
        if isinstance(value, float):
            return 'number'
        if isinstance(value, list):
            return 'array'
        if isinstance(value, dict):
            return 'object'
        return 'string'

    def _extract_parameters_from_mdx(self, content: str) -> List[Parameter]:
        """Extract parameters from MDX parameter tables."""
        parameters = []
        
        # Look for request parameter tables
        table_match = re.search(r'###\s+Request\s+Parameters?\s*Table\s*\n\n(.*?)(?=\n###|\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
        if not table_match:
            table_match = re.search(r'###\s+Request\s+Parameters?\s*\n\n(.*?)(?=\n###|\n##|\Z)', content, re.DOTALL | re.IGNORECASE)
        
        if table_match:
            table_content = table_match.group(1)
            parameters = self._parse_parameter_table(table_content)
            
        return parameters

    def _extract_enum_from_description(self, description: str) -> Optional[List[str]]:
        """
        Extract enum values from the description string.
        Looks for patterns like "one of: `value1`, `value2`" or lists.
        """
        # Pattern for "one of: `val1`, `val2`"
        match = re.search(r'one of:\s*((?:`[^`]+`\s*,?\s*)+)', description, re.IGNORECASE)
        if match:
            # Extract values from backticks
            return re.findall(r'`([^`]+)`', match.group(1))

        # Pattern for markdown lists
        list_match = re.search(r'Can be one of the following:\s*\n((?:\s*-\s*`.*?`\s*\n)+)', description, re.IGNORECASE | re.DOTALL)
        if list_match:
            return re.findall(r'`([^`]+)`', list_match.group(1))

        return None
    
    def _extract_enum_references_from_description(self, description: str) -> Optional[str]:
        """
        Extracts references to common enums from the description.
        Looks for links like `[MyEnum](/path/to/enums#myenum)`.
        """
        match = re.search(r'\[([\w\s]+)\]\((.*?)\)', description)
        if match:
            link_text = match.group(1)
            link_url = match.group(2)
            
            # Check if it's an internal link to an enum
            if '#-enum' in link_url.lower() or 'enums' in link_url.lower():
                # Extract enum name from the anchor
                anchor_match = re.search(r'#([\w-]+enum)$', link_url, re.IGNORECASE)
                if anchor_match:
                    return anchor_match.group(1)
        return None 