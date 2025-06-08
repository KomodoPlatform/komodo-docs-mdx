#!/usr/bin/env python3
"""
Method Mapping Classes

This module provides classes for mapping API methods to their corresponding
MDX documentation files and OpenAPI YAML specifications.
"""

import os
import re
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass


@dataclass
class MethodMapping:
    """Represents a mapping between a method and its associated files."""
    method: str
    mdx_path: Optional[str] = None
    yaml_path: Optional[str] = None
    
    @property
    def has_mdx(self) -> bool:
        return self.mdx_path is not None
    
    @property
    def has_yaml(self) -> bool:
        return self.yaml_path is not None
    
    @property
    def is_complete(self) -> bool:
        return self.has_mdx and self.has_yaml


class MethodMapper:
    """
    Handles mapping of API methods to their corresponding MDX and YAML files.
    Consolidates functionality from multiple mapping scripts.
    """
    
    def __init__(self, base_path: str = ".", verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        self.mdx_dirs = {
            'legacy': '../../src/pages/komodo-defi-framework/api/legacy',
            'v2': '../../src/pages/komodo-defi-framework/api/v20',
            'v2-dev': '../../src/pages/komodo-defi-framework/api/v20-dev',
        }
        self.yaml_dirs = {
            'v1': '../../postman/openapi/paths/v1',
            'v2': '../../postman/openapi/paths/v2',
        }
        
    def _normalize_method_name(self, method_name: str) -> List[str]:
        """
        Generate possible variations of a method name to handle naming convention mismatches.
        Only converts between :: and - while preserving underscores.
        
        Args:
            method_name: The original method name
            
        Returns:
            List of possible method name variations
        """
        variations = [method_name]  # Always include the original
        
        # Convert :: to - (method format to YAML format)
        if '::' in method_name:
            dash_version = method_name.replace('::', '-')
            variations.append(dash_version)
        
        # Convert - to :: (YAML format to method format)
        elif '-' in method_name:
            colon_version = method_name.replace('-', '::')
            variations.append(colon_version)
        
        return list(set(variations))  # Remove duplicates
    
    def _find_best_match(self, method_name: str, mapping_dict: Dict[str, str]) -> Optional[str]:
        """
        Find the best match for a method name in a mapping dictionary.
        
        Args:
            method_name: The method name to find a match for
            mapping_dict: Dictionary to search in
            
        Returns:
            The path if found, None otherwise
        """
        # Try exact match first
        if method_name in mapping_dict:
            return mapping_dict[method_name]
        
        # Try variations
        variations = self._normalize_method_name(method_name)
        for variation in variations:
            if variation in mapping_dict:
                return mapping_dict[variation]
        
        return None
        
    def scan_mdx_files(self) -> Dict[str, Dict[str, str]]:
        """
        Scan MDX files and extract method mappings.
        Returns dict with v1 and v2 mappings: {method: mdx_path}
        """
        method_pages = {"v1": {}, "v2": {}}
        omit_path = os.path.relpath('../../src/pages/komodo-defi-framework/api/v20/index.mdx', '.')
        
        for version, base_dir in self.mdx_dirs.items():
            if not os.path.exists(base_dir):
                continue
                
            is_legacy = (version == 'legacy')
            
            for root, _, files in os.walk(base_dir):
                if 'index.mdx' in files:
                    mdx_path = os.path.relpath(os.path.join(root, 'index.mdx'), '.')
                    if mdx_path == omit_path:
                        continue
                        
                    try:
                        with open(os.path.join(root, 'index.mdx'), 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        v1_methods, v2_methods = self._extract_methods_from_mdx(content, is_legacy)
                        
                        # Map methods to this MDX file
                        for method in v1_methods:
                            if method in method_pages["v1"]:
                                print(f"[WARN] Method '{method}' for v1 found in multiple MDX files: "
                                     f"'{method_pages['v1'][method]}' and '{mdx_path}'")
                            method_pages["v1"][method] = mdx_path
                            
                        for method in v2_methods:
                            if method in method_pages["v2"]:
                                print(f"[WARN] Method '{method}' for v2 found in multiple MDX files: "
                                     f"'{method_pages['v2'][method]}' and '{mdx_path}'")
                            method_pages["v2"][method] = mdx_path
                            
                    except Exception as e:
                        print(f"Error processing MDX file {mdx_path}: {e}")
        
        return method_pages
    
    def scan_yaml_files(self) -> Dict[str, Dict[str, str]]:
        """
        Scan YAML files and extract method mappings.
        Returns dict with v1 and v2 mappings: {method: yaml_path}
        """
        method_yaml = {"v1": {}, "v2": {}}
        
        for version, base_dir in self.yaml_dirs.items():
            if not os.path.exists(base_dir):
                print(f"Warning: Directory {base_dir} does not exist")
                continue
                
            for filename in os.listdir(base_dir):
                if filename.endswith(('.yaml', '.yml')):
                    yaml_path = os.path.join(base_dir, filename)
                    relative_path = os.path.relpath(yaml_path, '.')
                    
                    try:
                        method = self._extract_method_from_yaml(yaml_path)
                        if method:
                            if method in method_yaml[version]:
                                print(f"[WARN] Method '{method}' for {version} found in multiple YAML files: "
                                     f"'{method_yaml[version][method]}' and '{relative_path}'")
                            method_yaml[version][method] = relative_path
                        else:
                            print(f"[WARN] Could not extract method from {relative_path}")
                            
                    except Exception as e:
                        print(f"Error processing YAML file {yaml_path}: {e}")
        
        return method_yaml
    
    def create_unified_mapping(self) -> Dict[str, Dict[str, MethodMapping]]:
        """
        Create unified mapping combining MDX and YAML mappings with name normalization.
        Returns dict with v1 and v2 mappings: {method: MethodMapping}
        """
        print("Scanning MDX files...")
        mdx_mappings = self.scan_mdx_files()
        
        print("Scanning YAML files...")
        yaml_mappings = self.scan_yaml_files()
        
        unified = {"v1": {}, "v2": {}}
        
        # Get all methods from both sources
        for version in ["v1", "v2"]:
            all_methods = set()
            all_methods.update(mdx_mappings[version].keys())
            all_methods.update(yaml_mappings[version].keys())
            
            print(f"\n=== Processing {version.upper()} Methods ===")
            
            for method in sorted(all_methods):
                # Use smart matching for cross-referencing
                mdx_path = self._find_best_match(method, mdx_mappings[version])
                yaml_path = self._find_best_match(method, yaml_mappings[version])
                
                mapping = MethodMapping(
                    method=method,
                    mdx_path=mdx_path,
                    yaml_path=yaml_path
                )
                
                # Log each method with timestamp and status
                if self.verbose:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    has_yaml_str = "✓ has yaml" if mapping.has_yaml else "✗ no yaml"
                    has_mdx_str = "✓ has mdx" if mapping.has_mdx else "✗ no mdx"
                    print(f"[{timestamp}] {method:<60} [{has_yaml_str}] [{has_mdx_str}]")
                
                unified[version][method] = mapping
        
        return unified
    
    def save_unified_mapping(self, output_file: str = "unified_method_mapping.json") -> None:
        """Save unified mapping to JSON file."""
        unified = self.create_unified_mapping()
        
        # Convert to serializable format
        serializable = {"v1": {}, "v2": {}}
        for version in ["v1", "v2"]:
            for method, mapping in unified[version].items():
                serializable[version][method] = {
                    "mdx": mapping.mdx_path,
                    "yaml": mapping.yaml_path
                }
        
        with open(output_file, 'w') as f:
            json.dump(serializable, f, indent=2)
        
        # Print detailed statistics
        self._print_detailed_mapping_stats(unified)
    
    def load_unified_mapping(self, input_file: str = "unified_method_mapping.json") -> Dict[str, Dict[str, MethodMapping]]:
        """Load unified mapping from JSON file."""
        try:
            with open(input_file, 'r') as f:
                data = json.load(f)
            
            unified = {"v1": {}, "v2": {}}
            for version in ["v1", "v2"]:
                for method, mapping_data in data[version].items():
                    unified[version][method] = MethodMapping(
                        method=method,
                        mdx_path=mapping_data.get("mdx"),
                        yaml_path=mapping_data.get("yaml")
                    )
            
            return unified
        except FileNotFoundError:
            print(f"Mapping file {input_file} not found. Creating new mapping...")
            return self.create_unified_mapping()
    
    def _extract_methods_from_mdx(self, content: str, is_legacy: bool) -> Tuple[List[str], List[str]]:
        """Extract method names from MDX content."""
        v1_methods = []
        v2_methods = []
        
        # Find all CodeGroup blocks
        codegroups = re.findall(r'<CodeGroup[\s\S]*?>([\s\S]*?)</CodeGroup>', content, re.MULTILINE)
        
        for block in codegroups:
            # Find all code blocks within the CodeGroup
            code_blocks = re.findall(r'```[a-zA-Z]*\n([\s\S]*?)```', block)
            
            for code in code_blocks:
                # Find method name
                method_match = re.search(r'"method"\s*:\s*"([a-zA-Z0-9_:.-]+)"', code)
                if method_match:
                    method = method_match.group(1)
                    
                    # Determine v1 or v2 based on content
                    if is_legacy:
                        v1_methods.append(method)
                    elif '"mmrpc": "2.0"' in code:
                        v2_methods.append(method)
                    else:
                        v1_methods.append(method)
        
        return sorted(list(set(v1_methods))), sorted(list(set(v2_methods)))
    
    def _extract_method_from_yaml(self, yaml_path: str) -> Optional[str]:
        """Extract method name from YAML file."""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse YAML and get the path key (which has the correct :: format)
            try:
                data = yaml.safe_load(content)
                # Get the first path key, which should be the method name
                for path_key in data.keys():
                    if path_key.startswith('/'):
                        # Remove leading slash and trailing colon
                        method = path_key.strip('/').rstrip(':')
                        return method
            except yaml.YAMLError:
                pass
            
            # Fallback: try to extract operationId 
            operation_id_match = re.search(r'^\s*operationId:\s*(.+?)\s*$', content, re.MULTILINE)
            if operation_id_match:
                operation_id = operation_id_match.group(1).strip().strip('"\'')
                return operation_id
            
            # Final fallback: parse YAML and look for method enum
            try:
                data = yaml.safe_load(content)
                for path, path_data in data.items():
                    if 'post' in path_data:
                        request_body = path_data['post'].get('requestBody', {})
                        content_data = request_body.get('content', {})
                        app_json = content_data.get('application/json', {})
                        schema = app_json.get('schema', {})
                        
                        # Handle allOf structure
                        if 'allOf' in schema:
                            for item in schema['allOf']:
                                if 'properties' in item:
                                    method_prop = item['properties'].get('method')
                                    if method_prop and 'enum' in method_prop and method_prop['enum']:
                                        return method_prop['enum'][0]
                        
                        # Handle direct properties structure
                        if 'properties' in schema:
                            method_prop = schema['properties'].get('method')
                            if method_prop and 'enum' in method_prop and method_prop['enum']:
                                return method_prop['enum'][0]
                                
            except yaml.YAMLError:
                pass
                
        except Exception as e:
            print(f"Error reading {yaml_path}: {e}")
        
        return None
    
    def _print_detailed_mapping_stats(self, unified: Dict[str, Dict[str, MethodMapping]]) -> None:
        """Print detailed statistics about the mapping with missing items lists."""
        total_methods = sum(len(methods) for methods in unified.values())
        v1_methods = len(unified["v1"])
        v2_methods = len(unified["v2"])
        
        print(f"\n{'='*60}")
        print(f"MAPPING SUMMARY")
        print(f"{'='*60}")
        print(f"Total methods: {total_methods}")
        print(f"  v1: {v1_methods} methods")
        print(f"  v2: {v2_methods} methods")
        
        # Detailed breakdown for each version
        for version in ["v1", "v2"]:
            mappings = unified[version].values()
            with_both = [m for m in mappings if m.is_complete]
            mdx_only = [m for m in mappings if m.has_mdx and not m.has_yaml]
            yaml_only = [m for m in mappings if m.has_yaml and not m.has_mdx]
            missing_both = [m for m in mappings if not m.has_mdx and not m.has_yaml]
            
            print(f"\n{version.upper()} Coverage:")
            print(f"  ✓ Complete (both MDX & YAML): {len(with_both)}")
            print(f"  ⚠ MDX only (missing YAML): {len(mdx_only)}")
            print(f"  ⚠ YAML only (missing MDX): {len(yaml_only)}")
            print(f"  ✗ Missing both: {len(missing_both)}")
            
            # List missing items if any
            if mdx_only:
                print(f"\n  Methods missing YAML ({version}):")
                for mapping in sorted(mdx_only, key=lambda x: x.method):
                    print(f"    - {mapping.method}")
            
            if yaml_only:
                print(f"\n  Methods missing MDX ({version}):")
                for mapping in sorted(yaml_only, key=lambda x: x.method):
                    print(f"    - {mapping.method}")
            
            if missing_both:
                print(f"\n  Methods missing both MDX & YAML ({version}):")
                for mapping in sorted(missing_both, key=lambda x: x.method):
                    print(f"    - {mapping.method}")
        
        print(f"\n{'='*60}")

    def _print_mapping_stats(self, unified: Dict[str, Dict[str, MethodMapping]]) -> None:
        """Legacy method for backward compatibility."""
        self._print_detailed_mapping_stats(unified)


def main():
    """Main function to generate unified method mapping."""
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    mapper = MethodMapper(verbose=True)
    mapper.save_unified_mapping()


if __name__ == "__main__":
    main() 