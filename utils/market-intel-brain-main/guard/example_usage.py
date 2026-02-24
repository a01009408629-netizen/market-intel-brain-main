"""
Schema Evolution Guard - Example Usage

This file demonstrates how to use the schema evolution guard system
for monitoring API responses, detecting schema changes, and alerting developers.
"""

import asyncio
import json
import time
from typing import Dict, Any

from guard import (
    SchemaGuard,
    GuardConfig,
    get_guard,
    validate_schema_globally,
    monitor_response_globally,
    register_alert_callback_globally,
    register_interceptor_globally,
    AlertLevel
)
from guard.exceptions import SchemaDriftError


# Example API responses to monitor
API_RESPONSES = {
    "v1": {
        "user": {
            "id": 123,
            "name": "John Doe",
            "email": "john@example.com"
        },
        "settings": {
            "theme": "dark",
            "notifications": True
        }
    },
    "v2": {
        "user": {
            "id": 123,
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "+1-555-0123"  # New field
        },
        "settings": {
            "theme": "light",  # Changed value
            "notifications": True,
            "privacy": "public"  # New field
        }
    },
    "v3": {
        "user": {
            "id": 123,
            "name": "John Doe",
            "email": "john.doe@company.com"  # Type change
        },
        "settings": {
            "theme": "light",
            "notifications": False  # Removed field
        }
    },
    "v4": {
        "user": {
            "id": 123,
            "name": "John Doe",
            "email": "john.doe@company.com"
            # "phone": "+1-555-0123"  # Removed field
        },
        "settings": {
            "theme": "dark",  # Changed back
            "notifications": True,
            "language": "en"  # New field
        }
    }
}


# Example interceptor functions
async def business_rule_interceptor(provider: str, schema_data: Any, fingerprint) -> Dict[str, Any]:
    """Example interceptor for business rules."""
    print(f"    🔍 Interceptor checking {provider} schema")
    
    # Example business rule: user email must be from company domain
    if "user" in schema_data and "email" in schema_data["user"]:
        email = schema_data["user"]["email"]
        if not email.endswith("@company.com"):
            return {
                "valid": False,
                "errors": [f"Email domain not allowed: {email}"],
                "rule": "business_email_domain"
            }
    
    # Example business rule: settings must have notifications enabled
    if "settings" in schema_data:
        if not schema_data["settings"].get("notifications", True):
            return {
                "valid": False,
                "errors": ["Notifications must be enabled"],
                "rule": "notifications_required"
            }
    
    return {"valid": True}


async def security_interceptor(provider: str, schema_data: Any, fingerprint) -> Dict[str, Any]:
    """Example interceptor for security rules."""
    print(f"    🛡️ Security interceptor checking {provider} schema")
    
    # Example security rule: no sensitive data in unexpected fields
    sensitive_fields = ["ssn", "password", "credit_card"]
    
    def check_sensitive(obj, path=""):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in sensitive_fields:
                    return {
                        "valid": False,
                        "errors": [f"Sensitive field found: {path}.{key}"],
                        "rule": "sensitive_data_prohibited"
                    }
                
                if isinstance(value, (dict, list)):
                    result = check_sensitive(value, f"{path}.{key}")
                    if not result["valid"]:
                        return result
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                result = check_sensitive(item, f"{path}[{i}]")
                if not result["valid"]:
                    return result
        
        return {"valid": True}
    
    return check_sensitive(schema_data)


# Example alert callbacks
def critical_alert_handler(provider: str, level: str, message: str, diff_result):
    """Handle critical schema drift alerts."""
    print(f"    🚨 CRITICAL ALERT: {message}")
    print(f"    Provider: {provider}")
    print(f"   Breaking changes: {diff_result.summary.get('breaking', 0)}")
    print(f"   Action: Immediate developer notification required")
    # In practice: Send to Slack, PagerDuty, etc.


def error_alert_handler(provider: str, level: str, message: str, diff_result):
    """Handle error-level schema drift alerts."""
    print(f"    ❌ ERROR ALERT: {message}")
    print(f"   Provider: {provider}")
    print(f"   Non-breaking changes: {diff_result.summary.get('non_breaking', 0)}")
    print(f"   Action: Developer notification within 24 hours")
    # In practice: Send to email, JIRA, etc.


def warning_alert_handler(provider: str, level: str, message: str, diff_result):
    """Handle warning-level schema drift alerts."""
    print(f"    ⚠️ WARNING ALERT: {message}")
    print(f"   Provider: {provider}")
    print(f"   Changes: {diff_result.summary.get('total_changes', 0)}")
    print(f"   Action: Log for developer review")
    # In practice: Log to monitoring system


