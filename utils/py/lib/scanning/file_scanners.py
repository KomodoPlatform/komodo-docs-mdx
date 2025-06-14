#!/usr/bin/env python3
"""
File Scanners - DEPRECATED

This module previously contained scanner classes that have been consolidated into UnifiedScanner.
Please use UnifiedScanner from lib.scanning.unified_scanners instead.

All functionality has been moved to:
- lib.scanning.unified_scanners.UnifiedScanner (for general file scanning)
- lib.postman.postman_scanners.JSONExampleScanner (for Postman-specific JSON scanning)
- lib.postman.postman_io.JSONExampleScanner (for Postman I/O operations)
"""

import warnings


def __getattr__(name):
    """Handle imports of deprecated classes with informative error messages."""
    deprecated_classes = {
        'MDXScanner': 'UnifiedScanner from lib.scanning.unified_scanners',
        'YAMLScanner': 'UnifiedScanner from lib.scanning.unified_scanners', 
        'JSONExampleScanner': 'UnifiedScanner from lib.scanning.unified_scanners or PostmanJSONScanner for Postman-specific use',
        'PathExtractor': 'inline path extraction logic (no longer needed)',
        'convert_dir_to_method_name': 'convert_dir_to_method_name from lib.utils.string_utils'
    }
    
    if name in deprecated_classes:
        replacement = deprecated_classes[name]
        error_msg = (
            f"{name} has been removed. Use {replacement} instead. "
            f"The old scanner classes contained duplicate logic and have been consolidated."
        )
        raise ImportError(error_msg)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'") 