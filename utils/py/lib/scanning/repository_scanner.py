#!/usr/bin/env python3
"""
KDF Repository Scanner - Consolidated

This module handles all aspects of scanning the KDF repository for API method names,
including fetching source code from remote repositories and extracting method names
from Rust dispatcher code.

Consolidated from previously separate components:
- RepositoryFetcher: HTTP fetching of source code
- MethodExtractor: Regex-based method extraction from Rust code
- KDFRepositoryScanner: Coordination and high-level scanning logic
"""

import re
import requests
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..utils.logging_utils import get_logger
from ..utils import normalize_method_name


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


class RepositoryFetcher:
    """
    Handles fetching source code from remote repositories.
    """
    
    def __init__(self, default_branch: str = "dev", cache_duration_hours: int = 1, verbose: bool = True):
        self.default_branch = default_branch
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self.verbose = verbose
        self.logger = get_logger("repo-fetcher")
        
        # Repository URL templates
        self.url_templates = {
            "v1": "https://raw.githubusercontent.com/KomodoPlatform/komodo-defi-framework/{branch}/mm2src/mm2_main/src/rpc/dispatcher/dispatcher_legacy.rs",
            "v2": "https://raw.githubusercontent.com/KomodoPlatform/komodo-defi-framework/{branch}/mm2src/mm2_main/src/rpc/dispatcher/dispatcher.rs"
        }
    
    def get_repository_urls(self, branch: str = None) -> Dict[str, str]:
        """Get repository URLs for different API versions."""
        if branch is None:
            branch = self.default_branch
        
        return {
            version: template.format(branch=branch)
            for version, template in self.url_templates.items()
        }
    
    def fetch_source_content(self, url: str, version: str) -> Optional[str]:
        """Fetch source code content from repository URL."""
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


