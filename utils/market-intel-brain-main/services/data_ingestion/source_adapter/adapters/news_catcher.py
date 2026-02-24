import asyncio
import logging
from typing import Any, Dict, Optional
from decimal import Decimal
from datetime import datetime
import httpx
import os

from ..base_adapter_v2 import BaseSourceAdapter
from ..validators.base_schema import NewsDataRequest
from ..normalization.unified_schema import UnifiedNewsData
from ..error_contract import (
    MaifaIngestionError, ProviderTimeoutError, ProviderRateLimitError,
    ProviderNetworkError, ProviderNotFoundError, ProviderValidationError
)


class NewsCatcherAdapter(BaseSourceAdapter):
    """NewsCatcher API adapter"""
    
    BASE_URL = "https://api.newscatcherapi.com/v2"
    
    def __init__(self, redis_client, api_key: Optional[str] = None, **kwargs):
        super().__init__(
            provider_name="NewsCatcher",
            base_url=self.BASE_URL,
            **kwargs
        )
        self.redis_client = redis_client
        self.api_key = api_key or os.getenv("NEWSCATCHER_API_KEY")
        
        if not self.api_key:
            raise MaifaIngestionError(
                message="API key is required for NewsCatcher",
                provider_name="NewsCatcher",
                suggested_action="Set NEWSCATCHER_API_KEY environment variable",
                is_transient=False
            )
    
    async def fetch(self, params: NewsDataRequest) -> Dict[str, Any]:
        """Fetch news data from NewsCatcher"""
        if not await self.validate_params(params):
            raise ProviderValidationError(
                provider_name="NewsCatcher",
                validation_errors={"params": "Invalid parameters"}
            )
        
        raw_data = await self._fetch_internal(params)
        normalized_data = await self.normalize_response(raw_data)
        return normalized_data.dict()
    
    async def validate_params(self, params: NewsDataRequest) -> bool:
        """Validate request parameters"""
        # NewsCatcher requires at least a query or sources
        return bool(params.query or params.sources)
    
    async def normalize_response(self, raw_data: Any) -> list[UnifiedNewsData]:
        """Normalize NewsCatcher response to unified format"""
        try:
            if isinstance(raw_data, dict) and 'articles' in raw_data:
                articles = raw_data['articles']
                normalized_articles = []
                
                for article in articles:
                    # Parse published date
                    published_at = datetime.utcnow()
                    if article.get('published_date'):
                        try:
                            # NewsCatcher returns ISO format
                            published_at = datetime.fromisoformat(article['published_date'].replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            pass
                    
                    # Extract symbols from title/content (basic implementation)
                    symbols_mentioned = []
                    title = article.get('title', '')
                    content = article.get('summary', '')
                    
                    # Simple symbol extraction (can be enhanced)
                    import re
                    symbol_pattern = r'\b[A-Z]{1,5}\b'
                    potential_symbols = re.findall(symbol_pattern, title + ' ' + content)
                    symbols_mentioned = list(set(potential_symbols))[:10]  # Limit to 10 symbols
                    
                    normalized_article = UnifiedNewsData(
                        title=article.get('title', ''),
                        content=article.get('summary', ''),
                        url=article.get('link', ''),
                        source=article.get('right', {}).get('source', '') or article.get('source', ''),
                        author=article.get('author'),
                        published_at=published_at,
                        categories=[article.get('topic')] if article.get('topic') else None,
                        tags=article.get('keywords', []) if article.get('keywords') else None,
                        language=article.get('language', 'en'),
                        symbols_mentioned=symbols_mentioned,
                        timestamp=datetime.utcnow(),
                        source_metadata={
                            "provider": "NewsCatcher",
                            "country": article.get('country'),
                            "media": article.get('media'),
                            "rank": article.get('rank'),
                            "raw_response": raw_data
                        }
                    )
                    normalized_articles.append(normalized_article)
                
                return normalized_articles
            
            raise MaifaIngestionError(
                message="Unexpected response format from NewsCatcher",
                provider_name="NewsCatcher",
                is_transient=False,
                context={"raw_data": raw_data}
            )
        
        except (ValueError, TypeError, KeyError) as e:
            raise MaifaIngestionError(
                message=f"Failed to normalize NewsCatcher response: {str(e)}",
                provider_name="NewsCatcher",
                is_transient=False,
                context={"raw_data": raw_data}
            )
    
    async def _fetch_internal(self, params: NewsDataRequest) -> Any:
        """Internal fetch method for NewsCatcher API"""
        try:
            request_params = {
                "api_key": self.api_key,
                "lang": params.language,
                "page_size": min(params.limit, 100)  # NewsCatcher max is 100
            }
            
            if params.query:
                request_params["q"] = params.query
            
            if params.sources:
                request_params["sources"] = ",".join(params.sources)
            
            if params.categories:
                request_params["topic"] = ",".join(params.categories)
            
            if params.from_date:
                request_params["from"] = params.from_date.strftime("%Y-%m-%d %H:%M:%S")
            
            if params.to_date:
                request_params["to"] = params.to_date.strftime("%Y-%m-%d %H:%M:%S")
            
            response = await self.get(
                "latest_headlines",
                params=request_params
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API errors
                if data.get('status') == 'error':
                    raise MaifaIngestionError(
                        message=f"NewsCatcher API error: {data.get('message', 'Unknown error')}",
                        provider_name="NewsCatcher",
                        is_transient=False,
                        context={"error": data}
                    )
                
                return data
            
            elif response.status_code == 401:
                raise MaifaIngestionError(
                    message="Invalid API key for NewsCatcher",
                    provider_name="NewsCatcher",
                    suggested_action="Check API key configuration",
                    is_transient=False
                )
            
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise ProviderRateLimitError(
                    provider_name="NewsCatcher",
                    retry_after=int(retry_after) if retry_after else 60
                )
            
            else:
                raise MaifaIngestionError(
                    message=f"NewsCatcher API error: HTTP {response.status_code}",
                    provider_name="NewsCatcher",
                    is_transient=response.status_code >= 500,
                    context={"status_code": response.status_code, "response": response.text}
                )
        
        except httpx.TimeoutException:
            raise ProviderTimeoutError(
                provider_name="NewsCatcher",
                timeout_seconds=self.timeout
            )
        
        except httpx.NetworkError as e:
            raise ProviderNetworkError(
                provider_name="NewsCatcher",
                network_error=str(e)
            )
        
        except MaifaIngestionError:
            raise
        
        except Exception as e:
            raise MaifaIngestionError(
                message=f"Unexpected error fetching from NewsCatcher: {str(e)}",
                provider_name="NewsCatcher",
                is_transient=True,
                context={"original_error": str(e)}
            )
