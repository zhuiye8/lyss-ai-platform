package configs

import (
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

// Config 应用配置结构
type Config struct {
	Server   ServerConfig   `json:"server"`
	Database DatabaseConfig `json:"database"`
	Redis    RedisConfig    `json:"redis"`
	Logger   LoggerConfig   `json:"logger"`
	EINO     EINOConfig     `json:"eino"`
}

// ServerConfig 服务器配置
type ServerConfig struct {
	Host string `json:"host"`
	Port int    `json:"port"`
	Mode string `json:"mode"`
}

// DatabaseConfig 数据库配置
type DatabaseConfig struct {
	Host     string `json:"host"`
	Port     int    `json:"port"`
	User     string `json:"user"`
	Password string `json:"password"`
	Database string `json:"database"`
	SSLMode  string `json:"ssl_mode"`
}

// RedisConfig Redis配置
type RedisConfig struct {
	Host     string `json:"host"`
	Port     int    `json:"port"`
	Password string `json:"password"`
	Database int    `json:"database"`
}

// LoggerConfig 日志配置
type LoggerConfig struct {
	Level  string `json:"level"`
	Format string `json:"format"`
}

// EINOConfig EINO框架配置
type EINOConfig struct {
	DefaultProvider string            `json:"default_provider"`
	Providers       map[string]string `json:"providers"`
	Timeout         int               `json:"timeout"`
}

// LoadConfig 加载配置
func LoadConfig() (*Config, error) {
	// 加载.env文件
	_ = godotenv.Load()

	return &Config{
		Server: ServerConfig{
			Host: getEnv("SERVER_HOST", "0.0.0.0"),
			Port: getEnvAsInt("SERVER_PORT", 8004),
			Mode: getEnv("GIN_MODE", "debug"),
		},
		Database: DatabaseConfig{
			Host:     getEnv("DB_HOST", "localhost"),
			Port:     getEnvAsInt("DB_PORT", 5433),
			User:     getEnv("DB_USER", "lyss"),
			Password: getEnv("DB_PASSWORD", "test"),
			Database: getEnv("DB_NAME", "lyss_db"),
			SSLMode:  getEnv("DB_SSL_MODE", "disable"),
		},
		Redis: RedisConfig{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnvAsInt("REDIS_PORT", 6380),
			Password: getEnv("REDIS_PASSWORD", ""),
			Database: getEnvAsInt("REDIS_DB", 0),
		},
		Logger: LoggerConfig{
			Level:  getEnv("LOG_LEVEL", "info"),
			Format: getEnv("LOG_FORMAT", "json"),
		},
		EINO: EINOConfig{
			DefaultProvider: getEnv("EINO_DEFAULT_PROVIDER", "openai"),
			Providers: map[string]string{
				"openai":    getEnv("OPENAI_API_KEY", ""),
				"anthropic": getEnv("ANTHROPIC_API_KEY", ""),
				"deepseek":  getEnv("DEEPSEEK_API_KEY", ""),
			},
			Timeout: getEnvAsInt("EINO_TIMEOUT", 30),
		},
	}, nil
}

// getEnv 获取环境变量，如果不存在则返回默认值
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// getEnvAsInt 获取环境变量并转换为整数
func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}