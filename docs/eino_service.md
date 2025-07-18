# EINO Service 技术规范文档

## 🎯 服务概述

EINO Service 是 Lyss AI Platform 的**AI模型编排与调用核心**，基于字节跳动开源的CloudWeGo EINO框架构建。EINO是专为Golang设计的大语言模型应用开发框架，强调类型安全的组件编排，为企业级AI应用提供可靠、高效的开发体验。

### EINO框架核心特性 (2025年最新)

1. **Go原生类型安全** - 通过编译期类型检查确保组件间数据流正确性，避免运行时错误
2. **组件抽象分离** - 核心eino库提供接口抽象，eino-ext库提供具体实现，架构清晰
3. **强大编排引擎** - 支持Chain(链式)和Graph(图式)两种编排模式，满足不同复杂度需求
4. **流式处理原生支持** - 自动处理流式和非流式数据转换，简化开发复杂度
5. **企业级生产就绪** - 已在字节跳动内部广泛应用，包括豆包、抖音、扣子等多条业务线

## 📋 核心职责与架构定位

### 🎯 服务定位
EINO Service在Lyss AI Platform微服务架构中的定位是**AI工作流编排与执行引擎**，专注于将AI能力通过EINO框架封装成可复用的服务组件，供API Gateway路由分发给前端使用。

### ✅ 负责的功能
1. **AI工作流编排**: 使用EINO Chain/Graph构建复杂的AI处理流程
2. **多供应商模型调用**: 统一封装OpenAI、Anthropic、Volcengine Ark、DeepSeek等
3. **智能凭证选择**: 基于租户凭证进行负载均衡和故障转移
4. **流式和非流式响应**: 支持标准响应和Server-Sent Events流式输出  
5. **本地凭证缓存**: 优化凭证获取性能，减少对Tenant Service的调用
6. **健康检查和监控**: 监控AI服务商可用性，及时发现问题

### ❌ 不负责的功能
- **用户认证和权限管理**（由Auth Service和API Gateway负责）
- **供应商凭证的存储和管理**（由Tenant Service统一管理）
- **数据库直接访问**（通过HTTP API调用其他服务获取数据）
- **对话记忆的持久化存储**（由Memory Service负责）
- **租户和用户数据管理**（由Tenant Service负责）

### 🔗 服务依赖关系
```
Frontend → API Gateway → EINO Service
                              ↓
                        Tenant Service (获取凭证)
                              ↓  
                         PostgreSQL (凭证存储)
```

## 🏗️ 技术架构

### 依赖关系澄清

**重要**: 基于最新调研，EINO框架采用"抽象与实现分离"的架构模式：

- **github.com/cloudwego/eino** (核心库): 提供组件接口抽象、编排引擎、类型定义
- **github.com/cloudwego/eino-ext** (扩展库): 提供具体模型实现，依赖于核心库

**核心库完全不依赖扩展库**，这种设计确保核心框架稳定，扩展实现可快速迭代。

### 正确的依赖导入方式

```go
// 正确的导入方式 - 按需导入具体实现
import (
    "context"
    
    // 核心框架 - 提供接口和编排能力
    "github.com/cloudwego/eino"
    "github.com/cloudwego/eino/compose"
    "github.com/cloudwego/eino/schema"
    "github.com/cloudwego/eino/components/model"
    
    // 具体模型实现 - 按需导入
    "github.com/cloudwego/eino-ext/components/model/openai"
    "github.com/cloudwego/eino-ext/components/model/ark"
    "github.com/cloudwego/eino-ext/components/model/deepseek"
    
    // 工具组件实现
    "github.com/cloudwego/eino-ext/components/tool/googlesearch"
)
```

### 支持的AI供应商 (2025年最新)

| 供应商 | EINO-EXT组件包 | 支持模型 | 状态 |
|--------|------------|----------|------|
| **OpenAI** | `eino-ext/components/model/openai` | GPT-4o, GPT-4, GPT-3.5-turbo | ✅ 已支持 |
| **DeepSeek** | `eino-ext/components/model/deepseek` | deepseek-chat, deepseek-reasoner | ✅ 已支持 |
| **Volcengine Ark** | `eino-ext/components/model/ark` | 豆包大模型系列 | ✅ 已支持 |
| **Volcengine ArkBot** | `eino-ext/components/model/arkbot` | 火山引擎Bot模型 | ✅ 已支持 |
| **Google Gemini** | `eino-ext/components/model/gemini` | Gemini系列 | ✅ 已支持 |
| **Anthropic Claude** | `eino-ext/components/model/anthropic` | Claude系列 | ✅ 已支持 |
| **Ollama** | `eino-ext/components/model/ollama` | 本地部署模型 | ✅ 已支持 |

