"""
Budget Firewall - Example Usage

This file demonstrates how to use the budget firewall system for
API cost management and rate limiting with token buckets.
"""

import asyncio
import time
import random
from typing import Dict, Any

from finops import (
    BudgetFirewall,
    BudgetConfig,
    CostConfig,
    get_firewall,
    get_calculator
)
from finops.exceptions import (
    BudgetExceededException,
    InsufficientTokensError
)


# Example API functions to protect
async def fetch_stock_data(provider: str, symbol: str) -> Dict[str, Any]:
    """Simulate fetching stock data from provider."""
    # Simulate API call
    await asyncio.sleep(random.uniform(0.1, 0.3))
    
    return {
        "symbol": symbol,
        "price": 100.0 + random.uniform(-5, 5),
        "timestamp": time.time(),
        "provider": provider
    }


async def sync_user_data(provider: str, user_data: Dict[str, Any]) -> bool:
    """Simulate syncing user data."""
    # Simulate sync operation
    await asyncio.sleep(random.uniform(0.5, 1.0))
    
    # Simulate occasional failure
    if random.random() < 0.1:  # 10% failure rate
        raise Exception(f"Sync failed for {provider}")
    
    return True


async def demonstrate_basic_budget_protection():
    """Demonstrate basic budget protection."""
    print("=== Basic Budget Protection ===\n")
    
    # Create budget firewall with default configuration
    firewall = get_firewall()
    await firewall.start()
    
    try:
        print("1. Testing budget limits:")
        
        # Make some requests within budget
        for i in range(5):
            try:
                await firewall.check_request(
                    provider="finnhub",
                    user_id="user123",
                    operation="fetch"
                )
                result = await fetch_stock_data("finnhub", "AAPL")
                print(f"   ✅ Request {i+1}: AAPL = ${result['price']:.2f}")
                
            except BudgetExceededException as e:
                print(f"   💰 Budget exceeded: {e}")
                break
            except InsufficientTokensError as e:
                print(f"   ⏱️ Rate limited: {e}")
                await asyncio.sleep(1)  # Wait for token refill
                continue
        
        # Show budget status
        status = await firewall.get_budget_status(user_id="user123")
        print(f"\n2. Budget status for user123:")
        print(f"   Current budget: ${status.current_budget:.6f}")
        print(f"   Total spent: ${status.total_spent:.6f}")
        print(f"   Remaining: ${status.remaining_budget:.6f}")
        print(f"   Utilization: {status.budget_utilization:.2%}")
        
    finally:
        await firewall.stop()


async def demonstrate_rate_limiting():
    """Demonstrate rate limiting with token buckets."""
    print("\n=== Rate Limiting ===\n")
    
    # Create budget firewall with aggressive rate limiting
    config = BudgetConfig(
        token_capacity=10,  # Small capacity for demonstration
        token_refill_rate=2.0,  # 2 tokens per second
        enable_rate_limiting=True
    )
    
    firewall = BudgetFirewall(config)
    await firewall.start()
    
    try:
        print("1. Testing rate limits:")
        
        # Make rapid requests to trigger rate limiting
        for i in range(15):
            try:
                start_time = time.time()
                await firewall.check_request(
                    provider="yahoo_finance",
                    user_id="user456",
                    operation="fetch"
                )
                
                result = await fetch_stock_data("yahoo_finance", "GOOGL")
                elapsed = time.time() - start_time
                
                print(f"   ✅ Request {i+1}: GOOGL = ${result['price']:.2f} ({elapsed:.3f}s)")
                
            except InsufficientTokensError as e:
                print(f"   ⏱️ Rate limited: {e}")
                await asyncio.sleep(0.5)  # Wait for token refill
                continue
            except BudgetExceededException as e:
                print(f"   💰 Budget exceeded: {e}")
                break
        
        # Show token bucket status
        bucket_key = "rate_limit:yahoo_finance:user456"
        if bucket_key in firewall._token_buckets:
            bucket_info = await firewall._token_buckets[bucket_key].get_bucket_info()
            print(f"\n2. Token bucket status:")
            print(f"   Available tokens: {bucket_info['current_tokens']}")
            print(f"   Capacity: {bucket_info['capacity']}")
            print(f"   Refill rate: {bucket_info['refill_rate']}/s")
            print(f"   Time to full: {bucket_info['time_to_full']:.1f}s")
        
    finally:
        await firewall.stop()


