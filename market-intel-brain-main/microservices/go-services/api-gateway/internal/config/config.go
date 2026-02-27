package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
	"errors"
	"strings"


)

// ConfigError represents a configuration error
type ConfigError struct {
	Key     string
	Value   string
	Message string
}

func (e *ConfigError) Error() string {
	return fmt.Sprintf("configuration error for %s: %s (value: %s)", e.Key, e.Message, e.Value)
}

// Config holds the application configuration
type Config struct {
	// Server configuration
	Server ServerConfig `mapstructure:"server"`
	
	// Database configuration
	Database DatabaseConfig `mapstructure:"database"`
	
	// Redis configuration
	Redis RedisConfig `mapstructure:"redis"`
	
	// Kafka configuration
	Kafka KafkaConfig `mapstructure:"kafka"`
	
	// Service URLs
	Services ServiceURLs `mapstructure:"services"`
	
	// Security configuration
	Security SecurityConfig `mapstructure:"security"`
	
	// Logging configuration
	Logging LoggingConfig `mapstructure:"logging"`
	
	// Metrics configuration
	Metrics MetricsConfig `mapstructure:"metrics"`
	
	// Environment
	Environment string `mapstructure:"environment"`
}

// ServerConfig holds server-related configuration
type ServerConfig struct {
	HTTPPort           int           `mapstructure:"http_port"`
	GRPCPort           int           `mapstructure:"grpc_port"`
	Host               string        `mapstructure:"host"`
	ReadTimeout        time.Duration `mapstructure:"read_timeout"`
	WriteTimeout       time.Duration `mapstructure:"write_timeout"`
	IdleTimeout        time.Duration `mapstructure:"idle_timeout"`
	MaxHeaderBytes     int           `mapstructure:"max_header_bytes"`
	MaxBodyBytes       int64         `mapstructure:"max_body_bytes"`
	EnableHTTPS        bool          `mapstructure:"enable_https"`
	EnableCORS         bool          `mapstructure:"enable_cors"`
	EnableMetrics      bool          `mapstructure:"enable_metrics"`
	EnablePprof        bool          `mapstructure:"enable_pprof"`
	GracefulTimeout    time.Duration `mapstructure:"graceful_timeout"`
	MaxConnections     int           `mapstructure:"max_connections"`
}

// DatabaseConfig holds database configuration
type DatabaseConfig struct {
	Host            string        `mapstructure:"host"`
	Port            int           `mapstructure:"port"`
	Database        string        `mapstructure:"database"`
	Username        string        `mapstructure:"username"`
	Password        string        `mapstructure:"password"`
	SSLMode         string        `mapstructure:"ssl_mode"`
	MaxConnections  int           `mapstructure:"max_connections"`
	MinConnections  int           `mapstructure:"min_connections"`
	MaxIdleTime     time.Duration `mapstructure:"max_idle_time"`
	MaxLifetime     time.Duration `mapstructure:"max_lifetime"`
	ConnectTimeout  time.Duration `mapstructure:"connect_timeout"`
	QueryTimeout    time.Duration `mapstructure:"query_timeout"`
}

// RedisConfig holds Redis configuration
type RedisConfig struct {
	Host         string        `mapstructure:"host"`
	Port         int           `mapstructure:"port"`
	Password     string        `mapstructure:"password"`
	Database     int           `mapstructure:"database"`
	MaxRetries   int           `mapstructure:"max_retries"`
	DialTimeout  time.Duration `mapstructure:"dial_timeout"`
	ReadTimeout  time.Duration `mapstructure:"read_timeout"`
	WriteTimeout time.Duration `mapstructure:"write_timeout"`
	PoolSize     int           `mapstructure:"pool_size"`
	MinIdleConns int           `mapstructure:"min_idle_conns"`
	MaxConnAge   time.Duration `mapstructure:"max_conn_age"`
}

