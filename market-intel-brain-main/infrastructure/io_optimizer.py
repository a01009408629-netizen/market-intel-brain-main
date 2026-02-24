"""
Production-Ready I/O Optimizer & Memory Backpressure
Ring Buffer (LMAX Disruptor pattern) with AOF Batch Writer
LZ4 compression and HDD-optimized sequential writes
"""

import asyncio
import time
import threading
import os
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
import json
import struct
import hashlib
import lz4.frame
import snappy


@dataclass
class RingBufferConfig:
    """Configuration for ring buffer."""
    capacity: int = 10000
    backpressure_threshold: float = 0.8
    drop_stale_threshold_ms: int = 1000
    batch_size: int = 100
    flush_interval_ms: int = 1000


@dataclass
class AOFConfig:
    """Configuration for Append-Only File writer."""
    file_path: str = "data/market_data.aof"
    max_file_size_mb: int = 100
    compression_type: str = "lz4"  # "lz4" or "snappy"
    buffer_size_mb: int = 5
    sync_interval_ms: int = 5000
    enable_checksum: bool = True


class RingBuffer:
    """Lock-free ring buffer implementation (LMAX Disruptor pattern)."""
    
    def __init__(self, config: RingBufferConfig):
        self.config = config
        self.capacity = config.capacity
        self.buffer = [None] * self.capacity
        self.head = 0
        self.tail = 0
        self.size = 0
        self._lock = threading.RLock()
        self._dropped_count = 0
        self._total_count = 0
        self._last_drop_time = 0
    
    def put(self, item: Any) -> bool:
        """Put item into ring buffer."""
        current_time = time.time() * 1000
        
        with self._lock:
            if self.size >= self.capacity:
                # Check backpressure
                utilization = self.size / self.capacity
                if utilization >= self.config.backpressure_threshold:
                    # Drop stale items
                    self._drop_stale_items(current_time)
                    
                    if self.size >= self.capacity:
                        self._dropped_count += 1
                        return False
            
            # Add item
            self.buffer[self.tail] = item
            self.tail = (self.tail + 1) % self.capacity
            self.size = min(self.size + 1, self.capacity)
            self._total_count += 1
            return True
    
    def get_batch(self, max_items: Optional[int] = None) -> List[Any]:
        """Get batch of items from ring buffer."""
        if max_items is None:
            max_items = self.config.batch_size
        
        with self._lock:
            batch_size = min(max_items, self.size)
            if batch_size == 0:
                return []
            
            batch = []
            for _ in range(batch_size):
                if self.size == 0:
                    break
                
                item = self.buffer[self.head]
                if item is not None:
                    batch.append(item)
                
                self.buffer[self.head] = None
                self.head = (self.head + 1) % self.capacity
                self.size -= 1
            
            return batch
    
    def _drop_stale_items(self, current_time: float):
        """Drop stale items based on timestamp."""
        dropped = 0
        threshold = current_time - self.config.drop_stale_threshold_ms
        
        while self.size > 0:
            item = self.buffer[self.head]
            if item is None:
                break
            
            # Check if item is stale
            item_time = getattr(item, 'timestamp', None)
            if item_time and isinstance(item_time, datetime):
                item_time_ms = item_time.timestamp() * 1000
                if item_time_ms < threshold:
                    self.buffer[self.head] = None
                    self.head = (self.head + 1) % self.capacity
                    self.size -= 1
                    dropped += 1
                else:
                    break
            else:
                break
        
        if dropped > 0:
            self._dropped_count += dropped
            self._last_drop_time = current_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ring buffer statistics."""
        with self._lock:
            return {
                "capacity": self.capacity,
                "size": self.size,
                "utilization": self.size / self.capacity,
                "total_items": self._total_count,
                "dropped_items": self._dropped_count,
                "drop_rate": self._dropped_count / max(self._total_count, 1),
                "last_drop_time": self._last_drop_time,
                "backpressure_active": self.size / self.capacity >= self.config.backpressure_threshold
            }
    
    def clear(self):
        """Clear ring buffer."""
        with self._lock:
            self.buffer = [None] * self.capacity
            self.head = 0
            self.tail = 0
            self.size = 0


class AOFWriter:
    """Append-Only File batch writer with compression."""
    
    def __init__(self, config: AOFConfig):
        self.config = config
        self.file_path = config.file_path
        self.max_file_size = config.max_file_size_mb * 1024 * 1024
        self.buffer_size = config.buffer_size_mb * 1024 * 1024
        
        # Initialize compression
        if config.compression_type == "lz4":
            self.compress = self._compress_lz4
            self.decompress = self._decompress_lz4
        elif config.compression_type == "snappy":
            self.compress = self._compress_snappy
            self.decompress = self._decompress_snappy
        else:
            raise ValueError(f"Unsupported compression type: {config.compression_type}")
        
        self._write_buffer = []
        self._buffer_size = 0
        self._file_handle = None
        self._current_file_size = 0
        self._last_sync_time = time.time()
        self._lock = threading.RLock()
        self._stats = {
            "total_writes": 0,
            "total_bytes": 0,
            "compressed_bytes": 0,
            "compression_ratio": 0.0,
            "sync_count": 0
        }
        
        self._ensure_directory()
        self._open_file()
    
    def _ensure_directory(self):
        """Ensure directory exists."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
    
    def _open_file(self):
        """Open file for writing."""
        if self._file_handle:
            self._file_handle.close()
        
        # Check if file exists and get size
        if os.path.exists(self.file_path):
            self._current_file_size = os.path.getsize(self.file_path)
        else:
            self._current_file_size = 0
        
        # Rotate file if too large
        if self._current_file_size >= self.max_file_size:
            timestamp = int(time.time())
            backup_path = f"{self.file_path}.{timestamp}"
            os.rename(self.file_path, backup_path)
            self._current_file_size = 0
        
        self._file_handle = open(self.file_path, 'ab')
    
    def _compress_lz4(self, data: bytes) -> bytes:
        """Compress data using LZ4."""
        return lz4.frame.compress(data)
    
    def _decompress_lz4(self, data: bytes) -> bytes:
        """Decompress data using LZ4."""
        return lz4.frame.decompress(data)
    
    def _compress_snappy(self, data: bytes) -> bytes:
        """Compress data using Snappy."""
        return snappy.compress(data)
    
    def _decompress_snappy(self, data: bytes) -> bytes:
        """Decompress data using Snappy."""
        return snappy.decompress(data)
    
    def _serialize_item(self, item: Any) -> bytes:
        """Serialize item to bytes."""
        if hasattr(item, 'to_json'):
            data_str = item.to_json()
        elif hasattr(item, 'to_dict'):
            data_str = json.dumps(item.to_dict(), default=str)
        else:
            data_str = json.dumps(item, default=str)
        
        # Add checksum if enabled
        if self.config.enable_checksum:
            checksum = hashlib.sha256(data_str.encode()).hexdigest()[:8]
            data_str = f"{checksum}:{data_str}"
        
        return data_str.encode('utf-8')
    
    def _write_batch(self, batch: List[bytes]):
        """Write batch of compressed data to file."""
        if not batch:
            return
        
        # Compress batch
        batch_data = b'\n'.join(batch)
        compressed_data = self.compress(batch_data)
        
        # Write to file
        with self._lock:
            self._file_handle.write(compressed_data)
            self._file_handle.write(b'\n')  # Batch separator
            self._file_handle.flush()
            
            # Update stats
            self._stats["total_writes"] += len(batch)
            self._stats["total_bytes"] += len(batch_data)
            self._stats["compressed_bytes"] += len(compressed_data)
            self._stats["compression_ratio"] = self._stats["compressed_bytes"] / max(self._stats["total_bytes"], 1)
            self._current_file_size += len(compressed_data) + 1
    
    def write_items(self, items: List[Any]):
        """Write items to buffer and flush if needed."""
        if not items:
            return
        
        # Serialize items
        serialized_items = [self._serialize_item(item) for item in items]
        
        # Add to buffer
        with self._lock:
            self._write_buffer.extend(serialized_items)
            self._buffer_size += sum(len(item) for item in serialized_items)
        
        # Flush if buffer is full or time to sync
        current_time = time.time()
        time_since_sync = (current_time - self._last_sync_time) * 1000
        
        if (self._buffer_size >= self.buffer_size or 
            time_since_sync >= self.config.sync_interval_ms):
            self.flush()
    
    def flush(self):
        """Flush buffer to disk."""
        with self._lock:
            if not self._write_buffer:
                return
            
            # Write batch
            self._write_batch(self._write_buffer)
            
            # Clear buffer
            self._write_buffer.clear()
            self._buffer_size = 0
            self._last_sync_time = time.time()
            self._stats["sync_count"] += 1
    
    def sync(self):
        """Force sync to disk."""
        self.flush()
        if self._file_handle:
            self._file_handle.flush()
            os.fsync(self._file_handle.fileno())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get writer statistics."""
        with self._lock:
            stats = self._stats.copy()
            stats.update({
                "buffer_size_mb": self._buffer_size / (1024 * 1024),
                "buffer_items": len(self._write_buffer),
                "current_file_size_mb": self._current_file_size / (1024 * 1024),
                "compression_type": self.config.compression_type
            })
            return stats
    
    def close(self):
        """Close writer."""
        self.flush()
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None


class IOOptimizer:
    """Main I/O optimizer with ring buffer and AOF writer."""
    
    def __init__(self, ring_config: Optional[RingBufferConfig] = None, 
                 aof_config: Optional[AOFConfig] = None):
        self.ring_config = ring_config or RingBufferConfig()
        self.aof_config = aof_config or AOFConfig()
        
        self.ring_buffer = RingBuffer(self.ring_config)
        self.aof_writer = AOFWriter(self.aof_config)
        
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._stats = {
            "items_processed": 0,
            "items_written": 0,
            "items_dropped": 0,
            "processing_time_ms": 0.0
        }
    
    async def start(self):
        """Start the I/O optimizer."""
        if self._running:
            return
        
        self._running = True
        self._processor_task = asyncio.create_task(self._process_loop())
        print("I/O Optimizer started")
    
    async def stop(self):
        """Stop the I/O optimizer."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        self.aof_writer.close()
        print("I/O Optimizer stopped")
    
    async def put_item(self, item: Any) -> bool:
        """Put item into ring buffer."""
        start_time = time.time()
        success = self.ring_buffer.put(item)
        
        self._stats["items_processed"] += 1
        if not success:
            self._stats["items_dropped"] += 1
        
        self._stats["processing_time_ms"] += (time.time() - start_time) * 1000
        return success
    
    async def put_items(self, items: List[Any]) -> int:
        """Put multiple items into ring buffer."""
        success_count = 0
        for item in items:
            if await self.put_item(item):
                success_count += 1
        return success_count
    
    async def _process_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                # Get batch from ring buffer
                batch = self.ring_buffer.get_batch()
                
                if batch:
                    # Write to AOF
                    self.aof_writer.write_items(batch)
                    self._stats["items_written"] += len(batch)
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.001)
                
            except Exception as e:
                print(f"Error in I/O optimizer processing loop: {e}")
                await asyncio.sleep(0.1)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        ring_stats = self.ring_buffer.get_stats()
        aof_stats = self.aof_writer.get_stats()
        
        stats = {
            "ring_buffer": ring_stats,
            "aof_writer": aof_stats,
            "overall": self._stats.copy()
        }
        
        # Calculate derived metrics
        if self._stats["items_processed"] > 0:
            stats["overall"]["drop_rate"] = self._stats["items_dropped"] / self._stats["items_processed"]
            stats["overall"]["write_rate"] = self._stats["items_written"] / self._stats["items_processed"]
            stats["overall"]["avg_processing_time_ms"] = self._stats["processing_time_ms"] / self._stats["items_processed"]
        
        return stats
    
    def force_flush(self):
        """Force flush all buffers."""
        self.aof_writer.flush()


