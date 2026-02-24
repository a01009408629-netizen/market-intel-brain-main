# MAIFA Source Adapter - System Constitution

## 🎯 Project Vision
A high-performance, resilient, and stealthy middleware for financial data ingestion.

## 🛠 Technical Stack (Mandatory)
- **Language:** Python 3.11+ (Strict Asyncio)
- **Validation:** Pydantic V2 (Strict Mode)
- **Numbers:** Always use `decimal.Decimal` for financial data (No Floats).
- **Communication:** `httpx` or `curl_cffi` for TLS Fingerprinting.
- **Serialization:** MessagePack (`msgpack`) for all internal caching/transport.
- **Persistence:** Redis (Async) for L2 Cache and Rate Limiting.

## 🏗 Directory Structure
/maifa_adapter
├── core/               # Base classes, standardized exceptions
├── adapters/           # Source implementations (e.g., binance_adapter.py)
├── schemas/            # Unified Pydantic models (Decimal-based)
├── resilience/         # Circuit Breaker, Rate Limiter, Retry Jitter
├── identity/           # Proxy rotation & TLS Fingerprints
├── cache/              # SWR logic & Tiered Caching (L1/L2)
├── dqs/                # Data Quality (Z-Score Anomaly Detection)
├── orchestrator/       # Dynamic Adapter Loading & Registry
├── locks/              # Distributed Redlock Manager
├── telemetry/          # OpenTelemetry & Prometheus Metrics
├── security/           # SecretStr management (Zero-Trust)
└── utils/              # MsgPack serialization hooks

## 📏 Core Engineering Rules
1. **Zero Blocking:** Any sync code must be run in a threadpool or avoided.
2. **Standardized Errors:** Use `TransientAdapterError` for retriable issues and `FatalAdapterError` for permanent failures.
3. **Immutability:** Data schemas should be immutable once validated.
4. **Clean Code:** Follow SOLID principles and use Type Hints for EVERYTHING.
5. **Financial Precision:** All monetary values must use `decimal.Decimal` with proper quantization.
6. **Async-First:** All public methods must be async and non-blocking.
7. **Zero-Trust Security:** All secrets must be encrypted at rest and in transit.
8. **Observability:** Every operation must emit structured logs and metrics.
9. **Resilience First:** All external calls must pass through circuit breaker and retry logic.
10. **Cache-Aware:** All operations must respect SWR patterns and cache hierarchies.
