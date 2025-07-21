# EINO框架集成技术文档

## 📋 框架概述

**EINO** (v0.3.52) 是字节跳动开源的LLM应用编排框架，专为Go语言设计，支持多供应商模型集成和复杂工作流编排。

---

## 🎯 核心能力

### **多供应商支持**
- **OpenAI**: GPT-4、GPT-3.5-turbo等
- **DeepSeek**: DeepSeek-Chat、DeepSeek-Coder等  
- **Anthropic**: Claude系列模型
- **自定义供应商**: 支持OpenAI兼容API

### **工作流编排**
- **Chain编排**: 线性工作流处理
- **Graph编排**: 复杂分支和并行处理
- **流式响应**: 实时流式输出支持
- **工具调用**: Function Calling集成

---

## 🔧 最新API用法 (v0.3.52)

### **1. 基础依赖导入**
```go
// 最新EINO API - 基于Context7调研结果
import (
    "context"
    "github.com/cloudwego/eino/compose"
    "github.com/cloudwego/eino/schema"
    "github.com/cloudwego/eino-ext/components/model/openai"
    "github.com/cloudwego/eino-ext/components/model/deepseek"
)
```

### **2. Chain编排 - 简单对话工作流**
```go
func buildChatChain(ctx context.Context, model schema.ChatModel) (*compose.Chain, error) {
    // 创建新的Chain实例
    chain := compose.NewChain[map[string]any, *schema.Message]()
    
    // 添加聊天模板处理
    chain.AppendChatTemplate(chatTemplate)
    
    // 添加模型调用
    chain.AppendChatModel(model)
    
    // 编译Chain
    return chain.Compile(ctx)
}

// 执行Chain
func executeChatChain(ctx context.Context, chain *compose.Chain, input map[string]any) (*schema.Message, error) {
    result, err := chain.Invoke(ctx, input)
    if err != nil {
        return nil, fmt.Errorf("chain执行失败: %w", err)
    }
    return result, nil
}
```

### **3. Graph编排 - 复杂工作流**
```go
func buildComplexGraph(ctx context.Context, models map[string]schema.ChatModel) (*compose.Graph, error) {
    // 创建Graph构建器
    builder := compose.NewGraphBuilder[map[string]any, map[string]any]()
    
    // 添加节点
    builder.AddNode("analyze", func(ctx context.Context, input map[string]any) (map[string]any, error) {
        // 分析节点逻辑
        return models["analyzer"].Generate(ctx, input)
    })
    
    builder.AddNode("generate", func(ctx context.Context, input map[string]any) (map[string]any, error) {
        // 生成节点逻辑  
        return models["generator"].Generate(ctx, input)
    })
    
    // 添加边
    builder.AddEdge("analyze", "generate")
    
    // 编译Graph
    return builder.Compile(ctx)
}
```

### **4. 流式响应处理**
```go
func handleStreamResponse(ctx context.Context, model schema.ChatModel, messages []*schema.Message) error {
    // 创建流式请求
    stream, err := model.Stream(ctx, messages)
    if err != nil {
        return fmt.Errorf("创建流失败: %w", err)
    }
    defer stream.Close()
    
    // 处理流式数据
    for {
        chunk, err := stream.Recv()
        if err == io.EOF {
            break
        }
        if err != nil {
            return fmt.Errorf("接收流数据失败: %w", err)
        }
        
        // 实时处理chunk数据
        fmt.Printf("收到数据块: %s\n", chunk.Content)
    }
    
    return nil
}
```

### **5. 多供应商模型配置**
```go
// OpenAI模型配置
func createOpenAIModel(apiKey, baseURL string) (schema.ChatModel, error) {
    config := &openai.ChatModelConfig{
        APIKey:  apiKey,
        BaseURL: baseURL,
        Model:   "gpt-4",
    }
    return openai.NewChatModel(config)
}

// DeepSeek模型配置
func createDeepSeekModel(apiKey string) (schema.ChatModel, error) {
    config := &deepseek.ChatModelConfig{
        APIKey: apiKey,
        Model:  "deepseek-chat",
    }
    return deepseek.NewChatModel(config)
}

// 统一模型管理器
type ModelManager struct {
    models map[string]schema.ChatModel
}

func (m *ModelManager) GetModel(provider, model string) (schema.ChatModel, error) {
    key := fmt.Sprintf("%s:%s", provider, model)
    if model, exists := m.models[key]; exists {
        return model, nil
    }
    return nil, fmt.Errorf("模型不存在: %s", key)
}
```

---

## 🏗️ lyss-chat-service集成架构

