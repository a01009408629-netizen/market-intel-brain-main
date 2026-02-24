"""
Parquet Storage Engine with 512MB In-Memory Buffer
Optimized for HDD with LZ4/Snappy compression
"""

import asyncio
import os
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc
from concurrent.futures import ThreadPoolExecutor
import json

from infrastructure.data_normalization import UnifiedInternalSchema, DataType


class ParquetStorageConfig:
    """Configuration for Parquet storage."""
    
    def __init__(self):
        self.base_path = Path("data")
        self.buffer_size_mb = 512  # 512MB in-memory buffer
        self.compression = "lz4"  # lz4 or snappy
        self.partition_by = ["year", "month", "day"]
        self.row_group_size = 10000
        self.flush_interval_seconds = 300  # 5 minutes
        self.max_buffer_items = 50000


class ParquetBuffer:
    """In-memory buffer for batch writes."""
    
    def __init__(self, config: ParquetStorageConfig):
        self.config = config
        self.buffer = {}
        self.buffer_size_bytes = 0
        self.last_flush = time.time()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def add_item(self, item: UnifiedInternalSchema) -> bool:
        """Add item to buffer."""
        try:
            # Convert to dictionary
            item_dict = self._item_to_dict(item)
            
            # Get data type
            data_type = item_dict['data_type']
            
            if data_type not in self.buffer:
                self.buffer[data_type] = []
            
            # Add to buffer
            self.buffer[data_type].append(item_dict)
            
            # Estimate size (rough calculation)
            item_size = len(json.dumps(item_dict, default=str))
            self.buffer_size_bytes += item_size
            
            return True
            
        except Exception as e:
            print(f"Error adding item to buffer: {e}")
            return False
    
    def _item_to_dict(self, item: UnifiedInternalSchema) -> Dict[str, Any]:
        """Convert UnifiedInternalSchema to dictionary."""
        return {
            'data_type': item.data_type.value if hasattr(item.data_type, 'value') else str(item.data_type),
            'source': item.source,
            'source_type': item.source_type.value if hasattr(item.source_type, 'value') else str(item.source_type),
            'symbol': item.symbol,
            'timestamp': item.timestamp,
            'price': float(item.price) if item.price else None,
            'volume': float(item.volume) if item.volume else None,
            'market_cap': float(item.market_cap) if item.market_cap else None,
            'pe_ratio': float(item.pe_ratio) if item.pe_ratio else None,
            'dividend_yield': float(item.dividend_yield) if item.dividend_yield else None,
            'week_52_high': float(item.week_52_high) if item.week_52_high else None,
            'week_52_low': float(item.week_52_low) if item.week_52_low else None,
            'value': float(item.value) if item.value else None,
            'title': item.title,
            'content': item.content,
            'author': item.author,
            'url': item.url,
            'sentiment': item.sentiment,
            'relevance_score': float(item.relevance_score) if item.relevance_score else None,
            'tags': item.tags,
            'raw_data': json.dumps(item.raw_data) if item.raw_data else None,
            'processing_latency_ms': float(item.processing_latency_ms) if item.processing_latency_ms else None
        }
    
    def should_flush(self) -> bool:
        """Check if buffer should be flushed."""
        # Check size limit
        buffer_size_mb = self.buffer_size_bytes / (1024 * 1024)
        if buffer_size_mb >= self.config.buffer_size_mb:
            return True
        
        # Check time limit
        if time.time() - self.last_flush >= self.config.flush_interval_seconds:
            return True
        
        # Check item count
        total_items = sum(len(items) for items in self.buffer.values())
        if total_items >= self.config.max_buffer_items:
            return True
        
        return False
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """Get buffer statistics."""
        total_items = sum(len(items) for items in self.buffer.values())
        
        return {
            'total_items': total_items,
            'buffer_size_mb': self.buffer_size_bytes / (1024 * 1024),
            'data_types': list(self.buffer.keys()),
            'items_by_type': {k: len(v) for k, v in self.buffer.items()},
            'last_flush': self.last_flush,
            'time_since_flush': time.time() - self.last_flush
        }


