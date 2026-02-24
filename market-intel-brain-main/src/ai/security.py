"""
Security Layer - Prompt Injection Defense

Enterprise-grade security pipeline for LLM input sanitization
and prompt injection payload detection.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import json

class ThreatLevel(Enum):
    """Security threat level."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackType(Enum):
    """Types of prompt injection attacks."""
    DIRECT_INJECTION = "direct_injection"
    INDIRECT_INJECTION = "indirect_injection"
    ROLE_PLAYING = "role_playing"
    SYSTEM_PROMPT = "system_prompt"
    CODE_INJECTION = "code_injection"
    ESCAPE_SEQUENCE = "escape_sequence"
    CONTEXT_MANIPULATION = "context_manipulation"
    DATA_EXFILTRATION = "data_exfiltration"


@dataclass
class SecurityThreat:
    """Security threat detection result."""
    threat_level: ThreatLevel
    attack_type: AttackType
    confidence: float
    pattern_matched: str
    position: int
    original_text: str
    sanitized_text: str
    metadata: Dict[str, Any]


class SecuritySanitizer:
    """
    Enterprise-grade security sanitizer for LLM inputs.
    
    Features:
    - Multi-layer threat detection
    - Pattern-based injection detection
    - Contextual analysis
    - Real-time sanitization
    - Performance optimized
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("SecuritySanitizer")
        
        # Initialize threat patterns (O(1) lookup)
        self._threat_patterns = self._initialize_threat_patterns()
        self._suspicious_keywords = self._initialize_suspicious_keywords()
        self._escape_sequences = self._initialize_escape_sequences()
        
        # Performance metrics
        self.inputs_sanitized = 0
        self.threats_detected = 0
        self.avg_sanitization_time_ms = 0.0
        
        self.logger.info("SecuritySanitizer initialized with multi-layer threat detection")
    
    def _initialize_threat_patterns(self) -> Dict[AttackType, List[str]]:
        """Initialize threat detection patterns."""
        return {
            AttackType.DIRECT_INJECTION: [
                r"ignore\s+previous\s+instructions",
                r"disregard\s+all\s+above",
                r"forget\s+everything",
                r"system\s+prompt",
                r"developer\s+mode",
                r"jailbreak",
                r"override\s+instructions",
                r"new\s+instructions",
                r"act\s+as\s+a",
                r"pretend\s+to\s+be"
            ],
            
            AttackType.INDIRECT_INJECTION: [
                r"summarize\s+this\s+text",
                r"translate\s+to\s+english",
                r"explain\s+this\s+code",
                r"what\s+does\s+this\s+mean",
                r"analyze\s+this\s+content",
                r"interpret\s+this\s+data",
                r"process\s+this\s+information"
            ],
            
            AttackType.ROLE_PLAYING: [
                r"you\s+are\s+now",
                r"act\s+as\s+if",
                r"imagine\s+you\s+are",
                r"role\s+play\s+as",
                r"character\s+development",
                r"persona\s+adoption",
                r"assume\s+the\s+role"
            ],
            
            AttackType.SYSTEM_PROMPT: [
                r"system\s*:",
                r"system\s*message",
                r"system\s*instruction",
                r"system\s*configuration",
                r"system\s*settings",
                r"system\s*parameters"
            ],
            
            AttackType.CODE_INJECTION: [
                r"```",
                r"exec\s*\(",
                r"eval\s*\(",
                r"import\s+\w+",
                r"from\s+\w+\s+import",
                r"def\s+\w+\s*\(",
                r"class\s+\w+",
                r"lambda\s+",
                r"__import__",
                r"globals\s*\(\)",
                r"locals\s*\(\)"
            ],
            
            AttackType.ESCAPE_SEQUENCE: [
                r"\\x[0-9a-fA-F]{2}",
                r"\\u[0-9a-fA-F]{4}",
                r"\\U[0-9a-fA-F]{8}",
                r"\\n",
                r"\\r",
                r"\\t",
                r"\\\\",
                r"\\'",
                r'\\"'
            ],
            
            AttackType.CONTEXT_MANIPULATION: [
                r"previous\s+context",
                r"earlier\s+conversation",
                r"history\s+of",
                r"memory\s+of",
                r"recall\s+that",
                r"remember\s+when",
                r"as\s+mentioned\s+before"
            ],
            
            AttackType.DATA_EXFILTRATION: [
                r"print\s+all",
                r"show\s+me\s+everything",
                r"reveal\s+your",
                r"tell\s+me\s+your",
                r"what\s+are\s+your",
                r"list\s+all",
                r"dump\s+your",
                r"access\s+your"
            ]
        }
    
    def _initialize_suspicious_keywords(self) -> Set[str]:
        """Initialize suspicious keyword set."""
        return {
            "admin", "administrator", "root", "sudo", "password", "token",
            "secret", "key", "api_key", "private", "confidential", "sensitive",
            "internal", "system", "debug", "test", "backdoor", "exploit",
            "vulnerability", "bypass", "override", "escalate", "privilege"
        }
    
    def _initialize_escape_sequences(self) -> Set[str]:
        """Initialize escape sequence patterns."""
        return {
            "\\x", "\\u", "\\U", "\\n", "\\r", "\\t", "\\\\", "\\'", '\\"',
            "${", "<%", "%>", "{{", "}}", "[[", "]]", "``", "```"
        }
    
    async def sanitize(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, List[SecurityThreat]]:
        """
        Sanitize text for LLM input with multi-layer threat detection.
        
        Args:
            text: Input text to sanitize
            context: Additional context for analysis
            
        Returns:
            Tuple of (sanitized_text, detected_threats)
        """
        import time
        start_time = time.time()
        
        try:
            threats = []
            sanitized_text = text
            
            # Multi-layer threat detection
            for attack_type, patterns in self._threat_patterns.items():
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                    
                    for match in matches:
                        threat = SecurityThreat(
                            threat_level=self._calculate_threat_level(attack_type, match.group()),
                            attack_type=attack_type,
                            confidence=self._calculate_confidence(attack_type, match.group()),
                            pattern_matched=pattern,
                            position=match.start(),
                            original_text=match.group(),
                            sanitized_text=self._sanitize_match(match.group()),
                            metadata={
                                "context": context,
                                "pattern_type": "regex",
                                "match_length": len(match.group())
                            }
                        )
                        
                        threats.append(threat)
                        # Remove threat from text
                        sanitized_text = sanitized_text.replace(match.group(), threat.sanitized_text, 1)
            
            # Additional keyword-based detection
            keyword_threats = self._detect_keyword_threats(sanitized_text)
            threats.extend(keyword_threats)
            
            # Escape sequence detection and removal
            sanitized_text = self._remove_escape_sequences(sanitized_text)
            
            # Length and structure validation
            structure_threats = self._validate_structure(sanitized_text)
            threats.extend(structure_threats)
            
            # Update metrics
            self.inputs_sanitized += 1
            if threats:
                self.threats_detected += len(threats)
            
            processing_time = (time.time() - start_time) * 1000
            self.avg_sanitization_time_ms = (
                (self.avg_sanitization_time_ms * (self.inputs_sanitized - 1) + processing_time) /
                self.inputs_sanitized
            )
            
            self.logger.debug(f"Sanitized text in {processing_time:.2f}ms, {len(threats)} threats detected")
            return sanitized_text, threats
            
        except Exception as e:
            self.logger.error(f"Sanitization failed: {e}")
            return text, []
    
    def _calculate_threat_level(self, attack_type: AttackType, matched_text: str) -> ThreatLevel:
        """Calculate threat level based on attack type and content."""
        base_levels = {
            AttackType.DIRECT_INJECTION: ThreatLevel.HIGH,
            AttackType.INDIRECT_INJECTION: ThreatLevel.MEDIUM,
            AttackType.ROLE_PLAYING: ThreatLevel.MEDIUM,
            AttackType.SYSTEM_PROMPT: ThreatLevel.HIGH,
            AttackType.CODE_INJECTION: ThreatLevel.CRITICAL,
            AttackType.ESCAPE_SEQUENCE: ThreatLevel.LOW,
            AttackType.CONTEXT_MANIPULATION: ThreatLevel.MEDIUM,
            AttackType.DATA_EXFILTRATION: ThreatLevel.HIGH
        }
        
        base_level = base_levels.get(attack_type, ThreatLevel.LOW)
        
        # Adjust based on content
        if "jailbreak" in matched_text.lower() or "override" in matched_text.lower():
            return ThreatLevel.CRITICAL
        elif "system" in matched_text.lower() or "admin" in matched_text.lower():
            return ThreatLevel.HIGH
        
        return base_level
    
    def _calculate_confidence(self, attack_type: AttackType, matched_text: str) -> float:
        """Calculate confidence score for threat detection."""
        base_confidence = 0.8  # Base confidence for pattern matches
        
        # Increase confidence for specific indicators
        if "system" in matched_text.lower():
            base_confidence += 0.1
        if "ignore" in matched_text.lower() or "disregard" in matched_text.lower():
            base_confidence += 0.1
        if len(matched_text) > 20:  # Longer matches are more reliable
            base_confidence += 0.05
        
        return min(1.0, base_confidence)
    
    def _sanitize_match(self, matched_text: str) -> str:
        """Sanitize matched threat text."""
        # Replace with safe placeholder
        return "[REDACTED]"
    
    def _detect_keyword_threats(self, text: str) -> List[SecurityThreat]:
        """Detect threats based on suspicious keywords."""
        threats = []
        words = re.findall(r'\b\w+\b', text.lower())
        
        for i, word in enumerate(words):
            if word in self._suspicious_keywords:
                threat = SecurityThreat(
                    threat_level=ThreatLevel.LOW,
                    attack_type=AttackType.DATA_EXFILTRATION,
                    confidence=0.6,
                    pattern_matched=word,
                    position=i,
                    original_text=word,
                    sanitized_text="[FILTERED]",
                    metadata={"pattern_type": "keyword"}
                )
                threats.append(threat)
        
        return threats
    
    def _remove_escape_sequences(self, text: str) -> str:
        """Remove escape sequences from text."""
        for escape_seq in self._escape_sequences:
            text = text.replace(escape_seq, "")
        return text
    
    def _validate_structure(self, text: str) -> List[SecurityThreat]:
        """Validate text structure for anomalies."""
        threats = []
        
        # Check for excessive repetition (potential DoS)
        if len(text) > 10000:
            threat = SecurityThreat(
                threat_level=ThreatLevel.MEDIUM,
                attack_type=AttackType.CONTEXT_MANIPULATION,
                confidence=0.7,
                pattern_matched="excessive_length",
                position=0,
                original_text=text[:100] + "...",
                sanitized_text="[TRUNCATED]",
                metadata={"pattern_type": "structure", "length": len(text)}
            )
            threats.append(threat)
        
        # Check for excessive line breaks (potential structure manipulation)
        line_count = text.count('\n')
        if line_count > 100:
            threat = SecurityThreat(
                threat_level=ThreatLevel.LOW,
                attack_type=AttackType.CONTEXT_MANIPULATION,
                confidence=0.5,
                pattern_matched="excessive_line_breaks",
                position=0,
                original_text=f"[{line_count} lines]",
                sanitized_text="[NORMALIZED]",
                metadata={"pattern_type": "structure", "line_count": line_count}
            )
            threats.append(threat)
        
        return threats
    
    def get_security_report(self, threats: List[SecurityThreat]) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        if not threats:
            return {
                "status": "safe",
                "threat_count": 0,
                "max_threat_level": ThreatLevel.SAFE.value,
                "recommendations": ["Input is safe for processing"]
            }
        
        # Analyze threats
        threat_counts = {}
        max_level = ThreatLevel.SAFE
        
        for threat in threats:
            attack_type = threat.attack_type.value
            threat_counts[attack_type] = threat_counts.get(attack_type, 0) + 1
            
            if threat.threat_level.value > max_level.value:
                max_level = threat.threat_level
        
        # Generate recommendations
        recommendations = self._generate_recommendations(threats)
        
        return {
            "status": "threat_detected",
            "threat_count": len(threats),
            "max_threat_level": max_level.value,
            "threat_types": threat_counts,
            "recommendations": recommendations,
            "high_confidence_threats": [t for t in threats if t.confidence > 0.8],
            "critical_threats": [t for t in threats if t.threat_level == ThreatLevel.CRITICAL]
        }
    
    def _generate_recommendations(self, threats: List[SecurityThreat]) -> List[str]:
        """Generate security recommendations based on threats."""
        recommendations = []
        
        critical_count = sum(1 for t in threats if t.threat_level == ThreatLevel.CRITICAL)
        high_count = sum(1 for t in threats if t.threat_level == ThreatLevel.HIGH)
        
        if critical_count > 0:
            recommendations.append("CRITICAL: Immediate review required - potential system compromise")
        
        if high_count > 0:
            recommendations.append("HIGH: Review input for potential injection attacks")
        
        code_injection_count = sum(1 for t in threats if t.attack_type == AttackType.CODE_INJECTION)
        if code_injection_count > 0:
            recommendations.append("Code injection detected - all code blocks have been removed")
        
        system_prompt_count = sum(1 for t in threats if t.attack_type == AttackType.SYSTEM_PROMPT)
        if system_prompt_count > 0:
            recommendations.append("System prompt manipulation detected - system references removed")
        
        if len(threats) > 5:
            recommendations.append("Multiple threats detected - consider blocking this input source")
        
        if not recommendations:
            recommendations.append("Input sanitized successfully - safe for processing")
        
        return recommendations
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get security metrics."""
        return {
            "inputs_sanitized": self.inputs_sanitized,
            "threats_detected": self.threats_detected,
            "threat_rate": self.threats_detected / max(self.inputs_sanitized, 1),
            "avg_sanitization_time_ms": self.avg_sanitization_time_ms,
            "supported_attack_types": [t.value for t in AttackType],
            "threat_patterns_count": sum(len(patterns) for patterns in self._threat_patterns.values())
        }


