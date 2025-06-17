#!/usr/bin/env python3
"""
Utils Package - Utility functions and classes

This package provides various utility functions and classes used throughout 
the KDF documentation utilities.

Components:
- File operations and management utilities
- Path manipulation utilities  
- String processing utilities
- Logging utilities
- Caching patterns
- Factory components
- Example management utilities
- Reporting utilities (moved to centralized reporting module)
"""

# File operations and types
from .file_utils import (
    normalize_file_path, validate_file_exists, ensure_directory_exists,
    find_files_by_pattern, safe_read_json, safe_write_json,
    get_file_stats, extract_filename_parts, calculate_file_hash, calculate_content_hash,
    safe_copy_file, create_backup_path, clean_empty_directories, quick_file_stats,
    cleanup_old_files, cleanup_kdf_temp_files
)
from .file_types import FileType, FileInfo, OperationResult, BatchResult
from .batch_processor import BatchFileProcessor, batch_read_json_files, batch_write_json_files

# Path utilities
from .path_utils import (
    EnhancedPathMapper, PathMapping
)

# String processing
from .string_utils import (
    normalize_method_name, format_method_name_for_display, extract_method_parts,
    convert_dir_to_method_name, convert_method_to_dir_name, join_method_parts,
    convert_canonical_to_slug, convert_slug_to_canonical, 
    convert_folder_to_slug, convert_slug_to_folder,
    generate_api_path, extract_category_from_method,
    extract_method_name_from_mdx_content, extract_method_name_from_yaml_filename,
    extract_methods_from_mdx_codeblocks, truncate_text, find_best_match,
    normalize_method_name_variations, convert_filesystem_to_api_format
)

# Logging utilities
from .logging_utils import (
    get_logger, setup_logging, KomodoLogger, ProgressTracker,
    log_file_operation, log_method_processing, log_stats
)

# Factory components
from .factories import (
    ComponentType, ComponentDependencies, MasterFactory, 
    get_master_factory, create_postman_generator, create_method_mapper, create_complete_pipeline
)

# Templates from constants package
from ..constants.templates import ExampleTemplates

# Import from centralized reporting module
from ..reporting.example_reporter import ExampleReporter

# Postman utilities
from .postman_utils import PostmanUtilities, PostmanFolder

# Cleanup utilities
from .cleanup_utils import (
    GeneratedFilesCleaner, clean_generated_files, clean_stale_generated_files
)

from .github_scanner import GitHubScanner
from .method_analyzer import MethodAnalyzer, Parameter, MethodAnalysis
from .doc_generator import DocumentationGenerator

__all__ = [
    # File operations and types
    'normalize_file_path', 'validate_file_exists', 'ensure_directory_exists',
    'find_files_by_pattern', 'safe_read_json', 'safe_write_json',
    'get_file_stats', 'extract_filename_parts', 'calculate_file_hash', 'calculate_content_hash',
    'safe_copy_file', 'create_backup_path', 'clean_empty_directories', 'quick_file_stats',
    'cleanup_old_files', 'cleanup_kdf_temp_files',
    'FileType', 'FileInfo', 'OperationResult', 'BatchResult',
    'BatchFileProcessor', 'batch_read_json_files', 'batch_write_json_files',
    
    # Path utilities
    'EnhancedPathMapper', 'PathMapping',
    
    # String operations
    'normalize_method_name', 'format_method_name_for_display', 'extract_method_parts',
    'convert_dir_to_method_name', 'convert_method_to_dir_name', 'join_method_parts',
    'convert_canonical_to_slug', 'convert_slug_to_canonical', 
    'convert_folder_to_slug', 'convert_slug_to_folder',
    'generate_api_path', 'extract_category_from_method',
    'extract_method_name_from_mdx_content', 'extract_method_name_from_yaml_filename',
    'extract_methods_from_mdx_codeblocks', 'truncate_text', 'find_best_match',
    'normalize_method_name_variations', 'convert_filesystem_to_api_format',
    
    # Logging utilities
    'get_logger', 'setup_logging', 'KomodoLogger', 'ProgressTracker',
    'log_file_operation', 'log_method_processing', 'log_stats',
    
    # Factory components
    'ComponentType', 'ComponentDependencies', 'MasterFactory',
    'get_master_factory', 'create_postman_generator', 'create_method_mapper', 'create_complete_pipeline',
    
    # Example management
    'ExampleTemplates', 'ExampleReporter',
    
    # Postman utilities
    'PostmanUtilities', 'PostmanFolder',
    
    # Cleanup utilities
    'GeneratedFilesCleaner', 'clean_generated_files', 'clean_stale_generated_files',

    'GitHubScanner',
    'MethodAnalyzer', 
    'Parameter',
    'MethodAnalysis',
    'DocumentationGenerator'
]

# Version info
__version__ = '1.0.0' 