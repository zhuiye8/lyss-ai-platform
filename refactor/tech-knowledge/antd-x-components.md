# Ant Design X 聊天组件集成技术文档

## 📋 组件库概述

**Ant Design X** 是蚂蚁集团推出的专业AI交互组件库，基于Ant Design设计语言，专为构建现代化AI对话界面而设计。提供完整的聊天、对话管理和AI交互解决方案。

---

## 🎯 核心组件能力

### **聊天核心组件**
- **useXChat**: 对话状态管理Hook
- **useXAgent**: AI代理交互Hook  
- **Bubble**: 消息气泡组件
- **Sender**: 消息输入组件
- **Conversations**: 对话历史管理
- **Welcome**: 欢迎界面组件

### **高级交互功能**
- **流式响应**: 实时消息流处理
- **多模态输入**: 文本、图片、文件上传
- **智能建议**: 快捷回复和提示词
- **对话管理**: 会话创建、切换、删除

---

## 🔧 最新集成方案

### **1. 基础依赖和导入**
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
```

### **2. 核心类型定义**
```typescript
// 全局对话配置和类型定义
interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  status?: 'sending' | 'success' | 'error';
  attachments?: Array<{
    type: 'image' | 'file';
    url: string;
    name: string;
  }>;
}

interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: Date;
  updatedAt: Date;
  metadata?: Record<string, any>;
}

