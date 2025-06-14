"""
Mapping Package - Method mapping and normalization

This package handles method mapping and normalization operations:
- Core mapping functionality
- Method name normalization
- Path mapping utilities
- Validation framework
- Mapping reports
"""

from .mapping import MethodMapper, MethodMapping
from .method_normalizer import MethodNameNormalizer
from .path_utils import PathMapper, PathMapping, VersionConfig, VersionStatus, PathType
from .validation import ValidationManager, ValidationResult, ValidationLevel
from .mapping_reports import MappingReporter

__all__ = [
    # Core mapping
    'MethodMapper', 'MethodMapping',
    
    # Method normalization
    'MethodNameNormalizer',
    
    # Path utilities
    'PathMapper', 'PathMapping', 'VersionConfig', 'VersionStatus', 'PathType',
    
    # Validation
    'ValidationManager', 'ValidationResult', 'ValidationLevel',
    
    # Reports
    'MappingReporter'
] 