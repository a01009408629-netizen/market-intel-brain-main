//! Data Ingestion Service
//! 
//! Handles real-time ingestion of market data, news feeds, and
//! economic events from various financial data sources.

use std::collections::HashMap;
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::sync::{Mutex, RwLock};
use tokio::time::sleep;
use tracing::{info, warn, error, debug};
use anyhow::{Result, anyhow};
use serde::{Deserialize, Serialize};
use reqwest::Client;
use chrono::{DateTime, Utc, TimeZone};

use crate::proto::core_engine::*;

/// Data source configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataSourceConfig {
    pub source_type: String,
    pub url: String,
    pub rate_limit: u32,
    pub enabled: bool,
}

/// Market data structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketData {
    pub symbol: String,
    pub price: f64,
    pub volume: i64,
    pub timestamp: DateTime<Utc>,
    pub source: String,
    pub additional_data: HashMap<String, String>,
}

/// News item structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NewsItem {
    pub title: String,
    pub content: String,
    pub source: String,
    pub timestamp: DateTime<Utc>,
    pub sentiment_score: f64,
    pub relevance_score: f64,
}

/// Data ingestion service
pub struct DataIngestionService {
    client: Client,
    active_connections: Arc<RwLock<HashMap<String, ()>>>, // Track active connections
    data_sources: Arc<RwLock<HashMap<String, DataSourceConfig>>>,
    market_data_buffer: Arc<Mutex<Vec<MarketData>>>,
    news_buffer: Arc<Mutex<Vec<NewsItem>>>,
    max_buffer_size: usize,
}

impl DataIngestionService {
    /// Create a new data ingestion service
    pub fn new() -> Result<Self> {
        let client = Client::builder()
            .timeout(Duration::from_secs(30))
            .user_agent("MAIFA-Intelligence/1.0")
            .build()?;

        let service = Self {
            client,
            active_connections: Arc::new(RwLock::new(HashMap::new())),
            data_sources: Arc::new(RwLock::new(HashMap::new())),
            market_data_buffer: Arc::new(Mutex::new(Vec::new())),
            news_buffer: Arc::new(Mutex::new(Vec::new())),
            max_buffer_size: 1000,
        };

        // Setup default data sources
        service.setup_default_sources()?;

        Ok(service)
    }

    /// Setup default financial data sources
    fn setup_default_sources(&self) -> Result<()> {
        let mut sources = self.data_sources.write().map_err(|e| anyhow!("Lock error: {}", e))?;
        
        let default_sources = HashMap::from([
            ("yahoo_finance".to_string(), DataSourceConfig {
                source_type: "market_data".to_string(),
                url: "https://query1.finance.yahoo.com/v8/finance/chart/".to_string(),
                rate_limit: 100,
                enabled: true,
            }),
            ("alpha_vantage".to_string(), DataSourceConfig {
                source_type: "market_data".to_string(),
                url: "https://www.alphavantage.co/query".to_string(),
                rate_limit: 5,
                enabled: false, // Requires API key
            }),
            ("news_api".to_string(), DataSourceConfig {
                source_type: "news".to_string(),
                url: "https://newsapi.org/v2/everything".to_string(),
                rate_limit: 1000,
                enabled: false, // Requires API key
            }),
            ("financial_calendar".to_string(), DataSourceConfig {
                source_type: "events".to_string(),
                url: "https://api.example.com/calendar".to_string(),
                rate_limit: 60,
                enabled: false,
            }),
        ]);

        *sources = default_sources;
        info!("Default data sources configured");
        Ok(())
    }

