package handlers

import (
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/models"
	"lyss-ai-platform/eino-service/pkg/credential"
)

// ChatHandler 聊天处理器
type ChatHandler struct {
	credentialManager *credential.Manager
	logger            *logrus.Logger
}

// NewChatHandler 创建新的聊天处理器
func NewChatHandler(credentialManager *credential.Manager, logger *logrus.Logger) *ChatHandler {
	return &ChatHandler{
		credentialManager: credentialManager,
		logger:            logger,
	}
}

// SimpleChat 简单聊天接口
func (h *ChatHandler) SimpleChat(c *gin.Context) {
	var request models.ChatRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		h.respondWithError(c, http.StatusBadRequest, "1001", "请求参数错误", map[string]interface{}{
			"error": err.Error(),
		})
		return
	}
	
	// 获取请求头信息
	userID := c.GetHeader("X-User-ID")
	tenantID := c.GetHeader("X-Tenant-ID")
	requestID := c.GetString("request_id")
	
	if userID == "" || tenantID == "" {
		h.respondWithError(c, http.StatusBadRequest, "2001", "缺少必要的请求头", map[string]interface{}{
			"required_headers": []string{"X-User-ID", "X-Tenant-ID"},
		})
		return
	}
	
	h.logger.WithFields(logrus.Fields{
		"request_id": requestID,
		"user_id":    userID,
		"tenant_id":  tenantID,
		"message":    request.Message,
		"model":      request.Model,
	}).Info("收到简单聊天请求")
	
	// 模拟处理（实际应该调用EINO工作流）
	startTime := time.Now()
	
	// 获取凭证
	provider := h.getProviderFromModel(request.Model)
	credential, err := h.credentialManager.GetBestCredentialForModel(tenantID, provider, request.Model)
	if err != nil {
		h.logger.WithError(err).WithFields(logrus.Fields{
			"request_id": requestID,
			"tenant_id":  tenantID,
			"provider":   provider,
			"model":      request.Model,
		}).Error("获取凭证失败")
		
		h.respondWithError(c, http.StatusInternalServerError, "5001", "获取凭证失败", map[string]interface{}{
			"provider": provider,
			"model":    request.Model,
		})
		return
	}
	
	// 记录凭证使用
	h.credentialManager.RecordUsage(credential.ID.String())
	
	// 模拟AI响应
	response := &models.ChatResponse{
		ID:              uuid.New().String(),
		Content:         h.generateMockResponse(request.Message, request.Model),
		Model:           request.Model,
		WorkflowType:    "simple_chat",
		ExecutionTimeMs: int(time.Since(startTime).Milliseconds()),
		Usage: models.TokenUsage{
			PromptTokens:     len(request.Message) / 4,
			CompletionTokens: 150,
			TotalTokens:      len(request.Message)/4 + 150,
		},
		Metadata: map[string]interface{}{
			"credential_id": credential.ID.String(),
			"provider":      credential.Provider,
		},
	}
	
	h.logger.WithFields(logrus.Fields{
		"request_id":       requestID,
		"user_id":          userID,
		"tenant_id":        tenantID,
		"execution_time":   response.ExecutionTimeMs,
		"credential_id":    credential.ID.String(),
		"provider":         credential.Provider,
	}).Info("简单聊天处理完成")
	
	h.respondWithSuccess(c, response, "聊天处理完成", requestID)
}

// StreamChat 流式聊天接口
func (h *ChatHandler) StreamChat(c *gin.Context) {
	var request models.ChatRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		h.respondWithError(c, http.StatusBadRequest, "1001", "请求参数错误", map[string]interface{}{
			"error": err.Error(),
		})
		return
	}
	
	// 获取请求头信息
	userID := c.GetHeader("X-User-ID")
	tenantID := c.GetHeader("X-Tenant-ID")
	requestID := c.GetString("request_id")
	
	if userID == "" || tenantID == "" {
		h.respondWithError(c, http.StatusBadRequest, "2001", "缺少必要的请求头", map[string]interface{}{
			"required_headers": []string{"X-User-ID", "X-Tenant-ID"},
		})
		return
	}
	
	h.logger.WithFields(logrus.Fields{
		"request_id": requestID,
		"user_id":    userID,
		"tenant_id":  tenantID,
		"message":    request.Message,
		"model":      request.Model,
	}).Info("收到流式聊天请求")
	
	// 设置SSE响应头
	c.Header("Content-Type", "text/event-stream")
	c.Header("Cache-Control", "no-cache")
	c.Header("Connection", "keep-alive")
	c.Header("Access-Control-Allow-Origin", "*")
	
	// 模拟流式响应
	flusher := c.Writer.(http.Flusher)
	
	// 发送开始事件
	c.SSEvent("start", map[string]interface{}{
		"execution_id": uuid.New().String(),
		"message":      "开始处理",
	})
	flusher.Flush()
	
	// 模拟分块响应
	message := "这是一个流式响应示例。EINO服务正在处理您的请求并生成实时响应。"
	for i, char := range message {
		if i > 0 && i%5 == 0 {
			time.Sleep(100 * time.Millisecond)
		}
		
		c.SSEvent("chunk", map[string]interface{}{
			"content": string(char),
			"delta":   string(char),
		})
		flusher.Flush()
	}
	
	// 发送结束事件
	c.SSEvent("end", map[string]interface{}{
		"usage": map[string]interface{}{
			"total_tokens": 200,
		},
		"execution_time_ms": 2000,
	})
	flusher.Flush()
}

