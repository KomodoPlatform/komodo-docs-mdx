#!/usr/bin/env python3
"""
Unified File Operations: 

Provides all JSON I/O, directory operations, scanning, and batch processing.
"""

import json
import os
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

from .logging_utils import get_logger


class FileType(Enum):
    """Supported file types."""
    JSON = "json"
    YAML = "yaml"
    MDX = "mdx"
    TXT = "txt"
    UNKNOWN = "unknown"


class ValidationLevel(Enum):
    """Validation levels for file operations."""
    NONE = "none"
    BASIC = "basic"
    STRICT = "strict"


@dataclass
class FileInfo:
    """Information about a file."""
    path: Path
    size: int
    modified: datetime
    file_type: FileType
    exists: bool = True
    
    @classmethod
    def from_path(cls, path: Union[str, Path]) -> 'FileInfo':
        path = Path(path)
        if not path.exists():
            return cls(
                path=path,
                size=0,
                modified=datetime.min,
                file_type=FileType.UNKNOWN,
                exists=False
            )
        
        stat = path.stat()
        file_type = FileType.UNKNOWN
        
        if path.suffix.lower() == '.json':
            file_type = FileType.JSON
        elif path.suffix.lower() in ['.yaml', '.yml']:
            file_type = FileType.YAML
        elif path.suffix.lower() == '.mdx':
            file_type = FileType.MDX
        elif path.suffix.lower() == '.txt':
            file_type = FileType.TXT
        
        return cls(
            path=path,
            size=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
            file_type=file_type
        )


@dataclass
class OperationResult:
    """Result of a file operation."""
    success: bool
    file_path: str
    operation: str
    message: str = ""
    data: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: Optional[float] = None


@dataclass
class BatchResult:
    """Result of a batch operation."""
    total: int
    successful: int
    failed: int
    results: List[OperationResult]
    duration_seconds: float
    
    @property
    def success_rate(self) -> float:
        return (self.successful / self.total * 100) if self.total > 0 else 0


class JSONValidator:
    """Simple JSON structure validator."""
    
    @staticmethod
    def is_valid_json_string(content: str) -> Tuple[bool, Optional[str]]:
        """Check if string is valid JSON."""
        try:
            json.loads(content)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)
    
    @staticmethod
    def validate_structure(data: Any, expected_keys: List[str] = None) -> Tuple[bool, List[str]]:
        """Basic structure validation."""
        errors = []
        
        if not isinstance(data, dict):
            errors.append(f"Expected object, got {type(data).__name__}")
            return False, errors
        
        if expected_keys:
            missing = [key for key in expected_keys if key not in data]
            if missing:
                errors.append(f"Missing required keys: {missing}")
        
        return len(errors) == 0, errors


