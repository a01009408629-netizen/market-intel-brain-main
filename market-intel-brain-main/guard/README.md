# Schema Evolution Guard

A comprehensive schema evolution guard system using hashlib for fingerprinting and deepdiff for change detection, providing early warnings to developers without blocking operations.

## 🚀 **Core Features**

### **🔍 Schema Fingerprinting**
- **Hashlib-based fingerprinting** for unique schema identification
- **Configurable algorithms** (SHA256, MD5, SHA1, etc.)
- **Canonical JSON representation** for consistent hashing
- **Metadata extraction** (field count, depth, size)
- **Version tracking** and registry management

### **📊 Difference Analysis**
- **DeepDiff integration** for detailed change detection
- **Change categorization** (breaking/non-breaking/unknown)
- **Path-based change tracking** for precise field location
- **Type change detection** with semantic analysis
- **Export capabilities** (JSON, CSV, YAML)

### **🛡️ Schema Validation**
- **Configurable validation rules** and business logic
- **Custom interceptor framework** for domain-specific rules
- **Real-time validation** without blocking operations
- **Error and warning collection** with detailed reporting
- **Performance-optimized** validation pipeline

### **🚨 Alert System**
- **Multi-level alerts** (CRITICAL/ERROR/WARNING/INFO)
- **Callback registration** for custom alert handling
- **Configurable alert triggers** for different change types
- **Non-blocking operation** - system continues running
- **Early warning system** for proactive developer notification

## 📁 **Structure**

```
guard/
├── __init__.py              # Main exports and global instances
├── exceptions.py            # Custom guard exceptions
├── fingerprint.py          # Schema fingerprinting with hashlib
├── diff_analyzer.py         # DeepDiff-based difference analysis
├── schema_guard.py         # Main guard system with interceptors
├── example_usage.py         # Comprehensive examples
├── requirements.txt         # Dependencies
└── README.md              # This file
```

## 🔧 **Installation**

```bash
pip install -r requirements.txt
```

## 💡 **Quick Start**

### **Basic Schema Monitoring**

```python
from guard import get_guard

# Get global guard
guard = get_guard()
await guard.start()

# Monitor API response
result = await guard.monitor_api_response(
    provider="user_api",
    response_data=api_response
)

if not result.is_valid:
    print(f"Schema issues detected: {result.errors}")
```

### **Schema Validation**

```python
from guard import validate_schema_globally

# Validate schema against expected fingerprint
result = await validate_schema_globally(
    provider="user_api",
    schema_data=response_data
)

print(f"Validation: {result.is_valid}")
print(f"Fields: {result.field_count}")
```

### **Custom Interceptors**

```python
from guard import register_interceptor_globally

# Register custom interceptor
async def business_rules(provider, schema_data, fingerprint):
    # Custom validation logic
    if "email" in schema_data:
        email = schema_data["email"]
        if not email.endswith("@company.com"):
            return {"valid": False, "errors": ["Invalid email domain"]}
    
    return {"valid": True}

register_interceptor_globally(business_rules)
```

## 🏗️ **Architecture Overview**

### **Fingerprinting Process**

```python
# Create canonical JSON
canonical_json = json.dumps(
    data,
    sort_keys=True,
    separators=(',', ':'),
    ensure_ascii=True
)

# Generate hash
hash_value = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

# Create fingerprint with metadata
fingerprint = SchemaFingerprint(
    hash=hash_value,
    algorithm="sha256",
    timestamp=time.time(),
    schema_type="api_response",
    field_count=len(data.keys()),
    depth=max_depth(data),
    metadata={"data_size": len(str(data))}
)
```

### **Difference Analysis**

```python
# Use deepdiff for detailed comparison
diff = DeepDiff(old_schema, new_schema, 
    ignore_order=True,
    verbose_level=1)

# Convert to our format
changes = convert_deepdiff_to_changes(diff)

# Categorize changes
categorized = {
    "breaking": [c for c in changes if is_breaking(c)],
    "non_breaking": [c for c in changes if not is_breaking(c)],
    "unknown": [c for c in changes if is_unknown(c)]
}
```

