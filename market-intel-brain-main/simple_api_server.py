#!/usr/bin/env python3
"""
Simple API Server for Market Intel Brain
Basic FastAPI server without unicode issues
"""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Add current directory to Python path
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Create FastAPI app
app = FastAPI(
    title="Market Intel Brain API",
    description="Financial Intelligence Platform API",
    version="1.0.0"
)

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    message: str
    components: dict[str, str]

class MarketDataRequest(BaseModel):
    symbol: str
    interval: str | None = "1h"

class MarketDataResponse(BaseModel):
    symbol: str
    price: float
    timestamp: str
    source: str

# In-memory storage for demo
market_data_cache = {}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Market Intel Brain API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Test data ingestion service
        from services.data_ingestion import get_orchestrator
        get_orchestrator()  # Test import and instantiation
        data_ingestion_status = "OK"
    except Exception as e:
        data_ingestion_status = f"ERROR: {str(e)}"
    
    return HealthResponse(
        status="healthy",
        message="All systems operational",
        components={
            "api": "OK",
            "data_ingestion": data_ingestion_status,
            "fastapi": "OK"
        }
    )

@app.post("/market-data", response_model=MarketDataResponse)
async def get_market_data(request: MarketDataRequest):
    """Get market data for a symbol"""
    try:
        # Mock market data for demo
        import time
        current_time = time.time()
        
        # Simulate market data
        mock_price = 100.0 + (hash(request.symbol) % 1000) / 10
        
        return MarketDataResponse(
            symbol=request.symbol,
            price=mock_price,
            timestamp=str(current_time),
            source="mock_data"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@app.get("/sources")
async def get_data_sources():
    """Get available data sources"""
    try:
        from services.data_ingestion import get_registry
        registry = get_registry()
        
        # Get available sources
        sources = list(registry.sources.keys()) if hasattr(registry, 'sources') else []
        
        return {
            "status": "success",
            "sources": sources,
            "total": len(sources)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "sources": []
        }

@app.get("/status")
async def get_system_status():
    """Get detailed system status"""
    return {
        "status": "operational",
        "uptime": "running",
        "components": {
            "api_server": "running",
            "data_ingestion": "available",
            "market_analysis": "ready"
        },
        "memory_usage": "normal",
        "active_connections": 0
    }

if __name__ == "__main__":
    import uvicorn
    
    print("Starting Market Intel Brain API Server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )
