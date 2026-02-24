"""
Production Configuration - LIVE_PRODUCTION Mode
Optimized for 8GB RAM + Mechanical HDD
"""

from typing import Dict, Any
from infrastructure import RingBufferConfig, AOFConfig, RateLimitConfig, RateLimitUnit


# Production Environment Configuration
PRODUCTION_CONFIG = {
    # Hardware Constraints
    "hardware": {
        "ram_gb": 8,
        "storage_type": "mechanical_hdd",
        "max_memory_usage_mb": 6400,  # 80% of 8GB
        "max_cpu_usage_percent": 75
    },
    
    # Data Sources Configuration
    "data_sources": {
        "total_sources": 13,
        "websocket_sources": ["binance_ws", "kraken_ws", "huobi_ws"],
        "rest_sources": [
            "binance_rest", "okx_rest", "coinbase_rest",
            "bloomberg_rest", "reuters_rest", "coindesk_rest",
            "cryptocompare_rest", "messari_rest", 
            "glassnode_rest", "coinmetrics_rest"
        ],
        "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"],
        "news_sources": ["bloomberg_rest", "reuters_rest", "coindesk_rest"]
    },
    
    # Ring Buffer Configuration (LMAX Disruptor Pattern)
    "ring_buffer": RingBufferConfig(
        capacity=50000,  # Optimized for 8GB RAM
        backpressure_threshold=0.8,  # 80% capacity triggers backpressure
        drop_stale_threshold_ms=1000,  # Drop ticks older than 1 second
        batch_size=200,  # Process in batches of 200
        flush_interval_ms=500  # Flush every 500ms
    ),
    
    # AOF Writer Configuration (HDD Optimized)
    "aof_writer": AOFConfig(
        file_path="data/production_market_data.aof",
        max_file_size_mb=200,  # Rotate at 200MB for HDD
        compression_type="lz4",  # Fast compression for HDD
        buffer_size_mb=5,  # 5MB buffer for HDD sequential writes
        sync_interval_ms=2000,  # Sync every 2 seconds
        enable_checksum=True  # Enable data integrity checks
    ),
    
    # Rate Limiting Configuration (13 Sources)
    "rate_limits": {
        # High-frequency WebSocket sources
        "binance_ws": RateLimitConfig(
            max_tokens=50000,
            refill_rate=1000,
            unit=RateLimitUnit.SECOND,
            weight=1
        ),
        "kraken_ws": RateLimitConfig(
            max_tokens=10000,
            refill_rate=200,
            unit=RateLimitUnit.SECOND,
            weight=1
        ),
        "huobi_ws": RateLimitConfig(
            max_tokens=20000,
            refill_rate=400,
            unit=RateLimitUnit.SECOND,
            weight=1
        ),
        
        # REST API sources
        "binance_rest": RateLimitConfig(
            max_tokens=2400,
            refill_rate=40,
            unit=RateLimitUnit.MINUTE,
            weight=1
        ),
        "okx_rest": RateLimitConfig(
            max_tokens=1200,
            refill_rate=20,
            unit=RateLimitUnit.MINUTE,
            weight=1
        ),
        "coinbase_rest": RateLimitConfig(
            max_tokens=10000,
            refill_rate=100,
            unit=RateLimitUnit.MINUTE,
            weight=1
        ),
        
        # News sources (lower limits)
        "bloomberg_rest": RateLimitConfig(
            max_tokens=1000,
            refill_rate=100,
            unit=RateLimitUnit.MINUTE,
            weight=2
        ),
        "reuters_rest": RateLimitConfig(
            max_tokens=500,
            refill_rate=50,
            unit=RateLimitUnit.MINUTE,
            weight=2
        ),
        "coindesk_rest": RateLimitConfig(
            max_tokens=800,
            refill_rate=80,
            unit=RateLimitUnit.MINUTE,
            weight=2
        ),
        
        # Analytics sources
        "cryptocompare_rest": RateLimitConfig(
            max_tokens=3000,
            refill_rate=50,
            unit=RateLimitUnit.MINUTE,
            weight=1
        ),
        "messari_rest": RateLimitConfig(
            max_tokens=2000,
            refill_rate=30,
            unit=RateLimitUnit.MINUTE,
            weight=1
        ),
        "glassnode_rest": RateLimitConfig(
            max_tokens=1000,
            refill_rate=20,
            unit=RateLimitUnit.MINUTE,
            weight=3
        ),
        "coinmetrics_rest": RateLimitConfig(
            max_tokens=1500,
            refill_rate=25,
            unit=RateLimitUnit.MINUTE,
            weight=3
        )
    },
    
    # Performance Monitoring
    "monitoring": {
        "metrics_interval_seconds": 30,
        "alert_thresholds": {
            "memory_usage_percent": 80,
            "cpu_usage_percent": 75,
            "ring_buffer_utilization": 0.9,
            "rate_limit_utilization": 0.8,
            "disk_io_wait_ms": 100
        },
        "log_levels": {
            "production": "INFO",
            "debug": False
        }
    },
    
    # Data Retention
    "retention": {
        "tick_data_days": 7,  # Keep tick data for 7 days
        "news_data_days": 30,  # Keep news for 30 days
        "compressed_backup": True,  # Compress old data
        "cleanup_interval_hours": 24  # Run cleanup daily
    },
    
    # Security
    "security": {
        "encryption_algorithm": "AES-256",
        "key_derivation_iterations": 100000,
        "secrets_rotation_days": 30,
        "api_timeout_seconds": 30,
        "max_retries": 3,
        "retry_backoff_base": 2.0
    }
}


def get_production_config() -> Dict[str, Any]:
    """Get production configuration."""
    return PRODUCTION_CONFIG


def get_rate_limit_configs() -> Dict[str, RateLimitConfig]:
    """Get rate limit configurations for all sources."""
    return PRODUCTION_CONFIG["rate_limits"]


def get_hardware_constraints() -> Dict[str, Any]:
    """Get hardware constraints."""
    return PRODUCTION_CONFIG["hardware"]


def get_data_sources_config() -> Dict[str, Any]:
    """Get data sources configuration."""
    return PRODUCTION_CONFIG["data_sources"]


def get_monitoring_config() -> Dict[str, Any]:
    """Get monitoring configuration."""
    return PRODUCTION_CONFIG["monitoring"]


if __name__ == "__main__":
    # Print configuration summary
    config = get_production_config()
    
    print("🔧 Production Configuration Summary")
    print("=" * 50)
    print(f"Hardware: {config['hardware']['ram_gb']}GB RAM + {config['hardware']['storage_type']}")
    print(f"Data Sources: {config['data_sources']['total_sources']}")
    print(f"WebSocket Sources: {len(config['data_sources']['websocket_sources'])}")
    print(f"REST Sources: {len(config['data_sources']['rest_sources'])}")
    print(f"Ring Buffer Capacity: {config['ring_buffer'].capacity:,}")
    print(f"AOF Buffer Size: {config['aof_writer'].buffer_size_mb}MB")
    print(f"Compression: {config['aof_writer'].compression_type}")
    print(f"Rate Limited Endpoints: {len(config['rate_limits'])}")
    print("=" * 50)
