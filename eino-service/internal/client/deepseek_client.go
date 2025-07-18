package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/sirupsen/logrus"
)

// DeepSeekClient DeepSeek API 客户端
type DeepSeekClient struct {
	apiKey     string
	baseURL    string
	httpClient *http.Client
	logger     *logrus.Logger
}

// DeepSeekRequest 聊天请求结构
type DeepSeekRequest struct {
	Model       string                 `json:"model"`
	Messages    []DeepSeekMessage      `json:"messages"`
	Temperature float64                `json:"temperature,omitempty"`
	MaxTokens   int                    `json:"max_tokens,omitempty"`
	Stream      bool                   `json:"stream,omitempty"`
	Stop        []string               `json:"stop,omitempty"`
	TopP        float64                `json:"top_p,omitempty"`
	TopK        int                    `json:"top_k,omitempty"`
	N           int                    `json:"n,omitempty"`
	User        string                 `json:"user,omitempty"`
	Extra       map[string]interface{} `json:"extra,omitempty"`
}

// DeepSeekMessage 消息结构
type DeepSeekMessage struct {
	Role    string `json:"role"`    // system, user, assistant
	Content string `json:"content"`
}

// DeepSeekResponse API 响应结构
type DeepSeekResponse struct {
	ID      string                 `json:"id"`
	Object  string                 `json:"object"`
	Created int64                  `json:"created"`
	Model   string                 `json:"model"`
	Choices []DeepSeekChoice       `json:"choices"`
	Usage   DeepSeekUsage          `json:"usage"`
	Error   *DeepSeekError         `json:"error,omitempty"`
	Extra   map[string]interface{} `json:"extra,omitempty"`
}

// DeepSeekChoice 选择结构
type DeepSeekChoice struct {
	Index        int               `json:"index"`
	Message      *DeepSeekMessage  `json:"message,omitempty"`
	Delta        *DeepSeekMessage  `json:"delta,omitempty"`
	FinishReason *string           `json:"finish_reason"`
	Logprobs     *DeepSeekLogprobs `json:"logprobs,omitempty"`
}

// DeepSeekLogprobs 日志概率结构
type DeepSeekLogprobs struct {
	Tokens        []string  `json:"tokens"`
	TokenLogprobs []float64 `json:"token_logprobs"`
	TopLogprobs   []map[string]float64 `json:"top_logprobs"`
}

// DeepSeekUsage 使用情况统计
type DeepSeekUsage struct {
	PromptTokens     int `json:"prompt_tokens"`
	CompletionTokens int `json:"completion_tokens"`
	TotalTokens      int `json:"total_tokens"`
}

// DeepSeekError 错误结构
type DeepSeekError struct {
	Message string `json:"message"`
	Type    string `json:"type"`
	Param   string `json:"param,omitempty"`
	Code    string `json:"code,omitempty"`
}

// DeepSeekStreamResponse 流式响应结构
type DeepSeekStreamResponse struct {
	ID      string           `json:"id"`
	Object  string           `json:"object"`
	Created int64            `json:"created"`
	Model   string           `json:"model"`
	Choices []DeepSeekChoice `json:"choices"`
	Usage   *DeepSeekUsage   `json:"usage,omitempty"`
	Error   *DeepSeekError   `json:"error,omitempty"`
}

// NewDeepSeekClient 创建DeepSeek客户端
func NewDeepSeekClient(apiKey, baseURL string, logger *logrus.Logger) *DeepSeekClient {
	if baseURL == "" {
		baseURL = "https://api.deepseek.com"
	}

	return &DeepSeekClient{
		apiKey:  apiKey,
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 60 * time.Second,
		},
		logger: logger,
	}
}

