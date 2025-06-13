#!/usr/bin/env python3
"""
Usage Examples

Demonstrates the improved Komodo Documentation Library functionality
including configuration, logging, caching, and async operations.
"""

import asyncio
from pathlib import Path

# Import the improved library components
from . import (
    get_config, setup_logging, get_logger, MethodMapper,
    PostmanCollectionGenerator, AsyncMethodProcessor, get_cache,
    cached, async_cached, run_async
)


def basic_usage_example():
    """Basic usage example with configuration and logging."""
    
    # Setup logging with custom configuration
    logger = setup_logging(verbose=True, emoji=True)
    logger.info("Starting Komodo Documentation Library example")
    
    # Get configuration
    config = get_config()
    logger.stats("Configuration", {
        "MDX directories": len(config.get_mdx_directories()),
        "YAML directories": len(config.get_yaml_directories()),
        "JSON directories": len(config.get_json_directories())
    })
    
    # Validate directories
    validation_results = config.validate_directories()
    valid_dirs = sum(1 for exists in validation_results.values() if exists)
    logger.info(f"Directory validation: {valid_dirs}/{len(validation_results)} directories exist")
    
    # Create missing directories if needed
    created_dirs = config.create_missing_directories()
    if created_dirs:
        logger.success(f"Created {len(created_dirs)} missing directories")
    
    return config


@cached(namespace="method_mapping", ttl_seconds=3600)
def cached_method_mapping_example():
    """Example of cached method mapping operations."""
    logger = get_logger("examples")
    logger.info("Running cached method mapping example")
    
    # This will be cached for 1 hour
    mapper = MethodMapper()
    unified_mapping = mapper.create_unified_mapping()
    
    # Statistics
    v1_methods = len(unified_mapping.get("v1", {}))
    v2_methods = len(unified_mapping.get("v2", {}))
    
    logger.stats("Method Mapping Results", {
        "V1 methods": v1_methods,
        "V2 methods": v2_methods,
        "Total methods": v1_methods + v2_methods
    })
    
    return unified_mapping


async def async_file_processing_example():
    """Example of async file processing."""
    logger = get_logger("async-example")
    logger.info("Running async file processing example")
    
    # Create async processor
    processor = AsyncMethodProcessor()
    
    # Get configuration
    config = get_config()
    
    # Scan files asynchronously
    logger.progress("Starting async MDX file scan")
    mdx_results = await processor.scan_mdx_files_async(config.get_mdx_directories())
    
    logger.progress("Starting async YAML file scan")
    yaml_results = await processor.scan_yaml_files_async(config.get_yaml_directories())
    
    logger.progress("Starting async JSON example scan")
    json_results = await processor.scan_json_examples_async(config.get_json_directories())
    
    # Report results
    for version in ["v1", "v2"]:
        logger.stats(f"{version.upper()} Scan Results", {
            "MDX files": len(mdx_results.get(version, {})),
            "YAML files": len(yaml_results.get(version, {})),
            "JSON examples": len(json_results.get(version, {}))
        })
    
    return {
        "mdx": mdx_results,
        "yaml": yaml_results,
        "json": json_results
    }


@async_cached(namespace="postman_generation", ttl_seconds=1800)
async def async_postman_generation_example():
    """Example of async Postman collection generation with caching."""
    logger = get_logger("postman-example")
    logger.info("Running async Postman generation example")
    
    # Create generator
    generator = PostmanCollectionGenerator()
    
    # Generate collections for both versions
    versions = ["v1", "v2"]
    results = {}
    
    for version in versions:
        logger.progress(f"Generating {version} collection")
        
        # This would be cached for 30 minutes
        collection = generator.generate_postman_collection(version)
        environment = generator.generate_environment_file(version)
        
        results[version] = {
            "collection": collection,
            "environment": environment
        }
        
        # Log collection stats
        if "item" in collection:
            request_count = sum(len(folder.get("item", [])) for folder in collection["item"])
            logger.success(f"{version} collection generated: {request_count} requests")
    
    return results


