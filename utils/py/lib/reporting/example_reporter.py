#!/usr/bin/env python3
"""
Example Reporter

Handles report generation and statistics for API example management.
Provides formatted summaries and analysis reports.
"""

from typing import Dict, List, TYPE_CHECKING, Tuple
from pathlib import Path
from .base_reporter import BaseReporter
from ..scanning.postman_scanners import ExtractedExample


class ExampleReporter(BaseReporter):
    """
    Generates reports and statistics for API example management operations.
    Provides formatted summaries and detailed analysis.
    """
    
    def generate_summary_report(self, examples: List['ExtractedExample'], stats: Dict[str, int]) -> str:
        """Generate a comprehensive summary report of the extraction process."""
        report = ["🎯 API Example Management Summary", "=" * 50]
        
        # Overall stats
        report.extend([
            f"📊 Total Methods Processed: {stats['total_methods_processed']}",
            f"📄 Total Examples: {len(examples)}",
            f"❌ Errors: {stats['errors']}",
            ""
        ])
        
        # Version breakdown
        for version in ['v1', 'v2']:
            if f'{version}_methods' in stats:
                report.extend([
                    f"🔍 {version.upper()} API:",
                    f"  Methods: {stats[f'{version}_methods']}",
                    f"  Extracted: {stats[f'{version}_extracted']}",
                    f"  Generated: {stats[f'{version}_generated']}",
                    ""
                ])
        
        # Method distribution
        version_dist = self._calculate_method_distribution(examples)
        
        for version, methods in version_dist.items():
            report.append(f"📈 {version.upper()} Method Distribution:")
            for method, count in sorted(methods.items()):
                report.append(f"  {method}: {count} examples")
            report.append("")
        
        # Example type breakdown
        type_breakdown = self._calculate_type_breakdown(examples)
        if type_breakdown:
            report.append("📋 Example Type Breakdown:")
            for example_type, count in type_breakdown.items():
                report.append(f"  {example_type}: {count}")
            report.append("")
        
        return "\n".join(report)
    
    def generate_processing_report(self, stats: Dict[str, int]) -> str:
        """Generate a focused processing report."""
        lines = ["📊 Processing Results:", "=" * 30]
        
        total_extracted = sum(stats[f'{v}_extracted'] for v in ['v1', 'v2'] if f'{v}_extracted' in stats)
        total_generated = sum(stats[f'{v}_generated'] for v in ['v1', 'v2'] if f'{v}_generated' in stats)
        
        lines.extend([
            f"🔍 Total Methods: {stats['total_methods_processed']}",
            f"📄 Extracted: {total_extracted}",
            f"🔄 Generated: {total_generated}",
            f"📚 Total Examples: {total_extracted + total_generated}",
            f"❌ Errors: {stats['errors']}"
        ])
        
        return "\n".join(lines)
    
    def generate_file_operation_report(self, operation: str, stats: Dict[str, int], 
                                     dry_run: bool = False) -> str:
        """Generate a report for file operations like consolidation or deduplication."""
        action_prefix = "Would" if dry_run else ""
        
        if operation == "consolidation":
            return self._generate_consolidation_report(stats, action_prefix)
        elif operation == "deduplication":
            return self._generate_deduplication_report_summary(stats, action_prefix)
        else:
            return f"📊 {operation.title()} Report:\n" + "\n".join(
                f"  {key}: {value}" for key, value in stats.items()
            )
    
    def generate_deduplication_report(self, duplicates: Dict[str, Dict[str, List[Tuple[Path, str]]]], 
                                    output_base: Path = None) -> str:
        """Generate a comprehensive summary report of duplicates found."""
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
                        if output_base:
                            relative_path = file_path.relative_to(output_base)
                        else:
                            relative_path = file_path
                        lines.append(f"      - {relative_path}")
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
    
    def _generate_consolidation_report(self, stats: Dict[str, int], action_prefix: str) -> str:
        """Generate consolidation-specific report."""
        lines = [f"📊 Consolidation {'Preview' if action_prefix else 'Complete'}:"]
        
        if 'files_moved' in stats:
            lines.append(f"  📄 Files {action_prefix.lower() + ' ' if action_prefix else ''}moved: {stats['files_moved']}")
        
        if 'folders_removed' in stats:
            lines.append(f"  🗑️  Folders {action_prefix.lower() + ' ' if action_prefix else ''}removed: {stats['folders_removed']}")
        elif 'folders_to_remove' in stats:
            lines.append(f"  🗑️  Folders to remove: {stats['folders_to_remove']}")
        
        if action_prefix:
            lines.append(f"\n💡 Run without --dry-run to apply changes")
        
        return "\n".join(lines)
    
    def _generate_deduplication_report_summary(self, stats: Dict[str, int], action_prefix: str) -> str:
        """Generate deduplication-specific report summary."""
        lines = [f"📊 Deduplication {'Preview' if action_prefix else 'Complete'}:"]
        
        lines.extend([
            f"  🗑️  Files {action_prefix.lower() + ' ' if action_prefix else ''}removed: {stats['files_removed']}",
            f"  ✅ Files kept: {stats['files_kept']}",
            f"  📊 Groups processed: {stats['groups_processed']}"
        ])
        
        if action_prefix:
            lines.append(f"\n💡 Run without --dedup-dry-run to perform actual deduplication")
        
        return "\n".join(lines)
    
    def _calculate_method_distribution(self, examples: List['ExtractedExample']) -> Dict[str, Dict[str, int]]:
        """Calculate distribution of examples by version and method."""
        version_dist = {}
        
        for example in examples:
            version = example.version
            if version not in version_dist:
                version_dist[version] = {}
            
            method = example.method_name
            if method not in version_dist[version]:
                version_dist[version][method] = 0
            
            version_dist[version][method] += 1
        
        return version_dist
    
    def _calculate_type_breakdown(self, examples: List['ExtractedExample']) -> Dict[str, int]:
        """Calculate breakdown by example type."""
        type_breakdown = {}
        
        for example in examples:
            example_type = example.example_type
            if example_type not in type_breakdown:
                type_breakdown[example_type] = 0
            
            type_breakdown[example_type] += 1
        
        return type_breakdown
    
    def generate_method_coverage_report(self, all_methods: Dict[str, List[str]], 
                                      processed_methods: Dict[str, List[str]]) -> str:
        """Generate a report showing method coverage."""
        lines = ["📊 Method Coverage Report", "=" * 40]
        
        for version in ['v1', 'v2']:
            total_methods = len(all_methods.get(version, []))
            processed_count = len(processed_methods.get(version, []))
            
            if total_methods > 0:
                coverage_pct = (processed_count / total_methods) * 100
                lines.extend([
                    f"\n🔍 {version.upper()} API:",
                    f"  Total methods: {total_methods}",
                    f"  Processed: {processed_count}",
                    f"  Coverage: {coverage_pct:.1f}%"
                ])
                
                # Show missing methods if any
                all_set = set(all_methods.get(version, []))
                processed_set = set(processed_methods.get(version, []))
                missing = all_set - processed_set
                
                if missing and len(missing) <= 10:  # Only show if reasonable number
                    lines.append(f"  Missing: {', '.join(sorted(missing))}")
                elif missing:
                    lines.append(f"  Missing: {len(missing)} methods")
        
        return "\n".join(lines) 