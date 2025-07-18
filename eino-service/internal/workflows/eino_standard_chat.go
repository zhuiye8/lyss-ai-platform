package workflows

import (
	"context"
	"fmt"
	"io"
	"time"

	"github.com/cloudwego/eino/schema"
	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino-ext/components/model/deepseek"
	"github.com/cloudwego/eino-ext/components/model/ark"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/models"
	"lyss-ai-platform/eino-service/pkg/credential"
)

// EINOStandardChatWorkflow 基于EINO官方标准的聊天工作流
type EINOStandardChatWorkflow struct {
	credentialManager *credential.Manager
	logger            *logrus.Logger
}

// NewEINOStandardChatWorkflow 创建标准EINO聊天工作流
func NewEINOStandardChatWorkflow(credentialManager *credential.Manager, logger *logrus.Logger) *EINOStandardChatWorkflow {
	return &EINOStandardChatWorkflow{
		credentialManager: credentialManager,
		logger:            logger,
	}
}

// Execute 执行标准EINO聊天工作流
func (w *EINOStandardChatWorkflow) Execute(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error) {
	startTime := time.Now()
	
	w.logger.WithFields(logrus.Fields{
		"request_id":    req.RequestID,
		"execution_id":  req.ExecutionID,
		"tenant_id":     req.TenantID,
		"user_id":       req.UserID,
		"workflow_type": "eino_standard_chat",
		"operation":     "workflow_start",
	}).Info("开始执行标准EINO聊天工作流")

	// 1. 获取租户最佳凭证
	provider := "openai" // 默认供应商
	if req.ModelConfig != nil {
		if p, exists := req.ModelConfig["provider"]; exists {
			provider = p.(string)
		}
	}
	
	credential, err := w.credentialManager.GetBestCredentialForModel(req.TenantID, provider, "")
	if err != nil {
		return w.buildErrorResponse(startTime, fmt.Sprintf("获取凭证失败: %v", err), err)
	}

	// 2. 根据供应商创建ChatModel
	chatModel, err := w.createChatModel(ctx, credential)
	if err != nil {
		return w.buildErrorResponse(startTime, fmt.Sprintf("创建聊天模型失败: %v", err), err)
	}

	// 3. 构建输入消息
	messages := w.buildMessages(req)

	// 4. 执行模型调用
	result, err := chatModel.Generate(ctx, messages)
	
	if err != nil {
		return w.buildErrorResponse(startTime, fmt.Sprintf("模型调用失败: %v", err), err)
	}

	// 5. 记录凭证使用
	w.credentialManager.RecordUsage(credential.ID.String())

	// 6. 构建成功响应
	response := &WorkflowResponse{
		Success:         true,
		Content:         result.Content,
		Model:           w.getModelName(credential),
		WorkflowType:    "eino_standard_chat",
		ExecutionTimeMs: time.Since(startTime).Milliseconds(),
		Usage: &TokenUsage{
			PromptTokens:     w.getPromptTokens(result),
			CompletionTokens: w.getCompletionTokens(result),
			TotalTokens:      w.getTotalTokens(result),
		},
		Metadata: map[string]interface{}{
			"provider":       credential.Provider,
			"credential_id":  credential.ID.String(),
			"model_used":     w.getModelName(credential),
			"eino_framework": "cloudwego/eino",
			"workflow_type":  "standard_chat",
		},
	}

	w.logger.WithFields(logrus.Fields{
		"request_id":       req.RequestID,
		"execution_id":     req.ExecutionID,
		"tenant_id":        req.TenantID,
		"user_id":          req.UserID,
		"workflow_type":    "eino_standard_chat",
		"operation":        "workflow_success",
		"provider":         credential.Provider,
		"model":            w.getModelName(credential),
		"execution_time_ms": response.ExecutionTimeMs,
		"total_tokens":     response.Usage.TotalTokens,
	}).Info("标准EINO聊天工作流执行成功")

	return response, nil
}

