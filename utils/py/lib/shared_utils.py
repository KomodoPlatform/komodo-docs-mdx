#!/usr/bin/env python3
"""
Shared Utilities

Common utility functions used across the Komodo Documentation Library.
Consolidates file path handling, validation, and other shared functionality.
"""

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, Any, Union, Optional, List
from datetime import datetime

from .logging_utils import get_logger
from .exceptions import FileOperationError, ValidationError


def normalize_file_path(path: Union[str, Path]) -> Path:
    """
    Normalize a file path to Path object with consistent handling.
    
    Args:
        path: File path as string or Path object
        
    Returns:
        Normalized Path object
    """
    if isinstance(path, str):
        return Path(path).resolve()
    return path.resolve()


def validate_file_exists(path: Union[str, Path], operation: str = "read") -> Path:
    """
    Validate that a file exists and is readable.
    
    Args:
        path: File path to validate
        operation: Operation being performed (for error messages)
        
    Returns:
        Validated Path object
        
    Raises:
        FileOperationError: If file doesn't exist or isn't accessible
    """
    normalized_path = normalize_file_path(path)
    
    if not normalized_path.exists():
        raise FileOperationError(f"File not found for {operation}: {normalized_path}")
    
    if not normalized_path.is_file():
        raise FileOperationError(f"Path is not a file: {normalized_path}")
    
    return normalized_path


