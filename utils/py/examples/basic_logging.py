#!/usr/bin/env python3
"""
Basic Logging Example

Demonstrates the improved logging system with dependency injection
and various logging features.
"""

import time
from lib.utils.logging_utils import get_logger, set_config_provider, ProgressTracker
from lib.constants.config import get_config


def demonstrate_basic_logging():
    """Demonstrate basic logging functionality."""
    print("🔧 Setting up logging with dependency injection...")
    
    # Step 1: Set up dependency injection (IMPORTANT!)
    set_config_provider(get_config)
    
    # Step 2: Get logger instance
    logger = get_logger("basic-example")
    
    print("\n📋 Demonstrating different log levels:")
    
    # Different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.success("This is a success message")
    
    # Custom operation logging
    logger.operation("save", "Configuration saved to file")
    logger.operation("scan", "Scanning directory for files")
    logger.operation("process", "Processing method mappings")
    
    # File operation logging
    logger.file_operation("create", "/tmp/test.json", success=True)
    logger.file_operation("delete", "/tmp/old.json", success=False)
    
    # Method operation logging
    logger.method_operation("enable_coin", "started", "Processing BTC activation")
    logger.method_operation("enable_coin", "completed", "BTC successfully activated")


def demonstrate_progress_tracking():
    """Demonstrate progress tracking functionality."""
    print("\n🔄 Demonstrating progress tracking:")
    
    logger = get_logger("progress-example")
    
    # Create progress tracker
    tracker = ProgressTracker(50, "Processing files", logger)
    
    # Simulate processing with progress updates
    for i in range(50):
        time.sleep(0.02)  # Simulate work
        
        if i % 10 == 0:
            tracker.update(10, f"Processed batch {i//10 + 1}")
        else:
            tracker.update(1)
    
    tracker.finish("All files processed successfully")


def demonstrate_statistics_logging():
    """Demonstrate statistics and structured logging."""
    print("\n📊 Demonstrating statistics logging:")
    
    logger = get_logger("stats-example")
    
    # Log statistics
    stats = {
        "Total Methods": 156,
        "V1 Methods": 45,
        "V2 Methods": 111,
        "Processing Time": "2.3s",
        "Cache Hit Rate": "87%"
    }
    
    logger.stats("Method Mapping Results", stats)
    
    # Visual separators
    logger.separator("Configuration Summary")
    logger.info("MDX Directory: ./src/pages/komodo-defi-framework/api/v20")
    logger.info("Output Directory: ./postman/collections")
    logger.info("Batch Size: 50")
    logger.separator()


def demonstrate_error_handling():
    """Demonstrate error handling with logging."""
    print("\n⚠️  Demonstrating error handling:")
    
    logger = get_logger("error-example")
    
    try:
        # Simulate an operation that might fail
        raise FileNotFoundError("Configuration file not found")
        
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        logger.info("Falling back to default configuration")
        logger.success("Default configuration loaded successfully")


def demonstrate_multiple_loggers():
    """Demonstrate using multiple logger instances."""
    print("\n🔀 Demonstrating multiple logger instances:")
    
    # Different loggers for different components
    mapping_logger = get_logger("method-mapper")
    postman_logger = get_logger("postman-generator")
    openapi_logger = get_logger("openapi-converter")
    
    mapping_logger.info("Starting method mapping process")
    postman_logger.info("Generating Postman collections")
    openapi_logger.info("Converting MDX to OpenAPI specs")
    
    # Demonstrate that same-named loggers are singletons
    another_mapping_logger = get_logger("method-mapper")
    print(f"Same logger instance? {mapping_logger is another_mapping_logger}")


def demonstrate_configuration_effects():
    """Demonstrate how configuration affects logging behavior."""
    print("\n⚙️  Demonstrating configuration effects:")
    
    logger = get_logger("config-example")
    config = get_config()
    
    logger.info(f"Emoji output enabled: {config.logging.emoji_output}")
    logger.info(f"Verbose mode: {config.logging.verbose}")
    logger.info(f"Progress indicators: {config.logging.progress_indicators}")
    
    # Progress message (only shows if progress_indicators is True)
    logger.progress("This is a progress message")


def main():
    """Run all logging examples."""
    print("🎯 Komodo DeFi Framework - Basic Logging Examples")
    print("=" * 60)
    
    try:
        demonstrate_basic_logging()
        demonstrate_progress_tracking()
        demonstrate_statistics_logging()
        demonstrate_error_handling()
        demonstrate_multiple_loggers()
        demonstrate_configuration_effects()
        
        print("\n✅ All logging examples completed successfully!")
        print("\n💡 Key Takeaways:")
        print("   1. Always call set_config_provider(get_config) first")
        print("   2. Use different logger instances for different components")
        print("   3. Progress tracking is great for long operations")
        print("   4. Statistics logging provides nice formatted output")
        print("   5. Error handling integrates well with logging")
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 