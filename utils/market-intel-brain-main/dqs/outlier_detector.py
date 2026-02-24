"""
Outlier Detector - High-Performance Statistical Anomaly Detection

This module provides memory-efficient outlier detection using Welford's online algorithm
with configurable thresholds and multiple detection strategies.
"""

import math
import time
import warnings
from typing import Optional, Dict, Any, List, Tuple, Union
from collections import deque
from dataclasses import dataclass, field

from .welford import WelfordStatistics, RunningStatistics
from .exceptions import (
    AnomalyDetectedWarning,
    OutlierRejectedError,
    InsufficientDataError,
    ConfigurationError
)


@dataclass
class OutlierResult:
    """Result of outlier detection."""
    is_outlier: bool
    value: float
    z_score: Optional[float]
    threshold: float
    timestamp: float
    asset_id: str
    action: str  # 'accepted', 'rejected', 'warning'
    message: str = ""


@dataclass
class DetectorConfig:
    """Configuration for outlier detector."""
    z_score_threshold: float = 3.0
    min_samples: int = 10
    max_history_size: int = 1000
    use_population_stddev: bool = False
    auto_reject: bool = False
    warning_enabled: bool = True
    sliding_window_size: Optional[int] = None
    iqr_threshold: float = 1.5  # For IQR-based detection
    enable_iqr_detection: bool = False
    median_absolute_deviation_threshold: float = 3.0  # For MAD-based detection
    enable_mad_detection: bool = False
    
    def __post_init__(self):
        """Validate configuration."""
        if self.z_score_threshold <= 0:
            raise ConfigurationError("z_score_threshold", self.z_score_threshold, "must be positive")
        
        if self.min_samples < 2:
            raise ConfigurationError("min_samples", self.min_samples, "must be at least 2")
        
        if self.max_history_size < self.min_samples:
            raise ConfigurationError(
                "max_history_size", 
                self.max_history_size, 
                f"must be at least min_samples ({self.min_samples})"
            )
        
        if self.sliding_window_size is not None and self.sliding_window_size < self.min_samples:
            raise ConfigurationError(
                "sliding_window_size",
                self.sliding_window_size,
                f"must be at least min_samples ({self.min_samples})"
            )


