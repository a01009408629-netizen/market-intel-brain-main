"""
Schema Difference Analyzer

This module provides schema difference analysis using deepdiff
to detect and categorize schema changes and drift.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

try:
    from deepdiff import DeepDiff
    DEEPDIFF_AVAILABLE = True
except ImportError:
    DEEPDIFF_AVAILABLE = False
    # Create minimal fallback
    DeepDiff = None

from .exceptions import DiffAnalysisError, ConfigurationError
from .fingerprint import SchemaFingerprint


@dataclass
class DiffConfig:
    """Configuration for difference analysis."""
    ignore_type_changes: bool = False
    ignore_type_subclasses: bool = True
    ignore_order: bool = True
    case_sensitive: bool = True
    verbose: int = 1  # 0=summary, 1=normal, 2=verbose
    include_path: bool = True
    max_diff_items: int = 1000
    max_string_length: int = 200


@dataclass
class SchemaChange:
    """Represents a single schema change."""
    change_type: str  # "added", "removed", "modified", "type_changed"
    path: str
    old_value: Any
    new_value: Any
    details: Dict[str, Any]


@dataclass
class DiffResult:
    """Result of schema difference analysis."""
    provider: str
    schema_type: str
    old_version: str
    new_version: str
    has_changes: bool
    changes: List[SchemaChange]
    summary: Dict[str, int]
    analysis_timestamp: float
    metadata: Dict[str, Any]


class BaseDiffAnalyzer(ABC):
    """Abstract base class for diff analyzers."""
    
    @abstractmethod
    def analyze_diff(self, old_data: Any, new_data: Any, **kwargs) -> DiffResult:
        """Analyze differences between two data structures."""
        pass


class DeepDiffAnalyzer(BaseDiffAnalyzer):
    """
    DeepDiff-based schema difference analyzer.
    
    This class uses deepdiff to detect and categorize changes
    between JSON schemas and API responses.
    """
    
    def __init__(
        self,
        config: Optional[DiffConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize DeepDiff analyzer.
        
        Args:
            config: Diff analysis configuration
            logger: Logger instance
        """
        self.config = config or DiffConfig()
        self.logger = logger or logging.getLogger("DeepDiffAnalyzer")
        
        if not DEEPDIFF_AVAILABLE:
            self.logger.warning("deepdiff not available, using fallback analyzer")
        
        self.logger.info("DeepDiffAnalyzer initialized")
    
    def analyze_diff(
        self,
        old_data: Any,
        new_data: Any,
        provider: str = "unknown",
        schema_type: str = "unknown",
        old_version: str = "unknown",
        new_version: str = "unknown",
        **kwargs
    ) -> DiffResult:
        """
        Analyze differences between two data structures.
        
        Args:
            old_data: Original data
            new_data: New data
            provider: Provider name
            schema_type: Type of schema
            old_version: Old schema version
            new_version: New schema version
            **kwargs: Additional parameters
            
        Returns:
            DiffResult with detailed analysis
        """
        try:
            if DEEPDIFF_AVAILABLE:
                return self._analyze_with_deepdiff(
                    old_data, new_data, provider, schema_type, old_version, new_version
                )
            else:
                return self._analyze_fallback(
                    old_data, new_data, provider, schema_type, old_version, new_version
                )
                
        except Exception as e:
            self.logger.error(f"Error analyzing diff: {e}")
            raise DiffAnalysisError(f"Failed to analyze diff: {e}")
    
    def _analyze_with_deepdiff(
        self,
        old_data: Any,
        new_data: Any,
        provider: str,
        schema_type: str,
        old_version: str,
        new_version: str
    ) -> DiffResult:
        """Analyze using deepdiff library."""
        
        # Configure deepdiff based on our config
        deepdiff_kwargs = {
            'ignore_type_changes': self.config.ignore_type_changes,
            'ignore_type_subclasses': self.config.ignore_type_subclasses,
            'ignore_order': self.config.ignore_order,
            'case_sensitive': self.config.case_sensitive,
            'verbose_level': self.config.verbose
        }
        
        # Create diff
        diff = DeepDiff(old_data, new_data, **deepdiff_kwargs)
        
        # Convert diff to our format
        changes = self._convert_deepdiff_to_changes(diff)
        
        # Create summary
        summary = self._create_summary(changes)
        
        # Create metadata
        metadata = {
            "deepdiff_config": deepdiff_kwargs,
            "diff_stats": {
                "values_changed": len(diff.get('values_changed', [])),
                "items_added": len(diff.get('dictionary_item_added', [])),
                "items_removed": len(diff.get('dictionary_item_removed', [])),
                "iterable_items_added": len(diff.get('iterable_item_added', [])),
                "iterable_items_removed": len(diff.get('iterable_item_removed', []))
            }
        }
        
        return DiffResult(
            provider=provider,
            schema_type=schema_type,
            old_version=old_version,
            new_version=new_version,
            has_changes=len(changes) > 0,
            changes=changes,
            summary=summary,
            analysis_timestamp=import time.time(),
            metadata=metadata
        )
    
    def _analyze_fallback(
        self,
        old_data: Any,
        new_data: Any,
        provider: str,
        schema_type: str,
        old_version: str,
        new_version: str
    ) -> DiffResult:
        """Fallback analysis without deepdiff."""
        
        # Simple comparison for when deepdiff is not available
        changes = []
        
        if type(old_data) != type(new_data):
            changes.append(SchemaChange(
                change_type="type_changed",
                path="root",
                old_value=type(old_data).__name__,
                new_value=type(new_data).__name__,
                details={"reason": "Type mismatch"}
            ))
        
        # Simple dict comparison
        if isinstance(old_data, dict) and isinstance(new_data, dict):
            old_keys = set(old_data.keys())
            new_keys = set(new_data.keys())
            
            # Find added keys
            for key in new_keys - old_keys:
                changes.append(SchemaChange(
                    change_type="added",
                    path=f".{key}",
                    old_value=None,
                    new_value=new_data[key],
                    details={"key": key}
                ))
            
            # Find removed keys
            for key in old_keys - new_keys:
                changes.append(SchemaChange(
                    change_type="removed",
                    path=f".{key}",
                    old_value=old_data[key],
                    new_value=None,
                    details={"key": key}
                ))
            
            # Find modified keys
            for key in old_keys & new_keys:
                if old_data[key] != new_data[key]:
                    changes.append(SchemaChange(
                        change_type="modified",
                        path=f".{key}",
                        old_value=old_data[key],
                        new_value=new_data[key],
                        details={"key": key}
                    ))
        
        # Create summary
        summary = self._create_summary(changes)
        
        return DiffResult(
            provider=provider,
            schema_type=schema_type,
            old_version=old_version,
            new_version=new_version,
            has_changes=len(changes) > 0,
            changes=changes,
            summary=summary,
            analysis_timestamp=import time.time(),
            metadata={"fallback": True}
        )
    
    def _convert_deepdiff_to_changes(self, diff: DeepDiff) -> List[SchemaChange]:
        """Convert deepdiff result to our SchemaChange format."""
        changes = []
        
        # Handle values changed
        if 'values_changed' in diff:
            for path, change in diff['values_changed'].items():
                changes.append(SchemaChange(
                    change_type="modified",
                    path='.'.join(map(str, path)),
                    old_value=change['old_value'],
                    new_value=change['new_value'],
                    details=change
                ))
        
        # Handle dictionary items added
        if 'dictionary_item_added' in diff:
            for path, item in diff['dictionary_item_added'].items():
                changes.append(SchemaChange(
                    change_type="added",
                    path='.'.join(map(str, path)),
                    old_value=None,
                    new_value=item,
                    details={"path": path}
                ))
        
        # Handle dictionary items removed
        if 'dictionary_item_removed' in diff:
            for path, item in diff['dictionary_item_removed'].items():
                changes.append(SchemaChange(
                    change_type="removed",
                    path='.'.join(map(str, path)),
                    old_value=item,
                    new_value=None,
                    details={"path": path}
                ))
        
        # Handle iterable items added
        if 'iterable_item_added' in diff:
            for path, item in diff['iterable_item_added'].items():
                changes.append(SchemaChange(
                    change_type="added",
                    path='.'.join(map(str, path)),
                    old_value=None,
                    new_value=item,
                    details={"path": path, "index": item[0]}
                ))
        
        # Handle iterable items removed
        if 'iterable_item_removed' in diff:
            for path, item in diff['iterable_item_removed'].items():
                changes.append(SchemaChange(
                    change_type="removed",
                    path='.'.join(map(str, path)),
                    old_value=item,
                    new_value=None,
                    details={"path": path, "index": item[0]}
                ))
        
        return changes
    
    def _create_summary(self, changes: List[SchemaChange]) -> Dict[str, int]:
        """Create summary statistics from changes."""
        summary = {
            "total_changes": len(changes),
            "added": 0,
            "removed": 0,
            "modified": 0,
            "type_changed": 0
        }
        
        for change in changes:
            summary[change.change_type] += 1
        
        return summary
    
    def categorize_changes(self, changes: List[SchemaChange]) -> Dict[str, List[SchemaChange]]:
        """Categorize changes by type."""
        categorized = {
            "breaking": [],
            "non_breaking": [],
            "unknown": []
        }
        
        for change in changes:
            category = self._determine_change_category(change)
            categorized[category].append(change)
        
        return categorized
    
    def _determine_change_category(self, change: SchemaChange) -> str:
        """Determine if change is breaking or non-breaking."""
        # This is a simplified heuristic - in practice, you'd want
        # more sophisticated logic based on your specific schema rules
        
        if change.change_type == "removed":
            return "breaking"
        elif change.change_type == "type_changed":
            # Check if type change is breaking
            old_type = change.old_value
            new_type = change.new_value
            
            # Simple heuristic: object -> primitive is breaking
            if self._is_more_specific_type(old_type, new_type):
                return "non_breaking"
            else:
                return "breaking"
        elif change.change_type == "modified":
            # Check if modification is breaking
            return self._is_modification_breaking(change)
        else:  # added
            return "non_breaking"
    
    def _is_more_specific_type(self, old_type: str, new_type: str) -> bool:
        """Check if new type is more specific than old type."""
        type_hierarchy = {
            "object": 0,
            "dict": 1,
            "list": 2,
            "str": 3,
            "int": 4,
            "float": 5,
            "bool": 6
        }
        
        old_rank = type_hierarchy.get(old_type, -1)
        new_rank = type_hierarchy.get(new_type, -1)
        
        return new_rank > old_rank
    
    def _is_modification_breaking(self, change: SchemaChange) -> bool:
        """Determine if a modification is breaking."""
        # This is a simplified heuristic
        # In practice, you'd want domain-specific rules
        
        old_value = change.old_value
        new_value = change.new_value
        
        # If type changed, it's potentially breaking
        if type(old_value) != type(new_value):
            return True
        
        # If required field became None, it's breaking
        if old_value is not None and new_value is None:
            return True
        
        # If numeric constraints changed (e.g., max length decreased)
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            if 'maxLength' in old_value and 'maxLength' in new_value:
                if new_value['maxLength'] < old_value['maxLength']:
                    return True
        
        return False
    
    def get_change_summary(self, diff_result: DiffResult) -> str:
        """Get human-readable summary of changes."""
        if not diff_result.has_changes:
            return "No changes detected"
        
        summary_parts = []
        
        if diff_result.summary["added"] > 0:
            summary_parts.append(f"{diff_result.summary['added']} added")
        
        if diff_result.summary["removed"] > 0:
            summary_parts.append(f"{diff_result.summary['removed']} removed")
        
        if diff_result.summary["modified"] > 0:
            summary_parts.append(f"{diff_result.summary['modified']} modified")
        
        if diff_result.summary["type_changed"] > 0:
            summary_parts.append(f"{diff_result.summary['type_changed']} type changes")
        
        return ", ".join(summary_parts)
    
    def export_changes(self, diff_result: DiffResult, format: str = "json") -> str:
        """
        Export changes in specified format.
        
        Args:
            diff_result: Diff result to export
            format: Export format ("json", "csv", "yaml")
            
        Returns:
            Exported changes string
        """
        if format == "json":
            import json
            return json.dumps([change.__dict__ for change in diff_result.changes], indent=2)
        
        elif format == "csv":
            lines = ["type,path,old_value,new_value"]
            for change in diff_result.changes:
                old_val = str(change.old_value).replace('"', '""')
                new_val = str(change.new_value).replace('"', '""')
                lines.append(f"{change.change_type},{change.path},{old_val},{new_val}")
            return "\n".join(lines)
        
        elif format == "yaml":
            return self._export_yaml(diff_result)
        
        else:
            raise DiffAnalysisError(f"Unsupported export format: {format}")
    
    def _export_yaml(self, diff_result: DiffResult) -> str:
        """Export changes as YAML."""
        yaml_lines = [
            f"provider: {diff_result.provider}",
            f"schema_type: {diff_result.schema_type}",
            f"old_version: {diff_result.old_version}",
            f"new_version: {diff_result.new_version}",
            f"has_changes: {diff_result.has_changes}",
            f"summary:",
            f"  total: {diff_result.summary['total_changes']}",
            f"  added: {diff_result.summary['added']}",
            f"  removed: {diff_result.summary['removed']}",
            f"  modified: {diff_result.summary['modified']}",
            f"  type_changed: {diff_result.summary['type_changed']}",
            "changes:"
        ]
        
        for change in diff_result.changes:
            yaml_lines.append(f"  - type: {change.change_type}")
            yaml_lines.append(f"    path: {change.path}")
            yaml_lines.append(f"    old_value: {change.old_value}")
            yaml_lines.append(f"    new_value: {change.new_value}")
            yaml_lines.append(f"    details: {change.details}")
        
        return "\n".join(yaml_lines)


