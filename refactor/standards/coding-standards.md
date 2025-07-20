# 编码规范标准

## 📋 文档概述

统一的编码规范和最佳实践，确保代码质量、可读性和可维护性。

---

## 📝 通用编码原则

### **代码注释规范**
- **中文注释** - 所有注释必须使用中文
- **注释密度** - 复杂逻辑必须添加注释说明
- **文档字符串** - 所有公共函数/类必须有文档字符串

### **错误处理原则**
- **明确异常类型** - 使用具体的异常类型，不使用通用Exception
- **日志记录** - 所有异常都必须记录日志
- **用户友好** - 向用户显示友好的错误信息

### **安全编码原则**
- **输入验证** - 所有外部输入必须验证
- **SQL注入防护** - 使用参数化查询
- **敏感信息保护** - 不在日志中记录敏感信息

---

## 🐍 Python编码规范 (FastAPI)

### **文件头注释**
```python
"""
用户服务 - 用户管理相关业务逻辑

该模块负责处理用户的注册、登录、权限管理等核心功能。
包含用户信息的CRUD操作和租户隔离逻辑。

Author: Lyss AI Team
Created: 2025-01-20
Modified: 2025-01-20
"""
```

### **导入顺序规范**
```python
# 1. 标准库导入
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

# 2. 第三方库导入
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy import Column, String, DateTime
from redis import Redis

# 3. 本地导入
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
```

### **类定义规范**
```python
class UserService:
    """
    用户服务类
    
    负责处理用户相关的业务逻辑，包括用户注册、登录验证、
    权限管理等功能。确保多租户数据隔离。
    """
    
    def __init__(self, db_session, redis_client: Redis):
        """
        初始化用户服务
        
        Args:
            db_session: 数据库会话对象
            redis_client: Redis客户端对象
        """
        self.db = db_session
        self.redis = redis_client
        self.logger = logging.getLogger(__name__)
    
    async def create_user(self, user_data: UserCreate, tenant_id: str) -> UserResponse:
        """
        创建新用户
        
        Args:
            user_data: 用户创建数据，包含邮箱、密码等信息
            tenant_id: 租户ID，用于数据隔离
            
        Returns:
            UserResponse: 创建成功的用户信息
            
        Raises:
            HTTPException: 当邮箱已存在或数据验证失败时抛出
        """
        try:
            # 检查邮箱是否已存在（在同一租户内）
            existing_user = await self._get_user_by_email(
                email=user_data.email, 
                tenant_id=tenant_id
            )
            if existing_user:
                self.logger.warning(f"尝试创建已存在的用户: {user_data.email}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="该邮箱已被注册"
                )
            
            # 创建用户逻辑
            user = await self._create_user_in_db(user_data, tenant_id)
            
            # 缓存用户信息
            await self._cache_user_info(user)
            
            self.logger.info(f"成功创建用户: {user.email}")
            return UserResponse.from_orm(user)
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"创建用户失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="用户创建失败"
            )
```