    /// Connect to a data source
    pub async fn connect_data_source(&self, source_id: &str, api_key: Option<String>) -> Result<bool> {
        let sources = self.data_sources.read().map_err(|e| anyhow!("Lock error: {}", e))?;
        
        let source_config = sources.get(source_id)
            .ok_or_else(|| anyhow!("Unknown data source: {}", source_id))?;

        if !source_config.enabled {
            return Err(anyhow!("Data source {} is not enabled", source_id));
        }

        // Test connection with optional API key
        let mut headers = HashMap::new();
        if let Some(key) = api_key {
            headers.insert("Authorization".to_string(), format!("Bearer {}", key));
        }

        // For now, we'll just mark it as connected
        // In a real implementation, you'd test the connection
        let mut connections = self.active_connections.write().map_err(|e| anyhow!("Lock error: {}", e))?;
        connections.insert(source_id.to_string(), ());

        info!("Connected to data source: {}", source_id);
        Ok(true)
    }

    /// Fetch market data for specified symbols
    pub async fn fetch_market_data(&self, symbols: Vec<String>, source_id: &str) -> Result<Vec<MarketData>> {
        let sources = self.data_sources.read().map_err(|e| anyhow!("Lock error: {}", e))?;
        let source_config = sources.get(source_id)
            .ok_or_else(|| anyhow!("Unknown data source: {}", source_id))?;

        if !source_config.enabled {
            return Err(anyhow!("Data source {} is not enabled", source_id));
        }

        let mut market_data = Vec::new();

        for symbol in symbols {
            match self.fetch_symbol_data(&symbol, source_config).await {
                Ok(data) => {
                    if let Some(parsed_data) = data {
                        market_data.push(parsed_data.clone());
                        self.add_to_market_buffer(parsed_data).await?;
                    }
                }
                Err(e) => {
                    warn!("Error fetching data for {}: {}", symbol, e);
                }
            }

            // Rate limiting
            sleep(Duration::from_secs(60 / source_config.rate_limit as u64)).await;
        }

        info!("Fetched market data for {} symbols", market_data.len());
        Ok(market_data)
    }

    /// Fetch data for a single symbol from Yahoo Finance
    async fn fetch_symbol_data(&self, symbol: &str, config: &DataSourceConfig) -> Result<Option<MarketData>> {
        if config.source_type != "market_data" || !config.url.contains("yahoo.com") {
            return Ok(None);
        }

        let url = format!("{}{}", config.url, symbol);
        
        let response = self.client
            .get(&url)
            .send()
            .await
            .map_err(|e| anyhow!("HTTP request failed: {}", e))?;

        if !response.status().is_success() {
            return Err(anyhow!("HTTP error: {}", response.status()));
        }

        let data: serde_json::Value = response
            .json()
            .await
            .map_err(|e| anyhow!("JSON parsing failed: {}", e))?;

        self.parse_yahoo_finance_data(symbol, data)
    }

    /// Parse Yahoo Finance API response
    fn parse_yahoo_finance_data(&self, symbol: &str, data: serde_json::Value) -> Result<Option<MarketData>> {
        let result = data
            .pointer("/chart/result")
            .and_then(|r| r.as_array())
            .and_then(|arr| arr.first())
            .ok_or_else(|| anyhow!("No chart result found"))?;

        let meta = result
            .pointer("/meta")
            .ok_or_else(|| anyhow!("No meta data found"))?;

        let timestamps = result
            .pointer("/timestamp")
            .and_then(|t| t.as_array())
            .ok_or_else(|| anyhow!("No timestamps found"))?;

        let close_prices = result
            .pointer("/indicators/quote/0/close")
            .and_then(|c| c.as_array())
            .ok_or_else(|| anyhow!("No close prices found"))?;

        if timestamps.is_empty() || close_prices.is_empty() {
            return Ok(None);
        }

        // Get latest data
        let latest_timestamp = timestamps.last()
            .and_then(|t| t.as_i64())
            .ok_or_else(|| anyhow!("Invalid timestamp"))?;

        let latest_price = close_prices.last()
            .and_then(|p| p.as_f64())
            .ok_or_else(|| anyhow!("Invalid price"))?;

        let volume = meta
            .pointer("/regularMarketVolume")
            .and_then(|v| v.as_i64())
            .unwrap_or(0);

        let timestamp = Utc.timestamp_opt(latest_timestamp, 0)
            .single()
            .ok_or_else(|| anyhow!("Invalid timestamp conversion"))?;

        let mut additional_data = HashMap::new();
        
        if let Some(currency) = meta.pointer("/currency").and_then(|c| c.as_str()) {
            additional_data.insert("currency".to_string(), currency.to_string());
        }
        
        if let Some(market_state) = meta.pointer("/marketState").and_then(|s| s.as_str()) {
            additional_data.insert("market_state".to_string(), market_state.to_string());
        }
        
        if let Some(exchange) = meta.pointer("/exchangeName").and_then(|e| e.as_str()) {
            additional_data.insert("exchange".to_string(), exchange.to_string());
        }

        Ok(Some(MarketData {
            symbol: symbol.to_string(),
            price: latest_price,
            volume,
            timestamp,
            source: "yahoo_finance".to_string(),
            additional_data,
        }))
    }

