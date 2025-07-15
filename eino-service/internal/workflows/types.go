package workflows

import (
	"context"
	"lyss-ai-platform/eino-service/internal/models"
)

// WorkflowEngine 工作流引擎接口
type WorkflowEngine interface {
	// Execute 执行工作流
	Execute(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error)
	
	// GetWorkflowInfo 获取工作流信息
	GetWorkflowInfo() *WorkflowInfo
	
	// ValidateInput 验证输入
	ValidateInput(req *WorkflowRequest) error
}

// WorkflowRequest 工作流请求
type WorkflowRequest struct {
	RequestID     string                 `json:"request_id"`
	ExecutionID   string                 `json:"execution_id"`
	TenantID      string                 `json:"tenant_id"`
	UserID        string                 `json:"user_id"`
	WorkflowType  string                 `json:"workflow_type"`
	Message       string                 `json:"message"`
	ModelConfig   map[string]interface{} `json:"model_config"`
	Configuration map[string]interface{} `json:"configuration"`
	Stream        bool                   `json:"stream"`
}

// WorkflowResponse 工作流响应
type WorkflowResponse struct {
	Success         bool                   `json:"success"`
	Content         string                 `json:"content"`
	Model           string                 `json:"model"`
	WorkflowType    string                 `json:"workflow_type"`
	ExecutionTimeMs int                    `json:"execution_time_ms"`
	Usage           models.TokenUsage      `json:"usage"`
	Metadata        map[string]interface{} `json:"metadata"`
	ErrorMessage    string                 `json:"error_message,omitempty"`
}

// WorkflowInfo 工作流信息
type WorkflowInfo struct {
	Name           string             `json:"name"`
	Description    string             `json:"description"`
	Version        string             `json:"version"`
	Type           string             `json:"type"`
	Nodes          []WorkflowNodeInfo `json:"nodes"`
	RequiredInputs []string           `json:"required_inputs"`
	OutputSchema   map[string]interface{} `json:"output_schema"`
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
	Type    string      `json:"type"`    // "data", "error", "done"
	Content string      `json:"content"` 
	Data    interface{} `json:"data"`
	Error   string      `json:"error,omitempty"`
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
	ExecutionTimeMs int            `json:"execution_time_ms"`
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