// ExecuteStream 流式执行标准EINO聊天工作流
func (w *EINOStandardChatWorkflow) ExecuteStream(ctx context.Context, req *WorkflowRequest) (<-chan *WorkflowStreamResponse, error) {
	responseChan := make(chan *WorkflowStreamResponse, 100)
	
	go func() {
		defer close(responseChan)
		
		w.logger.WithFields(logrus.Fields{
			"execution_id":  req.ExecutionID,
			"tenant_id":     req.TenantID,
			"user_id":       req.UserID,
			"workflow_type": "eino_standard_chat",
			"operation":     "workflow_stream_start",
		}).Info("开始流式执行标准EINO聊天工作流")

		// 1. 获取租户最佳凭证
		provider := "openai"
		if req.ModelConfig != nil {
			if p, exists := req.ModelConfig["provider"]; exists {
				provider = p.(string)
			}
		}
		
		credential, err := w.credentialManager.GetBestCredentialForModel(req.TenantID, provider, "")
		if err != nil {
			responseChan <- &WorkflowStreamResponse{
				Type:  "error",
				Error: fmt.Sprintf("获取凭证失败: %v", err),
			}
			return
		}

		// 2. 根据供应商创建ChatModel
		chatModel, err := w.createChatModel(ctx, credential)
		if err != nil {
			responseChan <- &WorkflowStreamResponse{
				Type:  "error",
				Error: fmt.Sprintf("创建模型失败: %v", err),
			}
			return
		}

		// 3. 构建消息
		messages := w.buildMessages(req)

		// 4. 发送开始事件
		responseChan <- &WorkflowStreamResponse{
			Type:        "start",
			ExecutionID: req.ExecutionID,
			Data: map[string]any{
				"provider": credential.Provider,
				"model":    w.getModelName(credential),
			},
		}

		// 5. 执行流式调用
		streamResult, err := chatModel.Stream(ctx, messages)
		if err != nil {
			responseChan <- &WorkflowStreamResponse{
				Type:  "error",
				Error: fmt.Sprintf("流式调用失败: %v", err),
			}
			return
		}

		// 6. 处理流式响应
		var fullContent string
		var chunks []*schema.Message
		
		for {
			chunk, err := streamResult.Recv()
			if err == io.EOF {
				break
			}
			if err != nil {
				responseChan <- &WorkflowStreamResponse{
					Type:  "error",
					Error: fmt.Sprintf("接收流式数据失败: %v", err),
				}
				return
			}

			chunks = append(chunks, chunk)
			fullContent += chunk.Content
			
			responseChan <- &WorkflowStreamResponse{
				Type:        "chunk",
				ExecutionID: req.ExecutionID,
				Content:     fullContent,
				Data: map[string]any{
					"delta": chunk.Content,
				},
			}
		}

		// 7. 合并最终消息
		finalMessage, err := schema.ConcatMessages(chunks)
		if err != nil {
			responseChan <- &WorkflowStreamResponse{
				Type:  "error",
				Error: fmt.Sprintf("合并消息失败: %v", err),
			}
			return
		}

		// 8. 发送结束事件
		responseChan <- &WorkflowStreamResponse{
			Type:        "end",
			ExecutionID: req.ExecutionID,
			Data: map[string]any{
				"final_content": finalMessage.Content,
				"provider":      credential.Provider,
				"model":         w.getModelName(credential),
				"usage": map[string]int{
					"prompt_tokens":     w.getPromptTokensFromMessage(finalMessage),
					"completion_tokens": w.getCompletionTokensFromMessage(finalMessage),
					"total_tokens":      w.getTotalTokensFromMessage(finalMessage),
				},
			},
		}

		// 9. 记录凭证使用
		w.credentialManager.RecordUsage(credential.ID.String())

		w.logger.WithFields(logrus.Fields{
			"execution_id":  req.ExecutionID,
			"tenant_id":     req.TenantID,
			"user_id":       req.UserID,
			"workflow_type": "eino_standard_chat",
			"operation":     "workflow_stream_success",
			"provider":      credential.Provider,
			"model":         w.getModelName(credential),
		}).Info("标准EINO流式聊天工作流执行成功")
	}()

	return responseChan, nil
}

// GetInfo 获取工作流信息
func (w *EINOStandardChatWorkflow) GetInfo() *WorkflowInfo {
	return &WorkflowInfo{
		Name:        "eino_standard_chat",
		DisplayName: "标准EINO聊天",
		Description: "基于CloudWeGo EINO官方框架的标准聊天工作流，支持多供应商模型调用",
		Version:     "1.0.0",
		Type:        "chat",
		Parameters: []WorkflowParameter{
			{
				Name:        "message",
				Type:        "string",
				Required:    true,
				Description: "用户输入的消息",
			},
			{
				Name:        "provider",
				Type:        "string",
				Required:    false,
				Description: "AI供应商（openai、deepseek、ark等）",
				Default:     "openai",
			},
		},
		SupportedFeatures: []string{
			"basic_chat",
			"streaming",
			"multi_provider",
			"official_eino",
		},
		Nodes: []WorkflowNodeInfo{
			{
				Name:        "eino_chat_model",
				Type:        "chat_model",
				Description: "使用EINO官方组件的AI模型调用",
				Required:    true,
			},
		},
		RequiredInputs: []string{"message", "tenant_id", "user_id", "request_id", "execution_id"},
		OutputSchema: map[string]interface{}{
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
		},
	}
}

