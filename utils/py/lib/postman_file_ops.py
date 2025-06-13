#!/usr/bin/env python3
"""
Postman File Operations

Handles file I/O operations for Postman collections and environments.
Manages saving, loading, and path operations.
"""

import json
from pathlib import Path
from typing import Dict, Any


class PostmanFileManager:
    """
    Manages file operations for Postman collections and environments.
    """
    
    def __init__(self, output_dir: str = "../../postman/collections", 
                 env_dir: str = "../../postman/environments", verbose: bool = True):
        self.output_dir = Path(output_dir)
        self.env_dir = Path(env_dir)
        self.verbose = verbose
    
    def save_collection(self, collection: Dict[str, Any], version: str) -> str:
        """
        Save a Postman collection to file.
        
        Args:
            collection: Collection dictionary
            version: API version
            
        Returns:
            Path to saved collection file
        """
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = f"kdf-{version}-postman-collection.json"
        filepath = self.output_dir / filename
        
        # Save collection
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"✅ Saved collection: {filepath}")
        
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
        # Ensure environment directory exists
        self.env_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        filename = f"kdf-{version}-environment.json"
        filepath = self.env_dir / filename
        
        # Save environment
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(environment, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"✅ Saved environment: {filepath}")
        
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
        
        if not filepath.exists():
            raise FileNotFoundError(f"Collection file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
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
        
        if not filepath.exists():
            raise FileNotFoundError(f"Environment file not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
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
                    print(f"Invalid collection: Missing required field '{field}'")
                return False
        
        # Check info section
        info = collection['info']
        required_info_fields = ['name', 'schema']
        
        for field in required_info_fields:
            if field not in info:
                if self.verbose:
                    print(f"Invalid collection: Missing info field '{field}'")
                return False
        
        # Check items
        if not isinstance(collection['item'], list):
            if self.verbose:
                print("Invalid collection: 'item' must be a list")
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
                    print(f"Invalid environment: Missing required field '{field}'")
                return False
        
        # Check values is a list
        if not isinstance(environment['values'], list):
            if self.verbose:
                print("Invalid environment: 'values' must be a list")
            return False
        
        # Check each value has key and value
        for var in environment['values']:
            if not isinstance(var, dict) or 'key' not in var:
                if self.verbose:
                    print("Invalid environment: Each variable must have a 'key'")
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