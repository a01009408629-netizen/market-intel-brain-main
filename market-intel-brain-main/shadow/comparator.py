"""
Response Comparator

This module provides response comparison functionality for shadow testing
with detailed difference analysis and similarity scoring.
"""

import asyncio
import logging
import time
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .exceptions import ComparatorError


@dataclass
class ComparisonConfig:
    """Configuration for response comparison."""
    ignore_timestamps: bool = True
    ignore_request_ids: bool = True
    ignore_order: bool = True
    case_sensitive: bool = True
    numeric_tolerance: float = 0.001  # For numeric comparisons
    string_similarity_threshold: float = 0.8
    max_depth: int = 100
    enable_structure_diff: bool = True
    enable_content_diff: bool = True
    enable_performance_diff: bool = True


@dataclass
class ComparisonResult:
    """Result of response comparison."""
    primary_request_id: str
    shadow_request_id: str
    primary_adapter: str
    shadow_adapter: str
    timestamp: float
    is_identical: bool
    similarity_score: float
    structure_differences: List[Dict[str, Any]]
    content_differences: List[Dict[str, Any]]
    performance_differences: Dict[str, Any]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class FieldDifference:
    """Represents a field-level difference."""
    path: str
    field_name: str
    primary_value: Any
    shadow_value: Any
    difference_type: str  # "added", "removed", "modified", "type_changed"
    old_value: Any
    new_value: Any
    details: Dict[str, Any]


class BaseComparator(ABC):
    """Abstract base class for response comparators."""
    
    @abstractmethod
    async def compare_responses(
        self,
        primary_response: Dict[str, Any],
        shadow_response: Dict[str, Any],
        **kwargs
    ) -> ComparisonResult:
        """Compare two responses."""
        pass


