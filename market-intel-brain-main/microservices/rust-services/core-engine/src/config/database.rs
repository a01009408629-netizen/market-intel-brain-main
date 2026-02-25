// Copyright (c) 2024 Market Intel Brain Team
// Database configuration module

use std::time::Duration;
use serde::{Deserialize, Serialize};
use super::{ConfigError, parse_env_var, parse_optional_env_var, parse_duration_env};

/// Database configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    pub host: String,
    pub port: u16,
    pub database: String,
    pub username: String,
    pub password: String,
    pub max_connections: u32,
    pub min_connections: u32,
    pub connection_timeout: Duration,
    pub idle_timeout: Duration,
    pub max_lifetime: Duration,
    pub ssl_mode: SslMode,
    pub ssl_cert_path: Option<String>,
    pub ssl_key_path: Option<String>,
    pub ssl_ca_path: Option<String>,
    pub application_name: String,
    pub statement_timeout: Duration,
    pub read_timeout: Duration,
    pub write_timeout: Duration,
}

/// SSL mode for database connections
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SslMode {
    Disable,
    Prefer,
    Require,
    VerifyCa,
    VerifyFull,
}

impl Default for DatabaseConfig {
    fn default() -> Self {
        Self {
            host: "localhost".to_string(),
            port: 5432,
            database: "market_intel".to_string(),
            username: "postgres".to_string(),
            password: "".to_string(),
            max_connections: 20,
            min_connections: 5,
            connection_timeout: Duration::from_secs(30),
            idle_timeout: Duration::from_secs(600),
            max_lifetime: Duration::from_secs(1800),
            ssl_mode: SslMode::Prefer,
            ssl_cert_path: None,
            ssl_key_path: None,
            ssl_ca_path: None,
            application_name: "core-engine".to_string(),
            statement_timeout: Duration::from_secs(30),
            read_timeout: Duration::from_secs(30),
            write_timeout: Duration::from_secs(30),
        }
    }
}

impl DatabaseConfig {
    pub fn from_env() -> Result<Self, ConfigError> {
        let host = parse_env_var("DB_HOST", "localhost")?;
        let port = parse_env_var("DB_PORT", "5432")?;
        let database = parse_env_var("DB_NAME", "market_intel")?;
        let username = parse_env_var("DB_USERNAME", "postgres")?;
        let password = env::var("DB_PASSWORD")
            .map_err(|_| ConfigError::MissingEnvVar("DB_PASSWORD".to_string()))?;
        let max_connections = parse_env_var("DB_MAX_CONNECTIONS", "20")?;
        let min_connections = parse_env_var("DB_MIN_CONNECTIONS", "5")?;
        let connection_timeout = parse_duration_env("DB_CONNECTION_TIMEOUT", "30s")?;
        let idle_timeout = parse_duration_env("DB_IDLE_TIMEOUT", "600s")?;
        let max_lifetime = parse_duration_env("DB_MAX_LIFETIME", "1800s")?;
        let ssl_mode = parse_ssl_mode_env("DB_SSL_MODE", SslMode::Prefer)?;
        let ssl_cert_path = parse_optional_env_var("DB_SSL_CERT_PATH")?;
        let ssl_key_path = parse_optional_env_var("DB_SSL_KEY_PATH")?;
        let ssl_ca_path = parse_optional_env_var("DB_SSL_CA_PATH")?;
        let application_name = parse_env_var("DB_APPLICATION_NAME", "core-engine")?;
        let statement_timeout = parse_duration_env("DB_STATEMENT_TIMEOUT", "30s")?;
        let read_timeout = parse_duration_env("DB_READ_TIMEOUT", "30s")?;
        let write_timeout = parse_duration_env("DB_WRITE_TIMEOUT", "30s")?;

        let config = Self {
            host,
            port,
            database,
            username,
            password,
            max_connections,
            min_connections,
            connection_timeout,
            idle_timeout,
            max_lifetime,
            ssl_mode,
            ssl_cert_path,
            ssl_key_path,
            ssl_ca_path,
            application_name,
            statement_timeout,
            read_timeout,
            write_timeout,
        };

        config.validate()?;
        Ok(config)
    }

    pub fn validate(&self) -> Result<(), ConfigError> {
        if self.host.is_empty() {
            return Err(ConfigError::ValidationError("Database host cannot be empty".to_string()));
        }
        
        if self.port == 0 {
            return Err(ConfigError::ValidationError("Database port cannot be 0".to_string()));
        }
        
        if self.database.is_empty() {
            return Err(ConfigError::ValidationError("Database name cannot be empty".to_string()));
        }
        
        if self.username.is_empty() {
            return Err(ConfigError::ValidationError("Database username cannot be empty".to_string()));
        }
        
        if self.password.is_empty() {
            return Err(ConfigError::ValidationError("Database password cannot be empty".to_string()));
        }
        
        if self.max_connections == 0 {
            return Err(ConfigError::ValidationError("Max connections cannot be 0".to_string()));
        }
        
        if self.min_connections > self.max_connections {
            return Err(ConfigError::ValidationError(
                "Min connections cannot be greater than max connections".to_string()
            ));
        }
        
        if self.connection_timeout.is_zero() {
            return Err(ConfigError::ValidationError("Connection timeout cannot be zero".to_string()));
        }
        
        if self.idle_timeout.is_zero() {
            return Err(ConfigError::ValidationError("Idle timeout cannot be zero".to_string()));
        }
        
        if self.max_lifetime.is_zero() {
            return Err(ConfigError::ValidationError("Max lifetime cannot be zero".to_string()));
        }
        
        if self.application_name.is_empty() {
            return Err(ConfigError::ValidationError("Application name cannot be empty".to_string()));
        }
        
        if self.statement_timeout.is_zero() {
            return Err(ConfigError::ValidationError("Statement timeout cannot be zero".to_string()));
        }
        
        if self.read_timeout.is_zero() {
            return Err(ConfigError::ValidationError("Read timeout cannot be zero".to_string()));
        }
        
        if self.write_timeout.is_zero() {
            return Err(ConfigError::ValidationError("Write timeout cannot be zero".to_string()));
        }

        // Validate SSL configuration
        match self.ssl_mode {
            SslMode::Require | SslMode::VerifyCa | SslMode::VerifyFull => {
                if self.ssl_ca_path.is_none() {
                    return Err(ConfigError::ValidationError(
                        "SSL CA path is required for this SSL mode".to_string()
                    ));
                }
            }
            _ => {}
        }

        Ok(())
    }

