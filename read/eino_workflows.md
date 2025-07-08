# EINO工作流配置文档

## 1. EINO框架概述

### 1.1 什么是EINO
EINO是字节跳动开源的AI应用开发框架，专门用于构建复杂的AI工作流和图编排系统。它提供了强大的图(Graph)编排能力，允许开发者构建模块化、可复用且可进行可视化调试的AI逻辑链。

### 1.2 核心概念
- **Graph**: 工作流图，由节点和边组成
- **Node**: 工作流中的处理单元，如ChatModel、ToolsNode等
- **Edge**: 连接节点的数据流路径
- **Chain**: 简单的线性执行链
- **Compose**: 复杂的图编排工具

### 1.3 EINO在Lyss平台中的作用
- **AI模型编排**: 协调多个AI模型协同工作
- **工具调用管理**: 管理外部工具和API调用
- **复杂对话流程**: 实现多步骤、有状态的对话逻辑
- **供应商抽象**: 提供统一的AI供应商接口

## 2. EINO服务架构

### 2.1 服务部署架构
```
API Gateway (FastAPI) → EINO Service (Go) → AI Providers
                     ↓
            Memory Service (Mem0AI)
                     ↓
                   Redis
```

### 2.2 EINO服务代码结构
```
eino-service/
├── cmd/
│   └── server/
│       └── main.go              # 服务启动入口
├── internal/
│   ├── config/
│   │   └── config.go            # 配置管理
│   ├── handlers/
│   │   ├── chat.go              # 聊天处理器
│   │   ├── workflow.go          # 工作流处理器
│   │   └── health.go            # 健康检查
│   ├── workflows/
│   │   ├── optimized_rag.go     # 优化RAG工作流
│   │   ├── simple_chat.go       # 简单聊天工作流
│   │   └── tool_calling.go      # 工具调用工作流
│   ├── models/
│   │   ├── openai.go            # OpenAI模型适配器
│   │   ├── anthropic.go         # Anthropic模型适配器
│   │   └── interface.go         # 模型接口定义
│   ├── tools/
│   │   ├── web_search.go        # 网页搜索工具
│   │   ├── calculator.go        # 计算器工具
│   │   └── memory.go            # 记忆工具
│   └── middleware/
│       ├── auth.go              # 认证中间件
│       └── logging.go           # 日志中间件
├── pkg/
│   ├── errors/
│   └── utils/
├── go.mod
└── go.sum
```

### 2.3 主要配置文件
```go
// internal/config/config.go
package config

import (
    "os"
    "encoding/json"
)

type Config struct {
    Server     ServerConfig     `json:"server"`
    Database   DatabaseConfig   `json:"database"`
    AI         AIConfig         `json:"ai"`
    Memory     MemoryConfig     `json:"memory"`
    Logging    LoggingConfig    `json:"logging"`
}

type ServerConfig struct {
    Port         string `json:"port"`
    Host         string `json:"host"`
    ReadTimeout  int    `json:"read_timeout"`
    WriteTimeout int    `json:"write_timeout"`
}

type AIConfig struct {
    Providers map[string]ProviderConfig `json:"providers"`
}

type ProviderConfig struct {
    BaseURL     string            `json:"base_url"`
    APIKey      string            `json:"api_key"`
    Models      map[string]string `json:"models"`
    RateLimit   RateLimitConfig   `json:"rate_limit"`
}

type MemoryConfig struct {
    RedisURL     string `json:"redis_url"`
    Mem0APIKey   string `json:"mem0_api_key"`
    MemoryTTL    int    `json:"memory_ttl"`
}
```

## 3. 核心工作流实现

### 3.1 OptimizedRAG工作流
这是平台的核心工作流，实现了优化的检索增强生成(RAG)模式。

