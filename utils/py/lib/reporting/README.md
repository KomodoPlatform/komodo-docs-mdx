# Reporting Module

This module provides centralized reporting functionality for the KDF documentation utilities. All reporter classes have been consolidated here to improve maintainability and promote code reuse.

## Structure

```
reporting/
├── __init__.py              # Module exports and version info
├── base_reporter.py         # Abstract base class with common utilities
├── mapping_reporter.py      # Method mapping coverage reports
├── postman_reporter.py      # Postman collection generation reports
├── example_reporter.py      # API example management reports
└── README.md               # This file
```

## Usage

### Basic Import

```python
from lib.reporting import MappingReporter, PostmanReportGenerator, ExampleReporter
```

### Individual Imports

```python
from lib.reporting.mapping_reporter import MappingReporter
from lib.reporting.postman_reporter import PostmanReportGenerator
from lib.reporting.example_reporter import ExampleReporter
```

## Available Reporters

### MappingReporter

Generates detailed reports and statistics for mapping operations:

- **Method coverage analysis** - Complete breakdowns of MDX, YAML, and JSON coverage
- **Debug reports** - Method matching diagnostics and suggestions
- **Coverage summaries** - Brief overview of documentation completeness

**Key Methods:**
- `generate_detailed_mapping_stats()` - Comprehensive mapping statistics
- `generate_debug_report()` - Debug method matching issues
- `generate_coverage_summary()` - Brief coverage overview

### PostmanReportGenerator

Generates reports for Postman collection operations:

- **Collection generation summaries** - Results of collection/environment creation
- **JSON scanning reports** - Analysis of available JSON examples
- **File statistics** - Size and count information for generated files

**Key Methods:**
- `generate_summary_report()` - Collection generation results
- `generate_scanning_report()` - JSON example analysis
- `generate_file_statistics_report()` - File size/count statistics

### ExampleReporter

Handles API example management reporting:

- **Extraction summaries** - Results of example extraction processes
- **File operation reports** - Consolidation and deduplication results  
- **Method coverage analysis** - Coverage across different API versions

**Key Methods:**
- `generate_summary_report()` - Comprehensive extraction results
- `generate_processing_report()` - Focused processing statistics
- `generate_file_operation_report()` - File operation results
- `generate_method_coverage_report()` - Method processing coverage

## Base Reporter

All reporter classes inherit from `BaseReporter`, which provides:

### Common Utilities

- **Formatting methods** - Headers, percentages, timestamps, file sizes
- **Statistics calculation** - Basic stats for collections of items
- **Error reporting** - Standardized error summaries
- **Coverage formatting** - Consistent coverage statistics display
- **Table generation** - Simple comparison tables
- **Duration formatting** - Human-readable time formatting

### Inheritance Pattern

```python
from lib.reporting.base_reporter import BaseReporter

class MyReporter(BaseReporter):
    def generate_summary_report(self, data):
        # Must implement this abstract method
        header = self.format_header("My Report")
        percentage = self.format_percentage(50, 100)
        return f"{header}\nSuccess rate: {percentage}"
```

## Migration from Old Locations

The reporting classes have been moved from their original locations:

- `utils/py/lib/mapping/mapping_reports.py` → `utils/py/lib/reporting/mapping_reporter.py`
- `utils/py/lib/postman/postman_reports.py` → `utils/py/lib/reporting/postman_reporter.py`  
- `utils/py/lib/utils/reporters.py` → `utils/py/lib/reporting/example_reporter.py`

### Backward Compatibility

The old module locations still work but will show deprecation warnings. Update your imports:

```python
# Old (deprecated)
from lib.mapping.mapping_reports import MappingReporter
from lib.postman.postman_reports import PostmanReportGenerator
from lib.utils.reporters import ExampleReporter

# New (recommended)
from lib.reporting import MappingReporter, PostmanReportGenerator, ExampleReporter
```

## Benefits of Centralization

1. **Single Responsibility** - All reporting logic in one place
2. **Code Reuse** - Common utilities shared across all reporters
3. **Consistency** - Standardized formatting and patterns
4. **Maintainability** - Easier to find and update reporting code
5. **Extensibility** - Simple to add new reporter types

## Best Practices

1. **Inherit from BaseReporter** - Use the common utilities and patterns
2. **Implement generate_summary_report()** - Required abstract method
3. **Use format_* methods** - Leverage consistent formatting utilities
4. **Follow naming conventions** - End class names with "Reporter" or "ReportGenerator"
5. **Document report types** - Clear docstrings for each report method

## Future Enhancements

Potential additions to the reporting module:

- **Report serialization** - Export reports to JSON, CSV, etc.
- **Template system** - Configurable report templates
- **Aggregation utilities** - Combine reports from multiple sources
- **Visualization helpers** - Generate charts and graphs
- **Report scheduling** - Automated report generation 