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
import shutil


@dataclass
class MethodMapping:
    """Represents a mapping between a method and its associated files."""
    method: str
    mdx_path: Optional[str] = None
    yaml_path: Optional[str] = None
    examples_path: Optional[str] = None
    example_count: int = 0
    
    @property
    def has_mdx(self) -> bool:
        return self.mdx_path is not None
    
    @property
    def has_yaml(self) -> bool:
        return self.yaml_path is not None
    
    @property
    def has_examples(self) -> bool:
        return self.example_count > 0
    
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
        self.json_dirs = {
            'v1': '../../postman/json/kdf/v1',
            'v2': '../../postman/json/kdf/v2',
        }
        self.main_openapi_file = '../../postman/openapi/openapi.yaml'
        
    def _normalize_method_name(self, method_name: str) -> List[str]:
        """
        Generate possible variations of a method name to handle naming convention mismatches.
        Handles conversions between :: and -, and various method patterns.
        
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
            
            # Also try without the final operation for methods that might have duplicated operations
            parts = method_name.split('::')
            if len(parts) > 2:
                # Check for duplicated final operation
                if parts[-1] == parts[-2]:
                    # Remove the duplicated operation
                    without_duplicate = '::'.join(parts[:-1])
                    variations.append(without_duplicate)
                    variations.append(without_duplicate.replace('::', '-'))
                
                # For lightning and stream methods, try without the final operation
                if method_name.startswith(('lightning::', 'stream::')):
                    base_method = '::'.join(parts[:-1])
                    variations.append(base_method)
                    variations.append(base_method.replace('::', '-'))
        
        # Convert - to :: (YAML format to method format)
        elif '-' in method_name:
            colon_version = method_name.replace('-', '::')
            variations.append(colon_version)
        
        # Handle special cases for method name patterns
        for variation in list(variations):  # Create a copy to iterate over
            # Lightning method variations
            if 'lightning' in variation:
                # Try with different separators
                if 'lightning-' in variation:
                    variations.append(variation.replace('lightning-', 'lightning::'))
                elif 'lightning::' in variation:
                    variations.append(variation.replace('lightning::', 'lightning-'))
            
            # Stream method variations  
            if 'stream' in variation:
                # Try with different separators
                if 'stream-' in variation:
                    variations.append(variation.replace('stream-', 'stream::'))
                elif 'stream::' in variation:
                    variations.append(variation.replace('stream::', 'stream-'))
            
            # Task method variations
            if 'task' in variation:
                # Try with different enable patterns
                if 'task-enable-' in variation:
                    enable_variant = variation.replace('task-enable-', 'task::enable_')
                    variations.append(enable_variant)
                elif 'task::enable_' in variation:
                    enable_variant = variation.replace('task::enable_', 'task-enable-')
                    variations.append(enable_variant)
        
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
    
    def _extract_path_from_yaml_filename(self, yaml_filename: str, version: str) -> str:
        """
        Extract the API path from a YAML filename.
        
        Args:
            yaml_filename: The YAML file name (without .yaml extension)
            version: The API version (v1 or v2)
            
        Returns:
            The API path string
        """
        # Remove .yaml extension if present
        if yaml_filename.endswith('.yaml') or yaml_filename.endswith('.yml'):
            yaml_filename = yaml_filename.rsplit('.', 1)[0]
        
        # Simple rule: prepend version prefix
        return f"/{version}/{yaml_filename}"
    
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

    def scan_json_examples(self) -> Dict[str, Dict[str, Tuple[str, int]]]:
        """
        Scan JSON example files using standardized method/operation/ structure.
        
        Structure:
        - Task methods: task-enable-utxo/init/, task-enable-utxo/status/, etc.
        - Non-task methods: my_balance/default/, orderbook/default/, etc.
        - Lightning methods: lightning-channels-close_channel/default/, etc.
        - Stream methods: stream-balance-enable/enable/, etc.
        
        Returns dict with v1 and v2 mappings: {method: (examples_path, count)}
        """
        method_examples = {"v1": {}, "v2": {}}
        
        for version, base_dir in self.json_dirs.items():
            if not os.path.exists(base_dir):
                if self.verbose:
                    print(f"Warning: Examples directory {base_dir} does not exist")
                continue
            
            # Look for method directories (e.g., task-enable-utxo, my_balance)
            for method_dir in os.listdir(base_dir):
                method_path = os.path.join(base_dir, method_dir)
                if not os.path.isdir(method_path):
                    continue
                
                # Convert method directory name to proper method name format
                method_name_base = method_dir.replace('-', '::')
                
                # Handle special naming conventions
                if method_name_base == "task::enable::z::coin":
                    method_name_base = "task::enable_z_coin"
                elif method_name_base.startswith("task::enable::"):
                    # Convert task::enable::xyz to task::enable_xyz
                    method_name_base = method_name_base.replace("::enable::", "::enable_")
                elif method_name_base.startswith("stream::") and method_name_base.endswith("::enable"):
                    # Convert stream::balance::enable to stream::balance::enable (keep as is)
                    pass
                elif method_name_base.startswith("lightning::"):
                    # Handle lightning methods - they may have the operation in the directory name
                    # e.g., lightning-channels-close_channel -> lightning::channels::close_channel
                    pass
                
                # Look for operation subdirectories (init, status, cancel, user-action, default)
                for operation_dir in os.listdir(method_path):
                    operation_path = os.path.join(method_path, operation_dir)
                    if not os.path.isdir(operation_path):
                        continue
                    
                    # Count JSON files in this operation directory
                    json_files = [f for f in os.listdir(operation_path) if f.endswith('.json')]
                    example_count = len(json_files)
                    
                    if example_count > 0:
                        # Create the full method name for the operation
                        if operation_dir == 'default':
                            # For non-task methods using default operation, use the base name as-is
                            full_method_name = method_name_base
                        else:
                            # For specific operations, we need to be smarter about avoiding duplication
                            operation_name = operation_dir.replace('-', '_')  # user-action -> user_action
                            
                            # Check if the operation is already in the method name
                            if method_name_base.endswith(f"::{operation_name}"):
                                # Already contains the operation, don't duplicate
                                full_method_name = method_name_base
                            elif method_name_base.startswith("stream::") and operation_name == "enable" and method_name_base.endswith("::enable"):
                                # Stream methods that end with ::enable and have enable operation
                                full_method_name = method_name_base
                            elif method_name_base.startswith("lightning::") and operation_name in method_name_base:
                                # Lightning methods where operation is already in the base name
                                full_method_name = method_name_base
                            else:
                                # Standard case: append operation to method base
                                full_method_name = f"{method_name_base}::{operation_name}"
                        
                        relative_path = os.path.relpath(operation_path, '.')
                        method_examples[version][full_method_name] = (relative_path, example_count)
        
        return method_examples

    def update_main_openapi_spec(self, dry_run: bool = False) -> bool:
        """
        Update the main OpenAPI specification file with discovered paths.
        
        Args:
            dry_run: If True, only print what would be changed without making changes
            
        Returns:
            True if updates were needed, False if no changes required
        """
        try:
            # Load current OpenAPI spec
            if not os.path.exists(self.main_openapi_file):
                print(f"Warning: Main OpenAPI file {self.main_openapi_file} does not exist")
                return False
                
            with open(self.main_openapi_file, 'r', encoding='utf-8') as f:
                openapi_spec = yaml.safe_load(f)
            
            if not openapi_spec or 'paths' not in openapi_spec:
                print("Warning: Invalid OpenAPI specification format")
                return False
            
            # Scan for available YAML files and generate correct paths
            available_paths = {}
            changes_needed = False
            
            for version, base_dir in self.yaml_dirs.items():
                if not os.path.exists(base_dir):
                    continue
                    
                for filename in os.listdir(base_dir):
                    if filename.endswith(('.yaml', '.yml')):
                        yaml_file = filename
                        yaml_path = f"./paths/{version}/{yaml_file}"
                        
                        # Generate API path from filename using the mapping logic
                        api_path = self._extract_path_from_yaml_filename(yaml_file, version)
                        available_paths[api_path] = yaml_path
            
            # Sort paths alphabetically
            sorted_available_paths = dict(sorted(available_paths.items()))
            
            # Check for missing paths in the OpenAPI spec
            current_paths = set(openapi_spec['paths'].keys())
            available_api_paths = set(sorted_available_paths.keys())
            
            missing_paths = available_api_paths - current_paths
            obsolete_paths = current_paths - available_api_paths
            
            if missing_paths:
                print(f"Found {len(missing_paths)} missing paths in OpenAPI spec:")
                for path in sorted(missing_paths):
                    print(f"  + {path}")
                changes_needed = True
            
            if obsolete_paths:
                print(f"Found {len(obsolete_paths)} obsolete paths in OpenAPI spec:")
                for path in sorted(obsolete_paths):
                    print(f"  - {path}")
                changes_needed = True
            
            # Rebuild the paths section with correct mappings and alphabetical sorting
            if changes_needed and not dry_run:
                # Create new paths section with sorted paths
                new_paths = {}
                for path in sorted(sorted_available_paths.keys()):
                    new_paths[path] = {'$ref': sorted_available_paths[path]}
                
                openapi_spec['paths'] = new_paths
                
                # Add metadata about the update
                if 'info' not in openapi_spec:
                    openapi_spec['info'] = {}
                
                openapi_spec['info']['x-last-updated'] = datetime.now().isoformat()
                openapi_spec['info']['x-updated-by'] = 'mapping.py script'
                
                # Write the updated spec
                with open(self.main_openapi_file, 'w', encoding='utf-8') as f:
                    yaml.dump(openapi_spec, f, default_flow_style=False, sort_keys=False, 
                             allow_unicode=True, width=120)
                
                print(f"✅ Updated {self.main_openapi_file}")
                print(f"   Total paths: {len(new_paths)} (sorted alphabetically)")
                return True
            
            elif dry_run:
                if missing_paths or obsolete_paths:
                    print("🔍 Dry run mode - no changes made")
                    return True
                else:
                    print("✅ OpenAPI spec is up to date")
                    return False
            else:
                print("✅ OpenAPI spec is up to date")
                return False
                
        except Exception as e:
            print(f"Error updating OpenAPI spec: {e}")
            return False

    def create_unified_mapping(self) -> Dict[str, Dict[str, MethodMapping]]:
        """
        Create unified mapping combining MDX, YAML, and JSON example mappings with name normalization.
        Returns dict with v1 and v2 mappings: {method: MethodMapping}
        """
        print("Scanning MDX files...")
        mdx_mappings = self.scan_mdx_files()
        
        print("Scanning YAML files...")
        yaml_mappings = self.scan_yaml_files()
        
        print("Scanning JSON examples...")
        example_mappings = self.scan_json_examples()
        
        unified = {"v1": {}, "v2": {}}
        
        # Get all methods from all sources
        for version in ["v1", "v2"]:
            all_methods = set()
            all_methods.update(mdx_mappings[version].keys())
            all_methods.update(yaml_mappings[version].keys())
            all_methods.update(example_mappings[version].keys())
            
            # Create MethodMapping objects for each method
            for method in all_methods:
                mdx_path = self._find_best_match(method, mdx_mappings[version])
                yaml_path = self._find_best_match(method, yaml_mappings[version])
                
                # Find example data
                examples_path = None
                example_count = 0
                example_data = self._find_best_match(method, {k: v for k, v in example_mappings[version].items()})
                if example_data:
                    examples_path, example_count = example_data
                
                unified[version][method] = MethodMapping(
                    method=method,
                    mdx_path=mdx_path,
                    yaml_path=yaml_path,
                    examples_path=examples_path,
                    example_count=example_count
                )
        
        return unified

    def save_unified_mapping(self, output_file: str = "unified_method_mapping.json") -> None:
        """Save unified mapping to JSON file."""
        unified = self.create_unified_mapping()
        
        # Convert MethodMapping objects to dicts for JSON serialization
        json_data = {}
        for version in unified:
            json_data[version] = {}
            # Sort methods alphabetically
            for method in sorted(unified[version].keys()):
                mapping = unified[version][method]
                json_data[version][method] = {
                    'method': mapping.method,
                    'mdx_path': mapping.mdx_path,
                    'yaml_path': mapping.yaml_path,
                    'examples_path': mapping.examples_path,
                    'has_mdx': mapping.has_mdx,
                    'has_yaml': mapping.has_yaml,
                    'has_examples': mapping.has_examples,
                    'is_complete': mapping.is_complete,
                    'example_count': mapping.example_count
                }
        
        # Add metadata
        json_data['_metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'generated_by': 'mapping.py',
            'total_methods': sum(len(json_data[v]) for v in ['v1', 'v2'])
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved unified mapping to {output_file}")
        self._print_mapping_stats(unified)

    def load_unified_mapping(self, input_file: str = "unified_method_mapping.json") -> Dict[str, Dict[str, MethodMapping]]:
        """Load unified mapping from JSON file."""
        with open(input_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        unified = {"v1": {}, "v2": {}}
        
        for version in ["v1", "v2"]:
            if version in json_data:
                for method, data in json_data[version].items():
                    unified[version][method] = MethodMapping(
                        method=data['method'],
                        mdx_path=data['mdx_path'],
                        yaml_path=data['yaml_path'],
                        examples_path=data.get('examples_path'),
                        example_count=data.get('example_count', 0)
                    )
        
        return unified
    
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
    
    def _print_mapping_stats(self, unified: Dict[str, Dict[str, MethodMapping]]) -> None:
        """Print detailed statistics about the mapping."""
        self._print_detailed_mapping_stats(unified)

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
            with_examples = [m for m in mappings if m.has_examples]
            
            print(f"\n{version.upper()} Coverage:")
            print(f"  ✓ Complete (both MDX & YAML): {len(with_both)}")
            print(f"  ⚠ MDX only (missing YAML): {len(mdx_only)}")
            print(f"  ⚠ YAML only (missing MDX): {len(yaml_only)}")
            print(f"  ✗ Missing both: {len(missing_both)}")
            
            # Example coverage stats
            total_examples = sum(m.example_count for m in mappings)
            coverage_pct = (len(with_examples) / len(mappings) * 100) if mappings else 0
            print(f"  🧪 With examples: {len(with_examples)}/{len(mappings)} ({coverage_pct:.1f}%) - {total_examples} total examples")
            
            # List missing items if any
            if mdx_only:
                print(f"\n  Methods missing YAML ({version}):")
                for mapping in sorted(mdx_only, key=lambda x: x.method):
                    examples_info = f" [{mapping.example_count} examples]" if mapping.has_examples else ""
                    print(f"    - {mapping.method}{examples_info}")
            
            if yaml_only:
                print(f"\n  Methods missing MDX ({version}):")
                for mapping in sorted(yaml_only, key=lambda x: x.method):
                    examples_info = f" [{mapping.example_count} examples]" if mapping.has_examples else ""
                    print(f"    - {mapping.method}{examples_info}")
            
            if missing_both:
                print(f"\n  Methods missing both MDX & YAML ({version}):")
                for mapping in sorted(missing_both, key=lambda x: x.method):
                    examples_info = f" [{mapping.example_count} examples]" if mapping.has_examples else ""
                    print(f"    - {mapping.method}{examples_info}")
        
        print(f"\n{'='*60}")

    def generate_focused_spec(self, focus_type: str = "activation", output_file: str = None) -> bool:
        """
        Generate a focused OpenAPI specification for specific functionality.
        
        Args:
            focus_type: Type of focus ("activation", "lightning", "trading", etc.)
            output_file: Output file path (auto-generated if None)
            
        Returns:
            True if generation was successful
        """
        try:
            # Load main OpenAPI spec
            if not os.path.exists(self.main_openapi_file):
                print(f"Error: Main OpenAPI file {self.main_openapi_file} not found")
                return False
            
            with open(self.main_openapi_file, 'r', encoding='utf-8') as f:
                main_spec = yaml.safe_load(f)
            
            # Define focus filters
            focus_filters = {
                "activation": [
                    "/v2/task/enable_", "/v2/enable_", "/v2/task/enable_lightning"
                ],
                "lightning": [
                    "/v2/lightning/", "/v2/task/enable_lightning"
                ],
                "trading": [
                    "/v2/swaps_and_orders/", "/v1/buy", "/v1/sell", "/v1/setprice", 
                    "/v1/cancel_order", "/v1/orderbook"
                ],
                "wallet": [
                    "/v2/wallet/", "/v1/my_balance", "/v1/withdraw", "/v2/withdraw"
                ]
            }
            
            if focus_type not in focus_filters:
                print(f"Error: Unknown focus type '{focus_type}'. Available: {list(focus_filters.keys())}")
                return False
            
            # Create focused spec
            focused_spec = {
                "openapi": main_spec["openapi"],
                "info": {
                    "title": f"Komodo DeFi Framework {focus_type.title()} API",
                    "version": main_spec["info"]["version"],
                    "description": f"Focused OpenAPI specification for {focus_type} endpoints in the Komodo DeFi Framework.\n\nFor the complete API specification, see the main openapi.yaml file."
                },
                "servers": main_spec["servers"],
                "tags": [],
                "paths": {},
                "components": {
                    "securitySchemes": main_spec["components"]["securitySchemes"],
                    "schemas": {}
                },
                "security": main_spec["security"]
            }
            
            # Filter paths based on focus type
            patterns = focus_filters[focus_type]
            for path, path_spec in main_spec["paths"].items():
                if any(pattern in path for pattern in patterns):
                    focused_spec["paths"][path] = path_spec
            
            # Sort paths alphabetically
            focused_spec["paths"] = dict(sorted(focused_spec["paths"].items()))
            
            # Add relevant tags
            focus_tag_mapping = {
                "activation": ["Coin Activation", "Token Activation", "Lightning Activation"],
                "lightning": ["Lightning Network", "Lightning Activation"],
                "trading": ["Trading & Orders", "Atomic Swaps"],
                "wallet": ["Wallet Management"]
            }
            
            if focus_type in focus_tag_mapping:
                for tag in main_spec.get("tags", []):
                    if tag["name"] in focus_tag_mapping[focus_type]:
                        focused_spec["tags"].append(tag)
            
            # Add essential schemas (could be enhanced to detect used schemas)
            essential_schemas = ["Common"]
            if focus_type == "activation":
                essential_schemas.extend(["Activation"])
            elif focus_type == "lightning":
                essential_schemas.extend(["Lightning", "Activation"])
            elif focus_type == "trading":
                essential_schemas.extend(["Orders", "Swaps", "MakerEvents", "TakerEvents"])
            elif focus_type == "wallet":
                essential_schemas.extend(["Wallet"])
            
            for schema_name in essential_schemas:
                if schema_name in main_spec["components"]["schemas"]:
                    focused_spec["components"]["schemas"][schema_name] = main_spec["components"]["schemas"][schema_name]
            
            # Generate output filename
            if output_file is None:
                output_file = f"../../postman/openapi/{focus_type}_generated.yaml"
            
            # Write focused spec
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(focused_spec, f, default_flow_style=False, sort_keys=False, 
                         allow_unicode=True, width=120)
            
            path_count = len(focused_spec["paths"])
            print(f"✅ Generated focused {focus_type} spec with {path_count} endpoints: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error generating focused spec: {e}")
            return False

    def debug_method_matching(self, method_name: str, version: str = "v2") -> None:
        """
        Debug method name matching issues by showing all attempted variations.
        
        Args:
            method_name: The method name to debug
            version: The API version to check against
        """
        print(f"\n🔍 Debugging method matching for: {method_name}")
        
        # Get mappings
        mdx_mappings = self.scan_mdx_files()
        yaml_mappings = self.scan_yaml_files()
        example_mappings = self.scan_json_examples()
        
        variations = self._normalize_method_name(method_name)
        print(f"📝 Generated variations:")
        for i, variation in enumerate(variations, 1):
            print(f"  {i}. {variation}")
        
        # Check MDX mappings
        print(f"\n📄 MDX mapping check:")
        mdx_match = self._find_best_match(method_name, mdx_mappings[version])
        if mdx_match:
            print(f"  ✅ Found: {mdx_match}")
        else:
            print(f"  ❌ Not found in MDX mappings")
            # Show similar methods
            similar_mdx = [m for m in mdx_mappings[version].keys() 
                          if any(part in m for part in method_name.split('::'))][:5]
            if similar_mdx:
                print(f"  🔍 Similar MDX methods:")
                for similar in similar_mdx:
                    print(f"    - {similar}")
        
        # Check YAML mappings
        print(f"\n📋 YAML mapping check:")
        yaml_match = self._find_best_match(method_name, yaml_mappings[version])
        if yaml_match:
            print(f"  ✅ Found: {yaml_match}")
        else:
            print(f"  ❌ Not found in YAML mappings")
            # Show similar methods
            similar_yaml = [m for m in yaml_mappings[version].keys() 
                           if any(part in m for part in method_name.split('::'))][:5]
            if similar_yaml:
                print(f"  🔍 Similar YAML methods:")
                for similar in similar_yaml:
                    print(f"    - {similar}")
        
        # Check example mappings
        print(f"\n🧪 Example mapping check:")
        example_data = self._find_best_match(method_name, {k: v for k, v in example_mappings[version].items()})
        if example_data:
            path, count = example_data
            print(f"  ✅ Found: {path} ({count} examples)")
        else:
            print(f"  ❌ Not found in example mappings")
            # Show similar methods
            similar_examples = [m for m in example_mappings[version].keys() 
                               if any(part in m for part in method_name.split('::'))][:5]
            if similar_examples:
                print(f"  🔍 Similar example methods:")
                for similar in similar_examples:
                    count = example_mappings[version][similar][1]
                    print(f"    - {similar} ({count} examples)")
        
        print(f"\n" + "="*60)

    def remove_method_files(self, method_name: str, dry_run: bool = False) -> None:
        """
        Remove all MDX, YAML, and JSON example files related to the specified method.
        Args:
            method_name: The method to remove (any format)
            dry_run: If True, only print what would be deleted
        """
        print(f"\n🔍 Searching for files related to method: {method_name}")
        unified = self.create_unified_mapping()
        found = []
        for version in ["v1", "v2"]:
            for m, mapping in unified[version].items():
                if m == method_name or m in self._normalize_method_name(method_name) or method_name in self._normalize_method_name(m):
                    found.append((version, mapping))
        if not found:
            print(f"❌ No files found for method '{method_name}'.")
            return
        files_to_delete = []
        dirs_to_delete = []
        for version, mapping in found:
            if mapping.mdx_path:
                mdx_dir = os.path.dirname(os.path.abspath(mapping.mdx_path))
                if os.path.isdir(mdx_dir):
                    dirs_to_delete.append(mdx_dir)
            if mapping.yaml_path:
                yaml_file = os.path.abspath(mapping.yaml_path)
                if os.path.isfile(yaml_file):
                    files_to_delete.append(yaml_file)
            if mapping.examples_path:
                ex_dir = os.path.abspath(mapping.examples_path)
                if os.path.isdir(ex_dir):
                    dirs_to_delete.append(ex_dir)
        if not files_to_delete and not dirs_to_delete:
            print(f"❌ No files or directories found for method '{method_name}'.")
            return
        print("\nThe following files/directories will be deleted:")
        for d in dirs_to_delete:
            print(f"  [DIR] {d}")
        for f in files_to_delete:
            print(f"  [FILE] {f}")
        confirm = input("\nAre you sure you want to delete these files/directories? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Aborted.")
            return
        for d in dirs_to_delete:
            if dry_run:
                print(f"[DRY RUN] Would remove directory: {d}")
            else:
                try:
                    shutil.rmtree(d)
                    print(f"Removed directory: {d}")
                except Exception as e:
                    print(f"Error removing directory {d}: {e}")
        for f in files_to_delete:
            if dry_run:
                print(f"[DRY RUN] Would remove file: {f}")
            else:
                try:
                    os.remove(f)
                    print(f"Removed file: {f}")
                except Exception as e:
                    print(f"Error removing file {f}: {e}")
        print("\n✅ Removal complete.")


def main():
    """Main function to generate unified method mapping and update OpenAPI spec."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Method Mapping and OpenAPI Management Tool')
    parser.add_argument('--update-openapi', action='store_true',
                       help='Update the main OpenAPI specification file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without making changes')
    parser.add_argument('--mapping-only', action='store_true',
                       help='Only generate mapping files, skip OpenAPI update')
    parser.add_argument('--verbose', '-v', action='store_true', default=True,
                       help='Enable verbose output')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')
    parser.add_argument('--generate-focused', choices=['activation', 'lightning', 'trading', 'wallet'],
                       help='Generate a focused OpenAPI spec for specific functionality')
    parser.add_argument('--remove', type=str, metavar='METHOD',
                       help='Remove all files related to the specified method (MDX, YAML, JSON examples)')
    
    args = parser.parse_args()
    
    # Change to script directory for relative paths
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Set verbosity
    verbose = args.verbose and not args.quiet
    
    mapper = MethodMapper(verbose=verbose)
    
    if args.remove:
        mapper.remove_method_files(args.remove, dry_run=args.dry_run)
        return 0
    
    if not args.quiet:
        print("🚀 Starting Komodo DeFi Framework API mapping and maintenance...")
    
    # Always generate the unified mapping unless specifically skipped
    if not args.update_openapi or not args.mapping_only:
        if not args.quiet:
            print("\n📋 Generating unified method mapping...")
        mapper.save_unified_mapping()
    
    # Update OpenAPI spec if requested or if not in mapping-only mode
    if args.update_openapi or not args.mapping_only:
        if not args.quiet:
            print("\n🔧 Updating main OpenAPI specification...")
        
        try:
            updated = mapper.update_main_openapi_spec(dry_run=args.dry_run)
            if updated and not args.dry_run:
                if not args.quiet:
                    print("✅ OpenAPI specification updated successfully!")
            elif args.dry_run:
                if not args.quiet:
                    print("🔍 Dry run completed - no files were modified")
        except Exception as e:
            print(f"❌ Error updating OpenAPI specification: {e}")
            return 1
    
    # Generate focused specification if requested
    if args.generate_focused:
        if not args.quiet:
            print(f"\n🎯 Generating focused {args.generate_focused} specification...")
        
        try:
            success = mapper.generate_focused_spec(args.generate_focused)
            if not success:
                print(f"❌ Failed to generate focused {args.generate_focused} specification")
                return 1
        except Exception as e:
            print(f"❌ Error generating focused specification: {e}")
            return 1
    
    if not args.quiet:
        print("\n🎉 Operation completed successfully!")
    
    return 0


if __name__ == "__main__":
    exit(main()) 