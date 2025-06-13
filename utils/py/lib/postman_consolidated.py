#!/usr/bin/env python3
"""
Consolidated Postman Collection Generator

Unified interface for generating Postman collections from JSON examples.
Replaces the old fragmented postman modules with a clean, consolidated approach.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Union

from .logging_utils import get_logger
from .postman_core import (
    PostmanRequest, PostmanFolder, PostmanRequestProcessor, 
    MethodCategorizer, FolderOrganizer, CollectionGenerator, EnvironmentGenerator
)
from .postman_io import PostmanFileManager, JSONExampleScanner, PostmanReportGenerator
from .mapping import MethodMapper


class PostmanCollectionGenerator:
    """
    Unified Postman collection generator.
    
    Consolidates all Postman-related functionality into a single, clean interface.
    Replaces the old fragmented approach with better organization and efficiency.
    """
    
    def __init__(self, base_path: Union[str, Path] = ".", verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        self.logger = get_logger("postman-generator")
        
        # Directory configurations
        self.json_dirs = {
            'v1': '../../postman/json/kdf/v1',
            'v2': '../../postman/json/kdf/v2',
        }
        
        # Initialize core components
        self.categorizer = MethodCategorizer()
        self.organizer = FolderOrganizer(self.categorizer)
        self.collection_generator = CollectionGenerator()
        self.environment_generator = EnvironmentGenerator()
        
        # Initialize I/O components
        self.scanner = JSONExampleScanner(self.json_dirs, verbose)
        self.file_manager = PostmanFileManager(verbose=verbose)
        self.report_generator = PostmanReportGenerator(verbose)
        
        # Optional method mapper for advanced functionality
        self.mapper = None
        
        if self.verbose:
            self.logger.info("Initialized consolidated Postman collection generator")
    
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
        folders = self.organizer.organize_requests_into_folders(categorized_requests)
        
        # Calculate total requests
        total_requests = sum(len(cat_requests) for cat_requests in categorized_requests.values())
        
        # Generate collection
        collection = self.collection_generator.generate_postman_collection(
            version, folders, total_requests
        )
        
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
        return self.environment_generator.generate_environment_file(version)
    
    def generate_collections(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Tuple[str, str]]:
        """
        Generate collections and environments for multiple versions.
        
        Args:
            versions: List of versions to generate
            
        Returns:
            Dictionary mapping versions to (collection_path, env_path) tuples
        """
        results = {}
        
        for version in versions:
            if self.verbose:
                self.logger.info(f"Processing {version.upper()} collection...")
            
            try:
                # Generate collection and environment
                collection = self.generate_postman_collection(version)
                environment = self.generate_environment_file(version)
                
                # Validate before saving
                if not self.file_manager.validate_collection(collection):
                    raise ValueError(f"Invalid collection generated for {version}")
                
                if not self.file_manager.validate_environment(environment):
                    raise ValueError(f"Invalid environment generated for {version}")
                
                # Save files
                collection_path = self.file_manager.save_collection(collection, version)
                environment_path = self.file_manager.save_environment(environment, version)
                
                results[version] = (collection_path, environment_path)
                
                if self.verbose:
                    self.logger.success(f"{version.upper()} generation completed")
                    self.logger.info(f"   Collection: {Path(collection_path).name}")
                    self.logger.info(f"   Environment: {Path(environment_path).name}")
                
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"Error generating {version} collection: {e}")
                results[version] = (None, None)
        
        return results
    
    def generate_summary_report(self, results: Dict[str, Tuple[str, str]]) -> str:
        """
        Generate a summary report of generation results.
        
        Args:
            results: Dictionary mapping versions to (collection_path, env_path) tuples
            
        Returns:
            Formatted summary report
        """
        return self.report_generator.generate_summary_report(results)
    
    def generate_scanning_report(self, versions: List[str] = ['v1', 'v2']) -> str:
        """
        Generate a report of JSON scanning results.
        
        Args:
            versions: List of versions to scan
            
        Returns:
            Formatted scanning report
        """
        scan_results = {}
        
        for version in versions:
            try:
                scan_results[version] = self.scanner.scan_json_examples(version)
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"Error scanning {version}: {e}")
                scan_results[version] = {}
        
        return self.report_generator.generate_scanning_report(scan_results)
    
    def get_file_statistics(self) -> Dict:
        """
        Get statistics about generated files.
        
        Returns:
            File statistics dictionary
        """
        return self.file_manager.get_file_stats()
    
    def get_file_statistics_report(self) -> str:
        """
        Get a formatted report of file statistics.
        
        Returns:
            Formatted statistics report
        """
        stats = self.get_file_statistics()
        return self.report_generator.generate_file_statistics_report(stats)
    
    def list_available_collections(self) -> Dict[str, str]:
        """
        List all available collections.
        
        Returns:
            Dictionary mapping versions to file paths
        """
        return self.file_manager.list_collections()
    
    def list_available_environments(self) -> Dict[str, str]:
        """
        List all available environments.
        
        Returns:
            Dictionary mapping versions to file paths
        """
        return self.file_manager.list_environments()
    
    def load_collection(self, version: str) -> Dict:
        """
        Load an existing collection.
        
        Args:
            version: API version
            
        Returns:
            Collection dictionary
        """
        return self.file_manager.load_collection(version)
    
    def load_environment(self, version: str) -> Dict:
        """
        Load an existing environment.
        
        Args:
            version: API version
            
        Returns:
            Environment dictionary
        """
        return self.file_manager.load_environment(version)
    
    def validate_collection(self, collection: Dict) -> bool:
        """
        Validate a collection structure.
        
        Args:
            collection: Collection to validate
            
        Returns:
            True if valid, False otherwise
        """
        return self.file_manager.validate_collection(collection)
    
    def validate_environment(self, environment: Dict) -> bool:
        """
        Validate an environment structure.
        
        Args:
            environment: Environment to validate
            
        Returns:
            True if valid, False otherwise
        """
        return self.file_manager.validate_environment(environment)
    
    def scan_json_examples(self, version: str) -> Dict:
        """
        Scan JSON examples for a specific version.
        
        Args:
            version: API version to scan
            
        Returns:
            Dictionary of categorized requests
        """
        return self.scanner.scan_json_examples(version)
    
    def save_collection(self, collection: Dict, version: str) -> str:
        """
        Save a collection to file.
        
        Args:
            collection: Collection to save
            version: API version
            
        Returns:
            Path to saved file
        """
        return self.file_manager.save_collection(collection, version)
    
    def save_environment(self, environment: Dict, version: str) -> str:
        """
        Save an environment to file.
        
        Args:
            environment: Environment to save
            version: API version
            
        Returns:
            Path to saved file
        """
        return self.file_manager.save_environment(environment, version)
    
    def enable_method_mapping(self, base_path: Union[str, Path] = None):
        """
        Enable advanced method mapping functionality.
        
        Args:
            base_path: Base path for method mapping
        """
        if base_path is None:
            base_path = self.base_path
        
        self.mapper = MethodMapper(base_path, self.verbose)
        
        if self.verbose:
            self.logger.info("Enabled method mapping functionality")
    
    def get_method_mapping(self) -> Dict:
        """
        Get unified method mapping if enabled.
        
        Returns:
            Method mapping dictionary or None if not enabled
        """
        if self.mapper is None:
            if self.verbose:
                self.logger.warning("Method mapping not enabled. Call enable_method_mapping() first.")
            return None
        
        return self.mapper.create_unified_mapping()
    
    def validate_json_examples_against_mapping(self, version: str) -> Dict[str, List[str]]:
        """
        Validate JSON examples against method mapping.
        
        Args:
            version: API version to validate
            
        Returns:
            Dictionary with validation results
        """
        if self.mapper is None:
            if self.verbose:
                self.logger.warning("Method mapping not enabled. Cannot validate against mapping.")
            return {"error": ["Method mapping not enabled"]}
        
        # Get method mapping
        unified_mapping = self.mapper.create_unified_mapping()
        version_mapping = unified_mapping.get(version, {})
        
        # Get JSON examples
        categorized_requests = self.scanner.scan_json_examples(version)
        
        # Extract method names from requests
        json_methods = set()
        for category_requests in categorized_requests.values():
            for request in category_requests:
                json_methods.add(request.method_name)
        
        # Compare with mapping
        mapped_methods = set(version_mapping.keys())
        
        validation_results = {
            "methods_with_json": list(json_methods),
            "methods_with_mapping": list(mapped_methods),
            "methods_with_both": list(json_methods & mapped_methods),
            "methods_json_only": list(json_methods - mapped_methods),
            "methods_mapping_only": list(mapped_methods - json_methods),
            "coverage_percentage": (len(json_methods & mapped_methods) / max(1, len(mapped_methods))) * 100
        }
        
        return validation_results


# Convenience function for quick generation
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
    generator = PostmanCollectionGenerator(verbose=verbose)
    return generator.generate_collections(versions)


def main():
    """Main function for command-line usage."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Generate Postman collections for KDF API')
    parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'], default=['v1', 'v2'],
                       help='API versions to generate collections for')
    parser.add_argument('--verbose', '-v', action='store_true', default=True,
                       help='Enable verbose output')
    parser.add_argument('--report', action='store_true',
                       help='Generate detailed reports only (no file generation)')
    parser.add_argument('--validate', action='store_true',
                       help='Validate existing collections and environments')
    parser.add_argument('--scan-only', action='store_true',
                       help='Only scan JSON examples and generate scanning report')
    
    args = parser.parse_args()
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    generator = PostmanCollectionGenerator(verbose=args.verbose)
    
    if args.scan_only:
        print("🔍 Scanning JSON examples...")
        report = generator.generate_scanning_report(args.versions)
        print(report)
        return
    
    if args.report:
        print("📊 Generating reports...")
        
        # Generate scanning report
        scan_report = generator.generate_scanning_report(args.versions)
        print(scan_report)
        
        # Generate file statistics report
        stats_report = generator.get_file_statistics_report()
        print(stats_report)
        
        return
    
    if args.validate:
        print("🔍 Validating existing files...")
        
        collections = generator.list_available_collections()
        environments = generator.list_available_environments()
        
        print(f"Found {len(collections)} collections and {len(environments)} environments")
        
        for version in args.versions:
            try:
                if version in collections:
                    collection = generator.load_collection(version)
                    is_valid = generator.validate_collection(collection)
                    status = "✅ Valid" if is_valid else "❌ Invalid"
                    print(f"Collection {version}: {status}")
                else:
                    print(f"Collection {version}: ❓ Not found")
                
                if version in environments:
                    environment = generator.load_environment(version)
                    is_valid = generator.validate_environment(environment)
                    status = "✅ Valid" if is_valid else "❌ Invalid"
                    print(f"Environment {version}: {status}")
                else:
                    print(f"Environment {version}: ❓ Not found")
                    
            except Exception as e:
                print(f"Error validating {version}: {e}")
        
        return
    
    # Generate collections
    print("🚀 Starting Postman collection generation...")
    print(f"📋 Processing versions: {', '.join(args.versions)}")
    
    results = generator.generate_collections(args.versions)
    
    # Generate summary report
    report = generator.generate_summary_report(results)
    print(f"\n{report}")


if __name__ == "__main__":
    main() 