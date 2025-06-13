#!/usr/bin/env python3
"""
API Example Manager

Orchestrates API example management operations using specialized components.
Coordinates extraction, generation, file operations, and reporting.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

# Import our specialized components
from .mapping import MethodMapper
from .extractors import ExtractedExample, MDXExtractor
from .file_operations import ExampleFileManager
from .deduplicator import ExampleDeduplicator
from .reporters import ExampleReporter
from .templates import ExampleTemplates


class APIExampleManager:
    """
    Main coordinator for API example management operations.
    
    Orchestrates the work of specialized components:
    - MDXExtractor: Extracts examples from MDX files
    - ExampleFileManager: Handles file I/O operations
    - ExampleDeduplicator: Manages duplicate detection/removal
    - ExampleReporter: Generates reports and statistics
    - ExampleTemplates: Provides template-based generation
    """
    
    def __init__(self, base_path: str = ".", verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        self.output_base = "../../postman/json/kdf"
        
        # Initialize components
        self.mapper = MethodMapper(base_path, verbose)
        self.extractor = MDXExtractor(verbose)
        self.file_manager = ExampleFileManager(self.output_base, verbose)
        self.deduplicator = ExampleDeduplicator(self.output_base, verbose)
        self.reporter = ExampleReporter(verbose)
        
        # Load unified mapping once
        self.unified_mapping = self.mapper.create_unified_mapping()
        
        # Template integration
        self.templates = ExampleTemplates()
    
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
        return self.file_manager.save_examples_to_files(examples)
    
    def consolidate_to_flat_structure(self, versions: List[str] = ['v1', 'v2'], 
                                    dry_run: bool = True) -> Dict[str, int]:
        """Consolidate operation subfolders into flat method folders."""
        return self.file_manager.consolidate_to_flat_structure(versions, dry_run)
    
    def clean_empty_directories(self, versions: List[str] = ['v1', 'v2'], 
                               dry_run: bool = True) -> int:
        """Remove empty directories after operations."""
        return self.file_manager.clean_empty_directories(versions, dry_run)
    
    def scan_duplicates(self, versions: List[str] = ['v1', 'v2']):
        """Scan for duplicate files by content hash."""
        return self.deduplicator.scan_duplicates(versions)
    
    def remove_duplicates(self, duplicates, dry_run: bool = True):
        """Remove duplicate files, keeping only the first one in each group."""
        return self.deduplicator.remove_duplicates(duplicates, dry_run)
    
    def generate_deduplication_report(self, duplicates) -> str:
        """Generate a summary report of duplicates found."""
        return self.deduplicator.generate_deduplication_report(duplicates)
    
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
    
    args = parser.parse_args()
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    manager = APIExampleManager(verbose=args.verbose)
    
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