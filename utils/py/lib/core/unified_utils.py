#!/usr/bin/env python3
"""
Core Unified Utilities

Core utility functions that don't depend on other lib modules.
This module provides only essential utilities needed by core modules.
Other utilities have been moved to the utils package to avoid circular imports.
"""

# Re-export commonly used functions from utils to maintain backward compatibility
# Note: These imports are safe because utils doesn't import from core
from ..utils.file_utils import (
    normalize_file_path, validate_file_exists, ensure_directory_exists,
    safe_read_json, safe_write_json, calculate_content_hash,
    get_file_stats, extract_filename_parts, calculate_file_hash,
    safe_copy_file, create_backup_path, clean_empty_directories,
    quick_file_stats, find_files_by_pattern
)

from ..utils.string_utils import (
    convert_dir_to_method_name, convert_method_to_dir_name,
    format_method_name_for_display, generate_api_path,
    extract_category_from_method, normalize_method_name,
    normalize_method_name_variations, convert_filesystem_to_api_format,
    convert_api_to_filesystem_format, extract_base_method, extract_operation,
    is_valid_method_name, clean_method_name
)

from ..utils.enums import PathType, VersionStatus 