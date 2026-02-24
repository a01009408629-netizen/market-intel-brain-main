"""
MAIFA v3 Google News Scraper Parser
Parses raw Google News data into structured format
"""

from typing import Dict, Any, List
import logging
from datetime import datetime
from bs4 import BeautifulSoup
import re

from ...interfaces import DataParser

class GoogleNewsScraperParser(DataParser):
    """Google News scraper parser"""
    
    def __init__(self):
        self.logger = logging.getLogger("GoogleNewsScraperParser")
        
    async def parse(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw Google News data"""
        try:
            if raw_data.get("status") != "success":
                return {
                    "status": "error",
                    "error": raw_data.get("error", "Unknown error"),
                    "source": "GoogleNewsScraper"
                }
            
            data = raw_data.get("data", {})
            soup_content = data.get("soup", "")
            
            if not soup_content:
                return {
                    "status": "no_data",
                    "message": "No RSS content available",
                    "source": "GoogleNewsScraper"
                }
            
            # Parse XML content
            soup = BeautifulSoup(soup_content, 'xml')
            
            # Extract items
            items = soup.find_all('item')
            
            if not items:
                return {
                    "status": "no_data",
                    "message": "No news items found",
                    "source": "GoogleNewsScraper"
                }
            
            parsed_articles = []
            for item in items:
                parsed_article = {
                    "title": self._extract_text(item.find('title')),
                    "link": self._extract_text(item.find('link')),
                    "description": self._extract_text(item.find('description')),
                    "pub_date": self._extract_text(item.find('pubDate')),
                    "source": self._extract_text(item.find('source')),
                    "guid": self._extract_text(item.find('guid')),
                    "categories": self._extract_categories(item),
                    "raw_xml": str(item)
                }
                parsed_articles.append(parsed_article)
            
            return {
                "status": "success",
                "articles": parsed_articles,
                "query_params": data.get("query_params", {}),
                "total_articles": len(parsed_articles),
                "source": "GoogleNewsScraper",
                "parsed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Google News scraper parse error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "source": "GoogleNewsScraper"
            }
    
    def _extract_text(self, element) -> str:
        """Extract text from XML element"""
        if element is None:
            return ""
        
        # Handle CDATA sections
        text = element.get_text(strip=True)
        
        # Clean up HTML entities
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'&#39;', "'", text)
        
        return text.strip()
    
    def _extract_categories(self, item) -> List[str]:
        """Extract categories from item"""
        categories = []
        category_elements = item.find_all('category')
        
        for cat_element in category_elements:
            category_text = self._extract_text(cat_element)
            if category_text:
                categories.append(category_text)
        
        return categories