class ParquetStorage:
    """High-performance Parquet storage engine."""
    
    def __init__(self, config: Optional[ParquetStorageConfig] = None):
        self.config = config or ParquetStorageConfig()
        self.buffer = ParquetBuffer(self.config)
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Ensure base directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create necessary directories."""
        directories = [
            self.config.base_path / "stocks",
            self.config.base_path / "forex",
            self.config.base_path / "macro",
            self.config.base_path / "news"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def start(self):
        """Start the storage engine."""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        print("Parquet storage engine started")
    
    async def stop(self):
        """Stop the storage engine."""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        await self.flush_buffer()
        
        self.executor.shutdown(wait=True)
        print("Parquet storage engine stopped")
    
    async def store_item(self, item: UnifiedInternalSchema) -> bool:
        """Store a single item."""
        return self.buffer.add_item(item)
    
    async def store_items(self, items: List[UnifiedInternalSchema]) -> int:
        """Store multiple items."""
        success_count = 0
        for item in items:
            if await self.store_item(item):
                success_count += 1
        return success_count
    
    async def _flush_loop(self):
        """Background flush loop."""
        while self._running:
            try:
                if self.buffer.should_flush():
                    await self.flush_buffer()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                print(f"Flush loop error: {e}")
                await asyncio.sleep(30)
    
    async def flush_buffer(self) -> bool:
        """Flush buffer to disk."""
        if not self.buffer.buffer:
            return True
        
        try:
            # Process each data type
            for data_type, items in self.buffer.buffer.items():
                if not items:
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame(items)
                
                # Convert timestamp column
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                # Add partition columns
                df['year'] = df['timestamp'].dt.year
                df['month'] = df['timestamp'].dt.month
                df['day'] = df['timestamp'].dt.day
                
                # Write to Parquet
                await self._write_parquet(df, data_type)
            
            # Clear buffer
            self.buffer.buffer.clear()
            self.buffer.buffer_size_bytes = 0
            self.buffer.last_flush = time.time()
            
            return True
            
        except Exception as e:
            print(f"Buffer flush error: {e}")
            return False
    
    async def _write_parquet(self, df: pd.DataFrame, data_type: str) -> bool:
        """Write DataFrame to Parquet file."""
        try:
            # Determine output directory
            if data_type in ['EQUITY', 'TICK']:
                output_dir = self.config.base_path / "stocks"
            elif data_type == 'FOREX':
                output_dir = self.config.base_path / "forex"
            elif data_type == 'MACRO':
                output_dir = self.config.base_path / "macro"
            elif data_type == 'NEWS':
                output_dir = self.config.base_path / "news"
            else:
                output_dir = self.config.base_path / "other"
            
            # Create filename with date
            latest_date = df['timestamp'].max()
            date_str = latest_date.strftime('%Y-%m-%d')
            filename = f"{data_type.lower()}_{date_str}.parquet"
            
            output_path = output_dir / filename
            
            # Convert to Arrow Table
            table = pa.Table.from_pandas(df)
            
            # Write with compression
            def _write():
                pq.write_to_dataset(
                    table,
                    root_path=str(output_dir),
                    partition_cols=self.config.partition_by,
                    compression=self.config.compression,
                    row_group_size=self.config.row_group_size,
                    existing_data_behavior='overwrite_or_ignore'
                )
            
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, _write)
            
            print(f"Written {len(df)} {data_type} items to {output_path}")
            return True
            
        except Exception as e:
            print(f"Parquet write error: {e}")
            return False
    
    async def query_data(self, 
                      data_type: Optional[str] = None,
                      symbol: Optional[str] = None,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query data from Parquet files."""
        try:
            # Determine search path
            if data_type:
                if data_type in ['EQUITY', 'TICK']:
                    search_path = self.config.base_path / "stocks"
                elif data_type == 'FOREX':
                    search_path = self.config.base_path / "forex"
                elif data_type == 'MACRO':
                    search_path = self.config.base_path / "macro"
                elif data_type == 'NEWS':
                    search_path = self.config.base_path / "news"
                else:
                    search_path = self.config.base_path
            else:
                search_path = self.config.base_path
            
            # Find Parquet files
            parquet_files = list(search_path.rglob("*.parquet"))
            
            if not parquet_files:
                return []
            
            # Read and filter data
            def _read_and_filter():
                all_data = []
                
                for file_path in parquet_files:
                    try:
                        # Read Parquet file
                        table = pq.read_table(file_path)
                        df = table.to_pandas()
                        
                        # Apply filters
                        if symbol and 'symbol' in df.columns:
                            df = df[df['symbol'] == symbol]
                        
                        if start_date and 'timestamp' in df.columns:
                            df = df[df['timestamp'] >= start_date]
                        
                        if end_date and 'timestamp' in df.columns:
                            df = df[df['timestamp'] <= end_date]
                        
                        if not df.empty:
                            all_data.append(df)
                            
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                        continue
                
                # Combine all data
                if all_data:
                    combined_df = pd.concat(all_data, ignore_index=True)
                    
                    # Sort by timestamp
                    if 'timestamp' in combined_df.columns:
                        combined_df = combined_df.sort_values('timestamp', ascending=False)
                    
                    # Apply limit
                    if limit:
                        combined_df = combined_df.head(limit)
                    
                    return combined_df.to_dict('records')
                
                return []
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, _read_and_filter)
            
            return result
            
        except Exception as e:
            print(f"Query error: {e}")
            return []
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        stats = {
            'buffer_stats': self.buffer.get_buffer_stats(),
            'config': {
                'buffer_size_mb': self.config.buffer_size_mb,
                'compression': self.config.compression,
                'partition_by': self.config.partition_by,
                'flush_interval_seconds': self.config.flush_interval_seconds
            }
        }
        
        # Calculate file sizes
        try:
            total_size = 0
            file_count = 0
            
            for data_dir in ["stocks", "forex", "macro", "news"]:
                dir_path = self.config.base_path / data_dir
                if dir_path.exists():
                    for file_path in dir_path.rglob("*.parquet"):
                        total_size += file_path.stat().st_size
                        file_count += 1
            
            stats['disk_usage'] = {
                'total_size_mb': total_size / (1024 * 1024),
                'file_count': file_count
            }
            
        except Exception as e:
            stats['disk_usage'] = {'error': str(e)}
        
        return stats


