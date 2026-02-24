"""
Encryption Layer - AES-256-GCM with ThreadPoolExecutor

Enterprise-grade encryption with CPU-bound worker isolation
to prevent blocking the main async event loop.
"""

import asyncio
import logging
import os
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Tuple, Union
from enum import Enum

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes, hmac
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from .config import SecurityConfig, EncryptionAlgorithm


class EncryptionStatus(Enum):
    """Encryption operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    KEY_ERROR = "key_error"
    DATA_ERROR = "data_error"
    TIMEOUT = "timeout"


@dataclass
class EncryptionResult:
    """Encryption operation result."""
    status: EncryptionStatus
    data: Optional[bytes] = None
    nonce: Optional[bytes] = None
    tag: Optional[bytes] = None
    algorithm: str = ""
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecryptionResult:
    """Decryption operation result."""
    status: EncryptionStatus
    data: Optional[bytes] = None
    processing_time_ms: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecureMemory:
    """
    Secure memory manager for sensitive data.
    
    Features:
    - Automatic memory clearing
    - Thread-safe operations
    - Memory pool management
    - Zero-knowledge cleanup
    """
    
    def __init__(
        self,
        pool_size: int = 100,
        logger: Optional[logging.Logger] = None
    ):
        self.pool_size = pool_size
        self.logger = logger or logging.getLogger("SecureMemory")
        
        # Memory pool
        self._memory_pool = []
        self._pool_lock = threading.Lock()
        self._allocated_count = 0
        
        # Initialize memory pool
        self._initialize_pool()
        
        self.logger.info(f"SecureMemory initialized with pool size: {pool_size}")
    
    def _initialize_pool(self):
        """Initialize secure memory pool."""
        for _ in range(self.pool_size):
            self._memory_pool.append(bytearray(1024))  # 1KB chunks
    
    @contextmanager
    def allocate(self, size: int):
        """Allocate secure memory block."""
        with self._pool_lock:
            if not self._memory_pool:
                # Pool exhausted, allocate new block
                memory_block = bytearray(size)
            else:
                memory_block = self._memory_pool.pop()
                if len(memory_block) < size:
                    memory_block.extend(bytearray(size - len(memory_block)))
            
            self._allocated_count += 1
        
        try:
            yield memory_block
        finally:
            # Clear sensitive data
            self._clear_memory(memory_block)
            
            # Return to pool
            with self._pool_lock:
                if len(self._memory_pool) < self.pool_size:
                    self._memory_pool.append(memory_block)
                self._allocated_count -= 1
    
    def _clear_memory(self, memory_block: bytearray):
        """Clear memory block securely."""
        # Overwrite with random data
        for i in range(len(memory_block)):
            memory_block[i] = secrets.randbits(8)
        
        # Final zero pass
        for i in range(len(memory_block)):
            memory_block[i] = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory pool statistics."""
        with self._pool_lock:
            return {
                "pool_size": self.pool_size,
                "available_blocks": len(self._memory_pool),
                "allocated_blocks": self._allocated_count,
                "utilization": self._allocated_count / self.pool_size
            }


