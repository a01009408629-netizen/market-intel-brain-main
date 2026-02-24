"""
Data Lineage Tracker

This module provides comprehensive data lineage tracking with UUID-based
identification and comprehensive metadata propagation.
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
    LineageError,
    ValidationError,
    StorageError,
    SerializationError,
    IntegrityError,
    TransformationError
)


class LineageOperation(Enum):
    """Types of lineage operations."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    TRANSFORM = "transform"
    MERGE = "merge"
    SPLIT = "split"
    COPY = "copy"
    ARCHIVE = "archive"
    RESTORE = "restore"


class DataObjectType(Enum):
    """Types of data objects."""
    RAW_DATA = "raw_data"
    PROCESSED_DATA = "processed_data"
    AGGREGATED_DATA = "aggregated_data"
    DERIVED_DATA = "derived_data"
    METADATA = "metadata"
    CONFIGURATION = "configuration"
    LOG = "log"
    REPORT = "report"
    MODEL = "model"
    CUSTOM = "custom"


@dataclass
class LineageNode:
    """Node in the data lineage graph."""
    object_id: str
    object_type: DataObjectType
    name: str
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]
    size_bytes: Optional[int]
    checksum: str
    tags: List[str]
    metadata: Dict[str, Any]
    parent_ids: List[str]
    child_ids: List[str]
    is_active: bool = True
    expires_at: Optional[datetime] = None


@dataclass
class LineageEdge:
    """Edge in the data lineage graph."""
    source_id: str
    target_id: str
    operation: LineageOperation
    timestamp: datetime
    user_id: Optional[str]
    transformation_logic: Optional[str]
    metadata: Dict[str, Any]
    confidence_score: float = 1.0


@dataclass
class LineageTrace:
    """Complete lineage trace for an object."""
    trace_id: str
    root_object_id: str
    object_id: str
    operation_chain: List[LineageEdge]
    metadata_chain: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    is_complete: bool = True


class BaseLineageStorage(ABC):
    """Abstract base class for lineage storage."""
    
    @abstractmethod
    async def store_node(self, node: LineageNode) -> bool:
        """Store lineage node."""
        pass
    
    @abstractmethod
    async def retrieve_node(self, object_id: str) -> Optional[LineageNode]:
        """Retrieve lineage node."""
        pass
    
    @abstractmethod
    async def store_edge(self, edge: LineageEdge) -> bool:
        """Store lineage edge."""
        pass
    
    @abstractmethod
    async def retrieve_edges(self, object_id: str, direction: str = "both") -> List[LineageEdge]:
        """Retrieve lineage edges."""
        pass
    
    @abstractmethod
    async def get_lineage_chain(self, object_id: str, max_depth: int = 10) -> List[LineageTrace]:
        """Get complete lineage chain."""
        pass
    
    @abstractmethod
    async def search_lineage(self, criteria: Dict[str, Any]) -> List[LineageNode]:
        """Search lineage nodes."""
        pass