async def demonstrate_basic_schema_validation():
    """Demonstrate basic schema validation."""
    print("=== Basic Schema Validation ===\n")
    
    guard = get_guard()
    await guard.start()
    
    try:
        print("1. Validating schema v1:")
        result1 = await guard.validate_schema("user_api", API_RESPONSES["v1"])
        print(f"   Valid: {result1.is_valid}")
        print(f"   Fields: {result1.field_count}")
        print(f"   Errors: {result1.errors}")
        
        print("\n2. Validating schema v2 (with new field):")
        result2 = await guard.validate_schema("user_api", API_RESPONSES["v2"])
        print(f"   Valid: {result2.is_valid}")
        print(f"   Fields: {result2.field_count}")
        print(f"   Errors: {result2.errors}")
        
        print("\n3. Validating schema v3 (with type change):")
        result3 = await guard.validate_schema("user_api", API_RESPONSES["v3"])
        print(f"   Valid: {result3.is_valid}")
        print(f"   Fields: {result3.field_count}")
        print(f"   Errors: {result3.errors}")
        
    finally:
        await guard.stop()


async def demonstrate_schema_drift_detection():
    """Demonstrate schema drift detection."""
    print("\n=== Schema Drift Detection ===\n")
    
    guard = get_guard()
    await guard.start()
    
    try:
        print("1. Initial schema (v1):")
        result1 = await guard.monitor_api_response("user_api", API_RESPONSES["v1"])
        print(f"   Monitored: {result1.is_valid}")
        
        # Wait a bit to simulate time passing
        await asyncio.sleep(1)
        
        print("\n2. Schema v2 (new field added):")
        result2 = await guard.monitor_api_response("user_api", API_RESPONSES["v2"])
        print(f"   Monitored: {result2.is_valid}")
        print(f"   Drift detected: {not result2.is_valid}")
        
        # Wait a bit
        await asyncio.sleep(1)
        
        print("\n3. Schema v3 (type change):")
        result3 = await guard.monitor_api_response("user_api", API_RESPONSES["v3"])
        print(f"   Monitored: {result3.is_valid}")
        print(f"   Drift detected: {not result3.is_valid}")
        
        # Wait a bit
        await asyncio.sleep(1)
        
        print("\n4. Schema v4 (field removed):")
        result4 = await guard.monitor_api_response("user_api", API_RESPONSES["v4"])
        print(f"   Monitored: {result4.is_valid}")
        print(f"   Drift detected: {not result4.is_valid}")
        
        # Show provider status
        print("\n5. Provider status:")
        status = await guard.get_provider_status("user_api")
        print(f"   Monitored: {status['monitored']}")
        print(f"   Current version: {status['current_version']}")
        print(f"   Available versions: {status['available_versions']}")
        
    finally:
        await guard.stop()


async def demonstrate_interceptors():
    """Demonstrate schema interceptors."""
    print("\n=== Schema Interceptors ===\n")
    
    # Configure guard with interceptors
    config = GuardConfig(
        enable_interception=True,
        enable_validation=True,
        enable_fingerprinting=True
    )
    
    guard = SchemaGuard(config)
    await guard.start()
    
    try:
        # Register interceptors
        guard.register_interceptor(business_rule_interceptor)
        guard.register_interceptor(security_interceptor)
        
        print("1. Testing business rule interceptor:")
        
        # Test with valid data
        valid_data = {
            "user": {
                "id": 123,
                "name": "John",
                "email": "john@company.com"
            },
            "settings": {
                "notifications": True
            }
        }
        
        result1 = await guard.validate_schema("test_api", valid_data)
        print(f"   Valid data: {result1.is_valid}")
        print(f"   Errors: {result1.errors}")
        
        # Test with invalid email domain
        invalid_data = {
            "user": {
                "id": 123,
                "name": "John",
                "email": "john@gmail.com"  # Not company domain
            },
            "settings": {
                "notifications": True
            }
        }
        
        result2 = await guard.validate_schema("test_api", invalid_data)
        print(f"   Invalid data: {result2.is_valid}")
        print(f"   Errors: {result2.errors}")
        
        print("\n2. Testing security interceptor:")
        
        # Test with sensitive data
        sensitive_data = {
            "user": {
                "id": 123,
                "name": "John",
                "ssn": "123-45-6789"  # Sensitive data
            }
        }
        
        result3 = await guard.validate_schema("test_api", sensitive_data)
        print(f"   Sensitive data: {result3.is_valid}")
        print(f"   Errors: {result3.errors}")
        
    finally:
        await guard.stop()


