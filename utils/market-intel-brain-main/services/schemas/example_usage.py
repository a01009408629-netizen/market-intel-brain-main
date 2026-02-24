"""
Strict Validation Layer - Example Usage

This file demonstrates how to use the strict validation schemas with Pydantic V2,
showing the enforcement of Decimal usage and strict type validation.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from .market_data import (
    UnifiedMarketData,
    OHLCV,
    MarketTicker,
    OrderBook,
    OrderBookLevel,
    MarketDataSymbol,
    DataSource,
    TimeFrame,
    create_market_data,
    create_ohlcv
)
from .financial import (
    Price,
    Volume,
    Percentage,
    MonetaryAmount,
    create_price,
    create_volume,
    create_percentage
)
from .validators import (
    validate_price_range,
    validate_volume_positive,
    validate_timestamp_order
)


def demonstrate_strict_validation():
    """Demonstrate strict validation behavior."""
    print("=== Strict Validation Demonstration ===\n")
    
    # ✅ VALID: Creating Price with string input
    print("1. Creating Price with string input (VALID):")
    try:
        price = Price(value="123.45", currency="USD")
        print(f"   ✓ Price created: {price}")
        print(f"   ✓ Type: {type(price.value)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ❌ INVALID: Creating Price with float input (should fail)
    print("\n2. Creating Price with float input (INVALID - should fail):")
    try:
        price = Price(value=123.45, currency="USD")  # Float not allowed
        print(f"   ✗ Unexpected success: {price}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")
    
    # ❌ INVALID: Creating Price with invalid currency
    print("\n3. Creating Price with invalid currency (INVALID - should fail):")
    try:
        price = Price(value="123.45", currency="usd")  # Lowercase not allowed
        print(f"   ✗ Unexpected success: {price}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")
    
    # ❌ INVALID: Creating Price with negative value
    print("\n4. Creating Price with negative value (INVALID - should fail):")
    try:
        price = Price(value="-123.45", currency="USD")
        print(f"   ✗ Unexpected success: {price}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")


def demonstrate_ohlcv_validation():
    """Demonstrate OHLCV validation with business logic."""
    print("\n=== OHLCV Validation Demonstration ===\n")
    
    # ✅ VALID: Proper OHLCV data
    print("1. Creating valid OHLCV data:")
    try:
        ohlcv = create_ohlcv(
            open_str="100.00",
            high_str="105.00", 
            low_str="98.50",
            close_str="103.25",
            volume_str="1000000",
            currency="USD",
            timestamp=datetime.now()
        )
        print(f"   ✓ OHLCV created successfully")
        print(f"   ✓ Open: {ohlcv.open.value}, High: {ohlcv.high.value}")
        print(f"   ✓ Low: {ohlcv.low.value}, Close: {ohlcv.close.value}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ❌ INVALID: High price lower than low price
    print("\n2. OHLCV with invalid price relationships (INVALID - should fail):")
    try:
        ohlcv = create_ohlcv(
            open_str="100.00",
            high_str="95.00",  # High < Low - invalid
            low_str="98.50",
            close_str="103.25",
            volume_str="1000000",
            currency="USD",
            timestamp=datetime.now()
        )
        print(f"   ✗ Unexpected success: {ohlcv}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")
    
    # ❌ INVALID: Different currencies in OHLCV
    print("\n3. OHLCV with mixed currencies (INVALID - should fail):")
    try:
        from .market_data import OHLCV, Price, Volume
        
        ohlcv = OHLCV(
            open=Price(value="100.00", currency="USD"),
            high=Price(value="105.00", currency="EUR"),  # Different currency
            low=Price(value="98.50", currency="USD"),
            close=Price(value="103.25", currency="USD"),
            volume=Volume(value="1000000"),
            timestamp=datetime.now()
        )
        print(f"   ✗ Unexpected success: {ohlcv}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")


def demonstrate_unified_market_data():
    """Demonstrate UnifiedMarketData with comprehensive validation."""
    print("\n=== UnifiedMarketData Demonstration ===\n")
    
    # ✅ VALID: Complete market data
    print("1. Creating valid UnifiedMarketData:")
    try:
        market_data = create_market_data(
            symbol="AAPL",
            asset_type=MarketDataSymbol.STOCK,
            exchange="NASDAQ",
            price_str="150.25",
            currency="USD",
            source=DataSource.YAHOO_FINANCE,
            timestamp=datetime.now()
        )
        print(f"   ✓ Market data created: {market_data.symbol}")
        print(f"   ✓ Price: {market_data.get_price()}")
        print(f"   ✓ Real-time: {market_data.is_real_time()}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ✅ VALID: Market data with OHLCV
    print("\n2. Creating market data with OHLCV:")
    try:
        ohlcv = create_ohlcv(
            open_str="149.00",
            high_str="151.00",
            low_str="148.50", 
            close_str="150.25",
            volume_str="50000000",
            currency="USD",
            timestamp=datetime.now()
        )
        
        market_data = UnifiedMarketData(
            symbol="AAPL",
            asset_type=MarketDataSymbol.STOCK,
            exchange="NASDAQ",
            price_data=ohlcv,
            timeframe=TimeFrame.DAY_1,
            source=DataSource.YAHOO_FINANCE,
            timestamp=datetime.now()
        )
        print(f"   ✓ Market data with OHLCV created")
        print(f"   ✓ Close price: {market_data.get_price()}")
        print(f"   ✓ Volume: {market_data.get_volume()}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ❌ INVALID: Symbol with invalid characters
    print("\n3. Market data with invalid symbol (INVALID - should fail):")
    try:
        market_data = UnifiedMarketData(
            symbol="AAPL@#$",  # Invalid characters
            asset_type=MarketDataSymbol.STOCK,
            exchange="NASDAQ",
            current_price=Price(value="150.25", currency="USD"),
            source=DataSource.YAHOO_FINANCE,
            timestamp=datetime.now()
        )
        print(f"   ✗ Unexpected success: {market_data}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")


def demonstrate_order_book_validation():
    """Demonstrate order book validation."""
    print("\n=== OrderBook Validation Demonstration ===\n")
    
    # ✅ VALID: Proper order book
    print("1. Creating valid OrderBook:")
    try:
        order_book = OrderBook(
            symbol="BTCUSD",
            exchange="Binance",
            timestamp=datetime.now(),
            bids=[
                OrderBookLevel(
                    price=Price(value="50000.00", currency="USD"),
                    volume=Volume(value="1.5")
                ),
                OrderBookLevel(
                    price=Price(value="49999.50", currency="USD"),
                    volume=Volume(value="2.0")
                )
            ],
            asks=[
                OrderBookLevel(
                    price=Price(value="50001.00", currency="USD"),
                    volume=Volume(value="1.2")
                ),
                OrderBookLevel(
                    price=Price(value="50001.50", currency="USD"),
                    volume=Volume(value="1.8")
                )
            ]
        )
        print(f"   ✓ Order book created: {order_book.symbol}")
        print(f"   ✓ Best bid: {order_book.bids[0].price.value}")
        print(f"   ✓ Best ask: {order_book.asks[0].price.value}")
        print(f"   ✓ Spread: {order_book.asks[0].price.value - order_book.bids[0].price.value}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ❌ INVALID: Best bid >= best ask
    print("\n2. Order book with invalid spread (INVALID - should fail):")
    try:
        order_book = OrderBook(
            symbol="BTCUSD",
            exchange="Binance",
            timestamp=datetime.now(),
            bids=[
                OrderBookLevel(
                    price=Price(value="50002.00", currency="USD"),  # Higher than ask
                    volume=Volume(value="1.5")
                )
            ],
            asks=[
                OrderBookLevel(
                    price=Price(value="50001.00", currency="USD"),
                    volume=Volume(value="1.2")
                )
            ]
        )
        print(f"   ✗ Unexpected success: {order_book}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")


def demonstrate_financial_types():
    """Demonstrate financial type validation."""
    print("\n=== Financial Types Demonstration ===\n")
    
    # ✅ VALID: Creating various financial types
    print("1. Creating financial types with string input:")
    try:
        # Monetary amount
        amount = MonetaryAmount(amount="1234.56", currency="USD")
        print(f"   ✓ Monetary amount: {amount}")
        
        # Volume
        volume = Volume(value="1000.5", unit="shares")
        print(f"   ✓ Volume: {volume}")
        
        # Percentage
        percentage = Percentage(value="0.05")  # 5%
        print(f"   ✓ Percentage: {percentage}")
        print(f"   ✓ As decimal: {percentage.as_decimal()}")
        print(f"   ✓ As percentage: {percentage.as_percentage()}%")
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ❌ INVALID: Percentage out of range
    print("\n2. Percentage out of range (INVALID - should fail):")
    try:
        percentage = Percentage(value="1.5")  # 150% - out of range
        print(f"   ✗ Unexpected success: {percentage}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")
    
    # ❌ INVALID: Negative volume
    print("\n3. Negative volume (INVALID - should fail):")
    try:
        volume = Volume(value="-100")  # Negative volume
        print(f"   ✗ Unexpected success: {volume}")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")


def demonstrate_custom_validators():
    """Demonstrate custom validator functions."""
    print("\n=== Custom Validators Demonstration ===\n")
    
    # ✅ VALID: Price range validation
    print("1. Valid price range:")
    try:
        validate_price_range(Decimal("105.00"), Decimal("100.00"))
        print("   ✓ Price range validation passed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ❌ INVALID: Invalid price range
    print("\n2. Invalid price range (high < low):")
    try:
        validate_price_range(Decimal("95.00"), Decimal("100.00"))
        print("   ✗ Unexpected success")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")
    
    # ✅ VALID: Volume validation
    print("\n3. Valid volume:")
    try:
        validate_volume_positive(Decimal("1000.00"))
        print("   ✓ Volume validation passed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ❌ INVALID: Negative volume
    print("\n4. Negative volume:")
    try:
        validate_volume_positive(Decimal("-100.00"))
        print("   ✗ Unexpected success")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")
    
    # ✅ VALID: Timestamp order
    print("\n5. Valid timestamp order:")
    try:
        start = datetime.now() - timedelta(hours=1)
        end = datetime.now()
        validate_timestamp_order(start, end)
        print("   ✓ Timestamp order validation passed")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # ❌ INVALID: Reversed timestamp order
    print("\n6. Invalid timestamp order:")
    try:
        start = datetime.now()
        end = datetime.now() - timedelta(hours=1)
        validate_timestamp_order(start, end)
        print("   ✗ Unexpected success")
    except Exception as e:
        print(f"   ✓ Expected error: {e}")


def demonstrate_decimal_precision():
    """Demonstrate Decimal precision preservation."""
    print("\n=== Decimal Precision Demonstration ===\n")
    
    # Show the difference between float and Decimal
    print("1. Float vs Decimal precision:")
    
    # Float precision loss
    float_value = 0.1 + 0.2
    print(f"   Float (0.1 + 0.2): {float_value}")
    print(f"   Float precision issue: {float_value != 0.3}")
    
    # Decimal precision preservation
    decimal_value = Decimal("0.1") + Decimal("0.2")
    print(f"   Decimal ('0.1' + '0.2'): {decimal_value}")
    print(f"   Decimal precision: {decimal_value == Decimal('0.3')}")
    
    # Financial calculations
    print("\n2. Financial calculations:")
    
    # Using our strict Price type
    price1 = Price(value="99.99", currency="USD")
    price2 = Price(value="0.01", currency="USD")
    
    total = price1.value + price2.value
    print(f"   Price 1: {price1.value}")
    print(f"   Price 2: {price2.value}")
    print(f"   Total: {total}")
    print(f"   Exact: {total == Decimal('100.00')}")


def main():
    """Run all demonstrations."""
    print("Strict Validation Layer - Pydantic V2 Demonstration")
    print("=" * 60)
    
    try:
        demonstrate_strict_validation()
        demonstrate_ohlcv_validation()
        demonstrate_unified_market_data()
        demonstrate_order_book_validation()
        demonstrate_financial_types()
        demonstrate_custom_validators()
        demonstrate_decimal_precision()
        
        print("\n" + "=" * 60)
        print("All demonstrations completed successfully!")
        print("\nKey Takeaways:")
        print("✓ All financial fields must use string input (no float conversion)")
        print("✓ Decimal precision is preserved throughout the system")
        print("✓ Strict validation prevents invalid data")
        print("✓ Business logic is enforced at the schema level")
        print("✓ Data contracts are non-negotiable")
        
    except Exception as e:
        print(f"\nDemonstration failed: {e}")
        raise


if __name__ == "__main__":
    main()
