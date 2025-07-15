# EINO Service 规范文档

## 🎯 服务概述

EINO Service 是 Lyss AI Platform 的**AI工作流编排核心**，基于字节跳动EINO框架构建，负责执行复杂的多步骤AI任务编排。本服务采用Go语言实现，提供高性能的AI工作流执行引擎。

## 📋 核心职责

### ✅ 负责的功能
1. **AI工作流编排**: 执行复杂的多模型协作工作流
2. **供应商抽象**: 统一封装OpenAI、Anthropic、Google等AI供应商
3. **流式响应处理**: 实现AI模型的实时流式输出
4. **工具节点管理**: 动态启用/禁用工具节点（如网络搜索、数据库查询）
5. **记忆集成**: 与Memory Service集成实现上下文感知对话
6. **执行状态跟踪**: 记录和管理工作流执行状态

### ❌ 不负责的功能
- 用户认证和权限管理（由Auth Service和API Gateway负责）
- 供应商凭证的存储和管理（由Tenant Service负责）
- 对话记忆的持久化存储（由Memory Service负责）
- 用户和租户数据管理（由Tenant Service负责）

## 🏗️ 工作流设计架构

### 🔥 静态为主，可配为辅的设计理念

**核心工作流图结构在Go代码中静态定义**，确保核心体验的稳定可靠。通过数据库配置实现工具节点的动态启用/禁用，提供必要的灵活性。

### 预定义核心工作流

#### 1. SimpleChat - 基础对话工作流
```go
// 静态定义的简单对话工作流
func buildSimpleChatGraph() *compose.Graph[map[string]any, *schema.Message] {
    g := compose.NewGraph[map[string]any, *schema.Message]()
    
    const (
        nodeMemoryRetrieval = "MemoryRetrieval"  // 记忆检索
        nodeChatModel      = "ChatModel"         // 主对话模型
        nodeMemoryStorage  = "MemoryStorage"     // 记忆存储
    )
    
    // 1. 记忆检索节点（可选）
    memoryRetrievalNode := chat.NewMemoryRetrievalNode(memoryService)
    g.AddNode(nodeMemoryRetrieval, memoryRetrievalNode)
    
    // 2. 主对话模型
    chatModel := chat.NewChatModel(getChatModelForTenant())
    g.AddChatModelNode(nodeChatModel, chatModel)
    
    // 3. 记忆存储节点（可选）
    memoryStorageNode := chat.NewMemoryStorageNode(memoryService)
    g.AddNode(nodeMemoryStorage, memoryStorageNode)
    
    // 定义执行流
    g.AddEdge(compose.NewEdge(compose.GraphInput, 0, nodeMemoryRetrieval, 0))
    g.AddEdge(compose.NewEdge(nodeMemoryRetrieval, 0, nodeChatModel, 0))
    g.AddEdge(compose.NewEdge(nodeChatModel, 0, nodeMemoryStorage, 0))
    g.AddEdge(compose.NewEdge(nodeMemoryStorage, 0, compose.GraphOutput, 0))
    
    return g
}
```

