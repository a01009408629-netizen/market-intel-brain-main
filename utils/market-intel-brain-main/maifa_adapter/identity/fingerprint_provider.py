"""
Fingerprint Provider Implementation

This module provides TLS fingerprinting and session management for stealth
browsing to bypass anti-bot protections like Cloudflare.
"""

import asyncio
import random
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from contextlib import asynccontextmanager
import hashlib
import time

try:
    import curl_cffi
    CURL_CFFI_AVAILABLE = True
except ImportError:
    CURL_CFFI_AVAILABLE = False
    import httpx
    import ssl

from ..core.exceptions import TransientAdapterError


@dataclass
class TLSFingerprint:
    """TLS fingerprint configuration"""
    ja3_hash: str
    user_agent: str
    accept_language: str
    accept_encoding: str
    accept: str
    connection: str
    upgrade_insecure_requests: str
    sec_fetch_dest: str
    sec_fetch_mode: str
    sec_fetch_site: str
    sec_fetch_user: str
    cache_control: str
    pragma: str


class FingerprintProvider:
    """
    Provider for generating realistic browser fingerprints.
    
    Creates TLS fingerprints that mimic popular browsers like Chrome and Safari
    to bypass anti-bot protections and detection systems.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("FingerprintProvider")
        
        # Predefined browser fingerprints
        self.chrome_fingerprints = self._generate_chrome_fingerprints()
        self.safari_fingerprints = self._generate_safari_fingerprints()
        self.firefox_fingerprints = self._generate_firefox_fingerprints()
        
        # Current fingerprint cache
        self._current_fingerprint: Optional[TLSFingerprint] = None
        self._fingerprint_rotation_time = 300  # 5 minutes
        self._last_rotation = time.time()
    
    def _generate_chrome_fingerprints(self) -> List[TLSFingerprint]:
        """Generate Chrome browser fingerprints"""
        fingerprints = []
        
        # Chrome versions and user agents
        chrome_versions = [
            "120.0.6099.129",
            "120.0.6099.110", 
            "119.0.6045.199",
            "119.0.6045.123",
            "118.0.5993.88"
        ]
        
        for version in chrome_versions:
            ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{version} Safari/537.36"
            
            fingerprint = TLSFingerprint(
                ja3_hash=hashlib.md5(ua.encode()).hexdigest()[:32],
                user_agent=ua,
                accept_language="en-US,en;q=0.9",
                accept_encoding="gzip, deflate, br",
                accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                connection="keep-alive",
                upgrade_insecure_requests="1",
                sec_fetch_dest="empty",
                sec_fetch_mode="cors",
                sec_fetch_site="cross-site",
                sec_fetch_user="?0",
                cache_control="max-age=0",
                pragma="no-cache"
            )
            fingerprints.append(fingerprint)
        
        return fingerprints
    
    def _generate_safari_fingerprints(self) -> List[TLSFingerprint]:
        """Generate Safari browser fingerprints"""
        fingerprints = []
        
        safari_versions = [
            "17.1.2",
            "17.1.1",
            "17.0.2",
            "16.6.1",
            "16.5.2"
        ]
        
        for version in safari_versions:
            ua = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/{version} Safari/605.1.15"
            
            fingerprint = TLSFingerprint(
                ja3_hash=hashlib.md5(ua.encode()).hexdigest()[:32],
                user_agent=ua,
                accept_language="en-US,en;q=0.9",
                accept_encoding="gzip, deflate, br",
                accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                connection="keep-alive",
                upgrade_insecure_requests="1",
                sec_fetch_dest="empty",
                sec_fetch_mode="cors",
                sec_fetch_site="cross-site",
                sec_fetch_user="?0",
                cache_control="max-age=0",
                pragma="no-cache"
            )
            fingerprints.append(fingerprint)
        
        return fingerprints
    
    def _generate_firefox_fingerprints(self) -> List[TLSFingerprint]:
        """Generate Firefox browser fingerprints"""
        fingerprints = []
        
        firefox_versions = [
            "121.0",
            "120.0.1",
            "119.0.1",
            "118.0.2",
            "117.0"
        ]
        
        for version in firefox_versions:
            ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}) Gecko/20100101 Firefox/{version}"
            
            fingerprint = TLSFingerprint(
                ja3_hash=hashlib.md5(ua.encode()).hexdigest()[:32],
                user_agent=ua,
                accept_language="en-US,en;q=0.5",
                accept_encoding="gzip, deflate, br",
                accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                connection="keep-alive",
                upgrade_insecure_requests="1",
                sec_fetch_dest="empty",
                sec_fetch_mode="cors",
                sec_fetch_site="cross-site",
                sec_fetch_user="?0",
                cache_control="max-age=0",
                pragma="no-cache"
            )
            fingerprints.append(fingerprint)
        
        return fingerprints
    
    def get_random_fingerprint(self, browser_type: Optional[str] = None) -> TLSFingerprint:
        """
        Get a random browser fingerprint.
        
        Args:
            browser_type: Specific browser type ('chrome', 'safari', 'firefox')
                          or None for random selection
        
        Returns:
            TLSFingerprint object
        """
        # Check if we need to rotate fingerprint
        current_time = time.time()
        if (current_time - self._last_rotation) > self._fingerprint_rotation_time:
            self._current_fingerprint = None
            self._last_rotation = current_time
        
        # Return cached fingerprint if available
        if self._current_fingerprint:
            return self._current_fingerprint
        
        # Select fingerprint pool
        if browser_type == 'chrome':
            pool = self.chrome_fingerprints
        elif browser_type == 'safari':
            pool = self.safari_fingerprints
        elif browser_type == 'firefox':
            pool = self.firefox_fingerprints
        else:
            # Random selection from all browsers
            pool = self.chrome_fingerprints + self.safari_fingerprints + self.firefox_fingerprints
        
        # Select random fingerprint
        self._current_fingerprint = random.choice(pool)
        
        self.logger.debug(
            f"Generated {browser_type or 'random'} fingerprint: "
            f"{self._current_fingerprint.user_agent[:50]}..."
        )
        
        return self._current_fingerprint
    
    def get_fingerprint_headers(self, fingerprint: Optional[TLSFingerprint] = None) -> Dict[str, str]:
        """
        Convert fingerprint to HTTP headers.
        
        Args:
            fingerprint: TLS fingerprint object or None for random
            
        Returns:
            Dictionary of HTTP headers
        """
        if fingerprint is None:
            fingerprint = self.get_random_fingerprint()
        
        return {
            "User-Agent": fingerprint.user_agent,
            "Accept-Language": fingerprint.accept_language,
            "Accept-Encoding": fingerprint.accept_encoding,
            "Accept": fingerprint.accept,
            "Connection": fingerprint.connection,
            "Upgrade-Insecure-Requests": fingerprint.upgrade_insecure_requests,
            "Sec-Fetch-Dest": fingerprint.sec_fetch_dest,
            "Sec-Fetch-Mode": fingerprint.sec_fetch_mode,
            "Sec-Fetch-Site": fingerprint.sec_fetch_site,
            "Sec-Fetch-User": fingerprint.sec_fetch_user,
            "Cache-Control": fingerprint.cache_control,
            "Pragma": fingerprint.pragma
        }


class AsyncSessionManager:
    """
    Async session manager with TLS fingerprinting and proxy support.
    
    Creates sessions that mimic real browsers to bypass anti-bot
    protections and detection systems.
    """
    
    def __init__(
        self,
        fingerprint_provider: Optional[FingerprintProvider] = None,
        proxy_manager: Optional['ProxyManager'] = None,
        timeout: float = 30.0,
        logger: Optional[logging.Logger] = None
    ):
        self.fingerprint_provider = fingerprint_provider or FingerprintProvider()
        self.proxy_manager = proxy_manager
        self.timeout = timeout
        self.logger = logger or logging.getLogger("AsyncSessionManager")
        
        # Session pool
        self._session_pool: List[Any] = []
        self._max_sessions = 10
        self._session_counter = 0
        
        # Initialize curl_cffi if available
        if CURL_CFFI_AVAILABLE:
            self._init_curl_sessions()
        else:
            self._init_httpx_sessions()
    
    def _init_curl_sessions(self):
        """Initialize curl_cffi sessions with TLS fingerprinting"""
        for i in range(self._max_sessions):
            # Get random fingerprint
            fingerprint = self.fingerprint_provider.get_random_fingerprint()
            headers = self.fingerprint_provider.get_fingerprint_headers(fingerprint)
            
            # Create curl session
            session = curl_cffi.Session(
                headers=headers,
                timeout=self.timeout,
                impersonate="chrome"  # or "safari", "firefox"
            )
            
            self._session_pool.append({
                'session': session,
                'fingerprint': fingerprint,
                'headers': headers,
                'in_use': False,
                'created_at': time.time()
            })
        
        self.logger.info(f"Initialized {self._max_sessions} curl_cffi sessions")
    
    def _init_httpx_sessions(self):
        """Initialize httpx sessions with TLS fingerprinting"""
        for i in range(self._max_sessions):
            # Get random fingerprint
            fingerprint = self.fingerprint_provider.get_random_fingerprint()
            headers = self.fingerprint_provider.get_fingerprint_headers(fingerprint)
            
            # Create SSL context for fingerprinting
            ssl_context = ssl.create_default_context()
            
            # Create httpx session
            session = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                verify=True,
                http2=True,
                follow_redirects=True
            )
            
            self._session_pool.append({
                'session': session,
                'fingerprint': fingerprint,
                'headers': headers,
                'in_use': False,
                'created_at': time.time()
            })
        
        self.logger.info(f"Initialized {self._max_sessions} httpx sessions")
    
    @asynccontextmanager
    async def get_session(self, browser_type: Optional[str] = None):
        """
        Get a session with fingerprint and proxy.
        
        Args:
            browser_type: Specific browser type for fingerprint
            
        Yields:
            Session object with fingerprint and proxy applied
        """
        session_data = None
        
        try:
            # Find available session
            for session_info in self._session_pool:
                if not session_info['in_use']:
                    session_info['in_use'] = True
                    session_data = session_info
                    break
            
            # Create new session if none available
            if session_data is None:
                session_data = await self._create_new_session(browser_type)
            
            # Apply proxy if available
            if self.proxy_manager:
                proxy = await self.proxy_manager.get_proxy()
                if proxy:
                    await self._apply_proxy_to_session(session_data, proxy)
            
            self.logger.debug(
                f"Providing session with fingerprint: "
                f"{session_data['fingerprint'].user_agent[:50]}..."
            )
            
            yield session_data['session']
            
        except Exception as e:
            self.logger.error(f"Error getting session: {e}")
            raise TransientAdapterError(
                message=f"Failed to get session: {str(e)}",
                adapter_name="AsyncSessionManager"
            ) from e
        
        finally:
            # Mark session as available
            if session_data:
                session_data['in_use'] = False
                
                # Rotate session if too old
                if time.time() - session_data['created_at'] > 3600:  # 1 hour
                    await self._rotate_session(session_data)
    
    async def _create_new_session(self, browser_type: Optional[str] = None) -> Dict[str, Any]:
        """Create a new session with fingerprint"""
        # Get fingerprint
        fingerprint = self.fingerprint_provider.get_random_fingerprint(browser_type)
        headers = self.fingerprint_provider.get_fingerprint_headers(fingerprint)
        
        if CURL_CFFI_AVAILABLE:
            session = curl_cffi.Session(
                headers=headers,
                timeout=self.timeout,
                impersonate=browser_type or "chrome"
            )
        else:
            session = httpx.AsyncClient(
                headers=headers,
                timeout=self.timeout,
                verify=True,
                http2=True,
                follow_redirects=True
            )
        
        session_data = {
            'session': session,
            'fingerprint': fingerprint,
            'headers': headers,
            'in_use': False,
            'created_at': time.time()
        }
        
        self._session_pool.append(session_data)
        return session_data
    
    async def _apply_proxy_to_session(self, session_data: Dict[str, Any], proxy: Dict[str, Any]):
        """Apply proxy to session"""
        try:
            if CURL_CFFI_AVAILABLE:
                # Apply proxy to curl_cffi session
                session = session_data['session']
                proxy_url = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
                
                if proxy.get('username') and proxy.get('password'):
                    proxy_url = f"{proxy['username']}:{proxy['password']}@{proxy_url}"
                
                session.proxies = {"http": proxy_url, "https": proxy_url}
                
            else:
                # Apply proxy to httpx session
                session = session_data['session']
                proxy_url = f"{proxy['protocol']}://{proxy['host']}:{proxy['port']}"
                
                if proxy.get('username') and proxy.get('password'):
                    proxy_url = f"{proxy['protocol']}://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
                
                session.proxies = {
                    "http://": proxy_url,
                    "https://": proxy_url
                }
            
            self.logger.debug(f"Applied proxy: {proxy['host']}:{proxy['port']}")
            
        except Exception as e:
            self.logger.error(f"Error applying proxy: {e}")
    
    async def _rotate_session(self, session_data: Dict[str, Any]):
        """Rotate an old session"""
        try:
            # Close old session
            if hasattr(session_data['session'], 'close'):
                if asyncio.iscoroutinefunction(session_data['session'].close):
                    await session_data['session'].close()
                else:
                    session_data['session'].close()
            
            # Remove from pool
            if session_data in self._session_pool:
                self._session_pool.remove(session_data)
            
            self.logger.debug("Rotated old session")
            
        except Exception as e:
            self.logger.error(f"Error rotating session: {e}")
    
    async def close_all_sessions(self):
        """Close all sessions"""
        close_tasks = []
        
        for session_data in self._session_pool:
            try:
                if hasattr(session_data['session'], 'close'):
                    if asyncio.iscoroutinefunction(session_data['session'].close):
                        close_tasks.append(session_data['session'].close())
                    else:
                        session_data['session'].close()
            except Exception as e:
                self.logger.error(f"Error closing session: {e}")
        
        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)
        
        self._session_pool.clear()
        self.logger.info("Closed all sessions")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get session manager metrics"""
        active_sessions = sum(1 for s in self._session_pool if s['in_use'])
        available_sessions = len(self._session_pool) - active_sessions
        
        return {
            "total_sessions": len(self._session_pool),
            "active_sessions": active_sessions,
            "available_sessions": available_sessions,
            "max_sessions": self._max_sessions,
            "backend": "curl_cffi" if CURL_CFFI_AVAILABLE else "httpx",
            "proxy_manager_available": self.proxy_manager is not None
        }
