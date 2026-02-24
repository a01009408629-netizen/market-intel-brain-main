"""
Asynchronous Audit Logging - Non-blocking SIEM Integration

Enterprise-grade audit logging with memory buffering,
batch flushing, and zero-blocking I/O operations.
"""

import asyncio
import json
import logging
import os
import threading
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Callable
import uuid
import gzip

from .config import SecurityConfig, AuditLevel


class AuditEventType(Enum):
    """Audit event types."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    ENCRYPTION = "encryption"
    DECRYPTION = "decryption"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_EVENT = "system_event"
    SECURITY_VIOLATION = "security_violation"
    API_CALL = "api_call"
    ERROR = "error"


class AuditOutcome(Enum):
    """Audit event outcomes."""
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"
    BLOCKED = "blocked"
    WARNING = "warning"


@dataclass
class AuditEvent:
    """Audit event structure."""
    
    # Core event information
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType = AuditEventType.SYSTEM_EVENT
    outcome: AuditOutcome = AuditOutcome.SUCCESS
    level: AuditLevel = AuditLevel.MEDIUM
    
    # Timestamps
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: Optional[float] = None
    
    # Actor information
    user_id: Optional[str] = None
    service_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Resource information
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    
    # Event details
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Security context
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Compliance
    compliance_tags: List[str] = field(default_factory=list)
    retention_days: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary."""
        data = asdict(self)
        # Convert datetime to ISO string
        data["timestamp"] = self.timestamp.isoformat()
        # Convert enums to strings
        data["event_type"] = self.event_type.value
        data["outcome"] = self.outcome.value
        data["level"] = self.level.value
        return data
    
    def to_json(self) -> str:
        """Convert audit event to JSON string."""
        return json.dumps(self.to_dict(), separators=(',', ':'), ensure_ascii=False)


class AuditBuffer:
    """Thread-safe audit event buffer."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._dropped_count = 0
    
    def append(self, event: AuditEvent) -> bool:
        """Append event to buffer."""
        with self._lock:
            if len(self._buffer) >= self.max_size:
                self._dropped_count += 1
                return False
            self._buffer.append(event)
            return True
    
    def extend(self, events: List[AuditEvent]) -> int:
        """Extend buffer with multiple events."""
        added_count = 0
        with self._lock:
            for event in events:
                if len(self._buffer) < self.max_size:
                    self._buffer.append(event)
                    added_count += 1
                else:
                    self._dropped_count += len(events) - added_count
                    break
        return added_count
    
    def flush(self) -> List[AuditEvent]:
        """Flush all events from buffer."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
            return events
    
    def size(self) -> int:
        """Get current buffer size."""
        with self._lock:
            return len(self._buffer)
    
    def get_dropped_count(self) -> int:
        """Get count of dropped events."""
        with self._lock:
            return self._dropped_count