// KafkaConfig holds Kafka configuration
type KafkaConfig struct {
	Brokers              []string      `mapstructure:"brokers"`
	ConsumerGroup        string        `mapstructure:"consumer_group"`
	TopicPrefix          string        `mapstructure:"topic_prefix"`
	CompressionType      string        `mapstructure:"compression_type"`
	BatchSize            int           `mapstructure:"batch_size"`
	BatchTimeout         time.Duration `mapstructure:"batch_timeout"`
	CompressionLevel     int           `mapstructure:"compression_level"`
	MaxMessageBytes      int           `mapstructure:"max_message_bytes"`
	ConsumerFetchMin     int           `mapstructure:"consumer_fetch_min"`
	ConsumerFetchDefault int           `mapstructure:"consumer_fetch_default"`
	ConsumerFetchMax     int           `mapstructure:"consumer_fetch_max"`
}

// ServiceURLs holds service endpoint URLs
type ServiceURLs struct {
	CoreEngine  string `mapstructure:"core_engine"`
	AuthService string `mapstructure:"auth_service"`
	Analytics   string `mapstructure:"analytics"`
	VectorStore string `mapstructure:"vector_store"`
}

// SecurityConfig holds security-related configuration
type SecurityConfig struct {
	JWTSecret           string        `mapstructure:"jwt_secret"`
	JWTExpiration       time.Duration `mapstructure:"jwt_expiration"`
	RefreshExpiration   time.Duration `mapstructure:"refresh_expiration"`
	BcryptCost          int           `mapstructure:"bcrypt_cost"`
	RateLimitEnabled    bool          `mapstructure:"rate_limit_enabled"`
	RateLimitRPS        int           `mapstructure:"rate_limit_rps"`
	RateLimitBurst      int           `mapstructure:"rate_limit_burst"`
	CORSAllowedOrigins  []string      `mapstructure:"cors_allowed_origins"`
	CORSAllowedMethods  []string      `mapstructure:"cors_allowed_methods"`
	CORSAllowedHeaders  []string      `mapstructure:"cors_allowed_headers"`
	EnableHTTPSRedirect bool          `mapstructure:"enable_https_redirect"`
	TrustedProxies      []string      `mapstructure:"trusted_proxies"`
}

// LoggingConfig holds logging configuration
type LoggingConfig struct {
	Level         string `mapstructure:"level"`
	Format        string `mapstructure:"format"`
	Output        string `mapstructure:"output"`
	EnableConsole bool   `mapstructure:"enable_console"`
	EnableFile    bool   `mapstructure:"enable_file"`
	FilePath      string `mapstructure:"file_path"`
	MaxSize       int    `mapstructure:"max_size"`
	MaxBackups    int    `mapstructure:"max_backups"`
	MaxAge        int    `mapstructure:"max_age"`
	Compress      bool   `mapstructure:"compress"`
}

// MetricsConfig holds metrics configuration
type MetricsConfig struct {
	Enabled    bool   `mapstructure:"enabled"`
	Path       string `mapstructure:"path"`
	Port       int    `mapstructure:"port"`
	Namespace  string `mapstructure:"namespace"`
	Subsystem  string `mapstructure:"subsystem"`
}

// Load loads configuration from environment variables with validation
func Load(configFile string) (*Config, error) {
	config := &Config{}
	
	// Load server configuration
	serverConfig, err := loadServerConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load server config: %w", err)
	}
	config.Server = serverConfig
	
	// Load database configuration
	databaseConfig, err := loadDatabaseConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load database config: %w", err)
	}
	config.Database = databaseConfig
	
	// Load Redis configuration
	redisConfig, err := loadRedisConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load redis config: %w", err)
	}
	config.Redis = redisConfig
	
	// Load Kafka configuration
	kafkaConfig, err := loadKafkaConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load kafka config: %w", err)
	}
	config.Kafka = kafkaConfig
	
	// Load service URLs
	serviceURLs, err := loadServiceURLs()
	if err != nil {
		return nil, fmt.Errorf("failed to load service URLs: %w", err)
	}
	config.Services = serviceURLs
	
	// Load security configuration
	securityConfig, err := loadSecurityConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load security config: %w", err)
	}
	config.Security = securityConfig
	
	// Load logging configuration
	loggingConfig, err := loadLoggingConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load logging config: %w", err)
	}
	config.Logging = loggingConfig
	
	// Load metrics configuration
	metricsConfig, err := loadMetricsConfig()
	if err != nil {
		return nil, fmt.Errorf("failed to load metrics config: %w", err)
	}
	config.Metrics = metricsConfig
	
	// Load environment
	config.Environment = getEnv("ENVIRONMENT", "development")
	
	// Validate entire configuration
	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("configuration validation failed: %w", err)
	}
	
	return config, nil
}

