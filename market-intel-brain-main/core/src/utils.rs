//! Utility functions for the Market Intel Brain platform

use chrono::{DateTime, Utc};
use rust_decimal::Decimal;
use std::collections::HashMap;
use uuid::Uuid;

use crate::types::*;
use crate::errors::MarketIntelError;

/// Generate a unique entity ID
pub fn generate_entity_id() -> EntityId {
    Uuid::new_v4()
}

/// Get current timestamp
pub fn now() -> Timestamp {
    Utc::now()
}

/// Parse symbol string to normalized format
pub fn normalize_symbol(symbol: &str) -> Symbol {
    symbol.to_uppercase().trim().to_string()
}

/// Validate symbol format
pub fn validate_symbol(symbol: &str) -> Result<()> {
    let normalized = normalize_symbol(symbol);
    
    if normalized.is_empty() {
        return Err(MarketIntelError::validation("symbol", "Symbol cannot be empty"));
    }
    
    if normalized.len() > 32 {
        return Err(MarketIntelError::validation("symbol", "Symbol too long (max 32 characters)"));
    }
    
    // Check for valid characters (letters, numbers, dots, hyphens)
    if !normalized.chars().all(|c| c.is_alphanumeric() || c == '.' || c == '-' || c == '_') {
        return Err(MarketIntelError::validation("symbol", "Symbol contains invalid characters"));
    }
    
    Ok(())
}

/// Parse string to decimal with validation
pub fn parse_decimal(value: &str) -> Result<Decimal> {
    value.parse::<Decimal>()
        .map_err(|_| MarketIntelError::validation("decimal", "Invalid decimal format"))
}

/// Validate price value
pub fn validate_price(price: Decimal) -> Result<()> {
    if price <= Decimal::ZERO {
        return Err(MarketIntelError::validation("price", "Price must be positive"));
    }
    
    if price > Decimal::from(1_000_000_000) {
        return Err(MarketIntelError::validation("price", "Price too large (max 1 billion)"));
    }
    
    Ok(())
}

/// Validate quantity value
pub fn validate_quantity(quantity: Decimal) -> Result<()> {
    if quantity <= Decimal::ZERO {
        return Err(MarketIntelError::validation("quantity", "Quantity must be positive"));
    }
    
    if quantity > Decimal::from(1_000_000_000) {
        return Err(MarketIntelError::validation("quantity", "Quantity too large (max 1 billion)"));
    }
    
    Ok(())
}

/// Calculate percentage change
pub fn calculate_percentage_change(old_value: Decimal, new_value: Decimal) -> Decimal {
    if old_value == Decimal::ZERO {
        return Decimal::ZERO;
    }
    
    ((new_value - old_value) / old_value) * Decimal::from(100)
}

/// Calculate mid price from bid and ask
pub fn calculate_mid_price(bid: Decimal, ask: Decimal) -> Decimal {
    (bid + ask) / Decimal::from(2)
}

/// Calculate spread from bid and ask
pub fn calculate_spread(bid: Decimal, ask: Decimal) -> Decimal {
    ask - bid
}

/// Calculate spread percentage
pub fn calculate_spread_percentage(bid: Decimal, ask: Decimal) -> Decimal {
    let mid = calculate_mid_price(bid, ask);
    if mid == Decimal::ZERO {
        return Decimal::ZERO;
    }
    
    (calculate_spread(bid, ask) / mid) * Decimal::from(100)
}

/// Round decimal to specified precision
pub fn round_to_precision(value: Decimal, precision: u32) -> Decimal {
    let scaler = Decimal::from(10_i64.pow(precision));
    (value * scaler).round() / scaler
}

/// Format price with appropriate precision
pub fn format_price(price: Decimal) -> String {
    if price < Decimal::from(1) {
        format!("{:.6}", price)
    } else if price < Decimal::from(100) {
        format!("{:.4}", price)
    } else {
        format!("{:.2}", price)
    }
}

/// Format percentage
pub fn format_percentage(value: Decimal) -> String {
    format!("{:.2}%", value)
}

/// Parse timeframe string (e.g., "1m", "5m", "1h", "1d")
pub fn parse_timeframe(timeframe: &str) -> Result<(u32, &str)> {
    let chars: Vec<char> = timeframe.chars().collect();
    if chars.len() < 2 {
        return Err(MarketIntelError::validation("timeframe", "Invalid timeframe format"));
    }
    
    let number_str: String = chars[..chars.len()-1].iter().collect();
    let unit = &chars[chars.len()-1..];
    
    let number = number_str.parse::<u32>()
        .map_err(|_| MarketIntelError::validation("timeframe", "Invalid number in timeframe"))?;
    
    if number == 0 {
        return Err(MarketIntelError::validation("timeframe", "Timeframe number must be positive"));
    }
    
    match unit {
        "s" | "m" | "h" | "d" | "w" | "M" | "y" => Ok((number, unit)),
        _ => Err(MarketIntelError::validation("timeframe", "Invalid timeframe unit (use s, m, h, d, w, M, y)")),
    }
}

