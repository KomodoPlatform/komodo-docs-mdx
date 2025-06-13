"""
Komodo Documentation Library

A comprehensive library for managing API documentation, Postman collections,
OpenAPI specifications, and file operations for Komodo DeFi Framework.

REFACTORED VERSION - Now with consolidated modules for better efficiency and maintainability.
"""

# Core classes - Updated to use consolidated modules
from .mapping import MethodMapper
from .postman_consolidated import PostmanCollectionGenerator, generate_postman_collections
from .openapi_manager import OpenAPIManager
from .cli_base import CLIBase, VersionedCLI, BatchProcessorCLI, create_simple_cli

# Repository scanning functionality
from .repository_scanner import KDFRepositoryScanner, RepositoryInfo, scan_kdf_repository, compare_repo_with_docs

# New unified base classes
from .shared_utils import (
    normalize_file_path, validate_file_exists, ensure_directory_exists,
    safe_read_json, safe_write_json, calculate_content_hash, 
    convert_dir_to_method_name, format_method_name_for_display
)
from .base_file_manager import BaseFileManager, FileOperationResult
from .unified_scanners import UnifiedScanner, ScanResult

# Consolidated Postman modules
from .postman_core import (
    PostmanRequest, PostmanFolder, PostmanRequestProcessor,
    MethodCategorizer, FolderOrganizer, CollectionGenerator, EnvironmentGenerator
)
from .postman_io import PostmanFileManager, JSONExampleScanner, PostmanReportGenerator

# Configuration and exceptions
from .config import KomodoConfig, get_config, reset_config
from .exceptions import (
    KomodoLibraryError, FileOperationError, ValidationError, ParseError,
    ConfigurationError, MethodNotFoundError, PostmanGenerationError,
    OpenAPIError, ExtractionError, DeduplicationError, MappingError
)

# Logging and utilities
from .logging_utils import (
    KomodoLogger, get_logger, setup_logging, ProgressTracker,
    log_file_operation, log_method_processing, log_stats
)

# Observer pattern for event handling
from .observers import (
    EventType, Event, Observer, Subject, LoggingObserver, ProgressTrackingObserver,
    StatisticsObserver, FileEventObserver, CallbackObserver, EventPublisher,
    get_event_publisher, publish_operation_started, publish_operation_completed,
    publish_file_processed, publish_file_error
)

# Caching system
from .cache import (
    KomodoCache, get_cache, cached, cache_file_scan, cache_directory_scan
)

# Async utilities
from .async_utils import (
    AsyncFileProcessor, AsyncMethodProcessor, async_cached,
    run_with_progress, run_async
)

# Legacy file operations (maintained for backward compatibility)
from .file_operations import ExampleFileManager

# Processing utilities
from .extractors import ExtractedExample, MDXExtractor
from .method_normalizer import MethodNameNormalizer
from .deduplicator import ExampleDeduplicator
from .converter import MDXToOpenAPIConverter

# Templates and reporting
from .templates import ExampleTemplates
from .reporters import ExampleReporter
from .mapping_reports import MethodMapping, MappingReporter

# Architecture improvements and patterns
from .processors import (
    FileProcessorStrategy, JSONProcessorStrategy, MDXProcessorStrategy, 
    YAMLProcessorStrategy, FileProcessorContext, ProcessingResult,
    create_file_processor, process_single_file
)

# Validation system
from .validation import ValidationManager, ValidationResult, ValidationLevel

# Legacy imports for backward compatibility
# These import the old modules but should not be used in new code
try:
    # Import old modules if they exist, but prefer new consolidated ones
    from .example_manager import APIExampleManager
    from .file_scanners import MDXScanner, YAMLScanner, JSONExampleScanner as LegacyJSONScanner
except ImportError:
    # Old modules may have been removed, which is fine
    pass

# Version and metadata
__version__ = "2.0.0"
__author__ = "Komodo Platform"
__description__ = "Consolidated documentation library for Komodo DeFi Framework"