// Validate validates the entire configuration
func (c *Config) Validate() error {
	if err := c.Server.Validate(); err != nil {
		return fmt.Errorf("server config validation failed: %w", err)
	}
	
	if err := c.Database.Validate(); err != nil {
		return fmt.Errorf("database config validation failed: %w", err)
	}
	
	if err := c.Redis.Validate(); err != nil {
		return fmt.Errorf("redis config validation failed: %w", err)
	}
	
	if err := c.Kafka.Validate(); err != nil {
		return fmt.Errorf("kafka config validation failed: %w", err)
	}
	
	if err := c.Services.Validate(); err != nil {
		return fmt.Errorf("services config validation failed: %w", err)
	}
	
	if err := c.Security.Validate(); err != nil {
		return fmt.Errorf("security config validation failed: %w", err)
	}
	
	if err := c.Logging.Validate(); err != nil {
		return fmt.Errorf("logging config validation failed: %w", err)
	}
	
	if err := c.Metrics.Validate(); err != nil {
		return fmt.Errorf("metrics config validation failed: %w", err)
	}
	
	// Cross-component validation
	if c.Server.HTTPPort == c.Server.GRPCPort {
		return errors.New("HTTP and gRPC ports cannot be the same")
	}
	
	return nil
}

// loadServerConfig loads server configuration from environment variables
func loadServerConfig() (ServerConfig, error) {
	config := ServerConfig{
		HTTPPort:           getEnvInt("SERVER_HTTP_PORT", 8080),
		GRPCPort:           getEnvInt("SERVER_GRPC_PORT", 8081),
		Host:               getEnv("SERVER_HOST", "0.0.0.0"),
		ReadTimeout:        getEnvDuration("SERVER_READ_TIMEOUT", 30*time.Second),
		WriteTimeout:       getEnvDuration("SERVER_WRITE_TIMEOUT", 30*time.Second),
		IdleTimeout:        getEnvDuration("SERVER_IDLE_TIMEOUT", 60*time.Second),
		MaxHeaderBytes:     getEnvInt("SERVER_MAX_HEADER_BYTES", 1<<20), // 1MB
		MaxBodyBytes:       getEnvInt64("SERVER_MAX_BODY_BYTES", 10<<20), // 10MB
		EnableHTTPS:        getEnvBool("SERVER_ENABLE_HTTPS", false),
		EnableCORS:         getEnvBool("SERVER_ENABLE_CORS", true),
		EnableMetrics:      getEnvBool("SERVER_ENABLE_METRICS", true),
		EnablePprof:        getEnvBool("SERVER_ENABLE_PPROF", false),
		GracefulTimeout:    getEnvDuration("SERVER_GRACEFUL_TIMEOUT", 30*time.Second),
		MaxConnections:     getEnvInt("SERVER_MAX_CONNECTIONS", 10000),
	}
	
	return config, config.Validate()
}

// loadDatabaseConfig loads database configuration from environment variables
func loadDatabaseConfig() (DatabaseConfig, error) {
	config := DatabaseConfig{
		Host:           getEnv("DB_HOST", "localhost"),
		Port:           getEnvInt("DB_PORT", 5432),
		Database:       getEnv("DB_NAME", "market_intel"),
		Username:       getEnv("DB_USERNAME", "postgres"),
		Password:       getEnvRequired("DB_PASSWORD"),
		SSLMode:        getEnv("DB_SSL_MODE", "prefer"),
		MaxConnections: getEnvInt("DB_MAX_CONNECTIONS", 20),
		MinConnections: getEnvInt("DB_MIN_CONNECTIONS", 5),
		MaxIdleTime:    getEnvDuration("DB_MAX_IDLE_TIME", 10*time.Minute),
		MaxLifetime:    getEnvDuration("DB_MAX_LIFETIME", 30*time.Minute),
		ConnectTimeout: getEnvDuration("DB_CONNECT_TIMEOUT", 30*time.Second),
		QueryTimeout:   getEnvDuration("DB_QUERY_TIMEOUT", 30*time.Second),
	}
	
	return config, config.Validate()
}