```go
// internal/workflows/optimized_rag.go
package workflows

import (
    "context"
    "github.com/cloudwego/eino/core/model/chat"
    "github.com/cloudwego/eino/core/model/schema"
    "github.com/cloudwego/eino/core/orchestration/compose"
    "github.com/cloudwego/eino/core/tools"
)

// OptimizedRAGWorkflow 优化的RAG工作流
type OptimizedRAGWorkflow struct {
    graph *compose.Graph[*schema.Message, *schema.Message]
}

// NewOptimizedRAGWorkflow 创建新的OptimizedRAG工作流
func NewOptimizedRAGWorkflow(providers map[string]chat.ChatModel) *OptimizedRAGWorkflow {
    g := compose.NewGraph[*schema.Message, *schema.Message]()
    
    // 定义节点键
    const (
        nodeKeyOfOptimizer      = "PromptOptimizer"
        nodeKeyOfResponder      = "CoreResponder"
        nodeKeyOfToolSelector   = "ToolSelector"
        nodeKeyOfToolExecutor   = "ToolExecutor"
        nodeKeyOfSynthesizer    = "FinalSynthesizer"
        nodeKeyOfMemoryRetriever = "MemoryRetriever"
    )
    
    // 1. 记忆检索节点
    memoryRetriever := NewMemoryRetrieverNode()
    _ = g.AddLambdaNode(nodeKeyOfMemoryRetriever, memoryRetriever)
    
    // 2. 提示词优化节点 (使用快速小模型)
    promptOptimizer := providers["gpt-4o-mini"] // 或其他快速模型
    promptOptimizerTemplate := chat.NewChatTemplate(chat.ChatTemplateConfig{
        SystemPrompt: `你是一个提示词优化助手。根据用户的查询和相关记忆上下文，
        将查询重写为一个清晰、自包含且为强大AI模型优化的提示词。
        消除歧义，保持原意，并利用上下文信息。`,
    })
    _ = g.AddChatModelNode(nodeKeyOfOptimizer, 
        compose.NewChatModelNode(promptOptimizer, promptOptimizerTemplate))
    
    // 3. 核心应答节点 (使用强大模型)
    coreResponder := providers["gpt-4o"] // 或其他强大模型
    coreResponderTemplate := chat.NewChatTemplate(chat.ChatTemplateConfig{
        SystemPrompt: `你是一个知识渊博、乐于助人的AI助手。
        请基于优化后的查询提供详尽、准确的回答。
        如果需要使用工具获取实时信息，请在回答中说明。`,
    })
    _ = g.AddChatModelNode(nodeKeyOfResponder,
        compose.NewChatModelNode(coreResponder, coreResponderTemplate))
    
    // 4. 工具选择节点
    toolSelector := providers["gpt-4o-mini"]
    toolSelectorTemplate := chat.NewChatTemplate(chat.ChatTemplateConfig{
        SystemPrompt: `你是一个工具选择专家。分析用户的查询和初步回答，
        判断是否需要使用工具获取额外信息。如果需要，选择合适的工具并构造调用参数。`,
    })
    _ = g.AddChatModelNode(nodeKeyOfToolSelector,
        compose.NewChatModelNode(toolSelector, toolSelectorTemplate))
    
    // 5. 工具执行节点
    toolExecutor := NewToolExecutorNode()
    _ = g.AddToolsNode(nodeKeyOfToolExecutor, toolExecutor)
    
    // 6. 最终合成节点
    finalSynthesizer := providers["gpt-4o"]
    synthesizerTemplate := chat.NewChatTemplate(chat.ChatTemplateConfig{
        SystemPrompt: `你是一个内容合成专家。将初步回答和工具查询结果
        合成为一个连贯、完整、准确的最终答案。`,
    })
    _ = g.AddChatModelNode(nodeKeyOfSynthesizer,
        compose.NewChatModelNode(finalSynthesizer, synthesizerTemplate))
    
    // 定义数据流边
    _ = g.AddEdge(compose.NewEdge(compose.GraphInput, 0, nodeKeyOfMemoryRetriever, 0))
    _ = g.AddEdge(compose.NewEdge(nodeKeyOfMemoryRetriever, 0, nodeKeyOfOptimizer, 0))
    _ = g.AddEdge(compose.NewEdge(nodeKeyOfOptimizer, 0, nodeKeyOfResponder, 0))
    _ = g.AddEdge(compose.NewEdge(nodeKeyOfResponder, 0, nodeKeyOfToolSelector, 0))
    
    // 条件边：是否需要工具调用
    _ = g.AddConditionalEdge(nodeKeyOfToolSelector, 
        func(state any) string {
            // 检查是否需要工具调用
            if needsToolCall(state) {
                return nodeKeyOfToolExecutor
            }
            return nodeKeyOfSynthesizer
        })
    
    _ = g.AddEdge(compose.NewEdge(nodeKeyOfToolExecutor, 0, nodeKeyOfSynthesizer, 0))
    _ = g.AddEdge(compose.NewEdge(nodeKeyOfSynthesizer, 0, compose.GraphOutput, 0))
    
    return &OptimizedRAGWorkflow{graph: g}
}

// Execute 执行工作流
func (w *OptimizedRAGWorkflow) Execute(ctx context.Context, input *schema.Message) (*schema.Message, error) {
    return w.graph.Run(ctx, input)
}

// ExecuteStream 流式执行工作流
func (w *OptimizedRAGWorkflow) ExecuteStream(ctx context.Context, input *schema.Message, callback func(*schema.Message)) error {
    // 实现流式执行逻辑
    result, err := w.graph.Run(ctx, input)
    if err != nil {
        return err
    }
    
    // 模拟流式输出
    content := result.Content
    for i := 0; i < len(content); i += 5 {
        end := i + 5
        if end > len(content) {
            end = len(content)
        }
        
        chunk := &schema.Message{
            Role:    "assistant",
            Content: content[i:end],
        }
        callback(chunk)
    }
    
    return nil
}
```

