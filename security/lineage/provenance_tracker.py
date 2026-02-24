"""
Provenance Tracker

This module provides comprehensive provenance tracking for data
with detailed audit trails and compliance reporting.
"""

import asyncio
import logging
import time
import json
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum
from collections import defaultdict, deque
import threading
from datetime import datetime, timezone

from .metadata_manager import MetadataManager, MetadataType, get_metadata_manager
from .exceptions import (
    ProvenanceError,
    ValidationError,
    StorageError,
    AuditError,
    ComplianceError
)


class ProvenanceType(Enum):
    """Types of provenance events."""
    DATA_CREATION = "data_creation"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    DATA_TRANSFER = "data_transfer"
    DATA_BACKUP = "data_backup"
    DATA_RESTORE = "data_restore"
    DATA_ARCHIVAL = "data_archival"
    DATA_RETENTION = "data_retention"
    QUALITY_CHECK = "quality_check"
    COMPLIANCE_CHECK = "compliance_check"
    SECURITY_EVENT = "security_event"
    SYSTEM_EVENT = "system_event"
    USER_ACTION = "user_action"
    AUTOMATED_PROCESS = "automated_process"


class ProvenanceLevel(Enum):
    """Levels of provenance detail."""
    MINIMAL = "minimal"  # Basic who, what, when
    STANDARD = "standard"  # Includes why, how
    DETAILED = "detailed"  # Includes environment, context
    COMPREHENSIVE = "comprehensive"  # Includes all available information


@dataclass
class ProvenanceEvent:
    """Provenance event with comprehensive information."""
    event_id: str
    object_id: str
    provenance_type: ProvenanceType
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    action: str
    outcome: str
    details: Dict[str, Any]
    context: Dict[str, Any]
    environment: Dict[str, Any]
    source_system: str
    target_system: Optional[str]
    data_before: Optional[Dict[str, Any]]
    data_after: Optional[Dict[str, Any]]
    checksum_before: Optional[str]
    checksum_after: Optional[str]
    compliance_tags: List[str]
    security_level: str
    retention_period: Optional[int]
    parent_event_id: Optional[str]
    child_event_ids: List[str]
    is_sensitive: bool = False
    is_compliant: bool = True
    audit_required: bool = True


@dataclass
class ProvenanceChain:
    """Chain of provenance events for an object."""
    chain_id: str
    object_id: str
    events: List[ProvenanceEvent]
    created_at: datetime
    updated_at: datetime
    is_complete: bool = True
    integrity_verified: bool = True


@dataclass
class ComplianceReport:
    """Compliance report for provenance events."""
    report_id: str
    object_id: str
    time_range: str
    compliance_type: str
    total_events: int
    compliant_events: int
    non_compliant_events: int
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    generated_at: datetime
    next_review_date: datetime


class BaseProvenanceStorage(ABC):
    """Abstract base class for provenance storage."""
    
    @abstractmethod
    async def store_event(self, event: ProvenanceEvent) -> bool:
        """Store provenance event."""
        pass
    
    @abstractmethod
    async def retrieve_events(
        self,
        object_id: str,
        provenance_type: Optional[ProvenanceType] = None,
        time_range: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ProvenanceEvent]:
        """Retrieve provenance events."""
        pass
    
    @abstractmethod
    async def get_provenance_chain(self, object_id: str) -> Optional[ProvenanceChain]:
        """Get complete provenance chain."""
        pass
    
    @abstractmethod
    async def search_events(self, criteria: Dict[str, Any]) -> List[ProvenanceEvent]:
        """Search provenance events."""
        pass
    
    @abstractmethod
    async def delete_events(self, object_id: str, before_date: datetime) -> int:
        """Delete old provenance events."""
        pass