async def demonstrate_cost_calculation():
    """Demonstrate cost calculation with different providers."""
    print("\n=== Cost Calculation ===\n")
    
    # Get global cost calculator
    calculator = get_calculator()
    
    print("1. Calculating costs for different providers:")
    
    providers = ["finnhub", "yahoo_finance", "alpha_vantage", "polygon"]
    
    for provider in providers:
        # Calculate cost for a request
        cost_breakdown = calculator.calculate_request_cost(
            provider=provider,
            operation="fetch",
            request_size=1024,  # 1KB request
            response_size=2048,  # 2KB response
            metadata={"record_count": 100}  # 100 records
        )
        
        print(f"   {provider}:")
        print(f"     Base cost: ${cost_breakdown.base_cost:.6f}")
        print(f"     Weight multiplier: {cost_breakdown.weight_multiplier:.2f}")
        print(f"     Volume cost: ${cost_breakdown.volume_cost:.6f}")
        print(f"     Total cost: ${cost_breakdown.total_cost:.6f}")
    
    print("\n2. Monthly cost estimation:")
    
    # Estimate monthly costs
    for provider in providers:
        monthly_estimate = calculator.estimate_monthly_cost(
            provider=provider,
            operation="fetch",
            requests_per_day=100,
            avg_request_size=1024,
            avg_response_size=2048
        )
        
        print(f"   {provider}:")
        print(f"     Daily requests: {monthly_estimate['requests_per_day']}")
        print(f"     Cost per request: ${monthly_estimate['cost_per_request']:.6f}")
        print(f"     Daily cost: ${monthly_estimate['daily_cost']:.2f}")
        print(f"     Monthly cost: ${monthly_estimate['monthly_cost']:.2f}")


async def demonstrate_user_budgets():
    """Demonstrate user-specific budgets."""
    print("\n=== User Budgets ===\n")
    
    # Create firewall with user budgets enabled
    config = BudgetConfig(
        default_budget=50.0,  # $50 default
        enable_user_budgets=True,
        enable_hard_limit=True,
        soft_limit_threshold=0.8
    )
    
    firewall = BudgetFirewall(config)
    await firewall.start()
    
    try:
        print("1. Setting custom user budgets:")
        
        # Set different budgets for different users
        await firewall.set_user_budget("premium_user", 200.0)  # $200 budget
        await firewall.set_user_budget("basic_user", 25.0)    # $25 budget
        await firewall.set_user_budget("trial_user", 10.0)    # $10 budget
        
        print("   ✅ Set budgets for premium_user ($200), basic_user ($25), trial_user ($10)")
        
        print("\n2. Testing requests with different user budgets:")
        
        users = [
            ("premium_user", "AAPL"),
            ("basic_user", "GOOGL"),
            ("trial_user", "MSFT")
        ]
        
        for user_id, symbol in users:
            try:
                await firewall.check_request(
                    provider="finnhub",
                    user_id=user_id,
                    operation="fetch"
                )
                
                result = await fetch_stock_data("finnhub", symbol)
                print(f"   ✅ {user_id}: {symbol} = ${result['price']:.2f}")
                
            except BudgetExceededException as e:
                print(f"   💰 {user_id} budget exceeded: {e}")
            except Exception as e:
                print(f"   ❌ {user_id} error: {e}")
        
        print("\n3. Budget status for all users:")
        
        for user_id, _ in users:
            status = await firewall.get_budget_status(user_id=user_id)
            print(f"   {user_id}:")
            print(f"     Budget: ${status.current_budget:.6f}")
            print(f"     Spent: ${status.total_spent:.6f}")
            print(f"     Remaining: ${status.remaining_budget:.6f}")
            print(f"     Utilization: {status.budget_utilization:.2%}")
        
    finally:
        await firewall.stop()


