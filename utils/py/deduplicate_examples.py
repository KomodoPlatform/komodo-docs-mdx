#!/usr/bin/env python3
"""
Deduplicate Example Files

This script identifies and removes duplicate JSON example files by comparing
their actual content, not just filenames. It keeps only one copy of each
unique example and removes the rest.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


class ExampleDeduplicator:
    """Identifies and removes duplicate JSON example files."""
    
    def __init__(self, base_path: str = "../../postman/json/kdf", verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        
    def calculate_content_hash(self, json_content: dict) -> str:
        """Calculate a hash of the JSON content for comparison."""
        # Normalize the JSON by sorting keys and converting to string
        normalized = json.dumps(json_content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def scan_duplicates(self, versions: List[str] = ['v1', 'v2']) -> Dict[str, Dict[str, List[Tuple[Path, str]]]]:
        """
        Scan for duplicate files by content hash.
        Returns: {version: {content_hash: [(file_path, filename), ...]}}
        """
        duplicates = {}
        
        for version in versions:
            version_path = self.base_path / version
            if not version_path.exists():
                if self.verbose:
                    print(f"Warning: {version_path} does not exist")
                continue
                
            if self.verbose:
                print(f"Scanning {version} for duplicates...")
                
            content_to_files = defaultdict(list)
            file_count = 0
            
            # Walk through all JSON files
            for json_file in version_path.rglob("*.json"):
                if json_file.is_file():
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                        
                        content_hash = self.calculate_content_hash(content)
                        content_to_files[content_hash].append((json_file, json_file.name))
                        file_count += 1
                        
                    except Exception as e:
                        if self.verbose:
                            print(f"Error reading {json_file}: {e}")
            
            # Filter to only duplicates (more than one file with same content)
            version_duplicates = {
                content_hash: files 
                for content_hash, files in content_to_files.items() 
                if len(files) > 1
            }
            
            duplicates[version] = version_duplicates
            
            if self.verbose:
                total_dupes = sum(len(files) for files in version_duplicates.values())
                unique_dupes = len(version_duplicates)
                print(f"  {version}: {file_count} total files, {total_dupes} duplicate files in {unique_dupes} groups")
        
        return duplicates
    
    def remove_duplicates(self, duplicates: Dict[str, Dict[str, List[Tuple[Path, str]]]], 
                         dry_run: bool = True) -> Dict[str, int]:
        """
        Remove duplicate files, keeping only the first one in each group.
        Returns statistics about files processed.
        """
        stats = {'files_removed': 0, 'files_kept': 0, 'groups_processed': 0}
        
        for version, version_duplicates in duplicates.items():
            if self.verbose:
                print(f"\nProcessing {version} duplicates...")
            
            for content_hash, files in version_duplicates.items():
                if len(files) <= 1:
                    continue
                    
                stats['groups_processed'] += 1
                
                # Sort files to have consistent ordering (keep the first one)
                sorted_files = sorted(files, key=lambda x: x[1])  # Sort by filename
                files_to_keep = sorted_files[:1]  # Keep only the first one
                files_to_remove = sorted_files[1:]  # Remove the rest
                
                if self.verbose:
                    print(f"\n  Duplicate group (hash: {content_hash[:8]}...):")
                    for file_path, filename in files_to_keep:
                        action = "Would keep" if dry_run else "Keeping"
                        print(f"    ✅ {action}: {file_path.relative_to(self.base_path)}")
                    
                    for file_path, filename in files_to_remove:
                        action = "Would remove" if dry_run else "Removing"
                        print(f"    🗑️  {action}: {file_path.relative_to(self.base_path)}")
                
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
        
        return stats
    
    def clean_empty_directories(self, versions: List[str] = ['v1', 'v2'], dry_run: bool = True) -> int:
        """Remove empty directories after deduplication."""
        removed_count = 0
        
        for version in versions:
            version_path = self.base_path / version
            if not version_path.exists():
                continue
            
            # Walk directories from deepest to shallowest
            for dir_path in sorted(version_path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
                if dir_path.is_dir() and dir_path != version_path:
                    try:
                        # Check if directory is empty
                        if not any(dir_path.iterdir()):
                            action = "Would remove" if dry_run else "Removing"
                            if self.verbose:
                                print(f"    📁 {action} empty directory: {dir_path.relative_to(self.base_path)}")
                            
                            if not dry_run:
                                dir_path.rmdir()
                            removed_count += 1
                    except Exception as e:
                        if self.verbose:
                            print(f"    ❌ Error removing directory {dir_path}: {e}")
        
        return removed_count
    
    def generate_report(self, duplicates: Dict[str, Dict[str, List[Tuple[Path, str]]]]) -> str:
        """Generate a summary report of duplicates found."""
        lines = ["🔍 Duplicate Example Files Report", "=" * 50]
        
        total_duplicate_files = 0
        total_groups = 0
        
        for version, version_duplicates in duplicates.items():
            version_file_count = sum(len(files) for files in version_duplicates.values())
            version_groups = len(version_duplicates)
            
            total_duplicate_files += version_file_count
            total_groups += version_groups
            
            lines.extend([
                f"\n📊 {version.upper()} API:",
                f"  Duplicate groups: {version_groups}",
                f"  Duplicate files: {version_file_count}",
                f"  Files to remove: {version_file_count - version_groups}",  # Keep 1 per group
            ])
            
            if version_duplicates:
                lines.append(f"\n  Top duplicate groups:")
                sorted_groups = sorted(version_duplicates.items(), 
                                     key=lambda x: len(x[1]), reverse=True)[:5]
                
                for content_hash, files in sorted_groups:
                    lines.append(f"    • {len(files)} files with hash {content_hash[:8]}...")
                    for file_path, filename in files[:3]:  # Show first 3
                        lines.append(f"      - {file_path.relative_to(self.base_path)}")
                    if len(files) > 3:
                        lines.append(f"      - ... and {len(files) - 3} more")
        
        lines.extend([
            "",
            f"📈 Summary:",
            f"  Total duplicate files: {total_duplicate_files}",
            f"  Total duplicate groups: {total_groups}",
            f"  Files that can be removed: {total_duplicate_files - total_groups}",
            f"  Space savings: Keep {total_groups}, remove {total_duplicate_files - total_groups}",
        ])
        
        return "\n".join(lines)


def main():
    """Main function to deduplicate example files."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deduplicate JSON example files by content')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be done without making changes (default: True)')
    parser.add_argument('--execute', action='store_true',
                       help='Actually perform the deduplication (overrides --dry-run)')
    parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'], default=['v1', 'v2'],
                       help='API versions to process (default: both)')
    parser.add_argument('--base-path', default='../../postman/json/kdf',
                       help='Base path to JSON examples (default: ../../postman/json/kdf)')
    parser.add_argument('--verbose', '-v', action='store_true', default=True,
                       help='Enable verbose output (default: True)')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output')
    
    args = parser.parse_args()
    
    # Change to script directory for relative paths
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    verbose = args.verbose and not args.quiet
    dry_run = args.dry_run and not args.execute
    
    deduplicator = ExampleDeduplicator(args.base_path, verbose=verbose)
    
    if not args.quiet:
        print("🔍 JSON Example Deduplication Tool")
        print(f"📁 Base path: {args.base_path}")
        print(f"📋 Versions: {', '.join(args.versions)}")
        print(f"🔄 Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print()
    
    # Scan for duplicates
    duplicates = deduplicator.scan_duplicates(args.versions)
    
    # Generate and display report
    if not args.quiet:
        print(deduplicator.generate_report(duplicates))
        print()
    
    # Remove duplicates
    if any(duplicates.values()):
        if not args.quiet:
            action = "Would remove" if dry_run else "Removing"
            print(f"🧹 {action} duplicate files...")
        
        stats = deduplicator.remove_duplicates(duplicates, dry_run=dry_run)
        
        # Clean empty directories
        empty_dirs_removed = deduplicator.clean_empty_directories(args.versions, dry_run=dry_run)
        
        if not args.quiet:
            print(f"\n✅ Deduplication {'Preview' if dry_run else 'Complete'}:")
            print(f"  🗑️  Files {'to remove' if dry_run else 'removed'}: {stats['files_removed']}")
            print(f"  ✅ Files kept: {stats['files_kept']}")
            print(f"  📁 Empty directories {'to remove' if dry_run else 'removed'}: {empty_dirs_removed}")
            print(f"  📊 Groups processed: {stats['groups_processed']}")
            
            if dry_run:
                print(f"\n💡 Run with --execute to perform actual deduplication")
    else:
        if not args.quiet:
            print("🎉 No duplicate files found!")
    
    return 0


if __name__ == "__main__":
    exit(main()) 