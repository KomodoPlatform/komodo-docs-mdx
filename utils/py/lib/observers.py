#!/usr/bin/env python3
"""
Observer Pattern Implementation

Provides event handling and progress reporting using the Observer pattern.
Allows multiple observers to monitor operations and respond to events.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import logging

from .logging_utils import get_logger


class EventType(Enum):
    """Types of events that can be observed."""
    
    # General events
    OPERATION_STARTED = "operation_started"
    OPERATION_COMPLETED = "operation_completed"
    OPERATION_FAILED = "operation_failed"
    
    # Progress events
    PROGRESS_UPDATED = "progress_updated"
    STAGE_CHANGED = "stage_changed"
    
    # File events
    FILE_PROCESSED = "file_processed"
    FILE_SKIPPED = "file_skipped"
    FILE_ERROR = "file_error"
    
    # Validation events
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    VALIDATION_WARNING = "validation_warning"
    
    # Cache events
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    CACHE_INVALIDATED = "cache_invalidated"
    
    # Custom events
    CUSTOM_EVENT = "custom_event"


@dataclass
class Event:
    """Represents an event in the system."""
    
    event_type: EventType
    source: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "source": self.source,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp.isoformat()
        }


class Observer(ABC):
    """
    Abstract base class for observers.
    
    Defines the interface that all observers must implement.
    """
    
    @abstractmethod
    def update(self, event: Event) -> None:
        """Handle an event notification."""
        pass
    
    @abstractmethod
    def get_observer_name(self) -> str:
        """Get the name of this observer."""
        pass


class Subject(ABC):
    """
    Abstract base class for subjects that can be observed.
    
    Provides the interface for managing observers and notifying them.
    """
    
    def __init__(self):
        self._observers: List[Observer] = []
        self._lock = threading.Lock()
    
    def attach(self, observer: Observer) -> None:
        """Attach an observer to this subject."""
        with self._lock:
            if observer not in self._observers:
                self._observers.append(observer)
    
    def detach(self, observer: Observer) -> None:
        """Detach an observer from this subject."""
        with self._lock:
            if observer in self._observers:
                self._observers.remove(observer)
    
    def notify(self, event: Event) -> None:
        """Notify all observers of an event."""
        # Create a snapshot of observers to avoid issues with concurrent modification
        with self._lock:
            observers_snapshot = self._observers.copy()
        
        # Notify all observers
        for observer in observers_snapshot:
            try:
                observer.update(event)
            except Exception as e:
                # Log error but don't fail the entire notification
                logger = get_logger("subject")
                logger.error(f"Error notifying observer {observer.get_observer_name()}: {e}")
    
    def get_observer_count(self) -> int:
        """Get the number of attached observers."""
        with self._lock:
            return len(self._observers)


class LoggingObserver(Observer):
    """Observer that logs events using the logging system."""
    
    def __init__(self, name: str = "logging-observer"):
        self.name = name
        self.logger = get_logger(f"observer-{name}")
    
    def update(self, event: Event) -> None:
        """Log the event based on its type."""
        # Clean up the message format for better alignment
        if event.source and event.source != "unknown":
            # Format with consistent spacing and alignment
            message = f"{event.message}"
        else:
            message = event.message
        
        # Log at different levels based on event type
        if event.event_type in [EventType.OPERATION_FAILED, EventType.FILE_ERROR, EventType.VALIDATION_FAILED]:
            self.logger.error(message)
        elif event.event_type in [EventType.VALIDATION_WARNING]:
            self.logger.warning(message)
        elif event.event_type in [EventType.PROGRESS_UPDATED]:
            self.logger.progress(message)
        elif event.event_type in [EventType.OPERATION_COMPLETED, EventType.VALIDATION_PASSED]:
            self.logger.success(message)
        else:
            self.logger.info(message)
        
        # Log additional data if present and in debug mode
        if event.data and self.logger.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Event data: {event.data}")
    
    def get_observer_name(self) -> str:
        """Get the name of this observer."""
        return self.name


class ProgressTrackingObserver(Observer):
    """Observer that tracks progress across operations."""
    
    def __init__(self, name: str = "progress-tracker"):
        self.name = name
        self.logger = get_logger(f"progress-{name}")
        
        # Progress tracking state
        self.operations: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def update(self, event: Event) -> None:
        """Update progress tracking based on event."""
        operation_id = event.data.get("operation_id", event.source)
        
        with self._lock:
            if event.event_type == EventType.OPERATION_STARTED:
                self.operations[operation_id] = {
                    "started_at": event.timestamp,
                    "total": event.data.get("total", 0),
                    "completed": 0,
                    "failed": 0,
                    "status": "running"
                }
                # self.logger.info(f"🔄 Started tracking operation: {operation_id}")
            
            elif event.event_type == EventType.PROGRESS_UPDATED:
                if operation_id in self.operations:
                    op = self.operations[operation_id]
                    op["completed"] += event.data.get("increment", 1)
                    
                    # Calculate percentage
                    if op["total"] > 0:
                        percentage = (op["completed"] / op["total"]) * 100
                        self.logger.progress(f"📈 {operation_id}: {op['completed']}/{op['total']} ({percentage:.1f}%)")
            
            elif event.event_type in [EventType.OPERATION_COMPLETED, EventType.OPERATION_FAILED]:
                if operation_id in self.operations:
                    op = self.operations[operation_id]
                    op["status"] = "completed" if event.event_type == EventType.OPERATION_COMPLETED else "failed"
                    op["completed_at"] = event.timestamp
                    
                    duration = (event.timestamp - op["started_at"]).total_seconds()
                    status_emoji = "✅" if event.event_type == EventType.OPERATION_COMPLETED else "❌"
                    # self.logger.info(f"{status_emoji} Operation {operation_id} {op['status']} in {duration:.2f}s")
            
            elif event.event_type == EventType.FILE_ERROR:
                if operation_id in self.operations:
                    self.operations[operation_id]["failed"] += 1
    
    def get_operation_stats(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific operation."""
        with self._lock:
            return self.operations.get(operation_id, {}).copy()
    
    def get_all_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all tracked operations."""
        with self._lock:
            return {op_id: op.copy() for op_id, op in self.operations.items()}
    
    def get_observer_name(self) -> str:
        """Get the name of this observer."""
        return self.name


class StatisticsObserver(Observer):
    """Observer that collects statistical information about events."""
    
    def __init__(self, name: str = "statistics-collector"):
        self.name = name
        self.logger = get_logger(f"stats-{name}")
        
        # Statistics collection
        self.event_counts: Dict[EventType, int] = {}
        self.source_counts: Dict[str, int] = {}
        self.error_types: Dict[str, int] = {}
        self.first_event_time: Optional[datetime] = None
        self.last_event_time: Optional[datetime] = None
        self._lock = threading.Lock()
    
    def update(self, event: Event) -> None:
        """Collect statistics from the event."""
        with self._lock:
            # Update event type counts
            if event.event_type in self.event_counts:
                self.event_counts[event.event_type] += 1
            else:
                self.event_counts[event.event_type] = 1
            
            # Update source counts
            if event.source in self.source_counts:
                self.source_counts[event.source] += 1
            else:
                self.source_counts[event.source] = 1
            
            # Track error types
            if event.event_type in [EventType.OPERATION_FAILED, EventType.FILE_ERROR, EventType.VALIDATION_FAILED]:
                error_type = event.data.get("error_type", "unknown")
                if error_type in self.error_types:
                    self.error_types[error_type] += 1
                else:
                    self.error_types[error_type] = 1
            
            # Update time tracking
            if self.first_event_time is None:
                self.first_event_time = event.timestamp
            self.last_event_time = event.timestamp
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get collected statistics."""
        with self._lock:
            total_events = sum(self.event_counts.values())
            duration = None
            
            if self.first_event_time and self.last_event_time:
                duration = (self.last_event_time - self.first_event_time).total_seconds()
            
            return {
                "total_events": total_events,
                "event_types": {event_type.value: count for event_type, count in self.event_counts.items()},
                "sources": self.source_counts.copy(),
                "error_types": self.error_types.copy(),
                "duration_seconds": duration,
                "events_per_second": total_events / duration if duration and duration > 0 else 0,
                "first_event": self.first_event_time.isoformat() if self.first_event_time else None,
                "last_event": self.last_event_time.isoformat() if self.last_event_time else None
            }
    
    def reset_statistics(self) -> None:
        """Reset all collected statistics."""
        with self._lock:
            self.event_counts.clear()
            self.source_counts.clear()
            self.error_types.clear()
            self.first_event_time = None
            self.last_event_time = None
        
        self.logger.info("Statistics reset")
    
    def get_observer_name(self) -> str:
        """Get the name of this observer."""
        return self.name


