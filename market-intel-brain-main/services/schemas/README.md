# Strict Validation Layer - Pydantic V2

A comprehensive validation layer using Pydantic V2 with strict type enforcement and Decimal precision for financial data. This layer implements non-negotiable data contracts that reject invalid data at the boundary.

## 🚀 **Core Features**

### **Strict Type Validation**
- `model_config = ConfigDict(strict=True)` - Rejects wrong data types
- No automatic type coercion - data must match exactly
- String-only input for financial fields to prevent float precision loss

### **Decimal Precision**
- All financial fields use `decimal.Decimal` exclusively
- Float conversion is explicitly blocked
- String input required: `"123.45"` → `Decimal("123.45")`
- Preserves monetary precision throughout the system

### **Business Logic Validation**
- `@model_validator(mode='after')` for complex validation
- Price relationships (high ≥ low, etc.)
- Volume positivity checks
- Timestamp ordering validation
- Currency consistency enforcement

## 📁 **Structure**

```
schemas/
├── __init__.py              # Main exports
├── financial.py             # Financial types (Price, Volume, etc.)
├── market_data.py           # Market data models (UnifiedMarketData, OHLCV)
├── validators.py            # Custom validation functions
├── example_usage.py         # Comprehensive examples
├── requirements.txt         # Dependencies
└── README.md               # This file
```

## 🔧 **Installation**

```bash
pip install -r requirements.txt
```

## 💡 **Quick Start**

### **Basic Usage**

```python
from services.schemas import Price, UnifiedMarketData, MarketDataSymbol, DataSource

# ✅ CORRECT: String input for financial fields
price = Price(value="123.45", currency="USD")

# ❌ WRONG: Float input (will raise ValidationError)
price = Price(value=123.45, currency="USD")  # Raises error!

# Create market data
market_data = UnifiedMarketData(
    symbol="AAPL",
    asset_type=MarketDataSymbol.STOCK,
    exchange="NASDAQ",
    current_price=price,
    source=DataSource.YAHOO_FINANCE,
    timestamp=datetime.now()
)
```

### **OHLCV Data**

```python
from services.schemas import create_ohlcv, TimeFrame

# ✅ Factory function with string inputs
ohlcv = create_ohlcv(
    open_str="100.00",
    high_str="105.00",
    low_str="98.50",
    close_str="103.25",
    volume_str="1000000",
    currency="USD",
    timestamp=datetime.now()
)

# ✅ Automatic validation of price relationships
# High must be ≥ all other prices
# Low must be ≤ all other prices
# All prices must have same currency
```

### **Financial Types**

```python
from services.schemas import Price, Volume, Percentage, MonetaryAmount

# Price with currency
price = Price(value="150.25", currency="USD")

# Volume with units
volume = Volume(value="1000.5", unit="shares")

# Percentage (as decimal: 0.05 = 5%)
percentage = Percentage(value="0.05")
print(f"Percentage: {percentage}")  # "5.00%"

# Monetary amount
amount = MonetaryAmount(amount="1234.56", currency="EUR")
```

## 🛡️ **Strict Validation Examples**

### **Type Safety**

```python
# ❌ These will ALL raise ValidationError:

# Float not allowed
Price(value=123.45, currency="USD")

# Invalid currency format
Price(value="123.45", currency="usd")  # Must be uppercase

# Negative price
Price(value="-123.45", currency="USD")

# Empty symbol
UnifiedMarketData(symbol="", asset_type=MarketDataSymbol.STOCK, ...)

# Invalid OHLCV relationships
create_ohlcv(
    open_str="100.00",
    high_str="95.00",  # High < Low - invalid!
    low_str="98.50",
    close_str="103.25",
    ...
)
```

### **Business Logic Validation**

```python
# Order book spread validation
order_book = OrderBook(
    symbol="BTCUSD",
    bids=[OrderBookLevel(price=Price(value="50002", currency="USD"), ...)],
    asks=[OrderBookLevel(price=Price(value="50001", currency="USD"), ...)]
)
# ❌ Raises error: Best bid (50002) >= best ask (50001)

# Timestamp validation
market_data = UnifiedMarketData(
    symbol="AAPL",
    timestamp=datetime.now() + timedelta(hours=1),  # Future timestamp!
    ...
)
# ❌ Raises error: Timestamp cannot be in the future
```

## 🔍 **Decimal Precision**

### **The Float Problem**

```python
# Float precision loss
result = 0.1 + 0.2
print(result)  # 0.30000000000000004
print(result == 0.3)  # False

# Decimal precision preservation
from decimal import Decimal
result = Decimal("0.1") + Decimal("0.2")
print(result)  # 0.3
print(result == Decimal("0.3"))  # True
```

### **Financial Calculations**

```python
# Using our strict types
price1 = Price(value="99.99", currency="USD")
price2 = Price(value="0.01", currency="USD")

total = price1.value + price2.value
print(total)  # Decimal('100.00')
print(total == Decimal("100.00"))  # True
```

## 📊 **Available Models**

### **Market Data Models**

