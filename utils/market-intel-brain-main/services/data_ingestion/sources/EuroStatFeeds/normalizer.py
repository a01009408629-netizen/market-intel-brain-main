"""
MAIFA v3 EuroStat Feeds Normalizer
Normalizes validated EuroStat data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class EuroStatFeedsNormalizer(DataNormalizer):
    """EuroStat Feeds data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("EuroStatFeedsNormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated EuroStat data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "EuroStatFeeds"
                }
            
            data_points = validated_data.get("data_points", [])
            
            # Normalize to standard format
            normalized_data = {
                "status": "success",
                "source": "EuroStatFeeds",
                "dataset": validated_data.get("dataset"),
                "indicator": validated_data.get("indicator"),
                "country": validated_data.get("country"),
                "time_period": validated_data.get("time_period"),
                "data_type": "economic_indicator",
                "metadata": {
                    "original_source": "EuroStatFeeds",
                    "normalized_at": datetime.now().isoformat()
                },
                "data": []
            }
            
            # Normalize each data point
            for point in data_points:
                normalized_point = {
                    "period": point.get("period"),
                    "value": point.get("value"),
                    "dataset": validated_data.get("dataset"),
                    "indicator": validated_data.get("indicator"),
                    "country": validated_data.get("country"),
                    "time_period": validated_data.get("time_period"),
                    "field": point.get("field"),
                    "source": "EuroStatFeeds"
                }
                normalized_data["data"].append(normalized_point)
            
            # Add summary statistics
            if normalized_data["data"]:
                values = [p.get("value") for p in normalized_data["data"] if isinstance(p.get("value"), (int, float))]
                
                if values:
                    normalized_data["summary"] = {
                        "data_points_count": len(normalized_data["data"]),
                        "period_range": self._get_period_range(normalized_data["data"]),
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
                source="EuroStatFeeds",
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
    
    def _get_period_range(self, data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get period range from data points"""
        if not data_points:
            return {}
        
        periods = []
        for point in data_points:
            period = point.get("period")
            if period:
                periods.append(period)
        
        if not periods:
            return {}
        
        return {
            "earliest": min(periods),
            "latest": max(periods),
            "count": len(periods)
        }
