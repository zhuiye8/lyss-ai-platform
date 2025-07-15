package credential

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
	"github.com/sirupsen/logrus"

	"lyss-ai-platform/eino-service/internal/client"
	"lyss-ai-platform/eino-service/internal/config"
	"lyss-ai-platform/eino-service/internal/models"
)

// Manager 凭证管理器
type Manager struct {
	tenantClient   *client.TenantClient
	redisClient    *redis.Client
	cache          map[string]*models.SupplierCredential
	lastUsed       map[string]time.Time
	usage          map[string]int64
	healthStatus   map[string]bool
	mutex          sync.RWMutex
	config         *config.CredentialConfig
	logger         *logrus.Logger
	ctx            context.Context
	cancel         context.CancelFunc
}

// NewManager 创建新的凭证管理器
func NewManager(tenantClient *client.TenantClient, redisClient *redis.Client, config *config.CredentialConfig, logger *logrus.Logger) *Manager {
	ctx, cancel := context.WithCancel(context.Background())
	
	return &Manager{
		tenantClient: tenantClient,
		redisClient:  redisClient,
		cache:        make(map[string]*models.SupplierCredential),
		lastUsed:     make(map[string]time.Time),
		usage:        make(map[string]int64),
		healthStatus: make(map[string]bool),
		config:       config,
		logger:       logger,
		ctx:          ctx,
		cancel:       cancel,
	}
}

// Start 启动凭证管理器
func (m *Manager) Start() error {
	m.logger.Info("启动凭证管理器...")
	
	// 启动凭证预热
	if err := m.WarmUpCredentials(); err != nil {
		return fmt.Errorf("凭证预热失败: %w", err)
	}
	
	// 启动健康检查
	go m.startHealthCheck()
	
	m.logger.Info("凭证管理器启动成功")
	return nil
}

// Stop 停止凭证管理器
func (m *Manager) Stop() {
	m.logger.Info("停止凭证管理器...")
	m.cancel()
	m.logger.Info("凭证管理器已停止")
}

// GetBestCredentialForModel 获取最佳凭证
func (m *Manager) GetBestCredentialForModel(tenantID, provider, modelName string) (*models.SupplierCredential, error) {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	
	// 1. 检查缓存
	cacheKey := fmt.Sprintf("%s:%s", tenantID, provider)
	if cached, exists := m.cache[cacheKey]; exists {
		if time.Since(cached.UpdatedAt) < m.config.CacheTTL && m.healthStatus[cached.ID.String()] {
			return cached, nil
		}
	}
	
	// 2. 从租户服务获取凭证
	credentials, err := m.tenantClient.GetAvailableCredentials(tenantID, &models.CredentialSelector{
		Strategy: "least_used",
		Filters: struct {
			OnlyActive bool     `json:"only_active"`
			Providers  []string `json:"providers"`
		}{
			OnlyActive: true,
			Providers:  []string{provider},
		},
	})
	
	if err != nil {
		return nil, fmt.Errorf("获取凭证失败: %w", err)
	}
	
	if len(credentials) == 0 {
		return nil, fmt.Errorf("没有找到可用的 %s 凭证", provider)
	}
	
	// 3. 选择最佳凭证
	best := m.selectBestCredential(credentials, modelName)
	
	// 4. 更新缓存
	m.cache[cacheKey] = best
	
	return best, nil
}

// selectBestCredential 选择最佳凭证
func (m *Manager) selectBestCredential(credentials []*models.SupplierCredential, modelName string) *models.SupplierCredential {
	var best *models.SupplierCredential
	var bestScore float64
	
	for _, cred := range credentials {
		score := m.calculateCredentialScore(cred, modelName)
		if best == nil || score > bestScore {
			best = cred
			bestScore = score
		}
	}
	
	return best
}

// calculateCredentialScore 计算凭证评分
func (m *Manager) calculateCredentialScore(cred *models.SupplierCredential, modelName string) float64 {
	score := 100.0
	
	// 1. 健康状态权重 (40%)
	if !m.healthStatus[cred.ID.String()] {
		score -= 40
	}
	
	// 2. 使用频率权重 (30%) - 负载均衡
	usageCount := m.usage[cred.ID.String()]
	if usageCount > 0 {
		score -= float64(usageCount) * 0.1
	}
	
	// 3. 最后使用时间权重 (20%) - 避免冷启动
	if lastUsed, exists := m.lastUsed[cred.ID.String()]; exists {
		timeSinceUsed := time.Since(lastUsed).Minutes()
		if timeSinceUsed > 60 { // 超过1小时未使用，减分
			score -= timeSinceUsed * 0.1
		}
	}
	
	// 4. 模型配置匹配度权重 (10%)
	if modelConfigs, ok := cred.ModelConfigs[modelName]; ok {
		if modelConfigs != nil {
			score += 10
		}
	}
	
	return score
}

