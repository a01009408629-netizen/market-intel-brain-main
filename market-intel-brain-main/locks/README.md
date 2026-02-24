# Distributed Lock Manager (DLM) - Redlock Implementation

A robust distributed locking system implementing the Redlock algorithm with Redis to prevent cache stampede and ensure safe distributed operations with automatic deadlock prevention.

## 🚀 **Core Features**

### **🔒 Redlock Algorithm**
- Distributed locking across multiple Redis instances
- Quorum-based consistency (majority of nodes)
- Automatic lock expiration to prevent deadlocks
- Clock drift compensation

### **🛡️ Cache Stampede Protection**
- Only one process refreshes data when cache expires
- Other processes either wait or receive stale data
- Configurable timeout and stale data fallback
- Seamless SWR (Stale-While-Revalidate) integration

### **⚡ Auto-Release TTL**
- Automatic lock expiration prevents deadlocks
- Configurable TTL for different use cases
- Lock extension support for long-running operations
- Worker crash protection

### **🎯 Context Manager Support**
- `async with get_lock(...)` syntax
- Automatic lock acquisition and release
- Error handling and cleanup
- Stale data access when lock unavailable

## 📁 **Structure**

```
locks/
├── __init__.py              # Main exports and global manager
├── exceptions.py            # Custom lock exceptions
├── redlock.py              # Redlock algorithm implementation
├── manager.py              # High-level lock management
├── example_usage.py        # Comprehensive examples
├── requirements.txt        # Dependencies
└── README.md             # This file
```

## 🔧 **Installation**

```bash
pip install -r requirements.txt
```

## 💡 **Quick Start**

### **Basic Usage**

```python
from locks import get_lock

# Simple distributed lock
async with get_lock("my_resource", timeout=5.0) as lock_wrapper:
    if lock_wrapper.has_lock():
        # Only one process can execute this at a time
        data = await fetch_expensive_data()
        process_data(data)
    else:
        # Lock not acquired, got stale data instead
        stale_data = lock_wrapper.get_stale_data()
        process_stale_data(stale_data)
```

### **Cache Stampede Protection**

```python
from locks import LockManager

manager = LockManager()

# Protect expensive data fetching
result = await manager.protect_cache_stampede(
    cache_key="user_profile_123",
    data_fetcher=fetch_user_profile,
    "123",
    timeout=3.0,
    return_stale=True
)
```

### **Decorator Usage**

```python
from locks import distributed_lock, cache_stampede_protect

@distributed_lock("critical_operation_{user_id}", timeout=5.0)
async def critical_operation(user_id: int, data: dict):
    # Only one operation per user at a time
    return await process_user_data(user_id, data)

@cache_stampede_protect("expensive_query_{symbol}")
async def expensive_stock_query(symbol: str):
    # Prevent multiple concurrent queries for same symbol
    return await fetch_stock_data(symbol)
```

## 🏗️ **Architecture Overview**

### **Redlock Algorithm**

The Redlock algorithm ensures distributed locking safety:

1. **Acquire Lock**: Try to acquire lock on majority of Redis nodes
2. **Quorum Check**: Success if majority of nodes grant lock
3. **Auto-Release**: Lock expires automatically after TTL
4. **Safe Release**: Only lock owner can release using Lua script

```python
# Redlock acquisition flow
1. Generate unique lock identifier
2. Try SET with NX and PX on all Redis nodes
3. Check if majority (quorum) succeeded
4. Apply clock drift safety margin
5. Return lock info if quorum achieved
```

### **Cache Stampede Prevention**

```python
# Cache stampede protection flow
1. Check if lock can be acquired
2. If YES: Acquire lock, fetch fresh data, cache result
3. If NO: Return stale data (if available) or wait
4. Auto-release lock after TTL
```

## 🎯 **Advanced Usage**

### **Custom Lock Manager**

```python
from locks import LockManager

manager = LockManager(
    redis_nodes=[
        "redis://node1:6379",
        "redis://node2:6379", 
        "redis://node3:6379"
    ],
    default_ttl=30000,      # 30 seconds
    default_timeout=5.0,     # 5 seconds
    retry_delay=0.1,         # 100ms
    max_retries=3
)
```

### **Lock with Stale Data Fallback**

```python
async with manager.get_lock(
    "user_data_123",
    timeout=2.0,
    return_stale=True,
    stale_ttl=60  # Accept stale data up to 1 minute old
) as lock_wrapper:
    
    if lock_wrapper.has_lock():
        # Fresh data fetch
        fresh_data = await fetch_user_data("123")
        return fresh_data
    else:
        # Stale data fallback
        return lock_wrapper.get_stale_data()
```

