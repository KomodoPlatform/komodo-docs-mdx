"""
Postman Package - Postman collection generation and management

This package handles all Postman-related functionality:
- Core Postman classes
- Collection generators
- File I/O operations
- Organization utilities
"""

from .postman_core import (
    PostmanRequest, PostmanFolder, PostmanRequestProcessor,
    MethodCategorizer, FolderOrganizer, CollectionGenerator, EnvironmentGenerator
)
from .postman_io import PostmanFileManager, JSONExampleScanner, PostmanReportGenerator
from .postman_consolidated import PostmanCollectionGenerator, generate_postman_collections
# Import what's available from other postman modules
try:
    from .postman_generators import *
except ImportError:
    pass
try:
    from .postman_organizers import *
except ImportError:
    pass
try:
    from .postman_file_ops import *
except ImportError:
    pass
try:
    from .postman import *
except ImportError:
    pass

__all__ = [
    # Core classes
    'PostmanRequest', 'PostmanFolder', 'PostmanRequestProcessor',
    'MethodCategorizer', 'FolderOrganizer', 'CollectionGenerator', 'EnvironmentGenerator',
    
    # I/O operations
    'PostmanFileManager', 'JSONExampleScanner', 'PostmanReportGenerator',
    
    # Main generator
    'PostmanCollectionGenerator', 'generate_postman_collections'
] 