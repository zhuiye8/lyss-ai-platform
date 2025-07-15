package nodes

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/models"
)

// NodeResult 节点执行结果
type NodeResult struct {
	Success      bool                   `json:"success"`
	Data         map[string]interface{} `json:"data"`
	Error        string                 `json:"error"`
	DurationMs   int                    `json:"duration_ms"`
	TokenUsage   *models.TokenUsage     `json:"token_usage,omitempty"`
	NodeMetadata map[string]interface{} `json:"node_metadata,omitempty"`
}

// NodeContext 节点执行上下文
type NodeContext struct {
	RequestID       string                 `json:"request_id"`
	ExecutionID     string                 `json:"execution_id"`
	TenantID        string                 `json:"tenant_id"`
	UserID          string                 `json:"user_id"`
	WorkflowType    string                 `json:"workflow_type"`
	State           map[string]interface{} `json:"state"`
	Logger          *logrus.Logger         `json:"-"`
	StartTime       time.Time              `json:"start_time"`
	Configuration   map[string]interface{} `json:"configuration"`
}

// WorkflowNode 工作流节点接口
type WorkflowNode interface {
	// GetName 获取节点名称
	GetName() string
	
	// GetType 获取节点类型
	GetType() string
	
	// Execute 执行节点逻辑
	Execute(ctx context.Context, nodeCtx *NodeContext) (*NodeResult, error)
	
	// ValidateInput 验证输入数据
	ValidateInput(input map[string]interface{}) error
	
	// GetRequiredInputs 获取必需的输入字段
	GetRequiredInputs() []string
	
	// GetOutputSchema 获取输出模式
	GetOutputSchema() map[string]interface{}
}

// BaseNode 基础节点实现
type BaseNode struct {
	Name        string
	Type        string
	Description string
	Logger      *logrus.Logger
}

// NewBaseNode 创建基础节点
func NewBaseNode(name, nodeType, description string, logger *logrus.Logger) *BaseNode {
	return &BaseNode{
		Name:        name,
		Type:        nodeType,
		Description: description,
		Logger:      logger,
	}
}

// GetName 获取节点名称
func (b *BaseNode) GetName() string {
	return b.Name
}

// GetType 获取节点类型
func (b *BaseNode) GetType() string {
	return b.Type
}

// ValidateInput 验证输入数据（基础实现）
func (b *BaseNode) ValidateInput(input map[string]interface{}) error {
	// 验证必需字段
	requiredInputs := b.GetRequiredInputs()
	for _, field := range requiredInputs {
		if _, exists := input[field]; !exists {
			return fmt.Errorf("缺少必需的输入字段: %s", field)
		}
	}
	return nil
}

// GetRequiredInputs 获取必需的输入字段（基础实现）
func (b *BaseNode) GetRequiredInputs() []string {
	return []string{} // 基础节点无必需输入
}

// GetOutputSchema 获取输出模式（基础实现）
func (b *BaseNode) GetOutputSchema() map[string]interface{} {
	return map[string]interface{}{
		"success": "boolean",
		"data":    "object",
		"error":   "string",
	}
}

// LogNodeStart 记录节点开始执行
func (b *BaseNode) LogNodeStart(ctx context.Context, nodeCtx *NodeContext) {
	b.Logger.WithFields(logrus.Fields{
		"request_id":    nodeCtx.RequestID,
		"execution_id":  nodeCtx.ExecutionID,
		"tenant_id":     nodeCtx.TenantID,
		"user_id":       nodeCtx.UserID,
		"workflow_type": nodeCtx.WorkflowType,
		"node_name":     b.Name,
		"node_type":     b.Type,
		"operation":     "node_start",
	}).Info("节点开始执行")
}

// LogNodeComplete 记录节点执行完成
func (b *BaseNode) LogNodeComplete(ctx context.Context, nodeCtx *NodeContext, result *NodeResult) {
	logFields := logrus.Fields{
		"request_id":    nodeCtx.RequestID,
		"execution_id":  nodeCtx.ExecutionID,
		"tenant_id":     nodeCtx.TenantID,
		"user_id":       nodeCtx.UserID,
		"workflow_type": nodeCtx.WorkflowType,
		"node_name":     b.Name,
		"node_type":     b.Type,
		"operation":     "node_complete",
		"success":       result.Success,
		"duration_ms":   result.DurationMs,
	}

	if result.TokenUsage != nil {
		logFields["prompt_tokens"] = result.TokenUsage.PromptTokens
		logFields["completion_tokens"] = result.TokenUsage.CompletionTokens
		logFields["total_tokens"] = result.TokenUsage.TotalTokens
	}

	if result.Success {
		b.Logger.WithFields(logFields).Info("节点执行成功")
	} else {
		logFields["error"] = result.Error
		b.Logger.WithFields(logFields).Error("节点执行失败")
	}
}

// LogNodeError 记录节点执行错误
func (b *BaseNode) LogNodeError(ctx context.Context, nodeCtx *NodeContext, err error) {
	b.Logger.WithFields(logrus.Fields{
		"request_id":    nodeCtx.RequestID,
		"execution_id":  nodeCtx.ExecutionID,
		"tenant_id":     nodeCtx.TenantID,
		"user_id":       nodeCtx.UserID,
		"workflow_type": nodeCtx.WorkflowType,
		"node_name":     b.Name,
		"node_type":     b.Type,
		"operation":     "node_error",
		"error":         err.Error(),
	}).Error("节点执行异常")
}

// CreateExecutionStep 创建执行步骤记录
func (b *BaseNode) CreateExecutionStep(nodeCtx *NodeContext, result *NodeResult) *models.ExecutionStep {
	status := "completed"
	if !result.Success {
		status = "failed"
	}

	return &models.ExecutionStep{
		Node:       b.Name,
		Status:     status,
		DurationMs: result.DurationMs,
		InputData:  nodeCtx.State,
		OutputData: result.Data,
		Error:      result.Error,
	}
}

// UpdateNodeContext 更新节点上下文
func (b *BaseNode) UpdateNodeContext(nodeCtx *NodeContext, result *NodeResult) {
	// 将节点输出数据合并到状态中
	if result.Success && result.Data != nil {
		for key, value := range result.Data {
			nodeCtx.State[key] = value
		}
	}
	
	// 更新节点元数据
	if result.NodeMetadata != nil {
		if nodeCtx.State["node_metadata"] == nil {
			nodeCtx.State["node_metadata"] = make(map[string]interface{})
		}
		metadata := nodeCtx.State["node_metadata"].(map[string]interface{})
		metadata[b.Name] = result.NodeMetadata
	}
}

// GenerateNodeExecutionID 生成节点执行ID
func (b *BaseNode) GenerateNodeExecutionID() string {
	return fmt.Sprintf("node_%s_%s", b.Name, uuid.New().String()[:8])
}

// SanitizeLogData 清理日志数据，移除敏感信息
func (b *BaseNode) SanitizeLogData(data map[string]interface{}) map[string]interface{} {
	sanitized := make(map[string]interface{})
	
	for key, value := range data {
		lowerKey := strings.ToLower(key)
		if strings.Contains(lowerKey, "key") || 
		   strings.Contains(lowerKey, "token") ||
		   strings.Contains(lowerKey, "secret") ||
		   strings.Contains(lowerKey, "password") {
			sanitized[key] = "***masked***"
		} else {
			sanitized[key] = value
		}
	}
	
	return sanitized
}