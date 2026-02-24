"""
Enterprise Authentication & Authorization System
JWT, OAuth2, RBAC, API Key Management, and Audit Logging
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import secrets
import hashlib
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
import json
import os

from .database import get_db_manager, get_postgres_session, ApiKey, UserSession, AuditLog

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Security
security = HTTPBearer()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class UserRole:
    """User roles for RBAC."""
    ADMIN = "admin"
    MANAGER = "manager"
    ANALYST = "analyst"
    VIEWER = "viewer"
    
    @classmethod
    def all_roles(cls) -> List[str]:
        return [cls.ADMIN, cls.MANAGER, cls.ANALYST, cls.VIEWER]


class Permission:
    """Permissions for RBAC."""
    # Data permissions
    READ_DATA = "read_data"
    WRITE_DATA = "write_data"
    DELETE_DATA = "delete_data"
    
    # User management
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    
    # System administration
    SYSTEM_CONFIG = "system_config"
    VIEW_LOGS = "view_logs"
    MANAGE_API_KEYS = "manage_api_keys"
    
    # Financial data specific
    ACCESS_MARKET_DATA = "access_market_data"
    ACCESS_NEWS_DATA = "access_news_data"
    EXPORT_DATA = "export_data"
    
    @classmethod
    def all_permissions(cls) -> List[str]:
        return [
            cls.READ_DATA, cls.WRITE_DATA, cls.DELETE_DATA,
            cls.CREATE_USER, cls.UPDATE_USER, cls.DELETE_USER,
            cls.SYSTEM_CONFIG, cls.VIEW_LOGS, cls.MANAGE_API_KEYS,
            cls.ACCESS_MARKET_DATA, cls.ACCESS_NEWS_DATA, cls.EXPORT_DATA
        ]


# Role-Permission Mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: Permission.all_permissions(),
    UserRole.MANAGER: [
        Permission.READ_DATA, Permission.WRITE_DATA,
        Permission.CREATE_USER, Permission.UPDATE_USER,
        Permission.ACCESS_MARKET_DATA, Permission.ACCESS_NEWS_DATA,
        Permission.EXPORT_DATA, Permission.MANAGE_API_KEYS
    ],
    UserRole.ANALYST: [
        Permission.READ_DATA, Permission.WRITE_DATA,
        Permission.ACCESS_MARKET_DATA, Permission.ACCESS_NEWS_DATA,
        Permission.EXPORT_DATA
    ],
    UserRole.VIEWER: [
        Permission.READ_DATA,
        Permission.ACCESS_MARKET_DATA, Permission.ACCESS_NEWS_DATA
    ]
}


class User(BaseModel):
    """User model for authentication."""
    id: str
    email: EmailStr
    username: str
    role: str
    is_active: bool = True
    created_at: datetime
    last_login: Optional[datetime] = None


class TokenData(BaseModel):
    """Token data model."""
    user_id: str
    username: str
    role: str
    permissions: List[str]
    exp: datetime
    iat: datetime
    type: str  # access or refresh


class APIKeyCreate(BaseModel):
    """API key creation model."""
    name: str
    permissions: List[str]
    rate_limit: int = 1000
    expires_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    """API key response model."""
    key_id: str
    api_key: str  # Only shown once during creation
    name: str
    permissions: List[str]
    rate_limit: int
    expires_at: Optional[datetime]
    created_at: datetime


class EnterpriseAuthManager:
    """Enterprise authentication and authorization manager."""
    
    def __init__(self):
        self.db_manager = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize authentication manager."""
        try:
            self.db_manager = await get_db_manager()
            self._initialized = True
            logger.info("✅ Enterprise Auth Manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Auth Manager initialization failed: {e}")
            raise
    
    def _get_password_hash(self, password: str) -> str:
        """Generate password hash."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def _generate_api_key(self) -> str:
        """Generate secure API key."""
        return f"mib_{secrets.token_urlsafe(32)}"
    
    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    async def create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        permissions = ROLE_PERMISSIONS.get(user.role, [])
        
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "permissions": permissions,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    
    async def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token."""
        payload = {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "exp": datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.now(timezone.utc),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    
    async def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            token_data = TokenData(**payload)
            return token_data
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password."""
        # This would typically query your user database
        # For now, we'll create a mock user for demonstration
        if username == "admin" and password == "admin123":
            return User(
                id="admin_001",
                email="admin@marketintelbrain.com",
                username="admin",
                role=UserRole.ADMIN,
                created_at=datetime.now(timezone.utc)
            )
        
        return None
    
    async def create_api_key(self, user_id: str, key_data: APIKeyCreate) -> APIKeyResponse:
        """Create new API key for user."""
        try:
            api_key = self._generate_api_key()
            key_hash = self._hash_api_key(api_key)
            key_id = f"key_{secrets.token_urlsafe(16)}"
            
            expires_at = None
            if key_data.expires_days:
                expires_at = datetime.now(timezone.utc) + timedelta(days=key_data.expires_days)
            
            async with self.db_manager.get_postgres_session() as session:
                db_key = ApiKey(
                    key_id=key_id,
                    user_id=user_id,
                    name=key_data.name,
                    key_hash=key_hash,
                    permissions=key_data.permissions,
                    rate_limit=key_data.rate_limit,
                    expires_at=expires_at
                )
                session.add(db_key)
                await session.commit()
                await session.refresh(db_key)
            
            # Log audit event
            await self.db_manager.log_audit_event(
                user_id=user_id,
                action="create_api_key",
                resource=f"api_key/{key_id}",
                details={"key_name": key_data.name, "permissions": key_data.permissions}
            )
            
            return APIKeyResponse(
                key_id=key_id,
                api_key=api_key,  # Only returned once
                name=key_data.name,
                permissions=key_data.permissions,
                rate_limit=key_data.rate_limit,
                expires_at=expires_at,
                created_at=db_key.created_at
            )
            
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create API key"
            )
    
    async def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify API key and return user info."""
        try:
            key_hash = self._hash_api_key(api_key)
            
            async with self.db_manager.get_postgres_session() as session:
                from sqlalchemy import select
                
                result = await session.execute(
                    select(ApiKey).where(
                        ApiKey.key_hash == key_hash,
                        ApiKey.is_active == True
                    )
                )
                db_key = result.scalar_one_or_none()
                
                if not db_key:
                    return None
                
                # Check expiration
                if db_key.expires_at and db_key.expires_at < datetime.now(timezone.utc):
                    return None
                
                # Update last used
                db_key.last_used = datetime.now(timezone.utc)
                await session.commit()
                
                return {
                    "user_id": db_key.user_id,
                    "key_id": db_key.key_id,
                    "permissions": db_key.permissions,
                    "rate_limit": db_key.rate_limit
                }
                
        except Exception as e:
            logger.error(f"API key verification failed: {e}")
            return None
    
    def has_permission(self, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has required permission."""
        return required_permission in user_permissions
    
    def has_role(self, user_role: str, required_role: str) -> bool:
        """Check if user has required role or higher."""
        role_hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.ANALYST: 1,
            UserRole.MANAGER: 2,
            UserRole.ADMIN: 3
        }
        
        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level


# Global auth manager instance
auth_manager = EnterpriseAuthManager()


async def get_auth_manager() -> EnterpriseAuthManager:
    """Get global auth manager instance."""
    if not auth_manager._initialized:
        await auth_manager.initialize()
    return auth_manager


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current user from JWT token."""
    token = credentials.credentials
    auth_mgr = await get_auth_manager()
    token_data = await auth_mgr.verify_token(token)
    return token_data


async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Get current active user."""
    # Additional checks for user status can be added here
    return current_user


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def permission_dependency(current_user: TokenData = Depends(get_current_active_user)):
        auth_mgr = auth_manager  # Use global instance
        if not auth_mgr.has_permission(current_user.permissions, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    
    return permission_dependency


def require_role(role: str):
    """Decorator to require specific role or higher."""
    def role_dependency(current_user: TokenData = Depends(get_current_active_user)):
        auth_mgr = auth_manager  # Use global instance
        if not auth_mgr.has_role(current_user.role, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' or higher required"
            )
        return current_user
    
    return role_dependency


async def api_key_auth(request: Request) -> Optional[Dict[str, Any]]:
    """Authenticate using API key from request headers."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        api_key = request.query_params.get("api_key")
    
    if api_key:
        auth_mgr = await get_auth_manager()
        return await auth_mgr.verify_api_key(api_key)
    
    return None