// loadRedisConfig loads Redis configuration from environment variables
func loadRedisConfig() (RedisConfig, error) {
	config := RedisConfig{
		Host:         getEnv("REDIS_HOST", "localhost"),
		Port:         getEnvInt("REDIS_PORT", 6379),
		Password:     getEnv("REDIS_PASSWORD", ""),
		Database:     getEnvInt("REDIS_DATABASE", 0),
		MaxRetries:   getEnvInt("REDIS_MAX_RETRIES", 3),
		DialTimeout:  getEnvDuration("REDIS_DIAL_TIMEOUT", 5*time.Second),
		ReadTimeout:  getEnvDuration("REDIS_READ_TIMEOUT", 3*time.Second),
		WriteTimeout: getEnvDuration("REDIS_WRITE_TIMEOUT", 3*time.Second),
		PoolSize:     getEnvInt("REDIS_POOL_SIZE", 10),
		MinIdleConns: getEnvInt("REDIS_MIN_IDLE_CONNS", 5),
		MaxConnAge:   getEnvDuration("REDIS_MAX_CONN_AGE", 30*time.Minute),
	}
	
	return config, config.Validate()
}

// loadKafkaConfig loads Kafka configuration from environment variables
func loadKafkaConfig() (KafkaConfig, error) {
	brokers := strings.Split(getEnv("KAFKA_BROKERS", "localhost:9092"), ",")
	for i, broker := range brokers {
		brokers[i] = strings.TrimSpace(broker)
	}
	
	config := KafkaConfig{
		Brokers:              brokers,
		ConsumerGroup:        getEnv("KAFKA_CONSUMER_GROUP", "api-gateway"),
		TopicPrefix:          getEnv("KAFKA_TOPIC_PREFIX", ""),
		CompressionType:      getEnv("KAFKA_COMPRESSION_TYPE", "gzip"),
		BatchSize:            getEnvInt("KAFKA_BATCH_SIZE", 100),
		BatchTimeout:         getEnvDuration("KAFKA_BATCH_TIMEOUT", 10*time.Millisecond),
		CompressionLevel:     getEnvInt("KAFKA_COMPRESSION_LEVEL", 6),
		MaxMessageBytes:      getEnvInt("KAFKA_MAX_MESSAGE_BYTES", 1000000),
		ConsumerFetchMin:     getEnvInt("KAFKA_CONSUMER_FETCH_MIN", 1),
		ConsumerFetchDefault: getEnvInt("KAFKA_CONSUMER_FETCH_DEFAULT", 1024),
		ConsumerFetchMax:     getEnvInt("KAFKA_CONSUMER_FETCH_MAX", 1048576),
	}
	
	return config, config.Validate()
}

// loadServiceURLs loads service URLs from environment variables
func loadServiceURLs() (ServiceURLs, error) {
	config := ServiceURLs{
		CoreEngine:  getEnv("CORE_ENGINE_URL", "localhost:50052"),
		AuthService: getEnv("AUTH_SERVICE_URL", "localhost:50051"),
		Analytics:   getEnv("ANALYTICS_SERVICE_URL", "localhost:50053"),
		VectorStore: getEnv("VECTOR_STORE_URL", "localhost:50054"),
	}
	
	return config, config.Validate()
}