### 3.2 简单聊天工作流
```go
// internal/workflows/simple_chat.go
package workflows

import (
    "context"
    "github.com/cloudwego/eino/core/model/chat"
    "github.com/cloudwego/eino/core/model/schema"
    "github.com/cloudwego/eino/core/orchestration/chain"
)

// SimpleChatWorkflow 简单聊天工作流
type SimpleChatWorkflow struct {
    chain *chain.Chain[*schema.Message, *schema.Message]
}

// NewSimpleChatWorkflow 创建简单聊天工作流
func NewSimpleChatWorkflow(model chat.ChatModel) *SimpleChatWorkflow {
    // 创建聊天模板
    template := chat.NewChatTemplate(chat.ChatTemplateConfig{
        SystemPrompt: `你是一个友好、乐于助人的AI助手。
        请以自然、对话的方式回答用户的问题。`,
    })
    
    // 创建链
    c := chain.NewChain[*schema.Message, *schema.Message]()
    c.AddChatModel(model, template)
    
    return &SimpleChatWorkflow{chain: c}
}

// Execute 执行简单聊天
func (w *SimpleChatWorkflow) Execute(ctx context.Context, input *schema.Message) (*schema.Message, error) {
    return w.chain.Run(ctx, input)
}
```

### 3.3 工具调用工作流
```go
// internal/workflows/tool_calling.go
package workflows

import (
    "context"
    "github.com/cloudwego/eino/core/model/chat"
    "github.com/cloudwego/eino/core/model/schema"
    "github.com/cloudwego/eino/core/orchestration/compose"
    "github.com/cloudwego/eino/core/tools"
)

// ToolCallingWorkflow 工具调用工作流
type ToolCallingWorkflow struct {
    graph *compose.Graph[*schema.Message, *schema.Message]
}

// NewToolCallingWorkflow 创建工具调用工作流
func NewToolCallingWorkflow(model chat.ChatModel, availableTools []tools.Tool) *ToolCallingWorkflow {
    g := compose.NewGraph[*schema.Message, *schema.Message]()
    
    const (
        nodeKeyOfPlanner  = "TaskPlanner"
        nodeKeyOfExecutor = "ToolExecutor"
        nodeKeyOfReviewer = "ResultReviewer"
    )
    
    // 任务规划节点
    plannerTemplate := chat.NewChatTemplate(chat.ChatTemplateConfig{
        SystemPrompt: `你是一个任务规划专家。分析用户的请求，
        制定使用工具完成任务的计划。可用工具列表：` + formatToolList(availableTools),
    })
    _ = g.AddChatModelNode(nodeKeyOfPlanner,
        compose.NewChatModelNode(model, plannerTemplate))
    
    // 工具执行节点
    toolExecutor := tools.NewToolsNode(availableTools...)
    _ = g.AddToolsNode(nodeKeyOfExecutor, toolExecutor)
    
    // 结果审查节点
    reviewerTemplate := chat.NewChatTemplate(chat.ChatTemplateConfig{
        SystemPrompt: `你是一个结果审查专家。基于工具执行结果，
        生成最终的回答。确保回答准确、完整、有用。`,
    })
    _ = g.AddChatModelNode(nodeKeyOfReviewer,
        compose.NewChatModelNode(model, reviewerTemplate))
    
    // 定义边
    _ = g.AddEdge(compose.NewEdge(compose.GraphInput, 0, nodeKeyOfPlanner, 0))
    _ = g.AddEdge(compose.NewEdge(nodeKeyOfPlanner, 0, nodeKeyOfExecutor, 0))
    _ = g.AddEdge(compose.NewEdge(nodeKeyOfExecutor, 0, nodeKeyOfReviewer, 0))
    _ = g.AddEdge(compose.NewEdge(nodeKeyOfReviewer, 0, compose.GraphOutput, 0))
    
    return &ToolCallingWorkflow{graph: g}
}

// formatToolList 格式化工具列表
func formatToolList(tools []tools.Tool) string {
    var result string
    for _, tool := range tools {
        result += "- " + tool.Name() + ": " + tool.Description() + "\n"
    }
    return result
}
```