class UnifiedFileOperations:
    """
    Unified file operations system.
    
    Consolidates all file I/O, scanning, and batch operations
    without circular dependencies.
    """
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.BASIC, 
                 max_workers: int = 4, verbose: bool = True):
        self.validation_level = validation_level
        self.max_workers = max_workers
        self.verbose = verbose
        self.logger = get_logger("unified-file-ops")
        self.validator = JSONValidator()
    
    # =============================================================================
    # CORE JSON OPERATIONS
    # =============================================================================
    
    def read_json(self, file_path: Union[str, Path], 
                  validate: bool = None) -> Dict[str, Any]:
        """Read and parse JSON file."""
        file_path = Path(file_path)
        validate = validate if validate is not None else (self.validation_level != ValidationLevel.NONE)
        
        if not file_path.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validate JSON syntax if requested
            if validate:
                is_valid, error = self.validator.is_valid_json_string(content)
                if not is_valid:
                    raise ValueError(f"Invalid JSON in {file_path}: {error}")
            
            data = json.loads(content)
            
            if self.verbose:
                self.logger.debug(f"Read JSON file: {file_path} ({len(content)} chars)")
            
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to read JSON file {file_path}: {e}")
            raise
    
    def write_json(self, file_path: Union[str, Path], data: Dict[str, Any],
                   indent: int = 2, backup: bool = False, 
                   validate: bool = None) -> OperationResult:
        """Write data to JSON file."""
        start_time = datetime.now()
        file_path = Path(file_path)
        validate = validate if validate is not None else (self.validation_level == ValidationLevel.STRICT)
        
        try:
            # Validate data structure if requested
            if validate:
                is_valid, errors = self.validator.validate_structure(data)
                if not is_valid:
                    return OperationResult(
                        success=False,
                        file_path=str(file_path),
                        operation="write_json",
                        message="Validation failed",
                        errors=errors
                    )
            
            # Create backup if requested
            if backup and file_path.exists():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                shutil.copy2(file_path, backup_path)
                if self.verbose:
                    self.logger.debug(f"Created backup: {backup_path}")
            
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write JSON
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False, sort_keys=True)
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            if self.verbose:
                self.logger.debug(f"Wrote JSON file: {file_path}")
            
            return OperationResult(
                success=True,
                file_path=str(file_path),
                operation="write_json",
                message="File written successfully",
                duration_ms=duration
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Failed to write JSON file {file_path}: {e}")
            
            return OperationResult(
                success=False,
                file_path=str(file_path),
                operation="write_json",
                message=f"Write failed: {e}",
                errors=[str(e)],
                duration_ms=duration
            )
    
    # =============================================================================
    # BATCH OPERATIONS
    # =============================================================================
    
    def batch_read_json(self, file_paths: List[Union[str, Path]], 
                        validate: bool = None) -> BatchResult:
        """Read multiple JSON files in parallel."""
        start_time = datetime.now()
        validate = validate if validate is not None else (self.validation_level != ValidationLevel.NONE)
        
        def read_single(file_path: Path) -> OperationResult:
            try:
                data = self.read_json(file_path, validate=validate)
                return OperationResult(
                    success=True,
                    file_path=str(file_path),
                    operation="batch_read_json",
                    message="Successfully read",
                    data=data
                )
            except Exception as e:
                return OperationResult(
                    success=False,
                    file_path=str(file_path),
                    operation="batch_read_json",
                    message=str(e),
                    errors=[str(e)]
                )
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(read_single, Path(fp)): fp for fp in file_paths}
            
            for future in as_completed(futures):
                results.append(future.result())
        
        successful = sum(1 for r in results if r.success)
        duration = (datetime.now() - start_time).total_seconds()
        
        return BatchResult(
            total=len(file_paths),
            successful=successful,
            failed=len(results) - successful,
            results=results,
            duration_seconds=duration
        )
    
    def batch_write_json(self, file_data_pairs: List[Tuple[Union[str, Path], Dict[str, Any]]],
                         indent: int = 2, backup: bool = False, 
                         validate: bool = None) -> BatchResult:
        """Write multiple JSON files in parallel."""
        start_time = datetime.now()
        
        def write_single(file_path: Path, data: Dict[str, Any]) -> OperationResult:
            return self.write_json(file_path, data, indent=indent, backup=backup, validate=validate)
        
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(write_single, Path(fp), data): fp 
                for fp, data in file_data_pairs
            }
            
            for future in as_completed(futures):
                results.append(future.result())
        
        successful = sum(1 for r in results if r.success)
        duration = (datetime.now() - start_time).total_seconds()
        
        return BatchResult(
            total=len(file_data_pairs),
            successful=successful,
            failed=len(results) - successful,
            results=results,
            duration_seconds=duration
        )
    
    # =============================================================================
    # DIRECTORY OPERATIONS
    # =============================================================================
    
    def ensure_directory(self, directory: Union[str, Path]) -> bool:
        """Ensure directory exists."""
        try:
            Path(directory).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Failed to create directory {directory}: {e}")
            return False
    
    def scan_files(self, directory: Union[str, Path], pattern: str = "*",
                   file_type: Optional[FileType] = None, 
                   recursive: bool = True) -> List[FileInfo]:
        """Scan directory for files matching criteria."""
        directory = Path(directory)
        
        if not directory.exists():
            if self.verbose:
                self.logger.warning(f"Directory does not exist: {directory}")
            return []
        
        try:
            if recursive:
                files = list(directory.rglob(pattern))
            else:
                files = list(directory.glob(pattern))
            
            # Filter to actual files
            files = [f for f in files if f.is_file()]
            
            # Get file info
            file_infos = [FileInfo.from_path(f) for f in files]
            
            # Filter by file type if specified
            if file_type:
                file_infos = [fi for fi in file_infos if fi.file_type == file_type]
            
            return file_infos
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error scanning directory {directory}: {e}")
            return []
    
    def scan_json_files(self, directory: Union[str, Path], 
                        recursive: bool = True) -> List[FileInfo]:
        """Scan for JSON files specifically."""
        return self.scan_files(directory, "*.json", FileType.JSON, recursive)
    
    # =============================================================================
    # FILE UTILITIES
    # =============================================================================
    
    def copy_file(self, src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """Copy file from source to destination."""
        try:
            dst_path = Path(dst)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return True
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Failed to copy {src} to {dst}: {e}")
            return False
    
    def move_file(self, src: Union[str, Path], dst: Union[str, Path]) -> bool:
        """Move file from source to destination."""
        try:
            dst_path = Path(dst)
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            return True
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Failed to move {src} to {dst}: {e}")
            return False
    
    def delete_file(self, file_path: Union[str, Path]) -> bool:
        """Delete a file."""
        try:
            Path(file_path).unlink()
            return True
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Failed to delete {file_path}: {e}")
            return False
    
    def get_file_stats(self, file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        """Get comprehensive statistics about files."""
        file_infos = [FileInfo.from_path(fp) for fp in file_paths]
        existing_files = [fi for fi in file_infos if fi.exists]
        
        if not existing_files:
            return {
                'total_files': len(file_paths),
                'existing_files': 0,
                'total_size': 0,
                'file_types': {},
                'avg_size': 0
            }
        
        total_size = sum(fi.size for fi in existing_files)
        file_types = {}
        
        for fi in existing_files:
            file_types[fi.file_type.value] = file_types.get(fi.file_type.value, 0) + 1
        
        largest = max(existing_files, key=lambda x: x.size)
        smallest = min(existing_files, key=lambda x: x.size)
        newest = max(existing_files, key=lambda x: x.modified)
        oldest = min(existing_files, key=lambda x: x.modified)
        
        return {
            'total_files': len(file_paths),
            'existing_files': len(existing_files),
            'total_size': total_size,
            'avg_size': total_size / len(existing_files),
            'file_types': file_types,
            'largest_file': {'path': str(largest.path), 'size': largest.size},
            'smallest_file': {'path': str(smallest.path), 'size': smallest.size},
            'newest_file': {'path': str(newest.path), 'modified': newest.modified},
            'oldest_file': {'path': str(oldest.path), 'modified': oldest.modified}
        }
    
    def cleanup_temp_files(self, directory: Union[str, Path],
                          patterns: List[str] = None,
                          max_age_hours: int = 24) -> OperationResult:
        """Clean up temporary files."""
        if patterns is None:
            patterns = ["*.tmp", "*.temp", "*~", "*.backup"]
        
        directory = Path(directory)
        if not directory.exists():
            return OperationResult(
                success=False,
                file_path=str(directory),
                operation="cleanup",
                message="Directory does not exist"
            )
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        deleted_files = []
        errors = []
        
        for pattern in patterns:
            for file_path in directory.rglob(pattern):
                if file_path.is_file():
                    try:
                        file_info = FileInfo.from_path(file_path)
                        if file_info.modified < cutoff_time:
                            file_path.unlink()
                            deleted_files.append(str(file_path))
                    except Exception as e:
                        errors.append(f"Failed to delete {file_path}: {e}")
        
        return OperationResult(
            success=len(errors) == 0,
            file_path=str(directory),
            operation="cleanup",
            message=f"Deleted {len(deleted_files)} files",
            data={'deleted_files': deleted_files},
            errors=errors
        )


# =============================================================================
# SPECIALIZED OPERATIONS FOR POSTMAN
# =============================================================================

class PostmanFileOperations(UnifiedFileOperations):
    """Specialized file operations for Postman collections and environments."""
    
    def __init__(self, collections_dir: str = "../../postman/collections",
                 environments_dir: str = "../../postman/environments", **kwargs):
        super().__init__(**kwargs)
        self.collections_dir = Path(collections_dir)
        self.environments_dir = Path(environments_dir)
        
        # Ensure directories exist
        self.ensure_directory(self.collections_dir)
        self.ensure_directory(self.environments_dir)
    
    def save_collection(self, collection: Dict[str, Any], version: str) -> OperationResult:
        """Save Postman collection."""
        filename = f"kdf-{version}-postman-collection.json"
        file_path = self.collections_dir / filename
        
        # Validate collection structure
        is_valid, errors = self._validate_collection(collection)
        if not is_valid:
            return OperationResult(
                success=False,
                file_path=str(file_path),
                operation="save_collection",
                message="Collection validation failed",
                errors=errors
            )
        
        return self.write_json(file_path, collection)
    
    def save_environment(self, environment: Dict[str, Any], version: str) -> OperationResult:
        """Save Postman environment."""
        filename = f"kdf-{version}-environment.json"
        file_path = self.environments_dir / filename
        
        # Validate environment structure
        is_valid, errors = self._validate_environment(environment)
        if not is_valid:
            return OperationResult(
                success=False,
                file_path=str(file_path),
                operation="save_environment",
                message="Environment validation failed",
                errors=errors
            )
        
        return self.write_json(file_path, environment)
    
    def load_collection(self, version: str) -> Dict[str, Any]:
        """Load Postman collection."""
        filename = f"kdf-{version}-postman-collection.json"
        file_path = self.collections_dir / filename
        return self.read_json(file_path)
    
    def load_environment(self, version: str) -> Dict[str, Any]:
        """Load Postman environment."""
        filename = f"kdf-{version}-environment.json"
        file_path = self.environments_dir / filename
        return self.read_json(file_path)
    
    def list_collections(self) -> Dict[str, str]:
        """List all collections."""
        collections = {}
        for file_info in self.scan_json_files(self.collections_dir, recursive=False):
            filename = file_info.path.stem
            if filename.startswith("kdf-") and filename.endswith("-postman-collection"):
                # Extract version
                parts = filename.split('-')
                if len(parts) >= 3:
                    version = parts[1]
                    collections[version] = str(file_info.path)
        return collections
    
    def list_environments(self) -> Dict[str, str]:
        """List all environments."""
        environments = {}
        for file_info in self.scan_json_files(self.environments_dir, recursive=False):
            filename = file_info.path.stem
            if filename.startswith("kdf-") and filename.endswith("-environment"):
                # Extract version
                parts = filename.split('-')
                if len(parts) >= 3:
                    version = parts[1]
                    environments[version] = str(file_info.path)
        return environments
    
    def _validate_collection(self, collection: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate Postman collection structure."""
        errors = []
        
        required_fields = ['info', 'item']
        for field in required_fields:
            if field not in collection:
                errors.append(f"Missing required field: {field}")
        
        if 'info' in collection:
            info = collection['info']
            required_info_fields = ['name', 'schema']
            for field in required_info_fields:
                if field not in info:
                    errors.append(f"Missing info field: {field}")
        
        if 'item' in collection and not isinstance(collection['item'], list):
            errors.append("'item' field must be a list")
        
        return len(errors) == 0, errors
    
    def _validate_environment(self, environment: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate Postman environment structure."""
        errors = []
        
        required_fields = ['id', 'name', 'values']
        for field in required_fields:
            if field not in environment:
                errors.append(f"Missing required field: {field}")
        
        if 'values' in environment and not isinstance(environment['values'], list):
            errors.append("'values' field must be a list")
        
        if 'values' in environment:
            for i, var in enumerate(environment['values']):
                if not isinstance(var, dict) or 'key' not in var:
                    errors.append(f"Variable {i} must have a 'key' field")
        
        return len(errors) == 0, errors


# =============================================================================
# GLOBAL INSTANCES & CONVENIENCE FUNCTIONS
# =============================================================================

_unified_ops = None
_postman_ops = None

def get_file_ops() -> UnifiedFileOperations:
    """Get global unified file operations instance."""
    global _unified_ops
    if _unified_ops is None:
        _unified_ops = UnifiedFileOperations()
    return _unified_ops

def get_postman_ops() -> PostmanFileOperations:
    """Get global Postman file operations instance."""
    global _postman_ops
    if _postman_ops is None:
        _postman_ops = PostmanFileOperations()
    return _postman_ops

# Convenience functions
def read_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    return get_file_ops().read_json(file_path)

def write_json(file_path: Union[str, Path], data: Dict[str, Any], **kwargs) -> OperationResult:
    return get_file_ops().write_json(file_path, data, **kwargs)

def ensure_dir(directory: Union[str, Path]) -> bool:
    return get_file_ops().ensure_directory(directory)

def scan_json_files(directory: Union[str, Path], recursive: bool = True) -> List[FileInfo]:
    return get_file_ops().scan_json_files(directory, recursive) 