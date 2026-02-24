"""
MAIFA v3 Logger Utility - Centralized logging configuration
Provides structured logging for all system components
"""

import logging
import logging.handlers
import json
import sys
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class MAIFALogger:
    """
    MAIFA v3 Logger - Structured logging with multiple output formats
    
    Features:
    - JSON structured logging
    - Multiple log levels and handlers
    - Component-specific loggers
    - Performance tracking
    - Error categorization
    - Log rotation and archival
    """
    
    def __init__(self, 
                 log_level: str = "INFO",
                 log_file: Optional[str] = None,
                 enable_console: bool = True,
                 enable_file: bool = True,
                 enable_json: bool = True):
        
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_json = enable_json
        self.log_file = log_file or "maifa.log"
        
        # Ensure log directory exists
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        self.root_logger = logging.getLogger("MAIFA")
        self.root_logger.setLevel(self.log_level)
        
        # Clear existing handlers
        self.root_logger.handlers.clear()
        
        # Setup handlers
        self._setup_handlers()
        
        # Component loggers cache
        self._component_loggers: Dict[str, logging.Logger] = {}
    
    def _setup_handlers(self):
        """Setup different log handlers"""
        formatter = self._get_formatter()
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(formatter)
            self.root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if self.enable_file:
            file_handler = logging.handlers.RotatingFileHandler(
                self.log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            self.root_logger.addHandler(file_handler)
        
        # JSON file handler for structured logging
        if self.enable_json:
            json_file = self.log_file.replace('.log', '.json')
            json_handler = logging.handlers.RotatingFileHandler(
                json_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5
            )
            json_handler.setLevel(self.log_level)
            json_handler.setFormatter(self._get_json_formatter())
            self.root_logger.addHandler(json_handler)
    
    def _get_formatter(self) -> logging.Formatter:
        """Get standard log formatter"""
        return logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON log formatter"""
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
                
                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                
                # Add extra fields
                for key, value in record.__dict__.items():
                    if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                                  'pathname', 'filename', 'module', 'lineno', 
                                  'funcName', 'created', 'msecs', 'relativeCreated',
                                  'thread', 'threadName', 'processName', 'process',
                                  'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                        log_entry[key] = value
                
                return json.dumps(log_entry, default=str)
        
        return JSONFormatter()
    
    def get_logger(self, component_name: str) -> logging.Logger:
        """Get logger for specific component"""
        if component_name not in self._component_loggers:
            logger_name = f"MAIFA.{component_name}"
            logger = logging.getLogger(logger_name)
            self._component_loggers[component_name] = logger
        
        return self._component_loggers[component_name]
    
    def log_performance(self, 
                       component: str,
                       operation: str,
                       duration: float,
                       metadata: Optional[Dict[str, Any]] = None):
        """Log performance metrics"""
        logger = self.get_logger(f"{component}.performance")
        
        log_data = {
            "operation": operation,
            "duration_ms": duration * 1000,
            "component": component
        }
        
        if metadata:
            log_data.update(metadata)
        
        logger.info(f"Performance: {operation} completed in {duration:.3f}s", extra=log_data)
    
    def log_error(self, 
                  component: str,
                  error: Exception,
                  context: Optional[Dict[str, Any]] = None,
                  severity: str = "ERROR"):
        """Log error with context"""
        logger = self.get_logger(f"{component}.errors")
        
        log_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "component": component,
            "severity": severity
        }
        
        if context:
            log_data.update(context)
        
        log_method = getattr(logger, severity.lower(), logger.error)
        log_method(f"Error in {component}: {str(error)}", extra=log_data, exc_info=True)
    
    def log_agent_execution(self, 
                           agent_name: str,
                           input_data: Dict[str, Any],
                           result: Dict[str, Any],
                           execution_time: float,
                           status: str):
        """Log agent execution details"""
        logger = self.get_logger("agents.execution")
        
        log_data = {
            "agent_name": agent_name,
            "execution_time_ms": execution_time * 1000,
            "status": status,
            "input_size": len(str(input_data)),
            "result_size": len(str(result))
        }
        
        logger.info(f"Agent {agent_name} {status} in {execution_time:.3f}s", extra=log_data)
    
    def log_pipeline_stage(self, 
                           pipeline_name: str,
                           stage: str,
                           input_size: int,
                           output_size: int,
                           duration: float,
                           status: str = "completed"):
        """Log pipeline stage execution"""
        logger = self.get_logger(f"{pipeline_name}.stages")
        
        log_data = {
            "pipeline": pipeline_name,
            "stage": stage,
            "input_size": input_size,
            "output_size": output_size,
            "duration_ms": duration * 1000,
            "status": status
        }
        
        logger.info(f"Pipeline {pipeline_name} stage {stage} {status} in {duration:.3f}s", extra=log_data)
    
    def log_system_metrics(self, metrics: Dict[str, Any]):
        """Log system performance metrics"""
        logger = self.get_logger("system.metrics")
        
        log_data = {
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("System metrics update", extra=log_data)
    
    def log_governance_event(self, 
                            event_type: str,
                            agent_name: str,
                            client_id: str,
                            decision: str,
                            reason: str):
        """Log governance events"""
        logger = self.get_logger("governance.events")
        
        log_data = {
            "event_type": event_type,
            "agent_name": agent_name,
            "client_id": client_id,
            "decision": decision,
            "reason": reason
        }
        
        logger.info(f"Governance: {event_type} for {agent_name} - {decision}", extra=log_data)
    
    def set_component_level(self, component_name: str, level: str):
        """Set log level for specific component"""
        logger = self.get_logger(component_name)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        return {
            "configured_level": logging.getLevelName(self.log_level),
            "handlers": {
                "console": self.enable_console,
                "file": self.enable_file,
                "json": self.enable_json
            },
            "log_file": self.log_file,
            "component_loggers": len(self._component_loggers)
        }


class PerformanceLogger:
    """Context manager for performance logging"""
    
    def __init__(self, 
                 logger: MAIFALogger,
                 component: str,
                 operation: str,
                 metadata: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.component = component
        self.operation = operation
        self.metadata = metadata or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            
            if exc_type:
                # Log error performance
                self.metadata["error"] = str(exc_val)
                self.metadata["error_type"] = exc_type.__name__
                self.logger.log_error(
                    self.component, 
                    exc_val or Exception("Unknown error"), 
                    self.metadata
                )
            else:
                # Log successful performance
                self.logger.log_performance(
                    self.component,
                    self.operation,
                    duration,
                    self.metadata
                )


# Global logger instance
maifa_logger = MAIFALogger()

def setup_logger(component_name: str, 
                level: Optional[str] = None,
                **kwargs) -> logging.Logger:
    """Setup logger for a component"""
    if level:
        maifa_logger.set_component_level(component_name, level)
    
    return maifa_logger.get_logger(component_name)

def log_performance(component: str, operation: str, **kwargs):
    """Decorator for performance logging"""
    def decorator(func):
        def wrapper(*args, **func_kwargs):
            with PerformanceLogger(maifa_logger, component, operation, kwargs):
                return func(*args, **func_kwargs)
        return wrapper
    return decorator

async def log_async_performance(component: str, operation: str, **kwargs):
    """Async context manager for performance logging"""
    return PerformanceLogger(maifa_logger, component, operation, kwargs)

def get_logger(component_name: str) -> logging.Logger:
    """Get logger for component"""
    return maifa_logger.get_logger(component_name)
