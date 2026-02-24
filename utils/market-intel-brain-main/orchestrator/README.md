# Dynamic Adapter Orchestrator

A sophisticated plug-and-play system for managing data source adapters with automatic discovery, registration, and dynamic loading capabilities. Built with Singleton pattern and decorator-based registration.

## 🚀 **Core Features**

### **🔌 Plug-and-Play Architecture**
- Drop new adapter files in the `adapters/` directory
- Automatic discovery and registration on startup
- No code changes required to add new adapters
- Runtime adapter management

### **🏗️ Singleton Registry Pattern**
- Thread-safe Singleton implementation
- Global adapter registry accessible throughout the application
- Consistent state management across modules

### **🎯 Decorator-Based Registration**
- Simple `@register_adapter('provider_name')` decorator
- Automatic registration on module import
- Metadata support for adapter categorization

### **⚡ Dynamic Loading**
- Uses `importlib` for runtime module loading
- `inspect` for class discovery and validation
- Hot-reloading capabilities for development

## 📁 **Structure**

```
orchestrator/
├── __init__.py              # Main exports and global registry
├── registry.py              # Singleton registry with decorator
├── loader.py                # Dynamic adapter loading
├── orchestrator.py          # Main orchestration logic
├── example_usage.py         # Comprehensive examples
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## 🔧 **Installation**

```bash
pip install -r requirements.txt
```

## 💡 **Quick Start**

### **Basic Usage**

```python
from orchestrator import AdapterOrchestrator

# Create orchestrator (auto-loads adapters)
orchestrator = AdapterOrchestrator()

# List available adapters
adapters = orchestrator.list_available_adapters()
print(f"Available adapters: {adapters}")

# Get adapter instance
adapter = orchestrator.get_adapter('my_provider', api_key='your_key')
data = adapter.fetch_data('AAPL')
```

### **Creating Adapters**

```python
# adapters/my_provider.py
from orchestrator import register_adapter

@register_adapter('my_provider', version='1.0', type='financial')
class MyProviderAdapter:
    """My custom data provider."""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.base_url = "https://api.myprovider.com"
    
    def fetch_data(self, symbol: str):
        # Implementation here
        return {"symbol": symbol, "data": "..."}
```

### **Plug-and-Play**

1. **Create adapter file** in `adapters/` directory
2. **Use decorator** to register the adapter
3. **Drop the file** - no other changes needed!
4. **Adapter is automatically** discovered and loaded

## 🏛️ **Architecture Overview**

### **Registry (Singleton Pattern)**

```python
from orchestrator import AdapterRegistry, register_adapter

# Global singleton instance
registry = AdapterRegistry()

# Decorator registration
@register_adapter('provider_name', version='1.0', type='financial')
class MyAdapter:
    pass

# Manual registration
registry.register('manual_provider', MyAdapter, version='1.0')
```

### **Dynamic Loading**

```python
from orchestrator import AdapterLoader

# Auto-discover and load adapters
loader = AdapterLoader("adapters/")
results = loader.load_all_adapters()

print(f"Loaded {results['total_adapters_registered']} adapters")
```

### **Orchestration**

```python
from orchestrator import AdapterOrchestrator

# Complete orchestration system
orchestrator = AdapterOrchestrator(
    adapters_directory="adapters/",
    auto_load=True
)

# Runtime management
adapter = orchestrator.get_adapter('provider_name')
info = orchestrator.get_adapter_info('provider_name')
orchestrator.reload_adapter('provider_name')
```

## 🎯 **Advanced Usage**

### **Custom Adapter Directory**

```python
orchestrator = AdapterOrchestrator(
    adapters_directory="/path/to/my/adapters",
    auto_load=True
)
```

### **Manual Adapter Registration**

```python
# Register adapter at runtime
orchestrator.register_adapter(
    'runtime_provider',
    MyAdapterClass,
    version='2.0',
    description='Registered at runtime'
)
```

### **Adapter Validation**

```python
# Validate adapter before use
validation_result = orchestrator.validate_adapter('provider_name')
if validation_result['valid']:
    adapter = orchestrator.get_adapter('provider_name')
```

### **Async Testing**

```python
# Test adapters asynchronously
result = await orchestrator.test_adapter_async('provider_name')
if result['test_passed']:
    print(f"Adapter tested in {result['execution_time']:.3f}s")
```

### **Search and Filter**

```python
# Search adapters
results = orchestrator.search_adapters('financial')

# Filter by type
financial_adapters = orchestrator.get_adapters_by_type('financial')
```

## 🔍 **Adapter Metadata**

The decorator supports rich metadata:

```python
@register_adapter(
    'advanced_provider',
    version='2.1.0',
    type='financial',
    description='Advanced financial data provider',
    author='Your Name',
    tags=['stocks', 'real-time', 'api'],
    requires_auth=True,
    rate_limit=1000
)
class AdvancedProvider:
    pass
```

### **Accessing Metadata**

```python
# Get adapter metadata
metadata = orchestrator.get_adapter_info('advanced_provider')
print(f"Version: {metadata['version']}")
print(f"Type: {metadata['type']}")
print(f"Author: {metadata['author']}")
```

## 🔄 **Hot Reloading**

### **Reload Single Adapter**

```python
# Reload specific adapter
result = orchestrator.reload_adapter('my_provider')
if result['success']:
    print("Adapter reloaded successfully")
