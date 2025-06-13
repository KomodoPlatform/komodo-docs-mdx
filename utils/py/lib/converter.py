import json
import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from .mapping import MethodMapper, MethodMapping

@dataclass
class Parameter:
    """Represents an API parameter."""
    name: str
    type: str
    description: str
    required: bool
    location: str = "query"

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
    def parse_mdx_file(self, mdx_path: str, method_name: str) -> MethodInfo:
        # Handle path resolution more carefully
        if mdx_path.startswith("../../"):
            # Path is relative to project root, resolve it relative to base_path
            full_path = (self.base_path / mdx_path).resolve()
        else:
            # Path is relative to base_path
            full_path = (self.base_path / mdx_path).resolve()
            
        if not full_path.exists():
            print(f"Warning: {method_name} MDX file not found: {full_path}")
            return self._create_placeholder_method_info(method_name, mdx_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading {full_path}: {e}")
            return self._create_placeholder_method_info(method_name, mdx_path)
        return self._parse_content(content, method_name, mdx_path)
    def _create_placeholder_method_info(self, method_name: str, mdx_path: str) -> MethodInfo:
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
        title_match = re.search(r'export const title = ["\']([^"\']+)["\']', content)
        description_match = re.search(r'export const description =\s*["\']([^"\']+)["\']', content)
        summary = title_match.group(1) if title_match else f"Komodo DeFi Framework Method: {method_name}"
        description = ""
        if description_match:
            description = description_match.group(1)
        else:
            desc_match = re.search(r'#[^#\n]*\n\n(.+?)(?:\n\n|\n<|$)', content, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
            else:
                description = f"The {method_name} method for Komodo DeFi Framework API."
        description = re.sub(r'<[^>]+>', '', description)
        description = re.sub(r'\n+', ' ', description)
        description = description.strip()
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
        args_section = re.search(r'##\s+Arguments?\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
        if not args_section:
            args_section = re.search(r'##\s+Parameters?\s*\n(.*?)(?=\n##|\n#|$)', content, re.DOTALL | re.IGNORECASE)
        if args_section:
            table_content = args_section.group(1)
            rows = re.findall(r'\|([^|]+)\|([^|]+)\|([^|]+)\|', table_content)
            for row in rows:
                if len(row) >= 3 and not any('Parameter' in cell or 'Type' in cell or '---' in cell for cell in row):
                    param_name = row[0].strip()
                    param_type = row[1].strip()
                    param_desc = row[2].strip()
                    required = not ('optional' in param_desc.lower() or 'defaults to' in param_desc.lower())
                    openapi_type = self._map_type(param_type)
                    parameters.append(Parameter(
                        name=param_name,
                        type=openapi_type,
                        description=param_desc,
                        required=required
                    ))
        return parameters
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

class OpenAPIConverter:
    """Converts method information to OpenAPI specifications."""
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
    def generate_openapi_spec(self, method_info: MethodInfo, version: str) -> Dict[str, Any]:
        path_spec = {
            "/api/v1/method" if version == "v1" else "/api/v2/method": {
                "post": {
                    "operationId": self._generate_operation_id(method_info.name),
                    "summary": method_info.summary,
                    "description": method_info.description,
                    "tags": [f"Komodo DeFi Framework API {version.upper()}"],
                    "requestBody": self._generate_request_body(method_info, version),
                    "responses": self._generate_responses(method_info.responses)
                }
            }
        }
        return path_spec
    def _generate_operation_id(self, method_name: str) -> str:
        return method_name.replace("::", "-")
    def _generate_request_body(self, method_info: MethodInfo, version: str) -> Dict[str, Any]:
        if method_info.request_body_schema:
            schema = method_info.request_body_schema
        else:
            schema = {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "enum": [method_info.name],
                        "description": "The method name"
                    }
                },
                "required": ["method"]
            }
            if version == "v2":
                schema["properties"]["mmrpc"] = {
                    "type": "string",
                    "enum": ["2.0"],
                    "description": "API version"
                }
                schema["required"].append("mmrpc")
            if method_info.parameters:
                params_schema = {
                    "type": "object",
                    "properties": {}
                }
                required_params = []
                for param in method_info.parameters:
                    params_schema["properties"][param.name] = {
                        "type": param.type,
                        "description": param.description
                    }
                    if param.required:
                        required_params.append(param.name)
                if required_params:
                    params_schema["required"] = required_params
                schema["properties"]["params"] = params_schema
                if required_params:
                    schema["required"].append("params")
        return {
            "required": True,
            "content": {
                "application/json": {
                    "schema": schema
                }
            }
        }
    def _generate_responses(self, responses: List[Response]) -> Dict[str, Any]:
        response_specs = {}
        for response in responses:
            response_spec = {
                "description": response.description
            }
            if response.schema:
                response_spec["content"] = {
                    "application/json": {
                        "schema": response.schema
                    }
                }
            response_specs[response.status_code] = response_spec
        if "400" not in response_specs:
            response_specs["400"] = {"description": "Bad request"}
        if "500" not in response_specs:
            response_specs["500"] = {"description": "Internal server error"}
        return response_specs
    def write_openapi_file(self, spec: Dict[str, Any], method_name: str, version: str, 
                          output_dir: str = None, dry_run: bool = False) -> str:
        if output_dir is None:
            output_dir = f"openapi/paths/{version}"
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = self._generate_filename(method_name)
        file_path = output_path / f"{filename}.yaml"
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

class MDXToOpenAPIConverter:
    """Main converter class that orchestrates the conversion process."""
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.mapper = MethodMapper(base_path)
        self.parser = MDXParser(base_path)
        self.converter = OpenAPIConverter(base_path)
    def convert_methods(self, version: str = "all", output_dir: str = None, dry_run: bool = False) -> None:
        print("Loading method mappings...")
        unified_mapping = self.mapper.create_unified_mapping()
        versions_to_process = ["v1", "v2"] if version == "all" else [version]
        for ver in versions_to_process:
            if ver not in unified_mapping:
                print(f"No methods found for version {ver}")
                continue
            methods = unified_mapping[ver]
            print(f"\nProcessing {len(methods)} methods for {ver}...")
            for method_name, mapping in methods.items():
                if not mapping.has_mdx:
                    print(f"Skipping {method_name}: No MDX file found")
                    continue
                try:
                    method_info = self.parser.parse_mdx_file(mapping.mdx_path, method_name)
                    openapi_spec = self.converter.generate_openapi_spec(method_info, ver)
                    self.converter.write_openapi_file(
                        openapi_spec, method_name, ver, output_dir, dry_run
                    )
                except Exception as e:
                    print(f"Error processing {method_name}: {e}") 