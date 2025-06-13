#!/usr/bin/env python3
"""
Async Utilities

Provides async/await support for I/O-bound operations in the Komodo Documentation Library.
Includes concurrent processing, file operations, and batch processing utilities.
"""

import asyncio
import aiofiles
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import functools

from .config import get_config
from .logging_utils import get_logger, ProgressTracker
from .cache import get_cache, cached


class AsyncFileProcessor:
    """
    Async file processing utilities for the Komodo Documentation Library.
    
    Provides high-performance file operations using async/await and
    concurrent processing for batch operations.
    """
    
    def __init__(self, max_workers: Optional[int] = None):
        self.config = get_config()
        self.logger = get_logger("async-processor")
        self.max_workers = max_workers or self.config.processing.max_workers
        
        # Thread pool for CPU-bound operations
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
    
    async def read_file_async(self, file_path: Union[str, Path]) -> str:
        """Read file content asynchronously."""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return content
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            raise
    
    async def read_json_async(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Read and parse JSON file asynchronously."""
        content = await self.read_file_async(file_path)
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            raise
    
    async def write_file_async(self, file_path: Union[str, Path], content: str) -> None:
        """Write file content asynchronously."""
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
                
            self.logger.debug(f"Written file: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to write file {file_path}: {e}")
            raise
    
    async def write_json_async(self, file_path: Union[str, Path], data: Dict[str, Any]) -> None:
        """Write JSON data to file asynchronously."""
        content = json.dumps(data, indent=2, ensure_ascii=False)
        await self.write_file_async(file_path, content)
    
    async def scan_directory_async(self, directory: Union[str, Path], 
                                  pattern: str = "*") -> List[Path]:
        """Scan directory for files matching pattern asynchronously."""
        def _scan():
            dir_path = Path(directory)
            if not dir_path.exists():
                return []
            return list(dir_path.rglob(pattern))
        
        # Run in thread pool since Path.rglob is not async
        loop = asyncio.get_event_loop()
        files = await loop.run_in_executor(self.thread_pool, _scan)
        
        self.logger.debug(f"Scanned {directory}: found {len(files)} files")
        return files
    
    async def process_files_batch(self, file_paths: List[Path], 
                                 processor_func: Callable,
                                 batch_size: Optional[int] = None) -> List[Any]:
        """Process multiple files in batches asynchronously."""
        batch_size = batch_size or self.config.processing.batch_size
        results = []
        
        self.logger.info(f"Processing {len(file_paths)} files in batches of {batch_size}")
        
        # Create progress tracker
        progress = ProgressTracker(len(file_paths), "File Processing", self.logger)
        
        # Process in batches
        for i in range(0, len(file_paths), batch_size):
            batch = file_paths[i:i + batch_size]
            
            # Process batch concurrently
            batch_tasks = []
            for file_path in batch:
                if asyncio.iscoroutinefunction(processor_func):
                    task = processor_func(file_path)
                else:
                    # Wrap sync function for async execution
                    loop = asyncio.get_event_loop()
                    task = loop.run_in_executor(self.thread_pool, processor_func, file_path)
                batch_tasks.append(task)
            
            # Wait for batch completion
            try:
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                
                # Handle results and exceptions
                for j, result in enumerate(batch_results):
                    if isinstance(result, Exception):
                        if self.config.processing.continue_on_error:
                            self.logger.warning(f"Error processing {batch[j]}: {result}")
                            results.append(None)
                        else:
                            raise result
                    else:
                        results.append(result)
                    
                    progress.update()
                    
            except Exception as e:
                if not self.config.processing.continue_on_error:
                    self.logger.error(f"Batch processing failed: {e}")
                    raise
        
        progress.finish()
        return results
    
    async def concurrent_map(self, func: Callable, items: List[Any], 
                           max_concurrent: Optional[int] = None) -> List[Any]:
        """Apply function to items concurrently with controlled concurrency."""
        max_concurrent = max_concurrent or self.max_workers
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def _process_item(item):
            async with semaphore:
                if asyncio.iscoroutinefunction(func):
                    return await func(item)
                else:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(self.thread_pool, func, item)
        
        # Create all tasks
        tasks = [_process_item(item) for item in items]
        
        # Execute with progress tracking
        progress = ProgressTracker(len(tasks), "Concurrent Processing", self.logger)
        results = []
        
        for completed_task in asyncio.as_completed(tasks):
            try:
                result = await completed_task
                results.append(result)
                progress.update()
            except Exception as e:
                if self.config.processing.continue_on_error:
                    self.logger.warning(f"Task failed: {e}")
                    results.append(None)
                    progress.update()
                else:
                    raise
        
        progress.finish()
        return results
    
    def __del__(self):
        """Clean up thread pool."""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)


class AsyncMethodProcessor:
    """
    Async processing utilities specifically for API method operations.
    
    Handles concurrent scanning, mapping, and processing of method-related files.
    """
    
    def __init__(self):
        self.file_processor = AsyncFileProcessor()
        self.logger = get_logger("method-processor")
        self.cache = get_cache()
    
    async def scan_mdx_files_async(self, directories: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Scan MDX files asynchronously across multiple directories."""
        results = {}
        
        for version, directory in directories.items():
            self.logger.info(f"Scanning MDX files for {version}")
            
            # Get all MDX files in directory
            mdx_files = await self.file_processor.scan_directory_async(directory, "*.mdx")
            
            # Process files concurrently
            version_results = await self._process_mdx_files(mdx_files)
            results[version] = version_results
        
        return results
    
    async def _process_mdx_files(self, mdx_files: List[Path]) -> Dict[str, str]:
        """Process MDX files to extract method mappings."""
        async def extract_method_from_mdx(file_path: Path) -> Tuple[str, str]:
            try:
                content = await self.file_processor.read_file_async(file_path)
                method_name = self._extract_method_name_from_mdx(content)
                return method_name, str(file_path) if method_name else None
            except Exception as e:
                self.logger.warning(f"Failed to process MDX file {file_path}: {e}")
                return None, None
        
        # Process all files concurrently
        results = await self.file_processor.concurrent_map(extract_method_from_mdx, mdx_files)
        
        # Filter and format results
        method_mappings = {}
        for method_name, file_path in results:
            if method_name and file_path:
                method_mappings[method_name] = file_path
        
        return method_mappings
    
    def _extract_method_name_from_mdx(self, content: str) -> Optional[str]:
        """Extract method name from MDX content."""
        import re
        
        # Look for method heading pattern
        method_pattern = r'##\s+([a-zA-Z0-9_:.-]+)\s*\{\{'
        match = re.search(method_pattern, content)
        
        if match:
            return match.group(1).strip()
        
        return None
    
    async def scan_yaml_files_async(self, directories: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        """Scan YAML files asynchronously across multiple directories."""
        results = {}
        
        for version, directory in directories.items():
            self.logger.info(f"Scanning YAML files for {version}")
            
            # Get all YAML files
            yaml_files = await self.file_processor.scan_directory_async(
                directory, "*.yaml"
            ) + await self.file_processor.scan_directory_async(
                directory, "*.yml"
            )
            
            # Process files concurrently
            version_results = await self._process_yaml_files(yaml_files, version)
            results[version] = version_results
        
        return results
    
    async def _process_yaml_files(self, yaml_files: List[Path], version: str) -> Dict[str, str]:
        """Process YAML files to extract method mappings."""
        async def extract_method_from_yaml(file_path: Path) -> Tuple[str, str]:
            try:
                method_name = self._extract_method_name_from_filename(file_path.name, version)
                return method_name, str(file_path) if method_name else None
            except Exception as e:
                self.logger.warning(f"Failed to process YAML file {file_path}: {e}")
                return None, None
        
        # Process all files concurrently
        results = await self.file_processor.concurrent_map(extract_method_from_yaml, yaml_files)
        
        # Filter and format results
        method_mappings = {}
        for method_name, file_path in results:
            if method_name and file_path:
                method_mappings[method_name] = file_path
        
        return method_mappings
    
    def _extract_method_name_from_filename(self, filename: str, version: str) -> Optional[str]:
        """Extract method name from YAML filename."""
        # Remove extension
        name = filename.replace('.yaml', '').replace('.yml', '')
        
        # Convert to method format based on version
        if version == 'v1':
            return name
        elif version == 'v2':
            # Convert dashes to double colons for v2
            return name.replace('-', '::')
        
        return name
    
    async def scan_json_examples_async(self, directories: Dict[str, str]) -> Dict[str, Dict[str, Tuple[str, int]]]:
        """Scan JSON example files asynchronously."""
        results = {}
        
        for version, directory in directories.items():
            self.logger.info(f"Scanning JSON examples for {version}")
            
            # Get all JSON files
            json_files = await self.file_processor.scan_directory_async(directory, "*.json")
            
            # Process files concurrently
            version_results = await self._process_json_examples(json_files)
            results[version] = version_results
        
        return results
    
    async def _process_json_examples(self, json_files: List[Path]) -> Dict[str, Tuple[str, int]]:
        """Process JSON example files to count examples per method."""
        method_counts = {}
        
        async def process_json_file(file_path: Path) -> Tuple[str, str]:
            try:
                data = await self.file_processor.read_json_async(file_path)
                method_name = data.get('method')
                return method_name, str(file_path) if method_name else None
            except Exception as e:
                self.logger.warning(f"Failed to process JSON file {file_path}: {e}")
                return None, None
        
        # Process all files concurrently
        results = await self.file_processor.concurrent_map(process_json_file, json_files)
        
        # Count examples per method
        for method_name, file_path in results:
            if method_name and file_path:
                if method_name not in method_counts:
                    method_counts[method_name] = (file_path, 0)
                
                # Increment count
                existing_path, count = method_counts[method_name]
                method_counts[method_name] = (existing_path, count + 1)
        
        return method_counts


# Async decorator for caching
def async_cached(namespace: str, ttl_seconds: Optional[int] = None):
    """Decorator for caching async function results."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = get_cache()
            
            cache_key = {
                'args': args,
                'kwargs': kwargs,
                'func_name': func.__name__
            }
            
            # Check cache
            cached_result = cache.get(namespace, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute async function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache.set(namespace, cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


# Convenience functions
async def run_with_progress(coro, description: str = "Operation"):
    """Run coroutine with progress logging."""
    logger = get_logger()
    logger.progress(f"Starting {description}")
    
    try:
        result = await coro
        logger.success(f"Completed {description}")
        return result
    except Exception as e:
        logger.error(f"Failed {description}: {e}")
        raise


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro) 