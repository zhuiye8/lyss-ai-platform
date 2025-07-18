package workflows

import (
	"fmt"
	"sync"

	"github.com/sirupsen/logrus"
)

// DefaultWorkflowRegistry 默认工作流注册表实现
type DefaultWorkflowRegistry struct {
	workflows map[string]WorkflowEngine
	mutex     sync.RWMutex
	logger    *logrus.Logger
}

// NewDefaultWorkflowRegistry 创建默认工作流注册表
func NewDefaultWorkflowRegistry(logger *logrus.Logger) *DefaultWorkflowRegistry {
	return &DefaultWorkflowRegistry{
		workflows: make(map[string]WorkflowEngine),
		logger:    logger,
	}
}

// RegisterWorkflow 注册工作流
func (r *DefaultWorkflowRegistry) RegisterWorkflow(name string, workflow WorkflowEngine) error {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	if _, exists := r.workflows[name]; exists {
		return fmt.Errorf("工作流 %s 已经注册", name)
	}

	r.workflows[name] = workflow
	r.logger.WithFields(logrus.Fields{
		"workflow_name": name,
		"operation":     "register_workflow",
	}).Info("工作流注册成功")

	return nil
}

// GetWorkflow 获取工作流
func (r *DefaultWorkflowRegistry) GetWorkflow(name string) (WorkflowEngine, error) {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	workflow, exists := r.workflows[name]
	if !exists {
		return nil, fmt.Errorf("工作流 %s 未注册", name)
	}

	return workflow, nil
}

// ListWorkflows 列出所有工作流
func (r *DefaultWorkflowRegistry) ListWorkflows() []WorkflowInfo {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	var workflows []WorkflowInfo
	for _, workflow := range r.workflows {
		workflows = append(workflows, *workflow.GetInfo())
	}

	return workflows
}

// IsWorkflowRegistered 检查工作流是否已注册
func (r *DefaultWorkflowRegistry) IsWorkflowRegistered(name string) bool {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	_, exists := r.workflows[name]
	return exists
}

// GetWorkflowNames 获取所有工作流名称
func (r *DefaultWorkflowRegistry) GetWorkflowNames() []string {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	var names []string
	for name := range r.workflows {
		names = append(names, name)
	}

	return names
}

// GetWorkflowCount 获取工作流数量
func (r *DefaultWorkflowRegistry) GetWorkflowCount() int {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	return len(r.workflows)
}

// UnregisterWorkflow 取消注册工作流
func (r *DefaultWorkflowRegistry) UnregisterWorkflow(name string) error {
	r.mutex.Lock()
	defer r.mutex.Unlock()

	if _, exists := r.workflows[name]; !exists {
		return fmt.Errorf("工作流 %s 未注册", name)
	}

	delete(r.workflows, name)
	r.logger.WithFields(logrus.Fields{
		"workflow_name": name,
		"operation":     "unregister_workflow",
	}).Info("工作流取消注册成功")

	return nil
}

// ValidateWorkflow 验证工作流
func (r *DefaultWorkflowRegistry) ValidateWorkflow(name string, workflow WorkflowEngine) error {
	if name == "" {
		return fmt.Errorf("工作流名称不能为空")
	}

	if workflow == nil {
		return fmt.Errorf("工作流实例不能为空")
	}

	info := workflow.GetInfo()
	if info == nil {
		return fmt.Errorf("工作流信息不能为空")
	}

	if info.Name == "" {
		return fmt.Errorf("工作流名称不能为空")
	}

	if info.Name != name {
		return fmt.Errorf("工作流名称不匹配: 期望 %s, 实际 %s", name, info.Name)
	}

	return nil
}

// RegisterWorkflowSafely 安全注册工作流（带验证）
func (r *DefaultWorkflowRegistry) RegisterWorkflowSafely(name string, workflow WorkflowEngine) error {
	if err := r.ValidateWorkflow(name, workflow); err != nil {
		return fmt.Errorf("工作流验证失败: %w", err)
	}

	return r.RegisterWorkflow(name, workflow)
}

// GetWorkflowInfo 获取工作流信息
func (r *DefaultWorkflowRegistry) GetWorkflowInfo(name string) (*WorkflowInfo, error) {
	workflow, err := r.GetWorkflow(name)
	if err != nil {
		return nil, err
	}

	return workflow.GetInfo(), nil
}

// GetWorkflowInfos 获取所有工作流信息
func (r *DefaultWorkflowRegistry) GetWorkflowInfos() map[string]*WorkflowInfo {
	r.mutex.RLock()
	defer r.mutex.RUnlock()

	infos := make(map[string]*WorkflowInfo)
	for name, workflow := range r.workflows {
		infos[name] = workflow.GetInfo()
	}

	return infos
}