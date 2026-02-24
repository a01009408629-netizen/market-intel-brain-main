"""
MAIFA v3 Context Layer (UML) - State, intermediate results, cache engine
Manages unified memory layer for the entire system
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import time

from models.schemas import ContextState
from models.datatypes import CacheKey, CacheValue, ContextData

class ContextManager:
    """
    MAIFA v3 Context Manager - Unified Memory Layer
    
    Manages state, intermediate results, and caching across the entire system.
    Provides thread-safe operations and TTL-based expiration.
    """
    
    def __init__(self, max_cache_size: int = 10000, default_ttl: int = 3600):
        self.logger = logging.getLogger("ContextManager")
        self._cache: Dict[CacheKey, Dict[str, Any]] = {}
        self._sessions: Dict[str, ContextState] = {}
        self._max_cache_size = max_cache_size
        self._default_ttl = default_ttl
        self._cache_lock = asyncio.Lock()
        self._session_lock = asyncio.Lock()
        
        # Performance metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_sets = 0
        self._cache_evictions = 0
        
    async def get(self, key: CacheKey, default: CacheValue = None) -> CacheValue:
        """
        Get value from cache
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        async with self._cache_lock:
            if key in self._cache:
                entry = self._cache[key]
                
                # Check TTL
                if entry["expires_at"] > time.time():
                    self._cache_hits += 1
                    self.logger.debug(f"Cache hit for key: {key}")
                    return entry["value"]
                else:
                    # Expired entry
                    del self._cache[key]
                    self._cache_evictions += 1
            
            self._cache_misses += 1
            self.logger.debug(f"Cache miss for key: {key}")
            return default
    
    async def set(self, 
                  key: CacheKey, 
                  value: CacheValue, 
                  ttl: Optional[int] = None) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: instance default)
            
        Returns:
            True if set successfully
        """
        try:
            async with self._cache_lock:
                # Check cache size and evict if necessary
                if len(self._cache) >= self._max_cache_size:
                    await self._evict_oldest_entries()
                
                ttl = ttl or self._default_ttl
                expires_at = time.time() + ttl
                
                self._cache[key] = {
                    "value": value,
                    "created_at": time.time(),
                    "expires_at": expires_at,
                    "ttl": ttl,
                    "access_count": 0
                }
                
                self._cache_sets += 1
                self.logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to set cache key {key}: {e}")
            return False
    
    async def delete(self, key: CacheKey) -> bool:
        """Delete key from cache"""
        async with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
                self.logger.debug(f"Cache delete for key: {key}")
                return True
            return False
    
    async def clear(self) -> bool:
        """Clear all cache entries"""
        async with self._cache_lock:
            count = len(self._cache)
            self._cache.clear()
            self.logger.info(f"Cache cleared: {count} entries removed")
            return True
    
    async def get_session(self, session_id: str) -> Optional[ContextState]:
        """
        Get session state by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            ContextState if found, None otherwise
        """
        async with self._session_lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                
                # Check TTL
                if (datetime.now() - session.last_updated).seconds < session.ttl_seconds:
                    return session
                else:
                    # Expired session
                    del self._sessions[session_id]
                    self.logger.debug(f"Session expired: {session_id}")
            
            return None
    
    async def create_session(self, 
                            session_id: str, 
                            symbol: str, 
                            initial_data: Optional[ContextData] = None,
                            ttl_seconds: int = 3600) -> ContextState:
        """
        Create new session state
        
        Args:
            session_id: Unique session identifier
            symbol: Financial symbol
            initial_data: Initial context data
            ttl_seconds: Session TTL in seconds
            
        Returns:
            Created ContextState
        """
        async with self._session_lock:
            session = ContextState(
                session_id=session_id,
                symbol=symbol,
                data=initial_data or {},
                ttl_seconds=ttl_seconds
            )
            
            self._sessions[session_id] = session
            self.logger.debug(f"Session created: {session_id} for symbol {symbol}")
            return session
    
    async def update_session(self, 
                           session_id: str, 
                           data: ContextData) -> bool:
        """
        Update session data
        
        Args:
            session_id: Session identifier
            data: Data to merge into session
            
        Returns:
            True if updated successfully
        """
        async with self._session_lock:
            if session_id in self._sessions:
                session = self._sessions[session_id]
                session.data.update(data)
                session.last_updated = datetime.now()
                self.logger.debug(f"Session updated: {session_id}")
                return True
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session by ID"""
        async with self._session_lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                self.logger.debug(f"Session deleted: {session_id}")
                return True
            return False
    
    async def get_agent_result(self, 
                              agent_name: str, 
                              input_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached agent result
        
        Args:
            agent_name: Name of the agent
            input_hash: Hash of input data
            
        Returns:
            Cached result or None
        """
        cache_key = f"agent:{agent_name}:{input_hash}"
        return await self.get(cache_key)
    
    async def cache_agent_result(self, 
                                agent_name: str, 
                                input_hash: str, 
                                result: Dict[str, Any],
                                ttl: int = 300) -> bool:
        """
        Cache agent result
        
        Args:
            agent_name: Name of the agent
            input_hash: Hash of input data
            result: Agent result to cache
            ttl: Cache TTL in seconds
            
        Returns:
            True if cached successfully
        """
        cache_key = f"agent:{agent_name}:{input_hash}"
        return await self.set(cache_key, result, ttl)
    
    async def get_pipeline_state(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get cached pipeline state"""
        cache_key = f"pipeline:{pipeline_id}"
        return await self.get(cache_key)
    
    async def set_pipeline_state(self, 
                                pipeline_id: str, 
                                state: Dict[str, Any],
                                ttl: int = 600) -> bool:
        """Set pipeline state"""
        cache_key = f"pipeline:{pipeline_id}"
        return await self.set(cache_key, state, ttl)
    
    def _generate_input_hash(self, input_data: Dict[str, Any]) -> str:
        """Generate hash for input data"""
        input_str = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(input_str.encode()).hexdigest()
    
    async def _evict_oldest_entries(self, count: int = 100):
        """Evict oldest cache entries to make space"""
        if not self._cache:
            return
        
        # Sort by creation time
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1]["created_at"]
        )
        
        # Evict oldest entries
        for i, (key, _) in enumerate(sorted_entries[:count]):
            if i >= count:
                break
            del self._cache[key]
            self._cache_evictions += 1
        
        self.logger.debug(f"Evicted {min(count, len(sorted_entries))} oldest cache entries")
    
    async def cleanup_expired_entries(self):
        """Clean up expired cache entries and sessions"""
        current_time = time.time()
        
        # Clean expired cache entries
        async with self._cache_lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry["expires_at"] <= current_time
            ]
            
            for key in expired_keys:
                del self._cache[key]
                self._cache_evictions += 1
            
            if expired_keys:
                self.logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
        
        # Clean expired sessions
        async with self._session_lock:
            current_datetime = datetime.now()
            expired_sessions = [
                session_id for session_id, session in self._sessions.items()
                if (current_datetime - session.last_updated).seconds >= session.ttl_seconds
            ]
            
            for session_id in expired_sessions:
                del self._sessions[session_id]
            
            if expired_sessions:
                self.logger.debug(f"Cleaned {len(expired_sessions)} expired sessions")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self._cache),
            "max_cache_size": self._max_cache_size,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_sets": self._cache_sets,
            "cache_evictions": self._cache_evictions,
            "hit_rate_percent": round(hit_rate, 2),
            "active_sessions": len(self._sessions),
            "memory_usage_mb": self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        try:
            import sys
            cache_size = sys.getsizeof(self._cache)
            sessions_size = sys.getsizeof(self._sessions)
            total_bytes = cache_size + sessions_size
            return round(total_bytes / (1024 * 1024), 2)
        except:
            return 0.0
    
    async def export_context(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export context data for backup or analysis
        
        Args:
            session_id: Specific session to export (None for all)
            
        Returns:
            Exported context data
        """
        if session_id:
            session = await self.get_session(session_id)
            return asdict(session) if session else {}
        else:
            return {
                "cache_stats": await self.get_cache_stats(),
                "sessions": {
                    sid: asdict(session) 
                    for sid, session in self._sessions.items()
                }
            }
    
    async def import_context(self, context_data: Dict[str, Any]) -> bool:
        """
        Import context data from backup
        
        Args:
            context_data: Context data to import
            
        Returns:
            True if imported successfully
        """
        try:
            if "sessions" in context_data:
                for session_id, session_dict in context_data["sessions"].items():
                    session = ContextState(**session_dict)
                    self._sessions[session_id] = session
            
            self.logger.info("Context data imported successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to import context data: {e}")
            return False


# Global context manager instance
context_manager = ContextManager()
