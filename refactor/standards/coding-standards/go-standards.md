# Go编码规范

## 📋 文档概述

Go语言项目的专用编码规范，确保代码质量和一致性。

---

## 🐹 Go编码规范

### **包和文件注释**
```go
// Package handlers 提供HTTP请求处理器
//
// 该包包含所有HTTP路由的处理逻辑，负责处理请求验证、
// 业务逻辑调用和响应格式化。
//
// 作者: Lyss AI Team
// 创建时间: 2025-01-20
package handlers

import (
    "context"
    "net/http"
    "time"
    
    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
    
    "lyss-chat-service/internal/models"
    "lyss-chat-service/internal/services"
)
```

### **结构体定义规范**
```go
// ChatRequest 对话请求结构
type ChatRequest struct {
    ConversationID string                 `json:"conversation_id" binding:"required"`
    UserID         string                 `json:"user_id" binding:"required"`
    Message        string                 `json:"message" binding:"required,min=1,max=4000"`
    ModelName      string                 `json:"model_name" binding:"required"`
    UserToken      string                 `json:"user_token" binding:"required"`
    Temperature    float32                `json:"temperature" binding:"min=0,max=2"`
    MaxTokens      int                    `json:"max_tokens" binding:"min=1,max=8000"`
    Stream         bool                   `json:"stream"`
    Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// ChatResponse 对话响应结构
type ChatResponse struct {
    ConversationID string    `json:"conversation_id"`
    MessageID      string    `json:"message_id"`
    Content        string    `json:"content"`
    Model          string    `json:"model"`
    Usage          Usage     `json:"usage"`
    CreatedAt      time.Time `json:"created_at"`
}

// Usage 使用量统计
type Usage struct {
    PromptTokens     int `json:"prompt_tokens"`
    CompletionTokens int `json:"completion_tokens"`
    TotalTokens      int `json:"total_tokens"`
}
```

### **方法定义规范**
```go
// ChatHandler 对话处理器
type ChatHandler struct {
    chatService    services.ChatService
    providerClient *clients.ProviderClient
    logger         *slog.Logger
}

// NewChatHandler 创建新的对话处理器
func NewChatHandler(
    chatService services.ChatService,
    providerClient *clients.ProviderClient,
    logger *slog.Logger,
) *ChatHandler {
    return &ChatHandler{
        chatService:    chatService,
        providerClient: providerClient,
        logger:         logger,
    }
}

// ProcessMessage 处理对话消息
//
// 该方法负责处理用户的对话请求，包括模型选择、
// 提示词增强、流式响应处理等功能。
//
// 参数:
//   - ctx: 请求上下文
//   - c: Gin上下文对象
//
// 响应:
//   - 成功: 返回流式对话响应
//   - 失败: 返回错误信息
func (h *ChatHandler) ProcessMessage(ctx context.Context, c *gin.Context) {
    // 解析请求参数
    var req ChatRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        h.logger.Warn("请求参数验证失败", 
            "error", err.Error(),
            "user_id", req.UserID)
        c.JSON(http.StatusBadRequest, gin.H{
            "success": false,
            "error": map[string]interface{}{
                "code":    "INVALID_REQUEST",
                "message": "请求参数格式错误",
                "details": err.Error(),
            },
            "timestamp":  time.Now().UTC(),
            "request_id": getRequestID(c),
        })
        return
    }
    
    // 验证用户权限
    if err := h.validateUserPermission(ctx, req.UserID, req.UserToken); err != nil {
        h.logger.Warn("用户权限验证失败",
            "user_id", req.UserID,
            "error", err.Error())
        c.JSON(http.StatusUnauthorized, gin.H{
            "success": false,
            "error": map[string]interface{}{
                "code":    "UNAUTHORIZED",
                "message": "用户权限验证失败",
            },
            "timestamp":  time.Now().UTC(),
            "request_id": getRequestID(c),
        })
        return
    }
    
    // 处理对话请求
    if req.Stream {
        h.handleStreamingChat(ctx, c, &req)
    } else {
        h.handleNormalChat(ctx, c, &req)
    }
}

// handleStreamingChat 处理流式对话
func (h *ChatHandler) handleStreamingChat(ctx context.Context, c *gin.Context, req *ChatRequest) {
    // 设置流式响应头
    c.Header("Content-Type", "text/event-stream")
    c.Header("Cache-Control", "no-cache")
    c.Header("Connection", "keep-alive")
    c.Header("Access-Control-Allow-Origin", "*")
    
    // 创建流式响应通道
    eventChan, err := h.chatService.ProcessMessageStream(ctx, req)
    if err != nil {
        h.logger.Error("创建流式对话失败",
            "conversation_id", req.ConversationID,
            "error", err.Error())
        c.JSON(http.StatusInternalServerError, gin.H{
            "success": false,
            "error": map[string]interface{}{
                "code":    "STREAM_ERROR",
                "message": "流式对话创建失败",
            },
        })
        return
    }
    
    // 发送流式事件
    c.Stream(func(w io.Writer) bool {
        select {
        case event, ok := <-eventChan:
            if !ok {
                // 通道已关闭
                return false
            }
            
            // 发送事件数据
            eventData, _ := json.Marshal(event)
            c.SSEvent("message", string(eventData))
            return true
            
        case <-ctx.Done():
            // 请求被取消
            h.logger.Info("流式对话被取消", "conversation_id", req.ConversationID)
            return false
        }
    })
}
```

### **错误处理规范**
```go
// errors.go - 自定义错误类型
package utils

import "fmt"

// ChatError 对话相关错误
type ChatError struct {
    Code    string
    Message string
    Details map[string]interface{}
}

func (e *ChatError) Error() string {
    return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

// NewChatError 创建对话错误
func NewChatError(code, message string, details map[string]interface{}) *ChatError {
    return &ChatError{
        Code:    code,
        Message: message,
        Details: details,
    }
}

// 预定义错误
var (
    ErrModelNotFound = &ChatError{
        Code:    "MODEL_NOT_FOUND",
        Message: "指定的模型不存在",
    }
    
    ErrQuotaExceeded = &ChatError{
        Code:    "QUOTA_EXCEEDED",
        Message: "已超出配额限制",
    }
    
    ErrProviderUnavailable = &ChatError{
        Code:    "PROVIDER_UNAVAILABLE",
        Message: "AI服务提供商暂时不可用",
    }
)

// 在服务中使用错误处理
func (s *ChatService) ProcessMessage(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
    // 获取模型配置
    modelConfig, err := s.providerClient.GetModelConfig(req.UserToken, req.ModelName)
    if err != nil {
        s.logger.Error("获取模型配置失败",
            "model", req.ModelName,
            "error", err.Error())
        return nil, NewChatError("MODEL_CONFIG_ERROR", "模型配置获取失败", map[string]interface{}{
            "model": req.ModelName,
        })
    }
    
    // 检查配额
    if err := s.checkQuota(req.UserID, req.UserToken); err != nil {
        s.logger.Warn("配额检查失败",
            "user_id", req.UserID,
            "error", err.Error())
        return nil, ErrQuotaExceeded
    }
    
    // 处理对话逻辑...
    response, err := s.callAIProvider(ctx, req, modelConfig)
    if err != nil {
        s.logger.Error("AI服务调用失败",
            "provider", modelConfig.Provider,
            "error", err.Error())
        return nil, ErrProviderUnavailable
    }
    
    return response, nil
}
```

---

## 📋 Go特定检查清单

- [ ] 遵循Go代码规范
- [ ] 错误处理完整
- [ ] 接口设计合理
- [ ] 并发安全
- [ ] 内存泄漏检查