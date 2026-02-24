"""
MAIFA v3 News Catcher API Parser
Parses raw News Catcher API data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataParser

class NewsCatcherAPIParser(DataParser):
    """News Catcher API data parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("NewsCatcherAPIParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw News Catcher API data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "NewsCatcherAPI"
                }
            
            data = raw_data.get("data", {})
            articles = data.get("articles", [])
            pagination = data.get("pagination", {})
            
            if not articles:
                return {
                    "status": "no_data",
                    "message": "No articles found",
                    "source": "NewsCatcherAPI"
                }
            
            parsed_articles = []
            for article in articles:
                parsed_article = {
                    "id": article.get("_id"),
                    "title": article.get("title"),
                    "summary": article.get("summary"),
                    "content": article.get("content"),
                    "author": article.get("author"),
                    "published_date": article.get("published_date"),
                    "published_date_precision": article.get("published_date_precision"),
                    "link": article.get("link"),
                    "clean_url": article.get("clean_url"),
                    "excerpt": article.get("excerpt"),
                    "is_opinion": article.get("is_opinion"),
                    "rank": article.get("rank"),
                    "topic": article.get("topic"),
                    "country": article.get("country"),
                    "category": article.get("category"),
                    "language": article.get("language"),
                    "authors": article.get("authors", []),
                    "media": article.get("media", []),
                    "rights": article.get("rights")
                }
                parsed_articles.append(parsed_article)
            
            return {
                "status": "success",
                "articles": parsed_articles,
                "pagination": {
                    "current_page": pagination.get("current_page"),
                    "next_page": pagination.get("next_page"),
                    "total_pages": pagination.get("total_pages"),
                    "total_hits": pagination.get("total_hits"),
                    "page_size": pagination.get("page_size")
                },
                "query_params": raw_data.get("query_params", {}),
                "source": "NewsCatcherAPI",
                "parsed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"News Catcher API parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "NewsCatcherAPI"
            }
