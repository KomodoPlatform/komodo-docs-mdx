#!/usr/bin/env python3
"""
Factory Pattern Implementation with Dependency Injection

Provides factory classes for creating different types of generators and processors
with proper dependency injection for improved modularity and testability.
"""

from abc import ABC, abstractmethod
from typing import Dict, Type, Any, Optional, List, Protocol
from dataclasses import dataclass
from enum import Enum

from .config import KomodoConfig, get_config
from .validation import ValidationManager, ValidationLevel
from .logging_utils import get_logger
from .cache import KomodoCache, get_cache
from .observers import EventPublisher, get_event_publisher
from .processors import FileProcessorContext
from .exceptions import ConfigurationError


class ComponentType(Enum):
    """Types of components that can be created by factories."""
    
    POSTMAN_GENERATOR = "postman_generator"
    OPENAPI_MANAGER = "openapi_manager"
    METHOD_MAPPER = "method_mapper"
    FILE_PROCESSOR = "file_processor"
    VALIDATION_MANAGER = "validation_manager"
    ASYNC_PROCESSOR = "async_processor"
    EXTRACTOR = "extractor"
    DEDUPLICATOR = "deduplicator"


@dataclass
class ComponentDependencies:
    """Container for component dependencies."""
    
    config: KomodoConfig
    logger: Any
    cache: KomodoCache
    event_publisher: EventPublisher
    validation_manager: ValidationManager
    
    @classmethod
    def create_default(cls) -> 'ComponentDependencies':
        """Create dependencies with default instances."""
        return cls(
            config=get_config(),
            logger=get_logger("factory"),
            cache=get_cache(),
            event_publisher=get_event_publisher(),
            validation_manager=ValidationManager()
        )


class ComponentFactory(ABC):
    """
    Abstract base class for component factories.
    
    Defines the interface for creating components with dependency injection.
    """
    
    def __init__(self, dependencies: ComponentDependencies = None):
        self.dependencies = dependencies or ComponentDependencies.create_default()
        self.logger = self.dependencies.logger
        self._instances: Dict[str, Any] = {}
    
    @abstractmethod
    def create(self, component_type: str, **kwargs) -> Any:
        """Create a component of the specified type."""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """Get list of supported component types."""
        pass
    
    def get_instance(self, component_type: str, **kwargs) -> Any:
        """Get or create a singleton instance of the component."""
        instance_key = f"{component_type}:{hash(frozenset(kwargs.items()) if kwargs else frozenset())}"
        
        if instance_key not in self._instances:
            self._instances[instance_key] = self.create(component_type, **kwargs)
        
        return self._instances[instance_key]
    
    def clear_instances(self):
        """Clear all cached instances."""
        self._instances.clear()


