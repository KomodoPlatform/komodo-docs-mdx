#!/usr/bin/env python3
"""
Local KDF Repository Scanner

This module provides comprehensive method analysis for a locally cloned 
KDF repository including parameter extraction, types, descriptions, 
and more detailed information.

Integrates with the existing scanning infrastructure.
"""

import os
import subprocess
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from ..utils.logging_utils import get_logger
from ..constants import get_config


@dataclass
class MethodDetails:
    """Detailed information about a KDF method."""
    method_name: str
    handler_file: Optional[str] = None
    parameters: List[Dict[str, Any]] = None
    response_type: Optional[str] = None
    description: Optional[str] = None
    examples: List[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = None
    request_type: Optional[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.examples is None:
            self.examples = []
        if self.errors is None:
            self.errors = []


class LocalKDFScanner:
    """
    Comprehensive local KDF repository scanner that extracts detailed
    method information including parameters, types, descriptions, etc.
    """
    
    def __init__(self, repo_path: Optional[Path] = None, data_dir: Optional[Path] = None):
        self.logger = get_logger("local-kdf-scanner")
        self.script_dir = Path(__file__).parent.parent.parent
        self.repo_path = repo_path or (self.script_dir / "kdf_repo")
        self.data_dir = data_dir or (self.script_dir / "data")
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
    def setup_repository(self, branch: str = "dev", force_clone: bool = False) -> bool:
        """Clone or update the local KDF repository."""
        repo_url = "https://github.com/KomodoPlatform/komodo-defi-framework.git"
        
        if self.repo_path.exists() and not force_clone:
            self.logger.info(f"Repository already exists at {self.repo_path}")
            self.logger.info("Pulling latest changes...")
            try:
                subprocess.run(
                    ["git", "pull", "origin", branch], 
                    cwd=self.repo_path, 
                    check=True,
                    capture_output=True
                )
                self.logger.success("Repository updated successfully")
                return True
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to update repository: {e}")
                self.logger.info("Trying to clone fresh...")
        
        if self.repo_path.exists():
            self.logger.info(f"Removing existing repository at {self.repo_path}")
            import shutil
            shutil.rmtree(self.repo_path)
        
        self.logger.info(f"Cloning KDF repository (branch: {branch})...")
        try:
            subprocess.run([
                "git", "clone", "--depth", "1", "--branch", branch,
                repo_url, str(self.repo_path)
            ], check=True, capture_output=True)
            self.logger.success("Repository cloned successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to clone repository: {e}")
            return False
    
    def find_method_files(self) -> Dict[str, List[Path]]:
        """Find all files that contain method implementations."""
        if not self.repo_path.exists():
            raise FileNotFoundError(f"Repository not found at {self.repo_path}")
        
        # Key directories to scan for method implementations
        search_dirs = [
            self.repo_path / "mm2src" / "mm2_main" / "src" / "rpc",
            self.repo_path / "mm2src" / "coins",
            self.repo_path / "mm2src" / "mm2_main" / "src" / "lp_swap",
            self.repo_path / "mm2src" / "mm2_main" / "src" / "lp_ordermatch",
        ]
        
        method_files = {
            "dispatchers": [],
            "handlers": [],
            "structs": [],
            "tests": []
        }
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            # Find Rust files
            for rust_file in search_dir.rglob("*.rs"):
                try:
                    file_content = rust_file.read_text(encoding='utf-8', errors='ignore')
                    
                    # Categorize files based on content
                    if "dispatcher" in rust_file.name.lower():
                        method_files["dispatchers"].append(rust_file)
                    elif any(pattern in file_content for pattern in [
                        "pub async fn", "fn rpc_", "RpcMethod", "#[derive"
                    ]):
                        if "struct" in file_content and "#[derive" in file_content:
                            method_files["structs"].append(rust_file)
                        if "pub async fn" in file_content or "fn rpc_" in file_content:
                            method_files["handlers"].append(rust_file)
                    elif "test" in rust_file.name.lower():
                        method_files["tests"].append(rust_file)
                except Exception as e:
                    self.logger.warning(f"Error reading {rust_file}: {e}")
                    continue
        
        return method_files
    
    def extract_method_details(self, method_name: str) -> MethodDetails:
        """Extract detailed information about a specific method."""
        method_info = MethodDetails(method_name=method_name)
        
        if not self.repo_path.exists():
            return method_info
        
        # Search for method handler
        handler_patterns = [
            rf"pub async fn {method_name.replace('::', '_')}_rpc",
            rf"pub async fn rpc_{method_name.replace('::', '_')}",
            rf"async fn {method_name.replace('::', '_')}",
            rf'"{method_name}"\s*=>\s*(\w+)',
        ]
        
        method_files = self.find_method_files()
        
        # Search handler files
        for handler_file in method_files["handlers"]:
            try:
                content = handler_file.read_text(encoding='utf-8', errors='ignore')
                
                for pattern in handler_patterns:
                    if re.search(pattern, content):
                        method_info.handler_file = str(handler_file)
                        method_info = self._extract_from_handler(content, method_info)
                        break
                        
                if method_info.handler_file:
                    break
                    
            except Exception as e:
                self.logger.warning(f"Error reading {handler_file}: {e}")
                continue
        
        # Search for struct definitions in struct files
        if method_info.parameters:
            method_info = self._enhance_with_struct_info(method_info, method_files["structs"])
        
        return method_info
    
    def _extract_from_handler(self, content: str, method_info: MethodDetails) -> MethodDetails:
        """Extract information from a method handler file."""
        
        # Extract function signature and parameters
        func_patterns = [
            r'pub async fn \w+\s*\([^)]*req:\s*(\w+)[^)]*\)',
            r'async fn \w+\s*\([^)]*req:\s*(\w+)[^)]*\)',
        ]
        
        for pattern in func_patterns:
            match = re.search(pattern, content)
            if match:
                request_type = match.group(1)
                method_info.request_type = request_type
                
                # Find the struct definition for this request type
                struct_pattern = rf'#\[derive[^\]]*\]\s*pub struct {request_type}\s*\{{([^}}]*)\}}'
                struct_match = re.search(struct_pattern, content, re.MULTILINE | re.DOTALL)
                
                if struct_match:
                    method_info.parameters = self._parse_struct_fields(struct_match.group(1))
                break
        
        # Extract description from comments
        doc_comments = re.findall(r'///\s*(.+)', content)
        if doc_comments:
            method_info.description = " ".join(doc_comments).strip()
        
        # Extract response type
        response_patterns = [
            r'-> Result<(\w+),',
            r'-> (\w+Result)',
            r'-> RpcResult<(\w+)>',
        ]
        
        for pattern in response_patterns:
            match = re.search(pattern, content)
            if match:
                method_info.response_type = match.group(1)
                break
        
        return method_info
    
    def _parse_struct_fields(self, struct_body: str) -> List[Dict[str, Any]]:
        """Parse struct fields to extract parameter information."""
        parameters = []
        
        # Split by lines and process each field
        lines = struct_body.strip().split('\n')
        current_field = {}
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('//'):
                continue
            
            # Check for field documentation
            if line.startswith('///'):
                current_field["description"] = line[3:].strip()
                continue
            
            # Check for serde attributes
            if line.startswith('#[serde'):
                serde_attrs = re.findall(r'(\w+)\s*=\s*"([^"]*)"', line)
                for attr_name, attr_value in serde_attrs:
                    if attr_name == "default":
                        current_field["default"] = attr_value
                    elif attr_name == "skip_serializing_if":
                        current_field["optional"] = True
                continue
            
            # Parse field definition
            field_match = re.match(r'pub\s+(\w+):\s*(.+?)(?:,|$)', line)
            if field_match:
                field_name = field_match.group(1)
                field_type = field_match.group(2).strip().rstrip(',')
                
                # Determine if optional
                is_optional = field_type.startswith('Option<') or current_field.get("optional", False)
                
                # Clean up type
                if field_type.startswith('Option<') and field_type.endswith('>'):
                    field_type = field_type[7:-1]  # Remove Option<...>
                
                parameters.append({
                    "name": field_name,
                    "type": field_type,
                    "required": not is_optional,
                    "description": current_field.get("description", ""),
                    "default": current_field.get("default")
                })
                
                current_field = {}  # Reset for next field
        
        return parameters
    
    def _enhance_with_struct_info(self, method_info: MethodDetails, struct_files: List[Path]) -> MethodDetails:
        """Enhance method info with additional struct information."""
        # This could search for more detailed struct definitions
        # in separate files if the request/response types are defined elsewhere
        return method_info
    
    def scan_missing_methods(self, missing_methods_data: Optional[Dict] = None) -> Dict[str, MethodDetails]:
        """Scan all missing methods for detailed information."""
        if missing_methods_data is None:
            # Load from unified mapping
            unified_mapping_path = self.data_dir / "unified_method_mapping.json"
            
            if not unified_mapping_path.exists():
                self.logger.error(f"Missing methods file not found: {unified_mapping_path}")
                return {}
            
            with open(unified_mapping_path) as f:
                data = json.load(f)
            
            missing_methods_data = data.get('missing', {}).get('methods_lacking_coverage', {})
        
        detailed_info = {}
        
        for version, methods in missing_methods_data.items():
            self.logger.info(f"Scanning {version.upper()} methods ({len(methods)} total)")
            detailed_info[version] = {}
            
            for i, method in enumerate(methods, 1):
                self.logger.debug(f"Analyzing {method} ({i}/{len(methods)})")
                method_details = self.extract_method_details(method)
                detailed_info[version][method] = method_details
        
        return detailed_info
    
    def save_detailed_analysis(self, detailed_info: Dict[str, MethodDetails], 
                              filename: Optional[str] = None) -> str:
        """Save the detailed analysis to a file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"kdf_detailed_method_analysis_{timestamp}.json"
        
        output_path = self.data_dir / filename
        
        # Convert MethodDetails objects to dicts for JSON serialization
        serializable_data = {}
        for version, methods in detailed_info.items():
            serializable_data[version] = {}
            for method_name, method_details in methods.items():
                if isinstance(method_details, MethodDetails):
                    serializable_data[version][method_name] = {
                        "method_name": method_details.method_name,
                        "handler_file": method_details.handler_file,
                        "parameters": method_details.parameters,
                        "response_type": method_details.response_type,
                        "description": method_details.description,
                        "request_type": method_details.request_type,
                        "examples": method_details.examples,
                        "errors": method_details.errors
                    }
                else:
                    serializable_data[version][method_name] = method_details
        
        with open(output_path, 'w') as f:
            json.dump(serializable_data, f, indent=2, default=str)
        
        self.logger.success(f"Detailed analysis saved to: {output_path}")
        return str(output_path)


# Convenience functions for backward compatibility
def setup_local_kdf_repo(branch: str = "dev", force_clone: bool = False) -> bool:
    """Convenience function to setup local KDF repository."""
    scanner = LocalKDFScanner()
    return scanner.setup_repository(branch, force_clone)


def scan_local_methods(method_names: List[str]) -> Dict[str, MethodDetails]:
    """Convenience function to scan specific methods."""
    scanner = LocalKDFScanner()
    results = {}
    
    for method_name in method_names:
        results[method_name] = scanner.extract_method_details(method_name)
    
    return results 