#!/usr/bin/env python3
"""
Logging Utilities

Centralized logging system for the Komodo Documentation Library.
Provides structured logging with configurable output formats and levels.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from .config import get_config


class EmojiFormatter(logging.Formatter):
    """Custom formatter that adds emoji indicators for different log levels."""
    
    EMOJI_MAP = {
        'DEBUG': '🔍 ',
        'INFO': 'ℹ️  ',
        'WARNING': '⚠️  ',
        'ERROR': '❌ ',
        'CRITICAL': '🚨 ',
        'SUCCESS': '✅ ',
        'PROGRESS': '🔄 ',
        'SAVE': '💾 ',
        'SKIP': '⏭️  ',
        'DELETE': '🗑️  ',
        'CREATE': '📁 ',
        'UPDATE': '🔄 '
    }
    
    def format(self, record):
        # Add emoji if configured
        config = get_config()
        if config.logging.emoji_output:
            emoji = self.EMOJI_MAP.get(record.levelname, '')
            if emoji:
                record.msg = f"{emoji} {record.msg}"
        
        return super().format(record)


class KomodoLogger:
    """
    Centralized logger for the Komodo Documentation Library.
    
    Provides structured logging with support for:
    - Multiple output destinations (console, file)
    - Configurable formatting (with/without emoji)
    - Progress tracking
    - Custom log levels for domain-specific events
    """
    
    def __init__(self, name: str = "komodo-lib"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Custom log levels
        logging.addLevelName(25, 'SUCCESS')
        logging.addLevelName(22, 'PROGRESS')
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup logging handlers based on configuration."""
        config = get_config()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_level = self._get_console_level(config)
        console_handler.setLevel(console_level)
        
        # Format setup
        if config.logging.emoji_output:
            console_formatter = EmojiFormatter('%(message)s')
        else:
            console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if configured)
        if config.logging.log_file:
            file_handler = logging.FileHandler(config.logging.log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def _get_console_level(self, config) -> int:
        """Determine console logging level based on configuration."""
        if config.logging.quiet:
            return logging.WARNING
        elif config.logging.verbose:
            return logging.DEBUG
        else:
            return logging.INFO
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)
    
    def success(self, message: str, **kwargs):
        """Log success message."""
        self.logger.log(25, message, extra=kwargs)
    
    def progress(self, message: str, **kwargs):
        """Log progress message."""
        config = get_config()
        if config.logging.progress_indicators:
            self.logger.log(22, message, extra=kwargs)
    
    def operation(self, operation: str, message: str, **kwargs):
        """Log operation-specific message with custom emoji."""
        config = get_config()
        if config.logging.emoji_output:
            emoji_map = {
                'save': '💾 ',
                'skip': '⏭️  ',
                'delete': '🗑️  ',
                'create': '📁 ',
                'update': '🔄 ',
                'scan': '🔍 ',
                'process': '⚙️  ',
                'generate': '🔨 ',
                'validate': '✅ '
            }
            emoji = emoji_map.get(operation.lower(), '')
            if emoji:
                message = f"{emoji}{message}"
        
        self.logger.info(message, extra=kwargs)
    
    def file_operation(self, operation: str, file_path: str, success: bool = True, **kwargs):
        """Log file operation with standardized format."""
        action = "completed" if success else "failed"
        level = self.success if success else self.error
        level(f"File {operation} {action}: {file_path}", **kwargs)
    
    def method_operation(self, method_name: str, operation: str, details: str = "", **kwargs):
        """Log method-specific operations."""
        message = f"Method '{method_name}': {operation}"
        if details:
            message += f" - {details}"
        self.info(message, **kwargs)
    
    def stats(self, title: str, stats: Dict[str, Any]):
        """Log statistics in a formatted way."""
        self.info(f"📊 {title}")
        for key, value in stats.items():
            self.info(f"   {key}: {value}")
    
    def separator(self, title: str = ""):
        """Log a visual separator."""
        if title:
            self.info(f"\n{'='*50}")
            self.info(title)
            self.info('='*50)
        else:
            self.info('-'*30)


# Global logger instances
_loggers: Dict[str, KomodoLogger] = {}


def get_logger(name: str = "komodo-lib") -> KomodoLogger:
    """Get a logger instance by name."""
    if name not in _loggers:
        _loggers[name] = KomodoLogger(name)
    return _loggers[name]


def setup_logging(log_file: Optional[str] = None, verbose: bool = None, 
                 quiet: bool = None, emoji: bool = None, events: bool = False) -> KomodoLogger:
    """
    Setup logging with custom configuration.
    
    Args:
        log_file: Path to log file (optional)
        verbose: Enable verbose logging
        quiet: Enable quiet mode (warnings and errors only)
        emoji: Enable emoji output
        events: Enable events logging
        
    Returns:
        Configured logger instance
    """
    config = get_config()
    
    # Override config if parameters provided
    if log_file is not None:
        config.logging.log_file = log_file
    if verbose is not None:
        config.logging.verbose = verbose
    if quiet is not None:
        config.logging.quiet = quiet
    if emoji is not None:
        config.logging.emoji_output = emoji
    if events is not None:
        config.logging.events = events
    
    # Clear existing loggers to apply new config
    _loggers.clear()
    
    return get_logger()


class ProgressTracker:
    """Helper class for tracking and logging progress of long operations."""
    
    def __init__(self, total: int, operation: str = "Processing", logger: KomodoLogger = None):
        self.total = total
        self.current = 0
        self.operation = operation
        self.logger = logger or get_logger()
        self.start_time = datetime.now()
        
        self.logger.progress(f"{operation}: Starting ({total} items)")
    
    def update(self, increment: int = 1, message: str = ""):
        """Update progress counter."""
        self.current += increment
        
        if self.current % max(1, self.total // 10) == 0 or self.current == self.total:
            percentage = (self.current / self.total) * 100
            elapsed = datetime.now() - self.start_time
            
            progress_msg = f"{self.operation}: {self.current}/{self.total} ({percentage:.1f}%)"
            if message:
                progress_msg += f" - {message}"
            
            if self.current == self.total:
                progress_msg += f" [Completed in {elapsed.total_seconds():.1f}s]"
            
            self.logger.progress(progress_msg)
    
    def finish(self, message: str = ""):
        """Mark operation as finished."""
        elapsed = datetime.now() - self.start_time
        final_msg = f"{self.operation}: Completed {self.current}/{self.total} in {elapsed.total_seconds():.1f}s"
        if message:
            final_msg += f" - {message}"
        self.logger.success(final_msg)


# Convenience functions for common logging scenarios
def log_file_operation(operation: str, file_path: str, success: bool = True):
    """Quick file operation logging."""
    logger = get_logger()
    logger.file_operation(operation, file_path, success)


def log_method_processing(method_name: str, operation: str, details: str = ""):
    """Quick method processing logging."""
    logger = get_logger()
    logger.method_operation(method_name, operation, details)


def log_stats(title: str, stats: Dict[str, Any]):
    """Quick statistics logging."""
    logger = get_logger()
    logger.stats(title, stats) 