class ProcessorFactory(ComponentFactory):
    """Factory for creating file processors and processing components."""
    
    def create(self, component_type: str, **kwargs) -> Any:
        """Create a processor component."""
        validation_level = kwargs.get('validation_level', ValidationLevel.STANDARD)
        
        if component_type == ComponentType.FILE_PROCESSOR.value:
            return self._create_file_processor(validation_level, **kwargs)
        
        elif component_type == ComponentType.ASYNC_PROCESSOR.value:
            return self._create_async_processor(**kwargs)
        
        elif component_type == ComponentType.EXTRACTOR.value:
            return self._create_extractor(**kwargs)
        
        elif component_type == ComponentType.DEDUPLICATOR.value:
            return self._create_deduplicator(**kwargs)
        
        else:
            raise ValueError(f"Unknown processor type: {component_type}")
    
    def get_supported_types(self) -> List[str]:
        """Get supported processor types."""
        return [
            ComponentType.FILE_PROCESSOR.value,
            ComponentType.ASYNC_PROCESSOR.value,
            ComponentType.EXTRACTOR.value,
            ComponentType.DEDUPLICATOR.value
        ]
    
    def _create_file_processor(self, validation_level: ValidationLevel, **kwargs) -> FileProcessorContext:
        """Create a file processor with dependencies."""
        from .processors import FileProcessorContext
        
        processor = FileProcessorContext(validation_level)
        
        # Inject dependencies
        processor.config = self.dependencies.config
        processor.event_publisher = self.dependencies.event_publisher
        
        self.logger.debug(f"Created FileProcessorContext with validation level: {validation_level}")
        return processor
    
    def _create_async_processor(self, **kwargs) -> Any:
        """Create an async processor with dependencies."""
        from .async_utils import AsyncFileProcessor
        
        max_workers = kwargs.get('max_workers', self.dependencies.config.processing.max_workers)
        processor = AsyncFileProcessor(max_workers)
        
        # Inject dependencies
        processor.config = self.dependencies.config
        processor.event_publisher = self.dependencies.event_publisher
        
        self.logger.debug(f"Created AsyncFileProcessor with {max_workers} workers")
        return processor
    
    def _create_extractor(self, **kwargs) -> Any:
        """Create an extractor with dependencies."""
        from .extractors import MDXExtractor
        
        extractor = MDXExtractor()
        
        # Inject dependencies
        extractor.config = self.dependencies.config
        extractor.validation_manager = self.dependencies.validation_manager
        extractor.event_publisher = self.dependencies.event_publisher
        
        self.logger.debug("Created MDXExtractor")
        return extractor
    
    def _create_deduplicator(self, **kwargs) -> Any:
        """Create a deduplicator with dependencies."""
        from .deduplicator import ExampleDeduplicator
        
        deduplicator = ExampleDeduplicator()
        
        # Inject dependencies
        deduplicator.cache = self.dependencies.cache
        deduplicator.event_publisher = self.dependencies.event_publisher
        
        self.logger.debug("Created ExampleDeduplicator")
        return deduplicator


class GeneratorFactory(ComponentFactory):
    """Factory for creating generators (Postman, OpenAPI, etc.)."""
    
    def create(self, component_type: str, **kwargs) -> Any:
        """Create a generator component."""
        if component_type == ComponentType.POSTMAN_GENERATOR.value:
            return self._create_postman_generator(**kwargs)
        
        elif component_type == ComponentType.OPENAPI_MANAGER.value:
            return self._create_openapi_manager(**kwargs)
        
        elif component_type == ComponentType.METHOD_MAPPER.value:
            return self._create_method_mapper(**kwargs)
        
        else:
            raise ValueError(f"Unknown generator type: {component_type}")
    
    def get_supported_types(self) -> List[str]:
        """Get supported generator types."""
        return [
            ComponentType.POSTMAN_GENERATOR.value,
            ComponentType.OPENAPI_MANAGER.value,
            ComponentType.METHOD_MAPPER.value
        ]
    
    def _create_postman_generator(self, **kwargs) -> Any:
        """Create a Postman generator with dependencies."""
        from .postman import PostmanCollectionGenerator
        
        generator = PostmanCollectionGenerator()
        
        # Inject dependencies
        generator.config = self.dependencies.config
        generator.cache = self.dependencies.cache
        generator.event_publisher = self.dependencies.event_publisher
        generator.validation_manager = self.dependencies.validation_manager
        
        self.logger.debug("Created PostmanCollectionGenerator")
        return generator
    
    def _create_openapi_manager(self, **kwargs) -> Any:
        """Create an OpenAPI manager with dependencies."""
        from .openapi_manager import OpenAPIManager
        
        manager = OpenAPIManager()
        
        # Inject dependencies
        manager.config = self.dependencies.config
        manager.cache = self.dependencies.cache
        manager.event_publisher = self.dependencies.event_publisher
        manager.validation_manager = self.dependencies.validation_manager
        
        self.logger.debug("Created OpenAPIManager")
        return manager
    
    def _create_method_mapper(self, **kwargs) -> Any:
        """Create a method mapper with dependencies."""
        from .mapping import MethodMapper
        
        mapper = MethodMapper()
        
        # Inject dependencies
        mapper.config = self.dependencies.config
        mapper.cache = self.dependencies.cache
        mapper.event_publisher = self.dependencies.event_publisher
        
        self.logger.debug("Created MethodMapper")
        return mapper


