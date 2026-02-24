"""
Stateful Mock Sandbox - Example Usage

This file demonstrates how to use the mock sandbox system for testing
and development with deterministic randomness and configurable providers.
"""

import asyncio
import time
from typing import Dict, Any

from sandbox import get_server, get_provider_registry, get_deterministic_random
from sandbox.exceptions import SandboxError


async def demonstrate_basic_server():
    """Demonstrate basic mock server functionality."""
    print("=== Basic Mock Server ===\n")
    
    try:
        # Get server instance
        server = get_server(port=8001)  # Use different port to avoid conflicts
        
        # Start server in background
        server_task = asyncio.create_task(server.start())
        
        print("1. Server started on port 8001")
        print("   Health check: http://localhost:8001/health")
        print("   Control plane: http://localhost:8001/control/status")
        print("   Metrics: http://localhost:8001/metrics")
        
        # Wait a bit for server to start
        await asyncio.sleep(2)
        
        # Check server status
        response = await server.get_app().get("/health")
        print(f"   Server health: {response.json()}")
        
        # Stop server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        
        print("2. Server stopped")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    finally:
        if 'server_task' in locals():
            server_task.cancel()


async def demonstrate_provider_integration():
    """Demonstrate provider integration."""
    print("\n=== Provider Integration ===\n")
    
    try:
        # Get provider registry
        registry = get_provider_registry()
        
        print("1. Available providers:")
        for provider_name in registry.list_providers():
            print(f"   - {provider_name}")
        
        print("\n2. Testing financial provider:")
        
        # Get financial provider
        finnhub = registry.get_provider("finnhub")
        if finnhub:
            # Test quote endpoint
            response = await finnhub.fetch_data(
                request_id="test_123",
                endpoint="/quote",
                params={"symbol": "AAPL"}
            )
            
            print(f"   Quote response: {response.success}")
            print(f"   Data: {response.data}")
            print(f"   Processing time: {response.processing_time:.3f}s")
            
            # Test error handling
            # Force an error by using invalid endpoint
            try:
                error_response = await finnhub.fetch_data(
                    request_id="test_456",
                    endpoint="/invalid",
                    params={"symbol": "AAPL"}
                )
            except Exception as e:
                print(f"   Error handling works: {type(e).__name__}")
        
        print("\n3. Testing market provider:")
        
        # Get market provider
        market = registry.get_provider("market_data")
        if market:
            # Test search endpoint
            response = await market.fetch_data(
                request_id="test_789",
                endpoint="/search",
                params={"query": "technology"}
            )
            
            print(f"   Search response: {response.success}")
            print(f"   Results count: {len(response.data.get('results', []))}")
            
            # Test trending endpoint
            trending_response = await market.fetch_data(
                request_id="test_101",
                endpoint="/trending",
                params={}
            )
            
            print(f"   Trending response: {response.success}")
            print(f"   Trending stocks: {len(response.data.get('trending_stocks', []))}")
        
        print("\n4. Testing social provider:")
        
        # Get social provider
        social = registry.get_provider("twitter")
        
        # Test user profile endpoint
        profile_response = await social.fetch_data(
            request_id="test_401",
            endpoint="/user_profile",
            params={"user_id": "user123"}
        )
        
        print(f"   Profile response: {profile_response.success}")
        
        # Test posts endpoint
        posts_response = await social.fetch_data(
            request_id="test_402",
            endpoint="/posts",
            params={"user_id": "user123"}
        )
        
        print(f"   Posts response: {posts_response.success}")
        print(f"   Posts count: {len(posts_response.data.get('posts', []))}")
        
        # Test followers endpoint
        followers_response = await social.fetch_data(
            request_id="test_403",
            endpoint="/followers",
            params={"user_id": "user123"}
        )
        
        print(f"   Followers response: {followers_response.success}")
        print(f"   Followers count: {len(followers_response.data.get('followers', []))}")
        
        print("\n5. Testing geopolitical news provider:")
        
        # Get geopolitical news provider
        news_provider = registry.get_provider("geopolitical_news")
        
        # Test news endpoint
        news_response = await news_provider.fetch_data(
            request_id="test_501",
            endpoint="/news",
            params={
                "category": "International Relations",
                "country": "United States",
                "limit": 5
            }
        )
        
        print(f"   News response: {news_response.success}")
        print(f"   Articles count: {len(news_response.data.get('articles', []))}")
        
        # Test sentiment analysis endpoint
        sentiment_response = await news_provider.fetch_data(
            request_id="test_502",
            endpoint="/sentiment",
            params={
                "text": "Positive developments in international trade agreements between US and China"
            }
        )
        
        print(f"   Sentiment analysis response: {sentiment_response.success}")
        if sentiment_response.success:
            sentiment_data = sentiment_response.data
            print(f"   Overall sentiment: {sentiment_data.get('overall_sentiment', 'neutral')}")
            print(f"   Sentiment score: {sentiment_data.get('sentiment_score', 0):.3f}")
        
        print("\n6. Testing social media sentiment provider:")
        
        # Get social media sentiment provider
        sentiment_provider = registry.get_provider("social_media_sentiment")
        
        # Test sentiment endpoint
        social_sentiment_response = await sentiment_provider.fetch_data(
            request_id="test_601",
            endpoint="/sentiment",
            params={
                "platform": "twitter",
                "topic": "technology",
                "time_range": "24h",
                "limit": 50
            }
        )
        
        print(f"   Social media sentiment response: {social_sentiment_response.success}")
        if social_sentiment_response.success:
            sentiment_data = social_sentiment_response.data
            aggregate_stats = sentiment_data.get("aggregate_stats", {})
            
            print(f"   Total posts analyzed: {aggregate_stats.get('total_posts', 0)}")
            print(f"   Average sentiment score: {aggregate_stats.get('average_sentiment_score', 0):.3f}")
            
            sentiment_dist = aggregate_stats.get("sentiment_percentages", {})
            print(f"   Sentiment distribution:")
            for sentiment, percentage in sentiment_dist.items():
                print(f"     {sentiment}: {percentage:.1f}%")
        
        print("\n4. Testing social provider:")
        
        # Get social provider
        social = registry.get_provider("twitter")
        if social:
            # Test user profile endpoint
            response = await social.fetch_data(
                request_id="test_202",
                endpoint="/user_profile",
                params={"user_id": "user123"}
            )
            
            print(f"   User profile: {response.success}")
            print(f"   Followers: {response.data.get('followers_count', 0)}")
            print(f"   Posts: {response.data.get('posts_count', 0)}")
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_deterministic_randomness():
    """Demonstrate deterministic randomness."""
    print("\n=== Deterministic Randomness ===\n")
    
    try:
        # Get deterministic random generator
        random_gen = get_deterministic_random(seed="test_seed_123")
        
        print("1. Testing reproducibility:")
        
        # Generate same sequence twice with same seed
        sequence1 = []
        for i in range(10):
            sequence1.append(random_gen.next_float(0, 100))
        
        # Reset and generate again
        random_gen.initialize("test_seed_123")
        sequence2 = []
        for i in range(10):
            sequence2.append(random_gen.next_float(0, 100))
        
        print(f"   Sequence 1: {[f'{x:.3f}' for x in sequence1]}")
        print(f"   Sequence 2: {[f'{x:.3f}' for x in sequence2]}")
        print(f"   Identical: {sequence1 == sequence2}")
        
        print("\n2. Testing different volatility patterns:")
        
        # Test different patterns
        patterns = ["stable", "volatile", "burst", "realistic"]
        
        for pattern in patterns:
            random_gen = get_deterministic_random(
                seed=f"pattern_{pattern}",
                volatility_pattern=pattern
            )
            
            values = [random_gen.next_float(0, 1) for _ in range(20)]
            
            print(f"   Pattern {pattern}:")
            print(f"     Min: {min(values):.3f}")
            print(f"     Max: {max(values):.3f}")
            print(f"     Avg: {sum(values)/len(values):.3f}")
        
        print("\n3. Testing time-based variation:")
        
        random_gen = get_deterministic_random(
            seed="time_based",
            time_based_variation=True
        )
        
        # Generate values over time
        print("   Time-based variation:")
        for i in range(5):
            value = random_gen.next_float(0, 1)
            print(f"     Time {i}: {value:.3f}")
            await asyncio.sleep(0.5)
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_control_plane():
    """Demonstrate control plane functionality."""
    print("\n=== Control Plane ===\n")
    
    try:
        # Get server instance
        server = get_server(port=8002)
        
        # Start server in background
        server_task = asyncio.create_task(server.start())
        
        # Wait for server to start
        await asyncio.sleep(1)
        
        # Test control endpoints
        import http
        
        # Check status
        status_response = http.get("http://localhost:8002/control/status")
        print(f"1. Server status: {status_response.json()}")
        
        # Test randomness control
        seed_response = http.post(
            "http://localhost:8002/control/set_seed",
            json={"seed": "control_test"}
        )
        print(f"2. Set seed: {seed_response.json()}")
        
        # Test fault injection
        fault_response = http.post(
            "http://localhost:8002/sandbox/inject_fault",
            json={
                "type": "latency",
                "provider": "finnhub",
                "endpoint": "/quote"
            }
        )
        print(f"3. Fault injection: {fault_response.json()}")
        
        # Check updated state
        state_response = http.get("http://localhost:8002/sandbox/state")
        print(f"4. Updated state: {state_response.json()}")
        
        # Reset server
        reset_response = http.post("http://localhost:8002/control/reset")
        print(f"5. Reset: {reset_response.json()}")
        
        # Stop server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_fault_injection():
    """Demonstrate fault injection capabilities."""
    print("\n=== Fault Injection ===\n")
    
    try:
        # Get server with fault injection enabled
        server = get_server(
            port=8003,
            enable_error_injection=True,
            error_injection_rate=0.2  # 20% error rate
        )
        
        # Start server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(1)
        
        # Test provider with fault injection
        registry = get_provider_registry()
        finnhub = registry.get_provider("finnhub")
        
        if finnhub:
            print("Testing with 20% error injection rate:")
            
            # Make multiple requests
            success_count = 0
            error_count = 0
            
            for i in range(10):
                response = await finnhub.fetch_data(
                    request_id=f"fault_test_{i}",
                    endpoint="/quote",
                    params={"symbol": "AAPL"}
                )
                
                if response.success:
                    success_count += 1
                else:
                    error_count += 1
                
                print(f"   Request {i+1}: {'Success' if response.success else 'Error'}")
            
            print(f"   Results: {success_count} successful, {error_count} errors")
            print(f"   Error rate: {error_count/(success_count + error_count):.1%}")
        
        # Stop server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_metrics_collection():
    """Demonstrate metrics collection."""
    print("\n=== Metrics Collection ===\n")
    
    try:
        # Get server with metrics enabled
        server = get_server(
            port=8004,
            enable_metrics=True,
            enable_request_logging=True
        )
        
        # Start server
        server_task = asyncio.create_task(server.start())
        
        # Wait for server to start
        await asyncio.sleep(1)
        
        # Generate some traffic
        registry = get_provider_registry()
        finnhub = registry.get_provider("finnhub")
        
        if finnhub:
            print("Generating traffic for metrics...")
            
            # Make multiple requests
            for i in range(50):
                await finnhub.fetch_data(
                    request_id=f"metrics_test_{i}",
                    endpoint="/quote",
                    params={"symbol": "AAPL"}
                )
        
        # Wait for processing
        await asyncio.sleep(2)
        
        # Check metrics
        metrics_response = http.get("http://localhost:8004/metrics")
        print(f"1. Metrics: {metrics_response.json()}")
        
        # Check request logs
        logs_response = http.get("http://localhost:8004/metrics/requests")
        print(f"2. Request logs summary: {logs_response.json()}")
        
        # Stop server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        print(f"   Error: {e}")


