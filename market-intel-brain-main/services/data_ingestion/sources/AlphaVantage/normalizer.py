"""
MAIFA v3 Alpha Vantage Normalizer
Normalizes validated Alpha Vantage data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class AlphaVantageNormalizer(DataNormalizer):
    """Alpha Vantage data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("AlphaVantageNormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated Alpha Vantage data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "AlphaVantage"
                }
            
            function = validated_data.get("function")
            data_points = validated_data.get("data_points", [])
            
            # Normalize based on function type
            if function == "TIME_SERIES_DAILY":
                return self._normalize_time_series(validated_data)
            elif function == "GLOBAL_QUOTE":
                return self._normalize_quote(validated_data)
            elif function == "NEWS_SENTIMENT":
                return self._normalize_news(validated_data)
            else:
                return self._normalize_generic(validated_data)
                
        except Exception as e:
            raise NormalizationError(
                source="AlphaVantage",
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
    
    def _normalize_time_series(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize time series data"""
        data_points = validated_data.get("data_points", [])
        
        normalized_data = {
            "status": "success",
            "source": "AlphaVantage",
            "symbol": validated_data.get("symbol"),
            "data_type": "stock_price_time_series",
            "timezone": validated_data.get("timezone"),
            "metadata": {
                "function": "TIME_SERIES_DAILY",
                "last_refreshed": validated_data.get("last_refreshed"),
                "original_source": "AlphaVantage",
                "normalized_at": datetime.now().isoformat()
            },
            "data": []
        }
        
        # Normalize each data point
        for point in data_points:
            normalized_point = {
                "timestamp": point["timestamp"],
                "datetime": point.get("date"),
                "open": point["open"],
                "high": point["high"],
                "low": point["low"],
                "close": point["close"],
                "volume": point["volume"],
                "source": "AlphaVantage"
            }
            normalized_data["data"].append(normalized_point)
        
        # Add summary statistics
        if normalized_data["data"]:
            closes = [p["close"] for p in normalized_data["data"]]
            volumes = [p["volume"] for p in normalized_data["data"]]
            
            normalized_data["summary"] = {
                "data_points_count": len(normalized_data["data"]),
                "date_range": {
                    "start": normalized_data["data"][0]["datetime"],
                    "end": normalized_data["data"][-1]["datetime"]
                },
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
        
        return normalized_data
    
    def _normalize_quote(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize quote data"""
        data_points = validated_data.get("data_points", [])
        point = data_points[0] if data_points else {}
        
        return {
            "status": "success",
            "source": "AlphaVantage",
            "symbol": validated_data.get("symbol"),
            "data_type": "stock_quote",
            "metadata": {
                "function": "GLOBAL_QUOTE",
                "timestamp": validated_data.get("timestamp"),
                "original_source": "AlphaVantage",
                "normalized_at": datetime.now().isoformat()
            },
            "data": [{
                "symbol": point.get("symbol"),
                "price": float(point.get("price", 0)),
                "change": float(point.get("change", 0)),
                "change_percent": point.get("change_percent", "0%"),
                "timestamp": validated_data.get("timestamp"),
                "source": "AlphaVantage"
            }]
        }
    
    def _normalize_news(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize news sentiment data"""
        data_points = validated_data.get("data_points", [])
        
        normalized_data = {
            "status": "success",
            "source": "AlphaVantage",
            "data_type": "news_sentiment",
            "metadata": {
                "function": "NEWS_SENTIMENT",
                "original_source": "AlphaVantage",
                "normalized_at": datetime.now().isoformat()
            },
            "data": []
        }
        
        # Normalize each news item
        for point in data_points:
            normalized_point = {
                "title": point.get("title"),
                "url": point.get("url"),
                "time_published": point.get("time_published"),
                "authors": point.get("authors", []),
                "summary": point.get("summary"),
                "banner_image": point.get("banner_image"),
                "source": point.get("source"),
                "category_within_source": point.get("category_within_source"),
                "source_domain": point.get("source_domain"),
                "topics": point.get("topics", []),
                "overall_sentiment_score": point.get("overall_sentiment_score"),
                "overall_sentiment_label": point.get("overall_sentiment_label"),
                "ticker_sentiment": point.get("ticker_sentiment", []),
                "source": "AlphaVantage"
            }
            normalized_data["data"].append(normalized_point)
        
        return normalized_data
    
    def _normalize_generic(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize generic data"""
        return {
            "status": "success",
            "source": "AlphaVantage",
            "data_type": "generic",
            "metadata": {
                "function": validated_data.get("function"),
                "original_source": "AlphaVantage",
                "normalized_at": datetime.now().isoformat()
            },
            "data": validated_data.get("data_points", [])
        }