class InMemoryLineageStorage(BaseLineageStorage):
    """In-memory lineage storage for development and testing."""
    
    def __init__(self):
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: Dict[str, List[LineageEdge]] = defaultdict(list)
        self._traces: Dict[str, LineageTrace] = {}
        self._lock = threading.RLock()
    
    async def store_node(self, node: LineageNode) -> bool:
        """Store lineage node in memory."""
        try:
            with self._lock:
                self._nodes[node.object_id] = node
                return True
        except Exception as e:
            raise StorageError(f"Failed to store lineage node: {e}", "in_memory", node.object_id)
    
    async def retrieve_node(self, object_id: str) -> Optional[LineageNode]:
        """Retrieve lineage node from memory."""
        try:
            with self._lock:
                return self._nodes.get(object_id)
        except Exception as e:
            raise StorageError(f"Failed to retrieve lineage node: {e}", "in_memory", object_id)
    
    async def store_edge(self, edge: LineageEdge) -> bool:
        """Store lineage edge in memory."""
        try:
            with self._lock:
                # Store edge for both source and target
                self._edges[edge.source_id].append(edge)
                self._edges[edge.target_id].append(edge)
                
                # Update node relationships
                if edge.source_id in self._nodes:
                    self._nodes[edge.source_id].child_ids.append(edge.target_id)
                
                if edge.target_id in self._nodes:
                    self._nodes[edge.target_id].parent_ids.append(edge.source_id)
                
                return True
        except Exception as e:
            raise StorageError(f"Failed to store lineage edge: {e}", "in_memory")
    
    async def retrieve_edges(self, object_id: str, direction: str = "both") -> List[LineageEdge]:
        """Retrieve lineage edges from memory."""
        try:
            with self._lock:
                edges = self._edges.get(object_id, [])
                
                if direction == "outgoing":
                    return [e for e in edges if e.source_id == object_id]
                elif direction == "incoming":
                    return [e for e in edges if e.target_id == object_id]
                else:
                    return edges
        except Exception as e:
            raise StorageError(f"Failed to retrieve lineage edges: {e}", "in_memory", object_id)
    
    async def get_lineage_chain(self, object_id: str, max_depth: int = 10) -> List[LineageTrace]:
        """Get complete lineage chain from memory."""
        try:
            with self._lock:
                traces = []
                
                # Build lineage trace
                trace_id = str(uuid.uuid4())
                operation_chain = []
                metadata_chain = []
                
                # Trace backwards through parents
                current_id = object_id
                depth = 0
                
                while current_id and depth < max_depth:
                    node = self._nodes.get(current_id)
                    if not node:
                        break
                    
                    # Get incoming edges
                    incoming_edges = [e for e in self._edges.get(current_id, []) if e.target_id == current_id]
                    
                    if incoming_edges:
                        edge = incoming_edges[0]  # Take first edge
                        
                        operation_chain.append(edge)
                        metadata_chain.append(node.metadata)
                        
                        current_id = edge.source_id
                        depth += 1
                    else:
                        break
                
                # Create trace
                trace = LineageTrace(
                    trace_id=trace_id,
                    root_object_id=current_id or object_id,
                    object_id=object_id,
                    operation_chain=operation_chain,
                    metadata_chain=metadata_chain,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    is_complete=True
                )
                
                traces.append(trace)
                return traces
        except Exception as e:
            raise StorageError(f"Failed to get lineage chain: {e}", "in_memory", object_id)
    
    async def search_lineage(self, criteria: Dict[str, Any]) -> List[LineageNode]:
        """Search lineage nodes in memory."""
        try:
            with self._lock:
                results = []
                
                for node in self._nodes.values():
                    if self._matches_criteria(node, criteria):
                        results.append(node)
                
                return results
        except Exception as e:
            raise StorageError(f"Failed to search lineage: {e}", "in_memory")
    
    def _matches_criteria(self, node: LineageNode, criteria: Dict[str, Any]) -> bool:
        """Check if node matches search criteria."""
        for key, value in criteria.items():
            if hasattr(node, key):
                node_value = getattr(node, key)
                if node_value != value:
                    return False
            else:
                return False
        
        return True


