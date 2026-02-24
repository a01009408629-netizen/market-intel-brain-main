"""
Proxy Manager Implementation

This module provides proxy rotation and management for stealth browsing
with support for different rotation strategies and blacklist management.
"""

import asyncio
import json
import logging
import random
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import aiofiles
import redis.asyncio as redis

from ..core.exceptions import TransientAdapterError


class ProxyRotationStrategy(Enum):
    """Proxy rotation strategies"""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_USED = "least_used"
    WEIGHTED_RANDOM = "weighted_random"


@dataclass
class ProxyConfig:
    """Proxy configuration"""
    host: str
    port: int
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    weight: int = 1
    max_connections: int = 10
    timeout: float = 30.0
    country: Optional[str] = None
    anonymous: bool = True


@dataclass
class ProxyStats:
    """Proxy usage statistics"""
    proxy_id: str
    usage_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[float] = None
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    blacklisted_until: Optional[float] = None
    error_rate: float = 0.0


class ProxyManager:
    """
    Proxy rotation and management system.
    
    Manages proxy pools with different rotation strategies,
    blacklist management, and automatic failover.
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        redis_client: Optional[redis.Redis] = None,
        rotation_strategy: ProxyRotationStrategy = ProxyRotationStrategy.ROUND_ROBIN,
        blacklist_duration: int = 3600,  # 1 hour
        max_failure_rate: float = 0.5,  # 50% failure rate
        logger: Optional[logging.Logger] = None
    ):
        self.config_file = config_file
        self.redis_client = redis_client
        self.rotation_strategy = rotation_strategy
        self.blacklist_duration = blacklist_duration
        self.max_failure_rate = max_failure_rate
        self.logger = logger or logging.getLogger("ProxyManager")
        
        # Proxy pools and stats
        self.proxies: Dict[str, ProxyConfig] = {}
        self.proxy_stats: Dict[str, ProxyStats] = {}
        self.current_index = 0
        
        # Redis keys
        self.blacklist_key = "proxy:blacklist"
        self.stats_key = "proxy:stats"
        
        # Initialize proxies
        asyncio.create_task(self._initialize_proxies())
    
    async def _initialize_proxies(self):
        """Initialize proxy pool from config file or Redis"""
        try:
            # Try loading from config file first
            if self.config_file:
                await self._load_proxies_from_file()
            
            # Load stats from Redis
            if self.redis_client:
                await self._load_stats_from_redis()
            
            self.logger.info(f"Initialized {len(self.proxies)} proxies")
            
        except Exception as e:
            self.logger.error(f"Error initializing proxies: {e}")
    
    async def _load_proxies_from_file(self):
        """Load proxy configurations from JSON file"""
        try:
            async with aiofiles.open(self.config_file, 'r') as f:
                content = await f.read()
                proxy_data = json.loads(content)
            
            for proxy_id, config in proxy_data.items():
                self.proxies[proxy_id] = ProxyConfig(**config)
                self.proxy_stats[proxy_id] = ProxyStats(proxy_id=proxy_id)
            
            self.logger.info(f"Loaded {len(self.proxies)} proxies from {self.config_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading proxies from file: {e}")
    
    async def _load_stats_from_redis(self):
        """Load proxy statistics from Redis"""
        try:
            # Load blacklist
            blacklist_data = await self.redis_client.hgetall(self.blacklist_key)
            for proxy_id, blacklist_info in blacklist_data.items():
                if proxy_id in self.proxy_stats:
                    blacklist_info = json.loads(blacklist_info)
                    self.proxy_stats[proxy_id].blacklisted_until = blacklist_info.get('until')
            
            # Load stats
            stats_data = await self.redis_client.hgetall(self.stats_key)
            for proxy_id, stats_info in stats_data.items():
                if proxy_id in self.proxy_stats:
                    stats = json.loads(stats_info)
                    for key, value in stats.items():
                        setattr(self.proxy_stats[proxy_id], key, value)
            
            self.logger.info("Loaded proxy stats from Redis")
            
        except Exception as e:
            self.logger.error(f"Error loading stats from Redis: {e}")
    
    async def _save_stats_to_redis(self):
        """Save proxy statistics to Redis"""
        if not self.redis_client:
            return
        
        try:
            # Save blacklist
            blacklist_data = {}
            for proxy_id, stats in self.proxy_stats.items():
                if stats.blacklisted_until and stats.blacklisted_until > time.time():
                    blacklist_data[proxy_id] = json.dumps({
                        'until': stats.blacklisted_until
                    })
            
            if blacklist_data:
                await self.redis_client.delete(self.blacklist_key)
                await self.redis_client.hset(self.blacklist_key, mapping=blacklist_data)
                await self.redis_client.expire(self.blacklist_key, self.blacklist_duration * 2)
            
            # Save stats
            stats_data = {}
            for proxy_id, stats in self.proxy_stats.items():
                stats_data[proxy_id] = json.dumps({
                    'usage_count': stats.usage_count,
                    'success_count': stats.success_count,
                    'failure_count': stats.failure_count,
                    'last_used': stats.last_used,
                    'last_success': stats.last_success,
                    'last_failure': stats.last_failure,
                    'error_rate': stats.error_rate
                })
            
            if stats_data:
                await self.redis_client.delete(self.stats_key)
                await self.redis_client.hset(self.stats_key, mapping=stats_data)
                await self.redis_client.expire(self.stats_key, 3600 * 24)  # 24 hours
            
        except Exception as e:
            self.logger.error(f"Error saving stats to Redis: {e}")
    
    async def get_proxy(self) -> Optional[ProxyConfig]:
        """
        Get a proxy based on rotation strategy.
        
        Returns:
            ProxyConfig object or None if no proxies available
        """
        try:
            # Get available proxies (not blacklisted)
            available_proxies = [
                (proxy_id, proxy) for proxy_id, proxy in self.proxies.items()
                if self._is_proxy_available(proxy_id)
            ]
            
            if not available_proxies:
                self.logger.warning("No available proxies")
                return None
            
            # Select proxy based on strategy
            if self.rotation_strategy == ProxyRotationStrategy.ROUND_ROBIN:
                proxy_id, proxy = self._select_round_robin(available_proxies)
            elif self.rotation_strategy == ProxyRotationStrategy.RANDOM:
                proxy_id, proxy = self._select_random(available_proxies)
            elif self.rotation_strategy == ProxyRotationStrategy.LEAST_USED:
                proxy_id, proxy = self._select_least_used(available_proxies)
            elif self.rotation_strategy == ProxyRotationStrategy.WEIGHTED_RANDOM:
                proxy_id, proxy = self._select_weighted_random(available_proxies)
            else:
                # Default to round robin
                proxy_id, proxy = self._select_round_robin(available_proxies)
            
            # Update stats
            self._update_proxy_stats(proxy_id, 'used')
            
            self.logger.debug(f"Selected proxy: {proxy_id} ({proxy.host}:{proxy.port})")
            
            return proxy
            
        except Exception as e:
            self.logger.error(f"Error getting proxy: {e}")
            return None
    
    def _is_proxy_available(self, proxy_id: str) -> bool:
        """Check if proxy is available (not blacklisted)"""
        if proxy_id not in self.proxy_stats:
            return True
        
        stats = self.proxy_stats[proxy_id]
        
        # Check if blacklisted
        if stats.blacklisted_until and stats.blacklisted_until > time.time():
            return False
        
        # Check error rate
        if stats.error_rate > self.max_failure_rate:
            return False
        
        return True
    
    def _select_round_robin(self, available_proxies: List[tuple]) -> tuple:
        """Select proxy using round-robin strategy"""
        if not available_proxies:
            return None, None
        
        proxy_id, proxy = available_proxies[self.current_index % len(available_proxies)]
        self.current_index += 1
        
        return proxy_id, proxy
    
    def _select_random(self, available_proxies: List[tuple]) -> tuple:
        """Select proxy using random strategy"""
        if not available_proxies:
            return None, None
        
        return random.choice(available_proxies)
    
    def _select_least_used(self, available_proxies: List[tuple]) -> tuple:
        """Select proxy with least usage"""
        if not available_proxies:
            return None, None
        
        least_used = min(
            available_proxies,
            key=lambda x: self.proxy_stats.get(x[0], ProxyStats(proxy_id=x[0])).usage_count
        )
        
        return least_used
    
    def _select_weighted_random(self, available_proxies: List[tuple]) -> tuple:
        """Select proxy using weighted random strategy"""
        if not available_proxies:
            return None, None
        
        # Calculate weights based on success rate
        weights = []
        for proxy_id, proxy in available_proxies:
            stats = self.proxy_stats.get(proxy_id, ProxyStats(proxy_id=proxy_id))
            
            # Higher weight for better success rate
            if stats.usage_count > 0:
                success_rate = stats.success_count / stats.usage_count
                weight = max(1, success_rate * proxy.weight)
            else:
                weight = proxy.weight
            
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(available_proxies)
        
        r = random.uniform(0, total_weight)
        current_weight = 0
        
        for i, weight in enumerate(weights):
            current_weight += weight
            if r <= current_weight:
                return available_proxies[i]
        
        return available_proxies[-1]
    
    async def report_success(self, proxy_id: str):
        """Report successful proxy usage"""
        self._update_proxy_stats(proxy_id, 'success')
        await self._save_stats_to_redis()
    
    async def report_failure(self, proxy_id: str, error_type: str = "unknown"):
        """
        Report failed proxy usage.
        
        Args:
            proxy_id: Proxy identifier
            error_type: Type of error ('403', '429', 'timeout', etc.)
        """
        self._update_proxy_stats(proxy_id, 'failure')
        
        # Blacklist for certain error types
        if error_type in ['403', '429']:
            await self._blacklist_proxy(proxy_id, reason=error_type)
        
        await self._save_stats_to_redis()
    
    async def _blacklist_proxy(self, proxy_id: str, reason: str = "failure"):
        """Add proxy to blacklist"""
        if proxy_id not in self.proxy_stats:
            return
        
        self.proxy_stats[proxy_id].blacklisted_until = time.time() + self.blacklist_duration
        
        self.logger.warning(
            f"Blacklisted proxy {proxy_id} for {self.blacklist_duration}s due to: {reason}"
        )
        
        # Save to Redis
        if self.redis_client:
            try:
                await self.redis_client.hset(
                    self.blacklist_key,
                    proxy_id,
                    json.dumps({
                        'until': self.proxy_stats[proxy_id].blacklisted_until,
                        'reason': reason
                    })
                )
                await self.redis_client.expire(self.blacklist_key, self.blacklist_duration * 2)
            except Exception as e:
                self.logger.error(f"Error saving blacklist to Redis: {e}")
    
    def _update_proxy_stats(self, proxy_id: str, action: str):
        """Update proxy statistics"""
        if proxy_id not in self.proxy_stats:
            return
        
        stats = self.proxy_stats[proxy_id]
        current_time = time.time()
        
        if action == 'used':
            stats.usage_count += 1
            stats.last_used = current_time
        elif action == 'success':
            stats.success_count += 1
            stats.last_success = current_time
        elif action == 'failure':
            stats.failure_count += 1
            stats.last_failure = current_time
        
        # Update error rate
        if stats.usage_count > 0:
            stats.error_rate = stats.failure_count / stats.usage_count
    
    async def add_proxy(self, proxy_id: str, proxy_config: ProxyConfig):
        """Add a new proxy to the pool"""
        self.proxies[proxy_id] = proxy_config
        self.proxy_stats[proxy_id] = ProxyStats(proxy_id=proxy_id)
        
        self.logger.info(f"Added proxy: {proxy_id} ({proxy_config.host}:{proxy_config.port})")
    
    async def remove_proxy(self, proxy_id: str):
        """Remove a proxy from the pool"""
        if proxy_id in self.proxies:
            del self.proxies[proxy_id]
        
        if proxy_id in self.proxy_stats:
            del self.proxy_stats[proxy_id]
        
        # Remove from Redis
        if self.redis_client:
            try:
                await self.redis_client.hdel(self.blacklist_key, proxy_id)
                await self.redis_client.hdel(self.stats_key, proxy_id)
            except Exception as e:
                self.logger.error(f"Error removing proxy from Redis: {e}")
        
        self.logger.info(f"Removed proxy: {proxy_id}")
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get proxy manager metrics"""
        total_proxies = len(self.proxies)
        available_proxies = sum(
            1 for proxy_id in self.proxies.keys()
            if self._is_proxy_available(proxy_id)
        )
        blacklisted_proxies = sum(
            1 for stats in self.proxy_stats.values()
            if stats.blacklisted_until and stats.blacklisted_until > time.time()
        )
        
        # Calculate average success rate
        total_usage = sum(stats.usage_count for stats in self.proxy_stats.values())
        total_successes = sum(stats.success_count for stats in self.proxy_stats.values())
        avg_success_rate = total_successes / total_usage if total_usage > 0 else 0
        
        return {
            "total_proxies": total_proxies,
            "available_proxies": available_proxies,
            "blacklisted_proxies": blacklisted_proxies,
            "rotation_strategy": self.rotation_strategy.value,
            "blacklist_duration": self.blacklist_duration,
            "max_failure_rate": self.max_failure_rate,
            "average_success_rate": avg_success_rate,
            "redis_backend": self.redis_client is not None
        }
    
    async def cleanup_expired_blacklist(self):
        """Clean up expired blacklist entries"""
        current_time = time.time()
        
        for proxy_id, stats in self.proxy_stats.items():
            if stats.blacklisted_until and stats.blacklisted_until <= current_time:
                stats.blacklisted_until = None
                
                # Remove from Redis blacklist
                if self.redis_client:
                    try:
                        await self.redis_client.hdel(self.blacklist_key, proxy_id)
                    except Exception as e:
                        self.logger.error(f"Error removing from Redis blacklist: {e}")
                
                self.logger.info(f"Removed {proxy_id} from blacklist")
    
    async def save_config(self, file_path: str):
        """Save current proxy configuration to file"""
        try:
            config_data = {}
            for proxy_id, proxy in self.proxies.items():
                config_data[proxy_id] = {
                    'host': proxy.host,
                    'port': proxy.port,
                    'protocol': proxy.protocol,
                    'username': proxy.username,
                    'password': proxy.password,
                    'weight': proxy.weight,
                    'max_connections': proxy.max_connections,
                    'timeout': proxy.timeout,
                    'country': proxy.country,
                    'anonymous': proxy.anonymous
                }
            
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(config_data, indent=2))
            
            self.logger.info(f"Saved proxy configuration to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving proxy configuration: {e}")