- **`UnifiedMarketData`** - Main market data contract
- **`OHLCV`** - Open, High, Low, Close, Volume data
- **`MarketTicker`** - Real-time ticker information
- **`OrderBook`** - Order book with bids/asks
- **`Trade`** - Individual trade information

### **Financial Types**

- **`Price`** - Price with currency
- **`Volume`** - Volume with units
- **`Percentage`** - Percentage values
- **`MonetaryAmount`** - General monetary amounts

### **Enums**

- **`MarketDataSymbol`** - Asset types (stock, crypto, forex, etc.)
- **`DataSource`** - Data source identifiers
- **`TimeFrame`** - Time intervals (1m, 5m, 1h, 1d, etc.)

## 🛠️ **Custom Validators**

```python
from services.schemas.validators import (
    validate_price_range,
    validate_volume_positive,
    validate_timestamp_order
)

# Validate price relationships
validate_price_range(Decimal("105.00"), Decimal("100.00"))  # ✅ Pass
validate_price_range(Decimal("95.00"), Decimal("100.00"))   # ❌ Error

# Validate volume
validate_volume_positive(Decimal("1000"))   # ✅ Pass
validate_volume_positive(Decimal("-100"))    # ❌ Error

# Validate timestamp order
start = datetime.now() - timedelta(hours=1)
end = datetime.now()
validate_timestamp_order(start, end)         # ✅ Pass
validate_timestamp_order(end, start)         # ❌ Error
```

## 🏭 **Factory Functions**

```python
from services.schemas import (
    create_market_data,
    create_ohlcv,
    create_price,
    create_volume
)

# Easy creation with string inputs
market_data = create_market_data(
    symbol="AAPL",
    asset_type=MarketDataSymbol.STOCK,
    exchange="NASDAQ",
    price_str="150.25",
    currency="USD",
    source=DataSource.YAHOO_FINANCE,
    timestamp=datetime.now()
)

price = create_price("123.45", "USD")
volume = create_volume("1000.5", "shares")
```

## 🧪 **Testing**

Run the example demonstration:

```bash
python example_usage.py
```

Run tests:

```bash
pytest -v
```

## 📈 **Performance Considerations**

### **Decimal Performance**
- Decimal is slower than float but provides exact precision
- Use Decimal for all financial calculations
- Cache Decimal values when possible
- Consider `cachetools` for frequently used values

### **Validation Overhead**
- Pydantic V2 validation is fast but adds overhead
- Validation happens at input boundaries
- Internal processing can use validated objects directly
- Consider caching validation results for repeated data

## 🔧 **Configuration**

### **Custom Validation Rules**

```python
from pydantic import field_validator, model_validator

class CustomModel(BaseModel):
    model_config = ConfigDict(strict=True)
    
    price: Price
    
    @field_validator('price')
    @classmethod
    def validate_price_range(cls, v: Price) -> Price:
        if v.value < Decimal('1.00'):
            raise ValueError("Price must be at least $1.00")
        return v
    
    @model_validator(mode='after')
    def validate_business_logic(self) -> 'CustomModel':
        # Custom business logic here
        return self
```

### **Error Handling**

```python
from pydantic import ValidationError

try:
    price = Price(value="123.45", currency="USD")
except ValidationError as e:
    print(f"Validation failed: {e}")
    # Handle validation error appropriately
```

## 🎯 **Best Practices**

### **1. Always Use String Input**
```python
# ✅ CORRECT
Price(value="123.45", currency="USD")

# ❌ WRONG
Price(value=123.45, currency="USD")
```

### **2. Validate at Boundaries**
```python
# Validate external data immediately
def process_api_response(api_data):
    try:
        market_data = UnifiedMarketData(**api_data)
        # Process validated data
    except ValidationError as e:
        # Handle invalid data
        raise
```

### **3. Use Factory Functions**
```python
# ✅ Easier and safer
price = create_price("123.45", "USD")

# ❌ More verbose
price = Price(value="123.45", currency="USD")
```

### **4. Handle Validation Errors Gracefully**
```python
def safe_create_price(value_str, currency):
    try:
        return Price(value=value_str, currency=currency)
    except ValidationError as e:
        logger.error(f"Invalid price data: {e}")
        return None
```

## 🚨 **Important Notes**

### **Float Conversion is BLOCKED**
```python
# This will ALWAYS raise an error
Price(value=123.45, currency="USD")

# Use string instead
Price(value="123.45", currency="USD")
```

### **Strict Mode is ENABLED**
```python
# No automatic type coercion
model_config = ConfigDict(strict=True)

# This will fail:
UnifiedMarketData(symbol=123, ...)  # Integer instead of string
```

### **Business Logic is ENFORCED**
```python
# OHLCV relationships are validated
# Order book spreads are validated
# Timestamps are validated
# Currency consistency is validated
```

## 📚 **Dependencies**

- **pydantic>=2.0.0** - Core validation framework
- **decimal** - Python standard library (built-in)

## 🤝 **Contributing**

When adding new models:

1. Always use `model_config = ConfigDict(strict=True)`
2. Use Decimal for all financial fields
3. Implement proper business logic validation
4. Add comprehensive examples
5. Update documentation

## 📄 **License**

This validation layer is part of the Market Intel Brain project.
