#!/usr/bin/env python3
"""
Method Mapping Coordinator

Main coordinator for mapping API methods to their corresponding MDX and YAML files.
Uses specialized components for scanning, normalization, and reporting.
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import specialized components
from .method_normalizer import MethodNameNormalizer
from .file_scanners import MDXScanner, YAMLScanner, JSONExampleScanner
from .openapi_manager import OpenAPIManager
from .mapping_reports import MethodMapping, MappingReporter


class MethodMapper:
    """
    Main coordinator for mapping API methods to their corresponding files.
    
    Uses specialized components:
    - MethodNameNormalizer: Handles method name variations
    - File scanners: Extract method information from different file types
    - OpenAPIManager: Manages OpenAPI specifications
    - MappingReporter: Generates detailed reports
    """
    
    def __init__(self, base_path: str = ".", verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        
        # Directory configurations
        self.mdx_dirs = {
            'legacy': '../../src/pages/komodo-defi-framework/api/legacy',
            'v2': '../../src/pages/komodo-defi-framework/api/v20',
            'v2-dev': '../../src/pages/komodo-defi-framework/api/v20-dev',
        }
        self.yaml_dirs = {
            'v1': '../../openapi/paths/v1',
            'v2': '../../openapi/paths/v2',
        }
        self.json_dirs = {
            'v1': '../../postman/json/kdf/v1',
            'v2': '../../postman/json/kdf/v2',
        }
        self.main_openapi_file = '../../openapi/openapi.yaml'
        
        # Initialize components
        self.normalizer = MethodNameNormalizer()
        self.mdx_scanner = MDXScanner(self.mdx_dirs, verbose)
        self.yaml_scanner = YAMLScanner(self.yaml_dirs, verbose)
        self.json_scanner = JSONExampleScanner(self.json_dirs, verbose)
        self.openapi_manager = OpenAPIManager(self.main_openapi_file, self.yaml_dirs, verbose)
        self.reporter = MappingReporter(verbose)
    
    def scan_mdx_files(self) -> Dict[str, Dict[str, str]]:
        """Scan MDX files and extract method mappings."""
        if self.verbose:
            print("Scanning MDX files...")
        return self.mdx_scanner.scan_mdx_files()
    
    def scan_yaml_files(self) -> Dict[str, Dict[str, str]]:
        """Scan YAML files and extract method mappings."""
        if self.verbose:
            print("Scanning YAML files...")
        return self.yaml_scanner.scan_yaml_files()
    
    def scan_json_examples(self) -> Dict[str, Dict[str, Tuple[str, int]]]:
        """Scan JSON example files and extract method mappings."""
        if self.verbose:
            print("Scanning JSON examples...")
        return self.json_scanner.scan_json_examples()
    
    def create_unified_mapping(self) -> Dict[str, Dict[str, MethodMapping]]:
        """Create a unified mapping combining all file types."""
        # Load canonical method names from KDF repository
        canonical_methods = self._load_canonical_methods()
        
        # Reset normalizer stats for this operation
        self.normalizer.reset_stats()
        
        # Scan all file types
        mdx_mappings = self.scan_mdx_files()
        yaml_mappings = self.scan_yaml_files()
        example_mappings = self.scan_json_examples()
        
        unified = {"v1": {}, "v2": {}}
        
        for version in ["v1", "v2"]:
            # Use canonical methods as the authoritative source
            canonical_method_list = canonical_methods.get(version, [])
            
            # Convert discovered methods from filesystem format to canonical format
            canonical_discovered_methods = set()
            for method in mdx_mappings[version].keys():
                canonical_discovered_methods.add(self.normalizer.convert_filesystem_to_canonical_format(method))
            for method in yaml_mappings[version].keys():
                canonical_discovered_methods.add(self.normalizer.convert_filesystem_to_canonical_format(method))
            for method in example_mappings[version].keys():
                canonical_discovered_methods.add(self.normalizer.convert_filesystem_to_canonical_format(method))
            
            # Combine canonical methods with canonical discovered methods
            # Canonical methods take priority (set union gives us unique methods)
            all_methods = set(canonical_method_list) | canonical_discovered_methods
            
            if self.verbose:
                print(f"📋 Processing {len(all_methods)} {version.upper()} methods (canonical format)...")
                print(f"   📋 {len(canonical_method_list)} from canonical source")
                print(f"   📋 {len(canonical_discovered_methods)} discovered and normalized")
            
            # Create mapping for each method (using canonical names)
            for method in all_methods:
                mdx_path = self.normalizer.find_best_match(method, mdx_mappings[version])
                yaml_path = self.normalizer.find_best_match(method, yaml_mappings[version])
                
                # Handle example mappings
                examples_path = None
                example_count = 0
                example_data = self.normalizer.find_best_match(
                    method, {k: v for k, v in example_mappings[version].items()}
                )
                if example_data:
                    examples_path, example_count = example_data
                
                unified[version][method] = MethodMapping(
                    method=method,
                    mdx_path=mdx_path,
                    yaml_path=yaml_path,
                    examples_path=examples_path,
                    example_count=example_count
                )
        
        # Show matching statistics summary
        if self.verbose:
            stats = self.normalizer.get_match_stats()
            total_matches = stats['direct_matches'] + stats['variation_matches'] + stats['fuzzy_matches']
            print(f"📊 Matching Summary:")
            print(f"   ✅ Direct matches: {stats['direct_matches']}")
            print(f"   🔄 Variation matches: {stats['variation_matches']}")
            print(f"   🎯 Fuzzy matches: {stats['fuzzy_matches']}")
            print(f"   ❌ No matches: {stats['no_matches']}")
            print(f"   📈 Total successful: {total_matches}/{total_matches + stats['no_matches']}")
        
        return unified
    
    def _load_canonical_methods(self) -> Dict[str, List[str]]:
        """Load canonical method names from kdf_repo_methods.json."""
        canonical_file = Path("data/kdf_repo_methods.json")
        
        if not canonical_file.exists():
            if self.verbose:
                print(f"⚠️  Canonical methods file not found: {canonical_file}")
                print("   Falling back to discovery-based method collection.")
            return {"v1": [], "v2": []}
        
        try:
            with open(canonical_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            methods_by_version = data.get('methods_by_version', {})
            canonical_methods = {
                "v1": methods_by_version.get('v1', {}).get('methods', []),
                "v2": methods_by_version.get('v2', {}).get('methods', [])
            }
            
            if self.verbose:
                print(f"📋 Loaded {len(canonical_methods['v1'])} v1 methods and {len(canonical_methods['v2'])} v2 methods from canonical source")
            
            return canonical_methods
            
        except (json.JSONDecodeError, KeyError) as e:
            if self.verbose:
                print(f"⚠️  Error loading canonical methods: {e}")
                print("   Falling back to discovery-based method collection.")
            return {"v1": [], "v2": []}
    
    def save_unified_mapping(self, output_file: str = "data/unified_method_mapping.json") -> None:
        """Save unified mapping to JSON file with metadata."""
        unified = self.create_unified_mapping()
        
        # Convert to JSON-serializable format
        json_data = self._convert_mapping_to_json(unified)
        
        # Add metadata
        json_data['_metadata'] = {
            'generated_at': datetime.now().isoformat(),
            'generated_by': 'mapping.py',
            'total_methods': sum(len(json_data[v]) for v in ['v1', 'v2'])
        }
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"✅ Saved unified mapping to {output_file}")
            self._print_mapping_stats(unified)
    
    def load_unified_mapping(self, input_file: str = "data/unified_method_mapping.json") -> Dict[str, Dict[str, MethodMapping]]:
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
    
    def _convert_mapping_to_json(self, unified: Dict[str, Dict[str, MethodMapping]]) -> Dict:
        """Convert mapping objects to JSON-serializable format."""
        json_data = {}
        
        for version in unified:
            json_data[version] = {}
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
        
        return json_data
    
    def _print_mapping_stats(self, unified: Dict[str, Dict[str, MethodMapping]]) -> None:
        """Print mapping statistics using the reporter."""
        report = self.reporter.generate_detailed_mapping_stats(unified)
        print(report)
    
    # Delegated methods to specialized components
    def update_main_openapi_spec(self, dry_run: bool = False) -> bool:
        """Update the main OpenAPI specification file."""
        return self.openapi_manager.update_main_openapi_spec(dry_run)
    
    def generate_focused_spec(self, focus_type: str = "activation", output_file: str = None) -> bool:
        """Generate a focused OpenAPI specification."""
        return self.openapi_manager.generate_focused_spec(focus_type, output_file)
    
    def debug_method_matching(self, method_name: str, version: str = "v2") -> None:
        """Debug method name matching using the reporter."""
        mdx_mappings = self.scan_mdx_files()
        yaml_mappings = self.scan_yaml_files()
        example_mappings = self.scan_json_examples()
        variations = self.normalizer.normalize_method_name(method_name)
        
        report = self.reporter.generate_debug_report(
            method_name, version, mdx_mappings, yaml_mappings, 
            example_mappings, variations
        )
        print(report)
    
    def remove_method_files(self, method_name: str, dry_run: bool = False) -> None:
        """Remove all files related to a specific method."""
        if self.verbose:
            print(f"\n🔍 Searching for files related to method: {method_name}")
        
        unified = self.create_unified_mapping()
        found_mappings = self._find_method_mappings(method_name, unified)
        
        if not found_mappings:
            if self.verbose:
                print(f"❌ No files found for method '{method_name}'.")
            return
        
        # Collect files and directories to delete
        files_to_delete, dirs_to_delete = self._collect_files_for_removal(found_mappings)
        
        if not files_to_delete and not dirs_to_delete:
            if self.verbose:
                print(f"❌ No files or directories found for method '{method_name}'.")
            return
        
        # Show what will be deleted
        self._show_removal_preview(files_to_delete, dirs_to_delete)
        
        # Confirm deletion
        if not self._confirm_deletion():
            if self.verbose:
                print("Aborted.")
            return
        
        # Perform deletion
        self._perform_deletion(files_to_delete, dirs_to_delete, dry_run)
        
        if self.verbose:
            print("\n✅ Removal complete.")
    
    def _find_method_mappings(self, method_name: str, unified: Dict) -> List[Tuple[str, MethodMapping]]:
        """Find all mappings related to a method name."""
        found = []
        
        for version in ["v1", "v2"]:
            for m, mapping in unified[version].items():
                if (m == method_name or 
                    m in self.normalizer.normalize_method_name(method_name) or 
                    method_name in self.normalizer.normalize_method_name(m)):
                    found.append((version, mapping))
        
        return found
    
    def _collect_files_for_removal(self, found_mappings: List) -> Tuple[List[str], List[str]]:
        """Collect files and directories that need to be removed."""
        files_to_delete = []
        dirs_to_delete = []
        
        for version, mapping in found_mappings:
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
        
        return files_to_delete, dirs_to_delete
    
    def _show_removal_preview(self, files_to_delete: List[str], dirs_to_delete: List[str]):
        """Show preview of what will be deleted."""
        if self.verbose:
            print("\nThe following files/directories will be deleted:")
            for d in dirs_to_delete:
                print(f"  [DIR] {d}")
            for f in files_to_delete:
                print(f"  [FILE] {f}")
    
    def _confirm_deletion(self) -> bool:
        """Confirm deletion with user."""
        confirm = input("\nAre you sure you want to delete these files/directories? [y/N]: ").strip().lower()
        return confirm == 'y'
    
    def _perform_deletion(self, files_to_delete: List[str], dirs_to_delete: List[str], dry_run: bool):
        """Perform the actual deletion."""
        for d in dirs_to_delete:
            if dry_run:
                if self.verbose:
                    print(f"[DRY RUN] Would remove directory: {d}")
            else:
                try:
                    shutil.rmtree(d)
                    if self.verbose:
                        print(f"Removed directory: {d}")
                except Exception as e:
                    if self.verbose:
                        print(f"Error removing directory {d}: {e}")
        
        for f in files_to_delete:
            if dry_run:
                if self.verbose:
                    print(f"[DRY RUN] Would remove file: {f}")
            else:
                try:
                    os.remove(f)
                    if self.verbose:
                        print(f"Removed file: {f}")
                except Exception as e:
                    if self.verbose:
                        print(f"Error removing file {f}: {e}")
    
    # Legacy compatibility methods
    def _normalize_method_name(self, method_name: str) -> List[str]:
        """Legacy compatibility for old method name normalization."""
        return self.normalizer.normalize_method_name(method_name)
    
    def _find_best_match(self, method_name: str, mapping_dict: Dict[str, str]) -> Optional[str]:
        """Legacy compatibility for best match finding."""
        return self.normalizer.find_best_match(method_name, mapping_dict)

 