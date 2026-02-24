"""
MAIFA v3 Aggregation Pipeline - Stage 4 of the 5-stage workflow
Aggregates multi-agent results into unified intelligence
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json
import statistics

from models.schemas import TradingSignal, SignalType
from models.datatypes import PipelineResult
from services.ai_models import ai_models_service
from services.sentiment_engine import sentiment_engine

class AggregationPipeline:
    """
    MAIFA v3 Aggregation Pipeline - Result fusion and intelligence generation
    
    Handles:
    - Multi-agent result fusion
    - Trading signal generation
    - Confidence scoring
    - Risk assessment integration
    - Final intelligence synthesis
    - Report generation
    """
    
    def __init__(self):
        self.logger = logging.getLogger("AggregationPipeline")
        self._fusion_strategies = self._initialize_fusion_strategies()
        self._signal_weights = self._initialize_signal_weights()
        self._confidence_models = self._initialize_confidence_models()
        self._risk_thresholds = self._initialize_risk_thresholds()
        
    def _initialize_fusion_strategies(self) -> Dict[str, Dict[str, Any]]:
        """Initialize different result fusion strategies"""
        return {
            "weighted_average": {
                "description": "Weighted average based on agent confidence",
                "confidence_factor": 0.8,
                "recency_factor": 0.2,
                "complexity_factor": 0.0
            },
            "bayesian_fusion": {
                "description": "Bayesian fusion of agent probabilities",
                "prior_weight": 0.3,
                "likelihood_weight": 0.7,
                "normalization": True
            },
            "ensemble_voting": {
                "description": "Majority voting with confidence weighting",
                "majority_threshold": 0.6,
                "abstention_handling": "ignore",
                "tie_breaking": "highest_confidence"
            },
            "hierarchical_fusion": {
                "description": "Hierarchical fusion based on agent hierarchy",
                "hierarchy_levels": ["filter", "analysis", "prediction"],
                "level_weights": {"filter": 0.2, "analysis": 0.5, "prediction": 0.3}
            },
            "adaptive_fusion": {
                "description": "Adaptive fusion based on context",
                "context_factors": ["market_volatility", "data_quality", "agent_reliability"],
                "adaptation_rate": 0.1
            }
        }
    
    def _initialize_signal_weights(self) -> Dict[str, float]:
        """Initialize weights for different signal components"""
        return {
            "sentiment_weight": 0.35,
            "keyword_weight": 0.25,
            "technical_weight": 0.20,
            "risk_weight": 0.15,
            "momentum_weight": 0.05
        }
    
    def _initialize_confidence_models(self) -> Dict[str, Dict[str, Any]]:
        """Initialize confidence calculation models"""
        return {
            "linear_combination": {
                "description": "Linear combination of agent confidences",
                "weights": {
                    "agent_confidence": 0.6,
                    "historical_accuracy": 0.3,
                    "data_quality": 0.1
                }
            },
            "bayesian_inference": {
                "description": "Bayesian inference for confidence",
                "prior_distribution": "beta",
                "likelihood_model": "binomial",
                "posterior_update": True
            },
            "ensemble_learning": {
                "description": "Ensemble learning for confidence estimation",
                "base_models": ["decision_tree", "neural_network", "random_forest"],
                "meta_learner": "logistic_regression"
            }
        }
    
    def _initialize_risk_thresholds(self) -> Dict[str, Any]:
        """Initialize risk assessment thresholds"""
        return {
            "signal_generation": {
                "min_confidence": 0.6,
                "max_risk_score": 0.7,
                "volatility_adjustment": True
            },
            "position_sizing": {
                "conservative": {"max_risk": 0.02, "confidence_threshold": 0.8},
                "moderate": {"max_risk": 0.05, "confidence_threshold": 0.6},
                "aggressive": {"max_risk": 0.10, "confidence_threshold": 0.4}
            },
            "stop_loss": {
                "tight_stop": 0.02,  # 2%
                "medium_stop": 0.05,  # 5%
                "wide_stop": 0.10    # 10%
            }
        }
    
    async def process(self, 
                     multi_agent_results: Dict[str, Any],
                     classification_result: Optional[Dict[str, Any]] = None,
                     processed_input: Optional[Dict[str, Any]] = None) -> PipelineResult:
        """
        Main aggregation pipeline
        
        Args:
            multi_agent_results: Results from multi-agent analysis
            classification_result: Results from event classification
            processed_input: Original processed input
            
        Returns:
            Aggregation results with final intelligence
        """
        try:
            self.logger.debug("Starting aggregation pipeline")
            
            # Step 1: Extract agent results
            agent_results = multi_agent_results.get("aggregated_results", {})
            validated_results = multi_agent_results.get("validated_results", [])
            
            # Step 2: Choose fusion strategy
            fusion_strategy = await self._choose_fusion_strategy(agent_results, classification_result)
            
            # Step 3: Fuse agent results
            fused_results = await self._fuse_agent_results(agent_results, fusion_strategy)
            
            # Step 4: Generate trading signals
            trading_signals = await self._generate_trading_signals(
                fused_results, classification_result, processed_input
            )
            
            # Step 5: Calculate confidence scores
            confidence_scores = await self._calculate_confidence_scores(
                fused_results, validated_results, trading_signals
            )
            
            # Step 6: Integrate risk assessment
            risk_assessment = await self._integrate_risk_assessment(
                fused_results, trading_signals, processed_input
            )
            
            # Step 7: Generate final intelligence
            final_intelligence = await self._generate_final_intelligence(
                fused_results, trading_signals, confidence_scores, risk_assessment
            )
            
            # Step 8: Create aggregation report
            aggregation_result = {
                "status": "completed",
                "fusion_strategy": fusion_strategy,
                "fused_results": fused_results,
                "trading_signals": trading_signals,
                "confidence_scores": confidence_scores,
                "risk_assessment": risk_assessment,
                "final_intelligence": final_intelligence,
                "processing_stats": {
                    "agents_fused": len(agent_results.get("successful_agents", [])),
                    "signals_generated": len(trading_signals.get("signals", [])),
                    "overall_confidence": confidence_scores.get("overall_confidence", 0.0),
                    "risk_level": risk_assessment.get("overall_risk_level", "unknown"),
                    "processing_timestamp": datetime.now().isoformat()
                }
            }
            
            self.logger.debug(f"Aggregation completed: {len(trading_signals.get('signals', []))} signals generated")
            return aggregation_result
            
        except Exception as e:
            self.logger.error(f"Aggregation pipeline failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "stage": "aggregation"
            }
    
    async def _choose_fusion_strategy(self, 
                                     agent_results: Dict[str, Any],
                                     classification_result: Optional[Dict[str, Any]]) -> str:
        """Choose optimal fusion strategy based on context"""
        try:
            successful_agents = agent_results.get("successful_agents", [])
            agent_count = len(successful_agents)
            
            # Get event type for context
            event_type = "news_event"  # Default
            if classification_result:
                event_type = classification_result.get("event_classification", {}).get("primary_event", {}).get("event_type", "news_event")
            
            # Choose strategy based on conditions
            if agent_count <= 2:
                return "weighted_average"
            elif agent_count >= 5:
                return "hierarchical_fusion"
            elif event_type in ["trading_signal", "earnings_report"]:
                return "bayesian_fusion"
            elif agent_results.get("aggregate_confidence", 0.0) > 0.8:
                return "ensemble_voting"
            else:
                return "adaptive_fusion"
                
        except Exception as e:
            self.logger.error(f"Fusion strategy selection failed: {e}")
            return "weighted_average"  # Default strategy
    
    async def _fuse_agent_results(self, 
                                 agent_results: Dict[str, Any],
                                 fusion_strategy: str) -> Dict[str, Any]:
        """Fuse results from multiple agents using chosen strategy"""
        try:
            strategy_config = self._fusion_strategies[fusion_strategy]
            
            if fusion_strategy == "weighted_average":
                return await self._weighted_average_fusion(agent_results, strategy_config)
            elif fusion_strategy == "bayesian_fusion":
                return await self._bayesian_fusion(agent_results, strategy_config)
            elif fusion_strategy == "ensemble_voting":
                return await self._ensemble_voting_fusion(agent_results, strategy_config)
            elif fusion_strategy == "hierarchical_fusion":
                return await self._hierarchical_fusion(agent_results, strategy_config)
            elif fusion_strategy == "adaptive_fusion":
                return await self._adaptive_fusion(agent_results, strategy_config)
            else:
                return await self._weighted_average_fusion(agent_results, strategy_config)
                
        except Exception as e:
            self.logger.error(f"Result fusion failed: {e}")
            return {}
    
    async def _weighted_average_fusion(self, 
                                       agent_results: Dict[str, Any],
                                       strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Weighted average fusion of agent results"""
        try:
            combined_results = agent_results.get("combined_results", {})
            confidence_scores = agent_results.get("confidence_scores", {})
            
            fused_sentiment = 0.0
            fused_keywords = []
            sentiment_weight_sum = 0.0
            
            # Fuse sentiment results
            for agent_name, result in combined_results.items():
                confidence = confidence_scores.get(agent_name, 0.5)
                
                # Extract sentiment if available
                if "analysis" in result:
                    analysis = result["analysis"]
                    if "polarity" in analysis:
                        fused_sentiment += analysis["polarity"] * confidence
                        sentiment_weight_sum += confidence
                
                # Extract keywords if available
                if "found_keywords" in result:
                    fused_keywords.extend(result["found_keywords"])
            
            # Normalize sentiment
            if sentiment_weight_sum > 0:
                fused_sentiment /= sentiment_weight_sum
            
            # Remove duplicate keywords
            unique_keywords = list(set(fused_keywords))
            
            return {
                "sentiment": {
                    "polarity": fused_sentiment,
                    "label": "positive" if fused_sentiment > 0.1 else "negative" if fused_sentiment < -0.1 else "neutral",
                    "confidence": sentiment_weight_sum / len(combined_results) if combined_results else 0.0
                },
                "keywords": {
                    "found_keywords": unique_keywords,
                    "count": len(unique_keywords),
                    "sources": list(combined_results.keys())
                },
                "fusion_metadata": {
                    "strategy": "weighted_average",
                    "agents_fused": len(combined_results),
                    "average_confidence": sentiment_weight_sum / len(combined_results) if combined_results else 0.0
                }
            }
            
        except Exception as e:
            self.logger.error(f"Weighted average fusion failed: {e}")
            return {}
    
    async def _bayesian_fusion(self, 
                               agent_results: Dict[str, Any],
                               strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Bayesian fusion of agent results"""
        try:
            combined_results = agent_results.get("combined_results", {})
            confidence_scores = agent_results.get("confidence_scores", {})
            
            # Simplified Bayesian fusion
            # In production, this would use proper Bayesian inference
            
            prior_weight = strategy_config["prior_weight"]
            likelihood_weight = strategy_config["likelihood_weight"]
            
            # Prior (neutral sentiment)
            prior_sentiment = 0.0
            
            # Likelihood from agents
            likelihood_sentiment = 0.0
            total_confidence = 0.0
            
            for agent_name, result in combined_results.items():
                confidence = confidence_scores.get(agent_name, 0.5)
                
                if "analysis" in result and "polarity" in result["analysis"]:
                    likelihood_sentiment += result["analysis"]["polarity"] * confidence
                    total_confidence += confidence
            
            if total_confidence > 0:
                likelihood_sentiment /= total_confidence
            
            # Posterior
            posterior_sentiment = (prior_weight * prior_sentiment + likelihood_weight * likelihood_sentiment)
            
            return {
                "sentiment": {
                    "polarity": posterior_sentiment,
                    "label": "positive" if posterior_sentiment > 0.1 else "negative" if posterior_sentiment < -0.1 else "neutral",
                    "confidence": total_confidence / len(combined_results) if combined_results else 0.0
                },
                "fusion_metadata": {
                    "strategy": "bayesian_fusion",
                    "prior_weight": prior_weight,
                    "likelihood_weight": likelihood_weight,
                    "agents_fused": len(combined_results)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Bayesian fusion failed: {e}")
            return {}
    
    async def _ensemble_voting_fusion(self, 
                                     agent_results: Dict[str, Any],
                                     strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Ensemble voting fusion"""
        try:
            combined_results = agent_results.get("combined_results", {})
            confidence_scores = agent_results.get("confidence_scores", {})
            
            # Collect votes for sentiment
            sentiment_votes = {"positive": 0, "negative": 0, "neutral": 0}
            weighted_votes = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
            
            for agent_name, result in combined_results.items():
                confidence = confidence_scores.get(agent_name, 0.5)
                
                if "analysis" in result and "label" in result["analysis"]:
                    label = result["analysis"]["label"]
                    if label in sentiment_votes:
                        sentiment_votes[label] += 1
                        weighted_votes[label] += confidence
            
            # Determine winner
            total_votes = sum(sentiment_votes.values())
            majority_threshold = strategy_config["majority_threshold"]
            
            winner = "neutral"
            max_votes = max(sentiment_votes.values())
            
            if max_votes / total_votes >= majority_threshold:
                winner = max(sentiment_votes, key=sentiment_votes.get)
            else:
                # Use weighted votes for tie-breaking
                winner = max(weighted_votes, key=weighted_votes.get)
            
            # Calculate confidence
            confidence = weighted_votes[winner] / sum(weighted_votes.values()) if sum(weighted_votes.values()) > 0 else 0.0
            
            return {
                "sentiment": {
                    "polarity": 0.3 if winner == "positive" else -0.3 if winner == "negative" else 0.0,
                    "label": winner,
                    "confidence": confidence
                },
                "voting_metadata": {
                    "sentiment_votes": sentiment_votes,
                    "weighted_votes": weighted_votes,
                    "majority_threshold": majority_threshold,
                    "total_votes": total_votes
                },
                "fusion_metadata": {
                    "strategy": "ensemble_voting",
                    "agents_fused": len(combined_results)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ensemble voting fusion failed: {e}")
            return {}
    
    async def _hierarchical_fusion(self, 
                                   agent_results: Dict[str, Any],
                                   strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Hierarchical fusion based on agent hierarchy"""
        try:
            combined_results = agent_results.get("combined_results", {})
            level_weights = strategy_config["level_weights"]
            
            # Group agents by hierarchy level
            level_results = {"filter": [], "analysis": [], "prediction": []}
            
            for agent_name, result in combined_results.items():
                # Determine agent level (simplified)
                if agent_name == "filter_agent":
                    level_results["filter"].append(result)
                elif agent_name in ["sentiment_agent", "hunter_agent"]:
                    level_results["analysis"].append(result)
                else:
                    level_results["prediction"].append(result)
            
            # Fuse results by level
            level_fusions = {}
            for level, results in level_results.items():
                if results:
                    # Simple average for each level
                    level_fusions[level] = await self._average_level_results(results)
            
            # Combine levels with weights
            final_sentiment = 0.0
            total_weight = 0.0
            
            for level, fusion in level_fusions.items():
                weight = level_weights.get(level, 0.33)
                if "sentiment" in fusion:
                    final_sentiment += fusion["sentiment"]["polarity"] * weight
                    total_weight += weight
            
            if total_weight > 0:
                final_sentiment /= total_weight
            
            return {
                "sentiment": {
                    "polarity": final_sentiment,
                    "label": "positive" if final_sentiment > 0.1 else "negative" if final_sentiment < -0.1 else "neutral",
                    "confidence": total_weight / len(level_weights)
                },
                "level_fusions": level_fusions,
                "fusion_metadata": {
                    "strategy": "hierarchical_fusion",
                    "level_weights": level_weights,
                    "agents_per_level": {level: len(results) for level, results in level_results.items()}
                }
            }
            
        except Exception as e:
            self.logger.error(f"Hierarchical fusion failed: {e}")
            return {}
    
    async def _adaptive_fusion(self, 
                               agent_results: Dict[str, Any],
                               strategy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Adaptive fusion based on context"""
        try:
            # For simplicity, use weighted average with adaptation
            base_result = await self._weighted_average_fusion(agent_results, self._fusion_strategies["weighted_average"])
            
            # Apply adaptation based on context factors
            adaptation_rate = strategy_config["adaptation_rate"]
            
            # Simplified adaptation: adjust confidence based on agent count
            agent_count = len(agent_results.get("successful_agents", []))
            adaptation_factor = min(agent_count / 5.0, 1.0)  # Normalize to 0-1
            
            if "sentiment" in base_result:
                original_confidence = base_result["sentiment"]["confidence"]
                adapted_confidence = original_confidence + (adaptation_factor - original_confidence) * adaptation_rate
                base_result["sentiment"]["confidence"] = max(0.0, min(1.0, adapted_confidence))
            
            base_result["fusion_metadata"]["strategy"] = "adaptive_fusion"
            base_result["fusion_metadata"]["adaptation_factor"] = adaptation_factor
            
            return base_result
            
        except Exception as e:
            self.logger.error(f"Adaptive fusion failed: {e}")
            return {}
    
    async def _average_level_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Average results within a hierarchy level"""
        try:
            if not results:
                return {}
            
            total_polarity = 0.0
            total_confidence = 0.0
            valid_results = 0
            
            for result in results:
                if "analysis" in result and "polarity" in result["analysis"]:
                    total_polarity += result["analysis"]["polarity"]
                    total_confidence += result.get("confidence", 0.5)
                    valid_results += 1
            
            if valid_results > 0:
                avg_polarity = total_polarity / valid_results
                avg_confidence = total_confidence / valid_results
                
                return {
                    "sentiment": {
                        "polarity": avg_polarity,
                        "label": "positive" if avg_polarity > 0.1 else "negative" if avg_polarity < -0.1 else "neutral",
                        "confidence": avg_confidence
                    }
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Level result averaging failed: {e}")
            return {}
    
    async def _generate_trading_signals(self, 
                                       fused_results: Dict[str, Any],
                                       classification_result: Optional[Dict[str, Any]] = None,
                                       processed_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate trading signals from fused results"""
        try:
            signals = []
            
            # Extract sentiment data
            sentiment_data = fused_results.get("sentiment", {})
            sentiment_polarity = sentiment_data.get("polarity", 0.0)
            sentiment_confidence = sentiment_data.get("confidence", 0.0)
            
            # Extract keyword data
            keyword_data = fused_results.get("keywords", {})
            keyword_count = keyword_data.get("count", 0)
            
            # Get symbol
            symbol = "UNKNOWN"
            if processed_input:
                symbol = processed_input.get("symbol", "UNKNOWN")
            elif classification_result:
                symbol = classification_result.get("enriched_metadata", {}).get("symbol", "UNKNOWN")
            
            # Generate primary signal
            signal_strength = 0.0
            signal_type = SignalType.HOLD
            
            # Sentiment contribution
            sentiment_weight = self._signal_weights["sentiment_weight"]
            signal_strength += sentiment_polarity * sentiment_weight * sentiment_confidence
            
            # Keyword contribution
            keyword_weight = self._signal_weights["keyword_weight"]
            keyword_contribution = min(keyword_count / 5.0, 1.0)  # Normalize keyword count
            signal_strength += keyword_contribution * keyword_weight
            
            # Determine signal type
            min_confidence = self._risk_thresholds["signal_generation"]["min_confidence"]
            
            if sentiment_confidence >= min_confidence:
                if signal_strength > 0.3:
                    signal_type = SignalType.BUY
                elif signal_strength < -0.3:
                    signal_type = SignalType.SELL
                else:
                    signal_type = SignalType.HOLD
            
            # Create trading signal
            trading_signal = TradingSignal(
                signal=signal_type,
                confidence=min(abs(signal_strength), 1.0),
                recommendation=self._generate_recommendation(signal_type, signal_strength, sentiment_confidence),
                risk_factors=self._identify_risk_factors(fused_results, classification_result),
                opportunities=self._identify_opportunities(fused_results, classification_result)
            )
            
            signals.append(trading_signal)
            
            # Generate additional signals if conditions warrant
            if sentiment_confidence > 0.8 and abs(sentiment_polarity) > 0.5:
                # Strong conviction signal
                strong_signal = TradingSignal(
                    signal=signal_type,
                    confidence=sentiment_confidence,
                    recommendation=f"STRONG_{signal_type.value}",
                    risk_factors=["high_conviction_risk"],
                    opportunities=["high_potential_return"]
                )
                signals.append(strong_signal)
            
            return {
                "signals": signals,
                "primary_signal": trading_signal,
                "signal_metadata": {
                    "signal_strength": signal_strength,
                    "sentiment_contribution": sentiment_polarity * sentiment_weight * sentiment_confidence,
                    "keyword_contribution": keyword_contribution * keyword_weight,
                    "generation_timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Trading signal generation failed: {e}")
            return {"signals": [], "error": str(e)}
    
    def _generate_recommendation(self, 
                                 signal_type: SignalType,
                                 signal_strength: float,
                                 confidence: float) -> str:
        """Generate detailed recommendation"""
        base_recommendation = signal_type.value.upper()
        
        if confidence > 0.8:
            strength = "STRONG"
        elif confidence > 0.6:
            strength = "MODERATE"
        else:
            strength = "WEAK"
        
        if abs(signal_strength) > 0.6:
            conviction = "HIGH_CONVCTION"
        elif abs(signal_strength) > 0.3:
            conviction = "MEDIUM_CONVCTION"
        else:
            conviction = "LOW_CONVCTION"
        
        return f"{strength}_{base_recommendation}_{conviction}"
    
    def _identify_risk_factors(self, 
                              fused_results: Dict[str, Any],
                              classification_result: Optional[Dict[str, Any]] = None) -> List[str]:
        """Identify risk factors from results"""
        risk_factors = []
        
        # Low confidence risk
        sentiment_confidence = fused_results.get("sentiment", {}).get("confidence", 0.0)
        if sentiment_confidence < 0.5:
            risk_factors.append("low_confidence")
        
        # Mixed signals risk
        if classification_result:
            primary_event = classification_result.get("event_classification", {}).get("primary_event", {}).get("event_type", "")
            if primary_event in ["regulatory_change", "macro_economic"]:
                risk_factors.append("high_volatility_risk")
        
        # Data quality risk
        fusion_metadata = fused_results.get("fusion_metadata", {})
        agents_fused = fusion_metadata.get("agents_fused", 0)
        if agents_fused < 2:
            risk_factors.append("limited_data_sources")
        
        return risk_factors
    
    def _identify_opportunities(self, 
                               fused_results: Dict[str, Any],
                               classification_result: Optional[Dict[str, Any]] = None) -> List[str]:
        """Identify opportunities from results"""
        opportunities = []
        
        # High confidence opportunity
        sentiment_confidence = fused_results.get("sentiment", {}).get("confidence", 0.0)
        if sentiment_confidence > 0.8:
            opportunities.append("high_confidence_signal")
        
        # Keyword opportunity
        keyword_count = fused_results.get("keywords", {}).get("count", 0)
        if keyword_count > 5:
            opportunities.append("strong_market_interest")
        
        # Event-based opportunity
        if classification_result:
            primary_event = classification_result.get("event_classification", {}).get("primary_event", {}).get("event_type", "")
            if primary_event in ["earnings_report", "trading_signal"]:
                opportunities.append("event_driven_opportunity")
        
        return opportunities
    
    async def _calculate_confidence_scores(self, 
                                           fused_results: Dict[str, Any],
                                           validated_results: List[Dict[str, Any]],
                                           trading_signals: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive confidence scores"""
        try:
            # Agent confidence
            agent_confidence = fused_results.get("sentiment", {}).get("confidence", 0.0)
            
            # Execution confidence
            successful_agents = len([r for r in validated_results if r.get("status") == "completed"])
            total_agents = len(validated_results)
            execution_confidence = successful_agents / total_agents if total_agents > 0 else 0.0
            
            # Signal confidence
            signals = trading_signals.get("signals", [])
            signal_confidence = 0.0
            if signals:
                signal_confidence = sum(signal.confidence for signal in signals) / len(signals)
            
            # Overall confidence (weighted average)
            overall_confidence = (
                agent_confidence * 0.4 +
                execution_confidence * 0.3 +
                signal_confidence * 0.3
            )
            
            return {
                "agent_confidence": agent_confidence,
                "execution_confidence": execution_confidence,
                "signal_confidence": signal_confidence,
                "overall_confidence": overall_confidence,
                "confidence_breakdown": {
                    "agent_weight": 0.4,
                    "execution_weight": 0.3,
                    "signal_weight": 0.3
                }
            }
            
        except Exception as e:
            self.logger.error(f"Confidence calculation failed: {e}")
            return {"overall_confidence": 0.0}
    
    async def _integrate_risk_assessment(self, 
                                         fused_results: Dict[str, Any],
                                         trading_signals: Dict[str, Any],
                                         processed_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Integrate risk assessment into aggregation"""
        try:
            # Extract risk factors from signals
            signals = trading_signals.get("signals", [])
            all_risk_factors = []
            for signal in signals:
                all_risk_factors.extend(signal.risk_factors)
            
            # Count risk factors by type
            risk_counts = {}
            for risk in all_risk_factors:
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
            
            # Calculate overall risk score
            max_risk_score = self._risk_thresholds["signal_generation"]["max_risk_score"]
            
            # Base risk from confidence
            confidence = fused_results.get("sentiment", {}).get("confidence", 0.0)
            base_risk = 1.0 - confidence
            
            # Additional risk from factors
            additional_risk = len(risk_counts) * 0.1
            
            overall_risk_score = min(base_risk + additional_risk, 1.0)
            
            # Determine risk level
            if overall_risk_score < 0.3:
                risk_level = "low"
            elif overall_risk_score < 0.6:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            return {
                "overall_risk_score": overall_risk_score,
                "overall_risk_level": risk_level,
                "risk_factors": risk_counts,
                "risk_assessment": {
                    "exceeds_threshold": overall_risk_score > max_risk_score,
                    "recommended_action": "caution" if overall_risk_score > 0.7 else "proceed"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Risk assessment integration failed: {e}")
            return {"overall_risk_level": "unknown"}
    
    async def _generate_final_intelligence(self, 
                                          fused_results: Dict[str, Any],
                                          trading_signals: Dict[str, Any],
                                          confidence_scores: Dict[str, Any],
                                          risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final intelligence report"""
        try:
            # Extract key components
            sentiment = fused_results.get("sentiment", {})
            keywords = fused_results.get("keywords", {})
            primary_signal = trading_signals.get("primary_signal")
            overall_confidence = confidence_scores.get("overall_confidence", 0.0)
            risk_level = risk_assessment.get("overall_risk_level", "unknown")
            
            # Generate summary
            summary = self._generate_intelligence_summary(
                sentiment, keywords, primary_signal, overall_confidence, risk_level
            )
            
            # Generate actionable insights
            insights = self._generate_actionable_insights(
                fused_results, trading_signals, risk_assessment
            )
            
            return {
                "summary": summary,
                "sentiment_analysis": sentiment,
                "keyword_analysis": keywords,
                "trading_recommendation": {
                    "signal": primary_signal.signal.value if primary_signal else "HOLD",
                    "confidence": primary_signal.confidence if primary_signal else 0.0,
                    "recommendation": primary_signal.recommendation if primary_signal else "HOLD"
                },
                "risk_summary": {
                    "level": risk_level,
                    "score": risk_assessment.get("overall_risk_score", 0.0),
                    "factors": risk_assessment.get("risk_factors", {})
                },
                "confidence_metrics": confidence_scores,
                "actionable_insights": insights,
                "intelligence_metadata": {
                    "generation_timestamp": datetime.now().isoformat(),
                    "data_sources": fused_results.get("fusion_metadata", {}).get("agents_fused", 0),
                    "processing_stage": "aggregation_complete"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Final intelligence generation failed: {e}")
            return {"error": str(e)}
    
    def _generate_intelligence_summary(self, 
                                      sentiment: Dict[str, Any],
                                      keywords: Dict[str, Any],
                                      primary_signal,
                                      overall_confidence: float,
                                      risk_level: str) -> str:
        """Generate concise intelligence summary"""
        try:
            sentiment_label = sentiment.get("label", "neutral")
            sentiment_confidence = sentiment.get("confidence", 0.0)
            keyword_count = keywords.get("count", 0)
            signal_type = primary_signal.signal.value if primary_signal else "HOLD"
            
            summary_parts = []
            
            # Sentiment part
            if sentiment_confidence > 0.7:
                summary_parts.append(f"Strong {sentiment_label} sentiment detected")
            elif sentiment_confidence > 0.5:
                summary_parts.append(f"Moderate {sentiment_label} sentiment")
            else:
                summary_parts.append(f"Weak {sentiment_label} sentiment")
            
            # Keywords part
            if keyword_count > 5:
                summary_parts.append("with significant market keyword activity")
            elif keyword_count > 2:
                summary_parts.append("with moderate keyword relevance")
            
            # Signal part
            if signal_type != "HOLD":
                summary_parts.append(f"indicating a {signal_type} signal")
            
            # Risk part
            if risk_level == "high":
                summary_parts.append("with elevated risk factors")
            elif risk_level == "low":
                summary_parts.append("with low risk profile")
            
            # Confidence part
            if overall_confidence > 0.8:
                summary_parts.append("(high confidence)")
            elif overall_confidence < 0.5:
                summary_parts.append("(low confidence)")
            
            return " ".join(summary_parts) + "."
            
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            return "Intelligence summary unavailable."
    
    def _generate_actionable_insights(self, 
                                       fused_results: Dict[str, Any],
                                       trading_signals: Dict[str, Any],
                                       risk_assessment: Dict[str, Any]) -> List[str]:
        """Generate actionable insights"""
        insights = []
        
        try:
            # Signal-based insights
            primary_signal = trading_signals.get("primary_signal")
            if primary_signal:
                if primary_signal.signal == SignalType.BUY:
                    insights.append("Consider establishing long positions based on positive sentiment")
                elif primary_signal.signal == SignalType.SELL:
                    insights.append("Consider reducing exposure or establishing short positions")
                
                if primary_signal.confidence > 0.8:
                    insights.append("High confidence signal warrants stronger position sizing")
            
            # Risk-based insights
            risk_level = risk_assessment.get("overall_risk_level", "")
            if risk_level == "high":
                insights.append("Implement strict risk management due to elevated risk factors")
                insights.append("Consider reducing position size or using stop-loss orders")
            elif risk_level == "low":
                insights.append("Favorable risk conditions support position taking")
            
            # Sentiment-based insights
            sentiment = fused_results.get("sentiment", {})
            sentiment_label = sentiment.get("label", "")
            if sentiment_label == "positive":
                insights.append("Positive market sentiment supports bullish strategies")
            elif sentiment_label == "negative":
                insights.append("Negative sentiment suggests defensive positioning")
            
            # Keyword-based insights
            keywords = fused_results.get("keywords", {})
            keyword_count = keywords.get("count", 0)
            if keyword_count > 5:
                insights.append("High keyword activity indicates strong market attention")
            
            return insights[:5]  # Limit to top 5 insights
            
        except Exception as e:
            self.logger.error(f"Insights generation failed: {e}")
            return ["Insight generation temporarily unavailable"]
    
    async def get_aggregation_stats(self) -> Dict[str, Any]:
        """Get aggregation pipeline statistics"""
        return {
            "fusion_strategies_count": len(self._fusion_strategies),
            "signal_weights": self._signal_weights,
            "confidence_models_count": len(self._confidence_models),
            "risk_thresholds": self._risk_thresholds,
            "available_strategies": list(self._fusion_strategies.keys())
        }


# Global aggregation pipeline instance
aggregation_pipeline = AggregationPipeline()
