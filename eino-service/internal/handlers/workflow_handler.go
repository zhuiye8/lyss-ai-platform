package handlers

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/models"
	"lyss-ai-platform/eino-service/internal/workflows"
)

// WorkflowHandler 工作流处理器
type WorkflowHandler struct {
	workflowManager *workflows.WorkflowManager
	logger          *logrus.Logger
}

// NewWorkflowHandler 创建工作流处理器
func NewWorkflowHandler(workflowManager *workflows.WorkflowManager, logger *logrus.Logger) *WorkflowHandler {
	return &WorkflowHandler{
		workflowManager: workflowManager,
		logger:          logger,
	}
}

// ExecuteWorkflow 执行工作流
func (h *WorkflowHandler) ExecuteWorkflow(c *gin.Context) {
	var req models.ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		h.respondWithError(c, http.StatusBadRequest, "请求格式错误", err)
		return
	}

	// 从请求头获取租户和用户信息
	tenantID := c.GetHeader("X-Tenant-ID")
	userID := c.GetHeader("X-User-ID")
	
	if tenantID == "" || userID == "" {
		h.respondWithError(c, http.StatusBadRequest, "缺少租户或用户信息", nil)
		return
	}

	// 生成请求ID和执行ID
	requestID := c.GetHeader("X-Request-ID")
	if requestID == "" {
		requestID = uuid.New().String()
	}
	
	executionID := uuid.New().String()

	// 构建工作流请求
	workflowReq := &workflows.WorkflowRequest{
		RequestID:     requestID,
		ExecutionID:   executionID,
		TenantID:      tenantID,
		UserID:        userID,
		WorkflowType:  "simple_chat", // 默认使用简单聊天工作流
		Message:       req.Message,
		ModelConfig:   req.ModelConfig,
		Configuration: make(map[string]interface{}),
		Stream:        req.Stream,
	}

	// 设置模型配置
	if req.Model != "" {
		workflowReq.ModelConfig["model"] = req.Model
	}
	if req.Temperature != 0 {
		workflowReq.ModelConfig["temperature"] = req.Temperature
	}
	if req.MaxTokens != 0 {
		workflowReq.ModelConfig["max_tokens"] = req.MaxTokens
	}
	workflowReq.ModelConfig["stream"] = req.Stream

	// 记录请求
	h.logger.WithFields(logrus.Fields{
		"request_id":     requestID,
		"execution_id":   executionID,
		"tenant_id":      tenantID,
		"user_id":        userID,
		"workflow_type":  "simple_chat",
		"message_length": len(req.Message),
		"model":          req.Model,
		"stream":         req.Stream,
		"operation":      "workflow_request",
	}).Info("收到工作流执行请求")

	// 检查是否为流式响应
	if req.Stream {
		h.handleStreamResponse(c, workflowReq)
		return
	}

	// 执行工作流
	response, err := h.workflowManager.ExecuteWorkflow(c.Request.Context(), workflowReq)
	if err != nil {
		h.respondWithError(c, http.StatusInternalServerError, "工作流执行失败", err)
		return
	}

	// 构建聊天响应
	chatResponse := &models.ChatResponse{
		ID:              response.Metadata["response_id"].(string),
		Content:         response.Content,
		Model:           response.Model,
		WorkflowType:    response.WorkflowType,
		ExecutionTimeMs: response.ExecutionTimeMs,
		Usage:           response.Usage,
		Metadata:        response.Metadata,
	}

	// 返回成功响应
	h.respondWithSuccess(c, chatResponse)
}

// handleStreamResponse 处理流式响应
func (h *WorkflowHandler) handleStreamResponse(c *gin.Context, req *workflows.WorkflowRequest) {
	// 设置流式响应头
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("Access-Control-Allow-Origin", "*")

	// 获取流式响应通道
	responseCh, err := h.workflowManager.ExecuteWorkflowStream(c.Request.Context(), req)
	if err != nil {
		h.sendSSEError(c, err)
		return
	}

	// 发送流式响应
	for streamResp := range responseCh {
		switch streamResp.Type {
		case "data":
			h.sendSSEData(c, streamResp.Content)
		case "error":
			h.sendSSEError(c, fmt.Errorf(streamResp.Error))
			return
		case "done":
			h.sendSSEDone(c)
			return
		}
	}
}