interface ChatAgentConfig {
  model: string;
  temperature: number;
  maxTokens: number;
  systemPrompt?: string;
}
```

### **3. 主对话组件实现**
```typescript
const ChatMainPage: React.FC = () => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [agentConfig, setAgentConfig] = useState<ChatAgentConfig>({
    model: 'gpt-4',
    temperature: 0.7,
    maxTokens: 2000,
  });
  
  // 使用Ant Design X的核心Hooks
  const chat = useXChat({
    defaultMessages: [],
    onMessagesChange: handleMessagesChange,
    onError: (error) => {
      console.error('聊天错误:', error);
      // 错误处理逻辑
    },
  });
  
  const agent = useXAgent({
    request: async (messages, options) => {
      // 调用后端聊天服务
      return await chatService.sendMessage({
        messages,
        conversationId: currentSessionId,
        stream: true,
        agentConfig: { ...agentConfig, ...options },
      });
    },
    onError: (error) => {
      console.error('AI代理请求失败:', error);
      // 显示错误提示
    },
    onStart: () => {
      console.log('AI开始处理请求');
    },
    onComplete: (result) => {
      console.log('AI处理完成:', result);
      // 更新会话状态
      updateSessionLastActive(currentSessionId);
    },
  });
  
  // 消息变化处理
  const handleMessagesChange = useCallback((newMessages: ChatMessage[]) => {
    if (currentSessionId) {
      updateSessionMessages(currentSessionId, newMessages);
    }
  }, [currentSessionId]);
  
  // 发送消息处理
  const handleSendMessage = useCallback(async (content: string, attachments?: File[]) => {
    if (!currentSessionId || !content.trim()) return;
    
    try {
      // 处理附件上传
      const uploadedAttachments = await uploadAttachments(attachments);
      
      // 添加用户消息
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        content: content.trim(),
        role: 'user',
        timestamp: new Date(),
        status: 'success',
        attachments: uploadedAttachments,
      };
      
      chat.pushMessage(userMessage);
      
      // 调用AI代理处理
      await agent.request([...chat.messages, userMessage], agentConfig);
      
    } catch (error) {
      console.error('发送消息失败:', error);
      // 显示错误提示
      notification.error({
        message: '发送失败',
        description: '消息发送失败，请重试',
      });
    }
  }, [currentSessionId, chat, agent, agentConfig]);
  
  // 上传附件处理
  const uploadAttachments = async (files?: File[]): Promise<Array<{type: string, url: string, name: string}>> => {
    if (!files || files.length === 0) return [];
    
    const uploadPromises = files.map(async (file) => {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch('/api/v1/upload', {
        method: 'POST',
        body: formData,
        headers: {
          'Authorization': `Bearer ${user?.token}`,
        },
      });
      
      const result = await response.json();
      return {
        type: file.type.startsWith('image/') ? 'image' : 'file',
        url: result.url,
        name: file.name,
      };
    });
    
    return Promise.all(uploadPromises);
  };
  
  return (
    <XProvider>
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: {
            colorPrimary: '#1890ff',
            borderRadius: 8,
            colorBgLayout: '#f5f5f5',
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
            style={{ 
              background: '#fff',
              borderRight: '1px solid #f0f0f0'
            }}
          >
            <div className="sidebar-header" style={{ padding: '16px' }}>
              <h3>对话历史</h3>
            </div>
            
            <Conversations
              items={sessions.map(session => ({
                key: session.id,
                label: session.title,
                timestamp: session.updatedAt,
                active: session.id === currentSessionId,
                avatar: { icon: <MessageOutlined /> },
                description: getLastMessage(session),
              }))}
              onActiveChange={(key) => switchSession(key as string)}
              onAdd={createNewSession}
              onDelete={(key) => deleteSession(key as string)}
              className="conversations-list"
              style={{ padding: '0 8px' }}
            />
          </Sider>
          
          {/* 主对话区域 */}
          <Content className="chat-content">
            {currentSessionId ? (
              <div className="chat-container" style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                height: '100%' 
              }}>
                {/* 对话消息列表 */}
                <div className="chat-messages" style={{ 
                  flex: 1, 
                  padding: '16px',
                  overflowY: 'auto',
                  background: 'linear-gradient(180deg, #fafafa 0%, #fff 100%)'
                }}>
                  {chat.messages.length === 0 ? (
                    <Welcome
                      title={`欢迎使用 Lyss AI 平台`}
                      description="请开始您的对话，我将为您提供智能助手服务"
                      extra={
                        <div className="welcome-suggestions" style={{ 
                          display: 'flex', 
                          gap: '8px', 
                          flexWrap: 'wrap',
                          marginTop: '16px'
                        }}>
                          <SuggestionButton 
                            text="你好，请介绍一下你的功能"
                            onClick={() => handleSendMessage('你好，请介绍一下你的功能')}
                          />
                          <SuggestionButton 
                            text="帮我写一段Python代码"
                            onClick={() => handleSendMessage('帮我写一段Python代码')}
                          />
                          <SuggestionButton 
                            text="分析一下这个文档的内容"
                            onClick={() => handleSendMessage('分析一下这个文档的内容')}
                          />
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
                        attachments: msg.attachments,
                        actions: msg.role === 'assistant' ? [
                          {
                            key: 'copy',
                            label: '复制',
                            icon: <CopyOutlined />,
                            onClick: () => copyToClipboard(msg.content),
                          },
                          {
                            key: 'regenerate',
                            label: '重新生成',
                            icon: <ReloadOutlined />,
                            onClick: () => regenerateMessage(msg.id),
                          },
                        ] : undefined,
                      }))}
                      className="bubble-list"
                      style={{ maxWidth: '800px', margin: '0 auto' }}
                    />
                  )}
                </div>
                
                {/* 消息输入区域 */}
                <div className="chat-input" style={{ 
                  padding: '16px',
                  borderTop: '1px solid #f0f0f0',
                  background: '#fff'
                }}>
                  <Sender
                    value=""
                    placeholder="输入您的消息..."
                    onSubmit={handleSendMessage}
                    loading={agent.isRequesting}
                    disabled={!currentSessionId}
                    allowFiles={true}
                    allowImages={true}
                    maxLength={2000}
                    actions={[
                      {
                        key: 'clear',
                        label: '清空对话',
                        icon: <ClearOutlined />,
                        onClick: () => clearCurrentSession(),
                      },
                      {
                        key: 'settings',
                        label: '设置',
                        icon: <SettingOutlined />,
                        onClick: () => openAgentSettings(),
                      },
                    ]}
                    className="message-sender"
                    style={{ maxWidth: '800px', margin: '0 auto' }}
                  />
                </div>
              </div>
            ) : (
              <Welcome
                title="选择或创建新对话"
                description="从左侧选择一个对话，或创建新的对话开始"
                extra={
                  <Button 
                    type="primary" 
                    size="large"
                    icon={<PlusOutlined />}
                    onClick={createNewSession}
                  >
                    创建新对话
                  </Button>
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

### **4. 对话管理Hook**
```typescript
export const useConversationManager = () => {
  const [conversations, setConversations] = useState<ChatSession[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  
  // 创建新对话
  const createConversation = useCallback(async (title?: string) => {
    const newConversation: ChatSession = {
      id: `conv-${Date.now()}`,
      title: title || `对话 ${conversations.length + 1}`,
      messages: [],
      createdAt: new Date(),
      updatedAt: new Date(),
      metadata: {
        model: 'gpt-4',
        temperature: 0.7,
      }
    };
    
    // 保存到后端
    try {
      await chatService.createConversation(newConversation);
      setConversations(prev => [newConversation, ...prev]);
      setActiveConversationId(newConversation.id);
      return newConversation;
    } catch (error) {
      console.error('创建对话失败:', error);
      throw error;
    }
  }, [conversations.length]);
  
  // 删除对话
  const deleteConversation = useCallback(async (conversationId: string) => {
    try {
      await chatService.deleteConversation(conversationId);
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
      
      if (activeConversationId === conversationId) {
        const remaining = conversations.filter(conv => conv.id !== conversationId);
        setActiveConversationId(remaining.length > 0 ? remaining[0].id : null);
      }
    } catch (error) {
      console.error('删除对话失败:', error);
      throw error;
    }
  }, [activeConversationId, conversations]);
  
  // 更新对话标题
  const updateConversationTitle = useCallback(async (conversationId: string, title: string) => {
    try {
      await chatService.updateConversation(conversationId, { title });
      setConversations(prev => prev.map(conv => 
        conv.id === conversationId 
          ? { ...conv, title, updatedAt: new Date() }
          : conv
      ));
    } catch (error) {
      console.error('更新对话标题失败:', error);
      throw error;
    }
  }, []);
  
  // 加载对话历史
  const loadConversations = useCallback(async () => {
    try {
      const loadedConversations = await chatService.getConversations();
      setConversations(loadedConversations);
      if (loadedConversations.length > 0 && !activeConversationId) {
        setActiveConversationId(loadedConversations[0].id);
      }
    } catch (error) {
      console.error('加载对话历史失败:', error);
    }
  }, [activeConversationId]);
  
  // 自动保存对话
  const saveConversation = useCallback(async (conversationId: string) => {
    const conversation = conversations.find(conv => conv.id === conversationId);
    if (conversation) {
      try {
        await chatService.updateConversation(conversationId, conversation);
      } catch (error) {
        console.error('保存对话失败:', error);
      }
    }
  }, [conversations]);
  
  return {
    conversations,
    activeConversationId,
    setActiveConversationId,
    createConversation,
    deleteConversation,
    updateConversationTitle,
    loadConversations,
    saveConversation,
  };
};
```

### **5. 建议回复组件**
```typescript
interface SuggestionButtonProps {
  text: string;
  onClick: () => void;
  icon?: React.ReactNode;
}

const SuggestionButton: React.FC<SuggestionButtonProps> = ({ text, onClick, icon }) => {
  return (
    <Button
      size="small"
      type="outline"
      className="suggestion-button"
      onClick={onClick}
      icon={icon}
      style={{
        borderRadius: '16px',
        border: '1px solid #d9d9d9',
        background: '#fff',
        color: '#666',
        fontSize: '12px',
        height: '32px',
        padding: '0 12px',
        transition: 'all 0.2s',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#1890ff';
        e.currentTarget.style.color = '#1890ff';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#d9d9d9';
        e.currentTarget.style.color = '#666';
      }}
    >
      {text}
    </Button>
  );
};

// 智能建议生成Hook
export const useSmartSuggestions = (currentMessage: string, conversationHistory: ChatMessage[]) => {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  
  useEffect(() => {
    if (currentMessage.length > 3) {
      // 基于当前输入和对话历史生成建议
      generateSuggestions(currentMessage, conversationHistory).then(setSuggestions);
    } else {
      setSuggestions([]);
    }
  }, [currentMessage, conversationHistory]);
  
  return suggestions;
};

const generateSuggestions = async (input: string, history: ChatMessage[]): Promise<string[]> => {
  // 这里可以调用后端API或使用本地算法生成智能建议
  const contextualSuggestions = [
    '请详细解释一下',
    '能给个具体例子吗？',
    '有什么相关资料推荐？',
    '这个问题的解决方案是什么？',
  ];
  
  return contextualSuggestions.slice(0, 3);
};
```

### **6. AI代理配置组件**
```typescript
interface AgentSettingsProps {
  config: ChatAgentConfig;
  onConfigChange: (config: ChatAgentConfig) => void;
  visible: boolean;
  onClose: () => void;
}

const AgentSettings: React.FC<AgentSettingsProps> = ({ 
  config, 
  onConfigChange, 
  visible, 
  onClose 
}) => {
  const [form] = Form.useForm();
  
  const handleSave = () => {
    form.validateFields().then(values => {
      onConfigChange(values);
      onClose();
      message.success('设置已保存');
    });
  };
  
  return (
    <Modal
      title="AI代理设置"
      open={visible}
      onOk={handleSave}
      onCancel={onClose}
      width={500}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={config}
      >
        <Form.Item
          name="model"
          label="模型选择"
          rules={[{ required: true, message: '请选择模型' }]}
        >
          <Select placeholder="选择AI模型">
            <Option value="gpt-4">GPT-4</Option>
            <Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Option>
            <Option value="claude-3">Claude-3</Option>
            <Option value="deepseek-chat">DeepSeek Chat</Option>
          </Select>
        </Form.Item>
        
        <Form.Item
          name="temperature"
          label="创造性"
          extra="控制回复的随机性，值越高越有创造性"
        >
          <Slider
            min={0}
            max={1}
            step={0.1}
            marks={{
              0: '严格',
              0.5: '平衡',
              1: '创造',
            }}
          />
        </Form.Item>
        
        <Form.Item
          name="maxTokens"
          label="最大令牌数"
          extra="控制回复的最大长度"
        >
          <Slider
            min={100}
            max={4000}
            step={100}
            marks={{
              100: '100',
              2000: '2000',
              4000: '4000',
            }}
          />
        </Form.Item>
        
        <Form.Item
          name="systemPrompt"
          label="系统提示词"
          extra="设置AI的角色和行为规范"
        >
          <TextArea
            rows={4}
            placeholder="你是一个专业的AI助手，请提供准确、有用的信息..."
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};
```

---

## 🎨 样式定制和主题配置

### **CSS样式定制**
```css
/* Chat组件自定义样式 */
.chat-layout {
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.chat-sidebar {
  background: #fff;
  border-right: 1px solid #f0f0f0;
  overflow-y: auto;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
}

.conversations-list {
  padding: 16px 8px;
}

.conversations-list .ant-list-item {
  border-radius: 8px;
  margin-bottom: 4px;
  transition: all 0.2s;
}

.conversations-list .ant-list-item:hover {
  background: #f5f5f5;
}

.conversations-list .ant-list-item.active {
  background: #e6f7ff;
  border-color: #1890ff;
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
  scroll-behavior: smooth;
}

.bubble-list {
  max-width: 800px;
  margin: 0 auto;
}

.bubble-list .ant-bubble {
  margin-bottom: 16px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.chat-input {
  padding: 16px;
  border-top: 1px solid #f0f0f0;
  background: #fff;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.05);
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

.welcome-suggestions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
  justify-content: center;
}

.suggestion-button {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.suggestion-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.2);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chat-layout .ant-layout-sider {
    position: fixed;
    height: 100vh;
    left: 0;
    top: 0;
    z-index: 100;
  }
  
  .chat-layout .ant-layout-sider.ant-layout-sider-collapsed {
    left: -280px;
  }
  
  .bubble-list {
    max-width: 100%;
    padding: 0 8px;
  }
  
  .message-sender {
    max-width: 100%;
  }
}

/* 暗色主题适配 */
[data-theme='dark'] .chat-layout {
  background: #141414;
}

[data-theme='dark'] .chat-sidebar {
  background: #1f1f1f;
  border-right-color: #303030;
}

[data-theme='dark'] .chat-content {
  background: #1f1f1f;
}

[data-theme='dark'] .chat-messages {
  background: linear-gradient(180deg, #1a1a1a 0%, #1f1f1f 100%);
}

[data-theme='dark'] .chat-input {
  background: #1f1f1f;
  border-top-color: #303030;
}
```

### **主题配置**
```typescript
// 主题配置
const lightTheme = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    colorInfo: '#1890ff',
    colorTextBase: '#000000',
    colorBgBase: '#ffffff',
    borderRadius: 8,
    wireframe: false,
  },
  components: {
    Layout: {
      colorBgHeader: '#001529',
      colorBgBody: '#f5f5f5',
    },
    Button: {
      borderRadius: 6,
    },
    Input: {
      borderRadius: 6,
    },
  },
};

const darkTheme = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#1890ff',
    colorBgBase: '#141414',
    colorTextBase: '#ffffff',
    borderRadius: 8,
  },
  components: {
    Layout: {
      colorBgHeader: '#1f1f1f',
      colorBgBody: '#141414',
    },
  },
};

// 主题切换Hook
export const useTheme = () => {
  const [isDark, setIsDark] = useState(false);
  
  const toggleTheme = useCallback(() => {
    setIsDark(prev => !prev);
    document.documentElement.setAttribute('data-theme', isDark ? 'light' : 'dark');
  }, [isDark]);
  
  return {
    theme: isDark ? darkTheme : lightTheme,
    isDark,
    toggleTheme,
  };
};
```

---

## 📱 响应式设计

### **移动端适配**
```typescript
// 移动端检测Hook
export const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(false);
  
  useEffect(() => {
    const checkIsMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    
    checkIsMobile();
    window.addEventListener('resize', checkIsMobile);
    
    return () => window.removeEventListener('resize', checkIsMobile);
  }, []);
  
  return isMobile;
};

// 移动端适配的聊天组件
const MobileChatPage: React.FC = () => {
  const isMobile = useIsMobile();
  const [showSidebar, setShowSidebar] = useState(false);
  
  if (isMobile) {
    return (
      <div className="mobile-chat-container">
        {/* 移动端顶部导航 */}
        <div className="mobile-header">
          <Button 
            icon={<MenuOutlined />}
            onClick={() => setShowSidebar(true)}
          />
          <h3>Lyss AI</h3>
          <Button icon={<SettingOutlined />} />
        </div>
        
        {/* 移动端侧边栏抽屉 */}
        <Drawer
          title="对话历史"
          placement="left"
          onClose={() => setShowSidebar(false)}
          open={showSidebar}
          width={280}
        >
          <Conversations
            items={sessions.map(session => ({
              key: session.id,
              label: session.title,
              timestamp: session.updatedAt,
              active: session.id === currentSessionId,
            }))}
            onActiveChange={(key) => {
              switchSession(key as string);
              setShowSidebar(false);
            }}
            onAdd={() => {
              createNewSession();
              setShowSidebar(false);
            }}
          />
        </Drawer>
        
        {/* 移动端聊天区域 */}
        <div className="mobile-chat-area">
          {/* 消息列表 */}
          <div className="mobile-messages">
            <Bubble.List
              items={chat.messages}
              className="mobile-bubble-list"
            />
          </div>
          
          {/* 输入框 */}
          <div className="mobile-input">
            <Sender
              placeholder="输入消息..."
              onSubmit={handleSendMessage}
              loading={agent.isRequesting}
              style={{ width: '100%' }}
            />
          </div>
        </div>
      </div>
    );
  }
  
  return <ChatMainPage />;
};
```

---

## 🔧 性能优化

### **虚拟滚动**
```typescript
import { VirtualList } from '@ant-design/virtual-list-utils';

// 大量消息时使用虚拟滚动
const VirtualMessageList: React.FC<{ messages: ChatMessage[] }> = ({ messages }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState(400);
  
  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        setHeight(containerRef.current.clientHeight);
      }
    };
    
    updateHeight();
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, []);
  
  return (
    <div ref={containerRef} style={{ height: '100%' }}>
      <VirtualList
        data={messages}
        height={height}
        itemHeight={100}
        itemKey="id"
      >
        {(message, index) => (
          <Bubble
            key={message.id}
            role={message.role}
            content={message.content}
            avatar={message.role === 'user' 
              ? { icon: <UserOutlined /> }
              : { icon: <RobotOutlined /> }
            }
          />
        )}
      </VirtualList>
    </div>
  );
};
```

### **消息懒加载**
```typescript
// 消息分页加载Hook
export const useMessagePagination = (conversationId: string) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  
  const loadMessages = useCallback(async (pageNum: number = 1) => {
    if (!conversationId || loading) return;
    
    setLoading(true);
    try {
      const response = await chatService.getMessages(conversationId, {
        page: pageNum,
        limit: 20,
      });
      
      if (pageNum === 1) {
        setMessages(response.messages);
      } else {
        setMessages(prev => [...response.messages, ...prev]);
      }
      
      setHasMore(response.hasMore);
      setPage(pageNum);
    } catch (error) {
      console.error('加载消息失败:', error);
    } finally {
      setLoading(false);
    }
  }, [conversationId, loading]);
  
  const loadMore = useCallback(() => {
    if (hasMore && !loading) {
      loadMessages(page + 1);
    }
  }, [hasMore, loading, page, loadMessages]);
  
  return {
    messages,
    loading,
    hasMore,
    loadMessages,
    loadMore,
  };
};
```

---

## 🚀 部署和构建

### **Vite配置**
```typescript
// vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'antd': ['antd'],
          'antd-x': ['@ant-design/x'],
          'react': ['react', 'react-dom'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ['@ant-design/x', 'antd'],
  },
});
```

### **环境变量**
```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/ws
VITE_APP_TITLE=Lyss AI Platform
VITE_APP_VERSION=1.0.0
VITE_ENABLE_MOCK=false

# .env.production
VITE_API_BASE_URL=/api/v1
VITE_WS_BASE_URL=/ws
VITE_APP_TITLE=Lyss AI Platform
VITE_APP_VERSION=1.0.0
VITE_ENABLE_MOCK=false
```

---

## 🔄 版本兼容性

- **Ant Design X版本**: 最新稳定版 (持续更新)
- **Ant Design版本**: 5.x+
- **React版本**: 18.x+
- **TypeScript版本**: 5.x+
- **依赖管理**: package.json精确版本控制
- **升级策略**: 定期使用Context7更新到最新兼容版本