## 🔧 核心工作流实现

### 1. 标准聊天工作流 (基于EINO Chain API)

基于最新EINO框架的正确实现方式：

```go
// 标准聊天工作流实现
type StandardChatWorkflow struct {
    credentialManager *CredentialManager
    logger           *logrus.Logger
}

// 根据供应商创建对应的ChatModel
func (w *StandardChatWorkflow) createChatModel(ctx context.Context, credential *SupplierCredential) (model.ChatModel, error) {
    switch credential.Provider {
    case "openai":
        return openai.NewChatModel(ctx, &openai.ChatModelConfig{
            APIKey:      credential.APIKey,
            Model:       credential.ModelConfigs["model"].(string),
            BaseURL:     credential.BaseURL,
            Temperature: credential.ModelConfigs["temperature"].(*float32),
            MaxTokens:   credential.ModelConfigs["max_tokens"].(*int),
        })
    case "deepseek":
        return deepseek.NewChatModel(ctx, &deepseek.ChatModelConfig{
            APIKey:      credential.APIKey,
            Model:       credential.ModelConfigs["model"].(string),
            Temperature: credential.ModelConfigs["temperature"].(float32),
            MaxTokens:   credential.ModelConfigs["max_tokens"].(int),
        })
    case "ark":
        return ark.NewChatModel(ctx, &ark.ChatModelConfig{
            APIKey:    credential.APIKey,
            Model:     credential.ModelConfigs["model"].(string),
            Region:    credential.ModelConfigs["region"].(string),
            BaseURL:   credential.BaseURL,
        })
    default:
        return nil, fmt.Errorf("不支持的供应商: %s", credential.Provider)
    }
}

// 使用EINO Chain构建简单聊天工作流
func (w *StandardChatWorkflow) buildChatChain(ctx context.Context, credential *SupplierCredential) (compose.Runnable[*schema.Message, *schema.Message], error) {
    // 创建聊天模型
    chatModel, err := w.createChatModel(ctx, credential)
    if err != nil {
        return nil, fmt.Errorf("创建聊天模型失败: %w", err)
    }
    
    // 构建Chain - 最简单的情况，直接使用ChatModel
    chain := compose.NewChain[*schema.Message, *schema.Message]().
        AppendChatModel(chatModel)
    
    // 编译Chain
    compiled, err := chain.Compile(ctx)
    if err != nil {
        return nil, fmt.Errorf("编译聊天链失败: %w", err)
    }
    
    return compiled, nil
}

// 标准聊天工作流执行
func (w *StandardChatWorkflow) Execute(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error) {
    startTime := time.Now()
    
    // 1. 获取租户最佳凭证
    credential, err := w.credentialManager.GetBestCredential(req.TenantID, req.ModelConfig["provider"].(string))
    if err != nil {
        return nil, fmt.Errorf("获取凭证失败: %w", err)
    }
    
    // 2. 构建EINO工作流链
    runnable, err := w.buildChatChain(ctx, credential)
    if err != nil {
        return nil, fmt.Errorf("构建工作流链失败: %w", err)
    }
    
    // 3. 构建输入消息
    inputMessage := &schema.Message{
        Role:    schema.User,
        Content: req.Message,
    }
    
    // 4. 执行EINO链 - 注意最新的API调用方式
    result, err := runnable.Invoke(ctx, inputMessage)
    if err != nil {
        return nil, fmt.Errorf("EINO链执行失败: %w", err)
    }
    
    // 5. 记录凭证使用
    w.credentialManager.RecordUsage(credential.ID)
    
    // 6. 构建响应
    response := &WorkflowResponse{
        Success:         true,
        Content:         result.Content,
        Model:           credential.ModelConfigs["model"].(string),
        WorkflowType:    "standard_chat",
        ExecutionTimeMs: time.Since(startTime).Milliseconds(),
        Metadata: map[string]interface{}{
            "provider":      credential.Provider,
            "credential_id": credential.ID,
            "model_used":    credential.ModelConfigs["model"],
        },
    }
    
    // 7. 提取Token使用信息（如果可用）
    if result.ResponseMeta != nil && result.ResponseMeta.Usage != nil {
        response.Usage = &TokenUsage{
            PromptTokens:     int(result.ResponseMeta.Usage.PromptTokens),
            CompletionTokens: int(result.ResponseMeta.Usage.CompletionTokens),
            TotalTokens:      int(result.ResponseMeta.Usage.TotalTokens),
        }
    }
    
    return response, nil
}
```

