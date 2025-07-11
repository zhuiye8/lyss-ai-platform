# Lyss AI Platform 前端应用规范

## 📋 文档概述

本文档是 **Lyss AI Platform** 前端应用的开发规范文档，专门定义前端应用的技术架构选型、API集成方案和前端特有的开发实践。

**适用范围**: Lyss AI Platform 前端应用（React + TypeScript + Ant Design）  
**更新日期**: 2025-07-11  
**技术栈版本**: React 18, TypeScript 5.x, Ant Design 5.x + Ant Design X

**重要说明**: 本文档专注于前端技术栈和集成方案，通用的开发规范请参考：
- **项目结构规范**: [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)
- **开发规范总纲**: [STANDARDS.md](./STANDARDS.md)
- **API响应格式**: [STANDARDS.md](./STANDARDS.md#2-api-设计与响应规范)

---

## 🎯 技术架构选型

### 2024-2025年技术栈调研结果

基于在线调研和企业级应用最佳实践，确定以下技术栈：

#### 核心框架
- **React 18.2+**: 现代React框架，支持并发渲染和新特性
- **TypeScript 5.x**: 类型安全的JavaScript超集
- **Vite 5.x**: 快速的前端构建工具，替代Create React App

#### UI组件库
- **Ant Design 5.x**: 企业级UI设计语言和组件库（NPM下载量6000万+）
- **Ant Design X**: 专门为AI驱动界面设计的新组件库（2024年发布）
- **@ant-design/icons**: 官方图标库

#### 状态管理
- **Zustand 4.x**: 轻量级状态管理库（2024年推荐，相比Redux更简单）
- **React Query (TanStack Query)**: 服务器状态管理
- **Context API**: 局部状态共享

#### 路由管理
- **React Router 6.x**: 现代化路由解决方案

#### HTTP客户端
- **Axios 1.x**: Promise基础的HTTP客户端，企业级应用首选

#### 开发工具
- **ESLint**: 代码质量检查
- **Prettier**: 代码格式化
- **Husky**: Git钩子管理
- **lint-staged**: 提交前代码检查

---

## 🔌 Backend API Gateway 集成

### HTTP客户端配置

遵循 [STANDARDS.md](./STANDARDS.md) 中的API设计规范，集成Backend API Gateway：

```typescript
// src/services/http.ts
import axios from 'axios';
import { message } from 'antd';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// 创建axios实例
const httpClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加JWT令牌
httpClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理统一响应格式
httpClient.interceptors.response.use(
  (response) => {
    // 处理STANDARDS.md中定义的统一响应格式
    const { success, data, message: msg } = response.data;
    if (success) {
      return { ...response, data };
    } else {
      throw new Error(msg || '请求失败');
    }
  },
  (error) => {
    if (error.response?.status === 401) {
      // 清除认证信息
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
      message.error('登录已过期，请重新登录');
    }
    return Promise.reject(error);
  }
);

export default httpClient;
```

### API服务层设计

```typescript
// src/services/tenant.ts
import httpClient from './http';
import type { Tenant, CreateTenantRequest } from '@/types/tenant';

export class TenantService {
  private static readonly BASE_URL = '/api/v1/admin/tenants';
  
  // 获取租户列表 - 支持STANDARDS.md中的分页规范
  static async getTenants(params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<{
    items: Tenant[];
    pagination: {
      page: number;
      page_size: number;
      total_items: number;
      total_pages: number;
      has_next: boolean;
      has_prev: boolean;
    };
  }> {
    const response = await httpClient.get(this.BASE_URL, { params });
    return response.data;
  }
  
  // 创建租户
  static async createTenant(data: CreateTenantRequest): Promise<Tenant> {
    const response = await httpClient.post(this.BASE_URL, data);
    return response.data;
  }
}
```

### 错误处理

遵循 [STANDARDS.md](./STANDARDS.md) 中的错误代码规范：

```typescript
// src/utils/errorHandler.ts
import { message } from 'antd';
import type { AxiosError } from 'axios';

export const handleApiError = (error: AxiosError) => {
  const response = error.response;
  
  if (response?.data?.error) {
    const { code, message: errorMessage } = response.data.error;
    
    // 根据STANDARDS.md中的错误代码进行处理
    switch (code) {
      case '2001':
        message.error('请先登录');
        break;
      case '2002':
        message.error('登录已过期，请重新登录');
        break;
      case '3001':
        message.error('租户不存在');
        break;
      case '3003':
        message.error('用户不存在');
        break;
      default:
        message.error(errorMessage || '操作失败');
    }
  } else {
    message.error('网络连接失败');
  }
};
```

---

## 🔐 JWT认证集成

### 认证状态管理

```typescript
// src/store/auth.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types/user';
import { AuthService } from '@/services/auth';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      loading: false,
      
      login: async (credentials) => {
        set({ loading: true });
        try {
          const response = await AuthService.login(credentials);
          const { user, access_token, refresh_token } = response.data;
          
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);
          
          set({ user, isAuthenticated: true, loading: false });
        } catch (error) {
          set({ loading: false });
          throw error;
        }
      },
      
      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        set({ user: null, isAuthenticated: false });
      },
      
      refreshToken: async () => {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('无刷新令牌');
        }
        
        try {
          const response = await AuthService.refreshToken(refreshToken);
          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);
        } catch (error) {
          get().logout();
          throw error;
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        isAuthenticated: state.isAuthenticated 
      }),
    }
  )
);
```

### 路由守卫

```typescript
// src/components/common/ProtectedRoute.tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requiredRole 
}) => {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  if (requiredRole && user?.role !== requiredRole) {
    return <Navigate to="/unauthorized" replace />;
  }
  
  return <>{children}</>;
};

export default ProtectedRoute;
```

---

## 🎨 Ant Design + Ant Design X 集成

### 主题配置

```typescript
// src/App.tsx
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';

const customTheme = {
  token: {
    colorPrimary: '#1890ff',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#f5222d',
    borderRadius: 6,
  },
  components: {
    Button: {
      borderRadius: 4,
    },
    Table: {
      borderRadius: 8,
    }
  }
};

function App() {
  return (
    <ConfigProvider theme={customTheme} locale={zhCN}>
      {/* 应用内容 */}
    </ConfigProvider>
  );
}
```

### AI聊天界面 (Ant Design X)

```typescript
// src/components/chat/ChatInterface.tsx
import React, { useState } from 'react';
import { Bubble, Sender } from '@ant-design/x';
import { UserOutlined } from '@ant-design/icons';
import { useAuthStore } from '@/store/auth';
import { ChatService } from '@/services/chat';

interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const { user } = useAuthStore();
  
  const handleSend = async (message: string) => {
    if (!message.trim()) return;
    
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: message,
      role: 'user',
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    
    try {
      // 调用Backend API Gateway的聊天接口
      const response = await ChatService.sendMessage(message);
      
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: response.data.content,
        role: 'assistant',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('发送消息失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="chat-interface">
      <div className="chat-messages">
        {messages.map((msg) => (
          <Bubble
            key={msg.id}
            content={msg.content}
            avatar={msg.role === 'user' ? user?.avatar : '/ai-avatar.png'}
            placement={msg.role === 'user' ? 'end' : 'start'}
          />
        ))}
      </div>
      
      <Sender
        onSubmit={handleSend}
        loading={loading}
        placeholder="输入消息..."
        prefix={<UserOutlined />}
      />
    </div>
  );
};

export default ChatInterface;
```

### 数据表格

```typescript
// src/components/admin/UserTable.tsx
import React from 'react';
import { Table, Button, Space, Tag, Modal } from 'antd';
import { EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { User } from '@/types/user';

interface UserTableProps {
  users: User[];
  loading: boolean;
  onEdit: (user: User) => void;
  onDelete: (userId: string) => void;
}

const UserTable: React.FC<UserTableProps> = ({
  users,
  loading,
  onEdit,
  onDelete
}) => {
  const columns: ColumnsType<User> = [
    {
      title: '用户名',
      dataIndex: 'name',
      key: 'name',
      sorter: true,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Tag color={role === 'admin' ? 'red' : 'blue'}>
          {role === 'admin' ? '管理员' : '用户'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => onEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];
  
  const handleDelete = (user: User) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除用户 "${user.name}" 吗？`,
      onOk: () => onDelete(user.id),
    });
  };
  
  return (
    <Table
      columns={columns}
      dataSource={users}
      loading={loading}
      rowKey="id"
      pagination={{
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total, range) => 
          `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
      }}
    />
  );
};

export default UserTable;
```

---

## 📦 构建与部署

### 环境变量配置

```bash
# .env.example
# API配置
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Lyss AI Platform
VITE_APP_VERSION=1.0.0

# 功能开关
VITE_ENABLE_MOCK=false
VITE_ENABLE_DEVTOOLS=true
```

### Vite配置

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
          vendor: ['react', 'react-dom'],
          antd: ['antd', '@ant-design/icons'],
          router: ['react-router-dom'],
        },
      },
    },
  },
});
```

---

## 🎯 核心页面开发要求

### 1. 登录页面 (`/login`)
- 响应式布局，支持桌面和移动端
- 表单验证：邮箱格式、密码长度
- 错误处理：显示友好的错误消息
- 集成JWT认证流程

### 2. 用户仪表板 (`/dashboard`)
- 显示用户基本信息
- 显示平台使用统计
- 快速操作入口

### 3. 租户管理 (`/admin/tenants`)
- 租户列表，支持分页和搜索
- 新增租户功能
- 编辑租户信息
- 删除租户（带确认）

### 4. 用户管理 (`/admin/users`)
- 用户列表，支持按租户筛选
- 用户角色管理
- 新增用户功能
- 用户状态管理

### 5. 供应商管理 (`/admin/suppliers`)
- 供应商凭证列表
- 添加新的API凭证
- 编辑凭证信息
- 安全的凭证显示（脱敏）

### 6. AI聊天界面 (`/chat`)
- 集成Ant Design X组件
- 实时消息显示
- 支持流式响应
- 消息历史记录

---

## 📋 开发工作流

### 开发环境启动
```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 类型检查
npm run type-check