### **API路由规范**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.core.dependencies import get_current_user, get_tenant_context

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_context),
    user_service: UserService = Depends(get_user_service)
):
    """
    创建新用户
    
    创建一个新的用户账户。只有租户管理员才能执行此操作。
    
    Args:
        user_data: 用户创建信息
        current_user: 当前登录用户（通过JWT获取）
        tenant_id: 租户ID（从JWT中提取）
        user_service: 用户服务实例
        
    Returns:
        UserResponse: 创建的用户信息
        
    Raises:
        HTTPException 403: 权限不足
        HTTPException 409: 邮箱已存在
        HTTPException 422: 数据验证失败
    """
    # 权限检查
    if current_user.role not in ["super_admin", "tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：只有管理员才能创建用户"
        )
    
    return await user_service.create_user(user_data, tenant_id)

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_tenant_context),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取用户信息
    
    根据用户ID获取用户详细信息。用户只能查看自己的信息，
    管理员可以查看租户内所有用户信息。
    """
    # 权限检查：用户只能查看自己的信息，管理员可以查看所有
    if (current_user.id != user_id and 
        current_user.role not in ["super_admin", "tenant_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足：只能查看自己的用户信息"
        )
    
    user = await user_service.get_user_by_id(user_id, tenant_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user
```

### **数据模型规范**
```python
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    """用户基础模型"""
    email: EmailStr = Field(..., description="用户邮箱地址")
    full_name: str = Field(..., min_length=2, max_length=100, description="用户姓名")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")

class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=8, max_length=100, description="用户密码")
    
    @validator('password')
    def validate_password(cls, v):
        """密码强度验证"""
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v

class UserResponse(UserBase):
    """用户响应模型"""
    id: UUID = Field(..., description="用户唯一标识")
    tenant_id: UUID = Field(..., description="租户ID")
    status: str = Field(..., description="用户状态")
    role: str = Field(..., description="用户角色")
    email_verified: bool = Field(..., description="邮箱验证状态")
    created_at: datetime = Field(..., description="创建时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "full_name": "张三",
                "username": "zhangsan",
                "tenant_id": "123e4567-e89b-12d3-a456-426614174001",
                "status": "active",
                "role": "end_user",
                "email_verified": True,
                "created_at": "2025-01-20T10:30:00Z",
                "last_login_at": "2025-01-20T15:45:00Z"
            }
        }
```

### **异常处理规范**
```python
from app.core.exceptions import (
    UserNotFoundError, 
    DuplicateEmailError, 
    InvalidCredentialsError
)

class UserService:
    async def authenticate_user(self, email: str, password: str, tenant_id: str) -> User:
        """
        用户认证
        
        验证用户邮箱和密码，返回认证成功的用户对象
        """
        try:
            # 查找用户
            user = await self.repository.get_by_email(email, tenant_id)
            if not user:
                self.logger.warning(f"登录失败：用户不存在 {email}")
                raise UserNotFoundError(f"用户 {email} 不存在")
            
            # 验证密码
            if not self.verify_password(password, user.password_hash):
                self.logger.warning(f"登录失败：密码错误 {email}")
                raise InvalidCredentialsError("邮箱或密码错误")
            
            # 检查用户状态
            if user.status != "active":
                self.logger.warning(f"登录失败：用户状态异常 {email}")
                raise InvalidCredentialsError("用户账户已被禁用")
            
            # 更新最后登录时间
            await self.repository.update_last_login(user.id)
            
            self.logger.info(f"用户登录成功: {email}")
            return user
            
        except (UserNotFoundError, InvalidCredentialsError):
            # 重新抛出业务异常
            raise
        except Exception as e:
            # 记录未预期的错误
            self.logger.error(f"用户认证过程中发生未预期错误: {str(e)}")
            raise InvalidCredentialsError("认证服务暂时不可用")
```

---

## 🐹 Go编码规范

### **包和文件注释**
```go
// Package handlers 提供HTTP请求处理器
//
// 该包包含所有HTTP路由的处理逻辑，负责处理请求验证、
// 业务逻辑调用和响应格式化。
//
// 作者: Lyss AI Team
// 创建时间: 2025-01-20
package handlers

import (
    "context"
    "net/http"
    "time"
    
    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
    
    "lyss-chat-service/internal/models"
    "lyss-chat-service/internal/services"
)
```

### **结构体定义规范**
```go
// ChatRequest 对话请求结构
type ChatRequest struct {
    ConversationID string                 `json:"conversation_id" binding:"required"`
    UserID         string                 `json:"user_id" binding:"required"`
    Message        string                 `json:"message" binding:"required,min=1,max=4000"`
    ModelName      string                 `json:"model_name" binding:"required"`
    UserToken      string                 `json:"user_token" binding:"required"`
    Temperature    float32                `json:"temperature" binding:"min=0,max=2"`
    MaxTokens      int                    `json:"max_tokens" binding:"min=1,max=8000"`
    Stream         bool                   `json:"stream"`
    Metadata       map[string]interface{} `json:"metadata,omitempty"`
}

// ChatResponse 对话响应结构
type ChatResponse struct {
    ConversationID string    `json:"conversation_id"`
    MessageID      string    `json:"message_id"`
    Content        string    `json:"content"`
    Model          string    `json:"model"`
    Usage          Usage     `json:"usage"`
    CreatedAt      time.Time `json:"created_at"`
}

// Usage 使用量统计
type Usage struct {
    PromptTokens     int `json:"prompt_tokens"`
    CompletionTokens int `json:"completion_tokens"`
    TotalTokens      int `json:"total_tokens"`
}
```

### **方法定义规范**
```go
// ChatHandler 对话处理器
type ChatHandler struct {
    chatService    services.ChatService
    providerClient *clients.ProviderClient
    logger         *slog.Logger
}

// NewChatHandler 创建新的对话处理器
func NewChatHandler(
    chatService services.ChatService,
    providerClient *clients.ProviderClient,
    logger *slog.Logger,
) *ChatHandler {
    return &ChatHandler{
        chatService:    chatService,
        providerClient: providerClient,
        logger:         logger,
    }
}

// ProcessMessage 处理对话消息
//
// 该方法负责处理用户的对话请求，包括模型选择、
// 提示词增强、流式响应处理等功能。
//
// 参数:
//   - ctx: 请求上下文
//   - c: Gin上下文对象
//
// 响应:
//   - 成功: 返回流式对话响应
//   - 失败: 返回错误信息
func (h *ChatHandler) ProcessMessage(ctx context.Context, c *gin.Context) {
    // 解析请求参数
    var req ChatRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        h.logger.Warn("请求参数验证失败", 
            "error", err.Error(),
            "user_id", req.UserID)
        c.JSON(http.StatusBadRequest, gin.H{
            "success": false,
            "error": map[string]interface{}{
                "code":    "INVALID_REQUEST",
                "message": "请求参数格式错误",
                "details": err.Error(),
            },
            "timestamp":  time.Now().UTC(),
            "request_id": getRequestID(c),
        })
        return
    }
    
    // 验证用户权限
    if err := h.validateUserPermission(ctx, req.UserID, req.UserToken); err != nil {
        h.logger.Warn("用户权限验证失败",
            "user_id", req.UserID,
            "error", err.Error())
        c.JSON(http.StatusUnauthorized, gin.H{
            "success": false,
            "error": map[string]interface{}{
                "code":    "UNAUTHORIZED",
                "message": "用户权限验证失败",
            },
            "timestamp":  time.Now().UTC(),
            "request_id": getRequestID(c),
        })
        return
    }
    
    // 处理对话请求
    if req.Stream {
        h.handleStreamingChat(ctx, c, &req)
    } else {
        h.handleNormalChat(ctx, c, &req)
    }
}

// handleStreamingChat 处理流式对话
func (h *ChatHandler) handleStreamingChat(ctx context.Context, c *gin.Context, req *ChatRequest) {
    // 设置流式响应头
    c.Header("Content-Type", "text/event-stream")
    c.Header("Cache-Control", "no-cache")
    c.Header("Connection", "keep-alive")
    c.Header("Access-Control-Allow-Origin", "*")
    
    // 创建流式响应通道
    eventChan, err := h.chatService.ProcessMessageStream(ctx, req)
    if err != nil {
        h.logger.Error("创建流式对话失败",
            "conversation_id", req.ConversationID,
            "error", err.Error())
        c.JSON(http.StatusInternalServerError, gin.H{
            "success": false,
            "error": map[string]interface{}{
                "code":    "STREAM_ERROR",
                "message": "流式对话创建失败",
            },
        })
        return
    }
    
    // 发送流式事件
    c.Stream(func(w io.Writer) bool {
        select {
        case event, ok := <-eventChan:
            if !ok {
                // 通道已关闭
                return false
            }
            
            // 发送事件数据
            eventData, _ := json.Marshal(event)
            c.SSEvent("message", string(eventData))
            return true
            
        case <-ctx.Done():
            // 请求被取消
            h.logger.Info("流式对话被取消", "conversation_id", req.ConversationID)
            return false
        }
    })
}
```

### **错误处理规范**
```go
// errors.go - 自定义错误类型
package utils

import "fmt"

// ChatError 对话相关错误
type ChatError struct {
    Code    string
    Message string
    Details map[string]interface{}
}

func (e *ChatError) Error() string {
    return fmt.Sprintf("[%s] %s", e.Code, e.Message)
}

// NewChatError 创建对话错误
func NewChatError(code, message string, details map[string]interface{}) *ChatError {
    return &ChatError{
        Code:    code,
        Message: message,
        Details: details,
    }
}

// 预定义错误
var (
    ErrModelNotFound = &ChatError{
        Code:    "MODEL_NOT_FOUND",
        Message: "指定的模型不存在",
    }
    
    ErrQuotaExceeded = &ChatError{
        Code:    "QUOTA_EXCEEDED",
        Message: "已超出配额限制",
    }
    
    ErrProviderUnavailable = &ChatError{
        Code:    "PROVIDER_UNAVAILABLE",
        Message: "AI服务提供商暂时不可用",
    }
)

// 在服务中使用错误处理
func (s *ChatService) ProcessMessage(ctx context.Context, req *ChatRequest) (*ChatResponse, error) {
    // 获取模型配置
    modelConfig, err := s.providerClient.GetModelConfig(req.UserToken, req.ModelName)
    if err != nil {
        s.logger.Error("获取模型配置失败",
            "model", req.ModelName,
            "error", err.Error())
        return nil, NewChatError("MODEL_CONFIG_ERROR", "模型配置获取失败", map[string]interface{}{
            "model": req.ModelName,
        })
    }
    
    // 检查配额
    if err := s.checkQuota(req.UserID, req.UserToken); err != nil {
        s.logger.Warn("配额检查失败",
            "user_id", req.UserID,
            "error", err.Error())
        return nil, ErrQuotaExceeded
    }
    
    // 处理对话逻辑...
    response, err := s.callAIProvider(ctx, req, modelConfig)
    if err != nil {
        s.logger.Error("AI服务调用失败",
            "provider", modelConfig.Provider,
            "error", err.Error())
        return nil, ErrProviderUnavailable
    }
    
    return response, nil
}
```

---

## ⚛️ TypeScript/React编码规范

### **组件定义规范**
```typescript
/**
 * 聊天消息气泡组件
 * 
 * 用于显示单条对话消息，支持用户消息和AI回复消息的不同样式。
 * 支持Markdown渲染、代码高亮等功能。
 * 
 * @author Lyss AI Team
 * @created 2025-01-20
 */

import React, { useState, useCallback, memo } from 'react';
import { Avatar, Typography, Card, Tooltip } from 'antd';
import { UserOutlined, RobotOutlined, CopyOutlined } from '@ant-design/icons';
import { message } from 'antd';

import { ChatMessage } from '@/types/chat';
import { formatTimestamp } from '@/utils/formatters';
import { copyToClipboard } from '@/utils/helpers';

import styles from './MessageBubble.module.css';

const { Text, Paragraph } = Typography;

interface MessageBubbleProps {
  /** 聊天消息数据 */
  message: ChatMessage;
  /** 是否显示时间戳 */
  showTimestamp?: boolean;
  /** 是否显示复制按钮 */
  showCopyButton?: boolean;
  /** 点击消息时的回调 */
  onMessageClick?: (message: ChatMessage) => void;
}

/**
 * 聊天消息气泡组件
 */
export const MessageBubble: React.FC<MessageBubbleProps> = memo(({
  message,
  showTimestamp = true,
  showCopyButton = true,
  onMessageClick,
}) => {
  const [isHovered, setIsHovered] = useState(false);
  
  // 判断是否为用户消息
  const isUserMessage = message.role === 'user';
  
  // 复制消息内容到剪贴板
  const handleCopyMessage = useCallback(async () => {
    try {
      await copyToClipboard(message.content);
      message.success('消息已复制到剪贴板');
    } catch (error) {
      message.error('复制失败，请重试');
    }
  }, [message.content]);
  
  // 处理消息点击事件
  const handleMessageClick = useCallback(() => {
    onMessageClick?.(message);
  }, [message, onMessageClick]);
  
  return (
    <div 
      className={`${styles.messageContainer} ${isUserMessage ? styles.userMessage : styles.aiMessage}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 头像 */}
      <Avatar 
        className={styles.avatar}
        icon={isUserMessage ? <UserOutlined /> : <RobotOutlined />}
        style={{
          backgroundColor: isUserMessage ? '#1890ff' : '#52c41a'
        }}
      />
      
      {/* 消息内容卡片 */}
      <Card 
        className={styles.messageCard}
        size="small"
        onClick={handleMessageClick}
        style={{
          cursor: onMessageClick ? 'pointer' : 'default'
        }}
      >
        {/* 消息内容 */}
        <Paragraph 
          className={styles.messageContent}
          copyable={false} // 使用自定义复制功能
        >
          {message.content}
        </Paragraph>
        
        {/* 消息元信息 */}
        <div className={styles.messageMetadata}>
          {showTimestamp && (
            <Text type="secondary" className={styles.timestamp}>
              {formatTimestamp(message.createdAt)}
            </Text>
          )}
          
          {message.tokenCount && (
            <Text type="secondary" className={styles.tokenCount}>
              {message.tokenCount} tokens
            </Text>
          )}
          
          {/* 模型信息（仅AI消息显示） */}
          {!isUserMessage && message.modelUsed && (
            <Text type="secondary" className={styles.modelInfo}>
              {message.modelUsed}
            </Text>
          )}
        </div>
        
        {/* 复制按钮 */}
        {showCopyButton && isHovered && (
          <Tooltip title="复制消息">
            <CopyOutlined 
              className={styles.copyButton}
              onClick={handleCopyMessage}
            />
          </Tooltip>
        )}
      </Card>
    </div>
  );
});

MessageBubble.displayName = 'MessageBubble';

export default MessageBubble;
```

### **Hook定义规范**
```typescript
/**
 * 聊天功能Hook
 * 
 * 提供聊天相关的状态管理和操作方法，包括发送消息、
 * 获取历史记录、管理对话状态等功能。
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { message } from 'antd';

import { ChatMessage, Conversation, SendMessageRequest } from '@/types/chat';
import { chatService } from '@/services/chat';
import { useAuthStore } from '@/store/auth/authStore';

interface UseChatOptions {
  /** 对话ID */
  conversationId?: string;
  /** 是否自动加载历史消息 */
  autoLoadHistory?: boolean;
  /** 消息每页数量 */
  pageSize?: number;
}

interface UseChatReturn {
  /** 当前对话信息 */
  conversation: Conversation | null;
  /** 消息列表 */
  messages: ChatMessage[];
  /** 是否正在发送消息 */
  isSending: boolean;
  /** 是否正在加载历史消息 */
  isLoadingHistory: boolean;
  /** 是否有更多历史消息 */
  hasMoreHistory: boolean;
  /** 发送消息 */
  sendMessage: (content: string, options?: Partial<SendMessageRequest>) => Promise<void>;
  /** 加载更多历史消息 */
  loadMoreHistory: () => Promise<void>;
  /** 清空当前对话 */
  clearConversation: () => void;
  /** 重新发送消息 */
  resendMessage: (messageId: string) => Promise<void>;
}

export const useChat = (options: UseChatOptions = {}): UseChatReturn => {
  const {
    conversationId,
    autoLoadHistory = true,
    pageSize = 20,
  } = options;
  
  // 状态管理
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  
  // 引用管理
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // 获取当前用户信息
  const { user } = useAuthStore();
  
  /**
   * 加载对话信息
   */
  const loadConversation = useCallback(async () => {
    if (!conversationId) return;
    
    try {
      const conversationData = await chatService.getConversation(conversationId);
      setConversation(conversationData);
    } catch (error) {
      console.error('加载对话信息失败:', error);
      message.error('加载对话信息失败');
    }
  }, [conversationId]);
  
  /**
   * 加载历史消息
   */
  const loadMessages = useCallback(async (page: number = 1, append: boolean = false) => {
    if (!conversationId) return;
    
    setIsLoadingHistory(true);
    
    try {
      const response = await chatService.getMessages(conversationId, {
        page,
        pageSize,
      });
      
      if (append) {
        setMessages(prev => [...prev, ...response.messages]);
      } else {
        setMessages(response.messages);
      }
      
      setHasMoreHistory(response.hasMore);
      setCurrentPage(page);
      
    } catch (error) {
      console.error('加载消息历史失败:', error);
      message.error('加载消息历史失败');
    } finally {
      setIsLoadingHistory(false);
    }
  }, [conversationId, pageSize]);
  
  /**
   * 发送消息
   */
  const sendMessage = useCallback(async (
    content: string, 
    options: Partial<SendMessageRequest> = {}
  ) => {
    if (!user || !content.trim()) return;
    
    // 取消之前的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // 创建新的取消控制器
    abortControllerRef.current = new AbortController();
    
    setIsSending(true);
    
    // 添加用户消息到界面
    const userMessage: ChatMessage = {
      id: `temp-${Date.now()}`,
      conversationId: conversationId || '',
      role: 'user',
      content: content.trim(),
      createdAt: new Date().toISOString(),
      tokenCount: 0,
    };
    
    setMessages(prev => [userMessage, ...prev]);
    
    try {
      const sendRequest: SendMessageRequest = {
        message: content.trim(),
        conversationId: conversationId,
        modelName: options.modelName || 'gpt-3.5-turbo',
        temperature: options.temperature || 0.7,
        maxTokens: options.maxTokens || 4000,
        stream: true,
        ...options,
      };
      
      // 发送消息并处理流式响应
      await chatService.sendMessage(sendRequest, {
        onMessage: (aiMessage: ChatMessage) => {
          // 更新或添加AI响应消息
          setMessages(prev => {
            const existingIndex = prev.findIndex(msg => msg.id === aiMessage.id);
            if (existingIndex >= 0) {
              // 更新现有消息
              const updated = [...prev];
              updated[existingIndex] = aiMessage;
              return updated;
            } else {
              // 添加新消息
              return [aiMessage, ...prev];
            }
          });
        },
        onError: (error) => {
          console.error('消息发送失败:', error);
          message.error('消息发送失败，请重试');
          
          // 移除失败的用户消息
          setMessages(prev => prev.filter(msg => msg.id !== userMessage.id));
        },
        signal: abortControllerRef.current.signal,
      });
      
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('发送消息时发生错误:', error);
        message.error('发送消息失败');
        
        // 移除失败的用户消息
        setMessages(prev => prev.filter(msg => msg.id !== userMessage.id));
      }
    } finally {
      setIsSending(false);
      abortControllerRef.current = null;
    }
  }, [user, conversationId]);
  
  /**
   * 加载更多历史消息
   */
  const loadMoreHistory = useCallback(async () => {
    if (!hasMoreHistory || isLoadingHistory) return;
    
    await loadMessages(currentPage + 1, true);
  }, [hasMoreHistory, isLoadingHistory, currentPage, loadMessages]);
  
  /**
   * 清空当前对话
   */
  const clearConversation = useCallback(() => {
    setMessages([]);
    setConversation(null);
    setCurrentPage(1);
    setHasMoreHistory(true);
    
    // 取消正在进行的请求
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);
  
  /**
   * 重新发送消息
   */
  const resendMessage = useCallback(async (messageId: string) => {
    const messageToResend = messages.find(msg => msg.id === messageId);
    if (!messageToResend || messageToResend.role !== 'user') return;
    
    await sendMessage(messageToResend.content);
  }, [messages, sendMessage]);
  
  // 初始化加载
  useEffect(() => {
    if (conversationId) {
      loadConversation();
      if (autoLoadHistory) {
        loadMessages();
      }
    }
  }, [conversationId, autoLoadHistory, loadConversation, loadMessages]);
  
  // 清理资源
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);
  
  return {
    conversation,
    messages,
    isSending,
    isLoadingHistory,
    hasMoreHistory,
    sendMessage,
    loadMoreHistory,
    clearConversation,
    resendMessage,
  };
};

export default useChat;
```

---

## 📋 代码审查清单

### **通用检查项**
- [ ] 所有注释使用中文
- [ ] 复杂逻辑有详细注释说明
- [ ] 错误处理完整且具体
- [ ] 日志记录适当且有意义
- [ ] 没有硬编码的敏感信息

### **Python特定检查**
- [ ] 遵循PEP 8规范
- [ ] 使用类型提示
- [ ] 文档字符串完整
- [ ] 异常处理具体化
- [ ] 使用参数化查询

### **Go特定检查**
- [ ] 遵循Go代码规范
- [ ] 错误处理完整
- [ ] 接口设计合理
- [ ] 并发安全
- [ ] 内存泄漏检查

### **TypeScript特定检查**
- [ ] 严格类型检查
- [ ] Props类型定义完整
- [ ] Hook使用正确
- [ ] 性能优化考虑
- [ ] 无障碍性支持