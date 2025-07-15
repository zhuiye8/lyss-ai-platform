package nodes

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/client"
	"lyss-ai-platform/eino-service/internal/models"
	"lyss-ai-platform/eino-service/pkg/credential"
)

// ChatModelNode 聊天模型节点
type ChatModelNode struct {
	*BaseNode
	credentialManager *credential.Manager
}

// NewChatModelNode 创建聊天模型节点
func NewChatModelNode(name string, credentialManager *credential.Manager, logger *logrus.Logger) *ChatModelNode {
	return &ChatModelNode{
		BaseNode: NewBaseNode(
			name,
			"chat_model",
			"调用AI模型进行对话生成",
			logger,
		),
		credentialManager: credentialManager,
	}
}

// Execute 执行聊天模型节点
func (n *ChatModelNode) Execute(ctx context.Context, nodeCtx *NodeContext) (*NodeResult, error) {
	startTime := time.Now()
	n.LogNodeStart(ctx, nodeCtx)

	// 验证输入
	if err := n.ValidateInput(nodeCtx.State); err != nil {
		n.LogNodeError(ctx, nodeCtx, err)
		return &NodeResult{
			Success:    false,
			Error:      fmt.Sprintf("输入验证失败: %s", err.Error()),
			DurationMs: int(time.Since(startTime).Milliseconds()),
		}, err
	}

	// 获取输入数据
	message, ok := nodeCtx.State["message"].(string)
	if !ok {
		err := fmt.Errorf("message字段类型错误")
		n.LogNodeError(ctx, nodeCtx, err)
		return &NodeResult{
			Success:    false,
			Error:      "message字段必须是字符串类型",
			DurationMs: int(time.Since(startTime).Milliseconds()),
		}, err
	}

	// 获取模型配置
	modelConfig := n.getModelConfig(nodeCtx.State)
	
	// 获取对话历史（如果存在）
	var conversationHistory []client.DeepSeekMessage
	if history, exists := nodeCtx.State["conversation_history"]; exists {
		if historySlice, ok := history.([]interface{}); ok {
			for _, item := range historySlice {
				if msgMap, ok := item.(map[string]interface{}); ok {
					if role, roleOk := msgMap["role"].(string); roleOk {
						if content, contentOk := msgMap["content"].(string); contentOk {
							conversationHistory = append(conversationHistory, client.DeepSeekMessage{
								Role:    role,
								Content: content,
							})
						}
					}
				}
			}
		}
	}

	// 构建消息序列
	messages := n.buildMessages(conversationHistory, message, nodeCtx.State)

	// 获取供应商凭证
	credential, err := n.credentialManager.GetBestCredentialForModel(
		nodeCtx.TenantID,
		modelConfig.Provider,
		modelConfig.ModelName,
	)
	if err != nil {
		n.LogNodeError(ctx, nodeCtx, err)
		return &NodeResult{
			Success:    false,
			Error:      fmt.Sprintf("获取凭证失败: %s", err.Error()),
			DurationMs: int(time.Since(startTime).Milliseconds()),
		}, err
	}

	// 记录凭证使用
	n.credentialManager.RecordUsage(credential.ID.String())

	// 调用AI模型
	result, err := n.callAIModel(ctx, nodeCtx, credential, messages, modelConfig)
	if err != nil {
		n.LogNodeError(ctx, nodeCtx, err)
		return &NodeResult{
			Success:    false,
			Error:      fmt.Sprintf("AI模型调用失败: %s", err.Error()),
			DurationMs: int(time.Since(startTime).Milliseconds()),
		}, err
	}

	// 处理成功结果
	result.DurationMs = int(time.Since(startTime).Milliseconds())
	n.LogNodeComplete(ctx, nodeCtx, result)

	return result, nil
}

// getModelConfig 获取模型配置
func (n *ChatModelNode) getModelConfig(state map[string]interface{}) *ModelConfig {
	config := &ModelConfig{
		Provider:    "deepseek",
		ModelName:   "deepseek-chat",
		Temperature: 0.7,
		MaxTokens:   2048,
		Stream:      false,
	}

	// 从状态中获取配置参数
	if modelName, exists := state["model"]; exists {
		if name, ok := modelName.(string); ok {
			config.ModelName = name
		}
	}

	if temperature, exists := state["temperature"]; exists {
		if temp, ok := temperature.(float64); ok {
			config.Temperature = temp
		}
	}

	if maxTokens, exists := state["max_tokens"]; exists {
		if tokens, ok := maxTokens.(int); ok {
			config.MaxTokens = tokens
		}
	}

	if stream, exists := state["stream"]; exists {
		if streamBool, ok := stream.(bool); ok {
			config.Stream = streamBool
		}
	}

	return config
}

