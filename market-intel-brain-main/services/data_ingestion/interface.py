"""
MAIFA Data Ingestion - Unified Interface
Simple interface for using the complete data ingestion system
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .orchestrator import orchestrator

class DataIngestionInterface:
    """Simple unified interface for MAIFA data ingestion"""
    
    def __init__(self):
        self.logger = logging.getLogger("DataIngestionInterface")
        self.orchestrator = orchestrator
        
    async def initialize(self) -> bool:
        """Initialize the data ingestion system"""
        try:
            success = await self.orchestrator.load_sources()
            if success:
                self.logger.info("MAIFA Data Ingestion initialized successfully")
            else:
                self.logger.error("Failed to initialize MAIFA Data Ingestion")
            return success
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            return False
    
    async def get_market_data(self, symbols: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Get complete market data from all sources
        Returns: {source_name: normalized_data}
        """
        try:
            # Step 1: Fetch raw data
            raw_data = await self.orchestrator.fetch_all(symbols, **kwargs)
            
            # Step 2: Validate data
            validated_data = await self.orchestrator.validate_all(raw_data)
            
            # Step 3: Normalize data
            normalized_data = await self.orchestrator.normalize_all(validated_data)
            
            return {
                "status": "success",
                "sources": normalized_data,
                "total_sources": len(normalized_data),
                "timestamp": datetime.now().isoformat(),
                "raw_data": raw_data,
                "validation_results": validated_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get market data: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def get_source_health(self) -> Dict[str, Any]:
        """Get health status of all sources"""
        return await self.orchestrator.health_check()
    
    async def get_available_sources(self) -> List[str]:
        """Get list of available data sources"""
        status = await self.orchestrator.get_source_status()
        return status.get("source_list", [])

# Global interface instance
data_interface = DataIngestionInterface()
