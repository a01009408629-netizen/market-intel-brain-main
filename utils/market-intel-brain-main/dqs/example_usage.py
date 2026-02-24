"""
Data Quality System - Example Usage

This file demonstrates how to use the DQS system for high-performance
outlier detection with Welford's online algorithm and memory efficiency.
"""

import asyncio
import time
import random
import warnings
from typing import List, Dict, Any

from dqs import (
    OutlierDetector, 
    SanityChecker, 
    DetectorConfig,
    get_sanity_checker,
    check_data_quality,
    AnomalyDetectedWarning
)
from dqs.exceptions import OutlierRejectedError


async def demonstrate_basic_outlier_detection():
    """Demonstrate basic outlier detection with Welford's algorithm."""
    print("=== Basic Outlier Detection ===\n")
    
    # Create detector for AAPL stock
    config = DetectorConfig(
        z_score_threshold=3.0,
        min_samples=10,
        auto_reject=False,
        warning_enabled=True
    )
    
    detector = OutlierDetector("AAPL", config)
    
    # Generate normal data points
    print("1. Adding normal data points (should be accepted):")
    normal_prices = [150.0, 150.5, 151.0, 149.8, 150.2, 150.9, 151.3, 149.5, 150.7, 151.1]
    
    for i, price in enumerate(normal_prices):
        result = await detector.add_sample(price)
        print(f"   Sample {i+1}: {price:.2f} -> {result.action} (z-score: {result.z_score:.3f if result.z_score else 'N/A'})")
    
    # Add an outlier
    print("\n2. Adding outlier (should trigger warning):")
    outlier_price = 200.0  # Significant jump
    
    try:
        result = await detector.add_sample(outlier_price)
        print(f"   Outlier: {outlier_price:.2f} -> {result.action}")
        print(f"   Z-score: {result.z_score:.3f}")
        print(f"   Message: {result.message}")
    except OutlierRejectedError as e:
        print(f"   Outlier rejected: {e}")
    
    # Show statistics
    print("\n3. Current statistics:")
    stats = detector.get_current_statistics()
    print(f"   Total samples: {stats['total_samples']}")
    print(f"   Outliers: {stats['outlier_count']}")
    print(f"   Outlier rate: {stats['outlier_rate']:.2%}")
    print(f"   Mean: {stats['mean']:.4f}")
    print(f"   Std dev: {stats['stddev']:.4f}")
    print(f"   Min: {stats['min']:.4f}")
    print(f"   Max: {stats['max']:.4f}")


async def demonstrate_memory_efficiency():
    """Demonstrate memory efficiency with Welford's algorithm."""
    print("\n=== Memory Efficiency Demonstration ===\n")
    
    # Create detector
    detector = OutlierDetector("MEMORY_TEST")
    
    # Add many data points
    print("1. Adding 1000 data points...")
    start_time = time.time()
    
    for i in range(1000):
        # Normal distribution around 100
        value = random.gauss(100, 5)
        await detector.add_sample(value)
    
    elapsed = time.time() - start_time
    print(f"   Processed 1000 points in {elapsed:.3f} seconds")
    
    # Show memory efficiency
    print("\n2. Memory efficiency:")
    stats = detector.get_current_statistics()
    print(f"   Samples processed: {stats['total_samples']}")
    print(f"   Memory used: Only running statistics (no history storage)")
    print(f"   Mean: {stats['mean']:.4f}")
    print(f"   Std dev: {stats['stddev']:.4f}")
    
    # Compare with theoretical full storage
    theoretical_memory = 1000 * 8  # 8 bytes per float
    actual_memory = 5 * 8  # 5 floats for Welford stats
    print(f"   Theoretical memory (full storage): {theoretical_memory} bytes")
    print(f"   Actual memory (Welford): {actual_memory} bytes")
    print(f"   Memory savings: {((theoretical_memory - actual_memory) / theoretical_memory * 100):.1f}%")


async def demonstrate_z_score_calculation():
    """Demonstrate Z-score calculation and thresholding."""
    print("\n=== Z-Score Calculation ===\n")
    
    detector = OutlierDetector("ZSCORE_TEST")
    
    # Build baseline data
    baseline_data = [100, 101, 99, 102, 98, 100, 101, 99, 100, 102]
    for value in baseline_data:
        await detector.add_sample(value)
    
    print("1. Baseline statistics:")
    stats = detector.get_current_statistics()
    print(f"   Mean: {stats['mean']:.2f}")
    print(f"   Std dev: {stats['stddev']:.2f}")
    
    # Test different values
    test_values = [95, 105, 90, 110, 85, 115]
    
    print("\n2. Testing different values:")
    for value in test_values:
        z_score = detector.calculate_z_score(value)
        is_outlier, z_check = detector.is_outlier(value)
        
        print(f"   Value {value:3d}: Z-score = {z_score:6.2f} -> {'OUTLIER' if is_outlier else 'Normal'}")
    
    # Show Z-score formula
    print("\n3. Z-Score Formula:")
    print("   Z = (x - μ) / σ")
    print("   Where:")
    print("   x = observed value")
    print("   μ = mean")
    print("   σ = standard deviation")


async def demonstrate_auto_reject():
    """Demonstrate automatic outlier rejection."""
    print("\n=== Auto-Reject Demonstration ===\n")
    
    # Create detector with auto-reject enabled
    config = DetectorConfig(
        z_score_threshold=2.5,
        min_samples=5,
        auto_reject=True,
        warning_enabled=False
    )
    
    detector = OutlierDetector("AUTO_REJECT", config)
    
    # Build baseline
    baseline = [50, 51, 49, 50, 52]
    for value in baseline:
        await detector.add_sample(value)
    
    print("1. Baseline data accepted:")
    for value in baseline:
        print(f"   {value}")
    
    print("\n2. Testing outlier (should be rejected):")
    try:
        result = await detector.add_sample(100)  # Clear outlier
        print(f"   Unexpected success: {result.action}")
    except OutlierRejectedError as e:
        print(f"   ✓ Outlier rejected: {e}")
    
    print("\n3. Statistics after rejection:")
    stats = detector.get_current_statistics()
    print(f"   Total samples: {stats['total_samples']} (rejection not counted)")
    print(f"   Outliers: {stats['outlier_count']}")


async def demonstrate_sanity_checker():
    """Demonstrate high-level sanity checker."""
    print("\n=== Sanity Checker Demonstration ===\n")
    
    # Create sanity checker
    from dqs.sanity_checker import SanityCheckConfig
    
    config = SanityCheckConfig(
        quality_score_threshold=0.8,
        alert_callback=lambda alert: print(f"   🚨 ALERT: {alert['asset_id']} - {alert['issues']}")
    )
    
    checker = SanityChecker(config)
    
    # Register multiple assets
    assets = ["AAPL", "GOOGL", "MSFT", "TSLA"]
    for asset in assets:
        checker.register_asset(asset)
    
    print("1. Registered assets:")
    for asset in assets:
        print(f"   - {asset}")
    
    # Add data points
    print("\n2. Adding data points:")
    
    # Normal data
    for i in range(5):
        for asset in assets:
            price = 100 + random.gauss(0, 2)
            result = await checker.check_data_point(asset, price)
            if i == 0:  # Show first result
                print(f"   {asset}: {price:.2f} -> Quality: {result.quality_score:.2f}")
    
    # Add outlier for one asset
    print("\n3. Adding outlier for TSLA:")
    result = await checker.check_data_point("TSLA", 150.0)
    print(f"   TSLA: 150.00 -> Quality: {result.quality_score:.2f}")
    print(f"   Issues: {result.issues}")
    
    # Show global statistics
    print("\n4. Global statistics:")
    global_stats = checker.get_global_statistics()
    print(f"   Monitored assets: {global_stats['monitored_assets']}")
    print(f"   Total checks: {global_stats['total_checks']}")
    print(f"   Total outliers: {global_stats['total_outliers']}")
    print(f"   Overall outlier rate: {global_stats['overall_outlier_rate']:.2%}")


async def demonstrate_batch_processing():
    """Demonstrate batch processing capabilities."""
    print("\n=== Batch Processing ===\n")
    
    checker = get_sanity_checker()
    
    # Generate batch data
    batch_data = []
    for i in range(20):
        asset_id = random.choice(["AAPL", "GOOGL"])
        value = random.gauss(100, 5)
        timestamp = time.time() + i
        
        batch_data.append({
            'asset_id': asset_id,
            'value': value,
            'timestamp': timestamp
        })
    
    print(f"1. Processing batch of {len(batch_data)} data points...")
    
    # Process batch
    start_time = time.time()
    results = await checker.check_batch(batch_data)
    elapsed = time.time() - start_time
    
    print(f"   Processed in {elapsed:.3f} seconds")
    
    # Show results summary
    valid_count = sum(1 for r in results if r.is_valid)
    outlier_count = len(results) - valid_count
    
    print(f"   Valid: {valid_count}, Outliers: {outlier_count}")
    
    # Show sample results
    print("\n2. Sample results:")
    for i, result in enumerate(results[:5]):
        print(f"   {result.asset_id}: {result.value:.2f} -> {result.action}")


async def demonstrate_redis_persistence():
    """Demonstrate Redis persistence for detector state."""
    print("\n=== Redis Persistence ===\n")
    
    try:
        # Create detector with Redis backend
        detector = OutlierDetector("REDIS_TEST", storage_backend="redis")
        
        # Add some data
        print("1. Adding data points...")
        for i in range(10):
            value = random.gauss(50, 3)
            await detector.add_sample(value)
        
        stats = detector.get_current_statistics()
        print(f"   Samples: {stats['total_samples']}")
        print(f"   Mean: {stats['mean']:.4f}")
        
        # Simulate restart by creating new detector
        print("\n2. Simulating restart - loading state...")
        new_detector = OutlierDetector("REDIS_TEST", storage_backend="redis")
        loaded = await new_detector.load_state()
        
        if loaded:
            new_stats = new_detector.get_current_statistics()
            print(f"   ✓ State loaded successfully")
            print(f"   Samples: {new_stats['total_samples']}")
            print(f"   Mean: {new_stats['mean']:.4f}")
        else:
            print("   ✗ No state found")
        
        # Clean up
        await detector.close()
        await new_detector.close()
        
    except Exception as e:
        print(f"   Redis not available: {e}")
        print("   Skipping Redis demonstration")