### **Lock Extension for Long Operations**

```python
async with manager.get_lock("long_task", ttl=5000) as lock_wrapper:
    if lock_wrapper.has_lock():
        # Extend lock if operation takes longer than expected
        await lock_wrapper.extend_lock(5000)  # Add 5 seconds
        
        # Continue with long operation
        result = await long_running_operation()
```

### **SWR Integration**

```python
# Stale-While-Revalidate pattern
async def swr_get_data(key: str):
    try:
        # Try to refresh with lock
        return await manager.refresh_with_lock(
            key=key,
            refresh_func=fetch_fresh_data,
            key,
            timeout=2.0
        )
    except LockAcquisitionError:
        # Return stale data if refresh fails
        return manager._get_stale_data(key, 300)
```

## 🔍 **Lock Information**

### **Lock Info Object**

```python
@dataclass
class LockInfo:
    name: str              # Lock name
    owner: str             # Unique owner identifier
    acquired_at: float      # Acquisition timestamp
    expires_at: float      # Expiration timestamp
    ttl: int              # TTL in milliseconds
    redis_nodes: List[str] # Redis node addresses
```

### **Lock Status Checking**

```python
# Check if lock is held
is_locked = await manager.is_locked("my_lock")

# Get lock owner
owner = await manager.get_lock_info("my_lock")

# Get manager statistics
stats = manager.get_statistics()
```

## 🛠️ **Configuration Options**

### **Redis Configuration**

```python
# Single Redis instance
manager = LockManager(redis_nodes=["redis://localhost:6379"])

# Multiple Redis instances (recommended for production)
manager = LockManager(redis_nodes=[
    "redis://node1:6379",
    "redis://node2:6379",
    "redis://node3:6379",
    "redis://node4:6379",
    "redis://node5:6379"
])
```

### **TTL and Timeout Settings**

```python
manager = LockManager(
    default_ttl=60000,      # 60 seconds default TTL
    default_timeout=10.0,    # 10 seconds acquisition timeout
    retry_delay=0.2,        # 200ms between retries
    max_retries=5,          # 5 retry attempts
    clock_drift_factor=0.01  # 1% clock drift margin
)
```

## 🚨 **Error Handling**

### **Exception Types**

```python
from locks import (
    LockError,
    LockAcquisitionError,
    LockTimeoutError,
    LockReleaseError,
    DeadlockError,
    LockOwnershipError,
    LockExpiredError
)

try:
    async with get_lock("my_lock") as lock_wrapper:
        # Your code here
        pass
except LockTimeoutError:
    print("Lock acquisition timed out")
except LockAcquisitionError:
    print("Failed to acquire lock")
except LockError as e:
    print(f"Lock error: {e}")
```

### **Graceful Degradation**

```python
async def safe_data_fetch(key: str):
    try:
        async with get_lock(key, timeout=2.0, return_stale=True) as lock_wrapper:
            if lock_wrapper.has_lock():
                return await fetch_fresh_data(key)
            else:
                # Use stale data if lock not available
                stale_data = lock_wrapper.get_stale_data()
                if stale_data:
                    return stale_data
                raise Exception("No data available")
    except LockTimeoutError:
        # Fallback to direct fetch (last resort)
        return await fetch_fresh_data(key)
```

## 🧪 **Testing**

### **Run Examples**

```bash
python example_usage.py
```

### **Unit Tests**

```python
import pytest
from locks import LockManager

@pytest.mark.asyncio
async def test_basic_locking():
    manager = LockManager()
    
    async with manager.get_lock("test_lock") as lock_wrapper:
        assert lock_wrapper.has_lock()
    
    # Lock should be released
    assert not await manager.is_locked("test_lock")
```

## 📊 **Monitoring and Statistics**

### **Lock Manager Statistics**

```python
stats = manager.get_statistics()
print(f"Stale cache size: {stats['stale_data_cache_size']}")
print(f"Default TTL: {stats['default_ttl']}")
print(f"Redis nodes: {stats['redis_nodes']}")
print(f"Quorum: {stats['quorum']}")
```

### **Lock Monitoring**

```python
# Monitor lock acquisition
async def monitor_locks():
    while True:
        stats = manager.get_statistics()
        print(f"Active locks: {len([k for k in manager.redlock.redis_clients])}")
        await asyncio.sleep(10)
```

## 🔧 **Best Practices**

### **1. Lock Naming**

