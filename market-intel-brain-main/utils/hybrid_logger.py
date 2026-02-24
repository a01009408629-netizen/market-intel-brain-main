"""
Hybrid Logger - High-Efficiency Async Logging System

Optimized logging configuration for constrained hardware (8GB RAM + HDD)
with minimal disk I/O and non-blocking async operations.

Features:
- Async logging queue to prevent blocking
- Terminal-only output for INFO/DEBUG/WARNING
- HDD logging only for CRITICAL and necessary ERRORs
- Minimal resource footprint
- Non-blocking operations
- Smart log level routing
"""

import asyncio
import logging
import logging.handlers
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from enum import Enum


class LogLevel(Enum):
    """Log levels with routing rules"""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"


class HybridLogHandler(logging.Handler):
    """
    Hybrid log handler that routes logs based on level.
    
    - INFO/DEBUG/WARNING -> Terminal only (stdout)
    - CRITICAL/ERROR -> Terminal + HDD (for critical errors)
    """
    
    def __init__(self, log_file_path: Optional[str] = None):
        super().__init__()
        self.log_file_path = log_file_path or "logs/critical_errors.log"
        self.terminal_handler = None
        self.file_handler = None
        
        # Ensure log directory exists
        if self.log_file_path:
            log_dir = Path(self.log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
        
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup terminal and file handlers."""
        # Terminal handler for all levels
        self.terminal_handler = logging.StreamHandler(sys.stdout)
        self.terminal_handler.setLevel(logging.DEBUG)
        
        # Format for terminal output
        terminal_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.terminal_handler.setFormatter(terminal_formatter)
        
        # File handler only for critical errors
        if self.log_file_path:
            self.file_handler = logging.FileHandler(self.log_file_path, mode='a', encoding='utf-8')
            self.file_handler.setLevel(logging.CRITICAL)
            
            # Format for file output (more detailed)
            file_formatter = logging.Formatter(
                fmt='%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(lineno)d - %(funcName)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self.file_handler.setFormatter(file_formatter)
    
    def emit(self, record: logging.LogRecord):
        """
        Emit log record with smart routing.
        
        Args:
            record: Log record to emit
        """
        try:
            # Always send to terminal
            if self.terminal_handler:
                self.terminal_handler.emit(record)
            
            # Only send critical errors to file
            if record.levelno >= logging.CRITICAL and self.file_handler:
                self.file_handler.emit(record)
                
        except Exception as e:
            # Fallback to stderr if logging fails
            print(f"Logging error: {e}", file=sys.stderr)
            print(f"Original record: {record.getMessage()}", file=sys.stderr)
    
    def close(self):
        """Close all handlers."""
        if self.terminal_handler:
            self.terminal_handler.close()
        if self.file_handler:
            self.file_handler.close()


class AsyncLogQueueHandler(logging.handlers.QueueHandler):
    """
    Async log queue handler with non-blocking operations.
    
    Uses asyncio queue for non-blocking log processing on constrained hardware.
    """
    
    def __init__(self, queue: Optional[asyncio.Queue] = None):
        # Create asyncio queue if not provided
        if queue is None:
            queue = asyncio.Queue(maxsize=1000)  # Limit queue size
        
        self.queue = queue
        self.listener_task: Optional[asyncio.Task] = None
        self.stop_event = asyncio.Event()
        
        # Create a simple queue-like interface for logging
        class AsyncQueue:
            def __init__(self, aio_queue):
                self.aio_queue = aio_queue
            
            def put(self, record):
                """Non-blocking put with fallback."""
                try:
                    # Try to put without blocking
                    self.aio_queue.put_nowait(record)
                except asyncio.QueueFull:
                    # Queue is full, drop the record to prevent blocking
                    print(f"[AsyncLogQueue] Queue full, dropping log: {record.getMessage()}", file=sys.stderr)
        
        super().__init__(AsyncQueue(queue))
    
    async def start_listener(self, target_handler: logging.Handler):
        """
        Start async listener to process log records.
        
        Args:
            target_handler: Handler to process log records
        """
        self.listener_task = asyncio.create_task(
            self._listen(target_handler)
        )
    
    async def _listen(self, target_handler: logging.Handler):
        """Listen for log records and process them."""
        while not self.stop_event.is_set():
            try:
                # Wait for record with timeout
                record = await asyncio.wait_for(
                    self.queue.get(), 
                    timeout=1.0
                )
                
                # Process record
                target_handler.emit(record)
                
            except asyncio.TimeoutError:
                # Timeout is normal, continue loop
                continue
            except Exception as e:
                print(f"[AsyncLogQueue] Listener error: {e}", file=sys.stderr)
    
    async def stop(self):
        """Stop the async listener."""
        self.stop_event.set()
        
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
        
        # Process remaining records
        while not self.queue.empty():
            try:
                record = self.queue.get_nowait()
                # Emit directly to terminal as fallback
                print(f"[AsyncLogQueue] Remaining: {record.getMessage()}", file=sys.stdout)
            except asyncio.QueueEmpty:
                break


class HybridLogger:
    """
    High-efficiency logger for constrained hardware.
    
    Provides async logging with minimal resource usage and smart HDD routing.
    """
    
    def __init__(self, name: str, log_file_path: Optional[str] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.queue_handler: Optional[AsyncLogQueueHandler] = None
        self.hybrid_handler: Optional[HybridLogHandler] = None
        
        self._setup_logger(log_file_path)
    
    def _setup_logger(self, log_file_path: Optional[str]):
        """Setup logger with async queue and hybrid routing."""
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Set log level
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
        
        # Create hybrid handler for smart routing
        self.hybrid_handler = HybridLogHandler(log_file_path)
        
        # Create async queue handler
        self.queue_handler = AsyncLogQueueHandler()
        
        # Set up async processing (only if event loop is running)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self._start_async_processing())
        except RuntimeError:
            # No event loop running, skip async setup
            pass
    
    async def _start_async_processing(self):
        """Start async log processing."""
        if self.queue_handler and self.hybrid_handler:
            await self.queue_handler.start_listener(self.hybrid_handler)
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message (terminal only)."""
        self.logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message (terminal only)."""
        self.logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message (terminal only)."""
        self.logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message (terminal only, unless critical)."""
        self.logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message (terminal + HDD)."""
        self.logger.critical(message, *args, **kwargs)
    
    async def close(self):
        """Close logger and cleanup resources."""
        if self.queue_handler:
            await self.queue_handler.stop()
        
        if self.hybrid_handler:
            self.hybrid_handler.close()


# Global logger instances
_loggers: Dict[str, HybridLogger] = {}


def get_hybrid_logger(name: str, log_file_path: Optional[str] = None) -> HybridLogger:
    """
    Get or create hybrid logger instance.
    
    Args:
        name: Logger name
        log_file_path: Path for critical error logs
        
    Returns:
        HybridLogger instance
    """
    if name not in _loggers:
        _loggers[name] = HybridLogger(name, log_file_path)
    return _loggers[name]


def setup_hybrid_logging(
    level: str = "INFO",
    log_file_path: Optional[str] = None,
    console_output: bool = True
):
    """
    Setup hybrid logging for the entire application.
    
    Args:
        level: Default log level
        log_file_path: Path for critical error logs
        console_output: Enable console output
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    if console_output:
        # Add hybrid handler to root logger
        hybrid_handler = HybridLogHandler(log_file_path)
        root_logger.addHandler(hybrid_handler)
    
    print(f"[HybridLogger] Setup complete - Level: {level}, Console: {console_output}")
    if log_file_path:
        print(f"[HybridLogger] Critical errors will be logged to: {log_file_path}")


# Convenience functions for common logging patterns
async def log_performance(
    logger: HybridLogger,
    operation: str,
    duration: float,
    metadata: Optional[Dict[str, Any]] = None
):
    """Log performance metrics efficiently."""
    metadata_str = f" | {metadata}" if metadata else ""
    logger.info(f"Performance: {operation} completed in {duration:.3f}s{metadata_str}")


async def log_error_with_context(
    logger: HybridLogger,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
):
    """Log error with context information."""
    context_str = f" | Context: {context}" if context else ""
    logger.error(f"Error: {type(error).__name__}: {error}{context_str}")


async def log_critical_system_event(
    logger: HybridLogger,
    event: str,
    details: Optional[Dict[str, Any]] = None
):
    """Log critical system event (will be written to HDD)."""
    details_str = f" | Details: {details}" if details else ""
    logger.critical(f"CRITICAL SYSTEM EVENT: {event}{details_str}")


# Performance monitoring decorator
def monitor_performance(logger_name: str = "performance"):
    """
    Decorator to monitor function performance.
    
    Args:
        logger_name: Logger name for performance logging
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            logger = get_hybrid_logger(logger_name)
            start_time = asyncio.get_event_loop().time()
            
            try:
                result = await func(*args, **kwargs)
                duration = asyncio.get_event_loop().time() - start_time
                await log_performance(logger, f"{func.__name__}", duration)
                return result
            except Exception as e:
                duration = asyncio.get_event_loop().time() - start_time
                await log_error_with_context(
                    logger, 
                    e, 
                    {"function": func.__name__, "duration": duration}
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            logger = get_hybrid_logger(logger_name)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                asyncio.create_task(
                    log_performance(logger, f"{func.__name__}", duration)
                )
                return result
            except Exception as e:
                duration = time.time() - start_time
                asyncio.create_task(
                    log_error_with_context(
                        logger, 
                        e, 
                        {"function": func.__name__, "duration": duration}
                    )
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


# Initialize hybrid logging for the application
def initialize_hybrid_logging():
    """Initialize hybrid logging with optimal settings for constrained hardware."""
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Setup hybrid logging
    setup_hybrid_logging(
        level="INFO",
        log_file_path="logs/critical_errors.log",
        console_output=True
    )
    
    print("[OK] Hybrid logging initialized - Optimized for constrained hardware")
    print("   - INFO/DEBUG/WARNING: Terminal only")
    print("   - CRITICAL/ERROR: Terminal + HDD logs/critical_errors.log")
    print("   - Async queue: Non-blocking operations")


# Auto-initialize when module is imported
initialize_hybrid_logging()
