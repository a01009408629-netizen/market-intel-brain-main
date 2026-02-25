//! Unit tests for Data Ingestion Service

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Utc;
    use std::collections::HashMap;

    #[tokio::test]
    async fn test_data_ingestion_creation() {
        let service = DataIngestionService::new();
        assert!(service.is_ok());
        
        let service = service.unwrap();
        let stats = service.get_ingestion_stats().await.unwrap();
        assert_eq!(stats.configured_sources, 4); // Default sources
        assert_eq!(stats.active_connections, 0);
        assert_eq!(stats.market_data_buffer_size, 0);
        assert_eq!(stats.news_buffer_size, 0);
        assert_eq!(stats.max_buffer_size, 1000);
    }

    #[tokio::test]
    async fn test_connect_data_source() {
        let service = DataIngestionService::new().unwrap();
        
        // Test connecting to Yahoo Finance (should work without API key)
        let result = service.connect_data_source("yahoo_finance", None).await;
        assert!(result.is_ok());
        assert!(result.unwrap());
        
        // Verify connection is tracked
        let stats = service.get_ingestion_stats().await.unwrap();
        assert_eq!(stats.active_connections, 1);
        assert!(stats.data_sources.contains_key("yahoo_finance"));
        assert!(stats.data_sources["yahoo_finance"].connected);
    }

    #[tokio::test]
    async fn test_connect_invalid_source() {
        let service = DataIngestionService::new().unwrap();
        
        let result = service.connect_data_source("invalid_source", None).await;
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("Unknown data source"));
    }

    #[tokio::test]
    async fn test_connect_disabled_source() {
        let service = DataIngestionService::new().unwrap();
        
        // Try to connect to Alpha Vantage (disabled by default)
        let result = service.connect_data_source("alpha_vantage", None).await;
        assert!(result.is_err());
        assert!(result.unwrap_err().to_string().contains("not enabled"));
    }

    #[tokio::test]
    async fn test_market_data_buffer_operations() {
        let service = DataIngestionService::new().unwrap();
        
        // Create test market data
        let test_data = MarketData {
            symbol: "AAPL".to_string(),
            price: 150.25,
            volume: 1000000,
            timestamp: Utc::now(),
            source: "test".to_string(),
            additional_data: {
                let mut map = HashMap::new();
                map.insert("currency".to_string(), "USD".to_string());
                map.insert("market".to_string(), "NASDAQ".to_string());
                map
            },
        };

        // Add to buffer
        service.add_to_market_buffer(test_data.clone()).await.unwrap();
        
        // Get all data from buffer
        let buffer_data = service.get_market_data(None, 10).await.unwrap();
        assert_eq!(buffer_data.len(), 1);
        assert_eq!(buffer_data[0].symbol, "AAPL");
        assert_eq!(buffer_data[0].price, 150.25);
        assert_eq!(buffer_data[0].volume, 1000000);
        assert_eq!(buffer_data[0].source, "test");
        assert_eq!(buffer_data[0].additional_data.get("currency"), Some(&"USD".to_string()));
        
        // Get data for specific symbol
        let aapl_data = service.get_market_data(Some("AAPL".to_string()), 10).await.unwrap();
        assert_eq!(aapl_data.len(), 1);
        
        let goog_data = service.get_market_data(Some("GOOG".to_string()), 10).await.unwrap();
        assert_eq!(goog_data.len(), 0);
        
        // Test limit functionality
        for i in 1..=5 {
            let mut data = test_data.clone();
            data.symbol = format!("TEST{}", i);
            service.add_to_market_buffer(data).await.unwrap();
        }
        
        let limited_data = service.get_market_data(None, 3).await.unwrap();
        assert_eq!(limited_data.len(), 3);
    }

    #[tokio::test]
    async fn test_news_buffer_operations() {
        let service = DataIngestionService::new().unwrap();
        
        // Create test news item
        let test_news = NewsItem {
            title: "Stock Market Rally Continues".to_string(),
            content: "Technology stocks surge as investors remain optimistic about economic recovery".to_string(),
            source: "Financial Times".to_string(),
            timestamp: Utc::now(),
            sentiment_score: 0.8,
            relevance_score: 0.9,
        };

        // Add to buffer
        service.add_to_news_buffer(test_news.clone()).await.unwrap();
        
        // Get all news from buffer
        let buffer_news = service.get_news_data(None, 10).await.unwrap();
        assert_eq!(buffer_news.len(), 1);
        assert_eq!(buffer_news[0].title, "Stock Market Rally Continues");
        assert_eq!(buffer_news[0].source, "Financial Times");
        assert_eq!(buffer_news[0].sentiment_score, 0.8);
        assert_eq!(buffer_news[0].relevance_score, 0.9);
        
        // Get news with keyword filter
        let stock_news = service.get_news_data(Some(vec!["stock".to_string()]), 10).await.unwrap();
        assert_eq!(stock_news.len(), 1); // Should match "stock" in title
        
        let crypto_news = service.get_news_data(Some(vec!["bitcoin".to_string()]), 10).await.unwrap();
        assert_eq!(crypto_news.len(), 0); // No match
        
        // Test multiple keywords
        let multi_news = service.get_news_data(Some(vec!["technology".to_string(), "stocks".to_string()]), 10).await.unwrap();
        assert_eq!(multi_news.len(), 1); // Should match "technology" in content
    }

    #[tokio::test]
    async fn test_news_relevance_calculation() {
        let service = DataIngestionService::new().unwrap();
        
        let text = "Stock market trading is booming with bitcoin economy showing strong growth";
        let keywords = vec!["stock".to_string(), "market".to_string(), "bitcoin".to_string()];
        
        let relevance = service.calculate_news_relevance(text, &keywords);
        assert_eq!(relevance, 1.0); // All keywords found
        
        let relevance = service.calculate_news_relevance(text, &["crypto".to_string()]);
        assert_eq!(relevance, 0.0); // No keywords found
        
        let relevance = service.calculate_news_relevance(text, &["stock".to_string(), "crypto".to_string()]);
        assert_eq!(relevance, 0.5); // 1 out of 2 keywords found
        
        // Test with empty keywords
        let relevance = service.calculate_news_relevance(text, &[]);
        assert_eq!(relevance, 0.0);
        
        // Test case sensitivity
        let relevance = service.calculate_news_relevance(text, &["STOCK".to_string()]);
        assert_eq!(relevance, 1.0); // Should match case-insensitive
    }

    #[tokio::test]
    async fn test_buffer_size_limit() {
        let service = DataIngestionService::new();
        
        // Create service with small buffer for testing
        let mut service = service.unwrap();
        service.max_buffer_size = 3;
        
        // Add more items than buffer size
        for i in 1..=5 {
            let data = MarketData {
                symbol: format!("TEST{}", i),
                price: 100.0 + i as f64,
                volume: 1000,
                timestamp: Utc::now(),
                source: "test".to_string(),
                additional_data: HashMap::new(),
            };
            service.add_to_market_buffer(data).await.unwrap();
        }
        
        // Buffer should only contain the last 3 items
        let buffer_data = service.get_market_data(None, 10).await.unwrap();
        assert_eq!(buffer_data.len(), 3);
        assert_eq!(buffer_data[0].symbol, "TEST3");
        assert_eq!(buffer_data[1].symbol, "TEST4");
        assert_eq!(buffer_data[2].symbol, "TEST5");
    }

    #[tokio::test]
    async fn test_yahoo_finance_parsing() {
        let service = DataIngestionService::new().unwrap();
        
        // Mock Yahoo Finance response
        let mock_data = serde_json::json!({
            "chart": {
                "result": [{
                    "meta": {
                        "currency": "USD",
                        "marketState": "regular",
                        "exchangeName": "NASDAQ",
                        "regularMarketVolume": 1000000
                    },
                    "timestamp": [1640995200, 1640995260, 1640995320],
                    "indicators": {
                        "quote": [{
                            "close": [150.25, 150.50, 150.75]
                        }]
                    }
                }]
            }
        });

        let result = service.parse_yahoo_finance_data("AAPL", mock_data);
        assert!(result.is_ok());
        
        let market_data = result.unwrap();
        assert!(market_data.is_some());
        
        let data = market_data.unwrap();
        assert_eq!(data.symbol, "AAPL");
        assert_eq!(data.price, 150.75); // Latest price
        assert_eq!(data.volume, 1000000);
        assert_eq!(data.source, "yahoo_finance");
        assert_eq!(data.additional_data.get("currency"), Some(&"USD".to_string()));
        assert_eq!(data.additional_data.get("market_state"), Some(&"regular".to_string()));
        assert_eq!(data.additional_data.get("exchange"), Some(&"NASDAQ".to_string()));
    }

    #[tokio::test]
    async fn test_yahoo_finance_parsing_invalid_data() {
        let service = DataIngestionService::new().unwrap();
        
        // Test with empty response
        let empty_data = serde_json::json!({});
        let result = service.parse_yahoo_finance_data("AAPL", empty_data);
        assert!(result.is_ok());
        assert!(result.unwrap().is_none());
        
        // Test with no chart result
        let no_chart_data = serde_json::json!({
            "chart": {
                "result": []
            }
        });
        let result = service.parse_yahoo_finance_data("AAPL", no_chart_data);
        assert!(result.is_ok());
        assert!(result.unwrap().is_none());
        
        // Test with no timestamps
        let no_timestamps_data = serde_json::json!({
            "chart": {
                "result": [{
                    "meta": {},
                    "timestamp": [],
                    "indicators": {
                        "quote": [{
                            "close": [150.25]
                        }]
                    }
                }]
            }
        });
        let result = service.parse_yahoo_finance_data("AAPL", no_timestamps_data);
        assert!(result.is_ok());
        assert!(result.unwrap().is_none());
    }

    #[tokio::test]
    async fn test_news_article_parsing() {
        let service = DataIngestionService::new().unwrap();
        
        // Mock news article
        let mock_article = serde_json::json!({
            "title": "Tech Stocks Rally on Positive Earnings",
            "description": "Major technology companies reported better than expected earnings",
            "source": {
                "name": "Reuters"
            },
            "publishedAt": "2024-02-25T13:30:00Z"
        });

        let keywords = vec!["tech".to_string(), "stocks".to_string()];
        let result = service.parse_news_article(&mock_article, &keywords);
        assert!(result.is_ok());
        
        let news_item = result.unwrap();
        assert_eq!(news_item.title, "Tech Stocks Rally on Positive Earnings");
        assert_eq!(news_item.content, "Major technology companies reported better than expected earnings");
        assert_eq!(news_item.source, "Reuters");
        assert!(news_item.relevance_score > 0.0); // Should match keywords
    }

    #[tokio::test]
    async fn test_ingestion_stats() {
        let service = DataIngestionService::new().unwrap();
        
        // Connect to a data source
        service.connect_data_source("yahoo_finance", None).await.unwrap();
        
        // Add some test data
        let test_data = MarketData {
            symbol: "AAPL".to_string(),
            price: 150.25,
            volume: 1000000,
            timestamp: Utc::now(),
            source: "test".to_string(),
            additional_data: HashMap::new(),
        };
        service.add_to_market_buffer(test_data).await.unwrap();
        
        let test_news = NewsItem {
            title: "Test News".to_string(),
            content: "Test content".to_string(),
            source: "Test".to_string(),
            timestamp: Utc::now(),
            sentiment_score: 0.5,
            relevance_score: 0.7,
        };
        service.add_to_news_buffer(test_news).await.unwrap();
        
        // Get stats
        let stats = service.get_ingestion_stats().await.unwrap();
        assert_eq!(stats.active_connections, 1);
        assert_eq!(stats.configured_sources, 4);
        assert_eq!(stats.market_data_buffer_size, 1);
        assert_eq!(stats.news_buffer_size, 1);
        assert_eq!(stats.max_buffer_size, 1000);
        
        // Check data source info
        assert!(stats.data_sources.contains_key("yahoo_finance"));
        let yahoo_info = &stats.data_sources["yahoo_finance"];
        assert_eq!(yahoo_info.r#type, "market_data");
        assert!(yahoo_info.enabled);
        assert!(yahoo_info.connected);
    }

    #[tokio::test]
    async fn test_concurrent_buffer_access() {
        let service = std::sync::Arc::new(DataIngestionService::new().unwrap());
        
        // Spawn multiple tasks to add data concurrently
        let mut handles = vec![];
        
        for i in 0..10 {
            let service_clone = service.clone();
            let handle = tokio::spawn(async move {
                let data = MarketData {
                    symbol: format!("CONCURRENT{}", i),
                    price: 100.0 + i as f64,
                    volume: 1000,
                    timestamp: Utc::now(),
                    source: "test".to_string(),
                    additional_data: HashMap::new(),
                };
                
                service_clone.add_to_market_buffer(data).await.unwrap();
            });
            handles.push(handle);
        }
        
        // Wait for all tasks to complete
        for handle in handles {
            handle.await.unwrap();
        }
        
        // Verify all data was added
        let buffer_data = service.get_market_data(None, 20).await.unwrap();
        assert_eq!(buffer_data.len(), 10);
        
        // Verify symbols are unique
        let mut symbols: std::collections::HashSet<String> = std::collections::HashSet::new();
        for data in &buffer_data {
            symbols.insert(data.symbol.clone());
        }
        assert_eq!(symbols.len(), 10);
    }

    #[tokio::test]
    async fn test_error_handling() {
        let service = DataIngestionService::new().unwrap();
        
        // Test fetching from invalid source
        let result = service.fetch_market_data(vec!["AAPL".to_string()], "invalid_source").await;
        assert!(result.is_err());
        
        // Test fetching from disabled source
        let result = service.fetch_market_data(vec!["AAPL".to_string()], "alpha_vantage").await;
        assert!(result.is_err());
        
        // Test fetching news from invalid source
        let result = service.fetch_news_data(vec!["stock".to_string()], "invalid_source", 24).await;
        assert!(result.is_err());
        
        // Test fetching news from non-news source
        let result = service.fetch_news_data(vec!["stock".to_string()], "yahoo_finance", 24).await;
        assert!(result.is_err());
    }
}
