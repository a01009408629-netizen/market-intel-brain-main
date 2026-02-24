"""
MAIFA v3 IMF Json Feeds Normalizer
Normalizes validated IMF data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class IMFJsonFeedsNormalizer(DataNormalizer):
    """IMF Json Feeds data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("IMFJsonFeedsNormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated IMF data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "IMFJsonFeeds"
                }
            
            data_points = validated_data.get("data_points", [])
            
            # Normalize to standard format
            normalized_data = {
                "status": "success",
                "source": "IMFJsonFeeds",
                "endpoint": validated_data.get("endpoint"),
                "series_code": validated_data.get("series_code"),
                "country": validated_data.get("country"),
                "data_type": "economic_indicator",
                "metadata": {
                    "original_source": "IMFJsonFeeds",
                    "normalized_at": datetime.now().isoformat()
                },
                "data": []
            }
            
            # Normalize each data point
            for point in data_points:
                normalized_point = {
                    "year": point.get("year"),
                    "value": point.get("value"),
                    "series_code": validated_data.get("series_code"),
                    "country": validated_data.get("country"),
                    "field": point.get("field"),
                    "source": "IMFJsonFeeds"
                }
                normalized_data["data"].append(normalized_point)
            
            # Add summary statistics
            if normalized_data["data"]:
                values = [p.get("value") for p in normalized_data["data"] if isinstance(p.get("value"), (int, float))]
                
                if values:
                    normalized_data["summary"] = {
                        "data_points_count": len(normalized_data["data"]),
                        "year_range": self._get_year_range(normalized_data["data"]),
                        "value_stats": {
                            "min": min(values),
                            "max": max(values),
                            "avg": sum(values) / len(values),
                            "latest": values[-1]
                        }
                    }
            
            self.logger.info(f"Normalized {len(normalized_data['data'])} monetary data points")
            return normalized_data
            
        except Exception as e:
            raise NormalizationError(
                source="IMFJsonFeeds",
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
    
    def _get_year_range(self, data_points: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get year range from data points"""
        if not data_points:
            return {}
        
        years = []
        for point in data_points:
            year = point.get("year")
            if year:
                years.append(year)
        
        if not years:
            return {}
        
        return {
            "earliest": min(years),
            "latest": max(years),
            "count": len(years)
        }
