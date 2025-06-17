#!/usr/bin/env python3
"""
Factory Components

Provides factory classes for creating and managing various components
of the Komodo Documentation Library system.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Type, Protocol, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

# Core imports
from ..constants.config import get_config
from .logging_utils import get_logger

# Lazy imports to avoid circular dependencies
def _get_config():
    """Lazy import of config to avoid circular dependency."""
    try:
        from ..constants.config import EnhancedKomodoConfig, get_config
        return EnhancedKomodoConfig, get_config
    except ImportError:
        # Fallback: return None if config not available
        return None, None

# Try to import logger - fallback if not available
try:
    from .logging_utils import get_logger
except ImportError:
    # Fallback: return a simple logger stub
    def get_logger(name="factories"):
        import logging
        return logging.getLogger(name)

# Initialize logger
logger = get_logger("factories")

from ..managers.validation_manager import ValidationManager
from ..constants.enums import ValidationLevel
from ..constants.exceptions import ConfigurationError
# from ..async_support.processors import FileProcessorContext  # Temporarily disabled


class ComponentType(Enum):
    """Types of components that can be created by factories."""
    
    POSTMAN_GENERATOR = "postman_generator"
    OPENAPI_MANAGER = "openapi_manager"
    METHOD_MAPPER = "method_mapper"
    # FILE_PROCESSOR = "file_processor"  # Temporarily disabled
    VALIDATION_MANAGER = "validation_manager"
    # ASYNC_PROCESSOR = "async_processor"  # Temporarily disabled
    EXTRACTOR = "extractor"
    DEDUPLICATOR = "deduplicator"


@dataclass
class ComponentDependencies:
    """Container for component dependencies."""
    
    config: Any
    logger: Any
    validation_manager: ValidationManager
    
    @classmethod
    def create_default(cls) -> 'ComponentDependencies':
        """Create dependencies with default instances."""
        EnhancedKomodoConfig, get_config_func = _get_config()
        get_logger_func = get_logger
        
        config = get_config_func() if get_config_func else None
        logger = get_logger_func("factory") if callable(get_logger_func) else get_logger_func
        
        return cls(
            config=config,
            logger=logger,
            validation_manager=ValidationManager()
        )


@dataclass
class ComponentCreationSpec:
    """Specification for creating a component with dependencies."""
    
    import_path: str
    class_name: str
    init_kwargs: Dict[str, Any] = None
    dependency_mappings: Dict[str, str] = None
    
    def __post_init__(self):
        """Set default values after initialization."""
        if self.init_kwargs is None:
            self.init_kwargs = {}
        if self.dependency_mappings is None:
            # Default dependency mappings
            self.dependency_mappings = {
                'config': 'config',
                'validation_manager': 'validation_manager'
            }


class ComponentFactory(ABC):
    """
    Abstract base class for component factories.
    
    CONSOLIDATED: Now uses unified component creation system to eliminate
    repetitive dependency injection patterns across all creation methods.
    """
    
    def __init__(self, dependencies: ComponentDependencies = None):
        self.dependencies = dependencies or ComponentDependencies.create_default()
        self.logger = self.dependencies.logger
        self._instances: Dict[str, Any] = {}
        
        # CONSOLIDATED: Component creation specifications
        self._component_specs = self._get_component_specs()
    
    @abstractmethod
    def _get_component_specs(self) -> Dict[str, ComponentCreationSpec]:
        """Get component creation specifications for this factory."""
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """Get list of supported component types."""
        pass
    
    def create(self, component_type: str, **kwargs) -> Any:
        """
        Create a component of the specified type.
        
        CONSOLIDATED: Unified creation logic eliminates duplicate patterns.
        """
        if component_type not in self._component_specs:
            raise ValueError(f"Unknown component type: {component_type}")
        
        spec = self._component_specs[component_type]
        return self._create_component_from_spec(spec, component_type, **kwargs)
    
    def _create_component_from_spec(self, spec: ComponentCreationSpec, 
                                  component_type: str, **kwargs) -> Any:
        """
        CONSOLIDATED: Unified component creation from specification.
        Eliminates duplicate creation and dependency injection logic.
        """
        # Import the component class
        try:
            module_parts = spec.import_path.rsplit('.', 1)
            module_path = module_parts[0]
            
            # Handle relative imports
            if module_path.startswith('..'):
                # Dynamic import for relative modules
                import importlib
                full_module_path = f"lib.{module_path[2:]}"  # Remove '..'
                module = importlib.import_module(full_module_path, package=__package__)
            else:
                exec(f"from {spec.import_path} import {spec.class_name}")
                module = locals()
                
        except ImportError as e:
            self.logger.error(f"Failed to import {spec.class_name} from {spec.import_path}: {e}")
            raise ConfigurationError(f"Component import failed: {e}", {"component_type": component_type})
        
        # Create component with init kwargs
        try:
            # Merge spec init_kwargs with runtime kwargs
            init_kwargs = {**spec.init_kwargs, **kwargs}
            
            # Create the component
            if hasattr(module, spec.class_name):
                component_class = getattr(module, spec.class_name)
            else:
                # Fallback for dynamic imports
                component_class = getattr(module, spec.class_name)
            
            component = component_class(**init_kwargs)
            
        except Exception as e:
            self.logger.error(f"Failed to create {spec.class_name}: {e}")
            raise ConfigurationError(f"Component creation failed: {e}", {"component_type": component_type})
        
        # CONSOLIDATED: Unified dependency injection
        self._inject_dependencies(component, spec.dependency_mappings)
        
        self.logger.debug(f"Created {spec.class_name} for type {component_type}")
        return component
    
    def _inject_dependencies(self, component: Any, dependency_mappings: Dict[str, str]):
        """
        CONSOLIDATED: Unified dependency injection logic.
        Eliminates duplicate injection patterns across all factories.
        """
        for component_attr, dependency_key in dependency_mappings.items():
            if hasattr(self.dependencies, dependency_key):
                dependency_value = getattr(self.dependencies, dependency_key)
                setattr(component, component_attr, dependency_value)
                self.logger.debug(f"Injected {dependency_key} -> {component_attr}")
    
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
    """
    Factory for creating file processors and processing components.
    
    CONSOLIDATED: Uses unified component creation system.
    """
    
    def _get_component_specs(self) -> Dict[str, ComponentCreationSpec]:
        """
        CONSOLIDATED: Component specifications eliminate duplicate creation logic.
        """
        return {
            ComponentType.EXTRACTOR.value: ComponentCreationSpec(
                import_path="..postman.postman_extractors",
                class_name="MDXExtractor",
                dependency_mappings={
                    'config': 'config',
                    'validation_manager': 'validation_manager'
                }
            ),
            ComponentType.DEDUPLICATOR.value: ComponentCreationSpec(
                import_path=".deduplicator",
                class_name="ExampleDeduplicator",
                dependency_mappings={}
            )
        }
    
    def get_supported_types(self) -> List[str]:
        """Get supported processor types."""
        return [
            ComponentType.EXTRACTOR.value,
            ComponentType.DEDUPLICATOR.value
        ]


class GeneratorFactory(ComponentFactory):
    """
    Factory for creating generators (Postman, OpenAPI, etc.).
    
    CONSOLIDATED: Uses unified component creation system.
    """
    
    def _get_component_specs(self) -> Dict[str, ComponentCreationSpec]:
        """
        CONSOLIDATED: Component specifications eliminate duplicate creation logic.
        """
        return {
            ComponentType.POSTMAN_GENERATOR.value: ComponentCreationSpec(
                import_path="..postman.postman_consolidated",
                class_name="PostmanCollectionGenerator",
                dependency_mappings={
                    'config': 'config',
                    'validation_manager': 'validation_manager'
                }
            ),
            ComponentType.OPENAPI_MANAGER.value: ComponentCreationSpec(
                import_path="..openapi.openapi_manager",
                class_name="OpenAPIManager",
                dependency_mappings={
                    'config': 'config',
                    'validation_manager': 'validation_manager'
                }
            ),
            ComponentType.METHOD_MAPPER.value: ComponentCreationSpec(
                import_path="..managers.method_mapping_manager",
                class_name="MethodMappingManager",
                dependency_mappings={
                    'config': 'config'
                }
            )
        }
    
    def get_supported_types(self) -> List[str]:
        """Get supported generator types."""
        return [
            ComponentType.POSTMAN_GENERATOR.value,
            ComponentType.OPENAPI_MANAGER.value,
            ComponentType.METHOD_MAPPER.value
        ]


class UtilityFactory(ComponentFactory):
    """
    Factory for creating utility components.
    
    CONSOLIDATED: Uses unified component creation system.
    """
    
    def _get_component_specs(self) -> Dict[str, ComponentCreationSpec]:
        """
        CONSOLIDATED: Component specifications eliminate duplicate creation logic.
        """
        return {
            ComponentType.VALIDATION_MANAGER.value: ComponentCreationSpec(
                import_path="..managers.validation_manager",
                class_name="ValidationManager",
                init_kwargs={'validation_level': ValidationLevel.NORMAL},  # Default level
                dependency_mappings={
                    'config': 'config'
                }
            )
        }
    
    def get_supported_types(self) -> List[str]:
        """Get supported utility types."""
        return [
            ComponentType.VALIDATION_MANAGER.value
        ]
    
    def create(self, component_type: str, **kwargs) -> Any:
        """
        Create utility component with validation level support.
        
        ENHANCED: Supports validation_level parameter for ValidationManager.
        """
        if component_type == ComponentType.VALIDATION_MANAGER.value:
            # Handle validation_level parameter specially
            validation_level = kwargs.get('validation_level', ValidationLevel.NORMAL)
            spec = self._component_specs[component_type]
            spec.init_kwargs['validation_level'] = validation_level
            
        return super().create(component_type, **kwargs)


class MasterFactory:
    """
    Master factory that coordinates all component factories.
    
    CONSOLIDATED: Simplified coordination logic using unified factory system.
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
        
        self.logger.debug("MasterFactory initialized with consolidated factory system")
    
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
        
        self.logger.debug(f"Created component {component_type} using unified factory system")
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
    
    def create_complete_pipeline(self, validation_level: ValidationLevel = ValidationLevel.NORMAL) -> Dict[str, Any]:
        """
        Create a complete processing pipeline with all components.
        
        CONSOLIDATED: Uses unified factory system for pipeline creation.
        """
        pipeline = {}
        
        try:
            # Create available components (skip disabled ones)
            available_components = [
                (ComponentType.METHOD_MAPPER.value, {}),
                (ComponentType.POSTMAN_GENERATOR.value, {}),
                (ComponentType.OPENAPI_MANAGER.value, {}),
                (ComponentType.VALIDATION_MANAGER.value, {'validation_level': validation_level}),
                (ComponentType.EXTRACTOR.value, {}),
                (ComponentType.DEDUPLICATOR.value, {})
            ]
            
            for component_type, create_kwargs in available_components:
                if component_type in self.factory_map:
                    pipeline[component_type.replace('_', '')] = self.create(component_type, **create_kwargs)
            
            self.logger.info(f"Created complete pipeline with {len(pipeline)} components using unified system")
            return pipeline
            
        except Exception as e:
            self.logger.error(f"Failed to create complete pipeline: {e}")
            raise ConfigurationError(f"Pipeline creation failed: {e}", {"component_count": len(pipeline)})