def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path
        
    Returns:
        Path object for the directory
    """
    normalized_path = normalize_file_path(path)
    normalized_path.mkdir(parents=True, exist_ok=True)
    return normalized_path


def safe_read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Safely read a JSON file with proper error handling.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileOperationError: If file cannot be read or parsed
    """
    validated_path = validate_file_exists(file_path, "read JSON")
    
    try:
        with open(validated_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise FileOperationError(f"Invalid JSON in {validated_path}: {e}")
    except Exception as e:
        raise FileOperationError(f"Error reading JSON file {validated_path}: {e}")


def safe_write_json(file_path: Union[str, Path], data: Dict[str, Any], 
                   indent: int = 2, ensure_ascii: bool = False) -> None:
    """
    Safely write data to a JSON file with proper error handling.
    
    Args:
        file_path: Path to write JSON file
        data: Data to write
        indent: JSON indentation
        ensure_ascii: Whether to ensure ASCII encoding
        
    Raises:
        FileOperationError: If file cannot be written
    """
    normalized_path = normalize_file_path(file_path)
    ensure_directory_exists(normalized_path.parent)
    
    try:
        with open(normalized_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    except Exception as e:
        raise FileOperationError(f"Error writing JSON file {normalized_path}: {e}")


def calculate_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
    """
    Calculate hash of a file's contents.
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        Hex digest of file hash
    """
    validated_path = validate_file_exists(file_path, "hash")
    
    hash_obj = hashlib.new(algorithm)
    
    with open(validated_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def calculate_content_hash(content: Union[str, Dict[str, Any]], algorithm: str = "md5") -> str:
    """
    Calculate hash of content (string or JSON data).
    
    Args:
        content: Content to hash
        algorithm: Hash algorithm
        
    Returns:
        Hex digest of content hash
    """
    if isinstance(content, dict):
        content_str = json.dumps(content, sort_keys=True, separators=(',', ':'))
    else:
        content_str = str(content)
    
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(content_str.encode('utf-8'))
    return hash_obj.hexdigest()


def extract_filename_parts(file_path: Union[str, Path]) -> Dict[str, str]:
    """
    Extract parts of a filename for analysis.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with name, stem, suffix, parent
    """
    path = normalize_file_path(file_path)
    
    return {
        'name': path.name,
        'stem': path.stem,
        'suffix': path.suffix,
        'parent': str(path.parent),
        'parent_name': path.parent.name
    }


def convert_dir_to_method_name(directory_name: str) -> str:
    """
    Convert directory name to API method name format.
    
    Args:
        directory_name: Directory name (with hyphens)
        
    Returns:
        Method name (with double colons)
    """
    return directory_name.replace('-', '::')


def convert_method_to_dir_name(method_name: str) -> str:
    """
    Convert API method name to directory name format.
    
    Args:
        method_name: Method name (with double colons)
        
    Returns:
        Directory name (with hyphens)
    """
    return method_name.replace('::', '-')


def format_method_name_for_display(method_name: str) -> str:
    """
    Format method name for human-readable display.
    
    Args:
        method_name: Raw method name
        
    Returns:
        Formatted display name
    """
    return method_name.replace('_', ' ').replace('::', ' ').title()


def get_file_stats(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Get comprehensive statistics about a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file statistics
    """
    validated_path = validate_file_exists(file_path, "get stats")
    stat = validated_path.stat()
    
    return {
        'size': stat.st_size,
        'modified': datetime.fromtimestamp(stat.st_mtime),
        'created': datetime.fromtimestamp(stat.st_ctime),
        'extension': validated_path.suffix,
        'name': validated_path.name,
        'stem': validated_path.stem,
        'is_file': validated_path.is_file(),
        'is_dir': validated_path.is_dir()
    }


def find_files_by_pattern(directory: Union[str, Path], pattern: str, 
                         recursive: bool = True) -> List[Path]:
    """
    Find files matching a pattern in a directory.
    
    Args:
        directory: Directory to search
        pattern: Glob pattern to match
        recursive: Whether to search recursively
        
    Returns:
        List of matching file paths
    """
    dir_path = normalize_file_path(directory)
    
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    
    if recursive:
        return list(dir_path.rglob(pattern))
    else:
        return list(dir_path.glob(pattern))


def clean_empty_directories(directory: Union[str, Path], dry_run: bool = True) -> List[str]:
    """
    Remove empty directories recursively.
    
    Args:
        directory: Root directory to clean
        dry_run: If True, only report what would be deleted
        
    Returns:
        List of directories that were (or would be) removed
    """
    dir_path = normalize_file_path(directory)
    removed_dirs = []
    
    if not dir_path.exists():
        return removed_dirs
    
    # Walk directory tree bottom-up
    for root, dirs, files in os.walk(str(dir_path), topdown=False):
        for dir_name in dirs:
            dir_to_check = Path(root) / dir_name
            
            # Check if directory is empty
            try:
                if not any(dir_to_check.iterdir()):
                    if dry_run:
                        removed_dirs.append(str(dir_to_check))
                    else:
                        dir_to_check.rmdir()
                        removed_dirs.append(str(dir_to_check))
            except OSError:
                # Directory not empty or permission error
                pass
    
    return removed_dirs


def create_backup_path(file_path: Union[str, Path], suffix: str = ".backup") -> Path:
    """
    Create a backup file path by adding a suffix.
    
    Args:
        file_path: Original file path
        suffix: Suffix to add
        
    Returns:
        Backup file path
    """
    path = normalize_file_path(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    return path.with_name(f"{path.stem}_{timestamp}{suffix}{path.suffix}")


def safe_copy_file(src: Union[str, Path], dst: Union[str, Path], 
                   create_backup: bool = False) -> None:
    """
    Safely copy a file with optional backup.
    
    Args:
        src: Source file path
        dst: Destination file path
        create_backup: Whether to create backup of destination if it exists
        
    Raises:
        FileOperationError: If copy operation fails
    """
    import shutil
    
    src_path = validate_file_exists(src, "copy from")
    dst_path = normalize_file_path(dst)
    
    # Create backup if requested and destination exists
    if create_backup and dst_path.exists():
        backup_path = create_backup_path(dst_path)
        shutil.copy2(str(dst_path), str(backup_path))
    
    # Ensure destination directory exists
    ensure_directory_exists(dst_path.parent)
    
    try:
        shutil.copy2(str(src_path), str(dst_path))
    except Exception as e:
        raise FileOperationError(f"Error copying {src_path} to {dst_path}: {e}") 