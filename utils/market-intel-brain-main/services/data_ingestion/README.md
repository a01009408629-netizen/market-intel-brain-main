# MAIFA v3 Data Ingestion Architecture

## Overview
Modular data ingestion system supporting 13 news & financial data sources with unified interfaces and parallel processing.

## Architecture

### Core Components
- **Interfaces**: Common interfaces for all sources (DataFetcher, DataParser, DataValidator, DataNormalizer)
- **Registry**: Central registry for source management and discovery
- **Orchestrator**: Master orchestrator for parallel ingestion with retry logic

### Data Sources
1. **YahooFinance** - Yahoo Finance API (no API key required)
2. **AlphaVantage** - Alpha Vantage API (API key required)
3. **NewsCatcherAPI** - News Catcher API (API key required)
4. **GoogleNewsScraper** - Google News scraper (no API key required)
5. **EconDB** - Economic database API (API key required)
6. **TradingEconomics** - Trading Economics API (API key required)
7. **MarketStack** - Market Stack API (API key required)
8. **FinMind** - FinMind API (API key required)
9. **TwelveData** - Twelve Data API (API key required)
10. **Finnhub** - Finnhub API (API key required)
11. **FinancialModelingPrep** - Financial Modeling Prep API (API key required)
12. **EuroStatFeeds** - EuroStat API (no API key required)
13. **IMFJsonFeeds** - IMF JSON Feeds API (no API key required)

## Data Flow
```
Input → Fetch → Parse → Validate → Normalize → Output
```

### Pipeline Stages
1. **Fetch**: Retrieve raw data from external API/scraper
2. **Parse**: Convert raw data to structured format
3. **Validate**: Ensure data integrity and required fields
4. **Normalize**: Convert to standardized MAIFA format

## Usage

### Initialize System
```python
from services.data_ingestion import register_all_sources, get_orchestrator

# Register all sources
await register_all_sources()

# Get orchestrator
orchestrator = get_orchestrator()
```

### Ingest Data
```python
# Ingest from all enabled sources
params = {
    "symbol": "AAPL",
    "query": "business",
    "language": "en"
}

results = await orchestrator.ingest_all_sources(params)
```

### Source Management
```python
from services.data_ingestion import get_registry

registry = get_registry()

# List all sources
sources = await registry.list_sources()

# Get source info
info = await registry.get_source_info("YahooFinance")

# Enable/disable sources
await registry.enable_source("AlphaVantage")
await registry.disable_source("NewsCatcherAPI")
```

## Configuration

### API Keys
Each source that requires an API key uses a placeholder that can be replaced:
- `YOUR_ALPHA_VANTAGE_API_KEY`
- `YOUR_NEWSCATCHER_API_KEY`
- `YOUR_ECONDB_API_KEY`
- etc.

### Rate Limits
Each source has configured rate limits:
- Yahoo Finance: 100 req/min
- Alpha Vantage: 5 req/min (free tier)
- News Catcher API: 100 req/min
- etc.

## Testing

Run the test suite:
```bash
python services/data_ingestion/test_data_ingestion.py
```

## Adding New Sources

1. Create new directory in `sources/`
2. Implement the 4 required components:
   - `fetcher.py` - DataFetcher implementation
   - `parser.py` - DataParser implementation
   - `validator.py` - DataValidator implementation
   - `normalizer.py` - DataNormalizer implementation
3. Create `__init__.py` with registration function
4. Add import to `sources/__init__.py`

## Error Handling

- **Retry Logic**: 3 attempts with exponential backoff
- **Timeout Protection**: 30-second timeout per source
- **Graceful Degradation**: Continue if individual sources fail
- **Comprehensive Logging**: All errors logged with context

## Performance

- **Parallel Processing**: All sources executed concurrently
- **Async/Await**: Non-blocking I/O throughout
- **Resource Pooling**: Efficient HTTP connection management
- **Circuit Breaker Ready**: Prepared for circuit breaker integration

## Future Enhancements

- API key management system
- Data caching and deduplication
- Real-time streaming support
- Circuit breaker integration
- Advanced monitoring and metrics