## 4. 工具实现

### 4.1 网页搜索工具
```go
// internal/tools/web_search.go
package tools

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "net/url"
    
    "github.com/cloudwego/eino/core/tools"
)

// WebSearchTool 网页搜索工具
type WebSearchTool struct {
    apiKey   string
    endpoint string
}

// WebSearchInput 搜索输入参数
type WebSearchInput struct {
    Query string `json:"query" jsonschema:"title=Search Query,description=搜索关键词"`
    Count int    `json:"count,omitempty" jsonschema:"title=Result Count,description=返回结果数量,default=5"`
}

// WebSearchResult 搜索结果
type WebSearchResult struct {
    Title   string `json:"title"`
    URL     string `json:"url"`
    Snippet string `json:"snippet"`
}

// NewWebSearchTool 创建网页搜索工具
func NewWebSearchTool(apiKey, endpoint string) *WebSearchTool {
    return &WebSearchTool{
        apiKey:   apiKey,
        endpoint: endpoint,
    }
}

// Name 工具名称
func (t *WebSearchTool) Name() string {
    return "web_search"
}

// Description 工具描述
func (t *WebSearchTool) Description() string {
    return "搜索网页内容，获取实时信息"
}

// InputSchema 输入参数结构
func (t *WebSearchTool) InputSchema() any {
    return &WebSearchInput{}
}

// Run 执行搜索
func (t *WebSearchTool) Run(ctx context.Context, input any) (any, error) {
    searchInput, ok := input.(*WebSearchInput)
    if !ok {
        return nil, fmt.Errorf("invalid input type")
    }
    
    // 构建搜索URL
    params := url.Values{}
    params.Set("q", searchInput.Query)
    params.Set("count", fmt.Sprintf("%d", searchInput.Count))
    searchURL := fmt.Sprintf("%s?%s", t.endpoint, params.Encode())
    
    // 创建HTTP请求
    req, err := http.NewRequestWithContext(ctx, "GET", searchURL, nil)
    if err != nil {
        return nil, err
    }
    req.Header.Set("X-API-Key", t.apiKey)
    
    // 发送请求
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    // 解析响应
    var results []WebSearchResult
    if err := json.NewDecoder(resp.Body).Decode(&results); err != nil {
        return nil, err
    }
    
    return results, nil
}
```

