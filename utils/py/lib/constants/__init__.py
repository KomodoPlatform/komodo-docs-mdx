#!/usr/bin/env python3
"""
Constants Package - Static Data and Configuration

This package contains all static data, enums, templates, configuration,
and exceptions used throughout the library. Organized for better maintainability.
"""

# Core enums and constants
from .enums import (
    ValidationLevel, VersionStatus, PathType, FileType, DeploymentEnvironment, EventType, ProcessingStatus,
    DEFAULT_CACHE_TTL, DEFAULT_BATCH_SIZE, DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES,
    MDX_PATTERNS, JSON_PATTERNS, YAML_PATTERNS, API_VERSIONS, SUPPORTED_EXTENSIONS,
    FILE_PATTERNS, BATCH_SIZES, TIMEOUT_SETTINGS, VALIDATION_RULES
)

# Template definitions
from .templates import ExampleTemplates

# Configuration management
from .config import (
    DirectoryConfig, VersionConfig, ProcessingConfig,
    LoggingConfig, ValidationConfig, EnhancedKomodoConfig, get_config, reset_config
)

# Exception hierarchy
from .exceptions import (
    KomodoLibraryError, FileOperationError, ValidationError, ParseError,
    ConfigurationError, MethodNotFoundError, PostmanGenerationError,
    OpenAPIError, ExtractionError, DeduplicationError, MappingError,
    raise_file_not_found, raise_invalid_json, raise_method_not_mapped
)

__all__ = [
    # Enums
    'ValidationLevel', 'VersionStatus', 'PathType', 'FileType', 'EventType', 'ProcessingStatus',
    
    # Constants
    'DEFAULT_CACHE_TTL', 'DEFAULT_BATCH_SIZE', 'DEFAULT_TIMEOUT', 'DEFAULT_MAX_RETRIES',
    'MDX_PATTERNS', 'JSON_PATTERNS', 'YAML_PATTERNS', 'API_VERSIONS', 'SUPPORTED_EXTENSIONS',
    'FILE_PATTERNS', 'BATCH_SIZES', 'TIMEOUT_SETTINGS', 'VALIDATION_RULES',
    
    # Templates
    'ExampleTemplates',
    
    # Configuration
    'DirectoryConfig', 'VersionConfig', 'ProcessingConfig',
    'LoggingConfig', 'ValidationConfig', 'EnhancedKomodoConfig', 'get_config', 'reset_config',
    
    # Exceptions
    'KomodoLibraryError', 'FileOperationError', 'ValidationError', 'ParseError',
    'ConfigurationError', 'MethodNotFoundError', 'PostmanGenerationError',
    'OpenAPIError', 'ExtractionError', 'DeduplicationError', 'MappingError',
    'raise_file_not_found', 'raise_invalid_json', 'raise_method_not_mapped'
] 