// RAGChat RAG聊天接口
func (h *ChatHandler) RAGChat(c *gin.Context) {
	var request models.ChatRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		h.respondWithError(c, http.StatusBadRequest, "1001", "请求参数错误", map[string]interface{}{
			"error": err.Error(),
		})
		return
	}
	
	// 获取请求头信息
	userID := c.GetHeader("X-User-ID")
	tenantID := c.GetHeader("X-Tenant-ID")
	requestID := c.GetString("request_id")
	
	if userID == "" || tenantID == "" {
		h.respondWithError(c, http.StatusBadRequest, "2001", "缺少必要的请求头", map[string]interface{}{
			"required_headers": []string{"X-User-ID", "X-Tenant-ID"},
		})
		return
	}
	
	h.logger.WithFields(logrus.Fields{
		"request_id": requestID,
		"user_id":    userID,
		"tenant_id":  tenantID,
		"message":    request.Message,
		"model":      request.Model,
	}).Info("收到RAG聊天请求")
	
	// 模拟RAG处理
	startTime := time.Now()
	
	response := &models.ChatResponse{
		ID:              uuid.New().String(),
		Content:         "这是一个RAG增强的回答示例。基于检索到的知识，我可以为您提供更准确和丰富的答案。",
		Model:           request.Model,
		WorkflowType:    "optimized_rag",
		ExecutionTimeMs: int(time.Since(startTime).Milliseconds()),
		Usage: models.TokenUsage{
			PromptTokens:     len(request.Message) / 4,
			CompletionTokens: 200,
			TotalTokens:      len(request.Message)/4 + 200,
		},
		Metadata: map[string]interface{}{
			"workflow_steps": []string{"prompt_optimizer", "memory_retrieval", "core_responder", "web_search", "final_synthesizer"},
		},
	}
	
	h.logger.WithFields(logrus.Fields{
		"request_id":     requestID,
		"user_id":        userID,
		"tenant_id":      tenantID,
		"execution_time": response.ExecutionTimeMs,
	}).Info("RAG聊天处理完成")
	
	h.respondWithSuccess(c, response, "RAG聊天处理完成", requestID)
}

// GetExecution 获取工作流执行状态
func (h *ChatHandler) GetExecution(c *gin.Context) {
	executionID := c.Param("execution_id")
	requestID := c.GetString("request_id")
	
	if executionID == "" {
		h.respondWithError(c, http.StatusBadRequest, "1001", "缺少执行ID", nil)
		return
	}
	
	// 模拟执行状态查询
	execution := &models.WorkflowExecution{
		ID:              uuid.MustParse(executionID),
		WorkflowType:    "simple_chat",
		Status:          "completed",
		Progress:        100,
		ExecutionTimeMs: 1500,
		Steps: []models.ExecutionStep{
			{
				Node:       "MemoryRetrieval",
				Status:     "completed",
				DurationMs: 200,
			},
			{
				Node:       "ChatModel",
				Status:     "completed",
				DurationMs: 1200,
			},
			{
				Node:       "MemoryStorage",
				Status:     "completed",
				DurationMs: 100,
			},
		},
	}
	
	h.respondWithSuccess(c, execution, "执行状态查询成功", requestID)
}

// getProviderFromModel 根据模型名称获取供应商
func (h *ChatHandler) getProviderFromModel(model string) string {
	switch {
	case model == "gpt-4" || model == "gpt-3.5-turbo":
		return "openai"
	case model == "claude-3-opus" || model == "claude-3-sonnet":
		return "anthropic"
	case model == "deepseek-chat" || model == "deepseek-coder":
		return "deepseek"
	default:
		return "openai" // 默认使用OpenAI
	}
}

// generateMockResponse 生成模拟响应
func (h *ChatHandler) generateMockResponse(message, model string) string {
	return "感谢您的消息：\"" + message + "\"。我是由 " + model + " 模型驱动的AI助手，通过Lyss EINO服务为您提供服务。这是一个模拟响应，用于演示凭证管理和工作流编排功能。"
}

// respondWithSuccess 返回成功响应
func (h *ChatHandler) respondWithSuccess(c *gin.Context, data interface{}, message, requestID string) {
	response := models.ApiResponse[interface{}]{
		Success:   true,
		Data:      data,
		Message:   message,
		RequestID: requestID,
		Timestamp: time.Now().Format(time.RFC3339),
	}
	
	c.JSON(http.StatusOK, response)
}

// respondWithError 返回错误响应
func (h *ChatHandler) respondWithError(c *gin.Context, statusCode int, code, message string, details map[string]interface{}) {
	requestID := c.GetString("request_id")
	
	response := models.ApiResponse[interface{}]{
		Success:   false,
		Data:      nil,
		Message:   message,
		RequestID: requestID,
		Timestamp: time.Now().Format(time.RFC3339),
	}
	
	if details != nil {
		response.Data = models.ErrorResponse{
			Code:    code,
			Message: message,
			Details: details,
		}
	}
	
	c.JSON(statusCode, response)
}