"""
Utils Package - Supporting utilities

This package provides supporting utilities:
- Shared enums and constants
- File utilities (path operations, file I/O)
- String utilities (method name conversions, formatting)
- Caching system
- Observer pattern
- Template management
- Reporting utilities
- Factory patterns
- Example management
- Table management
"""

# Core utilities
from .enums import (
    PathType, VersionStatus, EventType, ValidationLevel, ProcessingStatus,
    DEFAULT_CACHE_TTL, DEFAULT_BATCH_SIZE, DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES,
    MDX_PATTERNS, JSON_PATTERNS, YAML_PATTERNS, API_VERSIONS, SUPPORTED_EXTENSIONS,
    FILE_PATTERNS, KNOWN_EXTENSIONS, BATCH_SIZES, TIMEOUT_SETTINGS, VALIDATION_RULES
)
from .file_utils import (
    normalize_file_path, validate_file_exists, ensure_directory_exists,
    find_files_by_pattern, safe_read_json, safe_write_json,
    get_file_stats, extract_filename_parts, calculate_file_hash, calculate_content_hash,
    safe_copy_file, create_backup_path, clean_empty_directories, quick_file_stats
)
from .string_utils import (
    convert_dir_to_method_name, convert_method_to_dir_name, format_method_name_for_display,
    normalize_method_name, normalize_method_name_variations, extract_method_parts, join_method_parts,
    generate_api_path, extract_category_from_method, is_valid_method_name, clean_method_name,
    convert_filesystem_to_api_format, convert_api_to_filesystem_format, 
    extract_base_method, extract_operation,
    camel_case_to_snake_case, snake_case_to_camel_case, title_case_with_exceptions, truncate_text,
    extract_method_name_from_mdx_content, extract_method_name_from_yaml_filename,
    extract_methods_from_mdx_codeblocks
)

# Supporting utilities
from .cache import KomodoCache, get_cache, cached, cache_file_scan, cache_directory_scan, cache_key_from_dict
from .observers import (
    Event, Observer, Subject, LoggingObserver, ProgressTrackingObserver,
    StatisticsObserver, FileEventObserver, CallbackObserver, EventPublisher,
    get_event_publisher, publish_operation_started, publish_operation_completed,
    publish_file_processed, publish_file_error
)
from .templates import ExampleTemplates
from .reporters import ExampleReporter
from .deduplicator import ExampleDeduplicator
from .factories import *
# from .examples import *  # Commented out to avoid circular import with async_support
from .example_manager import APIExampleManager
from .table_manager import *

__all__ = [
    # Core utilities - Enums and constants
    'PathType', 'VersionStatus', 'EventType', 'ValidationLevel', 'ProcessingStatus',
    'DEFAULT_CACHE_TTL', 'DEFAULT_BATCH_SIZE', 'DEFAULT_TIMEOUT', 'DEFAULT_MAX_RETRIES',
    'MDX_PATTERNS', 'JSON_PATTERNS', 'YAML_PATTERNS', 'API_VERSIONS', 'SUPPORTED_EXTENSIONS',
    'FILE_PATTERNS', 'KNOWN_EXTENSIONS', 'BATCH_SIZES', 'TIMEOUT_SETTINGS', 'VALIDATION_RULES',
    
    # Core utilities - File operations
    'normalize_file_path', 'validate_file_exists', 'ensure_directory_exists',
    'find_files_by_pattern', 'safe_read_json', 'safe_write_json',
    'get_file_stats', 'extract_filename_parts', 'calculate_file_hash', 'calculate_content_hash',
    'safe_copy_file', 'create_backup_path', 'clean_empty_directories', 'quick_file_stats',
    
    # Core utilities - String operations
    'convert_dir_to_method_name', 'convert_method_to_dir_name', 'format_method_name_for_display',
    'normalize_method_name', 'normalize_method_name_variations', 'extract_method_parts', 'join_method_parts',
    'generate_api_path', 'extract_category_from_method', 'is_valid_method_name', 'clean_method_name',
    'convert_filesystem_to_api_format', 'convert_api_to_filesystem_format', 
    'extract_base_method', 'extract_operation',
    'camel_case_to_snake_case', 'snake_case_to_camel_case', 'title_case_with_exceptions', 'truncate_text',
    'extract_method_name_from_mdx_content', 'extract_method_name_from_yaml_filename',
    'extract_methods_from_mdx_codeblocks',
    
    # Caching system
    'KomodoCache', 'get_cache', 'cached', 'cache_file_scan', 'cache_directory_scan', 'cache_key_from_dict',
    
    # Observer pattern
    'Event', 'Observer', 'Subject', 'LoggingObserver', 'ProgressTrackingObserver',
    'StatisticsObserver', 'FileEventObserver', 'CallbackObserver', 'EventPublisher',
    'get_event_publisher', 'publish_operation_started', 'publish_operation_completed',
    'publish_file_processed', 'publish_file_error',
    
    # Templates and utilities
    'ExampleTemplates', 'ExampleReporter', 'ExampleDeduplicator',
    
    # Example management
    'APIExampleManager'
] 