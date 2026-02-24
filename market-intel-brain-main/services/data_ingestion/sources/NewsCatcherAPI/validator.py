"""
MAIFA v3 News Catcher API Validator
Validates parsed News Catcher API data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class NewsCatcherAPIValidator(DataValidator):
    """News Catcher API data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("NewsCatcherAPIValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed News Catcher API data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["articles", "source", "pagination"]
            for field in required_fields:
                if field not in parsed_data:
                    self.logger.warning(f"Validation failed: missing field {field}")
                    return False
            
            # Check articles
            articles = parsed_data.get("articles", [])
            if not articles:
                self.logger.warning("Validation failed: no articles")
                return False
            
            # Validate each article
            for i, article in enumerate(articles):
                if not isinstance(article, dict):
                    self.logger.warning(f"Validation failed: article {i} is not a dict")
                    return False
                
                # Check required article fields
                required_article_fields = ["title", "link", "published_date"]
                for field in required_article_fields:
                    if field not in article:
                        self.logger.warning(f"Validation failed: article {i} missing {field}")
                        return False
                
                # Validate published date
                published_date = article.get("published_date")
                if published_date and not isinstance(published_date, str):
                    self.logger.warning(f"Validation failed: article {i} published_date not string")
                    return False
                
                # Validate URL
                link = article.get("link")
                if link and not isinstance(link, str):
                    self.logger.warning(f"Validation failed: article {i} link not string")
                    return False
                
                # Validate rank
                rank = article.get("rank")
                if rank is not None and not isinstance(rank, (int, float)):
                    self.logger.warning(f"Validation failed: article {i} rank not numeric")
                    return False
            
            # Validate pagination
            pagination = parsed_data.get("pagination", {})
            if pagination:
                numeric_fields = ["current_page", "total_pages", "total_hits", "page_size"]
                for field in numeric_fields:
                    value = pagination.get(field)
                    if value is not None and not isinstance(value, (int, float)):
                        self.logger.warning(f"Validation failed: pagination {field} not numeric")
                        return False
            
            self.logger.debug("News Catcher API data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="NewsCatcherAPI",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
