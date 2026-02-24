"""
Blacklist Manager Implementation

This module provides blacklist management for proxies and fingerprints
that encounter errors like 403/429 responses.
"""

import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass
from enum import Enum
import redis.asyncio as redis

from ..core.exceptions import TransientAdapterError


class BlacklistReason(Enum):
    """Reasons for blacklisting"""
    RATE_LIMIT = "rate_limit"      # 429 errors
    FORBIDDEN = "forbidden"        # 403 errors
    TIMEOUT = "timeout"            # Connection timeouts
    DNS_ERROR = "dns_error"        # DNS resolution failures
    SSL_ERROR = "ssl_error"        # SSL/TLS errors
    MANUAL = "manual"              # Manual blacklisting
    HIGH_FAILURE_RATE = "high_failure_rate"  # Too many failures


@dataclass
class BlacklistEntry:
    """Blacklist entry configuration"""
    identifier: str               # Proxy ID, fingerprint hash, etc.
    reason: BlacklistReason
    blacklisted_at: float
    expires_at: float
    metadata: Optional[Dict[str, Any]] = None
    permanent: bool = False
    violation_count: int = 1


class BlacklistManager:
    """
    Blacklist management system for proxies and fingerprints.
    
    Automatically blacklists items that encounter errors and manages
    temporary and permanent blacklist entries with Redis backend.
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        default_duration: int = 3600,      # 1 hour default
        max_violations: int = 3,          # Max violations before permanent
        permanent_threshold: float = 0.8,   # 80% failure rate for permanent
        cleanup_interval: int = 300,        # 5 minutes cleanup
        logger: Optional[logging.Logger] = None
    ):
        self.redis_client = redis_client
        self.default_duration = default_duration
        self.max_violations = max_violations
        self.permanent_threshold = permanent_threshold
        self.cleanup_interval = cleanup_interval
        self.logger = logger or logging.getLogger("BlacklistManager")
        
        # Redis keys
        self.blacklist_key = "blacklist:entries"
        self.violations_key = "blacklist:violations"
        self.stats_key = "blacklist:stats"
        
        # In-memory cache for performance
        self._blacklist_cache: Dict[str, BlacklistEntry] = {}
        self._cache_timestamp = 0
        self._cache_ttl = 60  # 1 minute cache TTL
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_loop())
    
    async def is_blacklisted(self, identifier: str) -> Optional[BlacklistEntry]:
        """
        Check if an identifier is blacklisted.
        
        Args:
            identifier: Proxy ID, fingerprint hash, etc.
            
        Returns:
            BlacklistEntry if blacklisted, None otherwise
        """
        try:
            # Check cache first
            if self._is_cache_valid():
                if identifier in self._blacklist_cache:
                    entry = self._blacklist_cache[identifier]
                    if not entry.permanent and entry.expires_at <= time.time():
                        # Expired entry, remove from cache
                        del self._blacklist_cache[identifier]
                        return None
                    return entry
            
            # Check Redis
            if self.redis_client:
                entry_data = await self.redis_client.hget(self.blacklist_key, identifier)
                if entry_data:
                    entry_dict = json.loads(entry_data)
                    entry = BlacklistEntry(**entry_dict)
                    
                    # Check if expired
                    if not entry.permanent and entry.expires_at <= time.time():
                        await self.remove_from_blacklist(identifier)
                        return None
                    
                    # Update cache
                    self._blacklist_cache[identifier] = entry
                    return entry
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking blacklist: {e}")
            return None
    
    async def add_to_blacklist(
        self,
        identifier: str,
        reason: BlacklistReason,
        duration: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        permanent: bool = False
    ):
        """
        Add an identifier to blacklist.
        
        Args:
            identifier: Proxy ID, fingerprint hash, etc.
            reason: Reason for blacklisting
            duration: Blacklist duration in seconds (None for default)
            metadata: Additional metadata
            permanent: Whether this is a permanent blacklist
        """
        try:
            current_time = time.time()
            expires_at = current_time + (duration or self.default_duration)
            
            # Check existing violations
            violations = await self._get_violations(identifier)
            violations += 1
            
            # Check if should be permanent
            if not permanent and violations >= self.max_violations:
                permanent = True
                expires_at = current_time + (365 * 24 * 3600)  # 1 year
                self.logger.warning(f"Making {identifier} permanent blacklist due to {violations} violations")
            
            # Check failure rate for permanent threshold
            if not permanent:
                failure_rate = await self._get_failure_rate(identifier)
                if failure_rate >= self.permanent_threshold:
                    permanent = True
                    expires_at = current_time + (365 * 24 * 3600)  # 1 year
                    self.logger.warning(f"Making {identifier} permanent blacklist due to {failure_rate:.2%} failure rate")
            
            # Create blacklist entry
            entry = BlacklistEntry(
                identifier=identifier,
                reason=reason,
                blacklisted_at=current_time,
                expires_at=expires_at,
                metadata=metadata,
                permanent=permanent,
                violation_count=violations
            )
            
            # Save to Redis
            if self.redis_client:
                entry_data = json.dumps({
                    'identifier': entry.identifier,
                    'reason': entry.reason.value,
                    'blacklisted_at': entry.blacklisted_at,
                    'expires_at': entry.expires_at,
                    'metadata': entry.metadata,
                    'permanent': entry.permanent,
                    'violation_count': entry.violation_count
                })
                
                await self.redis_client.hset(self.blacklist_key, identifier, entry_data)
                
                # Set expiration for temporary entries
                if not permanent:
                    await self.redis_client.expire(self.blacklist_key, int(expires_at - current_time + 60))
            
            # Update violations count
            await self._update_violations(identifier, violations)
            
            # Update cache
            self._blacklist_cache[identifier] = entry
            
            self.logger.warning(
                f"Blacklisted {identifier} for reason: {reason.value}, "
                f"permanent: {permanent}, expires: {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(expires_at))}"
            )
            
        except Exception as e:
            self.logger.error(f"Error adding to blacklist: {e}")
    
    async def remove_from_blacklist(self, identifier: str):
        """Remove an identifier from blacklist"""
        try:
            # Remove from Redis
            if self.redis_client:
                await self.redis_client.hdel(self.blacklist_key, identifier)
                await self.redis_client.hdel(self.violations_key, identifier)
            
            # Remove from cache
            if identifier in self._blacklist_cache:
                del self._blacklist_cache[identifier]
            
            self.logger.info(f"Removed {identifier} from blacklist")
            
        except Exception as e:
            self.logger.error(f"Error removing from blacklist: {e}")
    
    async def get_blacklist_entries(self) -> Dict[str, BlacklistEntry]:
        """Get all blacklist entries"""
        try:
            if self.redis_client:
                # Get from Redis
                entries_data = await self.redis_client.hgetall(self.blacklist_key)
                entries = {}
                
                for identifier, entry_data in entries_data.items():
                    try:
                        entry_dict = json.loads(entry_data)
                        entry = BlacklistEntry(**entry_dict)
                        
                        # Skip expired entries
                        if not entry.permanent and entry.expires_at <= time.time():
                            continue
                        
                        entries[identifier] = entry
                        
                    except Exception as e:
                        self.logger.error(f"Error parsing blacklist entry: {e}")
                
                return entries
            else:
                # Return cache
                return {
                    identifier: entry for identifier, entry in self._blacklist_cache.items()
                    if entry.permanent or entry.expires_at > time.time()
                }
                
        except Exception as e:
            self.logger.error(f"Error getting blacklist entries: {e}")
            return {}
    
    async def _get_violations(self, identifier: str) -> int:
        """Get violation count for identifier"""
        try:
            if self.redis_client:
                violations_data = await self.redis_client.hget(self.violations_key, identifier)
                return int(violations_data) if violations_data else 0
            else:
                # Check cache
                if identifier in self._blacklist_cache:
                    return self._blacklist_cache[identifier].violation_count
                return 0
        except Exception:
            return 0
    
    async def _update_violations(self, identifier: str, count: int):
        """Update violation count for identifier"""
        try:
            if self.redis_client:
                await self.redis_client.hset(self.violations_key, identifier, str(count))
                await self.redis_client.expire(self.violations_key, 365 * 24 * 3600)  # 1 year
        except Exception as e:
            self.logger.error(f"Error updating violations: {e}")
    
    async def _get_failure_rate(self, identifier: str) -> float:
        """Calculate failure rate for identifier"""
        try:
            if self.redis_client:
                stats_data = await self.redis_client.hget(self.stats_key, identifier)
                if stats_data:
                    stats = json.loads(stats_data)
                    total_requests = stats.get('total_requests', 0)
                    failed_requests = stats.get('failed_requests', 0)
                    return failed_requests / total_requests if total_requests > 0 else 0
            return 0
        except Exception:
            return 0
    
    async def update_stats(self, identifier: str, success: bool):
        """Update success/failure statistics"""
        try:
            if self.redis_client:
                # Get existing stats
                stats_data = await self.redis_client.hget(self.stats_key, identifier)
                if stats_data:
                    stats = json.loads(stats_data)
                else:
                    stats = {
                        'total_requests': 0,
                        'failed_requests': 0,
                        'last_success': None,
                        'last_failure': None
                    }
                
                # Update stats
                stats['total_requests'] += 1
                if success:
                    stats['last_success'] = time.time()
                else:
                    stats['failed_requests'] += 1
                    stats['last_failure'] = time.time()
                
                # Save back to Redis
                await self.redis_client.hset(self.stats_key, identifier, json.dumps(stats))
                await self.redis_client.expire(self.stats_key, 365 * 24 * 3600)  # 1 year
                
        except Exception as e:
            self.logger.error(f"Error updating stats: {e}")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        return time.time() - self._cache_timestamp < self._cache_ttl
    
    def _update_cache_timestamp(self):
        """Update cache timestamp"""
        self._cache_timestamp = time.time()
    
    async def _cleanup_loop(self):
        """Background cleanup loop for expired entries"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_entries()
                await self._refresh_cache()
                
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")
    
    async def _cleanup_expired_entries(self):
        """Clean up expired blacklist entries"""
        try:
            current_time = time.time()
            expired_entries = []
            
            for identifier, entry in self._blacklist_cache.items():
                if not entry.permanent and entry.expires_at <= current_time:
                    expired_entries.append(identifier)
            
            # Remove expired entries
            for identifier in expired_entries:
                del self._blacklist_cache[identifier]
                await self.remove_from_blacklist(identifier)
            
            if expired_entries:
                self.logger.info(f"Cleaned up {len(expired_entries)} expired blacklist entries")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up expired entries: {e}")
    
    async def _refresh_cache(self):
        """Refresh blacklist cache from Redis"""
        try:
            if self.redis_client:
                entries = await self.get_blacklist_entries()
                self._blacklist_cache = entries
                self._update_cache_timestamp()
                
                self.logger.debug(f"Refreshed blacklist cache with {len(entries)} entries")
                
        except Exception as e:
            self.logger.error(f"Error refreshing cache: {e}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get blacklist manager metrics"""
        try:
            entries = await self.get_blacklist_entries()
            
            total_entries = len(entries)
            permanent_entries = sum(1 for entry in entries.values() if entry.permanent)
            temporary_entries = total_entries - permanent_entries
            
            # Count by reason
            reason_counts = {}
            for entry in entries.values():
                reason = entry.reason.value
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            # Count expiring soon (within 1 hour)
            current_time = time.time()
            expiring_soon = sum(
                1 for entry in entries.values()
                if not entry.permanent and (entry.expires_at - current_time) < 3600
            )
            
            return {
                "total_entries": total_entries,
                "permanent_entries": permanent_entries,
                "temporary_entries": temporary_entries,
                "expiring_soon": expiring_soon,
                "reason_breakdown": reason_counts,
                "default_duration": self.default_duration,
                "max_violations": self.max_violations,
                "permanent_threshold": self.permanent_threshold,
                "redis_backend": self.redis_client is not None,
                "cache_size": len(self._blacklist_cache)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting metrics: {e}")
            return {"error": str(e)}
    
    async def clear_blacklist(self):
        """Clear all blacklist entries"""
        try:
            # Clear Redis
            if self.redis_client:
                await self.redis_client.delete(self.blacklist_key, self.violations_key, self.stats_key)
            
            # Clear cache
            self._blacklist_cache.clear()
            
            self.logger.info("Cleared all blacklist entries")
            
        except Exception as e:
            self.logger.error(f"Error clearing blacklist: {e}")
    
    async def export_blacklist(self, file_path: str):
        """Export blacklist to file"""
        try:
            entries = await self.get_blacklist_entries()
            
            export_data = {
                'exported_at': time.time(),
                'total_entries': len(entries),
                'entries': {}
            }
            
            for identifier, entry in entries.items():
                export_data['entries'][identifier] = {
                    'reason': entry.reason.value,
                    'blacklisted_at': entry.blacklisted_at,
                    'expires_at': entry.expires_at,
                    'permanent': entry.permanent,
                    'violation_count': entry.violation_count,
                    'metadata': entry.metadata
                }
            
            import aiofiles
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(export_data, indent=2))
            
            self.logger.info(f"Exported blacklist to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error exporting blacklist: {e}")
