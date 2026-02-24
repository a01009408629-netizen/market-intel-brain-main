"""
Dynamic Adapter Orchestrator - Example Usage

This file demonstrates how to use the dynamic adapter orchestrator system
with automatic discovery, registration, and plug-and-play functionality.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from orchestrator import AdapterOrchestrator, register_adapter, get_global_orchestrator


# Example adapter classes for demonstration
@register_adapter('demo_provider', version='1.0', type='demo', description='Demo provider for testing')
class DemoAdapter:
    """Example adapter for demonstration purposes."""
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key
        self.name = "DemoAdapter"
        self.initialized = True
    
    def fetch_data(self, symbol: str):
        """Mock data fetching."""
        return {"symbol": symbol, "data": f"Mock data from {self.name}"}
    
    def test_connection(self):
        """Test connection method."""
        return True


@register_adapter('financial_provider', version='2.0', type='financial', description='Financial data provider')
class FinancialAdapter:
    """Example financial data adapter."""
    
    def __init__(self, api_key: str = None, base_url: str = None, **kwargs):
        self.api_key = api_key
        self.base_url = base_url or "https://api.example.com"
        self.name = "FinancialAdapter"
    
    def get_stock_data(self, symbol: str):
        """Mock stock data fetching."""
        return {
            "symbol": symbol,
            "price": 100.0,
            "volume": 1000000,
            "provider": self.name
        }
    
    def health_check(self):
        """Health check method."""
        return {"status": "healthy", "provider": self.name}


@register_adapter('news_provider', version='1.5', type='news', description='News data provider')
class NewsAdapter:
    """Example news data adapter."""
    
    def __init__(self, api_key: str = None, **kwargs):
        self.api_key = api_key
        self.name = "NewsAdapter"
    
    async def get_news(self, query: str):
        """Mock news fetching (async)."""
        await asyncio.sleep(0.1)  # Simulate async operation
        return {
            "query": query,
            "articles": [
                {"title": f"News about {query}", "source": self.name}
            ],
            "provider": self.name
        }


def demonstrate_basic_usage():
    """Demonstrate basic orchestrator usage."""
    print("=== Basic Orchestrator Usage ===\n")
    
    # Create orchestrator instance
    orchestrator = AdapterOrchestrator(auto_load=False)
    
    # Manually register some adapters (in real usage, they'd be auto-discovered)
    orchestrator.register_adapter('manual_provider', DemoAdapter, version='1.0')
    
    # Load adapters
    print("1. Loading adapters...")
    load_results = orchestrator.load_adapters()
    print(f"   ✓ Loaded {load_results.get('total_adapters_registered', 0)} adapters")
    
    # List available adapters
    print("\n2. Available adapters:")
    adapters = orchestrator.list_available_adapters()
    for adapter in adapters:
        print(f"   - {adapter}")
    
    # Get adapter info
    print("\n3. Adapter information:")
    for adapter_name in adapters[:2]:  # Show first 2
        info = orchestrator.get_adapter_info(adapter_name)
        if info:
            print(f"   {adapter_name}:")
            print(f"     Class: {info.get('class_name')}")
            print(f"     Module: {info.get('module')}")
            print(f"     Version: {info.get('version', 'N/A')}")
            print(f"     Type: {info.get('type', 'N/A')}")
    
    # Create adapter instances
    print("\n4. Creating adapter instances:")
    try:
        demo_adapter = orchestrator.get_adapter('demo_provider', api_key='test_key')
        print(f"   ✓ Created {demo_adapter.name}")
        
        financial_adapter = orchestrator.get_adapter('financial_provider', api_key='finance_key')
        print(f"   ✓ Created {financial_adapter.name}")
        
    except Exception as e:
        print(f"   ✗ Error creating adapters: {e}")


def demonstrate_plug_and_play():
    """Demonstrate plug-and-play functionality."""
    print("\n=== Plug-and-Play Demonstration ===\n")
    
    # Create a new adapter file dynamically
    new_adapter_content = '''
from orchestrator import register_adapter

@register_adapter('dynamic_provider', version='1.0', type='dynamic', description='Dynamically created provider')
class DynamicAdapter:
    """Adapter created at runtime."""
    
    def __init__(self, **kwargs):
        self.name = "DynamicAdapter"
        self.created_at = "runtime"
    
    def get_data(self):
        return {"message": "Hello from dynamic adapter!"}
'''
    
    # Create temporary adapters directory if it doesn't exist
    adapters_dir = Path("temp_adapters")
    adapters_dir.mkdir(exist_ok=True)
    
    # Write the new adapter file
    new_adapter_file = adapters_dir / "dynamic_adapter.py"
    with open(new_adapter_file, 'w') as f:
        f.write(new_adapter_content)
    
    print("1. Created new adapter file:")
    print(f"   {new_adapter_file}")
    
    try:
        # Create orchestrator with the new adapters directory
        orchestrator = AdapterOrchestrator(
            adapters_directory=str(adapters_dir),
            auto_load=True
        )
        
        print("\n2. Auto-loaded adapters:")
        adapters = orchestrator.list_available_adapters()
        for adapter in adapters:
            print(f"   - {adapter}")
        
        # Use the dynamically loaded adapter
        if 'dynamic_provider' in adapters:
            print("\n3. Using dynamically loaded adapter:")
            dynamic_adapter = orchestrator.get_adapter('dynamic_provider')
            data = dynamic_adapter.get_data()
            print(f"   ✓ Data: {data}")
        
    finally:
        # Clean up
        if new_adapter_file.exists():
            new_adapter_file.unlink()
        if adapters_dir.exists():
            adapters_dir.rmdir()
        print("\n4. Cleaned up temporary files")


def demonstrate_validation_and_testing():
    """Demonstrate adapter validation and testing."""
    print("\n=== Adapter Validation and Testing ===\n")
    
    orchestrator = AdapterOrchestrator(auto_load=True)
    
    # Test adapter validation
    print("1. Validating adapters:")
    adapters = orchestrator.list_available_adapters()
    
    for adapter_name in adapters[:3]:  # Test first 3 adapters
        validation_result = orchestrator.validate_adapter(adapter_name)
        status = "✓" if validation_result['valid'] else "✗"
        print(f"   {status} {adapter_name}: {validation_result.get('error', 'Valid')}")
    
    # Search adapters
    print("\n2. Searching adapters:")
    search_results = orchestrator.search_adapters('demo')
    print(f"   Search 'demo': {search_results}")
    
    search_results = orchestrator.search_adapters('financial')
    print(f"   Search 'financial': {search_results}")
    
    # Get adapters by type
    print("\n3. Adapters by type:")
    demo_adapters = orchestrator.get_adapters_by_type('demo')
    print(f"   Demo adapters: {demo_adapters}")
    
    financial_adapters = orchestrator.get_adapters_by_type('financial')
    print(f"   Financial adapters: {financial_adapters}")


async def demonstrate_async_testing():
    """Demonstrate async adapter testing."""
    print("\n=== Async Adapter Testing ===\n")
    
    orchestrator = AdapterOrchestrator(auto_load=True)
    
    # Test adapters asynchronously
    print("1. Async testing adapters:")
    adapters = orchestrator.list_available_adapters()
    
    for adapter_name in adapters[:3]:  # Test first 3
        test_result = await orchestrator.test_adapter_async(adapter_name)
        status = "✓" if test_result['test_passed'] else "✗"
        exec_time = test_result.get('execution_time', 0)
        print(f"   {status} {adapter_name}: {exec_time:.3f}s")
        if test_result.get('error'):
            print(f"     Error: {test_result['error']}")
        if test_result.get('tested_method'):
            print(f"     Tested method: {test_result['tested_method']}")


def demonstrate_global_orchestrator():
    """Demonstrate global orchestrator usage."""
    print("\n=== Global Orchestrator ===\n")
    
    # Get global orchestrator instance
    orchestrator = get_global_orchestrator(auto_load=True)
    
    print("1. Global orchestrator status:")
    status = orchestrator.get_orchestrator_status()
    print(f"   Loaded: {status['loaded']}")
    print(f"   Adapters directory: {status['adapters_directory']}")
    print(f"   Total adapters: {status['registry_info']['adapter_count']}")
    
    # Use global orchestrator
    print("\n2. Using global orchestrator:")
    adapters = orchestrator.list_available_adapters()
    print(f"   Available adapters: {len(adapters)}")
    
    # Get another instance (should be the same)
    orchestrator2 = get_global_orchestrator()
    print(f"\n3. Same instance: {orchestrator is orchestrator2}")


def demonstrate_error_handling():
    """Demonstrate error handling."""
    print("\n=== Error Handling ===\n")
    
    orchestrator = AdapterOrchestrator(auto_load=True)
    
    # Test getting non-existent adapter
    print("1. Getting non-existent adapter:")
    try:
        adapter = orchestrator.get_adapter('non_existent_provider')
        print("   ✗ Unexpected success")
    except Exception as e:
        print(f"   ✓ Expected error: {type(e).__name__}: {e}")
    
    # Test invalid adapter registration
    print("\n2. Invalid adapter registration:")
    try:
        orchestrator.register_adapter('invalid', "not_a_class")
        print("   ✗ Unexpected success")
    except Exception as e:
        print(f"   ✓ Expected error: {type(e).__name__}: {e}")
    
    # Test adapter validation with bad parameters
    print("\n3. Adapter validation with bad parameters:")
    validation_result = orchestrator.validate_adapter('demo_provider', invalid_param='test')
    print(f"   Result: {validation_result}")


def demonstrate_registry_operations():
    """Demonstrate registry operations."""
    print("\n=== Registry Operations ===\n")
    
    orchestrator = AdapterOrchestrator(auto_load=True)
    
    # Manual registration
    print("1. Manual adapter registration:")
    orchestrator.register_adapter(
        'manual_test', 
        DemoAdapter, 
        version='1.0',
        description='Manually registered for testing'
    )
    print(f"   ✓ Registered 'manual_test'")
    
    # Check registration
    is_registered = orchestrator.is_adapter_available('manual_test')
    print(f"   Is registered: {is_registered}")
    
    # Get adapter class without instantiation
    adapter_class = orchestrator.get_adapter_class('manual_test')
    print(f"   Adapter class: {adapter_class}")
    
    # Unregister adapter
    print("\n2. Unregistering adapter:")
    success = orchestrator.unregister_adapter('manual_test')
    print(f"   Unregistered: {success}")
    
    is_registered = orchestrator.is_adapter_available('manual_test')
    print(f"   Is still registered: {is_registered}")


async def main():
    """Run all demonstrations."""
    print("Dynamic Adapter Orchestrator - Complete Demonstration")
    print("=" * 60)
    
    try:
        demonstrate_basic_usage()
        demonstrate_plug_and_play()
        demonstrate_validation_and_testing()
        await demonstrate_async_testing()
        demonstrate_global_orchestrator()
        demonstrate_error_handling()
        demonstrate_registry_operations()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Singleton registry pattern")
        print("✓ @register_adapter decorator")
        print("✓ Dynamic loading with importlib")
        print("✓ Plug-and-play functionality")
        print("✓ Automatic adapter discovery")
        print("✓ Runtime adapter management")
        print("✓ Error handling and validation")
        print("✓ Async testing capabilities")
        print("✓ Global orchestrator instance")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