def caching_example():
    """Example of caching system usage."""
    logger = get_logger("cache-example")
    logger.info("Running caching system example")
    
    cache = get_cache()
    
    # Cache some data
    cache.set("example", "test_key", {"data": "test_value"}, ttl_seconds=300)
    cache.set("stats", "request_count", 42)
    
    # Retrieve cached data
    cached_data = cache.get("example", "test_key")
    cached_stats = cache.get("stats", "request_count")
    
    logger.info(f"Retrieved cached data: {cached_data}")
    logger.info(f"Retrieved cached stats: {cached_stats}")
    
    # Get cache statistics
    cache_stats = cache.get_stats()
    logger.stats("Cache Statistics", cache_stats)
    
    # Cleanup expired entries
    cleaned = cache.cleanup_expired()
    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} expired cache entries")
    
    return cache_stats


def performance_comparison_example():
    """Example comparing sync vs async performance."""
    import time
    
    logger = get_logger("performance")
    logger.separator("Performance Comparison")
    
    config = get_config()
    
    # Sync version
    start_time = time.time()
    mapper = MethodMapper()
    sync_results = mapper.scan_mdx_files()
    sync_time = time.time() - start_time
    
    logger.info(f"Sync MDX scan: {sync_time:.2f} seconds")
    
    # Async version
    async def async_scan():
        processor = AsyncMethodProcessor()
        return await processor.scan_mdx_files_async(config.get_mdx_directories())
    
    start_time = time.time()
    async_results = run_async(async_scan())
    async_time = time.time() - start_time
    
    logger.info(f"Async MDX scan: {async_time:.2f} seconds")
    
    # Performance comparison
    if sync_time > 0:
        speedup = sync_time / async_time if async_time > 0 else float('inf')
        logger.success(f"Async version is {speedup:.1f}x faster")
    
    return {
        "sync_time": sync_time,
        "async_time": async_time,
        "sync_results": len(sync_results.get("v2", {})),
        "async_results": len(async_results.get("v2", {}))
    }


def error_handling_example():
    """Example of improved error handling."""
    from .exceptions import FileOperationError, ConfigurationError
    
    logger = get_logger("error-example")
    logger.info("Running error handling example")
    
    try:
        # This will raise a specific exception
        config = get_config()
        config.directories.mdx_v2 = "/nonexistent/path"
        config.create_missing_directories()
        
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.message}")
        logger.debug(f"Error details: {e.details}")
    
    try:
        # Simulate file operation error
        from .exceptions import raise_file_not_found
        raise_file_not_found("/path/to/missing/file.json", "read")
        
    except FileOperationError as e:
        logger.error(f"File operation failed: {e.message}")
        logger.debug(f"File path: {e.file_path}, Operation: {e.operation}")
    
    logger.info("Error handling example completed")


def full_workflow_example():
    """Complete workflow example using all improved features."""
    logger = get_logger("workflow")
    logger.separator("Full Workflow Example")
    
    try:
        # 1. Setup and configuration
        config = basic_usage_example()
        
        # 2. Cached method mapping
        mapping_results = cached_method_mapping_example()
        
        # 3. Async file processing
        async_results = run_async(async_file_processing_example())
        
        # 4. Caching demonstration
        cache_stats = caching_example()
        
        # 5. Performance comparison
        perf_results = performance_comparison_example()
        
        # 6. Error handling
        error_handling_example()
        
        # Final summary
        logger.separator("Workflow Summary")
        logger.success("All examples completed successfully!")
        
        total_methods = sum(len(mapping_results.get(v, {})) for v in ["v1", "v2"])
        logger.stats("Final Results", {
            "Total methods mapped": total_methods,
            "Cache hit rate": f"{cache_stats.get('hit_rate_percent', 0)}%",
            "Performance improvement": f"{perf_results.get('sync_time', 0) / max(perf_results.get('async_time', 1), 0.001):.1f}x"
        })
        
        return {
            "config": config.to_dict(),
            "mapping": mapping_results,
            "async_results": async_results,
            "cache_stats": cache_stats,
            "performance": perf_results
        }
        
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        raise


if __name__ == "__main__":
    """Run examples when script is executed directly."""
    
    # Run the full workflow
    try:
        results = full_workflow_example()
        print("\n✅ All examples completed successfully!")
        print(f"📊 Total methods processed: {sum(len(results['mapping'].get(v, {})) for v in ['v1', 'v2'])}")
        
    except Exception as e:
        print(f"\n❌ Examples failed: {e}")
        import traceback
        traceback.print_exc() 