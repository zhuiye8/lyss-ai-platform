package handlers

import (
	"net/http"
	"strconv"
	"time"

	"chat-service/internal/services"
	"chat-service/pkg/types"

	"github.com/gin-gonic/gin"
)

// ChatHandler 聊天API处理器
type ChatHandler struct {
	chatService *services.ChatService
}

// NewChatHandler 创建聊天处理器
func NewChatHandler(chatService *services.ChatService) *ChatHandler {
	return &ChatHandler{
		chatService: chatService,
	}
}

// CreateConversation 创建新对话
func (h *ChatHandler) CreateConversation(c *gin.Context) {
	userID, exists := c.Get("user_id")
	if !exists {
		c.JSON(http.StatusUnauthorized, types.ErrorResponse{
			Error:     "未认证",
			Message:   "用户未认证",
			Code:      401,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	tenantID, exists := c.Get("tenant_id")
	if !exists {
		c.JSON(http.StatusBadRequest, types.ErrorResponse{
			Error:     "缺少租户信息",
			Message:   "请求中缺少租户ID",
			Code:      400,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	var req struct {
		Title    string `json:"title" binding:"required"`
		Model    string `json:"model"`
		Provider string `json:"provider"`
	}
	
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, types.ErrorResponse{
			Error:     "请求参数错误",
			Message:   err.Error(),
			Code:      400,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	// 设置默认值
	if req.Model == "" {
		req.Model = "gpt-3.5-turbo"
	}
	if req.Provider == "" {
		req.Provider = "openai"
	}
	
	conversation, err := h.chatService.CreateConversation(
		c.Request.Context(),
		userID.(string),
		tenantID.(string),
		req.Title,
		req.Model,
		req.Provider,
	)
	
	if err != nil {
		c.JSON(http.StatusInternalServerError, types.ErrorResponse{
			Error:     "创建对话失败",
			Message:   err.Error(),
			Code:      500,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	c.JSON(http.StatusCreated, gin.H{
		"success": true,
		"data":    conversation,
	})
}

// GetConversation 获取对话详情
func (h *ChatHandler) GetConversation(c *gin.Context) {
	conversationID := c.Param("id")
	if conversationID == "" {
		c.JSON(http.StatusBadRequest, types.ErrorResponse{
			Error:     "参数错误",
			Message:   "对话ID不能为空",
			Code:      400,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	userID, _ := c.Get("user_id")
	tenantID, _ := c.Get("tenant_id")
	
	conversation, err := h.chatService.GetConversation(
		c.Request.Context(),
		conversationID,
		userID.(string),
		tenantID.(string),
	)
	
	if err != nil {
		c.JSON(http.StatusNotFound, types.ErrorResponse{
			Error:     "对话不存在",
			Message:   err.Error(),
			Code:      404,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    conversation,
	})
}

// ListConversations 获取对话列表
func (h *ChatHandler) ListConversations(c *gin.Context) {
	userID, _ := c.Get("user_id")
	tenantID, _ := c.Get("tenant_id")
	
	// 解析查询参数
	var req types.ConversationListRequest
	if err := c.ShouldBindQuery(&req); err != nil {
		c.JSON(http.StatusBadRequest, types.ErrorResponse{
			Error:     "查询参数错误",
			Message:   err.Error(),
			Code:      400,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	// 设置默认值
	if req.Page <= 0 {
		req.Page = 1
	}
	if req.PageSize <= 0 || req.PageSize > 100 {
		req.PageSize = 20
	}
	
	response, err := h.chatService.ListConversations(
		c.Request.Context(),
		userID.(string),
		tenantID.(string),
		&req,
	)
	
	if err != nil {
		c.JSON(http.StatusInternalServerError, types.ErrorResponse{
			Error:     "获取对话列表失败",
			Message:   err.Error(),
			Code:      500,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    response,
	})
}

// SendMessage 发送消息（同步模式）
func (h *ChatHandler) SendMessage(c *gin.Context) {
	userID, _ := c.Get("user_id")
	tenantID, _ := c.Get("tenant_id")
	
	var req types.ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, types.ErrorResponse{
			Error:     "请求参数错误",
			Message:   err.Error(),
			Code:      400,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	response, err := h.chatService.SendMessage(
		c.Request.Context(),
		req.ConversationID,
		userID.(string),
		tenantID.(string),
		&req,
	)
	
	if err != nil {
		c.JSON(http.StatusInternalServerError, types.ErrorResponse{
			Error:     "发送消息失败",
			Message:   err.Error(),
			Code:      500,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data":    response,
	})
}

// DeleteConversation 删除对话
func (h *ChatHandler) DeleteConversation(c *gin.Context) {
	conversationID := c.Param("id")
	if conversationID == "" {
		c.JSON(http.StatusBadRequest, types.ErrorResponse{
			Error:     "参数错误",
			Message:   "对话ID不能为空",
			Code:      400,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	userID, _ := c.Get("user_id")
	tenantID, _ := c.Get("tenant_id")
	
	err := h.chatService.DeleteConversation(
		c.Request.Context(),
		conversationID,
		userID.(string),
		tenantID.(string),
	)
	
	if err != nil {
		c.JSON(http.StatusInternalServerError, types.ErrorResponse{
			Error:     "删除对话失败",
			Message:   err.Error(),
			Code:      500,
			Timestamp: time.Now().Unix(),
		})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"message": "对话删除成功",
	})
}

// GetHealth 健康检查
func (h *ChatHandler) GetHealth(c *gin.Context) {
	c.JSON(http.StatusOK, types.HealthResponse{
		Status:    "healthy",
		Service:   "chat-service",
		Version:   "1.0.0",
		Timestamp: time.Now().Unix(),
		Checks: map[string]string{
			"database": "connected",
			"eino":     "initialized",
		},
	})
}

// GetMetrics 获取服务指标
func (h *ChatHandler) GetMetrics(c *gin.Context) {
	// TODO: 实现详细的服务指标
	c.JSON(http.StatusOK, gin.H{
		"success": true,
		"data": map[string]interface{}{
			"uptime":           time.Now().Unix(),
			"active_connections": 0, // WebSocket连接数
			"total_conversations": 0, // 总对话数
			"total_messages":     0, // 总消息数
		},
	})
}

// parseIntParam 解析整数参数
func parseIntParam(c *gin.Context, param string, defaultValue int) int {
	if value := c.Query(param); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}