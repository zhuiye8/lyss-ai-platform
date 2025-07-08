package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

// Config holds all configuration for the EINO service
type Config struct {
	Environment string
	Server      ServerConfig
	Database    DatabaseConfig
	Redis       RedisConfig
	Monitoring  MonitoringConfig
	AI          AIConfig
	Workflow    WorkflowConfig
}

// ServerConfig holds HTTP server configuration
type ServerConfig struct {
	Port         string
	Host         string
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
}

// DatabaseConfig holds database configuration
type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	Database string
	SSLMode  string
}

// RedisConfig holds Redis configuration
type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
}

// MonitoringConfig holds monitoring configuration
type MonitoringConfig struct {
	JaegerEndpoint string
	LogLevel       string
	MetricsEnabled bool
}

// AIConfig holds AI provider configuration
type AIConfig struct {
	DefaultProvider string
	Timeout         time.Duration
	MaxRetries      int
}

// WorkflowConfig holds workflow engine configuration
type WorkflowConfig struct {
	MaxConcurrency   int
	ExecutionTimeout time.Duration
	RetryAttempts    int
	RetryDelay       time.Duration
}

// Load loads configuration from environment variables
func Load() (*Config, error) {
	config := &Config{
		Environment: getEnv("ENVIRONMENT", "development"),
		Server: ServerConfig{
			Port:         getEnv("SERVER_PORT", "8080"),
			Host:         getEnv("SERVER_HOST", "0.0.0.0"),
			ReadTimeout:  getDurationEnv("SERVER_READ_TIMEOUT", 30*time.Second),
			WriteTimeout: getDurationEnv("SERVER_WRITE_TIMEOUT", 30*time.Second),
		},
		Database: DatabaseConfig{
			Host:     getEnv("DB_HOST", "localhost"),
			Port:     getEnv("DB_PORT", "5432"),
			User:     getEnv("DB_USER", "lyss_user"),
			Password: getEnv("DB_PASSWORD", "lyss_password"),
			Database: getEnv("DB_NAME", "lyss_platform"),
			SSLMode:  getEnv("DB_SSL_MODE", "disable"),
		},
		Redis: RedisConfig{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       getIntEnv("REDIS_DB", 0),
		},
		Monitoring: MonitoringConfig{
			JaegerEndpoint: getEnv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces"),
			LogLevel:       getEnv("LOG_LEVEL", "info"),
			MetricsEnabled: getBoolEnv("METRICS_ENABLED", true),
		},
		AI: AIConfig{
			DefaultProvider: getEnv("AI_DEFAULT_PROVIDER", "openai"),
			Timeout:         getDurationEnv("AI_TIMEOUT", 30*time.Second),
			MaxRetries:      getIntEnv("AI_MAX_RETRIES", 3),
		},
		Workflow: WorkflowConfig{
			MaxConcurrency:   getIntEnv("WORKFLOW_MAX_CONCURRENCY", 100),
			ExecutionTimeout: getDurationEnv("WORKFLOW_EXECUTION_TIMEOUT", 5*time.Minute),
			RetryAttempts:    getIntEnv("WORKFLOW_RETRY_ATTEMPTS", 3),
			RetryDelay:       getDurationEnv("WORKFLOW_RETRY_DELAY", 1*time.Second),
		},
	}

	return config, nil
}

// GetDSN returns the database connection string
func (d *DatabaseConfig) GetDSN() string {
	return fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		d.Host, d.Port, d.User, d.Password, d.Database, d.SSLMode)
}

// GetRedisAddr returns the Redis address
func (r *RedisConfig) GetRedisAddr() string {
	return fmt.Sprintf("%s:%s", r.Host, r.Port)
}

// Helper functions
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getIntEnv(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getBoolEnv(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolValue, err := strconv.ParseBool(value); err == nil {
			return boolValue
		}
	}
	return defaultValue
}

func getDurationEnv(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if duration, err := time.ParseDuration(value); err == nil {
			return duration
		}
	}
	return defaultValue
}