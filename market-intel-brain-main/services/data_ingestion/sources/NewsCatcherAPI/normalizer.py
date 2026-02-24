"""
MAIFA v3 News Catcher API Normalizer
Normalizes validated News Catcher API data to standard format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataNormalizer
from ...errors import NormalizationError

class NewsCatcherAPINormalizer(DataNormalizer):
    """News Catcher API data normalizer"""
    
    def __init__(self):
        self.logger = logging.getLogger("NewsCatcherAPINormalizer")
        
    async def normalize(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize validated News Catcher API data to standard format"""
        try:
            if validated_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": validated_data.get("error", "Validation failed"),
                    "source": "NewsCatcherAPI"
                }
            
            articles = validated_data.get("articles", [])
            pagination = validated_data.get("pagination", {})
            query_params = validated_data.get("query_params", {})
            
            # Normalize to standard format
            normalized_data = {
                "status": "success",
                "source": "NewsCatcherAPI",
                "data_type": "news_articles",
                "metadata": {
                    "query_params": query_params,
                    "pagination": pagination,
                    "total_articles": len(articles),
                    "original_source": "NewsCatcherAPI",
                    "normalized_at": datetime.now().isoformat()
                },
                "data": []
            }
            
            # Normalize each article
            for article in articles:
                normalized_article = {
                    "id": article.get("id"),
                    "title": article.get("title"),
                    "summary": article.get("summary"),
                    "content": article.get("content"),
                    "author": article.get("author"),
                    "authors": article.get("authors", []),
                    "published_date": article.get("published_date"),
                    "published_date_precision": article.get("published_date_precision"),
                    "url": article.get("link"),
                    "clean_url": article.get("clean_url"),
                    "excerpt": article.get("excerpt"),
                    "is_opinion": article.get("is_opinion", False),
                    "rank": article.get("rank"),
                    "topic": article.get("topic"),
                    "country": article.get("country"),
                    "category": article.get("category"),
                    "language": article.get("language"),
                    "media": article.get("media", []),
                    "rights": article.get("rights"),
                    "source": "NewsCatcherAPI"
                }
                normalized_data["data"].append(normalized_article)
            
            # Add summary statistics
            if normalized_data["data"]:
                topics = [a.get("topic") for a in normalized_data["data"] if a.get("topic")]
                countries = [a.get("country") for a in normalized_data["data"] if a.get("country")]
                languages = [a.get("language") for a in normalized_data["data"] if a.get("language")]
                
                normalized_data["summary"] = {
                    "total_articles": len(normalized_data["data"]),
                    "topics": list(set(topics)),
                    "countries": list(set(countries)),
                    "languages": list(set(languages)),
                    "date_range": self._get_date_range(normalized_data["data"]),
                    "opinion_articles": len([a for a in normalized_data["data"] if a.get("is_opinion")])
                }
            
            self.logger.info(f"Normalized {len(normalized_data['data'])} articles from News Catcher API")
            return normalized_data
            
        except Exception as e:
            raise NormalizationError(
                source="NewsCatcherAPI",
                stage="normalize",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
    
    def _get_date_range(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get date range from articles"""
        if not articles:
            return {}
        
        dates = []
        for article in articles:
            published_date = article.get("published_date")
            if published_date:
                dates.append(published_date)
        
        if not dates:
            return {}
        
        return {
            "earliest": min(dates),
            "latest": max(dates),
            "count": len(dates)
        }
