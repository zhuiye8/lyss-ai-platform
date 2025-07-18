package workflows

import (
	"context"
)

// WorkflowEngine 工作流引擎接口
type WorkflowEngine interface {
	// Execute 执行工作流
	Execute(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error)
	
	// ExecuteStream 流式执行工作流
	ExecuteStream(ctx context.Context, req *WorkflowRequest) (<-chan *WorkflowStreamResponse, error)
	
	// GetInfo 获取工作流信息
	GetInfo() *WorkflowInfo
}

// WorkflowRequest 工作流请求
type WorkflowRequest struct {
	RequestID     string                 `json:"request_id"`
	ExecutionID   string                 `json:"execution_id"`
	TenantID      string                 `json:"tenant_id"`
	UserID        string                 `json:"user_id"`
	WorkflowType  string                 `json:"workflow_type"`
	Message       string                 `json:"message"`
	Model         string                 `json:"model"`
	Temperature   float64                `json:"temperature"`
	MaxTokens     int                    `json:"max_tokens"`
	ModelConfig   map[string]interface{} `json:"model_config"`
	Configuration map[string]interface{} `json:"configuration"`
	Stream        bool                   `json:"stream"`
}

// WorkflowResponse 工作流响应
type WorkflowResponse struct {
	ID              string                 `json:"id"`
	Success         bool                   `json:"success"`
	Content         string                 `json:"content"`
	Model           string                 `json:"model"`
	WorkflowType    string                 `json:"workflow_type"`
	Status          string                 `json:"status"`
	ExecutionTimeMs int64                  `json:"execution_time_ms"`
	Usage           *TokenUsage            `json:"usage"`
	Metadata        map[string]interface{} `json:"metadata"`
	ErrorMessage    string                 `json:"error_message,omitempty"`
}

// TokenUsage Token使用情况
type TokenUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// WorkflowInfo 工作流信息
type WorkflowInfo struct {
	Name              string               `json:"name"`
	DisplayName       string               `json:"display_name"`
	Description       string               `json:"description"`
	Version           string               `json:"version"`
	Type              string               `json:"type"`
	Parameters        []WorkflowParameter  `json:"parameters"`
	SupportedFeatures []string             `json:"supported_features"`
	Nodes             []WorkflowNodeInfo   `json:"nodes"`
	RequiredInputs    []string             `json:"required_inputs"`
	OutputSchema      map[string]interface{} `json:"output_schema"`
}

// WorkflowParameter 工作流参数
type WorkflowParameter struct {
	Name        string      `json:"name"`
	Type        string      `json:"type"`
	Required    bool        `json:"required"`
	Description string      `json:"description"`
	Default     interface{} `json:"default,omitempty"`
}

// WorkflowNodeInfo 工作流节点信息
type WorkflowNodeInfo struct {
	Name        string `json:"name"`
	Type        string `json:"type"`
	Description string `json:"description"`
	Required    bool   `json:"required"`
}

// WorkflowExecutionContext 工作流执行上下文
type WorkflowExecutionContext struct {
	RequestID     string                 `json:"request_id"`
	ExecutionID   string                 `json:"execution_id"`
	TenantID      string                 `json:"tenant_id"`
	UserID        string                 `json:"user_id"`
	WorkflowType  string                 `json:"workflow_type"`
	State         map[string]interface{} `json:"state"`
	Configuration map[string]interface{} `json:"configuration"`
	Steps         []WorkflowStep         `json:"steps"`
	StartTime     int64                  `json:"start_time"`
	EndTime       int64                  `json:"end_time"`
	Status        string                 `json:"status"`
}

// WorkflowStep 工作流步骤
type WorkflowStep struct {
	Name        string                 `json:"name"`
	Type        string                 `json:"type"`
	Status      string                 `json:"status"`
	StartTime   int64                  `json:"start_time"`
	EndTime     int64                  `json:"end_time"`
	DurationMs  int                    `json:"duration_ms"`
	InputData   map[string]interface{} `json:"input_data"`
	OutputData  map[string]interface{} `json:"output_data"`
	Error       string                 `json:"error,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// WorkflowRegistry 工作流注册表接口
type WorkflowRegistry interface {
	// RegisterWorkflow 注册工作流
	RegisterWorkflow(name string, workflow WorkflowEngine) error
	
	// GetWorkflow 获取工作流
	GetWorkflow(name string) (WorkflowEngine, error)
	
	// ListWorkflows 列出所有工作流
	ListWorkflows() []WorkflowInfo
	
	// IsWorkflowRegistered 检查工作流是否已注册
	IsWorkflowRegistered(name string) bool
	
	// GetWorkflowCount 获取工作流数量
	GetWorkflowCount() int
	
	// GetWorkflowNames 获取所有工作流名称
	GetWorkflowNames() []string
	
	// GetWorkflowInfo 获取工作流信息
	GetWorkflowInfo(name string) (*WorkflowInfo, error)
	
	// UnregisterWorkflow 取消注册工作流
	UnregisterWorkflow(name string) error
}

// WorkflowExecutor 工作流执行器接口
type WorkflowExecutor interface {
	// Execute 执行工作流
	Execute(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error)
	
	// ExecuteStream 流式执行工作流
	ExecuteStream(ctx context.Context, req *WorkflowRequest) (<-chan *WorkflowStreamResponse, error)
	
	// GetExecutionStatus 获取执行状态
	GetExecutionStatus(executionID string) (*WorkflowExecutionStatus, error)
	
	// CancelExecution 取消执行
	CancelExecution(executionID string) error
}

// WorkflowStreamResponse 工作流流式响应
type WorkflowStreamResponse struct {
	Type        string         `json:"type"`        // "start", "chunk", "end", "error"
	ExecutionID string         `json:"execution_id"`
	Content     string         `json:"content"` 
	Data        map[string]any `json:"data"`
	Error       string         `json:"error,omitempty"`
}

// WorkflowExecutionStatus 工作流执行状态
type WorkflowExecutionStatus struct {
	ExecutionID     string         `json:"execution_id"`
	Status          string         `json:"status"`
	Progress        int            `json:"progress"`
	CurrentStep     string         `json:"current_step"`
	Steps           []WorkflowStep `json:"steps"`
	StartTime       int64          `json:"start_time"`
	EndTime         int64          `json:"end_time"`
	ExecutionTimeMs int64          `json:"execution_time_ms"`
	Error           string         `json:"error,omitempty"`
}

// WorkflowMetrics 工作流指标
type WorkflowMetrics struct {
	TotalExecutions     int64 `json:"total_executions"`
	SuccessfulExecutions int64 `json:"successful_executions"`
	FailedExecutions    int64 `json:"failed_executions"`
	AverageExecutionTime int64 `json:"average_execution_time"`
	TotalTokensUsed     int64 `json:"total_tokens_used"`
}

// WorkflowEvent 工作流事件
type WorkflowEvent struct {
	Type        string                 `json:"type"`
	ExecutionID string                 `json:"execution_id"`
	TenantID    string                 `json:"tenant_id"`
	UserID      string                 `json:"user_id"`
	Timestamp   int64                  `json:"timestamp"`
	Data        map[string]interface{} `json:"data"`
}