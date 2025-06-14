#!/usr/bin/env python3
"""
Postman I/O Operations

Consolidated file operations and scanning for Postman collections.
Handles JSON scanning, file I/O, and collection management.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from ..core.logging_utils import get_logger
from ..utils.file_utils import (
    normalize_file_path, ensure_directory_exists, safe_read_json, safe_write_json,
    find_files_by_pattern, extract_filename_parts
)
from ..utils.string_utils import convert_dir_to_method_name
from ..core.unified_file_ops import UnifiedFileOperations as BaseFileManager
from .postman_core import (
    PostmanRequest, PostmanRequestProcessor, MethodCategorizer, 
    CollectionGenerator, EnvironmentGenerator
)


class PostmanFileManager(BaseFileManager):
    """
    Manages file operations for Postman collections and environments.
    """
    
    def __init__(self, output_dir: Union[str, Path] = "../../postman/collections", 
                 env_dir: Union[str, Path] = "../../postman/environments", 
                 verbose: bool = True):
        super().__init__(output_dir, verbose)
        
        self.output_dir = normalize_file_path(output_dir)
        self.env_dir = normalize_file_path(env_dir)
        
        # Ensure directories exist
        ensure_directory_exists(self.output_dir)
        ensure_directory_exists(self.env_dir)
    
    def save_collection(self, collection: Dict[str, Any], version: str) -> str:
        """
        Save a Postman collection to file.
        
        Args:
            collection: Collection dictionary
            version: API version
            
        Returns:
            Path to saved collection file
        """
        # Generate filename
        filename = f"kdf-{version}-postman-collection.json"
        filepath = self.output_dir / filename
        
        # Validate before saving
        if not self.validate_collection(collection):
            raise ValueError(f"Invalid collection structure for {version}")
        
        # Save collection
        safe_write_json(filepath, collection, indent=2)
        
        if self.verbose:
            self.logger.success(f"Saved collection: {filepath}")
        
        return str(filepath)
    
    def save_environment(self, environment: Dict[str, Any], version: str) -> str:
        """
        Save a Postman environment to file.
        
        Args:
            environment: Environment dictionary
            version: API version
            
        Returns:
            Path to saved environment file
        """
        # Generate filename
        filename = f"kdf-{version}-environment.json"
        filepath = self.env_dir / filename
        
        # Validate before saving
        if not self.validate_environment(environment):
            raise ValueError(f"Invalid environment structure for {version}")
        
        # Save environment
        safe_write_json(filepath, environment, indent=2)
        
        if self.verbose:
            self.logger.success(f"Saved environment: {filepath}")
        
        return str(filepath)
    
    def load_collection(self, version: str) -> Dict[str, Any]:
        """
        Load a Postman collection from file.
        
        Args:
            version: API version
            
        Returns:
            Collection dictionary
        """
        filename = f"kdf-{version}-postman-collection.json"
        filepath = self.output_dir / filename
        
        return safe_read_json(filepath)
    
    def load_environment(self, version: str) -> Dict[str, Any]:
        """
        Load a Postman environment from file.
        
        Args:
            version: API version
            
        Returns:
            Environment dictionary
        """
        filename = f"kdf-{version}-environment.json"
        filepath = self.env_dir / filename
        
        return safe_read_json(filepath)
    
    def list_collections(self) -> Dict[str, str]:
        """
        List all available collections.
        
        Returns:
            Dictionary mapping versions to file paths
        """
        collections = {}
        
        if not self.output_dir.exists():
            return collections
        
        for filepath in self.output_dir.glob("kdf-*-postman-collection.json"):
            # Extract version from filename
            filename = filepath.stem
            parts = filename.split('-')
            if len(parts) >= 2:
                version = parts[1]
                collections[version] = str(filepath)
        
        return collections
    
    def list_environments(self) -> Dict[str, str]:
        """
        List all available environments.
        
        Returns:
            Dictionary mapping versions to file paths
        """
        environments = {}
        
        if not self.env_dir.exists():
            return environments
        
        for filepath in self.env_dir.glob("kdf-*-environment.json"):
            # Extract version from filename
            filename = filepath.stem
            parts = filename.split('-')
            if len(parts) >= 2:
                version = parts[1]
                environments[version] = str(filepath)
        
        return environments
    
    def validate_collection(self, collection: Dict[str, Any]) -> bool:
        """
        Validate a Postman collection structure.
        
        Args:
            collection: Collection dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['info', 'item']
        
        # Check required top-level fields
        for field in required_fields:
            if field not in collection:
                if self.verbose:
                    self.logger.warning(f"Invalid collection: Missing required field '{field}'")
                return False
        
        # Check info section
        info = collection['info']
        required_info_fields = ['name', 'schema']
        
        for field in required_info_fields:
            if field not in info:
                if self.verbose:
                    self.logger.warning(f"Invalid collection: Missing info field '{field}'")
                return False
        
        # Check items
        if not isinstance(collection['item'], list):
            if self.verbose:
                self.logger.warning("Invalid collection: 'item' must be a list")
            return False
        
        return True
    
    def validate_environment(self, environment: Dict[str, Any]) -> bool:
        """
        Validate a Postman environment structure.
        
        Args:
            environment: Environment dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['id', 'name', 'values']
        
        # Check required fields
        for field in required_fields:
            if field not in environment:
                if self.verbose:
                    self.logger.warning(f"Invalid environment: Missing required field '{field}'")
                return False
        
        # Check values is a list
        if not isinstance(environment['values'], list):
            if self.verbose:
                self.logger.warning("Invalid environment: 'values' must be a list")
            return False
        
        # Check each value has key and value
        for var in environment['values']:
            if not isinstance(var, dict) or 'key' not in var:
                if self.verbose:
                    self.logger.warning("Invalid environment: Each variable must have a 'key'")
                return False
        
        return True
    
    def get_file_stats(self) -> Dict[str, Any]:
        """
        Get statistics about saved files.
        
        Returns:
            Dictionary with file statistics
        """
        collections = self.list_collections()
        environments = self.list_environments()
        
        stats = {
            'collections': {
                'count': len(collections),
                'versions': list(collections.keys()),
                'total_size': 0
            },
            'environments': {
                'count': len(environments),
                'versions': list(environments.keys()),
                'total_size': 0
            }
        }
        
        # Calculate file sizes
        for filepath in collections.values():
            if Path(filepath).exists():
                stats['collections']['total_size'] += Path(filepath).stat().st_size
        
        for filepath in environments.values():
            if Path(filepath).exists():
                stats['environments']['total_size'] += Path(filepath).stat().st_size
        
        return stats


class JSONExampleScanner(BaseFileManager):
    """
    Scans JSON example files and processes them for Postman collection generation.
    """
    
    def __init__(self, json_dirs: Dict[str, Union[str, Path]], verbose: bool = True):
        super().__init__(".", verbose)
        
        self.json_dirs = {k: normalize_file_path(v) for k, v in json_dirs.items()}
        self.categorizer = MethodCategorizer()
        self.request_processor = PostmanRequestProcessor(verbose)
    
    def scan_json_examples(self, version: str) -> Dict[str, List[PostmanRequest]]:
        """
        Scan JSON examples for a specific version and categorize them.
        
        Args:
            version: API version to scan
            
        Returns:
            Dictionary mapping categories to lists of PostmanRequest objects
        """
        if version not in self.json_dirs:
            if self.verbose:
                self.logger.warning(f"No directory configured for version {version}")
            return {}
        
        base_dir = self.json_dirs[version]
        if not base_dir.exists():
            if self.verbose:
                self.logger.warning(f"Directory does not exist: {base_dir}")
            return {}
        
        categorized_requests = {}
        
        # Initialize categories
        for category in self.categorizer.category_patterns.keys():
            categorized_requests[category] = []
        
        # Scan method directories
        for method_dir in base_dir.iterdir():
            if not method_dir.is_dir():
                continue
            
            method_name = convert_dir_to_method_name(method_dir.name)
            category = self.categorizer.categorize_method(method_name)
            
            # Scan operation subdirectories
            requests = self._scan_method_operations(method_dir, method_name, version)
            categorized_requests[category].extend(requests)
        
        return categorized_requests
    
    def _scan_method_operations(self, method_path: Path, method_name: str, version: str) -> List[PostmanRequest]:
        """
        Scan operation subdirectories within a method directory.
        
        Args:
            method_path: Path to method directory
            method_name: Method name
            version: API version
            
        Returns:
            List of PostmanRequest objects
        """
        requests = []
        
        # Check if there are operation subdirectories
        has_operation_dirs = any(
            item.is_dir() and item.name in ['init', 'status', 'cancel', 'user_action']
            for item in method_path.iterdir()
        )
        
        if has_operation_dirs:
            # Scan operation subdirectories
            for operation_dir in method_path.iterdir():
                if not operation_dir.is_dir():
                    continue
                
                operation = operation_dir.name
                
                # Scan JSON files in operation directory
                json_files = find_files_by_pattern(operation_dir, "*.json", recursive=False)
                
                for json_file in json_files:
                    request = self._process_json_file(json_file, method_name, operation, version)
                    if request:
                        requests.append(request)
        else:
            # Scan JSON files directly in method directory
            json_files = find_files_by_pattern(method_path, "*.json", recursive=False)
            
            for json_file in json_files:
                request = self._process_json_file(json_file, method_name, "default", version)
                if request:
                    requests.append(request)
        
        return requests
    
    def _process_json_file(self, json_path: Path, method_name: str,
                          operation: str, version: str) -> Optional[PostmanRequest]:
        """
        Process a single JSON file into a PostmanRequest.
        
        Args:
            json_path: Path to JSON file
            method_name: Method name
            operation: Operation name
            version: API version
            
        Returns:
            PostmanRequest object or None if processing fails
        """
        try:
            json_data = safe_read_json(json_path)
            
            if 'method' not in json_data:
                if self.verbose:
                    self.logger.warning(f"Skipping {json_path}: No 'method' field found")
                return None
            
            # Extract example description from filename
            example_description = self._extract_example_description(json_path)
            
            # Validate method-operation match
            json_method = json_data.get('method', '')
            if not self.request_processor.validate_method_operation_match(json_method, method_name, operation):
                if self.verbose:
                    self.logger.warning(f"Skipping mismatched file: {json_path}")
                    self.logger.debug(f"  Expected: {method_name} with operation '{operation}'")
                    self.logger.debug(f"  Found: {json_method}")
                return None
            
            # Validate content for operation
            if not self.request_processor.validate_content_for_operation(json_data, operation):
                if self.verbose:
                    self.logger.warning(f"Skipping invalid content: {json_path}")
                    self.logger.debug(f"  Issue: Status method has activation_params (should only have task_id)")
                return None
            
            # Create PostmanRequest
            return self.request_processor.create_postman_request(
                json_data, method_name, operation, example_description, version
            )
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error processing {json_path}: {e}")
            return None
    
    def _extract_example_description(self, json_path: Path) -> str:
        """
        Extract example description from JSON filename.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Example description string
        """
        filename_parts = extract_filename_parts(json_path)
        filename = filename_parts['stem']
        
        # Try to extract description from filename structure
        parts = filename.split('-')
        if len(parts) >= 2:
            # Skip the first part which is usually the method name
            description_parts = parts[1:]
            return '-'.join(description_parts)
        
        return "basic_request"  # Default fallback


class PostmanReportGenerator:
    """
    Generates reports and summaries for Postman collection operations.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = get_logger("postman-report-generator")
    
    def generate_summary_report(self, results: Dict[str, tuple]) -> str:
        """
        Generate a summary report of generation results.
        
        Args:
            results: Dictionary mapping versions to (collection_path, env_path) tuples
            
        Returns:
            Formatted summary report
        """
        report_lines = [
            "📊 Postman Collection Generation Summary",
            "=" * 50,
            ""
        ]
        
        successful_generations = 0
        failed_generations = 0
        
        for version, (collection_path, env_path) in results.items():
            if collection_path and env_path:
                successful_generations += 1
                report_lines.extend([
                    f"✅ {version.upper()} - Successfully generated",
                    f"   Collection: {Path(collection_path).name}",
                    f"   Environment: {Path(env_path).name}",
                    ""
                ])
            else:
                failed_generations += 1
                report_lines.extend([
                    f"❌ {version.upper()} - Generation failed",
                    ""
                ])
        
        # Summary statistics
        total_versions = len(results)
        report_lines.extend([
            "📈 Statistics:",
            f"   Total versions processed: {total_versions}",
            f"   Successful generations: {successful_generations}",
            f"   Failed generations: {failed_generations}",
            f"   Success rate: {(successful_generations/total_versions*100):.1f}%",
            ""
        ])
        
        # Next steps
        if successful_generations > 0:
            report_lines.extend([
                "🔗 Next Steps:",
                "1. Import the collection files into Postman",
                "2. Import the environment files",
                "3. Set the kdf_url variable to your KDF instance",
                "4. Update the userpass variable with your credentials",
                "5. Test the requests",
                ""
            ])
        
        return "\n".join(report_lines)
    
    def generate_file_statistics_report(self, file_stats: Dict[str, Any]) -> str:
        """
        Generate a report about file statistics.
        
        Args:
            file_stats: File statistics from PostmanFileManager
            
        Returns:
            Formatted statistics report
        """
        report_lines = [
            "📁 Postman File Statistics",
            "=" * 30,
            ""
        ]
        
        # Collections statistics
        collections = file_stats.get('collections', {})
        report_lines.extend([
            f"Collections: {collections.get('count', 0)}",
            f"Versions: {', '.join(collections.get('versions', []))}",
            f"Total size: {collections.get('total_size', 0):,} bytes",
            ""
        ])
        
        # Environments statistics
        environments = file_stats.get('environments', {})
        report_lines.extend([
            f"Environments: {environments.get('count', 0)}",
            f"Versions: {', '.join(environments.get('versions', []))}",
            f"Total size: {environments.get('total_size', 0):,} bytes",
            ""
        ])
        
        return "\n".join(report_lines)
    
    def generate_scanning_report(self, scan_results: Dict[str, Dict[str, List[PostmanRequest]]]) -> str:
        """
        Generate a report about JSON scanning results.
        
        Args:
            scan_results: Results from scanning JSON examples
            
        Returns:
            Formatted scanning report
        """
        report_lines = [
            "🔍 JSON Example Scanning Report",
            "=" * 35,
            ""
        ]
        
        for version, categorized_requests in scan_results.items():
            total_requests = sum(len(requests) for requests in categorized_requests.values())
            
            report_lines.extend([
                f"{version.upper()} API:",
                f"  Total requests: {total_requests}",
                ""
            ])
            
            # Category breakdown
            for category, requests in categorized_requests.items():
                if requests:
                    report_lines.append(f"  {category}: {len(requests)} requests")
            
            report_lines.append("")
        
        return "\n".join(report_lines) 