# Global diff analyzer instance
_global_analyzer: Optional[DeepDiffAnalyzer] = None


def get_analyzer(**kwargs) -> DeepDiffAnalyzer:
    """
    Get or create the global diff analyzer.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global DeepDiffAnalyzer instance
    """
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = DeepDiffAnalyzer(**kwargs)
    return _global_analyzer


# Utility functions
def compare_schemas(
    old_schema: Any,
    new_schema: Any,
    provider: str = "unknown",
    schema_type: str = "unknown",
    old_version: str = "unknown",
    new_version: str = "unknown",
    config: Optional[DiffConfig] = None
) -> DiffResult:
    """
    Compare two schemas and return detailed analysis.
    
    Args:
        old_schema: Original schema
        new_schema: New schema
        provider: Provider name
        schema_type: Type of schema
        old_version: Old version
        new_version: New version
        config: Diff configuration
        
    Returns:
        DiffResult with detailed analysis
    """
    analyzer = get_analyzer(config)
    return analyzer.analyze_diff(
        old_schema, new_schema, provider, schema_type, old_version, new_version
    )


def detect_schema_drift(
    current_schema: Any,
    expected_fingerprint: SchemaFingerprint,
    config: Optional[DiffConfig] = None
) -> Dict[str, Any]:
    """
    Detect schema drift by comparing current schema with expected fingerprint.
    
    Args:
        current_schema: Current schema data
        expected_fingerprint: Expected schema fingerprint
        config: Diff configuration
        
    Returns:
        Schema drift detection result
    """
    from .fingerprint import get_fingerprinter
    
    fingerprinter = get_fingerprinter(config)
    current_fingerprint = fingerprinter.create_fingerprint(current_schema)
    
    has_drift = current_fingerprint.hash != expected_fingerprint.hash
    
    return {
        "has_drift": has_drift,
        "expected_hash": expected_fingerprint.hash,
        "current_hash": current_fingerprint.hash,
        "expected_algorithm": expected_fingerprint.algorithm,
        "current_algorithm": current_fingerprint.algorithm,
        "expected_timestamp": expected_fingerprint.timestamp,
        "current_timestamp": current_fingerprint.timestamp,
        "time_diff": current_fingerprint.timestamp - expected_fingerprint.timestamp
    }
