#!/usr/bin/env python3
"""
File Types and Data Structures

Core data structures for file operations, moved from unified_file_ops.py
for better organization and to eliminate bloated files.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..constants.enums import FileType


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
        """Create FileInfo from a file path."""
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
        """Calculate success rate as percentage."""
        return (self.successful / self.total * 100) if self.total > 0 else 0 