package utils

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"chat-service/configs"
)

// ProviderClient Provider Service客户端
type ProviderClient struct {
	config     *configs.Config
	httpClient *http.Client
	baseURL    string
}

// NewProviderClient 创建Provider Service客户端
func NewProviderClient(config *configs.Config) *ProviderClient {
	return &ProviderClient{
		config:  config,
		baseURL: "http://localhost:8003", // Provider Service地址
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// ChatRequest Provider Service聊天请求结构
type ProviderChatRequest struct {
	Model       string                   `json:"model"`
	Messages    []ProviderMessage        `json:"messages"`
	Stream      bool                     `json:"stream,omitempty"`
	MaxTokens   int                      `json:"max_tokens,omitempty"`
	Temperature float32                  `json:"temperature,omitempty"`
	TopP        float32                  `json:"top_p,omitempty"`
	User        string                   `json:"user,omitempty"`
}

// ProviderMessage Provider Service消息结构
type ProviderMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// ProviderChatResponse Provider Service聊天响应结构
type ProviderChatResponse struct {
	ID      string                    `json:"id"`
	Object  string                    `json:"object"`
	Created int64                     `json:"created"`
	Model   string                    `json:"model"`
	Choices []ProviderChoice          `json:"choices"`
	Usage   ProviderUsage             `json:"usage"`
}

// ProviderChoice Provider Service选择结构
type ProviderChoice struct {
	Index        int                `json:"index"`
	Message      ProviderMessage    `json:"message"`
	FinishReason string             `json:"finish_reason"`
}

// ProviderUsage Provider Service使用情况结构
type ProviderUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// ProviderStreamResponse Provider Service流式响应结构
type ProviderStreamResponse struct {
	ID      string                     `json:"id"`
	Object  string                     `json:"object"`
	Created int64                      `json:"created"`
	Model   string                     `json:"model"`
	Choices []ProviderStreamChoice     `json:"choices"`
}

// ProviderStreamChoice Provider Service流式选择结构
type ProviderStreamChoice struct {
	Index int                      `json:"index"`
	Delta ProviderStreamDelta      `json:"delta"`
	FinishReason string            `json:"finish_reason,omitempty"`
}

// ProviderStreamDelta Provider Service流式增量结构
type ProviderStreamDelta struct {
	Role    string `json:"role,omitempty"`
	Content string `json:"content,omitempty"`
}

// CallModel 通过Provider Service调用AI模型
func (c *ProviderClient) CallModel(ctx context.Context, model string, messages []Message, userID string) (*ModelResponse, error) {
	// 转换消息格式
	providerMessages := make([]ProviderMessage, len(messages))
	for i, msg := range messages {
		providerMessages[i] = ProviderMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	// 构建请求
	request := ProviderChatRequest{
		Model:       model,
		Messages:    providerMessages,
		Stream:      false,
		MaxTokens:   4000,
		Temperature: 0.7,
		TopP:        1.0,
		User:        userID,
	}

	log.Printf("调用Provider Service: model=%s, messages=%d", model, len(messages))

	// 发送请求到Provider Service
	response, err := c.sendChatRequest(ctx, request)
	if err != nil {
		return nil, fmt.Errorf("Provider Service调用失败: %w", err)
	}

	// 转换响应格式
	if len(response.Choices) == 0 {
		return nil, fmt.Errorf("Provider Service返回空响应")
	}

	choice := response.Choices[0]
	result := &ModelResponse{
		Content:    choice.Message.Content,
		Model:      response.Model,
		Provider:   c.getProviderFromModel(model),
		TokensUsed: response.Usage.TotalTokens,
		Cost:       c.calculateCost(response.Usage.TotalTokens),
		Metadata: map[string]interface{}{
			"provider_service": true,
			"request_id":       response.ID,
			"timestamp":        time.Now().Unix(),
			"prompt_tokens":    response.Usage.PromptTokens,
			"completion_tokens": response.Usage.CompletionTokens,
		},
	}

	log.Printf("Provider Service调用成功: tokens=%d, cost=%.6f", result.TokensUsed, result.Cost)

	return result, nil
}

// CallModelStream 通过Provider Service进行流式调用
func (c *ProviderClient) CallModelStream(ctx context.Context, model string, messages []Message, userID string, callback StreamCallback) error {
	// 转换消息格式
	providerMessages := make([]ProviderMessage, len(messages))
	for i, msg := range messages {
		providerMessages[i] = ProviderMessage{
			Role:    msg.Role,
			Content: msg.Content,
		}
	}

	// 构建流式请求
	request := ProviderChatRequest{
		Model:       model,
		Messages:    providerMessages,
		Stream:      true,
		MaxTokens:   4000,
		Temperature: 0.7,
		TopP:        1.0,
		User:        userID,
	}

	log.Printf("流式调用Provider Service: model=%s, messages=%d", model, len(messages))

	// 发送流式请求
	return c.sendStreamRequest(ctx, request, callback)
}

// sendChatRequest 发送聊天请求到Provider Service
func (c *ProviderClient) sendChatRequest(ctx context.Context, request ProviderChatRequest) (*ProviderChatResponse, error) {
	requestBody, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("序列化请求失败: %w", err)
	}

	// 创建HTTP请求
	req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/v1/chat/completions", bytes.NewBuffer(requestBody))
	if err != nil {
		return nil, fmt.Errorf("创建请求失败: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.getJWTToken()) // 需要JWT认证

	// 发送请求
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("发送请求失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Provider Service返回错误 %d: %s", resp.StatusCode, string(body))
	}

	// 解析响应
	var response ProviderChatResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}

	return &response, nil
}

// sendStreamRequest 发送流式请求到Provider Service
func (c *ProviderClient) sendStreamRequest(ctx context.Context, request ProviderChatRequest, callback StreamCallback) error {
	requestBody, err := json.Marshal(request)
	if err != nil {
		return fmt.Errorf("序列化请求失败: %w", err)
	}

	// 创建HTTP请求
	req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/v1/chat/completions", bytes.NewBuffer(requestBody))
	if err != nil {
		return fmt.Errorf("创建请求失败: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.getJWTToken())
	req.Header.Set("Accept", "text/event-stream")

	// 发送请求
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("发送请求失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("Provider Service返回错误 %d: %s", resp.StatusCode, string(body))
	}

	// 处理流式响应
	decoder := json.NewDecoder(resp.Body)
	chunkIndex := 0

	for {
		var streamResp ProviderStreamResponse
		if err := decoder.Decode(&streamResp); err != nil {
			if err == io.EOF {
				// 发送完成信号
				return callback(StreamChunk{
					Content:  "",
					Done:     true,
					Metadata: map[string]interface{}{
						"chunk_index": chunkIndex,
						"final":       true,
					},
				})
			}
			return fmt.Errorf("解析流式响应失败: %w", err)
		}

		if len(streamResp.Choices) > 0 {
			choice := streamResp.Choices[0]
			
			// 调用回调函数
			if err := callback(StreamChunk{
				Content: choice.Delta.Content,
				Done:    choice.FinishReason != "",
				Metadata: map[string]interface{}{
					"chunk_index":     chunkIndex,
					"provider_service": true,
					"request_id":      streamResp.ID,
					"timestamp":       time.Now().Unix(),
				},
			}); err != nil {
				return fmt.Errorf("流式回调失败: %w", err)
			}

			chunkIndex++

			// 如果收到完成信号，结束处理
			if choice.FinishReason != "" {
				break
			}
		}
	}

	return nil
}

// getJWTToken 获取JWT令牌（临时实现）
func (c *ProviderClient) getJWTToken() string {
	// TODO: 集成Auth Service获取真实JWT令牌
	return "mock-jwt-token"
}

// getProviderFromModel 根据模型名称推断供应商
func (c *ProviderClient) getProviderFromModel(model string) string {
	switch {
	case model == "gpt-3.5-turbo" || model == "gpt-4" || model == "gpt-4-turbo":
		return "openai"
	case model == "deepseek-chat" || model == "deepseek-coder":
		return "deepseek"
	case model == "claude-3" || model == "claude-3-sonnet":
		return "anthropic"
	default:
		return "unknown"
	}
}

// calculateCost 计算调用成本（简化实现）
func (c *ProviderClient) calculateCost(tokens int) float64 {
	// 简化的成本计算，实际应该根据不同模型和供应商定价
	return float64(tokens) * 0.0001
}

// ValidateModel 验证模型是否支持
func (c *ProviderClient) ValidateModel(model string) bool {
	supportedModels := []string{
		"gpt-3.5-turbo", "gpt-4", "gpt-4-turbo",
		"deepseek-chat", "deepseek-coder",
		"claude-3", "claude-3-sonnet",
	}
	
	for _, supportedModel := range supportedModels {
		if model == supportedModel {
			return true
		}
	}
	
	return false
}