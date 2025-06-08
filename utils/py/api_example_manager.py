#!/usr/bin/env python3
"""
API Example Manager

This script manages JSON examples for the Komodo DeFi Framework API.
It extracts examples from MDX files using the mapping system and generates 
additional test cases to achieve comprehensive API coverage for both v1 and v2.
"""

import os
import re
import json
import copy
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from mapping import MethodMapper


@dataclass
class ExtractedExample:
    """Represents an extracted JSON example with metadata."""
    method_name: str
    operation: str
    example_type: str  # 'request' or 'response'
    content: Dict[str, Any]
    description: str
    source_file: str
    version: str  # 'v1' or 'v2'
    line_number: Optional[int] = None


class APIExampleManager:
    """
    Manages JSON examples for the KDF API using the mapping system.
    Extracts from MDX files and generates additional test cases.
    """
    
    def __init__(self, base_path: str = ".", verbose: bool = True):
        self.base_path = Path(base_path)
        self.verbose = verbose
        self.mapper = MethodMapper(base_path, verbose)
        self.output_base = "../../postman/json/kdf"
        
        # Load the unified mapping once
        self.unified_mapping = self.mapper.create_unified_mapping()
        
        # Generation templates for different method types
        self.generation_templates = {
            'activation': self._get_activation_templates(),
            'trading': self._get_trading_templates(),
            'wallet': self._get_wallet_templates(),
            'utility': self._get_utility_templates()
        }
    
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
                        # Extract from MDX using mapping data
                        examples = self.extract_from_mapped_mdx(method_name, mapping, version)
                        all_examples.extend(examples)
                        
                        extracted_count = len(examples)
                        stats[f'{version}_extracted'] += extracted_count
                        
                        if self.verbose and extracted_count > 0:
                            print(f"  📄 {method_name}: {extracted_count} examples")
                        
                        # Generate additional examples if we have base examples
                        if examples:
                            operation = self._determine_operation_from_mapping(method_name, mapping)
                            generated = self.generate_additional_examples(method_name, operation, examples, version)
                            all_examples.extend(generated)
                            stats[f'{version}_generated'] += len(generated)
                        
                        processed_methods += 1
                        
                except Exception as e:
                    if self.verbose:
                        print(f"❌ Error processing {method_name} ({version}): {e}")
                    stats['errors'] += 1
            
            stats[f'{version}_methods'] = processed_methods
            stats['total_methods_processed'] += processed_methods
            
            if self.verbose:
                print(f"✅ {version.upper()}: {processed_methods} methods processed, "
                      f"{stats[f'{version}_extracted']} extracted, {stats[f'{version}_generated']} generated")
        
        return all_examples, stats
    
    def extract_from_mapped_mdx(self, method_name: str, mapping: Any, version: str) -> List[ExtractedExample]:
        """Extract JSON examples from a mapped MDX file."""
        if not mapping.mdx_path or not os.path.exists(mapping.mdx_path):
            return []
        
        examples = []
        
        try:
            with open(mapping.mdx_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Use mapping data to enhance extraction
            method_context = {
                'method_name': method_name,
                'yaml_method': getattr(mapping, 'yaml_method', None),
                'operations': getattr(mapping, 'operations', []),
                'mdx_path': mapping.mdx_path,
                'version': version
            }
            
            # Find all CodeGroup blocks
            codegroup_pattern = r'<CodeGroup[^>]*>(.*?)</CodeGroup>'
            codegroups = re.findall(codegroup_pattern, content, re.DOTALL)
            
            for i, block in enumerate(codegroups):
                # Extract JSON from code blocks within CodeGroup
                json_examples = self._extract_json_from_codegroup_mapped(block, method_context)
                examples.extend(json_examples)
                
            # Find CollapsibleSection response examples
            collapsible_pattern = r'<CollapsibleSection[^>]*>(.*?)</CollapsibleSection>'
            collapsible_sections = re.findall(collapsible_pattern, content, re.DOTALL)
            
            for section in collapsible_sections:
                json_examples = self._extract_json_from_collapsible_mapped(section, method_context)
                examples.extend(json_examples)
                
        except Exception as e:
            if self.verbose:
                print(f"Error processing {mapping.mdx_path}: {e}")
            
        return examples
    
    def _extract_json_from_codegroup_mapped(self, block: str, method_context: Dict[str, Any]) -> List[ExtractedExample]:
        """Extract JSON examples from a CodeGroup block using mapping context."""
        examples = []
        
        # Find JSON code blocks
        json_pattern = r'```json\s*\n(.*?)```'
        json_blocks = re.findall(json_pattern, block, re.DOTALL)
        
        for json_content in json_blocks:
            try:
                # Parse JSON
                parsed_json = json.loads(json_content.strip())
                
                # Only extract requests (must have 'method' field)
                if 'method' not in parsed_json:
                    continue
                    
                example_type = 'request'
                
                # Use mapping context to determine method name
                method_name = self._resolve_method_name_from_context(parsed_json, method_context)
                
                # Skip if we can't determine a valid method name
                if not method_name or not self._is_valid_method_name(method_name):
                    if self.verbose:
                        print(f"Skipping invalid method name: {method_name} in {method_context['mdx_path']}")
                    continue
                    
                description = self._generate_description(parsed_json, example_type)
                operation = self._determine_operation_from_context(method_name, method_context)
                
                example = ExtractedExample(
                    method_name=method_name,
                    operation=operation,
                    example_type=example_type,
                    content=parsed_json,
                    description=description,
                    source_file=method_context['mdx_path'],
                    version=method_context['version']
                )
                examples.append(example)
                    
            except json.JSONDecodeError as e:
                if self.verbose:
                    print(f"JSON parse error in {method_context['mdx_path']}: {e}")
                    
        return examples
    
    def _extract_json_from_collapsible_mapped(self, section: str, method_context: Dict[str, Any]) -> List[ExtractedExample]:
        """Extract JSON examples from CollapsibleSection using mapping context."""
        examples = []
        
        # Find JSON code blocks in collapsible sections
        json_pattern = r'```json\s*\n(.*?)```'
        json_blocks = re.findall(json_pattern, section, re.DOTALL)
        
        for json_content in json_blocks:
            try:
                parsed_json = json.loads(json_content.strip())
                
                # Only extract requests (must have 'method' field)
                if 'method' not in parsed_json:
                    continue
                    
                example_type = 'request'
                
                # Use mapping context to determine method name
                method_name = self._resolve_method_name_from_context(parsed_json, method_context)
                
                # Skip if we can't determine a valid method name
                if not method_name or not self._is_valid_method_name(method_name):
                    if self.verbose:
                        print(f"Skipping invalid method name: {method_name} in {method_context['mdx_path']}")
                    continue
                    
                description = self._generate_description(parsed_json, example_type)
                operation = self._determine_operation_from_context(method_name, method_context)
                
                example = ExtractedExample(
                    method_name=method_name,
                    operation=operation,
                    example_type=example_type,
                    content=parsed_json,
                    description=description,
                    source_file=method_context['mdx_path'],
                    version=method_context['version']
                )
                examples.append(example)
                    
            except json.JSONDecodeError as e:
                if self.verbose:
                    print(f"JSON parse error in collapsible section {method_context['mdx_path']}: {e}")
                    
        return examples
    
    def _resolve_method_name_from_context(self, json_data: Dict[str, Any], method_context: Dict[str, Any]) -> Optional[str]:
        """Resolve method name using JSON data and mapping context."""
        # Direct method field (most reliable)
        if 'method' in json_data:
            method_name = json_data['method']
            if method_name and method_name.strip() and not method_name.strip() in [':', '::', '']:
                return method_name
        
        # Fallback to mapping context
        if method_context.get('method_name'):
            return method_context['method_name']
        
        # Try to extract from YAML method name
        if method_context.get('yaml_method'):
            return method_context['yaml_method']
        
        return None
    
    def _determine_operation_from_context(self, method_name: str, method_context: Dict[str, Any]) -> str:
        """Determine operation using method name and mapping context."""
        # First try the standard method name parsing
        if '::' in method_name:
            parts = method_name.split('::')
            if len(parts) >= 3:
                return parts[-1]  # Last part is usually the operation
        
        # Use mapping context operations if available
        if method_context.get('operations'):
            operations = method_context['operations']
            if operations and len(operations) > 0:
                # Return the first operation as default
                return operations[0]
        
        return 'default'
    
    def _determine_operation_from_mapping(self, method_name: str, mapping: Any) -> str:
        """Determine operation from mapping data."""
        # Check if mapping has operations
        if hasattr(mapping, 'operations') and mapping.operations:
            return mapping.operations[0] if mapping.operations else 'default'
        
        # Fallback to method name parsing
        return self._determine_operation(method_name)
    
    def _determine_operation(self, method_name: str) -> str:
        """Determine the operation type from method name."""
        if not method_name:
            return 'default'
            
        if '::' in method_name:
            parts = method_name.split('::')
            if len(parts) >= 3:
                return parts[-1]  # Last part is usually the operation
                
        return 'default'
    
    def _generate_description(self, json_data: Dict[str, Any], example_type: str) -> str:
        """Generate a descriptive name for the example (requests only)."""
        # Look for distinctive parameters in the request
        if 'params' in json_data:
            params = json_data['params']
            
            # Coin activation patterns
            if 'ticker' in params:
                ticker = params['ticker'].lower()
                if 'activation_params' in params:
                    activation_params = params['activation_params']
                    if 'mode' in activation_params and 'rpc' in activation_params['mode']:
                        rpc_mode = activation_params['mode']['rpc'].lower()
                        return f"{ticker}_{rpc_mode}_activation"
                return f"{ticker}_activation"
            
            # Hardware wallet patterns
            elif 'priv_key_policy' in params and params.get('priv_key_policy') == 'Trezor':
                return "trezor_mode"
            
            # Trading patterns
            elif 'base' in params and 'rel' in params:
                base = params['base']
                rel = params['rel']
                return f"{base}_{rel}_trade"
            
            # Task ID patterns
            elif 'task_id' in params:
                return "task_operation"
            
            # Coin patterns
            elif 'coin' in params:
                coin = params['coin'].lower()
                return f"{coin}_operation"
        
        # Default fallback
        return "basic_request"
    
    def generate_additional_examples(self, method_name: str, operation: str, base_examples: List[ExtractedExample], version: str) -> List[ExtractedExample]:
        """Generate additional test cases based on existing examples."""
        generated = []
        
        # Determine method category
        category = self._categorize_method(method_name)
        templates = self.generation_templates.get(category, {})
        
        if not templates:
            return generated
            
        # Generate variations based on category
        for template_name, template_data in templates.items():
            if self._should_apply_template(method_name, operation, template_name):
                new_example = self._apply_template(method_name, operation, template_data, base_examples, version)
                if new_example:
                    generated.append(new_example)
                    
        return generated
    
    def _categorize_method(self, method_name: str) -> str:
        """Categorize method for template selection."""
        if 'enable' in method_name or 'activation' in method_name:
            return 'activation'
        elif any(keyword in method_name for keyword in ['buy', 'sell', 'trade', 'order', 'swap']):
            return 'trading'
        elif any(keyword in method_name for keyword in ['balance', 'withdraw', 'address', 'wallet']):
            return 'wallet'
        else:
            return 'utility'
    
    def _should_apply_template(self, method_name: str, operation: str, template_name: str) -> bool:
        """Determine if a template should be applied to a method."""
        # Logic to determine template applicability
        # This would be method-specific
        return True
    
    def _apply_template(self, method_name: str, operation: str, template_data: Dict[str, Any], base_examples: List[ExtractedExample], version: str) -> Optional[ExtractedExample]:
        """Apply a template to generate a new example."""
        try:
            # Create a new example based on template
            new_content = copy.deepcopy(template_data['content'])
            
            # Customize for specific method
            if 'method' in new_content:
                new_content['method'] = method_name
                
            # Apply variations based on base examples
            if base_examples:
                # Use patterns from existing examples
                base_example = base_examples[0]
                if 'params' in base_example.content and 'params' in new_content:
                    # Merge parameter patterns
                    new_content['params'].update(self._extract_param_patterns(base_example.content['params']))
            
            return ExtractedExample(
                method_name=method_name,
                operation=operation,
                example_type=template_data['type'],
                content=new_content,
                description=template_data['description'],
                source_file='generated',
                version=version
            )
            
        except Exception as e:
            if self.verbose:
                print(f"Error applying template {template_data}: {e}")
            return None
    
    def _extract_param_patterns(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Extract parameter patterns from existing examples."""
        patterns = {}
        
        # Extract common patterns
        if 'ticker' in params:
            patterns['ticker'] = params['ticker']
        if 'activation_params' in params:
            patterns['activation_params'] = params['activation_params']
            
        return patterns
    
    def save_examples_to_files(self, examples: List[ExtractedExample]) -> int:
        """Save extracted examples to JSON files in the standardized structure."""
        saved_count = 0
        
        # Group examples by version, method, and operation
        grouped = self._group_examples_by_version(examples)
        
        for version, version_examples in grouped.items():
            for method_name, operations in version_examples.items():
                for operation, operation_examples in operations.items():
                    # Create directory structure
                    method_dir = method_name.replace('::', '-')
                    output_dir = Path(self.output_base) / version / method_dir / operation
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Save each example type
                    request_count = 1
                    response_count = 1
                    
                    for example in operation_examples:
                        if example.example_type == 'request':
                            filename = f"{method_dir}-{operation}-example-{request_count}-{example.description}-request.json"
                            request_count += 1
                        else:
                            filename = f"{method_dir}-{operation}-example-{response_count}-{example.description}-response.json"
                            response_count += 1
                        
                        filepath = output_dir / filename
                        
                        try:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                json.dump(example.content, f, indent=2, ensure_ascii=False)
                            
                            if self.verbose:
                                print(f"💾 Saved: {filepath}")
                            saved_count += 1
                            
                        except Exception as e:
                            print(f"❌ Error saving {filepath}: {e}")
        
        return saved_count
    
    def _group_examples_by_version(self, examples: List[ExtractedExample]) -> Dict[str, Dict[str, Dict[str, List[ExtractedExample]]]]:
        """Group examples by version, method, and operation."""
        grouped = {}
        
        for example in examples:
            version = example.version
            method = example.method_name
            operation = example.operation
            
            if version not in grouped:
                grouped[version] = {}
            if method not in grouped[version]:
                grouped[version][method] = {}
            if operation not in grouped[version][method]:
                grouped[version][method][operation] = []
                
            grouped[version][method][operation].append(example)
            
        return grouped
    
    def _group_examples(self, examples: List[ExtractedExample]) -> Dict[str, Dict[str, List[ExtractedExample]]]:
        """Group examples by method and operation (legacy method)."""
        grouped = {}
        
        for example in examples:
            method = example.method_name
            operation = example.operation
            
            if method not in grouped:
                grouped[method] = {}
            if operation not in grouped[method]:
                grouped[method][operation] = []
                
            grouped[method][operation].append(example)
            
        return grouped
    
    def generate_summary_report(self, examples: List[ExtractedExample], stats: Dict[str, int]) -> str:
        """Generate a summary report of the extraction process."""
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
        version_dist = {}
        for example in examples:
            version = example.version
            if version not in version_dist:
                version_dist[version] = {}
            method = example.method_name
            if method not in version_dist[version]:
                version_dist[version][method] = 0
            version_dist[version][method] += 1
        
        for version, methods in version_dist.items():
            report.append(f"📈 {version.upper()} Method Distribution:")
            for method, count in sorted(methods.items()):
                report.append(f"  {method}: {count} examples")
            report.append("")
        
        return "\n".join(report)
    
    def _get_activation_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get templates for activation methods."""
        return {
            'electrum_mode': {
                'type': 'request',
                'description': 'electrum_mode',
                'content': {
                    "userpass": "RPC_UserP@SSW0RD",
                    "mmrpc": "2.0",
                    "method": "placeholder",
                    "params": {
                        "ticker": "BTC",
                        "activation_params": {
                            "mode": {
                                "rpc": "Electrum",
                                "rpc_data": {
                                    "servers": [
                                        {"url": "electrum1.cipig.net:10000"},
                                        {"url": "electrum2.cipig.net:10001"}
                                    ]
                                }
                            }
                        }
                    }
                }
            },
            'native_mode': {
                'type': 'request',
                'description': 'native_mode',
                'content': {
                    "userpass": "RPC_UserP@SSW0RD",
                    "mmrpc": "2.0",
                    "method": "placeholder",
                    "params": {
                        "ticker": "KMD",
                        "activation_params": {
                            "mode": {
                                "rpc": "Native",
                                "rpc_data": {
                                    "datadir": "/home/user/.komodo",
                                    "conf": "komodo.conf"
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def _get_trading_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get templates for trading methods."""
        return {
            'basic_trade': {
                'type': 'request',
                'description': 'basic_trade',
                'content': {
                    "userpass": "RPC_UserP@SSW0RD",
                    "mmrpc": "2.0",
                    "method": "placeholder",
                    "params": {
                        "base": "KMD",
                        "rel": "BTC",
                        "price": "0.1",
                        "volume": "10"
                    }
                }
            }
        }
    
    def _get_wallet_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get templates for wallet methods."""
        return {
            'basic_wallet': {
                'type': 'request',
                'description': 'basic_request',
                'content': {
                    "userpass": "RPC_UserP@SSW0RD",
                    "mmrpc": "2.0",
                    "method": "placeholder",
                    "params": {}
                }
            }
        }
    
    def _get_utility_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get templates for utility methods."""
        return {
            'basic_utility': {
                'type': 'request',
                'description': 'basic_request',
                'content': {
                    "userpass": "RPC_UserP@SSW0RD",
                    "mmrpc": "2.0",
                    "method": "placeholder",
                    "params": {}
                }
            }
        }
    
    def _is_valid_method_name(self, method_name: str) -> bool:
        """Validate that a method name is reasonable and not just punctuation."""
        if not method_name:
            return False
            
        method_name = method_name.strip()
        
        # Reject empty, very short, or punctuation-only names
        if len(method_name) < 2:
            return False
            
        # Reject names that are just punctuation
        if method_name in [':', '::', ':::', '', '/', '\\', '-', '_']:
            return False
            
        # Reject names that start or end with invalid characters
        if method_name.startswith(':') or method_name.endswith(':'):
            return False
            
        # Ensure it has at least one letter
        if not any(c.isalpha() for c in method_name):
            return False
            
        return True


def main():
    """Main function to manage API examples via mapping system."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage JSON examples for KDF API using mapping system')
    parser.add_argument('--extract-only', action='store_true',
                       help='Only extract existing examples, do not generate new ones')
    parser.add_argument('--generate-only', action='store_true',
                       help='Only generate examples, do not extract from MDX')
    parser.add_argument('--method', type=str,
                       help='Process only a specific method')
    parser.add_argument('--versions', nargs='+', choices=['v1', 'v2'], default=['v1', 'v2'],
                       help='API versions to process (default: both v1 and v2)')
    parser.add_argument('--verbose', '-v', action='store_true', default=True,
                       help='Enable verbose output')
    parser.add_argument('--report', action='store_true',
                       help='Generate detailed summary report')
    
    args = parser.parse_args()
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    manager = APIExampleManager(verbose=args.verbose)
    
    print("🚀 Starting API Example Management via Mapping System...")
    print(f"📋 Processing versions: {', '.join(args.versions)}")
    
    # Extract examples using mapping system
    all_examples, stats = manager.extract_examples_via_mapping(args.versions)
    
    print(f"\n📊 Processing Results:")
    total_extracted = sum(stats[f'{v}_extracted'] for v in args.versions if f'{v}_extracted' in stats)
    total_generated = sum(stats[f'{v}_generated'] for v in args.versions if f'{v}_generated' in stats)
    
    print(f"  🔍 Total Methods: {stats['total_methods_processed']}")
    print(f"  📄 Extracted: {total_extracted}")
    print(f"  🔄 Generated: {total_generated}")
    print(f"  📚 Total Examples: {len(all_examples)}")
    print(f"  ❌ Errors: {stats['errors']}")
    
    # Save examples
    if all_examples:
        print(f"\n💾 Saving examples to {manager.output_base}/...")
        saved_count = manager.save_examples_to_files(all_examples)
        print(f"✅ Saved {saved_count} example files")
    else:
        print("⚠️ No examples to save")
    
    # Generate detailed report if requested
    if args.report:
        print("\n" + "="*60)
        print(manager.generate_summary_report(all_examples, stats))
        print("="*60)
    
    print("\n🎉 API Example Management completed!")


if __name__ == "__main__":
    main() 