// sendSSEData 发送SSE数据
func (h *WorkflowHandler) sendSSEData(c *gin.Context, content string) {
	c.Writer.WriteString(fmt.Sprintf("data: %s\n\n", content))
	c.Writer.Flush()
}

// sendSSEError 发送SSE错误
func (h *WorkflowHandler) sendSSEError(c *gin.Context, err error) {
	errorData := map[string]interface{}{
		"error": err.Error(),
	}
	jsonData, _ := json.Marshal(errorData)
	c.Writer.WriteString(fmt.Sprintf("event: error\ndata: %s\n\n", string(jsonData)))
	c.Writer.Flush()
}

// sendSSEDone 发送SSE完成信号
func (h *WorkflowHandler) sendSSEDone(c *gin.Context) {
	c.Writer.WriteString("event: done\ndata: {}\n\n")
	c.Writer.Flush()
}

// ListWorkflows 列出所有工作流
func (h *WorkflowHandler) ListWorkflows(c *gin.Context) {
	workflows := h.workflowManager.ListWorkflows()
	h.respondWithSuccess(c, workflows)
}

// GetWorkflowInfo 获取工作流信息
func (h *WorkflowHandler) GetWorkflowInfo(c *gin.Context) {
	workflowName := c.Param("name")
	if workflowName == "" {
		h.respondWithError(c, http.StatusBadRequest, "工作流名称不能为空", nil)
		return
	}

	info, err := h.workflowManager.GetWorkflowInfo(workflowName)
	if err != nil {
		h.respondWithError(c, http.StatusNotFound, "工作流不存在", err)
		return
	}

	h.respondWithSuccess(c, info)
}

// GetExecutionStatus 获取执行状态
func (h *WorkflowHandler) GetExecutionStatus(c *gin.Context) {
	executionID := c.Param("execution_id")
	if executionID == "" {
		h.respondWithError(c, http.StatusBadRequest, "执行ID不能为空", nil)
		return
	}

	status, err := h.workflowManager.GetExecutionStatus(executionID)
	if err != nil {
		h.respondWithError(c, http.StatusNotFound, "执行记录不存在", err)
		return
	}

	h.respondWithSuccess(c, status)
}

// CancelExecution 取消执行
func (h *WorkflowHandler) CancelExecution(c *gin.Context) {
	executionID := c.Param("execution_id")
	if executionID == "" {
		h.respondWithError(c, http.StatusBadRequest, "执行ID不能为空", nil)
		return
	}

	err := h.workflowManager.CancelExecution(executionID)
	if err != nil {
		h.respondWithError(c, http.StatusBadRequest, "取消执行失败", err)
		return
	}

	h.respondWithSuccess(c, map[string]interface{}{
		"execution_id": executionID,
		"status":       "cancelled",
	})
}

// GetMetrics 获取工作流指标
func (h *WorkflowHandler) GetMetrics(c *gin.Context) {
	metrics := h.workflowManager.GetMetrics()
	h.respondWithSuccess(c, metrics)
}

// respondWithSuccess 返回成功响应
func (h *WorkflowHandler) respondWithSuccess(c *gin.Context, data interface{}) {
	response := models.ApiResponse[interface{}]{
		Success:   true,
		Data:      data,
		Message:   "请求成功",
		RequestID: c.GetHeader("X-Request-ID"),
		Timestamp: fmt.Sprintf("%d", c.GetInt64("timestamp")),
	}

	c.JSON(http.StatusOK, response)
}

