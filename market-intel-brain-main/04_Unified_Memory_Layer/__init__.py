"""
04_Unified_Memory_Layer: Historical data, Vector embeddings for news, and State Manager
Centralized memory and state management for the entire system
"""

import asyncio
import json
import sqlite3
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import hashlib
import pickle
from pathlib import Path

@dataclass
class MarketMemory:
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    technical_indicators: Dict[str, float]
    news_context: List[str]
    
@dataclass
class NewsEmbedding:
    news_id: str
    content_hash: str
    vector: np.ndarray
    metadata: Dict[str, Any]
    timestamp: datetime

class VectorStore:
    """High-performance vector embeddings for news and market data"""
    
    def __init__(self, storage_path: str = "data/vector_store"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.embeddings: Dict[str, NewsEmbedding] = {}
        self.index = {}  # Simple in-memory index
        
    async def store_embedding(self, news_id: str, text: str, metadata: Dict[str, Any] = None):
        """Store text embedding for similarity search"""
        content_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Simple embedding (replace with actual model like sentence-transformers)
        vector = self._simple_embedding(text)
        
        embedding = NewsEmbedding(
            news_id=news_id,
            content_hash=content_hash,
            vector=vector,
            metadata=metadata or {},
            timestamp=datetime.now()
        )
        
        self.embeddings[news_id] = embedding
        await self._save_to_disk(embedding)
        
    def _simple_embedding(self, text: str) -> np.ndarray:
        """Simple text embedding (replace with proper model)"""
        # Placeholder - implement proper embedding model
        words = text.lower().split()
        vocab = set(words)
        return np.random.random(min(384, len(vocab)))  # Simulate 384-dim embedding
        
    async def _save_to_disk(self, embedding: NewsEmbedding):
        """Persist embedding to disk"""
        file_path = self.storage_path / f"{embedding.news_id}.pkl"
        with open(file_path, 'wb') as f:
            pickle.dump(embedding, f)
            
    async def find_similar(self, query_vector: np.ndarray, top_k: int = 10) -> List[NewsEmbedding]:
        """Find similar embeddings using cosine similarity"""
        similarities = []
        for embedding in self.embeddings.values():
            similarity = np.dot(query_vector, embedding.vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(embedding.vector)
            )
            similarities.append((similarity, embedding))
            
        similarities.sort(reverse=True, key=lambda x: x[0])
        return [emb for _, emb in similarities[:top_k]]

class HistoricalDataManager:
    """Historical market data management with caching"""
    
    def __init__(self, db_path: str = "data/market_history.db"):
        self.db_path = db_path
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)
        self._init_database()
        
    def _init_database(self):
        """Initialize SQLite database for historical data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS market_data (
                symbol TEXT,
                timestamp DATETIME,
                price REAL,
                volume INTEGER,
                technical_indicators TEXT,
                PRIMARY KEY (symbol, timestamp)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_history (
                news_id TEXT PRIMARY KEY,
                timestamp DATETIME,
                content TEXT,
                source TEXT,
                sentiment_score REAL
            )
        ''')
        
        conn.commit()
        conn.close()
        
    async def store_market_data(self, data: MarketMemory):
        """Store market data with caching"""
        cache_key = f"{data.symbol}_{data.timestamp}"
        self.cache[cache_key] = {
            'data': data,
            'timestamp': datetime.now()
        }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO market_data 
            (symbol, timestamp, price, volume, technical_indicators)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.symbol,
            data.timestamp,
            data.price,
            data.volume,
            json.dumps(data.technical_indicators)
        ))
        
        conn.commit()
        conn.close()
        
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[MarketMemory]:
        """Retrieve historical data for a symbol"""
        cache_key = f"{symbol}_history_{days}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - cached['timestamp'] < self.cache_ttl:
                return cached['data']
                
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cursor.execute('''
            SELECT symbol, timestamp, price, volume, technical_indicators
            FROM market_data
            WHERE symbol = ? AND timestamp >= ?
            ORDER BY timestamp DESC
        ''', (symbol, cutoff_date))
        
        results = []
        for row in cursor.fetchall():
            results.append(MarketMemory(
                symbol=row[0],
                timestamp=datetime.fromisoformat(row[1]),
                price=row[2],
                volume=row[3],
                technical_indicators=json.loads(row[4]),
                news_context=[]
            ))
        
        conn.close()
        
        self.cache[cache_key] = {
            'data': results,
            'timestamp': datetime.now()
        }
        
        return results

class StateManager:
    """Centralized state management for the entire system"""
    
    def __init__(self):
        self.system_state = {
            'active_agents': {},
            'market_conditions': {},
            'system_health': {
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'active_connections': 0
            },
            'last_update': datetime.now()
        }
        self.lock = asyncio.Lock()
        
    async def update_state(self, key: str, value: Any):
        """Thread-safe state update"""
        async with self.lock:
            self.system_state[key] = value
            self.system_state['last_update'] = datetime.now()
            
    async def get_state(self, key: str = None) -> Any:
        """Thread-safe state retrieval"""
        async with self.lock:
            if key:
                return self.system_state.get(key)
            return self.system_state.copy()
            
    async def register_agent(self, agent_id: str, agent_info: Dict[str, Any]):
        """Register active agent"""
        async with self.lock:
            self.system_state['active_agents'][agent_id] = {
                **agent_info,
                'registered_at': datetime.now(),
                'status': 'active'
            }
            
    async def update_agent_status(self, agent_id: str, status: str):
        """Update agent status"""
        async with self.lock:
            if agent_id in self.system_state['active_agents']:
                self.system_state['active_agents'][agent_id]['status'] = status
                self.system_state['active_agents'][agent_id]['last_heartbeat'] = datetime.now()
