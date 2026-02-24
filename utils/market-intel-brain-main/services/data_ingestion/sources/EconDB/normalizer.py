"""
MAIFA v3 EconDB Normalizer
Normalizes validated EconDB data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class EconDBNormalizer(DataNormalizer):
    """EconDB data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("EconDBNormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated EconDB data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "EconDB"
                }
            
            data_points = validated_data.get("data_points", [])
            
            # Normalize to standard format
            normalized_data = {
                "status": "success",
                "source": "EconDB",
                "indicator": validated_data.get("indicator"),
                "country": validated_data.get("country"),
                "data_type": "economic_indicator",
                "metadata": {
                    "original_source": "EconDB",
                    "normalized_at": datetime.now().isoformat()
                },
                "data": []
            }
            
            # Normalize each data point
            for point in data_points:
                normalized_point = {
                    "period": point.get("period"),
                    "date": point.get("date"),
                    "value": point.get("value"),
                    "source": "EconDB"
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
                source="EconDB",
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
        dates = []
        
        for point in data_points:
            period = point.get("period")
            date = point.get("date")
            
            if period:
                periods.append(period)
            if date:
                dates.append(date)
        
        result = {}
        
        if periods:
            result["period_range"] = {
                "earliest": min(periods),
                "latest": max(periods),
                "count": len(periods)
            }
        
        if dates:
            result["date_range"] = {
                "earliest": min(dates),
                "latest": max(dates),
                "count": len(dates)
            }
        
        return result