    /// Fetch news data for specified keywords
    pub async fn fetch_news_data(&self, keywords: Vec<String>, source_id: &str, hours_back: i32) -> Result<Vec<NewsItem>> {
        let sources = self.data_sources.read().map_err(|e| anyhow!("Lock error: {}", e))?;
        let source_config = sources.get(source_id)
            .ok_or_else(|| anyhow!("Unknown data source: {}", source_id))?;

        if source_config.source_type != "news" {
            return Err(anyhow!("Source {} is not a news source", source_id));
        }

        let query = keywords.join(" OR ");
        let from_time = Utc::now() - chrono::Duration::hours(hours_back as i64);

        let mut params = HashMap::new();
        params.insert("q", &query);
        params.insert("from", &from_time.to_rfc3339());
        params.insert("sortBy", "publishedAt");
        params.insert("pageSize", "50");

        let response = self.client
            .get(&source_config.url)
            .query(&params)
            .send()
            .await
            .map_err(|e| anyhow!("HTTP request failed: {}", e))?;

        if !response.status().is_success() {
            return Err(anyhow!("HTTP error: {}", response.status()));
        }

        let data: serde_json::Value = response
            .json()
            .await
            .map_err(|e| anyhow!("JSON parsing failed: {}", e))?;

        let articles = data
            .pointer("/articles")
            .and_then(|a| a.as_array())
            .unwrap_or(&vec![]);

        let mut news_items = Vec::new();

        for article in articles {
            if let Ok(news_item) = self.parse_news_article(article, &keywords) {
                self.add_to_news_buffer(news_item.clone()).await?;
                news_items.push(news_item);
            }
        }

        info!("Fetched {} news items", news_items.len());
        Ok(news_items)
    }

    /// Parse a news article
    fn parse_news_article(&self, article: &serde_json::Value, keywords: &[String]) -> Result<NewsItem> {
        let title = article
            .pointer("/title")
            .and_then(|t| t.as_str())
            .unwrap_or("")
            .to_string();

        let content = article
            .pointer("/description")
            .and_then(|d| d.as_str())
            .unwrap_or("")
            .to_string();

        let source = article
            .pointer("/source/name")
            .and_then(|s| s.as_str())
            .unwrap_or("unknown")
            .to_string();

        let published_at = article
            .pointer("/publishedAt")
            .and_then(|p| p.as_str())
            .ok_or_else(|| anyhow!("No publishedAt found"))?;

        let timestamp = DateTime::parse_from_rfc3339(published_at)
            .map_err(|e| anyhow!("Date parsing failed: {}", e))?
            .with_timezone(&Utc);

        let relevance_score = self.calculate_news_relevance(&format!("{} {}", title, content), keywords);

        Ok(NewsItem {
            title,
            content,
            source,
            timestamp,
            sentiment_score: 0.0, // TODO: Implement sentiment analysis
            relevance_score,
        })
    }