class FileEventObserver(Observer):
    """Observer specifically for file-related events."""
    
    def __init__(self, name: str = "file-event-observer"):
        self.name = name
        self.logger = get_logger(f"file-{name}")
        
        # File tracking
        self.processed_files: List[str] = []
        self.failed_files: List[str] = []
        self.skipped_files: List[str] = []
        self._lock = threading.Lock()
    
    def update(self, event: Event) -> None:
        """Handle file-related events."""
        if event.event_type == EventType.FILE_PROCESSED:
            file_path = event.data.get("file_path", "unknown")
            with self._lock:
                self.processed_files.append(file_path)
        
        elif event.event_type == EventType.FILE_ERROR:
            file_path = event.data.get("file_path", "unknown")
            error = event.data.get("error", "unknown error")
            with self._lock:
                self.failed_files.append(file_path)
            self.logger.error(f"File error in {file_path}: {error}")
        
        elif event.event_type == EventType.FILE_SKIPPED:
            file_path = event.data.get("file_path", "unknown")
            reason = event.data.get("reason", "unknown reason")
            with self._lock:
                self.skipped_files.append(file_path)
            self.logger.debug(f"File skipped {file_path}: {reason}")
    
    def get_file_statistics(self) -> Dict[str, Any]:
        """Get file processing statistics."""
        with self._lock:
            return {
                "processed_count": len(self.processed_files),
                "failed_count": len(self.failed_files),
                "skipped_count": len(self.skipped_files),
                "total_files": len(self.processed_files) + len(self.failed_files) + len(self.skipped_files),
                "success_rate": (len(self.processed_files) / 
                               max(1, len(self.processed_files) + len(self.failed_files))) * 100
            }
    
    def get_failed_files(self) -> List[str]:
        """Get list of files that failed processing."""
        with self._lock:
            return self.failed_files.copy()
    
    def get_observer_name(self) -> str:
        """Get the name of this observer."""
        return self.name


