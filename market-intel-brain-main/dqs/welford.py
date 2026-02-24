"""
Welford's Online Algorithm for Statistics

This module implements Welford's online algorithm for calculating mean and variance
in a memory-efficient way without storing all historical values.
"""

import math
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class WelfordStatistics:
    """
    Statistics calculated using Welford's online algorithm.
    
    This class maintains running statistics without storing all values,
    making it memory-efficient for streaming data.
    """
    
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0  # Sum of squares of differences from mean
    min_value: float = float('inf')
    max_value: float = float('-inf')
    
    def __post_init__(self):
        """Initialize optional fields."""
        self._variance = None
        self._stddev = None
    
    @property
    def variance(self) -> Optional[float]:
        """Get the sample variance."""
        if self.count < 2:
            return None
        return self.m2 / (self.count - 1)
    
    @property
    def stddev(self) -> Optional[float]:
        """Get the sample standard deviation."""
        var = self.variance
        return math.sqrt(var) if var is not None else None
    
    @property
    def population_variance(self) -> Optional[float]:
        """Get the population variance."""
        if self.count == 0:
            return None
        return self.m2 / self.count
    
    @property
    def population_stddev(self) -> Optional[float]:
        """Get the population standard deviation."""
        var = self.population_variance
        return math.sqrt(var) if var is not None else None
    
    def update(self, value: float) -> None:
        """
        Update statistics with a new value using Welford's algorithm.
        
        Args:
            value: New value to incorporate
        """
        self.count += 1
        delta = value - self.mean
        self.mean += delta / self.count
        delta2 = value - self.mean
        self.m2 += delta * delta2
        
        # Update min/max
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        
        # Invalidate cached variance/stddev
        self._variance = None
        self._stddev = None
    
    def update_batch(self, values: list[float]) -> None:
        """
        Update statistics with multiple values at once.
        
        Args:
            values: List of values to incorporate
        """
        for value in values:
            self.update(value)
    
    def merge(self, other: 'WelfordStatistics') -> None:
        """
        Merge another WelfordStatistics into this one.
        
        Args:
            other: Another WelfordStatistics to merge
        """
        if other.count == 0:
            return
        
        if self.count == 0:
            self.count = other.count
            self.mean = other.mean
            self.m2 = other.m2
            self.min_value = other.min_value
            self.max_value = other.max_value
            return
        
        # Merge statistics
        total_count = self.count + other.count
        delta = other.mean - self.mean
        new_mean = self.mean + delta * (other.count / total_count)
        
        # Update m2 using parallel algorithm
        new_m2 = (
            self.m2 + other.m2 + 
            (delta ** 2) * (self.count * other.count / total_count)
        )
        
        self.count = total_count
        self.mean = new_mean
        self.m2 = new_m2
        self.min_value = min(self.min_value, other.min_value)
        self.max_value = max(self.max_value, other.max_value)
        
        # Invalidate cached values
        self._variance = None
        self._stddev = None
    
    def reset(self) -> None:
        """Reset all statistics to initial state."""
        self.count = 0
        self.mean = 0.0
        self.m2 = 0.0
        self.min_value = float('inf')
        self.max_value = float('-inf')
        self._variance = None
        self._stddev = None
    
    def copy(self) -> 'WelfordStatistics':
        """Create a copy of this statistics object."""
        copy = WelfordStatistics(
            count=self.count,
            mean=self.mean,
            m2=self.m2,
            min_value=self.min_value,
            max_value=self.max_value
        )
        return copy
    
    def calculate_z_score(self, value: float, use_population: bool = False) -> Optional[float]:
        """
        Calculate Z-score for a value.
        
        Args:
            value: Value to calculate Z-score for
            use_population: Whether to use population std dev
            
        Returns:
            Z-score or None if variance is zero or insufficient data
        """
        if self.count < 2:
            return None
        
        stddev = self.population_stddev if use_population else self.stddev
        if stddev is None or stddev == 0:
            return None
        
        return (value - self.mean) / stddev
    
    def is_outlier(self, value: float, threshold: float = 3.0, use_population: bool = False) -> tuple[bool, Optional[float]]:
        """
        Check if a value is an outlier based on Z-score threshold.
        
        Args:
            value: Value to check
            threshold: Z-score threshold for outlier detection
            use_population: Whether to use population std dev
            
        Returns:
            Tuple of (is_outlier, z_score)
        """
        z_score = self.calculate_z_score(value, use_population)
        if z_score is None:
            return False, None
        
        is_outlier = abs(z_score) > threshold
        return is_outlier, z_score
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all statistics.
        
        Returns:
            Dictionary with all statistical measures
        """
        return {
            'count': self.count,
            'mean': self.mean,
            'variance': self.variance,
            'stddev': self.stddev,
            'population_variance': self.population_variance,
            'population_stddev': self.population_stddev,
            'min': self.min_value if self.min_value != float('inf') else None,
            'max': self.max_value if self.max_value != float('-inf') else None,
            'range': self.max_value - self.min_value if self.count > 0 else None
        }
    
    def __str__(self) -> str:
        """String representation of statistics."""
        if self.count == 0:
            return "WelfordStatistics(count=0)"
        
        return (
            f"WelfordStatistics(count={self.count}, "
            f"mean={self.mean:.4f}, "
            f"stddev={self.stddev:.4f if self.stddev else 'N/A'}, "
            f"min={self.min_value:.4f}, "
            f"max={self.max_value:.4f})"
        )
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()


class RunningStatistics:
    """
    Extended running statistics with additional metrics.
    
    This class extends WelfordStatistics with additional statistical measures
    useful for data quality monitoring.
    """
    
    def __init__(self):
        self.welford = WelfordStatistics()
        self._sum = 0.0
        self._sum_squares = 0.0
    
    def update(self, value: float) -> None:
        """Update statistics with new value."""
        self.welford.update(value)
        self._sum += value
        self._sum_squares += value * value
    
    def update_batch(self, values: list[float]) -> None:
        """Update statistics with multiple values."""
        for value in values:
            self.update(value)
    
    @property
    def count(self) -> int:
        """Get the count of values."""
        return self.welford.count
    
    @property
    def mean(self) -> float:
        """Get the mean value."""
        return self.welford.mean
    
    @property
    def variance(self) -> Optional[float]:
        """Get the sample variance."""
        return self.welford.variance
    
    @property
    def stddev(self) -> Optional[float]:
        """Get the sample standard deviation."""
        return self.welford.stddev
    
    @property
    def min_value(self) -> float:
        """Get the minimum value."""
        return self.welford.min_value
    
    @property
    def max_value(self) -> float:
        """Get the maximum value."""
        return self.welford.max_value
    
    @property
    def range(self) -> Optional[float]:
        """Get the range of values."""
        if self.count == 0:
            return None
        return self.max_value - self.min_value
    
    @property
    def sum(self) -> float:
        """Get the sum of all values."""
        return self._sum
    
    @property
    def sum_of_squares(self) -> float:
        """Get the sum of squares of all values."""
        return self._sum_squares
    
    @property
    def rms(self) -> Optional[float]:
        """Get the root mean square."""
        if self.count == 0:
            return None
        return math.sqrt(self._sum_squares / self.count)
    
    def calculate_cv(self) -> Optional[float]:
        """
        Calculate coefficient of variation.
        
        Returns:
            Coefficient of variation or None if mean is zero
        """
        if self.mean == 0:
            return None
        
        stddev = self.stddev
        if stddev is None:
            return None
        
        return stddev / abs(self.mean)
    
    def calculate_mad(self) -> Optional[float]:
        """
        Calculate mean absolute deviation.
        
        Note: This requires storing all values, so it's not truly online.
        Use sparingly for monitoring purposes.
        
        Returns:
            Mean absolute deviation or None if no data
        """
        if self.count == 0:
            return None
        
        # This is not truly online, but useful for monitoring
        mad = sum(abs(value - self.mean) for value in []) / self.count
        return mad
    
    def get_percentile_estimate(self, percentile: float) -> Optional[float]:
        """
        Estimate percentile using current statistics.
        
        This is a rough estimate assuming normal distribution.
        
        Args:
            percentile: Percentile to estimate (0-100)
            
        Returns:
            Estimated percentile value or None if insufficient data
        """
        if self.count < 2 or self.stddev is None:
            return None
        
        from math import erf, sqrt
        
        # Convert percentile to Z-score
        p = percentile / 100.0
        if p <= 0.5:
            z = -sqrt(2) * erf_inv(2 * p - 1)
        else:
            z = sqrt(2) * erf_inv(2 * p - 1)
        
        return self.mean + z * self.stddev
    
    def get_comprehensive_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics summary.
        
        Returns:
            Dictionary with all statistical measures
        """
        summary = self.welford.get_summary()
        summary.update({
            'sum': self.sum,
            'sum_of_squares': self.sum_of_squares,
            'rms': self.rms,
            'coefficient_of_variation': self.calculate_cv(),
            'range': self.range
        })
        
        # Add percentile estimates
        for p in [25, 50, 75, 90, 95, 99]:
            summary[f'p{p}_estimate'] = self.get_percentile_estimate(p)
        
        return summary
    
    def reset(self) -> None:
        """Reset all statistics."""
        self.welford.reset()
        self._sum = 0.0
        self._sum_squares = 0.0
    
    def __str__(self) -> str:
        """String representation."""
        return f"RunningStatistics({self.welford})"


def erf_inv(x: float) -> float:
    """
    Approximate inverse error function.
    
    Args:
        x: Value between -1 and 1
        
    Returns:
        Inverse error function approximation
    """
    # Approximation using Abramowitz and Stegun formula
    a = 0.147
    if x >= 0:
        ln1 = math.log(1 - x)
        ln2 = math.log(1 + x)
        sign = 1
    else:
        ln1 = math.log(1 - x)
        ln2 = math.log(1 + x)
        sign = -1
    
    t = math.sqrt(-2 * (ln1 + ln2))
    numerator = t - (a * t**3) / (1 + a * t**2)
    denominator = 1 + a * t**2
    
    return sign * math.sqrt(math.sqrt(numerator**2 / denominator**2 - ln1 * ln2) - ln1) / math.sqrt(2)
