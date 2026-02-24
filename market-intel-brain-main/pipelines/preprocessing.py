"""
MAIFA v3 Preprocessing Pipeline - Stage 1 of the 5-stage workflow
Data cleaning, normalization, and preparation for analysis
"""

import asyncio
import logging
import re
import html
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from models.schemas import AgentInput, FilterResult
from models.datatypes import PipelineResult

class PreprocessingPipeline:
    """
    MAIFA v3 Preprocessing Pipeline - Data cleaning and normalization
    
    Handles:
    - Text cleaning and normalization
    - Noise detection and filtering
    - Data validation
    - Format standardization
    - Quality assessment
    """
    
    def __init__(self):
        self.logger = logging.getLogger("PreprocessingPipeline")
        self._noise_patterns = self._initialize_noise_patterns()
        self._normalization_rules = self._initialize_normalization_rules()
        self._quality_thresholds = self._initialize_quality_thresholds()
        
    def _initialize_noise_patterns(self) -> List[Dict[str, Any]]:
        """Initialize patterns for noise detection"""
        return [
            {
                "pattern": r"http\S+",
                "type": "url",
                "severity": "high",
                "action": "remove"
            },
            {
                "pattern": r"\b(BUY NOW|CLICK HERE|FREE|LIMITED OFFER|ACT NOW)\b",
                "type": "spam",
                "severity": "high", 
                "action": "flag"
            },
            {
                "pattern": r"[^\w\s.,?!-:;،؛'\"()@#$%^&*+=\[\]{}|\\/<>~`]",
                "type": "special_chars",
                "severity": "medium",
                "action": "clean"
            },
            {
                "pattern": r"[A-Z]{5,}",
                "type": "excessive_caps",
                "severity": "medium",
                "action": "normalize"
            },
            {
                "pattern": r"[!?]{3,}",
                "type": "excessive_punctuation",
                "severity": "medium",
                "action": "normalize"
            },
            {
                "pattern": r"\s{3,}",
                "type": "excessive_whitespace",
                "severity": "low",
                "action": "normalize"
            }
        ]
    
    def _initialize_normalization_rules(self) -> Dict[str, Any]:
        """Initialize text normalization rules"""
        return {
            "case_normalization": True,
            "punctuation_normalization": True,
            "whitespace_normalization": True,
            "unicode_normalization": True,
            "html_entity_decoding": True,
            "emoji_handling": "remove",  # remove, replace, keep
            "number_normalization": True,
            "currency_normalization": True
        }
    
    def _initialize_quality_thresholds(self) -> Dict[str, Any]:
        """Initialize data quality thresholds"""
        return {
            "min_text_length": 10,
            "max_text_length": 10000,
            "min_word_count": 3,
            "max_noise_score": 3,
            "min_relevance_score": 0.1,
            "max_duplicate_ratio": 0.8
        }
    
    async def process(self, 
                    input_data: Dict[str, Any],
                    config: Optional[Dict[str, Any]] = None) -> PipelineResult:
        """
        Main preprocessing pipeline
        
        Args:
            input_data: Raw input data
            config: Optional processing configuration
            
        Returns:
            Preprocessing results
        """
        try:
            self.logger.debug("Starting preprocessing pipeline")
            
            # Extract text and metadata
            text = input_data.get("text", "")
            symbol = input_data.get("symbol", "UNKNOWN")
            metadata = input_data.get("metadata", {})
            
            # Initialize processing config
            processing_config = {**self._normalization_rules, **(config or {})}
            
            # Step 1: Initial validation
            validation_result = await self._validate_input(text, metadata)
            if not validation_result["is_valid"]:
                return {
                    "status": "failed",
                    "error": validation_result["error"],
                    "stage": "validation"
                }
            
            # Step 2: Noise detection
            noise_analysis = await self._detect_noise(text)
            
            # Step 3: Text cleaning
            cleaned_text = await self._clean_text(text, noise_analysis, processing_config)
            
            # Step 4: Normalization
            normalized_text = await self._normalize_text(cleaned_text, processing_config)
            
            # Step 5: Quality assessment
            quality_assessment = await self._assess_quality(normalized_text, noise_analysis)
            
            # Step 6: Create standardized input
            processed_input = AgentInput(
                text=normalized_text,
                symbol=symbol,
                timestamp=datetime.now(),
                metadata={
                    **metadata,
                    "preprocessing": {
                        "noise_score": noise_analysis["noise_score"],
                        "quality_score": quality_assessment["quality_score"],
                        "original_length": len(text),
                        "processed_length": len(normalized_text),
                        "processing_timestamp": datetime.now().isoformat()
                    }
                }
            )
            
            # Step 7: Determine if data should be filtered out
            should_filter = await self._should_filter_data(noise_analysis, quality_assessment)
            
            pipeline_result = {
                "status": "completed",
                "processed_input": processed_input,
                "noise_analysis": noise_analysis,
                "quality_assessment": quality_assessment,
                "should_filter": should_filter,
                "processing_stats": {
                    "original_length": len(text),
                    "processed_length": len(normalized_text),
                    "compression_ratio": len(normalized_text) / len(text) if text else 0,
                    "noise_patterns_found": len(noise_analysis["patterns_found"]),
                    "processing_time": datetime.now().isoformat()
                }
            }
            
            self.logger.debug(f"Preprocessing completed: {len(normalized_text)} chars, noise_score: {noise_analysis['noise_score']}")
            return pipeline_result
            
        except Exception as e:
            self.logger.error(f"Preprocessing pipeline failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "stage": "unknown"
            }
    
    async def _validate_input(self, text: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate input data"""
        try:
            # Check text length
            if len(text) < self._quality_thresholds["min_text_length"]:
                return {
                    "is_valid": False,
                    "error": f"Text too short: {len(text)} < {self._quality_thresholds['min_text_length']}"
                }
            
            if len(text) > self._quality_thresholds["max_text_length"]:
                return {
                    "is_valid": False,
                    "error": f"Text too long: {len(text)} > {self._quality_thresholds['max_text_length']}"
                }
            
            # Check word count
            word_count = len(text.split())
            if word_count < self._quality_thresholds["min_word_count"]:
                return {
                    "is_valid": False,
                    "error": f"Too few words: {word_count} < {self._quality_thresholds['min_word_count']}"
                }
            
            # Check for empty or whitespace-only text
            if not text.strip():
                return {
                    "is_valid": False,
                    "error": "Text is empty or whitespace only"
                }
            
            return {"is_valid": True}
            
        except Exception as e:
            return {
                "is_valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    async def _detect_noise(self, text: str) -> Dict[str, Any]:
        """Detect noise patterns in text"""
        try:
            noise_score = 0
            patterns_found = []
            cleaned_segments = []
            
            for pattern_info in self._noise_patterns:
                pattern = pattern_info["pattern"]
                pattern_type = pattern_info["type"]
                severity = pattern_info["severity"]
                
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    patterns_found.append({
                        "type": pattern_type,
                        "severity": severity,
                        "matches": matches,
                        "count": len(matches)
                    })
                    
                    # Calculate noise contribution
                    severity_weight = {"high": 3, "medium": 2, "low": 1}[severity]
                    noise_score += len(matches) * severity_weight
            
            return {
                "noise_score": noise_score,
                "patterns_found": patterns_found,
                "total_patterns": len(patterns_found)
            }
            
        except Exception as e:
            self.logger.error(f"Noise detection failed: {e}")
            return {
                "noise_score": 0,
                "patterns_found": [],
                "total_patterns": 0
            }
    
    async def _clean_text(self, 
                         text: str, 
                         noise_analysis: Dict[str, Any],
                         config: Dict[str, Any]) -> str:
        """Clean text based on noise analysis"""
        try:
            cleaned_text = text
            
            # Apply cleaning actions based on noise patterns
            for pattern_info in self._noise_patterns:
                pattern = pattern_info["pattern"]
                action = pattern_info["action"]
                
                if action == "remove":
                    cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)
                elif action == "clean":
                    # Clean but preserve structure
                    if pattern_info["type"] == "special_chars":
                        # Remove excessive special characters but keep basic punctuation
                        cleaned_text = re.sub(r"[^\w\s.,?!-:;،؛'\"()]", "", cleaned_text)
                elif action == "normalize":
                    # Normalize but don't remove
                    if pattern_info["type"] == "excessive_caps":
                        # Convert excessive caps to normal case
                        cleaned_text = re.sub(r"[A-Z]{5,}", lambda m: m.group().lower(), cleaned_text)
                    elif pattern_info["type"] == "excessive_punctuation":
                        # Reduce excessive punctuation
                        cleaned_text = re.sub(r"[!?]{3,}", "!!", cleaned_text)
            
            # HTML entity decoding
            if config.get("html_entity_decoding", True):
                cleaned_text = html.unescape(cleaned_text)
            
            # Emoji handling
            emoji_handling = config.get("emoji_handling", "remove")
            if emoji_handling == "remove":
                # Remove emojis (simplified regex)
                cleaned_text = re.sub(r"[^\w\s.,?!-:;،؛'\"()@#$%^&*+=\[\]{}|\\/<>~`]", "", cleaned_text)
            elif emoji_handling == "replace":
                # Replace with placeholder
                cleaned_text = re.sub(r"[^\w\s.,?!-:;،؛'\"()@#$%^&*+=\[\]{}|\\/<>~`]", "[EMOJI]", cleaned_text)
            
            return cleaned_text.strip()
            
        except Exception as e:
            self.logger.error(f"Text cleaning failed: {e}")
            return text  # Return original text if cleaning fails
    
    async def _normalize_text(self, text: str, config: Dict[str, Any]) -> str:
        """Normalize text according to configuration"""
        try:
            normalized_text = text
            
            # Case normalization
            if config.get("case_normalization", True):
                # Keep first letter of sentences capitalized
                sentences = re.split(r'(?<=[.!?])\s+', normalized_text)
                normalized_sentences = []
                for sentence in sentences:
                    if sentence.strip():
                        normalized_sentences.append(sentence[0].upper() + sentence[1:].lower())
                    else:
                        normalized_sentences.append(sentence)
                normalized_text = " ".join(normalized_sentences)
            
            # Whitespace normalization
            if config.get("whitespace_normalization", True):
                normalized_text = re.sub(r'\s+', ' ', normalized_text)
                normalized_text = normalized_text.strip()
            
            # Punctuation normalization
            if config.get("punctuation_normalization", True):
                # Ensure proper spacing around punctuation
                normalized_text = re.sub(r'\s*([.,!?;:])', r'\1', normalized_text)
                normalized_text = re.sub(r'([.,!?;:])\s*', r'\1 ', normalized_text)
                normalized_text = re.sub(r'\s+', ' ', normalized_text).strip()
            
            # Number normalization
            if config.get("number_normalization", True):
                # Normalize number formats
                normalized_text = re.sub(r'(\d+),(\d+)', r'\1\2', normalized_text)  # Remove commas in numbers
            
            # Currency normalization
            if config.get("currency_normalization", True):
                # Standardize currency symbols
                normalized_text = re.sub(r'[$€£¥]', 'USD', normalized_text)
            
            # Unicode normalization
            if config.get("unicode_normalization", True):
                import unicodedata
                normalized_text = unicodedata.normalize('NFKC', normalized_text)
            
            return normalized_text
            
        except Exception as e:
            self.logger.error(f"Text normalization failed: {e}")
            return text  # Return original text if normalization fails
    
    async def _assess_quality(self, 
                             text: str, 
                             noise_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess quality of processed text"""
        try:
            quality_factors = {}
            total_quality_score = 1.0
            
            # Length quality
            text_length = len(text)
            if text_length < 50:
                length_quality = 0.5
            elif text_length > 2000:
                length_quality = 0.8
            else:
                length_quality = 1.0
            quality_factors["length"] = length_quality
            
            # Noise quality (inverse of noise score)
            noise_score = noise_analysis["noise_score"]
            noise_quality = max(0.0, 1.0 - (noise_score / 10.0))  # Normalize to 0-1
            quality_factors["noise"] = noise_quality
            
            # Word diversity
            words = text.lower().split()
            unique_words = set(words)
            if len(words) > 0:
                diversity_ratio = len(unique_words) / len(words)
                diversity_quality = min(diversity_ratio * 1.5, 1.0)  # Boost diversity score
            else:
                diversity_quality = 0.0
            quality_factors["diversity"] = diversity_quality
            
            # Structure quality (presence of sentences)
            sentences = re.split(r'[.!?]+', text)
            if len(sentences) > 1:
                structure_quality = 1.0
            elif len(sentences) == 1 and len(text) > 100:
                structure_quality = 0.7
            else:
                structure_quality = 0.5
            quality_factors["structure"] = structure_quality
            
            # Calculate overall quality score
            total_quality_score = sum(quality_factors.values()) / len(quality_factors)
            
            return {
                "quality_score": total_quality_score,
                "quality_factors": quality_factors,
                "meets_threshold": total_quality_score >= 0.5,
                "text_stats": {
                    "character_count": text_length,
                    "word_count": len(words),
                    "unique_word_count": len(unique_words),
                    "sentence_count": len([s for s in sentences if s.strip()])
                }
            }
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            return {
                "quality_score": 0.0,
                "quality_factors": {},
                "meets_threshold": False,
                "error": str(e)
            }
    
    async def _should_filter_data(self, 
                                 noise_analysis: Dict[str, Any], 
                                 quality_assessment: Dict[str, Any]) -> bool:
        """Determine if data should be filtered out"""
        try:
            # Filter based on noise score
            if noise_analysis["noise_score"] > self._quality_thresholds["max_noise_score"]:
                return True
            
            # Filter based on quality score
            if not quality_assessment.get("meets_threshold", False):
                return True
            
            # Check for high-severity spam patterns
            high_severity_patterns = [
                p for p in noise_analysis["patterns_found"]
                if p["severity"] == "high"
            ]
            if len(high_severity_patterns) > 2:
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Filter decision failed: {e}")
            return False  # Don't filter on error
    
    async def batch_process(self, 
                           inputs: List[Dict[str, Any]],
                           config: Optional[Dict[str, Any]] = None) -> List[PipelineResult]:
        """Process multiple inputs in parallel"""
        tasks = [
            self.process(input_data, config)
            for input_data in inputs
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Batch preprocessing error: {result}")
                valid_results.append({
                    "status": "failed",
                    "error": str(result),
                    "stage": "batch_processing"
                })
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def get_preprocessing_stats(self) -> Dict[str, Any]:
        """Get preprocessing pipeline statistics"""
        return {
            "noise_patterns_count": len(self._noise_patterns),
            "normalization_rules_count": len(self._normalization_rules),
            "quality_thresholds": self._quality_thresholds,
            "available_actions": ["remove", "clean", "normalize", "flag"],
            "severity_levels": ["high", "medium", "low"]
        }


# Global preprocessing pipeline instance
preprocessing_pipeline = PreprocessingPipeline()