class InMemoryProvenanceStorage(BaseProvenanceStorage):
    """In-memory provenance storage for development and testing."""
    
    def __init__(self):
        self._events: Dict[str, List[ProvenanceEvent]] = defaultdict(list)
        self._chains: Dict[str, ProvenanceChain] = {}
        self._lock = threading.RLock()
    
    async def store_event(self, event: ProvenanceEvent) -> bool:
        """Store provenance event in memory."""
        try:
            with self._lock:
                self._events[event.object_id].append(event)
                
                # Update or create chain
                if event.object_id in self._chains:
                    chain = self._chains[event.object_id]
                    chain.events.append(event)
                    chain.updated_at = event.timestamp
                else:
                    chain = ProvenanceChain(
                        chain_id=str(uuid.uuid4()),
                        object_id=event.object_id,
                        events=[event],
                        created_at=event.timestamp,
                        updated_at=event.timestamp
                    )
                    self._chains[event.object_id] = chain
                
                return True
        except Exception as e:
            raise StorageError(f"Failed to store provenance event: {e}", "in_memory", event.object_id)
    
    async def retrieve_events(
        self,
        object_id: str,
        provenance_type: Optional[ProvenanceType] = None,
        time_range: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ProvenanceEvent]:
        """Retrieve provenance events from memory."""
        try:
            with self._lock:
                events = self._events.get(object_id, [])
                
                # Filter by provenance type
                if provenance_type:
                    events = [e for e in events if e.provenance_type == provenance_type]
                
                # Filter by time range
                if time_range:
                    start_time, end_time = self._parse_time_range(time_range)
                    events = [e for e in events if start_time <= e.timestamp <= end_time]
                
                # Sort by timestamp
                events.sort(key=lambda x: x.timestamp)
                
                # Apply limit
                if limit:
                    events = events[:limit]
                
                return events
        except Exception as e:
            raise StorageError(f"Failed to retrieve provenance events: {e}", "in_memory", object_id)
    
    async def get_provenance_chain(self, object_id: str) -> Optional[ProvenanceChain]:
        """Get complete provenance chain from memory."""
        try:
            with self._lock:
                return self._chains.get(object_id)
        except Exception as e:
            raise StorageError(f"Failed to get provenance chain: {e}", "in_memory", object_id)
    
    async def search_events(self, criteria: Dict[str, Any]) -> List[ProvenanceEvent]:
        """Search provenance events in memory."""
        try:
            with self._lock:
                results = []
                
                for object_id, events in self._events.items():
                    for event in events:
                        if self._matches_criteria(event, criteria):
                            results.append(event)
                
                # Sort by timestamp
                results.sort(key=lambda x: x.timestamp)
                
                return results
        except Exception as e:
            raise StorageError(f"Failed to search provenance events: {e}", "in_memory")
    
    async def delete_events(self, object_id: str, before_date: datetime) -> int:
        """Delete old provenance events from memory."""
        try:
            with self._lock:
                if object_id not in self._events:
                    return 0
                
                original_count = len(self._events[object_id])
                
                # Filter events
                self._events[object_id] = [
                    e for e in self._events[object_id]
                    if e.timestamp >= before_date
                ]
                
                # Update chain
                if object_id in self._chains:
                    self._chains[object_id].events = self._events[object_id]
                    self._chains[object_id].updated_at = datetime.now(timezone.utc)
                
                deleted_count = original_count - len(self._events[object_id])
                
                return deleted_count
        except Exception as e:
            raise StorageError(f"Failed to delete provenance events: {e}", "in_memory", object_id)
    
    def _matches_criteria(self, event: ProvenanceEvent, criteria: Dict[str, Any]) -> bool:
        """Check if event matches search criteria."""
        for key, value in criteria.items():
            if hasattr(event, key):
                event_value = getattr(event, key)
                if event_value != value:
                    return False
            else:
                return False
        
        return True
    
    def _parse_time_range(self, time_range: str) -> tuple:
        """Parse ISO time range string."""
        try:
            if "/" in time_range:
                start_str, end_str = time_range.split("/")
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                return start_time, end_time
            else:
                # Single timestamp
                timestamp = datetime.fromisoformat(time_range.replace("Z", "+00:00"))
                return timestamp, timestamp
        except Exception as e:
            raise ValidationError(f"Invalid time range format: {time_range}")


