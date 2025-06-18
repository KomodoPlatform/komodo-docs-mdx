#!/usr/bin/env python3
"""
OpenAPI Converter

This module contains the OpenApiSpecGenerator class, which is responsible for
converting parsed MDX information into OpenAPI specification format. It handles
the creation of schemas, parameters, responses, and the final OpenAPI file.
"""

import re
import yaml
import json
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict
from datetime import datetime

# Import constants and path utilities
from ..constants import (
    UnifiedParameterInfo as Parameter,
    OpenAPIMethod,
    PathDetail
)
from ..utils.path_utils import EnhancedPathMapper
from ..mdx.mdx_parser import MDXParser

# Import local modules
from .openapi_schema_factory import OpenApiSchemaFactory
from .openapi_schema_generator import OpenApiSchemaGenerator


class OpenApiSpecGenerator:
    """
    Converts MDX documentation into OpenAPI specification files.
    It processes method information parsed by MDXParser to generate structured
    OpenAPI schemas, including request bodies, responses, and common components
    like enums and data structures.
    """
    def __init__(self, base_path: str = ".", path_mapper: EnhancedPathMapper = None):
        self.base_path = Path(base_path)
        self.path_mapper = path_mapper or EnhancedPathMapper()
        self.mdx_parser = MDXParser(base_path)
        self.schema_creator = OpenApiSchemaFactory()
        self.common_schema_generator = OpenApiSchemaGenerator(self.path_mapper)
        
        self.all_methods = defaultdict(list)
        self.all_method_details: List[OpenAPIMethod] = []
        self.all_path_details: List[PathDetail] = []
        self.all_enums = defaultdict(set)

    def build_openapi_spec(self, method_info: Dict[str, Any], version: str = "v2") -> Dict[str, Any]:
        """
        Generates a complete OpenAPI specification for a single method.

        Args:
            method_info: A dictionary containing parsed information for a method.
            version: The API version string (e.g., "v2").

        Returns:
            A dictionary representing the OpenAPI specification for the method.
        """
        method_name = method_info['method_name']
        
        # Prepare a simple summary from the title
        summary = method_info.get('title', f"Komodo DeFi Framework Method: {method_name}")
        summary = summary.replace("Komodo DeFi Framework Method: ", "")

        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"Komodo DeFi Framework API - {method_name}",
                "version": version,
                "description": method_info.get('description', f"API documentation for the {method_name} method.")
            },
            "paths": {
                f"/{method_name}": {
                    "post": {
                        "summary": summary,
                        "description": method_info.get('description', ''),
                        "operationId": method_name,
                        "tags": [method_name.split('::')[0]],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": self.schema_creator.create_request_body_schema(method_info)
                                }
                            }
                        },
                        "responses": self.schema_creator.create_response_schema(method_info)
                    }
                }
            }
        }
        return spec

    def write_openapi_file(self, spec: Dict[str, Any], method_name: str, version: str, 
                          output_dir: str = None, dry_run: bool = False, mdx_path: str = "") -> str:
        """
        Writes a given OpenAPI specification to a YAML file.
        """
        # Determine base directories based on version
        if version == 'v1':
            mdx_base_dirs = [self.path_mapper.config.directories.mdx_legacy]
            yaml_base_dir = self.path_mapper.config.directories.yaml_v1
        else: # v2 and v2-dev
            mdx_base_dirs = [
                self.path_mapper.config.directories.mdx_v2,
                self.path_mapper.config.directories.mdx_v2_dev
            ]
            yaml_base_dir = self.path_mapper.config.directories.yaml_v2

        filename = f"{method_name.replace('::', '-')}.yml"
        if mdx_path:
            root = self.path_mapper.config.workspace_root
            relative_mdx_path = None
            
            # Add common structures to search paths
            search_dirs = mdx_base_dirs + ["src/pages/komodo-defi-framework/api/common_structures"]

            for src_dir in search_dirs:
                try:
                    relative_mdx_path = Path(mdx_path).relative_to(Path(root) / src_dir)
                    break
                except ValueError:
                    continue
            
            if relative_mdx_path is None:
                raise ValueError(f"Could not determine relative path for {mdx_path} in any of the expected directories.")

            path_parts = list(relative_mdx_path.parts)
            
            # Clean up path components
            if 'index.mdx' in path_parts:
                path_parts.remove('index.mdx')

            # The final output path should be relative to the versioned yaml directory
            output_path = Path(self.path_mapper.config.workspace_root) / yaml_base_dir / '/'.join(path_parts) / filename
        
        
        
        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(spec, f, allow_unicode=True, sort_keys=False)
        
        return str(output_path)

    def generate_common_schemas(self, all_enums: Dict[str, Set[str]], output_base: Path):
        """
        Delegates the generation of common schemas to the OpenApiSchemaGenerator.
        """
        self.common_schema_generator.generate_common_schemas(all_enums, output_base)

    def _generate_category_specs(self, all_methods: Dict[str, Dict], version: str):
        """
        Groups all processed methods by category and generates a spec file for each.
        """
        categorized_methods = defaultdict(list)
        for method_name, method_info in all_methods.items():
            if method_info.get('version') == version:
                category = method_name.split('::')[0]
                categorized_methods[category].append(method_info)
            
        for category, methods in categorized_methods.items():
            self._generate_category_spec_file(category, methods, version)

    def _generate_category_spec_file(self, category: str, methods: List[Dict], version: str):
        """
        Creates a single OpenAPI specification file for a given category.
        """
        if version == "v1":
            output_path = Path(self.path_mapper.config.directories.yaml_v1) / f"{category}.yml"
        else:
            output_path = Path(self.path_mapper.config.directories.yaml_v2) / f"{category}.yml"
        
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"Komodo DeFi Framework - {category.replace('_', ' ').title()} API",
                "version": version,
                "description": f"OpenAPI specification for the {category} methods."
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }
        
        for method_info in methods:
            method_name = method_info['method_name']
            method_spec = self.build_openapi_spec(method_info, version)
            spec["paths"].update(method_spec.get("paths", {}))
            
            if "components" in method_spec:
                for comp_name, comp_schema in method_spec["components"].get("schemas", {}).items():
                    if comp_name not in spec["components"]["schemas"]:
                        spec["components"]["schemas"][comp_name] = comp_schema
        
        spec["components"]["schemas"]["ErrorResponse"] = {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "error_path": {"type": "string"},
                "error_trace": {"type": "string"},
                "error_type": {"type": "string"},
                "error_data": {"type": "object"}
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            yaml.dump(spec, f, sort_keys=False)

    def get_stats(self) -> Dict[str, Any]:
        """
        Returns statistics about the OpenAPI generation process.
        """
        return {
            "files_processed": len(self.all_method_details),
            "errors": 0,
            "enums_found": len(self.all_enums),
            "structures_found": 0,
            "methods": self.all_method_details,
            "paths": self.all_path_details,
            "enums": {k: list(v) for k, v in self.all_enums.items()}
        }

    def generate_tracking_files(self, version: str, success_count: int, error_count: int,
                                all_enums: Dict[str, Set[str]], structures_count: int,
                                enums_count: int, source_dirs: List[str], all_methods: Dict[str, Any]) -> None:
        """
        Generates tracking and summary files for the generation process.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = Path(self.path_mapper.config.directories.reports_dir)

        self._generate_openapi_methods_file(
            timestamp, data_dir, version, success_count, error_count,
            all_enums, structures_count, enums_count, source_dirs, all_methods
        )
        self._generate_openapi_method_paths_file(timestamp, data_dir)

    def _generate_openapi_method_paths_file(self, timestamp: str, data_dir: Path) -> None:
        """
        Creates a text file listing all generated OpenAPI method paths.
        """
        sorted_paths = sorted(self.all_path_details, key=lambda p: p.path)
        paths_file = data_dir / "openapi_method_paths.txt"
        if paths_file.exists():
            backup_dir = Path(self.path_mapper.config.directories.backup_dir)
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f"openapi_method_paths_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            paths_file.rename(backup_path)
            
        with open(paths_file, "w") as f:
            f.write(f"# OpenAPI Method Paths - Generated at {timestamp}\n")
            grouped_paths = defaultdict(list)
            for detail in sorted_paths:
                top_level = Path(detail.path).parts[1]
                grouped_paths[top_level].append(detail)
            
            for group, paths in grouped_paths.items():
                f.write(f"## Version: {group.upper()}\n")
                for detail in paths:
                    f.write(f"- `{detail.path}` (Method: `{detail.method_name}`)\n")
                f.write("\n")

    def _generate_openapi_methods_file(self, timestamp: str, data_dir: Path, version: str,
                                     success_count: int, error_count: int, all_enums: Dict[str, Set[str]],
                                     structures_count: int, enums_count: int, source_dirs: List[str], all_methods: Dict[str, Any]) -> None:
        """
        Generates a comprehensive JSON summary file of the generation process.
        """
        path_file_name = f"report-kdf_openapi_methods_{timestamp}.json"
        output_file = data_dir / path_file_name
        
        # backup existing
        if output_file.exists():
            backup_dir = Path(self.path_mapper.config.directories.backup_dir)
            backup_dir.mkdir(exist_ok=True)
            backup_path = backup_dir / f"{path_file_name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_file.rename(backup_path)

        # Ensure the directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Separate methods by version
        v1_methods = sorted([m.name for m in self.all_method_details if 'v1' in m.openapi_path])
        v2_methods = sorted([m.name for m in self.all_method_details if 'v2' in m.openapi_path])

        output_data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDF-OpenAPI-Generator v1.0.0",
                "scanner_type": "OPENAPI_DOCUMENTATION",
                "total_versions": 2,
                "total_methods": len(all_methods),
                "includes_path_mapping": True,
                "method_source": "generated_from_mdx",
                "paths_file_reference": f"report-kdf_openapi_method_paths_{timestamp}.json",
                "includes_only_documented_methods": True
            },
            "repository_data": {
                "v1": {
                    "branch": "add/postman/utils", 
                    "version": "v1",
                    "source_type": "OPENAPI_DOCUMENTATION",
                    "methods": v1_methods,
                    "last_updated": datetime.now().isoformat(),
                    "extraction_patterns_used": ["MDX file parsing"]
                },
                "v2": {
                    "branch": "add/postman/utils",
                    "version": "v2",
                    "source_type": "OPENAPI_DOCUMENTATION",
                    "methods": v2_methods,
                    "last_updated": datetime.now().isoformat(),
                    "extraction_patterns_used": ["MDX file parsing"]
                }
            }
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2) 