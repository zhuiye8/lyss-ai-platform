package workflows

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
)

// DefaultWorkflowExecutor 默认工作流执行器实现
type DefaultWorkflowExecutor struct {
	registry     WorkflowRegistry
	executions   map[string]*WorkflowExecutionContext
	mutex        sync.RWMutex
	logger       *logrus.Logger
	maxExecutions int
	executionTimeout time.Duration
}

// NewDefaultWorkflowExecutor 创建默认工作流执行器
func NewDefaultWorkflowExecutor(registry WorkflowRegistry, logger *logrus.Logger, maxExecutions int, executionTimeout time.Duration) *DefaultWorkflowExecutor {
	return &DefaultWorkflowExecutor{
		registry:         registry,
		executions:       make(map[string]*WorkflowExecutionContext),
		logger:           logger,
		maxExecutions:    maxExecutions,
		executionTimeout: executionTimeout,
	}
}

// Execute 执行工作流
func (e *DefaultWorkflowExecutor) Execute(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error) {
	// 验证并发限制
	if err := e.checkConcurrencyLimit(); err != nil {
		return nil, err
	}

	// 获取工作流
	workflow, err := e.registry.GetWorkflow(req.WorkflowType)
	if err != nil {
		return nil, fmt.Errorf("获取工作流失败: %w", err)
	}

	// 生成执行ID（如果未提供）
	if req.ExecutionID == "" {
		req.ExecutionID = uuid.New().String()
	}

	// 创建执行上下文
	execCtx := &WorkflowExecutionContext{
		RequestID:     req.RequestID,
		ExecutionID:   req.ExecutionID,
		TenantID:      req.TenantID,
		UserID:        req.UserID,
		WorkflowType:  req.WorkflowType,
		State:         make(map[string]interface{}),
		Configuration: req.Configuration,
		Steps:         make([]WorkflowStep, 0),
		StartTime:     time.Now().UnixMilli(),
		Status:        "running",
	}

	// 注册执行上下文
	e.registerExecution(execCtx)
	defer e.unregisterExecution(req.ExecutionID)

	// 创建带超时的上下文
	timeoutCtx, cancel := context.WithTimeout(ctx, e.executionTimeout)
	defer cancel()

	// 记录开始执行
	e.logger.WithFields(logrus.Fields{
		"request_id":     req.RequestID,
		"execution_id":   req.ExecutionID,
		"tenant_id":      req.TenantID,
		"user_id":        req.UserID,
		"workflow_type":  req.WorkflowType,
		"operation":      "execution_start",
	}).Info("开始执行工作流")

	// 执行工作流
	response, err := workflow.Execute(timeoutCtx, req)
	
	// 更新执行状态
	execCtx.EndTime = time.Now().UnixMilli()
	if err != nil {
		execCtx.Status = "failed"
		e.logger.WithFields(logrus.Fields{
			"request_id":     req.RequestID,
			"execution_id":   req.ExecutionID,
			"tenant_id":      req.TenantID,
			"user_id":        req.UserID,
			"workflow_type":  req.WorkflowType,
			"operation":      "execution_failed",
			"error":          err.Error(),
			"execution_time": execCtx.EndTime - execCtx.StartTime,
		}).Error("工作流执行失败")
	} else {
		execCtx.Status = "completed"
		e.logger.WithFields(logrus.Fields{
			"request_id":     req.RequestID,
			"execution_id":   req.ExecutionID,
			"tenant_id":      req.TenantID,
			"user_id":        req.UserID,
			"workflow_type":  req.WorkflowType,
			"operation":      "execution_completed",
			"execution_time": execCtx.EndTime - execCtx.StartTime,
		}).Info("工作流执行成功")
	}

	return response, err
}

// ExecuteStream 流式执行工作流
func (e *DefaultWorkflowExecutor) ExecuteStream(ctx context.Context, req *WorkflowRequest) (<-chan *WorkflowStreamResponse, error) {
	// 创建响应通道
	responseCh := make(chan *WorkflowStreamResponse, 100)
	
	// 异步执行工作流
	go func() {
		defer close(responseCh)
		
		// 执行工作流
		response, err := e.Execute(ctx, req)
		
		if err != nil {
			// 发送错误
			responseCh <- &WorkflowStreamResponse{
				Type:  "error",
				Error: err.Error(),
			}
			return
		}
		
		// 发送成功响应
		responseCh <- &WorkflowStreamResponse{
			Type:    "data",
			Content: response.Content,
			Data:    response,
		}
		
		// 发送完成信号
		responseCh <- &WorkflowStreamResponse{
			Type: "done",
		}
	}()
	
	return responseCh, nil
}

