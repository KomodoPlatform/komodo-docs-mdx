#!/usr/bin/env python3
"""
Postman Manager

Complete Postman operations manager following standard architecture.
Orchestrates collection generation, file management, and reporting.
Replaces the pipeline architecture from postman_consolidated.py.
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

from ..utils.file_types import OperationResult
from ..utils.file_utils import safe_read_json, safe_write_json, ensure_directory_exists
from ..utils.logging_utils import get_logger
from ..constants.config import get_config


class PostmanFileManager:
    """
    Manages file operations for Postman collections and environments.
    
    Provides validation, loading, saving, and management functionality with
    structured error handling using OperationResult.
    """
    
    def __init__(self, collections_dir: str = "../../postman/collections",
                 environments_dir: str = "../../postman/environments", 
                 verbose: bool = True):
        self.collections_dir = Path(collections_dir)
        self.environments_dir = Path(environments_dir)
        self.verbose = verbose
        self.logger = get_logger("postman-file-manager")
        
        # Ensure directories exist
        ensure_directory_exists(self.collections_dir)
        ensure_directory_exists(self.environments_dir)
    
    def save_collection(self, collection: Dict[str, Any], version: str) -> OperationResult:
        """Save Postman collection."""
        filename = f"KDF_API_{version.upper()}_Collection.postman_collection.json"
        filepath = self.collections_dir / filename
        
        # Validate collection structure
        is_valid, errors = self.validate_collection_structure(collection)
        if not is_valid:
            return OperationResult(
                success=False,
                file_path=str(filepath),
                operation="save_collection",
                message="Collection validation failed",
                errors=errors
            )
        
        try:
            safe_write_json(filepath, collection)
            
            if self.verbose:
                self.logger.info(f"Saved collection: {filename}")
            
            return OperationResult(
                success=True,
                file_path=str(filepath),
                operation="save_collection",
                message="Collection saved successfully",
                data=collection
            )
        except Exception as e:
            return OperationResult(
                success=False,
                file_path=str(filepath),
                operation="save_collection",
                message=f"Save failed: {e}",
                errors=[str(e)]
            )
    
    def save_environment(self, environment: Dict[str, Any], version: str) -> OperationResult:
        """Save Postman environment."""
        filename = f"KDF_API_{version.upper()}_Environment.postman_environment.json"
        filepath = self.environments_dir / filename
        
        # Validate environment structure
        is_valid, errors = self.validate_environment_structure(environment)
        if not is_valid:
            return OperationResult(
                success=False,
                file_path=str(filepath),
                operation="save_environment",
                message="Environment validation failed",
                errors=errors
            )
        
        try:
            safe_write_json(filepath, environment)
            
            if self.verbose:
                self.logger.info(f"Saved environment: {filename}")
            
            return OperationResult(
                success=True,
                file_path=str(filepath),
                operation="save_environment",
                message="Environment saved successfully",
                data=environment
            )
        except Exception as e:
            return OperationResult(
                success=False,
                file_path=str(filepath),
                operation="save_environment",
                message=f"Save failed: {e}",
                errors=[str(e)]
            )
    
    def load_collection(self, version: str) -> Dict[str, Any]:
        """Load Postman collection."""
        filename = f"KDF_API_{version.upper()}_Collection.postman_collection.json"
        filepath = self.collections_dir / filename
        return safe_read_json(filepath)
    
    def load_environment(self, version: str) -> Dict[str, Any]:
        """Load Postman environment."""
        filename = f"KDF_API_{version.upper()}_Environment.postman_environment.json"
        filepath = self.environments_dir / filename
        return safe_read_json(filepath)
    
    def list_collections(self) -> Dict[str, str]:
        """List available collections."""
        collections = {}
        for file_path in self.collections_dir.glob("*.postman_collection.json"):
            # Extract version from filename
            name_parts = file_path.stem.split('_')
            if len(name_parts) >= 3:
                version = name_parts[2].lower()
                collections[version] = str(file_path)
        return collections
    
    def list_environments(self) -> Dict[str, str]:
        """List available environments."""
        environments = {}
        for file_path in self.environments_dir.glob("*.postman_environment.json"):
            # Extract version from filename
            name_parts = file_path.stem.split('_')
            if len(name_parts) >= 3:
                version = name_parts[2].lower()
                environments[version] = str(file_path)
        return environments
    
    def validate_collection_structure(self, collection: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate Postman collection structure."""
        errors = []
        
        # Check required fields
        required_fields = ['info', 'item']
        for field in required_fields:
            if field not in collection:
                errors.append(f"Missing required field: {field}")
        
        # Validate info section
        if 'info' in collection:
            info = collection['info']
            info_required = ['name', 'schema']
            for field in info_required:
                if field not in info:
                    errors.append(f"Missing required info field: {field}")
        
        # Validate items
        if 'item' in collection:
            if not isinstance(collection['item'], list):
                errors.append("Collection items must be a list")
        
        return len(errors) == 0, errors
    
    def validate_environment_structure(self, environment: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate Postman environment structure."""
        errors = []
        
        # Check required fields
        required_fields = ['id', 'name', 'values']
        for field in required_fields:
            if field not in environment:
                errors.append(f"Missing required field: {field}")
        
        # Validate values
        if 'values' in environment:
            values = environment['values']
            if not isinstance(values, list):
                errors.append("Environment values must be a list")
            else:
                for i, value in enumerate(values):
                    if not isinstance(value, dict):
                        errors.append(f"Environment value {i} must be a dictionary")
                    elif 'key' not in value:
                        errors.append(f"Environment value {i} missing 'key' field")
        
        return len(errors) == 0, errors

    def get_file_stats(self) -> Dict[str, Any]:
        """
        Get statistics about saved files.
        
        Returns:
            Statistics dictionary
        """
        from ..utils.file_utils import quick_file_stats
        
        stats = {
            'collections': {
                'count': 0,
                'total_size': 0,
                'files': []
            },
            'environments': {
                'count': 0,
                'total_size': 0,
                'files': []
            }
        }
        
        # Get collections stats
        collections = self.list_collections()
        collection_paths = list(collections.values())
        if collection_paths:
            collection_stats = quick_file_stats(collection_paths)
            stats['collections']['count'] = collection_stats['total_files']
            stats['collections']['total_size'] = collection_stats['total_size']
            stats['collections']['files'] = list(collections.keys())
        
        # Get environments stats
        environments = self.list_environments()
        environment_paths = list(environments.values())
        if environment_paths:
            env_stats = quick_file_stats(environment_paths)
            stats['environments']['count'] = env_stats['total_files']
            stats['environments']['total_size'] = env_stats['total_size']
            stats['environments']['files'] = list(environments.keys())
        
        return stats


class PostmanManager:
    """
    Complete Postman operations manager following standard architecture.
    
    Orchestrates collection generation, file management, and reporting.
    Replaces the pipeline architecture from postman_consolidated.py.
    """
    
    def __init__(self, config=None, verbose: bool = True):
        self.config = config or get_config()
        self.verbose = verbose
        self.logger = get_logger("postman-manager")
        
        # Initialize standard components
        self.file_manager = PostmanFileManager(verbose=verbose)
        self._scanner = None  # Lazy loading
        self._reporter = None  # Lazy loading
        self._utils = None    # Lazy loading
        
        if self.verbose:
            self.logger.info("PostmanManager initialized with standard architecture")
    
    @property
    def scanner(self):
        """Lazy loading property for PostmanJSONProcessor."""
        if self._scanner is None:
            from ..scanning.postman_scanners import PostmanJSONProcessor
            json_dirs = {
                'v1': str(self.config.directories.json_v1),
                'v2': str(self.config.directories.json_v2)
            }
            self._scanner = PostmanJSONProcessor(json_dirs, self.verbose)
        return self._scanner
    
    @property
    def reporter(self):
        """Lazy loading property for PostmanReportGenerator."""
        if self._reporter is None:
            from ..reporting.postman_reporter import PostmanReportGenerator
            self._reporter = PostmanReportGenerator(self.verbose)
        return self._reporter
    
    @property
    def utils(self):
        """Lazy loading property for PostmanUtilities."""
        if self._utils is None:
            from ..utils.postman_utils import PostmanUtilities
            self._utils = PostmanUtilities()
        return self._utils
    
    def generate_collections(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Tuple[str, str]]:
        """
        Generate collections and environments for multiple versions.
        
        Args:
            versions: List of versions to generate
            
        Returns:
            Dictionary mapping versions to (collection_path, env_path) tuples
        """
        results = {}
        
        # Use async processing for better performance when processing multiple versions
        if len(versions) > 1:
            if self.verbose:
                self.logger.info("💡 Using async processing for multiple versions...")
            return self._generate_collections_async_wrapper(versions)
        
        # Single version - use synchronous processing
        for version in versions:
            if self.verbose:
                self.logger.info(f"Processing {version.upper()} collection...")
            
            try:
                # Generate collection and environment
                collection = self.generate_postman_collection(version)
                environment = self.generate_environment_file(version)
                
                # Validate before saving
                is_valid_collection, collection_errors = self.file_manager.validate_collection_structure(collection)
                if not is_valid_collection:
                    raise ValueError(f"Invalid collection generated for {version}: {'; '.join(collection_errors)}")
                
                is_valid_env, env_errors = self.file_manager.validate_environment_structure(environment)
                if not is_valid_env:
                    raise ValueError(f"Invalid environment generated for {version}: {'; '.join(env_errors)}")
                
                # Save files
                collection_result = self.file_manager.save_collection(collection, version)
                if not collection_result.success:
                    raise Exception(f"Failed to save collection: {collection_result.message}")
                
                environment_result = self.file_manager.save_environment(environment, version)
                if not environment_result.success:
                    raise Exception(f"Failed to save environment: {environment_result.message}")
                
                results[version] = (collection_result.file_path, environment_result.file_path)
                
                if self.verbose:
                    self.logger.success(f"{version.upper()} generation completed")
                    self.logger.info(f"   Collection: {Path(collection_result.file_path).name}")
                    self.logger.info(f"   Environment: {Path(environment_result.file_path).name}")
                
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"Error generating {version} collection: {e}")
                results[version] = (None, None)
        
        return results
    
    def generate_postman_collection(self, version: str) -> Dict:
        """
        Generate a complete Postman collection for a specific version.
        
        Args:
            version: API version to generate collection for
            
        Returns:
            Complete Postman collection dictionary
        """
        if self.verbose:
            self.logger.info(f"Generating {version.upper()} collection...")
        
        # Scan and categorize JSON examples
        categorized_requests = self.scanner.scan_json_examples(version)
        
        # Organize requests into folder structure
        folders = self.utils.organize_requests_into_folders(categorized_requests)
        
        # Calculate total requests
        total_requests = sum(len(cat_requests) for cat_requests in categorized_requests.values())
        
        # Generate collection using utilities
        collection = self.utils.generate_postman_collection(version, folders, total_requests)
        
        if self.verbose:
            self.logger.success(f"{version.upper()}: {total_requests} requests in {len(folders)} folders")
        
        return collection
    
    def generate_environment_file(self, version: str) -> Dict:
        """
        Generate a Postman environment file for a specific version.
        
        Args:
            version: API version
            
        Returns:
            Complete environment dictionary
        """
        return self.utils.generate_environment_file(version)
    
    async def generate_collections_async(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Tuple[str, str]]:
        """Generate collections asynchronously for better performance."""
        async def generate_single_version(version: str) -> Tuple[str, Tuple[str, str]]:
            """Generate collection for a single version asynchronously."""
            if self.verbose:
                print(f"🔄 Processing {version.upper()} collection asynchronously...")
            
            try:
                # Generate collection and environment (these are I/O bound operations)
                loop = asyncio.get_event_loop()
                
                # Run sync operations in thread pool to avoid blocking
                collection = await loop.run_in_executor(None, self.generate_postman_collection, version)
                environment = await loop.run_in_executor(None, self.generate_environment_file, version)
                
                # Validate before saving
                is_valid_collection, collection_errors = self.file_manager.validate_collection_structure(collection)
                if not is_valid_collection:
                    raise ValueError(f"Invalid collection generated for {version}: {'; '.join(collection_errors)}")
                
                is_valid_env, env_errors = self.file_manager.validate_environment_structure(environment)
                if not is_valid_env:
                    raise ValueError(f"Invalid environment generated for {version}: {'; '.join(env_errors)}")
                
                # Save files
                collection_result = self.file_manager.save_collection(collection, version)
                if not collection_result.success:
                    raise Exception(f"Failed to save collection: {collection_result.message}")
                
                environment_result = self.file_manager.save_environment(environment, version)
                if not environment_result.success:
                    raise Exception(f"Failed to save environment: {environment_result.message}")
                
                if self.verbose:
                    print(f"✅ {version.upper()} generation completed")
                    print(f"   Collection: {Path(collection_result.file_path).name}")
                    print(f"   Environment: {Path(environment_result.file_path).name}")
                
                return version, (collection_result.file_path, environment_result.file_path)
                
            except Exception as e:
                if self.verbose:
                    print(f"❌ Error generating {version} collection: {e}")
                return version, (None, None)
        
        # Generate all versions concurrently
        tasks = [generate_single_version(version) for version in versions]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert to dictionary format
        results = {}
        for result in results_list:
            if isinstance(result, Exception):
                if self.verbose:
                    self.logger.error(f"Async generation error: {result}")
                continue
            version, paths = result
            results[version] = paths
        
        return results
    
    def _generate_collections_async_wrapper(self, versions: List[str]) -> Dict[str, Tuple[str, str]]:
        """Wrapper to run async generation from sync context."""
        from ..async_support import run_async
        return run_async(self.generate_collections_async(versions))
    
    def generate_summary_report(self, results: Dict[str, Tuple[str, str]]) -> str:
        """Generate a summary report of generation results."""
        return self.reporter.generate_summary_report(results)
    
    def generate_scanning_report(self, versions: List[str] = ['v1', 'v2']) -> str:
        """Generate a report of JSON scanning results."""
        scan_results = {}
        
        for version in versions:
            try:
                scan_results[version] = self.scanner.scan_json_examples(version)
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"Error scanning {version}: {e}")
                scan_results[version] = {}
        
        return self.reporter.generate_scanning_report(scan_results)
    
    def get_file_statistics(self) -> Dict:
        """Get statistics about generated files."""
        return self.file_manager.get_file_stats()
    
    def get_file_statistics_report(self) -> str:
        """Get a formatted report of file statistics."""
        stats = self.get_file_statistics()
        return self.reporter.generate_file_statistics_report(stats)


# Convenience functions for quick generation
def generate_postman_collections(versions: List[str] = ['v1', 'v2'], 
                                verbose: bool = True) -> Dict[str, Tuple[str, str]]:
    """
    Convenience function to quickly generate Postman collections.
    
    Args:
        versions: List of API versions to generate
        verbose: Whether to enable verbose output
        
    Returns:
        Dictionary mapping versions to (collection_path, env_path) tuples
    """
    manager = PostmanManager(verbose=verbose)
    return manager.generate_collections(versions)


def get_postman_manager(config=None, verbose: bool = True) -> PostmanManager:
    """Get a PostmanManager instance."""
    return PostmanManager(config, verbose)


# Legacy compatibility - keep old function for backwards compatibility
def get_postman_file_manager(collections_dir: str = "../../postman/collections",
                           environments_dir: str = "../../postman/environments") -> PostmanFileManager:
    """Get a PostmanFileManager instance."""
    return PostmanFileManager(collections_dir, environments_dir) 