### **服务结构**
```
lyss-chat-service/
├── internal/
│   ├── models/          # 模型管理
│   ├── chains/          # Chain工作流
│   ├── graphs/          # Graph工作流  
│   ├── streaming/       # 流式处理
│   └── providers/       # 供应商集成
├── api/                 # HTTP API接口
├── config/              # 配置管理
└── cmd/                 # 服务启动入口
```

### **核心接口设计**
```go
// 聊天服务接口
type ChatService interface {
    // 简单对话
    Chat(ctx context.Context, req *ChatRequest) (*ChatResponse, error)
    
    // 流式对话
    StreamChat(ctx context.Context, req *ChatRequest) (<-chan *ChatChunk, error)
    
    // 工作流执行
    ExecuteWorkflow(ctx context.Context, req *WorkflowRequest) (*WorkflowResponse, error)
}

// 请求结构
type ChatRequest struct {
    ConversationID string            `json:"conversation_id"`
    Messages       []*schema.Message `json:"messages"`
    ModelProvider  string            `json:"model_provider"`
    ModelName      string            `json:"model_name"`
    Parameters     map[string]any    `json:"parameters"`
    WorkflowType   string            `json:"workflow_type,omitempty"`
}
```

---

## 🔍 错误处理和最佳实践

### **错误处理模式**
```go
// 统一错误处理
func handleEINOError(err error) error {
    switch {
    case errors.Is(err, schema.ErrModelNotFound):
        return fmt.Errorf("模型未找到: %w", err)
    case errors.Is(err, schema.ErrInvalidInput):
        return fmt.Errorf("输入参数无效: %w", err)
    case errors.Is(err, schema.ErrRateLimited):
        return fmt.Errorf("请求频率过高: %w", err)
    default:
        return fmt.Errorf("EINO执行错误: %w", err)
    }
}
```

### **性能优化**
```go
// 模型预热
func (s *ChatService) WarmupModels(ctx context.Context) error {
    for name, model := range s.models {
        log.Printf("预热模型: %s", name)
        _, err := model.Generate(ctx, []*schema.Message{
            {Role: "user", Content: "hello"},
        })
        if err != nil {
            log.Printf("模型预热失败 %s: %v", name, err)
        }
    }
    return nil
}

// 连接池配置
func setupHTTPClient() *http.Client {
    return &http.Client{
        Timeout: 30 * time.Second,
        Transport: &http.Transport{
            MaxIdleConns:        100,
            MaxIdleConnsPerHost: 10,
            IdleConnTimeout:     90 * time.Second,
        },
    }
}
```

---

## 🚀 部署配置

### **Docker配置**
```dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o lyss-chat-service ./cmd/

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/

COPY --from=builder /app/lyss-chat-service .
EXPOSE 8004

CMD ["./lyss-chat-service"]
```

### **环境变量**
```bash
# 服务配置
CHAT_SERVICE_PORT=8004
CHAT_SERVICE_DEBUG=false

# EINO配置
EINO_TIMEOUT=30s
EINO_MAX_RETRIES=3

# 模型配置  
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.openai.com/v1
DEEPSEEK_API_KEY=your_deepseek_key

# 数据库配置
CHAT_SERVICE_DATABASE_URL=postgresql://lyss:password@lyss-postgres:5432/lyss_chat_db
```

---

## 📊 监控和调试

### **日志配置**
```go
// 结构化日志
func setupLogger() *logrus.Logger {
    logger := logrus.New()
    logger.SetFormatter(&logrus.JSONFormatter{})
    logger.SetLevel(logrus.InfoLevel)
    return logger
}

// 请求追踪
func logChatRequest(ctx context.Context, req *ChatRequest) {
    logger.WithFields(logrus.Fields{
        "conversation_id": req.ConversationID,
        "model_provider":  req.ModelProvider,
        "model_name":     req.ModelName,
        "message_count":  len(req.Messages),
    }).Info("处理聊天请求")
}
```

### **性能监控**
```go
// 执行时间监控
func measureExecutionTime(operation string) func() {
    start := time.Now()
    return func() {
        duration := time.Since(start)
        logger.WithFields(logrus.Fields{
            "operation": operation,
            "duration":  duration.Milliseconds(),
        }).Info("操作完成")
    }
}
```

---

## 🔄 版本兼容性

- **EINO版本**: v0.3.52 (当前稳定版)
- **Go版本要求**: Go 1.21+
- **依赖管理**: 使用go.mod精确版本控制
- **升级路径**: 关注EINO官方发布，及时更新补丁版本