/// Convert timeframe to seconds
pub fn timeframe_to_seconds(number: u32, unit: &str) -> u32 {
    match unit {
        "s" => number,
        "m" => number * 60,
        "h" => number * 60 * 60,
        "d" => number * 60 * 60 * 24,
        "w" => number * 60 * 60 * 24 * 7,
        "M" => number * 60 * 60 * 24 * 30, // Approximate
        "y" => number * 60 * 60 * 24 * 365, // Approximate
        _ => 0,
    }
}

/// Validate timestamp is not in the future (with some tolerance)
pub fn validate_timestamp(timestamp: Timestamp, tolerance_seconds: i64) -> Result<()> {
    let now = Utc::now();
    let diff = timestamp.signed_duration_since(now);
    
    if diff.num_seconds() > tolerance_seconds {
        return Err(MarketIntelError::validation("timestamp", "Timestamp is too far in the future"));
    }
    
    Ok(())
}

/// Calculate age of timestamp in seconds
pub fn timestamp_age_seconds(timestamp: Timestamp) -> i64 {
    let now = Utc::now();
    now.signed_duration_since(timestamp).num_seconds()
}

/// Check if timestamp is recent (within specified seconds)
pub fn is_recent_timestamp(timestamp: Timestamp, within_seconds: i64) -> bool {
    timestamp_age_seconds(timestamp).abs() <= within_seconds
}

/// Merge two metadata maps
pub fn merge_metadata(
    base: HashMap<String, serde_json::Value>,
    overlay: HashMap<String, serde_json::Value>,
) -> HashMap<String, serde_json::Value> {
    let mut result = base;
    for (key, value) in overlay {
        result.insert(key, value);
    }
    result
}

/// Extract numeric value from JSON
pub fn extract_numeric_from_json(value: &serde_json::Value) -> Option<Decimal> {
    match value {
        serde_json::Value::Number(n) => n.as_f64().map(|f| Decimal::from_f64(f).unwrap_or_default()),
        serde_json::Value::String(s) => s.parse::<Decimal>().ok(),
        _ => None,
    }
}

/// Convert decimal to JSON value
pub fn decimal_to_json(value: Decimal) -> serde_json::Value {
    serde_json::Value::String(value.to_string())
}

/// Create a standard metadata map
pub fn create_metadata() -> HashMap<String, serde_json::Value> {
    HashMap::new()
}

/// Add metadata entry
pub fn add_metadata(
    mut metadata: HashMap<String, serde_json::Value>,
    key: &str,
    value: impl Into<serde_json::Value>,
) -> HashMap<String, serde_json::Value> {
    metadata.insert(key.to_string(), value.into());
    metadata
}

/// Get metadata value
pub fn get_metadata<T>(
    metadata: &HashMap<String, serde_json::Value>,
    key: &str,
) -> Option<T>
where
    T: serde::de::DeserializeOwned,
{
    metadata.get(key).and_then(|v| serde_json::from_value(v.clone()).ok())
}

/// Remove metadata entry
pub fn remove_metadata(
    mut metadata: HashMap<String, serde_json::Value>,
    key: &str,
) -> HashMap<String, serde_json::Value> {
    metadata.remove(key);
    metadata
}

/// Calculate hash of data for integrity checks
pub fn calculate_data_hash(data: &[u8]) -> String {
    use std::hash::{Hash, Hasher};
    use std::collections::hash_map::DefaultHasher;
    
    let mut hasher = DefaultHasher::new();
    data.hash(&mut hasher);
    format!("{:x}", hasher.finish())
}

/// Validate data integrity
pub fn validate_data_integrity(data: &[u8], expected_hash: &str) -> Result<()> {
    let actual_hash = calculate_data_hash(data);
    if actual_hash != expected_hash {
        return Err(MarketIntelError::validation("integrity", "Data integrity check failed"));
    }
    Ok(())
}