### 2. 流式聊天工作流 (基于EINO Stream API)

```go
// 流式聊天工作流执行
func (w *StandardChatWorkflow) ExecuteStream(ctx context.Context, req *WorkflowRequest) (<-chan *WorkflowStreamResponse, error) {
    responseChan := make(chan *WorkflowStreamResponse, 100)
    
    go func() {
        defer close(responseChan)
        
        // 1. 获取租户最佳凭证
        credential, err := w.credentialManager.GetBestCredential(req.TenantID, req.ModelConfig["provider"].(string))
        if err != nil {
            responseChan <- &WorkflowStreamResponse{
                Type:  "error",
                Error: fmt.Sprintf("获取凭证失败: %v", err),
            }
            return
        }
        
        // 2. 构建EINO工作流链
        runnable, err := w.buildChatChain(ctx, credential)
        if err != nil {
            responseChan <- &WorkflowStreamResponse{
                Type:  "error",
                Error: fmt.Sprintf("构建工作流链失败: %v", err),
            }
            return
        }
        
        // 3. 构建输入消息
        inputMessage := &schema.Message{
            Role:    schema.User,
            Content: req.Message,
        }
        
        // 4. 发送开始事件
        responseChan <- &WorkflowStreamResponse{
            Type:        "start",
            ExecutionID: req.ExecutionID,
            Data:        map[string]any{"provider": credential.Provider},
        }
        
        // 5. 执行流式调用 - 使用EINO的Stream方法
        streamReader, err := runnable.Stream(ctx, inputMessage)
        if err != nil {
            responseChan <- &WorkflowStreamResponse{
                Type:  "error",
                Error: fmt.Sprintf("流式调用失败: %v", err),
            }
            return
        }
        defer streamReader.Close()
        
        // 6. 处理流式响应
        var fullContent string
        for {
            chunk, err := streamReader.Recv()
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
            
            fullContent += chunk.Content
            responseChan <- &WorkflowStreamResponse{
                Type:        "chunk",
                ExecutionID: req.ExecutionID,
                Content:     chunk.Content, // 发送增量内容
                Data: map[string]any{
                    "accumulated_content": fullContent,
                    "delta":              chunk.Content,
                },
            }
        }
        
        // 7. 发送结束事件
        responseChan <- &WorkflowStreamResponse{
            Type:        "end",
            ExecutionID: req.ExecutionID,
            Content:     fullContent,
            Data: map[string]any{
                "final_content": fullContent,
                "provider":      credential.Provider,
            },
        }
        
        // 8. 记录凭证使用
        w.credentialManager.RecordUsage(credential.ID)
    }()
    
    return responseChan, nil
}
```

## 🔐 智能凭证管理系统

### 架构设计原则

**重要提醒**: EINO Service采用**无状态 + 缓存优化**的架构模式：

1. **不直接访问数据库** - 所有凭证数据通过Tenant Service HTTP API获取
2. **智能本地缓存** - 减少网络调用，提升响应性能
3. **故障容错机制** - 缓存失效时自动回退到API调用
4. **租户级别隔离** - 缓存Key包含tenant_id，确保多租户安全

### 凭证管理器架构

