# lyss-frontend (前端应用)

## 📋 服务概述

前端应用基于React 18和Ant Design X，提供现代化的AI对话界面和管理功能。

---

## 🎯 服务职责

```
技术栈: React 18 + TypeScript + Ant Design X
端口: 3000
职责：
- 现代化AI对话界面
- 对话历史侧边栏
- 供应商和模型管理界面
- 用户偏好设置
- 响应式设计
```

---

## 🔍 技术实现详细说明

### **Ant Design X最新集成方案**
```typescript
// 基于Context7调研的Ant Design X最佳实践
import React, { useState, useCallback, useEffect } from 'react';
import { 
  useXChat, 
  useXAgent, 
  Bubble, 
  Sender,
  Conversations,
  XProvider,
  Welcome
} from '@ant-design/x';
import { ConfigProvider, Layout, theme } from 'antd';
import { UserOutlined, RobotOutlined } from '@ant-design/icons';

import { chatService } from '@/services/chat';
import { useAuth } from '@/hooks/useAuth';

const { Content, Sider } = Layout;

// 1. 全局对话配置和类型定义
interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  status?: 'sending' | 'success' | 'error';
}

interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
}

// 2. 主对话组件实现
const ChatMainPage: React.FC = () => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // 使用Ant Design X的核心Hooks
  const chat = useXChat({
    defaultMessages: [],
    onMessagesChange: handleMessagesChange,
  });
  
  const agent = useXAgent({
    request: async (messages, options) => {
      // 调用后端聊天服务
      return await chatService.sendMessage({
        messages,
        conversationId: currentSessionId,
        stream: true,
        ...options,
      });
    },
    onError: (error) => {
      console.error('聊天请求失败:', error);
      // 错误处理逻辑
    },
  });
  
  // 发送消息处理
  const handleSendMessage = useCallback(async (content: string) => {
    if (!currentSessionId || !content.trim()) return;
    
    try {
      // 添加用户消息
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        content: content.trim(),
        role: 'user',
        timestamp: new Date(),
        status: 'success',
      };
      
      chat.pushMessage(userMessage);
      
      // 调用AI代理处理
      await agent.request([...chat.messages, userMessage], {
        model: 'gpt-4',
        temperature: 0.7,
      });
      
    } catch (error) {
      console.error('发送消息失败:', error);
      // 错误提示处理
    }
  }, [currentSessionId, chat, agent]);
  
  return (
    <XProvider>
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: '#1890ff',
            borderRadius: 8,
          },
        }}
      >
        <Layout className="chat-layout" style={{ height: '100vh' }}>
          {/* 左侧对话历史侧边栏 */}
          <Sider 
            width={280}
            collapsible
            collapsed={sidebarCollapsed}
            onCollapse={setSidebarCollapsed}
            className="chat-sidebar"
          >
            <Conversations
              items={sessions.map(session => ({
                key: session.id,
                label: session.title,
                timestamp: session.updatedAt,
                active: session.id === currentSessionId,
              }))}
              onActiveChange={(key) => switchSession(key as string)}
              onAdd={createNewSession}
              className="conversations-list"
            />
          </Sider>
          
          {/* 主对话区域 */}
          <Content className="chat-content">
            {currentSessionId ? (
              <div className="chat-container">
                {/* 对话消息列表 */}
                <div className="chat-messages">
                  {chat.messages.length === 0 ? (
                    <Welcome
                      title={`欢迎使用 Lyss AI 平台`}
                      description="请开始您的对话"
                      extra={
                        <div className="welcome-suggestions">
                          <button onClick={() => handleSendMessage('你好，请介绍一下你的功能')}>
                            了解功能
                          </button>
                          <button onClick={() => handleSendMessage('帮我写一段Python代码')}>
                            代码协助
                          </button>
                        </div>
                      }
                    />
                  ) : (
                    <Bubble.List
                      items={chat.messages.map(msg => ({
                        key: msg.id,
                        role: msg.role,
                        content: msg.content,
                        avatar: msg.role === 'user' 
                          ? { icon: <UserOutlined /> }
                          : { icon: <RobotOutlined /> },
                        status: msg.status,
                        timestamp: msg.timestamp,
                      }))}
                      className="bubble-list"
                    />
                  )}
                </div>
                
                {/* 消息输入区域 */}
                <div className="chat-input">
                  <Sender
                    value=""
                    placeholder="输入您的消息..."
                    onSubmit={handleSendMessage}
                    loading={agent.isRequesting}
                    disabled={!currentSessionId}
                    actions={[
                      {
                        key: 'clear',
                        label: '清空对话',
                        onClick: () => chat.setMessages([]),
                      },
                    ]}
                    className="message-sender"
                  />
                </div>
              </div>
            ) : (
              <Welcome
                title="选择或创建新对话"
                description="从左侧选择一个对话，或创建新的对话开始"
                extra={
                  <button onClick={createNewSession}>
                    创建新对话
                  </button>
                }
              />
            )}
          </Content>
        </Layout>
      </ConfigProvider>
    </XProvider>
  );
};
```