#### 2. OptimizedRAG - 优化检索增强生成工作流
```go
// 静态定义的优化RAG工作流
func buildOptimizedRAGGraph() *compose.Graph[map[string]any, *schema.Message] {
    g := compose.NewGraph[map[string]any, *schema.Message]()
    
    const (
        nodePromptOptimizer  = "PromptOptimizer"   // 提示词优化
        nodeMemoryRetrieval  = "MemoryRetrieval"   // 记忆检索  
        nodeCoreResponder    = "CoreResponder"     // 核心回答器
        nodeToolSelector     = "ToolSelector"      // 工具选择器
        nodeWebSearch        = "WebSearchTool"     // 网络搜索（可配）
        nodeDbQuery          = "DatabaseTool"      // 数据库查询（可配）
        nodeFinalSynthesizer = "FinalSynthesizer"  // 最终合成器
        nodeMemoryStorage    = "MemoryStorage"     // 记忆存储
    )
    
    // 节点定义
    g.AddChatModelNode(nodePromptOptimizer, getSmallModel())    // 小模型优化提示
    g.AddNode(nodeMemoryRetrieval, newMemoryRetrievalNode())
    g.AddChatModelNode(nodeCoreResponder, getLargeModel())      // 大模型生成回答
    g.AddChatModelNode(nodeToolSelector, getFunctionModel())   // 函数调用模型
    g.AddToolsNode(nodeWebSearch, newWebSearchTool())          // 🔧 可配置工具
    g.AddToolsNode(nodeDbQuery, newDatabaseTool())             // 🔧 可配置工具  
    g.AddChatModelNode(nodeFinalSynthesizer, getSynthesisModel())
    g.AddNode(nodeMemoryStorage, newMemoryStorageNode())
    
    // 核心流程定义
    g.AddEdge(compose.NewEdge(compose.GraphInput, 0, nodePromptOptimizer, 0))
    g.AddEdge(compose.NewEdge(nodePromptOptimizer, 0, nodeMemoryRetrieval, 0))
    g.AddEdge(compose.NewEdge(nodeMemoryRetrieval, 0, nodeCoreResponder, 0))
    g.AddEdge(compose.NewEdge(nodeCoreResponder, 0, nodeToolSelector, 0))
    
    // 🔧 动态工具路由（运行时检查配置）
    g.AddConditionalEdge(nodeToolSelector, func(state map[string]any) string {
        if shouldEnableTool(state["tenant_id"], "optimized_rag", "web_search") {
            return nodeWebSearch
        }
        if shouldEnableTool(state["tenant_id"], "optimized_rag", "database_query") {
            return nodeDbQuery
        }
        return nodeFinalSynthesizer
    })
    
    g.AddEdge(compose.NewEdge(nodeWebSearch, 0, nodeFinalSynthesizer, 0))
    g.AddEdge(compose.NewEdge(nodeDbQuery, 0, nodeFinalSynthesizer, 0))
    g.AddEdge(compose.NewEdge(nodeFinalSynthesizer, 0, nodeMemoryStorage, 0))
    g.AddEdge(compose.NewEdge(nodeMemoryStorage, 0, compose.GraphOutput, 0))
    
    return g
}
```

### 🔧 动态工具配置机制

#### 工具配置查询逻辑
```go
type ToolConfig struct {
    TenantID     string `json:"tenant_id"`
    WorkflowName string `json:"workflow_name"`
    ToolName     string `json:"tool_node_name"`
    IsEnabled    bool   `json:"is_enabled"`
    ConfigParams map[string]interface{} `json:"config_params"`
}

// 查询租户的工具配置
func shouldEnableTool(tenantID, workflowName, toolName string) bool {
    config, err := tenantServiceClient.GetToolConfig(tenantID, workflowName, toolName)
    if err != nil {
        // 默认启用策略
        return true
    }
    return config.IsEnabled
}

// 在工作流执行前查询所有工具配置
func loadTenantToolConfigs(tenantID, workflowName string) map[string]ToolConfig {
    configs, err := tenantServiceClient.GetAllToolConfigs(tenantID, workflowName)
    if err != nil {
        log.Printf("Failed to load tool configs: %v", err)
        return make(map[string]ToolConfig)
    }
    
    configMap := make(map[string]ToolConfig)
    for _, config := range configs {
        configMap[config.ToolName] = config
    }
    return configMap
}
```

## 🧠 记忆集成机制

### 记忆开关检查逻辑

在调用Memory Service之前，必须检查用户的`active_memory_enabled`标志：