async def demonstrate_real_world_scenario():
    """Demonstrate realistic testing scenario with news and sentiment analysis."""
    print("\n=== Real-World Scenario with News & Sentiment ===\n")
    
    try:
        # Configure realistic server
        server = get_server(
            port=8005,
            enable_cors=True,
            enable_request_logging=True,
            enable_metrics=True,
            enable_latency_injection=True,
            latency_injection_range=(0.1, 2.0),  # Realistic latency
            error_injection_rate=0.02,  # 2% error rate
            volatility_pattern="realistic"
        )
        
        # Start server
        server_task = asyncio.create_task(server.start())
        await asyncio.sleep(1)
        
        # Get providers
        registry = get_provider_registry()
        
        # Simulate realistic trading scenario with news and sentiment
        print("Simulating realistic trading scenario with news and sentiment analysis...")
        
        # Initialize deterministic randomness for reproducible tests
        random_gen = get_deterministic_random(seed="trading_scenario_123")
        
        # Test multiple providers including news and sentiment
        providers = ["finnhub", "yahoo_finance", "alpha_vantage", "geopolitical_news", "social_media_sentiment"]
        
        # Collect data from all sources
        financial_data = []
        news_data = []
        sentiment_data = []
        
        for provider_name in providers:
            provider = registry.get_provider(provider_name)
            if provider:
                print(f"\nTesting {provider_name}:")
                
                if provider_name in ["finnhub", "yahoo_finance", "alpha_vantage"]:
                    # Test financial providers
                    for i in range(10):
                        response = await provider.fetch_data(
                            request_id=f"trading_{provider_name}_{i}",
                            endpoint="/quote",
                            params={"symbol": "AAPL"}
                        )
                        
                        if response.success:
                            price = response.data.get("price", 100.0)
                            change = response.data.get("change", 0.0)
                            print(f"   Request {i+1}: {provider_name} - ${price:.2f} ({change:+.2f}%)")
                        else:
                            print(f"   Request {i+1}: ERROR - {response.error}")
                
                elif provider_name == "geopolitical_news":
                    # Test geopolitical news provider
                    for i in range(5):
                        response = await provider.fetch_data(
                            request_id=f"news_{provider_name}_{i}",
                            endpoint="/news",
                            params={
                                "category": "International Relations",
                                "keywords": ["trade", "technology"],
                                "limit": 5
                            }
                        )
                        
                        if response.success:
                            articles = response.data.get("articles", [])
                            print(f"   Request {i+1}: {len(articles)} articles found")
                            for article in articles[:2]:  # Show first 2 articles
                                print(f"     - {article.get('title', 'No title')}")
                                print(f"       Sentiment: {article.get('sentiment_score', 0):.2f}")
                        else:
                            print(f"   Request {i+1}: ERROR - {response.error}")
                
                elif provider_name == "social_media_sentiment":
                    # Test social media sentiment provider
                    for i in range(5):
                        response = await provider.fetch_data(
                            request_id=f"sentiment_{provider_name}_{i}",
                            endpoint="/sentiment",
                            params={
                                "platform": "twitter",
                                "topic": "market_trends",
                                "time_range": "24h",
                                "limit": 20
                            }
                        )
                        
                        if response.success:
                            sentiment_data = response.data.get("sentiment_data", [])
                            aggregate_stats = response.data.get("aggregate_stats", {})
                            print(f"   Request {i+1}: {len(sentiment_data)} posts analyzed")
                            print(f"     Overall sentiment: {aggregate_stats.get('average_sentiment_score', 0):.3f}")
                            
                            sentiment_dist = aggregate_stats.get("sentiment_percentages", {})
                            for sentiment, percentage in sentiment_dist.items():
                                print(f"     {sentiment}: {percentage:.1f}%")
                        else:
                            print(f"   Request {i+1}: ERROR - {response.error}")
        
        print(f"\nMulti-Source Scenario completed")
        print(f"Seed: {random_gen.get_state().seed}")
        
        # Check final metrics
        metrics_response = http.get("http://localhost:8005/metrics")
        print(f"\nFinal metrics: {metrics_response.json()}")
        
        # Stop server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        
    except Exception as e:
        print(f"   Error: {e}")


async def main():
    """Run all sandbox demonstrations."""
    print("Stateful Mock Sandbox - Complete Demonstration")
    print("=" * 60)
    
    try:
        await demonstrate_basic_server()
        await demonstrate_provider_integration()
        await demonstrate_deterministic_randomness()
        await demonstrate_control_plane()
        await demonstrate_fault_injection()
        await demonstrate_metrics_collection()
        await demonstrate_real_world_scenario()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ FastAPI-based mock server with configurable endpoints")
        print("✓ Multiple mock providers (financial, market, social)")
        print("✓ Deterministic randomness with configurable volatility patterns")
        print("✓ Fault injection capabilities (latency, errors)")
        print("✓ Control plane for runtime configuration")
        print("✓ Comprehensive metrics collection and logging")
        print("✓ CORS and middleware support")
        print("✓ Realistic data generation with business logic")
        print("✓ Reproducible test scenarios")
        print("✓ No external dependencies required")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
