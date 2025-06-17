#!/usr/bin/env python3
"""
Comprehensive scanner for existing KDF method documentation to build pattern awareness.
This will analyze all existing method docs to understand actual parameter patterns.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class MethodParameter:
    name: str
    type: str
    required: bool
    default: Optional[str] = None
    description: str = ""


@dataclass
class MethodPattern:
    method_name: str
    version: str
    parameters: List[MethodParameter]
    response_parameters: List[MethodParameter]
    error_types: List[str]
    file_path: str


class ExistingDocsScanner:
    """Scans existing KDF documentation to extract method patterns."""
    
    def __init__(self, docs_base_path: str = "../../src/pages/komodo-defi-framework/api"):
        self.docs_base_path = Path(docs_base_path)
        self.patterns: Dict[str, MethodPattern] = {}
    
    def scan_all_methods(self) -> Dict[str, MethodPattern]:
        """Scan all existing method documentation."""
        print("🔍 Scanning existing KDF method documentation...")
        
        # Scan v1 and v2 directories
        for version in ["v1", "v2", "v20"]:
            version_path = self.docs_base_path / version
            if version_path.exists():
                self._scan_version_directory(version_path, version)
        
        print(f"✅ Found {len(self.patterns)} documented methods")
        return self.patterns
    
    def _scan_version_directory(self, version_path: Path, version: str):
        """Scan a specific version directory."""
        for mdx_file in version_path.rglob("index.mdx"):
            try:
                pattern = self._extract_method_pattern(mdx_file, version)
                if pattern:
                    self.patterns[pattern.method_name] = pattern
                    print(f"  📄 {pattern.method_name} ({version})")
            except Exception as e:
                print(f"  ⚠️  Error scanning {mdx_file}: {e}")
    
    def _extract_method_pattern(self, mdx_file: Path, version: str) -> Optional[MethodPattern]:
        """Extract method pattern from an MDX file."""
        try:
            content = mdx_file.read_text(encoding='utf-8')
            
            # Extract method name from ## heading
            method_match = re.search(r'^## ([a-zA-Z0-9_:]+)', content, re.MULTILINE)
            if not method_match:
                return None
            
            method_name = method_match.group(1)
            
            # Extract request parameters
            parameters = self._extract_parameters_table(content, "### Request Parameters")
            
            # Extract response parameters  
            response_parameters = self._extract_parameters_table(content, "### Response Parameters")
            
            # Extract error types
            error_types = self._extract_error_types(content)
            
            return MethodPattern(
                method_name=method_name,
                version=version,
                parameters=parameters,
                response_parameters=response_parameters,
                error_types=error_types,
                file_path=str(mdx_file)
            )
            
        except Exception as e:
            print(f"Error extracting pattern from {mdx_file}: {e}")
            return None
    
    def _extract_parameters_table(self, content: str, section_header: str) -> List[MethodParameter]:
        """Extract parameters from a table section."""
        parameters = []
        
        # Find the section
        section_match = re.search(rf'{re.escape(section_header)}.*?\n(.*?)(?=\n###|\n##|\nℹ️|\n<|\Z)', 
                                content, re.DOTALL)
        if not section_match:
            return parameters
        
        section_content = section_match.group(1)
        
        # Extract table rows
        table_rows = re.findall(r'\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|([^|]*)\|?', section_content)
        
        for row in table_rows:
            if len(row) >= 3 and not row[0].strip().startswith('-'):  # Skip header separator
                param_name = row[0].strip()
                param_type = row[1].strip()
                required_str = row[2].strip()
                
                # Skip header row
                if param_name.lower() == 'parameter':
                    continue
                
                required = '✓' in required_str or 'true' in required_str.lower()
                
                default = None
                description = ""
                
                if len(row) >= 4:
                    default_str = row[3].strip()
                    if default_str and default_str != '-':
                        default = default_str.strip('`')
                
                if len(row) >= 5:
                    description = row[4].strip()
                elif len(row) == 4:
                    # 4-column format (no default column)
                    description = row[3].strip()
                
                parameters.append(MethodParameter(
                    name=param_name,
                    type=param_type,
                    required=required,
                    default=default,
                    description=description
                ))
        
        return parameters
    
    def _extract_error_types(self, content: str) -> List[str]:
        """Extract error types from the Error Types section."""
        error_types = []
        
        section_match = re.search(r'### Error Types.*?\n(.*?)(?=\n###|\n##|\n<|\Z)', 
                                content, re.DOTALL)
        if not section_match:
            return error_types
        
        section_content = section_match.group(1)
        
        # Extract error type names from table
        error_rows = re.findall(r'\|([^|]+)\|[^|]+\|[^|]+\|', section_content)
        
        for row in error_rows:
            error_name = row.strip()
            if error_name and error_name.lower() != 'parameter':
                error_types.append(error_name)
        
        return error_types
    
    def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze the discovered patterns to identify commonalities."""
        analysis = {
            "total_methods": len(self.patterns),
            "method_categories": {},
            "common_parameters": {},
            "common_error_types": {},
            "parameter_patterns": {}
        }
        
        # Categorize methods
        for method_name, pattern in self.patterns.items():
            category = self._categorize_method(method_name)
            if category not in analysis["method_categories"]:
                analysis["method_categories"][category] = []
            analysis["method_categories"][category].append(method_name)
        
        # Find common parameters
        param_counts = {}
        for pattern in self.patterns.values():
            for param in pattern.parameters:
                key = f"{param.name}:{param.type}"
                param_counts[key] = param_counts.get(key, 0) + 1
        
        analysis["common_parameters"] = {
            k: v for k, v in param_counts.items() 
            if v >= 3  # Appears in 3+ methods
        }
        
        # Find common error types
        error_counts = {}
        for pattern in self.patterns.values():
            for error in pattern.error_types:
                error_counts[error] = error_counts.get(error, 0) + 1
        
        analysis["common_error_types"] = {
            k: v for k, v in error_counts.items()
            if v >= 3  # Appears in 3+ methods
        }
        
        return analysis
    
    def _categorize_method(self, method_name: str) -> str:
        """Categorize a method based on its name."""
        if method_name.startswith("task::"):
            parts = method_name.split("::")
            if len(parts) >= 3:
                return f"task::{parts[1]}"
            return "task"
        elif method_name.startswith("lightning::"):
            parts = method_name.split("::")
            if len(parts) >= 3:
                return f"lightning::{parts[1]}"
            return "lightning"
        elif method_name.startswith("stream::"):
            return "streaming"
        else:
            return "other"
    
    def save_patterns(self, output_file: str = "data/existing_method_patterns.json"):
        """Save the discovered patterns to a JSON file."""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        serializable_patterns = {}
        for method_name, pattern in self.patterns.items():
            serializable_patterns[method_name] = {
                "method_name": pattern.method_name,
                "version": pattern.version,
                "parameters": [asdict(p) for p in pattern.parameters],
                "response_parameters": [asdict(p) for p in pattern.response_parameters],
                "error_types": pattern.error_types,
                "file_path": pattern.file_path
            }
        
        with open(output_path, 'w') as f:
            json.dump(serializable_patterns, f, indent=2)
        
        print(f"✅ Saved {len(self.patterns)} method patterns to {output_path}")


def main():
    """Main function to run the documentation scanner."""
    scanner = ExistingDocsScanner()
    
    # Scan all existing documentation
    patterns = scanner.scan_all_methods()
    
    # Analyze patterns
    analysis = scanner.analyze_patterns()
    
    # Save patterns
    scanner.save_patterns()
    
    # Print analysis summary
    print("\n📊 Pattern Analysis Summary:")
    print(f"  📄 Total methods: {analysis['total_methods']}")
    print(f"  📂 Categories: {len(analysis['method_categories'])}")
    
    for category, methods in analysis['method_categories'].items():
        print(f"    • {category}: {len(methods)} methods")
    
    print(f"  🔧 Common parameters: {len(analysis['common_parameters'])}")
    for param, count in list(analysis['common_parameters'].items())[:5]:
        print(f"    • {param}: {count} methods")
    
    print(f"  ⚠️  Common error types: {len(analysis['common_error_types'])}")
    for error, count in list(analysis['common_error_types'].items())[:5]:
        print(f"    • {error}: {count} methods")


if __name__ == "__main__":
    main() 