class AsyncAuditLogger:
    """
    Asynchronous audit logger with memory buffering.
    
    Features:
    - Non-blocking I/O operations
    - Memory buffering with batch flushing
    - SIEM integration
    - File rotation
    - Performance monitoring
    """
    
    def __init__(
        self,
        config: Optional[SecurityConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.config = config or SecurityConfig()
        self.logger = logger or logging.getLogger("AsyncAuditLogger")
        
        # Audit buffer
        self.buffer = AuditBuffer(max_size=self.config.audit_buffer_size)
        
        # Background tasks
        self.flush_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # File handling
        self.log_file_path = Path(self.config.audit_log_path)
        self.log_file_lock = threading.Lock()
        
        # Performance metrics
        self.events_logged = 0
        self.events_flushed = 0
        self.events_dropped = 0
        self.total_flush_time_ms = 0.0
        self.flush_errors = 0
        
        # SIEM integration
        self.siem_session = None
        self._initialize_siem()
        
        self.logger.info(f"AsyncAuditLogger initialized: buffer_size={self.config.audit_buffer_size}")
    
    def _initialize_siem(self):
        """Initialize SIEM integration."""
        if self.config.audit_siem_endpoint:
            try:
                import aiohttp
                self.siem_session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"Content-Type": "application/json"}
                )
                self.logger.info(f"SIEM integration initialized: {self.config.audit_siem_endpoint}")
            except ImportError:
                self.logger.warning("aiohttp not available, SIEM integration disabled")
            except Exception as e:
                self.logger.error(f"Failed to initialize SIEM integration: {e}")
    
    async def start(self):
        """Start audit logger background tasks."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Create log directory if not exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Start background flush task
        self.flush_task = asyncio.create_task(self._flush_loop())
        
        self.logger.info("AsyncAuditLogger started")
    
    async def stop(self):
        """Stop audit logger and cleanup."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel flush task
        if self.flush_task:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self._flush_events()
        
        # Close SIEM session
        if self.siem_session:
            await self.siem_session.close()
        
        self.logger.info("AsyncAuditLogger stopped")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        description: str,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        level: AuditLevel = AuditLevel.MEDIUM,
        **kwargs
    ) -> str:
        """
        Log audit event asynchronously.
        
        Args:
            event_type: Type of event
            description: Event description
            outcome: Event outcome
            level: Audit level
            **kwargs: Additional event fields
            
        Returns:
            Event ID
        """
        try:
            # Create audit event
            event = AuditEvent(
                event_type=event_type,
                description=description,
                outcome=outcome,
                level=level,
                **kwargs
            )
            
            # Add to buffer
            if self.buffer.append(event):
                self.events_logged += 1
                self.logger.debug(f"Audit event logged: {event.event_id}")
                return event.event_id
            else:
                self.events_dropped += 1
                self.logger.warning("Audit buffer full, event dropped")
                return ""
                
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
            return ""
    
    async def log_authentication(
        self,
        user_id: str,
        outcome: AuditOutcome,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log authentication event."""
        return await self.log_event(
            event_type=AuditEventType.AUTHENTICATION,
            description=f"Authentication attempt for user: {user_id}",
            outcome=outcome,
            level=AuditLevel.HIGH if outcome == AuditOutcome.FAILURE else AuditLevel.MEDIUM,
            user_id=user_id,
            ip_address=ip_address,
            details=details or {}
        )
    
    async def log_data_access(
        self,
        user_id: str,
        resource_id: str,
        resource_type: str,
        action: str,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log data access event."""
        return await self.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            description=f"Data access: {action} on {resource_type}:{resource_id}",
            outcome=outcome,
            level=AuditLevel.MEDIUM,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            action=action,
            details=details or {}
        )
    
    async def log_encryption(
        self,
        operation: str,
        outcome: AuditOutcome,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log encryption event."""
        return await self.log_event(
            event_type=AuditEventType.ENCRYPTION,
            description=f"Encryption operation: {operation}",
            outcome=outcome,
            level=AuditLevel.LOW,
            details=details or {}
        )
    
    async def log_security_violation(
        self,
        violation_type: str,
        description: str,
        severity: AuditLevel = AuditLevel.HIGH,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log security violation event."""
        return await self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            description=f"Security violation: {violation_type} - {description}",
            outcome=AuditOutcome.BLOCKED,
            level=severity,
            details=details or {}
        )
    
    async def _flush_loop(self):
        """Background flush loop."""
        while self.is_running:
            try:
                await asyncio.sleep(self.config.audit_flush_interval_seconds)
                await self._flush_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in flush loop: {e}")
    
    async def _flush_events(self):
        """Flush buffered events to storage."""
        start_time = time.time()
        
        try:
            # Get events from buffer
            events = self.buffer.flush()
            
            if not events:
                return
            
            # Write to file
            await self._write_to_file(events)
            
            # Send to SIEM
            if self.siem_session:
                await self._send_to_siem(events)
            
            # Update metrics
            self.events_flushed += len(events)
            flush_time = (time.time() - start_time) * 1000
            self.total_flush_time_ms += flush_time
            
            if flush_time > self.config.max_audit_log_time_ms:
                self.logger.warning(f"Audit flush exceeded time limit: {flush_time:.2f}ms")
            
            self.logger.debug(f"Flushed {len(events)} audit events in {flush_time:.2f}ms")
            
        except Exception as e:
            self.flush_errors += 1
            self.logger.error(f"Failed to flush audit events: {e}")
    
    async def _write_to_file(self, events: List[AuditEvent]):
        """Write events to log file (non-blocking)."""
        try:
            # Prepare log entries
            log_entries = []
            for event in events:
                log_entries.append(event.to_json())
            
            # Write to file in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._write_to_file_sync,
                log_entries
            )
            
        except Exception as e:
            self.logger.error(f"Failed to write audit events to file: {e}")
    
    def _write_to_file_sync(self, log_entries: List[str]):
        """Synchronous file write operation."""
        try:
            with self.log_file_lock:
                # Create log file with timestamp
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
                log_file = self.log_file_path.parent / f"audit_{timestamp}.log"
                
                # Append to log file
                with open(log_file, 'a', encoding='utf-8') as f:
                    for entry in log_entries:
                        f.write(entry + '\n')
                
                # Rotate if file is too large
                if log_file.stat().st_size > 100 * 1024 * 1024:  # 100MB
                    self._rotate_log_file(log_file)
                    
        except Exception as e:
            self.logger.error(f"Sync file write failed: {e}")
    
    def _rotate_log_file(self, log_file: Path):
        """Rotate log file."""
        try:
            # Compress old file
            compressed_file = log_file.with_suffix('.log.gz')
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Remove original file
            log_file.unlink()
            
            self.logger.info(f"Log file rotated: {log_file}")
            
        except Exception as e:
            self.logger.error(f"Log rotation failed: {e}")
    
    async def _send_to_siem(self, events: List[AuditEvent]):
        """Send events to SIEM endpoint."""
        try:
            # Prepare SIEM payload
            payload = {
                "events": [event.to_dict() for event in events],
                "source": {
                    "service": self.config.service_id,
                    "namespace": self.config.service_namespace,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
            # Send to SIEM
            async with self.siem_session.post(
                self.config.audit_siem_endpoint,
                json=payload
            ) as response:
                if response.status == 200:
                    self.logger.debug(f"Sent {len(events)} events to SIEM")
                else:
                    self.logger.warning(f"SIEM upload failed: {response.status}")
                    
        except Exception as e:
            self.logger.error(f"Failed to send events to SIEM: {e}")
    
    @asynccontextmanager
    async def audit_context(
        self,
        event_type: AuditEventType,
        description: str,
        **kwargs
    ):
        """Context manager for audit operations."""
        event_id = await self.log_event(
            event_type=event_type,
            description=f"Started: {description}",
            **kwargs
        )
        
        start_time = time.time()
        
        try:
            yield event_id
            
            # Log successful completion
            await self.log_event(
                event_type=event_type,
                description=f"Completed: {description}",
                outcome=AuditOutcome.SUCCESS,
                duration_ms=(time.time() - start_time) * 1000,
                **kwargs
            )
            
        except Exception as e:
            # Log failure
            await self.log_event(
                event_type=event_type,
                description=f"Failed: {description} - {str(e)}",
                outcome=AuditOutcome.ERROR,
                duration_ms=(time.time() - start_time) * 1000,
                details={"error": str(e)},
                **kwargs
            )
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get audit logger metrics."""
        avg_flush_time = self.total_flush_time_ms / max(self.events_flushed, 1)
        
        return {
            "audit_metrics": {
                "events": {
                    "logged": self.events_logged,
                    "flushed": self.events_flushed,
                    "dropped": self.events_dropped,
                    "buffer_size": self.buffer.size(),
                    "dropped_count": self.buffer.get_dropped_count()
                },
                "performance": {
                    "avg_flush_time_ms": avg_flush_time,
                    "total_flush_time_ms": self.total_flush_time_ms,
                    "flush_interval_seconds": self.config.audit_flush_interval_seconds,
                    "flush_errors": self.flush_errors
                },
                "configuration": {
                    "buffer_size": self.config.audit_buffer_size,
                    "retention_days": self.config.audit_retention_days,
                    "log_path": str(self.config.log_file_path),
                    "siem_endpoint": self.config.audit_siem_endpoint
                }
            }
        }


# Global audit logger instance
_audit_logger: Optional[AsyncAuditLogger] = None


def get_audit_logger(config: Optional[SecurityConfig] = None) -> AsyncAuditLogger:
    """Get or create global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AsyncAuditLogger(config)
    return _audit_logger


async def initialize_audit_logger(config: Optional[SecurityConfig] = None) -> AsyncAuditLogger:
    """Initialize and start global audit logger."""
    logger = get_audit_logger(config)
    await logger.start()
    return logger
