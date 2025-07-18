package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/url"
	"strings"

	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/config"
	"lyss-ai-platform/eino-service/internal/models"
)

// TenantClient 租户服务客户端
type TenantClient struct {
	baseURL    string
	httpClient *http.Client
	logger     *logrus.Logger
}

// NewTenantClient 创建新的租户服务客户端
func NewTenantClient(config *config.TenantServiceConfig, logger *logrus.Logger) *TenantClient {
	return &TenantClient{
		baseURL: config.BaseURL,
		httpClient: &http.Client{
			Timeout: config.Timeout,
		},
		logger: logger,
	}
}

// GetAvailableCredentials 获取可用凭证列表
func (c *TenantClient) GetAvailableCredentials(tenantID string, selector *models.CredentialSelector) ([]*models.SupplierCredential, error) {
	requestURL := fmt.Sprintf("%s/internal/suppliers/%s/available", c.baseURL, tenantID)
	
	// 构建查询参数
	params := url.Values{}
	if selector != nil {
		params.Add("strategy", selector.Strategy)
		params.Add("only_active", fmt.Sprintf("%t", selector.Filters.OnlyActive))
		if len(selector.Filters.Providers) > 0 {
			params.Add("providers", strings.Join(selector.Filters.Providers, ","))
		}
	}
	
	if len(params) > 0 {
		requestURL += "?" + params.Encode()
	}
	
	c.logger.WithFields(logrus.Fields{
		"tenant_id": tenantID,
		"url":       requestURL,
	}).Debug("获取可用凭证列表")
	
	resp, err := c.httpClient.Get(requestURL)
	if err != nil {
		return nil, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP状态码错误: %d", resp.StatusCode)
	}
	
	var apiResponse models.ApiResponse[[]*models.SupplierCredential]
	if err := json.NewDecoder(resp.Body).Decode(&apiResponse); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}
	
	if !apiResponse.Success {
		return nil, fmt.Errorf("API请求失败: %s", apiResponse.Message)
	}
	
	c.logger.WithFields(logrus.Fields{
		"tenant_id": tenantID,
		"count":     len(apiResponse.Data),
	}).Debug("获取可用凭证列表成功")
	
	return apiResponse.Data, nil
}

// TestCredential 测试凭证连接
func (c *TenantClient) TestCredential(credentialID string, testRequest *models.CredentialTestRequest) (bool, error) {
	url := fmt.Sprintf("%s/internal/suppliers/%s/test", c.baseURL, credentialID)
	
	reqBody, err := json.Marshal(testRequest)
	if err != nil {
		return false, fmt.Errorf("序列化请求失败: %w", err)
	}
	
	c.logger.WithFields(logrus.Fields{
		"credential_id": credentialID,
		"test_type":     testRequest.TestType,
	}).Debug("测试凭证连接")
	
	resp, err := c.httpClient.Post(url, "application/json", bytes.NewBuffer(reqBody))
	if err != nil {
		return false, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return false, fmt.Errorf("HTTP状态码错误: %d", resp.StatusCode)
	}
	
	var apiResponse models.ApiResponse[models.CredentialTestResponse]
	if err := json.NewDecoder(resp.Body).Decode(&apiResponse); err != nil {
		return false, fmt.Errorf("解析响应失败: %w", err)
	}
	
	if !apiResponse.Success {
		return false, fmt.Errorf("API请求失败: %s", apiResponse.Message)
	}
	
	c.logger.WithFields(logrus.Fields{
		"credential_id":    credentialID,
		"test_success":     apiResponse.Data.Success,
		"response_time_ms": apiResponse.Data.ResponseTimeMs,
	}).Debug("凭证连接测试完成")
	
	return apiResponse.Data.Success, nil
}

// GetActiveTenants 获取活跃租户列表
func (c *TenantClient) GetActiveTenants() ([]string, error) {
	url := fmt.Sprintf("%s/internal/tenants/active", c.baseURL)
	
	c.logger.Debug("获取活跃租户列表")
	
	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP状态码错误: %d", resp.StatusCode)
	}
	
	var apiResponse models.ApiResponse[[]string]
	if err := json.NewDecoder(resp.Body).Decode(&apiResponse); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}
	
	if !apiResponse.Success {
		return nil, fmt.Errorf("API请求失败: %s", apiResponse.Message)
	}
	
	c.logger.WithField("count", len(apiResponse.Data)).Debug("获取活跃租户列表成功")
	
	return apiResponse.Data, nil
}

// GetToolConfig 获取工具配置
func (c *TenantClient) GetToolConfig(tenantID, workflowName, toolName string) (*models.ToolConfig, error) {
	url := fmt.Sprintf("%s/internal/tool-configs/%s/%s/%s", c.baseURL, tenantID, workflowName, toolName)
	
	c.logger.WithFields(logrus.Fields{
		"tenant_id":     tenantID,
		"workflow_name": workflowName,
		"tool_name":     toolName,
	}).Debug("获取工具配置")
	
	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP状态码错误: %d", resp.StatusCode)
	}
	
	var apiResponse models.ApiResponse[models.ToolConfig]
	if err := json.NewDecoder(resp.Body).Decode(&apiResponse); err != nil {
		return nil, fmt.Errorf("解析响应失败: %w", err)
	}
	
	if !apiResponse.Success {
		return nil, fmt.Errorf("API请求失败: %s", apiResponse.Message)
	}
	
	c.logger.WithFields(logrus.Fields{
		"tenant_id":     tenantID,
		"workflow_name": workflowName,
		"tool_name":     toolName,
		"is_enabled":    apiResponse.Data.IsEnabled,
	}).Debug("获取工具配置成功")
	
	return &apiResponse.Data, nil
}

// HealthCheck 健康检查
func (c *TenantClient) HealthCheck(ctx context.Context) error {
	url := fmt.Sprintf("%s/health", c.baseURL)
	
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return fmt.Errorf("创建请求失败: %w", err)
	}
	
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("租户服务健康检查失败，状态码: %d", resp.StatusCode)
	}
	
	return nil
}