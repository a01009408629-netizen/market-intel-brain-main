"""
Zero Trust Architecture - Service-to-Service Authentication

Enterprise-grade zero-trust middleware with JWT/mTLS authentication,
service mesh integration, and comprehensive authorization.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import secrets

try:
    import jwt
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    JWT_AVAILABLE = True
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    CRYPTOGRAPHY_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .config import SecurityConfig, AuthMethod
from .audit import AsyncAuditLogger, AuditEventType, AuditOutcome


class TrustLevel(Enum):
    """Service trust levels."""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuthStatus(Enum):
    """Authentication status."""
    AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"
    EXPIRED = "expired"
    INVALID = "invalid"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"


@dataclass
class ServiceIdentity:
    """Service identity information."""
    service_id: str
    service_name: str
    namespace: str
    trust_level: TrustLevel
    permissions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


@dataclass
class AuthContext:
    """Authentication context."""
    service_identity: ServiceIdentity
    auth_method: AuthMethod
    auth_status: AuthStatus
    token: Optional[str] = None
    certificate_info: Optional[Dict[str, Any]] = None
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[float] = None


@dataclass
class AuthPolicy:
    """Authorization policy."""
    policy_id: str
    name: str
    description: str
    rules: List[Dict[str, Any]]
    effect: str  # "allow" or "deny"
    priority: int = 0
    conditions: Dict[str, Any] = field(default_factory=dict)


class ServiceAuthenticator:
    """
    Service-to-service authenticator with JWT and mTLS support.
    
    Features:
    - JWT token generation and validation
    - mTLS certificate validation
    - Service identity management
    - Trust level assessment
    """
    
    def __init__(
        self,
        config: SecurityConfig,
        audit_logger: Optional[AsyncAuditLogger] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config
        self.audit_logger = audit_logger
        self.logger = logger or logging.getLogger("ServiceAuthenticator")
        
        if not JWT_AVAILABLE and self.config.auth_method == AuthMethod.JWT:
            raise ImportError("PyJWT is required for JWT authentication. Install with: pip install PyJWT")
        
        if not CRYPTOGRAPHY_AVAILABLE and self.config.auth_method == AuthMethod.MTLS:
            raise ImportError("cryptography is required for mTLS authentication. Install with: pip install cryptography")
        
        # Service registry
        self._service_registry: Dict[str, ServiceIdentity] = {}
        self._trust_relationships: Dict[str, List[str]] = {}
        
        # JWT keys
        self._jwt_private_key = None
        self._jwt_public_key = None
        self._jwt_algorithm = "RS256"
        
        # Rate limiting
        self._auth_attempts: Dict[str, List[datetime]] = {}
        self._rate_limit_window = timedelta(minutes=1)
        
        # Performance metrics
        self.auth_requests = 0
        self.auth_successes = 0
        self.auth_failures = 0
        self.total_auth_time_ms = 0.0
        
        # Initialize authentication
        self._initialize_authentication()
        
        self.logger.info(f"ServiceAuthenticator initialized: {self.config.auth_method.value}")
    
    def _initialize_authentication(self):
        """Initialize authentication components."""
        try:
            # Initialize JWT keys
            if self.config.auth_method == AuthMethod.JWT:
                self._initialize_jwt_keys()
            
            # Register trusted services
            self._register_trusted_services()
            
            self.logger.info("Authentication components initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize authentication: {e}")
            raise
    
    def _initialize_jwt_keys(self):
        """Initialize JWT signing keys."""
        try:
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Serialize private key
            self._jwt_private_key = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Serialize public key
            public_key = private_key.public_key()
            self._jwt_public_key = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            self.logger.info("JWT keys generated")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize JWT keys: {e}")
            raise
    
    def _register_trusted_services(self):
        """Register trusted services."""
        for service_name in self.config.trusted_services:
            service_id = f"{service_name}.{self.config.service_namespace}"
            
            service_identity = ServiceIdentity(
                service_id=service_id,
                service_name=service_name,
                namespace=self.config.service_namespace,
                trust_level=TrustLevel.MEDIUM,
                permissions=["read", "write"],
                metadata={"registered_at": datetime.now(timezone.utc).isoformat()}
            )
            
            self._service_registry[service_id] = service_identity
            self._trust_relationships[service_id] = self.config.trusted_services
        
        self.logger.info(f"Registered {len(self._service_registry)} trusted services")
    
    async def authenticate_request(
        self,
        headers: Dict[str, str],
        request_path: str,
        request_method: str
    ) -> AuthContext:
        """
        Authenticate incoming service request.
        
        Args:
            headers: HTTP headers
            request_path: Request path
            request_method: HTTP method
            
        Returns:
            Authentication context
        """
        start_time = time.time()
        
        try:
            self.auth_requests += 1
            
            # Check rate limiting
            client_id = headers.get("X-Service-ID", "unknown")
            if self._is_rate_limited(client_id):
                auth_context = AuthContext(
                    service_identity=ServiceIdentity(
                        service_id="unknown",
                        service_name="unknown",
                        namespace="unknown",
                        trust_level=TrustLevel.UNTRUSTED
                    ),
                    auth_method=self.config.auth_method,
                    auth_status=AuthStatus.RATE_LIMITED,
                    duration_ms=(time.time() - start_time) * 1000
                )
                
                await self._log_auth_event(auth_context, request_path, request_method)
                return auth_context
            
            # Authenticate based on method
            if self.config.auth_method == AuthMethod.JWT:
                auth_context = await self._authenticate_jwt(headers)
            elif self.config.auth_method == AuthMethod.MTLS:
                auth_context = await self._authenticate_mtls(headers)
            else:
                auth_context = AuthContext(
                    service_identity=ServiceIdentity(
                        service_id="unknown",
                        service_name="unknown",
                        namespace="unknown",
                        trust_level=TrustLevel.UNTRUSTED
                    ),
                    auth_method=self.config.auth_method,
                    auth_status=AuthStatus.UNAUTHENTICATED,
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Update metrics
            if auth_context.auth_status == AuthStatus.AUTHENTICATED:
                self.auth_successes += 1
            else:
                self.auth_failures += 1
            
            auth_context.duration_ms = (time.time() - start_time) * 1000
            self.total_auth_time_ms += auth_context.duration_ms
            
            # Log authentication event
            await self._log_auth_event(auth_context, request_path, request_method)
            
            return auth_context
            
        except Exception as e:
            self.auth_failures += 1
            self.logger.error(f"Authentication failed: {e}")
            
            return AuthContext(
                service_identity=ServiceIdentity(
                    service_id="unknown",
                    service_name="unknown",
                    namespace="unknown",
                    trust_level=TrustLevel.UNTRUSTED
                ),
                auth_method=self.config.auth_method,
                auth_status=AuthStatus.INVALID,
                duration_ms=(time.time() - start_time) * 1000
            )
    
    async def _authenticate_jwt(self, headers: Dict[str, str]) -> AuthContext:
        """Authenticate using JWT token."""
        try:
            # Extract JWT token
            auth_header = headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return AuthContext(
                    service_identity=ServiceIdentity(
                        service_id="unknown",
                        service_name="unknown",
                        namespace="unknown",
                        trust_level=TrustLevel.UNTRUSTED
                    ),
                    auth_method=AuthMethod.JWT,
                    auth_status=AuthStatus.UNAUTHENTICATED
                )
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Decode and validate JWT
            payload = jwt.decode(
                token,
                key=self._jwt_public_key,
                algorithms=[self._jwt_algorithm],
                options={"verify_exp": True}
            )
            
            # Extract service identity
            service_id = payload.get("service_id")
            service_name = payload.get("service_name")
            namespace = payload.get("namespace")
            
            if not all([service_id, service_name, namespace]):
                return AuthContext(
                    service_identity=ServiceIdentity(
                        service_id="unknown",
                        service_name="unknown",
                        namespace="unknown",
                        trust_level=TrustLevel.UNTRUSTED
                    ),
                    auth_method=AuthMethod.JWT,
                    auth_status=AuthStatus.INVALID,
                    token=token
                )
            
            # Check if service is trusted
            service_identity = self._service_registry.get(service_id)
            if not service_identity:
                return AuthContext(
                    service_identity=ServiceIdentity(
                        service_id=service_id,
                        service_name=service_name,
                        namespace=namespace,
                        trust_level=TrustLevel.UNTRUSTED
                    ),
                    auth_method=AuthMethod.JWT,
                    auth_status=AuthStatus.FORBIDDEN,
                    token=token
                )
            
            return AuthContext(
                service_identity=service_identity,
                auth_method=AuthMethod.JWT,
                auth_status=AuthStatus.AUTHENTICATED,
                token=token
            )
            
        except jwt.ExpiredSignatureError:
            return AuthContext(
                service_identity=ServiceIdentity(
                    service_id="unknown",
                    service_name="unknown",
                    namespace="unknown",
                    trust_level=TrustLevel.UNTRUSTED
                ),
                auth_method=AuthMethod.JWT,
                auth_status=AuthStatus.EXPIRED
            )
        except jwt.InvalidTokenError as e:
            return AuthContext(
                service_identity=ServiceIdentity(
                    service_id="unknown",
                    service_name="unknown",
                    namespace="unknown",
                    trust_level=TrustLevel.UNTRUSTED
                ),
                auth_method=AuthMethod.JWT,
                auth_status=AuthStatus.INVALID
            )
        except Exception as e:
            self.logger.error(f"JWT authentication error: {e}")
            return AuthContext(
                service_identity=ServiceIdentity(
                    service_id="unknown",
                    service_name="unknown",
                    namespace="unknown",
                    trust_level=TrustLevel.UNTRUSTED
                ),
                auth_method=AuthMethod.JWT,
                auth_status=AuthStatus.INVALID
            )
    
    async def _authenticate_mtls(self, headers: Dict[str, str]) -> AuthContext:
        """Authenticate using mTLS certificate."""
        try:
            # Extract certificate information from headers
            cert_subject = headers.get("X-SSL-Client-Subject-CN")
            cert_issuer = headers.get("X-SSL-Client-Issuer-CN")
            cert_verify = headers.get("X-SSL-Verify", "FAILED")
            
            if cert_verify != "SUCCESS":
                return AuthContext(
                    service_identity=ServiceIdentity(
                        service_id="unknown",
                        service_name="unknown",
                        namespace="unknown",
                        trust_level=TrustLevel.UNTRUSTED
                    ),
                    auth_method=AuthMethod.MTLS,
                    auth_status=AuthStatus.UNAUTHENTICATED,
                    certificate_info={"verify_result": cert_verify}
                )
            
            # Extract service identity from certificate
            if not cert_subject:
                return AuthContext(
                    service_identity=ServiceIdentity(
                        service_id="unknown",
                        service_name="unknown",
                        namespace="unknown",
                        trust_level=TrustLevel.UNTRUSTED
                    ),
                    auth_method=AuthMethod.MTLS,
                    auth_status=AuthStatus.INVALID,
                    certificate_info={"subject": cert_subject, "issuer": cert_issuer}
                )
            
            # Parse service ID from certificate subject
            service_id = cert_subject
            service_name = service_id.split('.')[0] if '.' in service_id else service_id
            namespace = service_id.split('.')[1] if '.' in service_id else self.config.service_namespace
            
            # Check if service is trusted
            service_identity = self._service_registry.get(service_id)
            if not service_identity:
                return AuthContext(
                    service_identity=ServiceIdentity(
                        service_id=service_id,
                        service_name=service_name,
                        namespace=namespace,
                        trust_level=TrustLevel.UNTRUSTED
                    ),
                    auth_method=AuthMethod.MTLS,
                    auth_status=AuthStatus.FORBIDDEN,
                    certificate_info={"subject": cert_subject, "issuer": cert_issuer}
                )
            
            return AuthContext(
                service_identity=service_identity,
                auth_method=AuthMethod.MTLS,
                auth_status=AuthStatus.AUTHENTICATED,
                certificate_info={"subject": cert_subject, "issuer": cert_issuer}
            )
            
        except Exception as e:
            self.logger.error(f"mTLS authentication error: {e}")
            return AuthContext(
                service_identity=ServiceIdentity(
                    service_id="unknown",
                    service_name="unknown",
                    namespace="unknown",
                    trust_level=TrustLevel.UNTRUSTED
                ),
                auth_method=AuthMethod.MTLS,
                auth_status=AuthStatus.INVALID
            )
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client is rate limited."""
        now = datetime.now(timezone.utc)
        
        # Clean old attempts
        if client_id in self._auth_attempts:
            self._auth_attempts[client_id] = [
                attempt for attempt in self._auth_attempts[client_id]
                if now - attempt < self._rate_limit_window
            ]
        else:
            self._auth_attempts[client_id] = []
        
        # Check rate limit
        if len(self._auth_attempts[client_id]) >= self.config.auth_rate_limit_per_second:
            return True
        
        # Record this attempt
        self._auth_attempts[client_id].append(now)
        return False
    
    async def _log_auth_event(self, auth_context: AuthContext, request_path: str, request_method: str):
        """Log authentication event."""
        if self.audit_logger:
            await self.audit_logger.log_event(
                event_type=AuditEventType.AUTHENTICATION,
                description=f"Service authentication: {auth_context.service_identity.service_id}",
                outcome=AuditOutcome.SUCCESS if auth_context.auth_status == AuthStatus.AUTHENTICATED else AuditOutcome.FAILURE,
                level=AuditLevel.HIGH if auth_context.auth_status != AuthStatus.AUTHENTICATED else AuditLevel.MEDIUM,
                service_id=auth_context.service_identity.service_id,
                details={
                    "auth_method": auth_context.auth_method.value,
                    "auth_status": auth_context.auth_status.value,
                    "trust_level": auth_context.service_identity.trust_level.value,
                    "request_path": request_path,
                    "request_method": request_method,
                    "duration_ms": auth_context.duration_ms
                }
            )
    
    def generate_service_token(self, service_identity: ServiceIdentity, ttl_hours: Optional[int] = None) -> str:
        """Generate JWT token for service."""
        if self.config.auth_method != AuthMethod.JWT:
            raise ValueError("JWT authentication not enabled")
        
        try:
            # Create token payload
            now = datetime.now(timezone.utc)
            ttl = ttl_hours or self.config.jwt_expiry_hours
            expires_at = now + timedelta(hours=ttl)
            
            payload = {
                "service_id": service_identity.service_id,
                "service_name": service_identity.service_name,
                "namespace": service_identity.namespace,
                "trust_level": service_identity.trust_level.value,
                "permissions": service_identity.permissions,
                "iat": int(now.timestamp()),
                "exp": int(expires_at.timestamp()),
                "jti": str(uuid.uuid4())
            }
            
            # Generate JWT token
            token = jwt.encode(
                payload=payload,
                key=self._jwt_private_key,
                algorithm=self._jwt_algorithm
            )
            
            return token
            
        except Exception as e:
            self.logger.error(f"Failed to generate service token: {e}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get authentication metrics."""
        total_requests = self.auth_requests
        success_rate = self.auth_successes / max(total_requests, 1)
        avg_auth_time = self.total_auth_time_ms / max(total_requests, 1)
        
        return {
            "auth_metrics": {
                "requests": {
                    "total": self.auth_requests,
                    "successes": self.auth_successes,
                    "failures": self.auth_failures,
                    "success_rate": success_rate
                },
                "performance": {
                    "avg_auth_time_ms": avg_auth_time,
                    "total_auth_time_ms": self.total_auth_time_ms,
                    "max_auth_time_ms": self.config.max_auth_time_ms
                },
                "services": {
                    "registered": len(self._service_registry),
                    "trusted": len([s for s in self._service_registry.values() if s.trust_level != TrustLevel.UNTRUSTED])
                },
                "configuration": {
                    "auth_method": self.config.auth_method.value,
                    "rate_limit_per_second": self.config.auth_rate_limit_per_second,
                    "jwt_expiry_hours": self.config.jwt_expiry_hours
                }
            }
        }


class ZeroTrustMiddleware:
    """
    Zero Trust middleware for service-to-service communication.
    
    Features:
    - Request authentication and authorization
    - Policy enforcement
    - Request/response interception
    - Audit logging integration
    """
    
    def __init__(
        self,
        config: SecurityConfig,
        audit_logger: Optional[AsyncAuditLogger] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config
        self.audit_logger = audit_logger
        self.logger = logger or logging.getLogger("ZeroTrustMiddleware")
        
        # Service authenticator
        self.authenticator = ServiceAuthenticator(config, audit_logger, logger)
        
        # Authorization policies
        self._policies: Dict[str, AuthPolicy] = {}
        self._initialize_policies()
        
        # Request tracking
        self._active_requests: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("ZeroTrustMiddleware initialized")
    
    def _initialize_policies(self):
        """Initialize authorization policies."""
        # Default allow policy for trusted services
        self._policies["default_allow"] = AuthPolicy(
            policy_id="default_allow",
            name="Default Allow",
            description="Allow requests from trusted services",
            rules=[
                {
                    "type": "trust_level",
                    "operator": "gte",
                    "value": "medium"
                }
            ],
            effect="allow",
            priority=100
        )
        
        # Deny policy for untrusted services
        self._policies["deny_untrusted"] = AuthPolicy(
            policy_id="deny_untrusted",
            name="Deny Untrusted",
            description="Deny requests from untrusted services",
            rules=[
                {
                    "type": "trust_level",
                    "operator": "eq",
                    "value": "untrusted"
                }
            ],
            effect="deny",
            priority=1000
        )
        
        self.logger.info(f"Initialized {len(self._policies)} authorization policies")
    
    async def intercept_request(
        self,
        headers: Dict[str, str],
        request_path: str,
        request_method: str,
        request_body: Optional[bytes] = None
    ) -> Tuple[bool, Optional[str], Optional[AuthContext]]:
        """
        Intercept and authenticate incoming request.
        
        Args:
            headers: HTTP headers
            request_path: Request path
            request_method: HTTP method
            request_body: Request body
            
        Returns:
            Tuple of (is_allowed, error_message, auth_context)
        """
        try:
            # Authenticate request
            auth_context = await self.authenticator.authenticate_request(
                headers, request_path, request_method
            )
            
            # Check if authenticated
            if auth_context.auth_status != AuthStatus.AUTHENTICATED:
                error_message = f"Authentication failed: {auth_context.auth_status.value}"
                return False, error_message, auth_context
            
            # Authorize request
            is_authorized, error_message = await self._authorize_request(
                auth_context, request_path, request_method
            )
            
            if not is_authorized:
                return False, error_message, auth_context
            
            # Track active request
            request_id = auth_context.request_id
            self._active_requests[request_id] = {
                "auth_context": auth_context,
                "request_path": request_path,
                "request_method": request_method,
                "start_time": datetime.now(timezone.utc)
            }
            
            return True, None, auth_context
            
        except Exception as e:
            self.logger.error(f"Request interception failed: {e}")
            return False, f"Internal error: {str(e)}", None
    
    async def _authorize_request(
        self,
        auth_context: AuthContext,
        request_path: str,
        request_method: str
    ) -> Tuple[bool, Optional[str]]:
        """Authorize request based on policies."""
        try:
            # Evaluate policies in priority order
            sorted_policies = sorted(
                self._policies.values(),
                key=lambda p: p.priority,
                reverse=True
            )
            
            for policy in sorted_policies:
                if await self._evaluate_policy(policy, auth_context, request_path, request_method):
                    if policy.effect == "allow":
                        return True, None
                    else:
                        return False, f"Access denied by policy: {policy.name}"
            
            # Default deny
            return False, "Access denied: no matching policy"
            
        except Exception as e:
            self.logger.error(f"Authorization evaluation failed: {e}")
            return False, f"Authorization error: {str(e)}"
    
    async def _evaluate_policy(
        self,
        policy: AuthPolicy,
        auth_context: AuthContext,
        request_path: str,
        request_method: str
    ) -> bool:
        """Evaluate authorization policy."""
        try:
            for rule in policy.rules:
                rule_type = rule.get("type")
                operator = rule.get("operator")
                value = rule.get("value")
                
                if rule_type == "trust_level":
                    actual_value = auth_context.service_identity.trust_level.value
                elif rule_type == "service_name":
                    actual_value = auth_context.service_identity.service_name
                elif rule_type == "namespace":
                    actual_value = auth_context.service_identity.namespace
                elif rule_type == "permission":
                    actual_value = auth_context.service_identity.permissions
                else:
                    continue
                
                # Evaluate rule
                if operator == "eq":
                    if actual_value != value:
                        return False
                elif operator == "ne":
                    if actual_value == value:
                        return False
                elif operator == "gte":
                    if isinstance(actual_value, str) and isinstance(value, str):
                        trust_levels = {"untrusted": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
                        if trust_levels.get(actual_value, 0) < trust_levels.get(value, 0):
                            return False
                elif operator == "in":
                    if actual_value not in value:
                        return False
                elif operator == "has":
                    if not isinstance(actual_value, list) or value not in actual_value:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Policy evaluation failed: {e}")
            return False
    
    async def complete_request(self, request_id: str, response_status: int):
        """Complete request tracking."""
        try:
            if request_id in self._active_requests:
                request_info = self._active_requests.pop(request_id)
                
                # Log request completion
                if self.audit_logger:
                    await self.audit_logger.log_event(
                        event_type=AuditEventType.API_CALL,
                        description=f"Request completed: {request_info['request_path']}",
                        outcome=AuditOutcome.SUCCESS if 200 <= response_status < 400 else AuditOutcome.FAILURE,
                        service_id=request_info['auth_context'].service_identity.service_id,
                        details={
                            "request_path": request_info['request_path'],
                            "request_method": request_info['request_method'],
                            "response_status": response_status,
                            "duration_ms": (datetime.now(timezone.utc) - request_info['start_time']).total_seconds() * 1000
                        }
                    )
                
        except Exception as e:
            self.logger.error(f"Failed to complete request tracking: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get middleware metrics."""
        auth_metrics = self.authenticator.get_metrics()
        
        return {
            "zero_trust_metrics": {
                "active_requests": len(self._active_requests),
                "policies_count": len(self._policies),
                "authenticator": auth_metrics
            }
        }


# Global zero trust middleware instance
_zero_trust_middleware: Optional[ZeroTrustMiddleware] = None


def get_zero_trust_middleware(
    config: SecurityConfig,
    audit_logger: Optional[AsyncAuditLogger] = None
) -> ZeroTrustMiddleware:
    """Get or create global zero trust middleware."""
    global _zero_trust_middleware
    if _zero_trust_middleware is None:
        _zero_trust_middleware = ZeroTrustMiddleware(config, audit_logger)
    return _zero_trust_middleware