```go
type UserPreferences struct {
    UserID              string `json:"user_id"`
    ActiveMemoryEnabled bool   `json:"active_memory_enabled"`
    PreferredLanguage   string `json:"preferred_language"`
    AIModelPreferences  map[string]interface{} `json:"ai_model_preferences"`
}

// 记忆检索节点实现
func (n *MemoryRetrievalNode) Execute(ctx context.Context, input map[string]any) (map[string]any, error) {
    userID := input["user_id"].(string)
    tenantID := input["tenant_id"].(string)
    
    // 🔍 检查用户记忆开关
    prefs, err := tenantServiceClient.GetUserPreferences(userID, tenantID)
    if err != nil || !prefs.ActiveMemoryEnabled {
        log.Printf("Memory disabled for user %s, skipping retrieval", userID)
        return input, nil // 跳过记忆检索
    }
    
    // 执行记忆检索
    query := input["message"].(string)
    memories, err := memoryServiceClient.SearchMemories(userID, query)
    if err != nil {
        log.Printf("Memory search failed: %v", err)
        return input, nil
    }
    
    // 将检索到的记忆添加到上下文
    input["retrieved_memories"] = memories
    return input, nil
}

// 记忆存储节点实现  
func (n *MemoryStorageNode) Execute(ctx context.Context, input map[string]any) (map[string]any, error) {
    userID := input["user_id"].(string)
    tenantID := input["tenant_id"].(string)
    
    // 🔍 检查用户记忆开关
    prefs, err := tenantServiceClient.GetUserPreferences(userID, tenantID)
    if err != nil || !prefs.ActiveMemoryEnabled {
        log.Printf("Memory disabled for user %s, skipping storage", userID)
        return input, nil // 跳过记忆存储
    }
    
    // 异步存储对话记忆
    go func() {
        conversation := buildConversationFromInput(input)
        err := memoryServiceClient.AddMemory(userID, conversation)
        if err != nil {
            log.Printf("Failed to store memory: %v", err)
        }
    }()
    
    return input, nil
}
```

## 🔄 需要Tenant Service实现的内部接口

**重要提醒**：为了支持EINO服务的智能凭证管理，Tenant Service需要实现以下内部接口：

### 1. 获取可用凭证列表
```http
GET /internal/suppliers/{tenant_id}/available?strategy=least_used&only_active=true&providers=openai,deepseek
```

### 2. 凭证连接测试
```http
POST /internal/suppliers/{credential_id}/test
Content-Type: application/json

{
  "tenant_id": "tenant-uuid",
  "test_type": "connection"
}
```

### 3. 工具配置管理
```http
GET /internal/tool-configs/{tenant_id}/{workflow_name}/{tool_name}
```

**这些接口需要在Tenant Service中实现，用于EINO服务的凭证管理和工具配置。**

---

## 📡 对外API接口

### 1. 简单对话接口
```http
POST /api/v1/chat/simple
Content-Type: application/json
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-Request-ID: {request_id}
```

**请求体:**
```json
{
  "message": "请解释一下机器学习的基本概念",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": false
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "id": "exec-uuid",
    "content": "机器学习是人工智能的一个分支...",
    "model": "gpt-4",
    "workflow_type": "simple_chat",
    "execution_time_ms": 1250,
    "usage": {
      "prompt_tokens": 45,
      "completion_tokens": 312,
      "total_tokens": 357
    }
  },
  "request_id": "req-20250710143025-a1b2c3d4"
}
```

### 2. 流式对话接口
```http
POST /api/v1/chat/stream
Content-Type: application/json
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-Request-ID: {request_id}
```

**流式响应 (Server-Sent Events):**
```
data: {"type":"start","execution_id":"exec-uuid"}

data: {"type":"chunk","content":"机器学习","delta":"机器学习"}

data: {"type":"chunk","content":"机器学习是","delta":"是"}

data: {"type":"end","usage":{"total_tokens":357},"execution_time_ms":1250}
```

### 3. 优化RAG接口
```http
POST /api/v1/chat/rag
Content-Type: application/json
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-Request-ID: {request_id}
```

**请求体:**
```json
{
  "query": "最新的AI技术发展趋势是什么？",
  "enable_web_search": true,
  "enable_memory": true,
  "model_config": {
    "optimizer_model": "gpt-4o-mini",
    "core_model": "gpt-4",
    "synthesizer_model": "gpt-4"
  }
}
```

