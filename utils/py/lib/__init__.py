#!/usr/bin/env python3
"""
Komodo Documentation Library

A comprehensive library for processing, validating, and managing
Komodo DeFi Framework API documentation across multiple formats.

ULTRA-LEAN VERSION: Optimized for production use with dead weight removed.
"""

# Core functionality - Enhanced async-first approach
from .utils.logging_utils import get_logger, setup_logging

# Configuration and exceptions from constants package
from .constants import (
    get_config, ValidationLevel, 
    FileOperationError, ValidationError, ConfigurationError
)

# Enhanced mapping and processing
from .managers.method_mapping_manager import (
    MethodMappingManager, MethodMapping
)

from .utils.path_utils import EnhancedPathMapper

# Async processing capabilities
from .async_support import (
    AsyncMethodProcessor, run_async
)

# Scanning and analysis
from .scanning import (
    UnifiedScanner, KDFRepositoryScanner, PostmanJSONProcessor,
    LocalKDFScanner, MethodDetails
)

# OpenAPI generation
from .managers import (
    OpenAPIManager, TableManager,
    PostmanFileManager, ValidationManager, MethodMappingManager,
    DocumentationGenerator
)
# Note: APIExampleManager removed to avoid circular imports
# Use: from lib.managers.example_manager import APIExampleManager

# Postman collection management - now handled by PostmanManager
# from .postman import (
#     PostmanCollectionGenerator, MethodCategorizer, PostmanReportGenerator
# ) - REMOVED: Functionality consolidated into managers.postman_manager

# Utilities and helpers
from .utils import (
    normalize_method_name, format_method_name_for_display, extract_method_parts,
    ensure_directory_exists, safe_read_json, safe_write_json
)

# Import centralized reporting module
from .reporting import BaseReporter, MappingReporter, PostmanReportGenerator, ExampleReporter

__version__ = "2.0.0-lean"

__all__ = [
    # Core functionality
    'get_logger', 'setup_logging', 'get_config',
    'FileOperationError', 'ValidationError', 'ConfigurationError',
    
    # Enhanced mapping (primary)
    'MethodMappingManager', 'MethodMapping', 'EnhancedPathMapper',
    
    # Async processing
    'AsyncMethodProcessor', 'run_async',
    
    # Scanning and analysis
    'UnifiedScanner', 'KDFRepositoryScanner', 'PostmanJSONProcessor',
    'LocalKDFScanner', 'MethodDetails',
    
    # OpenAPI generation
    'OpenAPIManager',
    
    # Postman management
    # 'PostmanCollectionGenerator', 'MethodCategorizer', 'PostmanReportGenerator',
    
    # Managers - Centralized management
    'TableManager', 'PostmanFileManager', 'ValidationManager', 'MethodMappingManager',
    'DocumentationGenerator',
    
    # Essential utilities
    'normalize_method_name', 'format_method_name_for_display', 'extract_method_parts',
    'ensure_directory_exists', 'safe_read_json', 'safe_write_json',
    'ValidationLevel',
    
    # Version
    '__version__',

    # Reporting
    'BaseReporter', 'MappingReporter', 'PostmanReportGenerator', 'ExampleReporter'
]

# Package structure information
PACKAGE_STRUCTURE = {
    "constants": "Static data, configuration, exceptions, enums, templates",
    "scanning": "File scanning and content extraction",
    "postman": "Postman collection generation and management",
    "openapi": "OpenAPI specification management",
    "async_support": "Asynchronous processing utilities",
    "utils": "Supporting utilities (cache, observers, file operations, etc.)",
    "managers": "Centralized management classes (including method mapping)",
    "reporting": "Centralized reporting functionality"
}

def print_package_structure():
    """Print the package structure for reference."""
    print("Komodo Documentation Library v2.0.0-lean - Package Structure:")
    print("=" * 60)
    for package, description in PACKAGE_STRUCTURE.items():
        print(f"📦 {package:15} - {description}")
    print("=" * 60)
    print("Use: from lib.{package} import {Class} for organized imports")
    print("Or:  from lib import {Class} for backward compatibility") 