// ChatCompletion 发送聊天请求
func (c *DeepSeekClient) ChatCompletion(ctx context.Context, req *DeepSeekRequest) (*DeepSeekResponse, error) {
	startTime := time.Now()
	
	// 构建请求URL
	url := fmt.Sprintf("%s/chat/completions", c.baseURL)
	
	// 序列化请求体
	reqBody, err := json.Marshal(req)
	if err != nil {
		c.logger.WithError(err).Error("序列化DeepSeek请求失败")
		return nil, fmt.Errorf("序列化请求失败: %w", err)
	}

	// 创建HTTP请求
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(reqBody))
	if err != nil {
		c.logger.WithError(err).Error("创建HTTP请求失败")
		return nil, fmt.Errorf("创建请求失败: %w", err)
	}

	// 设置请求头
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	httpReq.Header.Set("User-Agent", "Lyss-EINO-Service/1.0.0")

	c.logger.WithFields(logrus.Fields{
		"url":           url,
		"model":         req.Model,
		"messages":      len(req.Messages),
		"temperature":   req.Temperature,
		"max_tokens":    req.MaxTokens,
		"stream":        req.Stream,
	}).Info("发送DeepSeek聊天请求")

	// 发送请求
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		c.logger.WithError(err).Error("发送DeepSeek请求失败")
		return nil, fmt.Errorf("请求失败: %w", err)
	}
	defer resp.Body.Close()

	// 读取响应体
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		c.logger.WithError(err).Error("读取DeepSeek响应失败")
		return nil, fmt.Errorf("读取响应失败: %w", err)
	}

	// 记录响应时间
	duration := time.Since(startTime)
	c.logger.WithFields(logrus.Fields{
		"status_code":     resp.StatusCode,
		"response_time_ms": duration.Milliseconds(),
		"response_size":   len(respBody),
	}).Info("DeepSeek请求完成")

	// 检查HTTP状态码
	if resp.StatusCode != http.StatusOK {
		var errorResp DeepSeekResponse
		if err := json.Unmarshal(respBody, &errorResp); err == nil && errorResp.Error != nil {
			c.logger.WithFields(logrus.Fields{
				"status_code":   resp.StatusCode,
				"error_type":    errorResp.Error.Type,
				"error_message": errorResp.Error.Message,
				"error_code":    errorResp.Error.Code,
			}).Error("DeepSeek API返回错误")
			return nil, fmt.Errorf("DeepSeek API错误 [%s]: %s", errorResp.Error.Type, errorResp.Error.Message)
		}
		
		c.logger.WithFields(logrus.Fields{
			"status_code": resp.StatusCode,
			"response":    string(respBody),
		}).Error("DeepSeek HTTP错误")
		return nil, fmt.Errorf("HTTP错误: %d", resp.StatusCode)
	}

	// 解析成功响应
	var deepSeekResp DeepSeekResponse
	if err := json.Unmarshal(respBody, &deepSeekResp); err != nil {
		c.logger.WithError(err).WithField("response", string(respBody)).Error("解析DeepSeek响应失败")
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}

	// 记录成功响应
	c.logger.WithFields(logrus.Fields{
		"response_id":    deepSeekResp.ID,
		"model":          deepSeekResp.Model,
		"choices":        len(deepSeekResp.Choices),
		"prompt_tokens":  deepSeekResp.Usage.PromptTokens,
		"completion_tokens": deepSeekResp.Usage.CompletionTokens,
		"total_tokens":   deepSeekResp.Usage.TotalTokens,
	}).Info("DeepSeek响应解析成功")

	return &deepSeekResp, nil
}

// ChatCompletionStream 发送流式聊天请求
func (c *DeepSeekClient) ChatCompletionStream(ctx context.Context, req *DeepSeekRequest) (<-chan *DeepSeekStreamResponse, error) {
	// 确保流式请求
	req.Stream = true
	
	// 构建请求URL
	url := fmt.Sprintf("%s/chat/completions", c.baseURL)
	
	// 序列化请求体
	reqBody, err := json.Marshal(req)
	if err != nil {
		c.logger.WithError(err).Error("序列化DeepSeek流式请求失败")
		return nil, fmt.Errorf("序列化请求失败: %w", err)
	}

	// 创建HTTP请求
	httpReq, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(reqBody))
	if err != nil {
		c.logger.WithError(err).Error("创建HTTP流式请求失败")
		return nil, fmt.Errorf("创建请求失败: %w", err)
	}

	// 设置请求头
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.apiKey))
	httpReq.Header.Set("User-Agent", "Lyss-EINO-Service/1.0.0")
	httpReq.Header.Set("Accept", "text/event-stream")

	c.logger.WithFields(logrus.Fields{
		"url":           url,
		"model":         req.Model,
		"messages":      len(req.Messages),
		"temperature":   req.Temperature,
		"max_tokens":    req.MaxTokens,
		"stream":        true,
	}).Info("发送DeepSeek流式聊天请求")

	// 发送请求
	resp, err := c.httpClient.Do(httpReq)
	if err != nil {
		c.logger.WithError(err).Error("发送DeepSeek流式请求失败")
		return nil, fmt.Errorf("请求失败: %w", err)
	}

	// 检查HTTP状态码
	if resp.StatusCode != http.StatusOK {
		defer resp.Body.Close()
		respBody, _ := io.ReadAll(resp.Body)
		c.logger.WithFields(logrus.Fields{
			"status_code": resp.StatusCode,
			"response":    string(respBody),
		}).Error("DeepSeek流式请求HTTP错误")
		return nil, fmt.Errorf("HTTP错误: %d", resp.StatusCode)
	}

	// 创建响应通道
	responseChan := make(chan *DeepSeekStreamResponse, 100)

	// 启动goroutine处理流式响应
	go func() {
		defer close(responseChan)
		defer resp.Body.Close()
		
		c.processStreamResponse(ctx, resp.Body, responseChan)
	}()

	return responseChan, nil
}

