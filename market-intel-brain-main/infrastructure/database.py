"""
Enterprise Database Manager
Production-ready PostgreSQL and Redis management with connection pooling
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import asyncpg
import aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from datetime import datetime, timezone
import json
import os

logger = logging.getLogger(__name__)

Base = declarative_base()


class DatabaseConfig:
    """Database configuration for enterprise deployment."""
    
    def __init__(self):
        self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
        self.postgres_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.postgres_db = os.getenv("POSTGRES_DB", "market_intel_brain")
        self.postgres_user = os.getenv("POSTGRES_USER", "postgres")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD", "")
        
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password = os.getenv("REDIS_PASSWORD", "")
        self.redis_db = int(os.getenv("REDIS_DB", "0"))
        
        # Connection pool settings
        self.postgres_pool_size = int(os.getenv("POSTGRES_POOL_SIZE", "20"))
        self.postgres_max_overflow = int(os.getenv("POSTGRES_MAX_OVERFLOW", "30"))
        self.redis_pool_size = int(os.getenv("REDIS_POOL_SIZE", "50"))
        
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


class AuditLog(Base):
    """Audit log table for enterprise compliance."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=False)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    success = Column(Boolean, default=True)


class UserSession(Base):
    """User session management table."""
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    metadata = Column(JSON)


class ApiKey(Base):
    """API key management table."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    key_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False)
    permissions = Column(JSON)
    rate_limit = Column(Integer, default=1000)  # requests per hour
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    last_used = Column(DateTime(timezone=True))


class EnterpriseDatabaseManager:
    """Enterprise-grade database manager with connection pooling and failover."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.postgres_engine = None
        self.postgres_session_factory = None
        self.redis_pool = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize database connections and create tables."""
        try:
            logger.info("🗄️ Initializing Enterprise Database Manager...")
            
            # Initialize PostgreSQL
            await self._initialize_postgres()
            
            # Initialize Redis
            await self._initialize_redis()
            
            # Create tables
            await self._create_tables()
            
            self._initialized = True
            logger.info("✅ Enterprise Database Manager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def _initialize_postgres(self):
        """Initialize PostgreSQL connection pool."""
        try:
            self.postgres_engine = create_async_engine(
                self.config.postgres_url,
                pool_size=self.config.postgres_pool_size,
                max_overflow=self.config.postgres_max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
                echo=False
            )
            
            self.postgres_session_factory = async_sessionmaker(
                self.postgres_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.postgres_engine.begin() as conn:
                await conn.execute("SELECT 1")
            
            logger.info("✅ PostgreSQL connection pool initialized")
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL initialization failed: {e}")
            raise
    
    async def _initialize_redis(self):
        """Initialize Redis connection pool."""
        try:
            self.redis_pool = aioredis.ConnectionPool.from_url(
                self.config.redis_url,
                max_connections=self.config.redis_pool_size,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test connection
            redis_client = aioredis.Redis(connection_pool=self.redis_pool)
            await redis_client.ping()
            
            logger.info("✅ Redis connection pool initialized")
            
        except Exception as e:
            logger.error(f"❌ Redis initialization failed: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables."""
        try:
            async with self.postgres_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ Database tables created successfully")
            
        except Exception as e:
            logger.error(f"❌ Table creation failed: {e}")
            raise
    
    @asynccontextmanager
    async def get_postgres_session(self):
        """Get PostgreSQL session with automatic cleanup."""
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")
        
        async with self.postgres_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()
    
    async def get_redis_client(self):
        """Get Redis client."""
        if not self._initialized:
            raise RuntimeError("Database manager not initialized")
        
        return aioredis.Redis(connection_pool=self.redis_pool)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all database connections."""
        health_status = {
            "postgres": {"status": "unknown", "response_time": None},
            "redis": {"status": "unknown", "response_time": None},
            "overall": "unknown"
        }
        
        try:
            # Check PostgreSQL
            start_time = datetime.now()
            async with self.postgres_engine.begin() as conn:
                await conn.execute("SELECT 1")
            postgres_time = (datetime.now() - start_time).total_seconds() * 1000
            health_status["postgres"] = {
                "status": "healthy",
                "response_time": f"{postgres_time:.2f}ms"
            }
            
        except Exception as e:
            health_status["postgres"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        try:
            # Check Redis
            start_time = datetime.now()
            redis_client = await self.get_redis_client()
            await redis_client.ping()
            redis_time = (datetime.now() - start_time).total_seconds() * 1000
            health_status["redis"] = {
                "status": "healthy",
                "response_time": f"{redis_time:.2f}ms"
            }
            
        except Exception as e:
            health_status["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
        
        # Determine overall health
        if (health_status["postgres"]["status"] == "healthy" and 
            health_status["redis"]["status"] == "healthy"):
            health_status["overall"] = "healthy"
        else:
            health_status["overall"] = "unhealthy"
        
        return health_status
    
    async def log_audit_event(self, user_id: str, action: str, resource: str, 
                           details: Optional[Dict] = None, ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None, success: bool = True):
        """Log audit event for compliance."""
        try:
            async with self.get_postgres_session() as session:
                audit_log = AuditLog(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    details=details,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=success
                )
                session.add(audit_log)
                await session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    async def close(self):
        """Close all database connections."""
        try:
            if self.postgres_engine:
                await self.postgres_engine.dispose()
            
            if self.redis_pool:
                await self.redis_pool.disconnect()
            
            logger.info("✅ Database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing database connections: {e}")


# Global database manager instance
db_manager = EnterpriseDatabaseManager()


async def get_db_manager() -> EnterpriseDatabaseManager:
    """Get global database manager instance."""
    return db_manager


async def get_postgres_session():
    """Get PostgreSQL session for dependency injection."""
    async with db_manager.get_postgres_session() as session:
        yield session


async def get_redis_client():
    """Get Redis client for dependency injection."""
    return await db_manager.get_redis_client()
