# API接口设计文档

## 1. API架构概述

### 1.1 设计原则
- **RESTful设计**：遵循REST设计原则，使用标准HTTP方法
- **版本控制**：使用URL路径版本控制 `/api/v1/`
- **统一响应格式**：所有API返回统一的JSON格式
- **错误处理**：标准化错误代码和错误消息
- **认证授权**：基于JWT的无状态认证
- **速率限制**：基于租户和用户的API调用限制
- **请求追踪**：每个请求包含唯一的request_id

### 1.2 API网关架构
```
Client → API Gateway → 微服务
                  ↓
            认证/授权/限流/监控
```

### 1.3 响应格式规范
```json
{
  "success": true,
  "data": {},
  "message": "操作成功",
  "request_id": "uuid-string",
  "timestamp": "2025-07-08T10:30:00Z",
  "errors": []
}
```

## 2. 认证与授权API

### 2.1 用户认证
```
POST /api/v1/auth/login
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "password123",
  "remember_me": false
}

Response:
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "user_id": "uuid",
      "email": "user@example.com",
      "username": "username",
      "tenant_id": "uuid",
      "roles": ["end_user"]
    }
  },
  "message": "登录成功"
}
```

### 2.2 刷新Token
```
POST /api/v1/auth/refresh
Content-Type: application/json
Authorization: Bearer {refresh_token}

Response:
{
  "success": true,
  "data": {
    "access_token": "new_access_token",
    "expires_in": 3600
  },
  "message": "Token刷新成功"
}
```

### 2.3 用户登出
```
POST /api/v1/auth/logout
Authorization: Bearer {access_token}

Response:
{
  "success": true,
  "message": "登出成功"
}
```

## 3. 对话管理API

### 3.1 创建对话
```
POST /api/v1/conversations
Content-Type: application/json
Authorization: Bearer {access_token}

Request Body:
{
  "title": "新的对话",
  "metadata": {
    "tags": ["work", "ai"],
    "priority": "normal"
  }
}

Response:
{
  "success": true,
  "data": {
    "conversation_id": "uuid",
    "title": "新的对话",
    "status": "active",
    "created_at": "2025-07-08T10:30:00Z",
    "updated_at": "2025-07-08T10:30:00Z",
    "message_count": 0,
    "metadata": {
      "tags": ["work", "ai"],
      "priority": "normal"
    }
  },
  "message": "对话创建成功"
}
```

### 3.2 获取对话列表
```
GET /api/v1/conversations?page=1&page_size=20&status=active&tag=work
Authorization: Bearer {access_token}

Response:
{
  "success": true,
  "data": {
    "conversations": [
      {
        "conversation_id": "uuid",
        "title": "对话标题",
        "status": "active",
        "created_at": "2025-07-08T10:30:00Z",
        "updated_at": "2025-07-08T10:30:00Z",
        "last_message_at": "2025-07-08T10:30:00Z",
        "message_count": 5,
        "summary": "对话摘要",
        "metadata": {}
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_count": 100,
      "total_pages": 5
    }
  },
  "message": "获取对话列表成功"
}
```

### 3.3 发送消息（流式响应）
```
POST /api/v1/conversations/{conversation_id}/messages/stream
Content-Type: application/json
Authorization: Bearer {access_token}

Request Body:
{
  "content": "你好，请帮我分析一下这个问题",
  "content_type": "text",
  "metadata": {
    "use_memory": true,
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "attachments": [
    {
      "type": "file",
      "url": "https://example.com/file.pdf",
      "name": "document.pdf"
    }
  ]
}

Response (Server-Sent Events):
data: {"type": "message_start", "message_id": "uuid"}

data: {"type": "content_delta", "delta": "你好"}

data: {"type": "content_delta", "delta": "！我"}

data: {"type": "content_delta", "delta": "来帮"}

data: {"type": "message_end", "message_id": "uuid", "usage": {"prompt_tokens": 50, "completion_tokens": 200, "total_tokens": 250}}
```

### 3.4 获取对话消息
```
GET /api/v1/conversations/{conversation_id}/messages?page=1&page_size=50
Authorization: Bearer {access_token}

Response:
{
  "success": true,
  "data": {
    "messages": [
      {
        "message_id": "uuid",
        "conversation_id": "uuid",
        "role": "user",
        "content": "用户消息内容",
        "content_type": "text",
        "metadata": {},
        "attachments": [],
        "created_at": "2025-07-08T10:30:00Z"
      },
      {
        "message_id": "uuid",
        "conversation_id": "uuid",
        "role": "assistant",
        "content": "AI助手回复",
        "content_type": "text",
        "metadata": {
          "model": "gpt-4",
          "provider": "openai",
          "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 200,
            "total_tokens": 250
          }
        },
        "attachments": [],
        "created_at": "2025-07-08T10:30:01Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 50,
      "total_count": 10,
      "total_pages": 1
    }
  },
  "message": "获取消息列表成功"
}
```