async def demonstrate_alert_system():
    """Demonstrate alert system."""
    print("\n=== Alert System ===\n")
    
    # Configure guard with alerts
    config = GuardConfig(
        enable_alerting=True,
        enable_diff_analysis=True,
        alert_on_new_fields=True,
        alert_on_removed_fields=True,
        alert_on_type_changes=True,
        alert_on_breaking_changes=True
    )
    
    guard = SchemaGuard(config)
    await guard.start()
    
    try:
        # Register alert callbacks
        guard.register_alert_callback(AlertLevel.CRITICAL, critical_alert_handler)
        guard.register_alert_callback(AlertLevel.ERROR, error_alert_handler)
        guard.register_alert_callback(AlertLevel.WARNING, warning_alert_handler)
        
        print("1. Registered alert callbacks:")
        print("   - CRITICAL: critical_alert_handler")
        print("   - ERROR: error_alert_handler")
        print("   - WARNING: warning_alert_handler")
        
        print("\n2. Simulating schema changes that trigger alerts:")
        
        # Simulate breaking change
        breaking_change = {
            "user": {
                "id": 123,
                "name": "John"
                # "email": "john@company.com"  # Removed field
            }
        }
        
        result1 = await guard.monitor_api_response("alert_test", breaking_change)
        print(f"   Breaking change detected: {not result1.is_valid}")
        
        # Simulate non-breaking change
        non_breaking_change = {
            "user": {
                "id": 123,
                "name": "John",
                "email": "john@company.com",
                "phone": "+1-555-0123"  # New field
            }
        }
        
        result2 = await guard.monitor_api_response("alert_test", non_breaking_change)
        print(f"   Non-breaking change detected: {not result2.is_valid}")
        
        # Show guard statistics
        print("\n3. Guard statistics:")
        stats = guard.get_statistics()
        print(f"   Alerts sent: {stats['alerts_sent']}")
        print(f"   Drifts detected: {stats['drifts_detected']}")
        print(f"   Validations: {stats['validations_performed']}")
        
    finally:
        await guard.stop()


async def demonstrate_fingerprinting():
    """Demonstrate schema fingerprinting."""
    print("\n=== Schema Fingerprinting ===\n")
    
    from guard import get_fingerprinter
    
    fingerprinter = get_fingerprinter()
    
    print("1. Creating fingerprints for different schema versions:")
    
    schemas = {
        "v1": API_RESPONSES["v1"],
        "v2": API_RESPONSES["v2"],
        "v3": API_RESPONSES["v3"]
    }
    
    fingerprints = {}
    for version, schema in schemas.items():
        fp = fingerprinter.create_fingerprint(schema, f"api_response_v{version}")
        fingerprints[version] = fp
        print(f"   v{version[-1]}: {fp.hash[:16]}... (fields: {fp.field_count}, depth: {fp.depth})")
    
    print("\n2. Comparing fingerprints:")
    
    # Compare v1 vs v2
    fp1 = fingerprints["v1"]
    fp2 = fingerprints["v2"]
    
    print(f"   v1 vs v2: {'same' if fp1.hash == fp2.hash else 'different'}")
    
    # Compare v2 vs v3
    print(f"   v2 vs v3: {'same' if fp2.hash == fp3.hash else 'different'}")
    
    print("\n3. Fingerprint details:")
    for version, fp in fingerprints.items():
        print(f"   v{version[-1]} metadata:")
        print(f"     Algorithm: {fp.algorithm}")
        print(f"     Field count: {fp.field_count}")
        print(f"     Max depth: {fp.depth}")
        print(f"     Data size: {fp.metadata.get('data_size', 0)}")


