#!/usr/bin/env python3
"""
Configuration Management

Centralized configuration system for the Komodo Documentation Library.
Handles paths, settings, and environment-specific configurations.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

from .exceptions import ConfigurationError


@dataclass
class DirectoryConfig:
    """Configuration for directory paths."""
    mdx_legacy: str = "../../src/pages/komodo-defi-framework/api/legacy"
    mdx_v2: str = "../../src/pages/komodo-defi-framework/api/v20"
    mdx_v2_dev: str = "../../src/pages/komodo-defi-framework/api/v20-dev"
    yaml_v1: str = "../../openapi/paths/v1"
    yaml_v2: str = "../../openapi/paths/v2"
    json_v1: str = "../../postman/json/kdf/v1"
    json_v2: str = "../../postman/json/kdf/v2"
    openapi_main: str = "../../openapi/openapi.yaml"
    postman_collections: str = "../../postman/collections"
    postman_environments: str = "../../postman/environments"


@dataclass
class ProcessingConfig:
    """Configuration for processing operations."""
    batch_size: int = 50
    parallel_processing: bool = True
    max_workers: int = 4
    continue_on_error: bool = False
    validate_every_nth_block: int = 10
    required_confirmations: int = 3


@dataclass
class LoggingConfig:
    """Configuration for logging and output."""
    verbose: bool = True
    quiet: bool = False
    log_file: Optional[str] = None
    progress_indicators: bool = True
    emoji_output: bool = True
    events: bool = False


@dataclass
class ValidationConfig:
    """Configuration for validation rules."""
    strict_method_validation: bool = True
    require_examples: bool = False
    validate_json_syntax: bool = True
    check_duplicates: bool = True
    minimum_method_name_length: int = 2


class KomodoConfig:
    """
    Centralized configuration manager for the Komodo Documentation Library.
    
    Provides access to all configuration settings and handles loading/saving
    of configuration files.
    """
    
    def __init__(self, config_file: Optional[str] = None, base_path: Optional[str] = None):
        self.base_path = Path(base_path or ".")
        self.config_file = config_file or "komodo-lib-config.json"
        
        # Initialize with defaults
        self.directories = DirectoryConfig()
        self.processing = ProcessingConfig()
        self.logging = LoggingConfig()
        self.validation = ValidationConfig()
        
        # Load from file if it exists
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from file if it exists."""
        config_path = self.base_path / self.config_file
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Update configurations
                if 'directories' in config_data:
                    self.directories = DirectoryConfig(**config_data['directories'])
                if 'processing' in config_data:
                    self.processing = ProcessingConfig(**config_data['processing'])
                if 'logging' in config_data:
                    self.logging = LoggingConfig(**config_data['logging'])
                if 'validation' in config_data:
                    self.validation = ValidationConfig(**config_data['validation'])
                    
            except Exception as e:
                raise ConfigurationError(f"Failed to load config from {config_path}: {e}")
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        config_path = self.base_path / self.config_file
        
        config_data = {
            'directories': asdict(self.directories),
            'processing': asdict(self.processing),
            'logging': asdict(self.logging),
            'validation': asdict(self.validation),
            '_metadata': {
                'version': '1.0.0',
                'generated_by': 'KomodoConfig'
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to save config to {config_path}: {e}")
    
    def get_mdx_directories(self) -> Dict[str, str]:
        """Get MDX directory mappings."""
        return {
            'legacy': self._resolve_path(self.directories.mdx_legacy),
            'v2': self._resolve_path(self.directories.mdx_v2),
            'v2-dev': self._resolve_path(self.directories.mdx_v2_dev),
        }
    
    def get_yaml_directories(self) -> Dict[str, str]:
        """Get YAML directory mappings."""
        return {
            'v1': self._resolve_path(self.directories.yaml_v1),
            'v2': self._resolve_path(self.directories.yaml_v2),
        }
    
    def get_json_directories(self) -> Dict[str, str]:
        """Get JSON directory mappings."""
        return {
            'v1': self._resolve_path(self.directories.json_v1),
            'v2': self._resolve_path(self.directories.json_v2),
        }
    
    def get_openapi_main_file(self) -> str:
        """Get the main OpenAPI file path."""
        return self._resolve_path(self.directories.openapi_main)
    
    def get_postman_directories(self) -> Dict[str, str]:
        """Get Postman directory mappings."""
        return {
            'collections': self._resolve_path(self.directories.postman_collections),
            'environments': self._resolve_path(self.directories.postman_environments),
        }
    
    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to the base path."""
        if os.path.isabs(path):
            return path
        return str(self.base_path / path)
    
    def validate_directories(self) -> Dict[str, bool]:
        """Validate that configured directories exist."""
        results = {}
        
        for name, path in self.get_mdx_directories().items():
            results[f"mdx_{name}"] = os.path.exists(path)
        
        for name, path in self.get_yaml_directories().items():
            results[f"yaml_{name}"] = os.path.exists(path)
        
        for name, path in self.get_json_directories().items():
            results[f"json_{name}"] = os.path.exists(path)
        
        for name, path in self.get_postman_directories().items():
            results[f"postman_{name}"] = os.path.exists(path)
        
        results["openapi_main"] = os.path.exists(self.get_openapi_main_file())
        
        return results
    
    def create_missing_directories(self) -> List[str]:
        """Create any missing directories and return the list of created directories."""
        created = []
        
        all_dirs = {
            **self.get_mdx_directories(),
            **self.get_yaml_directories(),
            **self.get_json_directories(),
            **self.get_postman_directories()
        }
        
        for name, path in all_dirs.items():
            if not os.path.exists(path):
                try:
                    os.makedirs(path, exist_ok=True)
                    created.append(path)
                except Exception as e:
                    raise ConfigurationError(f"Failed to create directory {path}: {e}")
        
        return created
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'directories': asdict(self.directories),
            'processing': asdict(self.processing),
            'logging': asdict(self.logging),
            'validation': asdict(self.validation),
        }


# Global configuration instance
_config_instance: Optional[KomodoConfig] = None


def get_config(config_file: Optional[str] = None, base_path: Optional[str] = None) -> KomodoConfig:
    """Get the global configuration instance."""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = KomodoConfig(config_file, base_path)
    
    return _config_instance


def reset_config() -> None:
    """Reset the global configuration instance."""
    global _config_instance
    _config_instance = None 