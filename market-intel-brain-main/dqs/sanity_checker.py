"""
Sanity Checker - High-Level Data Quality Management

This module provides a high-level interface for managing multiple outlier detectors
with comprehensive data quality monitoring and alerting.
"""

import asyncio
import time
import warnings
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass
from collections import defaultdict

from .outlier_detector import OutlierDetector, OutlierResult, DetectorConfig
from .exceptions import (
    DataQualityError,
    InsufficientDataError,
    AnomalyDetectedWarning
)


@dataclass
class SanityCheckResult:
    """Result of a sanity check operation."""
    asset_id: str
    value: float
    timestamp: float
    is_valid: bool
    outlier_result: Optional[OutlierResult]
    quality_score: float  # 0.0 to 1.0
    issues: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'asset_id': self.asset_id,
            'value': self.value,
            'timestamp': self.timestamp,
            'is_valid': self.is_valid,
            'quality_score': self.quality_score,
            'issues': self.issues,
            'outlier_result': self.outlier_result.__dict__ if self.outlier_result else None
        }


@dataclass
class SanityCheckConfig:
    """Configuration for sanity checker."""
    default_detector_config: DetectorConfig = None
    enable_global_monitoring: bool = True
    quality_score_threshold: float = 0.8  # Alert if quality score below this
    alert_callback: Optional[Callable] = None
    max_alerts_per_minute: int = 10
    enable_auto_recovery: bool = False
    recovery_callback: Optional[Callable] = None


