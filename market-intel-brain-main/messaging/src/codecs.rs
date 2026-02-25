//! Message codecs for encoding/decoding and compression/encryption

use crate::core::*;
use crate::message_types::*;
use bytes::{Bytes, BytesMut};
use prost::Message;
use ring::aead::{Aad, LessSafeKey, Nonce, UnboundKey, AES_256_GCM};
use ring::rand::{SecureRandom, SystemRandom};
use std::io::{Read, Write};
use tracing::{debug, error};

/// Message codec trait
#[async_trait]
pub trait MessageCodec: Send + Sync {
    /// Encode message to bytes
    fn encode(&self, message: &UnifiedMessage) -> Result<Vec<u8>>;
    
    /// Decode message from bytes
    fn decode(&self, data: &[u8]) -> Result<UnifiedMessage>;
    
    /// Compress data
    fn compress(&self, data: &[u8]) -> Result<Vec<u8>>;
    
    /// Decompress data
    fn decompress(&self, data: &[u8]) -> Result<Vec<u8>>;
    
    /// Encrypt data
    fn encrypt(&self, data: &[u8]) -> Result<Vec<u8>>;
    
    /// Decrypt data
    fn decrypt(&self, data: &[u8]) -> Result<Vec<u8>>;
    
    /// Get codec name
    fn name(&self) -> &str;
    
    /// Get codec version
    fn version(&self) -> &str;
}

/// Protocol Buffers codec
pub struct ProstCodec {
    compression_type: CompressionType,
    encryption_key: Option<Vec<u8>>,
}

impl ProstCodec {
    /// Create new Prost codec
    pub fn new(compression_type: CompressionType) -> Self {
        Self {
            compression_type,
            encryption_key: None,
        }
    }
    
    /// Create codec with encryption
    pub fn with_encryption(compression_type: CompressionType, key: Vec<u8>) -> Self {
        Self {
            compression_type,
            encryption_key: Some(key),
        }
    }
    
    /// Compress data using configured algorithm
    fn compress_data(&self, data: &[u8]) -> Result<Vec<u8>> {
        match self.compression_type {
            CompressionType::None => Ok(data.to_vec()),
            CompressionType::LZ4 => self.compress_lz4(data),
            CompressionType::Zstd => self.compress_zstd(data),
            CompressionType::Gzip => self.compress_gzip(data),
        }
    }
    
    /// Decompress data using configured algorithm
    fn decompress_data(&self, data: &[u8]) -> Result<Vec<u8>> {
        match self.compression_type {
            CompressionType::None => Ok(data.to_vec()),
            CompressionType::LZ4 => self.decompress_lz4(data),
            CompressionType::Zstd => self.decompress_zstd(data),
            CompressionType::Gzip => self.decompress_gzip(data),
        }
    }
    
    /// LZ4 compression
    fn compress_lz4(&self, data: &[u8]) -> Result<Vec<u8>> {
        // Use lz4_flex for compression
        let compressed = lz4_flex::block::compress(data);
        Ok(compressed)
    }
    
    /// LZ4 decompression
    fn decompress_lz4(&self, data: &[u8]) -> Result<Vec<u8>> {
        let decompressed = lz4_flex::block::decompress(data, None)
            .map_err(|e| MarketIntelError::serialization(format!("LZ4 decompression failed: {}", e)))?;
        Ok(decompressed)
    }
    
    /// Zstd compression
    fn compress_zstd(&self, data: &[u8]) -> Result<Vec<u8>> {
        let compressed = zstd::encode_all(data, 3)
            .map_err(|e| MarketIntelError::serialization(format!("Zstd compression failed: {}", e)))?;
        Ok(compressed)
    }
    
    /// Zstd decompression
    fn decompress_zstd(&self, data: &[u8]) -> Result<Vec<u8>> {
        let decompressed = zstd::decode_all(data)
            .map_err(|e| MarketIntelError::serialization(format!("Zstd decompression failed: {}", e)))?;
        Ok(decompressed)
    }
    
    /// Gzip compression
    fn compress_gzip(&self, data: &[u8]) -> Result<Vec<u8>> {
        use flate2::write::GzEncoder;
        use flate2::Compression;
        
        let mut encoder = GzEncoder::new(Vec::new(), Compression::fast());
        encoder.write_all(data)
            .map_err(|e| MarketIntelError::serialization(format!("Gzip compression failed: {}", e)))?;
        
        let compressed = encoder.finish()
            .map_err(|e| MarketIntelError::serialization(format!("Gzip compression failed: {}", e)))?;
        Ok(compressed)
    }
    
