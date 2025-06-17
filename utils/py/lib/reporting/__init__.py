#!/usr/bin/env python3
"""
Reporting Module

Centralized reporting functionality for the KDF documentation utilities.
Provides unified access to all reporter classes and common utilities.

RECENT UPDATES:
- ExampleReporter: Added generate_deduplication_report() method moved from example_manager
- MappingReporter: Added generate_comparison_report() method moved from repository_scanner
- All reporting functionality now consolidated in appropriate reporter classes
"""

from .base_reporter import BaseReporter
from .mapping_reporter import MappingReporter
from .postman_reporter import PostmanReportGenerator
from .example_reporter import ExampleReporter

__all__ = [
    'BaseReporter',
    'MappingReporter', 
    'PostmanReportGenerator',
    'ExampleReporter'
]

# Version info
__version__ = '1.1.0'  # Updated to reflect reporting consolidation 