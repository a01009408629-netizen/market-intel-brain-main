"""
MAIFA v3 Trading Economics Normalizer
Normalizes validated Trading Economics data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class TradingEconomicsNormalizer(DataNormalizer):
    """Trading Economics data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("TradingEconomicsNormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated Trading Economics data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "TradingEconomics"
                }
            
            data_points = validated_data.get("data_points", [])
            
            # Normalize to standard format
            normalized_data = {
                "status": "success",
                "source": "TradingEconomics",
                "endpoint": validated_data.get("endpoint"),
                "country": validated_data.get("country"),
                "indicator": validated_data.get("indicator"),
                "data_type": "economic_indicator",
                "metadata": {
                    "original_source": "TradingEconomics",
                    "normalized_at": datetime.now().isoformat()
                },
                "data": []
            }
            
            # Normalize each data point
            for point in data_points:
                normalized_point = {
                    "date": point.get("date"),
                    "value": point.get("value"),
                    "symbol": point.get("symbol"),
                    "frequency": point.get("frequency"),
                    "indicator": point.get("indicator"),
                    "country": validated_data.get("country"),
                    "source": "TradingEconomics"
                }
                normalized_data["data"].append(normalized_point)
            
            # Add summary statistics
            if normalized_data["data"]:
                values = [p.get("value") for p in normalized_data["data"] if isinstance(p.get("value"), (int, float))]
                
                if values:
                    normalized_data["summary"] = {
                        "data_points_count": len(normalized_data["data"]),
                        "date_range": self._get_date_range(normalized_data["data"]),
                        "value_stats": {
                            "min": min(values),
                            "max": max(values),
                            "avg": sum(values) / len(values),
                            "latest": values[-1]
                        }
                    }
            
            self.logger.info(f"Normalized {len(normalized_data['data'])} economic data points")
            return normalized_data
            
        except Exception as e:
            raise NormalizationError(
                source="TradingEconomics",
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
    
    def _get_date_range(self, data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get date range from data points"""
        if not data_points:
            return {}
        
        dates = []
        for point in data_points:
            date = point.get("date")
            if date:
                dates.append(date)
        
        if not dates:
            return {}
        
        return {
            "earliest": min(dates),
            "latest": max(dates),
            "count": len(dates)
        }
