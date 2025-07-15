package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/pkg/health"
)

// HealthHandler 健康检查处理器
type HealthHandler struct {
	healthChecker *health.Checker
	logger        *logrus.Logger
}

// NewHealthHandler 创建新的健康检查处理器
func NewHealthHandler(healthChecker *health.Checker, logger *logrus.Logger) *HealthHandler {
	return &HealthHandler{
		healthChecker: healthChecker,
		logger:        logger,
	}
}

// HealthCheck 健康检查接口
func (h *HealthHandler) HealthCheck(c *gin.Context) {
	health := h.healthChecker.CheckHealth()
	
	// 根据健康状态设置HTTP状态码
	statusCode := http.StatusOK
	if health.Status != "healthy" {
		statusCode = http.StatusServiceUnavailable
	}
	
	h.logger.WithFields(logrus.Fields{
		"status":      health.Status,
		"metrics":     health.Metrics,
		"dependencies": health.Dependencies,
	}).Debug("健康检查完成")
	
	c.JSON(statusCode, health)
}