// buildMessages 构建消息序列
func (n *ChatModelNode) buildMessages(history []client.DeepSeekMessage, currentMessage string, state map[string]interface{}) []client.DeepSeekMessage {
	messages := make([]client.DeepSeekMessage, 0)

	// 添加系统消息（如果存在）
	if systemPrompt, exists := state["system_prompt"]; exists {
		if prompt, ok := systemPrompt.(string); ok && prompt != "" {
			messages = append(messages, client.DeepSeekMessage{
				Role:    "system",
				Content: prompt,
			})
		}
	}

	// 添加对话历史
	messages = append(messages, history...)

	// 添加当前用户消息
	messages = append(messages, client.DeepSeekMessage{
		Role:    "user",
		Content: currentMessage,
	})

	return messages
}

// callAIModel 调用AI模型
func (n *ChatModelNode) callAIModel(
	ctx context.Context,
	nodeCtx *NodeContext,
	credential *models.SupplierCredential,
	messages []client.DeepSeekMessage,
	config *ModelConfig,
) (*NodeResult, error) {
	// 目前只支持DeepSeek，后续可扩展其他供应商
	switch credential.Provider {
	case "deepseek":
		return n.callDeepSeekModel(ctx, nodeCtx, credential, messages, config)
	default:
		return nil, fmt.Errorf("不支持的供应商: %s", credential.Provider)
	}
}

// callDeepSeekModel 调用DeepSeek模型
func (n *ChatModelNode) callDeepSeekModel(
	ctx context.Context,
	nodeCtx *NodeContext,
	credential *models.SupplierCredential,
	messages []client.DeepSeekMessage,
	config *ModelConfig,
) (*NodeResult, error) {
	// 创建DeepSeek客户端
	deepSeekClient := client.NewDeepSeekClient(
		credential.APIKey,
		credential.BaseURL,
		n.Logger,
	)

	// 构建请求
	req := &client.DeepSeekRequest{
		Model:       config.ModelName,
		Messages:    messages,
		Temperature: config.Temperature,
		MaxTokens:   config.MaxTokens,
		Stream:      config.Stream,
	}

	// 发送请求
	resp, err := deepSeekClient.ChatCompletion(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("DeepSeek API调用失败: %w", err)
	}

	// 检查响应
	if len(resp.Choices) == 0 {
		return nil, fmt.Errorf("DeepSeek响应无选择项")
	}

	choice := resp.Choices[0]
	if choice.Message == nil {
		return nil, fmt.Errorf("DeepSeek响应消息为空")
	}

	// 构建结果
	result := &NodeResult{
		Success: true,
		Data: map[string]interface{}{
			"response":           choice.Message.Content,
			"assistant_message":  choice.Message.Content,
			"model_response":     choice.Message.Content,
			"finish_reason":      choice.FinishReason,
			"response_id":        resp.ID,
			"model_used":         resp.Model,
		},
		TokenUsage: &models.TokenUsage{
			PromptTokens:     resp.Usage.PromptTokens,
			CompletionTokens: resp.Usage.CompletionTokens,
			TotalTokens:      resp.Usage.TotalTokens,
		},
		NodeMetadata: map[string]interface{}{
			"provider":       credential.Provider,
			"model":          resp.Model,
			"credential_id":  credential.ID.String(),
			"finish_reason":  choice.FinishReason,
			"messages_count": len(messages),
		},
	}

	return result, nil
}

// ValidateInput 验证输入数据
func (n *ChatModelNode) ValidateInput(input map[string]interface{}) error {
	if err := n.BaseNode.ValidateInput(input); err != nil {
		return err
	}

	// 验证message字段
	if message, exists := input["message"]; exists {
		if messageStr, ok := message.(string); !ok || strings.TrimSpace(messageStr) == "" {
			return fmt.Errorf("message字段必须是非空字符串")
		}
	}

	return nil
}

// GetRequiredInputs 获取必需的输入字段
func (n *ChatModelNode) GetRequiredInputs() []string {
	return []string{"message"}
}

// GetOutputSchema 获取输出模式
func (n *ChatModelNode) GetOutputSchema() map[string]interface{} {
	return map[string]interface{}{
		"response":          "string",
		"assistant_message": "string",
		"model_response":    "string",
		"finish_reason":     "string",
		"response_id":       "string",
		"model_used":        "string",
	}
}

// ModelConfig 模型配置
type ModelConfig struct {
	Provider    string  `json:"provider"`
	ModelName   string  `json:"model_name"`
	Temperature float64 `json:"temperature"`
	MaxTokens   int     `json:"max_tokens"`
	Stream      bool    `json:"stream"`
}