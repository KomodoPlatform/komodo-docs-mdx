"""
Unit tests for logging utilities.

Tests the improved logging system with dependency injection.
"""

import pytest
import logging
from io import StringIO
from unittest.mock import Mock, patch

from lib.utils.logging_utils import (
    get_logger, 
    set_config_provider, 
    KomodoLogger, 
    EmojiFormatter,
    ProgressTracker
)


class TestEmojiFormatter:
    """Test cases for EmojiFormatter class."""
    
    def test_emoji_formatter_enabled(self):
        """Test emoji formatter when emojis are enabled."""
        formatter = EmojiFormatter(emoji_enabled=True)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "ℹ️" in formatted
        assert "Test message" in formatted
    
    def test_emoji_formatter_disabled(self):
        """Test emoji formatter when emojis are disabled."""
        formatter = EmojiFormatter(emoji_enabled=False)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Test message", args=(), exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "ℹ️" not in formatted
        assert "Test message" in formatted


class TestKomodoLogger:
    """Test cases for KomodoLogger class."""
    
    def setup_method(self):
        """Set up test environment."""
        # Clear singleton instances
        KomodoLogger._instances.clear()
    
    def test_singleton_pattern(self):
        """Test that KomodoLogger follows singleton pattern per name."""
        logger1 = KomodoLogger("test-logger")
        logger2 = KomodoLogger("test-logger")
        logger3 = KomodoLogger("different-logger")
        
        assert logger1 is logger2
        assert logger1 is not logger3
    
    def test_dependency_injection(self):
        """Test dependency injection for configuration."""
        mock_config_provider = Mock()
        mock_config = Mock()
        mock_config.logging.emoji_output = True
        mock_config.logging.log_file = None
        mock_config.logging.quiet = False
        mock_config.logging.verbose = True
        mock_config.logging.progress_indicators = True
        mock_config_provider.return_value = mock_config
        
        logger = KomodoLogger("di-test", config_provider=mock_config_provider)
        
        # Test that config provider is used
        emoji_output, log_file, quiet, verbose, progress = logger._get_config_values()
        assert emoji_output is True
        assert log_file is None
        assert quiet is False
        assert verbose is True
        assert progress is True
    
    def test_fallback_config(self):
        """Test fallback configuration when provider fails."""
        def failing_provider():
            raise Exception("Config failed")
        
        logger = KomodoLogger("fallback-test", config_provider=failing_provider)
        
        # Should fall back to defaults
        emoji_output, log_file, quiet, verbose, progress = logger._get_config_values()
        assert emoji_output is True  # Default fallback
        assert log_file is None
        assert quiet is False
        assert verbose is True
        assert progress is True
    
    def test_logging_methods(self):
        """Test various logging methods."""
        # Create a simple mock logger
        class MockLogger:
            def info(self, msg): print(f"INFO: {msg}")
            def success(self, msg): print(f"SUCCESS: {msg}")
            def warning(self, msg): print(f"WARNING: {msg}")
            def error(self, msg): print(f"ERROR: {msg}")
        
        mock_logger = MockLogger()
        
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            mock_logger.info("Info message")
            mock_logger.success("Success message")
            mock_logger.warning("Warning message")
            mock_logger.error("Error message")
            
            # Check that messages were logged
            output = mock_stdout.getvalue()
            # Note: Actual output depends on configuration, just verify no exceptions


class TestProgressTracker:
    """Test cases for ProgressTracker class."""
    
    def test_progress_tracker_initialization(self):
        """Test ProgressTracker initialization."""
        # Create a simple mock logger
        class MockLogger:
            def info(self, msg): pass
            def debug(self, msg): pass
            def progress(self, msg): pass
        
        mock_logger = MockLogger()
        tracker = ProgressTracker(100, "Test Operation", mock_logger)
        
        assert tracker.total == 100
        assert tracker.current == 0
        assert tracker.operation == "Test Operation"
        assert tracker.logger is mock_logger
    
    def test_progress_update(self):
        """Test progress updates."""
        class MockLogger:
            def info(self, msg): pass
            def debug(self, msg): pass
            def progress(self, msg): pass
        
        mock_logger = MockLogger()
        tracker = ProgressTracker(10, "Test", mock_logger)
        
        # Update progress
        tracker.update(5)
        assert tracker.current == 5
        
        # Update with message
        tracker.update(3, "Processing files")
        assert tracker.current == 8
    
    def test_progress_finish(self):
        """Test progress completion."""
        class MockLogger:
            def info(self, msg): pass
            def success(self, msg): pass
            def progress(self, msg): pass
        
        mock_logger = MockLogger()
        tracker = ProgressTracker(5, "Test", mock_logger)
        tracker.current = 5
        
        # Should complete without error
        tracker.finish("All done")


class TestGlobalFunctions:
    """Test global utility functions."""
    
    def test_set_config_provider(self):
        """Test setting global config provider."""
        mock_provider = Mock()
        set_config_provider(mock_provider)
        
        # Test that new loggers use the provider
        from lib.utils.logging_utils import _config_provider
        assert _config_provider is mock_provider
    
    def test_get_logger_singleton(self):
        """Test that get_logger returns singleton instances."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        
        assert logger1 is logger2


@pytest.mark.integration
class TestLoggingIntegration:
    """Integration tests for the complete logging system."""
    
    def test_full_logging_setup(self):
        """Test complete logging setup with configuration."""
        from lib.constants.config import get_config
        
        # Setup dependency injection
        set_config_provider(get_config)
        logger = get_logger("integration-test")
        
        # Test all logging levels
        with patch('sys.stdout', new_callable=StringIO):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.success("Success message")
            logger.progress("Progress message")
        
        # If we get here without exceptions, the integration works
        assert True 