### 4.2 计算器工具
```go
// internal/tools/calculator.go
package tools

import (
    "context"
    "fmt"
    "go/ast"
    "go/parser"
    "go/token"
    "strconv"
)

// CalculatorTool 计算器工具
type CalculatorTool struct{}

// CalculatorInput 计算输入
type CalculatorInput struct {
    Expression string `json:"expression" jsonschema:"title=Mathematical Expression,description=要计算的数学表达式"`
}

// NewCalculatorTool 创建计算器工具
func NewCalculatorTool() *CalculatorTool {
    return &CalculatorTool{}
}

// Name 工具名称
func (t *CalculatorTool) Name() string {
    return "calculator"
}

// Description 工具描述
func (t *CalculatorTool) Description() string {
    return "计算数学表达式，支持基本的四则运算"
}

// InputSchema 输入参数结构
func (t *CalculatorTool) InputSchema() any {
    return &CalculatorInput{}
}

// Run 执行计算
func (t *CalculatorTool) Run(ctx context.Context, input any) (any, error) {
    calcInput, ok := input.(*CalculatorInput)
    if !ok {
        return nil, fmt.Errorf("invalid input type")
    }
    
    result, err := t.evaluate(calcInput.Expression)
    if err != nil {
        return nil, err
    }
    
    return map[string]interface{}{
        "expression": calcInput.Expression,
        "result":     result,
    }, nil
}

// evaluate 计算表达式
func (t *CalculatorTool) evaluate(expr string) (float64, error) {
    // 使用Go的AST解析器安全地计算表达式
    node, err := parser.ParseExpr(expr)
    if err != nil {
        return 0, err
    }
    
    return t.evaluateNode(node)
}

// evaluateNode 递归计算AST节点
func (t *CalculatorTool) evaluateNode(node ast.Expr) (float64, error) {
    switch n := node.(type) {
    case *ast.BasicLit:
        if n.Kind == token.INT || n.Kind == token.FLOAT {
            return strconv.ParseFloat(n.Value, 64)
        }
        return 0, fmt.Errorf("unsupported literal: %s", n.Value)
        
    case *ast.BinaryExpr:
        left, err := t.evaluateNode(n.X)
        if err != nil {
            return 0, err
        }
        right, err := t.evaluateNode(n.Y)
        if err != nil {
            return 0, err
        }
        
        switch n.Op {
        case token.ADD:
            return left + right, nil
        case token.SUB:
            return left - right, nil
        case token.MUL:
            return left * right, nil
        case token.QUO:
            if right == 0 {
                return 0, fmt.Errorf("division by zero")
            }
            return left / right, nil
        default:
            return 0, fmt.Errorf("unsupported operator: %s", n.Op)
        }
        
    case *ast.ParenExpr:
        return t.evaluateNode(n.X)
        
    default:
        return 0, fmt.Errorf("unsupported expression type")
    }
}
```

### 4.3 记忆工具
```go
// internal/tools/memory.go
package tools

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "bytes"
)

// MemoryTool 记忆工具
type MemoryTool struct {
    memoryServiceURL string
}

// MemorySearchInput 记忆搜索输入
type MemorySearchInput struct {
    Query  string `json:"query" jsonschema:"title=Search Query,description=搜索记忆的关键词"`
    Limit  int    `json:"limit,omitempty" jsonschema:"title=Result Limit,description=返回结果数量,default=5"`
    UserID string `json:"user_id" jsonschema:"title=User ID,description=用户ID"`
}

// MemoryAddInput 记忆添加输入
type MemoryAddInput struct {
    Content string `json:"content" jsonschema:"title=Memory Content,description=要记住的内容"`
    UserID  string `json:"user_id" jsonschema:"title=User ID,description=用户ID"`
}

// NewMemoryTool 创建记忆工具
func NewMemoryTool(memoryServiceURL string) *MemoryTool {
    return &MemoryTool{
        memoryServiceURL: memoryServiceURL,
    }
}

// Name 工具名称
func (t *MemoryTool) Name() string {
    return "memory_search"
}

// Description 工具描述
func (t *MemoryTool) Description() string {
    return "搜索用户的历史记忆和偏好信息"
}

// InputSchema 输入参数结构
func (t *MemoryTool) InputSchema() any {
    return &MemorySearchInput{}
}

// Run 执行记忆搜索
func (t *MemoryTool) Run(ctx context.Context, input any) (any, error) {
    searchInput, ok := input.(*MemorySearchInput)
    if !ok {
        return nil, fmt.Errorf("invalid input type")
    }
    
    // 构建请求
    requestBody, err := json.Marshal(map[string]interface{}{
        "query": searchInput.Query,
        "limit": searchInput.Limit,
        "user_id": searchInput.UserID,
    })
    if err != nil {
        return nil, err
    }
    
    // 发送HTTP请求到记忆服务
    req, err := http.NewRequestWithContext(ctx, "POST", 
        t.memoryServiceURL+"/search", bytes.NewBuffer(requestBody))
    if err != nil {
        return nil, err
    }
    req.Header.Set("Content-Type", "application/json")
    
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    // 解析响应
    var result map[string]interface{}
    if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
        return nil, err
    }
    
    return result, nil
}
```

## 5. 服务处理器