    /// Gzip decompression
    fn decompress_gzip(&self, data: &[u8]) -> Result<Vec<u8>> {
        use flate2::read::GzDecoder;
        
        let mut decoder = GzDecoder::new(data);
        let mut decompressed = Vec::new();
        decoder.read_to_end(&mut decompressed)
            .map_err(|e| MarketIntelError::serialization(format!("Gzip decompression failed: {}", e)))?;
        Ok(decompressed)
    }
    
    /// Encrypt data using AES-256-GCM
    fn encrypt_data(&self, data: &[u8]) -> Result<Vec<u8>> {
        let key = self.encryption_key.as_ref()
            .ok_or_else(|| MarketIntelError::authentication("Encryption key not set"))?;
        
        // Create unbound key
        let unbound_key = UnboundKey::new(&AES_256_GCM, key)
            .map_err(|e| MarketIntelError::authentication(format!("Failed to create encryption key: {}", e)))?;
        
        // Create less safe key
        let less_safe_key = LessSafeKey::new(unbound_key);
        
        // Generate random nonce
        let rng = SystemRandom::new();
        let mut nonce_bytes = [0u8; 12];
        rng.fill(&mut nonce_bytes)
            .map_err(|e| MarketIntelError::authentication(format!("Failed to generate nonce: {}", e)))?;
        let nonce = Nonce::assume_unique_for_key(nonce_bytes);
        
        // Encrypt data
        let mut in_out = data.to_vec();
        let mut tag = [0u8; 16];
        less_safe_key.seal_in_place_separate_tag(nonce, Aad::empty(), &mut in_out, &mut tag)
            .map_err(|e| MarketIntelError::authentication(format!("Encryption failed: {}", e)))?;
        
        // Combine nonce + ciphertext + tag
        let mut encrypted = Vec::with_capacity(nonce_bytes.len() + in_out.len() + tag.len());
        encrypted.extend_from_slice(&nonce_bytes);
        encrypted.extend_from_slice(&in_out);
        encrypted.extend_from_slice(&tag);
        
        Ok(encrypted)
    }
    
    /// Decrypt data using AES-256-GCM
    fn decrypt_data(&self, encrypted_data: &[u8]) -> Result<Vec<u8>> {
        let key = self.encryption_key.as_ref()
            .ok_or_else(|| MarketIntelError::authentication("Encryption key not set"))?;
        
        if encrypted_data.len() < 28 { // 12 bytes nonce + 16 bytes tag minimum
            return Err(MarketIntelError::authentication("Invalid encrypted data length"));
        }
        
        // Extract nonce, ciphertext, and tag
        let nonce_bytes = &encrypted_data[..12];
        let ciphertext_len = encrypted_data.len() - 28;
        let ciphertext = &encrypted_data[12..12 + ciphertext_len];
        let tag = &encrypted_data[12 + ciphertext_len..];
        
        // Create unbound key
        let unbound_key = UnboundKey::new(&AES_256_GCM, key)
            .map_err(|e| MarketIntelError::authentication(format!("Failed to create encryption key: {}", e)))?;
        
        // Create less safe key
        let less_safe_key = LessSafeKey::new(unbound_key);
        
        // Create nonce
        let nonce = Nonce::assume_unique_for_key(nonce_bytes.try_into()
            .map_err(|_| MarketIntelError::authentication("Invalid nonce length"))?);
        
        // Decrypt data
        let mut in_out = ciphertext.to_vec();
        less_safe_key.open_in_place(nonce, Aad::empty(), &mut in_out, tag)
            .map_err(|e| MarketIntelError::authentication(format!("Decryption failed: {}", e)))?;
        
        Ok(in_out)
    }
}

#[async_trait]
impl MessageCodec for ProstCodec {
    fn encode(&self, message: &UnifiedMessage) -> Result<Vec<u8>> {
        let start_time = std::time::Instant::now();
        
        // Encode using Protocol Buffers
        let encoded = message.encode_to_vec()
            .map_err(|e| MarketIntelError::serialization(format!("Protobuf encoding failed: {}", e)))?;
        
        debug!("Encoded message in {:?}", start_time.elapsed());
        Ok(encoded)
    }
    
    fn decode(&self, data: &[u8]) -> Result<UnifiedMessage> {
        let start_time = std::time::Instant::now();
        
        // Decode using Protocol Buffers
        let message = UnifiedMessage::decode(data)
            .map_err(|e| MarketIntelError::deserialization(format!("Protobuf decoding failed: {}", e)))?;
        
        debug!("Decoded message in {:?}", start_time.elapsed());
        Ok(message)
    }
    
