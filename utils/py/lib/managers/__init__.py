"""
Managers Package - Centralized Management Classes

This package consolidates all manager classes that coordinate complex operations:
- OpenAPIManager: OpenAPI specification management
- TableManager: API methods table generation
- PostmanFileManager: Postman file operations
- ValidationManager: Validation operations
- MethodMappingManager: API method mapping operations
- MethodMapping: Data structure for method mapping information
- SimpleComparator: Simple JSON-based method comparison
- DocumentationGenerator: Generate comprehensive MDX documentation

Note: APIExampleManager removed from init to avoid circular imports.
Import directly: from lib.managers.example_manager import APIExampleManager
"""

from .openapi_manager import OpenAPIManager
from .table_manager import TableManager
# Removed: from .example_manager import APIExampleManager  # Circular import
from .postman_manager import PostmanFileManager
from .validation_manager import ValidationManager
from .method_mapping_manager import MethodMappingManager
from .method_mapping import MethodMapping
from .simple_comparator import SimpleComparator

# Import documentation generator
try:
    from .documentation_generator import (
        DocumentationGenerator, generate_documentation_from_analysis, generate_single_method_doc
    )
except ImportError:
    # Documentation generator not available
    DocumentationGenerator = None
    generate_documentation_from_analysis = None
    generate_single_method_doc = None

__all__ = [
    # Core managers
    'OpenAPIManager',
    'TableManager', 
    # 'APIExampleManager',  # Removed due to circular import
    'PostmanFileManager',
    'ValidationManager',
    'MethodMappingManager',
    'MethodMapping',
    'SimpleComparator',
    
    # Documentation generation
    'DocumentationGenerator',
    'generate_documentation_from_analysis',
    'generate_single_method_doc'
] 