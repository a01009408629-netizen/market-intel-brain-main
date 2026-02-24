"""
MAIFA v3 Data Source Registry
Central registry for all data sources
"""

from typing import Dict, List, Any, Optional, Type
import asyncio
import logging

from .interfaces import DataFetcher, DataParser, DataValidator, DataNormalizer

class SourceRegistry:
    """Central registry for data sources with their components"""
    
    def __init__(self):
        self.logger = logging.getLogger("SourceRegistry")
        self._sources: Dict[str, Dict[str, Any]] = {}
        self._registry_lock = asyncio.Lock()
        
    async def register_source(self, 
                          source_name: str,
                          fetcher: DataFetcher,
                          parser: DataParser,
                          validator: DataValidator,
                          normalizer: DataNormalizer,
                          config: Optional[Dict[str, Any]] = None) -> bool:
        """Register a complete data source"""
        async with self._registry_lock:
            try:
                self._sources[source_name] = {
                    "fetcher": fetcher,
                    "parser": parser,
                    "validator": validator,
                    "normalizer": normalizer,
                    "config": config or {},
                    "registered_at": datetime.now(),
                    "enabled": True
                }
                
                self.logger.info(f"Data source registered: {source_name}")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to register source {source_name}: {e}")
                return False
    
    async def get_source(self, source_name: str) -> Optional[Dict[str, Any]]:
        """Get source components by name"""
        return self._sources.get(source_name)
    
    async def list_sources(self) -> List[str]:
        """List all registered source names"""
        return list(self._sources.keys())
    
    async def get_enabled_sources(self) -> List[str]:
        """List only enabled sources"""
        return [
            name for name, config in self._sources.items()
            if config.get("enabled", True)
        ]
    
    async def enable_source(self, source_name: str) -> bool:
        """Enable a data source"""
        if source_name in self._sources:
            self._sources[source_name]["enabled"] = True
            self.logger.info(f"Source enabled: {source_name}")
            return True
        return False
    
    async def disable_source(self, source_name: str) -> bool:
        """Disable a data source"""
        if source_name in self._sources:
            self._sources[source_name]["enabled"] = False
            self.logger.info(f"Source disabled: {source_name}")
            return True
        return False
    
    async def get_source_info(self, source_name: str) -> Dict[str, Any]:
        """Get detailed source information"""
        source = self._sources.get(source_name)
        if not source:
            return {"error": f"Source {source_name} not found"}
        
        return {
            "name": source_name,
            "enabled": source.get("enabled", True),
            "registered_at": source.get("registered_at"),
            "config": source.get("config", {}),
            "components": {
                "fetcher": source["fetcher"].__class__.__name__,
                "parser": source["parser"].__class__.__name__,
                "validator": source["validator"].__class__.__name__,
                "normalizer": source["normalizer"].__class__.__name__
            }
        }
    
    async def get_registry_info(self) -> Dict[str, Any]:
        """Get comprehensive registry information"""
        return {
            "total_sources": len(self._sources),
            "enabled_sources": len(await self.get_enabled_sources()),
            "sources": {
                name: await self.get_source_info(name)
                for name in self._sources.keys()
            }
        }
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all source configurations (sync version for orchestrator)"""
        return {
            name: source.get("config", {})
            for name, source in self._sources.items()
        }
    
    def get_all_instances(self) -> Dict[str, Any]:
        """Get all source instances (sync version for orchestrator)"""
        return {
            name: {
                "fetcher": source["fetcher"],
                "parser": source["parser"],
                "validator": source["validator"],
                "normalizer": source["normalizer"]
            }
            for name, source in self._sources.items()
        }

# Global registry instance
source_registry = SourceRegistry()