```go
// 智能凭证管理器 - 专注于缓存和选择算法
type CredentialManager struct {
    tenantClient   *TenantServiceClient   // 租户服务HTTP客户端
    redisClient    *redis.Client          // Redis缓存客户端  
    cache          map[string]*SupplierCredential // 本地L1缓存
    lastUsed       map[string]time.Time   // 最后使用时间
    usage          map[string]int64       // 使用次数统计
    healthStatus   map[string]bool        // 健康状态监控
    mutex          sync.RWMutex           // 读写锁
    logger         *logrus.Logger         // 日志记录器
}

// 供应商凭证结构（从Tenant Service获取）
type SupplierCredential struct {
    ID           string                 `json:"id"`
    TenantID     string                 `json:"tenant_id"`
    Provider     string                 `json:"provider_name"`    // openai, deepseek, ark等
    DisplayName  string                 `json:"display_name"`
    APIKey       string                 `json:"api_key"`
    BaseURL      string                 `json:"base_url"`
    ModelConfigs map[string]interface{} `json:"model_configs"`
    IsActive     bool                   `json:"is_active"`
    CreatedAt    time.Time              `json:"created_at"`
    UpdatedAt    time.Time              `json:"updated_at"`
}

// 智能凭证获取算法 - 三级缓存策略
func (cm *CredentialManager) GetBestCredential(tenantID, provider string) (*SupplierCredential, error) {
    cacheKey := fmt.Sprintf("tenant:%s:credentials:%s", tenantID, provider)
    
    // 1. 检查本地缓存 (L1)
    cm.mutex.RLock()
    if cached, exists := cm.cache[cacheKey]; exists {
        if time.Since(cached.UpdatedAt) < 2*time.Minute && cm.healthStatus[cached.ID] {
            cm.mutex.RUnlock()
            cm.logger.WithFields(logrus.Fields{
                "tenant_id":     tenantID,
                "provider":      provider,
                "credential_id": cached.ID,
                "source":        "local_cache",
            }).Debug("使用本地缓存的凭证")
            return cached, nil
        }
    }
    cm.mutex.RUnlock()
    
    // 2. 检查Redis缓存 (L2)
    if cm.redisClient != nil {
        ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
        defer cancel()
        
        if credentialJSON, err := cm.redisClient.Get(ctx, cacheKey).Result(); err == nil {
            var credential SupplierCredential
            if json.Unmarshal([]byte(credentialJSON), &credential) == nil {
                if time.Since(credential.UpdatedAt) < 5*time.Minute {
                    cm.updateLocalCache(cacheKey, &credential)
                    cm.logger.WithFields(logrus.Fields{
                        "tenant_id":     tenantID,
                        "provider":      provider,
                        "credential_id": credential.ID,
                        "source":        "redis_cache",
                    }).Debug("使用Redis缓存的凭证")
                    return &credential, nil
                }
            }
        }
    }
    
    // 3. 从Tenant Service获取最新凭证 (L3 - API调用)
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
        return nil, fmt.Errorf("从Tenant Service获取凭证失败: %w", err)
    }
    
    if len(credentials) == 0 {
        return nil, fmt.Errorf("租户 %s 没有可用的 %s 凭证", tenantID, provider)
    }
    
    // 4. 智能选择最佳凭证
    best := cm.selectBestCredential(credentials)
    
    // 5. 更新多级缓存
    cm.updateCaches(cacheKey, best)
    
    cm.logger.WithFields(logrus.Fields{
        "tenant_id":     tenantID,
        "provider":      provider,
        "credential_id": best.ID,
        "source":        "tenant_service_api",
    }).Info("从Tenant Service获取新凭证")
    
    return best, nil
}

// 凭证评分算法
func (cm *CredentialManager) selectBestCredential(credentials []*SupplierCredential) *SupplierCredential {
    var best *SupplierCredential
    var bestScore float64
    
    for _, cred := range credentials {
        score := 100.0
        
        // 健康状态权重 (50%)
        if !cm.healthStatus[cred.ID] {
            score -= 50
        }
        
        // 负载均衡权重 (30%)
        usageCount := cm.usage[cred.ID]
        score -= float64(usageCount) * 0.1
        
        // 最近使用时间权重 (20%)
        if lastUsed, exists := cm.lastUsed[cred.ID]; exists {
            minutesSinceUsed := time.Since(lastUsed).Minutes()
            if minutesSinceUsed > 30 {
                score -= minutesSinceUsed * 0.1
            }
        }
        
        if best == nil || score > bestScore {
            best = cred
            bestScore = score
        }
    }
    
    return best
}
```

### 凭证健康检查系统

