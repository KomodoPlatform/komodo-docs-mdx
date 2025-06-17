#!/usr/bin/env python3
"""
Batch File Processor

Handles batch processing of files with progress tracking and error handling.
Optimized for processing large numbers of files efficiently.
"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Union, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .logging_utils import get_logger
from .file_types import FileInfo, OperationResult, BatchResult
from .file_utils import safe_read_json, safe_write_json


class BatchFileProcessor:
    """
    Handles batch processing of file operations.
    
    Focused on concurrent file processing without the bloat
    of the original unified_file_ops.py.
    """
    
    def __init__(self, max_workers: int = 4, verbose: bool = True):
        self.max_workers = max_workers
        self.verbose = verbose
        self.logger = get_logger("batch-processor")
    
    def batch_read_json(self, file_paths: List[Union[str, Path]]) -> BatchResult:
        """Read multiple JSON files concurrently."""
        start_time = datetime.now()
        results = []
        
        def read_single(file_path: Path) -> OperationResult:
            op_start = datetime.now()
            try:
                data = safe_read_json(file_path)
                duration = (datetime.now() - op_start).total_seconds() * 1000
                return OperationResult(
                    success=True,
                    file_path=str(file_path),
                    operation="read_json",
                    message="Read successful",
                    data=data,
                    duration_ms=duration
                )
            except Exception as e:
                duration = (datetime.now() - op_start).total_seconds() * 1000
                return OperationResult(
                    success=False,
                    file_path=str(file_path),
                    operation="read_json",
                    message=f"Read failed: {e}",
                    errors=[str(e)],
                    duration_ms=duration
                )
        
        # Process files concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(read_single, Path(fp)): fp for fp in file_paths
            }
            
            for future in as_completed(future_to_path):
                results.append(future.result())
        
        duration = (datetime.now() - start_time).total_seconds()
        successful = sum(1 for r in results if r.success)
        
        if self.verbose:
            self.logger.info(f"Batch read: {successful}/{len(file_paths)} files successful")
        
        return BatchResult(
            total=len(file_paths),
            successful=successful,
            failed=len(file_paths) - successful,
            results=results,
            duration_seconds=duration
        )
    
    def batch_write_json(self, file_data_pairs: List[Tuple[Union[str, Path], Dict[str, Any]]],
                         indent: int = 2) -> BatchResult:
        """Write multiple JSON files concurrently."""
        start_time = datetime.now()
        results = []
        
        def write_single(file_path: Path, data: Dict[str, Any]) -> OperationResult:
            op_start = datetime.now()
            try:
                safe_write_json(file_path, data, indent=indent)
                duration = (datetime.now() - op_start).total_seconds() * 1000
                return OperationResult(
                    success=True,
                    file_path=str(file_path),
                    operation="write_json",
                    message="Write successful",
                    data=data,
                    duration_ms=duration
                )
            except Exception as e:
                duration = (datetime.now() - op_start).total_seconds() * 1000
                return OperationResult(
                    success=False,
                    file_path=str(file_path),
                    operation="write_json",
                    message=f"Write failed: {e}",
                    errors=[str(e)],
                    duration_ms=duration
                )
        
        # Process files concurrently
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_pair = {
                executor.submit(write_single, Path(fp), data): (fp, data) 
                for fp, data in file_data_pairs
            }
            
            for future in as_completed(future_to_pair):
                results.append(future.result())
        
        duration = (datetime.now() - start_time).total_seconds()
        successful = sum(1 for r in results if r.success)
        
        if self.verbose:
            self.logger.info(f"Batch write: {successful}/{len(file_data_pairs)} files successful")
        
        return BatchResult(
            total=len(file_data_pairs),
            successful=successful,
            failed=len(file_data_pairs) - successful,
            results=results,
            duration_seconds=duration
        )


# Convenience functions
def batch_read_json_files(file_paths: List[Union[str, Path]], max_workers: int = 4) -> BatchResult:
    """Quick batch read of JSON files."""
    processor = BatchFileProcessor(max_workers=max_workers)
    return processor.batch_read_json(file_paths)


def batch_write_json_files(file_data_pairs: List[Tuple[Union[str, Path], Dict[str, Any]]], 
                          max_workers: int = 4, indent: int = 2) -> BatchResult:
    """Quick batch write of JSON files."""
    processor = BatchFileProcessor(max_workers=max_workers)
    return processor.batch_write_json(file_data_pairs, indent) 