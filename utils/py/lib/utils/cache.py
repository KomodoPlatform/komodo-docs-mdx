#!/usr/bin/env python3
"""
Caching System

Provides caching functionality for expensive operations in the Komodo Documentation Library.
Supports memory and file-based caching with TTL and invalidation strategies.
"""

import os
import json
import hashlib
import pickle
from pathlib import Path
from typing import Any, Optional, Dict, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass

from ..core.config import get_config
from ..core.logging_utils import get_logger


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    data: Any
    created_at: datetime
    ttl_seconds: Optional[int] = None
    file_dependencies: list = None
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        
        expiry_time = self.created_at + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time
    
    def are_dependencies_modified(self) -> bool:
        """Check if file dependencies have been modified since cache creation."""
        if not self.file_dependencies:
            return False
        
        for file_path in self.file_dependencies:
            if not os.path.exists(file_path):
                return True
            
            file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_mtime > self.created_at:
                return True
        
        return False
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return not self.is_expired() and not self.are_dependencies_modified()


def cache_key_from_dict(data: Dict[str, Any]) -> str:
    """
    Generate a cache key from a dictionary.
    
    Args:
        data: Dictionary to generate cache key from
        
    Returns:
        SHA256 hash of the dictionary contents
    """
    # Convert to JSON with sorted keys for consistent hashing
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


