# 项目结构标准

## 📋 文档概述

定义统一的项目目录结构标准，适用于所有服务和组件，确保代码组织的一致性。

---

## 🏗️ 项目根目录结构

```
lyss-ai-platform/
├── README.md                          # 项目总览和快速开始
├── CLAUDE.md                          # Claude AI开发助手指令
├── ARCHITECTURE.md                    # 架构设计文档
├── CHANGELOG.md                       # 版本变更记录
├── docker-compose.yml                 # 生产环境服务编排
├── docker-compose.dev.yml             # 开发环境服务编排
├── .env.example                       # 环境变量模板
├── .env.production.example            # 生产环境变量模板
├── .gitignore                         # Git忽略规则
├── .editorconfig                      # 编辑器配置
├──
├── docs/                              # 📚 项目文档
├── scripts/                           # 🔧 项目脚本
├── infrastructure/                    # 🐳 基础设施配置
├── sql/                               # 📊 数据库相关
├── tests/                             # 🧪 集成测试
├── refactor/                          # 📋 重构分析文档
├── shared/                            # 🔗 共享代码库
├──
├── lyss-api-gateway/                  # 🌐 API网关服务
├── lyss-auth-service/                 # 🔐 认证服务
├── lyss-user-service/                 # 👥 用户管理服务
├── lyss-provider-service/             # 🔌 供应商管理服务
├── lyss-chat-service/                 # 💬 AI对话服务
├── lyss-memory-service/               # 🧠 智能记忆服务
└── lyss-frontend/                     # 🎨 前端应用
```

---

## 📚 公共目录详解

### **docs/ 文档目录**
```
docs/
├── README.md                          # 文档目录说明
├── api/                               # API文档
│   ├── api-gateway.md                 # API网关接口文档
│   ├── auth-service.md                # 认证服务接口文档
│   ├── user-service.md                # 用户服务接口文档
│   ├── provider-service.md            # 供应商服务接口文档
│   ├── chat-service.md                # 对话服务接口文档
│   └── memory-service.md              # 记忆服务接口文档
├── development/                       # 开发文档
│   ├── setup-guide.md                 # 环境搭建指南
│   ├── coding-standards.md            # 编码规范
│   ├── testing-guide.md               # 测试指南
│   └── deployment-guide.md            # 部署指南
├── architecture/                      # 架构文档
│   ├── service-overview.md            # 服务总览
│   ├── database-design.md             # 数据库设计
│   ├── security-design.md             # 安全设计
│   └── scalability-design.md          # 扩展性设计
└── operation/                         # 运维文档
    ├── monitoring.md                  # 监控配置
    ├── troubleshooting.md             # 故障排查
    └── backup-recovery.md             # 备份恢复
```

### **scripts/ 脚本目录**
```
scripts/
├── setup.sh                          # 项目初始化脚本
├── start-dev.sh                      # 开发环境启动脚本
├── start-prod.sh                     # 生产环境启动脚本
├── stop-services.sh                  # 服务停止脚本
├── health-check.sh                   # 健康检查脚本
├── backup-db.sh                      # 数据库备份脚本
├── restore-db.sh                     # 数据库恢复脚本
└── deploy/                           # 部署脚本
    ├── build-all.sh                  # 构建所有服务
    ├── push-images.sh                # 推送镜像
    └── rolling-update.sh             # 滚动更新
```

### **infrastructure/ 基础设施目录**
```
infrastructure/
├── docker/                           # Docker相关配置
│   ├── postgres/
│   │   ├── Dockerfile                # 自定义PostgreSQL镜像
│   │   └── init-scripts/             # 初始化脚本
│   ├── redis/
│   │   ├── Dockerfile                # 自定义Redis镜像
│   │   └── redis.conf                # Redis配置
│   └── nginx/
│       ├── Dockerfile                # Nginx镜像
│       └── nginx.conf                # Nginx配置
├── k8s/                              # Kubernetes配置（可选）
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   └── services/
└── monitoring/                       # 监控配置
    ├── prometheus/
    ├── grafana/
    └── loki/
```

