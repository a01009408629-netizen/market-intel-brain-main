"""
MAIFA v3 Data Sources
Individual modules for each data source
"""

# Import all sources
from . import YahooFinance
from . import AlphaVantage
from . import NewsCatcherAPI
from . import GoogleNewsScraper
from . import EconDB
from . import TradingEconomics
from . import MarketStack
from . import FinMind
from . import TwelveData
from . import Finnhub
from . import FinancialModelingPrep
from . import EuroStatFeeds
from . import IMFJsonFeeds

# Auto-register all sources
async def register_all_sources():
    """Auto-register all data sources"""
    from .YahooFinance import register_yahoo_finance
    from .AlphaVantage import register_alpha_vantage
    from .NewsCatcherAPI import register_news_catcher_api
    from .GoogleNewsScraper import register_google_news_scraper
    from .EconDB import register_econ_db
    from .TradingEconomics import register_trading_economics
    from .MarketStack import register_market_stack
    from .FinMind import register_fin_mind
    from .TwelveData import register_twelve_data
    from .Finnhub import register_finnhub
    from .FinancialModelingPrep import register_financial_modeling_prep
    from .EuroStatFeeds import register_eurostat_feeds
    from .IMFJsonFeeds import register_imf_json_feeds
    
    # Register all sources
    await register_yahoo_finance()
    await register_alpha_vantage()
    await register_news_catcher_api()
    await register_google_news_scraper()
    await register_econ_db()
    await register_trading_economics()
    await register_market_stack()
    await register_fin_mind()
    await register_twelve_data()
    await register_finnhub()
    await register_financial_modeling_prep()
    await register_eurostat_feeds()
    await register_imf_json_feeds()