class CallbackObserver(Observer):
    """Observer that executes custom callback functions."""
    
    def __init__(self, callback: Callable[[Event], None], name: str = "callback-observer"):
        self.callback = callback
        self.name = name
        self.logger = get_logger(f"callback-{name}")
    
    def update(self, event: Event) -> None:
        """Execute the callback function."""
        try:
            self.callback(event)
        except Exception as e:
            self.logger.error(f"Callback error in {self.name}: {e}")
    
    def get_observer_name(self) -> str:
        """Get the name of this observer."""
        return self.name


class EventPublisher(Subject):
    """
    Central event publisher for the Komodo Documentation Library.
    
    Provides a centralized way to publish events to all registered observers.
    """
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("event-publisher")
        
        # Import here to avoid circular imports
        from .config import get_config
        config = get_config()
        
        # Default observers
        self.progress_observer = ProgressTrackingObserver()
        self.statistics_observer = StatisticsObserver()
        self.file_observer = FileEventObserver()
        
        # Always attach these core observers
        self.attach(self.progress_observer)
        self.attach(self.statistics_observer)
        self.attach(self.file_observer)
        
        # Only attach logging observer if events are enabled
        if config.logging.events:
            self.logging_observer = LoggingObserver()
            self.attach(self.logging_observer)
            self.logger.debug("EventPublisher initialized with event logging enabled")
        else:
            self.logging_observer = None
            self.logger.debug("EventPublisher initialized with event logging disabled")
    
    def publish_operation_started(self, source: str, operation_name: str, total_items: int = 0, **kwargs):
        """Publish operation started event."""
        event = Event(
            event_type=EventType.OPERATION_STARTED,
            source=source,
            message=f"Started operation: {operation_name}",
            data={"operation_name": operation_name, "total": total_items, **kwargs}
        )
        self.notify(event)
    
    def publish_operation_completed(self, source: str, operation_name: str, **kwargs):
        """Publish operation completed event."""
        event = Event(
            event_type=EventType.OPERATION_COMPLETED,
            source=source,
            message=f"Completed operation: {operation_name}",
            data={"operation_name": operation_name, **kwargs}
        )
        self.notify(event)
    
    def publish_operation_failed(self, source: str, operation_name: str, error: str, **kwargs):
        """Publish operation failed event."""
        event = Event(
            event_type=EventType.OPERATION_FAILED,
            source=source,
            message=f"Failed operation: {operation_name} - {error}",
            data={"operation_name": operation_name, "error": error, **kwargs}
        )
        self.notify(event)
    
    def publish_progress_update(self, source: str, message: str, increment: int = 1, **kwargs):
        """Publish progress update event."""
        event = Event(
            event_type=EventType.PROGRESS_UPDATED,
            source=source,
            message=message,
            data={"increment": increment, **kwargs}
        )
        self.notify(event)
    
    def publish_file_processed(self, source: str, file_path: str, **kwargs):
        """Publish file processed event."""
        event = Event(
            event_type=EventType.FILE_PROCESSED,
            source=source,
            message=f"Processed file: {file_path}",
            data={"file_path": file_path, **kwargs}
        )
        self.notify(event)
    
    def publish_file_error(self, source: str, file_path: str, error: str, **kwargs):
        """Publish file error event."""
        event = Event(
            event_type=EventType.FILE_ERROR,
            source=source,
            message=f"Error processing file: {file_path} - {error}",
            data={"file_path": file_path, "error": error, **kwargs}
        )
        self.notify(event)
    
    def publish_custom_event(self, source: str, message: str, **kwargs):
        """Publish a custom event."""
        event = Event(
            event_type=EventType.CUSTOM_EVENT,
            source=source,
            message=message,
            data=kwargs
        )
        self.notify(event)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics from the statistics observer."""
        return self.statistics_observer.get_statistics()
    
    def get_file_statistics(self) -> Dict[str, Any]:
        """Get file statistics from the file observer."""
        return self.file_observer.get_file_statistics()
    
    def get_operation_stats(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific operation."""
        return self.progress_observer.get_operation_stats(operation_id)
    
    def add_callback_observer(self, callback: Callable[[Event], None], name: str = None) -> CallbackObserver:
        """Add a custom callback observer."""
        if name is None:
            name = f"callback-{len(self._observers)}"
        
        observer = CallbackObserver(callback, name)
        self.attach(observer)
        self.logger.debug(f"Added callback observer: {name}")
        return observer


