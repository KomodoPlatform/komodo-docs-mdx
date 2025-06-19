#!/usr/bin/env python3
"""
OpenAPI Manager

This module contains the OpenAPIManager class, which orchestrates the entire
OpenAPI specification generation process. It discovers MDX files, uses the
MDXParser to extract information, and the OpenApiSpecGenerator to generate
the final specification files.
"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Set
import os

# Import local modules
from ..utils import get_logger
from .openapi_spec_generator import OpenApiSpecGenerator
from .openapi_schema_generator import OpenApiSchemaGenerator
from ..mdx.mdx_parser import MDXParser
from ..utils.path_utils import EnhancedPathMapper
from ..constants import OpenAPIMethod, PathDetail, get_config
from .openapi_schema_factory import OpenApiSchemaFactory


class OpenAPIManager:
    """
    Manages the end-to-end process of generating OpenAPI specifications
    from MDX documentation files. It acts as a high-level orchestrator,
    coordinating the parser and converter to produce individual and
    categorized OpenAPI specs.
    """

    def __init__(self, config=None, verbose: bool = True):
        self.config = config if config else get_config()
        self.base_path = Path(self.config.workspace_root)
        self.path_mapper = EnhancedPathMapper(self.config)
        self.verbose = verbose
        
        # Initialize the main components
        self.mdx_parser = MDXParser(config=self.config)
        self.schema_factory = OpenApiSchemaFactory(config=self.config, path_mapper=self.path_mapper)
        self.spec_generator = OpenApiSpecGenerator(config=self.config, path_mapper=self.path_mapper, schema_creator=self.schema_factory)
        self.schema_generator = OpenApiSchemaGenerator(config=self.config, path_mapper=self.path_mapper)
        
        # Tracking attributes
        self.all_methods = {}
        self.success_count = 0
        self.error_count = 0
        self.enum_count = 0
        self.structure_count = 0
        self.logger = get_logger("openapi-manager")

    def generate_openapi_specs(self, version: str, process_schemas: bool = True, process_methods: bool = True, link_schemas: bool = True) -> str:
        self.logger.info(f"Processing version: {version} with flags: schemas={process_schemas}, methods={process_methods}, link={link_schemas}")

        all_parsed_info = []
        # Schemas and methods require parsing MDX files.
        if process_schemas or process_methods:
            mdx_files = self._get_mdx_files_for_version(version)
            all_parsed_info = [self.mdx_parser.parse_mdx_file(f) for f in mdx_files]

        if process_schemas:
            self.logger.info("Processing schemas...")
            self.schema_generator.generate_common_schemas(self.mdx_parser.enum_patterns)

        processed_methods = {}
        if process_methods:
            self.logger.info("Processing methods...")
            for parsed_info in all_parsed_info:
                if parsed_info and parsed_info.get('type') == 'method':
                    parsed_info['version'] = version
                    spec = self.spec_generator.build_openapi_spec(parsed_info)
                    if spec:
                        method_name = parsed_info['method_name']
                        self.spec_generator.write_openapi_file(spec, method_name, version, mdx_path=parsed_info['file_path'])
                        processed_methods[method_name] = parsed_info
            self.all_methods.update(processed_methods)
        
        # When linking, we assume methods were processed before and `all_methods` is populated.
        if link_schemas:
            self.logger.info("Linking schemas by generating category specs...")
            if not self.all_methods and not process_methods:
                self.logger.warning("`link_schemas` is true, but `process_methods` is false and no methods are cached. Results may be incomplete.")
            self.spec_generator._generate_category_specs(self.all_methods, version)
        
        return f"Processed version {version}. Schemas: {process_schemas}, Methods: {len(processed_methods)}, Linking: {link_schemas}."

    def _get_mdx_files_for_version(self, version: str) -> List[str]:
        # Define source directories based on version
        source_dirs = []
        if version == "v1":
            source_dirs.append(Path(self.config.workspace_root) / self.path_mapper.config.directories.mdx_v1)
        elif version == "v2":
            source_dirs.append(Path(self.config.workspace_root) / self.path_mapper.config.directories.mdx_v2)
            source_dirs.append(Path(self.config.workspace_root) / self.path_mapper.config.directories.mdx_v2_dev)
        
        # Add common structures directory, which is relevant for all versions
        source_dirs.append(self.path_mapper.config.directories.mdx_common_structures)
        
        source_dirs = [d for d in source_dirs if d.exists()]
        
        # Discover and process all MDX files
        mdx_files = []
        for dir_path in source_dirs:
            for mdx_file in sorted(dir_path.rglob("*.mdx")):
                mdx_files.append(str(mdx_file))
        
        return mdx_files

    def vlog(self, message: str):
        """Verbose logging utility."""
        if self.verbose:
            print(message)

    def get_stats(self) -> Dict[str, Any]:
        """
        Retrieves and consolidates statistics from the manager and spec_generator.
        """
        spec_stats = self.spec_generator.get_stats()
        return {
            'files_processed': spec_stats.get('files_processed', 0),
            'enums_found': self.enum_count,
            'structures_found': self.structure_count,
        }

    def generate_common_schemas_only(self):
        """
        Discovers and processes only common component files (enums, structures)
        and generates their corresponding OpenAPI schemas.
        """
        self.logger.info("Starting common schema generation...")
        
        common_structures_dir = self.path_mapper.config.directories.mdx_common_structures
        if not common_structures_dir.exists():
            self.logger.warning(f"Common structures directory not found at: {common_structures_dir}")
            return

        for mdx_file in sorted(common_structures_dir.rglob("*.mdx")):
            parsed_info = self.mdx_parser.parse_mdx_file(mdx_file)
            if parsed_info:
                doc_type = parsed_info.get('type')
                name = parsed_info.get('name')

                if doc_type in ['enum', 'structure']:
                    spec = self.spec_generator.build_component_spec(parsed_info)
                    self.spec_generator.write_openapi_file(
                        spec, name, 'v2', mdx_path=str(mdx_file)
                    )
                    self.logger.save(f"Schema created for [{name}]")
                    if doc_type == 'enum':
                        self.enum_count += 1
                    else:
                        self.structure_count += 1
        
        self.logger.info(f"Common schema generation complete. Processed {self.enum_count} enums and {self.structure_count} structures.")

    def _merge_specs(self, paths: List[str], version: str) -> Dict:
        """
        Merges multiple OpenAPI specification files into a single dictionary.
        This is useful for creating aggregated or master specifications.

        Args:
            paths: A list of file paths to the OpenAPI YAML files.
            version: The API version string.

        Returns:
            A dictionary representing the merged OpenAPI specification.
        """
        main_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": f"Komodo DeFi Framework API - {version.upper()}",
                "version": version,
                "description": "The comprehensive OpenAPI specification for Komodo DeFi Framework API."
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }
        
        for path in paths:
            try:
                with open(path, 'r') as f:
                    spec = yaml.safe_load(f)
                
                # Merge paths
                if "paths" in spec:
                    main_spec["paths"].update(spec.get("paths", {}))
                
                # Merge components
                if "components" in spec and "schemas" in spec["components"]:
                    main_spec["components"]["schemas"].update(spec["components"]["schemas"])
            
            except FileNotFoundError:
                self.logger.info(f"Warning: File not found - {path}")
            except yaml.YAMLError as e:
                self.logger.info(f"Error parsing YAML file {path}: {e}")
                
        return main_spec

    def _get_yaml_files(self, directory: str) -> List[str]:
        """
        Recursively finds all YAML files in a given directory.
        """
        yaml_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith((".yaml", ".yml")):
                    yaml_files.append(os.path.join(root, file))
        return yaml_files

    def _write_main_openapi_file(self, spec: Dict, version: str):
        """
        Writes the main, aggregated OpenAPI specification to a file.
        The output path is determined by the PathMapper.
        """
        output_path = self.path_mapper.openapi_path / f"main_openapi_spec_{version}.yml"
        
        with open(output_path, 'w') as f:
            yaml.dump(spec, f, sort_keys=False, allow_unicode=True)
            
        self.logger.info(f"Main OpenAPI spec file written to: {output_path}")

    def update_main_spec(self, version: str):
        """
        Updates the main OpenAPI specification by discovering all individual
        and categorized spec files and merging them. This ensures the main
        spec is always up-to-date.
        """
        self.logger.info("Updating main OpenAPI specification...")
        
        # Define directories to scan for spec files
        spec_dirs = [
            Path(self.config.workspace_root) / self.path_mapper.config.directories.yaml_v2,
            Path(self.config.workspace_root) / self.path_mapper.config.directories.openapi_main
        ]
        
        all_spec_files = []
        for directory in spec_dirs:
            if directory.exists():
                all_spec_files.extend(self._get_yaml_files(str(directory)))
                
        # Remove duplicates
        all_spec_files = sorted(list(set(all_spec_files)))
        
        # Merge all found specs
        merged_spec = self._merge_specs(all_spec_files, version)
        
        # Write the final main spec file
        self._write_main_openapi_file(merged_spec, version)
        
        self.logger.info("Main OpenAPI specification updated successfully.") 