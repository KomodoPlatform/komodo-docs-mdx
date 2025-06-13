#!/usr/bin/env python3
"""
Mapping Reports

Handles detailed reporting and statistics for mapping operations.
Provides formatted summaries and analysis reports for method mappings.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MethodMapping:
    """Represents a mapping between a method and its associated files."""
    method: str
    mdx_path: Optional[str] = None
    yaml_path: Optional[str] = None
    examples_path: Optional[str] = None
    example_count: int = 0
    
    @property
    def has_mdx(self) -> bool:
        return self.mdx_path is not None
    
    @property
    def has_yaml(self) -> bool:
        return self.yaml_path is not None
    
    @property
    def has_examples(self) -> bool:
        return self.example_count > 0
    
    @property
    def is_complete(self) -> bool:
        return self.has_mdx and self.has_yaml


class MappingReporter:
    """
    Generates detailed reports and statistics for mapping operations.
    Provides comprehensive analysis of method coverage and file associations.
    """
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
    
    def generate_detailed_mapping_stats(self, unified: Dict[str, Dict[str, MethodMapping]]) -> str:
        """Generate a comprehensive mapping statistics report."""
        lines = self._build_summary_header(unified)
        
        # Generate detailed version-specific stats
        for version in ["v1", "v2"]:
            lines.extend(self._generate_version_stats(version, unified[version]))
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def _build_summary_header(self, unified: Dict[str, Dict[str, MethodMapping]]) -> List[str]:
        """Build the summary header section."""
        total_methods = sum(len(methods) for methods in unified.values())
        v1_methods = len(unified["v1"])
        v2_methods = len(unified["v2"])
        
        return [
            f"\n{'=' * 60}",
            f"MAPPING SUMMARY",
            f"{'=' * 60}",
            f"Total methods: {total_methods}",
            f"  v1: {v1_methods} methods",
            f"  v2: {v2_methods} methods"
        ]
    
    def _generate_version_stats(self, version: str, mappings: Dict[str, MethodMapping]) -> List[str]:
        """Generate detailed statistics for a specific version."""
        lines = []
        
        # Calculate coverage statistics
        coverage_stats = self._calculate_coverage_stats(mappings.values())
        total_methods = len(mappings)
        
        # Helper function to calculate percentage
        def calc_pct(count: int) -> str:
            return f"({count/total_methods*100:.1f}%)" if total_methods > 0 else "(0.0%)"
        
        lines.extend([
            f"\n{version.upper()} Coverage:",
            f"  ✅ Complete (JSON, MDX & YAML): {coverage_stats['all_three']} {calc_pct(coverage_stats['all_three'])}",
            f"  📚 MDX + YAML (missing JSON): {coverage_stats['mdx_yaml_only']} {calc_pct(coverage_stats['mdx_yaml_only'])}",
            f"  🔬 MDX + JSON (missing YAML): {coverage_stats['mdx_json_only']} {calc_pct(coverage_stats['mdx_json_only'])}",
            f"  📊 YAML + JSON (missing MDX): {coverage_stats['yaml_json_only']} {calc_pct(coverage_stats['yaml_json_only'])}",
            f"  📄 MDX only (missing YAML & JSON): {coverage_stats['mdx_only']} {calc_pct(coverage_stats['mdx_only'])}",
            f"  📋 YAML only (missing MDX & JSON): {coverage_stats['yaml_only']} {calc_pct(coverage_stats['yaml_only'])}",
            f"  🧪 JSON only (missing MDX & YAML): {coverage_stats['json_only']} {calc_pct(coverage_stats['json_only'])}",
            f"  ❌ Missing all three: {coverage_stats['missing_all']} {calc_pct(coverage_stats['missing_all'])}",
        ])
        
        # Enhanced example statistics breakdown
        example_stats = self._calculate_detailed_example_stats(mappings.values())
        lines.extend([
            f"  🧪 Postman JSON Examples: {example_stats['with_examples']}/{len(mappings)} "
            f"({example_stats['coverage_pct']:.1f}%) - {example_stats['total_examples']} total examples"
        ])
        
        # Add detailed coverage breakdown
        if example_stats['methods_with_examples']:
            lines.append(f"      📄 Methods with documentation: {example_stats['with_mdx']}")
            lines.append(f"      📋 Methods with YAML specs: {example_stats['with_yaml']}")
            lines.append(f"      🔗 Methods with both MDX + JSON: {example_stats['mdx_and_examples']}")
            lines.append(f"      ⚠️  Methods with only JSON examples: {example_stats['examples_only']}")
        
        # Detailed breakdowns for missing items
        if coverage_stats['mdx_yaml_only_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods with MDX + YAML (missing JSON) ({version}):",
                coverage_stats['mdx_yaml_only_list']
            ))
        
        if coverage_stats['mdx_only_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods with MDX only (missing YAML & JSON) ({version}):",
                coverage_stats['mdx_only_list']
            ))
        
        if coverage_stats['yaml_only_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods with YAML only (missing MDX & JSON) ({version}):",
                coverage_stats['yaml_only_list']
            ))
        
        if coverage_stats['json_only_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods with JSON only (missing MDX & YAML) ({version}):",
                coverage_stats['json_only_list']
            ))
        
        if coverage_stats['missing_all_list']:
            lines.extend(self._generate_missing_section(
                f"\n  Methods missing all three ({version}):",
                coverage_stats['missing_all_list']
            ))
        
        return lines
    
    def _calculate_coverage_stats(self, mappings) -> Dict:
        """Calculate coverage statistics for a set of mappings."""
        mappings_list = list(mappings)
        
        # All 8 possible combinations
        all_three_list = [m for m in mappings_list if m.has_mdx and m.has_yaml and m.has_examples]
        mdx_yaml_only_list = [m for m in mappings_list if m.has_mdx and m.has_yaml and not m.has_examples]
        mdx_json_only_list = [m for m in mappings_list if m.has_mdx and not m.has_yaml and m.has_examples]
        yaml_json_only_list = [m for m in mappings_list if not m.has_mdx and m.has_yaml and m.has_examples]
        mdx_only_list = [m for m in mappings_list if m.has_mdx and not m.has_yaml and not m.has_examples]
        yaml_only_list = [m for m in mappings_list if not m.has_mdx and m.has_yaml and not m.has_examples]
        json_only_list = [m for m in mappings_list if not m.has_mdx and not m.has_yaml and m.has_examples]
        missing_all_list = [m for m in mappings_list if not m.has_mdx and not m.has_yaml and not m.has_examples]
        
        return {
            'all_three': len(all_three_list),
            'mdx_yaml_only': len(mdx_yaml_only_list),
            'mdx_json_only': len(mdx_json_only_list),
            'yaml_json_only': len(yaml_json_only_list),
            'mdx_only': len(mdx_only_list),
            'yaml_only': len(yaml_only_list),
            'json_only': len(json_only_list),
            'missing_all': len(missing_all_list),
            'all_three_list': all_three_list,
            'mdx_yaml_only_list': mdx_yaml_only_list,
            'mdx_json_only_list': mdx_json_only_list,
            'yaml_json_only_list': yaml_json_only_list,
            'mdx_only_list': mdx_only_list,
            'yaml_only_list': yaml_only_list,
            'json_only_list': json_only_list,
            'missing_all_list': missing_all_list,
            # Keep legacy fields for backward compatibility
            'complete': len(all_three_list) + len(mdx_yaml_only_list),  # MDX + YAML (with or without JSON)
            'complete_list': all_three_list + mdx_yaml_only_list,
            'missing_both': len(json_only_list) + len(missing_all_list),  # Missing both MDX and YAML
            'missing_both_list': json_only_list + missing_all_list
        }
    
    def _calculate_detailed_example_stats(self, mappings) -> Dict:
        """Calculate detailed example statistics for a set of mappings."""
        mappings_list = list(mappings)
        with_examples = [m for m in mappings_list if m.has_examples]
        total_examples = sum(m.example_count for m in mappings_list)
        coverage_pct = (len(with_examples) / len(mappings_list) * 100) if mappings_list else 0
        
        with_mdx = len([m for m in with_examples if m.has_mdx])
        with_yaml = len([m for m in with_examples if m.has_yaml])
        mdx_and_examples = len([m for m in with_examples if m.has_mdx and m.has_yaml])
        examples_only = len([m for m in with_examples if not m.has_mdx and not m.has_yaml])
        
        return {
            'with_examples': len(with_examples),
            'total_examples': total_examples,
            'coverage_pct': coverage_pct,
            'with_mdx': with_mdx,
            'with_yaml': with_yaml,
            'mdx_and_examples': mdx_and_examples,
            'examples_only': examples_only,
            'methods_with_examples': len(with_examples)
        }
    
    def _generate_missing_section(self, header: str, missing_list: List[MethodMapping]) -> List[str]:
        """Generate a section for missing items."""
        lines = [header]
        
        for mapping in sorted(missing_list, key=lambda x: x.method):
            examples_info = f" [{mapping.example_count} examples]" if mapping.has_examples else ""
            lines.append(f"    - {mapping.method}{examples_info}")
        
        return lines
    
    def generate_debug_report(self, method_name: str, version: str, 
                            mdx_mappings: Dict, yaml_mappings: Dict, 
                            example_mappings: Dict, variations: List[str]) -> str:
        """Generate a debug report for method matching."""
        lines = [
            f"\n🔍 Debugging method matching for: {method_name}",
            f"📝 Generated variations:"
        ]
        
        for i, variation in enumerate(variations, 1):
            lines.append(f"  {i}. {variation}")
        
        # MDX mapping check
        lines.extend(self._generate_debug_section(
            "📄 MDX mapping check:",
            method_name, mdx_mappings.get(version, {}), variations
        ))
        
        # YAML mapping check
        lines.extend(self._generate_debug_section(
            "📋 YAML mapping check:",
            method_name, yaml_mappings.get(version, {}), variations
        ))
        
        # Example mapping check
        lines.extend(self._generate_example_debug_section(
            "🧪 Example mapping check:",
            method_name, example_mappings.get(version, {}), variations
        ))
        
        lines.append("=" * 60)
        return "\n".join(lines)
    
    def _generate_debug_section(self, header: str, method_name: str, 
                              mapping_dict: Dict, variations: List[str]) -> List[str]:
        """Generate a debug section for a specific mapping type."""
        lines = [f"\n{header}"]
        
        # Direct or variation match
        found_match = self._find_debug_match(method_name, mapping_dict, variations)
        
        if found_match:
            lines.append(f"  ✅ Found: {found_match}")
        else:
            lines.append(f"  ❌ Not found in mappings")
            
            # Show similar methods
            similar_methods = self._find_similar_methods(method_name, mapping_dict)
            if similar_methods:
                lines.append(f"  🔍 Similar methods:")
                for similar in similar_methods[:5]:
                    lines.append(f"    - {similar}")
        
        return lines
    
    def _generate_example_debug_section(self, header: str, method_name: str, 
                                      example_mappings: Dict, variations: List[str]) -> List[str]:
        """Generate a debug section for example mappings."""
        lines = [f"\n{header}"]
        
        # Convert example mappings to simple dict for matching
        simple_dict = {k: v for k, v in example_mappings.items()}
        found_match = self._find_debug_match(method_name, simple_dict, variations)
        
        if found_match:
            path, count = found_match
            lines.append(f"  ✅ Found: {path} ({count} examples)")
        else:
            lines.append(f"  ❌ Not found in example mappings")
            
            # Show similar example methods
            similar_examples = self._find_similar_methods(method_name, simple_dict)
            if similar_examples:
                lines.append(f"  🔍 Similar example methods:")
                for similar in similar_examples[:5]:
                    count = example_mappings[similar][1] if similar in example_mappings else 0
                    lines.append(f"    - {similar} ({count} examples)")
        
        return lines
    
    def _find_debug_match(self, method_name: str, mapping_dict: Dict, variations: List[str]):
        """Find a match for debugging purposes."""
        # Direct match
        if method_name in mapping_dict:
            return mapping_dict[method_name]
        
        # Try variations
        for variation in variations:
            if variation in mapping_dict:
                return mapping_dict[variation]
        
        return None
    
    def _find_similar_methods(self, method_name: str, mapping_dict: Dict) -> List[str]:
        """Find similar methods for debugging suggestions."""
        if not method_name:
            return []
        
        method_parts = method_name.split('::')
        similar_methods = []
        
        for existing_method in mapping_dict.keys():
            if any(part in existing_method for part in method_parts):
                similar_methods.append(existing_method)
        
        return similar_methods
    
    def generate_coverage_summary(self, unified: Dict[str, Dict[str, MethodMapping]]) -> str:
        """Generate a brief coverage summary."""
        total_methods = sum(len(methods) for methods in unified.values())
        
        total_all_three = 0
        total_mdx_yaml = 0
        total_with_examples = 0
        
        for version_mappings in unified.values():
            mappings_list = list(version_mappings.values())
            total_all_three += len([m for m in mappings_list if m.has_mdx and m.has_yaml and m.has_examples])
            total_mdx_yaml += len([m for m in mappings_list if m.has_mdx and m.has_yaml])
            total_with_examples += len([m for m in mappings_list if m.has_examples])
        
        all_three_pct = (total_all_three / total_methods * 100) if total_methods else 0
        mdx_yaml_pct = (total_mdx_yaml / total_methods * 100) if total_methods else 0
        examples_pct = (total_with_examples / total_methods * 100) if total_methods else 0
        
        return (
            f"📊 Coverage Summary: {total_methods} methods total | "
            f"{all_three_pct:.1f}% complete (JSON+MDX+YAML) | "
            f"{mdx_yaml_pct:.1f}% with docs (MDX+YAML) | "
            f"{examples_pct:.1f}% with JSON examples"
        ) 