async def demonstrate_provider_budgets():
    """Demonstrate provider-specific budgets."""
    print("\n=== Provider Budgets ===\n")
    
    # Create firewall with provider budgets enabled
    config = BudgetConfig(
        default_budget=100.0,
        enable_provider_budgets=True,
        enable_hard_limit=True
    )
    
    firewall = BudgetFirewall(config)
    await firewall.start()
    
    try:
        print("1. Setting custom provider budgets:")
        
        # Set different budgets for different providers
        await firewall.set_provider_budget("finnhub", 50.0)   # $50 budget
        await firewall.set_provider_budget("alpha_vantage", 30.0)  # $30 budget
        await firewall.set_provider_budget("polygon", 20.0)       # $20 budget
        
        print("   ✅ Set provider budgets: finnhub ($50), alpha_vantage ($30), polygon ($20)")
        
        print("\n2. Testing requests with different provider budgets:")
        
        providers = ["finnhub", "alpha_vantage", "polygon"]
        symbols = ["TSLA", "NVDA", "AMD"]
        
        for provider, symbol in zip(providers, symbols):
            try:
                await firewall.check_request(
                    provider=provider,
                    user_id="user789",
                    operation="fetch"
                )
                
                result = await fetch_stock_data(provider, symbol)
                print(f"   ✅ {provider}: {symbol} = ${result['price']:.2f}")
                
            except BudgetExceededException as e:
                print(f"   💰 {provider} budget exceeded: {e}")
            except Exception as e:
                print(f"   ❌ {provider} error: {e}")
        
        print("\n3. Provider budget status:")
        
        for provider in providers:
            status = await firewall.get_budget_status(provider=provider)
            print(f"   {provider}:")
            print(f"     Budget: ${status.current_budget:.6f}")
            print(f"     Spent: ${status.total_spent:.6f}")
            print(f"     Remaining: ${status.remaining_budget:.6f}")
            print(f"     Utilization: {status.budget_utilization:.2%}")
        
    finally:
        await firewall.stop()


async def demonstrate_real_world_scenario():
    """Demonstrate a real-world scenario with mixed usage."""
    print("\n=== Real-World Scenario ===\n")
    
    # Create comprehensive configuration
    budget_config = BudgetConfig(
        default_budget=100.0,
        budget_period=3600,  # 1 hour
        token_capacity=100,
        token_refill_rate=5.0,  # 5 tokens per second
        enable_user_budgets=True,
        enable_provider_budgets=True,
        enable_hard_limit=True,
        soft_limit_threshold=0.8
    )
    
    cost_config = CostConfig(
        default_cost_per_request=0.01,
        cost_weights={
            "finnhub": 0.015,
            "yahoo_finance": 0.008,
            "alpha_vantage": 0.025
        },
        cost_per_unit={
            "record": 0.0001,
            "kb": 0.00001
        }
    )
    
    firewall = BudgetFirewall(budget_config)
    await firewall.start()
    
    try:
        print("1. Simulating mixed usage pattern:")
        
        # Simulate different users with different usage patterns
        scenarios = [
            ("heavy_user", "finnhub", 20, "High usage user"),
            ("light_user", "yahoo_finance", 5, "Light usage user"),
            ("batch_user", "alpha_vantage", 50, "Batch processing user")
        ]
        
        for user_id, provider, request_count, description in scenarios:
            print(f"\n   {description} ({user_id}):")
            
            successful_requests = 0
            for i in range(request_count):
                try:
                    await firewall.check_request(
                        provider=provider,
                        user_id=user_id,
                        operation="fetch",
                        request_size=512,
                        response_size=1024,
                        metadata={"record_count": 50}
                    )
                    
                    result = await fetch_stock_data(provider, f"SYMBOL{i}")
                    successful_requests += 1
                    
                    if i < 5:  # Show first 5 requests
                        print(f"     ✅ Request {i+1}: {result['symbol']} = ${result['price']:.2f}")
                    
                except BudgetExceededException as e:
                    print(f"     💰 Budget exceeded after {successful_requests} requests")
                    break
                except InsufficientTokensError as e:
                    print(f"     ⏱️ Rate limited, waiting...")
                    await asyncio.sleep(1)
                    continue
                except Exception as e:
                    print(f"     ❌ Error: {e}")
            
            # Show final status
            status = await firewall.get_budget_status(user_id=user_id)
            print(f"     Final: ${status.total_spent:.6f}/${status.current_budget:.6f} "
                  f"({status.budget_utilization:.2%})")
        
        print("\n2. Overall statistics:")
        stats = firewall.get_statistics()
        print(f"   Total requests checked: {stats['requests_checked']}")
        print(f"   Requests allowed: {stats['requests_allowed']}")
        print(f"   Requests blocked: {stats['requests_blocked']}")
        print(f"   Allowance rate: {stats['allowance_rate']:.2%}")
        print(f"   Block rate: {stats['block_rate']:.2%}")
        
    finally:
        await firewall.stop()


