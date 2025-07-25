package utils

import (
	"context"
	"fmt"
	"log"
	"io"
	"time"

	"chat-service/configs"

	"github.com/cloudwego/eino/schema"
	"github.com/cloudwego/eino/components/model"
	"github.com/cloudwego/eino-ext/components/model/openai"
	"github.com/cloudwego/eino-ext/components/model/deepseek"
)

// EINOHelper EINO框架辅助工具
type EINOHelper struct {
	config *configs.Config
	models map[string]model.ChatModel
}

// NewEINOHelper 创建EINO辅助工具
func NewEINOHelper(config *configs.Config) *EINOHelper {
	helper := &EINOHelper{
		config: config,
		models: make(map[string]model.ChatModel),
	}
	
	// 初始化模型
	if err := helper.initializeModels(); err != nil {
		log.Printf("模型初始化失败: %v", err)
	}
	
	return helper
}

// initializeModels 初始化支持的AI模型
func (h *EINOHelper) initializeModels() error {
	ctx := context.Background()
	
	// 初始化OpenAI模型
	if apiKey, exists := h.config.EINO.Providers["openai"]; exists && apiKey != "" {
		models := []string{"gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"}
		for _, modelName := range models {
			maxTokens := 4000
			temperature := float32(0.7)
			topP := float32(1.0)
			
			model, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
				APIKey:      apiKey,
				Model:       modelName,
				MaxTokens:   &maxTokens,
				Temperature: &temperature,
				TopP:        &topP,
			})
			if err != nil {
				log.Printf("OpenAI模型 %s 初始化失败: %v", modelName, err)
				continue
			}
			
			key := fmt.Sprintf("openai:%s", modelName)
			h.models[key] = model
			log.Printf("OpenAI模型初始化成功: %s", key)
		}
	}
	
	// 初始化DeepSeek模型
	if apiKey, exists := h.config.EINO.Providers["deepseek"]; exists && apiKey != "" {
		models := []string{"deepseek-chat", "deepseek-coder"}
		for _, modelName := range models {
			maxTokens := 2000
			temperature := float32(0.7)
			
			model, err := deepseek.NewChatModel(ctx, &deepseek.ChatModelConfig{
				APIKey:      apiKey,
				Model:       modelName,
				MaxTokens:   maxTokens,
				Temperature: temperature,
			})
			if err != nil {
				log.Printf("DeepSeek模型 %s 初始化失败: %v", modelName, err)
				continue
			}
			
			key := fmt.Sprintf("deepseek:%s", modelName)
			h.models[key] = model
			log.Printf("DeepSeek模型初始化成功: %s", key)
		}
	}
	
	return nil
}

// CallModel 调用AI模型（简化接口）
func (h *EINOHelper) CallModel(ctx context.Context, provider, model, message string) (*ModelResponse, error) {
	// 获取模型实例
	key := fmt.Sprintf("%s:%s", provider, model)
	chatModel, exists := h.models[key]
	if !exists {
		return nil, fmt.Errorf("模型未找到: %s", key)
	}
	
	log.Printf("调用真实EINO模型: provider=%s, model=%s, message长度=%d", provider, model, len(message))
	
	// 构建消息
	messages := []*schema.Message{
		{
			Role:    schema.RoleType("user"),
			Content: message,
		},
	}
	
	// 调用模型生成
	response, err := chatModel.Generate(ctx, messages)
	if err != nil {
		return nil, fmt.Errorf("模型调用失败: %w", err)
	}
	
	// 构建响应
	var tokensUsed int
	var cost float64
	
	// 尝试获取使用情况信息
	if response.ResponseMeta != nil && response.ResponseMeta.Usage != nil {
		tokensUsed = response.ResponseMeta.Usage.TotalTokens
		// 简单的成本估算 (实际应该根据供应商的定价)
		cost = float64(tokensUsed) * 0.0001
	}
	
	result := &ModelResponse{
		Content:    response.Content,
		Model:      model,
		Provider:   provider,
		TokensUsed: tokensUsed,
		Cost:       cost,
		Metadata: map[string]interface{}{
			"real_eino":   true,
			"timestamp":   time.Now().Unix(),
			"request_id":  response.ResponseMeta,
		},
	}
	
	return result, nil
}