// loadSecurityConfig loads security configuration from environment variables
func loadSecurityConfig() (SecurityConfig, error) {
	config := SecurityConfig{
		JWTSecret:           getEnvRequired("JWT_SECRET"),
		JWTExpiration:       getEnvDuration("JWT_EXPIRATION", 24*time.Hour),
		RefreshExpiration:   getEnvDuration("REFRESH_TOKEN_EXPIRATION", 7*24*time.Hour),
		BcryptCost:          getEnvInt("BCRYPT_COST", 12),
		RateLimitEnabled:    getEnvBool("RATE_LIMIT_ENABLED", true),
		RateLimitRPS:        getEnvInt("RATE_LIMIT_RPS", 100),
		RateLimitBurst:      getEnvInt("RATE_LIMIT_BURST", 200),
		CORSAllowedOrigins:  strings.Split(getEnv("CORS_ALLOWED_ORIGINS", "*"), ","),
		CORSAllowedMethods:  strings.Split(getEnv("CORS_ALLOWED_METHODS", "GET,POST,PUT,DELETE,OPTIONS"), ","),
		CORSAllowedHeaders:  strings.Split(getEnv("CORS_ALLOWED_HEADERS", "Content-Type,Authorization"), ","),
		EnableHTTPSRedirect: getEnvBool("ENABLE_HTTPS_REDIRECT", false),
		TrustedProxies:      strings.Split(getEnv("TRUSTED_PROXIES", ""), ","),
	}
	
	return config, config.Validate()
}

// loadLoggingConfig loads logging configuration from environment variables
func loadLoggingConfig() (LoggingConfig, error) {
	config := LoggingConfig{
		Level:         getEnv("LOG_LEVEL", "info"),
		Format:        getEnv("LOG_FORMAT", "json"),
		Output:        getEnv("LOG_OUTPUT", "stdout"),
		EnableConsole: getEnvBool("LOG_ENABLE_CONSOLE", true),
		EnableFile:    getEnvBool("LOG_ENABLE_FILE", false),
		FilePath:      getEnv("LOG_FILE_PATH", "/var/log/api-gateway.log"),
		MaxSize:       getEnvInt("LOG_MAX_SIZE", 100),
		MaxBackups:    getEnvInt("LOG_MAX_BACKUPS", 3),
		MaxAge:        getEnvInt("LOG_MAX_AGE", 28),
		Compress:      getEnvBool("LOG_COMPRESS", true),
	}
	
	return config, config.Validate()
}

// loadMetricsConfig loads metrics configuration from environment variables
func loadMetricsConfig() (MetricsConfig, error) {
	config := MetricsConfig{
		Enabled:   getEnvBool("METRICS_ENABLED", true),
		Path:      getEnv("METRICS_PATH", "/metrics"),
		Port:      getEnvInt("METRICS_PORT", 9090),
		Namespace: getEnv("METRICS_NAMESPACE", "market_intel"),
		Subsystem: getEnv("METRICS_SUBSYSTEM", "api_gateway"),
	}
	
	return config, config.Validate()
}

// Helper functions for environment variable parsing with validation

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvRequired(key string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	panic(fmt.Sprintf("required environment variable %s is not set", key))
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getEnvInt64(key string, defaultValue int64) int64 {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.ParseInt(value, 10, 64); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getEnvBool(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolValue, err := strconv.ParseBool(value); err == nil {
			return boolValue
		}
	}
	return defaultValue
}

func getEnvDuration(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if duration, err := time.ParseDuration(value); err == nil {
			return duration
		}
	}
	return defaultValue
}

// GetHTTPPort returns the HTTP port as a string
func (c *Config) GetHTTPPort() string {
	return fmt.Sprintf(":%d", c.Server.HTTPPort)
}

// GetGRPCPort returns the gRPC port as a string
func (c *Config) GetGRPCPort() string {
	return fmt.Sprintf(":%d", c.Server.GRPCPort)
}

// GetDatabaseURL returns the database connection URL
func (c *Config) GetDatabaseURL() string {
	return fmt.Sprintf("postgres://%s:%s@%s:%d/%s?sslmode=%s",
		c.Database.Username,
		c.Database.Password,
		c.Database.Host,
		c.Database.Port,
		c.Database.Database,
		c.Database.SSLMode,
	)
}

// GetRedisURL returns the Redis connection URL
func (c *Config) GetRedisURL() string {
	if c.Redis.Password != "" {
		return fmt.Sprintf("redis://%s@%s:%d/%d",
			c.Redis.Password,
			c.Redis.Host,
			c.Redis.Port,
			c.Redis.Database,
		)
	}
	return fmt.Sprintf("redis://%s:%d/%d",
		c.Redis.Host,
		c.Redis.Port,
		c.Redis.Database,
	)
}