class DependencyInjector:
    """
    Dependency injection container for managing component dependencies.
    
    ENHANCED: Works with consolidated factory system.
    """
    
    def __init__(self):
        get_logger_func = get_logger
        self.logger = get_logger_func("dependency-injector") if callable(get_logger_func) else get_logger_func
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
        """
        Inject dependencies into a component.
        
        ENHANCED: Integrates with consolidated factory system.
        """
        for attr_name, interface in dependencies.items():
            dependency = self.get_dependency(interface)
            setattr(component, attr_name, dependency)
            self.logger.debug(f"Injected {interface.__name__} -> {attr_name}")


# CONSOLIDATED: Simplified convenience functions that use unified factory system
_master_factory: Optional[MasterFactory] = None
_dependency_injector: Optional[DependencyInjector] = None


def get_master_factory(dependencies: ComponentDependencies = None) -> MasterFactory:
    """Get or create master factory instance."""
    global _master_factory
    if _master_factory is None:
        _master_factory = MasterFactory(dependencies)
    return _master_factory


def get_dependency_injector() -> DependencyInjector:
    """Get or create dependency injector instance."""
    global _dependency_injector
    if _dependency_injector is None:
        _dependency_injector = DependencyInjector()
    return _dependency_injector


# CONSOLIDATED: Simplified convenience functions eliminate duplicate factory logic
def create_postman_generator() -> Any:
    """Create Postman generator using unified factory system."""
    return get_master_factory().create(ComponentType.POSTMAN_GENERATOR.value)


def create_method_mapper() -> Any:
    """Create method mapper using unified factory system."""
    return get_master_factory().create(ComponentType.METHOD_MAPPER.value)


def create_complete_pipeline(validation_level: ValidationLevel = ValidationLevel.NORMAL) -> Dict[str, Any]:
    """Create complete pipeline using unified factory system."""
    return get_master_factory().create_complete_pipeline(validation_level)


def reset_factories():
    """Reset all factory instances."""
    global _master_factory, _dependency_injector
    if _master_factory:
        _master_factory.clear_all_instances()
    _master_factory = None
    _dependency_injector = None