class ProvenanceTracker:
    """
    Comprehensive provenance tracker for data audit trails
    and compliance reporting with detailed event tracking.
    
    This class provides complete provenance tracking ensuring that
    all data operations are recorded with comprehensive context
    for audit and compliance purposes.
    """
    
    def __init__(
        self,
        storage: Optional[BaseProvenanceStorage] = None,
        metadata_manager: Optional[MetadataManager] = None,
        logger: Optional[logging.Logger] = None,
        compliance_rules: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize provenance tracker.
        
        Args:
            storage: Provenance storage backend
            metadata_manager: Metadata manager instance
            logger: Logger instance
            compliance_rules: Compliance rules configuration
        """
        self.storage = storage or InMemoryProvenanceStorage()
        self.metadata_manager = metadata_manager or get_metadata_manager()
        self.logger = logger or logging.getLogger("ProvenanceTracker")
        self.compliance_rules = compliance_rules or {}
        
        # State management
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        self._compliance_cache: Dict[str, ComplianceReport] = {}
        self._lock = threading.RLock()
        
        # Initialize default compliance rules
        self._initialize_compliance_rules()
        
        self.logger.info("ProvenanceTracker initialized")
    
    def _initialize_compliance_rules(self):
        """Initialize default compliance rules."""
        self.compliance_rules = {
            "data_retention": {
                "default_period": 2555,  # 7 years in days
                "sensitive_data_period": 3650,  # 10 years
                "audit_data_period": 1825  # 5 years
            },
            "access_control": {
                "require_authentication": True,
                "require_authorization": True,
                "log_all_access": True,
                "sensitive_data_access": "strict"
            },
            "audit_requirements": {
                "log_all_modifications": True,
                "log_all_access": True,
                "log_system_events": True,
                "preserve_chain_of_custody": True
            },
            "data_quality": {
                "require_quality_checks": True,
                "minimum_quality_score": 0.8,
                "quality_check_frequency": "daily"
            },
            "security": {
                "encrypt_sensitive_data": True,
                "require_integrity_checks": True,
                "log_security_events": True,
                "detect_anomalies": True
            }
        }
    
    async def track_provenance(
        self,
        object_id: str,
        provenance_type: ProvenanceType,
        details: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track provenance event with comprehensive information.
        
        Args:
            object_id: Object identifier
            provenance_type: Type of provenance event
            details: Event details
            context: Additional context information
            
        Returns:
            Event ID
        """
        try:
            # Generate event ID
            event_id = str(uuid.uuid4())
            
            # Extract context information
            user_id = context.get("user_id") if context else None
            session_id = context.get("session_id") if context else None
            action = details.get("action", provenance_type.value)
            outcome = details.get("outcome", "success")
            
            # Build environment information
            environment = {
                "system_name": context.get("system_name", "market-intel-brain") if context else "market-intel-brain",
                "version": context.get("version", "1.0.0") if context else "1.0.0",
                "hostname": context.get("hostname", "localhost") if context else "localhost",
                "ip_address": context.get("ip_address", "127.0.0.1") if context else "127.0.0.1",
                "user_agent": context.get("user_agent", "unknown") if context else "unknown"
            }
            
            # Determine security level and compliance
            security_level = self._determine_security_level(details, context)
            compliance_tags = self._determine_compliance_tags(provenance_type, details, context)
            is_sensitive = self._is_sensitive_data(details, context)
            is_compliant = self._check_compliance(provenance_type, details, context)
            audit_required = self._requires_audit(provenance_type, details, context)
            
            # Calculate checksums if data is provided
            checksum_before = None
            checksum_after = None
            
            if "data_before" in details:
                checksum_before = self._calculate_checksum(details["data_before"])
            
            if "data_after" in details:
                checksum_after = self._calculate_checksum(details["data_after"])
            
            # Determine retention period
            retention_period = self._determine_retention_period(
                provenance_type, is_sensitive, compliance_tags
            )
            
            # Create provenance event
            event = ProvenanceEvent(
                event_id=event_id,
                object_id=object_id,
                provenance_type=provenance_type,
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                session_id=session_id,
                action=action,
                outcome=outcome,
                details=details,
                context=context or {},
                environment=environment,
                source_system=context.get("source_system", "unknown") if context else "unknown",
                target_system=details.get("target_system"),
                data_before=details.get("data_before"),
                data_after=details.get("data_after"),
                checksum_before=checksum_before,
                checksum_after=checksum_after,
                compliance_tags=compliance_tags,
                security_level=security_level,
                retention_period=retention_period,
                parent_event_id=details.get("parent_event_id"),
                child_event_ids=[],
                is_sensitive=is_sensitive,
                is_compliant=is_compliant,
                audit_required=audit_required
            )
            
            # Store event
            await self.storage.store_event(event)
            
            # Store as metadata for lineage integration
            provenance_metadata = {
                "event_id": event_id,
                "provenance_type": provenance_type.value,
                "timestamp": event.timestamp.isoformat(),
                "user_id": user_id,
                "action": action,
                "outcome": outcome,
                "security_level": security_level,
                "compliance_tags": compliance_tags,
                "is_sensitive": is_sensitive,
                "is_compliant": is_compliant
            }
            
            await self.metadata_manager.add_metadata(
                object_id=object_id,
                metadata=provenance_metadata,
                metadata_type=MetadataType.AUDIT,
                context={"source": "provenance_tracker"}
            )
            
            # Check compliance violations
            if not is_compliant:
                await self._handle_compliance_violation(event)
            
            self.logger.info(f"Tracked provenance event {event_id} for object {object_id}")
            
            return event_id
            
        except Exception as e:
            self.logger.error(f"Failed to track provenance: {e}")
            raise ProvenanceError(f"Failed to track provenance: {e}", provenance_type.value, object_id)
    
    async def get_provenance_summary(
        self,
        object_id: str,
        provenance_type: Optional[ProvenanceType] = None,
        time_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get provenance summary for an object.
        
        Args:
            object_id: Object identifier
            provenance_type: Filter by provenance type
            time_range: Time range filter (ISO format)
            
        Returns:
            Provenance summary
        """
        try:
            # Get events
            events = await self.storage.retrieve_events(
                object_id=object_id,
                provenance_type=provenance_type,
                time_range=time_range
            )
            
            # Get provenance chain
            chain = await self.storage.get_provenance_chain(object_id)
            
            # Calculate statistics
            total_events = len(events)
            successful_events = len([e for e in events if e.outcome == "success"])
            failed_events = len([e for e in events if e.outcome == "failed"])
            sensitive_events = len([e for e in events if e.is_sensitive])
            compliant_events = len([e for e in events if e.is_compliant])
            
            # Group by type
            events_by_type = defaultdict(int)
            for event in events:
                events_by_type[event.provenance_type.value] += 1
            
            # Group by user
            events_by_user = defaultdict(int)
            for event in events:
                if event.user_id:
                    events_by_user[event.user_id] += 1
            
            # Time range analysis
            if events:
                earliest_event = min(events, key=lambda x: x.timestamp)
                latest_event = max(events, key=lambda x: x.timestamp)
                time_span = (latest_event.timestamp - earliest_event.timestamp).total_seconds()
            else:
                earliest_event = None
                latest_event = None
                time_span = 0
            
            # Build summary
            summary = {
                "object_id": object_id,
                "total_events": total_events,
                "successful_events": successful_events,
                "failed_events": failed_events,
                "sensitive_events": sensitive_events,
                "compliant_events": compliant_events,
                "success_rate": successful_events / max(total_events, 1),
                "compliance_rate": compliant_events / max(total_events, 1),
                "events_by_type": dict(events_by_type),
                "events_by_user": dict(events_by_user),
                "earliest_event": earliest_event.timestamp.isoformat() if earliest_event else None,
                "latest_event": latest_event.timestamp.isoformat() if latest_event else None,
                "time_span_seconds": time_span,
                "provenance_chain": {
                    "chain_id": chain.chain_id if chain else None,
                    "is_complete": chain.is_complete if chain else None,
                    "integrity_verified": chain.integrity_verified if chain else None,
                    "created_at": chain.created_at.isoformat() if chain else None,
                    "updated_at": chain.updated_at.isoformat() if chain else None
                },
                "time_range": time_range
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get provenance summary for object {object_id}: {e}")
            raise ProvenanceError(f"Failed to get provenance summary: {e}", None, object_id)
    
    async def get_full_provenance_history(
        self,
        object_id: str,
        time_range: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get full provenance history for an object.
        
        Args:
            object_id: Object identifier
            time_range: Time range filter (ISO format)
            limit: Maximum number of events
            
        Returns:
            List of provenance events
        """
        try:
            # Get events
            events = await self.storage.retrieve_events(
                object_id=object_id,
                time_range=time_range,
                limit=limit
            )
            
            # Convert to dictionaries
            history = []
            for event in events:
                event_dict = {
                    "event_id": event.event_id,
                    "object_id": event.object_id,
                    "provenance_type": event.provenance_type.value,
                    "timestamp": event.timestamp.isoformat(),
                    "user_id": event.user_id,
                    "session_id": event.session_id,
                    "action": event.action,
                    "outcome": event.outcome,
                    "details": event.details,
                    "context": event.context,
                    "environment": event.environment,
                    "source_system": event.source_system,
                    "target_system": event.target_system,
                    "checksum_before": event.checksum_before,
                    "checksum_after": event.checksum_after,
                    "compliance_tags": event.compliance_tags,
                    "security_level": event.security_level,
                    "retention_period": event.retention_period,
                    "parent_event_id": event.parent_event_id,
                    "child_event_ids": event.child_event_ids,
                    "is_sensitive": event.is_sensitive,
                    "is_compliant": event.is_compliant,
                    "audit_required": event.audit_required
                }
                
                # Include data snapshots if available (with size limits)
                if event.data_before and len(str(event.data_before)) < 1000:
                    event_dict["data_before"] = event.data_before
                
                if event.data_after and len(str(event.data_after)) < 1000:
                    event_dict["data_after"] = event.data_after
                
                history.append(event_dict)
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get provenance history for object {object_id}: {e}")
            raise ProvenanceError(f"Failed to get provenance history: {e}", None, object_id)
    
    async def generate_compliance_report(
        self,
        object_id: str,
        compliance_type: str,
        time_range: Optional[str] = None
    ) -> ComplianceReport:
        """
        Generate compliance report for an object.
        
        Args:
            object_id: Object identifier
            compliance_type: Type of compliance check
            time_range: Time range for the report
            
        Returns:
            Compliance report
        """
        try:
            # Get events for the time range
            events = await self.storage.retrieve_events(
                object_id=object_id,
                time_range=time_range
            )
            
            # Filter events by compliance type
            relevant_events = []
            for event in events:
                if compliance_type in event.compliance_tags:
                    relevant_events.append(event)
            
            # Analyze compliance
            total_events = len(relevant_events)
            compliant_events = len([e for e in relevant_events if e.is_compliant])
            non_compliant_events = total_events - compliant_events
            
            # Identify violations
            violations = []
            for event in relevant_events:
                if not event.is_compliant:
                    violation = {
                        "event_id": event.event_id,
                        "timestamp": event.timestamp.isoformat(),
                        "provenance_type": event.provenance_type.value,
                        "violation_type": compliance_type,
                        "description": f"Event {event.event_id} failed compliance check",
                        "severity": self._determine_violation_severity(event),
                        "user_id": event.user_id,
                        "action": event.action
                    }
                    violations.append(violation)
            
            # Generate recommendations
            recommendations = self._generate_compliance_recommendations(
                compliance_type, violations, relevant_events
            )
            
            # Create report
            report = ComplianceReport(
                report_id=str(uuid.uuid4()),
                object_id=object_id,
                time_range=time_range or "all_time",
                compliance_type=compliance_type,
                total_events=total_events,
                compliant_events=compliant_events,
                non_compliant_events=non_compliant_events,
                violations=violations,
                recommendations=recommendations,
                generated_at=datetime.now(timezone.utc),
                next_review_date=datetime.now(timezone.utc).replace(
                    year=datetime.now().year + 1
                )
            )
            
            # Cache report
            cache_key = f"{object_id}:{compliance_type}:{time_range}"
            self._compliance_cache[cache_key] = report
            
            self.logger.info(f"Generated compliance report {report.report_id} for object {object_id}")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Failed to generate compliance report for object {object_id}: {e}")
            raise ProvenanceError(f"Failed to generate compliance report: {e}", compliance_type, object_id)
    
    async def _handle_compliance_violation(self, event: ProvenanceEvent):
        """Handle compliance violations."""
        try:
            # Log violation
            self.logger.warning(
                f"Compliance violation detected: Event {event.event_id} for object {event.object_id}"
            )
            
            # Create violation metadata
            violation_metadata = {
                "violation_type": "compliance_breach",
                "event_id": event.event_id,
                "provenance_type": event.provenance_type.value,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "severity": self._determine_violation_severity(event),
                "auto_detected": True
            }
            
            await self.metadata_manager.add_metadata(
                object_id=event.object_id,
                metadata=violation_metadata,
                metadata_type=MetadataType.COMPLIANCE,
                context={"source": "provenance_tracker"}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle compliance violation: {e}")
    
    def _determine_security_level(self, details: Dict[str, Any], context: Optional[Dict[str, Any]]) -> str:
        """Determine security level for an event."""
        # Check for sensitive data indicators
        sensitive_indicators = [
            "ssn", "credit_card", "bank_account", "personal_data",
            "health_record", "financial_data", "confidential"
        ]
        
        details_str = str(details).lower()
        context_str = str(context).lower() if context else ""
        
        for indicator in sensitive_indicators:
            if indicator in details_str or indicator in context_str:
                return "high"
        
        # Check for privileged operations
        privileged_operations = ["admin", "delete", "modify", "export", "bulk"]
        for operation in privileged_operations:
            if operation in details_str:
                return "medium"
        
        return "low"
    
    def _determine_compliance_tags(
        self,
        provenance_type: ProvenanceType,
        details: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Determine compliance tags for an event."""
        tags = []
        
        # Add provenance type as tag
        tags.append(provenance_type.value)
        
        # Add data classification tags
        if "classification" in details:
            tags.append(f"classification:{details['classification']}")
        
        # Add regulatory tags
        if "regulatory_requirements" in details:
            for req in details["regulatory_requirements"]:
                tags.append(f"regulation:{req}")
        
        # Add security tags
        if "security_level" in details:
            tags.append(f"security:{details['security_level']}")
        
        # Add geographic tags
        if "geographic_scope" in details:
            tags.append(f"geo:{details['geographic_scope']}")
        
        return tags
    
    def _is_sensitive_data(self, details: Dict[str, Any], context: Optional[Dict[str, Any]]) -> bool:
        """Check if data is sensitive."""
        sensitive_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit card
            r'\b\d{9}\b',  # Bank account
            r'password|secret|token|key'
        ]
        
        import re
        details_str = str(details).lower()
        context_str = str(context).lower() if context else ""
        combined_str = details_str + " " + context_str
        
        for pattern in sensitive_patterns:
            if re.search(pattern, combined_str):
                return True
        
        return False
    
    def _check_compliance(
        self,
        provenance_type: ProvenanceType,
        details: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if event complies with rules."""
        # Check authentication requirement
        if self.compliance_rules["access_control"]["require_authentication"]:
            if not context or not context.get("user_id"):
                return False
        
        # Check authorization requirement
        if self.compliance_rules["access_control"]["require_authorization"]:
            if not context or not context.get("permissions"):
                return False
        
        # Check audit requirements
        if provenance_type in [ProvenanceType.DATA_MODIFICATION, ProvenanceType.DATA_DELETION]:
            if not self.compliance_rules["audit_requirements"]["log_all_modifications"]:
                return False
        
        # Check security requirements
        if self._is_sensitive_data(details, context):
            if not self.compliance_rules["security"]["encrypt_sensitive_data"]:
                return False
        
        return True
    
    def _requires_audit(
        self,
        provenance_type: ProvenanceType,
        details: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> bool:
        """Check if event requires audit."""
        # All sensitive data operations require audit
        if self._is_sensitive_data(details, context):
            return True
        
        # All modification operations require audit
        if provenance_type in [ProvenanceType.DATA_MODIFICATION, ProvenanceType.DATA_DELETION]:
            return True
        
        # All access to sensitive data requires audit
        if provenance_type == ProvenanceType.DATA_ACCESS:
            if self._is_sensitive_data(details, context):
                return True
        
        return self.compliance_rules["audit_requirements"]["log_all_access"]
    
    def _determine_retention_period(
        self,
        provenance_type: ProvenanceType,
        is_sensitive: bool,
        compliance_tags: List[str]
    ) -> int:
        """Determine retention period for an event."""
        base_period = self.compliance_rules["data_retention"]["default_period"]
        
        # Extend for sensitive data
        if is_sensitive:
            base_period = max(base_period, self.compliance_rules["data_retention"]["sensitive_data_period"])
        
        # Extend for audit data
        if "audit" in compliance_tags:
            base_period = max(base_period, self.compliance_rules["data_retention"]["audit_data_period"])
        
        return base_period
    
    def _calculate_checksum(self, data: Any) -> str:
        """Calculate checksum for data integrity."""
        try:
            serialized = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        except Exception:
            return hashlib.sha256(str(data).encode('utf-8')).hexdigest()
    
    def _determine_violation_severity(self, event: ProvenanceEvent) -> str:
        """Determine severity of compliance violation."""
        if event.is_sensitive:
            return "high"
        
        if event.provenance_type in [ProvenanceType.DATA_DELETION, ProvenanceType.DATA_MODIFICATION]:
            return "medium"
        
        return "low"
    
    def _generate_compliance_recommendations(
        self,
        compliance_type: str,
        violations: List[Dict[str, Any]],
        events: List[ProvenanceEvent]
    ) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []
        
        if violations:
            recommendations.append(f"Review and address {len(violations)} compliance violations")
        
        # Analyze violation patterns
        violation_types = [v["provenance_type"] for v in violations]
        from collections import Counter
        violation_counts = Counter(violation_types)
        
        for violation_type, count in violation_counts.most_common():
            if violation_type == "data_access":
                recommendations.append("Implement stricter access controls and monitoring")
            elif violation_type == "data_modification":
                recommendations.append("Add approval workflows for data modifications")
            elif violation_type == "data_deletion":
                recommendations.append("Implement data retention and deletion policies")
        
        # General recommendations
        if len(events) > 100:
            recommendations.append("Consider implementing automated compliance monitoring")
        
        if not recommendations:
            recommendations.append("Continue maintaining current compliance practices")
        
        return recommendations
    
    def get_status(self) -> Dict[str, Any]:
        """Get provenance tracker status."""
        return {
            "storage_type": type(self.storage).__name__,
            "active_sessions": len(self._active_sessions),
            "compliance_cache_size": len(self._compliance_cache),
            "compliance_rules_configured": len(self.compliance_rules),
            "metadata_manager_type": type(self.metadata_manager).__name__,
            "timestamp": time.time()
        }


# Global provenance tracker instance
_global_provenance_tracker: Optional[ProvenanceTracker] = None


def get_provenance_tracker(**kwargs) -> ProvenanceTracker:
    """
    Get or create global provenance tracker.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global ProvenanceTracker instance
    """
    global _global_provenance_tracker
    if _global_provenance_tracker is None:
        _global_provenance_tracker = ProvenanceTracker(**kwargs)
    return _global_provenance_tracker