# 代码检查
npm run lint

# 代码格式化
npm run format
```

### 代码规范检查

使用 [STANDARDS.md](./STANDARDS.md) 中定义的代码规范：

```javascript
// .eslintrc.js
module.exports = {
  extends: [
    'eslint:recommended',
    '@typescript-eslint/recommended',
    'plugin:react/recommended',
    'plugin:react-hooks/recommended',
  ],
  rules: {
    // React相关
    'react/react-in-jsx-scope': 'off',
    'react/prop-types': 'off',
    
    // TypeScript相关
    '@typescript-eslint/no-unused-vars': 'error',
    '@typescript-eslint/explicit-function-return-type': 'off',
    
    // 通用规则
    'no-console': 'warn',
    'prefer-const': 'error',
    'no-var': 'error',
  },
};
```

---

## 🎯 总结

本规范文档定义了Lyss AI Platform前端应用的技术选型和集成方案：

1. **技术栈**: React 18 + TypeScript + Ant Design + Ant Design X
2. **Backend集成**: 完整的API Gateway集成方案
3. **认证集成**: JWT认证和路由守卫
4. **UI组件**: Ant Design企业级组件 + AI聊天组件
5. **状态管理**: Zustand轻量级状态管理

**重要提醒**: 
- 严格遵循 [STANDARDS.md](./STANDARDS.md) 中的通用开发规范
- 项目结构必须符合 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) 规范
- 与Backend API Gateway的集成必须正确
- 注释和文档必须使用中文

---

**文档版本**: 1.0.0  
**最后更新**: 2025-07-11  
**下次审查**: 2025-08-11