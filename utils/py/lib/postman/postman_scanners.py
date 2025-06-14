#!/usr/bin/env python3
"""
Postman JSON Example Scanners

Handles scanning and processing of JSON example files for Postman collection generation.
Manages file discovery, validation, and categorization.
"""

import os
import json
from typing import Dict, List, Optional
from pathlib import Path

from .postman_requests import PostmanRequest, PostmanRequestProcessor
from .postman_organizers import MethodCategorizer
from ..utils.string_utils import convert_dir_to_method_name


class JSONExampleScanner:
    """
    Scans JSON example directories and processes them into Postman requests.
    """
    
    def __init__(self, json_dirs: Dict[str, str], verbose: bool = True):
        self.json_dirs = json_dirs
        self.verbose = verbose
        self.request_processor = PostmanRequestProcessor(verbose)
        self.categorizer = MethodCategorizer()
    
    def scan_json_examples(self, version: str) -> Dict[str, List[PostmanRequest]]:
        """
        Scan JSON examples for a specific version and return categorized requests.
        
        Args:
            version: API version to scan
            
        Returns:
            Dictionary mapping categories to request lists
        """
        if version not in self.json_dirs:
            raise ValueError(f"Unsupported version: {version}")
        
        base_dir = self.json_dirs[version]
        if not os.path.exists(base_dir):
            if self.verbose:
                print(f"Warning: Examples directory {base_dir} does not exist")
            return {}
        
        # Initialize categorized requests
        categorized_requests = {category: [] for category in self.categorizer.method_categories.keys()}
        
        # Scan method directories
        for method_dir in os.listdir(base_dir):
            method_path = os.path.join(base_dir, method_dir)
            if not os.path.isdir(method_path):
                continue
            
            method_name = convert_dir_to_method_name(method_dir)
            category = self.categorizer.categorize_method(method_name)
            
            # Scan operation subdirectories
            requests = self._scan_method_operations(method_path, method_name, version)
            categorized_requests[category].extend(requests)
        
        return categorized_requests
    
    def _scan_method_operations(self, method_path: str, method_name: str, version: str) -> List[PostmanRequest]:
        """
        Scan JSON files within a method directory.
        
        Args:
            method_path: Path to method directory
            method_name: Method name
            version: API version
            
        Returns:
            List of PostmanRequest objects
        """
        requests = []
        
        # Check if there are subdirectories (nested structure) or JSON files directly (flat structure)
        has_subdirs = any(os.path.isdir(os.path.join(method_path, item)) 
                         for item in os.listdir(method_path))
        has_json_files = any(item.endswith('.json') 
                           for item in os.listdir(method_path))
        
        if has_subdirs and not has_json_files:
            # Nested structure: scan operation subdirectories
            for operation_dir in os.listdir(method_path):
                operation_path = os.path.join(method_path, operation_dir)
                if not os.path.isdir(operation_path):
                    continue
                
                operation = operation_dir
                
                # Scan JSON files in operation directory
                for json_file in os.listdir(operation_path):
                    if not json_file.endswith('.json'):
                        continue
                    
                    json_path = os.path.join(operation_path, json_file)
                    request = self._process_json_file(json_path, method_name, operation, version)
                    
                    if request:
                        requests.append(request)
        
        elif has_json_files:
            # Flat structure: scan JSON files directly in method directory
            for json_file in os.listdir(method_path):
                if not json_file.endswith('.json'):
                    continue
                
                json_path = os.path.join(method_path, json_file)
                
                # Extract operation from filename or use default
                operation = self._extract_operation_from_filename(json_file, method_name)
                
                request = self._process_json_file(json_path, method_name, operation, version)
                
                if request:
                    requests.append(request)
        
        return requests
    
    def _extract_operation_from_filename(self, filename: str, method_name: str) -> str:
        """
        Extract operation from filename.
        
        Args:
            filename: JSON filename
            method_name: Method name
            
        Returns:
            Operation name or 'request' as default
        """
        # Remove .json extension
        basename = filename[:-5] if filename.endswith('.json') else filename
        
        # For task methods, try to extract operation from method name
        if '::' in method_name:
            parts = method_name.split('::')
            if len(parts) >= 3:
                # For task::enable_coin::operation format
                return parts[-1]
            elif len(parts) == 2 and parts[0] in ['task', 'stream', 'lightning']:
                # For task::method format, try to extract from filename
                if 'init' in basename:
                    return 'init'
                elif 'status' in basename:
                    return 'status'
                elif 'cancel' in basename:
                    return 'cancel'
                elif 'user_action' in basename:
                    return 'user_action'
        
        # Default operation
        return 'request'
    
    def _process_json_file(self, json_path: str, method_name: str, 
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
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            if 'method' not in json_data:
                if self.verbose:
                    print(f"Skipping {json_path}: No 'method' field found")
                return None
            
            # Extract example description from filename
            example_description = self._extract_example_description(json_path)
            
            # Validate method-operation match
            json_method = json_data.get('method', '')
            if not self.request_processor.validate_method_operation_match(json_method, method_name, operation):
                if self.verbose:
                    print(f"Skipping mismatched file: {json_path}")
                    print(f"  Expected: {method_name} with operation '{operation}'")
                    print(f"  Found: {json_method}")
                return None
            
            # Validate content for operation
            if not self.request_processor.validate_content_for_operation(json_data, operation):
                if self.verbose:
                    print(f"Skipping invalid content: {json_path}")
                    print(f"  Issue: Status method has activation_params (should only have task_id)")
                return None
            
            # Create PostmanRequest
            return self.request_processor.create_postman_request(
                json_data, method_name, operation, example_description, version
            )
            
        except Exception as e:
            if self.verbose:
                print(f"Error processing {json_path}: {e}")
            return None
    
    def _extract_example_description(self, json_path: str) -> str:
        """
        Extract example description from JSON filename.
        
        Args:
            json_path: Path to JSON file
            
        Returns:
            Example description string
        """
        filename = Path(json_path).stem  # Remove .json extension
        parts = filename.split('-')
        
        # Try to extract description from filename structure
        if len(parts) >= 5:
            return parts[-2]  # Usually the description part
        
        return "basic_request"  # Default fallback


class PostmanReportGenerator:
    """
    Generates reports and summaries for Postman collection generation.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def generate_summary_report(self, results: Dict[str, tuple]) -> str:
        """
        Generate a summary report of collection generation results.
        
        Args:
            results: Dictionary mapping versions to (collection_path, env_path) tuples
            
        Returns:
            Formatted summary report
        """
        report_lines = [
            "🎯 Postman Collection Generation Summary",
            "=" * 50,
            ""
        ]
        
        total_collections = 0
        total_environments = 0
        
        for version, (collection_path, env_path) in results.items():
            if collection_path and env_path:
                total_collections += 1
                total_environments += 1
                report_lines.extend([
                    f"✅ {version.upper()} API:",
                    f"    📁 Collection: {Path(collection_path).name}",
                    f"    🌍 Environment: {Path(env_path).name}",
                    ""
                ])
            else:
                report_lines.extend([
                    f"❌ {version.upper()} API: Generation failed",
                    ""
                ])
        
        report_lines.extend([
            f"📊 Results:",
            f"   Collections generated: {total_collections}",
            f"   Environments generated: {total_environments}",
            "",
            "🚀 Next Steps:",
            "1. Import the collection files into Postman",
            "2. Import the environment files",
            "3. Update the 'userpass' environment variable",
            "4. Set the 'kdf_url' to your KDF instance",
            "5. Start testing the API!",
            "",
            "📚 Documentation:",
            "- Collection includes comprehensive test scripts",
            "- Each request has detailed descriptions",
            "- Environment variables are pre-configured",
            "- Folders organize methods by functionality"
        ])
        
        return "\n".join(report_lines) 