### 4. 工作流状态查询
```http
GET /api/v1/executions/{execution_id}
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "execution_id": "exec-uuid",
    "workflow_type": "optimized_rag",
    "status": "completed",
    "progress": 100,
    "steps": [
      {
        "node": "PromptOptimizer",
        "status": "completed",
        "duration_ms": 245
      },
      {
        "node": "CoreResponder", 
        "status": "completed",
        "duration_ms": 1105
      }
    ],
    "total_duration_ms": 1350
  }
}
```

## 🔧 服务间集成

### Tenant Service集成（增强版凭证管理）
```go
type TenantServiceClient struct {
    baseURL string
    client  *http.Client
}

// 增强的供应商凭证结构
type SupplierCredential struct {
    ID           string                 `json:"id"`
    TenantID     string                 `json:"tenant_id"`
    Provider     string                 `json:"provider_name"`
    DisplayName  string                 `json:"display_name"`
    APIKey       string                 `json:"api_key"`
    BaseURL      string                 `json:"base_url"`
    ModelConfigs map[string]interface{} `json:"model_configs"`
    IsActive     bool                   `json:"is_active"`
    CreatedAt    time.Time              `json:"created_at"`
    UpdatedAt    time.Time              `json:"updated_at"`
}

// 凭证选择策略
type CredentialSelector struct {
    Strategy string `json:"strategy"` // "first_available", "round_robin", "least_used"
    Filters  struct {
        OnlyActive bool     `json:"only_active"`
        Providers  []string `json:"providers"`
    } `json:"filters"`
}

// 获取租户的所有可用凭证
func (c *TenantServiceClient) GetAvailableCredentials(tenantID string, selector *CredentialSelector) ([]*SupplierCredential, error) {
    url := fmt.Sprintf("%s/internal/suppliers/%s/available", c.baseURL, tenantID)
    
    // 构建查询参数
    req, err := http.NewRequest("GET", url, nil)
    if err != nil {
        return nil, fmt.Errorf("failed to create request: %w", err)
    }
    
    q := req.URL.Query()
    if selector != nil {
        q.Add("strategy", selector.Strategy)
        q.Add("only_active", fmt.Sprintf("%t", selector.Filters.OnlyActive))
        if len(selector.Filters.Providers) > 0 {
            q.Add("providers", strings.Join(selector.Filters.Providers, ","))
        }
    }
    req.URL.RawQuery = q.Encode()
    
    resp, err := c.client.Do(req)
    if err != nil {
        return nil, fmt.Errorf("failed to get available credentials: %w", err)
    }
    defer resp.Body.Close()
    
    var result struct {
        Success bool                  `json:"success"`
        Data    []*SupplierCredential `json:"data"`
    }
    
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, fmt.Errorf("failed to decode credentials: %w", err)
    }
    
    return result.Data, nil
}

// 获取特定供应商的最佳凭证
func (c *TenantServiceClient) GetBestCredential(tenantID, provider string) (*SupplierCredential, error) {
    selector := &CredentialSelector{
        Strategy: "first_available",
        Filters: struct {
            OnlyActive bool     `json:"only_active"`
            Providers  []string `json:"providers"`
        }{
            OnlyActive: true,
            Providers:  []string{provider},
        },
    }
    
    credentials, err := c.GetAvailableCredentials(tenantID, selector)
    if err != nil {
        return nil, fmt.Errorf("failed to get credentials: %w", err)
    }
    
    if len(credentials) == 0 {
        return nil, fmt.Errorf("no available credentials for provider %s", provider)
    }
    
    return credentials[0], nil
}

// 测试凭证连接性
func (c *TenantServiceClient) TestCredential(credentialID, tenantID string) (bool, error) {
    url := fmt.Sprintf("%s/internal/suppliers/%s/test", c.baseURL, credentialID)
    
    reqBody := map[string]interface{}{
        "tenant_id": tenantID,
        "test_type": "connection",
    }
    
    bodyBytes, err := json.Marshal(reqBody)
    if err != nil {
        return false, fmt.Errorf("failed to marshal request: %w", err)
    }
    
    resp, err := c.client.Post(url, "application/json", bytes.NewBuffer(bodyBytes))
    if err != nil {
        return false, fmt.Errorf("failed to test credential: %w", err)
    }
    defer resp.Body.Close()
    
    var result struct {
        Success bool `json:"success"`
        Data    struct {
            Success bool `json:"success"`
        } `json:"data"`
    }
    
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return false, fmt.Errorf("failed to decode test result: %w", err)
    }
    
    return result.Success && result.Data.Success, nil
}

// 获取工具配置
func (c *TenantServiceClient) GetToolConfig(tenantID, workflow, tool string) (*ToolConfig, error) {
    url := fmt.Sprintf("%s/internal/tool-configs/%s/%s/%s", c.baseURL, tenantID, workflow, tool)
    
    resp, err := c.client.Get(url)
    if err != nil {
        return nil, fmt.Errorf("failed to get tool config: %w", err)
    }
    defer resp.Body.Close()
    
    var config ToolConfig
    if err := json.NewDecoder(resp.Body).Decode(&config); err != nil {
        return nil, fmt.Errorf("failed to decode tool config: %w", err)
    }
    
    return &config, nil
}
```