    fn compress(&self, data: &[u8]) -> Result<Vec<u8>> {
        let start_time = std::time::Instant::now();
        
        let compressed = self.compress_data(data)?;
        
        debug!("Compressed {} bytes to {} bytes in {:?}", 
               data.len(), compressed.len(), start_time.elapsed());
        Ok(compressed)
    }
    
    fn decompress(&self, data: &[u8]) -> Result<Vec<u8>> {
        let start_time = std::time::Instant::now();
        
        let decompressed = self.decompress_data(data)?;
        
        debug!("Decompressed {} bytes to {} bytes in {:?}", 
               data.len(), decompressed.len(), start_time.elapsed());
        Ok(decompressed)
    }
    
    fn encrypt(&self, data: &[u8]) -> Result<Vec<u8>> {
        let start_time = std::time::Instant::now();
        
        let encrypted = self.encrypt_data(data)?;
        
        debug!("Encrypted {} bytes to {} bytes in {:?}", 
               data.len(), encrypted.len(), start_time.elapsed());
        Ok(encrypted)
    }
    
    fn decrypt(&self, data: &[u8]) -> Result<Vec<u8>> {
        let start_time = std::time::Instant::now();
        
        let decrypted = self.decrypt_data(data)?;
        
        debug!("Decrypted {} bytes to {} bytes in {:?}", 
               data.len(), decrypted.len(), start_time.elapsed());
        Ok(decrypted)
    }
    
    fn name(&self) -> &str {
        "prost"
    }
    
    fn version(&self) -> &str {
        "1.0"
    }
}

/// Compression types
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompressionType {
    /// No compression
    None,
    /// LZ4 compression (fast)
    LZ4,
    /// Zstd compression (balanced)
    Zstd,
    /// Gzip compression (standard)
    Gzip,
}

impl CompressionType {
    /// Get compression type from string
    pub fn from_str(s: &str) -> Self {
        match s.to_lowercase().as_str() {
            "none" => CompressionType::None,
            "lz4" => CompressionType::LZ4,
            "zstd" => CompressionType::Zstd,
            "gzip" => CompressionType::Gzip,
            _ => CompressionType::None,
        }
    }
    
    /// Get string representation
    pub fn as_str(&self) -> &str {
        match self {
            CompressionType::None => "none",
            CompressionType::LZ4 => "lz4",
            CompressionType::Zstd => "zstd",
            CompressionType::Gzip => "gzip",
        }
    }
}

/// Message codec factory
pub struct CodecFactory;

impl CodecFactory {
    /// Create codec with specified compression and encryption
    pub fn create_codec(
        compression: CompressionType,
        encryption_key: Option<Vec<u8>>,
    ) -> Arc<dyn MessageCodec> {
        match encryption_key {
            Some(key) => Arc::new(ProstCodec::with_encryption(compression, key)),
            None => Arc::new(ProstCodec::new(compression)),
        }
    }
    
    /// Create default codec
    pub fn create_default() -> Arc<dyn MessageCodec> {
        Arc::new(ProstCodec::new(CompressionType::None))
    }
    
    /// Create high-performance codec
    pub fn create_high_performance() -> Arc<dyn MessageCodec> {
        Arc::new(ProstCodec::new(CompressionType::LZ4))
    }
    
    /// Create balanced codec
    pub fn create_balanced() -> Arc<dyn MessageCodec> {
        Arc::new(ProstCodec::new(CompressionType::Zstd))
    }
    
    /// Create secure codec
    pub fn create_secure(encryption_key: Vec<u8>) -> Arc<dyn MessageCodec> {
        Arc::new(ProstCodec::with_encryption(CompressionType::Zstd, encryption_key))
    }
}

/// Codec performance metrics
pub struct CodecMetrics {
    pub encode_duration_ns: u64,
    pub decode_duration_ns: u64,
    pub compress_duration_ns: u64,
    pub decompress_duration_ns: u64,
    pub encrypt_duration_ns: u64,
    pub decrypt_duration_ns: u64,
    pub compression_ratio: f64,
    pub messages_processed: u64,
    pub bytes_processed: u64,
}

impl CodecMetrics {
    /// Create new metrics
    pub fn new() -> Self {
        Self {
            encode_duration_ns: 0,
            decode_duration_ns: 0,
            compress_duration_ns: 0,
            decompress_duration_ns: 0,
            encrypt_duration_ns: 0,
            decrypt_duration_ns: 0,
            compression_ratio: 1.0,
            messages_processed: 0,
            bytes_processed: 0,
        }
    }
    
    /// Reset metrics
    pub fn reset(&mut self) {
        *self = Self::new();
    }
    