### **Interceptor Framework**

```python
# Guard calls interceptors before validation
for interceptor in interceptors:
    result = await interceptor(provider, schema_data, fingerprint)
    if not result.get("valid", True):
        errors.extend(result.get("errors", []))
        warnings.extend(result.get("warnings", []))
```

## 🎯 **Advanced Usage**

### **Custom Configuration**

```python
from guard import GuardConfig, SchemaGuard

config = GuardConfig(
    enable_validation=True,
    enable_fingerprinting=True,
    enable_diff_analysis=True,
    enable_alerting=True,
    enable_interception=True,
    alert_on_new_fields=True,
    alert_on_removed_fields=True,
    alert_on_type_changes=True,
    alert_on_breaking_changes=True,
    storage_backend="redis",
    redis_url="redis://localhost:6379"
)

guard = SchemaGuard(config)
```

### **Alert Callbacks**

```python
from guard import AlertLevel

def critical_handler(provider, level, message, diff_result):
    """Handle critical schema changes."""
    print(f"CRITICAL: {message}")
    # Send to PagerDuty, Slack, etc.
    # Create JIRA ticket
    # Notify development team

def warning_handler(provider, level, message, diff_result):
    """Handle non-breaking schema changes."""
    print(f"WARNING: {message}")
    # Log to monitoring system
    # Create GitHub issue
    # Schedule developer review

guard.register_alert_callback(AlertLevel.CRITICAL, critical_handler)
guard.register_alert_callback(AlertLevel.WARNING, warning_handler)
```

### **Schema Registry**

```python
# Get provider status
status = await guard.get_provider_status("user_api")

print(f"Provider: {status['provider']}")
print(f"Monitored: {status['monitored']}")
print(f"Current version: {status['current_version']}")
print(f"Available versions: {status['available_versions']}")
```

## 📊 **Configuration Options**

### **GuardConfig**

```python
config = GuardConfig(
    enable_validation=True,              # Enable schema validation
    enable_fingerprinting=True,           # Enable fingerprinting
    enable_diff_analysis=True,            # Enable diff analysis
    enable_alerting=True,                # Enable alert system
    enable_interception=True,             # Enable interceptors
    alert_on_new_fields=True,            # Alert on new fields
    alert_on_removed_fields=True,         # Alert on removed fields
    alert_on_type_changes=True,           # Alert on type changes
    alert_on_breaking_changes=True,        # Alert on breaking changes
    log_level="INFO",                   # Logging level
    storage_backend="memory",              # "memory" or "redis"
    redis_url="redis://localhost:6379",   # Redis connection URL
    max_stored_versions=10               # Max versions to store
)
```

### **Fingerprinting Configuration**

```python
from guard import FingerprintConfig

config = FingerprintConfig(
    hash_algorithm="sha256",              # Hash algorithm
    include_metadata=True,                 # Include metadata
    include_types=True,                    # Include type information
    include_nulls=False,                   # Include null values
    sort_keys=True,                       # Sort keys for canonical form
    normalize_whitespace=True,              # Normalize whitespace
    case_sensitive=True,                    # Case-sensitive comparison
    max_depth=100                          # Maximum depth for nested objects
)
```

## 🧪 **Testing**

### **Run Examples**

```bash
python example_usage.py
```

### **Unit Tests**

```python
import pytest
from guard import SchemaGuard

@pytest.mark.asyncio
async def test_schema_validation():
    guard = SchemaGuard()
    await guard.start()
    
    result = await guard.validate_schema("test", {"field": "value"})
    assert result.is_valid
    assert result.field_count == 1
    
    await guard.stop()
```

## 🚨 **Error Handling**

### **Exception Types**

```python
from guard.exceptions import (
    SchemaDriftError,      # Schema drift detected
    SchemaValidationError, # Validation failed
    ConfigurationError,     # Invalid configuration
    FingerprintError,      # Fingerprinting failed
    DiffAnalysisError,     # Diff analysis failed
    StorageError,          # Storage operation failed
    AlertError,            # Alert system failed
    InterceptorError        # Interceptor failed
)
```