# Global event publisher instance
_event_publisher: Optional[EventPublisher] = None


def get_event_publisher() -> EventPublisher:
    """Get the global event publisher instance."""
    global _event_publisher
    if _event_publisher is None:
        _event_publisher = EventPublisher()
    return _event_publisher


# Convenience functions for publishing common events
def publish_operation_started(source: str, operation_name: str, total_items: int = 0, **kwargs):
    """Convenience function to publish operation started event."""
    get_event_publisher().publish_operation_started(source, operation_name, total_items, **kwargs)


def publish_operation_completed(source: str, operation_name: str, **kwargs):
    """Convenience function to publish operation completed event."""
    get_event_publisher().publish_operation_completed(source, operation_name, **kwargs)


def publish_operation_failed(source: str, operation_name: str, error: str, **kwargs):
    """Convenience function to publish operation failed event."""
    get_event_publisher().publish_operation_failed(source, operation_name, error, **kwargs)


def publish_progress_update(source: str, message: str, increment: int = 1, **kwargs):
    """Convenience function to publish progress update."""
    get_event_publisher().publish_progress_update(source, message, increment, **kwargs)


def publish_file_processed(source: str, file_path: str, **kwargs):
    """Convenience function to publish file processed event."""
    get_event_publisher().publish_file_processed(source, file_path, **kwargs)


def publish_file_error(source: str, file_path: str, error: str, **kwargs):
    """Convenience function to publish file error event."""
    get_event_publisher().publish_file_error(source, file_path, error, **kwargs) 