    /// Calculate average encode time
    pub fn avg_encode_time_ns(&self) -> f64 {
        if self.messages_processed == 0 {
            0.0
        } else {
            self.encode_duration_ns as f64 / self.messages_processed as f64
        }
    }
    
    /// Calculate average decode time
    pub fn avg_decode_time_ns(&self) -> f64 {
        if self.messages_processed == 0 {
            0.0
        } else {
            self.decode_duration_ns as f64 / self.messages_processed as f64
        }
    }
    
    /// Calculate throughput (bytes per second)
    pub fn throughput_bytes_per_sec(&self) -> f64 {
        if self.encode_duration_ns + self.decode_duration_ns == 0 {
            0.0
        } else {
            let total_duration_ns = self.encode_duration_ns + self.decode_duration_ns;
            (self.bytes_processed as f64 * 1_000_000_000.0) / total_duration_ns as f64
        }
    }
}

impl Default for CodecMetrics {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::message_types::utils::*;
    
    #[tokio::test]
    async fn test_prost_codec() {
        let codec = ProstCodec::new(CompressionType::None);
        
        // Create test message
        let header = create_header("test", "test_source", MessagePriority::Normal);
        let message = UnifiedMessage {
            header,
            payload: None,
        };
        
        // Test encoding
        let encoded = codec.encode(&message).unwrap();
        assert!(!encoded.is_empty());
        
        // Test decoding
        let decoded = codec.decode(&encoded).unwrap();
        assert_eq!(decoded.header.message_type, "test");
        assert_eq!(decoded.header.source, "test_source");
    }
    
    #[tokio::test]
    async fn test_compression() {
        let codec = ProstCodec::new(CompressionType::LZ4);
        
        let data = b"Hello, World! This is a test message for compression.";
        
        // Test compression
        let compressed = codec.compress(data).unwrap();
        assert!(!compressed.is_empty());
        
        // Test decompression
        let decompressed = codec.decompress(&compressed).unwrap();
        assert_eq!(decompressed, data);
    }
    
    #[tokio::test]
    async fn test_encryption() {
        let key = vec![0u8; 32]; // 256-bit key
        let codec = ProstCodec::with_encryption(CompressionType::None, key);
        
        let data = b"Hello, World! This is a test message for encryption.";
        
        // Test encryption
        let encrypted = codec.encrypt(data).unwrap();
        assert!(!encrypted.is_empty());
        assert_ne!(encrypted, data);
        
        // Test decryption
        let decrypted = codec.decrypt(&encrypted).unwrap();
        assert_eq!(decrypted, data);
    }
    
    #[tokio::test]
    async fn test_codec_factory() {
        let codec = CodecFactory::create_default();
        assert_eq!(codec.name(), "prost");
        assert_eq!(codec.version(), "1.0");
        
        let high_perf = CodecFactory::create_high_performance();
        assert_eq!(high_perf.name(), "prost");
        
        let balanced = CodecFactory::create_balanced();
        assert_eq!(balanced.name(), "prost");
        
        let key = vec![0u8; 32];
        let secure = CodecFactory::create_secure(key);
        assert_eq!(secure.name(), "prost");
    }
    
    #[tokio::test]
    async fn test_compression_type() {
        assert_eq!(CompressionType::from_str("lz4"), CompressionType::LZ4);
        assert_eq!(CompressionType::from_str("zstd"), CompressionType::Zstd);
        assert_eq!(CompressionType::from_str("gzip"), CompressionType::Gzip);
        assert_eq!(CompressionType::from_str("none"), CompressionType::None);
        assert_eq!(CompressionType::from_str("invalid"), CompressionType::None);
        
        assert_eq!(CompressionType::LZ4.as_str(), "lz4");
        assert_eq!(CompressionType::Zstd.as_str(), "zstd");
        assert_eq!(CompressionType::Gzip.as_str(), "gzip");
        assert_eq!(CompressionType::None.as_str(), "none");
    }
    
    #[tokio::test]
    async fn test_codec_metrics() {
        let mut metrics = CodecMetrics::new();
        assert_eq!(metrics.messages_processed, 0);
        assert_eq!(metrics.avg_encode_time_ns(), 0.0);
        assert_eq!(metrics.throughput_bytes_per_sec(), 0.0);
        
        metrics.messages_processed = 100;
        metrics.encode_duration_ns = 1_000_000; // 1ms total
        metrics.bytes_processed = 10_000;
        
        assert_eq!(metrics.avg_encode_time_ns(), 10_000.0); // 10μs per message
        
        metrics.decode_duration_ns = 1_000_000; // 1ms total
        assert_eq!(metrics.throughput_bytes_per_sec(), 5_000_000.0); // 5MB/s
    }
}
