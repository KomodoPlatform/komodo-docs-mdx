"""
Path Utilities for KDF Documentation Structure

This module provides flexible path mapping utilities that can handle:
- Version migrations (v20-dev → v20, v1 → deprecated)
- Structural changes in documentation
- Method deprecation and removal
- Future extensibility

The system is designed to be configuration-driven to handle changes gracefully.
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

# Import enums from utils to avoid circular dependencies
from ..utils.enums import PathType, VersionStatus

@dataclass
class VersionConfig:
    """Configuration for an API version"""
    name: str
    status: VersionStatus
    mdx_path: str
    openapi_path: str
    postman_path: str
    aliases: List[str] = field(default_factory=list)
    migration_target: Optional[str] = None  # For handling migrations

@dataclass
class PathMapping:
    """Complete path mapping for a method"""
    method_name: str
    version: str
    mdx_path: str
    category: str
    subcategory: Optional[str] = None
    openapi_path: str = ""
    postman_json_path: str = ""
    postman_collection_path: str = ""
    deprecated: bool = False
    migration_source: Optional[str] = None

class PathMapper:
    """
    Flexible path mapper that handles version migrations and structural changes.
    
    This class provides a central place to manage path mappings and can be
    easily extended or reconfigured for future changes.
    """
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.version_configs = self._initialize_version_configs()
        self.category_mappings = self._initialize_category_mappings()
        
    def _initialize_version_configs(self) -> Dict[str, VersionConfig]:
        """Initialize version configurations with migration paths"""
        return {
            "v1": VersionConfig(
                name="v1",
                status=VersionStatus.LEGACY,
                mdx_path="src/pages/komodo-defi-framework/api/legacy",
                openapi_path="openapi/paths/v1",
                postman_path="postman/json/kdf/v1",
                aliases=["legacy", "v1.0"]
            ),
            "v2": VersionConfig(
                name="v2", 
                status=VersionStatus.ACTIVE,
                mdx_path="src/pages/komodo-defi-framework/api/v20",
                openapi_path="openapi/paths/v2",
                postman_path="postman/json/kdf/v2",
                aliases=["v20", "v2.0", "current"]
            ),
            "v2-dev": VersionConfig(
                name="v2-dev",
                status=VersionStatus.DEVELOPMENT,
                mdx_path="src/pages/komodo-defi-framework/api/v20-dev",
                openapi_path="openapi/paths/v2-dev",
                postman_path="postman/json/kdf/v2-dev",
                aliases=["v20-dev", "dev", "development"],
                migration_target="v2"  # Will migrate to v2 when stable
            )
        }
    
    def _initialize_category_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        Initialize category mappings for different versions.
        This allows for flexible restructuring of categories.
        """
        return {
            "v2": {
                # Coin Activation
                "coin_activation": "coin_activation",
                "task_managed": "coin_activation/task_managed",
                
                # Trading & Orders
                "swaps_and_orders": "trading",
                "orderbook": "trading",
                "best_orders": "trading", 
                "active_swaps": "trading",
                
                # Lightning Network
                "lightning": "lightning",
                "lightning/channels": "lightning/channels",
                "lightning/nodes": "lightning/nodes", 
                "lightning/payments": "lightning/payments",
                "lightning/activation": "lightning/activation",
                
                # Streaming
                "streaming": "streaming",
                "stream": "streaming",  # Handle both naming conventions
                
                # Wallet Management
                "wallet": "wallet",
                "wallet/staking": "wallet/staking",
                "wallet/task_managed": "wallet/task_managed",
                "wallet/tx": "wallet/transactions",
                "wallet/fee_management": "wallet/fees",
                
                # Utilities
                "utils": "utilities",
                "utils/message_signing": "utilities/messaging", 
                "utils/task_init_trezor": "utilities/hardware",
                "utils/telegram_alerts": "utilities/notifications",
                
                # NFTs
                "non_fungible_tokens": "nft",
                
                # External Integrations
                "1inch": "integrations/1inch",
                
                # Default fallback
                "_default": "misc"
            },
            "v1": {
                # V1 has mostly flat structure, but we can organize it
                "coin_activation": "coin_activation",
                "trading": "trading",
                "orders": "trading",
                "swaps": "trading", 
                "wallet": "wallet",
                "_default": "general"
            }
        }
    
    def get_method_path_mapping(self, method_name: str, mdx_path: str, version: str) -> PathMapping:
        """
        Get complete path mapping for a method.
        
        Args:
            method_name: The canonical method name (e.g., "task::enable_eth::init")
            mdx_path: The current MDX file path
            version: The API version
            
        Returns:
            PathMapping with all generated paths
        """
        # Normalize version (handle aliases)
        version = self._normalize_version(version)
        
        # Extract category and subcategory from MDX path
        category, subcategory = self._extract_category_from_mdx_path(mdx_path, version)
        
        # Generate all paths
        openapi_path = self._generate_openapi_path(method_name, category, subcategory, version)
        postman_json_path = self._generate_postman_json_path(method_name, category, subcategory, version)
        postman_collection_path = self._generate_postman_collection_path(category, subcategory, version)
        
        # Check for deprecation or migration
        deprecated = self._is_deprecated(method_name, version)
        migration_source = self._get_migration_source(method_name, version)
        
        return PathMapping(
            method_name=method_name,
            version=version,
            mdx_path=mdx_path,
            category=category,
            subcategory=subcategory,
            openapi_path=openapi_path,
            postman_json_path=postman_json_path,
            postman_collection_path=postman_collection_path,
            deprecated=deprecated,
            migration_source=migration_source
        )
    
    def _normalize_version(self, version: str) -> str:
        """Normalize version string using aliases"""
        for ver_name, config in self.version_configs.items():
            if version == ver_name or version in config.aliases:
                return ver_name
        return version
    
    def _extract_category_from_mdx_path(self, mdx_path: str, version: str) -> Tuple[str, Optional[str]]:
        """Extract category and subcategory from MDX path"""
        # Get the version config
        version_config = self.version_configs.get(version)
        if not version_config:
            return "misc", None
            
        # Remove the base MDX path to get relative path
        rel_path = mdx_path.replace(version_config.mdx_path, "").strip("/")
        
        # Split into parts
        parts = [p for p in rel_path.split("/") if p and p != "index.mdx"]
        
        if not parts:
            return "misc", None
        
        # First part is typically the main category
        category = parts[0]
        subcategory = parts[1] if len(parts) > 1 else None
        
        # Apply category mappings for this version
        category_map = self.category_mappings.get(version, {})
        full_category_key = f"{category}/{subcategory}" if subcategory else category
        
        # Try full path first, then just category, then default
        if full_category_key in category_map:
            mapped = category_map[full_category_key]
        elif category in category_map:
            mapped = category_map[category]
        else:
            mapped = category_map.get("_default", category)
        
        # Split mapped result back into category/subcategory
        mapped_parts = mapped.split("/")
        return mapped_parts[0], mapped_parts[1] if len(mapped_parts) > 1 else None
    
    def _generate_openapi_path(self, method_name: str, category: str, subcategory: Optional[str], version: str) -> str:
        """Generate OpenAPI YAML file path"""
        version_config = self.version_configs.get(version)
        if not version_config:
            return ""
        
        # Create nested directory structure
        if subcategory:
            dir_path = f"{version_config.openapi_path}/{category}/{subcategory}"
        else:
            dir_path = f"{version_config.openapi_path}/{category}"
        
        # Generate filename from method name
        filename = self._method_name_to_filename(method_name)
        return f"{dir_path}/{filename}.yaml"
    
    def _generate_postman_json_path(self, method_name: str, category: str, subcategory: Optional[str], version: str) -> str:
        """Generate Postman JSON examples directory path"""
        version_config = self.version_configs.get(version)
        if not version_config:
            return ""
        
        # Create nested directory structure
        if subcategory:
            dir_path = f"{version_config.postman_path}/{category}/{subcategory}"
        else:
            dir_path = f"{version_config.postman_path}/{category}"
        
        # Use method name as directory name (normalized)
        method_dir = self._method_name_to_dirname(method_name)
        return f"{dir_path}/{method_dir}"
    
    def _generate_postman_collection_path(self, category: str, subcategory: Optional[str], version: str) -> str:
        """Generate Postman collection file path"""
        version_config = self.version_configs.get(version)
        if not version_config:
            return ""
        
        # Collections are organized by category
        if subcategory:
            collection_name = f"{category}_{subcategory}"
        else:
            collection_name = category
        
        return f"postman/collections/{version}/{collection_name}.json"
    
    def _method_name_to_filename(self, method_name: str) -> str:
        """Convert method name to filename (for OpenAPI)"""
        return method_name.replace("::", "_").lower()
    
    def _method_name_to_dirname(self, method_name: str) -> str:
        """Convert method name to directory name (for JSON examples)"""
        return method_name.replace("::", "-").lower()
    
    def _is_deprecated(self, method_name: str, version: str) -> bool:
        """Check if a method is deprecated"""
        version_config = self.version_configs.get(version)
        return version_config and version_config.status == VersionStatus.DEPRECATED
    
    def _get_migration_source(self, method_name: str, version: str) -> Optional[str]:
        """Get migration source version if this method was migrated"""
        # This could be enhanced with a migration tracking system
        # For now, just check if this version is a migration target
        for ver_name, config in self.version_configs.items():
            if config.migration_target == version:
                return ver_name
        return None
    
    def create_directory_structure(self, path_mapping: PathMapping, dry_run: bool = False) -> List[str]:
        """
        Create the directory structure for a path mapping.
        
        Returns:
            List of directories that were created (or would be created in dry run)
        """
        created_dirs = []
        
        # Directories to create
        paths_to_create = [
            os.path.dirname(path_mapping.openapi_path),
            path_mapping.postman_json_path,
            os.path.dirname(path_mapping.postman_collection_path)
        ]
        
        for dir_path in paths_to_create:
            if not dir_path:
                continue
                
            full_path = self.base_path / dir_path
            
            if dry_run:
                created_dirs.append(str(full_path))
            else:
                try:
                    full_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(full_path))
                except Exception as e:
                    print(f"Warning: Could not create directory {full_path}: {e}")
        
        return created_dirs
    
    def get_all_versions(self, include_deprecated: bool = False) -> List[str]:
        """Get list of all configured versions"""
        versions = []
        for ver_name, config in self.version_configs.items():
            if include_deprecated or config.status != VersionStatus.DEPRECATED:
                versions.append(ver_name)
        return versions
    
    def get_version_status(self, version: str) -> Optional[VersionStatus]:
        """Get the status of a version"""
        version = self._normalize_version(version)
        config = self.version_configs.get(version)
        return config.status if config else None
    
    def handle_version_migration(self, method_name: str, from_version: str, to_version: str, 
                                dry_run: bool = False) -> Dict[str, str]:
        """
        Handle migration of a method from one version to another.
        
        Returns:
            Dictionary with old and new paths for each file type
        """
        # This would be used when methods move between versions
        # For example, when a v2-dev method moves to v2
        
        # Create mappings for both versions
        # This is a placeholder for future implementation
        return {
            "status": "migration_planned",
            "from_version": from_version,
            "to_version": to_version,
            "method": method_name
        } 