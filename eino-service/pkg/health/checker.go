package health

import (
	"context"
	"runtime"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/client"
	"lyss-ai-platform/eino-service/internal/models"
	"lyss-ai-platform/eino-service/pkg/credential"
)

// Checker 健康检查器
type Checker struct {
	tenantClient      *client.TenantClient
	redisClient       *redis.Client
	credentialManager *credential.Manager
	logger            *logrus.Logger
}

// NewChecker 创建新的健康检查器
func NewChecker(tenantClient *client.TenantClient, redisClient *redis.Client, credentialManager *credential.Manager, logger *logrus.Logger) *Checker {
	return &Checker{
		tenantClient:      tenantClient,
		redisClient:       redisClient,
		credentialManager: credentialManager,
		logger:            logger,
	}
}

// HealthResult 健康检查结果
type HealthResult struct {
	Status        string            `json:"status"`
	Dependencies  map[string]string `json:"dependencies"`
	ResponseTimes map[string]int64  `json:"response_times"`
	Metrics       map[string]int    `json:"metrics"`
}

// Check 执行健康检查
func (c *Checker) Check(ctx context.Context) *HealthResult {
	result := &HealthResult{
		Status:        "healthy",
		Dependencies:  make(map[string]string),
		ResponseTimes: make(map[string]int64),
		Metrics:       make(map[string]int),
	}
	
	// 检查租户服务
	start := time.Now()
	if err := c.checkTenantService(ctx); err != nil {
		result.Dependencies["tenant_service"] = "unhealthy"
		result.Status = "unhealthy"
		c.logger.WithError(err).Error("租户服务健康检查失败")
	} else {
		result.Dependencies["tenant_service"] = "healthy"
	}
	result.ResponseTimes["tenant_service"] = time.Since(start).Milliseconds()
	
	// 检查Redis
	start = time.Now()
	if err := c.checkRedis(ctx); err != nil {
		result.Dependencies["redis"] = "unhealthy"
		result.Status = "unhealthy"
		c.logger.WithError(err).Error("Redis健康检查失败")
	} else {
		result.Dependencies["redis"] = "healthy"
	}
	result.ResponseTimes["redis"] = time.Since(start).Milliseconds()
	
	// 检查数据库（通过租户服务间接检查）
	start = time.Now()
	if err := c.checkDatabase(ctx); err != nil {
		result.Dependencies["database"] = "unhealthy"
		result.Status = "unhealthy"
		c.logger.WithError(err).Error("数据库健康检查失败")
	} else {
		result.Dependencies["database"] = "healthy"
	}
	result.ResponseTimes["database"] = time.Since(start).Milliseconds()
	
	// 获取系统指标
	result.Metrics["goroutines"] = runtime.NumGoroutine()
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	result.Metrics["memory_mb"] = int(m.Alloc / 1024 / 1024)
	result.Metrics["cpu_usage"] = 0 // 简化处理，实际应用中可以获取CPU使用率
	
	return result
}

// CheckHealth 执行健康检查（兼容性方法）
func (c *Checker) CheckHealth() *models.HealthResponse {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	
	result := c.Check(ctx)
	
	response := &models.HealthResponse{
		Status:       result.Status,
		Timestamp:    time.Now().Format(time.RFC3339),
		Version:      "1.0.0",
		Dependencies: result.Dependencies,
		Metrics:      result.Metrics,
	}
	
	// 获取凭证统计
	stats := c.credentialManager.GetCredentialStats()
	if totalCredentials, ok := stats["total_credentials"].(int); ok {
		response.Metrics["total_credentials"] = totalCredentials
	}
	if healthyCredentials, ok := stats["healthy_credentials"].(int); ok {
		response.Metrics["healthy_credentials"] = healthyCredentials
	}
	if totalUsage, ok := stats["total_usage"].(int64); ok {
		response.Metrics["total_usage"] = int(totalUsage)
	}
	
	return response
}

// checkTenantService 检查租户服务
func (c *Checker) checkTenantService(ctx context.Context) error {
	return c.tenantClient.HealthCheck(ctx)
}

// checkRedis 检查Redis
func (c *Checker) checkRedis(ctx context.Context) error {
	return c.redisClient.Ping(ctx).Err()
}

// checkDatabase 检查数据库（通过租户服务间接检查）
func (c *Checker) checkDatabase(ctx context.Context) error {
	// 通过租户服务检查数据库连接
	return c.tenantClient.HealthCheck(ctx)
}