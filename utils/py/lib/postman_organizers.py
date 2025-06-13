#!/usr/bin/env python3
"""
Postman Collection Organizers

Handles organization of Postman requests into folders and categories.
Manages method categorization and folder structure generation.
"""

from typing import Dict, List
from dataclasses import dataclass

from .postman_requests import PostmanRequest


@dataclass
class PostmanFolder:
    """Represents a Postman folder containing related requests."""
    name: str
    description: str
    requests: List[PostmanRequest]
    subfolders: List['PostmanFolder']


class MethodCategorizer:
    """
    Categorizes API methods into logical groups for folder organization.
    """
    
    def __init__(self):
        # Method categorization configuration
        self.method_categories = {
            'activation': {
                'name': 'Coin & Token Activation',
                'description': 'Methods for activating coins, tokens, and blockchain protocols',
                'patterns': ['enable', 'activation', 'task::enable']
            },
            'lightning': {
                'name': 'Lightning Network',
                'description': 'Lightning Network channel and payment management',
                'patterns': ['lightning::', 'task::enable_lightning']
            },
            'trading': {
                'name': 'Trading & Orders',
                'description': 'Order placement, trading, and market operations',
                'patterns': ['buy', 'sell', 'setprice', 'cancel_order', 'orderbook', 'trade', 'swap', 'best_orders']
            },
            'wallet': {
                'name': 'Wallet Management',
                'description': 'Wallet operations, balances, and transaction management',
                'patterns': ['balance', 'withdraw', 'my_tx_history', 'get_wallet', 'get_public_key']
            },
            'streaming': {
                'name': 'Real-time Streaming',
                'description': 'WebSocket streaming endpoints for real-time data',
                'patterns': ['stream::']
            },
            'tasks': {
                'name': 'Task Management',
                'description': 'Asynchronous task operations and status monitoring',
                'patterns': ['task::', 'init', 'status', 'cancel', 'user_action']
            },
            'utility': {
                'name': 'Utility & Information',
                'description': 'General utility methods and system information',
                'patterns': ['version', 'metrics', 'get_', 'convert', 'sign_', 'verify_']
            }
        }
    
    def categorize_method(self, method_name: str) -> str:
        """
        Categorize a method based on its name patterns.
        
        Args:
            method_name: The method name to categorize
            
        Returns:
            Category name
        """
        method_lower = method_name.lower()
        
        for category, config in self.method_categories.items():
            for pattern in config['patterns']:
                if pattern.lower() in method_lower:
                    return category
        
        return 'utility'  # Default category
    
    def get_category_config(self, category: str) -> Dict[str, str]:
        """
        Get configuration for a specific category.
        
        Args:
            category: Category name
            
        Returns:
            Category configuration dict
        """
        return self.method_categories.get(category, {})


class FolderOrganizer:
    """
    Organizes Postman requests into a hierarchical folder structure.
    """
    
    def __init__(self, categorizer: MethodCategorizer):
        self.categorizer = categorizer
    
    def organize_requests_into_folders(self, categorized_requests: Dict[str, List[PostmanRequest]]) -> List[PostmanFolder]:
        """
        Organize categorized requests into a folder structure.
        
        Args:
            categorized_requests: Dictionary mapping categories to request lists
            
        Returns:
            List of organized folders
        """
        folders = []
        
        for category, requests in categorized_requests.items():
            if not requests:
                continue
            
            category_config = self.categorizer.get_category_config(category)
            
            # Group requests by base method name
            method_groups = self._group_requests_by_method(requests)
            
            # Organize into subfolders and direct requests
            subfolders, folder_requests = self._organize_method_groups(method_groups)
            
            # Create main category folder
            folder = PostmanFolder(
                name=category_config['name'],
                description=category_config['description'],
                requests=sorted(folder_requests, key=lambda x: x.name),
                subfolders=sorted(subfolders, key=lambda x: x.name)
            )
            folders.append(folder)
        
        return sorted(folders, key=lambda x: x.name)
    
    def _group_requests_by_method(self, requests: List[PostmanRequest]) -> Dict[str, List[PostmanRequest]]:
        """Group requests by their base method name."""
        method_groups = {}
        
        for request in requests:
            base_method = self._extract_base_method(request.method_name)
            if base_method not in method_groups:
                method_groups[base_method] = []
            method_groups[base_method].append(request)
        
        return method_groups
    
    def _extract_base_method(self, method_name: str) -> str:
        """Extract the base method name without operations."""
        if '::' in method_name:
            parts = method_name.split('::')
            if len(parts) > 1:
                return parts[0]
        elif '_' in method_name:
            parts = method_name.split('_')
            if len(parts) > 1:
                return parts[0]
        
        return method_name
    
    def _organize_method_groups(self, method_groups: Dict[str, List[PostmanRequest]]) -> tuple:
        """
        Organize method groups into subfolders and direct requests.
        
        Returns:
            Tuple of (subfolders, direct_requests)
        """
        subfolders = []
        folder_requests = []
        
        for method_name, method_requests in method_groups.items():
            # Create subfolder for methods with many requests
            if len(method_requests) > 3:
                subfolder = PostmanFolder(
                    name=self._format_method_name(method_name),
                    description=f"Examples for the {method_name} method",
                    requests=sorted(method_requests, key=lambda x: x.name),
                    subfolders=[]
                )
                subfolders.append(subfolder)
            else:
                # Add to main folder if few requests
                folder_requests.extend(method_requests)
        
        return subfolders, folder_requests
    
    def _format_method_name(self, method_name: str) -> str:
        """Format method name for display in folder names."""
        return method_name.replace('_', ' ').title()


class PostmanStructureBuilder:
    """
    Builds Postman collection structure from organized folders.
    """
    
    def folder_to_postman_item(self, folder: PostmanFolder) -> Dict:
        """
        Convert a PostmanFolder to Postman collection item format.
        
        Args:
            folder: The folder to convert
            
        Returns:
            Postman item dictionary
        """
        item = {
            "name": folder.name,
            "description": folder.description,
            "item": []
        }
        
        # Add direct requests
        for request in folder.requests:
            item["item"].append(self.request_to_postman_item(request))
        
        # Add subfolders
        for subfolder in folder.subfolders:
            item["item"].append(self.folder_to_postman_item(subfolder))
        
        return item
    
    def request_to_postman_item(self, request: PostmanRequest) -> Dict:
        """
        Convert a PostmanRequest to Postman collection item format.
        
        Args:
            request: The request to convert
            
        Returns:
            Postman request item dictionary
        """
        return {
            "name": request.name,
            "request": {
                "method": request.method,
                "header": request.headers,
                "body": {
                    "mode": "raw",
                    "raw": self._format_json_body(request.body),
                    "options": {
                        "raw": {
                            "language": "json"
                        }
                    }
                },
                "url": {
                    "raw": request.url,
                    "host": ["{{kdf_url}}"]
                },
                "description": request.description
            },
            "event": [
                {
                    "listen": "test",
                    "script": {
                        "type": "text/javascript",
                        "exec": request.tests.split('\n')
                    }
                }
            ]
        }
    
    def _format_json_body(self, body: Dict) -> str:
        """Format JSON body with proper indentation."""
        import json
        return json.dumps(body, indent=2) 