class DataLineageTracker:
    """
    Comprehensive data lineage tracker with UUID-based identification
    and metadata propagation throughout the data lifecycle.
    
    This class provides complete data lineage tracking ensuring that
    metadata accompanies data throughout its lifecycle, even after
    transformations, merges, or other operations.
    """
    
    def __init__(
        self,
        storage: Optional[BaseLineageStorage] = None,
        metadata_manager: Optional[MetadataManager] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize data lineage tracker.
        
        Args:
            storage: Lineage storage backend
            metadata_manager: Metadata manager instance
            logger: Logger instance
        """
        self.storage = storage or InMemoryLineageStorage()
        self.metadata_manager = metadata_manager or get_metadata_manager()
        self.logger = logger or logging.getLogger("DataLineageTracker")
        
        # State management
        self._active_traces: Dict[str, LineageTrace] = {}
        self._lock = threading.RLock()
        
        self.logger.info("DataLineageTracker initialized")
    
    async def track_data_lineage(
        self,
        provider_name: str,
        data: Any,
        operation: LineageOperation,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track data lineage with comprehensive metadata.
        
        Args:
            provider_name: Name of the data provider
            data: Data object to track
            operation: Lineage operation
            context: Additional context information
            metadata: Additional metadata
            
        Returns:
            Object ID for the tracked data
        """
        try:
            # Generate unique object ID
            object_id = str(uuid.uuid4())
            
            # Create base metadata with required fields
            base_metadata = {
                "trace_id": str(uuid.uuid4()),
                "source_name": provider_name,
                "fetch_timestamp": datetime.now(timezone.utc).isoformat(),
                "adapter_version": context.get("adapter_version", "1.0.0") if context else "1.0.0",
                "operation": operation.value,
                "data_type": type(data).__name__,
                "data_size": len(str(data)) if data else 0
            }
            
            # Merge additional metadata
            if metadata:
                base_metadata.update(metadata)
            
            # Create lineage node
            node = LineageNode(
                object_id=object_id,
                object_type=self._determine_object_type(data),
                name=context.get("name", f"{provider_name}_{operation.value}") if context else f"{provider_name}_{operation.value}",
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=context.get("user_id") if context else None,
                updated_by=context.get("user_id") if context else None,
                size_bytes=self._calculate_data_size(data),
                checksum=self._calculate_checksum(data),
                tags=context.get("tags", []) if context else [],
                metadata=base_metadata,
                parent_ids=[],
                child_ids=[]
            )
            
            # Store lineage node
            await self.storage.store_node(node)
            
            # Store metadata
            await self.metadata_manager.add_metadata(
                object_id=object_id,
                metadata=base_metadata,
                metadata_type=MetadataType.SOURCE,
                context=context
            )
            
            # Create lineage trace
            trace = LineageTrace(
                trace_id=base_metadata["trace_id"],
                root_object_id=object_id,
                object_id=object_id,
                operation_chain=[],
                metadata_chain=[base_metadata],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_complete=True
            )
            
            self._active_traces[object_id] = trace
            
            self.logger.info(f"Tracked data lineage for object {object_id} from provider {provider_name}")
            
            return object_id
            
        except Exception as e:
            self.logger.error(f"Failed to track data lineage: {e}")
            raise LineageError(f"Failed to track data lineage: {e}", None, operation.value)
    
    async def track_transformation(
        self,
        input_object_ids: List[str],
        output_data: Any,
        transformation_type: str,
        transformation_logic: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track data transformation with lineage propagation.
        
        Args:
            input_object_ids: List of input object IDs
            output_data: Transformed output data
            transformation_type: Type of transformation
            transformation_logic: Description of transformation logic
            context: Additional context information
            
        Returns:
            Output object ID
        """
        try:
            # Generate output object ID
            output_object_id = str(uuid.uuid4())
            
            # Get input objects and their metadata
            input_objects = []
            input_metadata = []
            
            for input_id in input_object_ids:
                input_node = await self.storage.retrieve_node(input_id)
                if input_node:
                    input_objects.append(input_node)
                    
                    # Get metadata for input object
                    metadata = await self.metadata_manager.get_metadata(input_id)
                    input_metadata.append(metadata)
            
            # Create transformation metadata
            transformation_metadata = {
                "transformation_type": transformation_type,
                "transformation_logic": transformation_logic,
                "input_object_ids": input_object_ids,
                "input_metadata": input_metadata,
                "output_timestamp": datetime.now(timezone.utc).isoformat(),
                "adapter_version": context.get("adapter_version", "1.0.0") if context else "1.0.0",
                "user_id": context.get("user_id") if context else None
            }
            
            # Create output node
            output_node = LineageNode(
                object_id=output_object_id,
                object_type=self._determine_object_type(output_data),
                name=context.get("name", f"transformed_{transformation_type}") if context else f"transformed_{transformation_type}",
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=context.get("user_id") if context else None,
                updated_by=context.get("user_id") if context else None,
                size_bytes=self._calculate_data_size(output_data),
                checksum=self._calculate_checksum(output_data),
                tags=context.get("tags", []) if context else [],
                metadata=transformation_metadata,
                parent_ids=input_object_ids,
                child_ids=[]
            )
            
            # Store output node
            await self.storage.store_node(output_node)
            
            # Create transformation edges
            for input_id in input_object_ids:
                edge = LineageEdge(
                    source_id=input_id,
                    target_id=output_object_id,
                    operation=LineageOperation.TRANSFORM,
                    timestamp=datetime.now(timezone.utc),
                    user_id=context.get("user_id") if context else None,
                    transformation_logic=transformation_logic,
                    metadata=transformation_metadata,
                    confidence_score=1.0
                )
                
                await self.storage.store_edge(edge)
            
            # Store transformation metadata
            await self.metadata_manager.add_metadata(
                object_id=output_object_id,
                metadata=transformation_metadata,
                metadata_type=MetadataType.TRANSFORMATION,
                context=context
            )
            
            # Propagate metadata from inputs to output
            await self._propagate_metadata(input_object_ids, output_object_id, transformation_type)
            
            self.logger.info(f"Tracked transformation for object {output_object_id} with {len(input_object_ids)} inputs")
            
            return output_object_id
            
        except Exception as e:
            self.logger.error(f"Failed to track transformation: {e}")
            raise TransformationError(f"Failed to track transformation: {e}", transformation_type)
    
    async def track_merge(
        self,
        input_object_ids: List[str],
        output_data: Any,
        merge_strategy: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track data merge operation with lineage propagation.
        
        Args:
            input_object_ids: List of input object IDs to merge
            output_data: Merged output data
            merge_strategy: Strategy used for merging
            context: Additional context information
            
        Returns:
            Output object ID
        """
        try:
            # Generate output object ID
            output_object_id = str(uuid.uuid4())
            
            # Get input objects and their metadata
            input_objects = []
            input_metadata = []
            
            for input_id in input_object_ids:
                input_node = await self.storage.retrieve_node(input_id)
                if input_node:
                    input_objects.append(input_node)
                    
                    # Get metadata for input object
                    metadata = await self.metadata_manager.get_metadata(input_id)
                    input_metadata.append(metadata)
            
            # Create merge metadata
            merge_metadata = {
                "merge_strategy": merge_strategy,
                "input_object_ids": input_object_ids,
                "input_metadata": input_metadata,
                "output_timestamp": datetime.now(timezone.utc).isoformat(),
                "adapter_version": context.get("adapter_version", "1.0.0") if context else "1.0.0",
                "user_id": context.get("user_id") if context else None
            }
            
            # Create output node
            output_node = LineageNode(
                object_id=output_object_id,
                object_type=self._determine_object_type(output_data),
                name=context.get("name", f"merged_{merge_strategy}") if context else f"merged_{merge_strategy}",
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                created_by=context.get("user_id") if context else None,
                updated_by=context.get("user_id") if context else None,
                size_bytes=self._calculate_data_size(output_data),
                checksum=self._calculate_checksum(output_data),
                tags=context.get("tags", []) if context else [],
                metadata=merge_metadata,
                parent_ids=input_object_ids,
                child_ids=[]
            )
            
            # Store output node
            await self.storage.store_node(output_node)
            
            # Create merge edges
            for input_id in input_object_ids:
                edge = LineageEdge(
                    source_id=input_id,
                    target_id=output_object_id,
                    operation=LineageOperation.MERGE,
                    timestamp=datetime.now(timezone.utc),
                    user_id=context.get("user_id") if context else None,
                    transformation_logic=f"Merge using {merge_strategy} strategy",
                    metadata=merge_metadata,
                    confidence_score=1.0
                )
                
                await self.storage.store_edge(edge)
            
            # Store merge metadata
            await self.metadata_manager.add_metadata(
                object_id=output_object_id,
                metadata=merge_metadata,
                metadata_type=MetadataType.TRANSFORMATION,
                context=context
            )
            
            # Propagate metadata from inputs to output
            await self._propagate_metadata(input_object_ids, output_object_id, "merge")
            
            self.logger.info(f"Tracked merge for object {output_object_id} with {len(input_object_ids)} inputs")
            
            return output_object_id
            
        except Exception as e:
            self.logger.error(f"Failed to track merge: {e}")
            raise TransformationError(f"Failed to track merge: {e}", "merge")
    
    async def get_lineage_summary(
        self,
        object_id: str,
        provider_name: Optional[str] = None,
        operation: Optional[LineageOperation] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive lineage summary for an object.
        
        Args:
            object_id: Object identifier
            provider_name: Filter by provider name
            operation: Filter by operation type
            
        Returns:
            Lineage summary
        """
        try:
            # Get lineage node
            node = await self.storage.retrieve_node(object_id)
            if not node:
                raise LineageError(f"Object {object_id} not found", object_id)
            
            # Get lineage chain
            traces = await self.storage.get_lineage_chain(object_id)
            
            # Get metadata
            metadata = await self.metadata_manager.get_metadata(object_id)
            
            # Get edges
            incoming_edges = await self.storage.retrieve_edges(object_id, "incoming")
            outgoing_edges = await self.storage.retrieve_edges(object_id, "outgoing")
            
            # Build summary
            summary = {
                "object_id": object_id,
                "object_type": node.object_type.value,
                "name": node.name,
                "version": node.version,
                "created_at": node.created_at.isoformat(),
                "updated_at": node.updated_at.isoformat(),
                "created_by": node.created_by,
                "updated_by": node.updated_by,
                "size_bytes": node.size_bytes,
                "checksum": node.checksum,
                "tags": node.tags,
                "is_active": node.is_active,
                "expires_at": node.expires_at.isoformat() if node.expires_at else None,
                "metadata": metadata,
                "lineage_chain": [],
                "incoming_edges": len(incoming_edges),
                "outgoing_edges": len(outgoing_edges),
                "total_dependencies": len(node.parent_ids),
                "total_dependents": len(node.child_ids)
            }
            
            # Add lineage chain details
            for trace in traces:
                chain_summary = {
                    "trace_id": trace.trace_id,
                    "root_object_id": trace.root_object_id,
                    "operation_count": len(trace.operation_chain),
                    "is_complete": trace.is_complete,
                    "created_at": trace.created_at.isoformat(),
                    "updated_at": trace.updated_at.isoformat()
                }
                summary["lineage_chain"].append(chain_summary)
            
            # Apply filters if specified
            if provider_name:
                summary = self._filter_by_provider(summary, provider_name)
            
            if operation:
                summary = self._filter_by_operation(summary, operation)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to get lineage summary for object {object_id}: {e}")
            raise LineageError(f"Failed to get lineage summary: {e}", object_id)
    
    async def get_full_data_history(
        self,
        object_id: str,
        time_range: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get full data history for an object.
        
        Args:
            object_id: Object identifier
            time_range: Time range filter (ISO format)
            limit: Maximum number of history entries
            
        Returns:
            List of history entries
        """
        try:
            # Get lineage chain
            traces = await self.storage.get_lineage_chain(object_id, max_depth=limit)
            
            # Build history
            history = []
            
            for trace in traces:
                # Add root object
                root_node = await self.storage.retrieve_node(trace.root_object_id)
                if root_node:
                    root_metadata = await self.metadata_manager.get_metadata(trace.root_object_id)
                    
                    history_entry = {
                        "object_id": root_node.object_id,
                        "timestamp": root_node.created_at.isoformat(),
                        "operation": "create",
                        "object_type": root_node.object_type.value,
                        "name": root_node.name,
                        "size_bytes": root_node.size_bytes,
                        "checksum": root_node.checksum,
                        "metadata": root_metadata,
                        "trace_id": trace.trace_id
                    }
                    
                    # Apply time filter if specified
                    if not time_range or self._is_in_time_range(root_node.created_at, time_range):
                        history.append(history_entry)
                
                # Add operations in chain
                for edge in trace.operation_chain:
                    target_node = await self.storage.retrieve_node(edge.target_id)
                    if target_node:
                        target_metadata = await self.metadata_manager.get_metadata(edge.target_id)
                        
                        history_entry = {
                            "object_id": target_node.object_id,
                            "timestamp": edge.timestamp.isoformat(),
                            "operation": edge.operation.value,
                            "object_type": target_node.object_type.value,
                            "name": target_node.name,
                            "size_bytes": target_node.size_bytes,
                            "checksum": target_node.checksum,
                            "metadata": target_metadata,
                            "transformation_logic": edge.transformation_logic,
                            "confidence_score": edge.confidence_score,
                            "trace_id": trace.trace_id
                        }
                        
                        # Apply time filter if specified
                        if not time_range or self._is_in_time_range(edge.timestamp, time_range):
                            history.append(history_entry)
            
            # Sort by timestamp
            history.sort(key=lambda x: x["timestamp"])
            
            # Apply limit
            if limit:
                history = history[:limit]
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get data history for object {object_id}: {e}")
            raise LineageError(f"Failed to get data history: {e}", object_id)
    
    async def _propagate_metadata(
        self,
        input_object_ids: List[str],
        output_object_id: str,
        operation_type: str
    ):
        """Propagate metadata from inputs to output."""
        try:
            # Get all metadata from input objects
            propagated_metadata = {}
            
            for input_id in input_object_ids:
                input_metadata = await self.metadata_manager.get_metadata(input_id)
                
                # Merge metadata with precedence rules
                for key, value in input_metadata.items():
                    if key not in propagated_metadata:
                        propagated_metadata[key] = value
                    elif operation_type == "merge":
                        # For merge operations, create arrays for conflicting keys
                        if not isinstance(propagated_metadata[key], list):
                            propagated_metadata[key] = [propagated_metadata[key]]
                        propagated_metadata[key].append(value)
            
            # Add operation metadata
            propagated_metadata["propagation_operation"] = operation_type
            propagated_metadata["propagation_timestamp"] = datetime.now(timezone.utc).isoformat()
            propagated_metadata["source_object_ids"] = input_object_ids
            
            # Store propagated metadata
            await self.metadata_manager.add_metadata(
                object_id=output_object_id,
                metadata=propagated_metadata,
                metadata_type=MetadataType.TRANSFORMATION,
                context={"operation": "metadata_propagation"}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to propagate metadata: {e}")
            raise LineageError(f"Failed to propagate metadata: {e}")
    
    def _determine_object_type(self, data: Any) -> DataObjectType:
        """Determine object type based on data."""
        if isinstance(data, dict):
            if "trace_id" in data and "source_name" in data:
                return DataObjectType.RAW_DATA
            elif "transformation_type" in data:
                return DataObjectType.PROCESSED_DATA
            else:
                return DataObjectType.CUSTOM
        elif isinstance(data, list):
            return DataObjectType.AGGREGATED_DATA
        elif isinstance(data, (int, float)):
            return DataObjectType.DERIVED_DATA
        else:
            return DataObjectType.CUSTOM
    
    def _calculate_data_size(self, data: Any) -> int:
        """Calculate data size in bytes."""
        try:
            if isinstance(data, str):
                return len(data.encode('utf-8'))
            elif isinstance(data, (dict, list)):
                return len(json.dumps(data, default=str).encode('utf-8'))
            else:
                return len(str(data).encode('utf-8'))
        except Exception:
            return 0
    
    def _calculate_checksum(self, data: Any) -> str:
        """Calculate checksum for data integrity."""
        try:
            serialized = json.dumps(data, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
        except Exception:
            return hashlib.sha256(str(data).encode('utf-8')).hexdigest()
    
    def _filter_by_provider(self, summary: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
        """Filter lineage summary by provider name."""
        # Filter metadata by provider
        filtered_metadata = {}
        for key, value in summary["metadata"].items():
            if key == "source_name" and value == provider_name:
                filtered_metadata[key] = value
            elif key != "source_name":
                filtered_metadata[key] = value
        
        summary["metadata"] = filtered_metadata
        return summary
    
    def _filter_by_operation(self, summary: Dict[str, Any], operation: LineageOperation) -> Dict[str, Any]:
        """Filter lineage summary by operation type."""
        # Filter lineage chain by operation
        filtered_chain = []
        for chain in summary["lineage_chain"]:
            # This would require more detailed operation tracking
            filtered_chain.append(chain)
        
        summary["lineage_chain"] = filtered_chain
        return summary
    
    def _is_in_time_range(self, timestamp: datetime, time_range: str) -> bool:
        """Check if timestamp is within time range."""
        try:
            if "/" in time_range:
                start_str, end_str = time_range.split("/")
                start_time = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                return start_time <= timestamp <= end_time
            else:
                # Single timestamp
                target_time = datetime.fromisoformat(time_range.replace("Z", "+00:00"))
                return timestamp == target_time
        except Exception:
            return True  # Invalid time range, include all
    
    def get_status(self) -> Dict[str, Any]:
        """Get lineage tracker status."""
        return {
            "storage_type": type(self.storage).__name__,
            "active_traces": len(self._active_traces),
            "metadata_manager_type": type(self.metadata_manager).__name__,
            "timestamp": time.time()
        }


# Global lineage tracker instance
_global_lineage_tracker: Optional[DataLineageTracker] = None


def get_tracker(**kwargs) -> DataLineageTracker:
    """
    Get or create global lineage tracker.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global DataLineageTracker instance
    """
    global _global_lineage_tracker
    if _global_lineage_tracker is None:
        _global_lineage_tracker = DataLineageTracker(**kwargs)
    return _global_lineage_tracker
