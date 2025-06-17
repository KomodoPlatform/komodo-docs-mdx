#!/usr/bin/env python3
"""
Performance Comparison Example

Demonstrates the performance benefits of async processing
vs synchronous processing for I/O-bound operations.
"""

import asyncio
import json
import time
import tempfile
from pathlib import Path
from typing import List, Dict, Any

from lib.utils.logging_utils import get_logger, set_config_provider, ProgressTracker
from lib.constants.config import get_config
from lib.async_support import run_async


class PerformanceTester:
    """Performance testing utilities for sync vs async comparisons."""
    
    def __init__(self):
        # Set up logging
        set_config_provider(get_config)
        self.logger = get_logger("performance-tester")
        
    def create_test_data(self, num_files: int = 50) -> Path:
        """Create test data files for performance testing."""
        temp_dir = Path(tempfile.mkdtemp(prefix="kdf_perf_test_"))
        
        self.logger.info(f"Creating {num_files} test files in {temp_dir}")
        
        for i in range(num_files):
            file_path = temp_dir / f"test_method_{i:03d}.json"
            test_data = {
                "method": f"test_method_{i}",
                "version": "v2",
                "description": f"Test method {i} for performance testing",
                "parameters": {
                    "param1": {"type": "string", "required": True},
                    "param2": {"type": "number", "required": False, "default": 42}
                },
                "example": {
                    "request": {"method": f"test_method_{i}", "params": {"param1": "value"}},
                    "response": {"result": f"success_{i}"}
                }
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(test_data, f, indent=2)
        
        self.logger.success(f"Created {num_files} test files")
        return temp_dir
    
    def sync_file_processor(self, file_paths: List[Path]) -> Dict[str, Any]:
        """Synchronous file processing."""
        results = {"files_processed": 0, "total_size": 0, "methods": []}
        
        start_time = time.time()
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                results["files_processed"] += 1
                results["total_size"] += file_path.stat().st_size
                results["methods"].append(data["method"])
                
                # Simulate some processing time
                time.sleep(0.01)
                
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
        
        results["processing_time"] = time.time() - start_time
        return results
    
    async def async_file_processor(self, file_paths: List[Path]) -> Dict[str, Any]:
        """Asynchronous file processing."""
        results = {"files_processed": 0, "total_size": 0, "methods": []}
        
        start_time = time.time()
        
        async def process_file(file_path: Path) -> Dict[str, Any]:
            try:
                # Simulate async file reading
                await asyncio.sleep(0.01)  # Simulate I/O delay
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                return {
                    "method": data["method"],
                    "size": file_path.stat().st_size,
                    "success": True
                }
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {e}")
                return {"method": None, "size": 0, "success": False}
        
        # Process files concurrently
        tasks = [process_file(file_path) for file_path in file_paths]
        file_results = await asyncio.gather(*tasks)
        
        # Aggregate results
        for result in file_results:
            if result["success"]:
                results["files_processed"] += 1
                results["total_size"] += result["size"]
                results["methods"].append(result["method"])
        
        results["processing_time"] = time.time() - start_time
        return results
    
    def compare_performance(self, num_files: int = 50, iterations: int = 3):
        """Compare sync vs async performance."""
        self.logger.separator(f"Performance Comparison ({num_files} files)")
        
        # Create test data
        test_dir = self.create_test_data(num_files)
        file_paths = list(test_dir.glob("*.json"))
        
        sync_times = []
        async_times = []
        
        try:
            for i in range(iterations):
                self.logger.info(f"Running iteration {i + 1}/{iterations}")
                
                # Test synchronous processing
                self.logger.info("Testing synchronous processing...")
                sync_results = self.sync_file_processor(file_paths)
                sync_times.append(sync_results["processing_time"])
                
                # Test asynchronous processing  
                self.logger.info("Testing asynchronous processing...")
                async_results = run_async(self.async_file_processor(file_paths))
                async_times.append(async_results["processing_time"])
                
                self.logger.info(f"Sync: {sync_results['processing_time']:.3f}s, "
                               f"Async: {async_results['processing_time']:.3f}s")
            
            # Calculate averages
            avg_sync = sum(sync_times) / len(sync_times)
            avg_async = sum(async_times) / len(async_times)
            improvement = ((avg_sync - avg_async) / avg_sync) * 100
            
            # Report results
            self.logger.separator("Performance Results")
            self.logger.stats("Performance Comparison", {
                "Files Processed": num_files,
                "Iterations": iterations,
                "Avg Sync Time": f"{avg_sync:.3f}s",
                "Avg Async Time": f"{avg_async:.3f}s", 
                "Improvement": f"{improvement:.1f}%",
                "Speedup Factor": f"{avg_sync/avg_async:.2f}x"
            })
            
            if improvement > 0:
                self.logger.success(f"Async processing is {improvement:.1f}% faster!")
            else:
                self.logger.warning("Sync processing was faster (overhead might be too high)")
            
        finally:
            # Clean up test files
            import shutil
            shutil.rmtree(test_dir)
            self.logger.info("Test files cleaned up")


def demonstrate_progress_with_async():
    """Demonstrate progress tracking with async operations."""
    print("\n🔄 Demonstrating async progress tracking:")
    
    set_config_provider(get_config)
    logger = get_logger("async-progress")
    
    async def async_operation_with_progress():
        total_items = 30
        tracker = ProgressTracker(total_items, "Async Processing", logger)
        
        for i in range(total_items):
            # Simulate async work
            await asyncio.sleep(0.05)
            tracker.update(1, f"Processed item {i + 1}")
        
        tracker.finish("Async processing completed")
    
    run_async(async_operation_with_progress())


def main():
    """Run performance comparison examples."""
    print("🚀 Komodo DeFi Framework - Performance Comparison Examples")
    print("=" * 70)
    
    tester = PerformanceTester()
    
    try:
        # Run performance tests
        tester.compare_performance(num_files=30, iterations=2)
        
        # Demonstrate async progress tracking
        demonstrate_progress_with_async()
        
        print("\n✅ All performance examples completed!")
        print("\n💡 Key Performance Insights:")
        print("   1. Async processing shines with I/O-bound operations")
        print("   2. Real benefits show with larger datasets and network I/O")
        print("   3. Progress tracking works seamlessly with async")
        print("   4. Concurrent processing improves throughput")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 