### **sql/ 数据库目录**
```
sql/
├── init-databases.sql                # 数据库初始化脚本
├── migrations/                       # 数据库迁移脚本
│   ├── 001_create_user_tables.sql    # 用户服务表结构
│   ├── 002_create_provider_tables.sql # 供应商服务表结构
│   ├── 003_create_chat_tables.sql    # 对话服务表结构
│   └── 004_create_memory_tables.sql  # 记忆服务表结构
├── seeds/                            # 测试数据脚本
│   ├── dev-data.sql                  # 开发环境数据
│   └── test-data.sql                 # 测试环境数据
└── schema/                           # 数据库模式文档
    ├── user-service-schema.md        # 用户服务数据库文档
    ├── provider-service-schema.md    # 供应商服务数据库文档
    ├── chat-service-schema.md        # 对话服务数据库文档
    └── memory-service-schema.md      # 记忆服务数据库文档
```

### **shared/ 共享代码目录**
```
shared/
├── types/                            # 共享类型定义
│   ├── user.ts                       # 用户相关类型
│   ├── conversation.ts               # 对话相关类型
│   ├── provider.ts                   # 供应商相关类型
│   └── common.ts                     # 通用类型
├── utils/                            # 共享工具函数
│   ├── validation.ts                 # 验证函数
│   ├── formatting.ts                 # 格式化函数
│   └── encryption.ts                 # 加密函数
├── constants/                        # 共享常量
│   ├── api.ts                        # API相关常量
│   ├── status.ts                     # 状态常量
│   └── errors.ts                     # 错误代码常量
└── schemas/                          # 共享数据模型
    ├── request.json                  # 请求模式
    ├── response.json                 # 响应模式
    └── database.json                 # 数据库模式
```

---

## 🐍 Python服务结构标准 (FastAPI)

```
lyss-{service-name}/
├── README.md                         # 服务说明文档
├── Dockerfile                        # Docker构建文件
├── Dockerfile.dev                    # 开发环境Docker文件
├── docker-compose.yml                # 服务独立测试环境
├── requirements.txt                  # 生产依赖
├── requirements-dev.txt              # 开发依赖
├── pyproject.toml                    # Python项目配置
├── .env.example                      # 环境变量示例
├── .gitignore                        # Git忽略文件
├──
├── app/                              # 应用主目录
│   ├── __init__.py
│   ├── main.py                       # FastAPI应用入口
│   ├── config.py                     # 配置管理
│   ├──
│   ├── core/                         # 核心模块
│   │   ├── __init__.py
│   │   ├── database.py               # 数据库连接
│   │   ├── security.py               # 安全相关
│   │   ├── logging.py                # 日志配置
│   │   ├── exceptions.py             # 自定义异常
│   │   └── dependencies.py           # 依赖注入
│   ├──
│   ├── models/                       # 数据模型
│   │   ├── __init__.py
│   │   ├── database/                 # 数据库模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # 基础模型
│   │   │   └── {entity}.py           # 具体实体模型
│   │   └── schemas/                  # API模型
│   │       ├── __init__.py
│   │       ├── base.py               # 基础模式
│   │       ├── requests/             # 请求模式
│   │       └── responses/            # 响应模式
│   ├──
│   ├── repositories/                 # 数据访问层
│   │   ├── __init__.py
│   │   ├── base.py                   # 基础仓库
│   │   └── {entity}_repository.py   # 具体实体仓库
│   ├──
│   ├── services/                     # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── base.py                   # 基础服务
│   │   └── {entity}_service.py      # 具体业务服务
│   ├──
│   ├── routers/                      # API路由
│   │   ├── __init__.py
│   │   ├── health.py                 # 健康检查路由
│   │   ├── internal.py               # 内部API路由
│   │   └── {entity}.py               # 具体实体路由
│   ├──
│   ├── middleware/                   # 中间件
│   │   ├── __init__.py
│   │   ├── cors.py                   # CORS中间件
│   │   ├── auth.py                   # 认证中间件
│   │   ├── rate_limit.py             # 限流中间件
│   │   └── error_handler.py          # 错误处理中间件
│   ├──
│   └── utils/                        # 工具模块
│       ├── __init__.py
│       ├── helpers.py                # 帮助函数
│       ├── validators.py             # 验证器
│       └── formatters.py             # 格式化器
├──
├── scripts/                          # 脚本文件
│   ├── start-dev.py                  # 开发启动脚本
│   ├── migrate.py                    # 数据库迁移脚本
│   └── seed.py                       # 数据播种脚本
├──
├── tests/                           # 测试文件
│   ├── __init__.py
│   ├── conftest.py                  # 测试配置
│   ├── fixtures/                    # 测试夹具
│   ├── unit/                        # 单元测试
│   │   ├── test_services/
│   │   ├── test_repositories/
│   │   └── test_utils/
│   └── integration/                 # 集成测试
│       ├── test_routers/
│       └── test_external_apis/
├──
├── migrations/                      # 数据库迁移（如使用Alembic）
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
└──
└── docs/                           # 服务文档
    ├── api.md                      # API文档
    ├── setup.md                    # 设置指南
    └── deployment.md               # 部署指南
```