# Global storage instance
_parquet_storage: Optional[ParquetStorage] = None


def get_parquet_storage() -> ParquetStorage:
    """Get global Parquet storage instance."""
    global _parquet_storage
    if _parquet_storage is None:
        _parquet_storage = ParquetStorage()
    return _parquet_storage


async def main():
    """Test Parquet storage."""
    print("Testing Parquet Storage Engine...")
    
    # Create storage
    storage = get_parquet_storage()
    await storage.start()
    
    # Create test data
    from infrastructure.data_normalization import DataType, SourceType
    
    test_items = []
    for i in range(1000):
        item = UnifiedInternalSchema(
            data_type=DataType.EQUITY,
            source="test",
            source_type=SourceType.REST,
            symbol="AAPL",
            timestamp=datetime.now(timezone.utc),
            price=150.0 + (i * 0.01),
            volume=1000000 + i,
            market_cap=3000000000000,
            pe_ratio=25.5,
            dividend_yield=0.5
        )
        test_items.append(item)
    
    # Store items
    print(f"Storing {len(test_items)} items...")
    success_count = await storage.store_items(test_items)
    print(f"Successfully stored {success_count} items")
    
    # Get stats
    stats = storage.get_storage_stats()
    print(f"Storage stats: {json.dumps(stats, indent=2, default=str)}")
    
    # Query data
    print("Querying stored data...")
    queried_data = await storage.query_data(
        data_type="EQUITY",
        symbol="AAPL",
        limit=10
    )
    print(f"Queried {len(queried_data)} items")
    
    if queried_data:
        print(f"Sample: {queried_data[0]}")
    
    # Flush and stop
    await storage.flush_buffer()
    await storage.stop()
    
    print("Parquet storage test completed!")


if __name__ == "__main__":
    asyncio.run(main())