```

### **Reload All Adapters**

```python
# Reload all adapters
results = orchestrator.reload_all_adapters()
print(f"Reloaded {results['total_adapters_registered']} adapters")
```

## 🌐 **Global Orchestrator**

### **Easy Access**

```python
from orchestrator import get_global_orchestrator

# Get global instance (creates if needed)
orchestrator = get_global_orchestrator()

# Same instance across modules
adapter = orchestrator.get_adapter('provider_name')
```

### **Reset Global Instance**

```python
from orchestrator import reset_global_orchestrator

# Reset global instance (useful for testing)
reset_global_orchestrator()
```

## 🛠️ **Development Workflow**

### **1. Create New Adapter**

```python
# adapters/new_provider.py
from orchestrator import register_adapter

@register_adapter('new_provider', version='1.0', type='custom')
class NewProviderAdapter:
    def __init__(self, **kwargs):
        self.name = "NewProvider"
    
    def fetch_data(self, symbol):
        return {"symbol": symbol, "provider": self.name}
```

### **2. Drop File in Directory**

```bash
# Just drop the file - no other changes needed!
mv new_provider.py adapters/
```

### **3. Auto-Discovery**

```python
# Adapter is automatically available
orchestrator = AdapterOrchestrator()
adapter = orchestrator.get_adapter('new_provider')
```

## 📊 **Monitoring and Status**

### **Orchestrator Status**

```python
# Get comprehensive status
status = orchestrator.get_orchestrator_status()
print(f"Loaded: {status['loaded']}")
print(f"Adapters: {status['registry_info']['adapter_count']}")
print(f"Load time: {status['load_time']}")
```

### **Registry Information**

```python
# Detailed registry info
registry_info = orchestrator.registry.get_registry_info()
print(f"Total adapters: {registry_info['adapter_count']}")
print(f"Adapters: {registry_info['adapters']}")
```

## 🧪 **Testing**

### **Run Examples**

```bash
python example_usage.py
```

### **Run Tests**

```bash
pytest -v
```

### **Test Individual Components**

```python
# Test registry
from orchestrator import AdapterRegistry
registry = AdapterRegistry()
assert registry.get_adapter_count() == 0

# Test loader
from orchestrator import AdapterLoader
loader = AdapterLoader("adapters/")
results = loader.load_all_adapters()
assert results['total_modules_found'] > 0
```

## 🔧 **Configuration**

### **Environment Variables**

```python
import os
from orchestrator import AdapterOrchestrator

orchestrator = AdapterOrchestrator(
    adapters_directory=os.getenv('ADAPTERS_DIR', 'adapters'),
    auto_load=os.getenv('AUTO_LOAD', 'true').lower() == 'true'
)
```

### **Custom Registry**

```python
from orchestrator import AdapterRegistry, AdapterOrchestrator

# Use custom registry instance
custom_registry = AdapterRegistry()
orchestrator = AdapterOrchestrator(registry=custom_registry)
```

## 🚨 **Error Handling**

### **Common Errors**

```python
try:
    adapter = orchestrator.get_adapter('non_existent')
except AdapterNotFoundError as e:
    print(f"Adapter not found: {e}")

try:
    orchestrator.register_adapter('duplicate', MyAdapter)
except AdapterRegistrationError as e:
    print(f"Registration failed: {e}")
```

### **Validation Errors**

```python
validation_result = orchestrator.validate_adapter('provider_name')
if not validation_result['valid']:
    print(f"Validation failed: {validation_result['error']}")
```

## 🎯 **Best Practices**

### **1. Adapter Naming**

```python
# ✅ Good: descriptive names
@register_adapter('yahoo_finance', type='financial')
@register_adapter('alpha_vantage', type='financial')

# ❌ Avoid: generic names
@register_adapter('provider1')
@register_adapter('api_adapter')
```

### **2. Metadata Usage**

```python
# ✅ Good: rich metadata
@register_adapter(
    'my_provider',
    version='1.2.0',
    type='financial',
    description='Real-time stock data provider',
    author='Your Name',
    tags=['stocks', 'real-time'],
    requires_auth=True
)
```

### **3. Error Handling**

```python
@register_adapter('robust_provider')
class RobustProvider:
    def __init__(self, **kwargs):
        try:
            self.initialize()
        except Exception as e:
            raise AdapterInitializationError(f"Failed to initialize: {e}")
```

### **4. Async Support**

```python
@register_adapter('async_provider')
class AsyncProvider:
    async def fetch_data(self, symbol):
        # Async implementation
        return await self.api_call(symbol)
```

## 🔄 **Migration Guide**

### **From Manual Registration**

```python
# Old way
adapters = {
    'provider1': Provider1,
    'provider2': Provider2
}

# New way
@register_adapter('provider1')
class Provider1: pass

@register_adapter('provider2')
class Provider2: pass

orchestrator = AdapterOrchestrator()
```

## 📚 **Dependencies**

- **Python 3.8+** (for type annotations and async support)
- **Built-in modules only**: `importlib`, `inspect`, `threading`, `pathlib`
- **No external dependencies** required for core functionality

## 🤝 **Contributing**

When adding new adapters:

1. **Use the decorator**: `@register_adapter('name', metadata...)`
2. **Add metadata**: version, type, description
3. **Include docstrings**: Clear documentation
4. **Handle errors**: Proper exception handling
5. **Test thoroughly**: Include validation methods

## 📄 **License**

This orchestrator system is part of the Market Intel Brain project.