async def demonstrate_real_world_scenario():
    """Demonstrate real-world schema evolution scenario."""
    print("\n=== Real-World Scenario ===\n")
    
    # Configure comprehensive guard
    config = GuardConfig(
        enable_validation=True,
        enable_fingerprinting=True,
        enable_diff_analysis=True,
        enable_alerting=True,
        enable_interception=True,
        storage_backend="memory",  # Use memory for demo
        alert_on_new_fields=True,
        alert_on_removed_fields=True,
        alert_on_type_changes=True,
        alert_on_breaking_changes=True
    )
    
    guard = SchemaGuard(config)
    await guard.start()
    
    try:
        # Register interceptors and alerts
        guard.register_interceptor(business_rule_interceptor)
        guard.register_alert_callback(AlertLevel.CRITICAL, critical_alert_handler)
        guard.register_alert_callback(AlertLevel.WARNING, warning_alert_handler)
        
        print("1. Simulating API evolution over time:")
        
        # Initial API version
        print("   Day 1: Initial API v1")
        result1 = await guard.monitor_api_response("production_api", API_RESPONSES["v1"])
        print(f"      Status: {'OK' if result1.is_valid else 'ISSUES'}")
        
        await asyncio.sleep(0.5)
        
        # API v2 with new field
        print("   Day 7: API v2 (new 'phone' field)")
        result2 = await guard.monitor_api_response("production_api", API_RESPONSES["v2"])
        print(f"      Status: {'OK' if result2.is_valid else 'ISSUES'}")
        print(f"      Alert: {'SENT' if not result2.is_valid else 'NONE'}")
        
        await asyncio.sleep(0.5)
        
        # API v3 with breaking change
        print("   Day 14: API v3 (email type change)")
        result3 = await guard.monitor_api_response("production_api", API_RESPONSES["v3"])
        print(f"      Status: {'OK' if result3.is_valid else 'ISSUES'}")
        print(f"      Alert: {'CRITICAL' if not result3.is_valid else 'NONE'}")
        
        await asyncio.sleep(0.5)
        
        # API v4 with field removal
        print("   Day 21: API v4 (removed 'phone' field)")
        result4 = await guard.monitor_api_response("production_api", API_RESPONSES["v4"])
        print(f"      Status: {'OK' if result4.is_valid else 'ISSUES'}")
        print(f"      Alert: {'WARNING' if not result4.is_valid else 'NONE'}")
        
        print("\n2. Final provider status:")
        status = await guard.get_provider_status("production_api")
        print(f"   Provider: {status['provider']}")
        print(f"   Monitored: {status['monitored']}")
        print(f"   Current version: {status['current_version']}")
        print(f"   Available versions: {status['available_versions']}")
        
        print("\n3. Guard statistics:")
        stats = guard.get_statistics()
        print(f"   Uptime: {stats['uptime']:.1f}s")
        print(f"   Validations: {stats['validations_performed']}")
        print(f"   Interceptions: {stats['interceptions_performed']}")
        print(f"   Alerts sent: {stats['alerts_sent']}")
        print(f"   Drifts detected: {stats['drifts_detected']}")
        
    finally:
        await guard.stop()


async def demonstrate_global_functions():
    """Demonstrate global convenience functions."""
    print("\n=== Global Functions ===\n")
    
    try:
        print("1. Using global validation:")
        result = await validate_schema_globally("global_api", API_RESPONSES["v2"])
        print(f"   Validation result: {result.is_valid}")
        
        print("\n2. Using global monitoring:")
        result = await monitor_response_globally("global_api", API_RESPONSES["v3"])
        print(f"   Monitoring result: {result.is_valid}")
        
        print("\n3. Registering global alert callback:")
        register_alert_callback_globally(AlertLevel.WARNING, lambda *args: print(f"   📧 Global warning: {args[1]}"))
        
        # This will trigger on the next monitoring call
        result = await monitor_response_globally("global_api", API_RESPONSES["v2"])
        print(f"   Should trigger warning: {not result.is_valid}")
        
    finally:
        # Clean up global guard
        global_guard = get_guard()
        await global_guard.stop()


async def main():
    """Run all schema guard demonstrations."""
    print("Schema Evolution Guard - Complete Demonstration")
    print("=" * 60)
    
    try:
        await demonstrate_basic_schema_validation()
        await demonstrate_schema_drift_detection()
        await demonstrate_interceptors()
        await demonstrate_alert_system()
        await demonstrate_fingerprinting()
        await demonstrate_real_world_scenario()
        await demonstrate_global_functions()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Hashlib-based schema fingerprinting")
        print("✓ Deepdiff-based schema difference analysis")
        print("✓ Schema validation with configurable rules")
        print("✓ Schema drift detection and alerting")
        print("✓ Custom interceptor framework")
        print("✓ Multi-level alerting system (CRITICAL/ERROR/WARNING/INFO)")
        print("✓ Memory and Redis storage backends")
        print("✓ Non-blocking operation (no system shutdown)")
        print("✓ Comprehensive change categorization")
        print("✓ Early warning system for developers")
        print("✓ Schema registry and version tracking")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
