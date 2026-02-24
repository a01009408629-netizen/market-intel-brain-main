"""
Deterministic Randomness

This module provides deterministic random number generation for reproducible
mock data generation with configurable volatility patterns.
"""

import time
import logging
import hashlib
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .exceptions import RandomnessError, ConfigurationError


@dataclass
class RandomnessConfig:
    """Configuration for deterministic randomness."""
    seed: Optional[str] = None
    enable_deterministic: bool = True
    volatility_pattern: str = "stable"  # "stable", "volatile", "burst", "realistic"
    base_variance: float = 0.1
    time_based_variation: bool = False
    state_based_variation: bool = True
    reproducibility_window: int = 3600  # 1 hour


@dataclass
class RandomnessState:
    """State for deterministic random number generation."""
    seed: str
    position: int
    generated_count: int
    last_timestamp: float
    volatility_state: Dict[str, Any]


class BaseRandomGenerator(ABC):
    """Abstract base class for random number generators."""
    
    @abstractmethod
    def initialize(self, seed: str) -> None:
        """Initialize generator with seed."""
        pass
    
    @abstractmethod
    def next_float(self, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Get next float in range."""
        pass
    
    @abstractmethod
    def next_int(self, min_val: int = 0, max_val: int = 100) -> int:
        """Get next integer in range."""
        pass
    
    @abstractmethod
    def next_choice(self, choices: List[Any]) -> Any:
        """Get next choice from list."""
        pass
    
    @abstractmethod
    def next_gaussian(self, mean: float = 0.0, std_dev: float = 1.0) -> float:
        """Get next Gaussian-distributed float."""
        pass
    
    @abstractmethod
    def get_state(self) -> RandomnessState:
        """Get current generator state."""
        pass
    
    @abstractmethod
    def set_state(self, state: RandomnessState) -> None:
        """Set generator state."""
        pass


class DeterministicRandom(BaseRandomGenerator):
    """
    Deterministic random number generator with configurable volatility patterns.
    
    This class provides reproducible random number generation with
    different volatility patterns for testing and development.
    """
    
    def __init__(
        self,
        config: Optional[RandomnessConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize deterministic random generator.
        
        Args:
            config: Randomness configuration
            logger: Logger instance
        """
        self.config = config or RandomnessConfig()
        self.logger = logger or logging.getLogger("DeterministicRandom")
        
        self._state = RandomnessState(
            seed="",
            position=0,
            generated_count=0,
            last_timestamp=time.time(),
            volatility_state={}
        )
        
        self._initialize_seed()
        
        self.logger.info("DeterministicRandom initialized")
    
    def _initialize_seed(self):
        """Initialize the seed for deterministic generation."""
        if self.config.enable_deterministic:
            if self.config.seed:
                self._state.seed = self.config.seed
            else:
                # Generate seed from timestamp
                timestamp_str = str(time.time())
                self._state.seed = hashlib.sha256(timestamp_str.encode()).hexdigest()[:16]
        else:
            self._state.seed = "random"
    
    def initialize(self, seed: str) -> None:
        """Initialize generator with seed."""
        self._state.seed = seed
        self._state.position = 0
        self._state.generated_count = 0
        self._state.last_timestamp = time.time()
        self._state.volatility_state = {}
        
        self.logger.info(f"DeterministicRandom initialized with seed: {seed}")
    
    def next_float(self, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Get next float in range with volatility."""
        if not self.config.enable_deterministic:
            import random
            return random.uniform(min_val, max_val)
        
        # Generate deterministic float with volatility
        base_value = self._generate_base_float(min_val, max_val)
        volatility_adjustment = self._get_volatility_adjustment("float")
        
        result = min_val + (base_value * (max_val - min_val) * volatility_adjustment)
        result = max(min_val, min(max_val, result))
        
        self._update_state()
        return result
    
    def next_int(self, min_val: int = 0, max_val: int = 100) -> int:
        """Get next integer in range with volatility."""
        if not self.config.enable_deterministic:
            import random
            return random.randint(min_val, max_val)
        
        # Generate deterministic integer with volatility
        base_value = self._generate_base_int(min_val, max_val)
        volatility_adjustment = self._get_volatility_adjustment("int")
        
        result = min_val + int((base_value * (max_val - min_val) * volatility_adjustment))
        result = max(min_val, min(max_val, result))
        
        self._update_state()
        return result
    
    def next_choice(self, choices: List[Any]) -> Any:
        """Get next choice from list with volatility."""
        if not self.config.enable_deterministic:
            import random
            return random.choice(choices)
        
        if not choices:
            raise RandomnessError("Cannot choose from empty list")
        
        # Generate deterministic choice with volatility
        base_index = self._generate_base_int(0, len(choices) - 1)
        volatility_adjustment = self._get_volatility_adjustment("choice")
        
        adjusted_index = min(len(choices) - 1, int(base_index * volatility_adjustment))
        
        self._update_state()
        return choices[adjusted_index]
    
    def next_gaussian(self, mean: float = 0.0, std_dev: float = 1.0) -> float:
        """Get next Gaussian-distributed float with volatility."""
        if not self.config.enable_deterministic:
            import random
            return random.gauss(mean, std_dev)
        
        # Generate deterministic Gaussian with volatility
        base_value = self._generate_base_gaussian(mean, std_dev)
        volatility_adjustment = self._get_volatility_adjustment("gaussian")
        
        result = mean + (base_value * std_dev * volatility_adjustment)
        
        self._update_state()
        return result
    
    def _generate_base_float(self, min_val: float, max_val: float) -> float:
        """Generate base float value."""
        # Use position-based generation
        position = self._state.position
        self._state.position += 1
        
        # Generate using position
        return (position * 0.6180339887498948482) % 1.0  # Golden ratio
    
    def _generate_base_int(self, min_val: int, max_val: int) -> int:
        """Generate base integer value."""
        position = self._state.position
        self._state.position += 1
        
        # Generate using position
        return (position * 1103515245) % (max_val - min_val + 1)
    
    def _generate_base_gaussian(self, mean: float, std_dev: float) -> float:
        """Generate base Gaussian value."""
        position = self._state.position
        self._state.position += 1
        
        # Use Box-Muller transform for Gaussian
        u1 = (position * 4.0 / 2147483647.0) % 1.0 - 0.5
        v1 = ((position * 4.0 / 2147483647.0) % 1.0) * 2.0) - 1.0
        
        z = (position * 4.0 / 2147483647.0) % 1.0 - 0.5
        
        # Generate Gaussian value
        u1_squared = u1 * u1
        v1_squared = v1 * v1
        z_squared = z * z
        
        u1_v1 = u1 * v1
        u1_z = u1 * z
        
        u1_v1_cubed = u1_v1 * u1_v1
        u1_z_cubed = u1_z * u1_z
        
        # Box-Muller transform
        x = u1_v1_cubed - 3 * u1_v1 * z_squared + 2 * u1_z_cubed - z_squared * z
        y = 3 * z * (u1_v1 - u1_z) + 2 * u1 * (z_squared - v1_squared) - (v1_squared - u1_v1) * (z_squared - u1_v1)
        z = z * (z_squared - u1_squared) - (v1_squared - u1_v1)
        
        # Gaussian value
        if x > 0:
            value = (x ** (1.0 / 3.0)) - y / (3.0 * x) + z / (3.0 * x)
        else:
            value = 0.0
        
        return mean + (value * std_dev)
    
    def _get_volatility_adjustment(self, data_type: str) -> float:
        """Get volatility adjustment based on pattern."""
        if not self.config.enable_deterministic:
            return 1.0
        
        # Time-based variation
        if self.config.time_based_variation:
            time_factor = (time.time() - self._state.last_timestamp) / self.config.reproducibility_window
            time_variation = 0.8 + 0.4 * math.sin(time_factor * 2 * math.pi)
            return time_variation
        
        # State-based variation
        if self.config.state_based_variation:
            state_key = f"{data_type}_volatility"
            if state_key not in self._state.volatility_state:
                self._state.volatility_state[state_key] = 1.0
            else:
                # Cycle through volatility states
                self._state.volatility_state[state_key] = (
                    (self._state.volatility_state[state_key] % 1.0) + 0.1
                ) % 2.0
        
            return self._state.volatility_state[state_key]
        
        # Pattern-based volatility
        if self.config.volatility_pattern == "stable":
            return 1.0
        elif self.config.volatility_pattern == "volatile":
            return 0.5 + 0.5 * ((self._state.generated_count % 100) / 100.0)
        elif self.config.volatility_pattern == "burst":
            # Burst pattern: periods of high volatility
            burst_phase = (self._state.generated_count // 50) % 3
            if burst_phase == 0:
                return 0.1  # Low volatility
            elif burst_phase == 1:
                return 2.0  # High volatility
            else:
                return 0.3  # Medium volatility
        elif self.config.volatility_pattern == "realistic":
            # Realistic pattern with multiple factors
            return 0.7 + 0.3 * math.sin(self._state.generated_count * 0.01)
        else:
            return 1.0
    
    def _update_state(self):
        """Update generator state."""
        self._state.generated_count += 1
        self._state.last_timestamp = time.time()
    
    def get_state(self) -> RandomnessState:
        """Get current generator state."""
        return self._state
    
    def set_state(self, state: RandomnessState) -> None:
        """Set generator state."""
        self._state = state
        self.logger.info(f"DeterministicRandom state set: seed={state.seed}, position={state.position}")
    
    def get_config(self) -> RandomnessConfig:
        """Get current configuration."""
        return self.config
    
    def reset(self) -> None:
        """Reset generator to initial state."""
        self._state.position = 0
        self._state.generated_count = 0
        self._state.volatility_state = {}
        self._state.last_timestamp = time.time()
        self.logger.info("DeterministicRandom reset")


class VolatilitySimulator:
    """
    Simulates different volatility patterns for testing.
    
    This class provides realistic market volatility simulation
    for testing trading algorithms and financial systems.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("VolatilitySimulator")
        
        self.patterns = {
            "stable": self._stable_pattern,
            "trending": self._trending_pattern,
            "volatile": self._volatile_pattern,
            "crash": self._crash_pattern,
            "recovery": self._recovery_pattern
        }
    
    def simulate_pattern(self, pattern_name: str, data_points: int = 100) -> List[float]:
        """Simulate a specific volatility pattern."""
        if pattern_name not in self.patterns:
            raise RandomnessError(f"Unknown pattern: {pattern_name}")
        
        pattern_func = self.patterns[pattern_name]
        return pattern_func(data_points)
    
    def _stable_pattern(self, data_points: int) -> List[float]:
        """Generate stable market data."""
        import random
        random.seed(42)  # Fixed seed for reproducibility
        
        base_value = 100.0
        data = []
        
        for i in range(data_points):
            # Small random walk around base value
            change = random.uniform(-0.5, 0.5)
            base_value += change * 0.1
            data.append(base_value)
        
        return data
    
    def _trending_pattern(self, data_points: int) -> List[float]:
        """Generate trending market data."""
        import random
        random.seed(123)  # Fixed seed for reproducibility
        
        data = []
        trend = 0.5  # Upward trend
        
        for i in range(data_points):
            # Add trend with some noise
            noise = random.uniform(-0.2, 0.2)
            value = 100.0 + (i * trend) + noise
            data.append(max(0, value))
        
        return data
    
    def _volatile_pattern(self, data_points: int) -> List[float]:
        """Generate volatile market data."""
        import random
        random.seed(456)  # Fixed seed for reproducibility
        
        data = []
        
        for i in range(data_points):
            # High volatility with random jumps
            if i % 10 == 0:
                # Random jump
                jump = random.uniform(-10, 10)
                data.append(max(0, data[-1] + jump if data else 100))
            else:
                # High frequency noise
                noise = random.uniform(-2, 2)
                data.append(max(0, data[-1] + noise if data else 100))
        
        return data
    
    def _crash_pattern(self, data_points: int) -> List[float]:
        """Generate market crash data."""
        import random
        random.seed(789)  # Fixed seed for reproducibility
        
        data = []
        crash_point = random.randint(20, 30)
        
        for i in range(data_points):
            if i < crash_point:
                # Normal market with slight downward trend
                value = 100.0 - (i * 0.1) + random.uniform(-0.5, 0.5)
                data.append(max(0, value))
            else:
                # Sharp crash
                drop = random.uniform(20, 40)
                value = max(0, data[-1] - drop)
                data.append(value)
        
        return data
    
    def _recovery_pattern(self, data_points: int) -> List[float]:
        """Generate market recovery data."""
        import random
        random.seed(321)  # Fixed seed for reproducibility
        
        data = []
        recovery_start = random.randint(10, 20)
        
        for i in range(data_points):
            if i < recovery_start:
                # Continue crash
                value = max(0, data[-1] - random.uniform(1, 3))
                data.append(value)
            else:
                # Gradual recovery
                recovery_rate = 0.02
                value = min(100, data[-1] + (i - recovery_start) * recovery_rate)
                data.append(value)
        
        return data


# Global deterministic random instance
_global_deterministic_random: Optional[DeterministicRandom] = None


def get_deterministic_random(**kwargs) -> DeterministicRandom:
    """
    Get or create global deterministic random generator.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global DeterministicRandom instance
    """
    global _global_deterministic_random
    if _global_deterministic_random is None:
        _global_deterministic_random = DeterministicRandom(**kwargs)
    return _global_deterministic_random


# Import required modules
import math