### 5.1 聊天处理器
```go
// internal/handlers/chat.go
package handlers

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
    
    "github.com/gin-gonic/gin"
    "your-project/internal/workflows"
)

// ChatHandler 聊天处理器
type ChatHandler struct {
    workflows map[string]workflows.Workflow
}

// ChatRequest 聊天请求
type ChatRequest struct {
    ConversationID string                 `json:"conversation_id"`
    Message        string                 `json:"message"`
    WorkflowType   string                 `json:"workflow_type,omitempty"`
    Parameters     map[string]interface{} `json:"parameters,omitempty"`
    UserID         string                 `json:"user_id"`
    TenantID       string                 `json:"tenant_id"`
}

// NewChatHandler 创建聊天处理器
func NewChatHandler() *ChatHandler {
    return &ChatHandler{
        workflows: make(map[string]workflows.Workflow),
    }
}

// RegisterWorkflow 注册工作流
func (h *ChatHandler) RegisterWorkflow(name string, workflow workflows.Workflow) {
    h.workflows[name] = workflow
}

// HandleChat 处理聊天请求
func (h *ChatHandler) HandleChat(c *gin.Context) {
    var req ChatRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    // 默认使用OptimizedRAG工作流
    workflowType := req.WorkflowType
    if workflowType == "" {
        workflowType = "optimized_rag"
    }
    
    workflow, exists := h.workflows[workflowType]
    if !exists {
        c.JSON(http.StatusBadRequest, gin.H{"error": "unknown workflow type"})
        return
    }
    
    // 构造输入消息
    input := &schema.Message{
        Role:    "user",
        Content: req.Message,
        Extra: map[string]interface{}{
            "user_id":         req.UserID,
            "tenant_id":       req.TenantID,
            "conversation_id": req.ConversationID,
            "parameters":      req.Parameters,
        },
    }
    
    // 执行工作流
    ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
    defer cancel()
    
    result, err := workflow.Execute(ctx, input)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    // 返回结果
    c.JSON(http.StatusOK, gin.H{
        "success": true,
        "data": gin.H{
            "message_id":      generateMessageID(),
            "conversation_id": req.ConversationID,
            "content":         result.Content,
            "role":            result.Role,
            "created_at":      time.Now().UTC(),
        },
    })
}

// HandleChatStream 处理流式聊天请求
func (h *ChatHandler) HandleChatStream(c *gin.Context) {
    var req ChatRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    // 设置SSE响应头
    c.Header("Content-Type", "text/event-stream")
    c.Header("Cache-Control", "no-cache")
    c.Header("Connection", "keep-alive")
    c.Header("Access-Control-Allow-Origin", "*")
    
    // 获取工作流
    workflowType := req.WorkflowType
    if workflowType == "" {
        workflowType = "optimized_rag"
    }
    
    workflow, exists := h.workflows[workflowType]
    if !exists {
        c.String(http.StatusBadRequest, "data: {\"error\": \"unknown workflow type\"}\n\n")
        return
    }
    
    // 构造输入
    input := &schema.Message{
        Role:    "user",
        Content: req.Message,
        Extra: map[string]interface{}{
            "user_id":         req.UserID,
            "tenant_id":       req.TenantID,
            "conversation_id": req.ConversationID,
        },
    }
    
    // 流式执行
    ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
    defer cancel()
    
    messageID := generateMessageID()
    
    // 发送开始事件
    c.String(http.StatusOK, "data: %s\n\n", 
        mustMarshal(map[string]interface{}{
            "type":       "message_start",
            "message_id": messageID,
        }))
    c.Writer.Flush()
    
    // 执行流式工作流
    err := workflow.ExecuteStream(ctx, input, func(chunk *schema.Message) {
        // 发送内容块
        c.String(http.StatusOK, "data: %s\n\n",
            mustMarshal(map[string]interface{}{
                "type":  "content_delta",
                "delta": chunk.Content,
            }))
        c.Writer.Flush()
    })
    
    if err != nil {
        c.String(http.StatusOK, "data: %s\n\n",
            mustMarshal(map[string]interface{}{
                "type":  "error",
                "error": err.Error(),
            }))
    } else {
        // 发送结束事件
        c.String(http.StatusOK, "data: %s\n\n",
            mustMarshal(map[string]interface{}{
                "type":       "message_end",
                "message_id": messageID,
            }))
    }
    
    c.Writer.Flush()
}

// generateMessageID 生成消息ID
func generateMessageID() string {
    return fmt.Sprintf("msg_%d", time.Now().UnixNano())
}

// mustMarshal JSON序列化（忽略错误）
func mustMarshal(v interface{}) string {
    data, _ := json.Marshal(v)
    return string(data)
}
```

## 6. 配置管理