```go
// 启动健康检查服务
func (cm *CredentialManager) StartHealthCheck(ctx context.Context) {
    ticker := time.NewTicker(2 * time.Minute)
    defer ticker.Stop()
    
    cm.logger.Info("启动凭证健康检查服务")
    
    for {
        select {
        case <-ctx.Done():
            cm.logger.Info("凭证健康检查服务停止")
            return
        case <-ticker.C:
            cm.performHealthCheck(ctx)
        }
    }
}

// 执行健康检查
func (cm *CredentialManager) performHealthCheck(ctx context.Context) {
    cm.mutex.RLock()
    credentials := make([]*SupplierCredential, 0, len(cm.cache))
    for _, cred := range cm.cache {
        credentials = append(credentials, cred)
    }
    cm.mutex.RUnlock()
    
    var wg sync.WaitGroup
    for _, cred := range credentials {
        wg.Add(1)
        go func(c *SupplierCredential) {
            defer wg.Done()
            cm.checkSingleCredential(ctx, c)
        }(cred)
    }
    wg.Wait()
    
    cm.logger.WithField("checked_count", len(credentials)).Info("凭证健康检查完成")
}

// 单个凭证健康检查
func (cm *CredentialManager) checkSingleCredential(ctx context.Context, cred *SupplierCredential) {
    startTime := time.Now()
    
    // 使用对应的EINO模型组件进行健康检查
    healthy := false
    
    switch cred.Provider {
    case "openai":
        healthy = cm.checkOpenAICredential(ctx, cred)
    case "deepseek":
        healthy = cm.checkDeepSeekCredential(ctx, cred)
    case "ark":
        healthy = cm.checkArkCredential(ctx, cred)
    default:
        cm.logger.WithField("provider", cred.Provider).Warn("不支持的供应商健康检查")
        healthy = false
    }
    
    // 更新健康状态
    cm.mutex.Lock()
    cm.healthStatus[cred.ID] = healthy
    cm.mutex.Unlock()
    
    duration := time.Since(startTime)
    cm.logger.WithFields(logrus.Fields{
        "credential_id": cred.ID,
        "provider":      cred.Provider,
        "display_name":  cred.DisplayName,
        "healthy":       healthy,
        "duration_ms":   duration.Milliseconds(),
    }).Info("凭证健康检查完成")
}

// OpenAI凭证健康检查
func (cm *CredentialManager) checkOpenAICredential(ctx context.Context, cred *SupplierCredential) bool {
    model, err := openai.NewChatModel(ctx, &openai.ChatModelConfig{
        APIKey:  cred.APIKey,
        Model:   "gpt-3.5-turbo", // 使用最便宜的模型进行测试
        BaseURL: cred.BaseURL,
    })
    
    if err != nil {
        cm.logger.WithError(err).WithField("credential_id", cred.ID).Error("创建OpenAI模型失败")
        return false
    }
    
    // 发送简单测试消息
    testCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
    defer cancel()
    
    messages := []*schema.Message{
        {
            Role:    schema.User,
            Content: "ping",
        },
    }
    
    _, err = model.Generate(testCtx, messages)
    return err == nil
}

// DeepSeek凭证健康检查
func (cm *CredentialManager) checkDeepSeekCredential(ctx context.Context, cred *SupplierCredential) bool {
    model, err := deepseek.NewChatModel(ctx, &deepseek.ChatModelConfig{
        APIKey: cred.APIKey,
        Model:  "deepseek-chat",
    })
    
    if err != nil {
        cm.logger.WithError(err).WithField("credential_id", cred.ID).Error("创建DeepSeek模型失败")
        return false
    }
    
    testCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
    defer cancel()
    
    messages := []*schema.Message{
        {
            Role:    schema.User,
            Content: "ping",
        },
    }
    
    _, err = model.Generate(testCtx, messages)
    return err == nil
}
```

## 📡 对外API接口

### 1. 标准聊天接口

```http
POST /api/v1/chat/completions
Content-Type: application/json
Authorization: Bearer {jwt_token}
X-Tenant-ID: {tenant_id}
```

**请求体:**
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "system",
      "content": "你是一个有用的AI助手"
    },
    {
      "role": "user", 
      "content": "请解释一下机器学习的基本概念"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 2048,
  "stream": false,
  "provider": "openai"
}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "id": "chatcmpl-uuid",
    "object": "chat.completion",
    "created": 1710845760,
    "model": "gpt-4",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "机器学习是人工智能的一个分支..."
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 45,
      "completion_tokens": 312,
      "total_tokens": 357
    },
    "provider": "openai",
    "execution_time_ms": 1250
  },
  "request_id": "req-20250717-uuid",
  "timestamp": "2025-07-17T14:30:00Z"
}
```

### 2. 流式聊天接口

```http
POST /api/v1/chat/completions
Content-Type: application/json
Authorization: Bearer {jwt_token}
X-Tenant-ID: {tenant_id}
```

**请求体:**
```json
{
  "model": "gpt-4",
  "messages": [
    {
      "role": "user",
      "content": "写一首关于春天的诗"
    }
  ],
  "stream": true,
  "provider": "openai"
}
```

**流式响应 (Server-Sent Events):**
```
data: {"id":"chatcmpl-uuid","object":"chat.completion.chunk","created":1710845760,"model":"gpt-4","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}

data: {"id":"chatcmpl-uuid","object":"chat.completion.chunk","created":1710845760,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"春"},"finish_reason":null}]}

data: {"id":"chatcmpl-uuid","object":"chat.completion.chunk","created":1710845760,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"天"},"finish_reason":null}]}

data: {"id":"chatcmpl-uuid","object":"chat.completion.chunk","created":1710845760,"model":"gpt-4","choices":[{"index":0,"delta":{"content":"的"},"finish_reason":null}]}

