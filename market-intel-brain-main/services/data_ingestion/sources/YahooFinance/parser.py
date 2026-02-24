"""
MAIFA v3 Yahoo Finance Parser
Parses raw Yahoo Finance data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class YahooFinanceParser(DataParser):
    """Yahoo Finance data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("YahooFinanceParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Yahoo Finance data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "YahooFinance"
                }
            
            data = raw_data.get("data", {})
            chart = data.get("chart", {})
            
            if not chart or not chart.get("result"):
                return {
                    "status": "no_data",
                    "message": "No chart data available",
                    "source": "YahooFinance"
                }
            
            result = chart["result"][0]
            meta = result.get("meta", {})
            timestamps = result.get("timestamp", [])
            indicators = result.get("indicators", {})
            
            # Extract price data
            close_data = indicators.get("close", [{}])[0].get("data", [])
            volume_data = indicators.get("volume", [{}])[0].get("data", [])
            
            parsed_data = {
                "status": "success",
                "symbol": meta.get("symbol"),
                "currency": meta.get("currency"),
                "instrument_type": meta.get("instrumentType"),
                "first_trade_date": meta.get("firstTradeDate"),
                "regular_market_time": meta.get("regularMarketTime"),
                "gmtoffset": meta.get("gmtoffset"),
                "timezone": meta.get("timezone"),
                "exchange": meta.get("exchangeName"),
                "quote_type": meta.get("quoteType"),
                "data_points": [],
                "source": "YahooFinance",
                "parsed_at": datetime.now().isoformat()
            }
            
            # Create data points
            for i, timestamp in enumerate(timestamps):
                if i < len(close_data) and i < len(volume_data):
                    data_point = {
                        "timestamp": timestamp,
                        "datetime": datetime.fromtimestamp(timestamp).isoformat(),
                        "close": close_data[i],
                        "volume": volume_data[i]
                    }
                    parsed_data["data_points"].append(data_point)
            
            self.logger.info(f"Parsed {len(parsed_data['data_points'])} data points for {parsed_data['symbol']}")
            return parsed_data
            
        except Exception as e:
            self.logger.error(f"Yahoo Finance parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "YahooFinance"
            }
