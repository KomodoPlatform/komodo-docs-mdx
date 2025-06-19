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
import os

# Import constants and path utilities
from ..constants import (
    OpenAPIMethod,
    PathDetail
)
from ..utils.path_utils import EnhancedPathMapper
from ..mdx.mdx_parser import MDXParser

# Import local modules
from .openapi_schema_factory import OpenApiSchemaFactory
from .openapi_schema_generator import OpenApiSchemaGenerator
from ..utils.file_utils import safe_write_json
from ..constants.config import get_config
from ..constants.data_structures import ScanMetadata
from ..utils.logging_utils import get_logger
from ..utils.data_utils import sort_version_method_counts


class OpenApiSpecGenerator:
    """
    Converts MDX documentation into OpenAPI specification files.
    It processes method information parsed by MDXParser to generate structured
    OpenAPI schemas, including request bodies, responses, and common components
    like enums and data structures.
    """
    def __init__(self, config=None, path_mapper=None, mdx_parser=None, schema_creator=None, common_schema_generator=None):
        self.config = config or get_config()
        self.base_path = Path(self.config.workspace_root)
        self.path_mapper = path_mapper or EnhancedPathMapper(config=self.config)
        
        self.mdx_parser = mdx_parser or MDXParser()
        self.schema_creator = schema_creator or OpenApiSchemaFactory(path_mapper=self.path_mapper)
        self.common_schema_generator = common_schema_generator or OpenApiSchemaGenerator()
        
        self.all_methods = defaultdict(list)
        self.all_method_details: List[OpenAPIMethod] = []
        self.all_path_details: List[PathDetail] = []
        self.all_enums = defaultdict(set)
        self.config = get_config()
        self.reports_dir = Path(self.config._resolve_path(self.config.directories.reports_dir))
        self.reports_dir.mkdir(exist_ok=True, parents=True)
        self.logger = get_logger("openapi-spec-generator")


    def build_openapi_spec(self, method_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds the full OpenAPI specification for a single method.
        """
        if not method_info or not isinstance(method_info, dict):
            return {}
            
        method_name = method_info.get('method_name', 'unknown_method')

        return {
            "paths": {
                f"/{method_name}": {
                    "post": {
                        "summary": method_info.get('description'),
                        "description": method_info.get('description'),
                        "operationId": method_info.get('method_name'),
                        "tags": [method_info.get('category', "default")],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": self.schema_creator.create_request_body_schema(
                                        method_info, 
                                        method_info.get('file_path')
                                    )
                                }
                            }
                        },
                        "responses": self.schema_creator.create_response_schema(
                            method_info,
                            method_info.get('file_path')
                        )
                    }
                }
            }
        }

    def build_component_spec(self, component_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a simple OpenAPI component specification for an enum or structure.
        """
        comp_name = component_info['name']
        comp_type = component_info.get('type', 'object')

        return {
            "components": {
                "schemas": {
                    comp_name: {
                        "type": "string" if comp_type == "enum" else "object",
                        "title": f"Component: {comp_name}"
                    }
                }
            }
        }

    def write_openapi_file(self, spec: Dict[str, Any], method_name: str, version: str, 
                          output_dir: str = None, dry_run: bool = False, mdx_path: str = "") -> str:
        """
        Writes a given OpenAPI specification to a YAML file.
        """
        # Determine base directories based on version
        if version == 'v1':
            mdx_base_dirs = [self.path_mapper.config.directories.mdx_v1]
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
            search_dirs = mdx_base_dirs + [self.path_mapper.config.directories.mdx_common_structures]

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
            if str(mdx_path).startswith(str(self.path_mapper.config.directories.mdx_common_structures)):
                output_path = Path(self.path_mapper.config.directories.openapi_schemas) / filename
            else:
                output_path = self.path_mapper.config.directories.workspace_root / yaml_base_dir / '/'.join(path_parts) / filename
        
        
        
        if not dry_run:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(spec, f, allow_unicode=True, sort_keys=False)
        
        return str(output_path)

        

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
        self.logger.info(f"Generating category spec file for {category} with {len(methods)} methods")
        for method_info in methods:
            method_spec = self.build_openapi_spec(method_info)
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

        self._generate_openapi_methods_file(
            timestamp, version, success_count, error_count,
            all_enums, structures_count, enums_count, source_dirs, all_methods
        )

        version_method_counts = {
            version: len([m for m, d in all_methods.items() if d.get('version') == version])
        }
        
        self._generate_openapi_method_paths_file(
            all_methods=all_methods,
            path_mapper=self.path_mapper,
            versions=[version],
            version_method_counts=sort_version_method_counts(version_method_counts)
        )

    def _generate_openapi_method_paths_file(self, all_methods: Dict[str, Any], path_mapper, versions: List[str], version_method_counts: Dict[str, int]) -> str:
        """NEW: Creates a JSON file that maps each method to its OpenAPI spec path, using ScanMetadata."""
        self.logger.info("🗺️  Generating OpenAPI method-to-path mapping (new)...")
        
        paths_data = { "v1": {}, "v2": {} }
        
        for versioned_method_key, parsed_info in all_methods.items():
            openapi_path = parsed_info.get("openapi_path")
            method_name = parsed_info.get("method_name")
            version = parsed_info.get("version")
            
            if not all([openapi_path, method_name, version]):
                continue

            if version == "v1":
                paths_data["v1"][method_name] = openapi_path
            elif version == "v2":
                paths_data["v2"][method_name] = openapi_path

        total_methods = len(paths_data["v1"]) + len(paths_data["v2"])

        if total_methods == 0:
            self.logger.warning("No methods with paths found for OpenAPI.")
            return None

        metadata = ScanMetadata(
            scanner_type="OPENAPI_SPEC_GENERATOR",
            scanner_version="KDF-OpenAPI-Generator v2.0.0",
            version_method_counts=sort_version_method_counts(version_method_counts),
            generated_during="OpenAPI spec generation",
            method_source="MDX method files",
            is_primary_data_source=False
        )
        
        output_data = {
            "scan_metadata": metadata.to_dict(),
            "method_paths": paths_data
        }

        file_path = self.reports_dir / "report-kdf_openapi_method_paths.json"
        safe_write_json(file_path, output_data, indent=2)
        
        self.logger.save(f"✅ 💾 Saved OpenAPI method paths mapping to: {file_path}")
        self.logger.save(f"📊 V1: {len(paths_data['v1'])} methods")
        self.logger.save(f"📊 V2: {len(paths_data['v2'])} methods")
        
        return str(file_path)
    
    def _generate_openapi_methods_file(self, timestamp: str, version: str,
                                     success_count: int, error_count: int, all_enums: Dict[str, Set[str]],
                                     structures_count: int, enums_count: int, source_dirs: List[str], all_methods: Dict[str, Any]) -> None:
        """
        Generates a comprehensive JSON summary file of the generation process.
        """
        path_file_name = f"report-kdf_openapi_methods.json"
        output_file = self.reports_dir / path_file_name
        
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

        version_method_counts = {
            'v1': len(v1_methods),
            'v2': len(v2_methods)
        }
        
        metadata = ScanMetadata(
            scanner_type="OPENAPI_SPEC_GENERATOR",
            scanner_version="KDF-OpenAPI-Generator v2.0.0",
            version_method_counts=sort_version_method_counts(version_method_counts),
            generated_during="OpenAPI spec generation",
            method_source="MDX method files",
            is_primary_data_source=False
        )

        output_data = {
            "scan_metadata": metadata.to_dict(),
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

    def vlog(self, message: str):
        self.logger.info(message)

    def _get_yaml_files(self, directory: str) -> List[str]:
        """
        Returns a list of all YAML files in a given directory and its subdirectories.
        """
        yaml_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith((".yaml", ".yml")):
                    yaml_files.append(os.path.join(root, file))
        return yaml_files

    def _write_main_openapi_file(self, spec: Dict, version: str):
        """
        Writes a merged OpenAPI specification to a file.
        """
        output_path = self.reports_dir / f"report-kdf_openapi_main_spec_{version}.yml"
        
        with open(output_path, 'w') as f:
            yaml.dump(spec, f, sort_keys=False, allow_unicode=True)
            
        self.logger.info(f"Main OpenAPI spec file written to: {output_path}")

    def update_main_spec(self, version: str):
        """
        Updates the main OpenAPI specification for a given version.
        """
        all_spec_files = []
        for directory in self.path_mapper.config.directories.spec_dirs:
            if directory.exists():
                all_spec_files.extend(self._get_yaml_files(str(directory)))
                
        merged_spec = self._merge_specs(all_spec_files, version)
        self._write_main_openapi_file(merged_spec, version)

    def _merge_specs(self, spec_files: List[str], version: str) -> Dict:
        """
        Merges multiple OpenAPI specification files into a single dictionary.
        """
        merged_spec = {}
        for file in spec_files:
            with open(file, 'r') as f:
                spec = yaml.safe_load(f)
                merged_spec.update(spec)
        return merged_spec

    def _generate_openapi_methods_file(self, timestamp: str, version: str,
                                     success_count: int, error_count: int, all_enums: Dict[str, Set[str]],
                                     structures_count: int, enums_count: int, source_dirs: List[str], all_methods: Dict[str, Any]) -> None:
        """
        Generates a comprehensive JSON summary file of the generation process.
        """
        path_file_name = f"report-kdf_openapi_methods.json"
        output_file = self.reports_dir / path_file_name
        
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

        version_method_counts = {
            'v1': len(v1_methods),
            'v2': len(v2_methods)
        }
        
        metadata = ScanMetadata(
            scanner_type="OPENAPI_SPEC_GENERATOR",
            scanner_version="KDF-OpenAPI-Generator v2.0.0",
            version_method_counts=sort_version_method_counts(version_method_counts),
            generated_during="OpenAPI spec generation",
            method_source="MDX method files",
            is_primary_data_source=False
        )

        output_data = {
            "scan_metadata": metadata.to_dict(),
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