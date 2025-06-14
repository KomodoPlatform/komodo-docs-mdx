"""
Komodo Documentation Library v2.1.0 - Package-Based Architecture

A comprehensive library for managing API documentation, Postman collections,
OpenAPI specifications, and file operations for Komodo DeFi Framework.

RESTRUCTURED VERSION - Now organized into logical packages for better maintainability.
"""

# Import everything from new package structure
# This maintains backward compatibility while using the new organization

# Core functionality - Foundation utilities
from .core import (
    # Configuration
    KomodoConfig, get_config, reset_config,
    # Exceptions
    KomodoLibraryError, FileOperationError, ValidationError, ParseError,
    ConfigurationError, MethodNotFoundError, PostmanGenerationError,
    OpenAPIError, ExtractionError, DeduplicationError, MappingError,
    # Logging
    KomodoLogger, get_logger, setup_logging, ProgressTracker,
    log_file_operation, log_method_processing, log_stats,
    # Shared utilities
    normalize_file_path, validate_file_exists, ensure_directory_exists,
    safe_read_json, safe_write_json, calculate_content_hash, 
    convert_dir_to_method_name, format_method_name_for_display,
    # File operations
    BaseFileManager, FileOperationResult, ExampleFileManager
)

# Scanning functionality - File scanning and content extraction
from .scanning import (
    UnifiedScanner, ScanResult,
    ExtractedExample, MDXExtractor,
    KDFRepositoryScanner, RepositoryInfo, scan_kdf_repository, compare_repo_with_docs
)

# Mapping functionality - Method mapping and normalization
from .mapping import (
    MethodMapper, MethodMapping,
    MethodNameNormalizer,
    PathMapper, PathMapping, VersionConfig, VersionStatus, PathType,
    ValidationManager, ValidationResult, ValidationLevel,
    MappingReporter
)

# Postman functionality - Collection generation and management
from .postman import (
    PostmanRequest, PostmanFolder, PostmanRequestProcessor,
    MethodCategorizer, FolderOrganizer, CollectionGenerator, EnvironmentGenerator,
    PostmanFileManager, PostmanReportGenerator,
    PostmanCollectionGenerator, generate_postman_collections
)

# OpenAPI functionality - Specification management
from .openapi import (
    OpenAPIManager,
    MDXToOpenAPIConverter, MDXParser, OpenAPIConverter
)

# Async support - Asynchronous processing utilities
from .async_support import (
    AsyncFileProcessor, AsyncMethodProcessor, async_cached,
    run_with_progress, run_async,
    FileProcessorStrategy, JSONProcessorStrategy, MDXProcessorStrategy, 
    YAMLProcessorStrategy, FileProcessorContext, ProcessingResult,
    create_file_processor, process_single_file
)

# CLI functionality - Command-line interface components
from .cli import (
    CLIBase, VersionedCLI, BatchProcessorCLI, create_simple_cli
)

# Utility functionality - Supporting utilities
from .utils import (
    KomodoCache, get_cache, cached, cache_file_scan, cache_directory_scan,
    EventType, Event, Observer, Subject, LoggingObserver, ProgressTrackingObserver,
    StatisticsObserver, FileEventObserver, CallbackObserver, EventPublisher,
    get_event_publisher, publish_operation_started, publish_operation_completed,
    publish_file_processed, publish_file_error,
    ExampleTemplates, ExampleReporter, ExampleDeduplicator,
    APIExampleManager
)

