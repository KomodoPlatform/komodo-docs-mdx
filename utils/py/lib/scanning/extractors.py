#!/usr/bin/env python3
"""
Example Extractors

Classes for extracting JSON examples from different source formats.
Handles MDX parsing, JSON extraction, and content validation.
"""

import os
import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path
from ..mapping.path_utils import PathMapper


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


class MDXExtractor:
    """
    Extracts JSON examples from MDX documentation files.
    Handles CodeGroup parsing and method name resolution.
    """
    
    def __init__(self, verbose: bool = True, use_nested_structure: bool = True, base_path: str = "."):
        self.verbose = verbose
        self.use_nested_structure = use_nested_structure
        self.path_mapper = PathMapper(base_path) if use_nested_structure else None
        self.base_path = Path(base_path)
    
    def extract_from_mdx_file(self, method_name: str, mapping: Any, version: str) -> List[ExtractedExample]:
        """Extract JSON examples from a mapped MDX file."""
        if not mapping.mdx_path or not os.path.exists(mapping.mdx_path):
            return []
        
        examples = []
        
        try:
            with open(mapping.mdx_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create context for extraction
            method_context = {
                'method_name': method_name,
                'yaml_method': getattr(mapping, 'yaml_method', None),
                'operations': getattr(mapping, 'operations', []),
                'mdx_path': mapping.mdx_path,
                'version': version
            }
            
            # Extract from CodeGroup blocks (requests only)
            examples.extend(self._extract_from_codegroups(content, method_context))
            
            # Deduplicate examples
            if examples:
                unique_examples = self._deduplicate_examples(examples)
                if self.verbose and len(examples) != len(unique_examples):
                    removed_count = len(examples) - len(unique_examples)
                    print(f"  🔄 Deduplicated {method_name}: removed {removed_count} duplicate examples")
                examples = unique_examples
                
        except Exception as e:
            if self.verbose:
                print(f"Error processing {mapping.mdx_path}: {e}")
            
        return examples
    
    def _extract_from_codegroups(self, content: str, method_context: Dict[str, Any]) -> List[ExtractedExample]:
        """Extract examples from CodeGroup blocks."""
        examples = []
        
        # Find all CodeGroup blocks
        codegroup_pattern = r'<CodeGroup[^>]*>(.*?)</CodeGroup>'
        codegroups = re.findall(codegroup_pattern, content, re.DOTALL)
        
        for block in codegroups:
            examples.extend(self._extract_json_from_block(block, method_context))
        
        return examples
    
    def _extract_json_from_block(self, block: str, method_context: Dict[str, Any]) -> List[ExtractedExample]:
        """Extract JSON examples from a code block."""
        examples = []
        
        # Find JSON code blocks
        json_pattern = r'```json\s*\n(.*?)```'
        json_blocks = re.findall(json_pattern, block, re.DOTALL)
        
        for json_content in json_blocks:
            try:
                parsed_json = json.loads(json_content.strip())
                
                # Only extract requests (must have 'method' field)
                if 'method' not in parsed_json:
                    continue
                
                # Resolve method name from context
                method_name = self._resolve_method_name(parsed_json, method_context)
                
                if not method_name or not self._is_valid_method_name(method_name):
                    if self.verbose:
                        print(f"Skipping invalid method name: {method_name} in {method_context['mdx_path']}")
                    continue
                
                description = self._generate_description(parsed_json)
                operation = 'default'  # Simplified operation handling
                
                example = ExtractedExample(
                    method_name=method_name,
                    operation=operation,
                    example_type='request',
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
    
    def _resolve_method_name(self, json_data: Dict[str, Any], method_context: Dict[str, Any]) -> Optional[str]:
        """Resolve method name using JSON data and mapping context."""
        # Direct method field (most reliable)
        if 'method' in json_data:
            method_name = json_data['method']
            if method_name and method_name.strip() and not method_name.strip() in [':', '::', '']:
                return self._normalize_method_name(method_name)
        
        # Fallback to mapping context
        if method_context.get('method_name'):
            return self._normalize_method_name(method_context['method_name'])
        
        return None
    
    def _normalize_method_name(self, method_name: str) -> str:
        """Convert filesystem-safe format to proper :: format."""
        if not method_name or '::' in method_name:
            return method_name
        
        # Convert specific patterns we know are filesystem substitutions
        if (method_name.startswith('task-') or 
            method_name.startswith('stream-') or 
            'lightning-' in method_name or
            method_name.count('-') >= 2):
            return method_name.replace('-', '::')
        
        return method_name
    
    def _generate_description(self, json_data: Dict[str, Any]) -> str:
        """Generate a descriptive name for the example."""
        if 'params' in json_data:
            params = json_data['params']
            
            # Coin activation patterns
            if 'ticker' in params:
                ticker = params['ticker'].lower()
                if 'activation_params' in params:
                    activation_params = params['activation_params']
                    if 'mode' in activation_params and 'rpc' in activation_params['mode']:
                        return f"{ticker}_rpc_activation"
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
        
        return "basic_request"
    
    def _is_valid_method_name(self, method_name: str) -> bool:
        """Validate that a method name is reasonable."""
        if not method_name:
            return False
        
        method_name = method_name.strip()
        
        # Basic validation rules
        if (len(method_name) < 2 or
            method_name in [':', '::', ':::', '', '/', '\\', '-', '_'] or
            method_name.startswith(':') or method_name.endswith(':') or
            not any(c.isalpha() for c in method_name)):
            return False
        
        return True
    
    def _deduplicate_examples(self, examples: List[ExtractedExample]) -> List[ExtractedExample]:
        """Remove duplicate examples based on content hash."""
        import hashlib
        
        seen_hashes = set()
        unique_examples = []
        
        for example in examples:
            # Create content hash for deduplication
            content_str = json.dumps(example.content, sort_keys=True, ensure_ascii=False)
            content_hash = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_examples.append(example)
        
        return unique_examples

    def save_extracted_examples(self, examples: List[ExtractedExample], dry_run: bool = False) -> int:
        """
        Save extracted examples to JSON files using the configured structure.
        
        Args:
            examples: List of extracted examples to save
            dry_run: If True, only log what would be saved without actually saving
            
        Returns:
            Number of files saved (or would be saved in dry run)
        """
        if not examples:
            return 0
            
        # Group examples by method
        grouped_examples = {}
        for example in examples:
            key = (example.method_name, example.version)
            if key not in grouped_examples:
                grouped_examples[key] = []
            grouped_examples[key].append(example)
        
        saved_count = 0
        
        for (method_name, version), method_examples in grouped_examples.items():
            if self.use_nested_structure and self.path_mapper:
                # Use nested structure
                saved_count += self._save_examples_nested(method_name, version, method_examples, dry_run)
            else:
                # Use legacy flat structure  
                saved_count += self._save_examples_flat(method_name, version, method_examples, dry_run)
        
        return saved_count
    
    def _save_examples_nested(self, method_name: str, version: str, examples: List[ExtractedExample], dry_run: bool) -> int:
        """Save examples using nested directory structure."""
        if not examples:
            return 0
            
        # Get the MDX path from the first example
        mdx_path = examples[0].source_file
        
        # Get path mapping for this method
        path_mapping = self.path_mapper.get_method_path_mapping(method_name, mdx_path, version)
        
        # Create directory structure
        if not dry_run:
            self.path_mapper.create_directory_structure(path_mapping, dry_run=False)
        
        saved_count = 0
        
        # Save each example
        for i, example in enumerate(examples, 1):
            filename = f"{example.method_name.replace('::', '-')}-{example.description}-{example.example_type}-{i}.json"
            file_path = Path(path_mapping.postman_json_path) / filename
            
            if dry_run:
                print(f"[DRY RUN] Would save: {file_path}")
            else:
                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(example.content, f, indent=2, ensure_ascii=False)
                    if self.verbose:
                        print(f"  💾 Saved: {file_path}")
                except Exception as e:
                    print(f"Error saving {file_path}: {e}")
                    continue
            
            saved_count += 1
        
        return saved_count
    
    def _save_examples_flat(self, method_name: str, version: str, examples: List[ExtractedExample], dry_run: bool) -> int:
        """Save examples using legacy flat directory structure."""
        if not examples:
            return 0
            
        # Create flat directory path
        method_dir_name = method_name.replace('::', '-').lower()
        output_dir = self.base_path / f"../postman/json/kdf/{version}/{method_dir_name}"
        
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        
        # Save each example
        for i, example in enumerate(examples, 1):
            filename = f"{example.method_name.replace('::', '-')}-{example.description}-{example.example_type}-{i}.json"
            file_path = output_dir / filename
            
            if dry_run:
                print(f"[DRY RUN] Would save: {file_path}")
            else:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(example.content, f, indent=2, ensure_ascii=False)
                    if self.verbose:
                        print(f"  💾 Saved: {file_path}")
                except Exception as e:
                    print(f"Error saving {file_path}: {e}")
                    continue
            
            saved_count += 1
        
        return saved_count 