class JSONComparator(BaseComparator):
    """
    JSON response comparator for structured data comparison.
    
    This class provides detailed comparison of JSON responses including
    structure, content, and performance analysis.
    """
    
    def __init__(
        self,
        config: Optional[ComparisonConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize JSON comparator.
        
        Args:
            config: Comparison configuration
            logger: Logger instance
        """
        self.config = config or ComparisonConfig()
        self.logger = logger or logging.getLogger("JSONComparator")
        
        self.logger.info("JSONComparator initialized")
    
    async def compare_responses(
        self,
        primary_response: Dict[str, Any],
        shadow_response: Dict[str, Any],
        primary_adapter: str = "unknown",
        shadow_adapter: str = "unknown",
        primary_request_id: str = "unknown",
        shadow_request_id: str = "unknown",
        **kwargs
    ) -> ComparisonResult:
        """
        Compare two JSON responses.
        
        Args:
            primary_response: Primary response data
            shadow_response: Shadow response data
            primary_adapter: Primary adapter name
            shadow_adapter: Shadow adapter name
            primary_request_id: Primary request ID
            shadow_request_id: Shadow request ID
            
        Returns:
            ComparisonResult with detailed analysis
        """
        try:
            start_time = time.time()
            
            # Compare structure
            structure_diffs = []
            if self.config.enable_structure_diff:
                structure_diffs = self._compare_structure(
                    primary_response, shadow_response
                )
            
            # Compare content
            content_diffs = []
            if self.config.enable_content_diff:
                content_diffs = self._compare_content(
                    primary_response, shadow_response
                )
            
            # Compare performance
            performance_diffs = {}
            if self.config.enable_performance_diff:
                performance_diffs = self._compare_performance(
                    primary_response, shadow_response,
                    primary_adapter,
                    shadow_adapter,
                    kwargs.get("primary_latency", 0),
                    kwargs.get("shadow_latency", 0)
                )
            
            # Calculate similarity score
            similarity_score = self._calculate_similarity_score(
                structure_diffs, content_diffs
            )
            
            # Create field differences
            field_diffs = self._create_field_differences(
                structure_diffs + content_diffs
            )
            
            # Create summary
            summary = self._create_summary(
                structure_diffs, content_diffs, field_diffs, performance_diffs
            )
            
            comparison_time = time.time() - start_time
            
            result = ComparisonResult(
                primary_request_id=primary_request_id,
                shadow_request_id=shadow_request_id,
                primary_adapter=primary_adapter,
                shadow_adapter=shadow_adapter,
                timestamp=start_time,
                is_identical=similarity_score == 1.0,
                similarity_score=similarity_score,
                structure_differences=structure_diffs,
                content_differences=content_diffs,
                performance_differences=performance_diffs,
                summary=summary,
                metadata={
                    "comparison_time": comparison_time,
                    "config": self.config.__dict__
                }
            )
            
            self.logger.debug(
                f"Compared responses: {primary_adapter} vs {shadow_adapter} "
                f"(similarity: {similarity_score:.3f}, time: {comparison_time:.3f}s)"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error comparing responses: {e}")
            raise ComparatorError(f"Failed to compare responses: {e}")
    
    def _compare_structure(self, primary: Dict[str, Any], shadow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare structure of two JSON responses."""
        differences = []
        
        # Compare keys
        primary_keys = set(primary.keys())
        shadow_keys = set(shadow.keys())
        
        # Find added keys
        for key in shadow_keys - primary_keys:
            differences.append({
                "type": "field_added",
                "path": f".{key}",
                "field_name": key,
                "primary_value": None,
                "shadow_value": shadow[key],
                "details": {"key": key}
            })
        
        # Find removed keys
        for key in primary_keys - shadow_keys:
            differences.append({
                "type": "field_removed",
                "path": f".{key}",
                "field_name": key,
                "primary_value": primary[key],
                "shadow_value": None,
                "details": {"key": key}
            })
        
        # Find modified keys
        for key in primary_keys & shadow_keys:
            primary_val = primary[key]
            shadow_val = shadow[key]
            
            if not self._values_equal(primary_val, shadow_val):
                differences.append({
                    "type": "field_modified",
                    "path": f".{key}",
                    "field_name": key,
                    "primary_value": primary_val,
                    "shadow_value": shadow_val,
                    "details": {
                        "primary_type": type(primary_val).__name__,
                        "shadow_type": type(shadow_val).__name__
                    }
                })
        
        return differences
    
    def _compare_content(self, primary: Dict[str, Any], shadow: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare content of two JSON responses."""
        differences = []
        
        # Compare values for common keys
        common_keys = set(primary.keys()) & set(shadow.keys())
        
        for key in common_keys:
            primary_val = primary[key]
            shadow_val = shadow[key]
            
            if not self._values_equal(primary_val, shadow_val):
                differences.append({
                    "type": "content_modified",
                    "path": f".{key}",
                    "field_name": key,
                    "primary_value": primary_val,
                    "shadow_value": shadow_val,
                    "details": {
                        "primary_type": type(primary_val).__name__,
                        "shadow_type": type(shadow_val).__name__
                    }
                })
        
        return differences
    
    def _compare_performance(
        self,
        primary: Dict[str, Any],
        shadow: Dict[str, Any],
        primary_adapter: str,
        shadow_adapter: str,
        primary_latency: float,
        shadow_latency: float
    ) -> Dict[str, Any]:
        """Compare performance metrics."""
        return {
            "primary_adapter": primary_adapter,
            "shadow_adapter": shadow_adapter,
            "primary_latency_ms": primary_latency * 1000,
            "shadow_latency_ms": shadow_latency * 1000,
            "latency_difference_ms": (shadow_latency - primary_latency) * 1000,
            "latency_ratio": shadow_latency / max(primary_latency, 0.001),
            "is_shadow_faster": shadow_latency < primary_latency,
            "is_shadow_slower": shadow_latency > primary_latency,
            "performance_impact": self._calculate_performance_impact(primary_latency, shadow_latency)
        }
    
    def _calculate_similarity_score(
        self,
        structure_diffs: List[Dict[str, Any]],
        content_diffs: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall similarity score."""
        # Start with perfect score
        score = 1.0
        
        # Deduct for structure differences
        if self.config.enable_structure_diff:
            structure_penalty = len(structure_diffs) * 0.1
            score = max(0.0, score - structure_penalty)
        
        # Deduct for content differences
        if self.config.enable_content_diff:
            content_penalty = len(content_diffs) * 0.05
            score = max(0.0, score - content_penalty)
        
        return score
    
    def _create_field_differences(self, diffs: List[Dict[str, Any]]) -> List[FieldDifference]:
        """Create field difference objects."""
        field_diffs = []
        
        for diff in diffs:
            field_diffs.append(FieldDifference(
                path=diff["path"],
                field_name=diff["field_name"],
                primary_value=diff["primary_value"],
                shadow_value=diff["shadow_value"],
                difference_type=diff["type"],
                old_value=diff["primary_value"],
                new_value=diff["shadow_value"],
                details=diff.get("details", {})
            ))
        
        return field_diffs
    
    def _values_equal(self, val1: Any, val2: Any) -> bool:
        """Check if two values are equal with tolerance."""
        # Handle numeric values with tolerance
        if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
            return abs(val1 - val2) <= self.config.numeric_tolerance
        
        # Handle strings with case sensitivity
        if isinstance(val1, str) and isinstance(val2, str):
            if not self.config.case_sensitive:
                return val1.lower() == val2.lower()
        
        # Handle other types
        return val1 == val2
    
    def _create_summary(
        self,
        structure_diffs: List[Dict[str, Any]],
        content_diffs: List[Dict[str, Any]],
        field_diffs: List[FieldDifference],
        performance_diffs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comparison summary."""
        return {
            "total_differences": len(structure_diffs) + len(content_diffs),
            "structure_differences": len(structure_diffs),
            "content_differences": len(content_diffs),
            "field_differences": len(field_diffs),
            "performance_differences": performance_diffs,
            "similarity_score": self._calculate_similarity_score(structure_diffs, content_diffs),
            "change_types": {
                "field_added": len([d for d in field_diffs if d.difference_type == "field_added"]),
                "field_removed": len([d for d in field_diffs if d.difference_type == "field_removed"]),
                "field_modified": len([d for d in field_diffs if d.difference_type == "field_modified"]),
                "content_modified": len([d for d in field_diffs if d.difference_type == "content_modified"]),
                "type_changed": len([d for d in field_diffs if d.difference_type == "type_changed"])
            }
        }


class ResponseComparator(BaseComparator):
    """
    High-level response comparator that can handle different response types.
    
    This class provides a unified interface for comparing different
    response formats (JSON, XML, binary, etc.).
    """
    
    def __init__(
        self,
        config: Optional[ComparisonConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize response comparator.
        
        Args:
            config: Comparison configuration
            logger: Logger instance
        """
        self.config = config or ComparisonConfig()
        self.logger = logger or logging.getLogger("ResponseComparator")
        
        self.json_comparator = JSONComparator(config, logger)
        
        self.logger.info("ResponseComparator initialized")
    
    async def compare_responses(
        self,
        primary_response: Any,
        shadow_response: Any,
        **kwargs
    ) -> ComparisonResult:
        """
        Compare two responses based on their type.
        
        Args:
            primary_response: Primary response
            shadow_response: Shadow response
            **kwargs: Additional parameters
            
        Returns:
            ComparisonResult with detailed analysis
        """
        try:
            # Determine response types
            primary_type = self._get_response_type(primary_response)
            shadow_type = self._get_response_type(shadow_response)
            
            if primary_type != shadow_type:
                self.logger.warning(
                    f"Response type mismatch: {primary_type} vs {shadow_type}"
                )
                # Create difference for type mismatch
                return ComparisonResult(
                    primary_request_id=kwargs.get("primary_request_id", "unknown"),
                    shadow_request_id=kwargs.get("shadow_request_id", "unknown"),
                    primary_adapter=kwargs.get("primary_adapter", "unknown"),
                    shadow_adapter=kwargs.get("shadow_adapter", "unknown"),
                    timestamp=time.time(),
                    is_identical=False,
                    similarity_score=0.0,
                    structure_differences=[{
                        "type": "type_mismatch",
                        "path": "root",
                        "primary_type": primary_type,
                        "shadow_type": shadow_type,
                        "details": {"mismatch": True}
                    }],
                    content_differences=[],
                    field_differences=[],
                    performance_differences={},
                    summary={"error": "Response type mismatch"},
                    metadata={"response_types": [primary_type, shadow_type]}
                )
            
            # Use JSON comparator for JSON responses
            if primary_type == "json":
                return await self.json_comparator.compare_responses(
                    primary_response, shadow_response, **kwargs
                )
            
            # For other types, use generic comparison
            return await self._compare_generic_responses(
                primary_response, shadow_response, primary_type, **kwargs
            )
            
        except Exception as e:
            self.logger.error(f"Error comparing responses: {e}")
            raise ComparatorError(f"Failed to compare responses: {e}")
    
    def _get_response_type(self, response: Any) -> str:
        """Determine response type."""
        if isinstance(response, dict):
            return "json"
        elif isinstance(response, str):
            return "string"
        elif isinstance(response, bytes):
            return "binary"
        elif response is None:
            return "null"
        else:
            return "unknown"
    
    async def _compare_generic_responses(
        self,
        primary_response: Any,
        shadow_response: Any,
        response_type: str,
        **kwargs
    ) -> ComparisonResult:
        """Generic comparison for non-JSON responses."""
        try:
            # Convert to string representation for comparison
            primary_str = str(primary_response)
            shadow_str = str(shadow_response)
            
            # Simple string comparison
            is_identical = primary_str == shadow_str
            similarity_score = 1.0 if is_identical else 0.0
            
            return ComparisonResult(
                primary_request_id=kwargs.get("primary_request_id", "unknown"),
                shadow_request_id=kwargs.get("shadow_request_id", "unknown"),
                primary_adapter=kwargs.get("primary_adapter", "unknown"),
                shadow_adapter=kwargs.get("shadow_adapter", "unknown"),
                timestamp=time.time(),
                is_identical=is_identical,
                similarity_score=similarity_score,
                structure_differences=[],
                content_differences=[],
                field_differences=[],
                performance_differences={},
                summary={
                    "response_type": response_type,
                    "identical": is_identical,
                    "similarity_score": similarity_score
                },
                metadata={"generic_comparison": True}
            )
            
        except Exception as e:
            self.logger.error(f"Error in generic comparison: {e}")
            raise ComparatorError(f"Failed to compare responses: {e}")


# Global comparator instance
_global_comparator: Optional[ResponseComparator] = None


def get_comparator(**kwargs) -> ResponseComparator:
    """
    Get or create the global response comparator.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global ResponseComparator instance
    """
    global _global_comparator
    if _global_comparator is None:
        _global_comparator = ResponseComparator(**kwargs)
    return _global_comparator


# Utility functions
def compare_json_responses(
    primary_response: Dict[str, Any],
    shadow_response: Dict[str, Any],
    **kwargs
) -> ComparisonResult:
    """
    Compare two JSON responses.
    
    Args:
        primary_response: Primary response
        shadow_response: Shadow response
        **kwargs: Additional parameters
        
    Returns:
        ComparisonResult with detailed analysis
    """
    comparator = get_comparator()
    return await comparator.compare_responses(
        primary_response, shadow_response, **kwargs
    )


def calculate_similarity_score(
    primary_response: Dict[str, Any],
    shadow_response: Dict[str, Any],
    config: Optional[ComparisonConfig] = None
) -> float:
    """
    Calculate similarity score between two responses.
    
    Args:
        primary_response: Primary response
        shadow_response: Shadow response
        config: Comparison configuration
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    comparator = get_comparator(config)
    result = await comparator.compare_responses(
        primary_response, shadow_response
    )
    return result.similarity_score
