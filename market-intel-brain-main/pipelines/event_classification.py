"""
MAIFA v3 Event Classification Pipeline - Stage 2 of the 5-stage workflow
Classifies events and determines processing routing
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from models.schemas import FinancialEvent, Priority
from models.datatypes import PipelineResult
from services.classifier import classifier_service

class EventClassificationPipeline:
    """
    MAIFA v3 Event Classification Pipeline - Event type identification and routing
    
    Handles:
    - Event type classification
    - Priority assignment
    - Routing determination
    - Relevance scoring
    - Event metadata enrichment
    """
    
    def __init__(self):
        self.logger = logging.getLogger("EventClassificationPipeline")
        self._routing_rules = self._initialize_routing_rules()
        self._event_templates = self._initialize_event_templates()
        self._classification_cache = {}
        
    def _initialize_routing_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize event routing rules"""
        return {
            "price_movement": {
                "required_agents": ["sentiment_agent", "hunter_agent"],
                "priority_boost": 0.2,
                "processing_pipeline": "standard",
                "requires_real_time": True
            },
            "news_event": {
                "required_agents": ["sentiment_agent", "hunter_agent"],
                "priority_boost": 0.1,
                "processing_pipeline": "standard",
                "requires_real_time": False
            },
            "trading_signal": {
                "required_agents": ["sentiment_agent"],
                "priority_boost": 0.3,
                "processing_pipeline": "urgent",
                "requires_real_time": True
            },
            "earnings_report": {
                "required_agents": ["sentiment_agent", "hunter_agent"],
                "priority_boost": 0.4,
                "processing_pipeline": "comprehensive",
                "requires_real_time": True
            },
            "economic_indicator": {
                "required_agents": ["sentiment_agent"],
                "priority_boost": 0.2,
                "processing_pipeline": "standard",
                "requires_real_time": True
            },
            "market_sentiment": {
                "required_agents": ["sentiment_agent"],
                "priority_boost": 0.1,
                "processing_pipeline": "standard",
                "requires_real_time": False
            },
            "regulatory_change": {
                "required_agents": ["sentiment_agent", "hunter_agent"],
                "priority_boost": 0.5,
                "processing_pipeline": "urgent",
                "requires_real_time": True
            },
            "technical_analysis": {
                "required_agents": ["hunter_agent"],
                "priority_boost": 0.0,
                "processing_pipeline": "standard",
                "requires_real_time": False
            },
            "company_specific": {
                "required_agents": ["sentiment_agent", "hunter_agent"],
                "priority_boost": 0.2,
                "processing_pipeline": "standard",
                "requires_real_time": False
            },
            "macro_economic": {
                "required_agents": ["sentiment_agent"],
                "priority_boost": 0.1,
                "processing_pipeline": "standard",
                "requires_real_time": False
            }
        }
    
    def _initialize_event_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize event templates for metadata enrichment"""
        return {
            "price_movement": {
                "data_schema": ["symbol", "price_change", "volume", "timestamp"],
                "required_fields": ["symbol", "price_change"],
                "default_priority": Priority.MEDIUM
            },
            "news_event": {
                "data_schema": ["symbol", "headline", "source", "sentiment_indicators"],
                "required_fields": ["headline"],
                "default_priority": Priority.MEDIUM
            },
            "trading_signal": {
                "data_schema": ["symbol", "signal_type", "confidence", "source"],
                "required_fields": ["symbol", "signal_type"],
                "default_priority": Priority.HIGH
            },
            "earnings_report": {
                "data_schema": ["symbol", "eps", "revenue", "guidance", "beat_miss"],
                "required_fields": ["symbol", "eps"],
                "default_priority": Priority.HIGH
            }
        }
    
    async def process(self, 
                    processed_input: Dict[str, Any],
                    preprocessing_result: Optional[Dict[str, Any]] = None) -> PipelineResult:
        """
        Main event classification pipeline
        
        Args:
            processed_input: Preprocessed input data
            preprocessing_result: Results from preprocessing stage
            
        Returns:
            Event classification results
        """
        try:
            self.logger.debug("Starting event classification pipeline")
            
            # Extract data
            text = processed_input.get("text", "")
            symbol = processed_input.get("symbol", "UNKNOWN")
            metadata = processed_input.get("metadata", {})
            
            # Step 1: Classify event type
            event_classification = await classifier_service.classify_event(text, metadata)
            
            # Step 2: Classify data category
            data_classification = await classifier_service.classify_data(
                {"text": text, "symbol": symbol},
                "event_classification"
            )
            
            # Step 3: Assign priority
            priority = await classifier_service.assign_priority(event_classification, text, metadata)
            
            # Step 4: Calculate relevance
            relevance_keywords = metadata.get("keywords", ["market", "stock", "trading"])
            relevance_score = await classifier_service.calculate_relevance(
                text, [symbol], relevance_keywords
            )
            
            # Step 5: Determine routing
            routing_info = await self._determine_routing(event_classification, priority)
            
            # Step 6: Create financial event
            financial_event = await self._create_financial_event(
                event_classification, text, symbol, priority, metadata
            )
            
            # Step 7: Enrich metadata
            enriched_metadata = await self._enrich_metadata(
                metadata, event_classification, data_classification, priority, relevance_score
            )
            
            # Step 8: Create classification result
            classification_result = {
                "status": "completed",
                "event_classification": event_classification,
                "data_classification": data_classification,
                "assigned_priority": priority.value,
                "relevance_score": relevance_score,
                "routing_info": routing_info,
                "financial_event": financial_event,
                "enriched_metadata": enriched_metadata,
                "processing_stats": {
                    "classification_confidence": event_classification.get("primary_event", {}).get("confidence", 0.0),
                    "data_confidence": data_classification.get("primary_category", {}).get("confidence", 0.0),
                    "processing_timestamp": datetime.now().isoformat()
                }
            }
            
            self.logger.debug(f"Event classification completed: {event_classification.get('primary_event', {}).get('event_type', 'unknown')}")
            return classification_result
            
        except Exception as e:
            self.logger.error(f"Event classification pipeline failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "stage": "classification"
            }
    
    async def _determine_routing(self, 
                                event_classification: Dict[str, Any],
                                priority: Priority) -> Dict[str, Any]:
        """Determine processing routing based on classification"""
        try:
            primary_event_type = event_classification.get("primary_event", {}).get("event_type", "news_event")
            
            # Get routing rules for this event type
            routing_rule = self._routing_rules.get(primary_event_type, self._routing_rules["news_event"])
            
            # Determine required agents
            required_agents = routing_rule["required_agents"]
            
            # Apply priority boost
            base_priority = priority
            priority_boost = routing_rule["priority_boost"]
            
            # Calculate final priority
            if priority_boost >= 0.4:
                final_priority = Priority.CRITICAL
            elif priority_boost >= 0.2:
                final_priority = Priority.HIGH
            elif priority_boost <= -0.1:
                final_priority = Priority.LOW
            else:
                final_priority = Priority.MEDIUM
            
            # Determine processing pipeline
            processing_pipeline = routing_rule["processing_pipeline"]
            
            # Check if real-time processing is required
            requires_real_time = routing_rule["requires_real_time"]
            
            return {
                "required_agents": required_agents,
                "base_priority": base_priority.value,
                "priority_boost": priority_boost,
                "final_priority": final_priority.value,
                "processing_pipeline": processing_pipeline,
                "requires_real_time": requires_real_time,
                "estimated_processing_time": self._estimate_processing_time(processing_pipeline, required_agents)
            }
            
        except Exception as e:
            self.logger.error(f"Routing determination failed: {e}")
            return {
                "required_agents": ["sentiment_agent"],
                "final_priority": Priority.MEDIUM.value,
                "processing_pipeline": "standard",
                "requires_real_time": False
            }
    
    def _estimate_processing_time(self, 
                                  processing_pipeline: str,
                                  required_agents: List[str]) -> float:
        """Estimate processing time in seconds"""
        base_times = {
            "standard": 2.0,
            "urgent": 1.0,
            "comprehensive": 4.0
        }
        
        base_time = base_times.get(processing_pipeline, 2.0)
        agent_time = len(required_agents) * 0.5
        
        return base_time + agent_time
    
    async def _create_financial_event(self, 
                                     event_classification: Dict[str, Any],
                                     text: str,
                                     symbol: str,
                                     priority: Priority,
                                     metadata: Dict[str, Any]) -> FinancialEvent:
        """Create a financial event from classification results"""
        try:
            primary_event_type = event_classification.get("primary_event", {}).get("event_type", "news_event")
            confidence = event_classification.get("primary_event", {}).get("confidence", 0.0)
            
            # Prepare event data
            event_data = {
                "text": text[:500],  # Truncate text for storage
                "classification_confidence": confidence,
                "source": metadata.get("source", "unknown"),
                "original_metadata": metadata
            }
            
            # Add event-type specific data
            if primary_event_type == "price_movement":
                # Extract price-related information
                import re
                price_changes = re.findall(r'([+-]?\d+\.?\d*%)', text)
                if price_changes:
                    event_data["price_changes"] = price_changes
            
            elif primary_event_type == "trading_signal":
                # Extract signal information
                signals = re.findall(r'(buy|sell|hold)', text, re.IGNORECASE)
                if signals:
                    event_data["signals"] = [s.lower() for s in signals]
            
            elif primary_event_type == "earnings_report":
                # Extract earnings information
                eps_values = re.findall(r'eps[^:]*:?\s*([+-]?\d+\.?\d*)', text, re.IGNORECASE)
                if eps_values:
                    event_data["eps_values"] = eps_values
            
            # Create the financial event
            financial_event = FinancialEvent(
                event_type=primary_event_type,
                symbol=symbol,
                data=event_data,
                priority=priority,
                timestamp=datetime.now()
            )
            
            return financial_event
            
        except Exception as e:
            self.logger.error(f"Financial event creation failed: {e}")
            # Return a basic event on error
            return FinancialEvent(
                event_type="news_event",
                symbol=symbol,
                data={"text": text[:200], "error": str(e)},
                priority=Priority.MEDIUM,
                timestamp=datetime.now()
            )
    
    async def _enrich_metadata(self, 
                              original_metadata: Dict[str, Any],
                              event_classification: Dict[str, Any],
                              data_classification: Dict[str, Any],
                              priority: Priority,
                              relevance_score: float) -> Dict[str, Any]:
        """Enrich metadata with classification results"""
        try:
            enriched_metadata = original_metadata.copy()
            
            # Add classification metadata
            enriched_metadata.update({
                "event_classification": {
                    "primary_event": event_classification.get("primary_event", {}).get("event_type"),
                    "confidence": event_classification.get("primary_event", {}).get("confidence"),
                    "secondary_events": event_classification.get("secondary_events", [])
                },
                "data_classification": {
                    "primary_category": data_classification.get("primary_category", {}).get("category"),
                    "confidence": data_classification.get("primary_category", {}).get("confidence")
                },
                "processing_metadata": {
                    "assigned_priority": priority.value,
                    "relevance_score": relevance_score,
                    "classification_timestamp": datetime.now().isoformat()
                }
            })
            
            # Add quality indicators
            classification_quality = (
                event_classification.get("primary_event", {}).get("confidence", 0.0) *
                data_classification.get("primary_category", {}).get("confidence", 0.0)
            )
            
            enriched_metadata["quality_indicators"] = {
                "classification_quality": classification_quality,
                "data_relevance": relevance_score,
                "overall_quality": (classification_quality + relevance_score) / 2
            }
            
            return enriched_metadata
            
        except Exception as e:
            self.logger.error(f"Metadata enrichment failed: {e}")
            return original_metadata
    
    async def batch_classify(self, 
                            processed_inputs: List[Dict[str, Any]],
                            preprocessing_results: Optional[List[Dict[str, Any]]] = None) -> List[PipelineResult]:
        """Classify multiple events in parallel"""
        if preprocessing_results is None:
            preprocessing_results = [None] * len(processed_inputs)
        elif len(preprocessing_results) != len(processed_inputs):
            preprocessing_results = [None] * len(processed_inputs)
        
        tasks = [
            self.process(processed_input, preprocessing_result)
            for processed_input, preprocessing_result in zip(processed_inputs, preprocessing_results)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Batch classification error: {result}")
                valid_results.append({
                    "status": "failed",
                    "error": str(result),
                    "stage": "batch_classification"
                })
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def get_classification_stats(self) -> Dict[str, Any]:
        """Get event classification pipeline statistics"""
        return {
            "routing_rules_count": len(self._routing_rules),
            "event_templates_count": len(self._event_templates),
            "cache_size": len(self._classification_cache),
            "available_event_types": list(self._routing_rules.keys()),
            "processing_pipelines": ["standard", "urgent", "comprehensive"],
            "priority_levels": [p.value for p in Priority]
        }


# Global event classification pipeline instance
event_classification_pipeline = EventClassificationPipeline()
