package workflows

import (
	"context"
	"fmt"
	"time"

	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/config"
	"lyss-ai-platform/eino-service/pkg/credential"
)

// WorkflowManager 工作流管理器
type WorkflowManager struct {
	registry         WorkflowRegistry
	executor         WorkflowExecutor
	credentialManager *credential.Manager
	logger           *logrus.Logger
	config           *config.Config
}

// NewWorkflowManager 创建工作流管理器
func NewWorkflowManager(
	credentialManager *credential.Manager,
	logger *logrus.Logger,
	config *config.Config,
) *WorkflowManager {
	// 创建注册表
	registry := NewDefaultWorkflowRegistry(logger)
	
	// 创建执行器
	executor := NewDefaultWorkflowExecutor(
		registry,
		logger,
		config.Workflows.MaxConcurrentExecutions,
		config.Workflows.ExecutionTimeout,
	)

	return &WorkflowManager{
		registry:         registry,
		executor:         executor,
		credentialManager: credentialManager,
		logger:           logger,
		config:           config,
	}
}

// Initialize 初始化工作流管理器
func (wm *WorkflowManager) Initialize() error {
	wm.logger.Info("正在初始化工作流管理器...")

	// 注册内置工作流
	if err := wm.registerBuiltinWorkflows(); err != nil {
		return fmt.Errorf("注册内置工作流失败: %w", err)
	}

	wm.logger.WithFields(logrus.Fields{
		"operation":        "workflow_manager_initialized",
		"workflow_count":   wm.registry.GetWorkflowCount(),
		"workflow_names":   wm.registry.GetWorkflowNames(),
	}).Info("工作流管理器初始化成功")

	return nil
}

// registerBuiltinWorkflows 注册内置工作流
func (wm *WorkflowManager) registerBuiltinWorkflows() error {
	// 注册标准EINO聊天工作流（主要工作流）
	einoChatWorkflow := NewEINOStandardChatWorkflow(wm.credentialManager, wm.logger)
	if err := wm.registry.RegisterWorkflow("eino_standard_chat", einoChatWorkflow); err != nil {
		return fmt.Errorf("注册标准EINO聊天工作流失败: %w", err)
	}

	// 注册简单聊天工作流（兼容性）
	simpleChatWorkflow := NewSimpleChatWorkflow(wm.credentialManager, wm.logger)
	if err := wm.registry.RegisterWorkflow("simple_chat", simpleChatWorkflow); err != nil {
		return fmt.Errorf("注册简单聊天工作流失败: %w", err)
	}

	// 注册标准EINO聊天工作流（旧版本兼容）
	standardEinoChatWorkflow := NewStandardEINOChatWorkflow(wm.credentialManager, wm.logger)
	if err := wm.registry.RegisterWorkflow("standard_eino_chat", standardEinoChatWorkflow); err != nil {
		return fmt.Errorf("注册标准EINO聊天工作流失败: %w", err)
	}

	// TODO: 注册其他EINO工作流
	// - RAG工作流（基于EINO Graph）
	// - Tool调用工作流（基于EINO Tools）
	// - 多步对话工作流

	return nil
}

// ExecuteWorkflow 执行工作流
func (wm *WorkflowManager) ExecuteWorkflow(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error) {
	// 验证请求
	if err := wm.validateRequest(req); err != nil {
		return nil, fmt.Errorf("请求验证失败: %w", err)
	}

	// 记录请求
	wm.logger.WithFields(logrus.Fields{
		"request_id":     req.RequestID,
		"execution_id":   req.ExecutionID,
		"tenant_id":      req.TenantID,
		"user_id":        req.UserID,
		"workflow_type":  req.WorkflowType,
		"message_length": len(req.Message),
		"operation":      "workflow_request",
	}).Info("收到工作流执行请求")

	// 执行工作流
	response, err := wm.executor.Execute(ctx, req)
	if err != nil {
		wm.logger.WithFields(logrus.Fields{
			"request_id":    req.RequestID,
			"execution_id":  req.ExecutionID,
			"tenant_id":     req.TenantID,
			"user_id":       req.UserID,
			"workflow_type": req.WorkflowType,
			"operation":     "workflow_execution_failed",
			"error":         err.Error(),
		}).Error("工作流执行失败")
		return nil, err
	}

	// 记录成功
	wm.logger.WithFields(logrus.Fields{
		"request_id":       req.RequestID,
		"execution_id":     req.ExecutionID,
		"tenant_id":        req.TenantID,
		"user_id":          req.UserID,
		"workflow_type":    req.WorkflowType,
		"operation":        "workflow_execution_success",
		"execution_time_ms": response.ExecutionTimeMs,
		"total_tokens":     response.Usage.TotalTokens,
	}).Info("工作流执行成功")

	return response, nil
}

