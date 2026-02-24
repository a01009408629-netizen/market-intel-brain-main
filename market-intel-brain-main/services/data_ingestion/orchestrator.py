"""
MAIFA v3 Data Ingestion Orchestrator
Unified orchestration layer for all 13 data sources
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import traceback

from .registry import source_registry
from .interfaces import DataFetcher, DataParser, DataValidator, DataNormalizer
from .errors import MAIFAError, FetchError, ValidationError, NormalizationError

class DataIngestionOrchestrator:
    """Unified orchestrator for all MAIFA data sources"""
    
    def __init__(self):
        self.logger = logging.getLogger("DataIngestionOrchestrator")
        self.sources_loaded = False
        self.source_configs = {}
        self.source_instances = {}
        self.raw_data_cache = {}
        
    async def load_sources(self) -> bool:
        """
        Load all 13 data sources by calling their register() functions
        Returns True if all sources loaded successfully
        """
        try:
            self.logger.info("Loading MAIFA data sources...")
            
            # List of all 13 sources
            sources = [
                "YahooFinance",
                "AlphaVantage", 
                "NewsCatcherAPI",
                "GoogleNewsScraper",
                "EconDB",
                "TradingEconomics",
                "MarketStack",
                "FinMind",
                "TwelveData",
                "Finnhub",
                "FinancialModelingPrep",
                "EuroStatFeeds",
                "IMFJsonFeeds"
            ]
            
            # Load all sources in parallel
            load_tasks = []
            for source_name in sources:
                try:
                    # Import and register each source
                    module_path = f"services.data_ingestion.sources.{source_name}"
                    module = __import__(module_path, fromlist=[source_name])
                    
                    if hasattr(module, 'register'):
                        load_tasks.append(module.register())
                        self.logger.debug(f"Queued registration for {source_name}")
                    else:
                        self.logger.error(f"Source {source_name} missing register() function")
                        
                except Exception as e:
                    self.logger.error(f"Failed to import {source_name}: {e}")
                    traceback.print_exc()
            
            # Execute all registrations in parallel
            if load_tasks:
                results = await asyncio.gather(*load_tasks, return_exceptions=True)
                
                # Check results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Registration failed: {result}")
                    else:
                        self.logger.debug(f"Registration successful: {result}")
            
            # Get loaded sources from registry
            self.source_configs = source_registry.get_all_configs()
            self.source_instances = source_registry.get_all_instances()
            self.sources_loaded = True
            
            self.logger.info(f"Loaded {len(self.source_configs)} data sources")
            return len(self.source_configs) == 13
            
        except Exception as e:
            self.logger.error(f"Failed to load sources: {e}")
            traceback.print_exc()
            return False
    
    async def fetch_all(self, symbols: List[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Fetch data from all 13 sources in parallel
        Returns: {source_name: data_dict}
        """
        if not self.sources_loaded:
            await self.load_sources()
        
        try:
            self.logger.info("Fetching data from all sources...")
            
            fetch_tasks = []
            source_names = []
            
            # Create fetch tasks for all sources
            for source_name, instances in self.source_instances.items():
                if instances and 'fetcher' in instances:
                    fetcher = instances['fetcher']
                    if hasattr(fetcher, 'fetch'):
                        task = asyncio.create_task(
                            self._safe_fetch(source_name, fetcher, symbols, **kwargs)
                        )
                        fetch_tasks.append(task)
                        source_names.append(source_name)
            
            # Execute all fetches in parallel
            if fetch_tasks:
                results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                
                # Combine results and cache raw data
                fetch_results = {}
                for i, result in enumerate(results):
                    source_name = source_names[i]
                    if isinstance(result, MAIFAError):
                        # Handle MAIFA errors - use titanium contract format
                        fetch_results[source_name] = result.to_dict()
                        self.logger.error(f"MAIFA error in {source_name}: {result.message}")
                    elif isinstance(result, Exception):
                        # Handle raw exceptions - wrap in MAIFA error
                        fetch_results[source_name] = FetchError(
                            source=source_name,
                            stage="fetch",
                            error_type=result.__class__.__name__,
                            message=str(result),
                            retryable=True
                        ).to_dict()
                        self.logger.error(f"Raw exception in {source_name}: {result}")
                    else:
                        fetch_results[source_name] = result
                        # Cache raw data for validation/normalization
                        if result.get("status") == "success":
                            self.raw_data_cache[source_name] = result.get("data")
                        self.logger.debug(f"Fetch success in {source_name}")
                
                self.logger.info(f"Fetched data from {len(fetch_results)} sources")
                return fetch_results
            else:
                self.logger.warning("No fetchers available")
                return {}
                
        except Exception as e:
            self.logger.error(f"Failed to fetch all sources: {e}")
            traceback.print_exc()
            return {}
    
    async def _safe_fetch(self, source_name: str, fetcher: DataFetcher, 
                        symbols: List[str] = None, **kwargs) -> Dict[str, Any]:
        """Safe fetch with error handling and timeout"""
        try:
            # Add timeout to prevent blocking
            timeout = kwargs.get('timeout', 30.0)
            
            if asyncio.iscoroutinefunction(fetcher.fetch):
                result = await asyncio.wait_for(fetcher.fetch(symbols, **kwargs), timeout=timeout)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, fetcher.fetch, symbols, **kwargs),
                    timeout=timeout
                )
            
            return {
                "status": "success",
                "data": result,
                "source": source_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except asyncio.TimeoutError:
            # Return MAIFA error for timeout
            return FetchError(
                source=source_name,
                stage="fetch",
                error_type="TimeoutError",
                message=f"Timeout in {source_name} after 30s",
                retryable=True
            ).to_dict()
        except MAIFAError:
            # Re-raise MAIFA errors to be handled by gather
            raise
        except Exception as e:
            # Return MAIFA error for other exceptions
            return FetchError(
                source=source_name,
                stage="fetch",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=True
            ).to_dict()
    
    async def validate_all(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data from all sources in parallel
        Returns: {source_name: validation_result}
        """
        try:
            self.logger.info("Validating data from all sources...")
            
            validate_tasks = []
            source_names = []
            
            # Create validation tasks
            for source_name, data in raw_data.items():
                if data.get("status") == "success" and source_name in self.source_instances:
                    instances = self.source_instances[source_name]
                    if 'validator' in instances:
                        validator = instances['validator']
                        task = asyncio.create_task(
                            self._safe_validate(source_name, validator, data.get("data"))
                        )
                        validate_tasks.append(task)
                        source_names.append(source_name)
            
            # Execute all validations in parallel
            if validate_tasks:
                results = await asyncio.gather(*validate_tasks, return_exceptions=True)
                
                # Combine results
                validation_results = {}
                for i, result in enumerate(results):
                    source_name = source_names[i]
                    if isinstance(result, MAIFAError):
                        # Handle MAIFA errors - use titanium contract format
                        validation_results[source_name] = result.to_dict()
                        self.logger.error(f"MAIFA validation error in {source_name}: {result.message}")
                    elif isinstance(result, Exception):
                        # Handle raw exceptions - wrap in MAIFA error
                        validation_results[source_name] = ValidationError(
                            source=source_name,
                            stage="validate",
                            error_type=result.__class__.__name__,
                            message=str(result),
                            retryable=False
                        ).to_dict()
                        self.logger.error(f"Raw validation exception in {source_name}: {result}")
                    else:
                        validation_results[source_name] = result
                
                self.logger.info(f"Validated data from {len(validation_results)} sources")
                return validation_results
            else:
                self.logger.warning("No validators available")
                return {}
                
        except Exception as e:
            self.logger.error(f"Failed to validate all sources: {e}")
            traceback.print_exc()
            return {}
    
    async def _safe_validate(self, source_name: str, validator: DataValidator, 
                          data: Any) -> Dict[str, Any]:
        """Safe validation with error handling"""
        try:
            if asyncio.iscoroutinefunction(validator.validate):
                is_valid = await validator.validate(data)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                is_valid = await loop.run_in_executor(None, validator.validate, data)
            
            return {
                "status": "success",
                "valid": is_valid,
                "source": source_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except MAIFAError:
            # Re-raise MAIFA errors to be handled by gather
            raise
        except Exception as e:
            # Return MAIFA error for other exceptions
            return ValidationError(
                source=source_name,
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            ).to_dict()
    
    async def normalize_all(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize data from all sources in parallel
        Returns: {source_name: normalized_data}
        """
        try:
            self.logger.info("Normalizing data from all sources...")
            
            normalize_tasks = []
            source_names = []
            
            # Create normalization tasks
            for source_name, data in validated_data.items():
                if data.get("status") == "success" and data.get("valid") and source_name in self.source_instances:
                    instances = self.source_instances[source_name]
                    if 'normalizer' in instances:
                        normalizer = instances['normalizer']
                        # Get cached raw data
                        raw_data = self.raw_data_cache.get(source_name)
                        task = asyncio.create_task(
                            self._safe_normalize(source_name, normalizer, raw_data)
                        )
                        normalize_tasks.append(task)
                        source_names.append(source_name)
            
            # Execute all normalizations in parallel
            if normalize_tasks:
                results = await asyncio.gather(*normalize_tasks, return_exceptions=True)
                
                # Combine results
                normalized_results = {}
                for i, result in enumerate(results):
                    source_name = source_names[i]
                    if isinstance(result, MAIFAError):
                        # Handle MAIFA errors - use titanium contract format
                        normalized_results[source_name] = result.to_dict()
                        self.logger.error(f"MAIFA normalization error in {source_name}: {result.message}")
                    elif isinstance(result, Exception):
                        # Handle raw exceptions - wrap in MAIFA error
                        normalized_results[source_name] = NormalizationError(
                            source=source_name,
                            stage="normalize",
                            error_type=result.__class__.__name__,
                            message=str(result),
                            retryable=False
                        ).to_dict()
                        self.logger.error(f"Raw normalization exception in {source_name}: {result}")
                    else:
                        normalized_results[source_name] = result
                
                self.logger.info(f"Normalized data from {len(normalized_results)} sources")
                return normalized_results
            else:
                self.logger.warning("No normalizers available")
                return {}
                
        except Exception as e:
            self.logger.error(f"Failed to normalize all sources: {e}")
            traceback.print_exc()
            return {}
    
    async def _safe_normalize(self, source_name: str, normalizer: DataNormalizer, 
                           data: Any) -> Dict[str, Any]:
        """Safe normalization with error handling"""
        try:
            if asyncio.iscoroutinefunction(normalizer.normalize):
                normalized = await normalizer.normalize(data)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                normalized = await loop.run_in_executor(None, normalizer.normalize, data)
            
            return {
                "status": "success",
                "data": normalized,
                "source": source_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except MAIFAError:
            # Re-raise MAIFA errors to be handled by gather
            raise
        except Exception as e:
            # Return MAIFA error for other exceptions
            return NormalizationError(
                source=source_name,
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            ).to_dict()
    
    async def get_source_status(self) -> Dict[str, Any]:
        """Get status of all sources"""
        return {
            "sources_loaded": self.sources_loaded,
            "total_sources": len(self.source_configs),
            "source_list": list(self.source_configs.keys()),
            "timestamp": datetime.now().isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for all sources"""
        try:
            if not self.sources_loaded:
                await self.load_sources()
            
            health_results = {}
            
            for source_name, instances in self.source_instances.items():
                health_results[source_name] = {
                    "has_fetcher": "fetcher" in instances,
                    "has_parser": "parser" in instances, 
                    "has_validator": "validator" in instances,
                    "has_normalizer": "normalizer" in instances,
                    "status": "healthy" if len(instances) == 4 else "incomplete"
                }
            
            return {
                "overall_health": "healthy" if all(
                    h["status"] == "healthy" for h in health_results.values()
                ) else "degraded",
                "sources": health_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "overall_health": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Global orchestrator instance
orchestrator = DataIngestionOrchestrator()