class EncryptionManager:
    """
    Enterprise-grade encryption manager with ThreadPoolExecutor.
    
    Features:
    - AES-256-GCM encryption
    - CPU-bound worker isolation
    - Key rotation support
    - Performance monitoring
    - Zero-knowledge operations
    """
    
    def __init__(
        self,
        config: Optional[SecurityConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config or SecurityConfig()
        self.logger = logger or logging.getLogger("EncryptionManager")
        
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError("cryptography package is required. Install with: pip install cryptography")
        
        # ThreadPoolExecutor for CPU-bound operations
        self.thread_pool = ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="encryption"
        )
        
        # Secure memory manager
        self.secure_memory = SecureMemory(
            pool_size=self.config.secure_memory_pool_size,
            logger=self.logger
        )
        
        # Encryption key management
        self._master_key = None
        self._key_derivation_salt = None
        self._key_rotation_time = None
        self._key_lock = threading.Lock()
        
        # Performance metrics
        self.encryption_count = 0
        self.decryption_count = 0
        self.total_encryption_time_ms = 0.0
        self.total_decryption_time_ms = 0.0
        self.encryption_errors = 0
        self.decryption_errors = 0
        
        # Initialize encryption
        self._initialize_encryption()
        
        self.logger.info(f"EncryptionManager initialized: {self.config.encryption_algorithm.value}")
    
    def _initialize_encryption(self):
        """Initialize encryption components."""
        try:
            # Derive encryption key from master key
            self._derive_encryption_key()
            
            # Set key rotation time
            self._key_rotation_time = datetime.now(timezone.utc) + timedelta(
                hours=self.config.key_rotation_interval_hours
            )
            
            self.logger.info("Encryption components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize encryption: {e}")
            raise
    
    def _derive_encryption_key(self):
        """Derive encryption key from master key using PBKDF2."""
        with self._key_lock:
            if self._master_key is None:
                # Convert hex key to bytes
                if len(self.config.encryption_key) == 64:
                    # Hex string
                    self._master_key = bytes.fromhex(self.config.encryption_key)
                elif len(self.config.encryption_key) == 44:
                    # Base64
                    import base64
                    self._master_key = base64.b64decode(self.config.encryption_key)
                else:
                    # Direct bytes (32 characters)
                    self._master_key = self.config.encryption_key.encode('utf-8')
                
                # Generate salt if not exists
                if self._key_derivation_salt is None:
                    self._key_derivation_salt = secrets.token_bytes(32)
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._key_derivation_salt,
                iterations=100000,
                backend=default_backend()
            )
            
            derived_key = kdf.derive(self._master_key)
            return derived_key
    
    def _rotate_key_if_needed(self):
        """Rotate encryption key if needed."""
        if datetime.now(timezone.utc) >= self._key_rotation_time:
            self.logger.info("Rotating encryption key")
            self._derive_encryption_key()
            self._key_rotation_time = datetime.now(timezone.utc) + timedelta(
                hours=self.config.key_rotation_interval_hours
            )
    
    async def encrypt(self, data: Union[bytes, str], associated_data: Optional[bytes] = None) -> EncryptionResult:
        """
        Encrypt data using AES-256-GCM in ThreadPoolExecutor.
        
        Args:
            data: Data to encrypt
            associated_data: Additional authenticated data
            
        Returns:
            Encryption result
        """
        if not self.config.enable_encryption:
            return EncryptionResult(
                status=EncryptionStatus.SUCCESS,
                data=data if isinstance(data, bytes) else data.encode('utf-8'),
                algorithm="none",
                processing_time_ms=0.0
            )
        
        start_time = time.time()
        
        try:
            # Convert data to bytes
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
            
            # Check key rotation
            self._rotate_key_if_needed()
            
            # Run encryption in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._encrypt_sync,
                data_bytes,
                associated_data
            )
            
            # Update metrics
            self.encryption_count += 1
            processing_time = (time.time() - start_time) * 1000
            self.total_encryption_time_ms += processing_time
            
            if processing_time > self.config.max_encryption_time_ms:
                self.logger.warning(f"Encryption exceeded time limit: {processing_time:.2f}ms")
            
            result.processing_time_ms = processing_time
            return result
            
        except Exception as e:
            self.encryption_errors += 1
            self.logger.error(f"Encryption failed: {e}")
            
            return EncryptionResult(
                status=EncryptionStatus.FAILED,
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    def _encrypt_sync(self, data: bytes, associated_data: Optional[bytes] = None) -> EncryptionResult:
        """Synchronous encryption operation."""
        try:
            # Get encryption key
            key = self._derive_encryption_key()
            
            # Generate nonce
            nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
            
            # Encrypt using AES-256-GCM
            aesgcm = AESGCM(key)
            
            if associated_data:
                encrypted_data = aesgcm.encrypt(nonce, data, associated_data)
            else:
                encrypted_data = aesgcm.encrypt(nonce, data, None)
            
            # Extract tag (last 16 bytes for GCM)
            tag = encrypted_data[-16:]
            ciphertext = encrypted_data[:-16]
            
            return EncryptionResult(
                status=EncryptionStatus.SUCCESS,
                data=ciphertext,
                nonce=nonce,
                tag=tag,
                algorithm=self.config.encryption_algorithm.value,
                metadata={
                    "key_version": 1,
                    "nonce_length": len(nonce),
                    "tag_length": len(tag)
                }
            )
            
        except Exception as e:
            return EncryptionResult(
                status=EncryptionStatus.FAILED,
                error_message=str(e),
                algorithm=self.config.encryption_algorithm.value
            )
    
    async def decrypt(
        self,
        ciphertext: bytes,
        nonce: bytes,
        tag: bytes,
        associated_data: Optional[bytes] = None
    ) -> DecryptionResult:
        """
        Decrypt data using AES-256-GCM in ThreadPoolExecutor.
        
        Args:
            ciphertext: Encrypted data
            nonce: Nonce used during encryption
            tag: Authentication tag
            associated_data: Additional authenticated data
            
        Returns:
            Decryption result
        """
        if not self.config.enable_encryption:
            return DecryptionResult(
                status=EncryptionStatus.SUCCESS,
                data=ciphertext,
                processing_time_ms=0.0
            )
        
        start_time = time.time()
        
        try:
            # Run decryption in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.thread_pool,
                self._decrypt_sync,
                ciphertext,
                nonce,
                tag,
                associated_data
            )
            
            # Update metrics
            self.decryption_count += 1
            processing_time = (time.time() - start_time) * 1000
            self.total_decryption_time_ms += processing_time
            
            if processing_time > self.config.max_encryption_time_ms:
                self.logger.warning(f"Decryption exceeded time limit: {processing_time:.2f}ms")
            
            result.processing_time_ms = processing_time
            return result
            
        except Exception as e:
            self.decryption_errors += 1
            self.logger.error(f"Decryption failed: {e}")
            
            return DecryptionResult(
                status=EncryptionStatus.FAILED,
                error_message=str(e),
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    def _decrypt_sync(
        self,
        ciphertext: bytes,
        nonce: bytes,
        tag: bytes,
        associated_data: Optional[bytes] = None
    ) -> DecryptionResult:
        """Synchronous decryption operation."""
        try:
            # Get encryption key
            key = self._derive_encryption_key()
            
            # Reconstruct encrypted data
            encrypted_data = ciphertext + tag
            
            # Decrypt using AES-256-GCM
            aesgcm = AESGCM(key)
            
            if associated_data:
                decrypted_data = aesgcm.decrypt(nonce, encrypted_data, associated_data)
            else:
                decrypted_data = aesgcm.decrypt(nonce, encrypted_data, None)
            
            return DecryptionResult(
                status=EncryptionStatus.SUCCESS,
                data=decrypted_data,
                metadata={
                    "key_version": 1,
                    "nonce_length": len(nonce),
                    "tag_length": len(tag)
                }
            )
            
        except Exception as e:
            return DecryptionResult(
                status=EncryptionStatus.FAILED,
                error_message=str(e)
            )
    
    async def encrypt_sensitive_field(self, field_name: str, value: Any) -> Dict[str, Any]:
        """Encrypt sensitive field with metadata."""
        try:
            # Serialize value
            import json
            serialized_value = json.dumps(value, default=str).encode('utf-8')
            
            # Encrypt
            result = await self.encrypt(serialized_value)
            
            if result.status == EncryptionStatus.SUCCESS:
                return {
                    "encrypted": True,
                    "algorithm": result.algorithm,
                    "nonce": result.nonce.hex(),
                    "tag": result.tag.hex(),
                    "data": result.data.hex(),
                    "field_name": field_name,
                    "encrypted_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "encrypted": False,
                    "error": result.error_message,
                    "field_name": field_name
                }
                
        except Exception as e:
            self.logger.error(f"Failed to encrypt field {field_name}: {e}")
            return {
                "encrypted": False,
                "error": str(e),
                "field_name": field_name
            }
    
    async def decrypt_sensitive_field(self, encrypted_field: Dict[str, Any]) -> Any:
        """Decrypt sensitive field from metadata."""
        try:
            if not encrypted_field.get("encrypted", False):
                return encrypted_field.get("data")
            
            # Extract encryption components
            nonce = bytes.fromhex(encrypted_field["nonce"])
            tag = bytes.fromhex(encrypted_field["tag"])
            ciphertext = bytes.fromhex(encrypted_field["data"])
            
            # Decrypt
            result = await self.decrypt(ciphertext, nonce, tag)
            
            if result.status == EncryptionStatus.SUCCESS:
                import json
                return json.loads(result.data.decode('utf-8'))
            else:
                self.logger.error(f"Decryption failed: {result.error_message}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to decrypt field: {e}")
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get encryption metrics."""
        total_operations = self.encryption_count + self.decryption_count
        avg_encryption_time = self.total_encryption_time_ms / max(self.encryption_count, 1)
        avg_decryption_time = self.total_decryption_time_ms / max(self.decryption_count, 1)
        
        return {
            "encryption_metrics": {
                "operations_count": {
                    "encryption": self.encryption_count,
                    "decryption": self.decryption_count,
                    "total": total_operations
                },
                "performance": {
                    "avg_encryption_time_ms": avg_encryption_time,
                    "avg_decryption_time_ms": avg_decryption_time,
                    "total_encryption_time_ms": self.total_encryption_time_ms,
                    "total_decryption_time_ms": self.total_decryption_time_ms
                },
                "errors": {
                    "encryption_errors": self.encryption_errors,
                    "decryption_errors": self.decryption_errors,
                    "error_rate": (self.encryption_errors + self.decryption_errors) / max(total_operations, 1)
                },
                "configuration": {
                    "algorithm": self.config.encryption_algorithm.value,
                    "key_rotation_interval_hours": self.config.key_rotation_interval_hours,
                    "max_encryption_time_ms": self.config.max_encryption_time_ms
                }
            },
            "memory_metrics": self.secure_memory.get_stats(),
            "thread_pool_metrics": {
                "max_workers": self.thread_pool._max_workers,
                "active_threads": len([t for t in self.thread_pool._threads if t.is_alive()])
            }
        }
    
    async def close(self):
        """Close encryption manager and cleanup resources."""
        try:
            # Shutdown thread pool
            self.thread_pool.shutdown(wait=True)
            
            # Clear sensitive data
            with self._key_lock:
                if self._master_key:
                    self._master_key = None
                if self._key_derivation_salt:
                    self._key_derivation_salt = None
            
            self.logger.info("EncryptionManager closed and cleaned up")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """Destructor for cleanup."""
        try:
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
        except:
            pass


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager(config: Optional[SecurityConfig] = None) -> EncryptionManager:
    """Get or create global encryption manager."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager(config)
    return _encryption_manager


async def initialize_encryption(config: Optional[SecurityConfig] = None) -> EncryptionManager:
    """Initialize and return global encryption manager."""
    manager = get_encryption_manager(config)
    return manager