# Preferred imports for new code
__all__ = [
    # Core functionality - RECOMMENDED
    'PostmanCollectionGenerator',
    'generate_postman_collections',
    'UnifiedScanner',
    'BaseFileManager',
    'MethodMapper',
    'OpenAPIManager',
    
    # Repository scanning - NEW
    'KDFRepositoryScanner',
    'RepositoryInfo',
    'scan_kdf_repository',
    'compare_repo_with_docs',
    
    # Shared utilities - RECOMMENDED
    'normalize_file_path',
    'safe_read_json', 
    'safe_write_json',
    'convert_dir_to_method_name',
    'format_method_name_for_display',
    
    # Event system - RECOMMENDED
    'get_event_publisher',
    'publish_file_processed',
    'publish_file_error',
    
    # Configuration and logging
    'get_config',
    'get_logger',
    'setup_logging',
    
    # Exceptions
    'KomodoLibraryError',
    'FileOperationError',
    'ValidationError',
    
    # Legacy support (use new modules instead)
    'ExampleFileManager',
    'MDXExtractor',
    'ExampleDeduplicator',
]

# Deprecation warnings for old patterns
import warnings

def _warn_legacy_usage(old_name: str, new_name: str):
    """Helper to issue deprecation warnings."""
    warnings.warn(
        f"{old_name} is deprecated. Use {new_name} instead.",
        DeprecationWarning,
        stacklevel=3
    )

# Legacy compatibility functions with deprecation warnings
def create_postman_generator(*args, **kwargs):
    """Legacy function - use PostmanCollectionGenerator directly."""
    _warn_legacy_usage("create_postman_generator", "PostmanCollectionGenerator")
    return PostmanCollectionGenerator(*args, **kwargs)

def create_file_scanner(*args, **kwargs):
    """Legacy function - use UnifiedScanner directly."""
    _warn_legacy_usage("create_file_scanner", "UnifiedScanner")
    return UnifiedScanner(*args, **kwargs)

def create_example_manager(*args, **kwargs):
    """Legacy function - use BaseFileManager or PostmanCollectionGenerator directly."""
    _warn_legacy_usage("create_example_manager", "BaseFileManager or PostmanCollectionGenerator")
    try:
        from .example_manager import APIExampleManager
        return APIExampleManager(*args, **kwargs)
    except ImportError:
        # Fallback to new unified approach
        return PostmanCollectionGenerator(*args, **kwargs)

# Module-level convenience functions
def quick_generate_postman(versions=['v1', 'v2'], verbose=True):
    """
    Quick generation of Postman collections using the new consolidated approach.
    
    Args:
        versions: List of API versions to generate
        verbose: Enable verbose output
        
    Returns:
        Dictionary mapping versions to (collection_path, env_path) tuples
    """
    return generate_postman_collections(versions, verbose)

def scan_all_files(versions=['v1', 'v2'], verbose=True):
    """
    Quick scanning of all file types using the unified scanner.
    
    Args:
        versions: List of API versions to scan
        verbose: Enable verbose output
        
    Returns:
        Dictionary with scanning results
    """
    scanner = UnifiedScanner(verbose=verbose)
    return scanner.scan_all_files(versions)

def get_file_manager(base_directory=".", verbose=True):
    """
    Get a file manager instance using the new base class.
    
    Args:
        base_directory: Base directory for operations
        verbose: Enable verbose output
        
    Returns:
        BaseFileManager instance
    """
    return BaseFileManager(base_directory, verbose)

# Print initialization message for new consolidated library
import sys
if '--quiet' not in sys.argv and '-q' not in sys.argv:
    print("📚 Komodo Documentation Library v2.0.0 - Consolidated Edition")
    print("   ✨ Now with unified modules for better performance and maintainability")
    print("   📖 Use PostmanCollectionGenerator and UnifiedScanner for best experience")
    print()

# Cleanup
del warnings, sys 