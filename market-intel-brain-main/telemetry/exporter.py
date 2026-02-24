"""
Prometheus Exporter

This module provides Prometheus exporter functionality for sending
telemetry data to Prometheus for visualization in Grafana.
"""

import time
import logging
import asyncio
from typing import Dict, Any, Optional, List
from threading import Lock
from dataclasses import dataclass

try:
    from prometheus_client import CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
    from prometheus_client.exposition import MetricsHandler
    from aiohttp import web
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    web = None
    CollectorRegistry = None
    generate_latest = None
    CONTENT_TYPE_LATEST = None
    MetricsHandler = None


@dataclass
class ExporterConfig:
    """Configuration for Prometheus exporter."""
    host: str = "0.0.0.0"
    port: int = 8000
    endpoint: str = "/metrics"
    registry: Optional[CollectorRegistry] = None
    enable_compression: bool = False
    update_interval: float = 5.0  # seconds
    enable_gateway: bool = False
    gateway_url: Optional[str] = None
    job_name: str = "market_intel_brain"


class PrometheusExporter:
    """
    Prometheus exporter for telemetry data.
    
    This class provides an HTTP server for Prometheus to scrape
    metrics and optionally pushes to a Prometheus gateway.
    """
    
    def __init__(
        self,
        config: Optional[ExporterConfig] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize Prometheus exporter.
        
        Args:
            config: Exporter configuration
            logger: Logger instance
        """
        self.config = config or ExporterConfig()
        self.logger = logger or logging.getLogger("PrometheusExporter")
        
        if not PROMETHEUS_AVAILABLE:
            self.logger.error("prometheus_client not available")
            return
        
        self.registry = self.config.registry or CollectorRegistry()
        self.app = None
        self.site = None
        self.runner = None
        self._lock = Lock()
        
        self.logger.info(f"PrometheusExporter initialized (port={self.config.port})")
    
    async def start(self):
        """Start the Prometheus HTTP server."""
        if not PROMETHEUS_AVAILABLE:
            self.logger.error("Cannot start: prometheus_client not available")
            return
        
        if self.app is not None:
            self.logger.warning("Prometheus exporter already started")
            return
        
        # Create web application
        self.app = web.Application()
        self.app.router.add_get(self.config.endpoint, self._metrics_handler)
        
        # Create and start site
        self.runner = web.AppRunner(self.app)
        self.site = web.TCPSite(self.runner, self.config.host, self.config.port)
        
        try:
            await self.site.start()
            self.logger.info(f"Prometheus exporter started on {self.config.host}:{self.config.port}")
            
            # Start background tasks
            if self.config.enable_gateway:
                asyncio.create_task(self._gateway_push_loop())
            
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus exporter: {e}")
            raise
    
    async def stop(self):
        """Stop the Prometheus HTTP server."""
        if self.site is None:
            return
        
        try:
            await self.site.stop()
            self.logger.info("Prometheus exporter stopped")
        except Exception as e:
            self.logger.error(f"Error stopping Prometheus exporter: {e}")
    
    async def _metrics_handler(self, request: web.Request) -> web.Response:
        """
        Handle metrics requests.
        
        Args:
            request: HTTP request
            
        Returns:
            HTTP response with metrics
        """
        try:
            # Generate latest metrics
            output = generate_latest(self.registry)
            
            # Create response
            response = web.Response(
                body=output,
                content_type=CONTENT_TYPE_LATEST
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error generating metrics: {e}")
            return web.Response(
                text=f"Error generating metrics: {e}",
                status=500
            )
    
    async def _gateway_push_loop(self):
        """Background loop for pushing to Prometheus gateway."""
        if not self.config.enable_gateway or not self.config.gateway_url:
            return
        
        while True:
            try:
                await self._push_to_gateway()
                await asyncio.sleep(self.config.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in gateway push loop: {e}")
                await asyncio.sleep(self.config.update_interval)
    
    async def _push_to_gateway(self):
        """Push metrics to Prometheus gateway."""
        if not PROMETHEUS_AVAILABLE:
            return
        
        try:
            from prometheus_client import push_to_gateway
            
            push_to_gateway(
                self.config.gateway_url,
                job=self.config.job_name,
                registry=self.registry
            )
            
            self.logger.debug(f"Pushed metrics to gateway: {self.config.gateway_url}")
            
        except Exception as e:
            self.logger.error(f"Failed to push to gateway: {e}")
    
    def get_metrics_data(self) -> Dict[str, Any]:
        """
        Get current metrics data.
        
        Returns:
            Metrics data dictionary
        """
        if not PROMETHEUS_AVAILABLE:
            return {"error": "Prometheus not available"}
        
        try:
            # Generate metrics in Prometheus format
            output = generate_latest(self.registry)
            
            # Parse the output into a dictionary
            metrics_data = {}
            
            for line in output.split('\n'):
                if line.startswith('#') or not line.strip():
                    continue
                
                if '{' in line:
                    # This is a metric line
                    try:
                        # Parse metric line
                        parts = line.split('{')
                        metric_info = parts[0].strip()
                        metric_values = parts[1].strip('} ')
                        
                        metric_name = metric_info.split()[0]
                        
                        # Parse values
                        values = {}
                        for value_line in metric_values.split('\n'):
                            if value_line.strip():
                                value_parts = value_line.split()
                                if len(value_parts) >= 2:
                                    value_key = value_parts[0]
                                    value_value = float(value_parts[1])
                                    values[value_key] = value_value
                        
                        metrics_data[metric_name] = values
                        
                    except Exception as e:
                        self.logger.debug(f"Failed to parse metric line: {e}")
                        continue
            
            return metrics_data
            
        except Exception as e:
            return {"error": f"Failed to get metrics data: {e}"}
    
    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get registry information.
        
        Returns:
            Registry information dictionary
        """
        if not PROMETHEUS_AVAILABLE:
            return {"error": "Prometheus not available"}
        
        try:
            collectors = list(self.registry._collector_to_names.keys())
            collector_names = list(self.registry._names_to_collectors.keys())
            
            return {
                "collectors": collectors,
                "collector_names": collector_names,
                "total_collectors": len(collectors)
            }
            
        except Exception as e:
            return {"error": f"Failed to get registry info: {e}"}
    
    def get_exporter_status(self) -> Dict[str, Any]:
        """
        Get exporter status.
        
        Returns:
            Exporter status dictionary
        """
        return {
            "prometheus_available": PROMETHEUS_AVAILABLE,
            "running": self.site is not None and self.site._server is not None,
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "endpoint": self.config.endpoint,
                "enable_gateway": self.config.enable_gateway,
                "gateway_url": self.config.gateway_url,
                "job_name": self.config.job_name
            },
            "registry_info": self.get_registry_info() if PROMETHEUS_AVAILABLE else None
        }


# Global exporter instance
_global_exporter: Optional[PrometheusExporter] = None


def get_exporter(**kwargs) -> PrometheusExporter:
    """
    Get or create the global exporter instance.
    
    Args:
        **kwargs: Configuration overrides
        
    Returns:
        Global PrometheusExporter instance
    """
    global _global_exporter
    if _global_exporter is None:
        _global_exporter = PrometheusExporter(**kwargs)
    return _global_exporter


# Convenience functions
async def start_exporter(**kwargs):
    """Start the global Prometheus exporter."""
    exporter = get_exporter(**kwargs)
    await exporter.start()


async def stop_exporter():
    """Stop the global Prometheus exporter."""
    exporter = get_exporter()
    await exporter.stop()


def get_exporter_status():
    """Get status of global Prometheus exporter."""
    exporter = get_exporter()
    return exporter.get_exporter_status()


def get_metrics_data():
    """Get metrics data from global exporter."""
    exporter = get_exporter()
    return exporter.get_metrics_data()