data: [DONE]
```

### 3. 模型列表接口

```http
GET /api/v1/models
Authorization: Bearer {jwt_token}
X-Tenant-ID: {tenant_id}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "object": "list",
    "data": [
      {
        "id": "gpt-4",
        "object": "model",
        "provider": "openai",
        "available": true,
        "credentials_count": 2
      },
      {
        "id": "claude-3-sonnet",
        "object": "model", 
        "provider": "anthropic",
        "available": false,
        "credentials_count": 0
      },
      {
        "id": "deepseek-chat",
        "object": "model",
        "provider": "deepseek", 
        "available": true,
        "credentials_count": 1
      }
    ]
  }
}
```

## 🔗 与Tenant Service集成

### 服务间通信协议

**EINO Service与Tenant Service之间采用HTTP RESTful API通信**，遵循微服务架构最佳实践：

1. **无状态通信** - 每次请求包含完整上下文信息
2. **标准HTTP状态码** - 200成功、404未找到、500服务错误等
3. **JSON数据格式** - 统一使用JSON进行数据交换
4. **超时和重试** - 配置合理的超时时间和重试策略
5. **错误处理** - 优雅处理网络异常和服务不可用情况

### Tenant Service内部API接口

**以下接口由Tenant Service提供，供EINO Service调用：**

#### 1. 获取可用凭证列表
```http
GET /internal/suppliers/{tenant_id}/available
Authorization: Internal-Service-Token
Query Parameters:
  - strategy: least_used | round_robin | first_available
  - only_active: true | false
  - providers: openai,deepseek,ark (逗号分隔)

Response:
{
  "success": true,
  "data": [
    {
      "id": "credential-uuid",
      "provider": "openai", 
      "api_key": "sk-...",  // 已解密
      "model_configs": {...},
      "is_active": true,
      "usage_stats": {...}
    }
  ]
}
```

#### 2. 凭证健康检测
```http
POST /internal/suppliers/{credential_id}/health-check
Authorization: Internal-Service-Token
Content-Type: application/json

{
  "tenant_id": "tenant-uuid",
  "test_type": "connection",
  "model_name": "gpt-3.5-turbo"
}

Response:
{
  "success": true,
  "data": {
    "healthy": true,
    "response_time_ms": 350,
    "last_checked": "2025-07-18T10:30:00Z",
    "error_message": null
  }
}
```

#### 3. 更新凭证使用统计
```http
POST /internal/suppliers/{credential_id}/usage
Authorization: Internal-Service-Token
Content-Type: application/json

{
  "tenant_id": "tenant-uuid",
  "tokens_used": 1500,
  "request_count": 1,
  "execution_time_ms": 1200
}
```

### Tenant Service客户端实现

**基于微服务架构的HTTP客户端设计**：

```go
type TenantServiceClient struct {
    baseURL     string
    client      *http.Client
    logger      *logrus.Logger
    authToken   string  // 内部服务认证令牌
    timeout     time.Duration
    retryConfig *RetryConfig
}

type RetryConfig struct {
    MaxRetries int
    BackoffMs  []int  // 递增退避策略
}

// 获取租户可用凭证 - 核心接口
func (c *TenantServiceClient) GetAvailableCredentials(tenantID string, selector *CredentialSelector) ([]*SupplierCredential, error) {
    url := fmt.Sprintf("%s/internal/suppliers/%s/available", c.baseURL, tenantID)
    
    req, err := http.NewRequest("GET", url, nil)
    if err != nil {
        return nil, fmt.Errorf("创建HTTP请求失败: %w", err)
    }
    
    // 添加内部服务认证头
    req.Header.Set("Authorization", fmt.Sprintf("Internal-Service-Token %s", c.authToken))
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("X-Service-Name", "eino-service")
    
    // 构建查询参数
    q := req.URL.Query()
    if selector != nil {
        q.Add("strategy", selector.Strategy)
        q.Add("only_active", fmt.Sprintf("%t", selector.Filters.OnlyActive))
        if len(selector.Filters.Providers) > 0 {
            q.Add("providers", strings.Join(selector.Filters.Providers, ","))
        }
    }
    req.URL.RawQuery = q.Encode()
    
    // 执行请求（带重试机制）
    resp, err := c.executeWithRetry(req)
    if err != nil {
        return nil, fmt.Errorf("调用Tenant Service失败: %w", err)
    }
    defer resp.Body.Close()
    
    // 解析响应
    var result struct {
        Success bool                  `json:"success"`
        Data    []*SupplierCredential `json:"data"`
        Message string                `json:"message"`
        RequestID string              `json:"request_id"`
    }
    
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, fmt.Errorf("解析Tenant Service响应失败: %w", err)
    }
    
    if !result.Success {
        return nil, fmt.Errorf("Tenant Service返回错误: %s", result.Message)
    }
    
    c.logger.WithFields(logrus.Fields{
        "tenant_id":         tenantID,
        "credentials_count": len(result.Data),
        "request_id":        result.RequestID,
        "source":           "tenant_service",
    }).Info("成功获取租户凭证")
    
    return result.Data, nil
}