### **Error Handling Strategy**

```python
try:
    result = await guard.monitor_api_response(provider, response)
    if not result.is_valid:
        # Log error but don't block
        logger.warning(f"Schema validation failed: {result.errors}")
        
except SchemaDriftError as e:
    # Log critical error
    logger.critical(f"Schema drift detected: {e}")
    # Send alert
    await send_alert(e)
```

## 🔧 **Best Practices**

### **1. Fingerprinting Strategy**

```python
# Use SHA256 for production
hash_algorithm = "sha256"

# Include comprehensive metadata
include_metadata = True

# Normalize data for consistency
normalize_whitespace = True
sort_keys = True
```

### **2. Alert Configuration**

```python
# Set appropriate alert levels
alert_on_new_fields = True      # New fields often need attention
alert_on_removed_fields = True   # Removed fields are breaking
alert_on_type_changes = True     # Type changes can be breaking
alert_on_breaking_changes = True  # Breaking changes need immediate attention
```

### **3. Interceptor Design**

```python
# Keep interceptors lightweight
async def interceptor(provider, schema_data, fingerprint):
    # Fast validation
    if not is_valid_structure(schema_data):
        return {"valid": False, "errors": ["Invalid structure"]}
    
    # Business logic validation
    if not meets_business_rules(schema_data):
        return {"valid": False, "errors": ["Business rule violation"]}
    
    return {"valid": True}
```

### **4. Change Categorization**

```python
# Define breaking change rules
def is_breaking_change(change):
    # Required field removal
    if change.change_type == "removed" and is_required_field(change.path):
        return True
    
    # Type change to incompatible type
    if change.change_type == "type_changed" and is_incompatible_type_change(change):
        return True
    
    return False
```

## 🔄 **Integration Examples**

### **API Gateway Integration**

```python
from guard import get_guard

# Initialize guard
guard = get_guard()
await guard.start()

# Middleware for API responses
async def api_middleware(request, response):
    # Monitor response for schema changes
    result = await guard.monitor_api_response(
        provider=request.provider,
        response_data=response.json()
    )
    
    if not result.is_valid:
        # Log but don't block
        logger.warning(f"Schema issues: {result.errors}")
    
    return response
```

### **Pydantic Integration**

```python
from guard import register_interceptor_globally
from pydantic import BaseModel

# Pre-Pydantic validation
async def pydantic_interceptor(provider, schema_data, fingerprint):
    try:
        # Convert to Pydantic model
        validated_data = MyModel(**schema_data)
        return {"valid": True, "validated": validated_data.dict()}
    except Exception as e:
        return {"valid": False, "errors": [str(e)]}

# Register before Pydantic validation
register_interceptor_globally(pydantic_interceptor)

# Now Pydantic validation happens after schema guard
```

### **Background Monitoring**

```python
# Background task for continuous monitoring
async def schema_monitoring_task():
    guard = get_guard()
    await guard.start()
    
    while True:
        # Check all registered providers
        for provider in monitored_providers:
            response = await fetch_provider_response(provider)
            await guard.monitor_api_response(provider, response)
        
        await asyncio.sleep(60)  # Check every minute
```

## 📚 **Dependencies**

- **hashlib** - Built-in fingerprinting
- **deepdiff>=6.2.0** - Schema difference analysis
- **redis[asyncio]>=4.5.0** - Optional persistent storage
- **Python 3.8+** - For async/await support

## 🤝 **Contributing**

When contributing to the schema guard:

1. **Test fingerprint accuracy** with various JSON structures
2. **Validate diff analysis** with edge cases and large schemas
3. **Test interceptor performance** under high load
4. **Verify alert delivery** and callback handling
5. **Test storage backends** (memory and Redis)

## 📄 **License**

This schema evolution guard is part of the Market Intel Brain project.
