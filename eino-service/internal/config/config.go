package config

import (
	"fmt"
	"time"

	"github.com/spf13/viper"
)

// Config EINO服务配置结构
type Config struct {
	Server       ServerConfig       `mapstructure:"server"`
	Database     DatabaseConfig     `mapstructure:"database"`
	Redis        RedisConfig        `mapstructure:"redis"`
	Services     ServicesConfig     `mapstructure:"services"`
	Logging      LoggingConfig      `mapstructure:"logging"`
	Credential   CredentialConfig   `mapstructure:"credential"`
	Workflows    WorkflowsConfig    `mapstructure:"workflows"`
}

// ServerConfig 服务器配置
type ServerConfig struct {
	Host         string        `mapstructure:"host"`
	Port         int           `mapstructure:"port"`
	ReadTimeout  time.Duration `mapstructure:"read_timeout"`
	WriteTimeout time.Duration `mapstructure:"write_timeout"`
	IdleTimeout  time.Duration `mapstructure:"idle_timeout"`
}

// DatabaseConfig 数据库配置
type DatabaseConfig struct {
	Host     string `mapstructure:"host"`
	Port     int    `mapstructure:"port"`
	Username string `mapstructure:"username"`
	Password string `mapstructure:"password"`
	Database string `mapstructure:"database"`
	SSLMode  string `mapstructure:"ssl_mode"`
}

// RedisConfig Redis配置
type RedisConfig struct {
	Host     string `mapstructure:"host"`
	Port     int    `mapstructure:"port"`
	Password string `mapstructure:"password"`
	DB       int    `mapstructure:"db"`
}

// ServicesConfig 依赖服务配置
type ServicesConfig struct {
	TenantService TenantServiceConfig `mapstructure:"tenant_service"`
	MemoryService MemoryServiceConfig `mapstructure:"memory_service"`
}

// TenantServiceConfig 租户服务配置
type TenantServiceConfig struct {
	BaseURL string        `mapstructure:"base_url"`
	Timeout time.Duration `mapstructure:"timeout"`
}

// MemoryServiceConfig 记忆服务配置
type MemoryServiceConfig struct {
	BaseURL string        `mapstructure:"base_url"`
	Timeout time.Duration `mapstructure:"timeout"`
}

// LoggingConfig 日志配置
type LoggingConfig struct {
	Level      string `mapstructure:"level"`
	Format     string `mapstructure:"format"`
	Output     string `mapstructure:"output"`
	MaxSize    int    `mapstructure:"max_size"`
	MaxBackups int    `mapstructure:"max_backups"`
	MaxAge     int    `mapstructure:"max_age"`
}

// CredentialConfig 凭证管理配置
type CredentialConfig struct {
	CacheTTL           time.Duration `mapstructure:"cache_ttl"`
	HealthCheckInterval time.Duration `mapstructure:"health_check_interval"`
	MaxConcurrentTests int           `mapstructure:"max_concurrent_tests"`
}

// WorkflowsConfig 工作流配置
type WorkflowsConfig struct {
	MaxConcurrentExecutions int           `mapstructure:"max_concurrent_executions"`
	ExecutionTimeout        time.Duration `mapstructure:"execution_timeout"`
	DefaultStrategy         string        `mapstructure:"default_strategy"`
}

// LoadConfig 加载配置
func LoadConfig(configPath string) (*Config, error) {
	viper.SetConfigFile(configPath)
	viper.SetConfigType("yaml")
	
	// 设置默认值
	setDefaultValues()
	
	// 环境变量支持
	viper.SetEnvPrefix("EINO")
	viper.AutomaticEnv()
	
	if err := viper.ReadInConfig(); err != nil {
		return nil, fmt.Errorf("读取配置文件失败: %w", err)
	}
	
	var config Config
	if err := viper.Unmarshal(&config); err != nil {
		return nil, fmt.Errorf("解析配置文件失败: %w", err)
	}
	
	return &config, nil
}

// setDefaultValues 设置默认配置值
func setDefaultValues() {
	// 服务器默认配置
	viper.SetDefault("server.host", "0.0.0.0")
	viper.SetDefault("server.port", 8003)
	viper.SetDefault("server.read_timeout", "30s")
	viper.SetDefault("server.write_timeout", "30s")
	viper.SetDefault("server.idle_timeout", "120s")
	
	// 数据库默认配置
	viper.SetDefault("database.host", "localhost")
	viper.SetDefault("database.port", 5432)
	viper.SetDefault("database.username", "lyss_user")
	viper.SetDefault("database.password", "lyss_dev_password_2025")
	viper.SetDefault("database.database", "lyss_platform")
	viper.SetDefault("database.ssl_mode", "disable")
	
	// Redis默认配置
	viper.SetDefault("redis.host", "localhost")
	viper.SetDefault("redis.port", 6379)
	viper.SetDefault("redis.password", "")
	viper.SetDefault("redis.db", 0)
	
	// 依赖服务默认配置
	viper.SetDefault("services.tenant_service.base_url", "http://localhost:8002")
	viper.SetDefault("services.tenant_service.timeout", "30s")
	viper.SetDefault("services.memory_service.base_url", "http://localhost:8004")
	viper.SetDefault("services.memory_service.timeout", "30s")
	
	// 日志默认配置
	viper.SetDefault("logging.level", "info")
	viper.SetDefault("logging.format", "json")
	viper.SetDefault("logging.output", "stdout")
	viper.SetDefault("logging.max_size", 100)
	viper.SetDefault("logging.max_backups", 3)
	viper.SetDefault("logging.max_age", 7)
	
	// 凭证管理默认配置
	viper.SetDefault("credential.cache_ttl", "5m")
	viper.SetDefault("credential.health_check_interval", "2m")
	viper.SetDefault("credential.max_concurrent_tests", 10)
	
	// 工作流默认配置
	viper.SetDefault("workflows.max_concurrent_executions", 100)
	viper.SetDefault("workflows.execution_timeout", "5m")
	viper.SetDefault("workflows.default_strategy", "first_available")
}