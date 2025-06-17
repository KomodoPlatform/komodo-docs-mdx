#!/usr/bin/env python3
"""
Enhanced Configuration Management

Centralized configuration system for the Komodo Documentation Library.
Handles paths, settings, and environment-specific configurations.

REFACTORED: Enhanced to be the single source of truth for all configuration,
eliminating hardcoded paths scattered across modules.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
import logging

from .enums import ValidationLevel, VersionStatus, DeploymentEnvironment


@dataclass
class DirectoryConfig:
    """Enhanced configuration for directory paths with version support."""
    # MDX documentation paths
    mdx_legacy: str = "src/pages/komodo-defi-framework/api/legacy"
    mdx_v2: str = "src/pages/komodo-defi-framework/api/v20"
    mdx_v2_dev: str = "src/pages/komodo-defi-framework/api/v20-dev"
    
    # OpenAPI specification paths
    yaml_v1: str = "openapi/paths/v1"
    yaml_v2: str = "openapi/paths/v2"
    openapi_main: str = "openapi/openapi.yaml"
    
    # Postman collection paths
    json_v1: str = "postman/json/kdf/v1"
    json_v2: str = "postman/json/kdf/v2"
    postman_collections: str = "postman/collections"
    postman_environments: str = "postman/environments"
    
    # Output and working directories
    output_dir: str = "output"
    temp_dir: str = "temp"
    backup_dir: str = "backups"
    
    # Data and cache directories
    data_dir: str = "utils/py/data"
    cache_dir: str = "cache"
    
    def get_version_directories(self) -> Dict[str, Dict[str, str]]:
        """Get directories organized by version and type."""
        return {
            "v1": {
                "yaml": self.yaml_v1,
                "json": self.json_v1,
                "mdx": self.mdx_legacy
            },
            "v2": {
                "yaml": self.yaml_v2,
                "json": self.json_v2,
                "mdx": self.mdx_v2
            },
            "v2-dev": {
                "yaml": self.yaml_v2,  # v2-dev uses same YAML as v2
                "json": self.json_v2,  # v2-dev uses same JSON as v2
                "mdx": self.mdx_v2_dev
            }
        }


@dataclass
class VersionMappingConfig:
    """
    Centralized version mapping configuration to eliminate duplication across the codebase.
    
    This class provides a single source of truth for:
    - Version aliases and canonical names
    - Directory mappings for different file types
    - Postman collection version mappings
    - OpenAPI source version mappings
    - Migration paths between versions
    """
    
    # Core version definitions
    canonical_versions: Dict[str, str] = field(default_factory=lambda: {
        # Canonical mappings - all aliases point to these canonical versions
        'v1': 'v1',
        'legacy': 'v1',
        'deprecated': 'v1',
        'v1.0': 'v1',
        
        'v2': 'v2',
        'v20': 'v2',
        'v2.0': 'v2',
        'current': 'v2',
        'stable': 'v2',
        
        'v2-dev': 'v2-dev',
        'v20-dev': 'v2-dev',
        'dev': 'v2-dev',
        'development': 'v2-dev',
        'beta': 'v2-dev'
    })
    
    # Postman collection version mappings
    postman_version_mapping: Dict[str, str] = field(default_factory=lambda: {
        'v1': 'v1',
        'v2': 'v2',
        'v20': 'v2',
        'v2-dev': 'v2',  # v2-dev methods use v2 Postman data
        'v20-dev': 'v2'  # v20-dev methods use v2 Postman data
    })
    
    # OpenAPI source directory mappings
    openapi_source_mapping: Dict[str, List[str]] = field(default_factory=lambda: {
        'v1': ['legacy'],
        'v2': ['v20', 'v20-dev'],  # v2 processes both v20 and v20-dev
        'v2-dev': ['v20-dev'],
        'v20-dev': ['v20-dev']
    })
    
    # Documentation directory mappings
    doc_path_mapping: Dict[str, str] = field(default_factory=lambda: {
        'v1': 'legacy',
        'v2': 'v20',
        'v2-dev': 'v20-dev',
        'v20': 'v20',
        'v20-dev': 'v20-dev'
    })
    
    # Version status definitions
    version_status: Dict[str, VersionStatus] = field(default_factory=lambda: {
        'v1': VersionStatus.LEGACY,
        'v2': VersionStatus.ACTIVE,
        'v2-dev': VersionStatus.DEVELOPMENT
    })
    
    # Migration targets
    migration_targets: Dict[str, Optional[str]] = field(default_factory=lambda: {
        'v1': None,  # No migration target for legacy
        'v2': None,  # Current stable version
        'v2-dev': 'v2'  # Development migrates to stable
    })
    
    def get_canonical_version(self, version: str) -> str:
        """Get the canonical version name for any version alias."""
        return self.canonical_versions.get(version, version)
    
    def get_postman_version(self, version: str) -> str:
        """Get the Postman collection version for a given version."""
        canonical = self.get_canonical_version(version)
        return self.postman_version_mapping.get(canonical, canonical)
    
    def get_openapi_sources(self, version: str) -> List[str]:
        """Get the source directories for OpenAPI generation for a given version."""
        canonical = self.get_canonical_version(version)
        return self.openapi_source_mapping.get(canonical, [canonical])
    
    def get_doc_path(self, version: str) -> str:
        """Get the documentation path for a given version."""
        canonical = self.get_canonical_version(version)
        return self.doc_path_mapping.get(canonical, canonical)
    
    def get_version_status(self, version: str) -> VersionStatus:
        """Get the status for a given version."""
        canonical = self.get_canonical_version(version)
        return self.version_status.get(canonical, VersionStatus.UNKNOWN)
    
    def get_migration_target(self, version: str) -> Optional[str]:
        """Get the migration target for a given version."""
        canonical = self.get_canonical_version(version)
        return self.migration_targets.get(canonical)
    
    def is_deprecated(self, version: str) -> bool:
        """Check if a version is deprecated."""
        return self.get_version_status(version) == VersionStatus.LEGACY
    
    def get_all_canonical_versions(self) -> List[str]:
        """Get all canonical version names."""
        return list(set(self.canonical_versions.values()))
    
    def get_aliases_for_version(self, canonical_version: str) -> List[str]:
        """Get all aliases for a canonical version."""
        return [alias for alias, canon in self.canonical_versions.items() 
                if canon == canonical_version]


@dataclass
class VersionConfig:
    """Configuration for a specific API version."""
    name: str
    status: VersionStatus
    aliases: List[str] = field(default_factory=list)
    migration_target: Optional[str] = None
    
    @classmethod
    def create_version_configs(cls) -> Dict[str, 'VersionConfig']:
        """Create default version configurations."""
        return {
            "v1": cls(
                name="v1",
                status=VersionStatus.LEGACY,
                aliases=["legacy", "v1.0", "deprecated"],
                migration_target=None
            ),
            "v2": cls(
                name="v2",
                status=VersionStatus.ACTIVE,
                aliases=["v20", "v2.0", "current", "stable"],
                migration_target=None
            ),
            "v2-dev": cls(
                name="v2-dev",
                status=VersionStatus.DEVELOPMENT,
                aliases=["v20-dev", "dev", "development", "beta"],
                migration_target="v2"
            )
        }


@dataclass
class ProcessingConfig:
    """Enhanced configuration for processing operations."""
    batch_size: int = 50
    parallel_processing: bool = True
    max_workers: int = 4
    continue_on_error: bool = False
    validate_every_nth_block: int = 10
    required_confirmations: int = 3
    
    # File operation settings
    backup_on_write: bool = False
    cleanup_temp_files: bool = True
    max_file_age_hours: int = 24
    
    # Performance settings
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_cache_size_mb: int = 100


@dataclass
class LoggingConfig:
    """Enhanced configuration for logging and output."""
    verbose: bool = True
    quiet: bool = False
    log_file: Optional[str] = None
    progress_indicators: bool = True
    emoji_output: bool = True
    
    # Log levels and formatting
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    
    # Output control
    show_warnings: bool = True
    show_debug: bool = False
    colored_output: bool = True


@dataclass
class ValidationConfig:
    """Enhanced configuration for validation rules."""
    strict_method_validation: bool = True
    require_examples: bool = False
    validate_json_syntax: bool = True
    check_duplicates: bool = True
    minimum_method_name_length: int = 2
    
    # Validation levels
    default_validation_level: ValidationLevel = ValidationLevel.NORMAL
    file_validation_level: ValidationLevel = ValidationLevel.NORMAL
    schema_validation_enabled: bool = True
    
    # Custom validation rules
    custom_validation_rules: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.custom_validation_rules is None:
            self.custom_validation_rules = {}


@dataclass
class EnhancedKomodoConfig:
    """Enhanced configuration with flexible directory management and version handling."""
    
    # Core configuration
    directories: DirectoryConfig = field(default_factory=DirectoryConfig)
    versions: Dict[str, VersionConfig] = field(default_factory=VersionConfig.create_version_configs)
    version_mapping: VersionMappingConfig = field(default_factory=VersionMappingConfig)
    
    # Environment and deployment settings
    environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT
    workspace_root: Optional[str] = None
    
    # Feature flags
    enable_async_processing: bool = True
    enable_postman_integration: bool = True
    enable_openapi_generation: bool = True
    
    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        """Post-initialization setup."""
        self._setup_logging()
        self._resolve_workspace_root()
    
    def _setup_logging(self):
        """Configure logging based on settings."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format=self.log_format
        )
    
    def _resolve_workspace_root(self):
        """Resolve workspace root if not explicitly set."""
        if self.workspace_root is None:
            # Try to find workspace root by looking for characteristic files
            current = Path.cwd()
            for parent in [current] + list(current.parents):
                if (parent / "src" / "pages").exists() and (parent / "utils").exists():
                    self.workspace_root = str(parent)
                    break
            else:
                self.workspace_root = str(current)
    
    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to workspace root."""
        if os.path.isabs(path):
            return path
        return os.path.join(self.workspace_root, path)
    
    # Version mapping convenience methods
    def get_canonical_version(self, version: str) -> str:
        """Get canonical version name."""
        return self.version_mapping.get_canonical_version(version)
    
    def get_postman_version(self, version: str) -> str:
        """Get Postman collection version."""
        return self.version_mapping.get_postman_version(version)
    
    def get_openapi_sources(self, version: str) -> List[str]:
        """Get OpenAPI source directories."""
        return self.version_mapping.get_openapi_sources(version)
    
    def get_doc_path(self, version: str) -> str:
        """Get documentation path."""
        return self.version_mapping.get_doc_path(version)
    
    def is_version_deprecated(self, version: str) -> bool:
        """Check if version is deprecated."""
        return self.version_mapping.is_deprecated(version)
    
    def get_version_status(self, version: str) -> VersionStatus:
        """Get version status."""
        return self.version_mapping.get_version_status(version)
    
    def get_supported_versions(self, include_deprecated: bool = False) -> List[str]:
        """Get list of supported versions."""
        versions = self.version_mapping.get_all_canonical_versions()
        if not include_deprecated:
            versions = [v for v in versions if not self.is_version_deprecated(v)]
        return sorted(versions)
    
    # Directory resolution methods
    def get_directory_for_version_and_type(self, version: str, file_type: str) -> str:
        """Get directory path for a specific version and file type."""
        canonical_version = self.get_canonical_version(version)
        
        if file_type == "mdx":
            if canonical_version == "v1":
                return self._resolve_path(self.directories.mdx_legacy)
            else:
                return self._resolve_path(self.directories.mdx_v2)
        elif file_type == "yaml":
            if canonical_version == "v1":
                return self._resolve_path(self.directories.yaml_v1)
            else:
                return self._resolve_path(self.directories.yaml_v2)
        elif file_type == "json":
            if canonical_version == "v1":
                return self._resolve_path(self.directories.json_v1)
            else:
                return self._resolve_path(self.directories.json_v2)
        else:
            raise ValueError(f"Unknown file type: {file_type}")
    
    def get_all_directories(self) -> Dict[str, str]:
        """Get all configured directories as resolved paths."""
        return {
            name: self._resolve_path(path)
            for name, path in asdict(self.directories).items()
        }


# Global configuration instance
_config_instance: Optional[EnhancedKomodoConfig] = None


def get_config(config_file: Optional[str] = None, base_path: Optional[str] = None,
               environment: DeploymentEnvironment = DeploymentEnvironment.DEVELOPMENT) -> EnhancedKomodoConfig:
    """Get the global configuration instance."""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = EnhancedKomodoConfig(
            environment=environment,
            workspace_root=base_path
        )
    
    return _config_instance


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config_instance
    _config_instance = None 