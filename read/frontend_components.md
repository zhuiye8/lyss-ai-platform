# 前端组件设计文档

## 1. 前端架构概述

### 1.1 技术栈
- **框架**: React 18+ with TypeScript
- **UI库**: Ant Design 5.x + Ant Design X
- **状态管理**: Zustand + React Query
- **路由**: React Router v6
- **构建工具**: Vite
- **样式**: CSS-in-JS (Ant Design's @ant-design/cssinjs)
- **图表**: Ant Design Charts (基于G2Plot)

### 1.2 项目结构
```
src/
├── components/           # 通用组件
│   ├── common/          # 基础组件
│   ├── chat/            # 聊天相关组件
│   ├── admin/           # 管理后台组件
│   └── layouts/         # 布局组件
├── pages/               # 页面组件
│   ├── auth/            # 认证页面
│   ├── chat/            # 聊天页面
│   ├── admin/           # 管理页面
│   └── dashboard/       # 仪表盘页面
├── hooks/               # 自定义Hook
├── services/            # API服务
├── stores/              # 状态管理
├── utils/               # 工具函数
├── types/               # 类型定义
└── constants/           # 常量定义
```

### 1.3 设计原则
- **统一主题**: 通过ConfigProvider实现统一的设计系统
- **响应式设计**: 支持PC、平板、手机等多端适配
- **组件复用**: 高度可复用的组件设计
- **类型安全**: 完整的TypeScript类型定义
- **性能优化**: 懒加载、虚拟滚动等优化策略

## 2. 全局配置组件

### 2.1 应用根组件
```typescript
// src/App.tsx
import React from 'react';
import { ConfigProvider, theme } from 'antd';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppRouter } from './router';
import { useThemeStore } from './stores/themeStore';
import zhCN from 'antd/locale/zh_CN';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 5 * 60 * 1000, // 5分钟
    },
  },
});

export const App: React.FC = () => {
  const { isDarkMode, primaryColor } = useThemeStore();

  const themeConfig = {
    algorithm: isDarkMode ? theme.darkAlgorithm : theme.defaultAlgorithm,
    token: {
      colorPrimary: primaryColor,
      borderRadius: 8,
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    },
    components: {
      Layout: {
        siderBg: isDarkMode ? '#141414' : '#001529',
        triggerBg: isDarkMode ? '#1f1f1f' : '#002140',
      },
      Menu: {
        darkItemBg: 'transparent',
        darkItemSelectedBg: '#1890ff',
      },
    },
  };

  return (
    <ConfigProvider theme={themeConfig} locale={zhCN}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppRouter />
        </BrowserRouter>
      </QueryClientProvider>
    </ConfigProvider>
  );
};
```

### 2.2 主题配置Hook
```typescript
// src/hooks/useUnifiedTheme.ts
import { theme } from 'antd';
import { useThemeStore } from '../stores/themeStore';

export const useUnifiedTheme = () => {
  const { token } = theme.useToken();
  const { isDarkMode } = useThemeStore();

  return {
    token,
    isDarkMode,
    colors: {
      primary: token.colorPrimary,
      success: token.colorSuccess,
      warning: token.colorWarning,
      error: token.colorError,
      text: token.colorText,
      textSecondary: token.colorTextSecondary,
      background: token.colorBgContainer,
      border: token.colorBorder,
    },
    spacing: {
      xs: token.sizeXS,
      sm: token.sizeSM,
      md: token.size,
      lg: token.sizeLG,
      xl: token.sizeXL,
    },
  };
};
```

## 3. 认证组件

### 3.1 登录组件
```typescript
// src/components/auth/LoginForm.tsx
import React from 'react';
import { Form, Input, Button, Checkbox, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import { useAuthStore } from '../../stores/authStore';

interface LoginFormData {
  email: string;
  password: string;
  remember_me?: boolean;
}

export const LoginForm: React.FC = () => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();

  const loginMutation = useMutation({
    mutationFn: authService.login,
    onSuccess: (response) => {
      setAuth(response.data);
      message.success('登录成功');
      navigate('/chat');
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '登录失败');
    },
  });

  const onFinish = (values: LoginFormData) => {
    loginMutation.mutate(values);
  };

  return (
    <Card 
      title="登录" 
      style={{ width: 400, margin: '0 auto' }}
      className="login-card"
    >
      <Form
        form={form}
        name="login"
        onFinish={onFinish}
        autoComplete="off"
        layout="vertical"
      >
        <Form.Item
          name="email"
          label="邮箱"
          rules={[
            { required: true, message: '请输入邮箱地址' },
            { type: 'email', message: '邮箱格式不正确' },
          ]}
        >
          <Input 
            prefix={<UserOutlined />} 
            placeholder="请输入邮箱地址"
            size="large"
          />
        </Form.Item>

        <Form.Item
          name="password"
          label="密码"
          rules={[
            { required: true, message: '请输入密码' },
            { min: 6, message: '密码长度不能少于6位' },
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="请输入密码"
            size="large"
          />
        </Form.Item>

        <Form.Item>
          <Form.Item name="remember_me" valuePropName="checked" noStyle>
            <Checkbox>记住我</Checkbox>
          </Form.Item>
          <a style={{ float: 'right' }} href="/forgot-password">
            忘记密码？
          </a>
        </Form.Item>

        <Form.Item>
          <Button 
            type="primary" 
            htmlType="submit" 
            block 
            size="large"
            loading={loginMutation.isPending}
          >
            登录
          </Button>
        </Form.Item>
      </Form>
    </Card>
  );
};
```

### 3.2 权限守卫组件
```typescript
// src/components/auth/AuthGuard.tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from '../../stores/authStore';

interface AuthGuardProps {
  children: React.ReactNode;
  requiredRoles?: string[];
  fallback?: React.ReactNode;
}

export const AuthGuard: React.FC<AuthGuardProps> = ({
  children,
  requiredRoles = [],
  fallback = <Navigate to="/login" replace />,
}) => {
  const { user, isLoading } = useAuthStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!user) {
    return fallback;
  }

  // 检查角色权限
  if (requiredRoles.length > 0) {
    const hasRequiredRole = requiredRoles.some(role => 
      user.roles.includes(role)
    );
    
    if (!hasRequiredRole) {
      return <Navigate to="/unauthorized" replace />;
    }
  }

  return <>{children}</>;
};
```

## 4. 聊天组件

### 4.1 聊天界面主组件
```typescript
// src/components/chat/ChatInterface.tsx
import React, { useEffect, useRef } from 'react';
import { Layout, Row, Col } from 'antd';
import { Bubble, Sender, useXAgent } from '@ant-design/x';
import { useChatStore } from '../../stores/chatStore';
import { useAuthStore } from '../../stores/authStore';
import { chatService } from '../../services/chatService';
import { ConversationSidebar } from './ConversationSidebar';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { ChatHeader } from './ChatHeader';

const { Content, Sider } = Layout;

export const ChatInterface: React.FC = () => {
  const { user } = useAuthStore();
  const { 
    currentConversation, 
    messages, 
    addMessage, 
    updateMessage,
    setCurrentConversation 
  } = useChatStore();
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 聊天代理配置
  const [agent] = useXAgent({
    request: async (info, callbacks) => {
      const { message } = info;
      const { onUpdate, onSuccess, onError } = callbacks;

      try {
        const response = await chatService.sendMessage(
          currentConversation?.conversation_id || '',
          {
            content: message,
            content_type: 'text',
            metadata: {
              use_memory: true,
              temperature: 0.7,
            },
          }
        );

        // 处理流式响应
        if (response.body) {
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let streamedContent = '';

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  if (data.type === 'content_delta') {
                    streamedContent += data.delta;
                    onUpdate(streamedContent);
                  } else if (data.type === 'message_end') {
                    onSuccess(streamedContent);
                  }
                } catch (e) {
                  // 忽略解析错误
                }
              }
            }
          }
        }
      } catch (error) {
        onError(error);
      }
    },
  });

  const handleSendMessage = async (content: string) => {
    if (!currentConversation) return;

    // 添加用户消息
    addMessage({
      message_id: Date.now().toString(),
      conversation_id: currentConversation.conversation_id,
      role: 'user',
      content,
      content_type: 'text',
      created_at: new Date().toISOString(),
    });

    // 发送消息给AI
    agent.request({ message: content });
  };

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider 
        width={300} 
        theme="light" 
        style={{ 
          borderRight: '1px solid #f0f0f0',
          overflow: 'auto',
        }}
      >
        <ConversationSidebar />
      </Sider>
      
      <Layout>
        <ChatHeader />
        
        <Content style={{ 
          padding: '16px', 
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <div style={{ flex: 1, overflow: 'auto' }}>
            <MessageList messages={agent.messages} />
            <div ref={messagesEndRef} />
          </div>
          
          <MessageInput 
            onSend={handleSendMessage}
            loading={agent.loading}
            disabled={!currentConversation}
          />
        </Content>
      </Layout>
    </Layout>
  );
};
```

### 4.2 消息列表组件
```typescript
// src/components/chat/MessageList.tsx
import React from 'react';
import { Bubble } from '@ant-design/x';
import { Avatar, Typography } from 'antd';
import { UserOutlined, RobotOutlined } from '@ant-design/icons';
import { useUnifiedTheme } from '../../hooks/useUnifiedTheme';
import { Message } from '../../types/chat';

const { Text } = Typography;

interface MessageListProps {
  messages: Message[];
}

export const MessageList: React.FC<MessageListProps> = ({ messages }) => {
  const { colors } = useUnifiedTheme();

  return (
    <div style={{ padding: '16px 0' }}>
      {messages.map((message) => (
        <div
          key={message.message_id}
          style={{
            marginBottom: '16px',
            display: 'flex',
            justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
          }}
        >
          <div
            style={{
              maxWidth: '80%',
              display: 'flex',
              flexDirection: message.role === 'user' ? 'row-reverse' : 'row',
              alignItems: 'flex-start',
              gap: '8px',
            }}
          >
            <Avatar
              size={32}
              icon={message.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
              style={{
                backgroundColor: message.role === 'user' ? colors.primary : colors.success,
                flexShrink: 0,
              }}
            />
            
            <div
              style={{
                background: message.role === 'user' ? colors.primary : colors.background,
                color: message.role === 'user' ? '#fff' : colors.text,
                padding: '12px 16px',
                borderRadius: '12px',
                border: message.role === 'user' ? 'none' : `1px solid ${colors.border}`,
                wordBreak: 'break-word',
              }}
            >
              <div style={{ marginBottom: '4px' }}>
                {message.content}
              </div>
              
              <Text 
                type="secondary" 
                style={{ 
                  fontSize: '12px',
                  color: message.role === 'user' ? 'rgba(255,255,255,0.7)' : colors.textSecondary,
                }}
              >
                {new Date(message.created_at).toLocaleTimeString()}
              </Text>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
```

### 4.3 消息输入组件
```typescript
// src/components/chat/MessageInput.tsx
import React, { useState, useRef } from 'react';
import { Input, Button, Upload, Tooltip } from 'antd';
import { SendOutlined, PaperClipOutlined, MicrophoneOutlined } from '@ant-design/icons';
import { useUnifiedTheme } from '../../hooks/useUnifiedTheme';

const { TextArea } = Input;

interface MessageInputProps {
  onSend: (content: string) => void;
  loading?: boolean;
  disabled?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSend,
  loading = false,
  disabled = false,
}) => {
  const [content, setContent] = useState('');
  const [isComposing, setIsComposing] = useState(false);
  const textAreaRef = useRef<HTMLTextAreaElement>(null);
  const { colors } = useUnifiedTheme();

  const handleSend = () => {
    if (content.trim() && !loading && !disabled) {
      onSend(content.trim());
      setContent('');
      textAreaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCompositionStart = () => {
    setIsComposing(true);
  };

  const handleCompositionEnd = () => {
    setIsComposing(false);
  };

  return (
    <div
      style={{
        padding: '16px',
        borderTop: `1px solid ${colors.border}`,
        backgroundColor: colors.background,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
        <div style={{ flex: 1 }}>
          <TextArea
            ref={textAreaRef}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            placeholder="输入消息... (Enter发送，Shift+Enter换行)"
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={disabled}
            style={{ resize: 'none' }}
          />
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <Tooltip title="上传附件">
            <Upload
              showUploadList={false}
              beforeUpload={() => false}
              disabled={disabled}
            >
              <Button
                icon={<PaperClipOutlined />}
                disabled={disabled}
              />
            </Upload>
          </Tooltip>

          <Tooltip title="语音输入">
            <Button
              icon={<MicrophoneOutlined />}
              disabled={disabled}
            />
          </Tooltip>

          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            disabled={disabled || !content.trim()}
          />
        </div>
      </div>
    </div>
  );
};
```

### 4.4 对话侧边栏
```typescript
// src/components/chat/ConversationSidebar.tsx
import React, { useState } from 'react';
import { 
  List, 
  Button, 
  Input, 
  Dropdown, 
  Typography, 
  Space, 
  Empty,
  Spin 
} from 'antd';
import { 
  PlusOutlined, 
  SearchOutlined, 
  MoreOutlined, 
  DeleteOutlined, 
  EditOutlined 
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useChatStore } from '../../stores/chatStore';
import { chatService } from '../../services/chatService';
import { useUnifiedTheme } from '../../hooks/useUnifiedTheme';

const { Title, Text } = Typography;

export const ConversationSidebar: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const { colors } = useUnifiedTheme();
  const { currentConversation, setCurrentConversation } = useChatStore();

  const { data: conversations, isLoading } = useQuery({
    queryKey: ['conversations', searchTerm],
    queryFn: () => chatService.getConversations({
      page: 1,
      page_size: 50,
      search: searchTerm,
    }),
  });

  const handleCreateConversation = async () => {
    try {
      const newConversation = await chatService.createConversation({
        title: '新对话',
      });
      setCurrentConversation(newConversation);
    } catch (error) {
      console.error('创建对话失败:', error);
    }
  };

  const handleDeleteConversation = async (conversationId: string) => {
    try {
      await chatService.deleteConversation(conversationId);
      // 刷新对话列表
    } catch (error) {
      console.error('删除对话失败:', error);
    }
  };

  const menuItems = (conversationId: string) => [
    {
      key: 'rename',
      label: '重命名',
      icon: <EditOutlined />,
    },
    {
      key: 'delete',
      label: '删除',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => handleDeleteConversation(conversationId),
    },
  ];

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '16px', borderBottom: `1px solid ${colors.border}` }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreateConversation}
            block
          >
            新建对话
          </Button>
          
          <Input
            placeholder="搜索对话..."
            prefix={<SearchOutlined />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            allowClear
          />
        </Space>
      </div>

      <div style={{ flex: 1, overflow: 'auto' }}>
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '20px' }}>
            <Spin />
          </div>
        ) : conversations?.data?.conversations?.length ? (
          <List
            dataSource={conversations.data.conversations}
            renderItem={(conversation) => (
              <List.Item
                key={conversation.conversation_id}
                style={{
                  padding: '12px 16px',
                  cursor: 'pointer',
                  backgroundColor: 
                    currentConversation?.conversation_id === conversation.conversation_id 
                      ? colors.primary + '10' 
                      : 'transparent',
                  borderLeft: 
                    currentConversation?.conversation_id === conversation.conversation_id 
                      ? `3px solid ${colors.primary}` 
                      : 'none',
                }}
                onClick={() => setCurrentConversation(conversation)}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    marginBottom: '4px' 
                  }}>
                    <Text 
                      strong 
                      ellipsis 
                      style={{ 
                        fontSize: '14px',
                        color: colors.text,
                      }}
                    >
                      {conversation.title}
                    </Text>
                    
                    <Dropdown
                      menu={{ items: menuItems(conversation.conversation_id) }}
                      trigger={['click']}
                      placement="bottomRight"
                    >
                      <Button
                        type="text"
                        icon={<MoreOutlined />}
                        size="small"
                        style={{ flexShrink: 0 }}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </Dropdown>
                  </div>
                  
                  <Text 
                    type="secondary" 
                    style={{ fontSize: '12px' }}
                  >
                    {conversation.message_count} 条消息 • {' '}
                    {new Date(conversation.updated_at).toLocaleDateString()}
                  </Text>
                </div>
              </List.Item>
            )}
          />
        ) : (
          <Empty 
            description="暂无对话" 
            style={{ marginTop: '60px' }}
          />
        )}
      </div>
    </div>
  );
};
```

## 5. 管理后台组件

### 5.1 仪表盘组件
```typescript
// src/components/admin/Dashboard.tsx
import React from 'react';
import { Row, Col, Card, Statistic, Table, Progress } from 'antd';
import { 
  UserOutlined, 
  MessageOutlined, 
  DollarOutlined, 
  RobotOutlined 
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { adminService } from '../../services/adminService';
import { UsageChart } from './UsageChart';
import { CostChart } from './CostChart';

export const Dashboard: React.FC = () => {
  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminService.getStats,
  });

  const { data: usageStats } = useQuery({
    queryKey: ['usage-stats'],
    queryFn: () => adminService.getUsageStats({
      start_date: '2025-07-01',
      end_date: '2025-07-08',
      granularity: 'daily',
    }),
  });

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]}>
        {/* 统计卡片 */}
        <Col span={6}>
          <Card>
            <Statistic
              title="总用户数"
              value={stats?.total_users || 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="总对话数"
              value={stats?.total_conversations || 0}
              prefix={<MessageOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="本月花费"
              value={stats?.monthly_cost || 0}
              prefix={<DollarOutlined />}
              precision={2}
              valueStyle={{ color: '#cf1322' }}
              suffix="USD"
            />
          </Card>
        </Col>
        
        <Col span={6}>
          <Card>
            <Statistic
              title="AI调用次数"
              value={stats?.total_ai_calls || 0}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        {/* 使用趋势图 */}
        <Col span={12}>
          <Card title="使用趋势">
            <UsageChart data={usageStats?.data?.usage_stats || []} />
          </Card>
        </Col>
        
        {/* 成本分析图 */}
        <Col span={12}>
          <Card title="成本分析">
            <CostChart data={usageStats?.data?.usage_stats || []} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
        {/* 模型使用排行 */}
        <Col span={12}>
          <Card title="模型使用排行">
            <Table
              dataSource={stats?.model_usage || []}
              columns={[
                {
                  title: '模型名称',
                  dataIndex: 'model_name',
                  key: 'model_name',
                },
                {
                  title: '调用次数',
                  dataIndex: 'call_count',
                  key: 'call_count',
                },
                {
                  title: '使用率',
                  dataIndex: 'usage_rate',
                  key: 'usage_rate',
                  render: (value: number) => (
                    <Progress 
                      percent={value} 
                      size="small" 
                      showInfo={false}
                    />
                  ),
                },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        
        {/* 活跃用户列表 */}
        <Col span={12}>
          <Card title="活跃用户">
            <Table
              dataSource={stats?.active_users || []}
              columns={[
                {
                  title: '用户',
                  dataIndex: 'username',
                  key: 'username',
                },
                {
                  title: '对话数',
                  dataIndex: 'conversation_count',
                  key: 'conversation_count',
                },
                {
                  title: '最后活跃',
                  dataIndex: 'last_active',
                  key: 'last_active',
                  render: (date: string) => 
                    new Date(date).toLocaleString(),
                },
              ]}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};
```

### 5.2 用户管理组件
```typescript
// src/components/admin/UserManagement.tsx
import React, { useState } from 'react';
import { 
  Table, 
  Button, 
  Space, 
  Modal, 
  Form, 
  Input, 
  Select, 
  Tag, 
  message,
  Popconfirm 
} from 'antd';
import { 
  PlusOutlined, 
  EditOutlined, 
  DeleteOutlined, 
  UserOutlined 
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminService } from '../../services/adminService';
import { User, CreateUserRequest } from '../../types/admin';

const { Option } = Select;

export const UserManagement: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const { data: users, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: adminService.getUsers,
  });

  const createUserMutation = useMutation({
    mutationFn: adminService.createUser,
    onSuccess: () => {
      message.success('用户创建成功');
      setIsModalVisible(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '创建用户失败');
    },
  });

  const updateUserMutation = useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: Partial<User> }) =>
      adminService.updateUser(userId, data),
    onSuccess: () => {
      message.success('用户更新成功');
      setIsModalVisible(false);
      form.resetFields();
      setEditingUser(null);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '更新用户失败');
    },
  });

  const deleteUserMutation = useMutation({
    mutationFn: adminService.deleteUser,
    onSuccess: () => {
      message.success('用户删除成功');
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.message || '删除用户失败');
    },
  });

  const handleCreate = () => {
    setEditingUser(null);
    form.resetFields();
    setIsModalVisible(true);
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue(user);
    setIsModalVisible(true);
  };

  const handleDelete = (userId: string) => {
    deleteUserMutation.mutate(userId);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingUser) {
        updateUserMutation.mutate({
          userId: editingUser.user_id,
          data: values,
        });
      } else {
        createUserMutation.mutate(values);
      }
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };

  const columns = [
    {
      title: '用户ID',
      dataIndex: 'user_id',
      key: 'user_id',
      width: 100,
      render: (id: string) => id.slice(0, 8) + '...',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '姓名',
      key: 'name',
      render: (record: User) => `${record.first_name} ${record.last_name}`,
    },
    {
      title: '角色',
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: string[]) => (
        <>
          {roles.map(role => (
            <Tag key={role} color="blue">{role}</Tag>
          ))}
        </>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'red'}>
          {status === 'active' ? '活跃' : '停用'}
        </Tag>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login_at',
      key: 'last_login_at',
      render: (date: string) => 
        date ? new Date(date).toLocaleString() : '从未登录',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (record: User) => (
        <Space size="middle">
          <Button 
            type="link" 
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个用户吗？"
            onConfirm={() => handleDelete(record.user_id)}
            okText="确定"
            cancelText="取消"
          >
            <Button 
              type="link" 
              danger 
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '16px' }}>
        <Button 
          type="primary" 
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          新建用户
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={users?.data?.users || []}
        loading={isLoading}
        rowKey="user_id"
        pagination={{
          total: users?.data?.pagination?.total_count || 0,
          pageSize: users?.data?.pagination?.page_size || 20,
          current: users?.data?.pagination?.page || 1,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => 
            `第 ${range[0]}-${range[1]} 条，共 ${total} 条记录`,
        }}
      />

      <Modal
        title={editingUser ? '编辑用户' : '新建用户'}
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={() => setIsModalVisible(false)}
        confirmLoading={createUserMutation.isPending || updateUserMutation.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
        >
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: '请输入邮箱' },
              { type: 'email', message: '邮箱格式不正确' },
            ]}
          >
            <Input prefix={<UserOutlined />} />
          </Form.Item>

          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="first_name"
            label="名"
            rules={[{ required: true, message: '请输入名' }]}
          >
            <Input />
          </Form.Item>

          <Form.Item
            name="last_name"
            label="姓"
            rules={[{ required: true, message: '请输入姓' }]}
          >
            <Input />
          </Form.Item>

          {!editingUser && (
            <Form.Item
              name="password"
              label="密码"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码长度不能少于6位' },
              ]}
            >
              <Input.Password />
            </Form.Item>
          )}

          <Form.Item
            name="roles"
            label="角色"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select mode="multiple">
              <Option value="end_user">终端用户</Option>
              <Option value="tenant_admin">租户管理员</Option>
              <Option value="super_admin">超级管理员</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="status"
            label="状态"
            rules={[{ required: true, message: '请选择状态' }]}
          >
            <Select>
              <Option value="active">活跃</Option>
              <Option value="inactive">停用</Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
```

## 6. 通用组件

### 6.1 加载组件
```typescript
// src/components/common/Loading.tsx
import React from 'react';
import { Spin } from 'antd';
import { useUnifiedTheme } from '../../hooks/useUnifiedTheme';

interface LoadingProps {
  size?: 'small' | 'default' | 'large';
  tip?: string;
  spinning?: boolean;
  children?: React.ReactNode;
}

export const Loading: React.FC<LoadingProps> = ({
  size = 'default',
  tip,
  spinning = true,
  children,
}) => {
  const { colors } = useUnifiedTheme();

  if (children) {
    return (
      <Spin spinning={spinning} tip={tip} size={size}>
        {children}
      </Spin>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '200px',
        backgroundColor: colors.background,
      }}
    >
      <Spin size={size} tip={tip} />
    </div>
  );
};
```

### 6.2 错误边界组件
```typescript
// src/components/common/ErrorBoundary.tsx
import React from 'react';
import { Result, Button } from 'antd';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <Result
          status="error"
          title="出现了一些错误"
          subTitle="抱歉，页面出现了错误。请尝试刷新页面或联系管理员。"
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          }
        />
      );
    }

    return this.props.children;
  }
}
```

这个前端组件设计文档提供了完整的React + TypeScript + Ant Design组件架构，包括认证、聊天、管理后台等核心功能的详细实现。