### **对话管理Hook**
```typescript
// 4. 对话管理Hook
export const useConversationManager = () => {
  const [conversations, setConversations] = useState<ChatSession[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  
  const createConversation = useCallback(async (title?: string) => {
    const newConversation: ChatSession = {
      id: `conv-${Date.now()}`,
      title: title || `对话 ${conversations.length + 1}`,
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    setConversations(prev => [newConversation, ...prev]);
    setActiveConversationId(newConversation.id);
    
    return newConversation;
  }, [conversations.length]);
  
  const deleteConversation = useCallback(async (conversationId: string) => {
    setConversations(prev => prev.filter(conv => conv.id !== conversationId));
    
    if (activeConversationId === conversationId) {
      const remaining = conversations.filter(conv => conv.id !== conversationId);
      setActiveConversationId(remaining.length > 0 ? remaining[0].id : null);
    }
  }, [activeConversationId, conversations]);
  
  const updateConversationTitle = useCallback(async (conversationId: string, title: string) => {
    setConversations(prev => prev.map(conv => 
      conv.id === conversationId 
        ? { ...conv, title, updatedAt: new Date() }
        : conv
    ));
  }, []);
  
  return {
    conversations,
    activeConversationId,
    setActiveConversationId,
    createConversation,
    deleteConversation,
    updateConversationTitle,
  };
};
```

### **样式定制和主题配置**
```css
/* Chat组件自定义样式 */
.chat-layout {
  background: #f5f5f5;
}

.chat-sidebar {
  background: #fff;
  border-right: 1px solid #f0f0f0;
  overflow-y: auto;
}

.conversations-list {
  padding: 16px 8px;
}

.chat-content {
  display: flex;
  flex-direction: column;
  background: #fff;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background: linear-gradient(180deg, #fafafa 0%, #fff 100%);
}

.bubble-list {
  max-width: 800px;
  margin: 0 auto;
}

.chat-input {
  padding: 16px;
  border-top: 1px solid #f0f0f0;
  background: #fff;
}

.message-sender {
  max-width: 800px;
  margin: 0 auto;
}

.streaming-bubble {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.welcome-suggestions, .chat-suggestions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.suggestion-button {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-button:hover {
  border-color: #1890ff;
  color: #1890ff;
}
```

### **关键技术优势**
- **现代化UI**: 使用Ant Design X提供的最新聊天组件
- **流式响应**: 支持实时流式AI回复显示
- **智能交互**: useXChat和useXAgent提供强大的对话管理
- **响应式设计**: 自适应各种屏幕尺寸
- **可扩展架构**: 易于添加新功能和自定义组件

---

## 🔧 项目结构

```
lyss-frontend/
├── src/
│   ├── components/           # 组件库
│   │   ├── chat/            # 对话相关组件
│   │   ├── layout/          # 布局组件
│   │   └── common/          # 通用组件
│   ├── pages/               # 页面组件
│   │   ├── chat/           # 对话页面
│   │   ├── admin/          # 管理页面
│   │   └── auth/           # 认证页面
│   ├── hooks/               # 自定义Hooks
│   ├── services/            # API服务
│   ├── store/               # 状态管理
│   ├── types/               # 类型定义
│   ├── utils/               # 工具函数
│   └── styles/              # 样式文件
├── public/                  # 静态资源
└── docs/                    # 文档
```

---

## 🔧 配置管理

### **环境变量**
```bash
# 开发服务器配置
VITE_PORT=3000
VITE_HOST=0.0.0.0

# API配置
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/ws

# 应用配置
VITE_APP_TITLE=Lyss AI Platform
VITE_APP_VERSION=1.0.0

# 功能开关
VITE_ENABLE_CHAT_HISTORY=true
VITE_ENABLE_MEMORY_SEARCH=true
VITE_ENABLE_PROVIDER_MANAGEMENT=true
```

### **Docker配置**
```dockerfile
# 构建阶段
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

# 生产阶段
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
```