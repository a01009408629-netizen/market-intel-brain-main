"""
Security Module - Legacy Compatibility Layer

This module provides backward compatibility for existing imports
while redirecting to the new src/security structure.
"""

import sys
import os
from pathlib import Path

# Add src to path for security imports
current_dir = Path(__file__).parent
src_dir = current_dir.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Import and re-export for compatibility
from src.security.config import SecurityConfig, get_security_config
from src.security.encryption import EncryptionManager, get_encryption_manager
from src.security.audit import AsyncAuditLogger, get_audit_logger
from src.security.zero_trust import ZeroTrustMiddleware, get_zero_trust_middleware

# Create a simple settings module for compatibility
class SecuritySettings:
    """Simple security settings for compatibility."""
    
    def __init__(self):
        self.config = get_security_config()
    
    def get(self, key: str, default=None):
        """Get setting value."""
        return getattr(self.config, key.lower(), default)

def get_settings():
    """Get security settings instance."""
    return SecuritySettings()

# Export for compatibility
__all__ = [
    'SecurityConfig',
    'get_security_config', 
    'EncryptionManager',
    'get_encryption_manager',
    'AsyncAuditLogger',
    'get_audit_logger',
    'ZeroTrustMiddleware',
    'get_zero_trust_middleware',
    'SecuritySettings',
    'get_settings'
]
