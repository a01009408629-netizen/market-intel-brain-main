"""
MAIFA v3 Google News Scraper Normalizer
Normalizes validated Google News data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class GoogleNewsScraperNormalizer(DataNormalizer):
    """Google News scraper data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("GoogleNewsScraperNormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated Google News data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "GoogleNewsScraper"
                }
            
            articles = validated_data.get("articles", [])
            query_params = validated_data.get("query_params", {})
            
            # Normalize to standard format
            normalized_data = {
                "status": "success",
                "source": "GoogleNewsScraper",
                "data_type": "news_articles",
                "metadata": {
                    "query_params": query_params,
                    "total_articles": len(articles),
                    "original_source": "GoogleNewsScraper",
                    "normalized_at": datetime.now().isoformat()
                },
                "data": []
            }
            
            # Normalize each article
            for article in articles:
                normalized_article = {
                    "id": article.get("guid"),
                    "title": article.get("title"),
                    "summary": self._clean_html(article.get("description", "")),
                    "content": self._clean_html(article.get("description", "")),
                    "author": article.get("source"),
                    "authors": [article.get("source")] if article.get("source") else [],
                    "published_date": article.get("pub_date"),
                    "url": article.get("link"),
                    "categories": article.get("categories", []),
                    "source": "GoogleNewsScraper",
                    "raw_xml": article.get("raw_xml", "")
                }
                normalized_data["data"].append(normalized_article)
            
            # Add summary statistics
            if normalized_data["data"]:
                sources = [a.get("source") for a in normalized_data["data"] if a.get("source")]
                categories = []
                for a in normalized_data["data"]:
                    categories.extend(a.get("categories", []))
                
                normalized_data["summary"] = {
                    "total_articles": len(normalized_data["data"]),
                    "unique_sources": list(set(sources)),
                    "unique_categories": list(set(categories)),
                    "date_range": self._get_date_range(normalized_data["data"])
                }
            
            self.logger.info(f"Normalized {len(normalized_data['data'])} articles from Google News")
            return normalized_data
            
        except Exception as e:
            raise NormalizationError(
                source="GoogleNewsScraper",
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
    
    def _clean_html(self, text: str) -> str:
        """Clean HTML tags from text"""
        if not text:
            return ""
        
        # Basic HTML tag removal
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&[^;]+;', '', text)
        return text.strip()
    
    def _get_date_range(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get date range from articles"""
        if not articles:
            return {}
        
        dates = []
        for article in articles:
            pub_date = article.get("published_date")
            if pub_date:
                dates.append(pub_date)
        
        if not dates:
            return {}
        
        return {
            "earliest": min(dates),
            "latest": max(dates),
            "count": len(dates)
        }
