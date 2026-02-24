"""
MAIFA v3 Data Ingestion Interfaces
Common interfaces for all data sources
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio

class DataFetcher(ABC):
    """Interface for fetching data from external sources"""
    
    @abstractmethod
    async def fetch(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch raw data from source"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if source is accessible"""
        pass

class DataParser(ABC):
    """Interface for parsing raw data"""
    
    @abstractmethod
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw data into structured format"""
        pass

class DataValidator(ABC):
    """Interface for validating parsed data"""
    
    @abstractmethod
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed data"""
        pass

class DataNormalizer(ABC):
    """Interface for normalizing validated data"""
    
    @abstractmethod
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize data to standard format"""
        pass
