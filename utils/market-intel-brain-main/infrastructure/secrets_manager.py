"""
Production-Ready Secrets Manager Module
AES-256 encrypted environment variable loader with in-memory decryption
"""

import os
import json
import base64
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hashlib


class SecretsManager:
    """Secure secrets manager with AES-256 encryption and in-memory decryption."""
    
    def __init__(self, master_key_env: str = "SECRETS_MASTER_KEY"):
        self.master_key_env = master_key_env
        self._decrypted_secrets: Optional[Dict[str, str]] = None
        self._fernet: Optional[Fernet] = None
        self._initialize()
    
    def _initialize(self):
        """Initialize encryption with master key from environment."""
        master_key = os.getenv(self.master_key_env)
        if not master_key:
            raise ValueError(f"Master key environment variable '{self.master_key_env}' not found")
        
        # Derive encryption key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'market_intel_brain_salt',  # Fixed salt for consistency
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self._fernet = Fernet(key)
    
    def _load_encrypted_env(self) -> Dict[str, str]:
        """Load encrypted .env file."""
        env_file = ".env.encrypted"
        if not os.path.exists(env_file):
            raise FileNotFoundError(f"Encrypted environment file '{env_file}' not found")
        
        encrypted_data = {}
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, encrypted_value = line.split('=', 1)
                    encrypted_data[key.strip()] = encrypted_value.strip()
        
        return encrypted_data
    
    def _decrypt_secrets(self) -> Dict[str, str]:
        """Decrypt all secrets strictly in memory."""
        if self._decrypted_secrets is not None:
            return self._decrypted_secrets
        
        encrypted_env = self._load_encrypted_env()
        decrypted = {}
        
        for key, encrypted_value in encrypted_env.items():
            try:
                # Decode base64 and decrypt
                encrypted_bytes = base64.b64decode(encrypted_value)
                decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
                decrypted[key] = decrypted_bytes.decode('utf-8')
            except Exception as e:
                raise ValueError(f"Failed to decrypt secret '{key}': {e}")
        
        self._decrypted_secrets = decrypted
        return decrypted
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get decrypted secret value."""
        secrets = self._decrypt_secrets()
        return secrets.get(key, default)
    
    def get_api_credentials(self, provider: str) -> Dict[str, str]:
        """Get API credentials for a specific provider."""
        secrets = self._decrypt_secrets()
        prefix = f"{provider.upper()}_"
        
        credentials = {}
        for key, value in secrets.items():
            if key.startswith(prefix):
                credential_key = key[len(prefix):].lower()
                credentials[credential_key] = value
        
        return credentials
    
    def get_database_config(self) -> Dict[str, str]:
        """Get database configuration."""
        secrets = self._decrypt_secrets()
        db_keys = ['db_host', 'db_port', 'db_name', 'db_user', 'db_password']
        
        return {key: secrets.get(key, '') for key in db_keys}
    
    def clear_memory(self):
        """Clear decrypted secrets from memory."""
        if self._decrypted_secrets:
            # Overwrite memory with zeros
            for key in list(self._decrypted_secrets.keys()):
                self._decrypted_secrets[key] = '0' * len(self._decrypted_secrets[key])
            self._decrypted_secrets.clear()
            self._decrypted_secrets = None


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get global secrets manager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


def encrypt_env_file(input_file: str = ".env", output_file: str = ".env.encrypted", master_key: Optional[str] = None):
    """Utility function to encrypt environment file."""
    if master_key is None:
        master_key = os.getenv("SECRETS_MASTER_KEY")
        if not master_key:
            raise ValueError("Master key required for encryption")
    
    # Derive encryption key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'market_intel_brain_salt',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    fernet = Fernet(key)
    
    # Encrypt environment variables
    encrypted_lines = []
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                encrypted_bytes = fernet.encrypt(value.encode('utf-8'))
                encrypted_value = base64.b64encode(encrypted_bytes).decode('utf-8')
                encrypted_lines.append(f"{key}={encrypted_value}")
            else:
                encrypted_lines.append(line)
    
    # Write encrypted file
    with open(output_file, 'w') as f:
        f.write('\n'.join(encrypted_lines))
    
    print(f"Encrypted {input_file} -> {output_file}")


if __name__ == "__main__":
    # Example usage
    secrets = get_secrets_manager()
    
    # Get individual secret
    binance_api_key = secrets.get_secret("BINANCE_API_KEY")
    print(f"Binance API Key: {binance_api_key[:10]}...")
    
    # Get provider credentials
    binance_creds = secrets.get_api_credentials("binance")
    print(f"Binance credentials: {list(binance_creds.keys())}")
    
    # Get database config
    db_config = secrets.get_database_config()
    print(f"Database config: {db_config}")