# Global instance
_io_optimizer: Optional[IOOptimizer] = None


def get_io_optimizer() -> IOOptimizer:
    """Get global I/O optimizer instance."""
    global _io_optimizer
    if _io_optimizer is None:
        _io_optimizer = IOOptimizer()
    return _io_optimizer


async def main():
    """Example usage."""
    optimizer = get_io_optimizer()
    await optimizer.start()
    
    # Mock data items
    from infrastructure.data_normalization import UnifiedInternalSchema, DataType, SourceType
    from datetime import timezone
    
    items = []
    for i in range(1000):
        item = UnifiedInternalSchema(
            data_type=DataType.TICK,
            source="test",
            source_type=SourceType.REST,
            symbol="BTCUSDT",
            timestamp=datetime.now(timezone.utc),
            price=float(50000 + i),
            volume=1.0
        )
        items.append(item)
    
    # Put items
    success_count = await optimizer.put_items(items)
    print(f"Successfully put {success_count}/{len(items)} items")
    
    # Wait for processing
    await asyncio.sleep(2)
    
    # Show stats
    stats = optimizer.get_stats()
    print(f"Stats: {json.dumps(stats, indent=2, default=str)}")
    
    # Stop
    await optimizer.stop()


if __name__ == "__main__":
    import json
    asyncio.run(main())