### Memory Service集成
```go
type MemoryServiceClient struct {
    baseURL string
    client  *http.Client
}

// 搜索相关记忆
func (c *MemoryServiceClient) SearchMemories(userID, query string) ([]Memory, error) {
    requestBody := map[string]interface{}{
        "user_id": userID,
        "query":   query,
        "limit":   5
    }
    
    // 实现HTTP调用逻辑
}

// 添加新记忆
func (c *MemoryServiceClient) AddMemory(userID string, conversation Conversation) error {
    requestBody := map[string]interface{}{
        "user_id":      userID,
        "messages":     conversation.Messages,
        "context":      conversation.Context,
    }
    
    // 实现HTTP调用逻辑
}
```

## 🏗️ 数据模型设计

### 工作流执行状态表 (EINO Service专有)
```sql
CREATE TABLE workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL, 
    workflow_type VARCHAR(50) NOT NULL,
    input_data JSONB NOT NULL,
    output_data JSONB,
    status VARCHAR(20) DEFAULT 'running', -- 'running', 'completed', 'failed'
    progress INTEGER DEFAULT 0,
    steps JSONB DEFAULT '[]',
    execution_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 智能供应商凭证管理器
```go
type CredentialManager struct {
    tenantClient   *TenantServiceClient
    cache          map[string]*SupplierCredential
    lastUsed       map[string]time.Time
    usage          map[string]int64
    healthStatus   map[string]bool
    mutex          sync.RWMutex
    ttl            time.Duration
}

type ModelConfig struct {
    TenantID       string                 `json:"tenant_id"`
    Provider       string                 `json:"provider"`
    ModelName      string                 `json:"model_name"`
    Credential     *SupplierCredential    `json:"credential"`
    ModelParams    map[string]interface{} `json:"model_params"`
    CachedAt       time.Time              `json:"cached_at"`
    LastHealthCheck time.Time             `json:"last_health_check"`
}