    pub fn connection_string(&self) -> String {
        format!(
            "postgresql://{}:{}@{}:{}/{}?application_name={}&sslmode={}",
            self.username,
            self.password,
            self.host,
            self.port,
            self.database,
            self.application_name,
            self.ssl_mode_as_string()
        )
    }

    fn ssl_mode_as_string(&self) -> &'static str {
        match self.ssl_mode {
            SslMode::Disable => "disable",
            SslMode::Prefer => "prefer",
            SslMode::Require => "require",
            SslMode::VerifyCa => "verify-ca",
            SslMode::VerifyFull => "verify-full",
        }
    }
}

fn parse_ssl_mode_env(key: &str, default: SslMode) -> Result<SslMode, ConfigError> {
    match std::env::var(key) {
        Ok(value) => {
            match value.to_lowercase().as_str() {
                "disable" => Ok(SslMode::Disable),
                "prefer" => Ok(SslMode::Prefer),
                "require" => Ok(SslMode::Require),
                "verify-ca" => Ok(SslMode::VerifyCa),
                "verify-full" => Ok(SslMode::VerifyFull),
                _ => Err(ConfigError::InvalidEnvVar(
                    key.to_string(),
                    "Expected 'disable', 'prefer', 'require', 'verify-ca', or 'verify-full'".to_string(),
                )),
            }
        }
        Err(_) => Ok(default),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_database_config_from_env() {
        env::set_var("DB_HOST", "test-host");
        env::set_var("DB_PORT", "5433");
        env::set_var("DB_NAME", "test-db");
        env::set_var("DB_USERNAME", "test-user");
        env::set_var("DB_PASSWORD", "test-pass");
        env::set_var("DB_SSL_MODE", "require");
        
        let config = DatabaseConfig::from_env().unwrap();
        assert_eq!(config.host, "test-host");
        assert_eq!(config.port, 5433);
        assert_eq!(config.database, "test-db");
        assert_eq!(config.username, "test-user");
        assert_eq!(config.password, "test-pass");
        assert_eq!(config.ssl_mode, SslMode::Require);
        
        env::remove_var("DB_HOST");
        env::remove_var("DB_PORT");
        env::remove_var("DB_NAME");
        env::remove_var("DB_USERNAME");
        env::remove_var("DB_PASSWORD");
        env::remove_var("DB_SSL_MODE");
    }

    #[test]
    fn test_database_config_validation() {
        let mut config = DatabaseConfig::default();
        
        // Test valid config
        assert!(config.validate().is_ok());
        
        // Test invalid host
        config.host = "".to_string();
        assert!(config.validate().is_err());
        
        config.host = "localhost".to_string();
        config.port = 0;
        assert!(config.validate().is_err());
    }

    #[test]
    fn test_ssl_mode_parsing() {
        env::set_var("TEST_SSL_MODE", "disable");
        assert!(matches!(parse_ssl_mode_env("TEST_SSL_MODE", SslMode::Prefer).unwrap(), SslMode::Disable));
        
        env::set_var("TEST_SSL_MODE", "require");
        assert!(matches!(parse_ssl_mode_env("TEST_SSL_MODE", SslMode::Prefer).unwrap(), SslMode::Require));
        
        env::set_var("TEST_SSL_MODE", "verify-full");
        assert!(matches!(parse_ssl_mode_env("TEST_SSL_MODE", SslMode::Prefer).unwrap(), SslMode::VerifyFull));
        
        env::remove_var("TEST_SSL_MODE");
        assert!(matches!(parse_ssl_mode_env("TEST_SSL_MODE", SslMode::Prefer).unwrap(), SslMode::Prefer));
    }

    #[test]
    fn test_connection_string() {
        let config = DatabaseConfig {
            host: "localhost".to_string(),
            port: 5432,
            database: "test".to_string(),
            username: "user".to_string(),
            password: "pass".to_string(),
            application_name: "test-app".to_string(),
            ssl_mode: SslMode::Require,
            ..Default::default()
        };
        
        let conn_str = config.connection_string();
        assert!(conn_str.contains("postgresql://user:pass@localhost:5432/test"));
        assert!(conn_str.contains("application_name=test-app"));
        assert!(conn_str.contains("sslmode=require"));
    }
}