// HTTP请求重试机制
func (c *TenantServiceClient) executeWithRetry(req *http.Request) (*http.Response, error) {
    var lastErr error
    
    for i := 0; i <= c.retryConfig.MaxRetries; i++ {
        if i > 0 {
            // 指数退避策略
            backoffMs := c.retryConfig.BackoffMs[min(i-1, len(c.retryConfig.BackoffMs)-1)]
            time.Sleep(time.Duration(backoffMs) * time.Millisecond)
            c.logger.WithField("retry_attempt", i).Warn("重试调用Tenant Service")
        }
        
        ctx, cancel := context.WithTimeout(context.Background(), c.timeout)
        reqWithTimeout := req.WithContext(ctx)
        
        resp, err := c.client.Do(reqWithTimeout)
        cancel()
        
        if err == nil && resp.StatusCode < 500 {
            return resp, nil  // 成功或客户端错误，不重试
        }
        
        if err != nil {
            lastErr = err
        } else {
            lastErr = fmt.Errorf("HTTP %d", resp.StatusCode)
            resp.Body.Close()
        }
    }
    
    return nil, fmt.Errorf("重试%d次后仍失败: %w", c.retryConfig.MaxRetries, lastErr)
}

// 测试凭证连接性
func (c *TenantServiceClient) TestCredential(credentialID, tenantID, modelName string) (bool, error) {
    url := fmt.Sprintf("%s/internal/suppliers/%s/test", c.baseURL, credentialID)
    
    reqBody := map[string]interface{}{
        "tenant_id":  tenantID,
        "test_type":  "connection",
        "model_name": modelName,
    }
    
    bodyBytes, err := json.Marshal(reqBody)
    if err != nil {
        return false, fmt.Errorf("编码请求体失败: %w", err)
    }
    
    resp, err := c.client.Post(url, "application/json", bytes.NewBuffer(bodyBytes))
    if err != nil {
        return false, fmt.Errorf("测试凭证请求失败: %w", err)
    }
    defer resp.Body.Close()
    
    var result struct {
        Success bool `json:"success"`
        Data    struct {
            Success        bool `json:"success"`
            ResponseTimeMs int  `json:"response_time_ms"`
        } `json:"data"`
        Message string `json:"message"`
    }
    
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return false, fmt.Errorf("解析测试结果失败: %w", err)
    }
    
    return result.Success && result.Data.Success, nil
}
```

## 🚀 部署和运行

### Go模块配置 (go.mod)

基于最新EINO框架的正确依赖配置：

```go
module eino-service

go 1.21

require (
    // EINO核心框架
    github.com/cloudwego/eino v0.3.34
    
    // 具体模型实现 - 按需导入
    github.com/cloudwego/eino-ext/components/model/openai v0.3.34
    github.com/cloudwego/eino-ext/components/model/deepseek v0.3.34
    github.com/cloudwego/eino-ext/components/model/ark v0.3.34
    github.com/cloudwego/eino-ext/components/model/arkbot v0.3.34
    github.com/cloudwego/eino-ext/components/model/gemini v0.3.34
    
    // 工具组件
    github.com/cloudwego/eino-ext/components/tool/googlesearch v0.3.34
    
    // 其他依赖
    github.com/gin-gonic/gin v1.9.1
    github.com/sirupsen/logrus v1.9.3
    github.com/redis/go-redis/v9 v9.0.5
)
```

### 环境变量配置

```bash
# 服务基本配置
PORT=8003
LOG_LEVEL=INFO
GIN_MODE=release

# Redis配置 (用于凭证和响应缓存)
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_PASSWORD=

# 依赖服务 - EINO Service通过HTTP API调用其他服务
TENANT_SERVICE_URL=http://localhost:8002
MEMORY_SERVICE_URL=http://localhost:8004

# 注意: EINO Service不直接连接PostgreSQL数据库
# 所有数据通过Tenant Service的HTTP API获取

