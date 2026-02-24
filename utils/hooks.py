"""
MessagePack Hooks for Binary Serialization

This module provides custom hooks for MessagePack serialization
with special handling for decimal, datetime, and UUID types.
"""

import uuid
import time
import logging
from typing import Any, Dict, Any, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from .exceptions import ValidationError


@dataclass
class HookContext:
    """Context passed to hooks."""
    request_id: str
    adapter_name: str
    operation: str
    data: Any
    metadata: Dict[str, Any]


class BaseHook(ABC):
    """Abstract base class for MessagePack hooks."""
    
    @abstractmethod
    async def before_serialize(
        self,
        context: HookContext
    ) -> Dict[str, Any]:
        """Called before serialization."""
        pass
    
    @abstractmethod
    async def after_serialize(
        self,
        context: HookContext,
        serialized_data: bytes,
        original_data: Any
    ) -> Dict[str, Any]:
        """Called after serialization."""
        pass


@dataclass
class DecimalHook(BaseHook):
    """Hook for handling Decimal serialization."""
    
    async def before_serialize(
        self,
        context: HookContext
    ) -> Dict[str, Any]:
        """Handle Decimal before serialization."""
        if isinstance(context.data, Decimal):
            # Log decimal precision and context
            self.logger.debug(
                f"Serializing Decimal {context.field_name}: {context.data} "
                f"(precision: {context.data.as_tuple()})"
            )
            
            # Convert to string for MessagePack
            context.data = str(context.data)
        
        return {"status": "continue"}
    
    async def after_serialize(
        self,
        context: HookContext,
        serialized_data: bytes,
        original_data: Any
    ) -> Dict[str, Any]:
        """Handle Decimal after serialization."""
        # Restore original Decimal from string
        try:
            restored_data = Decimal(context.data)
            
            if context.original_data != restored_data:
                self.logger.warning(
                    f"Decimal precision change detected for {context.field_name}: "
                    f"{context.original_value} -> {restored_data}"
                )
            
            return {
                "status": "precision_changed",
                "original_value": context.original_value,
                "restored_value": restored_data,
                "precision_change": abs(context.original_value - restored_data) > 0.00001
            }
        
        return {"status": "success"}


@dataclass
class DatetimeHook(BaseHook):
    """Hook for handling datetime serialization."""
    
    async def before_serialize(
        self,
        context: HookContext
    ) -> Dict[str, Any]:
        """Handle datetime before serialization."""
        if isinstance(context.data, datetime):
            # Format datetime for MessagePack
            context.data = context.data.isoformat()
            
            self.logger.debug(
                f"Serializing datetime {context.field_name}: {context.data} "
                f"(format: {context.data})"
            )
        
        return {"status": "continue"}
    
    async def after_serialize(
        self,
        context: HookContext,
        serialized_data: bytes,
        original_data: Any
    ) -> Dict[str, Any]:
        """Handle datetime after serialization."""
        # Restore original datetime from string
        try:
            restored_data = datetime.fromisoformat(context.data)
            
            if context.original_data != restored_data:
                self.logger.warning(
                    f"Datetime precision change detected for {context.field_name}: "
                    f"{context.original_value} -> {restored_data}"
                )
            
            return {
                "status": "precision_changed",
                "original_value": context.original_value,
                "restored_value": restored_data,
                "time_change": (restored_data - context.original_value).total_seconds()
            }
        
        return {"status": "success"}


