#!/usr/bin/env python3
"""
Repository Scanner

Scans the Komodo DeFi Framework repository to extract RPC method definitions
directly from the Rust source code. Provides up-to-date method information
for validation and documentation purposes.
"""

import re
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

from .logging_utils import get_logger
from .shared_utils import safe_write_json, ensure_directory_exists, normalize_file_path
from .base_file_manager import BaseFileManager
from .cache import cached
from .observers import publish_operation_started, publish_operation_completed, publish_operation_failed
from .method_normalizer import MethodNameNormalizer


@dataclass
class RepositoryInfo:
    """Information about a repository branch and its method extraction."""
    branch: str
    version: str
    url: str
    methods: List[str]
    last_updated: datetime
    commit_hash: Optional[str] = None
    extraction_patterns_used: List[str] = None


class KDFRepositoryScanner(BaseFileManager):
    """
    Scanner for extracting RPC method names from KDF repository source code.
    
    Fetches method definitions directly from GitHub repository to ensure
    documentation stays in sync with actual implementation.
    """
    
    def __init__(self, base_directory: Union[str, Path] = "data", 
                 default_branch: str = "dev", verbose: bool = True):
        super().__init__(base_directory, verbose)
        
        self.default_branch = default_branch
        self.logger = get_logger("kdf-repo-scanner")
        
        # Ensure data directory exists
        self.data_dir = self.base_directory 
        ensure_directory_exists(self.data_dir)
        
        # Method extraction patterns for different Rust code patterns
        self.method_patterns = [
            r'register_method\s*\(\s*"([^"]+)"',        # register_method("method")
            r'"([a-zA-Z0-9_:]+)"\s*=>',                 # "method" =>
            r'Some\s*\(\s*"([a-zA-Z0-9_:]+)"\s*\)',     # Some("method")
            r'rpc_match!\s*\(\s*"([^"]+)"',             # rpc_match!("method")
            r'method:\s*"([a-zA-Z0-9_:]+)"',            # method: "method"
            r'Method::([A-Za-z0-9_]+)',                 # Method::MethodName
        ]
        
        # Repository URL templates
        self.url_templates = {
            "v1": "https://raw.githubusercontent.com/KomodoPlatform/komodo-defi-framework/{branch}/mm2src/mm2_main/src/rpc/dispatcher/dispatcher_legacy.rs",
            "v2": "https://raw.githubusercontent.com/KomodoPlatform/komodo-defi-framework/{branch}/mm2src/mm2_main/src/rpc/dispatcher/dispatcher.rs"
        }
        
        # Cache settings
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
        
        if self.verbose:
            self.logger.info(f"Initialized KDF repository scanner for branch: {default_branch}")
    
    def get_repository_urls(self, branch: str = None) -> Dict[str, str]:
        """
        Get repository URLs for different API versions.
        
        Args:
            branch: Git branch to scan (defaults to default_branch)
            
        Returns:
            Dictionary mapping versions to repository URLs
        """
        if branch is None:
            branch = self.default_branch
        
        return {
            version: template.format(branch=branch)
            for version, template in self.url_templates.items()
        }
    
    @cached(namespace="kdf_repository", ttl_seconds=3600, 
            key_func=lambda self, url, version: {"url": url, "version": version})
    def fetch_source_content(self, url: str, version: str) -> Optional[str]:
        """
        Fetch source code content from repository URL.
        
        Args:
            url: Repository URL to fetch
            version: API version for logging
            
        Returns:
            Source code content or None if fetch fails
        """
        try:
            if self.verbose:
                self.logger.info(f"Fetching {version} source from repository")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            if self.verbose:
                self.logger.success(f"Successfully fetched {version} source ({len(response.text):,} chars)")
            
            return response.text
            
        except requests.RequestException as e:
            if self.verbose:
                self.logger.error(f"Failed to fetch {version} source: {e}")
            return None
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Unexpected error fetching {version} source: {e}")
            return None
    
    def extract_methods_from_source(self, source_content: str, version: str) -> Set[str]:
        """
        Extract RPC method names from Rust source code.
        
        Args:
            source_content: Rust source code content
            version: API version for logging
            
        Returns:
            Set of extracted method names with proper prefixes
        """
        methods = set()
        
        # Handle V1 and V2 differently due to different dispatcher structures
        if version == "v1":
            # V1 uses a simple match pattern in the main dispatcher function
            v1_methods = self._extract_legacy_dispatcher_methods(source_content)
            methods.update(v1_methods)
            
            if self.verbose:
                self.logger.info(f"{version}: Extracted {len(methods)} methods")
                self.logger.info(f"  - direct: {len(v1_methods)} methods")
        else:
            # V2 uses structured dispatcher functions with prefixes
            # 1. Task dispatcher methods (task::)
            task_methods = self._extract_task_dispatcher_methods(source_content)
            for method in task_methods:
                methods.add(f"task::{method}")
            
            # 2. Lightning dispatcher methods (lightning::)
            lightning_methods = self._extract_lightning_dispatcher_methods(source_content)
            for method in lightning_methods:
                methods.add(f"lightning::{method}")
            
            # 3. Streaming dispatcher methods (stream::)
            streaming_methods = self._extract_streaming_dispatcher_methods(source_content)
            for method in streaming_methods:
                methods.add(f"stream::{method}")
            
            # 4. GUI Storage dispatcher methods (gui_storage::)
            gui_storage_methods = self._extract_gui_storage_dispatcher_methods(source_content)
            for method in gui_storage_methods:
                methods.add(f"gui_storage::{method}")
            
            # 5. Staking dispatcher methods (experimental::staking::)
            staking_methods = self._extract_staking_dispatcher_methods(source_content)
            for method in staking_methods:
                methods.add(f"experimental::staking::{method}")
            
            # 6. Direct methods (no prefix) from main dispatcher
            direct_methods = self._extract_direct_dispatcher_methods(source_content)
            methods.update(direct_methods)
            
            if self.verbose:
                total_methods = len(methods)
                self.logger.info(f"{version}: Extracted {total_methods} methods with proper prefixes")
                self.logger.info(f"  - task:: {len(task_methods)} methods")
                self.logger.info(f"  - lightning:: {len(lightning_methods)} methods")
                self.logger.info(f"  - stream:: {len(streaming_methods)} methods") 
                self.logger.info(f"  - gui_storage:: {len(gui_storage_methods)} methods")
                self.logger.info(f"  - experimental::staking:: {len(staking_methods)} methods")
                self.logger.info(f"  - direct: {len(direct_methods)} methods")
        
        return methods
    
    def _extract_task_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from rpc_task_dispatcher function."""
        methods = set()
        
        # Find the task dispatcher function
        task_pattern = r'async fn rpc_task_dispatcher\([^)]*\)[^{]*\{[\s\S]*?match task_method\.as_str\(\) \{([\s\S]*?)\s*\}\s*\}'
        match = re.search(task_pattern, source_content, re.MULTILINE)
        
        if match:
            match_block = match.group(1)
            # Extract quoted method names from match arms
            method_pattern = r'"([^"]+)"\s*=>'
            found_methods = re.findall(method_pattern, match_block)
            
            # Also look for conditional compilation blocks
            native_pattern = r'native_only_methods => match native_only_methods \{([\s\S]*?)\}'
            native_match = re.search(native_pattern, match_block)
            if native_match:
                native_block = native_match.group(1)
                native_methods = re.findall(method_pattern, native_block)
                found_methods.extend(native_methods)
            
            wasm_pattern = r'wasm_only_methods => match wasm_only_methods \{([\s\S]*?)\}'
            wasm_match = re.search(wasm_pattern, match_block)
            if wasm_match:
                wasm_block = wasm_match.group(1)
                wasm_methods = re.findall(method_pattern, wasm_block)
                found_methods.extend(wasm_methods)
            
            methods.update(found_methods)
        
        return methods
    
    def _extract_lightning_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from lightning_dispatcher function."""
        methods = set()
        
        # Find the lightning dispatcher function  
        lightning_pattern = r'async fn lightning_dispatcher\([^)]*\)[^{]*\{[\s\S]*?match lightning_method \{([\s\S]*?)\s*\}\s*\}'
        match = re.search(lightning_pattern, source_content, re.MULTILINE)
        
        if match:
            match_block = match.group(1)
            # Extract quoted method names from match arms
            method_pattern = r'"([^"]+)"\s*=>'
            found_methods = re.findall(method_pattern, match_block)
            methods.update(found_methods)
        
        return methods
    
    def _extract_streaming_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from rpc_streaming_dispatcher function."""
        methods = set()
        
        # Find the streaming dispatcher function
        streaming_pattern = r'async fn rpc_streaming_dispatcher\([^)]*\)[^{]*\{[\s\S]*?match streaming_request\.as_str\(\) \{([\s\S]*?)\s*\}\s*\}'
        match = re.search(streaming_pattern, source_content, re.MULTILINE)
        
        if match:
            match_block = match.group(1)
            # Extract quoted method names from match arms
            method_pattern = r'"([^"]+)"\s*=>'
            found_methods = re.findall(method_pattern, match_block)
            methods.update(found_methods)
        
        return methods
    
    def _extract_gui_storage_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from gui_storage_dispatcher function."""
        methods = set()
        
        # Find the gui_storage dispatcher function
        gui_storage_pattern = r'async fn gui_storage_dispatcher\([^)]*\)[^{]*\{[\s\S]*?match gui_storage_method \{([\s\S]*?)\s*\}\s*\}'
        match = re.search(gui_storage_pattern, source_content, re.MULTILINE)
        
        if match:
            match_block = match.group(1)
            # Extract quoted method names from match arms
            method_pattern = r'"([^"]+)"\s*=>'
            found_methods = re.findall(method_pattern, match_block)
            methods.update(found_methods)
        
        return methods
    
    def _extract_staking_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from staking_dispatcher function."""
        methods = set()
        
        # Find the staking dispatcher function
        staking_pattern = r'async fn staking_dispatcher\([^)]*\)[^{]*\{([\s\S]*?)\s*\}\s*$'
        match = re.search(staking_pattern, source_content, re.MULTILINE)
        
        if match:
            staking_block = match.group(1)
            
            # Extract methods from the nested query_dispatcher function
            query_pattern = r'async fn query_dispatcher\([^)]*\)[^{]*\{[\s\S]*?match staking_query_method \{([\s\S]*?)\s*\}\s*\}'
            query_match = re.search(query_pattern, staking_block)
            
            if query_match:
                query_match_block = query_match.group(1)
                query_method_pattern = r'"([^"]+)"\s*=>'
                query_methods = re.findall(query_method_pattern, query_match_block)
                # Add query:: prefix to these methods
                for query_method in query_methods:
                    methods.add(f"query::{query_method}")
            
            # Extract methods from the main staking match block
            main_method_pattern = r'match staking_method \{([\s\S]*?)\s*\}\s*$'
            main_match = re.search(main_method_pattern, staking_block)
            
            if main_match:
                main_match_block = main_match.group(1)
                method_pattern = r'"([^"]+)"\s*=>'
                found_methods = re.findall(method_pattern, main_match_block)
                methods.update(found_methods)
        
        return methods
    
    def _extract_direct_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from main dispatcher_v2 function that don't have prefixes."""
        methods = set()
        
        # Find the main dispatcher_v2 function match block
        dispatcher_pattern = r'async fn dispatcher_v2\([^)]*\)[^{]*\{[\s\S]*?match request\.method\.as_str\(\) \{([\s\S]*?)\s*\}\s*\}'
        match = re.search(dispatcher_pattern, source_content, re.MULTILINE)
        
        if match:
            match_block = match.group(1)
            # Extract quoted method names from match arms
            method_pattern = r'"([^"]+)"\s*=>'
            found_methods = re.findall(method_pattern, match_block)
            methods.update(found_methods)
        
        return methods
    
    def _extract_legacy_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from legacy dispatcher function (V1 API)."""
        methods = set()
        
        # Find the main dispatcher function and its match block
        # Looking for: DispatcherRes::Match(match &method[..] {
        dispatcher_pattern = r'DispatcherRes::Match\(match\s+&method\[..\]\s*\{([\s\S]*?)\s*\}\)'
        match = re.search(dispatcher_pattern, source_content, re.MULTILINE)
        
        if match:
            match_block = match.group(1)
            # Extract quoted method names from match arms
            # Pattern: "method_name" => 
            method_pattern = r'"([^"]+)"\s*=>'
            found_methods = re.findall(method_pattern, match_block)
            methods.update(found_methods)
        
        return methods
    
    def scan_repository_methods(self, branch: str = None, 
                               versions: List[str] = None) -> Dict[str, RepositoryInfo]:
        """
        Scan repository for RPC methods across specified versions.
        
        Args:
            branch: Git branch to scan
            versions: List of API versions to scan
            
        Returns:
            Dictionary mapping versions to RepositoryInfo objects
        """
        if branch is None:
            branch = self.default_branch
        
        if versions is None:
            versions = ['v1', 'v2']
        
        publish_operation_started("KDFRepositoryScanner", f"scan_repository_methods", len(versions))
        
        results = {}
        urls = self.get_repository_urls(branch)
        
        for version in versions:
            if version not in urls:
                if self.verbose:
                    self.logger.warning(f"No URL configured for version {version}")
                continue
            
            try:
                url = urls[version]
                
                # Fetch source content
                source_content = self.fetch_source_content(url, version)
                if source_content is None:
                    results[version] = RepositoryInfo(
                        branch=branch,
                        version=version,
                        url=url,
                        methods=[],
                        last_updated=datetime.now(),
                        extraction_patterns_used=[]
                    )
                    continue
                
                # Extract methods
                method_set = self.extract_methods_from_source(source_content, version)
                methods = sorted(list(method_set))
                
                # Create repository info
                results[version] = RepositoryInfo(
                    branch=branch,
                    version=version,
                    url=url,
                    methods=methods,
                    last_updated=datetime.now(),
                    extraction_patterns_used=self.method_patterns
                )
                
                if self.verbose:
                    self.logger.success(f"{version}: Found {len(methods)} methods")
            
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"Error scanning {version}: {e}")
                
                results[version] = RepositoryInfo(
                    branch=branch,
                    version=version,
                    url=urls.get(version, ""),
                    methods=[],
                    last_updated=datetime.now(),
                    extraction_patterns_used=[]
                )
        
        publish_operation_completed("KDFRepositoryScanner", f"scan_repository_methods")
        return results
    
    def save_repository_methods(self, repo_info: Dict[str, RepositoryInfo], 
                               filename: str = None) -> str:
        """
        Save repository method information to JSON file.
        
        Args:
            repo_info: Dictionary of RepositoryInfo objects
            filename: Output filename (auto-generated if None)
            
        Returns:
            Path to saved file
        """
        if filename is None:
            filename = "kdf_repo_methods.json"
        filepath = self.data_dir / filename
        
        # Convert to serializable format
        data = {
            "scan_metadata": {
                "scan_time": datetime.now().isoformat(),
                "total_versions": len(repo_info),
                "scanner_version": "2.0.0"
            },
            "methods_by_version": {}
        }
        
        for version, info in repo_info.items():
            data["methods_by_version"][version] = {
                "branch": info.branch,
                "url": info.url,
                "methods": info.methods,
                "method_count": len(info.methods),
                "last_updated": info.last_updated.isoformat(),
                "commit_hash": info.commit_hash,
                "extraction_patterns_count": len(info.extraction_patterns_used or [])
            }
        
        # Save to file
        safe_write_json(filepath, data, indent=2)
        
        if self.verbose:
            total_methods = sum(len(info.methods) for info in repo_info.values())
            self.logger.success(f"Saved {total_methods} methods across {len(repo_info)} versions to: {filepath}")
        
        return str(filepath)
    
    def load_repository_methods(self, filename: str = None) -> Optional[Dict[str, RepositoryInfo]]:
        """
        Load repository method information from JSON file.
        
        Args:
            filename: File to load (loads latest if None)
            
        Returns:
            Dictionary of RepositoryInfo objects or None if not found
        """
        if filename is None:
            # Find the latest file
            pattern = "kdf_repo_methods*.json"
            files = list(self.data_dir.glob(pattern))
            
            if not files:
                if self.verbose:
                    self.logger.warning("No repository method files found")
                return None
            
            # Get the most recent file
            latest_file = max(files, key=lambda f: f.stat().st_mtime)
            filepath = latest_file
        else:
            filepath = self.data_dir / filename
        
        try:
            data = self.read_json_file(filepath)
            
            # Convert back to RepositoryInfo objects
            repo_info = {}
            methods_data = data.get("methods_by_version", {})
            
            for version, version_data in methods_data.items():
                repo_info[version] = RepositoryInfo(
                    branch=version_data.get("branch", "unknown"),
                    version=version,
                    url=version_data.get("url", ""),
                    methods=version_data.get("methods", []),
                    last_updated=datetime.fromisoformat(version_data.get("last_updated", datetime.now().isoformat())),
                    commit_hash=version_data.get("commit_hash"),
                    extraction_patterns_used=[]  # Not stored in detail
                )
            
            if self.verbose:
                total_methods = sum(len(info.methods) for info in repo_info.values())
                self.logger.info(f"Loaded {total_methods} methods across {len(repo_info)} versions from: {filepath}")
            
            return repo_info
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error loading repository methods from {filepath}: {e}")
            return None
    
    def compare_with_documentation(self, repo_methods: Dict[str, RepositoryInfo],
                                  doc_methods: Dict[str, List[str]]) -> Dict[str, Dict[str, List[str]]]:
        """
        Compare repository methods with documented methods.
        
        Args:
            repo_methods: Methods from repository scan
            doc_methods: Methods from documentation scan
            
        Returns:
            Comparison results with missing/extra methods
        """
        comparison = {}
        
        def normalize_for_comparison(method_name: str) -> str:
            """Normalize method name for comparison by converting :: to -"""
            return method_name.replace('::', '-').lower()
        
        for version in repo_methods.keys():
            repo_set = set(repo_methods[version].methods)
            doc_set = set(doc_methods.get(version, []))
            
            # Deduplicate documentation methods first
            doc_deduplicated = {}
            for method in doc_set:
                normalized_key = normalize_for_comparison(method)
                if normalized_key not in doc_deduplicated:
                    # Keep the first occurrence (prefer :: format over - format)
                    doc_deduplicated[normalized_key] = method
                else:
                    # If current method has :: and stored one has -, replace it
                    if '::' in method and '::' not in doc_deduplicated[normalized_key]:
                        doc_deduplicated[normalized_key] = method
            
            # Use deduplicated documentation methods
            doc_set_deduplicated = set(doc_deduplicated.values())
            
            # Create normalized mapping for comparison
            repo_normalized = {}
            doc_normalized = {}
            
            # Normalize repository methods
            for method in repo_set:
                normalized_key = normalize_for_comparison(method)
                if normalized_key not in repo_normalized:
                    repo_normalized[normalized_key] = []
                repo_normalized[normalized_key].append(method)
            
            # Normalize deduplicated documentation methods
            for method in doc_set_deduplicated:
                normalized_key = normalize_for_comparison(method)
                if normalized_key not in doc_normalized:
                    doc_normalized[normalized_key] = []
                doc_normalized[normalized_key].append(method)
            
            # Find matches using normalized keys
            repo_normalized_keys = set(repo_normalized.keys())
            doc_normalized_keys = set(doc_normalized.keys())
            
            # Methods that are in repo but not in docs (after normalization)
            repo_only_normalized = repo_normalized_keys - doc_normalized_keys
            repo_only = []
            for key in repo_only_normalized:
                repo_only.extend(repo_normalized[key])
            
            # Methods that are in docs but not in repo (after normalization)
            doc_only_normalized = doc_normalized_keys - repo_normalized_keys
            doc_only = []
            for key in doc_only_normalized:
                doc_only.extend(doc_normalized[key])
            
            # Common methods (intersection after normalization)
            common_normalized = repo_normalized_keys & doc_normalized_keys
            common = []
            for key in common_normalized:
                # Include both repo and doc variations for completeness
                common.extend(repo_normalized[key])
                common.extend(doc_normalized[key])
            
            # Remove duplicates from common while preserving order
            common = list(dict.fromkeys(common))
            
            comparison[version] = {
                "repo_only": sorted(repo_only),
                "doc_only": sorted(doc_only),
                "common": sorted(common),
                "repo_count": len(repo_set),
                "doc_count": len(doc_set_deduplicated),  # Use deduplicated count
                "common_count": len(common_normalized),
                "coverage_percentage": (len(common_normalized) / max(1, len(repo_normalized_keys))) * 100
            }
        
        return comparison
    
    def generate_comparison_report(self, comparison: Dict[str, Dict[str, List[str]]]) -> str:
        """
        Generate a formatted comparison report.
        
        Args:
            comparison: Results from compare_with_documentation
            
        Returns:
            Formatted report string
        """
        report_lines = [
            "🔍 KDF Repository vs Documentation Comparison",
            "=" * 50,
            ""
        ]
        
        for version, results in comparison.items():
            report_lines.extend([
                f"{version.upper()} API:",
                f"  Repository methods: {results['repo_count']}",
                f"  Documented methods: {results['doc_count']}",
                f"  Common methods: {results['common_count']}",
                f"  Coverage: {results['coverage_percentage']:.1f}%",
                ""
            ])
            
            if results['repo_only']:
                report_lines.extend([
                    f"  📋 Methods in repository but not documented ({len(results['repo_only'])}):",
                    *[f"    - {method}" for method in results['repo_only'][:10]],
                    f"    ... and {len(results['repo_only']) - 10} more" if len(results['repo_only']) > 10 else "",
                    ""
                ])
            
            if results['doc_only']:
                report_lines.extend([
                    f"  📚 Methods documented but not in repository ({len(results['doc_only'])}):",
                    *[f"    - {method}" for method in results['doc_only'][:10]],
                    f"    ... and {len(results['doc_only']) - 10} more" if len(results['doc_only']) > 10 else "",
                    ""
                ])
        
        return "\n".join(report_lines)
    
    def get_latest_methods(self, branch: str = None, force_refresh: bool = False) -> Dict[str, List[str]]:
        """
        Get the latest methods, using cache if available.
        
        Args:
            branch: Git branch to scan
            force_refresh: Force refresh even if cache is valid
            
        Returns:
            Dictionary mapping versions to method lists
        """
        if not force_refresh:
            # Try to load from cache first
            cached_data = self.load_repository_methods()
            if cached_data:
                # Check if cache is still valid
                now = datetime.now()
                for info in cached_data.values():
                    if now - info.last_updated < self.cache_duration:
                        # Cache is valid, return cached data
                        return {version: info.methods for version, info in cached_data.items()}
        
        # Cache is invalid or force refresh requested
        if self.verbose:
            self.logger.info("Refreshing repository methods from source...")
        
        repo_info = self.scan_repository_methods(branch)
        self.save_repository_methods(repo_info)
        
        return {version: info.methods for version, info in repo_info.items()}


# Convenience functions
def scan_kdf_repository(branch: str = "dev", versions: List[str] = None, 
                       verbose: bool = True) -> Dict[str, List[str]]:
    """
    Convenience function to quickly scan KDF repository for methods.
    
    Args:
        branch: Git branch to scan
        versions: API versions to scan
        verbose: Enable verbose output
        
    Returns:
        Dictionary mapping versions to method lists
    """
    scanner = KDFRepositoryScanner(default_branch=branch, verbose=verbose)
    return scanner.get_latest_methods(branch, force_refresh=True)


def compare_repo_with_docs(doc_methods: Dict[str, List[str]], 
                          branch: str = "dev", verbose: bool = True) -> Dict[str, Dict[str, List[str]]]:
    """
    Convenience function to compare repository methods with documentation.
    
    Args:
        doc_methods: Methods from documentation
        branch: Git branch to scan
        verbose: Enable verbose output
        
    Returns:
        Comparison results
    """
    scanner = KDFRepositoryScanner(default_branch=branch, verbose=verbose)
    repo_info = scanner.scan_repository_methods(branch)
    return scanner.compare_with_documentation(repo_info, doc_methods) 