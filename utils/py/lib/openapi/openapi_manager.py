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
from ..utils.logging_utils import get_logger
from .openapi_spec_generator import OpenApiSpecGenerator
from .openapi_schema_generator import OpenApiSchemaGenerator
from ..mdx.mdx_parser import MDXParser
from ..utils.path_utils import EnhancedPathMapper
from ..constants import OpenAPIMethod, PathDetail, get_config


class OpenAPIManager:
    """
    Manages the end-to-end process of generating OpenAPI specifications
    from MDX documentation files. It acts as a high-level orchestrator,
    coordinating the parser and converter to produce individual and
    categorized OpenAPI specs.
    """

    def __init__(self, config: object = None, verbose: bool = True):
        self.config = config or get_config()
        self.base_path = Path(self.config.workspace_root)
        self.path_mapper = EnhancedPathMapper(config=self.config)
        self.verbose = verbose
        
        # Initialize the main components
        self.mdx_parser = MDXParser(self.base_path)
        self.spec_generator = OpenApiSpecGenerator(
            base_path=self.base_path,
            path_mapper=self.path_mapper
        )
        self.schema_generator = OpenApiSchemaGenerator(
            path_mapper=self.path_mapper
        )
        
        # Tracking attributes
        self.all_methods = {}
        self.success_count = 0
        self.error_count = 0
        self.enum_count = 0
        self.structure_count = 0
        self.logger = get_logger("openapi-manager")

    def generate_openapi_specs(self, version: str = "v2") -> str:
        """
        Main orchestration method. It finds all relevant MDX files, parses them,
        generates individual OpenAPI specs, and then aggregates them into
        category-based specs.

        Args:
            version: The API version to process (e.g., "v2").

        Returns:
            A string message summarizing the result of the operation.
        """
        self.logger.info(f"Starting OpenAPI generation for version: {version}")
        
        # Define source directories based on version
        source_dirs = []
        if version == "v1":
            source_dirs.append(Path(self.config.workspace_root) / self.path_mapper.config.directories.mdx_v1)
        elif version == "v2":
            source_dirs.append(Path(self.config.workspace_root) / self.path_mapper.config.directories.mdx_v2)
            source_dirs.append(Path(self.config.workspace_root) / self.path_mapper.config.directories.mdx_v2_dev)
        
        # Add common structures directory, which is relevant for all versions
        source_dirs.append(Path(self.config.workspace_root) / "src/pages/komodo-defi-framework/api/common_structures")
        
        source_dirs = [d for d in source_dirs if d.exists()]
        
        # Discover and process all MDX files
        for dir_path in source_dirs:
            for mdx_file in sorted(dir_path.rglob("*.mdx")):
                
                # Parse the MDX file to get method information
                parsed_info = self.mdx_parser.parse_mdx_file(mdx_file)
                
                if parsed_info:
                    parsed_info['version'] = version
                    doc_type = parsed_info.get('type')
                    if doc_type == 'method':
                        method_name = parsed_info['method_name']
                        
                        # Generate the individual OpenAPI spec for the method
                        spec = self.spec_generator.build_openapi_spec(parsed_info, version)
                        # Write the spec to a file
                        openapi_path = self.spec_generator.write_openapi_file(
                            spec, method_name, version, mdx_path=str(mdx_file)
                        )
                        self.logger.save(f"{version} YAML created for [{method_name}]")
                        self.success_count += 1
                        
                        # Add openapi_path to parsed_info for tracking
                        parsed_info['openapi_path'] = openapi_path
                        
                        # Use a versioned key to prevent overwrites
                        versioned_method_key = f"{method_name}_{version}"
                        self.all_methods[versioned_method_key] = parsed_info
                        
                        # Track method details for reporting
                        self.spec_generator.all_method_details.append(OpenAPIMethod(
                            name=method_name,
                            summary=parsed_info['title'],
                            mdx_path=str(mdx_file),
                            openapi_path=openapi_path
                        ))
                        self.spec_generator.all_path_details.append(PathDetail(
                            path=openapi_path,
                            method_name=method_name
                        ))
                    elif doc_type == 'enum':
                        self.enum_count += 1
                    elif doc_type == 'structure':
                        self.structure_count += 1
                else:
                    self.error_count += 1
        
        # Generate common schemas like enums and structures
        self.schema_generator.generate_common_schemas(self.mdx_parser.enum_patterns)
        
        # Generate categorized OpenAPI specifications
        self.spec_generator._generate_category_specs(self.all_methods, version)
        
        # Final reporting
        stats = self.get_stats()
        self.logger.info(f"OpenAPI generation complete. {stats['files_processed']} files processed.")
        
        # Get enum and structure counts from the parser
        enums_count = len(self.mdx_parser.enum_patterns)
        structures_count = len(self.mdx_parser.common_structures)
        
        # Generate tracking files
        self.spec_generator.generate_tracking_files(version, self.success_count, self.error_count,
                                             self.mdx_parser.enum_patterns, structures_count, 
                                             enums_count, [str(d) for d in source_dirs], self.all_methods)

        return f"Successfully generated OpenAPI specs for {self.success_count} methods with {self.error_count} errors, and processed {self.enum_count} enums and {self.structure_count} structures."

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