### 6.1 工作流配置文件
```yaml
# config/workflows.yaml
workflows:
  optimized_rag:
    name: "OptimizedRAG"
    description: "优化的检索增强生成工作流"
    enabled: true
    nodes:
      memory_retriever:
        type: "lambda"
        config:
          memory_service_url: "${MEMORY_SERVICE_URL}"
      prompt_optimizer:
        type: "chat_model"
        provider: "openai"
        model: "gpt-4o-mini"
        config:
          temperature: 0.3
          max_tokens: 500
      core_responder:
        type: "chat_model"
        provider: "openai"
        model: "gpt-4o"
        config:
          temperature: 0.7
          max_tokens: 2000
      tool_selector:
        type: "chat_model"
        provider: "openai"
        model: "gpt-4o-mini"
        config:
          temperature: 0.1
          max_tokens: 200
      final_synthesizer:
        type: "chat_model"
        provider: "openai"
        model: "gpt-4o"
        config:
          temperature: 0.7
          max_tokens: 2000
    tools:
      - name: "web_search"
        enabled: true
        config:
          api_key: "${WEB_SEARCH_API_KEY}"
          endpoint: "${WEB_SEARCH_ENDPOINT}"
      - name: "calculator"
        enabled: true
      - name: "memory_search"
        enabled: true
        config:
          memory_service_url: "${MEMORY_SERVICE_URL}"

  simple_chat:
    name: "SimpleChat"
    description: "简单聊天工作流"
    enabled: true
    model:
      provider: "openai"
      model: "gpt-4o"
      config:
        temperature: 0.8
        max_tokens: 1500

  tool_calling:
    name: "ToolCalling"
    description: "工具调用工作流"
    enabled: true
    model:
      provider: "openai"
      model: "gpt-4o"
      config:
        temperature: 0.5
        max_tokens: 1500
    tools:
      - "web_search"
      - "calculator"
      - "memory_search"
```

### 6.2 供应商配置
```yaml
# config/providers.yaml
providers:
  openai:
    name: "OpenAI"
    base_url: "https://api.openai.com/v1"
    api_key: "${OPENAI_API_KEY}"
    models:
      gpt-4o: "gpt-4o"
      gpt-4o-mini: "gpt-4o-mini"
      gpt-3.5-turbo: "gpt-3.5-turbo"
    rate_limit:
      requests_per_minute: 500
      tokens_per_minute: 30000
    retry:
      max_attempts: 3
      backoff_factor: 2
    timeout: 30

  anthropic:
    name: "Anthropic"
    base_url: "https://api.anthropic.com"
    api_key: "${ANTHROPIC_API_KEY}"
    models:
      claude-3-opus: "claude-3-opus-20240229"
      claude-3-sonnet: "claude-3-sonnet-20240229"
      claude-3-haiku: "claude-3-haiku-20240307"
    rate_limit:
      requests_per_minute: 100
      tokens_per_minute: 10000
    retry:
      max_attempts: 3
      backoff_factor: 2
    timeout: 30

  google:
    name: "Google"
    base_url: "https://generativelanguage.googleapis.com/v1"
    api_key: "${GOOGLE_API_KEY}"
    models:
      gemini-pro: "gemini-pro"
      gemini-pro-vision: "gemini-pro-vision"
    rate_limit:
      requests_per_minute: 60
      tokens_per_minute: 15000
    retry:
      max_attempts: 3
      backoff_factor: 2
    timeout: 30
```

## 7. 部署配置

### 7.1 Docker配置
```dockerfile
# Dockerfile
FROM golang:1.21-alpine AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o eino-service cmd/server/main.go

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/

COPY --from=builder /app/eino-service .
COPY --from=builder /app/config ./config

CMD ["./eino-service"]
```

### 7.2 Docker Compose配置
```yaml
# docker-compose.yml (EINO service部分)
version: '3.8'

services:
  eino-service:
    build: ./eino-service
    ports:
      - "8080:8080"
    environment:
      - SERVER_PORT=8080
      - REDIS_URL=redis://redis:6379
      - MEMORY_SERVICE_URL=http://memory-service:8000
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - WEB_SEARCH_API_KEY=${WEB_SEARCH_API_KEY}
    depends_on:
      - redis
      - memory-service
    volumes:
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

这个EINO工作流配置文档提供了完整的工作流设计、实现和配置方案，是平台AI编排能力的核心技术文档。