class MethodExtractor:
    """
    Extracts RPC method names from Rust source code.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = get_logger("method-extractor")
        
        # Method extraction patterns for different Rust code patterns
        self.method_patterns = [
            r'register_method\s*\(\s*"([^"]+)"',        # register_method("method")
            r'"([a-zA-Z0-9_:]+)"\s*=>',                 # "method" =>
            r'Some\s*\(\s*"([a-zA-Z0-9_:]+)"\s*\)',     # Some("method")
            r'rpc_match!\s*\(\s*"([^"]+)"',             # rpc_match!("method")
            r'method:\s*"([a-zA-Z0-9_:]+)"',            # method: "method"
            r'Method::([A-Za-z0-9_]+)',                 # Method::MethodName
        ]
    
    def extract_methods_from_source(self, source_content: str, version: str) -> Set[str]:
        """Extract RPC method names from Rust source code."""
        methods = set()
        
        # Extract methods based on version-specific patterns
        if version == 'v1':
            v1_methods = self._extract_legacy_dispatcher_methods(source_content)
            v1_methods.update(self._extract_direct_dispatcher_methods(source_content))
            methods.update(v1_methods)
        else:
            # V2 API - multiple dispatcher types
            task_methods = self._extract_task_dispatcher_methods(source_content)
            lightning_methods = self._extract_lightning_dispatcher_methods(source_content)
            streaming_methods = self._extract_streaming_dispatcher_methods(source_content)
            gui_storage_methods = self._extract_gui_storage_dispatcher_methods(source_content)
            staking_methods = self._extract_staking_dispatcher_methods(source_content)
            direct_methods = self._extract_direct_dispatcher_methods(source_content)
            
            methods.update(task_methods)
            methods.update(lightning_methods)
            methods.update(streaming_methods)
            methods.update(gui_storage_methods)
            methods.update(staking_methods)
            methods.update(direct_methods)
            
            total_methods = len(methods)
            if self.verbose:
                self.logger.debug(f"{version}: Extracted {total_methods} methods with proper prefixes")
                self.logger.debug(f"  - task:: {len(task_methods)} methods")
                self.logger.debug(f"  - lightning:: {len(lightning_methods)} methods")
                self.logger.debug(f"  - stream:: {len(streaming_methods)} methods")
                self.logger.debug(f"  - gui_storage:: {len(gui_storage_methods)} methods")
                self.logger.debug(f"  - experimental::staking:: {len(staking_methods)} methods")
                self.logger.debug(f"  - direct: {len(direct_methods)} methods")
        
        return methods
    
    def _extract_dispatcher_methods_by_pattern(self, source_content: str, 
                                              function_name: str, 
                                              method_variable: str) -> Set[str]:
        """Generic method to extract methods from any dispatcher function."""
        methods = set()
        
        # Build pattern for the specified dispatcher function
        pattern = rf'async fn {function_name}\([^)]*\)[^{{]*\{{[\s\S]*?match {method_variable}\.as_str\(\) \{{([\s\S]*?)\s*\}}\s*\}}'
        match = re.search(pattern, source_content)
        
        if match:
            dispatcher_content = match.group(1)
            # Extract method names from match arms
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            methods.update(method_matches)
        
        return methods
    
    def _extract_task_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from task dispatcher function."""
        methods = self._extract_dispatcher_methods_by_pattern(
            source_content, "rpc_task_dispatcher", "task_method"
        )
        # Add task:: prefix to all extracted methods
        return {f"task::{method}" for method in methods}
    
    def _extract_lightning_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from lightning dispatcher function."""
        methods = set()
        
        # Lightning dispatcher has a specific structure with lightning_method parameter
        pattern = r'async fn lightning_dispatcher\([^)]*lightning_method: &str[^)]*\)[^{]*\{[\s\S]*?match lightning_method \{([\s\S]*?)\s*_\s*=>\s*MmError::err'
        match = re.search(pattern, source_content)
        
        if match:
            dispatcher_content = match.group(1)
            # Extract method names from match arms
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            # Add lightning:: prefix to all extracted methods
            methods = {f"lightning::{method}" for method in method_matches}
        
        return methods
    
    def _extract_streaming_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from streaming dispatcher function."""
        methods = self._extract_dispatcher_methods_by_pattern(
            source_content, "rpc_streaming_dispatcher", "streaming_request"
        )
        # Add stream:: prefix to all extracted methods
        return {f"stream::{method}" for method in methods}
    
    def _extract_gui_storage_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from GUI storage dispatcher function."""
        methods = set()
        
        # GUI storage dispatcher has a specific structure with gui_storage_method parameter
        pattern = r'async fn gui_storage_dispatcher\([^)]*gui_storage_method: &str[^)]*\)[^{]*\{[\s\S]*?match gui_storage_method \{([\s\S]*?)\s*_\s*=>\s*MmError::err'
        match = re.search(pattern, source_content)
        
        if match:
            dispatcher_content = match.group(1)
            # Extract method names from match arms
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            # Add gui_storage:: prefix to all extracted methods
            methods = {f"gui_storage::{method}" for method in method_matches}
        
        return methods
    
    def _extract_staking_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from staking dispatcher function."""
        methods = set()
        
        # Staking dispatcher has two levels - direct methods and query:: sub-methods
        # First extract direct staking methods
        staking_pattern = r'async fn staking_dispatcher\([^)]*staking_method: &str[^)]*\)[^{]*\{[\s\S]*?match staking_method \{([\s\S]*?)\s*_\s*=>\s*MmError::err'
        match = re.search(staking_pattern, source_content)
        
        if match:
            dispatcher_content = match.group(1)
            # Extract method names from match arms
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            # Add experimental::staking:: prefix to direct staking methods
            for method in method_matches:
                methods.add(f"experimental::staking::{method}")
        
        # Extract query sub-methods from the nested query_dispatcher
        query_pattern = r'async fn query_dispatcher\([^)]*staking_query_method: &str[^)]*\)[^{]*\{[\s\S]*?match staking_query_method \{([\s\S]*?)\s*_\s*=>\s*MmError::err'
        match = re.search(query_pattern, source_content)
        
        if match:
            query_content = match.group(1)
            # Extract query method names and prefix them with experimental::staking::query::
            query_matches = re.findall(r'"([^"]+)"\s*=>', query_content)
            for query_method in query_matches:
                methods.add(f"experimental::staking::query::{query_method}")
        
        return methods
    
    def _extract_direct_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract direct methods from main dispatcher function."""
        methods = set()
        
        # Find the main dispatcher function (now called dispatcher_v2)
        main_pattern = r'async fn dispatcher_v2\([^)]*\)[^{]*\{[\s\S]*?match request\.method\.as_str\(\) \{([\s\S]*?)\s*\}\s*\}'
        match = re.search(main_pattern, source_content)
        
        if match:
            dispatcher_content = match.group(1)
            # Extract method names from match arms, excluding prefixed ones
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            # Filter out methods that start with known prefixes
            prefixes = ["task::", "lightning::", "stream::", "gui_storage::", "experimental::"]
            for method in method_matches:
                if not any(method.startswith(prefix) for prefix in prefixes):
                    methods.add(method)
        
        return methods
    
    def _extract_legacy_dispatcher_methods(self, source_content: str) -> Set[str]:
        """Extract methods from V1 legacy dispatcher function."""
        methods = set()
        
        # V1 has a different structure - it's a regular function, not async
        # Pattern: DispatcherRes::Match(match &method[..] { ... methods ... _ => return DispatcherRes::NoMatch(req), })
        legacy_pattern = r'DispatcherRes::Match\(match &method\[\.\.\] \{([\s\S]*?)_\s*=>\s*return DispatcherRes::NoMatch'
        match = re.search(legacy_pattern, source_content)
        
        if match:
            dispatcher_content = match.group(1)
            # Extract method names from match arms - V1 uses string literals directly
            method_matches = re.findall(r'"([^"]+)"\s*=>', dispatcher_content)
            methods.update(method_matches)
        
        return methods


class KDFRepositoryScanner:
    """
    Comprehensive scanner for KDF repository method extraction.
    
    PERFORMANCE UPGRADE: Now supports async operations for faster repository scanning.
    """
    
    def __init__(self, base_directory: Union[str, Path] = "data", 
                 default_branch: str = "dev", verbose: bool = True):
        self.base_directory = Path(base_directory)
        self.default_branch = default_branch
        self.verbose = verbose
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
        
        self.logger = get_logger("kdf-repository-scanner")
        
        # Initialize async processor for performance
        self.async_processor = None
        
        # Initialize components
        self.fetcher = RepositoryFetcher(default_branch, verbose=verbose)
        self.extractor = MethodExtractor(verbose=verbose)
        
        # Ensure data directory exists
        self.base_directory.mkdir(parents=True, exist_ok=True)
        
        if self.verbose:
            self.logger.info(f"🔧 Initialized KDFRepositoryScanner with async support")
            self.logger.info(f"   📁 Data directory: {self.base_directory}")
            self.logger.info(f"   🌿 Default branch: {self.default_branch}")

    def _get_async_processor(self):
        """Lazy initialization of async processor.""" 
        if self.async_processor is None:
            from ..async_support import AsyncFileProcessor
            self.async_processor = AsyncFileProcessor()
        return self.async_processor

    async def scan_repository_methods_async(self, branch: str = None, 
                                          versions: List[str] = None) -> Dict[str, RepositoryInfo]:
        """
        Scan repository methods asynchronously for better performance.
        
        Args:
            branch: Git branch to scan
            versions: List of API versions to scan
            
        Returns:
            Dictionary mapping versions to RepositoryInfo objects
        """
        if branch is None:
            branch = self.default_branch
        
        if versions is None:
            versions = ["v1", "v2"]
        
        if self.verbose:
            self.logger.info(f"🔍 Scanning KDF repository asynchronously (branch: {branch})")
            print(f"📋 Versions: {', '.join(versions)}")
        
        processor = self._get_async_processor()
        
        # Get repository URLs
        repo_urls = self.fetcher.get_repository_urls(branch)
        
        # Create async tasks for all versions
        import asyncio
        tasks = []
        
        for version in versions:
            if version not in repo_urls:
                if self.verbose:
                    self.logger.warning(f"No URL configured for version {version}")
                continue
            
            tasks.append(self._scan_version_async(version, repo_urls[version], branch))
        
        # Execute all version scans concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        repository_info = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                version = versions[i] if i < len(versions) else "unknown"
                if self.verbose:
                    self.logger.error(f"Error scanning version {version}: {result}")
                continue
            
            version, repo_info = result
            repository_info[version] = repo_info
        
        if self.verbose:
            total_methods = sum(len(info.methods) for info in repository_info.values())
            self.logger.success(f"✅ Async scan completed: {total_methods} methods across {len(repository_info)} versions")
        
        return repository_info

    async def _scan_version_async(self, version: str, url: str, branch: str) -> Tuple[str, RepositoryInfo]:
        """Scan a single version asynchronously."""
        try:
            if self.verbose:
                print(f"🔄 Fetching {version.upper()} source from {url}...")
            
            # Fetch source content (this is I/O bound, so run in thread pool)
            import asyncio
            loop = asyncio.get_event_loop()
            source_content = await loop.run_in_executor(
                None, self.fetcher.fetch_source_content, url, version
            )
            
            if not source_content:
                raise ValueError(f"Failed to fetch source content for {version}")
            
            if self.verbose:
                print(f"🔍 Extracting methods from {version.upper()} source...")
            
            # Extract methods (CPU bound, but quick)
            methods = await loop.run_in_executor(
                None, self.extractor.extract_methods_from_source, source_content, version
            )
            
            # Create repository info
            repo_info = RepositoryInfo(
                branch=branch,
                version=version,
                url=url,
                methods=sorted(list(methods)),
                last_updated=datetime.now(),
                extraction_patterns_used=self.extractor.method_patterns
            )
            
            return version, repo_info
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Error scanning {version}: {e}")
            raise

    async def save_repository_methods_async(self, repo_info: Dict[str, RepositoryInfo], 
                                          filename: str = None) -> str:
        """
        Save repository methods asynchronously.
        
        Args:
            repo_info: Repository information to save
            filename: Optional filename override
            
        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # Extract branch name from the first repository info
            branch_name = list(repo_info.values())[0].branch if repo_info else "unknown"
            filename = f"kdf_rust_methods_{branch_name}_{timestamp}.json"
        
        file_path = self.base_directory / filename
        
        # Prepare data for JSON serialization
        data = {
            "scan_metadata": {
                "generated_at": datetime.now().isoformat(),
                "scanner_version": "KDFRepositoryScanner v2.0.0",
                "total_versions": len(repo_info),
                "total_methods": sum(len(info.methods) for info in repo_info.values())
            },
            "repository_data": {}
        }
        
        for version, info in repo_info.items():
            data["repository_data"][version] = {
                "branch": info.branch,
                "version": info.version,
                "url": info.url,
                "methods": info.methods,
                "last_updated": info.last_updated.isoformat(),
                "commit_hash": info.commit_hash,
                "extraction_patterns_used": info.extraction_patterns_used or []
            }
        
        # Use async file operations
        processor = self._get_async_processor()
        await processor.write_json_async(file_path, data)
        
        if self.verbose:
            self.logger.success(f"💾 Saved repository methods to: {file_path}")
        
        return str(file_path)

    async def load_repository_methods_async(self, filename: str = None) -> Optional[Dict[str, RepositoryInfo]]:
        """
        Load repository methods asynchronously.
        
        Args:
            filename: Optional filename to load
            
        Returns:
            Dictionary mapping versions to RepositoryInfo objects, or None if not found
        """
        if filename is None:
            # Find the most recent file - try both new format (with branch) and old format (without)
            pattern_with_branch = "kdf_rust_methods_*_*.json"
            pattern_old = "kdf_rust_methods_*.json"
            
            matching_files = list(self.base_directory.glob(pattern_with_branch))
            if not matching_files:
                # Fallback to old pattern
                matching_files = list(self.base_directory.glob(pattern_old))
            
            if not matching_files:
                if self.verbose:
                    self.logger.warning("No repository method files found")
                return None
            
            # Sort by modification time (most recent first)
            filename = max(matching_files, key=lambda f: f.stat().st_mtime).name
        
        file_path = self.base_directory / filename
        
        if not file_path.exists():
            if self.verbose:
                self.logger.error(f"File not found: {file_path}")
            return None
        
        try:
            # Use async file operations
            processor = self._get_async_processor()
            data = await processor.read_json_async(file_path)
            
            if "repository_data" not in data:
                if self.verbose:
                    self.logger.error(f"Invalid file format: missing repository_data")
                return None
            
            # Convert back to RepositoryInfo objects
            repository_info = {}
            for version, info_data in data["repository_data"].items():
                repo_info = RepositoryInfo(
                    branch=info_data["branch"],
                    version=info_data["version"],
                    url=info_data["url"],
                    methods=info_data["methods"],
                    last_updated=datetime.fromisoformat(info_data["last_updated"]),
                    commit_hash=info_data.get("commit_hash"),
                    extraction_patterns_used=info_data.get("extraction_patterns_used", [])
                )
                repository_info[version] = repo_info
            
            if self.verbose:
                total_methods = sum(len(info.methods) for info in repository_info.values())
            
            return repository_info
            
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Error loading repository methods from {file_path}: {e}")
            return None

    async def get_latest_methods_async(self, branch: str = None, force_refresh: bool = False) -> Dict[str, List[str]]:
        """
        Get the latest methods from repository asynchronously, using cache if available.
        
        Args:
            branch: Git branch to scan
            force_refresh: Force fresh scan even if cache is valid
            
        Returns:
            Dictionary mapping versions to method lists
        """
        if branch is None:
            branch = self.default_branch
        
        # Check if we need to refresh
        if not force_refresh:
            cached_data = await self.load_repository_methods_async()
            if cached_data:
                # Check if data is recent enough
                latest_update = max(info.last_updated for info in cached_data.values())
                if datetime.now() - latest_update < self.cache_duration:
                    if self.verbose:
                        self.logger.info("Using cached repository methods")
                    return {version: info.methods for version, info in cached_data.items()}
        
        # Perform fresh scan
        if self.verbose:
            self.logger.info("Performing fresh repository scan asynchronously")
        
        repo_info = await self.scan_repository_methods_async(branch)
        await self.save_repository_methods_async(repo_info)
        
        return {version: info.methods for version, info in repo_info.items()}

    def compare_with_documentation(self, repo_methods: Dict[str, RepositoryInfo],
                                  doc_methods: Dict[str, List[str]]) -> Dict[str, Dict[str, List[str]]]:
        """
        Compare repository methods with documentation methods.
        
        SIMPLIFIED: Now that the scanner returns proper full method names,
        comparison is much more straightforward.
        
        Args:
            repo_methods: Repository method information
            doc_methods: Documentation methods by version
            
        Returns:
            Comparison results with missing/extra methods
        """
        comparison = {}
        
        for version in set(repo_methods.keys()) | set(doc_methods.keys()):
            repo_set = set()
            doc_set = set()
            
            # Get repository methods for this version (now with proper prefixes)
            if version in repo_methods:
                repo_methods_raw = repo_methods[version].methods
                # Simple normalization - just convert to lowercase and handle format differences
                repo_set = {normalize_method_name(method) for method in repo_methods_raw}
            
            # Get documentation methods for this version
            if version in doc_methods:
                doc_methods_raw = doc_methods[version]
                # Simple normalization for documentation methods
                doc_set = {normalize_method_name(method) for method in doc_methods_raw}
            
            # Calculate differences
            missing_in_docs = repo_set - doc_set
            missing_in_repo = doc_set - repo_set
            common_methods = repo_set & doc_set
            
            comparison[version] = {
                "missing_in_docs": sorted(list(missing_in_docs)),
                "missing_in_repo": sorted(list(missing_in_repo)),
                "common_methods": sorted(list(common_methods)),
                "repo_total": len(repo_set),
                "docs_total": len(doc_set),
                "common_total": len(common_methods)
            }
        
        return comparison
    
    def generate_comparison_report(self, comparison: Dict[str, Dict[str, List[str]]], 
                                 method_mappings: Dict[str, Dict[str, 'MethodMapping']] = None) -> str:
        """
        Generate a human-readable comparison report.
        
        Args:
            comparison: Comparison results from compare_with_documentation
            method_mappings: Optional method mappings to include file paths
            
        Returns:
            Formatted report string
        """
        from ..reporting.mapping_reporter import MappingReporter
        reporter = MappingReporter(verbose=self.verbose)
        return reporter.generate_comparison_report(comparison, method_mappings)