// processStreamResponse 处理流式响应
func (c *DeepSeekClient) processStreamResponse(ctx context.Context, body io.ReadCloser, responseChan chan<- *DeepSeekStreamResponse) {
	scanner := NewSSEScanner(body)
	
	for scanner.Scan() {
		select {
		case <-ctx.Done():
			c.logger.Info("DeepSeek流式响应被取消")
			return
		default:
		}

		line := scanner.Text()
		
		// 跳过空行和注释
		if line == "" || strings.HasPrefix(line, ":") {
			continue
		}

		// 解析SSE格式
		if strings.HasPrefix(line, "data: ") {
			data := strings.TrimPrefix(line, "data: ")
			
			// 检查结束标记
			if data == "[DONE]" {
				c.logger.Info("DeepSeek流式响应结束")
				return
			}

			// 解析JSON数据
			var streamResp DeepSeekStreamResponse
			if err := json.Unmarshal([]byte(data), &streamResp); err != nil {
				c.logger.WithError(err).WithField("data", data).Error("解析DeepSeek流式响应失败")
				continue
			}

			// 检查错误
			if streamResp.Error != nil {
				c.logger.WithFields(logrus.Fields{
					"error_type":    streamResp.Error.Type,
					"error_message": streamResp.Error.Message,
					"error_code":    streamResp.Error.Code,
				}).Error("DeepSeek流式响应错误")
				continue
			}

			// 发送响应到通道
			select {
			case responseChan <- &streamResp:
			case <-ctx.Done():
				return
			}
		}
	}

	if err := scanner.Err(); err != nil {
		c.logger.WithError(err).Error("读取DeepSeek流式响应出错")
	}
}

// TestConnection 测试连接
func (c *DeepSeekClient) TestConnection(ctx context.Context) error {
	// 创建简单的测试请求
	req := &DeepSeekRequest{
		Model: "deepseek-chat",
		Messages: []DeepSeekMessage{
			{
				Role:    "user",
				Content: "Hello, this is a connection test.",
			},
		},
		MaxTokens:   10,
		Temperature: 0.1,
		Stream:      false,
	}

	// 发送测试请求
	resp, err := c.ChatCompletion(ctx, req)
	if err != nil {
		c.logger.WithError(err).Error("DeepSeek连接测试失败")
		return fmt.Errorf("连接测试失败: %w", err)
	}

	// 检查响应
	if len(resp.Choices) == 0 {
		c.logger.Error("DeepSeek测试响应为空")
		return fmt.Errorf("测试响应为空")
	}

	c.logger.WithFields(logrus.Fields{
		"response_id":   resp.ID,
		"model":         resp.Model,
		"total_tokens":  resp.Usage.TotalTokens,
	}).Info("DeepSeek连接测试成功")

	return nil
}

// GetModels 获取可用模型列表
func (c *DeepSeekClient) GetModels(ctx context.Context) ([]string, error) {
	// DeepSeek的主要模型
	models := []string{
		"deepseek-chat",
		"deepseek-coder",
	}

	c.logger.WithField("models", models).Info("返回DeepSeek模型列表")
	return models, nil
}

// ValidateModel 验证模型名称
func (c *DeepSeekClient) ValidateModel(model string) bool {
	validModels := map[string]bool{
		"deepseek-chat":  true,
		"deepseek-coder": true,
	}

	return validModels[model]
}

// GetDefaultModel 获取默认模型
func (c *DeepSeekClient) GetDefaultModel() string {
	return "deepseek-chat"
}

// Close 关闭客户端
func (c *DeepSeekClient) Close() error {
	// DeepSeek客户端无需特殊关闭操作
	c.logger.Info("DeepSeek客户端已关闭")
	return nil
}