async def demonstrate_advanced_features():
    """Demonstrate advanced detection features."""
    print("\n=== Advanced Features ===\n")
    
    # Create detector with multiple detection methods
    config = DetectorConfig(
        z_score_threshold=3.0,
        enable_iqr_detection=True,
        enable_mad_detection=True,
        sliding_window_size=50
    )
    
    detector = OutlierDetector("ADVANCED", config)
    
    # Build sliding window
    print("1. Building sliding window with normal data...")
    normal_data = [random.gauss(100, 5) for _ in range(50)]
    for value in normal_data:
        await detector.add_sample(value)
    
    print(f"   Added {len(normal_data)} normal data points")
    
    # Test with different types of outliers
    print("\n2. Testing different outlier types:")
    
    # Extreme value outlier
    extreme_result = await detector.add_sample(200.0)
    print(f"   Extreme outlier (200): {extreme_result.action}")
    
    # Moderate outlier
    moderate_result = await detector.add_sample(115.0)
    print(f"   Moderate outlier (115): {moderate_result.action}")
    
    # Normal value
    normal_result = await detector.add_sample(102.0)
    print(f"   Normal value (102): {normal_result.action}")
    
    # Show recent outliers
    print("\n3. Recent outliers:")
    recent_outliers = detector.get_recent_outliers(5)
    for outlier in recent_outliers:
        print(f"   {outlier.timestamp}: {outlier.value:.2f} (z={outlier.z_score:.2f})")


async def demonstrate_global_functions():
    """Demonstrate global convenience functions."""
    print("\n=== Global Functions ===\n")
    
    # Use global functions
    print("1. Using global check_data_quality function:")
    result = await check_data_quality("GLOBAL_TEST", 150.0)
    print(f"   Result: Quality score {result.quality_score:.2f}, Valid: {result.is_valid}")
    
    # Register monitored asset globally
    print("\n2. Registering monitored asset:")
    from dqs import register_monitored_asset
    detector = register_monitored_asset("GLOBAL_ASSET", z_score_threshold=2.5)
    print(f"   Registered: {detector.asset_id}")
    
    # Get global statistics
    print("\n3. Global quality statistics:")
    from dqs import get_quality_statistics
    stats = get_quality_statistics()
    print(f"   Monitored assets: {stats['monitored_assets']}")
    print(f"   Total checks: {stats['total_checks']}")


async def demonstrate_performance():
    """Demonstrate performance characteristics."""
    print("\n=== Performance Demonstration ===\n")
    
    detector = OutlierDetector("PERF_TEST")
    
    # Test different batch sizes
    batch_sizes = [100, 1000, 10000]
    
    for batch_size in batch_sizes:
        print(f"1. Processing {batch_size} data points...")
        
        start_time = time.time()
        
        for i in range(batch_size):
            value = random.gauss(100, 10)
            await detector.add_sample(value)
        
        elapsed = time.time() - start_time
        throughput = batch_size / elapsed
        
        print(f"   Time: {elapsed:.3f}s")
        print(f"   Throughput: {throughput:.0f} points/second")
        
        # Show memory usage is constant
        stats = detector.get_current_statistics()
        print(f"   Memory: Constant (only {len(stats)} statistical values)")
        
        # Reset for next test
        detector.reset()
        print()


async def main():
    """Run all demonstrations."""
    print("Data Quality System (DQS) - Complete Demonstration")
    print("=" * 60)
    
    # Suppress warnings for cleaner output
    warnings.filterwarnings("ignore", category=AnomalyDetectedWarning)
    
    try:
        await demonstrate_basic_outlier_detection()
        await demonstrate_memory_efficiency()
        await demonstrate_z_score_calculation()
        await demonstrate_auto_reject()
        await demonstrate_sanity_checker()
        await demonstrate_batch_processing()
        await demonstrate_redis_persistence()
        await demonstrate_advanced_features()
        await demonstrate_global_functions()
        await demonstrate_performance()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Welford's online algorithm for memory efficiency")
        print("✓ Z-score calculation: Z = (x - μ) / σ")
        print("✓ Outlier detection with configurable thresholds")
        print("✓ Auto-reject and warning mechanisms")
        print("✓ Redis persistence for state management")
        print("✓ Batch processing capabilities")
        print("✓ High-level sanity checker interface")
        print("✓ Global convenience functions")
        print("✓ Performance optimization")
        print("✓ Multiple detection methods (Z-score, IQR, MAD)")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up global checker
        try:
            global_checker = get_sanity_checker()
            await global_checker.close()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