# Main exports for backward compatibility
__all__ = [
    # Core - Configuration
    'KomodoConfig', 'get_config', 'reset_config',
    
    # Core - Exceptions
    'KomodoLibraryError', 'FileOperationError', 'ValidationError', 'ParseError',
    'ConfigurationError', 'MethodNotFoundError', 'PostmanGenerationError',
    'OpenAPIError', 'ExtractionError', 'DeduplicationError', 'MappingError',
    
    # Core - Logging
    'KomodoLogger', 'get_logger', 'setup_logging', 'ProgressTracker',
    'log_file_operation', 'log_method_processing', 'log_stats',
    
    # Core - Shared utilities
    'normalize_file_path', 'validate_file_exists', 'ensure_directory_exists',
    'safe_read_json', 'safe_write_json', 'calculate_content_hash', 
    'convert_dir_to_method_name', 'format_method_name_for_display',
    
    # Core - File operations
    'BaseFileManager', 'FileOperationResult', 'ExampleFileManager',
    
    # Scanning
    'UnifiedScanner', 'ScanResult',
    'ExtractedExample', 'MDXExtractor',
    'KDFRepositoryScanner', 'RepositoryInfo', 'scan_kdf_repository', 'compare_repo_with_docs',
    
    # Mapping
    'MethodMapper', 'MethodMapping',
    'MethodNameNormalizer',
    'PathMapper', 'PathMapping', 'VersionConfig', 'VersionStatus', 'PathType',
    'ValidationManager', 'ValidationResult', 'ValidationLevel',
    'MappingReporter',
    
    # Postman
    'PostmanRequest', 'PostmanFolder', 'PostmanRequestProcessor',
    'MethodCategorizer', 'FolderOrganizer', 'CollectionGenerator', 'EnvironmentGenerator',
    'PostmanFileManager', 'PostmanReportGenerator',
    'PostmanCollectionGenerator', 'generate_postman_collections',
    
    # OpenAPI
    'OpenAPIManager',
    'MDXToOpenAPIConverter', 'MDXParser', 'OpenAPIConverter',
    
    # Async support
    'AsyncFileProcessor', 'AsyncMethodProcessor', 'async_cached',
    'run_with_progress', 'run_async',
    'FileProcessorStrategy', 'JSONProcessorStrategy', 'MDXProcessorStrategy', 
    'YAMLProcessorStrategy', 'FileProcessorContext', 'ProcessingResult',
    'create_file_processor', 'process_single_file',
    
    # CLI
    'CLIBase', 'VersionedCLI', 'BatchProcessorCLI', 'create_simple_cli',
    
    # Utils - Caching
    'KomodoCache', 'get_cache', 'cached', 'cache_file_scan', 'cache_directory_scan',
    
    # Utils - Observer pattern
    'EventType', 'Event', 'Observer', 'Subject', 'LoggingObserver', 'ProgressTrackingObserver',
    'StatisticsObserver', 'FileEventObserver', 'CallbackObserver', 'EventPublisher',
    'get_event_publisher', 'publish_operation_started', 'publish_operation_completed',
    'publish_file_processed', 'publish_file_error',
    
    # Utils - Templates and utilities
    'ExampleTemplates', 'ExampleReporter', 'ExampleDeduplicator',
    'APIExampleManager'
]

# Legacy compatibility functions with deprecation warnings
import warnings

def _warn_legacy_usage(old_name: str, new_name: str):
    """Helper to issue deprecation warnings."""
    warnings.warn(
        f"{old_name} is deprecated. Use {new_name} instead.",
        DeprecationWarning,
        stacklevel=3
    )

# Legacy compatibility functions
def create_postman_generator(*args, **kwargs):
    """Legacy function - use PostmanCollectionGenerator directly."""
    _warn_legacy_usage("create_postman_generator", "PostmanCollectionGenerator")
    return PostmanCollectionGenerator(*args, **kwargs)

def create_file_scanner(*args, **kwargs):
    """Legacy function - use UnifiedScanner directly."""
    _warn_legacy_usage("create_file_scanner", "UnifiedScanner")
    return UnifiedScanner(*args, **kwargs)

def create_example_manager(*args, **kwargs):
    """Legacy function - use APIExampleManager directly."""
    _warn_legacy_usage("create_example_manager", "APIExampleManager")
    return APIExampleManager(*args, **kwargs)

# Module-level convenience functions
def quick_generate_postman(versions=['v1', 'v2'], verbose=True):
    """
    Quick generation of Postman collections using the new package-based approach.
    
    Args:
        versions: List of API versions to generate
        verbose: Enable verbose output
    """
    generator = PostmanCollectionGenerator()
    return generate_postman_collections(versions, verbose)

def scan_all_files(versions=['v1', 'v2'], verbose=True):
    """
    Quick scan of all files using the new package-based approach.
    
    Args:
        versions: List of API versions to scan
        verbose: Enable verbose output
    """
    scanner = UnifiedScanner()
    return scanner.scan_all(versions, verbose)

def get_file_manager(base_directory=".", verbose=True):
    """
    Get a file manager instance using the new package-based approach.
    
    Args:
        base_directory: Base directory for operations
        verbose: Enable verbose output
    """
    return BaseFileManager(base_directory, verbose)

# Package version information
__version__ = "2.1.0"
__author__ = "Komodo Documentation Team"
__description__ = "Comprehensive library for managing KDF API documentation"

# Package structure information
PACKAGE_STRUCTURE = {
    "core": "Foundation utilities (config, exceptions, logging, shared utils)",
    "scanning": "File scanning and content extraction",
    "mapping": "Method mapping and normalization", 
    "postman": "Postman collection generation and management",
    "openapi": "OpenAPI specification management",
    "async_support": "Asynchronous processing utilities",
    "cli": "Command-line interface components",
    "utils": "Supporting utilities (cache, observers, templates, etc.)"
}

def print_package_structure():
    """Print the new package structure for reference."""
    print("Komodo Documentation Library v2.1.0 - Package Structure:")
    print("=" * 60)
    for package, description in PACKAGE_STRUCTURE.items():
        print(f"📦 {package:15} - {description}")
    print("=" * 60)
    print("Use: from lib.{package} import {Class} for organized imports")
    print("Or:  from lib import {Class} for backward compatibility") 