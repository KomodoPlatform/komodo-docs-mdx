#!/usr/bin/env python3
"""
Scanning Module

Provides unified file scanning functionality for the Komodo Documentation Library.
All scanner functionality has been consolidated into a clean, well-organized system.
"""

# Import the unified scanning system
from .unified_scanners import (
    UnifiedScanner, ScanResult
)

# Import content extraction utilities
from .extractors import (
    ExtractedExample, MDXExtractor
)

# Import repository scanning functionality
try:
    from .repository_scanner import (
        KDFRepositoryScanner, RepositoryInfo, 
        scan_kdf_repository, compare_repo_with_docs
    )
except ImportError:
    # Repository scanner not available
    KDFRepositoryScanner = None
    RepositoryInfo = None
    scan_kdf_repository = None
    compare_repo_with_docs = None

# Convenience functions
def get_unified_scanner(*args, **kwargs):
    """Get a unified scanner instance."""
    return UnifiedScanner(*args, **kwargs)

def get_scanner():
    """Get default scanner instance."""
    return UnifiedScanner()

__all__ = [
    # Primary scanning interface
    'UnifiedScanner', 'ScanResult',
    
    # Content extraction
    'ExtractedExample', 'MDXExtractor',
    
    # Repository scanning
    'KDFRepositoryScanner', 'RepositoryInfo', 
    'scan_kdf_repository', 'compare_repo_with_docs',
    
    # Convenience functions
    'get_unified_scanner', 'get_scanner'
] 