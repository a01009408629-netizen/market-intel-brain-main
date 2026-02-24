"""
MAIFA v3 WebSocket API - Real-time streaming delivery
WebSocket endpoints for real-time intelligence streaming
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import websockets

# Import MAIFA components
from core.event_fabric import event_fabric
from core.orchestrator import orchestrator
from services.agents.registry import agent_registry
from utils.logger import get_logger

# Initialize logger
logger = get_logger("api.websocket")

@dataclass
class WebSocketConnection:
    """WebSocket connection information"""
    websocket: WebSocket
    client_id: str
    subscribed_events: Set[str]
    subscribed_symbols: Set[str]
    last_ping: float
    metadata: Dict[str, Any]

class WebSocketManager:
    """
    MAIFA v3 WebSocket Manager - Real-time streaming
    
    Manages WebSocket connections for:
    - Real-time event streaming
    - Agent execution updates
    - System monitoring
    - Live intelligence updates
    """
    
    def __init__(self):
        self.logger = get_logger("websocket.manager")
        self.connections: Dict[str, WebSocketConnection] = {}
        self.symbol_subscriptions: Dict[str, Set[str]] = {}
        self.event_subscriptions: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()
        
        # Background tasks
        self._heartbeat_task = None
        self._event_stream_task = None
        self._running = False
    
    async def connect(self, websocket: WebSocket, client_id: str, metadata: Dict[str, Any] = None) -> bool:
        """Accept WebSocket connection"""
        try:
            await websocket.accept()
            
            async with self._lock:
                connection = WebSocketConnection(
                    websocket=websocket,
                    client_id=client_id,
                    subscribed_events=set(),
                    subscribed_symbols=set(),
                    last_ping=asyncio.get_event_loop().time(),
                    metadata=metadata or {}
                )
                
                self.connections[client_id] = connection
                
                self.logger.info(f"WebSocket connected: {client_id}")
                
                # Send welcome message
                await self.send_message(client_id, {
                    "type": "connection",
                    "action": "connected",
                    "client_id": client_id,
                    "timestamp": datetime.now().isoformat(),
                    "server_info": {
                        "version": "3.0.0",
                        "capabilities": ["events", "agents", "system", "analysis"]
                    }
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"WebSocket connection failed for {client_id}: {e}")
            return False
    
    async def disconnect(self, client_id: str):
        """Disconnect WebSocket client"""
        try:
            async with self._lock:
                if client_id in self.connections:
                    connection = self.connections[client_id]
                    
                    # Remove from subscriptions
                    for symbol in connection.subscribed_symbols:
                        if symbol in self.symbol_subscriptions:
                            self.symbol_subscriptions[symbol].discard(client_id)
                            if not self.symbol_subscriptions[symbol]:
                                del self.symbol_subscriptions[symbol]
                    
                    for event_type in connection.subscribed_events:
                        if event_type in self.event_subscriptions:
                            self.event_subscriptions[event_type].discard(client_id)
                            if not self.event_subscriptions[event_type]:
                                del self.event_subscriptions[event_type]
                    
                    # Remove connection
                    del self.connections[client_id]
                    
                    self.logger.info(f"WebSocket disconnected: {client_id}")
                    
        except Exception as e:
            self.logger.error(f"WebSocket disconnection failed for {client_id}: {e}")
    
    async def send_message(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific client"""
        try:
            async with self._lock:
                if client_id not in self.connections:
                    return False
                
                connection = self.connections[client_id]
                
                if connection.websocket.state == WebSocketState.CONNECTED:
                    await connection.websocket.send_text(json.dumps(message, default=str))
                    return True
                else:
                    # Connection is dead, remove it
                    await self.disconnect(client_id)
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to send message to {client_id}: {e}")
            # Remove dead connection
            await self.disconnect(client_id)
            return False
    
    async def broadcast_message(self, message: Dict[str, Any], filter_func: Optional[callable] = None):
        """Broadcast message to all or filtered clients"""
        try:
            async with self._lock:
                dead_connections = []
                
                for client_id, connection in self.connections.items():
                    # Apply filter if provided
                    if filter_func and not filter_func(connection):
                        continue
                    
                    try:
                        if connection.websocket.state == WebSocketState.CONNECTED:
                            await connection.websocket.send_text(json.dumps(message, default=str))
                        else:
                            dead_connections.append(client_id)
                    except Exception as e:
                        self.logger.error(f"Broadcast failed for {client_id}: {e}")
                        dead_connections.append(client_id)
                
                # Remove dead connections
                for client_id in dead_connections:
                    await self.disconnect(client_id)
                    
        except Exception as e:
            self.logger.error(f"Broadcast failed: {e}")
    
    async def subscribe_events(self, client_id: str, event_types: List[str]) -> bool:
        """Subscribe client to event types"""
        try:
            async with self._lock:
                if client_id not in self.connections:
                    return False
                
                connection = self.connections[client_id]
                
                for event_type in event_types:
                    connection.subscribed_events.add(event_type)
                    
                    if event_type not in self.event_subscriptions:
                        self.event_subscriptions[event_type] = set()
                    
                    self.event_subscriptions[event_type].add(client_id)
                
                self.logger.info(f"Client {client_id} subscribed to events: {event_types}")
                
                # Send confirmation
                await self.send_message(client_id, {
                    "type": "subscription",
                    "action": "subscribed",
                    "target": "events",
                    "event_types": event_types,
                    "timestamp": datetime.now().isoformat()
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Event subscription failed for {client_id}: {e}")
            return False
    
    async def subscribe_symbols(self, client_id: str, symbols: List[str]) -> bool:
        """Subscribe client to symbols"""
        try:
            async with self._lock:
                if client_id not in self.connections:
                    return False
                
                connection = self.connections[client_id]
                
                for symbol in symbols:
                    symbol = symbol.upper()
                    connection.subscribed_symbols.add(symbol)
                    
                    if symbol not in self.symbol_subscriptions:
                        self.symbol_subscriptions[symbol] = set()
                    
                    self.symbol_subscriptions[symbol].add(client_id)
                
                self.logger.info(f"Client {client_id} subscribed to symbols: {symbols}")
                
                # Send confirmation
                await self.send_message(client_id, {
                    "type": "subscription",
                    "action": "subscribed",
                    "target": "symbols",
                    "symbols": symbols,
                    "timestamp": datetime.now().isoformat()
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Symbol subscription failed for {client_id}: {e}")
            return False
    
    async def unsubscribe_events(self, client_id: str, event_types: List[str]) -> bool:
        """Unsubscribe client from event types"""
        try:
            async with self._lock:
                if client_id not in self.connections:
                    return False
                
                connection = self.connections[client_id]
                
                for event_type in event_types:
                    connection.subscribed_events.discard(event_type)
                    
                    if event_type in self.event_subscriptions:
                        self.event_subscriptions[event_type].discard(client_id)
                        if not self.event_subscriptions[event_type]:
                            del self.event_subscriptions[event_type]
                
                self.logger.info(f"Client {client_id} unsubscribed from events: {event_types}")
                
                # Send confirmation
                await self.send_message(client_id, {
                    "type": "subscription",
                    "action": "unsubscribed",
                    "target": "events",
                    "event_types": event_types,
                    "timestamp": datetime.now().isoformat()
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Event unsubscription failed for {client_id}: {e}")
            return False
    
    async def unsubscribe_symbols(self, client_id: str, symbols: List[str]) -> bool:
        """Unsubscribe client from symbols"""
        try:
            async with self._lock:
                if client_id not in self.connections:
                    return False
                
                connection = self.connections[client_id]
                
                for symbol in symbols:
                    symbol = symbol.upper()
                    connection.subscribed_symbols.discard(symbol)
                    
                    if symbol in self.symbol_subscriptions:
                        self.symbol_subscriptions[symbol].discard(client_id)
                        if not self.symbol_subscriptions[symbol]:
                            del self.symbol_subscriptions[symbol]
                
                self.logger.info(f"Client {client_id} unsubscribed from symbols: {symbols}")
                
                # Send confirmation
                await self.send_message(client_id, {
                    "type": "subscription",
                    "action": "unsubscribed",
                    "target": "symbols",
                    "symbols": symbols,
                    "timestamp": datetime.now().isoformat()
                })
                
                return True
                
        except Exception as e:
            self.logger.error(f"Symbol unsubscription failed for {client_id}: {e}")
            return False
    
    async def handle_message(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Handle incoming WebSocket message"""
        try:
            message_type = message.get("type")
            action = message.get("action")
            
            if message_type == "subscribe":
                if action == "events":
                    event_types = message.get("event_types", [])
                    return await self.subscribe_events(client_id, event_types)
                elif action == "symbols":
                    symbols = message.get("symbols", [])
                    return await self.subscribe_symbols(client_id, symbols)
            
            elif message_type == "unsubscribe":
                if action == "events":
                    event_types = message.get("event_types", [])
                    return await self.unsubscribe_events(client_id, event_types)
                elif action == "symbols":
                    symbols = message.get("symbols", [])
                    return await self.unsubscribe_symbols(client_id, symbols)
            
            elif message_type == "analyze":
                # Handle real-time analysis request
                return await self.handle_analysis_request(client_id, message)
            
            elif message_type == "ping":
                # Handle ping
                await self.send_message(client_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                })
                return True
            
            else:
                self.logger.warning(f"Unknown message type: {message_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Message handling failed for {client_id}: {e}")
            return False
    
    async def handle_analysis_request(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Handle real-time analysis request"""
        try:
            text = message.get("text")
            symbol = message.get("symbol", "UNKNOWN")
            agents = message.get("agents")
            
            if not text:
                await self.send_message(client_id, {
                    "type": "error",
                    "message": "Missing required field: text",
                    "request_id": message.get("request_id"),
                    "timestamp": datetime.now().isoformat()
                })
                return False
            
            # Send analysis started message
            request_id = message.get("request_id", f"req_{datetime.now().timestamp()}")
            
            await self.send_message(client_id, {
                "type": "analysis",
                "action": "started",
                "request_id": request_id,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            })
            
            # Run analysis in background
            asyncio.create_task(self.run_analysis_websocket(client_id, request_id, text, symbol, agents))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Analysis request handling failed for {client_id}: {e}")
            return False
    
    async def run_analysis_websocket(self, client_id: str, request_id: str, text: str, symbol: str, agents: Optional[List[str]]):
        """Run analysis and send updates via WebSocket"""
        try:
            # Run analysis
            result = await orchestrator.process_request(
                text=text,
                symbol=symbol,
                agent_filter=agents
            )
            
            # Send completion message
            await self.send_message(client_id, {
                "type": "analysis",
                "action": "completed",
                "request_id": request_id,
                "symbol": symbol,
                "result": {
                    "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                    "agent_results": result.agent_results,
                    "trading_signal": result.trading_signal.__dict__ if result.trading_signal else None,
                    "events_created": result.events_created,
                    "execution_time": result.execution_time,
                    "performance_target_met": result.performance_target_met
                },
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.logger.error(f"WebSocket analysis failed for {client_id}: {e}")
            
            # Send error message
            await self.send_message(client_id, {
                "type": "analysis",
                "action": "error",
                "request_id": request_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    async def start_background_tasks(self):
        """Start background tasks"""
        if self._running:
            return
        
        self._running = True
        
        # Start heartbeat task
        self._heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        
        # Start event streaming task
        self._event_stream_task = asyncio.create_task(self.event_stream_loop())
        
        self.logger.info("WebSocket background tasks started")
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        self._running = False
        
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        
        if self._event_stream_task:
            self._event_stream_task.cancel()
        
        self.logger.info("WebSocket background tasks stopped")
    
    async def heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while self._running:
            try:
                await asyncio.sleep(30)  # 30 second heartbeat
                
                current_time = asyncio.get_event_loop().time()
                dead_connections = []
                
                async with self._lock:
                    for client_id, connection in self.connections.items():
                        # Check if connection is stale (no ping for 90 seconds)
                        if current_time - connection.last_ping > 90:
                            dead_connections.append(client_id)
                        else:
                            # Send ping
                            try:
                                await connection.websocket.send_text(json.dumps({
                                    "type": "ping",
                                    "timestamp": datetime.now().isoformat()
                                }))
                            except Exception:
                                dead_connections.append(client_id)
                
                # Remove dead connections
                for client_id in dead_connections:
                    await self.disconnect(client_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat loop error: {e}")
    
    async def event_stream_loop(self):
        """Stream events from event fabric to subscribed clients"""
        while self._running:
            try:
                await asyncio.sleep(1)  # Check every second
                
                # Get recent events from event fabric
                # This is a simplified implementation
                # In production, you'd have a proper event streaming mechanism
                
                # For now, simulate event streaming
                await self.stream_system_metrics()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Event stream loop error: {e}")
    
    async def stream_system_metrics(self):
        """Stream system metrics to subscribed clients"""
        try:
            # Get system metrics
            orchestrator_status = await orchestrator.get_orchestrator_status()
            
            # Create metrics message
            metrics_message = {
                "type": "metrics",
                "data": {
                    "orchestrator": orchestrator_status,
                    "connections": len(self.connections),
                    "subscriptions": {
                        "events": len(self.event_subscriptions),
                        "symbols": len(self.symbol_subscriptions)
                    }
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to clients subscribed to system events
            if "system" in self.event_subscriptions:
                for client_id in self.event_subscriptions["system"]:
                    await self.send_message(client_id, metrics_message)
                    
        except Exception as e:
            self.logger.error(f"Metrics streaming failed: {e}")
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        async with self._lock:
            return {
                "total_connections": len(self.connections),
                "event_subscriptions": {
                    event_type: len(clients)
                    for event_type, clients in self.event_subscriptions.items()
                },
                "symbol_subscriptions": {
                    symbol: len(clients)
                    for symbol, clients in self.symbol_subscriptions.items()
                },
                "connections": [
                    {
                        "client_id": conn.client_id,
                        "subscribed_events": list(conn.subscribed_events),
                        "subscribed_symbols": list(conn.subscribed_symbols),
                        "last_ping": conn.last_ping,
                        "metadata": conn.metadata
                    }
                    for conn in self.connections.values()
                ]
            }


# Global WebSocket manager
websocket_manager = WebSocketManager()

# WebSocket endpoint handlers
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """Main WebSocket endpoint"""
    if not client_id:
        client_id = f"client_{datetime.now().timestamp()}"
    
    # Accept connection
    connected = await websocket_manager.connect(websocket, client_id)
    if not connected:
        return
    
    try:
        # Start background tasks if not already running
        await websocket_manager.start_background_tasks()
        
        # Message loop
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await websocket_manager.handle_message(client_id, message)
            except json.JSONDecodeError:
                await websocket_manager.send_message(client_id, {
                    "type": "error",
                    "message": "Invalid JSON",
                    "timestamp": datetime.now().isoformat()
                })
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        await websocket_manager.disconnect(client_id)

# FastAPI WebSocket route
from fastapi import FastAPI

def add_websocket_routes(app: FastAPI):
    """Add WebSocket routes to FastAPI app"""
    
    @app.websocket("/ws/{client_id}")
    async def websocket_handler(websocket: WebSocket, client_id: str):
        await websocket_endpoint(websocket, client_id)
    
    @app.websocket("/ws")
    async def websocket_handler_anonymous(websocket: WebSocket):
        await websocket_endpoint(websocket)
    
    @app.get("/ws/stats")
    async def get_websocket_stats():
        """Get WebSocket statistics"""
        return await websocket_manager.get_connection_stats()

# Export for use in main app
__all__ = ["websocket_manager", "add_websocket_routes", "websocket_endpoint"]