---

## 🐹 Go服务结构标准

```
lyss-{service-name}/
├── README.md                         # 服务说明文档
├── Dockerfile                        # Docker构建文件
├── Dockerfile.dev                    # 开发环境Docker文件
├── docker-compose.yml                # 服务独立测试环境
├── go.mod                            # Go模块定义
├── go.sum                            # Go依赖锁定文件
├── .env.example                      # 环境变量示例
├── .gitignore                        # Git忽略文件
├──
├── cmd/                              # 应用入口
│   └── server/
│       └── main.go                   # 主程序入口
├──
├── internal/                         # 内部代码（不对外暴露）
│   ├── config/                       # 配置管理
│   │   ├── config.go
│   │   └── env.go
│   ├──
│   ├── handlers/                     # HTTP处理器
│   │   ├── health.go                 # 健康检查
│   │   ├── {entity}.go               # 具体实体处理器
│   │   └── middleware/               # 中间件
│   │       ├── auth.go
│   │       ├── cors.go
│   │       └── logging.go
│   ├──
│   ├── services/                     # 业务逻辑
│   │   ├── {entity}_service.go
│   │   └── interfaces.go             # 接口定义
│   ├──
│   ├── repositories/                 # 数据访问
│   │   ├── {entity}_repository.go
│   │   └── interfaces.go             # 接口定义
│   ├──
│   ├── models/                       # 数据模型
│   │   ├── {entity}.go
│   │   └── dto/                      # 数据传输对象
│   │       ├── requests.go
│   │       └── responses.go
│   ├──
│   ├── clients/                      # 外部服务客户端
│   │   ├── {service}_client.go
│   │   └── interfaces.go
│   ├──
│   └── utils/                        # 工具函数
│       ├── errors.go                 # 错误处理
│       ├── validation.go             # 验证器
│       └── helpers.go                # 帮助函数
├──
├── pkg/                              # 可对外暴露的代码
│   ├── logger/                       # 日志包
│   ├── database/                     # 数据库包
│   └── auth/                         # 认证包
├──
├── scripts/                          # 脚本文件
│   ├── build.sh                      # 构建脚本
│   ├── test.sh                       # 测试脚本
│   └── migrate.sh                    # 迁移脚本
├──
├── tests/                           # 测试文件
│   ├── integration/                  # 集成测试
│   ├── unit/                        # 单元测试
│   └── fixtures/                    # 测试数据
├──
└── docs/                           # 服务文档
    ├── api.md                      # API文档
    └── development.md              # 开发指南
```

---

## ⚛️ React前端结构标准