class UtilityFactory(ComponentFactory):
    """Factory for creating utility components."""
    
    def create(self, component_type: str, **kwargs) -> Any:
        """Create a utility component."""
        if component_type == ComponentType.VALIDATION_MANAGER.value:
            return self._create_validation_manager(**kwargs)
        
        else:
            raise ValueError(f"Unknown utility type: {component_type}")
    
    def get_supported_types(self) -> List[str]:
        """Get supported utility types."""
        return [
            ComponentType.VALIDATION_MANAGER.value
        ]
    
    def _create_validation_manager(self, **kwargs) -> ValidationManager:
        """Create a validation manager with dependencies."""
        validation_level = kwargs.get('validation_level', ValidationLevel.STANDARD)
        manager = ValidationManager(validation_level)
        
        # Inject dependencies
        manager.config = self.dependencies.config
        manager.event_publisher = self.dependencies.event_publisher
        
        self.logger.debug(f"Created ValidationManager with level: {validation_level}")
        return manager


class MasterFactory:
    """
    Master factory that coordinates all component factories.
    
    Provides a unified interface for creating any type of component
    with proper dependency injection.
    """
    
    def __init__(self, dependencies: ComponentDependencies = None):
        self.dependencies = dependencies or ComponentDependencies.create_default()
        self.logger = self.dependencies.logger
        
        # Initialize specialized factories
        self.processor_factory = ProcessorFactory(self.dependencies)
        self.generator_factory = GeneratorFactory(self.dependencies)
        self.utility_factory = UtilityFactory(self.dependencies)
        
        # Map component types to factories
        self.factory_map: Dict[str, ComponentFactory] = {}
        self._build_factory_map()
        
        self.logger.debug("MasterFactory initialized with all specialized factories")
    
    def _build_factory_map(self):
        """Build mapping of component types to factories."""
        for factory in [self.processor_factory, self.generator_factory, self.utility_factory]:
            for component_type in factory.get_supported_types():
                self.factory_map[component_type] = factory
    
    def create(self, component_type: str, **kwargs) -> Any:
        """Create a component using the appropriate factory."""
        if component_type not in self.factory_map:
            raise ValueError(f"Unknown component type: {component_type}. "
                           f"Supported types: {list(self.factory_map.keys())}")
        
        factory = self.factory_map[component_type]
        component = factory.create(component_type, **kwargs)
        
        self.logger.debug(f"Created component {component_type} using {factory.__class__.__name__}")
        return component
    
    def get_instance(self, component_type: str, **kwargs) -> Any:
        """Get or create a singleton instance using the appropriate factory."""
        if component_type not in self.factory_map:
            raise ValueError(f"Unknown component type: {component_type}")
        
        factory = self.factory_map[component_type]
        return factory.get_instance(component_type, **kwargs)
    
    def get_supported_types(self) -> List[str]:
        """Get all supported component types."""
        return list(self.factory_map.keys())
    
    def clear_all_instances(self):
        """Clear all cached instances from all factories."""
        for factory in [self.processor_factory, self.generator_factory, self.utility_factory]:
            factory.clear_instances()
        self.logger.info("Cleared all cached instances")
    
    def create_complete_pipeline(self, validation_level: ValidationLevel = ValidationLevel.STANDARD) -> Dict[str, Any]:
        """Create a complete processing pipeline with all components."""
        pipeline = {}
        
        try:
            # Create core components
            pipeline['file_processor'] = self.create(ComponentType.FILE_PROCESSOR.value, 
                                                   validation_level=validation_level)
            pipeline['async_processor'] = self.create(ComponentType.ASYNC_PROCESSOR.value)
            pipeline['method_mapper'] = self.create(ComponentType.METHOD_MAPPER.value)
            pipeline['postman_generator'] = self.create(ComponentType.POSTMAN_GENERATOR.value)
            pipeline['openapi_manager'] = self.create(ComponentType.OPENAPI_MANAGER.value)
            pipeline['validation_manager'] = self.create(ComponentType.VALIDATION_MANAGER.value,
                                                       validation_level=validation_level)
            pipeline['extractor'] = self.create(ComponentType.EXTRACTOR.value)
            pipeline['deduplicator'] = self.create(ComponentType.DEDUPLICATOR.value)
            
            self.logger.info(f"Created complete pipeline with {len(pipeline)} components")
            return pipeline
            
        except Exception as e:
            self.logger.error(f"Failed to create complete pipeline: {e}")
            raise ConfigurationError(f"Pipeline creation failed: {e}", {"component_count": len(pipeline)})


