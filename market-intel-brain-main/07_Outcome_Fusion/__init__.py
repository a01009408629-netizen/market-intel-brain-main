"""
07_Outcome_Fusion: Merging data from 50+ sources into one "Trading Insight" or "Report"
Advanced data fusion and insight generation system
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics
from collections import defaultdict

class ConfidenceLevel(Enum):
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WATCH = "WATCH"
    ALERT = "ALERT"

@dataclass
class DataSource:
    source_id: str
    source_type: str  # "agent", "api", "news", "technical", "fundamental"
    weight: float = 1.0
    reliability: float = 1.0
    last_update: datetime = field(default_factory=datetime.now)

@dataclass
class FusedSignal:
    symbol: str
    signal_type: SignalType
    confidence: float
    price_target: Optional[float] = None
    time_horizon: str = "short_term"  # short_term, medium_term, long_term
    sources: List[str] = field(default_factory=list)
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class TradingInsight:
    symbol: str
    overall_signal: SignalType
    confidence_score: float
    price_targets: Dict[str, float] = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    supporting_data: Dict[str, Any] = field(default_factory=dict)
    conflicting_signals: List[str] = field(default_factory=list)
    recommendation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

class DataFusionEngine:
    """Advanced data fusion engine for 50+ sources"""
    
    def __init__(self):
        self.data_sources: Dict[str, DataSource] = {}
        self.signal_buffer: List[Dict[str, Any]] = []
        self.fusion_weights = {
            "technical_analysis": 0.25,
            "sentiment_analysis": 0.20,
            "fundamental_analysis": 0.20,
            "news_analysis": 0.15,
            "market_data": 0.10,
            "risk_analysis": 0.10
        }
        self.confidence_thresholds = {
            "buy": 0.7,
            "sell": 0.7,
            "hold": 0.5
        }
        
    def register_data_source(self, source: DataSource):
        """Register a new data source"""
        self.data_sources[source.source_id] = source
        
    async def ingest_signals(self, signals: List[Dict[str, Any]]):
        """Ingest signals from multiple sources"""
        for signal in signals:
            signal["ingestion_time"] = datetime.now()
            self.signal_buffer.append(signal)
            
        # Keep buffer size manageable
        if len(self.signal_buffer) > 10000:
            self.signal_buffer = self.signal_buffer[-5000:]
            
    async def fuse_signals(self, symbol: str, time_window_minutes: int = 5) -> FusedSignal:
        """Fuse signals for a specific symbol"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        # Filter relevant signals
        relevant_signals = [
            signal for signal in self.signal_buffer
            if (signal.get("symbol") == symbol and 
                signal.get("ingestion_time") > cutoff_time)
        ]
        
        if not relevant_signals:
            return FusedSignal(
                symbol=symbol,
                signal_type=SignalType.WATCH,
                confidence=0.1,
                reasoning="No recent signals available"
            )
            
        # Analyze signal patterns
        signal_analysis = self._analyze_signals(relevant_signals)
        
        # Generate fused signal
        fused_signal = await self._generate_fused_signal(symbol, signal_analysis)
        
        return fused_signal
        
    def _analyze_signals(self, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze signal patterns and correlations"""
        analysis = {
            "signal_counts": defaultdict(int),
            "source_weights": defaultdict(float),
            "confidences": [],
            "signal_types": [],
            "price_targets": [],
            "sentiment_scores": [],
            "technical_indicators": []
        }
        
        total_weight = 0.0
        
        for signal in signals:
            source_id = signal.get("source_id", "unknown")
            source_type = signal.get("source_type", "unknown")
            
            # Count signal types
            signal_type = signal.get("signal_type", "HOLD")
            analysis["signal_counts"][signal_type] += 1
            analysis["signal_types"].append(signal_type)
            
            # Collect confidences
            if "confidence" in signal:
                analysis["confidences"].append(signal["confidence"])
                
            # Collect price targets
            if "price_target" in signal:
                analysis["price_targets"].append(signal["price_target"])
                
            # Collect sentiment scores
            if "sentiment_score" in signal:
                analysis["sentiment_scores"].append(signal["sentiment_score"])
                
            # Apply source weighting
            if source_id in self.data_sources:
                source = self.data_sources[source_id]
                weight = source.weight * source.reliability
                analysis["source_weights"][source_type] += weight
                total_weight += weight
                
        # Normalize weights
        if total_weight > 0:
            for source_type in analysis["source_weights"]:
                analysis["source_weights"][source_type] /= total_weight
                
        return analysis
        
    async def _generate_fused_signal(self, symbol: str, analysis: Dict[str, Any]) -> FusedSignal:
        """Generate fused signal from analysis"""
        signal_counts = analysis["signal_counts"]
        source_weights = analysis["source_weights"]
        confidences = analysis["confidences"]
        
        # Determine dominant signal type
        if not signal_counts:
            return FusedSignal(symbol=symbol, signal_type=SignalType.WATCH, confidence=0.1)
            
        # Weighted signal voting
        weighted_votes = defaultdict(float)
        for signal_type, count in signal_counts.items():
            source_type_weight = source_weights.get(signal_type, 0.1)
            weighted_votes[signal_type] += count * source_type_weight
            
        # Find dominant signal
        dominant_signal = max(weighted_votes.keys(), key=lambda x: weighted_votes[x])
        
        # Calculate confidence
        confidence = self._calculate_confidence(analysis, dominant_signal)
        
        # Determine signal type enum
        signal_type_map = {
            "BUY": SignalType.BUY,
            "SELL": SignalType.SELL,
            "HOLD": SignalType.HOLD,
            "WATCH": SignalType.WATCH,
            "ALERT": SignalType.ALERT
        }
        
        signal_type = signal_type_map.get(dominant_signal, SignalType.WATCH)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(analysis, dominant_signal, confidence)
        
        # Calculate price target if available
        price_target = None
        if analysis["price_targets"]:
            price_target = statistics.median(analysis["price_targets"])
            
        return FusedSignal(
            symbol=symbol,
            signal_type=signal_type,
            confidence=confidence,
            price_target=price_target,
            reasoning=reasoning,
            metadata={
                "signal_counts": dict(signal_counts),
                "source_weights": dict(source_weights),
                "data_points": len(analysis["signal_types"])
            }
        )
        
    def _calculate_confidence(self, analysis: Dict[str, Any], dominant_signal: str) -> float:
        """Calculate confidence score for fused signal"""
        confidences = analysis["confidences"]
        signal_counts = analysis["signal_counts"]
        source_weights = analysis["source_weights"]
        
        # Base confidence from average confidence
        base_confidence = statistics.mean(confidences) if confidences else 0.5
        
        # Consensus bonus
        total_signals = sum(signal_counts.values())
        dominant_count = signal_counts.get(dominant_signal, 0)
        consensus_bonus = (dominant_count / total_signals) if total_signals > 0 else 0
        
        # Source weight bonus
        source_bonus = source_weights.get(dominant_signal, 0.1)
        
        # Combine factors
        confidence = (base_confidence * 0.4 + 
                     consensus_bonus * 0.3 + 
                     source_bonus * 0.3)
        
        return min(confidence, 1.0)
        
    def _generate_reasoning(self, analysis: Dict[str, Any], dominant_signal: str, confidence: float) -> str:
        """Generate human-readable reasoning"""
        signal_counts = analysis["signal_counts"]
        total_signals = sum(signal_counts.values())
        dominant_count = signal_counts.get(dominant_signal, 0)
        
        reasoning_parts = []
        
        # Signal consensus
        consensus_pct = (dominant_count / total_signals * 100) if total_signals > 0 else 0
        reasoning_parts.append(f"{consensus_pct:.1f}% of signals indicate {dominant_signal}")
        
        # Source diversity
        source_types = len(set(analysis["signal_types"]))
        reasoning_parts.append(f"based on {source_types} different source types")
        
        # Data volume
        reasoning_parts.append(f"from {total_signals} data points")
        
        # Confidence level
        if confidence > 0.8:
            reasoning_parts.append("with very high confidence")
        elif confidence > 0.6:
            reasoning_parts.append("with high confidence")
        elif confidence > 0.4:
            reasoning_parts.append("with moderate confidence")
        else:
            reasoning_parts.append("with low confidence")
            
        return ". ".join(reasoning_parts) + "."

class TradingInsightGenerator:
    """Generate comprehensive trading insights from fused data"""
    
    def __init__(self, fusion_engine: DataFusionEngine):
        self.fusion_engine = fusion_engine
        self.insight_templates = {
            "bullish": [
                "Strong bullish momentum detected across multiple indicators",
                "Positive sentiment and technical alignment suggest upward potential",
                "Multiple sources confirm buying pressure"
            ],
            "bearish": [
                "Significant bearish signals from technical and sentiment analysis",
                "Risk factors outweigh potential opportunities at current levels",
                "Multiple indicators suggest downside pressure"
            ],
            "neutral": [
                "Mixed signals suggest caution in current market conditions",
                "Balanced risk-reward profile warrants wait-and-see approach",
                "Insufficient conviction for strong directional bias"
            ]
        }
        
    async def generate_insight(self, symbol: str, timeframe: str = "short_term") -> TradingInsight:
        """Generate comprehensive trading insight"""
        # Get fused signals for different timeframes
        short_term_signal = await self.fusion_engine.fuse_signals(symbol, 5)
        medium_term_signal = await self.fusion_engine.fuse_signals(symbol, 60)
        long_term_signal = await self.fusion_engine.fuse_signals(symbol, 1440)  # 24 hours
        
        # Analyze signal consistency
        signals = [short_term_signal, medium_term_signal, long_term_signal]
        overall_signal = self._determine_overall_signal(signals)
        confidence = self._calculate_overall_confidence(signals)
        
        # Generate insight components
        risk_factors = self._identify_risk_factors(signals)
        opportunities = self._identify_opportunities(signals)
        conflicting_signals = self._identify_conflicts(signals)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(overall_signal, confidence, risk_factors)
        
        # Compile supporting data
        supporting_data = {
            "short_term": {
                "signal": short_term_signal.signal_type.value,
                "confidence": short_term_signal.confidence,
                "reasoning": short_term_signal.reasoning
            },
            "medium_term": {
                "signal": medium_term_signal.signal_type.value,
                "confidence": medium_term_signal.confidence,
                "reasoning": medium_term_signal.reasoning
            },
            "long_term": {
                "signal": long_term_signal.signal_type.value,
                "confidence": long_term_signal.confidence,
                "reasoning": long_term_signal.reasoning
            }
        }
        
        # Calculate price targets
        price_targets = self._calculate_price_targets(signals)
        
        return TradingInsight(
            symbol=symbol,
            overall_signal=overall_signal,
            confidence_score=confidence,
            price_targets=price_targets,
            risk_factors=risk_factors,
            opportunities=opportunities,
            supporting_data=supporting_data,
            conflicting_signals=conflicting_signals,
            recommendation=recommendation
        )
        
    def _determine_overall_signal(self, signals: List[FusedSignal]) -> SignalType:
        """Determine overall signal from multiple timeframe signals"""
        signal_votes = defaultdict(int)
        total_weight = 0.0
        
        for signal in signals:
            signal_votes[signal.signal_type] += 1
            total_weight += signal.confidence
            
        # Weighted voting
        weighted_votes = defaultdict(float)
        for signal in signals:
            weighted_votes[signal.signal_type] += signal.confidence
            
        if not weighted_votes:
            return SignalType.WATCH
            
        return max(weighted_votes.keys(), key=lambda x: weighted_votes[x])
        
    def _calculate_overall_confidence(self, signals: List[FusedSignal]) -> float:
        """Calculate overall confidence from multiple signals"""
        if not signals:
            return 0.1
            
        confidences = [s.confidence for s in signals]
        return statistics.mean(confidences)
        
    def _identify_risk_factors(self, signals: List[FusedSignal]) -> List[str]:
        """Identify risk factors from signals"""
        risk_factors = []
        
        for signal in signals:
            if signal.signal_type == SignalType.SELL:
                risk_factors.append("Bearish sentiment detected")
            if signal.confidence < 0.3:
                risk_factors.append("Low confidence in signals")
            if "volatility" in signal.reasoning.lower():
                risk_factors.append("High volatility detected")
                
        return list(set(risk_factors))  # Remove duplicates
        
    def _identify_opportunities(self, signals: List[FusedSignal]) -> List[str]:
        """Identify opportunities from signals"""
        opportunities = []
        
        for signal in signals:
            if signal.signal_type == SignalType.BUY:
                opportunities.append("Positive momentum detected")
            if signal.confidence > 0.7:
                opportunities.append("High confidence signals")
            if signal.price_target:
                opportunities.append(f"Price target at ${signal.price_target}")
                
        return list(set(opportunities))
        
    def _identify_conflicts(self, signals: List[FusedSignal]) -> List[str]:
        """Identify conflicting signals"""
        conflicts = []
        signal_types = [s.signal_type for s in signals]
        
        if len(set(signal_types)) > 2:
            conflicts.append("Divergent signals across timeframes")
            
        buy_signals = sum(1 for s in signals if s.signal_type == SignalType.BUY)
        sell_signals = sum(1 for s in signals if s.signal_type == SignalType.SELL)
        
        if buy_signals > 0 and sell_signals > 0:
            conflicts.append("Mixed buy/sell signals detected")
            
        return conflicts
        
    def _generate_recommendation(self, signal: SignalType, confidence: float, risk_factors: List[str]) -> str:
        """Generate actionable recommendation"""
        if confidence < 0.4:
            return "WAIT - Insufficient confidence for action"
            
        if signal == SignalType.BUY:
            if len(risk_factors) == 0:
                return "STRONG BUY - High confidence with minimal risks"
            elif len(risk_factors) <= 2:
                return "BUY - Positive outlook with manageable risks"
            else:
                return "CONSIDER BUY - Positive but evaluate risks carefully"
                
        elif signal == SignalType.SELL:
            if len(risk_factors) >= 3:
                return "STRONG SELL - Multiple risk factors detected"
            elif len(risk_factors) >= 1:
                return "SELL - Downside pressure with risks confirmed"
            else:
                return "CONSIDER SELL - Cautious stance recommended"
                
        else:
            return "HOLD - Wait for clearer signals"
            
    def _calculate_price_targets(self, signals: List[FusedSignal]) -> Dict[str, float]:
        """Calculate price targets from signals"""
        price_targets = {}
        
        for signal in signals:
            if signal.price_target:
                timeframe = signal.time_horizon
                price_targets[timeframe] = signal.price_target
                
        return price_targets
