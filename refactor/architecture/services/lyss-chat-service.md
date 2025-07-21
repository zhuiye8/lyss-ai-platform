# lyss-chat-service (AI对话服务)

## 📋 服务概述

AI对话服务基于EINO框架，提供多供应商模型调用、工作流编排和流式响应处理功能。

---

## 🎯 服务职责

```
技术栈: Go + EINO v0.3.52 + PostgreSQL
端口: 8004
数据库: lyss_chat_db
职责：
- EINO框架集成和工作流编排
- 多供应商模型调用 (OpenAI、Anthropic、DeepSeek、Qwen等)
- 流式响应处理 (Server-Sent Events)
- 工具调用支持 (Function Calling)
- 对话历史管理和上下文增强
```

---

## 🔍 技术实现详细说明

### **EINO框架最新API用法**
```go
// 最新EINO API - 基于Context7调研结果
import (
    "github.com/cloudwego/eino/compose"
    "github.com/cloudwego/eino/schema"
    "github.com/cloudwego/eino-ext/components/model/openai"
    "github.com/cloudwego/eino-ext/components/model/deepseek"
)

// 1. 创建AI模型实例
func createChatModel(ctx context.Context, provider string, config map[string]interface{}) (schema.ChatModel, error) {
    switch provider {
    case "openai":
        return openai.NewChatModel(ctx, &openai.ChatModelConfig{
            APIKey:      config["api_key"].(string),
            Model:       config["model"].(string),
            Temperature: config["temperature"].(float32),
            MaxTokens:   config["max_tokens"].(int),
        })
    case "deepseek":
        return deepseek.NewChatModel(ctx, &deepseek.ChatModelConfig{
            APIKey:      config["api_key"].(string),
            Model:       config["model"].(string),
            Temperature: config["temperature"].(float32),
            MaxTokens:   config["max_tokens"].(int),
        })
    }
}

// 2. 构建EINO工作流链
func buildChatChain(ctx context.Context, model schema.ChatModel) (*compose.Chain, error) {
    // 使用最新的Chain API
    chain := compose.NewChain[map[string]any, *schema.Message]()
    
    // 添加聊天模板节点
    chain.AppendChatTemplate(chatTemplate)
    
    // 添加聊天模型节点
    chain.AppendChatModel(model)
    
    return chain.Compile(ctx)
}

// 3. 复杂工作流图编排 (支持工具调用)
func buildAdvancedGraph(ctx context.Context, model schema.ChatModel, tools []tool.BaseTool) (*compose.Graph, error) {
    graph := compose.NewGraph[map[string]any, *schema.Message]()
    
    // 添加各种节点
    graph.AddChatTemplateNode("template", chatTemplate)
    graph.AddChatModelNode("model", model)
    graph.AddToolsNode("tools", toolsNode)
    graph.AddLambdaNode("converter", messageConverter)
    
    // 定义边和分支
    graph.AddEdge(compose.START, "template")
    graph.AddEdge("template", "model")
    graph.AddBranch("model", branchFunc) // 条件分支
    graph.AddEdge("tools", "converter")
    graph.AddEdge("converter", compose.END)
    
    return graph.Compile(ctx)
}

// 4. 流式响应处理
func handleStreamingChat(ctx context.Context, graph *compose.Graph, userInput string) (<-chan string, error) {
    resultChan := make(chan string, 100)
    
    go func() {
        defer close(resultChan)
        
        // 使用EINO处理流式响应
        stream, err := graph.Stream(ctx, map[string]any{
            "query": userInput,
        })
        if err != nil {
            return
        }
        
        for chunk := range stream {
            if content, ok := chunk.(*schema.Message); ok {
                resultChan <- content.Content
            }
        }
    }()
    
    return resultChan, nil
}
```

### **关键技术改进**
- **编译错误修复**: 使用`compose.NewChain`和`compose.NewGraph`替代过时的API
- **流式响应**: 正确使用`Stream()`方法处理实时响应
- **多供应商支持**: 通过eino-ext扩展库支持多种AI模型
- **工作流编排**: 支持复杂的条件分支和工具调用

---

## 📊 数据库设计

### **对话表结构**
```sql
-- 对话会话表
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    system_prompt TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_conversations_user_tenant (user_id, tenant_id),
    INDEX idx_conversations_updated (updated_at DESC)
);

-- 消息表
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    model_used VARCHAR(100),
    token_count INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_messages_conversation (conversation_id, created_at),
    INDEX idx_messages_role (role)
);
```

---

## 🔧 配置管理

### **环境变量**
```bash
# 服务配置
CHAT_SERVICE_PORT=8004
CHAT_SERVICE_DEBUG=false

# 数据库配置
CHAT_SERVICE_DATABASE_URL=postgresql://lyss:password@lyss-postgres:5432/lyss_chat_db
CHAT_SERVICE_DATABASE_POOL_SIZE=20

# 外部服务
CHAT_SERVICE_PROVIDER_SERVICE_URL=http://lyss-provider-service:8003
CHAT_SERVICE_MEMORY_SERVICE_URL=http://lyss-memory-service:8005

# EINO配置
CHAT_SERVICE_EINO_LOG_LEVEL=info
CHAT_SERVICE_EINO_TIMEOUT=30s

# AI供应商配置 (由Provider Service管理)
# 这些配置在运行时从Provider Service获取
```

### **Docker配置**
```dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main cmd/server/main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/

COPY --from=builder /app/main .

EXPOSE 8004

CMD ["./main"]
```

---

## 🔍 监控和测试

### **健康检查**
```go
func (h *HealthHandler) Check(c *gin.Context) {
    ctx := c.Request.Context()
    
    // 检查数据库连接
    dbStatus := "healthy"
    if err := h.db.PingContext(ctx); err != nil {
        dbStatus = "unhealthy"
    }
    
    // 检查Provider Service连接
    providerStatus := "healthy"
    if _, err := h.providerClient.GetHealth(ctx); err != nil {
        providerStatus = "unhealthy"
    }
    
    c.JSON(200, gin.H{
        "status": "healthy",
        "timestamp": time.Now().UTC(),
        "checks": map[string]string{
            "database": dbStatus,
            "provider_service": providerStatus,
        },
    })
}
```

### **性能监控**
```go
import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

var (
    chatRequestsTotal = promauto.NewCounterVec(
        prometheus.CounterOpts{
            Name: "chat_requests_total",
            Help: "聊天请求总数",
        },
        []string{"model", "status"},
    )
    
    chatResponseTime = promauto.NewHistogramVec(
        prometheus.HistogramOpts{
            Name: "chat_response_duration_seconds",
            Help: "聊天响应时间",
        },
        []string{"model"},
    )
)
```