```python
# ✅ Good: Descriptive and specific
"user_profile_update_123"
"cache_refresh_financial_data_AAPL"
"order_processing_order_456"

# ❌ Avoid: Generic names
"lock1"
"resource"
"data_lock"
```

### **2. TTL Configuration**

```python
# ✅ Appropriate TTL for different operations
short_ttl = 5000      # 5 seconds for cache refresh
medium_ttl = 30000    # 30 seconds for API calls
long_ttl = 300000     # 5 minutes for batch processing

# ❌ Avoid: Too short or too long TTL
too_short = 100       # 100ms - may expire before operation completes
too_long = 3600000    # 1 hour - long deadlock if process crashes
```

### **3. Error Handling**

```python
# ✅ Good: Comprehensive error handling
async def robust_operation():
    try:
        async with get_lock("operation", timeout=5.0) as lock_wrapper:
            if lock_wrapper.has_lock():
                return await perform_operation()
            else:
                return await fallback_operation()
    except LockTimeoutError:
        return await timeout_fallback()
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        raise
```

### **4. Stale Data Strategy**

```python
# ✅ Good: Configurable stale data handling
async with get_lock(
    "data_key",
    timeout=2.0,
    return_stale=True,
    stale_ttl=300  # 5 minutes
) as lock_wrapper:
    
    if lock_wrapper.has_lock():
        fresh_data = await fetch_fresh_data()
        return fresh_data
    else:
        stale_data = lock_wrapper.get_stale_data()
        if is_stale_acceptable(stale_data):
            return stale_data
        else:
            raise Exception("Stale data not acceptable")
```

## 🔄 **Integration with Caching Systems**

### **Tiered Cache Integration**

```python
from caches import TieredCacheManager
from locks import LockManager

cache = TieredCacheManager()
lock_manager = LockManager()

async def get_data_with_protection(key: str):
    # Try cache first
    cached_data = await cache.get(key)
    if cached_data:
        return cached_data
    
    # Protect against stampede
    return await lock_manager.protect_cache_stampede(
        cache_key=key,
        data_fetcher=fetch_from_source,
        key
    )
```

### **SWR Pattern**

```python
async def swr_get(key: str):
    # Get from cache (may be stale)
    cached_data = await cache.get(key)
    
    if cached_data and is_stale(cached_data):
        # Trigger background refresh with lock
        asyncio.create_task(
            lock_manager.refresh_with_lock(
                key=key,
                refresh_func=refresh_data,
                key
            )
        )
        # Return stale data immediately
        return cached_data
    
    return cached_data or await fetch_fresh_data(key)
```

## 📈 **Performance Considerations**

### **Redis Configuration**

```python
# Production Redis settings
redis_nodes = [
    "redis://node1:6379?socket_timeout=2&socket_connect_timeout=2",
    "redis://node2:6379?socket_timeout=2&socket_connect_timeout=2",
    "redis://node3:6379?socket_timeout=2&socket_connect_timeout=2"
]
```

### **Lock Granularity**

```python
# ✅ Good: Fine-grained locks
"cache_refresh_user_123_profile"
"cache_refresh_user_123_orders"
"cache_refresh_user_123_preferences"

# ❌ Avoid: Coarse-grained locks
"cache_refresh_user_123"  # Blocks all user operations
"cache_refresh_all_users"  # Blocks entire system
```

## 🚨 **Production Deployment**

### **Redis Cluster Setup**

```bash
# Multiple Redis instances for Redlock
redis-server --port 6379 --bind 0.0.0.0
redis-server --port 6380 --bind 0.0.0.0
redis-server --port 6381 --bind 0.0.0.0
redis-server --port 6382 --bind 0.0.0.0
redis-server --port 6383 --bind 0.0.0.0
```

### **Monitoring**

```python
# Health check for lock system
async def health_check():
    try:
        # Test lock acquisition
        async with get_lock("health_check", timeout=1.0) as lock_wrapper:
            return lock_wrapper.has_lock()
    except Exception:
        return False
```

## 📚 **Dependencies**

- **redis[asyncio]>=4.5.0** - Redis async client
- **Python 3.8+** - For async/await support

## 🤝 **Contributing**

When contributing to the distributed lock manager:

1. **Test thoroughly** with multiple Redis instances
2. **Handle edge cases** (network failures, timeouts)
3. **Consider clock drift** in distributed systems
4. **Test deadlock scenarios**
5. **Validate quorum logic**

## 📄 **License**

This distributed lock manager is part of the Market Intel Brain project.
