#!/usr/bin/env python3
"""
Validation Utilities

Comprehensive validation system for JSON data, method names, and file formats.
Provides schema validation, syntax checking, and type validation.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass
from enum import Enum

from .exceptions import ValidationError, ParseError
from .logging_utils import get_logger


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"
    STANDARD = "standard"
    PERMISSIVE = "permissive"


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
    
    def __init__(self, level: ValidationLevel = ValidationLevel.STANDARD):
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
            valid_types = expected_type
        else:
            valid_types = [expected_type]
        
        # Check if data matches any of the valid types
        data_type = self._get_json_type(data)
        if data_type not in valid_types:
            result.add_error(
                f"Type mismatch at {path}: expected {valid_types}, got {data_type}"
            )
        
        return result
    
    def _get_json_type(self, data: Any) -> str:
        """Get JSON type name for Python object."""
        if data is None:
            return "null"
        elif isinstance(data, bool):
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
        else:
            return "unknown"
    
    def _validate_general_structure(self, data: Any) -> ValidationResult:
        """Perform general validation checks."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check for common issues
        if isinstance(data, dict):
            # Check for empty objects in strict mode
            if not data and self.level == ValidationLevel.STRICT:
                result.add_warning("Empty object")
            
            # Check for suspicious keys
            for key in data.keys():
                if not isinstance(key, str):
                    result.add_error(f"Non-string key: {key}")
                elif key.startswith('_') and self.level == ValidationLevel.STRICT:
                    result.add_warning(f"Private key '{key}' found")
        
        elif isinstance(data, list):
            # Check for empty arrays in strict mode
            if not data and self.level == ValidationLevel.STRICT:
                result.add_warning("Empty array")
        
        return result
    
    def add_custom_schema(self, name: str, schema: Dict):
        """Add a custom validation schema."""
        self._schemas[name] = schema
        self.logger.debug(f"Added custom schema: {name}")
    
    def get_available_schemas(self) -> List[str]:
        """Get list of available schema names."""
        return list(self._schemas.keys())


class MethodNameValidator:
    """
    Validator for API method names.
    
    Ensures method names follow naming conventions and standards.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.STANDARD):
        self.level = level
        self.logger = get_logger("method-validator")
        
        # Compile regex patterns
        self._patterns = {
            'valid_chars': re.compile(r'^[a-zA-Z0-9_:.-]+$'),
            'valid_structure': re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*(?:::?[a-zA-Z0-9_]+)*$'),
            'namespace_pattern': re.compile(r'^([a-zA-Z][a-zA-Z0-9_]*)(::?[a-zA-Z0-9_]+)+$'),
            'reserved_words': re.compile(r'\b(null|undefined|true|false|NaN)\b', re.IGNORECASE)
        }
    
    def validate_method_name(self, method_name: str) -> ValidationResult:
        """Validate a method name."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not method_name:
            result.add_error("Method name cannot be empty")
            return result
        
        method_name = method_name.strip()
        
        # Basic character validation
        if not self._patterns['valid_chars'].match(method_name):
            result.add_error("Method name contains invalid characters")
        
        # Structure validation
        if self.level in [ValidationLevel.STRICT, ValidationLevel.STANDARD]:
            if not self._patterns['valid_structure'].match(method_name):
                result.add_error("Method name doesn't follow naming conventions")
        
        # Length validation
        if len(method_name) > 100:
            result.add_error("Method name too long (max 100 characters)")
        elif len(method_name) < 2:
            result.add_error("Method name too short (min 2 characters)")
        
        # Reserved words check
        if self._patterns['reserved_words'].search(method_name):
            result.add_warning("Method name contains reserved words")
        
        # Namespace validation for strict mode
        if self.level == ValidationLevel.STRICT:
            if not self._patterns['namespace_pattern'].match(method_name):
                result.add_warning("Method name should use namespace pattern (e.g., 'namespace::method')")
        
        return result


