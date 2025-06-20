#!/usr/bin/env python3
"""
OpenAPI Common Schema Generator

This module contains the OpenApiSchemaGenerator class, which is responsible for
generating reusable schemas for enums and data structures. It scans the
documentation for definitions and creates OpenAPI components that can be
referenced throughout the API specification.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set

from ..utils.path_utils import EnhancedPathMapper
from ..constants.config import get_config
from .openapi_schema_factory import OpenApiSchemaFactory
from ..utils.file_utils import ensure_directory_exists
from ..utils.logging_utils import get_logger


class OpenApiSchemaGenerator:
    """
    Generates common OpenAPI schemas for enums and data structures.
    This class handles the discovery, parsing, and generation of reusable
    components from the MDX documentation.
    """
    # Regex to find structure definitions (### Heading) and their content (until the next ### or ##)
    _STRUCTURE_DEF_REGEX = re.compile(r'###\s+([\w_]+)\s*\n(.*?)(?=\n###|\n##|\Z)', re.DOTALL)
    # Regex to find enum definitions (### Heading ending with Enum) and their content
    _ENUM_DEF_REGEX = re.compile(r'###\s+([\w_]+Enum)\s*\n(.*?)(?=\n###|\n##|\Z)', re.DOTALL)
    _STRUCTURE_TABLE_ROW_REGEX = re.compile(r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|')
    _ENUM_NAME_REGEX = re.compile(r'##\s+([\w_]+)')
    _ENUM_DESC_REGEX = re.compile(r'export const description = "(.*?)"')
    _ENUM_TABLE_REGEX = re.compile(r'\| Value \|.*?\n\|-.*\n(.*)', re.DOTALL)
    _ENUM_TABLE_ROW_REGEX = re.compile(r'\|\s*`([^`]+)`\s*\|')

    def __init__(self, config=None, path_mapper=None):
        self.config = config or get_config()
        self.logger = get_logger(__name__)
        self.path_mapper = path_mapper or EnhancedPathMapper(config=self.config)
        self.schema_factory = OpenApiSchemaFactory(config=self.config, path_mapper=self.path_mapper)
        self.schemas_dir = Path(self.config.directories.openapi_schemas)
        self.common_structures_dir = Path(self.config.directories.mdx_common_structures)
        self.schemas_path = self.path_mapper.config.directories.openapi_schemas

    def generate_common_schemas(self, all_enums: Dict[str, Set[str]] = None):
        """
        Generates schemas for common data structures and enums.
        """
        self.logger.critical("!!!!!!!!!! EXECUTING generate_common_schemas !!!!!!!!!!!")
        # Generate files for manually defined enums from the enums/index.mdx file
        manual_enums = self._extract_manual_enums_from_docs()
        for enum_name, schema in manual_enums.items():
            full_schema = {
                'components': {
                    'schemas': {
                        enum_name: {
                            **schema,
                            "title": f"Component: {enum_name}"
                        }
                    }
                }
            }
            with open(Path(self.schemas_path) / f"{enum_name}.yml", 'w', encoding='utf-8') as f:
                yaml.dump(full_schema, f, sort_keys=False, allow_unicode=True)

        # Generate files for common data structures
        self.logger.info("Generating individual structure files...")
        self._generate_individual_structure_files()

        # Log any enums that are documented but not in the manual list for review
        self._output_undocumented_enums_for_review(all_enums)

    def _output_undocumented_enums_for_review(self, all_enums: Dict[str, Set[str]]):
        """
        Creates a file listing enums that are found in parameter descriptions
        but do not have a corresponding manual enum file.
        """
        # TODO: This is a temporary file for review. It should be removed when the enums are documented.
        # TODO: This should be a json file
        review_file = self.path_mapper.config.directories.reports_dir / "undocumented_enums_for_review.txt"
        
        manual_enums_path = self.path_mapper.config.directories.mdx_common_structures / "enums"
        existing_enums = {p.stem for p in manual_enums_path.glob("*.mdx")}
        
        with open(review_file, 'w') as f:
            f.write("## Enums for Review ##\n")
            f.write("The following enums were found in documentation but do not have a dedicated enum file.\n")
            
            for enum_name, values in sorted(all_enums.items()):
                if enum_name not in existing_enums:
                    f.write(f"### {enum_name}\n")
                    f.write("```yaml\n")
                    f.write(f"type: string\n")
                    f.write(f"enum:\n")
                    for value in sorted(list(values)):
                        f.write(f"  - {value}\n")
                    f.write("```\n\n")

    def _generate_individual_structure_files(self):
        """
        Scans for structure definition files and creates a YAML schema file for each.
        """
        structure_dir = self.path_mapper.config.directories.mdx_common_structures
        if not structure_dir.exists():
            return
            
        for structure_file in structure_dir.rglob("*.mdx"):
            if "enums" in structure_file.parts:
                continue
            self._create_structure_schema_file(structure_file)

    def _create_structure_schema_file(self, structure_file: Path):
        """
        Parses a single structure .mdx file and creates a corresponding OpenAPI schema file
        for each structure defined within it (marked by ###).
        """
        try:
            content = structure_file.read_text(encoding="utf-8")
            structures = self._parse_structure_definitions(content, str(structure_file))
            for name, schema in structures.items():
                full_schema = {
                    'components': {
                        'schemas': {
                            name: schema
                        }
                    }
                }
                self._write_schema_file(name, full_schema)
        except Exception as e:
            self.logger.error(f"Error processing structure file {structure_file}: {e}")

    def _parse_structure_definitions(self, content: str, file_path: str) -> Dict[str, Dict]:
        """
        Parses an MDX file for structure definitions. A single file can contain
        multiple structures, each denoted by a '###' heading.
        """
        structures = {}
        matches = self._STRUCTURE_DEF_REGEX.findall(content)
        
        for match in matches:
            structure_name, structure_content = match
            # Each match corresponds to one structure (e.g., ActivationMode)
            properties = self._parse_structure_table(structure_content, file_path)
            if properties: # Only add if properties were found
                structures[structure_name] = {
                    'type': 'object',
                    'properties': properties
                }
            
        return structures

    def _parse_structure_table(self, structure_content: str, file_path: str) -> Dict[str, Dict]:
        """
        Parses a markdown table within a structure's section to extract properties.
        """
        properties = {}
        # Regex updated to handle 4 or 5 columns (Parameter, Type, Required, Default, Description)
        rows = re.findall(
            r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|(?:s*(.*)\s*\|)?', 
            structure_content
        )
        
        for row in rows:
            # Unpack row, handling both 4 and 5 column tables
            if len(row) == 5 and row[4] is not None:
                param_name, param_type, required, default, param_desc = row
            else:
                param_name, param_type, required, default, _ = row
                param_desc = default # In 4-column tables, 4th col is description
                default = ''

            param_name = param_name.strip().strip('`')
            
            # Skip table header row
            if 'parameter' in param_name.lower() or '---' in param_name:
                continue
            
            param_name = param_name.replace('\\_', '_')
            param_type = param_type.strip()
            param_desc = param_desc.strip()

            properties[param_name] = self.schema_factory.create_parameter_schema(
                {"Type": param_type, "Description": param_desc, "Parameter": param_name},
                file_path
            )
            
        return properties

    def _write_schema_file(self, name: str, schema: Dict):
        """Writes a schema to a YAML file."""
        ensure_directory_exists(self.schemas_dir)
        filename = f"{name}.yml"
        output_file_path = Path(self.schemas_dir) / filename
        self.logger.info(f"Writing schema for {name} to {output_file_path}")
        with open(output_file_path, 'w', encoding='utf-8') as f_out:
            yaml.dump(schema, f_out, sort_keys=False, allow_unicode=True)

    def _extract_manual_enums_from_docs(self) -> Dict[str, Dict[str, Any]]:
        """
        Scans documentation for manually defined enum files. A single file can
        contain multiple enums, each denoted by a '###' heading ending in 'Enum'.
        """
        enums = {}
        enum_dir = self.path_mapper.config.directories.mdx_common_structures / "enums"
        if not enum_dir.exists():
            return enums
            
        for enum_file in enum_dir.glob("*.mdx"):
            with open(enum_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find all enum definitions in the file
            matches = self._ENUM_DEF_REGEX.findall(content)

            for match in matches:
                enum_name, enum_content = match
                
                # Simple description for now
                description = f"Enum for {enum_name}"

                # The rest of the content is assumed to be the table
                values = self._parse_enum_values_from_table(enum_content)
                if values:
                    enums[enum_name] = {
                        "type": "string",
                        "description": description,
                        "enum": values
                    }
        return enums

    def _parse_enum_values_from_table(self, table_content: str) -> List[str]:
        """Parses a markdown table to extract enum values."""
        values = []
        rows = self._ENUM_TABLE_ROW_REGEX.findall(table_content)
        for value in rows:
            values.append(value)
        return values 