async def demonstrate_cost_tracking():
    """Demonstrate cost tracking and reporting."""
    print("\n=== Cost Tracking ===\n")
    
    calculator = get_calculator()
    
    print("1. Batch cost calculation:")
    
    # Simulate a batch of requests
    requests = [
        {"provider": "finnhub", "operation": "fetch", "request_size": 1024},
        {"provider": "yahoo_finance", "operation": "fetch", "request_size": 512},
        {"provider": "alpha_vantage", "operation": "sync", "request_size": 2048},
        {"provider": "finnhub", "operation": "fetch", "request_size": 1024},
        {"provider": "polygon", "operation": "bulk", "request_size": 4096}
    ]
    
    batch_cost = calculator.calculate_batch_cost(requests)
    
    print(f"   Total requests: {len(requests)}")
    print(f"   Total cost: ${batch_cost.total_cost:.6f}")
    print(f"   Base cost: ${batch_cost.base_cost:.6f}")
    print(f"   Volume cost: ${batch_cost.volume_cost:.6f}")
    
    print("\n2. Cost breakdown by provider:")
    for provider, cost_info in batch_cost.calculation_details["providers"].items():
        print(f"   {provider}: {cost_info['count']} requests, ${cost_info['total_cost']:.6f}")
    
    print("\n3. Cost breakdown by operation:")
    for operation, cost_info in batch_cost.calculation_details["operations"].items():
        print(f"   {operation}: {cost_info['count']} requests, ${cost_info['total_cost']:.6f}")


async def main():
    """Run all budget firewall demonstrations."""
    print("Budget Firewall - Complete Demonstration")
    print("=" * 60)
    
    try:
        await demonstrate_basic_budget_protection()
        await demonstrate_rate_limiting()
        await demonstrate_cost_calculation()
        await demonstrate_user_budgets()
        await demonstrate_provider_budgets()
        await demonstrate_real_world_scenario()
        await demonstrate_cost_tracking()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✓ Token bucket algorithm for rate limiting")
        print("✓ Redis-based distributed token management")
        print("✓ Cost calculation with provider-specific weights")
        print("✓ Budget enforcement with hard and soft limits")
        print("✓ User-specific budget management")
        print("✓ Provider-specific budget management")
        print("✓ Real-time spending tracking")
        print("✓ BudgetExceededException for exceeded limits")
        print("✓ Comprehensive cost breakdown and reporting")
        print("✓ Volume-based cost calculation")
        print("✓ Budget reset and management")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
