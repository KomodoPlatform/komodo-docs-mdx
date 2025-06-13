#!/usr/bin/env python3
"""
File Scanners

Specialized scanners for different file types in the KDF documentation system.
Handles MDX, YAML, and JSON file scanning with specific extraction logic.
"""

import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, Tuple, List, Optional


class MDXScanner:
    """Scans MDX files to extract API method names and version information."""
    
    def __init__(self, mdx_dirs: Dict[str, str], verbose: bool = True):
        self.mdx_dirs = mdx_dirs
        self.verbose = verbose
    
    def scan_mdx_files(self) -> Dict[str, Dict[str, str]]:
        """
        Scan all MDX files and extract method mappings.
        
        Returns:
            Dictionary mapping versions to methods to file paths
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
                    
                    # Skip the main index file
                    if mdx_path == omit_path:
                        continue
                    
                    try:
                        with open(os.path.join(root, 'index.mdx'), 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        v1_methods, v2_methods = self._extract_methods_from_mdx(content, is_legacy)
                        
                        # Store method mappings with warning for duplicates
                        for method in v1_methods:
                            if method in method_pages["v1"]:
                                if self.verbose:
                                    print(f"[WARN] Method '{method}' for v1 found in multiple MDX files: "
                                         f"'{method_pages['v1'][method]}' and '{mdx_path}'")
                            method_pages["v1"][method] = mdx_path
                        
                        for method in v2_methods:
                            if method in method_pages["v2"]:
                                if self.verbose:
                                    print(f"[WARN] Method '{method}' for v2 found in multiple MDX files: "
                                         f"'{method_pages['v2'][method]}' and '{mdx_path}'")
                            method_pages["v2"][method] = mdx_path
                    
                    except Exception as e:
                        if self.verbose:
                            print(f"Error processing MDX file {mdx_path}: {e}")
        
        return method_pages
    
    def _extract_methods_from_mdx(self, content: str, is_legacy: bool) -> Tuple[List[str], List[str]]:
        """
        Extract method names from MDX content.
        
        Args:
            content: The MDX file content
            is_legacy: Whether this is a legacy API file
            
        Returns:
            Tuple of (v1_methods, v2_methods)
        """
        v1_methods = []
        v2_methods = []
        
        # Find all CodeGroup blocks
        codegroups = re.findall(r'<CodeGroup[\s\S]*?>([\s\S]*?)</CodeGroup>', content, re.MULTILINE)
        
        for block in codegroups:
            # Extract code blocks from within CodeGroup
            code_blocks = re.findall(r'```[a-zA-Z]*\n([\s\S]*?)```', block)
            
            for code in code_blocks:
                # Look for method field in JSON
                method_match = re.search(r'"method"\s*:\s*"([a-zA-Z0-9_:.-]+)"', code)
                if method_match:
                    method = method_match.group(1)
                    
                    if is_legacy:
                        v1_methods.append(method)
                    elif '"mmrpc": "2.0"' in code:
                        v2_methods.append(method)
                    else:
                        v1_methods.append(method)
        
        return sorted(list(set(v1_methods))), sorted(list(set(v2_methods)))


class YAMLScanner:
    """Scans YAML files to extract API method specifications."""
    
    def __init__(self, yaml_dirs: Dict[str, str], verbose: bool = True):
        self.yaml_dirs = yaml_dirs
        self.verbose = verbose
    
    def scan_yaml_files(self) -> Dict[str, Dict[str, str]]:
        """
        Scan all YAML files and extract method mappings.
        
        Returns:
            Dictionary mapping versions to methods to file paths
        """
        method_yaml = {"v1": {}, "v2": {}}
        
        for version, base_dir in self.yaml_dirs.items():
            if not os.path.exists(base_dir):
                if self.verbose:
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
                                if self.verbose:
                                    print(f"[WARN] Method '{method}' for {version} found in multiple YAML files: "
                                         f"'{method_yaml[version][method]}' and '{relative_path}'")
                            method_yaml[version][method] = relative_path
                        else:
                            if self.verbose:
                                print(f"[WARN] Could not extract method from {relative_path}")
                    
                    except Exception as e:
                        if self.verbose:
                            print(f"Error processing YAML file {yaml_path}: {e}")
        
        return method_yaml
    
    def _extract_method_from_yaml(self, yaml_path: str) -> Optional[str]:
        """
        Extract method name from a YAML file.
        
        Args:
            yaml_path: Path to the YAML file
            
        Returns:
            Method name or None if not found
        """
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to parse as YAML and extract from structure
            try:
                data = yaml.safe_load(content)
                
                # Method 1: Look for path keys starting with /
                for path_key in data.keys():
                    if path_key.startswith('/'):
                        method = path_key.strip('/').rstrip(':')
                        return method
            except yaml.YAMLError:
                pass
            
            # Method 2: Look for operationId in raw content
            operation_id_match = re.search(r'^\s*operationId:\s*(.+?)\s*$', content, re.MULTILINE)
            if operation_id_match:
                operation_id = operation_id_match.group(1).strip().strip('"\'')
                return operation_id
            
            # Method 3: Extract from schema method enum
            try:
                data = yaml.safe_load(content)
                
                for path, path_data in data.items():
                    if 'post' in path_data:
                        request_body = path_data['post'].get('requestBody', {})
                        content_data = request_body.get('content', {})
                        app_json = content_data.get('application/json', {})
                        schema = app_json.get('schema', {})
                        
                        # Handle allOf schema
                        if 'allOf' in schema:
                            for item in schema['allOf']:
                                if 'properties' in item:
                                    method_prop = item['properties'].get('method')
                                    if method_prop and 'enum' in method_prop and method_prop['enum']:
                                        return method_prop['enum'][0]
                        
                        # Handle direct properties schema
                        if 'properties' in schema:
                            method_prop = schema['properties'].get('method')
                            if method_prop and 'enum' in method_prop and method_prop['enum']:
                                return method_prop['enum'][0]
            
            except yaml.YAMLError:
                pass
        
        except Exception as e:
            if self.verbose:
                print(f"Error reading {yaml_path}: {e}")
        
        return None


class JSONExampleScanner:
    """Scans JSON example files to extract method mappings and counts."""
    
    def __init__(self, json_dirs: Dict[str, str], verbose: bool = True):
        self.json_dirs = json_dirs
        self.verbose = verbose
    
    def scan_json_examples(self) -> Dict[str, Dict[str, Tuple[str, int]]]:
        """
        Scan all JSON example files and extract method mappings.
        
        Returns:
            Dictionary mapping versions to methods to (path, count) tuples
        """
        method_examples = {"v1": {}, "v2": {}}
        
        for version, base_dir in self.json_dirs.items():
            if not os.path.exists(base_dir):
                if self.verbose:
                    print(f"Warning: Examples directory {base_dir} does not exist")
                continue
            
            for method_dir in os.listdir(base_dir):
                method_path = os.path.join(base_dir, method_dir)
                if not os.path.isdir(method_path):
                    continue
                
                # Convert method directory name to method name
                method_name_base = self._convert_dir_to_method_name(method_dir)
                
                # Scan operation subdirectories
                for operation_dir in os.listdir(method_path):
                    operation_path = os.path.join(method_path, operation_dir)
                    if not os.path.isdir(operation_path):
                        continue
                    
                    # Count JSON files
                    json_files = [f for f in os.listdir(operation_path) if f.endswith('.json')]
                    example_count = len(json_files)
                    
                    if example_count > 0:
                        full_method_name = self._build_full_method_name(method_name_base, operation_dir)
                        relative_path = os.path.relpath(operation_path, '.')
                        method_examples[version][full_method_name] = (relative_path, example_count)
        
        return method_examples
    
    def _convert_dir_to_method_name(self, method_dir: str) -> str:
        """Convert directory name to base method name."""
        method_name_base = method_dir.replace('-', '::')
        
        # Handle special cases
        if method_name_base == "task::enable::z::coin":
            method_name_base = "task::enable_z_coin"
        elif method_name_base.startswith("task::enable::"):
            method_name_base = method_name_base.replace("::enable::", "::enable_")
        
        return method_name_base
    
    def _build_full_method_name(self, base_method: str, operation_dir: str) -> str:
        """Build full method name from base method and operation."""
        if operation_dir == 'default':
            return base_method
        
        operation_name = operation_dir.replace('-', '_')
        
        # Handle special cases where operation is already in the method name
        if (base_method.endswith(f"::{operation_name}") or
            (base_method.startswith("stream::") and operation_name == "enable" and base_method.endswith("::enable")) or
            (base_method.startswith("lightning::") and operation_name in base_method)):
            return base_method
        
        return f"{base_method}::{operation_name}"


class PathExtractor:
    """Utilities for extracting API paths from YAML filenames."""
    
    @staticmethod
    def extract_path_from_yaml_filename(yaml_filename: str, version: str) -> str:
        """
        Extract API path from YAML filename.
        
        Args:
            yaml_filename: The YAML filename
            version: API version (v1 or v2)
            
        Returns:
            API path string
        """
        # Remove .yaml extension if present
        if yaml_filename.endswith('.yaml') or yaml_filename.endswith('.yml'):
            yaml_filename = yaml_filename.rsplit('.', 1)[0]
        
        # Simple rule: prepend version prefix
        return f"/{version}/{yaml_filename}" 