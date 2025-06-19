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


class OpenApiSchemaGenerator:
    """
    Generates common OpenAPI schemas for enums and data structures.
    This class handles the discovery, parsing, and generation of reusable
    components from the MDX documentation.
    """
    # Compiled regex patterns for parsing
    _STRUCTURE_DEF_REGEX = re.compile(r'##\s+([\w_]+)\s*\{\{.*?\}\}\s*\n(.*?)(?=\n##|\Z)', re.DOTALL)
    _STRUCTURE_TABLE_ROW_REGEX = re.compile(r'\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|')
    _ENUM_NAME_REGEX = re.compile(r'##\s+([\w_]+)')
    _ENUM_DESC_REGEX = re.compile(r'export const description = "(.*?)"')
    _ENUM_TABLE_REGEX = re.compile(r'\| Value \|.*?\n\|-.*\n(.*)', re.DOTALL)
    _ENUM_TABLE_ROW_REGEX = re.compile(r'\|\s*`([^`]+)`\s*\|')

    def __init__(self, config=None, path_mapper=None):
        self.config = config or get_config()
        self.base_path = Path(self.config.workspace_root)
        self.path_mapper = path_mapper or EnhancedPathMapper(config=self.config)
        self.schemas_path = self.path_mapper.config.directories.openapi_schemas

    def generate_common_schemas(self, all_enums: Dict[str, Set[str]]):
        """
        Generates schemas for common data structures and enums.
        """
        
        # Generate files for manually defined enums
        manual_enums = self._extract_manual_enums_from_docs()
        for enum_name, schema in manual_enums.items():
            with open(Path(self.schemas_path) / f"{enum_name}.yml", 'w') as f:
                yaml.dump({"title": enum_name, **schema}, f, sort_keys=False)

        # Generate files for common data structures
        self._generate_individual_structure_files()

        # Log any enums that are documented but not in the manual list for review
        self._output_undocumented_enums_for_review(all_enums)

    def _output_undocumented_enums_for_review(self, all_enums: Dict[str, Set[str]]):
        """
        Creates a file listing enums that are found in parameter descriptions
        but do not have a corresponding manual enum file.
        """
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
        Parses a single structure .mdx file and creates a corresponding OpenAPI schema file.
        """
        with open(structure_file, 'r') as f:
            content = f.read()
        
        structures = self._parse_structure_definitions(content)
        
        for structure_name, schema in structures.items():
            filename = f"{structure_name.lower()}.yml"
            
            full_schema = {
                "title": structure_name,
                "type": "object",
                "properties": schema
            }
            
            with open(Path(self.schemas_path) / filename, 'w') as f_out:
                yaml.dump(full_schema, f_out, sort_keys=False)

    def _parse_structure_definitions(self, content: str) -> Dict[str, Dict[str, Any]]:
        """
        Parses an MDX file for structure definitions.
        """
        structures = {}
        matches = self._STRUCTURE_DEF_REGEX.findall(content)
        
        for match in matches:
            structure_name, structure_content = match
            structures[structure_name] = self._parse_structure_table(structure_content)
            
        return structures

    def _parse_structure_table(self, structure_content: str) -> Dict[str, Any]:
        """
        Parses a markdown table within a structure's section to extract properties.
        """
        properties = {}
        rows = self._STRUCTURE_TABLE_ROW_REGEX.findall(structure_content)
        
        for row in rows:
            param_name, param_type, param_desc = row
            param_name = param_name.strip('`')
            
            if 'parameter' in param_name.lower() or '---' in param_name:
                continue
            
            param_name = param_name.replace('\\_', '_')
            param_type = param_type.strip()
            param_desc = param_desc.strip()

            properties[param_name] = OpenApiSchemaFactory.create_parameter_schema(param_type, param_desc)
            
        return properties

    def _extract_manual_enums_from_docs(self) -> Dict[str, Dict[str, Any]]:
        """
        Scans documentation for manually defined enum files.
        """
        enums = {}
        enum_dir = self.path_mapper.config.directories.mdx_common_structures / "enums"
        if not enum_dir.exists():
            return enums
            
        for enum_file in enum_dir.glob("*.mdx"):
            with open(enum_file, 'r') as f:
                content = f.read()
            
            name_match = self._ENUM_NAME_REGEX.search(content)
            if not name_match:
                continue
            enum_name = name_match.group(1)
            
            desc_match = self._ENUM_DESC_REGEX.search(content)
            description = desc_match.group(1) if desc_match else f"Enum for {enum_name}"
            
            table_match = self._ENUM_TABLE_REGEX.search(content)
            if table_match:
                table_content = table_match.group(1)
                values = self._parse_enum_values_from_table(table_content)
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