@dataclass
class UUIDHook(BaseHook):
    """Hook for UUID serialization."""
    
    async def before_serialize(
        self,
        context: HookContext
    ) -> Log UUID before serialization.
        """
        if isinstance(context.data, uuid.UUID):
            self.logger.debug(
                f"Serializing UUID {context.field_name}: {context.data}"
            )
        
        return {"status": "continue"}
    
    async def after_serialize(
        self,
        context: context,
        serialized_data: bytes,
        original_data: Any
    ) -> Dict[str, Any]:
        """Handle UUID after serialization."""
        # Restore original UUID from string
        try:
            restored_uuid = uuid.UUID(context.data)
            
            if context.original_uuid != restored_uuid:
                self.logger.warning(
                    f"UUID change detected for {context.field_name}: "
                    f"{context.original_uuid} -> {restored_uuid}"
                )
            
            return {
                "status": "uuid_changed",
                "original_uuid": context.original_uuid,
                "restored_uuid": restored_uuid,
                "uuid_change": (restored_uuid - context.original_uuid)
            }
        
        return {"status": "success"}


class MessagePackHooks:
    """Registry for MessagePack hooks."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("MessagePackHooks")
        self._hooks = {
            'decimal': [],
            'datetime': [],
            'uuid': []
        }
    
    def register_hook(self, hook_type: str, hook_class: BaseHook):
        """Register a hook for a specific type."""
        if not issubclass(hook_class, BaseHook):
            raise ValidationError(
                f"Hook class {hook_class.__name__} is not a BaseHook subclass"
            )
        
        self._hooks[hook_type].append(hook_class())
        self.logger.info(f"Registered {hook_type} hook: {hook_class.__name__}")
    
    def get_hooks(self, hook_type: str) -> List[BaseHook]:
        """Get all hooks of a specific type."""
        return self._hooks.get(hook_type, [])
    
    def get_all_hooks(self) -> Dict[str, List[BaseHook]]:
        """Get all registered hooks."""
        return self._hooks.copy()
    
    async def call_before_hooks(
        self,
        hook_type: str,
        context: HookContext
    ) -> Dict[str, Any]:
        """Call all before hooks of a type."""
        results = []
        
        for hook in self.get_hooks(hook_type):
            try:
                result = await hook.before_serialize(context)
                results.append(result)
            except Exception as e:
                    self.logger.error(f"Hook error in {hook_type} hook: {e}")
                    results.append({"status": "error", "error": str(e)})
        
        return results
    
    async def call_after_hooks(
        self,
        hook_type: str,
        context: HookContext,
        serialized_data: bytes,
        original_data: Any
    ) -> Dict[str, Any]:
        """Call all after hooks of a type."""
        results = []
        
        for hook in self.get_hooks(hook_type):
            try:
                result = await hook.after_serialize(context, serialized_data, original_data)
                results.append(result)
            except Exception as e:
                    self.logger.error(f"Hook error in {hook_type} hook: {e}")
                    results.append({"status": "error", "error": str(e)})
        
        return results


# Global hooks registry
_global_hooks: Optional[MessagePackHooks] = None


def get_hooks(**kwargs) -> MessagePackHooks:
    """Get or create the global hooks registry."""
    global _global_hooks
    if _global_hooks is None:
        _global_hooks = MessagePackHooks(**kwargs)
    return _global_hooks


def register_hook(hook_type: str, hook_class: type, **kwargs):
    """
    Register a hook using global registry.
    
    Args:
        hook_type: Type of hook
        hook_class: Hook class to register
        **kwargs: Additional arguments for hook class
    """
    global_hooks = get_hooks()
    global_hooks.register_hook(hook_type, hook_class)
    print(f"Registered {hook_type} hook: {hook_class.__name__}")


# Built-in hooks
register_hook('decimal', DecimalHook)
register_hook('datetime', DatetimeHook)
register_hook('uuid', UUIDHook)


# Convenience function for global usage
async def call_hooks_before(hook_type: str, context: HookContext):
    """Call all before hooks of a type using global registry."""
    global_hooks = get_hooks()
    return await global_hooks.call_before(hook_type, context)


async def call_hooks_after(
    hook_type: str,
    context: HookContext,
    serialized_data: bytes,
    original_data: Any
) -> List[Dict[str, Any]]:
    """Call all after hooks of a type using global registry."""
    global_hooks = get_hooks()
    return await global_hooks.call_after(hook_type, context, serialized_data, original_data)


# Legacy exports for backward compatibility
from .legacy_serializer import (
    LegacySerializer,
    get_legacy_serializer
    get_legacy_hooks
)
