"""
MAIFA v3 Event Fabric - Async dispatch, fan-out/fan-in, priority routing
Handles event streaming and distribution across the system
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid
from collections import defaultdict
import heapq

from models.schemas import FinancialEvent, Priority
from models.datatypes import EventStream, EventHandler, AsyncEventHandler, EventFilter

class EventSubscription:
    """Represents a subscription to events"""
    
    def __init__(self, 
                 subscriber_id: str,
                 event_types: List[str],
                 filter_func: Optional[EventFilter] = None,
                 handler: Optional[AsyncEventHandler] = None):
        self.subscriber_id = subscriber_id
        self.event_types = set(event_types)
        self.filter_func = filter_func
        self.handler = handler
        self.created_at = datetime.now()
        self.events_received = 0

class EventFabric:
    """
    MAIFA v3 Event Fabric - High-performance async event distribution
    
    Provides fan-out/fan-in capabilities with priority routing and
    efficient event streaming across all system components.
    """
    
    def __init__(self, max_queue_size: int = 10000):
        self.logger = logging.getLogger("EventFabric")
        self._event_queue: List[tuple] = []  # Priority queue
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._event_handlers: Dict[str, List[AsyncEventHandler]] = defaultdict(list)
        self._max_queue_size = max_queue_size
        self._queue_lock = asyncio.Lock()
        self._subscriptions_lock = asyncio.Lock()
        self._running = False
        self._dispatcher_task = None
        
        # Performance metrics
        self._events_published = 0
        self._events_delivered = 0
        self._events_dropped = 0
        self._delivery_failures = 0
        
    async def start_streaming(self):
        """Start the event streaming dispatcher"""
        if self._running:
            self.logger.warning("Event fabric already running")
            return
        
        self._running = True
        self._dispatcher_task = asyncio.create_task(self._dispatch_events())
        self.logger.info("Event fabric streaming started")
    
    async def stop_streaming(self):
        """Stop the event streaming dispatcher"""
        self._running = False
        if self._dispatcher_task:
            self._dispatcher_task.cancel()
            try:
                await self._dispatcher_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Event fabric streaming stopped")
    
    async def publish_event(self, event: FinancialEvent) -> bool:
        """
        Publish an event to the fabric
        
        Args:
            event: Financial event to publish
            
        Returns:
            True if published successfully
        """
        try:
            async with self._queue_lock:
                # Check queue size
                if len(self._event_queue) >= self._max_queue_size:
                    # Drop oldest low-priority events
                    await self._drop_low_priority_events()
                
                # Add to priority queue (negative priority for max-heap behavior)
                priority_value = -event.priority.value
                heapq.heappush(self._event_queue, (priority_value, event.timestamp, event))
                
                self._events_published += 1
                self.logger.debug(f"Event published: {event.event_id} (type: {event.event_type})")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to publish event {event.event_id}: {e}")
            return False
    
    async def subscribe(self, 
                       subscriber_id: str,
                       event_types: List[str],
                       filter_func: Optional[EventFilter] = None,
                       handler: Optional[AsyncEventHandler] = None) -> bool:
        """
        Subscribe to specific event types
        
        Args:
            subscriber_id: Unique subscriber identifier
            event_types: List of event types to subscribe to
            filter_func: Optional filter function
            handler: Optional async event handler
            
        Returns:
            True if subscription successful
        """
        try:
            async with self._subscriptions_lock:
                subscription = EventSubscription(
                    subscriber_id=subscriber_id,
                    event_types=event_types,
                    filter_func=filter_func,
                    handler=handler
                )
                
                self._subscriptions[subscriber_id] = subscription
                
                # Register handlers for each event type
                for event_type in event_types:
                    if handler:
                        self._event_handlers[event_type].append(handler)
                
                self.logger.info(f"Subscription created: {subscriber_id} for {event_types}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create subscription for {subscriber_id}: {e}")
            return False
    
    async def unsubscribe(self, subscriber_id: str) -> bool:
        """Unsubscribe from events"""
        try:
            async with self._subscriptions_lock:
                if subscriber_id in self._subscriptions:
                    subscription = self._subscriptions[subscriber_id]
                    
                    # Remove handlers
                    for event_type in subscription.event_types:
                        if subscription.handler:
                            handlers = self._event_handlers[event_type]
                            if subscription.handler in handlers:
                                handlers.remove(subscription.handler)
                    
                    del self._subscriptions[subscriber_id]
                    self.logger.info(f"Subscription removed: {subscriber_id}")
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove subscription for {subscriber_id}: {e}")
            return False
    
    async def _dispatch_events(self):
        """Main event dispatcher loop"""
        while self._running:
            try:
                # Get next event from queue
                event = await self._get_next_event()
                if not event:
                    await asyncio.sleep(0.01)  # Small delay if no events
                    continue
                
                # Dispatch to subscribers
                await self._dispatch_to_subscribers(event)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Event dispatch error: {e}")
                await asyncio.sleep(0.1)  # Brief pause on error
    
    async def _get_next_event(self) -> Optional[FinancialEvent]:
        """Get next event from priority queue"""
        async with self._queue_lock:
            if self._event_queue:
                _, _, event = heapq.heappop(self._event_queue)
                return event
            return None
    
    async def _dispatch_to_subscribers(self, event: FinancialEvent):
        """Dispatch event to all matching subscribers"""
        delivered_count = 0
        
        async with self._subscriptions_lock:
            matching_subscriptions = [
                sub for sub in self._subscriptions.values()
                if event.event_type in sub.event_types
                and (not sub.filter_func or sub.filter_func(event.__dict__))
            ]
        
        # Dispatch to all matching subscriptions
        tasks = []
        for subscription in matching_subscriptions:
            if subscription.handler:
                task = asyncio.create_task(
                    self._safe_handle_event(subscription, event)
                )
                tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful deliveries
            for result in results:
                if not isinstance(result, Exception):
                    delivered_count += 1
                else:
                    self._delivery_failures += 1
        
        self._events_delivered += delivered_count
        
        if delivered_count > 0:
            self.logger.debug(f"Event {event.event_id} delivered to {delivered_count} subscribers")
    
    async def _safe_handle_event(self, 
                                subscription: EventSubscription, 
                                event: FinancialEvent):
        """Safely handle event for a subscription"""
        try:
            await subscription.handler(event)
            subscription.events_received += 1
        except Exception as e:
            self.logger.error(f"Event handler failed for {subscription.subscriber_id}: {e}")
            self._delivery_failures += 1
    
    async def _drop_low_priority_events(self, count: int = 100):
        """Drop low priority events to make space"""
        dropped = 0
        
        # Separate events by priority
        high_priority = []
        low_priority = []
        
        while self._event_queue and dropped < count:
            priority, timestamp, event = heapq.heappop(self._event_queue)
            
            # Keep high priority events (CRITICAL, HIGH)
            if priority >= -3:  # Priority.HIGH.value = 3
                high_priority.append((priority, timestamp, event))
            else:
                low_priority.append((priority, timestamp, event))
                dropped += 1
                self._events_dropped += 1
        
        # Put high priority events back
        for item in high_priority:
            heapq.heappush(self._event_queue, item)
        
        self.logger.debug(f"Dropped {dropped} low priority events")
    
    async def create_market_event(self, 
                                event_type: str,
                                symbol: str,
                                data: Dict[str, Any],
                                priority: Priority = Priority.MEDIUM) -> FinancialEvent:
        """
        Create and publish a market event
        
        Args:
            event_type: Type of event
            symbol: Financial symbol
            data: Event data
            priority: Event priority
            
        Returns:
            Created event
        """
        event = FinancialEvent(
            event_type=event_type,
            symbol=symbol,
            data=data,
            priority=priority
        )
        
        await self.publish_event(event)
        return event
    
    async def create_sentiment_event(self, 
                                   symbol: str,
                                   sentiment: str,
                                   polarity: float,
                                   source_text: str,
                                   priority: Priority = Priority.MEDIUM) -> FinancialEvent:
        """Create a sentiment-related event"""
        return await self.create_market_event(
            event_type="sentiment_shift",
            symbol=symbol,
            data={
                "sentiment": sentiment,
                "polarity": polarity,
                "source_text": source_text[:100]
            },
            priority=priority
        )
    
    async def create_keyword_event(self,
                                 symbol: str,
                                 keywords: List[str],
                                 count: int,
                                 source_text: str,
                                 priority: Priority = Priority.MEDIUM) -> FinancialEvent:
        """Create a keyword spike event"""
        return await self.create_market_event(
            event_type="keyword_spike",
            symbol=symbol,
            data={
                "keywords": keywords,
                "count": count,
                "source_text": source_text[:100]
            },
            priority=priority
        )
    
    async def get_event_stats(self) -> Dict[str, Any]:
        """Get event fabric performance statistics"""
        return {
            "events_published": self._events_published,
            "events_delivered": self._events_delivered,
            "events_dropped": self._events_dropped,
            "delivery_failures": self._delivery_failures,
            "queue_size": len(self._event_queue),
            "max_queue_size": self._max_queue_size,
            "active_subscriptions": len(self._subscriptions),
            "event_handlers": {
                event_type: len(handlers)
                for event_type, handlers in self._event_handlers.items()
            },
            "delivery_rate": self._events_delivered / max(1, self._events_published) * 100
        }
    
    async def get_subscription_info(self, subscriber_id: Optional[str] = None) -> Dict[str, Any]:
        """Get subscription information"""
        if subscriber_id:
            subscription = self._subscriptions.get(subscriber_id)
            return asdict(subscription) if subscription else {}
        else:
            return {
                "total_subscriptions": len(self._subscriptions),
                "subscriptions": {
                    sub_id: {
                        "event_types": list(sub.event_types),
                        "events_received": sub.events_received,
                        "created_at": sub.created_at.isoformat()
                    }
                    for sub_id, sub in self._subscriptions.items()
                }
            }
    
    async def replay_events(self, 
                          event_type: str,
                          count: int = 100,
                          time_range: Optional[tuple] = None) -> List[FinancialEvent]:
        """
        Replay events (simplified implementation)
        
        Args:
            event_type: Type of events to replay
            count: Maximum number of events to replay
            time_range: Optional (start_time, end_time) tuple
            
        Returns:
            List of replayed events
        """
        # This is a simplified implementation
        # In production, you'd have persistent event storage
        self.logger.info(f"Event replay requested for {event_type}")
        return []


# Global event fabric instance
event_fabric = EventFabric()
