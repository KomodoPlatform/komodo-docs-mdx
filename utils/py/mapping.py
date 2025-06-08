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
        self.main_openapi_file = '../../postman/openapi/openapi.yaml'
        
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
            
            # Create MethodMapping objects for each method
            for method in all_methods:
                mdx_path = self._find_best_match(method, mdx_mappings[version])
                yaml_path = self._find_best_match(method, yaml_mappings[version])
                
                unified[version][method] = MethodMapping(
                    method=method,
                    mdx_path=mdx_path,
                    yaml_path=yaml_path
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
                    'has_mdx': mapping.has_mdx,
                    'has_yaml': mapping.has_yaml,
                    'is_complete': mapping.is_complete
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
                        yaml_path=data['yaml_path']
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
    
    args = parser.parse_args()
    
    # Change to script directory for relative paths
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Set verbosity
    verbose = args.verbose and not args.quiet
    
    mapper = MethodMapper(verbose=verbose)
    
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
            else:
                if not args.quiet:
                    print("✅ OpenAPI specification is already up to date")
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