class OutlierDetector:
    """
    High-performance outlier detector using Welford's online algorithm.
    
    This class maintains running statistics without storing all historical values,
    making it memory-efficient for streaming data analysis.
    """
    
    def __init__(
        self,
        asset_id: str,
        config: Optional[DetectorConfig] = None,
        storage_backend: str = "memory"  # "memory" or "redis"
    ):
        """
        Initialize outlier detector.
        
        Args:
            asset_id: Identifier for the asset being monitored
            config: Detection configuration
            storage_backend: Storage backend for historical data
        """
        self.asset_id = asset_id
        self.config = config or DetectorConfig()
        self.storage_backend = storage_backend
        
        # Welford statistics for memory-efficient calculation
        self._stats = RunningStatistics()
        
        # Sliding window for recent values (if enabled)
        self._sliding_window = deque(maxlen=self.config.sliding_window_size) if self.config.sliding_window_size else None
        
        # Recent history for detailed analysis (limited size)
        self._recent_history = deque(maxlen=self.config.max_history_size)
        
        # Detection statistics
        self._total_samples = 0
        self._outlier_count = 0
        self._last_outlier_time = None
        self._detection_start_time = time.time()
        
        # Redis client (if using Redis backend)
        self._redis_client = None
        if storage_backend == "redis":
            self._init_redis_client()
    
    def _init_redis_client(self):
        """Initialize Redis client for state storage."""
        try:
            import redis.asyncio as redis
            self._redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        except ImportError:
            raise ConfigurationError(
                "storage_backend", 
                "redis", 
                "redis-py package not available"
            )
    
    async def add_sample(self, value: float, timestamp: Optional[float] = None) -> OutlierResult:
        """
        Add a new sample and perform outlier detection.
        
        Args:
            value: New sample value
            timestamp: Sample timestamp (current time if None)
            
        Returns:
            OutlierResult with detection outcome
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Update statistics
        self._stats.update(value)
        self._total_samples += 1
        
        # Add to sliding window if enabled
        if self._sliding_window is not None:
            self._sliding_window.append(value)
        
        # Add to recent history
        self._recent_history.append((timestamp, value))
        
        # Perform outlier detection
        result = await self._detect_outlier(value, timestamp)
        
        # Update statistics
        if result.is_outlier:
            self._outlier_count += 1
            self._last_outlier_time = timestamp
        
        # Persist state if using Redis
        if self._redis_client:
            await self._persist_state()
        
        return result
    
    async def _detect_outlier(self, value: float, timestamp: float) -> OutlierResult:
        """
        Perform outlier detection using multiple methods.
        
        Args:
            value: Value to check
            timestamp: Timestamp of the value
            
        Returns:
            OutlierResult with detection outcome
        """
        if self._stats.count < self.config.min_samples:
            # Not enough data for reliable detection
            return OutlierResult(
                is_outlier=False,
                value=value,
                z_score=None,
                threshold=self.config.z_score_threshold,
                timestamp=timestamp,
                asset_id=self.asset_id,
                action="accepted",
                message=f"Insufficient data: {self._stats.count}/{self.config.min_samples}"
            )
        
        # Z-score based detection
        is_z_outlier, z_score = self._stats.welford.is_outlier(
            value, 
            self.config.z_score_threshold,
            self.config.use_population_stddev
        )
        
        # IQR-based detection (if enabled)
        is_iqr_outlier = False
        if self.config.enable_iqr_detection:
            is_iqr_outlier = self._detect_iqr_outlier(value)
        
        # MAD-based detection (if enabled)
        is_mad_outlier = False
        if self.config.enable_mad_detection:
            is_mad_outlier = self._detect_mad_outlier(value)
        
        # Combine detection results
        is_outlier = is_z_outlier or is_iqr_outlier or is_mad_outlier
        
        # Determine action and message
        if is_outlier:
            action, message = self._handle_outlier(value, z_score, timestamp)
        else:
            action = "accepted"
            message = f"Value within normal range (z-score: {z_score:.3f})"
        
        return OutlierResult(
            is_outlier=is_outlier,
            value=value,
            z_score=z_score,
            threshold=self.config.z_score_threshold,
            timestamp=timestamp,
            asset_id=self.asset_id,
            action=action,
            message=message
        )
    
    def _detect_iqr_outlier(self, value: float) -> bool:
        """
        Detect outlier using Interquartile Range method.
        
        Args:
            value: Value to check
            
        Returns:
            True if value is an outlier based on IQR
        """
        if self._sliding_window is None or len(self._sliding_window) < self.config.min_samples:
            return False
        
        # Calculate IQR from sliding window
        sorted_values = sorted(self._sliding_window)
        n = len(sorted_values)
        
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        q1 = sorted_values[q1_idx]
        q3 = sorted_values[q3_idx]
        iqr = q3 - q1
        
        if iqr == 0:
            return False
        
        lower_bound = q1 - self.config.iqr_threshold * iqr
        upper_bound = q3 + self.config.iqr_threshold * iqr
        
        return value < lower_bound or value > upper_bound
    
    def _detect_mad_outlier(self, value: float) -> bool:
        """
        Detect outlier using Median Absolute Deviation method.
        
        Args:
            value: Value to check
            
        Returns:
            True if value is an outlier based on MAD
        """
        if self._sliding_window is None or len(self._sliding_window) < self.config.min_samples:
            return False
        
        # Calculate MAD from sliding window
        sorted_values = sorted(self._sliding_window)
        n = len(sorted_values)
        median = sorted_values[n // 2] if n % 2 == 1 else (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        
        mad = sum(abs(v - median) for v in sorted_values) / n
        
        if mad == 0:
            return False
        
        modified_z_score = 0.6745 * (value - median) / mad
        return abs(modified_z_score) > self.config.median_absolute_deviation_threshold
    
    def _handle_outlier(self, value: float, z_score: Optional[float], timestamp: float) -> Tuple[str, str]:
        """
        Handle detected outlier based on configuration.
        
        Args:
            value: Outlier value
            z_score: Calculated Z-score
            timestamp: Detection timestamp
            
        Returns:
            Tuple of (action, message)
        """
        # Issue warning if enabled
        if self.config.warning_enabled:
            warning = AnomalyDetectedWarning(
                asset_id=self.asset_id,
                value=value,
                z_score=z_score or 0,
                threshold=self.config.z_score_threshold,
                timestamp=timestamp
            )
            warnings.warn(warning, category=AnomalyDetectedWarning)
        
        # Auto-reject if configured
        if self.config.auto_reject:
            raise OutlierRejectedError(
                asset_id=self.asset_id,
                value=value,
                z_score=z_score or 0,
                threshold=self.config.z_score_threshold
            )
        
        return "warning", f"Outlier detected: z-score={z_score:.3f}"
    
    async def add_batch(self, values: List[Tuple[float, float]]) -> List[OutlierResult]:
        """
        Add multiple samples at once.
        
        Args:
            values: List of (timestamp, value) tuples
            
        Returns:
            List of OutlierResult objects
        """
        results = []
        for timestamp, value in values:
            result = await self.add_sample(value, timestamp)
            results.append(result)
        
        return results
    
    def get_current_statistics(self) -> Dict[str, Any]:
        """
        Get current statistical summary.
        
        Returns:
            Dictionary with current statistics
        """
        stats = self._stats.get_comprehensive_summary()
        stats.update({
            'asset_id': self.asset_id,
            'total_samples': self._total_samples,
            'outlier_count': self._outlier_count,
            'outlier_rate': self._outlier_count / max(self._total_samples, 1),
            'last_outlier_time': self._last_outlier_time,
            'detection_duration': time.time() - self._detection_start_time,
            'config': {
                'z_score_threshold': self.config.z_score_threshold,
                'min_samples': self.config.min_samples,
                'auto_reject': self.config.auto_reject,
                'warning_enabled': self.config.warning_enabled
            }
        })
        
        return stats
    
    def get_recent_outliers(self, count: int = 10) -> List[OutlierResult]:
        """
        Get recent outlier detections.
        
        Args:
            count: Maximum number of recent outliers to return
            
        Returns:
            List of recent OutlierResult objects
        """
        outliers = []
        
        # Scan recent history for outliers
        for timestamp, value in reversed(list(self._recent_history)):
            if len(outliers) >= count:
                break
            
            # Re-calculate Z-score for this value
            z_score = self._stats.welford.calculate_z_score(value)
            if z_score is not None and abs(z_score) > self.config.z_score_threshold:
                outliers.append(OutlierResult(
                    is_outlier=True,
                    value=value,
                    z_score=z_score,
                    threshold=self.config.z_score_threshold,
                    timestamp=timestamp,
                    asset_id=self.asset_id,
                    action="historical",
                    message="Historical outlier"
                ))
        
        return outliers
    
    def calculate_z_score(self, value: float) -> Optional[float]:
        """
        Calculate Z-score for a value without updating statistics.
        
        Args:
            value: Value to calculate Z-score for
            
        Returns:
            Z-score or None if insufficient data
        """
        return self._stats.welford.calculate_z_score(value, self.config.use_population_stddev)
    
    def is_outlier(self, value: float) -> Tuple[bool, Optional[float]]:
        """
        Check if a value is an outlier without updating statistics.
        
        Args:
            value: Value to check
            
        Returns:
            Tuple of (is_outlier, z_score)
        """
        return self._stats.welford.is_outlier(
            value, 
            self.config.z_score_threshold,
            self.config.use_population_stddev
        )
    
    def reset(self) -> None:
        """Reset all statistics and history."""
        self._stats.reset()
        if self._sliding_window:
            self._sliding_window.clear()
        self._recent_history.clear()
        self._total_samples = 0
        self._outlier_count = 0
        self._last_outlier_time = None
        self._detection_start_time = time.time()
    
    async def _persist_state(self):
        """Persist detector state to Redis."""
        if not self._redis_client:
            return
        
        try:
            # Create state dictionary
            state = {
                'asset_id': self.asset_id,
                'stats': self._stats.get_comprehensive_summary(),
                'total_samples': self._total_samples,
                'outlier_count': self._outlier_count,
                'last_outlier_time': self._last_outlier_time,
                'detection_start_time': self._detection_start_time,
                'config': {
                    'z_score_threshold': self.config.z_score_threshold,
                    'min_samples': self.config.min_samples,
                    'auto_reject': self.config.auto_reject,
                    'warning_enabled': self.config.warning_enabled
                }
            }
            
            # Store in Redis with TTL
            import json
            await self._redis_client.setex(
                f"dqs:state:{self.asset_id}",
                3600,  # 1 hour TTL
                json.dumps(state)
            )
            
        except Exception as e:
            # Log error but don't fail detection
            import logging
            logger = logging.getLogger("OutlierDetector")
            logger.error(f"Failed to persist state for {self.asset_id}: {e}")
    
    async def load_state(self) -> bool:
        """
        Load detector state from Redis.
        
        Returns:
            True if state was loaded successfully
        """
        if not self._redis_client:
            return False
        
        try:
            import json
            state_json = await self._redis_client.get(f"dqs:state:{self.asset_id}")
            
            if not state_json:
                return False
            
            state = json.loads(state_json)
            
            # Restore statistics
            stats_summary = state['stats']
            self._stats.welford.count = stats_summary['count']
            self._stats.welford.mean = stats_summary['mean']
            self._stats.welford.m2 = stats_summary['m2']
            self._stats.welford.min_value = stats_summary['min']
            self._stats.welford.max_value = stats_summary['max']
            
            # Restore other state
            self._total_samples = state['total_samples']
            self._outlier_count = state['outlier_count']
            self._last_outlier_time = state.get('last_outlier_time')
            self._detection_start_time = state['detection_start_time']
            
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger("OutlierDetector")
            logger.error(f"Failed to load state for {self.asset_id}: {e}")
            return False
    
    async def close(self):
        """Clean up resources."""
        if self._redis_client:
            await self._redis_client.close()
    
    def __str__(self) -> str:
        """String representation."""
        return (
            f"OutlierDetector(asset_id='{self.asset_id}', "
            f"samples={self._total_samples}, "
            f"outliers={self._outlier_count}, "
            f"threshold={self.config.z_score_threshold})"
        )