## 4. 记忆管理API

### 4.1 添加记忆
```
POST /api/v1/memory/add
Content-Type: application/json
Authorization: Bearer {access_token}

Request Body:
{
  "messages": [
    {
      "role": "user",
      "content": "我的名字是张三，我是一名软件工程师"
    },
    {
      "role": "assistant", 
      "content": "很高兴认识你，张三！作为软件工程师，你一定有丰富的技术经验。"
    }
  ],
  "metadata": {
    "conversation_id": "uuid",
    "importance": "high"
  }
}

Response:
{
  "success": true,
  "data": {
    "memory_id": "uuid",
    "status": "added"
  },
  "message": "记忆添加成功"
}
```

### 4.2 搜索记忆
```
GET /api/v1/memory/search?query=张三&limit=10
Authorization: Bearer {access_token}

Response:
{
  "success": true,
  "data": {
    "memories": [
      {
        "memory_id": "uuid",
        "content": "用户张三是一名软件工程师",
        "relevance_score": 0.95,
        "created_at": "2025-07-08T10:30:00Z",
        "metadata": {
          "conversation_id": "uuid",
          "importance": "high"
        }
      }
    ],
    "total_count": 1
  },
  "message": "记忆搜索成功"
}
```

### 4.3 获取用户记忆
```
GET /api/v1/memory/user?limit=50&offset=0
Authorization: Bearer {access_token}

Response:
{
  "success": true,
  "data": {
    "memories": [
      {
        "memory_id": "uuid",
        "content": "用户偏好信息",
        "category": "preference",
        "created_at": "2025-07-08T10:30:00Z",
        "updated_at": "2025-07-08T10:30:00Z"
      }
    ],
    "total_count": 10
  },
  "message": "获取用户记忆成功"
}
```

## 5. 管理员API

### 5.1 租户管理
```
GET /api/v1/admin/tenants?page=1&page_size=20
Authorization: Bearer {access_token}
X-Required-Role: super_admin

Response:
{
  "success": true,
  "data": {
    "tenants": [
      {
        "tenant_id": "uuid",
        "tenant_name": "企业A",
        "tenant_slug": "enterprise-a",
        "status": "active",
        "subscription_plan": "enterprise",
        "max_users": 100,
        "current_users": 45,
        "max_api_calls_per_month": 100000,
        "current_api_calls": 15000,
        "created_at": "2025-07-08T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_count": 5,
      "total_pages": 1
    }
  },
  "message": "获取租户列表成功"
}
```

### 5.2 用户管理
```
GET /api/v1/admin/users?page=1&page_size=20&status=active
Authorization: Bearer {access_token}
X-Required-Role: tenant_admin

Response:
{
  "success": true,
  "data": {
    "users": [
      {
        "user_id": "uuid",
        "email": "user@example.com",
        "username": "user123",
        "first_name": "张",
        "last_name": "三",
        "status": "active",
        "roles": ["end_user"],
        "last_login_at": "2025-07-08T10:30:00Z",
        "created_at": "2025-07-08T10:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_count": 45,
      "total_pages": 3
    }
  },
  "message": "获取用户列表成功"
}
```

### 5.3 AI供应商管理
```
POST /api/v1/admin/ai-providers
Content-Type: application/json
Authorization: Bearer {access_token}
X-Required-Role: tenant_admin

Request Body:
{
  "provider_name": "OpenAI",
  "provider_type": "openai",
  "display_name": "OpenAI GPT-4",
  "api_key": "sk-xxxxxxxxxxxxxxxx",
  "base_url": "https://api.openai.com/v1",
  "model_mappings": {
    "gpt-4": {
      "model_name": "gpt-4",
      "model_type": "chat",
      "context_window": 8192,
      "max_tokens": 4096,
      "supports_streaming": true,
      "supports_function_calling": true
    }
  },
  "rate_limits": {
    "requests_per_minute": 60,
    "tokens_per_minute": 60000
  }
}

Response:
{
  "success": true,
  "data": {
    "credential_id": "uuid",
    "provider_name": "OpenAI",
    "display_name": "OpenAI GPT-4",
    "status": "active",
    "created_at": "2025-07-08T10:30:00Z"
  },
  "message": "AI供应商配置成功"
}
```

