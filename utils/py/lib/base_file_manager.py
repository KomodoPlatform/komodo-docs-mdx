#!/usr/bin/env python3
"""
Base File Manager

Unified base class for all file operations in the Komodo Documentation Library.
Consolidates common functionality from various file managers.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .logging_utils import get_logger, ProgressTracker
from .exceptions import FileOperationError, ValidationError
from .shared_utils import (
    normalize_file_path, validate_file_exists, ensure_directory_exists,
    safe_read_json, safe_write_json, get_file_stats, find_files_by_pattern,
    calculate_content_hash, extract_filename_parts
)
from .observers import get_event_publisher, publish_file_processed, publish_file_error


@dataclass
class FileOperationResult:
    """Result of a file operation."""
    success: bool
    file_path: str
    operation: str
    message: str = ""
    data: Optional[Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class BaseFileManager:
    """
    Base class for all file managers in the Komodo Documentation Library.
    
    Provides common functionality for JSON file operations, validation,
    and batch processing.
    """
    
    def __init__(self, base_directory: Union[str, Path] = ".", verbose: bool = True):
        self.base_directory = normalize_file_path(base_directory)
        self.verbose = verbose
        self.logger = get_logger(f"file-manager-{self.__class__.__name__.lower()}")
        self.event_publisher = get_event_publisher()
        
        # Ensure base directory exists
        ensure_directory_exists(self.base_directory)
        
        if self.verbose:
            self.logger.info(f"Initialized {self.__class__.__name__} with base directory: {self.base_directory}")
    
    def read_json_file(self, file_path: Union[str, Path], 
                      validate: bool = True) -> Dict[str, Any]:
        """
        Read a JSON file with error handling and optional validation.
        
        Args:
            file_path: Path to JSON file
            validate: Whether to validate the JSON structure
            
        Returns:
            Parsed JSON data
            
        Raises:
            FileOperationError: If file cannot be read or parsed
        """
        try:
            data = safe_read_json(file_path)
            
            if validate:
                self._validate_json_structure(data, file_path)
            
            publish_file_processed(self.__class__.__name__, str(file_path))
            return data
            
        except Exception as e:
            publish_file_error(self.__class__.__name__, str(file_path), str(e))
            raise
    
    def write_json_file(self, file_path: Union[str, Path], data: Dict[str, Any],
                       indent: int = 2, validate: bool = True,
                       create_backup: bool = False) -> None:
        """
        Write data to a JSON file with error handling and optional validation.
        
        Args:
            file_path: Path to write JSON file
            data: Data to write
            indent: JSON indentation
            validate: Whether to validate data before writing
            create_backup: Whether to create backup if file exists
            
        Raises:
            FileOperationError: If file cannot be written
        """
        try:
            if validate:
                self._validate_json_structure(data, file_path)
            
            # Create backup if requested
            normalized_path = normalize_file_path(file_path)
            if create_backup and normalized_path.exists():
                from .shared_utils import create_backup_path, safe_copy_file
                backup_path = create_backup_path(normalized_path)
                safe_copy_file(normalized_path, backup_path)
                
                if self.verbose:
                    self.logger.info(f"Created backup: {backup_path}")
            
            safe_write_json(file_path, data, indent=indent)
            publish_file_processed(self.__class__.__name__, str(file_path))
            
            if self.verbose:
                self.logger.success(f"Wrote JSON file: {file_path}")
                
        except Exception as e:
            publish_file_error(self.__class__.__name__, str(file_path), str(e))
            raise
    
    def batch_read_json_files(self, file_paths: List[Union[str, Path]],
                             validate: bool = True,
                             max_workers: int = 4) -> List[FileOperationResult]:
        """
        Read multiple JSON files concurrently.
        
        Args:
            file_paths: List of file paths to read
            validate: Whether to validate JSON structures
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of FileOperationResult objects
        """
        results = []
        
        def read_single_file(file_path: Path) -> FileOperationResult:
            try:
                data = self.read_json_file(file_path, validate=validate)
                return FileOperationResult(
                    success=True,
                    file_path=str(file_path),
                    operation="batch_read",
                    message="Successfully read JSON file",
                    data=data
                )
            except Exception as e:
                return FileOperationResult(
                    success=False,
                    file_path=str(file_path),
                    operation="batch_read",
                    message=str(e)
                )
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(read_single_file, normalize_file_path(fp)): fp 
                for fp in file_paths
            }
            
            # Collect results
            for future in as_completed(future_to_path):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    file_path = future_to_path[future]
                    results.append(FileOperationResult(
                        success=False,
                        file_path=str(file_path),
                        operation="batch_read",
                        message=f"Unexpected error: {e}"
                    ))
        
        return results
    
    def batch_write_json_files(self, file_data_pairs: List[Tuple[Union[str, Path], Dict[str, Any]]],
                              indent: int = 2, validate: bool = True,
                              max_workers: int = 4) -> List[FileOperationResult]:
        """
        Write multiple JSON files concurrently.
        
        Args:
            file_data_pairs: List of (file_path, data) tuples
            indent: JSON indentation
            validate: Whether to validate data before writing
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of FileOperationResult objects
        """
        results = []
        
        def write_single_file(file_path: Path, data: Dict[str, Any]) -> FileOperationResult:
            try:
                self.write_json_file(file_path, data, indent=indent, validate=validate)
                return FileOperationResult(
                    success=True,
                    file_path=str(file_path),
                    operation="batch_write",
                    message="Successfully wrote JSON file"
                )
            except Exception as e:
                return FileOperationResult(
                    success=False,
                    file_path=str(file_path),
                    operation="batch_write",
                    message=str(e)
                )
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(write_single_file, normalize_file_path(fp), data): fp 
                for fp, data in file_data_pairs
            }
            
            # Collect results
            for future in as_completed(future_to_path):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    file_path = future_to_path[future]
                    results.append(FileOperationResult(
                        success=False,
                        file_path=str(file_path),
                        operation="batch_write",
                        message=f"Unexpected error: {e}"
                    ))
        
        return results
    
    def scan_directory_for_json(self, directory: Union[str, Path],
                               pattern: str = "*.json",
                               recursive: bool = True) -> List[Path]:
        """
        Scan a directory for JSON files matching a pattern.
        
        Args:
            directory: Directory to scan
            pattern: File pattern to match
            recursive: Whether to search recursively
            
        Returns:
            List of matching JSON file paths
        """
        return find_files_by_pattern(directory, pattern, recursive)
    
    def get_file_statistics(self, file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        """
        Get comprehensive statistics about a list of files.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary with file statistics
        """
        stats = {
            'total_files': len(file_paths),
            'total_size': 0,
            'file_types': {},
            'avg_size': 0,
            'largest_file': None,
            'smallest_file': None,
            'newest_file': None,
            'oldest_file': None
        }
        
        if not file_paths:
            return stats
        
        file_info = []
        
        for file_path in file_paths:
            try:
                file_stats = get_file_stats(file_path)
                file_info.append((file_path, file_stats))
                
                # Update totals
                stats['total_size'] += file_stats['size']
                
                # Track file types
                ext = file_stats['extension']
                stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
                
            except Exception as e:
                if self.verbose:
                    self.logger.warning(f"Could not get stats for {file_path}: {e}")
        
        if file_info:
            # Calculate averages and extremes
            stats['avg_size'] = stats['total_size'] / len(file_info)
            
            # Find largest and smallest files
            largest = max(file_info, key=lambda x: x[1]['size'])
            smallest = min(file_info, key=lambda x: x[1]['size'])
            stats['largest_file'] = {'path': str(largest[0]), 'size': largest[1]['size']}
            stats['smallest_file'] = {'path': str(smallest[0]), 'size': smallest[1]['size']}
            
            # Find newest and oldest files
            newest = max(file_info, key=lambda x: x[1]['modified'])
            oldest = min(file_info, key=lambda x: x[1]['modified'])
            stats['newest_file'] = {'path': str(newest[0]), 'modified': newest[1]['modified']}
            stats['oldest_file'] = {'path': str(oldest[0]), 'modified': oldest[1]['modified']}
        
        return stats
    
    def validate_file_structure(self, file_path: Union[str, Path]) -> bool:
        """
        Validate the structure of a file.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic existence check
            validate_file_exists(file_path)
            
            # If it's a JSON file, validate JSON structure
            if str(file_path).endswith('.json'):
                data = safe_read_json(file_path)
                return self._validate_json_structure(data, file_path)
            
            return True
            
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"Validation failed for {file_path}: {e}")
            return False
    
    def _validate_json_structure(self, data: Dict[str, Any], 
                                file_path: Union[str, Path]) -> bool:
        """
        Validate JSON structure. Override in subclasses for specific validation.
        
        Args:
            data: JSON data to validate
            file_path: Path to file (for error messages)
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If validation fails
        """
        # Base validation - ensure it's a dictionary
        if not isinstance(data, dict):
            raise ValidationError(f"JSON file must contain an object, not {type(data).__name__}: {file_path}")
        
        return True
    
    def cleanup_temp_files(self, directory: Union[str, Path],
                          pattern: str = "*.tmp",
                          max_age_hours: int = 24) -> List[str]:
        """
        Clean up temporary files older than specified age.
        
        Args:
            directory: Directory to clean
            pattern: Pattern for temp files
            max_age_hours: Maximum age in hours
            
        Returns:
            List of cleaned up files
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        temp_files = find_files_by_pattern(directory, pattern, recursive=True)
        cleaned_files = []
        
        for temp_file in temp_files:
            try:
                file_stats = get_file_stats(temp_file)
                if file_stats['modified'] < cutoff_time:
                    temp_file.unlink()
                    cleaned_files.append(str(temp_file))
                    
                    if self.verbose:
                        self.logger.info(f"Cleaned up temp file: {temp_file}")
                        
            except Exception as e:
                if self.verbose:
                    self.logger.warning(f"Could not clean temp file {temp_file}: {e}")
        
        return cleaned_files
    
    def get_directory_summary(self, directory: Union[str, Path]) -> Dict[str, Any]:
        """
        Get a summary of a directory's contents.
        
        Args:
            directory: Directory to summarize
            
        Returns:
            Dictionary with directory summary
        """
        dir_path = normalize_file_path(directory)
        
        if not dir_path.exists() or not dir_path.is_dir():
            return {'error': f'Directory does not exist: {dir_path}'}
        
        # Scan for different file types
        json_files = find_files_by_pattern(dir_path, "*.json", recursive=True)
        mdx_files = find_files_by_pattern(dir_path, "*.mdx", recursive=True)
        yaml_files = find_files_by_pattern(dir_path, "*.yaml", recursive=True)
        yaml_files.extend(find_files_by_pattern(dir_path, "*.yml", recursive=True))
        
        # Count directories
        subdirs = [p for p in dir_path.rglob("*") if p.is_dir()]
        
        return {
            'directory': str(dir_path),
            'json_files': len(json_files),
            'mdx_files': len(mdx_files),
            'yaml_files': len(yaml_files),
            'subdirectories': len(subdirs),
            'total_files': len(json_files) + len(mdx_files) + len(yaml_files),
            'file_breakdown': {
                'json': [str(f) for f in json_files[:10]],  # First 10 for preview
                'mdx': [str(f) for f in mdx_files[:10]],
                'yaml': [str(f) for f in yaml_files[:10]]
            }
        } 