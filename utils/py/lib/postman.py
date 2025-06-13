#!/usr/bin/env python3
"""
Postman Collection Generator (Refactored)

Main coordinator for generating Postman collections from organized JSON examples.
Uses specialized components for request processing, organization, generation, and file operations.
"""

from pathlib import Path
from typing import Dict, List, Tuple

from .mapping import MethodMapper
from .postman_scanners import JSONExampleScanner, PostmanReportGenerator
from .postman_organizers import MethodCategorizer, FolderOrganizer
from .postman_generators import CollectionGenerator, EnvironmentGenerator
from .postman_file_ops import PostmanFileManager


class PostmanCollectionGenerator:
    """
    Main coordinator for generating comprehensive Postman collections.
    
    Uses specialized components:
    - JSONExampleScanner: Scans and processes JSON examples
    - MethodCategorizer: Categorizes methods into logical groups
    - FolderOrganizer: Organizes requests into folder structures
    - CollectionGenerator: Generates Postman collections
    - EnvironmentGenerator: Generates environment files
    - PostmanFileManager: Handles file I/O operations
    """
    
    def __init__(self, base_path: str = ".", verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        
        # Directory configurations - make paths absolute
        base_dir = Path(__file__).parent.parent.parent.parent  # Go up from lib/ to py/ to utils/ to komodo-docs-mdx/
        self.json_dirs = {
            'v1': str(base_dir / 'postman' / 'json' / 'kdf' / 'v1'),
            'v2': str(base_dir / 'postman' / 'json' / 'kdf' / 'v2'),
        }
        
        if self.verbose:
            print(f"🔍 JSON directories:")
            for version, path in self.json_dirs.items():
                exists = "✅" if Path(path).exists() else "❌"
                print(f"   {version}: {exists} {path}")
        
        # Initialize specialized components
        self.mapper = MethodMapper(base_path, verbose)
        self.scanner = JSONExampleScanner(self.json_dirs, verbose)
        self.categorizer = MethodCategorizer()
        self.organizer = FolderOrganizer(self.categorizer)
        self.collection_generator = CollectionGenerator()
        self.environment_generator = EnvironmentGenerator()
        self.file_manager = PostmanFileManager(verbose=verbose)
        self.report_generator = PostmanReportGenerator(verbose)
    
    def generate_postman_collection(self, version: str) -> Dict:
        """
        Generate a complete Postman collection for a specific version.
        
        Args:
            version: API version to generate collection for
            
        Returns:
            Complete Postman collection dictionary
        """
        if self.verbose:
            print(f"🔨 Generating {version.upper()} collection...")
        
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
            print(f"✅ {version.upper()}: {total_requests} requests in {len(folders)} folders")
        
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
                print(f"\n🔨 Generating {version.upper()} collection...")
            
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
                    print(f"✅ {version.upper()} generation completed")
                    print(f"   Collection: {Path(collection_path).name}")
                    print(f"   Environment: {Path(environment_path).name}")
                
            except Exception as e:
                if self.verbose:
                    print(f"❌ Error generating {version} collection: {e}")
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
    
    def get_file_statistics(self) -> Dict:
        """
        Get statistics about generated files.
        
        Returns:
            File statistics dictionary
        """
        return self.file_manager.get_file_stats()
    
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
    
    def categorize_method(self, method_name: str) -> str:
        """
        Categorize a method name.
        
        Args:
            method_name: The method name to categorize
            
        Returns:
            Category name
        """
        return self.categorizer.categorize_method(method_name)
    
    # Legacy compatibility methods (for backwards compatibility)
    def scan_json_examples(self, version: str) -> Dict:
        """Legacy compatibility method."""
        return self.scanner.scan_json_examples(version)
    
    def save_collection(self, collection: Dict, version: str) -> str:
        """Legacy compatibility method."""
        return self.file_manager.save_collection(collection, version)
    
    def save_environment(self, environment: Dict, version: str) -> str:
        """Legacy compatibility method."""
        return self.file_manager.save_environment(environment, version) 