class DependencyInjector:
    """
    Dependency injection container for managing component dependencies.
    
    Provides a clean way to inject dependencies into components.
    """
    
    def __init__(self):
        self.logger = get_logger("dependency-injector")
        self._dependencies: Dict[str, Any] = {}
        self._factories: Dict[Type, Callable] = {}
    
    def register_dependency(self, interface: Type, implementation: Any):
        """Register a dependency implementation for an interface."""
        self._dependencies[interface.__name__] = implementation
        self.logger.debug(f"Registered dependency: {interface.__name__} -> {implementation.__class__.__name__}")
    
    def register_factory(self, interface: Type, factory: Callable):
        """Register a factory function for creating instances."""
        self._factories[interface] = factory
        self.logger.debug(f"Registered factory for: {interface.__name__}")
    
    def get_dependency(self, interface: Type) -> Any:
        """Get a dependency by interface."""
        interface_name = interface.__name__
        
        if interface_name in self._dependencies:
            return self._dependencies[interface_name]
        
        if interface in self._factories:
            instance = self._factories[interface]()
            self._dependencies[interface_name] = instance
            return instance
        
        raise ValueError(f"No dependency registered for: {interface_name}")
    
    def inject_dependencies(self, component: Any, dependencies: Dict[str, Type]):
        """Inject dependencies into a component."""
        for attr_name, interface in dependencies.items():
            dependency = self.get_dependency(interface)
            setattr(component, attr_name, dependency)
            self.logger.debug(f"Injected {interface.__name__} into {component.__class__.__name__}.{attr_name}")


# Global factory instances
_master_factory: Optional[MasterFactory] = None
_dependency_injector: Optional[DependencyInjector] = None


def get_master_factory(dependencies: ComponentDependencies = None) -> MasterFactory:
    """Get the global master factory instance."""
    global _master_factory
    if _master_factory is None:
        _master_factory = MasterFactory(dependencies)
    return _master_factory


def get_dependency_injector() -> DependencyInjector:
    """Get the global dependency injector instance."""
    global _dependency_injector
    if _dependency_injector is None:
        _dependency_injector = DependencyInjector()
    return _dependency_injector


# Convenience functions for common component creation
def create_file_processor(validation_level: ValidationLevel = ValidationLevel.STANDARD) -> Any:
    """Create a file processor with default dependencies."""
    return get_master_factory().create(ComponentType.FILE_PROCESSOR.value, validation_level=validation_level)


def create_postman_generator() -> Any:
    """Create a Postman generator with default dependencies."""
    return get_master_factory().create(ComponentType.POSTMAN_GENERATOR.value)


def create_method_mapper() -> Any:
    """Create a method mapper with default dependencies."""
    return get_master_factory().create(ComponentType.METHOD_MAPPER.value)


def create_complete_pipeline(validation_level: ValidationLevel = ValidationLevel.STANDARD) -> Dict[str, Any]:
    """Create a complete processing pipeline."""
    return get_master_factory().create_complete_pipeline(validation_level)


def reset_factories():
    """Reset all factory instances (useful for testing)."""
    global _master_factory, _dependency_injector
    if _master_factory:
        _master_factory.clear_all_instances()
    _master_factory = None
    _dependency_injector = None 