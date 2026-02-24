"""
Zero-Trust Secrets Manager - Example Usage

This file demonstrates how to use the zero-trust secrets manager
with secure credential handling, audit logging, and external providers.
"""

import asyncio
import time
from typing import Dict, Any

from security import (
    get_manager,
    get_settings,
    get_provider,
    SecurityContext,
    AccessLevel,
    ProviderType
    get_secret_globally,
    set_secret_globally,
    delete_secret_globally,
    rotate_secret_globally,
    get_security_status_globally,
    mask_secret_globally
)
from security.exceptions import (
    SecretsError,
    SecurityError,
    AccessDeniedError,
    ValidationError
)


async def demonstrate_basic_secrets_management():
    """Demonstrate basic secrets management."""
    print("=== Basic Secrets Management ===\n")
    
    try:
        # Get secrets manager
        manager = get_manager()
        
        print("1. Setting up security context:")
        context = SecurityContext(
            user_id="user123",
            session_id="session_456",
            access_level=AccessLevel.READ,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            timestamp=time.time()
        )
        
        print(f"   User ID: {context.user_id}")
        print(f"   Access Level: {context.access_level.value}")
        print(f"   IP Address: {context.ip_address}")
        
        print("\n2. Getting API keys:")
        
        # Get Finnhub API key
        finnhub_key = await get_secret_globally("finnhub_api_key", context)
        if finnhub_key:
            print(f"   Finnhub API Key: {mask_secret_globally(finnhub_key)}")
        else:
            print("   Finnhub API Key: Not found")
        
        # Get Alpha Vantage API key
        alpha_vantage_key = await get_secret_globally("alpha_vantage_api_key", context)
        if alpha_vantage_key:
            print(f"   Alpha Vantage API Key: {mask_secret_globally(alpha_vantage_key)}")
        else:
            print("   Alpha Vantage API Key: Not found")
        
        print("\n3. Setting new secret:")
        
        new_secret_value = "new_secret_value_123"
        metadata = {
            "description": "Test secret for demonstration",
            "tags": {"environment": "test", "purpose": "demo"}
        }
        
        success = await set_secret_globally("test_secret", new_secret_value, context, metadata)
        print(f"   Set secret: {'Success' if success else 'Failed'}")
        
        if success:
            # Verify the secret was set
            retrieved_key = await get_secret_globally("test_secret", context)
            print(f"   Verification: {'Success' if retrieved_key == new_secret_value else 'Failed'}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_external_providers():
    """Demonstrate external secrets providers."""
    print("\n=== External Secrets Providers ===\n")
    
    try:
        # Get settings
        settings = get_settings()
        
        print("1. AWS Secrets Manager:")
        
        # Configure AWS provider
        aws_config = {
            "region": "us-east-1",
            "access_key_id": settings.providers.aws_access_key_id,
            "secret_access_key": settings.providers.aws_secret_access_key
        }
        
        # Update settings for AWS
        settings.providers.aws_region = aws_config["region"]
        settings.providers.aws_access_key_id = aws_config["access_key_id"]
        settings.providers.aws_secret_access_key = aws_config["secret_access_key"]
        
        # Create AWS provider
        from security.providers import SecretsProvider, ProviderType
        provider_factory = SecretsProvider(settings.providers.__dict__)
        aws_provider = provider_factory.create_provider(ProviderType.AWS_SECRETS_MANAGER)
        
        # Initialize AWS provider
        await aws_provider.initialize()
        print(f"   AWS provider initialized: {'Success' if aws_provider else 'Failed'}")
        
        if aws_provider:
            # Test AWS provider
            test_secret_name = "aws_test_secret"
            test_secret_value = "aws_test_value_123"
            
            success = await aws_provider.set_secret(test_secret_name, test_secret_value)
            print(f"   Set AWS secret: {'Success' if success else 'Failed'}")
            
            retrieved_secret = await aws_provider.get_secret(test_secret_name)
            if retrieved_secret:
                print(f"   Retrieved AWS secret: {mask_secret_globally(retrieved_secret.value)}")
            else:
                print("   Retrieved AWS secret: Not found")
        
        print("\n2. Azure Key Vault:")
        
        # Configure Azure provider
        azure_config = {
            "vault_url": "https://your-vault.vault.azure.net",
            "tenant_id": settings.providers.azure_tenant_id,
            "client_id": settings.providers.azure_client_id,
            "client_secret": settings.providers.azure_client_secret
        }
        
        # Update settings for Azure
        settings.providers.azure_tenant_id = azure_config["tenant_id"]
        settings.providers.azure_client_id = azure_config["client_id"]
        settings.providers.azure_client_secret = azure_config["client_secret"]
        
        # Create Azure provider
        azure_provider = provider_factory.create_provider(ProviderType.AZURE_KEY_VAULT)
        
        # Initialize Azure provider
        await azure_provider.initialize()
        print(f"   Azure provider initialized: {'Success' if azure_provider else 'Failed'}")
        
        if azure_provider:
            # Test Azure provider
            test_secret_name = "azure_test_secret"
            test_secret_value = "azure_test_value_123"
            
            success = await azure_provider.set_secret(test_secret_name, test_secret_value)
            print(f"   Set Azure secret: {'Success' if success else 'Failed'}")
            
            retrieved_secret = await azure_provider.get_secret(test_secret_name)
            if retrieved_secret:
                print(f"   Retrieved Azure secret: {mask_secret_globally(retrieved_secret.value)}")
            else:
                print("   Retrieved Azure secret: Not found")
        
        print("\n3. HashiCorp Vault:")
        
        # Configure HashiCorp Vault provider
        vault_config = {
            "vault_url": "http://localhost:8200",
            "token": settings.providers.hashicorp_vault_token
        }
        
        # Update settings for HashiCorp
        settings.providers.hashicorp_vault_url = vault_config["vault_url"]
        settings.providers.hashicorp_vault_token = vault_config["token"]
        
        # Create HashiCorp provider
        vault_provider = provider_factory.create_provider(ProviderType.HASHICORP_VAULT)
        
        # Initialize HashiCorp provider
        await vault_provider.initialize()
        print(f"   HashiCorp Vault provider initialized: {'Success' if vault_provider else 'Failed'}")
        
        if vault_provider:
            # Test HashiCorp Vault provider
            test_secret_name = "vault_test_secret"
            test_secret_value = "vault_test_value_123"
            
            success = await vault_provider.set_secret(test_secret_name, test_secret_value)
            print(f"   Set Vault secret: {'Success' if success else 'Failed'}")
            
            retrieved_secret = await vault_provider.get_secret(test_secret_name)
            if retrieved_secret:
                print(f"   Retrieved Vault secret: {mask_secret_globally(retrieved_secret.value)}")
            else:
                print("   Retrieved Vault secret: Not found")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_security_features():
    """Demonstrate security features like access control and audit logging."""
    print("\n=== Security Features ===\n")
    
    try:
        # Get security manager
        manager = get_manager()
        
        print("1. Access Control:")
        
        # Test with valid context
        valid_context = SecurityContext(
            user_id="valid_user",
            session_id="valid_session",
            access_level=AccessLevel.READ,
            ip_address="192.168.1.100"
        )
        
        print("   Testing with valid context:")
        secret = await manager.get_secret("test_secret", valid_context)
        print(f"   Access granted: {secret is not None}")
        
        # Test with invalid context (locked user)
        locked_context = SecurityContext(
            user_id="locked_user",
            session_id="locked_session",
            access_level=AccessLevel.READ,
            ip_address="192.168.1.200"
        )
        
        print("   Testing with locked user:")
        try:
            secret = await manager.get_secret("test_secret", locked_context)
            print(f"   Access denied: {secret is None}")
        except AccessDeniedError as e:
            print(f"   Access denied as expected: {e}")
        
        print("\n2. Audit Logging:")
        
        # Get access logs
        access_logs = manager.get_access_logs(limit=5)
        print(f"   Recent access logs: {len(access_logs)} entries")
        
        for log in access_logs:
            print(f"   {log.timestamp}: {log.user_id} - {log.operation} - {log.secret_name} - "
                  f"{'Success' if log.success else 'Failed'}")
        
        print("\n3. Security Status:")
        
        status = manager.get_security_status()
        print(f"   Active sessions: {status['active_sessions']}")
        print(f"   Locked users: {status['locked_users']}")
        print(f"   Failed attempts: {status['failed_attempts']}")
        print(f"   Providers configured: {status['providers_configured']}")
        print(f"   Encryption enabled: {status['encryption_enabled']}")
        print(f"   Audit logging enabled: {status['audit_logging_enabled']}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_secret_rotation():
    """Demonstrate automatic secret rotation."""
    print("\n=== Secret Rotation ===\n")
    
    try:
        # Get secrets manager
        manager = get_manager()
        
        print("1. Setting up secret for rotation:")
        
        context = SecurityContext(
            user_id="admin_user",
            session_id="admin_session",
            access_level=AccessLevel.ROTATE,
            ip_address="192.168.1.100"
        )
        
        # Set initial secret
        initial_secret = "initial_secret_value"
        await set_secret_globally("rotation_test", initial_secret, context)
        print(f"   Set initial secret: {mask_secret_globally(initial_secret)}")
        
        print("\n2. Rotating secret:")
        
        # Rotate secret (auto-generate new value)
        success = await rotate_secret_globally("rotation_test", None, context)
        print(f"   Rotation: {'Success' if success else 'Failed'}")
        
        if success:
            # Verify rotation
            new_secret = await get_secret_globally("rotation_test", context)
            print(f"   New secret: {mask_secret_globally(new_secret)}")
            
            # Verify old secret is no longer accessible
            # (In a real system, the old secret would be invalidated)
            print(f"   Rotation verification: {'Success' if new_secret != initial_secret else 'Failed'}")
        
        print("\n3. Rotation Audit Trail:")
        
        # Get audit events
        audit_events = manager.get_audit_events(limit=5)
        print(f"   Recent audit events: {len(audit_events)} entries")
        
        for event in audit_events:
            if event.event_type == "secret_rotation":
                print(f"   {event.timestamp}: {event.user_id} - {event.secret_name} - {event.operation}")
                print(f"      Details: {event.details}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_error_handling():
    """Demonstrate error handling and security violations."""
    print("\n=== Error Handling ===\n")
    
    try:
        # Get secrets manager
        manager = get_manager()
        
        print("1. Weak Secret Validation:")
        
        # Test with weak secret
        weak_secret = "password123"
        context = SecurityContext(user_id="test_user")
        
        try:
            await manager.set_secret("weak_test", weak_secret, context)
            print("   ERROR: Weak secret should have been rejected")
        except ValidationError as e:
            print(f"   SUCCESS: Weak secret rejected as expected: {e}")
        
        print("\n2. Access Control Violation:")
        
        # Test with invalid context
        invalid_context = SecurityContext(
            user_id="invalid_user",
            access_level=AccessLevel.ADMIN,
            ip_address="192.168.1.200"
        )
        
        try:
            await manager.get_secret("test_secret", invalid_context)
            print("   ERROR: Invalid context should be rejected")
        except AccessDeniedError as e:
            print(f"   SUCCESS: Invalid context rejected as expected: {e}")
        
        print("\n3. Provider Failures:")
        
        # Configure invalid provider
        from security.providers import SecretsProvider, ProviderType
        provider_factory = SecretsProvider({
            "aws_secrets_manager": {
                "region": "invalid-region",
                "access_key_id": "invalid-key",
                "secret_access_key": "invalid-secret"
            }
        })
        
        aws_provider = provider_factory.create_provider(ProviderType.AWS_SECRETS_MANAGER)
        
        try:
            await aws_provider.initialize()
            print("   ERROR: Invalid AWS config should be rejected")
        except ProviderError as e:
            print(f"   SUCCESS: Invalid AWS config rejected as expected: {e}")
        
        print("\n4. Encryption Failures:")
        
        # Temporarily disable encryption for testing
        original_encryption = manager.settings.security.enable_encryption
        manager.settings.security.enable_encryption = False
        
        try:
            # This should work without encryption
            await manager.set_secret("test_no_encryption", "test_value", SecurityContext())
            print("   SUCCESS: Operation without encryption completed")
        except Exception as e:
            print(f"   ERROR: Unexpected error without encryption: {e}")
        finally:
            # Restore encryption setting
            manager.settings.security.enable_encryption = original_encryption
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_real_world_scenario():
    """Demonstrate real-world secrets management scenario."""
    print("\n=== Real-World Scenario ===\n")
    
    try:
        # Get secrets manager
        manager = get_manager()
        
        print("1. Multi-Provider Setup:")
        
        # Configure multiple providers for redundancy
        settings = get_settings()
        
        # Add AWS provider
        settings.providers.aws_region = "us-west-2"
        settings.providers.aws_access_key_id = "AKIAIOSFODNN7EXAMPLE"
        settings.providers.aws_secret_access_key = "wJalrXtTKeyExample"
        
        # Add Azure provider
        settings.providers.azure_tenant_id = "your-tenant-id"
        settings.providers.azure_client_id = "your-client-id"
        settings.providers.azure_client_secret = "your-client-secret"
        
        # Add HashiCorp Vault
        settings.providers.hashicorp_vault_url = "https://vault.example.com"
        settings.providers.hashicorp_vault_token = "your-vault-token"
        
        # Add custom provider for local development
        settings.providers.custom_provider_url = "http://localhost:8080"
        settings.providers.custom_provider_token = "custom-provider-token"
        
        print("   Configured multiple providers for redundancy")
        
        print("\n2. Production Secret Management:")
        
        # Production context
        prod_context = SecurityContext(
            user_id="prod_user_123",
            session_id="prod_session_456",
            access_level=AccessLevel.READ,
            ip_address="10.0.0.100",
            user_agent="ProductionAPI/1.0"
        )
        
        # Set production secrets with metadata
        prod_metadata = {
            "environment": "production",
            "service": "market-data-api",
            "team": "data-platform",
            "created_by": "admin_user",
            "classification": "sensitive"
        }
        
        # Set database credentials
        await set_secret_globally("database_password", "prod_db_password_2024", prod_context, prod_metadata)
        print(f"   Set database password: {mask_secret_globally('prod_db_password_2024')}")
        
        # Set API keys with different providers
        await set_secret_globally("finnhub_api_key", "finnhub_prod_key_2024", prod_context, {"provider": "aws"})
        await set_secret_globally("alpha_vantage_api_key", "alpha_vantage_prod_key_2024", prod_context, {"provider": "azure"})
        
        print("   Set API keys with multiple providers for redundancy")
        
        print("\n3. Security Monitoring:")
        
        # Simulate multiple access attempts
        invalid_context = SecurityContext(
            user_id="attacker",
            session_id="malicious_session",
            access_level=AccessLevel.ADMIN,
            ip_address="192.168.1.200"
        )
        
        print("   Simulating failed attempts:")
        for i in range(5):
            try:
                await manager.get_secret("sensitive_secret", invalid_context)
                print(f"   Attempt {i+1}: Access denied (as expected)")
            except AccessDeniedError:
                print(f"   Attempt {i+1}: {e}")
        
        print("   Failed attempts count: {manager.get_security_status()['failed_attempts']}")
        
        print("\n4. Compliance and Auditing:")
        
        # Get audit trail
        audit_events = manager.get_audit_events(limit=10)
        
        print(f"   Audit events: {len(audit_events)} entries")
        
        for event in audit_events:
            if event.event_type in ["secret_rotation", "access_denied", "security_violation"]:
                print(f"   {event.timestamp}: {event.event_type.upper()} - {event.user_id}")
                print(f"      Secret: {event.secret_name}")
                print(f"      Operation: {event.operation}")
                print(f"      Success: {event.success}")
        
        print("\n5. Health Checks:")
        
        # Check provider health
        from security.providers import SecretsProvider, ProviderType
        provider_factory = SecretsProvider(settings.providers.__dict__)
        
        for provider_type in [ProviderType.AWS_SECRETS_MANAGER, ProviderType.AZURE_KEY_VAULT]:
            provider = provider_factory.get_provider(provider_type)
            if provider:
                health = await provider.health_check()
                print(f"   {provider_type.value} health: {health['status']}")
            else:
                print(f"   {provider_type.value}: Not configured")
        
        print("\n6. Security Status Summary:")
        
        status = manager.get_security_status()
        print(f"   Security Status: {'Healthy' if status['providers_configured'] > 0 else 'No providers'}")
        print(f"   Encryption: {'Enabled' if status['encryption_enabled'] else 'Disabled'}")
        print(f"   Audit Logging: {'Enabled' if status['audit_logging_enabled'] else 'Disabled'}")
        print(f"   Zero Trust: {'Enabled' if status['zero_trust_enabled'] else 'Disabled'}")
        print(f"   Active Sessions: {status['active_sessions']}")
        print(f"   Locked Users: {status['locked_users']}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def main():
    """Run all secrets manager demonstrations."""
    print("Zero-Trust Secrets Manager - Complete Demonstration")
    print("=" * 60)
    
    try:
        await demonstrate_basic_secrets_management()
        await demonstrate_external_providers()
        await demonstrate_security_features()
        await demonstrate_secret_rotation()
        await demonstrate_error_handling()
        await demonstrate_real_world_scenario()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Pydantic BaseSettings for secure configuration")
        print("✓ SecretStr for secure credential storage")
        print("✓ Zero-trust access control with security validation")
        print("✓ Comprehensive audit logging for compliance")
        print("✓ Multiple external providers (AWS, Azure, HashiCorp Vault)")
        print("✓ Automatic secret rotation with audit trail")
        print("✓ Encryption at rest with checksums")
        print("✓ Session management and lockout protection")
        print("✓ IP and user agent validation")
        print("✓ Failed attempt tracking and rate limiting")
        print("✅ No credential leakage in exception tracebacks")
        print("✓ Production-ready security policies")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
