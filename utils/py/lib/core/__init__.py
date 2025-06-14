#!/usr/bin/env python3
"""
Core Module

Central module providing core functionality for the Komodo Documentation Library.
Now uses unified file operations and scanning systems.
"""

# Core configuration and logging
from .config import KomodoConfig, get_config, reset_config
from .logging_utils import (
    get_logger, setup_logging, ProgressTracker, KomodoLogger,
    log_file_operation, log_method_processing, log_stats
)

# Unified file operations (replaces base_file_manager, file_utils, file_operations)
from .unified_file_ops import (
    UnifiedFileOperations, PostmanFileOperations, 
    get_file_ops, get_postman_ops,
    read_json, write_json, ensure_dir, scan_json_files,
    FileInfo, OperationResult, BatchResult, FileType, ValidationLevel
)

# Note: Scanner classes moved to scanning package for better organization

# Other core utilities
from .exceptions import (
    KomodoLibraryError, ConfigurationError, ValidationError, 
    FileOperationError, ParseError, MethodNotFoundError,
    PostmanGenerationError, OpenAPIError, ExtractionError, 
    DeduplicationError, MappingError
)

# Unified utilities (replaces shared_utils and scattered utility functions)
from .unified_utils import (
    normalize_file_path, validate_file_exists, ensure_directory_exists,
    safe_read_json, safe_write_json, get_file_stats, find_files_by_pattern,
    calculate_content_hash, extract_filename_parts,
    convert_dir_to_method_name, format_method_name_for_display,
    PathType, VersionStatus, generate_api_path, extract_category_from_method,
    normalize_method_name, quick_file_stats, clean_empty_directories
)

# Backward compatibility - map old imports to new unified system
BaseFileManager = UnifiedFileOperations
FileOperationResult = OperationResult
ExampleFileManager = UnifiedFileOperations

__all__ = [
    # Configuration and logging
    'KomodoConfig', 'get_config', 'reset_config', 'get_logger', 'setup_logging', 'ProgressTracker', 'KomodoLogger',
    'log_file_operation', 'log_method_processing', 'log_stats',
    
    # Unified file operations
    'UnifiedFileOperations', 'PostmanFileOperations', 
    'get_file_ops', 'get_postman_ops',
    'read_json', 'write_json', 'ensure_dir', 'scan_json_files',
    'FileInfo', 'OperationResult', 'BatchResult', 'FileType', 'ValidationLevel',
    
    # Exceptions
    'KomodoLibraryError', 'ConfigurationError', 'ValidationError', 
    'FileOperationError', 'ParseError', 'MethodNotFoundError',
    'PostmanGenerationError', 'OpenAPIError', 'ExtractionError', 
    'DeduplicationError', 'MappingError',
    
    # Shared utilities
    'normalize_file_path', 'validate_file_exists', 'ensure_directory_exists',
    'safe_read_json', 'safe_write_json', 'get_file_stats', 'find_files_by_pattern',
    'calculate_content_hash', 'extract_filename_parts',
    'convert_dir_to_method_name', 'format_method_name_for_display',
    'PathType', 'VersionStatus', 'generate_api_path', 'extract_category_from_method',
    'normalize_method_name', 'quick_file_stats', 'clean_empty_directories',
    
    # Backward compatibility
    'BaseFileManager', 'FileOperationResult', 'ExampleFileManager'
] 