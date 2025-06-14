#!/usr/bin/env python3
"""
Deduplicator

Handles duplicate detection and removal for JSON example files.
Provides content-based deduplication and cleanup utilities.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict


class ExampleDeduplicator:
    """
    Handles deduplication of JSON example files.
    Uses content-based hashing to identify and remove duplicates.
    """
    
    def __init__(self, output_base: str, verbose: bool = True):
        self.output_base = Path(output_base)
        self.verbose = verbose
    
    def calculate_content_hash(self, json_content: dict) -> str:
        """Calculate a hash of the JSON content for comparison."""
        normalized = json.dumps(json_content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
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
                    
                    content_hash = self.calculate_content_hash(content)
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
                f"  Files to remove: {version_file_count - version_groups}",
            ])
            
            if version_duplicates:
                lines.append(f"\n  Top duplicate groups:")
                sorted_groups = sorted(
                    version_duplicates.items(), 
                    key=lambda x: len(x[1]), 
                    reverse=True
                )[:5]
                
                for content_hash, files in sorted_groups:
                    lines.append(f"    • {len(files)} files with hash {content_hash[:8]}...")
                    for file_path, filename in files[:3]:
                        lines.append(f"      - {file_path.relative_to(self.output_base)}")
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