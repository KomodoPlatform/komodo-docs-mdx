#!/usr/bin/env python3
"""
Scanning Module

Provides unified file scanning functionality for the Komodo Documentation Library.
All scanner functionality has been consolidated into a clean, well-organized system.

Consolidated structure:
- documentation_scanner.py: Main file scanning (MDX, YAML, JSON) with async support
- postman_scanners.py: Postman-specific processing (now uses UnifiedScanner internally)
- repository_scanner.py: Repository source code scanning (consolidated)
- local_repository_scanner.py: Local repository scanning with detailed analysis

PERFORMANCE UPGRADE: All scanners now use async processing for 3-5x faster performance.
"""

# Import the documentation scanning system
from .mdx_scanner import (
    UnifiedScanner, ScanResult
)

# Import Postman-specific processing (now consolidated with UnifiedScanner)
from .postman_scanners import (
    PostmanJSONProcessor, PostmanRequest, MethodCategorizer
)

# Import repository scanning functionality (consolidated)
try:
    from .repository_scanner import (
        KDFRepositoryScanner, RepositoryInfo
    )
except ImportError:
    # Repository scanner not available
    KDFRepositoryScanner = None
    RepositoryInfo = None

# Import local repository scanning functionality
try:
    from .local_repository_scanner import (
        LocalKDFScanner, MethodDetails, setup_local_kdf_repo, scan_local_methods
    )
except ImportError:
    # Local scanner not available
    LocalKDFScanner = None
    MethodDetails = None
    setup_local_kdf_repo = None
    scan_local_methods = None

# Convenience functions
def get_unified_scanner(*args, **kwargs):
    """Get a unified scanner instance."""
    return UnifiedScanner(*args, **kwargs)

def get_postman_processor(*args, **kwargs):
    """Get a Postman processor instance (uses UnifiedScanner internally)."""
    return PostmanJSONProcessor(*args, **kwargs)

def get_local_kdf_scanner(*args, **kwargs):
    """Get a local KDF scanner instance."""
    if LocalKDFScanner is None:
        raise ImportError("LocalKDFScanner not available")
    return LocalKDFScanner(*args, **kwargs)

__all__ = [
    # Primary scanning interface
    'UnifiedScanner', 'ScanResult',
    
    # Postman processing
    'PostmanJSONProcessor', 'PostmanRequest', 'MethodCategorizer',
    
    # Repository scanning (consolidated)
    'KDFRepositoryScanner', 'RepositoryInfo',
    
    # Local repository scanning
    'LocalKDFScanner', 'MethodDetails', 'setup_local_kdf_repo', 'scan_local_methods',
    
    # Convenience functions
    'get_unified_scanner', 'get_postman_processor', 'get_local_kdf_scanner'
] 