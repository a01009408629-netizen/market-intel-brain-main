"""
Dead Letter Queue (DLQ) - Data Recovery System

Enterprise-grade dead letter queue for capturing and storing rejected data
from the quality gateway for later reprocessing and analysis.
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import hashlib
from pathlib import Path

from .data_quality_gateway import (
    ValidationResult,
    QualityLevel,
    ValidationIssue,
    ValidationSeverity
)


class DLQStatus(Enum):
    """Status of DLQ entries."""
    PENDING = "pending"           # Waiting for reprocessing
    PROCESSING = "processing"     # Currently being reprocessed
    RETRIED = "retried"          # Has been reprocessed
    FAILED = "failed"            # Final failure after retries
    ARCHIVED = "archived"         # Manually archived


class ReprocessingStrategy(Enum):
    """Strategies for reprocessing DLQ entries."""
    IMMEDIATE = "immediate"       # Reprocess immediately
    DELAYED = "delayed"          # Reprocess after delay
    MANUAL = "manual"            # Manual reprocessing only
    ADAPTIVE = "adaptive"         # Adaptive based on error type


@dataclass
class DLQEntry:
    """Dead letter queue entry."""
    
    # Core identification
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_id: Optional[str] = None  # Original data ID if available
    
    # Data content
    original_data: Dict[str, Any] = field(default_factory=dict)
    data_type: str = "unknown"  # Type of original data
    source: str = "unknown"     # Data source
    
    # Validation information
    validation_result: Optional[ValidationResult] = None
    rejection_reason: str = ""
    error_details: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_attempt: Optional[datetime] = None
    next_retry: Optional[datetime] = None
    
    # Retry information
    retry_count: int = 0
    max_retries: int = 3
    retry_strategy: ReprocessingStrategy = ReprocessingStrategy.DELAYED
    
    # Status and metadata
    status: DLQStatus = DLQStatus.PENDING
    priority: int = 0  # Higher priority = processed first
    
    # Processing results
    processing_attempts: List[Dict[str, Any]] = field(default_factory=list)
    final_outcome: Optional[str] = None
    
    # Custom metadata
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "entry_id": self.entry_id,
            "original_id": self.original_id,
            "original_data": self.original_data,
            "data_type": self.data_type,
            "source": self.source,
            "validation_result": self.validation_result.__dict__ if self.validation_result else None,
            "rejection_reason": self.rejection_reason,
            "error_details": self.error_details,
            "created_at": self.created_at.isoformat(),
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "next_retry": self.next_retry.isoformat() if self.next_retry else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "retry_strategy": self.retry_strategy.value,
            "status": self.status.value,
            "priority": self.priority,
            "processing_attempts": self.processing_attempts,
            "final_outcome": self.final_outcome,
            "custom_metadata": self.custom_metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DLQEntry":
        """Create from dictionary."""
        # Handle datetime fields
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        last_attempt = datetime.fromisoformat(data["last_attempt"]) if data.get("last_attempt") else None
        next_retry = datetime.fromisoformat(data["next_retry"]) if data.get("next_retry") else None
        
        # Handle validation result
        validation_result = None
        if data.get("validation_result"):
            vr_data = data["validation_result"]
            validation_result = ValidationResult(
                is_valid=vr_data.get("is_valid", False),
                quality_level=QualityLevel(vr_data.get("quality_level", "medium")),
                issues=[ValidationIssue(**issue) for issue in vr_data.get("issues", [])],
                processing_time_ms=vr_data.get("processing_time_ms", 0.0),
                validation_id=vr_data.get("validation_id", ""),
                timestamp=datetime.fromisoformat(vr_data["timestamp"]) if vr_data.get("timestamp") else datetime.now(timezone.utc)
            )
        
        return cls(
            entry_id=data.get("entry_id", str(uuid.uuid4())),
            original_id=data.get("original_id"),
            original_data=data.get("original_data", {}),
            data_type=data.get("data_type", "unknown"),
            source=data.get("source", "unknown"),
            validation_result=validation_result,
            rejection_reason=data.get("rejection_reason", ""),
            error_details=data.get("error_details", []),
            created_at=created_at,
            last_attempt=last_attempt,
            next_retry=next_retry,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            retry_strategy=ReprocessingStrategy(data.get("retry_strategy", "delayed")),
            status=DLQStatus(data.get("status", "pending")),
            priority=data.get("priority", 0),
            processing_attempts=data.get("processing_attempts", []),
            final_outcome=data.get("final_outcome"),
            custom_metadata=data.get("custom_metadata", {})
        )


class DeadLetterQueue:
    """
    Enterprise-grade dead letter queue for handling rejected data.
    
    Captures, stores, and manages data that fails validation
    for later reprocessing and analysis.
    """
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        max_entries: int = 10000,
        auto_reprocess: bool = True,
        reprocessing_interval: int = 300,  # 5 minutes
        logger: Optional[logging.Logger] = None
    ):
        self.storage_path = Path(storage_path) if storage_path else Path("dlq_storage")
        self.max_entries = max_entries
        self.auto_reprocess = auto_reprocess
        self.reprocessing_interval = reprocessing_interval
        self.logger = logger or logging.getLogger("DeadLetterQueue")
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for active entries
        self._entries: Dict[str, DLQEntry] = {}
        self._pending_retries: List[str] = []
        
        # Statistics
        self._stats = {
            "total_entries": 0,
            "pending_entries": 0,
            "processing_entries": 0,
            "retried_entries": 0,
            "failed_entries": 0,
            "archived_entries": 0,
            "successful_reprocesses": 0,
            "failed_reprocesses": 0
        }
        
        # Reprocessing task
        self._reprocess_task: Optional[asyncio.Task] = None
        
        self.logger.info(f"DeadLetterQueue initialized: storage_path={self.storage_path}")
    
    async def initialize(self) -> bool:
        """Initialize DLQ and load existing entries."""
        try:
            await self._load_entries()
            
            if self.auto_reprocess:
                self._reprocess_task = asyncio.create_task(self._reprocessing_loop())
            
            self.logger.info(f"DLQ initialized with {len(self._entries)} entries")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize DLQ: {e}")
            return False
    
    async def close(self) -> None:
        """Close DLQ and save entries."""
        try:
            if self._reprocess_task:
                self._reprocess_task.cancel()
                try:
                    await self._reprocess_task
                except asyncio.CancelledError:
                    pass
            
            await self._save_entries()
            self.logger.info("DLQ closed successfully")
            
        except Exception as e:
            self.logger.error(f"Error closing DLQ: {e}")
    
    async def add_entry(
        self,
        original_data: Dict[str, Any],
        validation_result: ValidationResult,
        data_type: str = "unknown",
        source: str = "unknown",
        original_id: Optional[str] = None,
        retry_strategy: ReprocessingStrategy = ReprocessingStrategy.DELAYED,
        priority: int = 0
    ) -> str:
        """Add rejected data to DLQ."""
        try:
            # Create DLQ entry
            entry = DLQEntry(
                original_data=original_data,
                data_type=data_type,
                source=source,
                original_id=original_id,
                validation_result=validation_result,
                rejection_reason=self._extract_rejection_reason(validation_result),
                error_details=self._extract_error_details(validation_result),
                retry_strategy=retry_strategy,
                priority=priority
            )
            
            # Store entry
            self._entries[entry.entry_id] = entry
            
            # Schedule retry if needed
            if entry.retry_strategy != ReprocessingStrategy.MANUAL:
                entry.next_retry = self._calculate_next_retry(entry)
                self._pending_retries.append(entry.entry_id)
            
            # Update statistics
            self._stats["total_entries"] += 1
            self._stats["pending_entries"] += 1
            
            # Save to disk
            await self._save_entry(entry)
            
            self.logger.info(f"Added DLQ entry: {entry.entry_id} (type: {data_type}, source: {source})")
            return entry.entry_id
            
        except Exception as e:
            self.logger.error(f"Failed to add DLQ entry: {e}")
            raise
    
    async def get_entry(self, entry_id: str) -> Optional[DLQEntry]:
        """Get DLQ entry by ID."""
        return self._entries.get(entry_id)
    
    async def get_entries(
        self,
        status: Optional[DLQStatus] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DLQEntry]:
        """Get DLQ entries with filtering."""
        entries = list(self._entries.values())
        
        # Apply filters
        if status:
            entries = [e for e in entries if e.status == status]
        
        if data_type:
            entries = [e for e in entries if e.data_type == data_type]
        
        if source:
            entries = [e for e in entries if e.source == source]
        
        # Sort by priority and creation time
        entries.sort(key=lambda e: (-e.priority, e.created_at))
        
        # Apply pagination
        return entries[offset:offset + limit]
    
    async def retry_entry(self, entry_id: str, reprocess_func: Callable) -> bool:
        """Manually retry a DLQ entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            self.logger.warning(f"DLQ entry not found: {entry_id}")
            return False
        
        if entry.status != DLQStatus.PENDING:
            self.logger.warning(f"DLQ entry not in pending status: {entry_id}")
            return False
        
        return await self._process_entry(entry, reprocess_func)
    
    async def archive_entry(self, entry_id: str) -> bool:
        """Archive a DLQ entry."""
        entry = self._entries.get(entry_id)
        if not entry:
            return False
        
        entry.status = DLQStatus.ARCHIVED
        entry.final_outcome = "manually_archived"
        
        self._stats["archived_entries"] += 1
        await self._save_entry(entry)
        
        self.logger.info(f"Archived DLQ entry: {entry_id}")
        return True
    
    async def delete_entry(self, entry_id: str) -> bool:
        """Delete a DLQ entry."""
        if entry_id in self._entries:
            entry = self._entries[entry_id]
            del self._entries[entry_id]
            
            # Remove from pending retries
            if entry_id in self._pending_retries:
                self._pending_retries.remove(entry_id)
            
            # Delete from disk
            entry_file = self.storage_path / f"{entry_id}.json"
            if entry_file.exists():
                entry_file.unlink()
            
            self.logger.info(f"Deleted DLQ entry: {entry_id}")
            return True
        
        return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get DLQ statistics."""
        # Update current counts
        self._stats["pending_entries"] = sum(
            1 for e in self._entries.values() if e.status == DLQStatus.PENDING
        )
        self._stats["processing_entries"] = sum(
            1 for e in self._entries.values() if e.status == DLQStatus.PROCESSING
        )
        self._stats["retried_entries"] = sum(
            1 for e in self._entries.values() if e.status == DLQStatus.RETRIED
        )
        self._stats["failed_entries"] = sum(
            1 for e in self._entries.values() if e.status == DLQStatus.FAILED
        )
        
        return {
            **self._stats,
            "storage_path": str(self.storage_path),
            "max_entries": self.max_entries,
            "utilization": len(self._entries) / self.max_entries,
            "pending_retries": len(self._pending_retries)
        }
    
    async def _reprocessing_loop(self):
        """Background loop for automatic reprocessing."""
        while True:
            try:
                await asyncio.sleep(self.reprocessing_interval)
                await self._process_pending_retries()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in reprocessing loop: {e}")
    
    async def _process_pending_retries(self):
        """Process entries ready for retry."""
        now = datetime.now(timezone.utc)
        ready_entries = []
        
        # Find entries ready for retry
        for entry_id in self._pending_retries[:]:  # Copy list to avoid modification during iteration
            entry = self._entries.get(entry_id)
            if not entry:
                self._pending_retries.remove(entry_id)
                continue
            
            if entry.next_retry and entry.next_retry <= now:
                ready_entries.append(entry)
                self._pending_retries.remove(entry_id)
        
        # Process ready entries
        for entry in ready_entries:
            try:
                await self._process_entry(entry, self._get_default_reprocess_func(entry.data_type))
            except Exception as e:
                self.logger.error(f"Failed to process DLQ entry {entry.entry_id}: {e}")
    
    async def _process_entry(self, entry: DLQEntry, reprocess_func: Callable) -> bool:
        """Process a DLQ entry."""
        entry.status = DLQStatus.PROCESSING
        entry.last_attempt = datetime.now(timezone.utc)
        entry.retry_count += 1
        
        processing_attempt = {
            "attempt_number": entry.retry_count,
            "timestamp": entry.last_attempt.isoformat(),
            "strategy": entry.retry_strategy.value
        }
        
        try:
            # Attempt reprocessing
            result = await reprocess_func(entry.original_data)
            
            processing_attempt["success"] = True
            processing_attempt["result"] = result
            
            # Mark as successfully reprocessed
            entry.status = DLQStatus.RETRIED
            entry.final_outcome = "successfully_reprocessed"
            
            self._stats["successful_reprocesses"] += 1
            self._stats["retried_entries"] += 1
            
            self.logger.info(f"Successfully reprocessed DLQ entry: {entry.entry_id}")
            return True
            
        except Exception as e:
            processing_attempt["success"] = False
            processing_attempt["error"] = str(e)
            
            # Handle retry logic
            if entry.retry_count >= entry.max_retries:
                entry.status = DLQStatus.FAILED
                entry.final_outcome = "max_retries_exceeded"
                
                self._stats["failed_entries"] += 1
                self._stats["failed_reprocesses"] += 1
                
                self.logger.error(f"DLQ entry failed after max retries: {entry.entry_id}")
            else:
                # Schedule next retry
                entry.status = DLQStatus.PENDING
                entry.next_retry = self._calculate_next_retry(entry)
                self._pending_retries.append(entry.entry_id)
                
                self.logger.warning(f"DLQ entry retry scheduled: {entry.entry_id} (attempt {entry.retry_count})")
            
            entry.processing_attempts.append(processing_attempt)
            await self._save_entry(entry)
            
            return False
    
    def _calculate_next_retry(self, entry: DLQEntry) -> datetime:
        """Calculate next retry time based on strategy."""
        base_delay = 60  # 1 minute base delay
        
        if entry.retry_strategy == ReprocessingStrategy.IMMEDIATE:
            return datetime.now(timezone.utc)
        
        elif entry.retry_strategy == ReprocessingStrategy.DELAYED:
            # Exponential backoff
            delay = base_delay * (2 ** (entry.retry_count - 1))
            return datetime.now(timezone.utc) + timedelta(seconds=delay)
        
        elif entry.retry_strategy == ReprocessingStrategy.ADAPTIVE:
            # Adaptive based on error type
            if entry.validation_result:
                critical_errors = [
                    issue for issue in entry.validation_result.issues
                    if issue.severity == ValidationSeverity.CRITICAL
                ]
                
                if critical_errors:
                    # Longer delay for critical errors
                    delay = base_delay * (3 ** (entry.retry_count - 1))
                else:
                    # Shorter delay for non-critical errors
                    delay = base_delay * (1.5 ** (entry.retry_count - 1))
            else:
                delay = base_delay * (2 ** (entry.retry_count - 1))
            
            return datetime.now(timezone.utc) + timedelta(seconds=delay)
        
        # Default: no retry for manual strategy
        return datetime.now(timezone.utc) + timedelta(days=365)
    
    def _extract_rejection_reason(self, validation_result: ValidationResult) -> str:
        """Extract primary rejection reason from validation result."""
        if not validation_result or not validation_result.issues:
            return "Unknown validation error"
        
        # Find the most severe issue
        critical_issues = [i for i in validation_result.issues if i.severity == ValidationSeverity.CRITICAL]
        if critical_issues:
            return critical_issues[0].message
        
        error_issues = [i for i in validation_result.issues if i.severity == ValidationSeverity.ERROR]
        if error_issues:
            return error_issues[0].message
        
        warning_issues = [i for i in validation_result.issues if i.severity == ValidationSeverity.WARNING]
        if warning_issues:
            return warning_issues[0].message
        
        return validation_result.issues[0].message if validation_result.issues else "Validation failed"
    
    def _extract_error_details(self, validation_result: ValidationResult) -> List[str]:
        """Extract all error details from validation result."""
        if not validation_result or not validation_result.issues:
            return []
        
        return [f"{issue.field}: {issue.message}" for issue in validation_result.issues]
    
    def _get_default_reprocess_func(self, data_type: str) -> Callable:
        """Get default reprocessing function for data type."""
        async def default_reprocess(data: Dict[str, Any]) -> Any:
            # This is a placeholder - in practice, you'd implement
            # specific reprocessing logic for each data type
            self.logger.warning(f"Using default reprocess for {data_type}")
            return {"status": "reprocessed", "data": data}
        
        return default_reprocess
    
    async def _load_entries(self):
        """Load existing entries from disk."""
        try:
            for entry_file in self.storage_path.glob("*.json"):
                try:
                    with open(entry_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        entry = DLQEntry.from_dict(data)
                        self._entries[entry.entry_id] = entry
                        
                        # Add to pending retries if needed
                        if (entry.status == DLQStatus.PENDING and 
                            entry.retry_strategy != ReprocessingStrategy.MANUAL and
                            entry.next_retry):
                            self._pending_retries.append(entry.entry_id)
                
                except Exception as e:
                    self.logger.error(f"Failed to load entry {entry_file}: {e}")
            
            self.logger.info(f"Loaded {len(self._entries)} entries from disk")
            
        except Exception as e:
            self.logger.error(f"Failed to load DLQ entries: {e}")
    
    async def _save_entry(self, entry: DLQEntry):
        """Save a single entry to disk."""
        try:
            entry_file = self.storage_path / f"{entry.entry_id}.json"
            with open(entry_file, 'w', encoding='utf-8') as f:
                json.dump(entry.to_dict(), f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Failed to save entry {entry.entry_id}: {e}")
    
    async def _save_entries(self):
        """Save all entries to disk."""
        for entry in self._entries.values():
            await self._save_entry(entry)


# Global DLQ instance
_dead_letter_queue: Optional[DeadLetterQueue] = None


def get_dead_letter_queue(
    storage_path: Optional[str] = None,
    auto_reprocess: bool = True
) -> DeadLetterQueue:
    """Get or create global DLQ instance."""
    global _dead_letter_queue
    if _dead_letter_queue is None:
        _dead_letter_queue = DeadLetterQueue(
            storage_path=storage_path,
            auto_reprocess=auto_reprocess
        )
    return _dead_letter_queue
