#!/usr/bin/env python3
"""
Unified File Scanners

Consolidated file scanning functionality for the Komodo Documentation Library.
Handles MDX, YAML, and JSON file scanning with unified logic.
"""

import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, Tuple, List, Optional, Any, Union
from dataclasses import dataclass

from ..core.logging_utils import get_logger
from ..utils.file_utils import (
    normalize_file_path, safe_read_json, find_files_by_pattern,
    extract_filename_parts, get_file_stats
)
from ..utils.string_utils import convert_dir_to_method_name


@dataclass
class ScanResult:
    """Result from scanning a file or directory."""
    success: bool
    file_path: str
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UnifiedScanner:
    """
    Unified scanner for all file types in the KDF documentation system.
    
    Consolidates scanning logic for MDX, YAML, and JSON files with
    consistent error handling and reporting.
    """
    
    def __init__(self, base_directories: Dict[str, Union[str, Path]] = None, 
                 verbose: bool = True):
        self.base_directory = "."
        self.verbose = verbose
        self.logger = get_logger("unified-scanner")
        
        self.base_directories = base_directories or {}
        
        # Default directory configurations
        if not self.base_directories:
            self.base_directories = {
                'mdx_v1': '../../src/pages/komodo-defi-framework/api/legacy',
                'mdx_v2': '../../src/pages/komodo-defi-framework/api/v20',
                'mdx_v2_dev': '../../src/pages/komodo-defi-framework/api/v20-dev',
                'yaml_v1': '../../openapi/paths/v1',
                'yaml_v2': '../../openapi/paths/v2',
                'json_v1': '../../postman/json/kdf/v1',
                'json_v2': '../../postman/json/kdf/v2',
            }
        
        if self.verbose:
            self.logger.info(f"Initialized UnifiedScanner with {len(self.base_directories)} directories")
    
    def scan_all_files(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Dict[str, Any]]:
        """
        Scan all file types for specified versions.
        
        Args:
            versions: List of API versions to scan
            
        Returns:
            Dictionary with scanning results for all file types
        """
        results = {}
        
        for version in versions:
            results[version] = {
                'mdx_files': self.scan_mdx_files(version),
                'yaml_files': self.scan_yaml_files(version),
                'json_examples': self.scan_json_examples(version)
            }
            
            if self.verbose:
                mdx_count = len(results[version]['mdx_files'])
                yaml_count = len(results[version]['yaml_files'])
                json_count = sum(len(examples) for examples in results[version]['json_examples'].values())
                
                self.logger.info(f"{version.upper()}: {mdx_count} MDX, {yaml_count} YAML, {json_count} JSON files")
        
        return results
    
    def scan_mdx_files(self, version: str = None) -> Dict[str, str]:
        """
        Scan MDX files to extract API method names and version information.
        
        Args:
            version: Specific version to scan, or None for all
            
        Returns:
            Dictionary mapping method names to file paths
        """
        method_pages = {}
        
        # Determine which directories to scan
        dirs_to_scan = {}
        if version:
            key = f'mdx_{version}'
            if key in self.base_directories:
                dirs_to_scan[key] = self.base_directories[key]
            # Also include v2_dev for v2 scanning
            if version == 'v2' and 'mdx_v2_dev' in self.base_directories:
                dirs_to_scan['mdx_v2_dev'] = self.base_directories['mdx_v2_dev']
        else:
            dirs_to_scan = {k: v for k, v in self.base_directories.items() if k.startswith('mdx_')}
        
        omit_path = normalize_file_path('../../src/pages/komodo-defi-framework/api/v20/index.mdx')
        
        for dir_key, base_dir in dirs_to_scan.items():
            if not Path(base_dir).exists():
                if self.verbose:
                    self.logger.warning(f"Directory does not exist: {base_dir}")
                continue
            
            # Extract version from directory key
            dir_version = dir_key.split('_')[-1] if '_' in dir_key else 'unknown'
            # Handle v2_dev as v2
            if dir_key == 'mdx_v2_dev':
                dir_version = 'v2'
            is_legacy = (dir_version == 'v1' or 'legacy' in base_dir)
            
            # Find all index.mdx files
            mdx_files = find_files_by_pattern(base_dir, "index.mdx", recursive=True)
            
            for mdx_path in mdx_files:
                # Skip the main index file
                if mdx_path.resolve() == omit_path.resolve():
                    continue
                
                try:
                    methods = self._extract_methods_from_mdx_file(mdx_path, is_legacy)
                    
                    for method in methods:
                        relative_path = os.path.relpath(str(mdx_path), '.')
                        
                        # Skip duplicate detection for batch_requests file
                        is_batch_requests = 'batch_requests' in str(mdx_path)
                        
                        if method in method_pages and not is_batch_requests:
                            if self.verbose:
                                self.logger.warning(f"Duplicate method '{method}' found in: {relative_path}")
                        
                        # Only store non-batch_requests methods in the main mapping
                        if not is_batch_requests:
                            method_pages[method] = relative_path
                
                except Exception as e:
                    if self.verbose:
                        self.logger.error(f"Error processing MDX file {mdx_path}: {e}")
        
        return method_pages
    
    def scan_yaml_files(self, version: str = None) -> Dict[str, str]:
        """
        Scan YAML files to extract API method specifications.
        
        Args:
            version: Specific version to scan, or None for all
            
        Returns:
            Dictionary mapping method names to file paths
        """
        method_yaml = {}
        
        # Determine which directories to scan
        dirs_to_scan = {}
        if version:
            key = f'yaml_{version}'
            if key in self.base_directories:
                dirs_to_scan[key] = self.base_directories[key]
        else:
            dirs_to_scan = {k: v for k, v in self.base_directories.items() if k.startswith('yaml_')}
        
        for dir_key, base_dir in dirs_to_scan.items():
            if not Path(base_dir).exists():
                if self.verbose:
                    self.logger.warning(f"Directory does not exist: {base_dir}")
                continue
            
            # Find all YAML files
            yaml_files = find_files_by_pattern(base_dir, "*.yaml", recursive=False)
            yaml_files.extend(find_files_by_pattern(base_dir, "*.yml", recursive=False))
            
            for yaml_path in yaml_files:
                try:
                    method = self._extract_method_from_yaml_file(yaml_path)
                    if method:
                        relative_path = os.path.relpath(str(yaml_path), '.')
                        
                        if method in method_yaml:
                            if self.verbose:
                                self.logger.warning(f"Duplicate method '{method}' found in YAML: {relative_path}")
                        
                        method_yaml[method] = relative_path
                    else:
                        if self.verbose:
                            self.logger.warning(f"Could not extract method from: {yaml_path}")
                
                except Exception as e:
                    if self.verbose:
                        self.logger.error(f"Error processing YAML file {yaml_path}: {e}")
        
        return method_yaml
    
    def scan_json_examples(self, version: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scan JSON example files and organize by method and operation.
        
        Args:
            version: Specific version to scan, or None for all
            
        Returns:
            Dictionary mapping method names to lists of example data
        """
        json_examples = {}
        
        # Determine which directories to scan
        dirs_to_scan = {}
        if version:
            key = f'json_{version}'
            if key in self.base_directories:
                dirs_to_scan[key] = self.base_directories[key]
        else:
            dirs_to_scan = {k: v for k, v in self.base_directories.items() if k.startswith('json_')}
        
        for dir_key, base_dir in dirs_to_scan.items():
            if not Path(base_dir).exists():
                if self.verbose:
                    self.logger.warning(f"Directory does not exist: {base_dir}")
                continue
            
            # Scan method directories
            base_path = Path(base_dir)
            
            for method_dir in base_path.iterdir():
                if not method_dir.is_dir():
                    continue
                
                method_name = convert_dir_to_method_name(method_dir.name)
                
                # Scan for JSON files in method directory and subdirectories
                json_files = find_files_by_pattern(method_dir, "*.json", recursive=True)
                
                examples = []
                for json_file in json_files:
                    try:
                        example_data = self._process_json_example_file(json_file, method_name)
                        if example_data:
                            examples.append(example_data)
                    
                    except Exception as e:
                        if self.verbose:
                            self.logger.error(f"Error processing JSON file {json_file}: {e}")
                
                if examples:
                    json_examples[method_name] = examples
        
        return json_examples
    
    def scan_directory_structure(self, directory: Union[str, Path]) -> Dict[str, Any]:
        """
        Scan and analyze the structure of a directory.
        
        Args:
            directory: Directory to analyze
            
        Returns:
            Dictionary with directory structure analysis
        """
        dir_path = normalize_file_path(directory)
        
        if not dir_path.exists():
            return {'error': f'Directory does not exist: {dir_path}'}
        
        structure = {
            'directory': str(dir_path),
            'subdirectories': [],
            'files_by_type': {},
            'total_files': 0,
            'depth_analysis': {}
        }
        
        # Analyze directory structure
        for item in dir_path.rglob('*'):
            if item.is_file():
                # Count files by extension
                ext = item.suffix.lower()
                if ext not in structure['files_by_type']:
                    structure['files_by_type'][ext] = []
                
                relative_path = str(item.relative_to(dir_path))
                structure['files_by_type'][ext].append(relative_path)
                structure['total_files'] += 1
                
                # Analyze depth
                depth = len(item.relative_to(dir_path).parts) - 1
                if depth not in structure['depth_analysis']:
                    structure['depth_analysis'][depth] = 0
                structure['depth_analysis'][depth] += 1
            
            elif item.is_dir() and item != dir_path:
                relative_path = str(item.relative_to(dir_path))
                structure['subdirectories'].append(relative_path)
        
        return structure
    
    def _extract_methods_from_mdx_file(self, mdx_path: Path, is_legacy: bool = False) -> List[str]:
        """
        Extract method names from an MDX file.
        
        Args:
            mdx_path: Path to MDX file
            is_legacy: Whether this is a legacy API file
            
        Returns:
            List of method names found
        """
        methods = []
        
        try:
            with open(mdx_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
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
                        
                        # Determine version based on mmrpc field
                        if is_legacy or '"mmrpc": "1.0"' in code or '"mmrpc":' not in code:
                            methods.append(method)
                        elif '"mmrpc": "2.0"' in code:
                            methods.append(method)
        
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error reading MDX file {mdx_path}: {e}")
        
        return sorted(list(set(methods)))
    
    def _extract_method_from_yaml_file(self, yaml_path: Path) -> Optional[str]:
        """
        Extract method name from a YAML file.
        
        Args:
            yaml_path: Path to YAML file
            
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
            
            # Method 3: Extract from filename if other methods fail
            filename_parts = extract_filename_parts(yaml_path)
            if filename_parts['stem']:
                return filename_parts['stem']
        
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error reading YAML file {yaml_path}: {e}")
        
        return None
    
    def _process_json_example_file(self, json_path: Path, method_name: str) -> Optional[Dict[str, Any]]:
        """
        Process a JSON example file and extract relevant data.
        
        Args:
            json_path: Path to JSON file
            method_name: Associated method name
            
        Returns:
            Dictionary with example data or None if invalid
        """
        try:
            json_data = safe_read_json(json_path)
            
            # Validate that it's a valid API example
            if not isinstance(json_data, dict) or 'method' not in json_data:
                return None
            
            # Extract operation and description from file path
            path_parts = json_path.parts
            operation = "default"
            description = "basic_request"
            
            # Try to determine operation from directory structure
            if len(path_parts) >= 2:
                # Look for operation in parent directory name
                parent_dir = path_parts[-2]
                if parent_dir in ['init', 'status', 'cancel', 'user_action']:
                    operation = parent_dir
            
            # Extract description from filename
            filename_parts = extract_filename_parts(json_path)
            if filename_parts['stem']:
                # Parse filename for description
                name_parts = filename_parts['stem'].split('-')
                if len(name_parts) >= 2:
                    description = '-'.join(name_parts[1:])  # Skip first part which is usually method
            
            return {
                'file_path': str(json_path),
                'relative_path': os.path.relpath(str(json_path), '.'),
                'method_name': method_name,
                'operation': operation,
                'description': description,
                'json_method': json_data.get('method', ''),
                'has_params': 'params' in json_data,
                'has_mmrpc': 'mmrpc' in json_data,
                'mmrpc_version': json_data.get('mmrpc', '1.0'),
                'data': json_data
            }
        
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error processing JSON example {json_path}: {e}")
            return None
    
    def get_scan_summary(self, scan_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of scan results.
        
        Args:
            scan_results: Results from scan_all_files()
            
        Returns:
            Summary statistics
        """
        summary = {
            'total_versions': len(scan_results),
            'by_version': {},
            'totals': {
                'mdx_files': 0,
                'yaml_files': 0,
                'json_examples': 0
            }
        }
        
        for version, results in scan_results.items():
            mdx_count = len(results.get('mdx_files', {}))
            yaml_count = len(results.get('yaml_files', {}))
            json_count = sum(len(examples) for examples in results.get('json_examples', {}).values())
            
            summary['by_version'][version] = {
                'mdx_files': mdx_count,
                'yaml_files': yaml_count,
                'json_examples': json_count,
                'total': mdx_count + yaml_count + json_count
            }
            
            # Update totals
            summary['totals']['mdx_files'] += mdx_count
            summary['totals']['yaml_files'] += yaml_count
            summary['totals']['json_examples'] += json_count
        
        summary['totals']['all_files'] = sum(summary['totals'].values())
        
        return summary 