class SanityChecker:
    """
    High-level data quality management system.
    
    This class manages multiple outlier detectors and provides comprehensive
    data quality monitoring with alerting and recovery mechanisms.
    """
    
    def __init__(
        self,
        config: Optional[SanityCheckConfig] = None,
        storage_backend: str = "memory"
    ):
        """
        Initialize sanity checker.
        
        Args:
            config: Global configuration
            storage_backend: Storage backend for detector state
        """
        self.config = config or SanityCheckConfig()
        self.storage_backend = storage_backend
        
        # Registry of outlier detectors
        self._detectors: Dict[str, OutlierDetector] = {}
        
        # Global monitoring state
        self._global_stats = {
            'total_checks': 0,
            'total_outliers': 0,
            'total_alerts': 0,
            'start_time': time.time()
        }
        
        # Alert rate limiting
        self._alert_times = []
        
        # Event callbacks
        self._event_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Background monitoring task
        self._monitoring_task = None
        self._monitoring_active = False
        
        if self.config.enable_global_monitoring:
            self._start_monitoring()
    
    def register_asset(
        self,
        asset_id: str,
        detector_config: Optional[DetectorConfig] = None
    ) -> OutlierDetector:
        """
        Register an asset for monitoring.
        
        Args:
            asset_id: Unique identifier for the asset
            detector_config: Specific configuration for this asset
            
        Returns:
            OutlierDetector instance
        """
        if asset_id in self._detectors:
            raise DataQualityError(f"Asset '{asset_id}' is already registered")
        
        config = detector_config or self.config.default_detector_config or DetectorConfig()
        detector = OutlierDetector(asset_id, config, self.storage_backend)
        
        self._detectors[asset_id] = detector
        
        # Trigger registration event
        self._trigger_event('asset_registered', {
            'asset_id': asset_id,
            'config': config
        })
        
        return detector
    
    def unregister_asset(self, asset_id: str) -> bool:
        """
        Unregister an asset from monitoring.
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            True if asset was unregistered
        """
        if asset_id not in self._detectors:
            return False
        
        detector = self._detectors.pop(asset_id)
        
        # Clean up detector resources
        if hasattr(detector, 'close'):
            asyncio.create_task(detector.close())
        
        # Trigger unregistration event
        self._trigger_event('asset_unregistered', {
            'asset_id': asset_id
        })
        
        return True
    
    async def check_data_point(
        self,
        asset_id: str,
        value: float,
        timestamp: Optional[float] = None
    ) -> SanityCheckResult:
        """
        Check a single data point for quality issues.
        
        Args:
            asset_id: Asset identifier
            value: Data value to check
            timestamp: Timestamp of the data point
            
        Returns:
            SanityCheckResult with detailed analysis
        """
        if asset_id not in self._detectors:
            # Auto-register asset with default config
            self.register_asset(asset_id)
        
        detector = self._detectors[asset_id]
        
        # Perform outlier detection
        outlier_result = await detector.add_sample(value, timestamp)
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(outlier_result)
        
        # Determine validity and collect issues
        is_valid = not outlier_result.is_outlier
        issues = []
        
        if outlier_result.is_outlier:
            issues.append(f"Outlier detected: {outlier_result.message}")
        
        # Additional quality checks
        additional_issues = await self._perform_additional_checks(asset_id, value, timestamp)
        issues.extend(additional_issues)
        
        if additional_issues:
            is_valid = False
            quality_score = max(0.0, quality_score - 0.2 * len(additional_issues))
        
        # Create result
        result = SanityCheckResult(
            asset_id=asset_id,
            value=value,
            timestamp=timestamp or time.time(),
            is_valid=is_valid,
            outlier_result=outlier_result,
            quality_score=quality_score,
            issues=issues
        )
        
        # Update global statistics
        self._global_stats['total_checks'] += 1
        if outlier_result.is_outlier:
            self._global_stats['total_outliers'] += 1
        
        # Handle alerts
        await self._handle_alerts(result)
        
        # Trigger events
        self._trigger_event('data_checked', result.to_dict())
        
        return result
    
    async def check_batch(
        self,
        data_points: List[Dict[str, Any]]
    ) -> List[SanityCheckResult]:
        """
        Check multiple data points.
        
        Args:
            data_points: List of dictionaries with 'asset_id', 'value', 'timestamp'
            
        Returns:
            List of SanityCheckResult objects
        """
        results = []
        
        for point in data_points:
            result = await self.check_data_point(
                asset_id=point['asset_id'],
                value=point['value'],
                timestamp=point.get('timestamp')
            )
            results.append(result)
        
        # Trigger batch event
        self._trigger_event('batch_checked', {
            'count': len(data_points),
            'results': [r.to_dict() for r in results]
        })
        
        return results
    
    def _calculate_quality_score(self, outlier_result: OutlierResult) -> float:
        """
        Calculate quality score based on outlier detection result.
        
        Args:
            outlier_result: Result from outlier detection
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not outlier_result.is_outlier:
            return 1.0
        
        # Base score reduction based on Z-score magnitude
        if outlier_result.z_score is not None:
            z_magnitude = abs(outlier_result.z_score)
            if z_magnitude > 5:
                return 0.0
            elif z_magnitude > 4:
                return 0.2
            elif z_magnitude > 3:
                return 0.4
            else:
                return 0.6
        
        return 0.5  # Default for outlier without Z-score
    
    async def _perform_additional_checks(
        self,
        asset_id: str,
        value: float,
        timestamp: Optional[float]
    ) -> List[str]:
        """
        Perform additional data quality checks.
        
        Args:
            asset_id: Asset identifier
            value: Data value
            timestamp: Data timestamp
            
        Returns:
            List of issue descriptions
        """
        issues = []
        
        # Check for invalid values
        if not isinstance(value, (int, float)):
            issues.append("Invalid data type")
            return issues
        
        if value != value:  # NaN check
            issues.append("NaN value detected")
        
        if value in (float('inf'), float('-inf')):
            issues.append("Infinite value detected")
        
        # Timestamp checks
        if timestamp is not None:
            current_time = time.time()
            if timestamp > current_time + 300:  # 5 minutes in future
                issues.append("Timestamp too far in future")
            elif timestamp < current_time - 86400 * 30:  # 30 days ago
                issues.append("Timestamp too far in past")
        
        return issues
    
    async def _handle_alerts(self, result: SanityCheckResult):
        """Handle alerts based on check result."""
        if result.quality_score >= self.config.quality_score_threshold:
            return
        
        # Rate limiting
        if not self._can_send_alert():
            return
        
        # Create alert data
        alert_data = {
            'asset_id': result.asset_id,
            'value': result.value,
            'quality_score': result.quality_score,
            'issues': result.issues,
            'timestamp': result.timestamp,
            'severity': 'high' if result.quality_score < 0.5 else 'medium'
        }
        
        # Send alert
        if self.config.alert_callback:
            try:
                if asyncio.iscoroutinefunction(self.config.alert_callback):
                    await self.config.alert_callback(alert_data)
                else:
                    self.config.alert_callback(alert_data)
            except Exception as e:
                import logging
                logger = logging.getLogger("SanityChecker")
                logger.error(f"Alert callback failed: {e}")
        
        # Update alert statistics
        self._global_stats['total_alerts'] += 1
        self._alert_times.append(time.time())
        
        # Trigger alert event
        self._trigger_event('alert', alert_data)
    
    def _can_send_alert(self) -> bool:
        """Check if alert can be sent based on rate limiting."""
        current_time = time.time()
        
        # Clean old alert times (older than 1 minute)
        self._alert_times = [
            t for t in self._alert_times 
            if current_time - t < 60
        ]
        
        return len(self._alert_times) < self.config.max_alerts_per_minute
    
    def get_asset_statistics(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific asset.
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            Statistics dictionary or None if asset not found
        """
        if asset_id not in self._detectors:
            return None
        
        return self._detectors[asset_id].get_current_statistics()
    
    def get_global_statistics(self) -> Dict[str, Any]:
        """
        Get global statistics for all monitored assets.
        
        Returns:
            Global statistics dictionary
        """
        asset_stats = {}
        total_samples = 0
        total_outliers = 0
        
        for asset_id, detector in self._detectors.items():
            stats = detector.get_current_statistics()
            asset_stats[asset_id] = stats
            total_samples += stats.get('total_samples', 0)
            total_outliers += stats.get('outlier_count', 0)
        
        global_stats = self._global_stats.copy()
        global_stats.update({
            'monitored_assets': len(self._detectors),
            'total_samples': total_samples,
            'total_outliers': total_outliers,
            'overall_outlier_rate': total_outliers / max(total_samples, 1),
            'uptime': time.time() - self._global_stats['start_time'],
            'asset_statistics': asset_stats
        })
        
        return global_stats
    
    def add_event_callback(self, event_type: str, callback: Callable):
        """
        Add callback for specific events.
        
        Args:
            event_type: Type of event ('data_checked', 'alert', etc.)
            callback: Callback function
        """
        self._event_callbacks[event_type].append(callback)
    
    def _trigger_event(self, event_type: str, data: Any):
        """Trigger event callbacks."""
        for callback in self._event_callbacks[event_type]:
            try:
                callback(data)
            except Exception as e:
                import logging
                logger = logging.getLogger("SanityChecker")
                logger.error(f"Event callback failed for {event_type}: {e}")
    
    def _start_monitoring(self):
        """Start background monitoring task."""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    def _stop_monitoring(self):
        """Stop background monitoring task."""
        self._monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
    
    async def _monitoring_loop(self):
        """Background monitoring loop."""
        while self._monitoring_active:
            try:
                # Perform periodic health checks
                await self._perform_health_checks()
                
                # Sleep for monitoring interval
                await asyncio.sleep(60)  # 1 minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                import logging
                logger = logging.getLogger("SanityChecker")
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(10)  # Short sleep on error
    
    async def _perform_health_checks(self):
        """Perform health checks on all detectors."""
        for asset_id, detector in self._detectors.items():
            try:
                stats = detector.get_current_statistics()
                
                # Check for stale data
                if stats.get('last_outlier_time'):
                    time_since_outlier = time.time() - stats['last_outlier_time']
                    if time_since_outlier > 3600:  # 1 hour
                        self._trigger_event('stale_data', {
                            'asset_id': asset_id,
                            'time_since_outlier': time_since_outlier
                        })
                
            except Exception as e:
                self._trigger_event('detector_error', {
                    'asset_id': asset_id,
                    'error': str(e)
                })
    
    async def load_all_states(self):
        """Load states for all detectors from storage."""
        if self.storage_backend != "redis":
            return
        
        for asset_id, detector in self._detectors.items():
            await detector.load_state()
    
    async def save_all_states(self):
        """Save states for all detectors to storage."""
        if self.storage_backend != "redis":
            return
        
        tasks = []
        for detector in self._detectors.values():
            tasks.append(detector._persist_state())
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def reset_asset(self, asset_id: str) -> bool:
        """
        Reset statistics for a specific asset.
        
        Args:
            asset_id: Asset identifier
            
        Returns:
            True if asset was reset
        """
        if asset_id not in self._detectors:
            return False
        
        self._detectors[asset_id].reset()
        
        self._trigger_event('asset_reset', {'asset_id': asset_id})
        return True
    
    def reset_all(self):
        """Reset all assets and global statistics."""
        for detector in self._detectors.values():
            detector.reset()
        
        self._global_stats = {
            'total_checks': 0,
            'total_outliers': 0,
            'total_alerts': 0,
            'start_time': time.time()
        }
        
        self._trigger_event('all_reset', {})
    
    async def close(self):
        """Close sanity checker and clean up resources."""
        self._stop_monitoring()
        
        # Close all detectors
        tasks = []
        for detector in self._detectors.values():
            if hasattr(detector, 'close'):
                tasks.append(detector.close())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"SanityChecker(assets={len(self._detectors)}, "
            f"checks={self._global_stats['total_checks']}, "
            f"outliers={self._global_stats['total_outliers']})"
        )


# Global sanity checker instance
_global_checker: Optional[SanityChecker] = None


def get_sanity_checker(**kwargs) -> SanityChecker:
    """
    Get or create the global sanity checker instance.
    
    Args:
        **kwargs: Arguments for SanityChecker initialization
        
    Returns:
        Global SanityChecker instance
    """
    global _global_checker
    if _global_checker is None:
        _global_checker = SanityChecker(**kwargs)
    return _global_checker


# Convenience functions for global usage
async def check_data_quality(asset_id: str, value: float, timestamp: Optional[float] = None) -> SanityCheckResult:
    """Check data quality using global sanity checker."""
    checker = get_sanity_checker()
    return await checker.check_data_point(asset_id, value, timestamp)


def register_monitored_asset(asset_id: str, **config) -> OutlierDetector:
    """Register asset for monitoring using global sanity checker."""
    checker = get_sanity_checker()
    return checker.register_asset(asset_id, **config)


def get_quality_statistics(asset_id: str = None) -> Dict[str, Any]:
    """Get quality statistics using global sanity checker."""
    checker = get_sanity_checker()
    
    if asset_id:
        return checker.get_asset_statistics(asset_id)
    else:
        return checker.get_global_statistics()
