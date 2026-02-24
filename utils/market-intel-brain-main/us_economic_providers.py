"""
U.S. Economic Data Providers
Government sources for American economic data
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from decimal import Decimal

from tradfi_providers import TradFiBaseProvider, AsyncJitter
from infrastructure.data_normalization import UnifiedInternalSchema, DataType, SourceType


class BLSProvider(TradFiBaseProvider):
    """U.S. Bureau of Labor Statistics - Free economic data."""
    
    def __init__(self):
        super().__init__("bls", SourceType.REST)
        self.base_url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
        # BLS doesn't require API key for public data
        
    async def connect(self) -> bool:
        """Test BLS connection."""
        try:
            await super().connect()
            
            # Test with unemployment rate
            test_url = f"{self.base_url}?registrationkey=&seriesid=LNS14000000&latest=true"
            async with self.session.get(test_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"BLS connection error: {e}")
            return False
    
    async def get_data(self, series_id: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get economic data from BLS."""
        try:
            url = f"{self.base_url}?registrationkey=&seriesid={series_id}&latest=true"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if 'Results' not in data or not data['Results']:
                    return []
                
                result = data['Results']['series'][0]
                if 'data' not in result or not result['data']:
                    return []
                
                latest_data = result['data'][0]
                
                return [self.normalize_data({
                    'series_id': series_id,
                    'value': latest_data.get('value', '0'),
                    'date': latest_data.get('year', '') + '-' + latest_data.get('period', 'M01').replace('M', ''),
                    'series_name': result.get('seriesTitle', series_id)
                })]
                
        except Exception as e:
            print(f"BLS data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize BLS data."""
        date_str = raw_data.get('date', '')
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m').replace(tzinfo=timezone.utc)
            except:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return UnifiedInternalSchema(
            data_type=DataType.MACRO,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('series_id', ''),
            timestamp=dt,
            value=Decimal(str(raw_data.get('value', '0'))),
            raw_data=raw_data,
            processing_latency_ms=2.0
        )


class BEAProvider(TradFiBaseProvider):
    """Bureau of Economic Analysis - GDP and economic data."""
    
    def __init__(self):
        super().__init__("bea", SourceType.REST)
        self.base_url = "https://apps.bea.gov/api/data/"
        # BEA requires free registration for API key
        
    async def connect(self) -> bool:
        """Test BEA connection."""
        try:
            await super().connect()
            
            # Test with GDP data (using public dataset)
            test_url = f"{self.base_url}?UserID=YOUR_API_KEY&method=GetData&datasetname=NIPA&TableName=T10101&Frequency=A&Year=2023&ResultFormat=JSON"
            
            # For now, just test connection to BEA
            async with self.session.get("https://apps.bea.gov/api/data/") as response:
                return response.status == 200
                
        except Exception as e:
            print(f"BEA connection error: {e}")
            return False
    
    async def get_data(self, table_name: str, **kwargs) -> List[UnifiedInternalSchema]:
        """Get economic data from BEA."""
        try:
            # This would need a real API key
            url = f"{self.base_url}?UserID=YOUR_API_KEY&method=GetData&datasetname=NIPA&TableName={table_name}&Frequency=A&Year=2023&ResultFormat=JSON"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                # Parse BEA response format
                if 'BEAAPI' not in data or 'Results' not in data['BEAAPI']:
                    return []
                
                results = data['BEAAPI']['Results']
                if not results:
                    return []
                
                # Get latest data point
                latest = results[-1]
                
                return [self.normalize_data({
                    'table_name': table_name,
                    'value': latest.get('DataValue', '0'),
                    'date': latest.get('TimePeriod', ''),
                    'line_description': latest.get('LineDescription', '')
                })]
                
        except Exception as e:
            print(f"BEA data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize BEA data."""
        date_str = raw_data.get('date', '')
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y').replace(tzinfo=timezone.utc)
            except:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return UnifiedInternalSchema(
            data_type=DataType.MACRO,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('table_name', ''),
            timestamp=dt,
            value=Decimal(str(raw_data.get('value', '0'))),
            raw_data=raw_data,
            processing_latency_ms=2.5
        )


class TreasuryProvider(TradFiBaseProvider):
    """U.S. Treasury - Interest rates and debt data."""
    
    def __init__(self):
        super().__init__("treasury", SourceType.REST)
        self.base_url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/debt_to_penny"
        
    async def connect(self) -> bool:
        """Test Treasury connection."""
        try:
            await super().connect()
            
            async with self.session.get(self.base_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Treasury connection error: {e}")
            return False
    
    async def get_data(self, data_type: str = "debt", **kwargs) -> List[UnifiedInternalSchema]:
        """Get Treasury data."""
        try:
            if data_type == "debt":
                url = self.base_url
            else:
                # For yields and other data
                url = f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/avg_interest_rates"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if 'data' not in data or not data['data']:
                    return []
                
                latest_data = data['data'][-1]
                
                return [self.normalize_data({
                    'data_type': data_type,
                    'value': latest_data.get('tot_pub_debt_out_amt', '0'),
                    'date': latest_data.get('record_date', ''),
                    'source_table': 'debt_to_penny'
                })]
                
        except Exception as e:
            print(f"Treasury data fetch error: {e}")
            return []
    
    def normalize_data(self, raw_data: Dict[str, Any]) -> UnifiedInternalSchema:
        """Normalize Treasury data."""
        date_str = raw_data.get('date', '')
        if date_str:
            try:
                dt = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            except:
                dt = datetime.now(timezone.utc)
        else:
            dt = datetime.now(timezone.utc)
        
        return UnifiedInternalSchema(
            data_type=DataType.MACRO,
            source=self.source_name,
            source_type=self.source_type,
            symbol=raw_data.get('data_type', ''),
            timestamp=dt,
            value=Decimal(str(raw_data.get('value', '0'))),
            raw_data=raw_data,
            processing_latency_ms=1.8
        )


class ReutersEconomicsProvider(TradFiBaseProvider):
    """Reuters Economics - Economic news and data."""
    
    def __init__(self):
        super().__init__("reuters_economics", SourceType.RSS)
        self.rss_url = "https://www.reuters.com/business/economy/"
        
    async def connect(self) -> bool:
        """Test Reuters connection."""
        try:
            await super().connect()
            
            async with self.session.get(self.rss_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Reuters connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get economic news from Reuters."""
        try:
            # Use RSS feed for Reuters
            rss_url = "https://www.reuters.com/rssFeed/businessNews"
            
            async with self.session.get(rss_url) as response:
                if response.status != 200:
                    return []
                
                xml_content = await response.text()
                
                # Parse RSS XML
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_content)
                
                news_items = []
                
                # Find all items
                items = root.findall('.//item')
                
                for item in items[:20]:  # Limit to 20 items
                    try:
                        title_elem = item.find('title')
                        title = title_elem.text if title_elem is not None else ''
                        
                        desc_elem = item.find('description')
                        description = desc_elem.text if desc_elem is not None else ''
                        
                        link_elem = item.find('link')
                        url = link_elem.text if link_elem is not None else ''
                        
                        # Parse date
                        date_elem = item.find('pubDate')
                        if date_elem is not None:
                            date_str = date_elem.text
                            try:
                                dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
                            except:
                                dt = datetime.now(timezone.utc)
                        else:
                            dt = datetime.now(timezone.utc)
                        
                        news_item = UnifiedInternalSchema(
                            data_type=DataType.NEWS,
                            source=self.source_name,
                            source_type=self.source_type,
                            symbol="",  # Economic news is general
                            timestamp=dt,
                            title=title,
                            content=description,
                            url=url,
                            relevance_score=0.9,
                            tags=["economics", "us", "reuters"],
                            raw_data={"title": title, "description": description, "url": url},
                            processing_latency_ms=2.0
                        )
                        
                        news_items.append(news_item)
                        
                    except Exception as e:
                        print(f"Error parsing Reuters item: {e}")
                        continue
                
                return news_items
                
        except Exception as e:
            print(f"Reuters data fetch error: {e}")
            return []


class APNewsEconomicsProvider(TradFiBaseProvider):
    """AP News Economics - Economic news."""
    
    def __init__(self):
        super().__init__("ap_economics", SourceType.RSS)
        self.rss_url = "https://feeds.apnews.com/business/economy"
        
    async def connect(self) -> bool:
        """Test AP News connection."""
        try:
            await super().connect()
            
            async with self.session.get(self.rss_url) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"AP News connection error: {e}")
            return False
    
    async def get_data(self, symbol: str = "", **kwargs) -> List[UnifiedInternalSchema]:
        """Get economic news from AP News."""
        try:
            async with self.session.get(self.rss_url) as response:
                if response.status != 200:
                    return []
                
                xml_content = await response.text()
                
                # Parse RSS XML
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_content)
                
                news_items = []
                
                # Find all items
                items = root.findall('.//item')
                
                for item in items[:15]:  # Limit to 15 items
                    try:
                        title_elem = item.find('title')
                        title = title_elem.text if title_elem is not None else ''
                        
                        desc_elem = item.find('description')
                        description = desc_elem.text if desc_elem is not None else ''
                        
                        link_elem = item.find('link')
                        url = link_elem.text if link_elem is not None else ''
                        
                        # Parse date
                        date_elem = item.find('pubDate')
                        if date_elem is not None:
                            date_str = date_elem.text
                            try:
                                dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z').replace(tzinfo=timezone.utc)
                            except:
                                dt = datetime.now(timezone.utc)
                        else:
                            dt = datetime.now(timezone.utc)
                        
                        news_item = UnifiedInternalSchema(
                            data_type=DataType.NEWS,
                            source=self.source_name,
                            source_type=self.source_type,
                            symbol="",
                            timestamp=dt,
                            title=title,
                            content=description,
                            url=url,
                            relevance_score=0.85,
                            tags=["economics", "us", "ap"],
                            raw_data={"title": title, "description": description, "url": url},
                            processing_latency_ms=2.2
                        )
                        
                        news_items.append(news_item)
                        
                    except Exception as e:
                        print(f"Error parsing AP News item: {e}")
                        continue
                
                return news_items
                
        except Exception as e:
            print(f"AP News data fetch error: {e}")
            return []


# Factory for U.S. Economic providers
class USEconomicProviderFactory:
    """Factory for U.S. economic data providers."""
    
    def __init__(self):
        self._providers = {
            "bls": BLSProvider,
            "bea": BEAProvider,
            "treasury": TreasuryProvider,
            "reuters_economics": ReutersEconomicsProvider,
            "ap_economics": APNewsEconomicsProvider,
        }
    
    def create_provider(self, name: str) -> TradFiBaseProvider:
        """Create a U.S. economic provider instance."""
        if name not in self._providers:
            raise ValueError(f"Unknown U.S. economic provider: {name}")
        
        return self._providers[name]()
    
    def list_providers(self) -> List[str]:
        """List available U.S. economic providers."""
        return list(self._providers.keys())


# Global factory instance
_us_economic_provider_factory: Optional[USEconomicProviderFactory] = None


def get_us_economic_provider_factory() -> USEconomicProviderFactory:
    """Get global U.S. economic provider factory."""
    global _us_economic_provider_factory
    if _us_economic_provider_factory is None:
        _us_economic_provider_factory = USEconomicProviderFactory()
    return _us_economic_provider_factory


async def main():
    """Test U.S. economic providers."""
    factory = get_us_economic_provider_factory()
    
    print("Testing U.S. Economic Data Providers")
    print("=" * 50)
    
    # Test BLS (unemployment rate)
    print("\n1. Testing BLS (Bureau of Labor Statistics):")
    try:
        provider = factory.create_provider("bls")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data("LNS14000000")  # Unemployment rate
            print(f"   Connected: {connected}, Data: {len(data)} items")
            if data:
                print(f"   Unemployment Rate: {data[0].value}")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Treasury (debt data)
    print("\n2. Testing Treasury:")
    try:
        provider = factory.create_provider("treasury")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data("debt")
            print(f"   Connected: {connected}, Data: {len(data)} items")
            if data:
                print(f"   Total Debt: {data[0].value}")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Reuters Economics
    print("\n3. Testing Reuters Economics:")
    try:
        provider = factory.create_provider("reuters_economics")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data()
            print(f"   Connected: {connected}, News: {len(data)} items")
            if data:
                print(f"   Latest: {data[0].title[:50]}...")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test AP News Economics
    print("\n4. Testing AP News Economics:")
    try:
        provider = factory.create_provider("ap_economics")
        connected = await provider.connect()
        if connected:
            data = await provider.get_data()
            print(f"   Connected: {connected}, News: {len(data)} items")
            if data:
                print(f"   Latest: {data[0].title[:50]}...")
        await provider.disconnect()
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nU.S. Economic providers test completed!")


if __name__ == "__main__":
    asyncio.run(main())
