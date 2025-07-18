package workflows

import (
	"context"
	"fmt"
	"time"

	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/workflows/nodes"
	"lyss-ai-platform/eino-service/pkg/credential"
)

// SimpleChatWorkflow 简单聊天工作流
type SimpleChatWorkflow struct {
	credentialManager *credential.Manager
	logger            *logrus.Logger
}

// NewSimpleChatWorkflow 创建简单聊天工作流
func NewSimpleChatWorkflow(credentialManager *credential.Manager, logger *logrus.Logger) *SimpleChatWorkflow {
	return &SimpleChatWorkflow{
		credentialManager: credentialManager,
		logger:            logger,
	}
}

// Execute 执行简单聊天工作流
func (w *SimpleChatWorkflow) Execute(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error) {
	startTime := time.Now()
	
	// 初始化工作流上下文
	nodeCtx := &nodes.NodeContext{
		RequestID:     req.RequestID,
		ExecutionID:   req.ExecutionID,
		TenantID:      req.TenantID,
		UserID:        req.UserID,
		WorkflowType:  "simple_chat",
		State:         make(map[string]interface{}),
		Logger:        w.logger,
		StartTime:     startTime,
		Configuration: req.Configuration,
	}

	// 验证输入
	if err := w.validateInput(req); err != nil {
		w.logger.WithFields(logrus.Fields{
			"request_id":     req.RequestID,
			"execution_id":   req.ExecutionID,
			"tenant_id":      req.TenantID,
			"user_id":        req.UserID,
			"workflow_type":  "simple_chat",
			"operation":      "validation_failed",
			"error":          err.Error(),
		}).Error("工作流输入验证失败")
		
		return &WorkflowResponse{
			Success:         false,
			ErrorMessage:    fmt.Sprintf("输入验证失败: %s", err.Error()),
			ExecutionTimeMs: time.Since(startTime).Milliseconds(),
		}, err
	}

	// 从请求中提取数据到状态
	nodeCtx.State["message"] = req.Message
	
	// 提取模型配置
	if req.ModelConfig != nil {
		if model, exists := req.ModelConfig["model"]; exists {
			nodeCtx.State["model"] = model
		}
		if temperature, exists := req.ModelConfig["temperature"]; exists {
			nodeCtx.State["temperature"] = temperature
		}
		if maxTokens, exists := req.ModelConfig["max_tokens"]; exists {
			nodeCtx.State["max_tokens"] = maxTokens
		}
		if stream, exists := req.ModelConfig["stream"]; exists {
			nodeCtx.State["stream"] = stream
		}
	}

	// 添加系统提示（如果存在）
	if systemPrompt, exists := req.Configuration["system_prompt"]; exists {
		nodeCtx.State["system_prompt"] = systemPrompt
	}

	// 添加对话历史（如果存在）
	if conversationHistory, exists := req.Configuration["conversation_history"]; exists {
		nodeCtx.State["conversation_history"] = conversationHistory
	}

	// 记录工作流开始
	w.logger.WithFields(logrus.Fields{
		"request_id":     req.RequestID,
		"execution_id":   req.ExecutionID,
		"tenant_id":      req.TenantID,
		"user_id":        req.UserID,
		"workflow_type":  "simple_chat",
		"operation":      "workflow_start",
		"message_length": len(req.Message),
	}).Info("简单聊天工作流开始执行")

	// 创建聊天模型节点
	chatNode := nodes.NewChatModelNode("chat_model", w.credentialManager, w.logger)

	// 执行聊天模型节点
	result, err := chatNode.Execute(ctx, nodeCtx)
	if err != nil {
		w.logger.WithFields(logrus.Fields{
			"request_id":     req.RequestID,
			"execution_id":   req.ExecutionID,
			"tenant_id":      req.TenantID,
			"user_id":        req.UserID,
			"workflow_type":  "simple_chat",
			"operation":      "chat_node_failed",
			"error":          err.Error(),
		}).Error("聊天模型节点执行失败")
		
		return &WorkflowResponse{
			Success:         false,
			ErrorMessage:    fmt.Sprintf("聊天模型节点执行失败: %s", err.Error()),
			ExecutionTimeMs: time.Since(startTime).Milliseconds(),
		}, err
	}

	// 更新节点上下文
	chatNode.UpdateNodeContext(nodeCtx, result)

	// 构建响应
	response := &WorkflowResponse{
		Success:         true,
		Content:         result.Data["response"].(string),
		Model:           nodeCtx.State["model"].(string),
		WorkflowType:    "simple_chat",
		ExecutionTimeMs: time.Since(startTime).Milliseconds(),
		Usage: &TokenUsage{
			PromptTokens:     result.TokenUsage.PromptTokens,
			CompletionTokens: result.TokenUsage.CompletionTokens,
			TotalTokens:      result.TokenUsage.TotalTokens,
		},
		Metadata: map[string]interface{}{
			"workflow_type":    "simple_chat",
			"nodes_executed":   []string{"chat_model"},
			"finish_reason":    result.Data["finish_reason"],
			"response_id":      result.Data["response_id"],
			"model_used":       result.Data["model_used"],
			"node_metadata":    result.NodeMetadata,
		},
	}

	// 记录工作流完成
	w.logger.WithFields(logrus.Fields{
		"request_id":       req.RequestID,
		"execution_id":     req.ExecutionID,
		"tenant_id":        req.TenantID,
		"user_id":          req.UserID,
		"workflow_type":    "simple_chat",
		"operation":        "workflow_complete",
		"success":          true,
		"execution_time_ms": response.ExecutionTimeMs,
		"prompt_tokens":    response.Usage.PromptTokens,
		"completion_tokens": response.Usage.CompletionTokens,
		"total_tokens":     response.Usage.TotalTokens,
	}).Info("简单聊天工作流执行完成")

	return response, nil
}

