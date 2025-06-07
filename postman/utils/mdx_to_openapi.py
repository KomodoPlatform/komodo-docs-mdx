#!/usr/bin/env python3
"""
MDX to OpenAPI Converter

This script processes methods from method_pages.json and generates OpenAPI path specifications
by parsing the corresponding MDX files.

Usage:
    python mdx_to_openapi.py [--version v1|v2|all] [--output-dir path] [--dry-run]
"""

import json
import os
import re
import yaml
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class Parameter:
    name: str
    type: str
    description: str
    required: bool
    location: str = "query"  # query, path, header, cookie


@dataclass
class Response:
    status_code: str
    description: str
    schema: Optional[Dict[str, Any]] = None


@dataclass
class MethodInfo:
    name: str
    mdx_path: str
    summary: str
    description: str
    parameters: List[Parameter]
    responses: List[Response]
    request_body_schema: Optional[Dict[str, Any]] = None


class MDXParser:
    """Parser for MDX files to extract API method information."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        
    def parse_mdx_file(self, mdx_path: str, method_name: str) -> MethodInfo:
        """Parse an MDX file and extract method information."""
        full_path = self.base_path / mdx_path.replace("../../", "")
        
        if not full_path.exists():
            print(f"Warning: MDX file not found: {full_path}")
            return self._create_placeholder_method_info(method_name, mdx_path)
            
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {full_path}: {e}")
            return self._create_placeholder_method_info(method_name, mdx_path)
            
        return self._parse_content(content, method_name, mdx_path)
    
    def _create_placeholder_method_info(self, method_name: str, mdx_path: str) -> MethodInfo:
        """Create placeholder method info when MDX file is unavailable."""
        return MethodInfo(
            name=method_name,
            mdx_path=mdx_path,
            summary=f"Komodo DeFi Framework Method: {method_name}",
            description=f"TODO: Add description for {method_name} method",
            parameters=[],
            responses=[
                Response("200", "Success"),
                Response("400", "Bad request"),
                Response("500", "Internal server error")
            ]
        )
    
    def _parse_content(self, content: str, method_name: str, mdx_path: str) -> MethodInfo:
        """Parse MDX content to extract method information."""
        # Extract title and description from export statements
        title_match = re.search(r'export const title = ["\']([^"\']+)["\']', content)
        description_match = re.search(r'export const description =\s*["\']([^"\']+)["\']', content)
        
        # Extract summary from h1 header or title
        summary = title_match.group(1) if title_match else f"Komodo DeFi Framework Method: {method_name}"
        
        # Extract description from various sources
        description = ""
        if description_match:
            description = description_match.group(1)
        else:
            # Try to extract from content after the header
            desc_match = re.search(r'#[^#\n]*\n\n(.+?)(?:\n\n|\n<|$)', content, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
            else:
                description = f"The {method_name} method for Komodo DeFi Framework API."
        
        # Clean up description
        description = re.sub(r'<[^>]+>', '', description)  # Remove HTML tags
        description = re.sub(r'\n+', ' ', description)    # Replace newlines with spaces
        description = description.strip()
        
        # Parse parameters table
        parameters = self._parse_parameters_table(content)
        
        # Parse responses table  
        responses = self._parse_responses_table(content)
        
        # Extract request body schema from examples
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
        """Parse parameters from MDX table format."""
        parameters = []
        
        # Look for Arguments or Parameters section
        args_section = re.search(r'##\s+Arguments?\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
        if not args_section:
            args_section = re.search(r'##\s+Parameters?\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
        
        if args_section:
            table_content = args_section.group(1)
            
            # Parse table rows
            rows = re.findall(r'\|([^|]+)\|([^|]+)\|([^|]+)\|', table_content)
            
            for row in rows:
                if len(row) >= 3 and not any('Parameter' in cell or 'Type' in cell or '---' in cell for cell in row):
                    param_name = row[0].strip()
                    param_type = row[1].strip()
                    param_desc = row[2].strip()
                    
                    # Determine if required (look for "Optional" or "optional" in description)
                    required = not ('optional' in param_desc.lower() or 'defaults to' in param_desc.lower())
                    
                    # Map types
                    openapi_type = self._map_type(param_type)
                    
                    parameters.append(Parameter(
                        name=param_name,
                        type=openapi_type,
                        description=param_desc,
                        required=required
                    ))
        
        return parameters
    
    def _parse_responses_table(self, content: str) -> List[Response]:
        """Parse responses from MDX content."""
        responses = []
        
        # Look for Response section
        response_section = re.search(r'##\s+Response\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
        
        if response_section:
            # For now, just create a basic success response
            responses.append(Response("200", "Success"))
        else:
            # Default responses
            responses.extend([
                Response("200", "Success"),
                Response("400", "Bad request"),
                Response("500", "Internal server error")
            ])
        
        return responses
    
    def _extract_request_body_schema(self, content: str, method_name: str) -> Optional[Dict[str, Any]]:
        """Extract request body schema from JSON examples in MDX."""
        # Look for JSON code blocks
        json_blocks = re.findall(r'```json\s*\n(.*?)\n\s*```', content, re.DOTALL)
        
        for block in json_blocks:
            try:
                data = json.loads(block.strip())
                if isinstance(data, dict) and 'method' in data:
                    # This looks like a request body example
                    schema = {
                        "type": "object",
                        "properties": {
                            "userpass": {
                                "type": "string",
                                "description": "RPC authentication password"
                            },
                            "method": {
                                "type": "string",
                                "enum": [method_name],
                                "description": "Method name"
                            }
                        },
                        "required": ["userpass", "method"]
                    }
                    
                    # Add other properties from the example
                    for key, value in data.items():
                        if key not in ["userpass", "method"]:
                            prop_type = self._infer_type_from_value(value)
                            schema["properties"][key] = {
                                "type": prop_type,
                                "description": f"TODO: Add description for {key}"
                            }
                    
                    return schema
            except json.JSONDecodeError:
                continue
        
        # Default request body schema
        return {
            "type": "object",
            "properties": {
                "userpass": {
                    "type": "string",
                    "description": "RPC authentication password"
                },
                "method": {
                    "type": "string",
                    "enum": [method_name],
                    "description": "Method name"
                }
            },
            "required": ["userpass", "method"]
        }
    
    def _map_type(self, mdx_type: str) -> str:
        """Map MDX table types to OpenAPI types."""
        type_mapping = {
            'string': 'string',
            'str': 'string',
            'bool': 'boolean',
            'boolean': 'boolean',
            'int': 'integer',
            'integer': 'integer',
            'number': 'number',
            'float': 'number',
            'array': 'array',
            'object': 'object',
            'map': 'object'
        }
        
        mdx_type_lower = mdx_type.lower().strip()
        return type_mapping.get(mdx_type_lower, 'string')
    
    def _infer_type_from_value(self, value: Any) -> str:
        """Infer OpenAPI type from a JSON value."""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float):
            return 'number'
        elif isinstance(value, list):
            return 'array'
        elif isinstance(value, dict):
            return 'object'
        else:
            return 'string'


class OpenAPIGenerator:
    """Generator for OpenAPI specifications from method information."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.components_path = self.base_path / "postman" / "openapi" / "components" / "schemas"
        self.paths_path = self.base_path / "postman" / "openapi" / "paths"
        
    def generate_openapi_spec(self, method_info: MethodInfo, version: str) -> Dict[str, Any]:
        """Generate OpenAPI specification for a method."""
        # Construct the path
        method_path = f"/api/{version}/{method_info.name}"
        
        # Build parameters
        parameters = []
        for param in method_info.parameters:
            param_spec = {
                "name": param.name,
                "in": param.location,
                "description": param.description,
                "required": param.required,
                "schema": {"type": param.type}
            }
            parameters.append(param_spec)
        
        # Build request body
        request_body = None
        if method_info.request_body_schema:
            request_body = {
                "content": {
                    "application/json": {
                        "schema": method_info.request_body_schema
                    }
                }
            }
        
        # Build responses
        responses = {}
        for response in method_info.responses:
            response_spec = {"description": response.description}
            if response.schema:
                response_spec["content"] = {
                    "application/json": {
                        "schema": response.schema
                    }
                }
            elif response.status_code == "200":
                # Add basic success response schema
                response_spec["content"] = {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "result": {
                                    "type": "object",
                                    "description": "TODO: Define response structure"
                                }
                            }
                        }
                    }
                }
            responses[response.status_code] = response_spec
        
        # Build the complete operation
        operation = {
            "operationId": method_info.name,
            "summary": method_info.summary,
            "description": method_info.description,
            "x-mdx-doc-path": method_info.mdx_path
        }
        
        if parameters:
            operation["parameters"] = parameters
        
        if request_body:
            operation["requestBody"] = request_body
            
        operation["responses"] = responses
        
        # Create the path spec
        spec = {
            f"# OpenAPI path spec for {method_info.name} ({version})": None,
            method_path: {
                "post": operation
            }
        }
        
        return spec
    
    def write_openapi_file(self, spec: Dict[str, Any], method_name: str, version: str, dry_run: bool = False) -> str:
        """Write OpenAPI specification to file."""
        output_dir = self.paths_path / version
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f"{method_name}.yaml"
        
        if dry_run:
            print(f"Would write to: {output_file}")
            print(yaml.dump(spec, default_flow_style=False, sort_keys=False))
            return str(output_file)
        
        # Remove the comment key from the spec for writing
        clean_spec = {k: v for k, v in spec.items() if not k.startswith("#")}
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# OpenAPI path spec for {method_name} ({version})\n")
            yaml.dump(clean_spec, f, default_flow_style=False, sort_keys=False)
        
        print(f"Generated: {output_file}")
        return str(output_file)