// GetExecutionStatus 获取执行状态
func (e *DefaultWorkflowExecutor) GetExecutionStatus(executionID string) (*WorkflowExecutionStatus, error) {
	e.mutex.RLock()
	defer e.mutex.RUnlock()

	execCtx, exists := e.executions[executionID]
	if !exists {
		return nil, fmt.Errorf("执行ID %s 不存在", executionID)
	}

	// 计算进度
	progress := 0
	if execCtx.Status == "completed" {
		progress = 100
	} else if execCtx.Status == "running" {
		progress = 50 // 简化的进度计算
	}

	// 当前步骤
	currentStep := ""
	if len(execCtx.Steps) > 0 {
		currentStep = execCtx.Steps[len(execCtx.Steps)-1].Name
	}

	// 执行时间
	executionTime := int(time.Now().UnixMilli() - execCtx.StartTime)
	if execCtx.EndTime > 0 {
		executionTime = int(execCtx.EndTime - execCtx.StartTime)
	}

	return &WorkflowExecutionStatus{
		ExecutionID:     executionID,
		Status:          execCtx.Status,
		Progress:        progress,
		CurrentStep:     currentStep,
		Steps:           execCtx.Steps,
		StartTime:       execCtx.StartTime,
		EndTime:         execCtx.EndTime,
		ExecutionTimeMs: executionTime,
	}, nil
}

// CancelExecution 取消执行
func (e *DefaultWorkflowExecutor) CancelExecution(executionID string) error {
	e.mutex.Lock()
	defer e.mutex.Unlock()

	execCtx, exists := e.executions[executionID]
	if !exists {
		return fmt.Errorf("执行ID %s 不存在", executionID)
	}

	if execCtx.Status != "running" {
		return fmt.Errorf("执行ID %s 状态为 %s，无法取消", executionID, execCtx.Status)
	}

	// 更新状态
	execCtx.Status = "cancelled"
	execCtx.EndTime = time.Now().UnixMilli()

	e.logger.WithFields(logrus.Fields{
		"execution_id": executionID,
		"tenant_id":    execCtx.TenantID,
		"user_id":      execCtx.UserID,
		"workflow_type": execCtx.WorkflowType,
		"operation":    "execution_cancelled",
	}).Info("工作流执行已取消")

	return nil
}

// checkConcurrencyLimit 检查并发限制
func (e *DefaultWorkflowExecutor) checkConcurrencyLimit() error {
	e.mutex.RLock()
	defer e.mutex.RUnlock()

	activeCount := 0
	for _, execCtx := range e.executions {
		if execCtx.Status == "running" {
			activeCount++
		}
	}

	if activeCount >= e.maxExecutions {
		return fmt.Errorf("已达到最大并发执行数限制: %d", e.maxExecutions)
	}

	return nil
}

// registerExecution 注册执行上下文
func (e *DefaultWorkflowExecutor) registerExecution(execCtx *WorkflowExecutionContext) {
	e.mutex.Lock()
	defer e.mutex.Unlock()
	
	e.executions[execCtx.ExecutionID] = execCtx
}

// unregisterExecution 取消注册执行上下文
func (e *DefaultWorkflowExecutor) unregisterExecution(executionID string) {
	e.mutex.Lock()
	defer e.mutex.Unlock()
	
	delete(e.executions, executionID)
}

// GetActiveExecutions 获取活跃执行数
func (e *DefaultWorkflowExecutor) GetActiveExecutions() int {
	e.mutex.RLock()
	defer e.mutex.RUnlock()

	activeCount := 0
	for _, execCtx := range e.executions {
		if execCtx.Status == "running" {
			activeCount++
		}
	}

	return activeCount
}

// GetExecutionCount 获取总执行数
func (e *DefaultWorkflowExecutor) GetExecutionCount() int {
	e.mutex.RLock()
	defer e.mutex.RUnlock()

	return len(e.executions)
}

// CleanupCompletedExecutions 清理已完成的执行
func (e *DefaultWorkflowExecutor) CleanupCompletedExecutions(maxAge time.Duration) {
	e.mutex.Lock()
	defer e.mutex.Unlock()

	now := time.Now().UnixMilli()
	cutoff := now - maxAge.Milliseconds()

	for id, execCtx := range e.executions {
		if execCtx.Status != "running" && execCtx.EndTime > 0 && execCtx.EndTime < cutoff {
			delete(e.executions, id)
		}
	}
}