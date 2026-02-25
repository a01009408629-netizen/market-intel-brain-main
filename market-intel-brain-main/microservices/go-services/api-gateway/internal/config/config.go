package config

import (
	"fmt"
	"os"
	"strconv"
)

type Config struct {
	HTTPPort      int    `mapstructure:"http_port"`
	GRPCPort      int    `mapstructure:"grpc_port"`
	DatabaseURL   string `mapstructure:"database_url"`
	RedisURL      string `mapstructure:"redis_url"`
	RedpandaBrokers string `mapstructure:"redpanda_brokers"`
	CoreEngineURL string `mapstructure:"core_engine_url"`
	AuthServiceURL string `mapstructure:"auth_service_url"`
	LogLevel      string `mapstructure:"log_level"`
	Environment   string `mapstructure:"environment"`
}

func Load(configFile string) (*Config, error) {
	config := &Config{
		HTTPPort:       getEnvInt("HTTP_PORT", 8080),
		GRPCPort:       getEnvInt("GRPC_PORT", 8081),
		DatabaseURL:    getEnv("DATABASE_URL", "postgres://postgres:postgres@localhost:5432/market_intel"),
		RedisURL:       getEnv("REDIS_URL", "redis://localhost:6379"),
		RedpandaBrokers: getEnv("REDPANDA_BROKERS", "localhost:9092"),
		CoreEngineURL: getEnv("CORE_ENGINE_URL", "localhost:50052"),
		AuthServiceURL: getEnv("AUTH_SERVICE_URL", "localhost:50051"),
		LogLevel:       getEnv("LOG_LEVEL", "info"),
		Environment:    getEnv("ENVIRONMENT", "development"),
	}

	return config, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func (c *Config) GetHTTPPort() string {
	return fmt.Sprintf(":%d", c.HTTPPort)
}

func (c *Config) GetGRPCPort() string {
	return fmt.Sprintf(":%d", c.GRPCPort)
}
