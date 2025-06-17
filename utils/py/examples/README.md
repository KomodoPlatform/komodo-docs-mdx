# Komodo DeFi Framework Python Tools - Usage Examples

This directory contains practical examples demonstrating how to use the various components of the Komodo DeFi Framework Python utilities.

## 📁 Examples Overview

### 1. **Basic Usage Examples**
- `basic_logging.py` - Demonstrate the improved logging system
- `basic_config.py` - Show configuration management
- `basic_file_ops.py` - File operations and utilities

### 2. **Advanced Integration Examples**
- `method_mapping_example.py` - Complete method mapping workflow
- `postman_generation_example.py` - Generate Postman collections
- `openapi_conversion_example.py` - Convert MDX to OpenAPI

### 3. **Async Processing Examples** 
- `async_file_processing.py` - Async file operations
- `async_method_mapping.py` - Async method mapping
- `performance_comparison.py` - Sync vs Async performance

### 4. **Testing Examples**
- `testing_setup_example.py` - How to set up tests
- `mock_examples.py` - Mocking and testing patterns

## 🚀 Quick Start

### Basic Setup
```python
# Set up logging and configuration
from lib.utils.logging_utils import get_logger, set_config_provider
from lib.constants.config import get_config

# Configure dependency injection
set_config_provider(get_config)
logger = get_logger()

logger.info("Ready to use Komodo DeFi tools!")
```

### Method Mapping
```python
from lib.mapping import MethodMapper

mapper = MethodMapper()
unified_mapping = mapper.create_unified_mapping()
mapper.save_unified_mapping()
```

### Postman Generation
```python
from lib.postman import PostmanCollectionGenerator

generator = PostmanCollectionGenerator()
results = generator.generate_collections(['v2'])
```

## 📋 Running Examples

Each example can be run independently:

```bash
# Run basic examples
python examples/basic_logging.py
python examples/basic_config.py

# Run advanced examples  
python examples/method_mapping_example.py
python examples/async_file_processing.py

# Run performance comparisons
python examples/performance_comparison.py
```

## 🔧 Development Examples

### Setting Up Development Environment
```bash
# Use the Makefile for quick setup
make setup-dev

# Or manually:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e ".[dev,performance]"
```

### Running Tests with Examples
```bash
# Run specific example tests
pytest examples/test_examples.py

# Run with coverage
pytest --cov=examples examples/
```

## 📚 Integration Patterns

### Configuration Management
```python
from lib.constants.config import get_config

config = get_config()
print(f"MDX v2 directory: {config.directories.mdx_v2}")
print(f"Processing batch size: {config.processing.batch_size}")
```

### Error Handling
```python
from lib.constants.exceptions import FileOperationError, ValidationError

try:
    # Your operation here
    pass
except FileOperationError as e:
    logger.error(f"File operation failed: {e}")
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
```

### Async Processing
```python
from lib.async_support import AsyncMethodProcessor, run_async

async def process_files():
    processor = AsyncMethodProcessor()
    results = await processor.scan_mdx_files_async(['./src/pages/'])
    return results

# Run async function
results = run_async(process_files())
```

## 🎯 Best Practices

1. **Always use dependency injection for logging**:
   ```python
   set_config_provider(get_config)
   ```

2. **Use async methods for I/O operations**:
   ```python
   results = run_async(async_function())
   ```

3. **Handle exceptions appropriately**:
   ```python
   from lib.constants.exceptions import KomodoLibraryError
   
   try:
       # Operation
       pass
   except KomodoLibraryError as e:
       logger.error(f"Operation failed: {e}")
   ```

4. **Use configuration for paths and settings**:
   ```python
   config = get_config()
   mdx_dir = config.directories.mdx_v2
   ```

## 🔍 Troubleshooting

### Common Issues

1. **Circular Import Errors**: Make sure to use dependency injection
2. **Configuration Not Found**: Check that config files exist
3. **Async Errors**: Use `run_async()` for async functions in sync context

### Debug Mode
```python
# Enable debug logging
from lib.utils.logging_utils import setup_logging
setup_logging(verbose=True, log_file="debug.log")
```

## 📈 Performance Tips

1. **Use async methods for file operations**
2. **Enable caching for repeated operations**
3. **Use batch processing for large datasets**
4. **Monitor memory usage with large files**

See individual example files for detailed implementations and explanations. 