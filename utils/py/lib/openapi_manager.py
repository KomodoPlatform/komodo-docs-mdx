#!/usr/bin/env python3
"""
OpenAPI Manager

Handles OpenAPI specification operations including updating main specs,
generating focused specs, and managing OpenAPI paths.
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .file_scanners import PathExtractor


class OpenAPIManager:
    """
    Manages OpenAPI specification files and operations.
    Handles updating main specs and generating focused specifications.
    """
    
    def __init__(self, main_openapi_file: str, yaml_dirs: Dict[str, str], verbose: bool = True):
        self.main_openapi_file = main_openapi_file
        self.yaml_dirs = yaml_dirs
        self.verbose = verbose
        self.path_extractor = PathExtractor()
    
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
                if self.verbose:
                    print(f"Warning: Main OpenAPI file {self.main_openapi_file} does not exist")
                return False
            
            with open(self.main_openapi_file, 'r', encoding='utf-8') as f:
                openapi_spec = yaml.safe_load(f)
            
            if not openapi_spec or 'paths' not in openapi_spec:
                if self.verbose:
                    print("Warning: Invalid OpenAPI specification format")
                return False
            
            # Scan for available YAML files and generate correct paths
            available_paths = self._discover_available_paths()
            sorted_available_paths = dict(sorted(available_paths.items()))
            
            # Compare with current paths
            current_paths = set(openapi_spec['paths'].keys())
            available_api_paths = set(sorted_available_paths.keys())
            
            missing_paths = available_api_paths - current_paths
            obsolete_paths = current_paths - available_api_paths
            
            changes_needed = self._report_path_differences(missing_paths, obsolete_paths)
            
            if changes_needed and not dry_run:
                return self._apply_path_updates(openapi_spec, sorted_available_paths)
            elif dry_run:
                if missing_paths or obsolete_paths:
                    if self.verbose:
                        print("🔍 Dry run mode - no changes made")
                    return True
                else:
                    if self.verbose:
                        print("✅ OpenAPI spec is up to date")
                    return False
            else:
                if self.verbose:
                    print("✅ OpenAPI spec is up to date")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"Error updating OpenAPI spec: {e}")
            return False
    
    def _discover_available_paths(self) -> Dict[str, str]:
        """Discover all available YAML paths."""
        available_paths = {}
        
        for version, base_dir in self.yaml_dirs.items():
            if not os.path.exists(base_dir):
                continue
            
            for filename in os.listdir(base_dir):
                if filename.endswith(('.yaml', '.yml')):
                    yaml_file = filename
                    yaml_path = f"./paths/{version}/{yaml_file}"
                    api_path = self.path_extractor.extract_path_from_yaml_filename(yaml_file, version)
                    available_paths[api_path] = yaml_path
        
        return available_paths
    
    def _report_path_differences(self, missing_paths: set, obsolete_paths: set) -> bool:
        """Report differences between current and available paths."""
        changes_needed = False
        
        if missing_paths:
            if self.verbose:
                print(f"Found {len(missing_paths)} missing paths in OpenAPI spec:")
                for path in sorted(missing_paths):
                    print(f"  + {path}")
            changes_needed = True
        
        if obsolete_paths:
            if self.verbose:
                print(f"Found {len(obsolete_paths)} obsolete paths in OpenAPI spec:")
                for path in sorted(obsolete_paths):
                    print(f"  - {path}")
            changes_needed = True
        
        return changes_needed
    
    def _apply_path_updates(self, openapi_spec: dict, sorted_available_paths: Dict[str, str]) -> bool:
        """Apply path updates to the OpenAPI spec."""
        try:
            # Update paths
            new_paths = {}
            for path in sorted(sorted_available_paths.keys()):
                new_paths[path] = {'$ref': sorted_available_paths[path]}
            
            openapi_spec['paths'] = new_paths
            
            # Update metadata
            if 'info' not in openapi_spec:
                openapi_spec['info'] = {}
            
            openapi_spec['info']['x-last-updated'] = datetime.now().isoformat()
            openapi_spec['info']['x-updated-by'] = 'openapi_manager.py'
            
            # Save updated spec
            with open(self.main_openapi_file, 'w', encoding='utf-8') as f:
                yaml.dump(openapi_spec, f, default_flow_style=False, sort_keys=False, 
                         allow_unicode=True, width=120)
            
            if self.verbose:
                print(f"✅ Updated {self.main_openapi_file}")
                print(f"   Total paths: {len(new_paths)} (sorted alphabetically)")
            
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"Error applying path updates: {e}")
            return False
    
    def generate_focused_spec(self, focus_type: str = "activation", output_file: str = None) -> bool:
        """
        Generate a focused OpenAPI specification for specific functionality.
        
        Args:
            focus_type: Type of focus (activation, lightning, trading, wallet)
            output_file: Output file path (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.main_openapi_file):
                if self.verbose:
                    print(f"Error: Main OpenAPI file {self.main_openapi_file} not found")
                return False
            
            with open(self.main_openapi_file, 'r', encoding='utf-8') as f:
                main_spec = yaml.safe_load(f)
            
            # Get focus configuration
            focus_config = self._get_focus_configuration(focus_type)
            if not focus_config:
                if self.verbose:
                    print(f"Error: Unknown focus type '{focus_type}'. Available: {list(self._get_all_focus_types())}")
                return False
            
            # Build focused specification
            focused_spec = self._build_focused_spec(main_spec, focus_config, focus_type)
            
            # Set output file
            if output_file is None:
                output_file = f"../../openapi/{focus_type}_generated.yaml"
            
            # Save focused spec
            with open(output_file, 'w', encoding='utf-8') as f:
                yaml.dump(focused_spec, f, default_flow_style=False, sort_keys=False, 
                         allow_unicode=True, width=120)
            
            path_count = len(focused_spec["paths"])
            if self.verbose:
                print(f"✅ Generated focused {focus_type} spec with {path_count} endpoints: {output_file}")
            
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"Error generating focused spec: {e}")
            return False
    
    def _get_focus_configuration(self, focus_type: str) -> Optional[Dict]:
        """Get configuration for a specific focus type."""
        focus_filters = {
            "activation": {
                "patterns": [
                    "/v2/task/enable_", "/v2/enable_", "/v2/task/enable_lightning"
                ],
                "tags": ["Coin Activation", "Token Activation", "Lightning Activation"],
                "schemas": ["Common", "Activation"]
            },
            "lightning": {
                "patterns": [
                    "/v2/lightning/", "/v2/task/enable_lightning"
                ],
                "tags": ["Lightning Network", "Lightning Activation"],
                "schemas": ["Common", "Lightning", "Activation"]
            },
            "trading": {
                "patterns": [
                    "/v2/swaps_and_orders/", "/v1/buy", "/v1/sell", "/v1/setprice", 
                    "/v1/cancel_order", "/v1/orderbook"
                ],
                "tags": ["Trading & Orders", "Atomic Swaps"],
                "schemas": ["Common", "Orders", "Swaps", "MakerEvents", "TakerEvents"]
            },
            "wallet": {
                "patterns": [
                    "/v2/wallet/", "/v1/my_balance", "/v1/withdraw", "/v2/withdraw"
                ],
                "tags": ["Wallet Management"],
                "schemas": ["Common", "Wallet"]
            }
        }
        
        return focus_filters.get(focus_type)
    
    def _get_all_focus_types(self) -> List[str]:
        """Get all available focus types."""
        return ["activation", "lightning", "trading", "wallet"]
    
    def _build_focused_spec(self, main_spec: dict, focus_config: Dict, focus_type: str) -> dict:
        """Build a focused OpenAPI specification."""
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
        
        # Filter paths based on patterns
        patterns = focus_config["patterns"]
        for path, path_spec in main_spec["paths"].items():
            if any(pattern in path for pattern in patterns):
                focused_spec["paths"][path] = path_spec
        
        # Sort paths
        focused_spec["paths"] = dict(sorted(focused_spec["paths"].items()))
        
        # Add relevant tags
        for tag in main_spec.get("tags", []):
            if tag["name"] in focus_config["tags"]:
                focused_spec["tags"].append(tag)
        
        # Add essential schemas
        for schema_name in focus_config["schemas"]:
            if schema_name in main_spec["components"]["schemas"]:
                focused_spec["components"]["schemas"][schema_name] = main_spec["components"]["schemas"][schema_name]
        
        return focused_spec 