// CallModelStream 流式调用AI模型
func (h *EINOHelper) CallModelStream(ctx context.Context, provider, model, message string, callback StreamCallback) error {
	// 获取模型实例
	key := fmt.Sprintf("%s:%s", provider, model)
	chatModel, exists := h.models[key]
	if !exists {
		return fmt.Errorf("模型未找到: %s", key)
	}
	
	log.Printf("流式调用真实EINO模型: provider=%s, model=%s, message长度=%d", provider, model, len(message))
	
	// 构建消息
	messages := []*schema.Message{
		{
			Role:    schema.RoleType("user"),
			Content: message,
		},
	}
	
	// 调用流式生成
	stream, err := chatModel.Stream(ctx, messages)
	if err != nil {
		return fmt.Errorf("创建流失败: %w", err)
	}
	defer stream.Close()
	
	// 处理流式数据
	chunkIndex := 0
	for {
		chunk, err := stream.Recv()
		if err == io.EOF {
			// 发送完成信号
			if callbackErr := callback(StreamChunk{
				Content:  "",
				Done:     true,
				Metadata: map[string]interface{}{
					"chunk_index": chunkIndex,
					"final":       true,
				},
			}); callbackErr != nil {
				return fmt.Errorf("流式回调失败: %w", callbackErr)
			}
			break
		}
		if err != nil {
			return fmt.Errorf("接收流数据失败: %w", err)
		}
		
		// 调用回调函数处理数据块
		if err := callback(StreamChunk{
			Content: chunk.Content,
			Done:    false,
			Metadata: map[string]interface{}{
				"chunk_index": chunkIndex,
				"real_eino":   true,
				"timestamp":   time.Now().Unix(),
			},
		}); err != nil {
			return fmt.Errorf("流式回调失败: %w", err)
		}
		
		chunkIndex++
	}
	
	return nil
}

// BuildMessages 构建EINO消息格式
func (h *EINOHelper) BuildMessages(messages []Message) []*schema.Message {
	schemaMessages := make([]*schema.Message, len(messages))
	
	for i, msg := range messages {
		schemaMessages[i] = &schema.Message{
			Role:    schema.RoleType(msg.Role),
			Content: msg.Content,
		}
	}
	
	return schemaMessages
}

// CallModelWithHistory 调用模型（支持对话历史）
func (h *EINOHelper) CallModelWithHistory(ctx context.Context, provider, model string, messages []Message) (*ModelResponse, error) {
	// 获取模型实例
	key := fmt.Sprintf("%s:%s", provider, model)
	chatModel, exists := h.models[key]
	if !exists {
		return nil, fmt.Errorf("模型未找到: %s", key)
	}
	
	log.Printf("调用真实EINO模型(含历史): provider=%s, model=%s, messages=%d", provider, model, len(messages))
	
	// 构建消息历史
	schemaMessages := h.BuildMessages(messages)
	
	// 调用模型生成
	response, err := chatModel.Generate(ctx, schemaMessages)
	if err != nil {
		return nil, fmt.Errorf("模型调用失败: %w", err)
	}
	
	// 构建响应
	var tokensUsed int
	var cost float64
	
	// 尝试获取使用情况信息
	if response.ResponseMeta != nil && response.ResponseMeta.Usage != nil {
		tokensUsed = response.ResponseMeta.Usage.TotalTokens
		cost = float64(tokensUsed) * 0.0001
	}
	
	result := &ModelResponse{
		Content:    response.Content,
		Model:      model,
		Provider:   provider,
		TokensUsed: tokensUsed,
		Cost:       cost,
		Metadata: map[string]interface{}{
			"real_eino":     true,
			"timestamp":     time.Now().Unix(),
			"message_count": len(messages),
			"request_id":    response.ResponseMeta,
		},
	}
	
	return result, nil
}

// GetSupportedProviders 获取支持的供应商列表
func (h *EINOHelper) GetSupportedProviders() []string {
	providers := make([]string, 0)
	
	for provider, apiKey := range h.config.EINO.Providers {
		if apiKey != "" {
			providers = append(providers, provider)
		}
	}
	
	return providers
}

// ValidateProvider 验证供应商是否支持
func (h *EINOHelper) ValidateProvider(provider string) bool {
	apiKey, exists := h.config.EINO.Providers[provider]
	return exists && apiKey != ""
}

// ModelResponse 模型响应结构
type ModelResponse struct {
	Content    string                 `json:"content"`
	Model      string                 `json:"model"`
	Provider   string                 `json:"provider"`
	TokensUsed int                    `json:"tokens_used"`
	Cost       float64                `json:"cost"`
	Metadata   map[string]interface{} `json:"metadata"`
}

// StreamChunk 流式响应块
type StreamChunk struct {
	Content  string                 `json:"content"`
	Done     bool                   `json:"done"`
	Metadata map[string]interface{} `json:"metadata"`
}

// StreamCallback 流式响应回调函数
type StreamCallback func(chunk StreamChunk) error

// Message 消息结构
type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// GetModelConfig 获取模型配置
func (h *EINOHelper) GetModelConfig(provider, model string) (*ModelConfig, error) {
	// TODO: 实现模型配置获取逻辑
	
	// 返回默认配置
	return &ModelConfig{
		Provider:     provider,
		Model:        model,
		MaxTokens:    4000,
		Temperature:  0.7,
		TopP:         1.0,
		FrequencyPenalty: 0.0,
		PresencePenalty:  0.0,
	}, nil
}

// ModelConfig 模型配置
type ModelConfig struct {
	Provider         string  `json:"provider"`
	Model            string  `json:"model"`
	MaxTokens        int     `json:"max_tokens"`
	Temperature      float64 `json:"temperature"`
	TopP             float64 `json:"top_p"`
	FrequencyPenalty float64 `json:"frequency_penalty"`
	PresencePenalty  float64 `json:"presence_penalty"`
}