```
lyss-frontend/
├── README.md                         # 项目说明
├── package.json                      # 依赖和脚本
├── package-lock.json                 # 依赖锁定
├── tsconfig.json                     # TypeScript配置
├── tsconfig.node.json                # Node.js TypeScript配置
├── vite.config.ts                    # Vite配置
├── .env.example                      # 环境变量示例
├── .env.development                  # 开发环境变量
├── .env.production                   # 生产环境变量
├── .gitignore                        # Git忽略文件
├── .eslintrc.js                      # ESLint配置
├── .prettierrc                       # Prettier配置
├── Dockerfile                        # Docker构建文件
├──
├── public/                           # 静态资源
│   ├── index.html
│   ├── favicon.ico
│   └── manifest.json
├──
├── src/                              # 源代码
│   ├── main.tsx                      # 应用入口
│   ├── App.tsx                       # 主应用组件
│   ├── vite-env.d.ts                # Vite类型定义
│   ├──
│   ├── components/                   # 组件库
│   │   ├── common/                   # 通用组件
│   │   │   ├── Button/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Button.module.css
│   │   │   │   └── index.ts
│   │   │   ├── Modal/
│   │   │   ├── Loading/
│   │   │   └── index.ts              # 组件导出
│   │   ├── layout/                   # 布局组件
│   │   │   ├── Header/
│   │   │   ├── Sidebar/
│   │   │   ├── AdminLayout/
│   │   │   └── index.ts
│   │   ├── chat/                     # 对话相关组件
│   │   │   ├── ChatWindow/
│   │   │   ├── MessageBubble/
│   │   │   ├── InputArea/
│   │   │   └── index.ts
│   │   └── forms/                    # 表单组件
│   │       ├── LoginForm/
│   │       ├── UserForm/
│   │       └── index.ts
│   ├──
│   ├── pages/                        # 页面组件
│   │   ├── login/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── LoginPage.module.css
│   │   │   └── index.ts
│   │   ├── dashboard/
│   │   │   ├── DashboardPage.tsx
│   │   │   └── index.ts
│   │   ├── chat/
│   │   │   ├── ChatPage.tsx
│   │   │   └── index.ts
│   │   ├── admin/
│   │   │   ├── users/
│   │   │   ├── providers/
│   │   │   └── settings/
│   │   └── error/
│   │       ├── NotFoundPage.tsx
│   │       ├── ErrorPage.tsx
│   │       └── index.ts
│   ├──
│   ├── hooks/                        # 自定义Hooks
│   │   ├── useAuth.ts
│   │   ├── useChat.ts
│   │   ├── useApi.ts
│   │   └── index.ts
│   ├──
│   ├── services/                     # API服务
│   │   ├── api.ts                    # API基础配置
│   │   ├── auth.ts                   # 认证相关API
│   │   ├── user.ts                   # 用户相关API
│   │   ├── chat.ts                   # 对话相关API
│   │   ├── provider.ts               # 供应商相关API
│   │   └── index.ts
│   ├──
│   ├── store/                        # 状态管理
│   │   ├── index.ts                  # Store配置
│   │   ├── auth/                     # 认证状态
│   │   │   ├── authStore.ts
│   │   │   └── types.ts
│   │   ├── chat/                     # 对话状态
│   │   │   ├── chatStore.ts
│   │   │   └── types.ts
│   │   └── user/                     # 用户状态
│   │       ├── userStore.ts
│   │       └── types.ts
│   ├──
│   ├── types/                        # 类型定义
│   │   ├── api.ts                    # API类型
│   │   ├── auth.ts                   # 认证类型
│   │   ├── user.ts                   # 用户类型
│   │   ├── chat.ts                   # 对话类型
│   │   ├── provider.ts               # 供应商类型
│   │   └── common.ts                 # 通用类型
│   ├──
│   ├── utils/                        # 工具函数
│   │   ├── constants.ts              # 常量定义
│   │   ├── helpers.ts                # 帮助函数
│   │   ├── formatters.ts             # 格式化函数
│   │   ├── validators.ts             # 验证函数
│   │   └── errorHandler.ts           # 错误处理
│   ├──
│   ├── styles/                       # 样式文件
│   │   ├── globals.css               # 全局样式
│   │   ├── variables.css             # CSS变量
│   │   ├── themes/                   # 主题样式
│   │   └── components/               # 组件样式
│   ├──
│   └── assets/                       # 静态资源
│       ├── images/
│       ├── icons/
│       └── fonts/
├──
├── tests/                           # 测试文件
│   ├── __tests__/                   # 测试用例
│   ├── __mocks__/                   # Mock文件
│   ├── fixtures/                    # 测试数据
│   └── utils/                       # 测试工具
├──
└── docs/                           # 文档
    ├── component-library.md         # 组件库文档
    ├── state-management.md          # 状态管理文档
    └── deployment.md                # 部署文档
```

---

## 📋 结构规范检查清单

### **项目根目录检查**
- [ ] 包含必要的配置文件（docker-compose.yml, .env.example等）
- [ ] docs/目录结构完整
- [ ] scripts/目录包含必要的脚本
- [ ] 服务目录命名符合规范

### **Python服务检查**
- [ ] app/目录作为主应用目录
- [ ] core/、models/、repositories/、services/、routers/目录完整
- [ ] 包含完整的测试目录结构
- [ ] Dockerfile和requirements文件存在

### **Go服务检查**
- [ ] cmd/目录包含应用入口
- [ ] internal/目录结构完整
- [ ] pkg/目录包含可复用代码
- [ ] go.mod和go.sum文件存在

### **React前端检查**
- [ ] src/目录结构完整
- [ ] components/、pages/、hooks/、services/、store/目录存在
- [ ] TypeScript配置完整
- [ ] 包含测试目录结构