package types

import "time"

// ChatRequest 聊天请求结构
type ChatRequest struct {
	ConversationID string            `json:"conversation_id,omitempty"`
	Message        string            `json:"message" binding:"required"`
	Model          string            `json:"model,omitempty"`
	Provider       string            `json:"provider,omitempty"`
	Stream         bool              `json:"stream,omitempty"`
	Options        map[string]interface{} `json:"options,omitempty"`
}

// ChatResponse 聊天响应结构
type ChatResponse struct {
	ConversationID string                 `json:"conversation_id"`
	MessageID      string                 `json:"message_id"`
	Content        string                 `json:"content"`
	Model          string                 `json:"model"`
	Provider       string                 `json:"provider"`
	TokensUsed     int                    `json:"tokens_used"`
	Cost           float64                `json:"cost"`
	Metadata       map[string]interface{} `json:"metadata"`
	CreatedAt      time.Time              `json:"created_at"`
}

// StreamResponse 流式响应结构
type StreamResponse struct {
	ConversationID string                 `json:"conversation_id"`
	MessageID      string                 `json:"message_id"`
	Delta          string                 `json:"delta"`
	Done           bool                   `json:"done"`
	Model          string                 `json:"model"`
	Provider       string                 `json:"provider"`
	Metadata       map[string]interface{} `json:"metadata"`
}

// ChatStreamChunk 聊天流式响应块
type ChatStreamChunk struct {
	ConversationID string                 `json:"conversation_id"`
	Content        string                 `json:"content"`
	Done           bool                   `json:"done"`
	Metadata       map[string]interface{} `json:"metadata"`
}

// ConversationListRequest 对话列表请求
type ConversationListRequest struct {
	Page     int    `form:"page,default=1"`
	PageSize int    `form:"page_size,default=20"`
	Status   string `form:"status"`
	Model    string `form:"model"`
}

// ConversationListResponse 对话列表响应
type ConversationListResponse struct {
	Conversations []ConversationSummary `json:"conversations"`
	Total         int64                 `json:"total"`
	Page          int                   `json:"page"`
	PageSize      int                   `json:"page_size"`
	HasMore       bool                  `json:"has_more"`
}

// ConversationSummary 对话摘要
type ConversationSummary struct {
	ID           string                 `json:"id"`
	Title        string                 `json:"title"`
	Model        string                 `json:"model"`
	Provider     string                 `json:"provider"`
	MessageCount int                    `json:"message_count"`
	LastMessage  string                 `json:"last_message"`
	UpdatedAt    time.Time              `json:"updated_at"`
	Metadata     map[string]interface{} `json:"metadata"`
}

// MessageListResponse 消息列表响应
type MessageListResponse struct {
	Messages []MessageSummary `json:"messages"`
	Total    int64            `json:"total"`
	HasMore  bool             `json:"has_more"`
}

// MessageSummary 消息摘要
type MessageSummary struct {
	ID         string                 `json:"id"`
	Role       string                 `json:"role"`
	Content    string                 `json:"content"`
	Model      string                 `json:"model"`
	Provider   string                 `json:"provider"`
	TokensUsed int                    `json:"tokens_used"`
	Cost       float64                `json:"cost"`
	Status     string                 `json:"status"`
	CreatedAt  time.Time              `json:"created_at"`
	Metadata   map[string]interface{} `json:"metadata"`
}

// ErrorResponse 错误响应结构
type ErrorResponse struct {
	Error       string `json:"error"`
	Message     string `json:"message"`
	Code        int    `json:"code"`
	RequestID   string `json:"request_id"`
	Timestamp   int64  `json:"timestamp"`
}

// HealthResponse 健康检查响应
type HealthResponse struct {
	Status    string            `json:"status"`
	Service   string            `json:"service"`
	Version   string            `json:"version"`
	Timestamp int64             `json:"timestamp"`
	Checks    map[string]string `json:"checks"`
}

// WSMessage WebSocket消息结构
type WSMessage struct {
	Type string      `json:"type"`
	Data interface{} `json:"data"`
}

// WSMessageType WebSocket消息类型
const (
	WSMsgTypeChat     = "chat"
	WSMsgTypeStream   = "stream"
	WSMsgTypeError    = "error"
	WSMsgTypeClose    = "close"
	WSMsgTypePing     = "ping"
	WSMsgTypePong     = "pong"
)