// RecordUsage 记录凭证使用情况
func (m *Manager) RecordUsage(credentialID string) {
	m.mutex.Lock()
	defer m.mutex.Unlock()
	
	m.usage[credentialID]++
	m.lastUsed[credentialID] = time.Now()
	
	// 异步更新Redis统计
	go func() {
		key := fmt.Sprintf("credential_usage:%s", credentialID)
		m.redisClient.Incr(m.ctx, key)
		m.redisClient.Expire(m.ctx, key, 24*time.Hour)
	}()
}

// WarmUpCredentials 预热凭证
func (m *Manager) WarmUpCredentials() error {
	m.logger.Info("开始凭证预热...")
	
	// 获取活跃租户列表
	tenantIDs, err := m.tenantClient.GetActiveTenants()
	if err != nil {
		return fmt.Errorf("获取活跃租户列表失败: %w", err)
	}
	
	// 为每个租户预热凭证
	for _, tenantID := range tenantIDs {
		if err := m.warmUpTenantCredentials(tenantID); err != nil {
			m.logger.WithError(err).WithField("tenant_id", tenantID).Error("租户凭证预热失败")
		}
	}
	
	m.logger.WithField("tenant_count", len(tenantIDs)).Info("凭证预热完成")
	return nil
}

// warmUpTenantCredentials 预热单个租户的凭证
func (m *Manager) warmUpTenantCredentials(tenantID string) error {
	providers := []string{"openai", "anthropic", "deepseek", "google", "azure"}
	
	for _, provider := range providers {
		credentials, err := m.tenantClient.GetAvailableCredentials(tenantID, &models.CredentialSelector{
			Strategy: "first_available",
			Filters: struct {
				OnlyActive bool     `json:"only_active"`
				Providers  []string `json:"providers"`
			}{
				OnlyActive: true,
				Providers:  []string{provider},
			},
		})
		
		if err != nil {
			continue
		}
		
		for _, cred := range credentials {
			cacheKey := fmt.Sprintf("%s:%s", tenantID, provider)
			
			m.mutex.Lock()
			m.cache[cacheKey] = cred
			m.usage[cred.ID.String()] = 0
			m.lastUsed[cred.ID.String()] = time.Now()
			m.mutex.Unlock()
			
			// 异步健康检查
			go m.testCredentialHealth(cred)
		}
	}
	
	return nil
}

// testCredentialHealth 测试凭证健康状态
func (m *Manager) testCredentialHealth(cred *models.SupplierCredential) {
	healthy, err := m.tenantClient.TestCredential(cred.ID.String(), &models.CredentialTestRequest{
		TenantID:  cred.TenantID.String(),
		TestType:  "connection",
		ModelName: "default",
	})
	
	if err != nil {
		m.logger.WithError(err).WithField("credential_id", cred.ID.String()).Error("凭证健康检查失败")
		healthy = false
	}
	
	m.mutex.Lock()
	m.healthStatus[cred.ID.String()] = healthy
	m.mutex.Unlock()
	
	if healthy {
		m.logger.WithFields(logrus.Fields{
			"credential_id": cred.ID.String(),
			"provider":      cred.Provider,
			"display_name":  cred.DisplayName,
		}).Info("凭证健康检查通过")
	} else {
		m.logger.WithFields(logrus.Fields{
			"credential_id": cred.ID.String(),
			"provider":      cred.Provider,
			"display_name":  cred.DisplayName,
		}).Warning("凭证健康检查失败")
	}
}

// startHealthCheck 启动健康检查
func (m *Manager) startHealthCheck() {
	ticker := time.NewTicker(m.config.HealthCheckInterval)
	defer ticker.Stop()
	
	for {
		select {
		case <-m.ctx.Done():
			return
		case <-ticker.C:
			m.performHealthCheck()
		}
	}
}

// performHealthCheck 执行健康检查
func (m *Manager) performHealthCheck() {
	m.mutex.RLock()
	credentials := make([]*models.SupplierCredential, 0, len(m.cache))
	for _, cred := range m.cache {
		credentials = append(credentials, cred)
	}
	m.mutex.RUnlock()
	
	for _, cred := range credentials {
		go m.testCredentialHealth(cred)
	}
}

// GetCredentialStats 获取凭证统计信息
func (m *Manager) GetCredentialStats() map[string]interface{} {
	m.mutex.RLock()
	defer m.mutex.RUnlock()
	
	stats := map[string]interface{}{
		"total_credentials":  len(m.cache),
		"healthy_credentials": func() int {
			count := 0
			for _, healthy := range m.healthStatus {
				if healthy {
					count++
				}
			}
			return count
		}(),
		"total_usage": func() int64 {
			var total int64
			for _, count := range m.usage {
				total += count
			}
			return total
		}(),
		"cache_size": len(m.cache),
	}
	
	return stats
}