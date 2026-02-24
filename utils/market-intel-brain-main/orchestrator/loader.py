"""
Dynamic Adapter Loader

This module provides automatic discovery and loading of adapter classes
from the adapters directory using importlib and inspect.
"""

import os
import importlib
import importlib.util
import inspect
import logging
from typing import List, Dict, Any, Optional, Type
from pathlib import Path

from .registry import AdapterRegistry


class AdapterLoader:
    """
    Dynamic loader for adapter classes.
    
    This class scans the adapters directory, automatically imports modules,
    and registers any adapter classes that use the @register_adapter decorator.
    """
    
    def __init__(self, adapters_directory: str = None, registry: AdapterRegistry = None):
        """
        Initialize the adapter loader.
        
        Args:
            adapters_directory: Path to the adapters directory
            registry: AdapterRegistry instance (uses global if None)
        """
        self.adapters_directory = adapters_directory or self._find_adapters_directory()
        self.registry = registry or AdapterRegistry()
        self.logger = logging.getLogger("AdapterLoader")
        
        self.logger.info(f"AdapterLoader initialized with directory: {self.adapters_directory}")
    
    def _find_adapters_directory(self) -> str:
        """
        Find the adapters directory automatically.
        
        Returns:
            Path to the adapters directory
            
        Raises:
            FileNotFoundError: If adapters directory cannot be found
        """
        # Try common locations
        possible_paths = [
            "adapters",
            "source_adapter/adapters",
            "services/data_ingestion/source_adapter/adapters",
            "market-intel-brain-main/services/data_ingestion/source_adapter/adapters"
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                return os.path.abspath(path)
        
        # Try relative to current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        relative_path = os.path.join(current_dir, "..", "services", "data_ingestion", "source_adapter", "adapters")
        if os.path.exists(relative_path) and os.path.isdir(relative_path):
            return os.path.abspath(relative_path)
        
        raise FileNotFoundError(
            "Could not find adapters directory. Please specify adapters_directory parameter."
        )
    
    def load_all_adapters(self) -> Dict[str, Any]:
        """
        Load all adapters from the adapters directory.
        
        Returns:
            Dictionary with loading results and statistics
        """
        self.logger.info("Starting to load all adapters...")
        
        results = {
            'loaded_adapters': [],
            'failed_modules': [],
            'total_modules_found': 0,
            'total_adapters_registered': 0,
            'errors': []
        }
        
        if not os.path.exists(self.adapters_directory):
            error_msg = f"Adapters directory not found: {self.adapters_directory}"
            self.logger.error(error_msg)
            results['errors'].append(error_msg)
            return results
        
        # Get all Python files in the adapters directory
        python_files = self._get_python_files()
        results['total_modules_found'] = len(python_files)
        
        self.logger.info(f"Found {len(python_files)} Python files to process")
        
        for file_path in python_files:
            try:
                module_result = self._load_module_from_file(file_path)
                if module_result['success']:
                    results['loaded_adapters'].append(module_result)
                    results['total_adapters_registered'] += module_result['adapters_found']
                else:
                    results['failed_modules'].append(module_result)
                    results['errors'].extend(module_result['errors'])
                    
            except Exception as e:
                error_info = {
                    'file': file_path,
                    'success': False,
                    'error': str(e),
                    'errors': [str(e)]
                }
                results['failed_modules'].append(error_info)
                results['errors'].append(f"Failed to load {file_path}: {e}")
                self.logger.error(f"Error loading {file_path}: {e}")
        
        # Log summary
        self.logger.info(
            f"Adapter loading completed: "
            f"{results['total_adapters_registered']} adapters registered from "
            f"{len(results['loaded_adapters'])} modules, "
            f"{len(results['failed_modules'])} modules failed"
        )
        
        return results
    
    def _get_python_files(self) -> List[str]:
        """
        Get all Python files in the adapters directory.
        
        Returns:
            List of Python file paths
        """
        python_files = []
        
        for file_name in os.listdir(self.adapters_directory):
            # Skip __init__.py and test files
            if (file_name.endswith('.py') and 
                not file_name.startswith('__') and 
                not file_name.startswith('test_')):
                
                file_path = os.path.join(self.adapters_directory, file_name)
                if os.path.isfile(file_path):
                    python_files.append(file_path)
        
        return sorted(python_files)
    
    def _load_module_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load a single module from file path.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Dictionary with loading result
        """
        result = {
            'file': file_path,
            'module_name': None,
            'success': False,
            'adapters_found': 0,
            'classes_found': [],
            'errors': []
        }
        
        try:
            # Get module name from file path
            module_name = self._get_module_name_from_path(file_path)
            result['module_name'] = module_name
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not create module spec for {file_path}")
            
            module = importlib.util.module_from_spec(spec)
            
            # Get adapter count before loading
            adapters_before = self.registry.get_adapter_count()
            
            # Execute the module (this triggers @register_adapter decorators)
            spec.loader.exec_module(module)
            
            # Get adapter count after loading
            adapters_after = self.registry.get_adapter_count()
            new_adapters = adapters_after - adapters_before
            
            result['success'] = True
            result['adapters_found'] = new_adapters
            result['classes_found'] = self._find_adapter_classes(module)
            
            self.logger.info(
                f"Successfully loaded {module_name}: "
                f"{new_adapters} adapters registered"
            )
            
        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Failed to load module {file_path}: {e}")
        
        return result
    
    def _get_module_name_from_path(self, file_path: str) -> str:
        """
        Generate a module name from file path.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Module name
        """
        file_name = os.path.basename(file_path)
        module_name = file_name[:-3]  # Remove .py extension
        
        # Add prefix to avoid conflicts
        return f"adapter_{module_name}"
    
    def _find_adapter_classes(self, module) -> List[str]:
        """
        Find all adapter classes in a module.
        
        Args:
            module: The loaded module
            
        Returns:
            List of class names
        """
        adapter_classes = []
        
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                obj.__module__ == module.__name__ and
                not name.startswith('_')):
                
                adapter_classes.append(name)
        
        return adapter_classes
    
    def reload_adapter(self, adapter_name: str) -> Dict[str, Any]:
        """
        Reload a specific adapter.
        
        Args:
            adapter_name: Name of the adapter to reload
            
        Returns:
            Dictionary with reload result
        """
        result = {
            'adapter_name': adapter_name,
            'success': False,
            'message': '',
            'old_count': 0,
            'new_count': 0
        }
        
        try:
            # Get current adapter count
            result['old_count'] = self.registry.get_adapter_count()
            
            # Find the module file for this adapter
            module_file = self._find_module_for_adapter(adapter_name)
            if not module_file:
                result['message'] = f"Could not find module file for adapter '{adapter_name}'"
                return result
            
            # Unregister the adapter
            self.registry.unregister(adapter_name)
            
            # Reload the module
            reload_result = self._load_module_from_file(module_file)
            
            if reload_result['success']:
                result['success'] = True
                result['message'] = f"Successfully reloaded adapter '{adapter_name}'"
                result['new_count'] = self.registry.get_adapter_count()
            else:
                result['message'] = f"Failed to reload module: {reload_result['errors']}"
            
        except Exception as e:
            result['message'] = f"Error reloading adapter: {e}"
            self.logger.error(f"Error reloading adapter '{adapter_name}': {e}")
        
        return result
    
    def _find_module_for_adapter(self, adapter_name: str) -> Optional[str]:
        """
        Find the module file for a specific adapter.
        
        Args:
            adapter_name: Name of the adapter
            
        Returns:
            Module file path or None if not found
        """
        # Get metadata for the adapter
        metadata = self.registry.get_metadata(adapter_name)
        if not metadata:
            return None
        
        module_name = metadata.get('module')
        if not module_name:
            return None
        
        # Find the corresponding file
        python_files = self._get_python_files()
        for file_path in python_files:
            file_module_name = self._get_module_name_from_path(file_path)
            if file_module_name == module_name:
                return file_path
        
        return None
    
    def load_single_adapter(self, file_path: str) -> Dict[str, Any]:
        """
        Load a single adapter file.
        
        Args:
            file_path: Path to the adapter file
            
        Returns:
            Dictionary with loading result
        """
        if not os.path.exists(file_path):
            return {
                'file': file_path,
                'success': False,
                'error': f"File not found: {file_path}"
            }
        
        return self._load_module_from_file(file_path)
    
    def get_loading_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about loaded adapters.
        
        Returns:
            Dictionary with loading statistics
        """
        registry_info = self.registry.get_registry_info()
        
        return {
            'adapters_directory': self.adapters_directory,
            'directory_exists': os.path.exists(self.adapters_directory),
            'registry_info': registry_info,
            'available_files': len(self._get_python_files()) if os.path.exists(self.adapters_directory) else 0
        }


class AdapterLoadError(Exception):
    """Custom exception for adapter loading errors."""
    pass


class AdapterNotFoundError(AdapterLoadError):
    """Raised when an adapter file cannot be found."""
    
    def __init__(self, file_path: str):
        super().__init__(f"Adapter file not found: {file_path}")
        self.file_path = file_path


class ModuleLoadError(AdapterLoadError):
    """Raised when a module fails to load."""
    
    def __init__(self, module_name: str, reason: str):
        super().__init__(f"Failed to load module '{module_name}': {reason}")
        self.module_name = module_name
        self.reason = reason
