# TypeScript/React编码规范

## 📋 文档概述

TypeScript和React项目的专用编码规范，确保前端代码质量和一致性。

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

### **类型定义规范**
```typescript
// types/chat.ts - 聊天相关类型定义

/** 消息角色类型 */
export type MessageRole = 'user' | 'assistant' | 'system';

/** 消息状态类型 */
export type MessageStatus = 'sending' | 'success' | 'error' | 'pending';

/** 聊天消息接口 */
export interface ChatMessage {
  /** 消息唯一标识 */
  id: string;
  /** 对话ID */
  conversationId: string;
  /** 消息角色 */
  role: MessageRole;
  /** 消息内容 */
  content: string;
  /** 创建时间 */
  createdAt: string;
  /** 更新时间 */
  updatedAt?: string;
  /** 消息状态 */
  status?: MessageStatus;
  /** Token数量 */
  tokenCount?: number;
  /** 使用的模型 */
  modelUsed?: string;
  /** 元数据 */
  metadata?: Record<string, any>;
}

/** 对话会话接口 */
export interface Conversation {
  /** 对话唯一标识 */
  id: string;
  /** 对话标题 */
  title: string;
  /** 用户ID */
  userId: string;
  /** 创建时间 */
  createdAt: string;
  /** 更新时间 */
  updatedAt: string;
  /** 消息数量 */
  messageCount: number;
  /** 对话设置 */
  settings?: ConversationSettings;
}

/** 对话设置接口 */
export interface ConversationSettings {
  /** 模型名称 */
  modelName: string;
  /** 温度值 */
  temperature: number;
  /** 最大Token数 */
  maxTokens: number;
  /** 系统提示词 */
  systemPrompt?: string;
}

/** 发送消息请求接口 */
export interface SendMessageRequest {
  /** 消息内容 */
  message: string;
  /** 对话ID */
  conversationId?: string;
  /** 模型名称 */
  modelName?: string;
  /** 温度值 */
  temperature?: number;
  /** 最大Token数 */
  maxTokens?: number;
  /** 是否流式响应 */
  stream?: boolean;
  /** 系统提示词 */
  systemPrompt?: string;
}

/** API响应基础接口 */
export interface ApiResponse<T = any> {
  /** 是否成功 */
  success: boolean;
  /** 响应数据 */
  data?: T;
  /** 错误信息 */
  error?: ApiError;
  /** 消息 */
  message?: string;
  /** 请求ID */
  requestId?: string;
  /** 时间戳 */
  timestamp?: string;
}

/** API错误接口 */
export interface ApiError {
  /** 错误代码 */
  code: string;
  /** 错误消息 */
  message: string;
  /** 错误详情 */
  details?: any;
}
```

---

## 📋 TypeScript特定检查清单

- [ ] 严格类型检查
- [ ] Props类型定义完整
- [ ] Hook使用正确
- [ ] 性能优化考虑
- [ ] 无障碍性支持