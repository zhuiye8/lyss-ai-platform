package health

import (
	"context"
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

// CheckHealth 执行健康检查
func (c *Checker) CheckHealth() *models.HealthResponse {
	response := &models.HealthResponse{
		Status:       "healthy",
		Timestamp:    time.Now().Format(time.RFC3339),
		Version:      "1.0.0",
		Dependencies: make(map[string]string),
		Metrics:      make(map[string]int),
	}
	
	// 检查租户服务
	if err := c.checkTenantService(); err != nil {
		response.Dependencies["tenant_service"] = "unhealthy"
		response.Status = "unhealthy"
		c.logger.WithError(err).Error("租户服务健康检查失败")
	} else {
		response.Dependencies["tenant_service"] = "healthy"
	}
	
	// 检查Redis
	if err := c.checkRedis(); err != nil {
		response.Dependencies["redis"] = "unhealthy"
		response.Status = "unhealthy"
		c.logger.WithError(err).Error("Redis健康检查失败")
	} else {
		response.Dependencies["redis"] = "healthy"
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
func (c *Checker) checkTenantService() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	return c.tenantClient.HealthCheck(ctx)
}

// checkRedis 检查Redis
func (c *Checker) checkRedis() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	return c.redisClient.Ping(ctx).Err()
}