### 5.4 使用统计API
```
GET /api/v1/admin/usage-stats?start_date=2025-07-01&end_date=2025-07-08&granularity=daily
Authorization: Bearer {access_token}
X-Required-Role: tenant_admin

Response:
{
  "success": true,
  "data": {
    "usage_stats": [
      {
        "date": "2025-07-08",
        "total_api_calls": 1500,
        "total_tokens": 50000,
        "total_cost_usd": 15.50,
        "unique_users": 25,
        "provider_breakdown": {
          "OpenAI": {
            "api_calls": 1200,
            "tokens": 40000,
            "cost_usd": 12.00
          },
          "Anthropic": {
            "api_calls": 300,
            "tokens": 10000,
            "cost_usd": 3.50
          }
        }
      }
    ],
    "summary": {
      "total_api_calls": 10500,
      "total_tokens": 350000,
      "total_cost_usd": 108.50,
      "average_daily_calls": 1500,
      "most_used_provider": "OpenAI"
    }
  },
  "message": "获取使用统计成功"
}
```

## 6. 系统监控API

### 6.1 健康检查
```
GET /api/v1/health
No Authorization Required

Response:
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2025-07-08T10:30:00Z",
    "version": "1.0.0",
    "services": {
      "database": "healthy",
      "redis": "healthy",
      "eino_service": "healthy",
      "memory_service": "healthy"
    },
    "metrics": {
      "uptime_seconds": 86400,
      "active_connections": 45,
      "memory_usage_percent": 65.5,
      "cpu_usage_percent": 23.2
    }
  },
  "message": "系统健康"
}
```

### 6.2 系统指标
```
GET /api/v1/metrics
Authorization: Bearer {access_token}
X-Required-Role: super_admin

Response:
{
  "success": true,
  "data": {
    "api_metrics": {
      "total_requests_today": 15000,
      "average_response_time_ms": 250,
      "error_rate_percent": 0.5,
      "rate_limit_hits": 12
    },
    "database_metrics": {
      "active_connections": 45,
      "slow_queries": 2,
      "cache_hit_ratio": 95.2,
      "database_size_gb": 2.5
    },
    "memory_metrics": {
      "total_memories": 10000,
      "search_latency_ms": 15,
      "memory_size_gb": 0.8
    }
  },
  "message": "获取系统指标成功"
}
```

## 7. 错误处理

### 7.1 错误响应格式
```json
{
  "success": false,
  "data": null,
  "message": "请求失败",
  "request_id": "uuid-string",
  "timestamp": "2025-07-08T10:30:00Z",
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "请求参数验证失败",
      "field": "email",
      "details": "邮箱格式不正确"
    }
  ]
}
```

### 7.2 标准错误代码
```
HTTP 400 - Bad Request
{
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "请求参数验证失败"
    }
  ]
}

HTTP 401 - Unauthorized
{
  "errors": [
    {
      "code": "AUTHENTICATION_REQUIRED",
      "message": "需要身份验证"
    }
  ]
}

HTTP 403 - Forbidden
{
  "errors": [
    {
      "code": "INSUFFICIENT_PERMISSIONS",
      "message": "权限不足"
    }
  ]
}

HTTP 404 - Not Found
{
  "errors": [
    {
      "code": "RESOURCE_NOT_FOUND",
      "message": "请求的资源不存在"
    }
  ]
}

HTTP 429 - Too Many Requests
{
  "errors": [
    {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "请求频率超过限制",
      "details": {
        "limit": 60,
        "remaining": 0,
        "reset_time": "2025-07-08T10:31:00Z"
      }
    }
  ]
}

HTTP 500 - Internal Server Error
{
  "errors": [
    {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "服务器内部错误"
    }
  ]
}
```

## 8. 请求限制与缓存

### 8.1 速率限制
```
Headers:
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1641718200
```

### 8.2 缓存策略
```
GET /api/v1/conversations
Cache-Control: private, max-age=300
ETag: "abc123"

GET /api/v1/admin/usage-stats
Cache-Control: private, max-age=3600
```

## 9. 分页规范

### 9.1 请求参数
```
GET /api/v1/conversations?page=1&page_size=20&sort=updated_at&order=desc
```

### 9.2 响应格式
```json
{
  "success": true,
  "data": {
    "items": [],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_count": 100,
      "total_pages": 5,
      "has_next": true,
      "has_previous": false
    }
  }
}
```

## 10. WebSocket API

### 10.1 实时通信
```
WebSocket Connection: wss://api.example.com/ws
Authorization: Bearer {access_token}

Message Types:
- conversation_update
- message_received
- typing_indicator
- system_notification

Example Message:
{
  "type": "message_received",
  "conversation_id": "uuid",
  "message": {
    "message_id": "uuid",
    "content": "新消息内容",
    "role": "assistant",
    "timestamp": "2025-07-08T10:30:00Z"
  }
}
```

这个API设计文档提供了完整的REST API规范，包括认证、对话管理、记忆系统、管理功能等核心接口的详细定义。