# Lyss AI Platform Frontend

## 📋 概述

Lyss AI Platform 前端应用，基于 React 18 + TypeScript + Ant Design 构建的现代化企业级管理界面。

## 🚀 快速启动

### 环境要求

- Node.js 18.0.0+
- npm 9.0.0+

### 安装依赖

```bash
cd frontend
npm install
```

### 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env.local

# 编辑环境变量
nano .env.local
```

### 启动开发服务器

```bash
npm run dev
```

应用将在 http://localhost:3000 启动

## 🔧 可用脚本

```bash
# 开发模式启动
npm run dev

# 生产构建
npm run build

# 预览生产版本
npm run preview

# 代码检查
npm run lint

# 修复代码问题
npm run lint:fix

# 类型检查
npm run type-check

# 代码格式化
npm run format

# 运行测试
npm run test

# 测试覆盖率
npm run test:coverage
```

## 🏗️ 项目结构

```
frontend/
├── public/                    # 静态资源
├── src/
│   ├── components/           # 可复用组件
│   │   ├── common/          # 通用组件
│   │   └── layout/          # 布局组件
│   ├── pages/               # 页面组件
│   │   ├── login/          # 登录页面
│   │   ├── dashboard/      # 仪表板
│   │   └── error/          # 错误页面
│   ├── services/           # API服务
│   ├── store/              # 状态管理
│   ├── types/              # TypeScript类型
│   ├── utils/              # 工具函数
│   ├── hooks/              # 自定义Hooks
│   ├── styles/             # 样式文件
│   ├── App.tsx             # 根组件
│   └── main.tsx            # 应用入口
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 🎯 核心功能

### 已实现功能

- ✅ **项目基础架构**
  - Vite + React 18 + TypeScript 5.x
  - Ant Design 5.x + Ant Design X
  - Zustand 状态管理
  - React Router 6.x 路由
  - Axios HTTP 客户端

- ✅ **认证系统**
  - JWT 认证集成
  - 自动令牌刷新
  - 路由守卫
  - 登录状态持久化

- ✅ **用户界面**
  - 响应式登录页面
  - 用户仪表板
  - 错误页面 (404, 401, 403)

### 开发中功能

- 🔄 **管理界面**
  - 租户管理
  - 用户管理
  - 供应商凭证管理

- 🔄 **AI功能**
  - 聊天界面
  - 对话历史
  - 记忆管理

## 🔐 认证集成

应用与 Backend API Gateway 完全集成：

- 自动JWT令牌管理
- 访问令牌自动刷新
- 统一错误处理
- 请求追踪 (X-Request-ID)

## 🎨 主题配置

使用 Ant Design 主题系统：

```typescript
const theme = {
  token: {
    colorPrimary: '#1890ff',
    borderRadius: 6,
  },
  components: {
    Button: { borderRadius: 4 },
    Table: { borderRadius: 8 },
  },
};
```

## 📱 响应式设计

- 支持桌面端 (≥1200px)
- 支持平板端 (768px-1199px)
- 支持移动端 (<768px)
- 自适应布局和组件

## 🔧 开发规范

### 代码风格

- 使用 ESLint + Prettier
- TypeScript 严格模式
- 中文注释和变量命名
- 函数式组件 + Hooks

### 目录命名

- 组件目录: PascalCase
- 文件名: camelCase.tsx
- 样式文件: Component.module.css

### 状态管理

使用 Zustand 进行状态管理：

```typescript
const useStore = create((set) => ({
  data: [],
  loading: false,
  setData: (data) => set({ data }),
  setLoading: (loading) => set({ loading }),
}));
```

## 🧪 测试

```bash
# 运行单元测试
npm run test

# 测试覆盖率
npm run test:coverage

# 测试UI界面
npm run test:ui
```

## 📦 构建部署

### 生产构建

```bash
npm run build
```

构建产物在 `dist/` 目录

### 环境配置

```bash
# 开发环境
VITE_API_BASE_URL=http://localhost:8000

# 生产环境
VITE_API_BASE_URL=https://api.lyss.com
```

## 🔗 API集成

### HTTP客户端配置

- 基础URL: `http://localhost:8000`
- 超时时间: 10秒
- 自动重试: 2次
- 请求拦截器: JWT令牌注入
- 响应拦截器: 统一错误处理

### API服务

```typescript
// 认证服务
AuthService.login(credentials)
AuthService.logout()
AuthService.refreshToken()

// 用户服务  
UserService.getUsers(params)
UserService.createUser(data)

// 租户服务
TenantService.getTenants(params)
TenantService.createTenant(data)
```

## 🚨 故障排除

### 常见问题

1. **启动失败**
   ```bash
   # 清除依赖重新安装
   rm -rf node_modules package-lock.json
   npm install
   ```

2. **API连接失败**
   - 检查Backend API Gateway是否启动 (端口8000)
   - 验证环境变量 `VITE_API_BASE_URL`

3. **认证问题**
   - 清除浏览器localStorage
   - 检查JWT密钥配置

4. **类型错误**
   ```bash
   # 运行类型检查
   npm run type-check
   ```

### 调试技巧

```bash
# 启用详细日志
VITE_LOG_LEVEL=debug npm run dev

# 查看网络请求
# 打开浏览器开发工具 -> Network 标签
```

## 📚 相关文档

- [前端规范](../docs/frontend.md)
- [开发规范](../docs/STANDARDS.md)
- [项目结构](../docs/PROJECT_STRUCTURE.md)
- [API网关文档](../backend/README.md)

## 🤝 贡献指南

1. 遵循项目代码规范
2. 提交前运行测试和检查
3. 使用中文注释
4. 保持响应式设计

---

**版本**: 1.0.0  
**最后更新**: 2025-07-11