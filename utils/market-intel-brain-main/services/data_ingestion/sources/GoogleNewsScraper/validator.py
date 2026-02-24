"""
MAIFA v3 Google News Scraper Validator
Validates parsed Google News data
"""

from typing import Dict, Any, List
import logging
from datetime import datetime

from ...interfaces import DataValidator
from ...errors import ValidationError

class GoogleNewsScraperValidator(DataValidator):
    """Google News scraper data validator"""
    
    def __init__(self):
        self.logger = logging.getLogger("GoogleNewsScraperValidator")
        
    async def validate(self, parsed_data: Dict[str, Any]) -> bool:
        """Validate parsed Google News data"""
        try:
            # Check status
            if parsed_data.get("status") != "success":
                self.logger.warning(f"Validation failed: status is {parsed_data.get('status')}")
                return False
            
            # Check required fields
            required_fields = ["articles", "source", "total_articles"]
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
                required_article_fields = ["title", "link"]
                for field in required_article_fields:
                    if field not in article:
                        self.logger.warning(f"Validation failed: article {i} missing {field}")
                        return False
                
                # Validate title
                title = article.get("title", "")
                if not isinstance(title, str) or len(title.strip()) == 0:
                    self.logger.warning(f"Validation failed: article {i} title invalid")
                    return False
                
                # Validate link
                link = article.get("link", "")
                if not isinstance(link, str) or len(link.strip()) == 0:
                    self.logger.warning(f"Validation failed: article {i} link invalid")
                    return False
                
                # Validate URL format
                if link and not (link.startswith("http://") or link.startswith("https://")):
                    self.logger.warning(f"Validation failed: article {i} link not valid URL")
                    return False
                
                # Validate publication date if present
                pub_date = article.get("pub_date")
                if pub_date and not isinstance(pub_date, str):
                    self.logger.warning(f"Validation failed: article {i} pub_date not string")
                    return False
            
            # Validate total articles count
            total_articles = parsed_data.get("total_articles")
            if not isinstance(total_articles, (int, float)) or total_articles != len(articles):
                self.logger.warning("Validation failed: total_articles count mismatch")
                return False
            
            self.logger.debug("Google News scraper data validation passed")
            return True
            
        except Exception as e:
            raise ValidationError(
                source="GoogleNewsScraper",
                stage="validate",
                error_type=e.__class__.__name__,
                message=str(e),
                retryable=False
            )