    /// Calculate relevance score for news item
    fn calculate_news_relevance(&self, text: &str, keywords: &[String]) -> f64 {
        if keywords.is_empty() {
            return 0.0;
        }

        let text_lower = text.to_lowercase();
        let keyword_matches = keywords
            .iter()
            .filter(|keyword| text_lower.contains(&keyword.to_lowercase()))
            .count();

        (keyword_matches as f64 / keywords.len() as f64).min(1.0)
    }

    /// Add market data to buffer
    async fn add_to_market_buffer(&self, data: MarketData) -> Result<()> {
        let mut buffer = self.market_data_buffer.lock().map_err(|e| anyhow!("Lock error: {}", e))?;
        buffer.push(data);

        // Maintain buffer size
        if buffer.len() > self.max_buffer_size {
            buffer.drain(0..buffer.len() - self.max_buffer_size);
        }

        Ok(())
    }

    /// Add news item to buffer
    async fn add_to_news_buffer(&self, news: NewsItem) -> Result<()> {
        let mut buffer = self.news_buffer.lock().map_err(|e| anyhow!("Lock error: {}", e))?;
        buffer.push(news);

        // Maintain buffer size
        if buffer.len() > self.max_buffer_size {
            buffer.drain(0..buffer.len() - self.max_buffer_size);
        }

        Ok(())
    }

    /// Get market data from buffer
    pub async fn get_market_data(&self, symbol: Option<String>, limit: usize) -> Result<Vec<MarketData>> {
        let mut buffer = self.market_data_buffer.lock().map_err(|e| anyhow!("Lock error: {}", e))?;
        
        let mut data = buffer.clone();
        
        if let Some(sym) = symbol {
            data.retain(|item| item.symbol == sym);
        }

        // Sort by timestamp (newest first) and limit
        data.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        data.truncate(limit);

        Ok(data)
    }

    /// Get news data from buffer
    pub async fn get_news_data(&self, keywords: Option<Vec<String>>, limit: usize) -> Result<Vec<NewsItem>> {
        let mut buffer = self.news_buffer.lock().map_err(|e| anyhow!("Lock error: {}", e))?;
        
        let mut news = buffer.clone();
        
        if let Some(kws) = keywords {
            news.retain(|item| {
                kws.iter().any(|keyword| {
                    item.title.to_lowercase().contains(&keyword.to_lowercase()) ||
                    item.content.to_lowercase().contains(&keyword.to_lowercase())
                })
            });
        }

        // Sort by timestamp (newest first) and limit
        news.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
        news.truncate(limit);

        Ok(news)
    }

    /// Get ingestion statistics
    pub async fn get_ingestion_stats(&self) -> Result<IngestionStats> {
        let connections = self.active_connections.read().map_err(|e| anyhow!("Lock error: {}", e))?;
        let sources = self.data_sources.read().map_err(|e| anyhow!("Lock error: {}", e))?;
        let market_buffer = self.market_data_buffer.lock().map_err(|e| anyhow!("Lock error: {}", e))?;
        let news_buffer = self.news_buffer.lock().map_err(|e| anyhow!("Lock error: {}", e))?;

        let mut data_sources_info = HashMap::new();
        for (source_id, config) in sources.iter() {
            data_sources_info.insert(source_id.clone(), DataSourceInfo {
                r#type: config.source_type.clone(),
                enabled: config.enabled,
                connected: connections.contains_key(source_id),
            });
        }

        Ok(IngestionStats {
            active_connections: connections.len() as i32,
            configured_sources: sources.len() as i32,
            market_data_buffer_size: market_buffer.len() as i32,
            news_buffer_size: news_buffer.len() as i32,
            max_buffer_size: self.max_buffer_size as i32,
            data_sources: data_sources_info,
        })
    }

