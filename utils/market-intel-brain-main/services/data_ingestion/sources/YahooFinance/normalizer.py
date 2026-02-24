"""
MAIFA v3 Yahoo Finance Normalizer
Normalizes validated Yahoo Finance data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class YahooFinanceNormalizer(DataNormalizer):
    """Yahoo Finance data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("YahooFinanceNormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated Yahoo Finance data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "YahooFinance"
                }
            
            # Extract data points
            data_points = validated_data.get("data_points", [])
            
            # Normalize to standard format
            normalized_data = {
                "status": "success",
                "source": "YahooFinance",
                "symbol": validated_data.get("symbol"),
                "data_type": "stock_price",
                "currency": validated_data.get("currency", "USD"),
                "exchange": validated_data.get("exchange"),
                "timezone": validated_data.get("timezone"),
                "metadata": {
                    "instrument_type": validated_data.get("instrument_type"),
                    "quote_type": validated_data.get("quote_type"),
                    "first_trade_date": validated_data.get("first_trade_date"),
                    "regular_market_time": validated_data.get("regular_market_time"),
                    "gmtoffset": validated_data.get("gmtoffset"),
                    "original_source": "YahooFinance",
                    "normalized_at": datetime.now().isoformat()
                },
                "data": []
            }
            
            # Normalize each data point
            for point in data_points:
                normalized_point = {
                    "timestamp": point["timestamp"],
                    "datetime": point.get("datetime", datetime.fromtimestamp(point["timestamp"]).isoformat()),
                    "open": point.get("open"),  # Yahoo Finance may not provide this
                    "high": point.get("high"),  # Yahoo Finance may not provide this
                    "low": point.get("low"),   # Yahoo Finance may not provide this
                    "close": point["close"],
                    "volume": point["volume"],
                    "adj_close": point.get("adj_close"),  # Adjusted close if available
                    "source": "YahooFinance"
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
            
            self.logger.info(f"Normalized {len(normalized_data['data'])} data points for {normalized_data['symbol']}")
            return normalized_data
            
        except Exception as e:
            raise NormalizationError(
                source="YahooFinance",
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
