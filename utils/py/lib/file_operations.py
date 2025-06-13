#!/usr/bin/env python3
"""
Enhanced File Operations

File operations with batch processing, async support, and improved error handling.
Provides high-performance file management for the Komodo Documentation Library.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from datetime import datetime

from .logging_utils import get_logger, ProgressTracker
from .exceptions import FileOperationError, ValidationError, raise_file_not_found
from .validation import ValidationManager, ValidationLevel
from .cache import get_cache, cached
from .async_utils import AsyncFileProcessor


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


@dataclass
class BatchOperationResult:
    """Result of a batch file operation."""
    total_files: int
    successful: int
    failed: int
    results: List[FileOperationResult]
    duration_seconds: float
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        return (self.successful / self.total_files * 100) if self.total_files > 0 else 0


class ExampleFileManager:
    """
    Enhanced file manager with batch processing and validation.
    
    Provides high-performance file operations with proper error handling,
    validation, and caching support.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        self.logger = get_logger("file-manager")
        self.cache = get_cache()
        self.validator = ValidationManager(validation_level)
        self.async_processor = AsyncFileProcessor()
        
        # Performance settings
        self.batch_size = 50
        self.max_workers = 4
        
        self.logger.debug("ExampleFileManager initialized")
    
    def read_json_file(self, file_path: Union[str, Path], validate: bool = True) -> Dict[str, Any]:
        """
        Read and parse JSON file with optional validation.
        
        Args:
            file_path: Path to JSON file
            validate: Whether to validate JSON structure
            
        Returns:
            Parsed JSON data
            
        Raises:
            FileOperationError: If file cannot be read or parsed
            ValidationError: If validation fails
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise_file_not_found(str(file_path), "read")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ValidationError(
                    f"Invalid JSON in {file_path}",
                    {"parse_error": str(e), "file_path": str(file_path)}
                )
            
            # Optional validation
            if validate:
                validation_result = self.validator.validate_json(data)
                if not validation_result.is_valid:
                    self.logger.warning(f"JSON validation issues in {file_path}: {validation_result.errors}")
            
            self.logger.debug(f"Successfully read JSON file: {file_path}")
            return data
            
        except Exception as e:
            raise FileOperationError(
                f"Failed to read JSON file: {e}",
                str(file_path),
                "read",
                {"error": str(e)}
            )
    
    def write_json_file(self, file_path: Union[str, Path], data: Dict[str, Any], 
                       validate: bool = True, backup: bool = True) -> FileOperationResult:
        """
        Write JSON data to file with validation and optional backup.
        
        Args:
            file_path: Path to write to
            data: JSON data to write
            validate: Whether to validate data before writing
            backup: Whether to create backup of existing file
            
        Returns:
            File operation result
        """
        file_path = Path(file_path)
        
        try:
            # Validate data before writing
            if validate:
                validation_result = self.validator.validate_json(data)
                if not validation_result.is_valid:
                    return FileOperationResult(
                        success=False,
                        file_path=str(file_path),
                        operation="write",
                        message=f"Validation failed: {validation_result.errors}"
                    )
            
            # Create backup if file exists
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
                self.logger.debug(f"Created backup: {backup_path}")
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON with pretty formatting
            json_content = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
            
            self.logger.debug(f"Successfully wrote JSON file: {file_path}")
            
            return FileOperationResult(
                success=True,
                file_path=str(file_path),
                operation="write",
                message="File written successfully",
                data={"size_bytes": len(json_content)}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to write JSON file {file_path}: {e}")
            return FileOperationResult(
                success=False,
                file_path=str(file_path),
                operation="write",
                message=f"Write failed: {e}"
            )
    
    def batch_read_json_files(self, file_paths: List[Union[str, Path]], 
                             validate: bool = True, max_workers: Optional[int] = None) -> BatchOperationResult:
        """
        Read multiple JSON files in parallel with batch processing.
        
        Args:
            file_paths: List of file paths to read
            validate: Whether to validate each file
            max_workers: Maximum number of worker threads
            
        Returns:
            Batch operation result
        """
        start_time = datetime.now()
        max_workers = max_workers or self.max_workers
        results = []
        
        self.logger.info(f"Starting batch read of {len(file_paths)} JSON files")
        progress = ProgressTracker(len(file_paths), "Reading JSON files", self.logger)
        
        def read_single_file(file_path: Path) -> FileOperationResult:
            """Read a single JSON file and return result."""
            try:
                data = self.read_json_file(file_path, validate)
                progress.update()
                return FileOperationResult(
                    success=True,
                    file_path=str(file_path),
                    operation="batch_read",
                    message="Read successfully",
                    data=data
                )
            except Exception as e:
                progress.update()
                return FileOperationResult(
                    success=False,
                    file_path=str(file_path),
                    operation="batch_read",
                    message=str(e)
                )
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(read_single_file, Path(path)): path 
                for path in file_paths
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                result = future.result()
                results.append(result)
        
        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        duration = (datetime.now() - start_time).total_seconds()
        
        progress.finish(f"Completed: {successful}/{len(file_paths)} successful")
        
        batch_result = BatchOperationResult(
            total_files=len(file_paths),
            successful=successful,
            failed=failed,
            results=results,
            duration_seconds=duration
        )
        
        self.logger.stats("Batch Read Results", {
            "Total files": batch_result.total_files,
            "Successful": batch_result.successful,
            "Failed": batch_result.failed,
            "Success rate": f"{batch_result.success_rate:.1f}%",
            "Duration": f"{duration:.2f}s"
        })
        
        return batch_result
    
    def batch_write_json_files(self, file_data_pairs: List[Tuple[Union[str, Path], Dict[str, Any]]], 
                              validate: bool = True, backup: bool = True, 
                              max_workers: Optional[int] = None) -> BatchOperationResult:
        """
        Write multiple JSON files in parallel with batch processing.
        
        Args:
            file_data_pairs: List of (file_path, data) tuples
            validate: Whether to validate each file
            backup: Whether to create backups
            max_workers: Maximum number of worker threads
            
        Returns:
            Batch operation result
        """
        start_time = datetime.now()
        max_workers = max_workers or self.max_workers
        results = []
        
        self.logger.info(f"Starting batch write of {len(file_data_pairs)} JSON files")
        progress = ProgressTracker(len(file_data_pairs), "Writing JSON files", self.logger)
        
        def write_single_file(file_path: Path, data: Dict[str, Any]) -> FileOperationResult:
            """Write a single JSON file and return result."""
            result = self.write_json_file(file_path, data, validate, backup)
            progress.update()
            return result
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_path = {
                executor.submit(write_single_file, Path(path), data): path 
                for path, data in file_data_pairs
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_path):
                result = future.result()
                results.append(result)
        
        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        duration = (datetime.now() - start_time).total_seconds()
        
        progress.finish(f"Completed: {successful}/{len(file_data_pairs)} successful")
        
        batch_result = BatchOperationResult(
            total_files=len(file_data_pairs),
            successful=successful,
            failed=failed,
            results=results,
            duration_seconds=duration
        )
        
        self.logger.stats("Batch Write Results", {
            "Total files": batch_result.total_files,
            "Successful": batch_result.successful,
            "Failed": batch_result.failed,
            "Success rate": f"{batch_result.success_rate:.1f}%",
            "Duration": f"{duration:.2f}s"
        })
        
        return batch_result
    
    @cached(namespace="file_scan", ttl_seconds=3600)
    def scan_directory_for_json(self, directory: Union[str, Path], 
                               pattern: str = "*.json", recursive: bool = True) -> List[Path]:
        """
        Scan directory for JSON files with caching.
        
        Args:
            directory: Directory to scan
            pattern: File pattern to match
            recursive: Whether to scan recursively
            
        Returns:
            List of JSON file paths
        """
        directory = Path(directory)
        
        if not directory.exists():
            self.logger.warning(f"Directory does not exist: {directory}")
            return []
        
        if recursive:
            files = list(directory.rglob(pattern))
        else:
            files = list(directory.glob(pattern))
        
        # Filter out non-files and validate
        json_files = []
        for file_path in files:
            if file_path.is_file():
                # Quick validation check
                if self.validator.validate_json(file_path).is_valid:
                    json_files.append(file_path)
                else:
                    self.logger.debug(f"Skipping invalid JSON file: {file_path}")
        
        self.logger.debug(f"Found {len(json_files)} valid JSON files in {directory}")
        return json_files
    
    async def async_batch_read_json_files(self, file_paths: List[Union[str, Path]], 
                                         validate: bool = True) -> BatchOperationResult:
        """
        Asynchronously read multiple JSON files for better performance.
        
        Args:
            file_paths: List of file paths to read
            validate: Whether to validate each file
            
        Returns:
            Batch operation result
        """
        start_time = datetime.now()
        results = []
        
        self.logger.info(f"Starting async batch read of {len(file_paths)} JSON files")
        progress = ProgressTracker(len(file_paths), "Async reading JSON files", self.logger)
        
        async def read_single_file_async(file_path: Path) -> FileOperationResult:
            """Asynchronously read a single JSON file."""
            try:
                data = await self.async_processor.read_json_async(file_path)
                
                # Validate if requested
                if validate:
                    validation_result = self.validator.validate_json(data)
                    if not validation_result.is_valid:
                        return FileOperationResult(
                            success=False,
                            file_path=str(file_path),
                            operation="async_batch_read",
                            message=f"Validation failed: {validation_result.errors}"
                        )
                
                progress.update()
                return FileOperationResult(
                    success=True,
                    file_path=str(file_path),
                    operation="async_batch_read",
                    message="Read successfully",
                    data=data
                )
                
            except Exception as e:
                progress.update()
                return FileOperationResult(
                    success=False,
                    file_path=str(file_path),
                    operation="async_batch_read",
                    message=str(e)
                )
        
        # Process all files concurrently
        tasks = [read_single_file_async(Path(path)) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(FileOperationResult(
                    success=False,
                    file_path=str(file_paths[i]),
                    operation="async_batch_read",
                    message=str(result)
                ))
            else:
                processed_results.append(result)
        
        # Calculate statistics
        successful = sum(1 for r in processed_results if r.success)
        failed = len(processed_results) - successful
        duration = (datetime.now() - start_time).total_seconds()
        
        progress.finish(f"Completed: {successful}/{len(file_paths)} successful")
        
        batch_result = BatchOperationResult(
            total_files=len(file_paths),
            successful=successful,
            failed=failed,
            results=processed_results,
            duration_seconds=duration
        )
        
        self.logger.stats("Async Batch Read Results", {
            "Total files": batch_result.total_files,
            "Successful": batch_result.successful,
            "Failed": batch_result.failed,
            "Success rate": f"{batch_result.success_rate:.1f}%",
            "Duration": f"{duration:.2f}s"
        })
        
        return batch_result
    
    def cleanup_temp_files(self, directory: Union[str, Path], 
                          patterns: List[str] = None) -> FileOperationResult:
        """
        Clean up temporary files in directory.
        
        Args:
            directory: Directory to clean
            patterns: File patterns to match for deletion
            
        Returns:
            Cleanup operation result
        """
        if patterns is None:
            patterns = ["*.tmp", "*.temp", "*~", "*.backup"]
        
        directory = Path(directory)
        deleted_files = []
        errors = []
        
        if not directory.exists():
            return FileOperationResult(
                success=False,
                file_path=str(directory),
                operation="cleanup",
                message="Directory does not exist"
            )
        
        self.logger.info(f"Cleaning up temporary files in {directory}")
        
        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        self.logger.debug(f"Deleted: {file_path}")
                    except Exception as e:
                        errors.append(f"Failed to delete {file_path}: {e}")
                        self.logger.warning(f"Failed to delete {file_path}: {e}")
        
        success = len(errors) == 0
        message = f"Deleted {len(deleted_files)} files"
        if errors:
            message += f", {len(errors)} errors"
        
        self.logger.info(message)
        
        return FileOperationResult(
            success=success,
            file_path=str(directory),
            operation="cleanup",
            message=message,
            data={
                "deleted_files": deleted_files,
                "errors": errors
            }
        )
    
    def get_file_stats(self, file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        """
        Get statistics about a collection of files.
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary with file statistics
        """
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "file_types": {},
            "avg_size_bytes": 0,
            "largest_file": {"path": "", "size": 0},
            "smallest_file": {"path": "", "size": float('inf')},
            "errors": []
        }
        
        for file_path in file_paths:
            try:
                file_path = Path(file_path)
                if file_path.exists() and file_path.is_file():
                    size = file_path.stat().st_size
                    extension = file_path.suffix.lower()
                    
                    stats["total_files"] += 1
                    stats["total_size_bytes"] += size
                    
                    # Track file types
                    if extension in stats["file_types"]:
                        stats["file_types"][extension] += 1
                    else:
                        stats["file_types"][extension] = 1
                    
                    # Track largest file
                    if size > stats["largest_file"]["size"]:
                        stats["largest_file"] = {"path": str(file_path), "size": size}
                    
                    # Track smallest file
                    if size < stats["smallest_file"]["size"]:
                        stats["smallest_file"] = {"path": str(file_path), "size": size}
                        
            except Exception as e:
                stats["errors"].append(f"Error processing {file_path}: {e}")
        
        # Calculate average
        if stats["total_files"] > 0:
            stats["avg_size_bytes"] = stats["total_size_bytes"] / stats["total_files"]
        
        # Handle case where no files were processed
        if stats["smallest_file"]["size"] == float('inf'):
            stats["smallest_file"] = {"path": "", "size": 0}
        
        return stats 