/// Retry function with exponential backoff
pub async fn retry_with_backoff<F, T, E>(
    mut operation: F,
    max_attempts: u32,
    initial_delay_ms: u64,
    max_delay_ms: u64,
) -> Result<T>
where
    F: FnMut() -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<T, E>> + Send>>,
    E: Into<MarketIntelError>,
{
    let mut delay = initial_delay_ms;
    
    for attempt in 1..=max_attempts {
        match operation().await {
            Ok(result) => return Ok(result),
            Err(err) if attempt == max_attempts => {
                return Err(err.into());
            }
            Err(_) => {
                tokio::time::sleep(tokio::time::Duration::from_millis(delay)).await;
                delay = std::cmp::min(delay * 2, max_delay_ms);
            }
        }
    }
    
    unreachable!()
}

/// Batch processing utility
pub async fn process_batch<T, R, F, Fut>(
    items: Vec<T>,
    batch_size: usize,
    processor: F,
) -> Vec<R>
where
    F: Fn(Vec<T>) -> Fut + Send + Sync,
    Fut: std::future::Future<Output = Vec<R>> + Send,
{
    let mut results = Vec::new();
    
    for chunk in items.chunks(batch_size) {
        let batch_results = processor(chunk.to_vec()).await;
        results.extend(batch_results);
    }
    
    results
}

/// Rate limiter implementation
pub struct RateLimiter {
    requests_per_second: u32,
    tokens: f64,
    last_update: std::time::Instant,
}

impl RateLimiter {
    /// Create new rate limiter
    pub fn new(requests_per_second: u32) -> Self {
        Self {
            requests_per_second,
            tokens: requests_per_second as f64,
            last_update: std::time::Instant::now(),
        }
    }
    
    /// Check if request is allowed
    pub fn is_allowed(&mut self) -> bool {
        let now = std::time::Instant::now();
        let elapsed = now.duration_since(self.last_update).as_secs_f64();
        
        // Add tokens based on elapsed time
        self.tokens += elapsed * self.requests_per_second as f64;
        self.tokens = self.tokens.min(self.requests_per_second as f64);
        
        self.last_update = now;
        
        if self.tokens >= 1.0 {
            self.tokens -= 1.0;
            true
        } else {
            false
        }
    }
    
    /// Get time until next request is allowed
    pub fn time_until_allowed(&self) -> std::time::Duration {
        if self.tokens >= 1.0 {
            std::time::Duration::ZERO
        } else {
            let tokens_needed = 1.0 - self.tokens;
            let seconds_needed = tokens_needed / self.requests_per_second as f64;
            std::time::Duration::from_secs_f64(seconds_needed)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_symbol_normalization() {
        assert_eq!(normalize_symbol("aapl"), "AAPL");
        assert_eq!(normalize_symbol("  msft  "), "MSFT");
        assert_eq!(normalize_symbol("GOOG"), "GOOG");
    }

    #[test]
    fn test_symbol_validation() {
        assert!(validate_symbol("AAPL").is_ok());
        assert!(validate_symbol("").is_err());
        assert!(validate_symbol("TOOLONGSYMBOLNAME123456789").is_err());
        assert!(validate_symbol("INVALID@SYMBOL").is_err());
    }

    #[test]
    fn test_price_validation() {
        assert!(validate_price(Decimal::from(100)).is_ok());
        assert!(validate_price(Decimal::ZERO).is_err());
        assert!(validate_price(Decimal::from(-1)).is_err());
    }

    #[test]
    fn test_percentage_change() {
        let old = Decimal::from(100);
        let new = Decimal::from(110);
        let change = calculate_percentage_change(old, new);
        assert_eq!(change, Decimal::from(10));
    }

    #[test]
    fn test_mid_price() {
        let bid = Decimal::from(99);
        let ask = Decimal::from(101);
        let mid = calculate_mid_price(bid, ask);
        assert_eq!(mid, Decimal::from(100));
    }

    #[test]
    fn test_spread() {
        let bid = Decimal::from(99);
        let ask = Decimal::from(101);
        let spread = calculate_spread(bid, ask);
        assert_eq!(spread, Decimal::from(2));
    }

    #[test]
    fn test_timeframe_parsing() {
        assert_eq!(parse_timeframe("1m").unwrap(), (1, "m"));
        assert_eq!(parse_timeframe("5m").unwrap(), (5, "m"));
        assert_eq!(parse_timeframe("1h").unwrap(), (1, "h"));
        assert!(parse_timeframe("invalid").is_err());
    }

    #[test]
    fn test_rate_limiter() {
        let mut limiter = RateLimiter::new(10);
        
        // Should allow first request
        assert!(limiter.is_allowed());
        
        // Should allow subsequent requests until tokens run out
        for _ in 0..9 {
            assert!(limiter.is_allowed());
        }
        
        // Should deny when tokens are exhausted
        assert!(!limiter.is_allowed());
    }
}