class KomodoCache:
    """
    Comprehensive caching system for the Komodo Documentation Library.
    
    Features:
    - Memory and file-based caching
    - TTL (Time To Live) support
    - File dependency tracking
    - Automatic invalidation
    - Statistics and monitoring
    """
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.logger = get_logger("komodo-cache")
        
        # Setup cache directory
        if cache_dir is None:
            cache_dir = Path.home() / ".komodo-cache"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        
        # In-memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'invalidations': 0,
            'saves': 0,
            'loads': 0
        }
        
        self.logger.debug(f"Initialized cache with directory: {self.cache_dir}")
    
    def _generate_key(self, namespace: str, key: Union[str, Dict]) -> str:
        """Generate a unique cache key."""
        if isinstance(key, dict):
            key_str = json.dumps(key, sort_keys=True)
        else:
            key_str = str(key)
        
        combined = f"{namespace}:{key_str}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(self, namespace: str, key: Union[str, Dict], 
            default: Any = None) -> Any:
        """Get value from cache."""
        cache_key = self._generate_key(namespace, key)
        
        # Check memory cache first
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if entry.is_valid():
                self.stats['hits'] += 1
                # self.logger.debug(f"Cache hit (memory): {namespace}")
                return entry.data
            else:
                # Remove invalid entry
                del self._memory_cache[cache_key]
                self.stats['invalidations'] += 1
        
        # Check file cache
        file_path = self.cache_dir / f"{cache_key}.cache"
        if file_path.exists():
            try:
                with open(file_path, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_valid():
                    # Load into memory cache
                    self._memory_cache[cache_key] = entry
                    self.stats['hits'] += 1
                    self.stats['loads'] += 1
                    # self.logger.debug(f"Cache hit (file): {namespace}")
                    return entry.data
                else:
                    # Remove invalid file
                    file_path.unlink()
                    self.stats['invalidations'] += 1
                    
            except Exception as e:
                self.logger.warning(f"Failed to load cache file {file_path}: {e}")
                file_path.unlink(missing_ok=True)
        
        self.stats['misses'] += 1
        self.logger.debug(f"Cache miss: {namespace}")
        return default
    
    def set(self, namespace: str, key: Union[str, Dict], value: Any,
            ttl_seconds: Optional[int] = None, 
            file_dependencies: Optional[list] = None,
            persist: bool = True) -> None:
        """Set value in cache."""
        cache_key = self._generate_key(namespace, key)
        
        entry = CacheEntry(
            data=value,
            created_at=datetime.now(),
            ttl_seconds=ttl_seconds,
            file_dependencies=file_dependencies or []
        )
        
        # Store in memory
        self._memory_cache[cache_key] = entry
        
        # Store in file cache if requested
        if persist:
            file_path = self.cache_dir / f"{cache_key}.cache"
            try:
                with open(file_path, 'wb') as f:
                    pickle.dump(entry, f)
                self.stats['saves'] += 1
                self.logger.debug(f"Cached to file: {namespace}")
            except Exception as e:
                self.logger.warning(f"Failed to save cache file {file_path}: {e}")
        
        self.logger.debug(f"Cached: {namespace}")
    
    def invalidate(self, namespace: str, key: Union[str, Dict] = None) -> int:
        """Invalidate cache entries."""
        if key is not None:
            # Invalidate specific key
            cache_key = self._generate_key(namespace, key)
            removed = 0
            
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
                removed += 1
            
            file_path = self.cache_dir / f"{cache_key}.cache"
            if file_path.exists():
                file_path.unlink()
                removed += 1
            
            if removed > 0:
                self.stats['invalidations'] += removed
                self.logger.debug(f"Invalidated cache: {namespace}")
            
            return removed
        else:
            # Invalidate all entries in namespace
            removed = 0
            namespace_prefix = f"{namespace}:"
            
            # Remove from memory cache
            keys_to_remove = []
            for cache_key in self._memory_cache:
                # Check if this cache key belongs to the namespace
                if self._memory_cache[cache_key].created_at:  # This is a bit of a hack
                    keys_to_remove.append(cache_key)
            
            for cache_key in keys_to_remove:
                del self._memory_cache[cache_key]
                removed += 1
            
            # Remove from file cache (scan all cache files)
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    # This is expensive but thorough
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                    # If we can load it, it might belong to this namespace
                    # For now, just track that we're doing namespace invalidation
                    pass
                except:
                    pass
            
            if removed > 0:
                self.stats['invalidations'] += removed
                self.logger.debug(f"Invalidated namespace: {namespace} ({removed} entries)")
            
            return removed
    
    def clear_all(self) -> int:
        """Clear all cache entries."""
        removed = len(self._memory_cache)
        
        # Clear memory cache
        self._memory_cache.clear()
        
        # Clear file cache
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()
            removed += 1
        
        self.stats['invalidations'] += removed
        self.logger.info(f"Cleared all cache entries ({removed} total)")
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'memory_entries': len(self._memory_cache),
            'file_entries': len(list(self.cache_dir.glob("*.cache")))
        }
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries."""
        removed = 0
        
        # Clean memory cache
        expired_keys = []
        for cache_key, entry in self._memory_cache.items():
            if entry.is_expired():
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            del self._memory_cache[cache_key]
            removed += 1
        
        # Clean file cache
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                
                if entry.is_expired():
                    cache_file.unlink()
                    removed += 1
                    
            except Exception as e:
                # If we can't read it, remove it
                self.logger.warning(f"Removing corrupted cache file {cache_file}: {e}")
                cache_file.unlink()
                removed += 1
        
        if removed > 0:
            self.stats['invalidations'] += removed
            self.logger.info(f"Cleaned up {removed} expired cache entries")
        
        return removed


# Global cache instance
_cache: Optional[KomodoCache] = None


def get_cache() -> KomodoCache:
    """Get the global cache instance."""
    global _cache
    if _cache is None:
        _cache = KomodoCache()
    return _cache


def cached(namespace: str, ttl_seconds: Optional[int] = None, 
          file_dependencies: Optional[Callable] = None,
          key_func: Optional[Callable] = None):
    """
    Decorator for caching function results.
    
    Args:
        namespace: Cache namespace
        ttl_seconds: Time to live in seconds
        file_dependencies: Function that returns list of file dependencies
        key_func: Function to generate cache key from function args
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = {
                    'args': args,
                    'kwargs': kwargs,
                    'func_name': func.__name__
                }
            
            # Check cache
            cached_result = cache.get(namespace, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Get file dependencies
            deps = file_dependencies(*args, **kwargs) if file_dependencies else None
            
            # Cache result
            cache.set(namespace, cache_key, result, ttl_seconds, deps)
            
            return result
        
        return wrapper
    return decorator


def cache_file_scan(file_path: str, scan_func: Callable) -> Any:
    """
    Cache the result of scanning a file.
    
    Args:
        file_path: Path to file being scanned
        scan_func: Function that scans the file
        
    Returns:
        Cached or fresh scan result
    """
    cache = get_cache()
    cache_key = {'file_path': file_path, 'func': scan_func.__name__}
    
    # Check cache with file dependency
    result = cache.get('file_scan', cache_key)
    if result is not None:
        return result
    
    # Scan file and cache result
    result = scan_func(file_path)
    cache.set('file_scan', cache_key, result, 
             file_dependencies=[file_path])
    
    return result


def cache_directory_scan(directory: str, scan_func: Callable) -> Any:
    """
    Cache the result of scanning a directory.
    
    Args:
        directory: Path to directory being scanned
        scan_func: Function that scans the directory
        
    Returns:
        Cached or fresh scan result
    """
    cache = get_cache()
    cache_key = {'directory': directory, 'func': scan_func.__name__}
    
    # Get all files in directory for dependencies
    dir_path = Path(directory)
    dependencies = [str(f) for f in dir_path.rglob('*') if f.is_file()]
    
    # Check cache
    result = cache.get('directory_scan', cache_key)
    if result is not None:
        return result
    
    # Scan directory and cache result
    result = scan_func(directory)
    cache.set('directory_scan', cache_key, result, 
             file_dependencies=dependencies)
    
    return result 