    /// Start background collection task
    pub async fn start_background_collection(&self) -> Result<()> {
        let service = self.clone();
        tokio::spawn(async move {
            service.background_collection_loop().await;
        });
        info!("Background collection task started");
        Ok(())
    }

    /// Background collection loop
    async fn background_collection_loop(&self) {
        loop {
            match self.background_collection().await {
                Ok(_) => debug!("Background collection completed successfully"),
                Err(e) => {
                    error!("Background collection error: {}", e);
                    sleep(Duration::from_secs(60)).await;
                }
            }
        }
    }

    /// Background collection task
    async fn background_collection(&self) -> Result<()> {
        // Collect data for major symbols every minute
        let major_symbols = vec![
            "AAPL".to_string(),
            "GOOGL".to_string(),
            "MSFT".to_string(),
            "AMZN".to_string(),
            "TSLA".to_string(),
            "BTC-USD".to_string(),
        ];

        if let Err(e) = self.fetch_market_data(major_symbols, "yahoo_finance").await {
            warn!("Failed to fetch market data in background: {}", e);
        }

        // Collect news every 5 minutes
        let now = Utc::now();
        if now.minute() % 5 == 0 {
            let financial_keywords = vec![
                "stock".to_string(),
                "market".to_string(),
                "trading".to_string(),
                "bitcoin".to_string(),
                "economy".to_string(),
            ];

            if let Err(e) = self.fetch_news_data(financial_keywords, "news_api", 24).await {
                warn!("Failed to fetch news data in background: {}", e);
            }
        }

        sleep(Duration::from_secs(60)).await;
        Ok(())
    }
}

impl Clone for DataIngestionService {
    fn clone(&self) -> Self {
        Self {
            client: self.client.clone(),
            active_connections: Arc::clone(&self.active_connections),
            data_sources: Arc::clone(&self.data_sources),
            market_data_buffer: Arc::clone(&self.market_data_buffer),
            news_buffer: Arc::clone(&self.news_buffer),
            max_buffer_size: self.max_buffer_size,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_data_ingestion_creation() {
        let service = DataIngestionService::new();
        assert!(service.is_ok());
        
        let service = service.unwrap();
        let stats = service.get_ingestion_stats().await.unwrap();
        assert_eq!(stats.configured_sources, 4); // Default sources
    }

    #[tokio::test]
    async fn test_connect_data_source() {
        let service = DataIngestionService::new().unwrap();
        
        // Test connecting to Yahoo Finance (should work without API key)
        let result = service.connect_data_source("yahoo_finance", None).await;
        assert!(result.is_ok());
        assert!(result.unwrap());
    }

    #[tokio::test]
    async fn test_connect_invalid_source() {
        let service = DataIngestionService::new().unwrap();
        
        let result = service.connect_data_source("invalid_source", None).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_market_data_buffer() {
        let service = DataIngestionService::new().unwrap();
        
        let test_data = MarketData {
            symbol: "TEST".to_string(),
            price: 100.0,
            volume: 1000,
            timestamp: Utc::now(),
            source: "test".to_string(),
            additional_data: HashMap::new(),
        };

        service.add_to_market_buffer(test_data.clone()).await.unwrap();
        
        let buffer_data = service.get_market_data(None, 10).await.unwrap();
        assert_eq!(buffer_data.len(), 1);
        assert_eq!(buffer_data[0].symbol, "TEST");
    }

    #[tokio::test]
    async fn test_news_relevance_calculation() {
        let service = DataIngestionService::new().unwrap();
        
        let text = "Stock market trading is booming with bitcoin economy";
        let keywords = vec!["stock".to_string(), "market".to_string()];
        
        let relevance = service.calculate_news_relevance(text, &keywords);
        assert_eq!(relevance, 1.0); // Both keywords found
        
        let relevance = service.calculate_news_relevance(text, &["crypto".to_string()]);
        assert_eq!(relevance, 0.0); // No keywords found
    }
}
