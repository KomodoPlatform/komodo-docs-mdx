#!/usr/bin/env python3
"""
Validation Manager

Centralized validation functionality for the Komodo Documentation Library.
Provides comprehensive validation for files, data structures, and configurations.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
import yaml

# Core imports
from ..constants.config import get_config
from ..constants.exceptions import ValidationError, FileOperationError
from ..constants.enums import ValidationLevel
from ..utils.logging_utils import get_logger


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    data: Optional[Any] = None
    
    def add_error(self, message: str):
        """Add validation error."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)
    
    def merge(self, other: 'ValidationResult'):
        """Merge with another validation result."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


class JSONValidator:
    """
    Comprehensive JSON validation with schema support.
    
    Validates JSON syntax, structure, and content against schemas.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.logger = get_logger("json-validator")
        
        # Predefined schemas for common structures
        self._schemas = self._load_predefined_schemas()
    
    def _load_predefined_schemas(self) -> Dict[str, Dict]:
        """Load predefined JSON schemas."""
        return {
            'postman_request': {
                'type': 'object',
                'required': ['method', 'url'],
                'properties': {
                    'method': {'type': 'string'},
                    'url': {'type': 'string'},
                    'body': {'type': 'object'},
                    'headers': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'key': {'type': 'string'},
                                'value': {'type': 'string'}
                            }
                        }
                    }
                }
            },
            'kdf_request': {
                'type': 'object',
                'required': ['method'],
                'properties': {
                    'method': {'type': 'string'},
                    'mmrpc': {'type': 'string'},
                    'params': {'type': 'object'},
                    'id': {'type': ['integer', 'string']},
                    'userpass': {'type': 'string'}
                }
            },
            'kdf_response': {
                'type': 'object',
                'properties': {
                    'mmrpc': {'type': 'string'},
                    'result': {'type': 'object'},
                    'error': {'type': 'string'},
                    'id': {'type': ['integer', 'string']}
                }
            },
            'openapi_path': {
                'type': 'object',
                'properties': {
                    'operationId': {'type': 'string'},
                    'summary': {'type': 'string'},
                    'description': {'type': 'string'},
                    'parameters': {'type': 'array'},
                    'responses': {'type': 'object'}
                }
            }
        }
    
    def validate_json_string(self, json_string: str, schema_name: str = None) -> ValidationResult:
        """Validate JSON string with optional schema."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Parse JSON
        try:
            data = json.loads(json_string)
            result.data = data
        except json.JSONDecodeError as e:
            result.add_error(f"Invalid JSON syntax: {e}")
            return result
        
        # Validate against schema if provided
        if schema_name:
            schema_result = self.validate_against_schema(data, schema_name)
            result.merge(schema_result)
        
        # General validation
        general_result = self._validate_general_structure(data)
        result.merge(general_result)
        
        return result
    
    def validate_json_file(self, file_path: Union[str, Path], schema_name: str = None) -> ValidationResult:
        """Validate JSON file with optional schema."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Validate content
            content_result = self.validate_json_string(content, schema_name)
            result.merge(content_result)
            result.data = content_result.data
            
        except FileNotFoundError:
            result.add_error(f"File not found: {file_path}")
        except PermissionError:
            result.add_error(f"Permission denied: {file_path}")
        except Exception as e:
            result.add_error(f"Error reading file {file_path}: {e}")
        
        return result
    
    def validate_against_schema(self, data: Any, schema_name: str) -> ValidationResult:
        """Validate data against a predefined schema."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if schema_name not in self._schemas:
            result.add_warning(f"Unknown schema: {schema_name}")
            return result
        
        schema = self._schemas[schema_name]
        validation_result = self._validate_schema(data, schema, "root")
        result.merge(validation_result)
        
        return result
    
    def _validate_schema(self, data: Any, schema: Dict, path: str) -> ValidationResult:
        """Recursively validate data against schema."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check type
        if 'type' in schema:
            type_result = self._validate_type(data, schema['type'], path)
            result.merge(type_result)
        
        # Check required fields for objects
        if isinstance(data, dict) and 'required' in schema:
            for field in schema['required']:
                if field not in data:
                    result.add_error(f"Missing required field '{field}' at {path}")
        
        # Validate object properties
        if isinstance(data, dict) and 'properties' in schema:
            for key, value in data.items():
                if key in schema['properties']:
                    prop_result = self._validate_schema(
                        value, schema['properties'][key], f"{path}.{key}"
                    )
                    result.merge(prop_result)
                elif self.level == ValidationLevel.STRICT:
                    result.add_warning(f"Unknown property '{key}' at {path}")
        
        # Validate array items
        if isinstance(data, list) and 'items' in schema:
            for i, item in enumerate(data):
                item_result = self._validate_schema(
                    item, schema['items'], f"{path}[{i}]"
                )
                result.merge(item_result)
        
        return result
    
    def _validate_type(self, data: Any, expected_type: Union[str, List[str]], path: str) -> ValidationResult:
        """Validate data type."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Handle multiple allowed types
        if isinstance(expected_type, list):
            type_valid = any(
                self._check_type_match(data, t) for t in expected_type
            )
            if not type_valid:
                result.add_error(
                    f"Type mismatch at {path}: expected one of {expected_type}, "
                    f"got {self._get_json_type(data)}"
                )
        else:
            if not self._check_type_match(data, expected_type):
                result.add_error(
                    f"Type mismatch at {path}: expected {expected_type}, "
                    f"got {self._get_json_type(data)}"
                )
        
        return result
    
    def _check_type_match(self, data: Any, expected_type: str) -> bool:
        """Check if data matches expected JSON type."""
        json_type = self._get_json_type(data)
        return json_type == expected_type
    
    def _get_json_type(self, data: Any) -> str:
        """Get JSON type name for data."""
        if isinstance(data, bool):
            return "boolean"
        elif isinstance(data, int):
            return "integer"
        elif isinstance(data, float):
            return "number"
        elif isinstance(data, str):
            return "string"
        elif isinstance(data, list):
            return "array"
        elif isinstance(data, dict):
            return "object"
        elif data is None:
            return "null"
        else:
            return "unknown"
    
    def _validate_general_structure(self, data: Any) -> ValidationResult:
        """Validate general structure and common patterns."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check for deeply nested structures
        if isinstance(data, (dict, list)):
            depth = self._calculate_depth(data)
            if depth > 10:
                result.add_warning(f"Very deep nesting detected: {depth} levels")
        
        # Check for very large structures  
        if isinstance(data, (dict, list)):
            size = len(str(data))
            if size > 1024 * 1024:  # 1MB
                result.add_warning(f"Very large JSON structure: {size:,} characters")
        
        return result
    
    def _calculate_depth(self, data: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth."""
        if not isinstance(data, (dict, list)):
            return current_depth
        
        if isinstance(data, dict):
            if not data:
                return current_depth
            return max(
                self._calculate_depth(v, current_depth + 1) for v in data.values()
            )
        else:  # list
            if not data:
                return current_depth
            return max(
                self._calculate_depth(item, current_depth + 1) for item in data
            )
    
    def add_custom_schema(self, name: str, schema: Dict):
        """Add a custom validation schema."""
        self._schemas[name] = schema
    
    def get_available_schemas(self) -> List[str]:
        """Get list of available schema names."""
        return list(self._schemas.keys())


class MethodNameValidator:
    """
    Validates API method names according to KDF conventions.
    Enhanced with utilities from string_utils.py.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.logger = get_logger("method-name-validator")
        
        # Common method name patterns
        self.valid_patterns = [
            r'^[a-z_][a-z0-9_]*$',  # Simple snake_case
            r'^[a-z_][a-z0-9_]*::[a-z_][a-z0-9_]*$',  # Namespaced methods
            r'^[a-z_][a-z0-9_]*::[a-z_][a-z0-9_]*::[a-z_][a-z0-9_]*$'  # Task methods
        ]
    
    def validate_method_name(self, method_name: str) -> ValidationResult:
        """Validate a method name."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not method_name:
            result.add_error("Method name cannot be empty")
            return result
        
        # Check length
        if len(method_name) < 2:
            result.add_error("Method name too short (minimum 2 characters)")
        elif len(method_name) > 100:
            result.add_error("Method name too long (maximum 100 characters)")
        
        # Use enhanced validation from string_utils.py
        if not self.is_valid_method_name(method_name):
            if self.level == ValidationLevel.STRICT:
                result.add_error(
                    f"Method name '{method_name}' doesn't match expected patterns"
                )
            else:
                result.add_warning(
                    f"Method name '{method_name}' may not follow conventions"
                )
        
        # Check for reserved words
        reserved_words = ['class', 'def', 'if', 'else', 'for', 'while', 'return']
        if method_name.lower() in reserved_words:
            result.add_warning(f"Method name '{method_name}' is a reserved word")
        
        return result
    
    def is_valid_method_name(self, method_name: str) -> bool:
        """
        Enhanced method name validation from string_utils.py.
        
        Args:
            method_name: Method name to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not method_name:
            return False
        
        method_name = method_name.strip()
        
        # Basic validation rules
        if (len(method_name) < 2 or
            method_name in [':', '::', ':::', '', '/', '\\', '-', '_'] or
            method_name.startswith(':') or method_name.endswith(':') or
            not any(c.isalpha() for c in method_name)):
            return False
        
        # Check for valid characters (letters, numbers, colons, hyphens, underscores, dots)
        valid_chars = re.compile(r'^[a-zA-Z0-9_:.-]+$')
        if not valid_chars.match(method_name):
            return False
        
        return True
    
    @lru_cache(maxsize=128)
    def clean_method_name(self, method_name: str) -> str:
        """
        Clean and normalize method name by removing problematic characters.
        
        Args:
            method_name: Raw method name
            
        Returns:
            Cleaned method name
        """
        if not method_name:
            return ""
        
        # Remove leading/trailing whitespace
        cleaned = method_name.strip()
        
        # Remove common problematic prefixes
        prefixes_to_remove = [
            "komodo defi framework method: ",
            "kdf method: ",
            "method: ",
            "api method: "
        ]
        
        cleaned_lower = cleaned.lower()
        for prefix in prefixes_to_remove:
            if cleaned_lower.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
                break
        
        # Remove extra whitespace and normalize separators
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Convert common separators to double colon
        cleaned = cleaned.replace(' → ', '::')
        cleaned = cleaned.replace(' -> ', '::')
        cleaned = cleaned.replace(' | ', '::')
        
        # Handle special characters
        cleaned = cleaned.replace('"', '').replace("'", "")
        cleaned = cleaned.replace('(', '').replace(')', '')
        cleaned = cleaned.replace('[', '').replace(']', '')
        
        return cleaned.strip()


class FileFormatValidator:
    """
    Validates various file formats used in the project.
    Enhanced with MDX content extraction capabilities.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.logger = get_logger("file-format-validator")
    
    def validate_mdx_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate MDX file structure and content."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required MDX elements
            if not content.strip():
                result.add_error("MDX file is empty")
                return result
            
            # Check for export statements
            if 'export const title' not in content:
                result.add_warning("Missing 'export const title' statement")
            
            if 'export const description' not in content:
                result.add_warning("Missing 'export const description' statement")
            
            # Check for proper heading structure
            lines = content.split('\n')
            has_main_heading = any(line.startswith('# ') for line in lines)
            
            if not has_main_heading:
                result.add_warning("Missing main heading (# level)")
            
            # Extract method name if present
            method_name = self.extract_method_name_from_mdx_content(content)
            if method_name:
                result.data = {'method_name': method_name}
            
        except Exception as e:
            result.add_error(f"Error reading MDX file: {e}")
        
        return result
    
    def validate_yaml_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate YAML file syntax and structure."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse YAML
            try:
                data = yaml.safe_load(content)
                result.data = data
            except yaml.YAMLError as e:
                result.add_error(f"Invalid YAML syntax: {e}")
                return result
            
            # Validate YAML structure
            if data is None:
                result.add_warning("YAML file contains no data")
            elif isinstance(data, dict):
                # Check for common OpenAPI fields if it looks like an API spec
                if any(key in data for key in ['paths', 'openapi', 'swagger']):
                    self._validate_openapi_yaml(data, result)
            
        except Exception as e:
            result.add_error(f"Error reading YAML file: {e}")
        
        return result
    
    def _validate_openapi_yaml(self, data: Dict, result: ValidationResult):
        """Validate OpenAPI YAML structure."""
        required_fields = ['paths']
        
        for field in required_fields:
            if field not in data:
                result.add_warning(f"Missing OpenAPI field: {field}")
        
        # Check version
        if 'openapi' in data:
            version = data['openapi']
            if not version.startswith('3.'):
                result.add_warning(f"OpenAPI version {version} may not be fully supported")
    
    def extract_method_name_from_mdx_content(self, content: str) -> Optional[str]:
        """
        Extract method name from MDX content using standardized pattern.
        
        Args:
            content: MDX file content
            
        Returns:
            Method name if found, None otherwise
        """
        # Look for method heading pattern (##\s+method_name\s*{{)
        method_pattern = r'##\s+([a-zA-Z0-9_:.-]+)\s*\{\{'
        match = re.search(method_pattern, content)
        
        if match:
            return match.group(1).strip()
        
        return None
    
    def extract_method_name_from_yaml_filename(self, filename: str, version: str) -> Optional[str]:
        """
        Extract method name from YAML filename using standardized conversion.
        
        Args:
            filename: YAML filename
            version: API version (v1 or v2)
            
        Returns:
            Method name if valid, None otherwise
        """
        # Remove extension
        name = filename.replace('.yaml', '').replace('.yml', '')
        
        # Convert to method format based on version
        if version == 'v1':
            return name
        elif version == 'v2':
            # Convert dashes to double colons for v2
            return name.replace('-', '::')
        
        return name
    
    def extract_methods_from_mdx_codeblocks(self, content: str, is_legacy: bool = False) -> Tuple[List[str], List[str]]:
        """
        Extract method names from MDX CodeGroup blocks.
        
        Args:
            content: MDX file content
            is_legacy: Whether this is a legacy API file
            
        Returns:
            Tuple of (v1_methods, v2_methods)
        """
        v1_methods = []
        v2_methods = []
        
        # Find all CodeGroup blocks
        codegroups = re.findall(r'<CodeGroup[\s\S]*?>([\s\S]*?)</CodeGroup>', content, re.MULTILINE)
        
        for block in codegroups:
            # Extract code blocks from within CodeGroup
            code_blocks = re.findall(r'```[a-zA-Z]*\n([\s\S]*?)```', block)
            
            for code in code_blocks:
                # Look for method field in JSON
                method_match = re.search(r'"method"\s*:\s*"([a-zA-Z0-9_:.-]+)"', code)
                if method_match:
                    method = method_match.group(1)
                    
                    if is_legacy:
                        v1_methods.append(method)
                    elif '"mmrpc": "2.0"' in code:
                        v2_methods.append(method)
                    else:
                        v1_methods.append(method)
        
        return sorted(list(set(v1_methods))), sorted(list(set(v2_methods)))

    def find_mdx_files_missing_codegroup(self, root_dir: Union[str, Path]) -> ValidationResult:
        """
        Find MDX files in the komodo-defi-framework API directory that are missing CodeGroup components.
        This helps identify overview pages that should be tagged as 'overview'.
        Ignores files already tagged as 'overview'.
        
        Args:
            root_dir: Root directory to search from
            
        Returns:
            ValidationResult with analysis data
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            root_path = Path(root_dir)
            api_path = root_path / "src" / "pages" / "komodo-defi-framework" / "api"
            
            if not api_path.exists():
                result.add_error(f"API directory not found: {api_path}")
                return result
            
            # Find all MDX files
            mdx_files = list(api_path.rglob("*.mdx"))
            
            if not mdx_files:
                result.add_warning("No MDX files found in API directory")
                return result
            
            # Analysis categories
            categories = {
                'missing_codegroup_candidates': [],  # Files missing CodeGroup, not tagged as overview
                'method_files_with_codegroup': [],   # Properly tagged method files
                'overview_files_ignored': [],        # Files already tagged as overview (ignored)
                'inconsistent_files': [],            # Files with CodeGroup but tagged as overview
                'analysis_errors': []
            }
            
            for file_path in mdx_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for CodeGroup component
                    has_codegroup = 'CodeGroup' in content
                    
                    # Check for overview tag in heading
                    overview_tag_pattern = r"tag\s*:\s*['\"]overview['\"]"
                    has_overview_tag = bool(re.search(overview_tag_pattern, content))
                    
                    # Extract method name and title
                    method_name = self.extract_method_name_from_mdx_content(content)
                    title_pattern = r'export\s+const\s+title\s*=\s*["\']([^"\']+)["\']'
                    title_match = re.search(title_pattern, content)
                    title = title_match.group(1) if title_match else None
                    
                    # Check if it's in a method-specific directory
                    path_parts = file_path.parts
                    is_method_file = any(part in ['init', 'status', 'cancel', 'user_action'] for part in path_parts[-3:])
                    
                    file_info = {
                        'path': file_path,
                        'relative_path': file_path.relative_to(root_path),
                        'method_name': method_name,
                        'title': title,
                        'is_method_file': is_method_file,
                        'content_length': len(content)
                    }
                    
                    # Categorize files, ignoring those already tagged as overview
                    if has_overview_tag:
                        categories['overview_files_ignored'].append(file_info)
                    elif not has_codegroup and not has_overview_tag:
                        categories['missing_codegroup_candidates'].append(file_info)
                    elif has_codegroup and not has_overview_tag:
                        categories['method_files_with_codegroup'].append(file_info)
                    elif has_codegroup and has_overview_tag:
                        categories['inconsistent_files'].append(file_info)
                        
                except Exception as e:
                    categories['analysis_errors'].append({
                        'path': file_path,
                        'relative_path': file_path.relative_to(root_path),
                        'error': str(e)
                    })
                    
            # Set result data
            result.data = {
                'categories': categories,
                'summary': {
                    'total_files': len(mdx_files),
                    'missing_codegroup_candidates': len(categories['missing_codegroup_candidates']),
                    'method_files_with_codegroup': len(categories['method_files_with_codegroup']),
                    'overview_files_ignored': len(categories['overview_files_ignored']),
                    'inconsistent_files': len(categories['inconsistent_files']),
                    'analysis_errors': len(categories['analysis_errors'])
                }
            }
            
            # Add warnings for candidates
            if categories['missing_codegroup_candidates']:
                result.add_warning(
                    f"Found {len(categories['missing_codegroup_candidates'])} files missing CodeGroup "
                    "that may need 'overview' tag"
                )
            
            if categories['inconsistent_files']:
                result.add_warning(
                    f"Found {len(categories['inconsistent_files'])} files with CodeGroup "
                    "but tagged as 'overview' - may need review"
                )
                
        except Exception as e:
            result.add_error(f"Error analyzing MDX files: {e}")
        
        return result
    
    def print_codegroup_analysis_report(self, analysis_result: ValidationResult):
        """
        Print a detailed report of MDX files missing CodeGroup analysis.
        
        Args:
            analysis_result: Result from find_mdx_files_missing_codegroup
        """
        if not analysis_result.data:
            print("No analysis data available")
            return
        
        categories = analysis_result.data['categories']
        summary = analysis_result.data['summary']
        
        print("=" * 80)
        print("MDX FILES MISSING CODEGROUP ANALYSIS REPORT")
        print("=" * 80)
        
        # Files that likely need overview tag
        candidates = categories['missing_codegroup_candidates']
        print(f"\n🔍 CANDIDATES FOR OVERVIEW TAG ({len(candidates)} files)")
        print("These files are missing CodeGroup and not tagged as 'overview':")
        print("-" * 60)
        
        for file_info in candidates:
            print(f"📄 {file_info['relative_path']}")
            print(f"   Method: {file_info['method_name'] or 'None'}")
            print(f"   Title: {file_info['title'] or 'None'}")
            print(f"   Is method file: {file_info['is_method_file']}")
            print(f"   Content length: {file_info['content_length']} chars")
            print()
        
        # Overview files (ignored)
        overview_files = categories['overview_files_ignored']
        print(f"\n✅ OVERVIEW FILES (IGNORED) ({len(overview_files)} files)")
        print("These files are already properly tagged as 'overview':")
        print("-" * 60)
        
        for file_info in overview_files[:5]:  # Show first 5
            print(f"📄 {file_info['relative_path']}")
            print(f"   Method: {file_info['method_name'] or 'None'}")
        
        if len(overview_files) > 5:
            print(f"   ... and {len(overview_files) - 5} more")
        print()
        
        # Method files with CodeGroup
        method_files = categories['method_files_with_codegroup']
        print(f"\n✅ METHOD FILES WITH CODEGROUP ({len(method_files)} files)")
        print("These appear to be properly structured method pages.")
        
        # Inconsistent files
        inconsistent = categories['inconsistent_files']
        if inconsistent:
            print(f"\n⚠️  INCONSISTENT FILES ({len(inconsistent)} files)")
            print("These files have CodeGroup but are tagged as 'overview' - may need review:")
            print("-" * 60)
            
            for file_info in inconsistent:
                print(f"📄 {file_info['relative_path']}")
                print(f"   Method: {file_info['method_name'] or 'None'}")
                print()
        
        # Errors
        errors = categories['analysis_errors']
        if errors:
            print(f"\n❌ ANALYSIS ERRORS ({len(errors)} files)")
            print("Files that couldn't be analyzed:")
            print("-" * 60)
            
            for error_info in errors:
                print(f"📄 {error_info['relative_path']}")
                print(f"   Error: {error_info['error']}")
                print()
        
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total files analyzed: {summary['total_files']}")
        print(f"Candidates for overview tag: {summary['missing_codegroup_candidates']}")
        print(f"Method files with CodeGroup: {summary['method_files_with_codegroup']}")
        print(f"Overview files (ignored): {summary['overview_files_ignored']}")
        print(f"Inconsistent files: {summary['inconsistent_files']}")
        print(f"Analysis errors: {summary['analysis_errors']}")


class ValidationManager:
    """
    Centralized validation management for all validation operations.
    Enhanced with comprehensive validation utilities.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.NORMAL):
        self.level = level
        self.logger = get_logger("validation-manager")
        
        # Initialize validators
        self.json_validator = JSONValidator(level)
        self.method_name_validator = MethodNameValidator(level)
        self.file_format_validator = FileFormatValidator(level)
    
    def validate_json(self, data: Union[str, Path, Dict], schema: str = None) -> ValidationResult:
        """Validate JSON data or file."""
        if isinstance(data, Path) or (isinstance(data, str) and Path(data).exists()):
            return self.json_validator.validate_json_file(data, schema)
        elif isinstance(data, str):
            return self.json_validator.validate_json_string(data, schema)
        elif isinstance(data, dict):
            return self.json_validator.validate_against_schema(data, schema) if schema else ValidationResult(True, [], [])
        else:
            result = ValidationResult(False, [], [])
            result.add_error(f"Unsupported data type for JSON validation: {type(data)}")
            return result
    
    def validate_method_name(self, method_name: str) -> ValidationResult:
        """Validate method name."""
        return self.method_name_validator.validate_method_name(method_name)
    
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate file based on extension."""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        if extension == '.mdx':
            return self.file_format_validator.validate_mdx_file(path)
        elif extension in ['.yaml', '.yml']:
            return self.file_format_validator.validate_yaml_file(path)
        elif extension == '.json':
            return self.json_validator.validate_json_file(path)
        else:
            result = ValidationResult(False, [], [])
            result.add_error(f"Unsupported file extension: {extension}")
            return result
    
    def validate_batch(self, items: List[Any], validator_func: Callable) -> Dict[str, ValidationResult]:
        """Validate multiple items in batch."""
        results = {}
        
        for i, item in enumerate(items):
            try:
                result = validator_func(item)
                results[f"item_{i}"] = result
            except Exception as e:
                error_result = ValidationResult(False, [str(e)], [])
                results[f"item_{i}"] = error_result
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get summary statistics from validation results."""
        total = len(results)
        valid = sum(1 for r in results.values() if r.is_valid)
        invalid = total - valid
        
        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())
        
        return {
            'total_items': total,
            'valid_items': valid,
            'invalid_items': invalid,
            'success_rate': (valid / total * 100) if total > 0 else 0,
            'total_errors': total_errors,
            'total_warnings': total_warnings
        }

    def analyze_mdx_codegroup_status(self, root_dir: Union[str, Path] = None) -> ValidationResult:
        """
        Analyze MDX files for CodeGroup status to identify potential overview pages.
        Convenience method that uses the current working directory if no root provided.
        
        Args:
            root_dir: Root directory to search from (defaults to current working directory)
            
        Returns:
            ValidationResult with analysis data
        """
        if root_dir is None:
            # Get current working directory or script directory
            root_dir = Path.cwd()
            
            # If we're in utils/py, go up two levels
            if root_dir.name == 'py' and root_dir.parent.name == 'utils':
                root_dir = root_dir.parent.parent
        
        return self.file_format_validator.find_mdx_files_missing_codegroup(root_dir)
    
    def print_codegroup_analysis(self, root_dir: Union[str, Path] = None):
        """
        Analyze and print CodeGroup status report for MDX files.
        
        Args:
            root_dir: Root directory to search from (defaults to current working directory)
        """
        analysis_result = self.analyze_mdx_codegroup_status(root_dir)
        self.file_format_validator.print_codegroup_analysis_report(analysis_result)


# Convenience functions
def validate_json_safe(data: Any, schema: str = None, level: ValidationLevel = ValidationLevel.NORMAL) -> bool:
    """Safe JSON validation that returns only boolean result."""
    try:
        manager = ValidationManager(level)
        result = manager.validate_json(data, schema)
        return result.is_valid
    except Exception:
        return False


def validate_method_name_safe(method_name: str, level: ValidationLevel = ValidationLevel.NORMAL) -> bool:
    """Safe method name validation that returns only boolean result."""
    try:
        manager = ValidationManager(level)
        result = manager.validate_method_name(method_name)
        return result.is_valid
    except Exception:
        return False


def get_validation_manager(level: ValidationLevel = ValidationLevel.NORMAL) -> ValidationManager:
    """Get a validation manager instance."""
    return ValidationManager(level) 