// validateInput 验证输入
func (w *SimpleChatWorkflow) validateInput(req *WorkflowRequest) error {
	if req.Message == "" {
		return fmt.Errorf("消息内容不能为空")
	}
	
	if req.TenantID == "" {
		return fmt.Errorf("租户ID不能为空")
	}
	
	if req.UserID == "" {
		return fmt.Errorf("用户ID不能为空")
	}
	
	if req.RequestID == "" {
		return fmt.Errorf("请求ID不能为空")
	}
	
	if req.ExecutionID == "" {
		return fmt.Errorf("执行ID不能为空")
	}
	
	return nil
}

// GetRequiredInputs 获取必需的输入字段
func (w *SimpleChatWorkflow) GetRequiredInputs() []string {
	return []string{"message", "tenant_id", "user_id", "request_id", "execution_id"}
}

// GetOutputSchema 获取输出架构
func (w *SimpleChatWorkflow) GetOutputSchema() map[string]interface{} {
	return map[string]interface{}{
		"success":           "boolean",
		"content":           "string",
		"model":             "string",
		"workflow_type":     "string",
		"execution_time_ms": "integer",
		"usage": map[string]interface{}{
			"prompt_tokens":     "integer",
			"completion_tokens": "integer",
			"total_tokens":      "integer",
		},
		"metadata": "object",
	}
}

// GetInfo 获取工作流信息
func (w *SimpleChatWorkflow) GetInfo() *WorkflowInfo {
	return &WorkflowInfo{
		Name:        "simple_chat",
		DisplayName: "简单聊天",
		Description: "简单聊天工作流，直接调用AI模型进行对话",
		Version:     "1.0.0",
		Type:        "chat",
		Parameters: []WorkflowParameter{
			{
				Name:        "message",
				Type:        "string",
				Required:    true,
				Description: "用户输入的消息",
			},
		},
		SupportedFeatures: []string{
			"basic_chat",
			"streaming",
		},
		Nodes: []WorkflowNodeInfo{
			{
				Name:        "chat_model",
				Type:        "chat_model",
				Description: "调用AI模型进行对话生成",
				Required:    true,
			},
		},
		RequiredInputs: w.GetRequiredInputs(),
		OutputSchema:   w.GetOutputSchema(),
	}
}

// ExecuteStream 流式执行工作流
func (w *SimpleChatWorkflow) ExecuteStream(ctx context.Context, req *WorkflowRequest) (<-chan *WorkflowStreamResponse, error) {
	responseChan := make(chan *WorkflowStreamResponse, 10)

	go func() {
		defer close(responseChan)

		w.logger.WithFields(logrus.Fields{
			"execution_id":  req.ExecutionID,
			"tenant_id":     req.TenantID,
			"user_id":       req.UserID,
			"workflow_type": "simple_chat",
			"operation":     "workflow_stream_start",
		}).Info("开始流式执行简单聊天工作流")

		// 发送开始事件
		responseChan <- &WorkflowStreamResponse{
			Type:        "start",
			ExecutionID: req.ExecutionID,
			Data:        map[string]any{"message": "简单聊天工作流开始执行"},
		}

		// 执行工作流（简化版本）
		response, err := w.Execute(ctx, req)
		if err != nil {
			responseChan <- &WorkflowStreamResponse{
				Type:        "error",
				ExecutionID: req.ExecutionID,
				Error:       err.Error(),
			}
			return
		}

		// 模拟流式输出
		words := []string{"这是", "简单", "聊天", "工作流", "的", "响应"}
		var fullContent string
		
		for _, word := range words {
			fullContent += word
			
			responseChan <- &WorkflowStreamResponse{
				Type:        "chunk",
				ExecutionID: req.ExecutionID,
				Content:     fullContent,
				Data: map[string]any{
					"content": fullContent,
					"delta":   word,
				},
			}
			
			time.Sleep(200 * time.Millisecond)
		}

		// 发送结束事件
		responseChan <- &WorkflowStreamResponse{
			Type:        "end",
			ExecutionID: req.ExecutionID,
			Data: map[string]any{
				"message": "简单聊天工作流执行完成",
				"usage": map[string]int{
					"prompt_tokens":     response.Usage.PromptTokens,
					"completion_tokens": response.Usage.CompletionTokens,
					"total_tokens":      response.Usage.TotalTokens,
				},
				"execution_time_ms": response.ExecutionTimeMs,
			},
		}

		w.logger.WithFields(logrus.Fields{
			"execution_id":  req.ExecutionID,
			"tenant_id":     req.TenantID,
			"user_id":       req.UserID,
			"workflow_type": "simple_chat",
			"operation":     "workflow_stream_success",
		}).Info("简单聊天流式工作流执行成功")
	}()

	return responseChan, nil
}