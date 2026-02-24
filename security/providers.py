"""
External Secrets Providers

This module provides interfaces for external secrets providers
like AWS Secrets Manager, Azure Key Vault, and HashiCorp Vault.
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from .exceptions import ProviderError, SecurityError


class ProviderType(Enum):
    """Types of external secrets providers."""
    AWS_SECRETS_MANAGER = "aws_secrets_manager"
    AZURE_KEY_VAULT = "azure_key_vault"
    GCP_SECRET_MANAGER = "gcp_secret_manager"
    HASHICORP_VAULT = "hashicorp_vault"
    CUSTOM_PROVIDER = "custom_provider"
    LOCAL_FILE = "local_file"


@dataclass
class SecretMetadata:
    """Metadata for a secret."""
    name: str
    version: str
    created_at: float
    updated_at: float
    expires_at: Optional[float]
    description: Optional[str]
    tags: Dict[str, str]
    rotation_enabled: bool
    last_rotated: Optional[float]


@dataclass
class SecretValue:
    """Secure secret value container."""
    value: str
    metadata: SecretMetadata
    is_encrypted: bool
    checksum: Optional[str]


class BaseSecretsProvider(ABC):
    """Abstract base class for secrets providers."""
    
    def __init__(self, provider_type: ProviderType, config: Dict[str, Any]):
        """
        Initialize secrets provider.
        
        Args:
            provider_type: Type of provider
            config: Provider configuration
        """
        self.provider_type = provider_type
        self.config = config
        self.logger = logging.getLogger(f"{provider_type.value}_provider")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the provider."""
        pass
    
    @abstractmethod
    async def get_secret(self, secret_name: str) -> Optional[SecretValue]:
        """Get a secret by name."""
        pass
    
    @abstractmethod
    async def set_secret(self, secret_name: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set a secret by name."""
        pass
    
    @abstractmethod
    async def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret by name."""
        pass
    
    @abstractmethod
    async def list_secrets(self, prefix: Optional[str] = None) -> List[SecretMetadata]:
        """List all secrets or secrets with prefix."""
        pass
    
    @abstractmethod
    async def rotate_secret(self, secret_name: str, new_value: Optional[str] = None) -> bool:
        """Rotate a secret by name."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health."""
        pass


class AWSSecretsManagerProvider(BaseSecretsProvider):
    """AWS Secrets Manager provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.AWS_SECRETS_MANAGER, config)
        
        # AWS configuration
        self.region = config.get("region", "us-east-1")
        self.access_key_id = config.get("access_key_id")
        self.secret_access_key = config.get("secret_access_key")
        self.session_token = None
        
        # Initialize boto3 client
        self._client = None
    
    async def initialize(self) -> bool:
        """Initialize AWS Secrets Manager client."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Create session
            session = boto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )
            
            # Create Secrets Manager client
            self._client = session.client('secretsmanager')
            
            # Test connection
            self._client.list_secrets(MaxResults=1)
            
            self.logger.info("AWS Secrets Manager provider initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS Secrets Manager: {e}")
            raise ProviderError(f"Failed to initialize AWS Secrets Manager: {e}", "aws_secrets_manager", "initialize")
    
    async def get_secret(self, secret_name: str) -> Optional[SecretValue]:
        """Get secret from AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            response = self._client.get_secret_value(SecretId=secret_name)
            
            if 'SecretString' in response:
                secret_value = response['SecretString']
                metadata = self._extract_metadata(response)
                
                return SecretValue(
                    value=secret_value,
                    metadata=metadata,
                    is_encrypted=True,
                    checksum=self._calculate_checksum(secret_value)
                )
            else:
                self.logger.warning(f"Secret not found: {secret_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get secret {secret_name}: {e}")
            raise ProviderError(f"Failed to get secret {secret_name}: {e}", "aws_secrets_manager", "get_secret")
    
    async def set_secret(self, secret_name: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set secret in AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Prepare secret string
            secret_string = json.dumps({
                "value": secret_value,
                "metadata": metadata or {}
            })
            
            # Create secret
            response = self._client.create_secret(
                Name=secret_name,
                SecretString=secret_string,
                Description=metadata.get("description", "") if metadata else "",
                Tags=[{"Key": k, "Value": v} for k, v in metadata.get("tags", {}).items()] if metadata else []
            )
            
            self.logger.info(f"Created secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set secret {secret_name}: {e}")
            raise ProviderError(f"Failed to set secret {secret_name}: {e}", "aws_secrets_manager", "set_secret")
    
    async def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            self._client.delete_secret(SecretId=secret_name)
            
            self.logger.info(f"Deleted secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete secret {secret_name}: {e}")
            raise ProviderError(f"Failed to delete secret {secret_name}: {e}", "aws_secrets_manager", "delete_secret")
    
    async def list_secrets(self, prefix: Optional[str] = None) -> List[SecretMetadata]:
        """List secrets from AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            secrets = []
            paginator = self._client.get_paginator('list_secrets')
            
            for page in paginator.paginate():
                for secret in page['SecretList']:
                    if prefix and not secret['Name'].startswith(prefix):
                        continue
                    
                    metadata = SecretMetadata(
                        name=secret['Name'],
                        version=secret['VersionId'],
                        created_at=secret['CreatedDate'].timestamp(),
                        updated_at=secret['LastChangedDate'].timestamp(),
                        expires_at=secret.get('LastChangedDate'),
                        description=secret.get('Description'),
                        tags={tag['Key']: tag['Value'] for tag in secret.get('Tags', [])},
                        rotation_enabled=secret.get('RotationEnabled', False),
                        last_rotated=secret.get('LastRotatedDate')
                    )
                    secrets.append(metadata)
            
            return secrets
            
        except Exception as e:
            self.logger.error(f"Failed to list secrets: {e}")
            raise ProviderError(f"Failed to list secrets: {e}", "aws_secrets_manager", "list_secrets")
    
    async def rotate_secret(self, secret_name: str, new_value: Optional[str] = None) -> bool:
        """Rotate secret in AWS Secrets Manager."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            if new_value:
                # Update secret value
                await self.set_secret(secret_name, new_value)
            else:
                # Use built-in rotation
                response = self._client.rotate_secret(SecretId=secret_name)
                
            self.logger.info(f"Rotated secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate secret {secret_name}: {e}")
            raise ProviderError(f"Failed to rotate secret {secret_name}: {e}", "aws_secrets_manager", "rotate_secret")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check AWS Secrets Manager health."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            # Test connection
            self._client.list_secrets(MaxResults=1)
            
            return {
                "provider": "aws_secrets_manager",
                "status": "healthy",
                "region": self.region,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"AWS Secrets Manager health check failed: {e}")
            return {
                "provider": "aws_secrets_manager",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _extract_metadata(self, response: Dict[str, Any]) -> SecretMetadata:
        """Extract metadata from AWS response."""
        return SecretMetadata(
            name=response.get('Name', ''),
            version=response.get('VersionId', ''),
            created_at=response.get('CreatedDate', time.time()).timestamp(),
            updated_at=response.get('LastChangedDate', time.time()).timestamp(),
            expires_at=response.get('LastChangedDate'),
            description=response.get('Description', ''),
            tags={tag['Key']: tag['Value'] for tag in response.get('Tags', [])},
            rotation_enabled=response.get('RotationEnabled', False),
            last_rotated=response.get('LastRotatedDate')
        )
    
    def _calculate_checksum(self, value: str) -> str:
        """Calculate checksum for integrity verification."""
        import hashlib
        return hashlib.sha256(value.encode('utf-8')).hexdigest()


class AzureKeyVaultProvider(BaseSecretsProvider):
    """Azure Key Vault provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.AZURE_KEY_VAULT, config)
        
        # Azure configuration
        self.vault_url = config.get("vault_url", "https://vault.azure.net")
        self.tenant_id = config.get("tenant_id")
        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        
        # Initialize Azure client
        self._client = None
    
    async def initialize(self) -> bool:
        """Initialize Azure Key Vault client."""
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import ClientSecretCredential
            
            # Create credential
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Create Key Vault client
            self._client = SecretClient(
                vault_url=self.vault_url,
                credential=credential
            )
            
            # Test connection
            list(self._client.list_properties_of_secrets())
            
            self.logger.info("Azure Key Vault provider initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Azure Key Vault: {e}")
            raise ProviderError(f"Failed to initialize Azure Key Vault: {e}", "azure_key_vault", "initialize")
    
    async def get_secret(self, secret_name: str) -> Optional[SecretValue]:
        """Get secret from Azure Key Vault."""
        try:
            # Get secret from Key Vault
            secret_bundle = self._client.get_secret(secret_name)
            
            if secret_bundle:
                secret_value = secret_bundle.value
                metadata = self._extract_metadata(secret_name, secret_bundle)
                
                return SecretValue(
                    value=secret_value,
                    metadata=metadata,
                    is_encrypted=True,
                    checksum=self._calculate_checksum(secret_value)
                )
            else:
                self.logger.warning(f"Secret not found: {secret_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get secret {secret_name}: {e}")
            raise ProviderError(f"Failed to get secret {secret_name}: {e}", "azure_key_vault", "get_secret")
    
    async def set_secret(self, secret_name: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set secret in Azure Key Vault."""
        try:
            # Set secret in Key Vault
            self._client.set_secret(secret_name, secret_value)
            
            self.logger.info(f"Created secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set secret {secret_name}: {e}")
            raise ProviderError(f"Failed to set secret {secret_name}: {e}", "azure_key_vault", "set_secret")
    
    async def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from Azure Key Vault."""
        try:
            # Delete secret from Key Vault
            self._client.begin_delete_secret(secret_name)
            self._client.purge_deleted_secret(secret_name)
            
            self.logger.info(f"Deleted secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete secret {secret_name}: {e}")
            raise ProviderError(f"Failed to delete secret {secret_name}: {e}", "azure_key_vault", "delete_secret")
    
    async def list_secrets(self, prefix: Optional[str] = None) -> List[SecretMetadata]:
        """List secrets from Azure Key Vault."""
        try:
            # List secrets from Key Vault
            secret_properties = self._client.list_properties_of_secrets()
            
            secrets = []
            for secret_prop in secret_properties:
                secret_name = secret_prop.name
                
                if prefix and not secret_name.startswith(prefix):
                    continue
                
                metadata = SecretMetadata(
                    name=secret_name,
                    version=secret_prop.version,
                    created_at=secret_prop.created_on.timestamp(),
                    updated_at=secret_prop.updated_on.timestamp(),
                    expires_at=secret_prop.expires_on.timestamp() if secret_prop.expires_on else None,
                    description=secret_prop.tags.get("description", ""),
                    tags=secret_prop.tags,
                    rotation_enabled=secret_prop.enabled,
                    last_rotated=None
                )
                secrets.append(metadata)
            
            return secrets
            
        except Exception as e:
            self.logger.error(f"Failed to list secrets: {e}")
            raise ProviderError(f"Failed to list secrets: {e}", "azure_key_vault", "list_secrets")
    
    async def rotate_secret(self, secret_name: str, new_value: Optional[str] = None) -> bool:
        """Rotate secret in Azure Key Vault."""
        try:
            if new_value:
                # Update secret value
                await self.set_secret(secret_name, new_value)
            else:
                # Azure Key Vault doesn't have built-in rotation
                self.logger.warning(f"Azure Key Vault doesn't support automatic rotation for {secret_name}")
                return False
            
            self.logger.info(f"Rotated secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate secret {secret_name}: {e}")
            raise ProviderError(f"Failed to rotate secret {secret_name}: {e}", "azure_key_vault", "rotate_secret")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Azure Key Vault health."""
        try:
            # Test connection
            list(self._client.list_properties_of_secrets())
            
            return {
                "provider": "azure_key_vault",
                "status": "healthy",
                "vault_url": self.vault_url,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Azure Key Vault health check failed: {e}")
            return {
                "provider": "azure_key_vault",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _extract_metadata(self, secret_name: str, secret_bundle) -> SecretMetadata:
        """Extract metadata from Azure response."""
        return SecretMetadata(
            name=secret_name,
            version=secret_bundle.properties.version,
            created_at=secret_bundle.properties.created_on.timestamp(),
            updated_at=secret_bundle.properties.updated_on.timestamp(),
            expires_at=secret_bundle.properties.expires_on.timestamp() if secret_bundle.properties.expires_on else None,
            description=secret_bundle.properties.tags.get("description", ""),
            tags=secret_bundle.properties.tags,
            rotation_enabled=secret_bundle.properties.enabled,
            last_rotated=None
        )
    
    def _calculate_checksum(self, value: str) -> str:
        """Calculate checksum for integrity verification."""
        import hashlib
        return hashlib.sha256(value.encode('utf-8')).hexdigest()


class HashiCorpVaultProvider(BaseSecretsProvider):
    """HashiCorp Vault provider."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.HASHICORP_VAULT, config)
        
        # HashiCorp Vault configuration
        self.vault_url = config.get("vault_url", "http://localhost:8200")
        self.token = config.get("token")
        self.namespace = config.get("namespace", "secret/")
        
        # Initialize Vault client
        self._client = None
    
    async def initialize(self) -> bool:
        """Initialize HashiCorp Vault client."""
        try:
            import hvac
            import requests
            
            # Create client
            self._client = hvac.Client(
                url=self.vault_url,
                token=self.token,
                namespace=self.namespace
            )
            
            # Test connection
            self._client.sys.health.status()
            
            self.logger.info("HashiCorp Vault provider initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize HashiCorp Vault: {e}")
            raise ProviderError(f"Failed to initialize HashiCorp Vault: {e}", "hashicorp_vault", "initialize")
    
    async def get_secret(self, secret_name: str) -> Optional[SecretValue]:
        """Get secret from HashiCorp Vault."""
        try:
            # Read secret from Vault
            secret_response = self._client.read(secret_name)
            
            if secret_response and 'data' in secret_response:
                secret_value = secret_response['data']
                metadata = self._extract_metadata(secret_name, secret_response)
                
                return SecretValue(
                    value=secret_value,
                    metadata=metadata,
                    is_encrypted=True,
                    checksum=self._calculate_checksum(str(secret_value))
                )
            else:
                self.logger.warning(f"Secret not found: {secret_name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get secret {secret_name}: {e}")
            raise ProviderError(f"Failed to get secret {secret_name}: {e}", "hashicorp_vault", "get_secret")
    
    async def set_secret(self, secret_name: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set secret in HashiCorp Vault."""
        try:
            # Write secret to Vault
            self._client.write(secret_name, secret_value)
            
            self.logger.info(f"Created secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set secret {secret_name}: {e}")
            raise ProviderError(f"Failed to set secret {secret_name}: {e}", "hashicorp_vault", "set_secret")
    
    async def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from HashiCorp Vault."""
        try:
            # Delete secret from Vault
            self._client.delete(secret_name)
            
            self.logger.info(f"Deleted secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete secret {secret_name}: {e}")
            raise ProviderError(f"Failed to delete secret {secret_name}: {e}", "hashicorp_vault", "delete_secret")
    
    async def list_secrets(self, prefix: Optional[str] = None) -> List[SecretMetadata]:
        """List secrets from HashiCorp Vault."""
        try:
            # List secrets from Vault
            list_response = self._client.list(self.namespace)
            
            secrets = []
            if list_response and 'data' in list_response:
                for secret_name in list_response['data']['keys']:
                    if prefix and not secret_name.startswith(prefix):
                        continue
                    
                    # Get secret to extract metadata
                    secret_response = self._client.read(secret_name)
                    
                    if secret_response and 'data' in secret_response:
                        metadata = self._extract_metadata(secret_name, secret_response)
                        secrets.append(metadata)
            
            return secrets
            
        except Exception as e:
            self.logger.error(f"Failed to list secrets: {e}")
            raise ProviderError(f"Failed to list secrets: {e}", "hashicorp_vault", "list_secrets")
    
    async def rotate_secret(self, secret_name: str, new_value: Optional[str] = None) -> bool:
        """Rotate secret in HashiCorp Vault."""
        try:
            if new_value:
                # Update secret value
                await self.set_secret(secret_name, new_value)
            else:
                # HashiCorp Vault doesn't have built-in rotation
                self.logger.warning(f"HashiCorp Vault doesn't support automatic rotation for {secret_name}")
                return False
            
            self.logger.info(f"Rotated secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate secret {secret_name}: {e}")
            raise ProviderError(f"Failed to rotate secret {secret_name}: {e}", "hashicorp_vault", "rotate_secret")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check HashiCorp Vault health."""
        try:
            # Check Vault health
            health_status = self._client.sys.health.status()
            
            return {
                "provider": "hashicorp_vault",
                "status": "healthy" if health_status['initialized'] else "unhealthy",
                "vault_url": self.vault_url,
                "namespace": self.namespace,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"HashiCorp Vault health check failed: {e}")
            return {
                "provider": "hashicorp_vault",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _extract_metadata(self, secret_name: str, secret_response: Dict[str, Any]) -> SecretMetadata:
        """Extract metadata from HashiCorp response."""
        return SecretMetadata(
            name=secret_name,
            version="1",
            created_at=time.time(),
            updated_at=time.time(),
            expires_at=None,
            description="",
            tags={},
            rotation_enabled=False,
            last_rotated=None
        )
    
    def _calculate_checksum(self, value: str) -> str:
        """Calculate checksum for integrity verification."""
        import hashlib
        return hashlib.sha256(value.encode('utf-8')).hexdigest()


class SecretsProvider:
    """Factory class for creating secrets providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize secrets provider factory.
        
        Args:
            config: Provider configuration
        """
        self.config = config
        self.logger = logging.getLogger("SecretsProvider")
        self._providers = {}
    
    def create_provider(self, provider_type: ProviderType) -> BaseSecretsProvider:
        """Create a secrets provider instance."""
        if provider_type in self._providers:
            return self._providers[provider_type]
        
        provider_config = self.config.get(provider_type.value, {})
        
        if provider_type == ProviderType.AWS_SECRETS_MANAGER:
            provider = AWSSecretsManagerProvider(provider_config)
        elif provider_type == ProviderType.AZURE_KEY_VAULT:
            provider = AzureKeyVaultProvider(provider_config)
        elif provider_type == ProviderType.HASHICORP_VAULT:
            provider = HashiCorpVaultProvider(provider_config)
        elif provider_type == ProviderType.CUSTOM_PROVIDER:
            provider = CustomProvider(provider_config)
        else:
            raise ProviderError(f"Unsupported provider type: {provider_type}", provider_type.value, "create_provider")
        
        self._providers[provider_type] = provider
        self.logger.info(f"Created provider: {provider_type.value}")
        
        return provider
    
    def get_provider(self, provider_type: ProviderType) -> Optional[BaseSecretsProvider]:
        """Get existing provider instance."""
        return self._providers.get(provider_type)


class CustomProvider(BaseSecretsProvider):
    """Custom secrets provider for generic HTTP APIs."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(ProviderType.CUSTOM_PROVIDER, config)
        
        self.base_url = config.get("base_url", "http://localhost:8080")
        self.api_key = config.get("api_key")
        self.headers = config.get("headers", {})
        
        # Initialize HTTP client
        self._session = None
    
    async def initialize(self) -> bool:
        """Initialize custom provider."""
        try:
            import aiohttp
            
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                connector=aiohttp.TCPConnector(limit=10)
            )
            
            # Test connection
            async with self._session.get(f"{self.base_url}/health") as response:
                if response.status != 200:
                    raise Exception(f"Health check failed: {response.status}")
            
            self.logger.info("Custom provider initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize custom provider: {e}")
            raise ProviderError(f"Failed to initialize custom provider: {e}", "custom_provider", "initialize")
    
    async def get_secret(self, secret_name: str) -> Optional[SecretValue]:
        """Get secret from custom provider."""
        try:
            url = f"{self.base_url}/secrets/{secret_name}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    return SecretValue(
                        value=data.get("value"),
                        metadata=self._extract_metadata(secret_name, data),
                        is_encrypted=True,
                        checksum=self._calculate_checksum(data.get("value", ""))
                    )
                else:
                    self.logger.warning(f"Secret not found: {secret_name}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Failed to get secret {secret_name}: {e}")
            raise ProviderError(f"Failed to get secret {secret_name}: {e}", "custom_provider", "get_secret")
    
    async def set_secret(self, secret_name: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Set secret in custom provider."""
        try:
            url = f"{self.base_url}/secrets/{secret_name}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            data = {
                "value": secret_value,
                "metadata": metadata or {}
            }
            
            async with self._session.post(url, headers=headers, json=data) as response:
                if response.status == 201:
                    self.logger.info(f"Created secret: {secret_name}")
                    return True
                else:
                    self.logger.error(f"Failed to create secret: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to set secret {secret_name}: {e}")
            raise ProviderError(f"Failed to set secret {secret_name}: {e}", "custom_provider", "set_secret")
    
    async def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from custom provider."""
        try:
            url = f"{self.base_url}/secrets/{secret_name}"
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with self._session.delete(url, headers=headers) as response:
                if response.status == 200:
                    self.logger.info(f"Deleted secret: {secret_name}")
                    return True
                else:
                    self.logger.error(f"Failed to delete secret: {response.status}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to delete secret {secret_name}: {e}")
            raise ProviderError(f"Failed to delete secret {secret_name}: {e}", "custom_provider", "delete_secret")
    
    async def list_secrets(self, prefix: Optional[str] = None) -> List[SecretMetadata]:
        """List secrets from custom provider."""
        try:
            url = f"{self.base_url}/secrets"
            if prefix:
                url += f"?prefix={prefix}"
            
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    secrets = []
                    for secret_data in data.get("secrets", []):
                        secret_name = secret_data.get("name")
                        
                        if prefix and not secret_name.startswith(prefix):
                            continue
                        
                        metadata = self._extract_metadata(secret_name, secret_data)
                        secrets.append(metadata)
                    
                    return secrets
                else:
                    self.logger.error(f"Failed to list secrets: {response.status}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Failed to list secrets: {e}")
            raise ProviderError(f"Failed to list secrets: {e}", "custom_provider", "list_secrets")
    
    async def rotate_secret(self, secret_name: str, new_value: Optional[str] = None) -> bool:
        """Rotate secret in custom provider."""
        try:
            if new_value:
                # Update secret value
                await self.set_secret(secret_name, new_value)
            else:
                # Custom provider doesn't have built-in rotation
                self.logger.warning(f"Custom provider doesn't support automatic rotation for {secret_name}")
                return False
            
            self.logger.info(f"Rotated secret: {secret_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rotate secret {secret_name}: {e}")
            raise ProviderError(f"Failed to rotate secret {secret_name}: {e}", "custom_provider", "rotate_secret")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check custom provider health."""
        try:
            async with self._session.get(f"{self.base_url}/health") as response:
                return {
                    "provider": "custom_provider",
                    "status": "healthy" if response.status == 200 else "unhealthy",
                    "base_url": self.base_url,
                    "timestamp": time.time()
                }
                    
        except Exception as e:
            self.logger.error(f"Custom provider health check failed: {e}")
            return {
                "provider": "custom_provider",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def _extract_metadata(self, secret_name: str, data: Dict[str, Any]) -> SecretMetadata:
        """Extract metadata from custom provider response."""
        return SecretMetadata(
            name=secret_name,
            version=data.get("version", "1"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            expires_at=data.get("expires_at"),
            description=data.get("metadata", {}).get("description", ""),
            tags=data.get("metadata", {}).get("tags", {}),
            rotation_enabled=data.get("metadata", {}).get("rotation_enabled", False),
            last_rotated=data.get("metadata", {}).get("last_rotated")
        )
    
    def _calculate_checksum(self, value: str) -> str:
        """Calculate checksum for integrity verification."""
        import hashlib
        return hashlib.sha256(value.encode('utf-8')).hexdigest()


# Global provider instance
_global_provider: Optional[SecretsProvider] = None


def get_provider(**kwargs) -> SecretsProvider:
    """
    Get or create global secrets provider.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global SecretsProvider instance
    """
    global _global_provider
    if _global_provider is None:
        _global_provider = SecretsProvider(**kwargs)
    return _global_provider


# Convenience functions for global usage
async def get_secret_globally(provider_type: str, secret_name: str) -> Optional[SecretValue]:
    """Get secret using global provider."""
    from .settings import get_settings
    
    settings = get_settings()
    provider_config = settings.get_provider_config(provider_type)
    
    provider_factory = SecretsProvider(provider_config)
    provider = provider_factory.create_provider(ProviderType(provider_type))
    
    await provider.initialize()
    return await provider.get_secret(secret_name)


async def set_secret_globally(provider_type: str, secret_name: str, secret_value: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Set secret using global provider."""
    from .settings import get_settings
    
    settings = get_settings()
    provider_config = settings.get_provider_config(provider_type)
    
    provider_factory = SecretsProvider(provider_config)
    provider = provider_factory.create_provider(ProviderType(provider_type))
    
    await provider.initialize()
    return await provider.set_secret(secret_name, secret_value, metadata)