class FileFormatValidator:
    """
    Validator for different file formats.
    
    Validates MDX, YAML, and other file formats used in the project.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.STANDARD):
        self.level = level
        self.logger = get_logger("file-validator")
    
    def validate_mdx_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate MDX file structure and content."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for required MDX elements
            if not content.startswith('export const title ='):
                result.add_error("MDX file must start with 'export const title ='")
            
            if 'export const description =' not in content:
                result.add_error("MDX file must contain 'export const description ='")
            
            # Check for method heading pattern
            method_heading_pattern = re.compile(r'##\s+[a-zA-Z0-9_:.-]+\s*\{\{')
            if not method_heading_pattern.search(content):
                result.add_warning("No method heading found (## method_name {{...}})")
            
            # Check for code blocks
            if '```' not in content:
                result.add_warning("No code blocks found")
            
        except Exception as e:
            result.add_error(f"Error reading MDX file: {e}")
        
        return result
    
    def validate_yaml_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate YAML file structure."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        try:
            import yaml
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse YAML
            try:
                data = yaml.safe_load(content)
                result.data = data
            except yaml.YAMLError as e:
                result.add_error(f"Invalid YAML syntax: {e}")
                return result
            
            # Validate structure
            if isinstance(data, dict):
                # Check for common OpenAPI fields
                if 'operationId' not in data and self.level == ValidationLevel.STRICT:
                    result.add_warning("Missing operationId in YAML")
                
                if 'summary' not in data:
                    result.add_warning("Missing summary in YAML")
            
        except ImportError:
            result.add_error("PyYAML not installed - cannot validate YAML files")
        except Exception as e:
            result.add_error(f"Error reading YAML file: {e}")
        
        return result


class ValidationManager:
    """
    Central validation manager that coordinates all validation operations.
    
    Provides a unified interface for validating different types of data and files.
    """
    
    def __init__(self, level: ValidationLevel = ValidationLevel.STANDARD):
        self.level = level
        self.logger = get_logger("validation-manager")
        
        # Initialize validators
        self.json_validator = JSONValidator(level)
        self.method_validator = MethodNameValidator(level)
        self.file_validator = FileFormatValidator(level)
    
    def validate_json(self, data: Union[str, Path, Dict], schema: str = None) -> ValidationResult:
        """Validate JSON data (string, file, or dict)."""
        if isinstance(data, (str, Path)) and Path(data).exists():
            return self.json_validator.validate_json_file(data, schema)
        elif isinstance(data, str):
            return self.json_validator.validate_json_string(data, schema)
        elif isinstance(data, dict):
            return self.json_validator.validate_against_schema(data, schema) if schema else ValidationResult(True, [], [])
        else:
            result = ValidationResult(False, [], [])
            result.add_error("Invalid data type for JSON validation")
            return result
    
    def validate_method_name(self, method_name: str) -> ValidationResult:
        """Validate method name."""
        return self.method_validator.validate_method_name(method_name)
    
    def validate_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate file based on its extension."""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.json':
            return self.json_validator.validate_json_file(file_path)
        elif file_path.suffix.lower() == '.mdx':
            return self.file_validator.validate_mdx_file(file_path)
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            return self.file_validator.validate_yaml_file(file_path)
        else:
            result = ValidationResult(True, [], [])
            result.add_warning(f"No specific validation for {file_path.suffix} files")
            return result
    
    def validate_batch(self, items: List[Any], validator_func: Callable) -> Dict[str, ValidationResult]:
        """Validate multiple items in batch."""
        results = {}
        
        for i, item in enumerate(items):
            try:
                result = validator_func(item)
                results[f"item_{i}"] = result
            except Exception as e:
                error_result = ValidationResult(False, [], [])
                error_result.add_error(f"Validation failed: {e}")
                results[f"item_{i}"] = error_result
        
        return results
    
    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get summary of validation results."""
        total = len(results)
        valid = sum(1 for r in results.values() if r.is_valid)
        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())
        
        return {
            'total_items': total,
            'valid_items': valid,
            'invalid_items': total - valid,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'success_rate': (valid / total * 100) if total > 0 else 0
        }


# Convenience functions
def validate_json_safe(data: Any, schema: str = None, level: ValidationLevel = ValidationLevel.STANDARD) -> bool:
    """Quick JSON validation that returns boolean."""
    try:
        manager = ValidationManager(level)
        result = manager.validate_json(data, schema)
        return result.is_valid
    except Exception:
        return False


def validate_method_name_safe(method_name: str, level: ValidationLevel = ValidationLevel.STANDARD) -> bool:
    """Quick method name validation that returns boolean."""
    try:
        manager = ValidationManager(level)
        result = manager.validate_method_name(method_name)
        return result.is_valid
    except Exception:
        return False


def get_validation_manager(level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationManager:
    """Get a validation manager instance."""
    return ValidationManager(level) 