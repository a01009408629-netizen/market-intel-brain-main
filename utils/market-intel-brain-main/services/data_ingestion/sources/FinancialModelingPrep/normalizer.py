"""
MAIFA v3 Financial Modeling Prep Normalizer
Normalizes validated Financial Modeling Prep data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class FinancialModelingPrepNormalizer(DataNormalizer):
    """Financial Modeling Prep data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("FinancialModelingPrepNormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated Financial Modeling Prep data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "FinancialModelingPrep"
                }
            
            data_points = validated_data.get("data_points", [])
            
            # Normalize to standard format
            normalized_data = {
                "status": "success",
                "source": "FinancialModelingPrep",
                "endpoint": validated_data.get("endpoint"),
                "symbol": validated_data.get("symbol"),
                "data_type": "stock_price",
                "metadata": {
                    "original_source": "FinancialModelingPrep",
                    "normalized_at": datetime.now().isoformat()
                },
                "data": []
            }
            
            # Normalize each data point
            for point in data_points:
                normalized_point = {
                    "date": point.get("date"),
                    "open": point.get("open"),
                    "high": point.get("high"),
                    "low": point.get("low"),
                    "close": point.get("close"),
                    "volume": point.get("volume"),
                    "adj_close": point.get("adj_close"),
                    "unadjusted_volume": point.get("unadjusted_volume"),
                    "change": point.get("change"),
                    "change_percent": point.get("change_percent"),
                    "vwap": point.get("vwap"),
                    "label": point.get("label"),
                    "profile": point.get("profile"),
                    "field": point.get("field"),
                    "value": point.get("value"),
                    "source": "FinancialModelingPrep"
                }
                normalized_data["data"].append(normalized_point)
            
            # Add summary statistics
            if normalized_data["data"]:
                closes = [p.get("close") for p in normalized_data["data"] if isinstance(p.get("close"), (int, float))]
                volumes = [p.get("volume") for p in normalized_data["data"] if isinstance(p.get("volume"), (int, float))]
                
                if closes:
                    normalized_data["summary"] = {
                        "data_points_count": len(normalized_data["data"]),
                        "date_range": self._get_date_range(normalized_data["data"]),
                        "price_stats": {
                            "min": min(closes),
                            "max": max(closes),
                            "avg": sum(closes) / len(closes),
                            "latest": closes[-1]
                        },
                        "volume_stats": {
                            "total": sum(volumes),
                            "avg": sum(volumes) / len(volumes),
                            "max": max(volumes)
                        }
                    }
            
            self.logger.info(f"Normalized {len(normalized_data['data'])} financial data points")
            return normalized_data
            
        except Exception as e:
            raise NormalizationError(
                source="FinancialModelingPrep",
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