// 智能凭证选择器
func (cm *CredentialManager) GetBestCredentialForModel(tenantID, provider, modelName string) (*SupplierCredential, error) {
    cm.mutex.RLock()
    defer cm.mutex.RUnlock()
    
    // 1. 从缓存中获取可用凭证
    cacheKey := fmt.Sprintf("%s:%s", tenantID, provider)
    if cached, exists := cm.cache[cacheKey]; exists {
        if time.Since(cached.UpdatedAt) < cm.ttl && cm.healthStatus[cached.ID] {
            return cached, nil
        }
    }
    
    // 2. 从Tenant Service获取所有可用凭证
    credentials, err := cm.tenantClient.GetAvailableCredentials(tenantID, &CredentialSelector{
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
        return nil, fmt.Errorf("failed to get credentials: %w", err)
    }
    
    if len(credentials) == 0 {
        return nil, fmt.Errorf("no available credentials for provider %s", provider)
    }
    
    // 3. 应用智能选择策略
    best := cm.selectBestCredential(credentials, modelName)
    
    // 4. 更新缓存
    cm.cache[cacheKey] = best
    
    return best, nil
}

// 智能凭证选择策略
func (cm *CredentialManager) selectBestCredential(credentials []*SupplierCredential, modelName string) *SupplierCredential {
    var best *SupplierCredential
    var bestScore float64
    
    for _, cred := range credentials {
        score := cm.calculateCredentialScore(cred, modelName)
        if best == nil || score > bestScore {
            best = cred
            bestScore = score
        }
    }
    
    return best
}

// 凭证评分算法
func (cm *CredentialManager) calculateCredentialScore(cred *SupplierCredential, modelName string) float64 {
    score := 100.0
    
    // 1. 健康状态权重 (40%)
    if !cm.healthStatus[cred.ID] {
        score -= 40
    }
    
    // 2. 使用频率权重 (30%) - 负载均衡
    usageCount := cm.usage[cred.ID]
    if usageCount > 0 {
        score -= float64(usageCount) * 0.1
    }
    
    // 3. 最后使用时间权重 (20%) - 避免冷启动
    if lastUsed, exists := cm.lastUsed[cred.ID]; exists {
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

// 凭证健康检查
func (cm *CredentialManager) healthCheck(ctx context.Context) {
    cm.mutex.RLock()
    credentials := make([]*SupplierCredential, 0, len(cm.cache))
    for _, cred := range cm.cache {
        credentials = append(credentials, cred)
    }
    cm.mutex.RUnlock()
    
    for _, cred := range credentials {
        go func(c *SupplierCredential) {
            healthy, err := cm.tenantClient.TestCredential(c.ID, c.TenantID)
            if err != nil {
                log.Printf("健康检查失败: %s - %v", c.ID, err)
                healthy = false
            }
            
            cm.mutex.Lock()
            cm.healthStatus[c.ID] = healthy
            cm.mutex.Unlock()
            
            if healthy {
                log.Printf("凭证 %s (%s) 健康检查通过", c.DisplayName, c.Provider)
            } else {
                log.Printf("凭证 %s (%s) 健康检查失败", c.DisplayName, c.Provider)
            }
        }(cred)
    }
}

// 记录凭证使用情况
func (cm *CredentialManager) RecordUsage(credentialID string) {
    cm.mutex.Lock()
    defer cm.mutex.Unlock()
    
    cm.usage[credentialID]++
    cm.lastUsed[credentialID] = time.Now()
}

// 启动后台健康检查
func (cm *CredentialManager) StartHealthCheck(ctx context.Context, interval time.Duration) {
    ticker := time.NewTicker(interval)
    defer ticker.Stop()
    
    for {
        select {
        case <-ctx.Done():
            return
        case <-ticker.C:
            cm.healthCheck(ctx)
        }
    }
}
```

## 📝 日志规范

### 工作流执行日志
```json
{
  "timestamp": "2025-07-10T10:30:00Z",
  "level": "INFO",
  "service": "eino_service",
  "request_id": "req-20250710143025-a1b2c3d4",
  "execution_id": "exec-uuid",
  "tenant_id": "tenant-uuid",
  "user_id": "user-uuid",
  "workflow_type": "optimized_rag",
  "node": "CoreResponder",
  "operation": "model_call",
  "model": "gpt-4",
  "provider": "openai",
  "duration_ms": 1105,
  "tokens_used": 357,
  "success": true,
  "message": "模型调用完成"
}
```

### 工具执行日志
```json
{
  "timestamp": "2025-07-10T10:30:00Z",
  "level": "INFO", 
  "service": "eino_service",
  "request_id": "req-20250710143025-a1b2c3d4",
  "execution_id": "exec-uuid",
  "tenant_id": "tenant-uuid",
  "workflow_type": "optimized_rag",
  "node": "WebSearchTool",
  "operation": "tool_execution",
  "tool_enabled": true,
  "search_query": "AI技术趋势2025",
  "results_count": 5,
  "duration_ms": 850,
  "message": "网络搜索工具执行完成"
}
```

## 🔒 安全和配置

### 环境变量配置
```bash
# 服务配置
PORT=8003
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30s

# 依赖服务
TENANT_SERVICE_URL=http://localhost:8002
MEMORY_SERVICE_URL=http://localhost:8004

# 模型配置缓存
MODEL_CONFIG_CACHE_TTL=300s
MAX_CONCURRENT_EXECUTIONS=100

# AI供应商默认配置
DEFAULT_MODEL_TIMEOUT=30s
MAX_TOKENS_PER_REQUEST=8192
```

### 供应商API密钥安全
```go
// API密钥在内存中的安全处理
type SecureCredential struct {
    encryptedKey []byte
    iv          []byte
}

func (c *SecureCredential) Decrypt() (string, error) {
    // 实现内存中的临时解密
    // 使用完立即清零内存
}

// 确保API密钥不会出现在日志中
func sanitizeLogData(data map[string]interface{}) map[string]interface{} {
    sanitized := make(map[string]interface{})
    for k, v := range data {
        if strings.Contains(strings.ToLower(k), "key") || 
           strings.Contains(strings.ToLower(k), "token") ||
           strings.Contains(strings.ToLower(k), "secret") {
            sanitized[k] = "***masked***"
        } else {
            sanitized[k] = v
        }
    }
    return sanitized
}
```

## 🚀 服务启动和凭证同步

### 启动时凭证预热机制

```go
// 服务启动时的凭证预热
func (cm *CredentialManager) WarmUpCredentials(ctx context.Context) error {
    log.Printf("开始凭证预热...")
    
    // 1. 获取所有租户列表（从配置或数据库）
    tenants, err := cm.loadActiveTenants()
    if err != nil {
        return fmt.Errorf("加载租户列表失败: %w", err)
    }
    
    // 2. 为每个租户预热凭证
    for _, tenantID := range tenants {
        go func(tid string) {
            if err := cm.warmUpTenantCredentials(ctx, tid); err != nil {
                log.Printf("租户 %s 凭证预热失败: %v", tid, err)
            }
        }(tenantID)
    }
    
    log.Printf("凭证预热完成，共处理 %d 个租户", len(tenants))
    return nil
}

// 单个租户凭证预热
func (cm *CredentialManager) warmUpTenantCredentials(ctx context.Context, tenantID string) error {
    // 获取所有支持的供应商
    providers := []string{"openai", "anthropic", "deepseek", "google", "azure"}
    
    for _, provider := range providers {
        credentials, err := cm.tenantClient.GetAvailableCredentials(tenantID, &CredentialSelector{
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
            log.Printf("获取租户 %s 的 %s 凭证失败: %v", tenantID, provider, err)
            continue
        }
        
        // 预热缓存并进行健康检查
        for _, cred := range credentials {
            cacheKey := fmt.Sprintf("%s:%s", tenantID, provider)
            
            cm.mutex.Lock()
            cm.cache[cacheKey] = cred
            cm.usage[cred.ID] = 0
            cm.lastUsed[cred.ID] = time.Now()
            cm.mutex.Unlock()
            
            // 异步健康检查
            go func(c *SupplierCredential) {
                healthy, err := cm.tenantClient.TestCredential(c.ID, c.TenantID)
                if err != nil {
                    log.Printf("凭证 %s 健康检查失败: %v", c.ID, err)
                    healthy = false
                }
                
                cm.mutex.Lock()
                cm.healthStatus[c.ID] = healthy
                cm.mutex.Unlock()
                
                if healthy {
                    log.Printf("凭证预热成功: %s (%s) - %s", c.DisplayName, c.Provider, c.ID)
                } else {
                    log.Printf("凭证预热失败: %s (%s) - %s", c.DisplayName, c.Provider, c.ID)
                }
            }(cred)
        }
    }
    
    return nil
}

// 加载活跃租户列表
func (cm *CredentialManager) loadActiveTenants() ([]string, error) {
    // 这里可以从配置文件或数据库获取
    // 为了简化，我们通过Tenant Service的内部接口获取
    resp, err := cm.tenantClient.client.Get(cm.tenantClient.baseURL + "/internal/tenants/active")
    if err != nil {
        return nil, fmt.Errorf("获取活跃租户失败: %w", err)
    }
    defer resp.Body.Close()
    
    var result struct {
        Success bool     `json:"success"`
        Data    []string `json:"data"`
    }
    
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, fmt.Errorf("解析租户列表失败: %w", err)
    }
    
    return result.Data, nil
}
```

### 服务启动流程

```go
func main() {
    // 1. 初始化配置
    config := loadConfig()
    
    // 2. 初始化服务客户端
    tenantClient := &TenantServiceClient{
        baseURL: config.TenantServiceURL,
        client:  &http.Client{Timeout: 30 * time.Second},
    }
    
    // 3. 初始化凭证管理器
    credentialManager := &CredentialManager{
        tenantClient: tenantClient,
        cache:        make(map[string]*SupplierCredential),
        lastUsed:     make(map[string]time.Time),
        usage:        make(map[string]int64),
        healthStatus: make(map[string]bool),
        ttl:          5 * time.Minute,
    }
    
    // 4. 启动凭证预热
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    if err := credentialManager.WarmUpCredentials(ctx); err != nil {
        log.Fatalf("凭证预热失败: %v", err)
    }
    
    // 5. 启动健康检查
    go credentialManager.StartHealthCheck(context.Background(), 2*time.Minute)
    
    // 6. 初始化EINO工作流
    workflowManager := initializeWorkflows(credentialManager)
    
    // 7. 启动HTTP服务
    server := &http.Server{
        Addr:    ":8003",
        Handler: setupRoutes(workflowManager),
    }
    
    log.Printf("EINO Service 启动成功，端口: 8003")
    if err := server.ListenAndServe(); err != nil {
        log.Fatalf("服务启动失败: %v", err)
    }
}
```

## 🚀 部署和运行

### 编译和启动
```bash
cd services/eino
go mod download
go build -o eino-service cmd/server/main.go
./eino-service
```

### Docker配置
```dockerfile
FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o eino-service cmd/server/main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/eino-service .
EXPOSE 8003
CMD ["./eino-service"]
```

### 健康检查
```http
GET /health
```

**响应:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-10T10:30:00Z",
  "version": "1.0.0",
  "dependencies": {
    "tenant_service": "healthy",
    "memory_service": "healthy"
  },
  "metrics": {
    "active_executions": 23,
    "total_executions_today": 1547
  }
}
```

## ⚠️ 关键约束和限制

### 强制约束
1. **静态工作流**: 核心工作流结构必须在代码中静态定义
2. **配置驱动**: 工具启用/禁用必须通过数据库配置
3. **记忆检查**: 调用Memory Service前必须检查用户记忆开关
4. **凭证安全**: 供应商API密钥必须安全处理，不得泄露到日志

### 性能要求
- **执行延迟**: P95 < 2000ms（简单对话），P95 < 5000ms（复杂RAG）
- **并发处理**: 支持100并发工作流执行
- **吞吐量**: 每秒处理200+请求

### 监控指标
- 工作流执行成功率和延迟分布
- 各节点执行时间统计
- AI模型调用统计和成本
- 工具使用频率和成功率
- 记忆服务集成状态

---

**⚡ 重要提醒**: EINO Service是整个平台的AI能力核心，其稳定性直接影响用户体验。所有工作流修改都必须经过充分测试，确保向后兼容性和性能要求。