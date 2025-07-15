package handlers

import (
	"context"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/client"
	"lyss-ai-platform/eino-service/internal/models"
	"lyss-ai-platform/eino-service/pkg/credential"
	"lyss-ai-platform/eino-service/pkg/health"
)

// HealthHandler 健康检查处理器
type HealthHandler struct {
	healthChecker     *health.Checker
	credentialManager *credential.Manager
	tenantClient      *client.TenantClient
	logger            *logrus.Logger
}

// NewHealthHandler 创建健康检查处理器
func NewHealthHandler(
	healthChecker *health.Checker,
	credentialManager *credential.Manager,
	tenantClient *client.TenantClient,
	logger *logrus.Logger,
) *HealthHandler {
	return &HealthHandler{
		healthChecker:     healthChecker,
		credentialManager: credentialManager,
		tenantClient:      tenantClient,
		logger:            logger,
	}
}

// Health 健康检查
func (h *HealthHandler) Health(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Second)
	defer cancel()

	// 执行健康检查
	result := h.healthChecker.Check(ctx)

	// 获取凭证管理器统计信息
	credentialStats := h.credentialManager.GetCredentialStats()

	// 构建响应
	response := &models.HealthResponse{
		Status:    result.Status,
		Timestamp: time.Now().Format(time.RFC3339),
		Version:   "1.0.0",
		Dependencies: map[string]string{
			"database":      result.Dependencies["database"],
			"redis":         result.Dependencies["redis"],
			"tenant_service": result.Dependencies["tenant_service"],
		},
		Metrics: map[string]int{
			"total_credentials":  credentialStats["total_credentials"].(int),
			"healthy_credentials": credentialStats["healthy_credentials"].(int),
			"cache_size":         credentialStats["cache_size"].(int),
			"total_usage":        int(credentialStats["total_usage"].(int64)),
		},
	}

	// 根据健康状态返回适当的状态码
	statusCode := http.StatusOK
	if result.Status == "unhealthy" {
		statusCode = http.StatusServiceUnavailable
	}

	// 记录健康检查日志
	h.logger.WithFields(logrus.Fields{
		"status":             result.Status,
		"total_credentials":  credentialStats["total_credentials"],
		"healthy_credentials": credentialStats["healthy_credentials"],
		"operation":          "health_check",
	}).Info("健康检查完成")

	c.JSON(statusCode, response)
}

// HealthCheck 健康检查接口（兼容性）
func (h *HealthHandler) HealthCheck(c *gin.Context) {
	h.Health(c)
}

// ReadinessCheck 就绪检查
func (h *HealthHandler) ReadinessCheck(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 3*time.Second)
	defer cancel()

	// 检查关键依赖是否就绪
	ready := true
	dependencies := make(map[string]bool)

	// 检查租户服务
	if err := h.tenantClient.HealthCheck(ctx); err != nil {
		ready = false
		dependencies["tenant_service"] = false
		h.logger.WithError(err).Error("租户服务健康检查失败")
	} else {
		dependencies["tenant_service"] = true
	}

	// 检查凭证管理器
	credentialStats := h.credentialManager.GetCredentialStats()
	if credentialStats["total_credentials"].(int) == 0 {
		ready = false
		dependencies["credential_manager"] = false
		h.logger.Warning("凭证管理器中没有可用凭证")
	} else {
		dependencies["credential_manager"] = true
	}

	// 构建响应
	response := map[string]interface{}{
		"ready":        ready,
		"timestamp":    time.Now().Format(time.RFC3339),
		"dependencies": dependencies,
	}

	statusCode := http.StatusOK
	if !ready {
		statusCode = http.StatusServiceUnavailable
	}

	c.JSON(statusCode, response)
}

// LivenessCheck 存活检查
func (h *HealthHandler) LivenessCheck(c *gin.Context) {
	// 简单的存活检查，只要服务能响应就认为是存活的
	response := map[string]interface{}{
		"alive":     true,
		"timestamp": time.Now().Format(time.RFC3339),
		"uptime":    "unknown", // 这里应该是服务启动时间
	}

	c.JSON(http.StatusOK, response)
}

// DetailedHealth 详细健康检查
func (h *HealthHandler) DetailedHealth(c *gin.Context) {
	ctx, cancel := context.WithTimeout(c.Request.Context(), 10*time.Second)
	defer cancel()

	// 执行详细健康检查
	result := h.healthChecker.Check(ctx)

	// 获取详细的凭证统计信息
	credentialStats := h.credentialManager.GetCredentialStats()

	// 构建详细响应
	response := map[string]interface{}{
		"status":     result.Status,
		"timestamp":  time.Now().Format(time.RFC3339),
		"version":    "1.0.0",
		"service":    "eino-service",
		"dependencies": map[string]interface{}{
			"database": map[string]interface{}{
				"status":       result.Dependencies["database"],
				"response_time": result.ResponseTimes["database"],
			},
			"redis": map[string]interface{}{
				"status":       result.Dependencies["redis"],
				"response_time": result.ResponseTimes["redis"],
			},
			"tenant_service": map[string]interface{}{
				"status":       result.Dependencies["tenant_service"],
				"response_time": result.ResponseTimes["tenant_service"],
			},
		},
		"credential_manager": map[string]interface{}{
			"total_credentials":  credentialStats["total_credentials"],
			"healthy_credentials": credentialStats["healthy_credentials"],
			"cache_size":         credentialStats["cache_size"],
			"total_usage":        credentialStats["total_usage"],
		},
		"system": map[string]interface{}{
			"goroutines": result.Metrics["goroutines"],
			"memory_mb":  result.Metrics["memory_mb"],
			"cpu_usage":  result.Metrics["cpu_usage"],
		},
	}

	// 根据健康状态返回适当的状态码
	statusCode := http.StatusOK
	if result.Status == "unhealthy" {
		statusCode = http.StatusServiceUnavailable
	}

	h.logger.WithFields(logrus.Fields{
		"status":             result.Status,
		"total_credentials":  credentialStats["total_credentials"],
		"healthy_credentials": credentialStats["healthy_credentials"],
		"operation":          "detailed_health_check",
	}).Info("详细健康检查完成")

	c.JSON(statusCode, response)
}

// RegisterRoutes 注册健康检查路由
func (h *HealthHandler) RegisterRoutes(r *gin.Engine) {
	// 健康检查路由
	r.GET("/health", h.Health)
	r.GET("/health/readiness", h.ReadinessCheck)
	r.GET("/health/liveness", h.LivenessCheck)
	r.GET("/health/detailed", h.DetailedHealth)
}