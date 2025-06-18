#!/usr/bin/env python3
"""
File Types and Data Structures

Core data structures for file operations, moved from unified_file_ops.py
for better organization and to eliminate bloated files.

Note: All dataclasses have been moved to constants.data_structures
"""

# Import all data structures from constants
from ..constants import FileInfo, OperationResult, BatchResult

# Re-export for backwards compatibility
__all__ = ['FileInfo', 'OperationResult', 'BatchResult'] 