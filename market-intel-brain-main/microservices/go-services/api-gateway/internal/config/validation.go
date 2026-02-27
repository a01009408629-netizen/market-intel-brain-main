package config

import (
	"fmt"
	"net/url"
	"regexp"
	"strings"

)

// Validation methods for each configuration struct

// Validate validates ServerConfig
func (s *ServerConfig) Validate() error {
	if s.HTTPPort == 0 {
		return &ConfigError{
			Key:     "SERVER_HTTP_PORT",
			Value:   fmt.Sprintf("%d", s.HTTPPort),
			Message: "HTTP port cannot be 0",
		}
	}
	
	if s.GRPCPort == 0 {
		return &ConfigError{
			Key:     "SERVER_GRPC_PORT",
			Value:   fmt.Sprintf("%d", s.GRPCPort),
			Message: "gRPC port cannot be 0",
		}
	}
	
	if s.HTTPPort == s.GRPCPort {
		return &ConfigError{
			Key:     "SERVER_PORTS",
			Value:   fmt.Sprintf("%d/%d", s.HTTPPort, s.GRPCPort),
			Message: "HTTP and gRPC ports cannot be the same",
		}
	}
	
	if s.HTTPPort < 1 || s.HTTPPort > 65535 {
		return &ConfigError{
			Key:     "SERVER_HTTP_PORT",
			Value:   fmt.Sprintf("%d", s.HTTPPort),
			Message: "HTTP port must be between 1 and 65535",
		}
	}
	
	if s.GRPCPort < 1 || s.GRPCPort > 65535 {
		return &ConfigError{
			Key:     "SERVER_GRPC_PORT",
			Value:   fmt.Sprintf("%d", s.GRPCPort),
			Message: "gRPC port must be between 1 and 65535",
		}
	}
	
	if s.Host == "" {
		return &ConfigError{
			Key:     "SERVER_HOST",
			Value:   s.Host,
			Message: "Server host cannot be empty",
		}
	}
	
	if s.ReadTimeout <= 0 {
		return &ConfigError{
			Key:     "SERVER_READ_TIMEOUT",
			Value:   s.ReadTimeout.String(),
			Message: "Read timeout must be positive",
		}
	}
	
	if s.WriteTimeout <= 0 {
		return &ConfigError{
			Key:     "SERVER_WRITE_TIMEOUT",
			Value:   s.WriteTimeout.String(),
			Message: "Write timeout must be positive",
		}
	}
	
	if s.IdleTimeout <= 0 {
		return &ConfigError{
			Key:     "SERVER_IDLE_TIMEOUT",
			Value:   s.IdleTimeout.String(),
			Message: "Idle timeout must be positive",
		}
	}
	
	if s.MaxHeaderBytes <= 0 {
		return &ConfigError{
			Key:     "SERVER_MAX_HEADER_BYTES",
			Value:   fmt.Sprintf("%d", s.MaxHeaderBytes),
			Message: "Max header bytes must be positive",
		}
	}
	
	if s.MaxBodyBytes <= 0 {
		return &ConfigError{
			Key:     "SERVER_MAX_BODY_BYTES",
			Value:   fmt.Sprintf("%d", s.MaxBodyBytes),
			Message: "Max body bytes must be positive",
		}
	}
	
	if s.GracefulTimeout <= 0 {
		return &ConfigError{
			Key:     "SERVER_GRACEFUL_TIMEOUT",
			Value:   s.GracefulTimeout.String(),
			Message: "Graceful timeout must be positive",
		}
	}
	
	if s.MaxConnections <= 0 {
		return &ConfigError{
			Key:     "SERVER_MAX_CONNECTIONS",
			Value:   fmt.Sprintf("%d", s.MaxConnections),
			Message: "Max connections must be positive",
		}
	}
	
	return nil
}