// respondWithError 返回错误响应
func (h *WorkflowHandler) respondWithError(c *gin.Context, statusCode int, message string, err error) {
	errorResponse := models.ErrorResponse{
		Code:    fmt.Sprintf("E%d", statusCode),
		Message: message,
		Details: make(map[string]interface{}),
	}

	if err != nil {
		errorResponse.Details["error"] = err.Error()
		h.logger.WithFields(logrus.Fields{
			"request_id": c.GetHeader("X-Request-ID"),
			"status":     statusCode,
			"message":    message,
			"error":      err.Error(),
			"path":       c.Request.URL.Path,
			"method":     c.Request.Method,
		}).Error("请求处理失败")
	}

	response := models.ApiResponse[interface{}]{
		Success:   false,
		Data:      nil,
		Message:   message,
		RequestID: c.GetHeader("X-Request-ID"),
		Timestamp: fmt.Sprintf("%d", c.GetInt64("timestamp")),
	}

	c.JSON(statusCode, response)
}

// extractTenantInfo 提取租户信息中间件
func (h *WorkflowHandler) extractTenantInfo() gin.HandlerFunc {
	return func(c *gin.Context) {
		// 从JWT或请求头提取租户信息
		tenantID := c.GetHeader("X-Tenant-ID")
		userID := c.GetHeader("X-User-ID")

		if tenantID == "" || userID == "" {
			h.respondWithError(c, http.StatusUnauthorized, "缺少认证信息", nil)
			c.Abort()
			return
		}

		// 验证租户ID和用户ID格式
		if _, err := uuid.Parse(tenantID); err != nil {
			h.respondWithError(c, http.StatusBadRequest, "租户ID格式错误", err)
			c.Abort()
			return
		}

		if _, err := uuid.Parse(userID); err != nil {
			h.respondWithError(c, http.StatusBadRequest, "用户ID格式错误", err)
			c.Abort()
			return
		}

		c.Set("tenant_id", tenantID)
		c.Set("user_id", userID)
		c.Next()
	}
}

// requestIDMiddleware 请求ID中间件
func (h *WorkflowHandler) requestIDMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		requestID := c.GetHeader("X-Request-ID")
		if requestID == "" {
			requestID = uuid.New().String()
			c.Header("X-Request-ID", requestID)
		}
		
		c.Set("request_id", requestID)
		c.Next()
	}
}

// corsMiddleware CORS中间件
func (h *WorkflowHandler) corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		if origin == "" {
			origin = "*"
		}
		
		c.Header("Access-Control-Allow-Origin", origin)
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Tenant-ID, X-User-ID, X-Request-ID")
		c.Header("Access-Control-Allow-Credentials", "true")
		c.Header("Access-Control-Max-Age", "86400")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

// loggerMiddleware 日志中间件
func (h *WorkflowHandler) loggerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := c.GetInt64("start_time")
		c.Next()
		
		duration := c.GetInt64("end_time") - start
		
		h.logger.WithFields(logrus.Fields{
			"method":     c.Request.Method,
			"path":       c.Request.URL.Path,
			"status":     c.Writer.Status(),
			"duration":   duration,
			"request_id": c.GetHeader("X-Request-ID"),
			"tenant_id":  c.GetHeader("X-Tenant-ID"),
			"user_id":    c.GetHeader("X-User-ID"),
		}).Info("HTTP请求处理完成")
	}
}

// RegisterRoutes 注册路由
func (h *WorkflowHandler) RegisterRoutes(r *gin.Engine) {
	// 应用中间件
	r.Use(h.corsMiddleware())
	r.Use(h.requestIDMiddleware())
	r.Use(h.loggerMiddleware())

	// API版本组
	v1 := r.Group("/api/v1")
	{
		// 聊天接口
		v1.POST("/chat", h.extractTenantInfo(), h.ExecuteWorkflow)
		
		// 工作流管理接口
		workflows := v1.Group("/workflows")
		{
			workflows.GET("", h.ListWorkflows)
			workflows.GET("/:name", h.GetWorkflowInfo)
		}
		
		// 执行管理接口
		executions := v1.Group("/executions")
		{
			executions.GET("/:execution_id", h.GetExecutionStatus)
			executions.DELETE("/:execution_id", h.CancelExecution)
		}
		
		// 指标接口
		v1.GET("/metrics", h.GetMetrics)
	}
}