class PromptInjectionDefense:
    """
    Comprehensive prompt injection defense system.
    
    Features:
    - Multi-layer detection
    - Context-aware analysis
    - Real-time blocking
    - Performance monitoring
    """
    
    def __init__(self, sanitizer: Optional[SecuritySanitizer] = None, logger: Optional[logging.Logger] = None):
        self.sanitizer = sanitizer or SecuritySanitizer(logger)
        self.logger = logger or logging.getLogger("PromptInjectionDefense")
        
        # Defense configuration
        self.block_critical_threats = True
        self.block_high_threats = False  # Allow but log
        self.max_threats_per_input = 10
        self.max_input_length = 50000
        
        self.logger.info("PromptInjectionDefense initialized")
    
    async def process_input(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
        allow_processing: bool = True
    ) -> Dict[str, Any]:
        """
        Process input with comprehensive defense.
        
        Args:
            text: Input text to process
            context: Additional context
            allow_processing: Whether to allow processing of threats
            
        Returns:
            Processing result with security analysis
        """
        try:
            # Initial validation
            if len(text) > self.max_input_length:
                return {
                    "success": False,
                    "error": "Input exceeds maximum length",
                    "sanitized_text": "",
                    "threats": [],
                    "security_report": {
                        "status": "blocked",
                        "reason": "excessive_length"
                    }
                }
            
            # Sanitize and detect threats
            sanitized_text, threats = await self.sanitizer.sanitize(text, context)
            
            # Generate security report
            security_report = self.sanitizer.get_security_report(threats)
            
            # Check if processing should be blocked
            should_block = self._should_block_processing(threats, allow_processing)
            
            if should_block:
                return {
                    "success": False,
                    "error": "Input blocked due to security threats",
                    "sanitized_text": "",
                    "threats": threats,
                    "security_report": security_report
                }
            
            return {
                "success": True,
                "sanitized_text": sanitized_text,
                "threats": threats,
                "security_report": security_report
            }
            
        except Exception as e:
            self.logger.error(f"Input processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "sanitized_text": "",
                "threats": [],
                "security_report": {"status": "error", "error": str(e)}
            }
    
    def _should_block_processing(self, threats: List[SecurityThreat], allow_processing: bool) -> bool:
        """Determine if processing should be blocked."""
        if not allow_processing:
            return True
        
        # Block critical threats
        if self.block_critical_threats:
            critical_threats = [t for t in threats if t.threat_level == ThreatLevel.CRITICAL]
            if critical_threats:
                return True
        
        # Block high threats if configured
        if self.block_high_threats:
            high_threats = [t for t in threats if t.threat_level == ThreatLevel.HIGH]
            if high_threats:
                return True
        
        # Block if too many threats
        if len(threats) > self.max_threats_per_input:
            return True
        
        return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get defense metrics."""
        sanitizer_metrics = self.sanitizer.get_metrics()
        
        return {
            **sanitizer_metrics,
            "defense_config": {
                "block_critical_threats": self.block_critical_threats,
                "block_high_threats": self.block_high_threats,
                "max_threats_per_input": self.max_threats_per_input,
                "max_input_length": self.max_input_length
            }
        }


# Global instances
_security_sanitizer: Optional[SecuritySanitizer] = None
_prompt_injection_defense: Optional[PromptInjectionDefense] = None


def get_security_sanitizer() -> SecuritySanitizer:
    """Get or create global security sanitizer."""
    global _security_sanitizer
    if _security_sanitizer is None:
        _security_sanitizer = SecuritySanitizer()
    return _security_sanitizer


def get_prompt_injection_defense() -> PromptInjectionDefense:
    """Get or create global prompt injection defense."""
    global _prompt_injection_defense
    if _prompt_injection_defense is None:
        _prompt_injection_defense = PromptInjectionDefense()
    return _prompt_injection_defense