# EINO框架配置
EINO_COMPILE_TIMEOUT=10s
EINO_EXECUTION_TIMEOUT=60s
CREDENTIAL_CACHE_TTL=300s
HEALTH_CHECK_INTERVAL=120s

# AI模型默认配置
DEFAULT_REQUEST_TIMEOUT=30s
MAX_TOKENS_PER_REQUEST=8192
DEFAULT_TEMPERATURE=0.7
```

### Docker配置

```dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o eino-service ./cmd/server

FROM alpine:latest
RUN apk --no-cache add ca-certificates tzdata
WORKDIR /root/

COPY --from=builder /app/eino-service .

EXPOSE 8003
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8003/health || exit 1

CMD ["./eino-service"]
```

### 编译和启动

```bash
# 下载EINO依赖
go mod download

# 编译服务
go build -o bin/eino-service ./cmd/server

# 启动服务
./bin/eino-service

# 或者直接运行
go run ./cmd/server

# 验证EINO框架版本
go list -m github.com/cloudwego/eino
```

### 健康检查

```http
GET /health
```

**响应:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-17T14:30:00Z",
  "version": "1.0.0",
  "dependencies": {
    "tenant_service": "healthy",
    "database": "healthy",
    "redis": "healthy"
  },
  "metrics": {
    "cached_credentials": 15,
    "healthy_credentials": 12,
    "active_executions": 3
  }
}
```

## 📊 监控和日志

### 关键指标

- **模型调用成功率**: 按供应商和模型分组
- **响应延迟分布**: P50, P95, P99延迟统计  
- **凭证健康状态**: 可用凭证数量和健康比例
- **并发执行数**: 当前活跃的工作流执行数
- **Token使用统计**: 按租户和供应商的Token消耗

### 日志格式

```json
{
  "timestamp": "2025-07-17T14:30:00Z",
  "level": "INFO",
  "service": "eino-service",
  "request_id": "req-uuid",
  "tenant_id": "tenant-uuid",
  "operation": "chat_completion",
  "provider": "openai",
  "model": "gpt-4",
  "execution_time_ms": 1250,
  "tokens_used": 357,
  "success": true,
  "message": "聊天完成"
}
```

## ⚠️ 重要约束

### 安全要求
1. **API密钥安全**: 供应商API密钥必须安全处理，不得出现在日志中
2. **租户隔离**: 严格的租户数据隔离，防止交叉访问
3. **请求验证**: 所有API请求必须通过JWT验证

### 性能要求  
- **响应延迟**: P95 < 2000ms（标准聊天）
- **并发处理**: 支持100并发请求
- **吞吐量**: 每秒处理200+请求

### 可靠性要求
- **故障转移**: 凭证失败时自动切换到其他可用凭证
- **健康检查**: 定期检查凭证可用性
- **优雅降级**: 服务异常时提供基本功能

## 🎯 开发最佳实践

### 1. EINO框架使用原则

- **按需导入**: 只导入实际需要的eino-ext组件，避免引入不必要的依赖
- **类型安全优先**: 利用EINO的编译期类型检查，在Compile()阶段发现问题
- **组件复用**: 将创建好的ChatModel等组件缓存复用，避免重复初始化
- **错误处理**: 充分利用Go的错误处理机制，确保稳定性

### 2. 性能优化建议

- **编译缓存**: 预编译常用的Chain和Graph，避免运行时编译开销
- **连接池**: 为HTTP客户端配置合适的连接池参数
- **流式优先**: 对于长文本生成，优先使用Stream模式提升用户体验
- **监控集成**: 集成EINO的回调机制实现全链路追踪

### 3. 错误处理和降级

```go
// 智能降级示例
func (w *StandardChatWorkflow) ExecuteWithFallback(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error) {
    providers := []string{"openai", "deepseek", "ark"} // 按优先级排序
    
    for _, provider := range providers {
        if credential, err := w.credentialManager.GetBestCredential(req.TenantID, provider); err == nil {
            if result, err := w.executeWithProvider(ctx, req, credential); err == nil {
                return result, nil
            }
            // 记录失败，尝试下一个供应商
            w.logger.WithError(err).Warnf("Provider %s failed, trying next", provider)
        }
    }
    
    return nil, fmt.Errorf("所有供应商都不可用")
}
```

---

**🎯 总结**: EINO Service基于字节跳动开源的EINO框架，专注于提供类型安全、高性能的AI模型编排服务。通过正确理解EINO的架构设计和最佳实践，能够构建出稳定可靠、易于维护的企业级AI应用。