def main():
    parser = argparse.ArgumentParser(description="Convert MDX files to OpenAPI specifications")
    parser.add_argument("--version", choices=["v1", "v2", "all"], default="all", 
                       help="Which version to process (default: all)")
    parser.add_argument("--output-dir", help="Output directory (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be generated without writing files")
    parser.add_argument("--method", help="Process only a specific method name")
    
    args = parser.parse_args()
    
    # Set base path
    base_path = Path(args.output_dir) if args.output_dir else Path.cwd()
    
    # Load method pages configuration
    method_pages_file = base_path / "postman" / "utils" / "method_pages.json"
    if not method_pages_file.exists():
        print(f"Error: {method_pages_file} not found")
        sys.exit(1)
    
    with open(method_pages_file, 'r') as f:
        method_pages = json.load(f)
    
    # Initialize parsers and generators
    mdx_parser = MDXParser(str(base_path))
    openapi_generator = OpenAPIGenerator(str(base_path))
    
    # Determine which versions to process
    versions_to_process = []
    if args.version == "all":
        versions_to_process = ["v1", "v2"]
    else:
        versions_to_process = [args.version]
    
    # Process each version
    total_processed = 0
    for version in versions_to_process:
        if version not in method_pages:
            print(f"Warning: Version {version} not found in method_pages.json")
            continue
            
        methods = method_pages[version]
        print(f"\n=== Processing {version} methods ===")
        
        for method_name, mdx_path in methods.items():
            # Skip if specific method requested and this isn't it
            if args.method and method_name != args.method:
                continue
                
            print(f"Processing {method_name}...")
            
            try:
                # Parse MDX file
                method_info = mdx_parser.parse_mdx_file(mdx_path, method_name)
                
                # Generate OpenAPI spec
                spec = openapi_generator.generate_openapi_spec(method_info, version)
                
                # Write to file
                openapi_generator.write_openapi_file(spec, method_name, version, args.dry_run)
                
                total_processed += 1
                
            except Exception as e:
                print(f"Error processing {method_name}: {e}")
                continue
    
    print(f"\n=== Summary ===")
    print(f"Total methods processed: {total_processed}")
    if args.dry_run:
        print("DRY RUN - No files were actually written")


if __name__ == "__main__":
    main() 