// ExecuteWorkflowStream 流式执行工作流
func (wm *WorkflowManager) ExecuteWorkflowStream(ctx context.Context, req *WorkflowRequest) (<-chan *WorkflowStreamResponse, error) {
	// 验证请求
	if err := wm.validateRequest(req); err != nil {
		return nil, fmt.Errorf("请求验证失败: %w", err)
	}

	// 记录流式请求
	wm.logger.WithFields(logrus.Fields{
		"request_id":     req.RequestID,
		"execution_id":   req.ExecutionID,
		"tenant_id":      req.TenantID,
		"user_id":        req.UserID,
		"workflow_type":  req.WorkflowType,
		"operation":      "workflow_stream_request",
	}).Info("收到工作流流式执行请求")

	// 执行流式工作流
	return wm.executor.ExecuteStream(ctx, req)
}

// GetWorkflowInfo 获取工作流信息
func (wm *WorkflowManager) GetWorkflowInfo(name string) (*WorkflowInfo, error) {
	return wm.registry.GetWorkflowInfo(name)
}

// ListWorkflows 列出所有工作流
func (wm *WorkflowManager) ListWorkflows() []WorkflowInfo {
	return wm.registry.ListWorkflows()
}

// GetExecutionStatus 获取执行状态
func (wm *WorkflowManager) GetExecutionStatus(executionID string) (*WorkflowExecutionStatus, error) {
	return wm.executor.GetExecutionStatus(executionID)
}

// CancelExecution 取消执行
func (wm *WorkflowManager) CancelExecution(executionID string) error {
	return wm.executor.CancelExecution(executionID)
}

// GetMetrics 获取工作流指标
func (wm *WorkflowManager) GetMetrics() *WorkflowMetrics {
	// TODO: 实现指标收集
	return &WorkflowMetrics{
		TotalExecutions:      0,
		SuccessfulExecutions: 0,
		FailedExecutions:     0,
		AverageExecutionTime: 0,
		TotalTokensUsed:      0,
	}
}

// validateRequest 验证请求
func (wm *WorkflowManager) validateRequest(req *WorkflowRequest) error {
	if req == nil {
		return fmt.Errorf("请求不能为空")
	}

	if req.RequestID == "" {
		return fmt.Errorf("请求ID不能为空")
	}

	if req.TenantID == "" {
		return fmt.Errorf("租户ID不能为空")
	}

	if req.UserID == "" {
		return fmt.Errorf("用户ID不能为空")
	}

	if req.WorkflowType == "" {
		return fmt.Errorf("工作流类型不能为空")
	}

	if req.Message == "" {
		return fmt.Errorf("消息不能为空")
	}

	// 检查工作流是否存在
	if !wm.registry.IsWorkflowRegistered(req.WorkflowType) {
		return fmt.Errorf("工作流类型 %s 不存在", req.WorkflowType)
	}

	return nil
}

// RegisterWorkflow 注册工作流
func (wm *WorkflowManager) RegisterWorkflow(name string, workflow WorkflowEngine) error {
	return wm.registry.RegisterWorkflow(name, workflow)
}

// UnregisterWorkflow 取消注册工作流
func (wm *WorkflowManager) UnregisterWorkflow(name string) error {
	// 检查是否为内置工作流
	if wm.isBuiltinWorkflow(name) {
		return fmt.Errorf("不能取消注册内置工作流: %s", name)
	}

	return wm.registry.UnregisterWorkflow(name)
}

// isBuiltinWorkflow 检查是否为内置工作流
func (wm *WorkflowManager) isBuiltinWorkflow(name string) bool {
	builtinWorkflows := []string{
		"simple_chat",
		"optimized_rag",
		"tool_calling",
		"multi_step_chat",
	}

	for _, builtin := range builtinWorkflows {
		if name == builtin {
			return true
		}
	}

	return false
}

// StartCleanupService 启动清理服务
func (wm *WorkflowManager) StartCleanupService() {
	cleanupInterval := 10 * time.Minute
	maxAge := 1 * time.Hour

	go func() {
		ticker := time.NewTicker(cleanupInterval)
		defer ticker.Stop()

		for {
			select {
			case <-ticker.C:
				if executor, ok := wm.executor.(*DefaultWorkflowExecutor); ok {
					executor.CleanupCompletedExecutions(maxAge)
					wm.logger.WithFields(logrus.Fields{
						"operation":     "cleanup_completed",
						"max_age":       maxAge.String(),
						"active_count":  executor.GetActiveExecutions(),
						"total_count":   executor.GetExecutionCount(),
					}).Debug("清理已完成的执行记录")
				}
			}
		}
	}()

	wm.logger.Info("工作流清理服务已启动")
}

// Shutdown 关闭工作流管理器
func (wm *WorkflowManager) Shutdown() {
	wm.logger.Info("正在关闭工作流管理器...")
	
	// TODO: 实现优雅关闭
	// - 等待当前执行完成
	// - 取消未完成的执行
	// - 清理资源
	
	wm.logger.Info("工作流管理器已关闭")
}