// Validate validates DatabaseConfig
func (d *DatabaseConfig) Validate() error {
	if d.Host == "" {
		return &ConfigError{
			Key:     "DB_HOST",
			Value:   d.Host,
			Message: "Database host cannot be empty",
		}
	}
	
	if d.Port == 0 {
		return &ConfigError{
			Key:     "DB_PORT",
			Value:   fmt.Sprintf("%d", d.Port),
			Message: "Database port cannot be 0",
		}
	}
	
	if d.Port < 1 || d.Port > 65535 {
		return &ConfigError{
			Key:     "DB_PORT",
			Value:   fmt.Sprintf("%d", d.Port),
			Message: "Database port must be between 1 and 65535",
		}
	}
	
	if d.Database == "" {
		return &ConfigError{
			Key:     "DB_NAME",
			Value:   d.Database,
			Message: "Database name cannot be empty",
		}
	}
	
	if d.Username == "" {
		return &ConfigError{
			Key:     "DB_USERNAME",
			Value:   d.Username,
			Message: "Database username cannot be empty",
		}
	}
	
	if d.Password == "" {
		return &ConfigError{
			Key:     "DB_PASSWORD",
			Value:   "***",
			Message: "Database password cannot be empty",
		}
	}
	
	if d.MaxConnections <= 0 {
		return &ConfigError{
			Key:     "DB_MAX_CONNECTIONS",
			Value:   fmt.Sprintf("%d", d.MaxConnections),
			Message: "Max connections must be positive",
		}
	}
	
	if d.MinConnections < 0 {
		return &ConfigError{
			Key:     "DB_MIN_CONNECTIONS",
			Value:   fmt.Sprintf("%d", d.MinConnections),
			Message: "Min connections cannot be negative",
		}
	}
	
	if d.MinConnections > d.MaxConnections {
		return &ConfigError{
			Key:     "DB_CONNECTIONS",
			Value:   fmt.Sprintf("%d/%d", d.MinConnections, d.MaxConnections),
			Message: "Min connections cannot be greater than max connections",
		}
	}
	
	// Validate SSL mode
	validSSLModes := []string{"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}
	isValidSSLMode := false
	for _, mode := range validSSLModes {
		if d.SSLMode == mode {
			isValidSSLMode = true
			break
		}
	}
	if !isValidSSLMode {
		return &ConfigError{
			Key:     "DB_SSL_MODE",
			Value:   d.SSLMode,
			Message: fmt.Sprintf("SSL mode must be one of: %s", strings.Join(validSSLModes, ", ")),
		}
	}
	
	if d.MaxIdleTime <= 0 {
		return &ConfigError{
			Key:     "DB_MAX_IDLE_TIME",
			Value:   d.MaxIdleTime.String(),
			Message: "Max idle time must be positive",
		}
	}
	
	if d.MaxLifetime <= 0 {
		return &ConfigError{
			Key:     "DB_MAX_LIFETIME",
			Value:   d.MaxLifetime.String(),
			Message: "Max lifetime must be positive",
		}
	}
	
	if d.ConnectTimeout <= 0 {
		return &ConfigError{
			Key:     "DB_CONNECT_TIMEOUT",
			Value:   d.ConnectTimeout.String(),
			Message: "Connect timeout must be positive",
		}
	}
	
	if d.QueryTimeout <= 0 {
		return &ConfigError{
			Key:     "DB_QUERY_TIMEOUT",
			Value:   d.QueryTimeout.String(),
			Message: "Query timeout must be positive",
		}
	}
	
	return nil
}

// Validate validates RedisConfig
func (r *RedisConfig) Validate() error {
	if r.Host == "" {
		return &ConfigError{
			Key:     "REDIS_HOST",
			Value:   r.Host,
			Message: "Redis host cannot be empty",
		}
	}
	
	if r.Port == 0 {
		return &ConfigError{
			Key:     "REDIS_PORT",
			Value:   fmt.Sprintf("%d", r.Port),
			Message: "Redis port cannot be 0",
		}
	}
	
	if r.Port < 1 || r.Port > 65535 {
		return &ConfigError{
			Key:     "REDIS_PORT",
			Value:   fmt.Sprintf("%d", r.Port),
			Message: "Redis port must be between 1 and 65535",
		}
	}
	
	if r.Database < 0 || r.Database > 15 {
		return &ConfigError{
			Key:     "REDIS_DATABASE",
			Value:   fmt.Sprintf("%d", r.Database),
			Message: "Redis database must be between 0 and 15",
		}
	}
	
	if r.MaxRetries < 0 {
		return &ConfigError{
			Key:     "REDIS_MAX_RETRIES",
			Value:   fmt.Sprintf("%d", r.MaxRetries),
			Message: "Max retries cannot be negative",
		}
	}
	
	if r.DialTimeout <= 0 {
		return &ConfigError{
			Key:     "REDIS_DIAL_TIMEOUT",
			Value:   r.DialTimeout.String(),
			Message: "Dial timeout must be positive",
		}
	}
	
	if r.ReadTimeout <= 0 {
		return &ConfigError{
			Key:     "REDIS_READ_TIMEOUT",
			Value:   r.ReadTimeout.String(),
			Message: "Read timeout must be positive",
		}
	}
	
	if r.WriteTimeout <= 0 {
		return &ConfigError{
			Key:     "REDIS_WRITE_TIMEOUT",
			Value:   r.WriteTimeout.String(),
			Message: "Write timeout must be positive",
		}
	}
	
	if r.PoolSize <= 0 {
		return &ConfigError{
			Key:     "REDIS_POOL_SIZE",
			Value:   fmt.Sprintf("%d", r.PoolSize),
			Message: "Pool size must be positive",
		}
	}
	
	if r.MinIdleConns < 0 {
		return &ConfigError{
			Key:     "REDIS_MIN_IDLE_CONNS",
			Value:   fmt.Sprintf("%d", r.MinIdleConns),
			Message: "Min idle connections cannot be negative",
		}
	}
	
	if r.MinIdleConns > r.PoolSize {
		return &ConfigError{
			Key:     "REDIS_CONNECTIONS",
			Value:   fmt.Sprintf("%d/%d", r.MinIdleConns, r.PoolSize),
			Message: "Min idle connections cannot be greater than pool size",
		}
	}
	
	if r.MaxConnAge <= 0 {
		return &ConfigError{
			Key:     "REDIS_MAX_CONN_AGE",
			Value:   r.MaxConnAge.String(),
			Message: "Max connection age must be positive",
		}
	}
	
	return nil
}

// Validate validates KafkaConfig
func (k *KafkaConfig) Validate() error {
	if len(k.Brokers) == 0 {
		return &ConfigError{
			Key:     "KAFKA_BROKERS",
			Value:   strings.Join(k.Brokers, ","),
			Message: "At least one Kafka broker must be specified",
		}
	}
	
	for i, broker := range k.Brokers {
		if broker == "" {
			return &ConfigError{
				Key:     "KAFKA_BROKERS",
				Value:   strings.Join(k.Brokers, ","),
				Message: fmt.Sprintf("Broker %d cannot be empty", i),
			}
		}
		
		// Validate broker format (host:port)
		if !isValidBroker(broker) {
			return &ConfigError{
				Key:     "KAFKA_BROKERS",
				Value:   broker,
				Message: "Broker must be in format host:port",
			}
		}
	}
	
	if k.ConsumerGroup == "" {
		return &ConfigError{
			Key:     "KAFKA_CONSUMER_GROUP",
			Value:   k.ConsumerGroup,
			Message: "Consumer group cannot be empty",
		}
	}
	
	if k.CompressionType == "" {
		return &ConfigError{
			Key:     "KAFKA_COMPRESSION_TYPE",
			Value:   k.CompressionType,
			Message: "Compression type cannot be empty",
		}
	}
	
	validCompressionTypes := []string{"none", "gzip", "snappy", "lz4", "zstd"}
	isValidCompressionType := false
	for _, ct := range validCompressionTypes {
		if k.CompressionType == ct {
			isValidCompressionType = true
			break
		}
	}
	if !isValidCompressionType {
		return &ConfigError{
			Key:     "KAFKA_COMPRESSION_TYPE",
			Value:   k.CompressionType,
			Message: fmt.Sprintf("Compression type must be one of: %s", strings.Join(validCompressionTypes, ", ")),
		}
	}
	
	if k.BatchSize <= 0 {
		return &ConfigError{
			Key:     "KAFKA_BATCH_SIZE",
			Value:   fmt.Sprintf("%d", k.BatchSize),
			Message: "Batch size must be positive",
		}
	}
	
	if k.BatchTimeout < 0 {
		return &ConfigError{
			Key:     "KAFKA_BATCH_TIMEOUT",
			Value:   k.BatchTimeout.String(),
			Message: "Batch timeout cannot be negative",
		}
	}
	
	if k.CompressionLevel < 0 || k.CompressionLevel > 9 {
		return &ConfigError{
			Key:     "KAFKA_COMPRESSION_LEVEL",
			Value:   fmt.Sprintf("%d", k.CompressionLevel),
			Message: "Compression level must be between 0 and 9",
		}
	}
	
	if k.MaxMessageBytes <= 0 {
		return &ConfigError{
			Key:     "KAFKA_MAX_MESSAGE_BYTES",
			Value:   fmt.Sprintf("%d", k.MaxMessageBytes),
			Message: "Max message bytes must be positive",
		}
	}
	
	if k.ConsumerFetchMin <= 0 {
		return &ConfigError{
			Key:     "KAFKA_CONSUMER_FETCH_MIN",
			Value:   fmt.Sprintf("%d", k.ConsumerFetchMin),
			Message: "Consumer fetch min must be positive",
		}
	}
	
	if k.ConsumerFetchDefault <= 0 {
		return &ConfigError{
			Key:     "KAFKA_CONSUMER_FETCH_DEFAULT",
			Value:   fmt.Sprintf("%d", k.ConsumerFetchDefault),
			Message: "Consumer fetch default must be positive",
		}
	}
	
	if k.ConsumerFetchMax <= 0 {
		return &ConfigError{
			Key:     "KAFKA_CONSUMER_FETCH_MAX",
			Value:   fmt.Sprintf("%d", k.ConsumerFetchMax),
			Message: "Consumer fetch max must be positive",
		}
	}
	
	if k.ConsumerFetchMin > k.ConsumerFetchDefault || k.ConsumerFetchDefault > k.ConsumerFetchMax {
		return &ConfigError{
			Key:     "KAFKA_CONSUMER_FETCH",
			Value:   fmt.Sprintf("%d/%d/%d", k.ConsumerFetchMin, k.ConsumerFetchDefault, k.ConsumerFetchMax),
			Message: "Fetch values must be: min <= default <= max",
		}
	}
	
	return nil
}

// Validate validates ServiceURLs
func (s *ServiceURLs) Validate() error {
	if s.CoreEngine == "" {
		return &ConfigError{
			Key:     "CORE_ENGINE_URL",
			Value:   s.CoreEngine,
			Message: "Core engine URL cannot be empty",
		}
	}
	
	if s.AuthService == "" {
		return &ConfigError{
			Key:     "AUTH_SERVICE_URL",
			Value:   s.AuthService,
			Message: "Auth service URL cannot be empty",
		}
	}
	
	if s.Analytics == "" {
		return &ConfigError{
			Key:     "ANALYTICS_SERVICE_URL",
			Value:   s.Analytics,
			Message: "Analytics service URL cannot be empty",
		}
	}
	
	if s.VectorStore == "" {
		return &ConfigError{
			Key:     "VECTOR_STORE_URL",
			Value:   s.VectorStore,
			Message: "Vector store URL cannot be empty",
		}
	}
	
	// Validate URL formats
	services := map[string]string{
		"CoreEngine":  s.CoreEngine,
		"AuthService": s.AuthService,
		"Analytics":   s.Analytics,
		"VectorStore": s.VectorStore,
	}
	
	for name, serviceURL := range services {
		if !isValidServiceURL(serviceURL) {
			return &ConfigError{
				Key:     fmt.Sprintf("%s_URL", name),
				Value:   serviceURL,
				Message: "Service URL must be in format host:port or https://host:port",
			}
		}
	}
	
	return nil
}

// Validate validates SecurityConfig
func (s *SecurityConfig) Validate() error {
	if s.JWTSecret == "" {
		return &ConfigError{
			Key:     "JWT_SECRET",
			Value:   "***",
			Message: "JWT secret cannot be empty",
		}
	}
	
	if len(s.JWTSecret) < 32 {
		return &ConfigError{
			Key:     "JWT_SECRET",
			Value:   "***",
			Message: "JWT secret must be at least 32 characters long",
		}
	}
	
	if s.JWTExpiration <= 0 {
		return &ConfigError{
			Key:     "JWT_EXPIRATION",
			Value:   s.JWTExpiration.String(),
			Message: "JWT expiration must be positive",
		}
	}
	
	if s.RefreshExpiration <= 0 {
		return &ConfigError{
			Key:     "REFRESH_TOKEN_EXPIRATION",
			Value:   s.RefreshExpiration.String(),
			Message: "Refresh token expiration must be positive",
		}
	}
	
	if s.RefreshExpiration < s.JWTExpiration {
		return &ConfigError{
			Key:     "TOKEN_EXPIRATION",
			Value:   fmt.Sprintf("%s/%s", s.JWTExpiration.String(), s.RefreshExpiration.String()),
			Message: "Refresh token expiration must be greater than or equal to JWT expiration",
		}
	}
	
	if s.BcryptCost < 4 || s.BcryptCost > 31 {
		return &ConfigError{
			Key:     "BCRYPT_COST",
			Value:   fmt.Sprintf("%d", s.BcryptCost),
			Message: "Bcrypt cost must be between 4 and 31",
		}
	}
	
	if s.RateLimitRPS <= 0 {
		return &ConfigError{
			Key:     "RATE_LIMIT_RPS",
			Value:   fmt.Sprintf("%d", s.RateLimitRPS),
			Message: "Rate limit RPS must be positive",
		}
	}
	
	if s.RateLimitBurst <= 0 {
		return &ConfigError{
			Key:     "RATE_LIMIT_BURST",
			Value:   fmt.Sprintf("%d", s.RateLimitBurst),
			Message: "Rate limit burst must be positive",
		}
	}
	
	if s.RateLimitBurst < s.RateLimitRPS {
		return &ConfigError{
			Key:     "RATE_LIMIT",
			Value:   fmt.Sprintf("%d/%d", s.RateLimitRPS, s.RateLimitBurst),
			Message: "Rate limit burst must be greater than or equal to RPS",
		}
	}
	
	// Validate CORS origins
	for i, origin := range s.CORSAllowedOrigins {
		origin = strings.TrimSpace(origin)
		if origin == "" {
			continue
		}
		
		if origin != "*" && !isValidOrigin(origin) {
			return &ConfigError{
				Key:     "CORS_ALLOWED_ORIGINS",
				Value:   origin,
				Message: fmt.Sprintf("CORS origin %d is invalid", i),
			}
		}
	}
	
	return nil
}

// Validate validates LoggingConfig
func (l *LoggingConfig) Validate() error {
	validLevels := []string{"trace", "debug", "info", "warn", "error", "fatal", "panic"}
	isValidLevel := false
	for _, level := range validLevels {
		if l.Level == level {
			isValidLevel = true
			break
		}
	}
	if !isValidLevel {
		return &ConfigError{
			Key:     "LOG_LEVEL",
			Value:   l.Level,
			Message: fmt.Sprintf("Log level must be one of: %s", strings.Join(validLevels, ", ")),
		}
	}
	
	validFormats := []string{"json", "text"}
	isValidFormat := false
	for _, format := range validFormats {
		if l.Format == format {
			isValidFormat = true
			break
		}
	}
	if !isValidFormat {
		return &ConfigError{
			Key:     "LOG_FORMAT",
			Value:   l.Format,
			Message: fmt.Sprintf("Log format must be one of: %s", strings.Join(validFormats, ", ")),
		}
	}
	
	validOutputs := []string{"stdout", "stderr", "file"}
	isValidOutput := false
	for _, output := range validOutputs {
		if l.Output == output {
			isValidOutput = true
			break
		}
	}
	if !isValidOutput {
		return &ConfigError{
			Key:     "LOG_OUTPUT",
			Value:   l.Output,
			Message: fmt.Sprintf("Log output must be one of: %s", strings.Join(validOutputs, ", ")),
		}
	}
	
	if l.EnableFile && l.FilePath == "" {
		return &ConfigError{
			Key:     "LOG_FILE_PATH",
			Value:   l.FilePath,
			Message: "Log file path cannot be empty when file logging is enabled",
		}
	}
	
	if l.MaxSize <= 0 {
		return &ConfigError{
			Key:     "LOG_MAX_SIZE",
			Value:   fmt.Sprintf("%d", l.MaxSize),
			Message: "Log max size must be positive",
		}
	}
	
	if l.MaxBackups < 0 {
		return &ConfigError{
			Key:     "LOG_MAX_BACKUPS",
			Value:   fmt.Sprintf("%d", l.MaxBackups),
			Message: "Log max backups cannot be negative",
		}
	}
	
	if l.MaxAge < 0 {
		return &ConfigError{
			Key:     "LOG_MAX_AGE",
			Value:   fmt.Sprintf("%d", l.MaxAge),
			Message: "Log max age cannot be negative",
		}
	}
	
	return nil
}

// Validate validates MetricsConfig
func (m *MetricsConfig) Validate() error {
	if m.Path == "" {
		return &ConfigError{
			Key:     "METRICS_PATH",
			Value:   m.Path,
			Message: "Metrics path cannot be empty",
		}
	}
	
	if !strings.HasPrefix(m.Path, "/") {
		return &ConfigError{
			Key:     "METRICS_PATH",
			Value:   m.Path,
			Message: "Metrics path must start with '/'",
		}
	}
	
	if m.Port == 0 {
		return &ConfigError{
			Key:     "METRICS_PORT",
			Value:   fmt.Sprintf("%d", m.Port),
			Message: "Metrics port cannot be 0",
		}
	}
	
	if m.Port < 1 || m.Port > 65535 {
		return &ConfigError{
			Key:     "METRICS_PORT",
			Value:   fmt.Sprintf("%d", m.Port),
			Message: "Metrics port must be between 1 and 65535",
		}
	}
	
	if m.Namespace == "" {
		return &ConfigError{
			Key:     "METRICS_NAMESPACE",
			Value:   m.Namespace,
			Message: "Metrics namespace cannot be empty",
		}
	}
	
	if m.Subsystem == "" {
		return &ConfigError{
			Key:     "METRICS_SUBSYSTEM",
			Value:   m.Subsystem,
			Message: "Metrics subsystem cannot be empty",
		}
	}
	
	// Validate namespace and subsystem format (should match regex: ^[a-zA-Z_][a-zA-Z0-9_]*$)
	validNamespace := regexp.MustCompile(`^[a-zA-Z_][a-zA-Z0-9_]*$`)
	if !validNamespace.MatchString(m.Namespace) {
		return &ConfigError{
			Key:     "METRICS_NAMESPACE",
			Value:   m.Namespace,
			Message: "Metrics namespace must contain only letters, numbers, and underscores, and start with a letter or underscore",
		}
	}
	
	if !validNamespace.MatchString(m.Subsystem) {
		return &ConfigError{
			Key:     "METRICS_SUBSYSTEM",
			Value:   m.Subsystem,
			Message: "Metrics subsystem must contain only letters, numbers, and underscores, and start with a letter or underscore",
		}
	}
	
	return nil
}

// Helper validation functions

func isValidBroker(broker string) bool {
	parts := strings.Split(broker, ":")
	if len(parts) != 2 {
		return false
	}
	
	host := parts[0]
	port := parts[1]
	
	if host == "" {
		return false
	}
	
	// Validate port
	if len(port) == 0 {
		return false
	}
	
	for _, char := range port {
		if char < '0' || char > '9' {
			return false
		}
	}
	
	return true
}

func isValidServiceURL(serviceURL string) bool {
	// Check if it's a full URL
	if strings.HasPrefix(serviceURL, "http://") || strings.HasPrefix(serviceURL, "https://") {
		_, err := url.Parse(serviceURL)
		return err == nil
	}
	
	// Otherwise, check if it's host:port
	return isValidBroker(serviceURL)
}

func isValidOrigin(origin string) bool {
	// Check if it's a valid URL
	if strings.HasPrefix(origin, "http://") || strings.HasPrefix(origin, "https://") {
		_, err := url.Parse(origin)
		return err == nil
	}
	
	// Check if it's a valid hostname pattern
	validOrigin := regexp.MustCompile(`^[a-zA-Z0-9.-]+$`)
	return validOrigin.MatchString(origin)
}
