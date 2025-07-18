package models

import (
	"time"

	"github.com/google/uuid"
)

// SupplierCredential 供应商凭证模型
type SupplierCredential struct {
	ID           uuid.UUID              `json:"id"`
	TenantID     uuid.UUID              `json:"tenant_id"`
	Provider     string                 `json:"provider_name"`
	DisplayName  string                 `json:"display_name"`
	APIKey       string                 `json:"api_key"`
	BaseURL      string                 `json:"base_url"`
	ModelConfigs map[string]interface{} `json:"model_configs"`
	IsActive     bool                   `json:"is_active"`
	CreatedAt    time.Time              `json:"created_at"`
	UpdatedAt    time.Time              `json:"updated_at"`
}

// CredentialSelector 凭证选择器
type CredentialSelector struct {
	Strategy string   `json:"strategy"`
	Filters  struct {
		OnlyActive bool     `json:"only_active"`
		Providers  []string `json:"providers"`
	} `json:"filters"`
}

// CredentialTestRequest 凭证测试请求
type CredentialTestRequest struct {
	TenantID  string `json:"tenant_id"`
	TestType  string `json:"test_type"`
	ModelName string `json:"model_name"`
}

// CredentialTestResponse 凭证测试响应
type CredentialTestResponse struct {
	Success        bool                   `json:"success"`
	TestType       string                 `json:"test_type"`
	ResponseTimeMs int                    `json:"response_time_ms"`
	ErrorMessage   string                 `json:"error_message"`
	ResultData     map[string]interface{} `json:"result_data"`
}

// ToolConfig 工具配置
type ToolConfig struct {
	TenantID     string                 `json:"tenant_id"`
	WorkflowName string                 `json:"workflow_name"`
	ToolName     string                 `json:"tool_name"`
	IsEnabled    bool                   `json:"is_enabled"`
	ConfigParams map[string]interface{} `json:"config_params"`
}

// ChatRequest 聊天请求
type ChatRequest struct {
	Message     string                 `json:"message"`
	Model       string                 `json:"model"`
	Temperature float64                `json:"temperature"`
	MaxTokens   int                    `json:"max_tokens"`
	Stream      bool                   `json:"stream"`
	ModelConfig map[string]interface{} `json:"model_config"`
}

// ChatResponse 聊天响应
type ChatResponse struct {
	ID              string                 `json:"id"`
	Content         string                 `json:"content"`
	Model           string                 `json:"model"`
	WorkflowType    string                 `json:"workflow_type"`
	ExecutionTimeMs int                    `json:"execution_time_ms"`
	Usage           TokenUsage             `json:"usage"`
	Metadata        map[string]interface{} `json:"metadata"`
}

// TokenUsage 令牌使用情况
type TokenUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// WorkflowExecution 工作流执行记录
type WorkflowExecution struct {
	ID              uuid.UUID              `json:"id"`
	TenantID        uuid.UUID              `json:"tenant_id"`
	UserID          uuid.UUID              `json:"user_id"`
	WorkflowType    string                 `json:"workflow_type"`
	Status          string                 `json:"status"`
	Progress        int                    `json:"progress"`
	InputData       map[string]interface{} `json:"input_data"`
	OutputData      map[string]interface{} `json:"output_data"`
	Steps           []ExecutionStep        `json:"steps"`
	ExecutionTimeMs int                    `json:"execution_time_ms"`
	ErrorMessage    string                 `json:"error_message"`
	CreatedAt       time.Time              `json:"created_at"`
	UpdatedAt       time.Time              `json:"updated_at"`
}

// ExecutionStep 执行步骤
type ExecutionStep struct {
	Node       string                 `json:"node"`
	Status     string                 `json:"status"`
	DurationMs int                    `json:"duration_ms"`
	InputData  map[string]interface{} `json:"input_data"`
	OutputData map[string]interface{} `json:"output_data"`
	Error      string                 `json:"error"`
}

// ApiResponse API响应通用结构
type ApiResponse[T any] struct {
	Success   bool   `json:"success"`
	Data      T      `json:"data"`
	Message   string `json:"message"`
	RequestID string `json:"request_id"`
	Timestamp string `json:"timestamp"`
}

// ErrorResponse 错误响应
type ErrorResponse struct {
	Code    string                 `json:"code"`
	Message string                 `json:"message"`
	Details map[string]interface{} `json:"details"`
}

// HealthResponse 健康检查响应
type HealthResponse struct {
	Status       string            `json:"status"`
	Timestamp    string            `json:"timestamp"`
	Version      string            `json:"version"`
	Dependencies map[string]string `json:"dependencies"`
	Metrics      map[string]int    `json:"metrics"`
}