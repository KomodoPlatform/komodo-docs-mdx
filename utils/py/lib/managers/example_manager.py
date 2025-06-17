#!/usr/bin/env python3
"""
API Example Manager - Main coordinator for example extraction and management

OPTIMIZATION: Fixed circular import issue by using lazy imports for file operations.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# Import our specialized components
from .method_mapping_manager import MethodMappingManager
from ..scanning.postman_scanners import ExtractedExample, MDXExtractor
from ..reporting.example_reporter import ExampleReporter
from ..constants.templates import ExampleTemplates
from ..constants.config import get_config, EnhancedKomodoConfig
from ..constants.enums import DeploymentEnvironment
from ..utils.logging_utils import get_logger
from ..utils.batch_processor import BatchFileProcessor
from ..utils.file_types import FileInfo, OperationResult
from ..utils.file_utils import calculate_content_hash


class APIExampleManager:
    """
    Main coordinator for API example management operations.
    
    Orchestrates the work of specialized components:
    - MDXExtractor: Extracts examples from MDX files
    - ExampleFileManager: Handles file I/O operations
    - ExampleReporter: Generates reports and statistics
    - ExampleTemplates: Provides template-based generation
    - Integrated deduplication functionality
    """
    
    def __init__(self, config: Optional[EnhancedKomodoConfig] = None, verbose: bool = True):
        """Initialize the example manager."""
        self.config = get_config() if config is None else config
        self.verbose = verbose
        self.logger = get_logger("example-manager")
        
        # Initialize mapper
        self.mapper = MethodMappingManager(config=self.config, verbose=verbose)
        
        # Load unified mapping
        if self.verbose:
            self.logger.info("Loading unified method mapping...")
        
        self.unified_mapping = self.mapper.create_unified_mapping()
        
        if self.verbose:
            total_methods = sum(len(v) for v in self.unified_mapping.values())
            self.logger.success(f"Loaded mapping for {total_methods} methods")
        
        # Initialize components
        self.extractor = MDXExtractor(verbose)
        self._file_ops = None
        self.reporter = ExampleReporter(verbose)
        
        # Template integration
        self.templates = ExampleTemplates()
        
        # Output base path for file operations
        self.output_base = Path("postman/json/kdf")

    async def init_async(self, config: Optional[EnhancedKomodoConfig] = None, verbose: bool = True):
        """Initialize the example manager asynchronously for better performance."""
        self.config = get_config() if config is None else config
        self.verbose = verbose
        self.logger = get_logger("example-manager")
        
        # Initialize mapper
        self.mapper = MethodMappingManager(config=self.config, verbose=verbose)
        
        # Load unified mapping asynchronously
        if self.verbose:
            self.logger.info("Loading unified method mapping asynchronously...")
        
        self.unified_mapping = await self.mapper.create_unified_mapping_async()
        
        if self.verbose:
            total_methods = sum(len(v) for v in self.unified_mapping.values())
            self.logger.success(f"Loaded mapping for {total_methods} methods")
        
        # Initialize components
        self.extractor = MDXExtractor(verbose)
        self._file_ops = None
        self.reporter = ExampleReporter(verbose)
        
        # Template integration
        self.templates = ExampleTemplates()
        
        # Output base path for file operations
        self.output_base = Path("postman/json/kdf")
    
    @classmethod
    async def create_async(cls, config: Optional[EnhancedKomodoConfig] = None, verbose: bool = True):
        """Create an ExampleManager instance asynchronously."""
        instance = cls.__new__(cls)
        await instance.init_async(config, verbose)
        return instance
    
    @property
    def file_ops(self):
        """Lazy-loaded file operations to prevent circular imports."""
        if self._file_ops is None:
            self._file_ops = self._get_file_operations()
        return self._file_ops
    
    def _get_file_operations(self):
        """Get file operations instance."""
        return BatchFileProcessor(verbose=self.verbose)

    # === DEDUPLICATION METHODS (integrated from ExampleDeduplicator) ===
    
    def scan_duplicates(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Dict[str, List[Tuple[Path, str]]]]:
        """Scan for duplicate files by content hash in the output_base directory."""
        duplicates = {}
        
        for version in versions:
            version_path = self.output_base / version
            if not version_path.exists():
                if self.verbose:
                    print(f"Warning: {version_path} does not exist")
                continue
            
            if self.verbose:
                print(f"Scanning {version} for duplicates...")
            
            version_duplicates = self._scan_version_duplicates(version_path)
            duplicates[version] = version_duplicates
            
            if self.verbose:
                self._print_scan_summary(version, version_duplicates)
        
        return duplicates
    
    def _scan_version_duplicates(self, version_path: Path) -> Dict[str, List[Tuple[Path, str]]]:
        """Scan a single version directory for duplicates."""
        content_to_files = defaultdict(list)
        
        for json_file in version_path.rglob("*.json"):
            if json_file.is_file():
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                    
                    content_hash = calculate_content_hash(content)
                    content_to_files[content_hash].append((json_file, json_file.name))
                    
                except Exception as e:
                    if self.verbose:
                        print(f"Error reading {json_file}: {e}")
        
        # Return only groups with duplicates
        return {
            content_hash: files 
            for content_hash, files in content_to_files.items() 
            if len(files) > 1
        }
    
    def _print_scan_summary(self, version: str, version_duplicates: Dict[str, List[Tuple[Path, str]]]):
        """Print summary of duplicate scan results."""
        total_dupes = sum(len(files) for files in version_duplicates.values())
        unique_dupes = len(version_duplicates)
        print(f"  {version}: {total_dupes} duplicate files in {unique_dupes} groups")
    
    def remove_duplicates(self, duplicates: Dict[str, Dict[str, List[Tuple[Path, str]]]], 
                         dry_run: bool = True) -> Dict[str, int]:
        """Remove duplicate files, keeping only the first one in each group."""
        stats = {'files_removed': 0, 'files_kept': 0, 'groups_processed': 0}
        
        for version, version_duplicates in duplicates.items():
            if self.verbose:
                print(f"\nProcessing {version} duplicates...")
            
            for content_hash, files in version_duplicates.items():
                if len(files) <= 1:
                    continue
                
                self._process_duplicate_group(content_hash, files, stats, dry_run)
        
        return stats
    
    def _process_duplicate_group(self, content_hash: str, files: List[Tuple[Path, str]], 
                               stats: Dict[str, int], dry_run: bool):
        """Process a single group of duplicate files."""
        stats['groups_processed'] += 1
        
        # Sort files to have consistent behavior
        sorted_files = sorted(files, key=lambda x: x[1])
        files_to_keep = sorted_files[:1]
        files_to_remove = sorted_files[1:]
        
        if self.verbose:
            print(f"\n  Duplicate group (hash: {content_hash[:8]}...):")
            
            for file_path, filename in files_to_keep:
                action = "Would keep" if dry_run else "Keeping"
                print(f"    ✅ {action}: {file_path.relative_to(self.output_base)}")
            
            for file_path, filename in files_to_remove:
                action = "Would remove" if dry_run else "Removing"
                print(f"    🗑️  {action}: {file_path.relative_to(self.output_base)}")
        
        # Remove duplicate files
        for file_path, filename in files_to_remove:
            if not dry_run:
                try:
                    file_path.unlink()
                    stats['files_removed'] += 1
                except Exception as e:
                    if self.verbose:
                        print(f"    ❌ Error removing {file_path}: {e}")
            else:
                stats['files_removed'] += 1
        
        stats['files_kept'] += len(files_to_keep)
    
    def generate_deduplication_report(self, duplicates: Dict[str, Dict[str, List[Tuple[Path, str]]]]) -> str:
        """Generate a summary report of duplicates found."""
        return self.reporter.generate_deduplication_report(duplicates, self.output_base)

    # === END DEDUPLICATION METHODS ===
    
    def extract_examples_via_mapping(self, versions: List[str] = ['v1', 'v2']) -> Tuple[List[ExtractedExample], Dict[str, int]]:
        """Extract examples from all mapped MDX files for specified versions."""
        all_examples = []
        stats = {
            'v1_extracted': 0, 'v1_generated': 0, 'v1_methods': 0,
            'v2_extracted': 0, 'v2_generated': 0, 'v2_methods': 0,
            'errors': 0, 'total_methods_processed': 0
        }
        
        for version in versions:
            if version not in self.unified_mapping:
                if self.verbose:
                    print(f"⚠️ Version {version} not found in mapping")
                continue
            
            version_methods = self.unified_mapping[version]
            if self.verbose:
                print(f"\n🔍 Processing {version.upper()} API ({len(version_methods)} methods)...")
            
            processed_methods = 0
            for method_name, mapping in version_methods.items():
                try:
                    if mapping.has_mdx and mapping.mdx_path:
                        # Extract using specialized extractor
                        examples = self.extractor.extract_from_mdx_file(method_name, mapping, version)
                        all_examples.extend(examples)
                        
                        extracted_count = len(examples)
                        stats[f'{version}_extracted'] += extracted_count
                        
                        if self.verbose and extracted_count > 0:
                            print(f"  📄 {method_name}: {extracted_count} examples")
                        
                        # Note: Example generation disabled to prevent duplication
                        # Could be re-enabled with proper template-based variation
                        
                        processed_methods += 1
                        
                except Exception as e:
                    if self.verbose:
                        print(f"❌ Error processing {method_name} ({version}): {e}")
                    stats['errors'] += 1
            
            stats[f'{version}_methods'] = processed_methods
            stats['total_methods_processed'] += processed_methods
            
            if self.verbose:
                print(f"✅ {version.upper()}: {processed_methods} methods processed, "
                      f"{stats[f'{version}_extracted']} extracted")
        
        return all_examples, stats
    
    def save_examples_to_files(self, examples: List[ExtractedExample]) -> int:
        """Save extracted examples to JSON files using the file manager."""
        return self.file_ops.save_examples_to_files(examples)
    
    def consolidate_to_flat_structure(self, versions: List[str] = ['v1', 'v2'], 
                                    dry_run: bool = True) -> Dict[str, int]:
        """Consolidate operation subfolders into flat method folders."""
        return self.file_ops.consolidate_to_flat_structure(versions, dry_run)
    
    def clean_empty_directories(self, versions: List[str] = ['v1', 'v2'], 
                               dry_run: bool = True) -> int:
        """Remove empty directories after operations."""
        return self.file_ops.clean_empty_directories(versions, dry_run)
    
    def generate_summary_report(self, examples: List[ExtractedExample], stats: Dict[str, int]) -> str:
        """Generate a comprehensive summary report."""
        return self.reporter.generate_summary_report(examples, stats)
    
    def generate_processing_report(self, stats: Dict[str, int]) -> str:
        """Generate a focused processing report."""
        return self.reporter.generate_processing_report(stats)
    
    def generate_file_operation_report(self, operation: str, stats: Dict[str, int], 
                                     dry_run: bool = False) -> str:
        """Generate a report for file operations."""
        return self.reporter.generate_file_operation_report(operation, stats, dry_run)
    
    # Template-based generation methods (for future use)
    def get_templates_for_category(self, category: str) -> Dict[str, Dict]:
        """Get templates for a specific method category."""
        return self.templates.get_templates_for_category(category)
    
    def categorize_method(self, method_name: str) -> str:
        """Categorize a method for template selection."""
        # Simple categorization logic
        if 'enable' in method_name or 'activation' in method_name:
            return 'activation'
        elif any(keyword in method_name for keyword in ['buy', 'sell', 'trade', 'order', 'swap']):
            return 'trading'
        elif any(keyword in method_name for keyword in ['balance', 'withdraw', 'address', 'wallet']):
            return 'wallet'
        elif method_name.startswith('task::'):
            return 'task_operation'
        else:
            return 'utility'


def main():
    """Main function for command-line usage."""
    import argparse
    from pathlib import Path
    
    parser = argparse.ArgumentParser(description='Manage JSON examples for KDF API using mapping system')
    parser.add_argument('--consolidate', action='store_true',
                       help='Flatten folder structure by moving all files to method folders')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'], default=['v1', 'v2'],
                       help='API versions to process')
    parser.add_argument('--verbose', '-v', action='store_true', default=True,
                       help='Enable verbose output')
    parser.add_argument('--report', action='store_true',
                       help='Generate detailed summary report')
    parser.add_argument('--deduplicate', action='store_true',
                       help='Deduplicate all example files')
    parser.add_argument('--dedup-dry-run', action='store_true',
                       help='Preview deduplication actions without deleting files')
    parser.add_argument('--workspace-root', 
                       help='Workspace root directory (auto-detected if not specified)')
    
    args = parser.parse_args()
    
    # Setup configuration with proper workspace root instead of os.chdir()
    workspace_root = args.workspace_root
    if workspace_root is None:
        # Auto-detect workspace root from current script location
        script_dir = Path(__file__).parent.absolute()
        # Go up from utils/py/lib/managers/ to workspace root
        workspace_root = script_dir.parent.parent.parent.parent
    else:
        workspace_root = Path(workspace_root).absolute()
    
    # Get configuration with proper workspace root
    config = get_config(
        base_path=str(workspace_root),
        environment=DeploymentEnvironment.DEVELOPMENT
    )
    
    if args.verbose:
        print(f"📁 Workspace root: {workspace_root}")
    
    # Initialize manager with proper config
    manager = APIExampleManager(config=config, verbose=args.verbose)
    
    # Handle consolidation command
    if args.consolidate:
        print("🔄 Consolidating folder structure...")
        stats = manager.consolidate_to_flat_structure(args.versions, dry_run=args.dry_run)
        print(manager.generate_file_operation_report("consolidation", stats, args.dry_run))
        return
    
    print("🚀 Starting API Example Management...")
    print(f"📋 Processing versions: {', '.join(args.versions)}")
    
    # Extract examples
    all_examples, stats = manager.extract_examples_via_mapping(args.versions)
    
    # Print processing results
    print(f"\n{manager.generate_processing_report(stats)}")
    
    # Save examples
    if all_examples:
        print(f"\n💾 Saving examples to {manager.output_base}/...")
        saved_count = manager.save_examples_to_files(all_examples)
        print(f"✅ Saved {saved_count} example files")
    else:
        print("⚠️ No examples to save")
    
    # Deduplication if requested
    if args.deduplicate:
        print("\n🔍 Running deduplication...")
        duplicates = manager.scan_duplicates(args.versions)
        print(manager.generate_deduplication_report(duplicates))
        
        if any(duplicates.values()):
            dedup_stats = manager.remove_duplicates(duplicates, dry_run=args.dedup_dry_run)
            empty_dirs_removed = manager.clean_empty_directories(args.versions, dry_run=args.dedup_dry_run)
            dedup_stats['empty_dirs_removed'] = empty_dirs_removed
            
            print(f"\n{manager.generate_file_operation_report('deduplication', dedup_stats, args.dedup_dry_run)}")
        else:
            print("🎉 No duplicate files found!")
    
    # Generate detailed report if requested
    if args.report:
        print("\n" + "="*60)
        print(manager.generate_summary_report(all_examples, stats))
        print("="*60)
    
    print("\n🎉 API Example Management completed!")


if __name__ == "__main__":
    main() 