// buildEINOChain 使用EINO官方API构建聊天链
func (w *EINOStandardChatWorkflow) buildEINOChain(ctx context.Context, credential *models.SupplierCredential) (eino.CompiledChain, error) {
	// 根据供应商创建对应的ChatModel
	chatModel, err := w.createChatModel(ctx, credential)
	if err != nil {
		return nil, fmt.Errorf("创建聊天模型失败: %w", err)
	}

	// 使用EINO官方Chain API构建工作流
	chain, err := eino.NewChain[map[string]any, *schema.Message]().
		AppendChatModel(chatModel).
		Compile(ctx)

	if err != nil {
		return nil, fmt.Errorf("编译EINO链失败: %w", err)
	}

	return chain, nil
}

// createChatModel 根据供应商创建对应的ChatModel
func (w *EINOStandardChatWorkflow) createChatModel(ctx context.Context, credential *models.SupplierCredential) (eino.ChatModel, error) {
	switch credential.Provider {
	case "openai":
		return openai.NewChatModel(ctx, &openai.ChatModelConfig{
			APIKey:  credential.APIKey,
			Model:   w.getModelName(credential),
			BaseURL: credential.BaseURL,
		})
	case "deepseek":
		return deepseek.NewChatModel(ctx, &deepseek.ChatModelConfig{
			APIKey: credential.APIKey,
			Model:  w.getModelName(credential),
		})
	case "ark":
		return ark.NewChatModel(ctx, &ark.ChatModelConfig{
			APIKey: credential.APIKey,
			Model:  w.getModelName(credential),
		})
	default:
		return nil, fmt.Errorf("不支持的供应商: %s", credential.Provider)
	}
}

// buildMessages 构建EINO schema消息
func (w *EINOStandardChatWorkflow) buildMessages(req *WorkflowRequest) []*schema.Message {
	var messages []*schema.Message

	// 添加系统提示（如果存在）
	if systemPrompt, exists := req.Configuration["system_prompt"]; exists {
		messages = append(messages, &schema.Message{
			Role:    schema.System,
			Content: systemPrompt.(string),
		})
	}

	// 添加用户消息
	messages = append(messages, &schema.Message{
		Role:    schema.User,
		Content: req.Message,
	})

	return messages
}

// buildErrorResponse 构建错误响应
func (w *EINOStandardChatWorkflow) buildErrorResponse(startTime time.Time, message string, err error) (*WorkflowResponse, error) {
	w.logger.WithError(err).Error(message)
	
	return &WorkflowResponse{
		Success:         false,
		ErrorMessage:    message,
		ExecutionTimeMs: time.Since(startTime).Milliseconds(),
		WorkflowType:    "eino_standard_chat",
	}, err
}

// getModelName 获取模型名称
func (w *EINOStandardChatWorkflow) getModelName(credential *models.SupplierCredential) string {
	if model, exists := credential.ModelConfigs["model"]; exists {
		return model.(string)
	}
	
	// 默认模型
	switch credential.Provider {
	case "openai":
		return "gpt-3.5-turbo"
	case "deepseek":
		return "deepseek-chat"
	case "ark":
		return "default-ark-model"
	default:
		return "unknown"
	}
}

// Token统计辅助方法
func (w *EINOStandardChatWorkflow) getPromptTokens(result *schema.Message) int {
	if result.ResponseMeta != nil && result.ResponseMeta.Usage != nil {
		return int(result.ResponseMeta.Usage.PromptTokens)
	}
	return 0
}

func (w *EINOStandardChatWorkflow) getCompletionTokens(result *schema.Message) int {
	if result.ResponseMeta != nil && result.ResponseMeta.Usage != nil {
		return int(result.ResponseMeta.Usage.CompletionTokens)
	}
	return 0
}

func (w *EINOStandardChatWorkflow) getTotalTokens(result *schema.Message) int {
	if result.ResponseMeta != nil && result.ResponseMeta.Usage != nil {
		return int(result.ResponseMeta.Usage.TotalTokens)
	}
	return 0
}

func (w *EINOStandardChatWorkflow) getPromptTokensFromMessage(message *schema.Message) int {
	return w.getPromptTokens(message)
}

func (w *EINOStandardChatWorkflow) getCompletionTokensFromMessage(message *schema.Message) int {
	return w.getCompletionTokens(message)
}

func (w *EINOStandardChatWorkflow) getTotalTokensFromMessage(message *schema.Message) int {
	return w.getTotalTokens(message)
}