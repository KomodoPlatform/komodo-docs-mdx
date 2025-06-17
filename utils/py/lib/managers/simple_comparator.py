#!/usr/bin/env python3
"""
Simple Comparator for KDF Methods

Provides simple comparison functionality using pre-generated JSON files.
Much simpler and faster than live-scanning approaches.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime

from ..utils.logging_utils import get_logger


class SimpleComparator:
    """
    Simple comparator for KDF methods using pre-generated JSON files.
    
    Provides fast, reliable comparison without complex live scanning.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.logger = get_logger("simple-comparator")
    
    def load_json_file(self, file_path: str) -> Dict:
        """Load and parse JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Failed to load JSON file {file_path}: {e}")
            raise
    
    def extract_methods_from_repo_file(self, data: Dict, versions: List[str]) -> Dict[str, Set[str]]:
        """Extract method sets from repository JSON file."""
        methods = {}
        repo_data = data.get('repository_data', {})
        
        for version in versions:
            if version in repo_data:
                method_list = repo_data[version].get('methods', [])
                methods[version] = set(method_list)
                if self.verbose:
                    self.logger.debug(f"Loaded {len(method_list)} {version} methods from repository")
            else:
                methods[version] = set()
                if self.verbose:
                    self.logger.warning(f"No {version} methods found in repository data")
        
        return methods
    
    def extract_methods_from_docs_file(self, data: Dict, versions: List[str]) -> Dict[str, Set[str]]:
        """Extract method sets from documentation JSON file."""
        methods = {}
        repo_data = data.get('repository_data', {})
        
        for version in versions:
            if version in repo_data:
                method_list = repo_data[version].get('methods', [])
                methods[version] = set(method_list)
                if self.verbose:
                    self.logger.debug(f"Loaded {len(method_list)} {version} methods from documentation")
            else:
                methods[version] = set()
                if self.verbose:
                    self.logger.warning(f"No {version} methods found in documentation data")
        
        return methods
    
    def compare_methods(self, repo_methods: Dict[str, Set[str]], 
                       docs_methods: Dict[str, Set[str]]) -> Dict[str, Dict]:
        """Compare repository methods with documentation methods."""
        comparison = {}
        
        if self.verbose:
            self.logger.info("Starting method comparison...")
        
        for version in repo_methods.keys() | docs_methods.keys():
            repo_set = repo_methods.get(version, set())
            docs_set = docs_methods.get(version, set())
            
            missing_in_docs = repo_set - docs_set
            missing_in_repo = docs_set - repo_set
            common_methods = repo_set & docs_set
            
            coverage = (len(common_methods) / len(repo_set) * 100) if repo_set else 0
            
            comparison[version] = {
                "missing_in_docs": sorted(list(missing_in_docs)),
                "missing_in_repo": sorted(list(missing_in_repo)),
                "common_methods": sorted(list(common_methods)),
                "repo_total": len(repo_set),
                "docs_total": len(docs_set),
                "common_total": len(common_methods),
                "coverage_percentage": coverage
            }
            
            if self.verbose:
                self.logger.info(f"{version.upper()}: {coverage:.1f}% coverage ({len(common_methods)}/{len(repo_set)})")
        
        return comparison
    
    def generate_report(self, comparison: Dict[str, Dict], repo_file: str, docs_file: str) -> str:
        """Generate a human-readable comparison report."""
        report = []
        report.append("=" * 80)
        report.append("KDF METHOD COMPARISON REPORT")
        report.append("=" * 80)
        report.append(f"Repository file: {repo_file}")
        report.append(f"Documentation file: {docs_file}")
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        total_repo_methods = 0
        total_docs_methods = 0
        total_common = 0
        
        for version, data in comparison.items():
            report.append(f"📋 {version.upper()} API Methods:")
            report.append("-" * 40)
            report.append(f"  Repository methods: {data['repo_total']}")
            report.append(f"  Documentation methods: {data['docs_total']}")
            report.append(f"  Common methods: {data['common_total']}")
            report.append(f"  Coverage: {data['coverage_percentage']:.1f}%")
            report.append("")
            
            if data['missing_in_docs']:
                report.append(f"  ❌ Missing in Documentation ({len(data['missing_in_docs'])}):")
                for method in data['missing_in_docs'][:10]:  # Show first 10
                    report.append(f"    - {method}")
                if len(data['missing_in_docs']) > 10:
                    report.append(f"    ... and {len(data['missing_in_docs']) - 10} more")
                report.append("")
            
            if data['missing_in_repo']:
                report.append(f"  ⚠️  Extra in Documentation ({len(data['missing_in_repo'])}):")
                for method in data['missing_in_repo'][:10]:  # Show first 10
                    report.append(f"    - {method}")
                if len(data['missing_in_repo']) > 10:
                    report.append(f"    ... and {len(data['missing_in_repo']) - 10} more")
                report.append("")
            
            total_repo_methods += data['repo_total']
            total_docs_methods += data['docs_total']
            total_common += data['common_total']
        
        # Summary
        overall_coverage = (total_common / total_repo_methods * 100) if total_repo_methods else 0
        report.append("=" * 40)
        report.append("OVERALL SUMMARY:")
        report.append(f"  Total repository methods: {total_repo_methods}")
        report.append(f"  Total documented methods: {total_docs_methods}")
        report.append(f"  Total common methods: {total_common}")
        report.append(f"  Overall coverage: {overall_coverage:.1f}%")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def compare_from_files(self, repo_file: str, docs_file: str, 
                          versions: List[str], output: Optional[str] = None) -> Dict[str, Dict]:
        """
        Complete comparison workflow using JSON files.
        
        Args:
            repo_file: Path to repository methods JSON file
            docs_file: Path to documentation methods JSON file  
            versions: List of API versions to compare
            output: Optional output file path for results
            
        Returns:
            Comparison results dictionary
        """
        # Validate files exist
        repo_path = Path(repo_file)
        docs_path = Path(docs_file)
        
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository file not found: {repo_path}")
        
        if not docs_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {docs_path}")
        
        if self.verbose:
            self.logger.info(f"Loading repository methods from: {repo_path}")
        repo_data = self.load_json_file(repo_path)
        
        if self.verbose:
            self.logger.info(f"Loading documentation methods from: {docs_path}")
        docs_data = self.load_json_file(docs_path)
        
        # Extract methods
        repo_methods = self.extract_methods_from_repo_file(repo_data, versions)
        docs_methods = self.extract_methods_from_docs_file(docs_data, versions)
        
        # Compare
        if self.verbose:
            self.logger.info("Comparing methods...")
        comparison = self.compare_methods(repo_methods, docs_methods)
        
        # Generate report
        report = self.generate_report(comparison, repo_file, docs_file)
        print(report)
        
        # Save results if requested
        if output:
            self.save_results(comparison, report, output)
        
        return comparison
    
    def save_results(self, comparison: Dict[str, Dict], report: str, output: str):
        """Save comparison results to files."""
        output_path = Path(output)
        
        # Save both raw comparison data and report
        comparison_file = output_path.with_suffix('.json')
        report_file = output_path.with_suffix('.txt')
        
        try:
            with open(comparison_file, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2)
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            if self.verbose:
                self.logger.success(f"Comparison data saved to: {comparison_file}")
                self.logger.success(f"Report saved to: {report_file}")
                
        except Exception as e:
            if self.verbose:
                self.logger.error(f"Failed to save results: {e}")
            raise
    
    def find_latest_files(self, data_dir: str, branch: str = "dev") -> tuple[str, str]:
        """
        Find the latest repository and documentation JSON files.
        
        Args:
            data_dir: Directory to search for files
            branch: Git branch name to look for
            
        Returns:
            Tuple of (repo_file_path, docs_file_path)
        """
        data_path = Path(data_dir)
        
        # Find latest repository file
        repo_pattern = "kdf_rust_methods_*.json"
        repo_files = list(data_path.glob(repo_pattern))
        if not repo_files:
            repo_pattern = "kdf_*repository*methods*.json"
            repo_files = list(data_path.glob(repo_pattern))
        
        # Find latest documentation file  
        docs_pattern = "kdf_mdx_methods_*.json"
        docs_files = list(data_path.glob(docs_pattern))
        
        if not repo_files:
            raise FileNotFoundError(f"No repository methods files found in {data_path}")
        
        if not docs_files:
            raise FileNotFoundError(f"No documentation methods files found in {data_path}")
        
        # Get most recent files
        latest_repo = max(repo_files, key=lambda f: f.stat().st_mtime)
        latest_docs = max(docs_files, key=lambda f: f.stat().st_mtime)
        
        if self.verbose:
            self.logger.info(f"Found latest repository file: {latest_repo.name}")
            self.logger.info(f"Found latest documentation file: {latest_docs.name}")
        
        return str(latest_repo), str(latest_docs)
    
    def compare_latest(self, data_dir: str = "data", branch: str = "dev", 
                      versions: List[str] = None, output: Optional[str] = None) -> Dict[str, Dict]:
        """
        Compare using the latest available JSON files.
        
        Args:
            data_dir: Directory containing JSON files
            branch: Git branch name  
            versions: API versions to compare (default: ['v1', 'v2'])
            output: Optional output file path
            
        Returns:
            Comparison results dictionary
        """
        if versions is None:
            versions = ['v1', 'v2']
        
        repo_file, docs_file = self.find_latest_files(data_dir, branch)
        return self.compare_from_files(repo_file, docs_file, versions, output) 