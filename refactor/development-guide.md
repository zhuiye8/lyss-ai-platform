# Lyss AI平台开发指南

## 📋 开发指南概述

本文档是Lyss AI平台的核心开发指南，基于refactor文档分析和Context7技术调研，为开发团队提供清晰的开发路径、阶段规划和技术指导。

---

## 🎯 开发策略确定

### **策略选择: 渐进式重构 + 新模块开发**

经过综合评估，采用以下开发策略：

1. **保留可用代码** - 前端登录功能、API Gateway基础架构已完成80%
2. **重构核心模块** - Chat Service、Memory Service采用最新技术栈重构
3. **新建缺失模块** - Provider Service基于One-API架构全新开发
4. **现代化前端** - 使用Ant Design X重构对话界面

---

## 🏗️ 开发阶段规划

### **阶段一: 基础设施完善** (1-2周)

**目标**: 建立稳固的基础服务层，确保多供应商管理和用户认证功能完备

#### **开发顺序**:
1. **lyss-provider-service** (新建，优先级：🔥 紧急)
2. **lyss-auth-service** (补充完善，优先级：⚡ 高)  
3. **lyss-user-service** (重构分离，优先级：⚡ 高)

#### **阶段一详细开发指导**:

**1.1 开发 lyss-provider-service**
```bash
# 必读文档
📖 /refactor/tech-knowledge/reference-projects/dify-analysis.md
📖 /refactor/tech-knowledge/reference-projects/one-api-analysis.md
📖 /refactor/architecture/services/lyss-provider-service.md
📖 /refactor/standards/coding-standards/python-fastapi.md

# 技术栈参考
🔧 Dify的Provider抽象层设计
🔧 One-API的Channel管理概念
🔧 统一的凭证验证和错误映射机制
```

**开发重点**:
- 实现Dify式的Provider抽象层
- 集成One-API的Channel负载均衡
- 建立统一的API代理和错误处理
- 完善多租户凭证隔离机制

**1.2 完善 lyss-auth-service**
```bash
# 必读文档  
📖 /refactor/architecture/services/lyss-auth-service.md
📖 /refactor/architecture/database-design.md
📖 /refactor/standards/coding-standards/python-fastapi.md
📖 /refactor/analysis/current-issues.md

# 现有代码基础
🔧 JWT认证机制已实现80%
🔧 Redis会话管理已集成
🔧 多租户认证框架已建立
```

**开发重点**:
- 补充OAuth2/OIDC联邦认证支持
- 完善用户权限管理RBAC系统
- 优化JWT令牌刷新和安全策略
- 集成用户画像和偏好设置

**1.3 重构 lyss-user-service**
```bash
# 必读文档
📖 /refactor/architecture/services/lyss-user-service.md
📖 /refactor/architecture/database-design.md
📖 /refactor/tech-knowledge/reference-projects/openwebui-analysis.md

# 重构原因
⚠️ 从tenant-service分离用户管理逻辑
⚠️ 采用SQLAlchemy优化并发性能
⚠️ 建立清晰的服务边界
```

**开发重点**:
- 用户生命周期管理（注册、激活、禁用）
- 租户关联和权限继承
- 用户偏好和配置管理
- 用户活动日志和审计

---

### **阶段二: 核心AI功能** (2-3周)

**目标**: 实现平台核心AI对话和智能记忆功能，建立完整的AI服务链路

#### **开发顺序**:
4. **lyss-chat-service** (新建，优先级：🔥 紧急)
5. **lyss-memory-service** (新建，优先级：🔥 紧急)
6. **lyss-frontend** (重构，优先级：⚡ 高)

#### **阶段二详细开发指导**:

**2.1 开发 lyss-chat-service**
```bash
# 必读文档
📖 /refactor/tech-knowledge/eino-framework.md
📖 /refactor/architecture/services/lyss-chat-service.md
📖 /refactor/standards/coding-standards/go-standards.md
📖 /refactor/tech-knowledge/version-locks.md

# Context7调研成果
🚀 EINO v0.3.52最新API用法
🚀 compose.NewChain和compose.NewGraph编排
🚀 多供应商模型集成方案
🚀 流式响应最佳实践
```

**开发重点**:
- 基于EINO框架的工作流编排
- 与Provider Service的模型调用集成
- 实时流式响应WebSocket支持
- 对话上下文管理和记忆增强

**2.2 开发 lyss-memory-service**
```bash
# 必读文档
📖 /refactor/tech-knowledge/mem0ai-integration.md
📖 /refactor/architecture/services/lyss-memory-service.md
📖 /refactor/standards/coding-standards/python-fastapi.md
📖 /refactor/tech-knowledge/reference-projects/openwebui-analysis.md

# Context7调研成果
🧠 Mem0AI最新集成方案
🧠 Qdrant向量数据库配置
🧠 智能记忆检索和用户画像
🧠 SQLAlchemy并发优化
```

**开发重点**:
- Mem0AI与Qdrant的无缝集成
- 智能对话记忆提取和存储
- 语义检索和个性化上下文生成
- 用户画像分析和行为模式识别

**2.3 重构 lyss-frontend**
```bash
# 必读文档
📖 /refactor/tech-knowledge/antd-x-components.md
📖 /refactor/architecture/services/lyss-frontend.md
📖 /refactor/standards/coding-standards/typescript-react.md
📖 /refactor/analysis/current-issues.md

# Context7调研成果
💎 Ant Design X最新聊天组件
💎 useXChat和useXAgent Hooks
💎 现代化响应式设计方案
💎 实时通信WebSocket优化
```

**开发重点**:
- 使用Ant Design X重构对话界面
- 实现对话历史侧边栏管理
- 集成实时流式响应显示
- 响应式设计和移动端适配

---

### **阶段三: 整合优化** (1周)

**目标**: 服务间集成测试、性能优化和部署准备

#### **整合任务**:
7. **服务间集成测试**
8. **性能优化和监控**
9. **部署配置和文档**

#### **阶段三详细指导**:

**3.1 集成测试**
```bash
# 测试重点
🧪 API Gateway路由和代理功能
🧪 认证授权全链路测试
🧪 Provider多供应商切换测试
🧪 Chat和Memory服务协作测试
🧪 前端实时交互测试
```

**3.2 性能优化**
```bash
# 优化重点
⚡ 数据库连接池和查询优化
⚡ Redis缓存策略优化
⚡ WebSocket连接管理优化
⚡ API响应时间和并发优化
⚡ 前端资源加载和渲染优化
```

**3.3 部署准备**
```bash
# 部署配置
🐳 Docker容器化配置
🐳 docker-compose编排文件
🐳 环境变量和配置管理
🐳 健康检查和监控配置
🐳 日志收集和分析配置
```

---

## 📚 开发时必读文档指南

### **开发前必读 (ALL)**
```bash
📖 /refactor/README.md                           # 项目概览和开发状态
📖 /refactor/tech-knowledge/README.md            # 技术知识库概览
📖 /refactor/standards/coding-standards/README.md # 编码规范总览
📖 /refactor/tech-knowledge/version-locks.md # 版本锁定要求
```

### **Provider Service开发**
```bash
# 架构设计
📖 /refactor/architecture/services/lyss-provider-service.md
📖 /refactor/architecture/database-design.md

# 技术参考  
📖 /refactor/tech-knowledge/reference-projects/dify-analysis.md
📖 /refactor/tech-knowledge/reference-projects/one-api-analysis.md

# 编码规范
📖 /refactor/standards/coding-standards/python-fastapi.md
📖 /refactor/standards/coding-standards/general-principles.md
```

### **Chat Service开发**
```bash
# 架构设计
📖 /refactor/architecture/services/lyss-chat-service.md
📖 /refactor/architecture/database-design.md

# 技术文档
📖 /refactor/tech-knowledge/eino-framework.md
📖 /refactor/tech-knowledge/version-locks.md

# 编码规范
📖 /refactor/standards/coding-standards/go-standards.md
📖 /refactor/standards/coding-standards/general-principles.md
```

### **Memory Service开发**
```bash
# 架构设计
📖 /refactor/architecture/services/lyss-memory-service.md
📖 /refactor/architecture/database-design.md

# 技术文档
📖 /refactor/tech-knowledge/mem0ai-integration.md
📖 /refactor/tech-knowledge/reference-projects/openwebui-analysis.md

# 编码规范
📖 /refactor/standards/coding-standards/python-fastapi.md
📖 /refactor/standards/coding-standards/general-principles.md
```

### **Frontend开发**
```bash
# 架构设计
📖 /refactor/architecture/services/lyss-frontend.md

# 技术文档
📖 /refactor/tech-knowledge/antd-x-components.md
📖 /refactor/tech-knowledge/reference-projects/openwebui-analysis.md

# 编码规范
📖 /refactor/standards/coding-standards/typescript-react.md
📖 /refactor/standards/coding-standards/general-principles.md
```

### **Auth/User Service开发**
```bash
# 架构设计
📖 /refactor/architecture/services/lyss-auth-service.md
📖 /refactor/architecture/services/lyss-user-service.md
📖 /refactor/architecture/database-design.md

# 参考实现
📖 /refactor/tech-knowledge/reference-projects/openwebui-analysis.md

# 编码规范
📖 /refactor/standards/coding-standards/python-fastapi.md
📖 /refactor/standards/coding-standards/general-principles.md
```

---

## ⚠️ 开发注意事项

### **技术栈使用要求**
1. **严格版本控制**: 必须按照`/refactor/tech-knowledge/version-locks.md`的版本要求
2. **Context7优先**: 优先使用已通过Context7验证的API和配置
3. **中文注释**: 所有代码注释和文档使用中文
4. **统一规范**: 严格遵循各语言的编码规范文档

### **架构设计原则**
1. **服务单一职责**: 每个服务专注一个业务领域
2. **数据库隔离**: 每个服务拥有独立的数据库
3. **API优先设计**: 服务间通过REST API通信
4. **无状态设计**: 所有服务支持水平扩展
5. **故障隔离**: 单服务故障不影响整体系统

### **开发质量保证**
1. **代码审查**: 每个PR需要代码审查
2. **单元测试**: 核心逻辑必须有单元测试覆盖
3. **集成测试**: 服务间接口必须有集成测试
4. **性能测试**: 关键接口需要性能基准测试
5. **安全扫描**: 定期进行安全漏洞扫描

### **错误处理规范**
1. **统一错误格式**: 所有API返回统一的错误响应格式
2. **错误分类**: 按照业务、系统、网络等维度分类错误
3. **错误日志**: 详细记录错误上下文和调用链
4. **用户友好**: 面向用户的错误信息简洁易懂
5. **监控告警**: 关键错误需要实时监控告警

---

## 🚀 开发环境准备

### **本地开发环境**
```bash
# 基础环境要求
✅ Python 3.11+
✅ Go 1.21+  
✅ Node.js 18+
✅ Docker 24.x+
✅ PostgreSQL 15.x
✅ Redis 7.x

# 开发工具推荐
🛠️ VS Code + 相关插件
🛠️ Git + 代码规范检查
🛠️ Postman/Insomnia API测试
🛠️ Redis Desktop Manager
🛠️ pgAdmin/DBeaver数据库管理
```

### **服务启动顺序**
```bash
# 1. 启动基础设施
docker-compose up -d postgres redis qdrant minio

# 2. 启动核心服务 (按依赖顺序)
cd auth-service && python main.py        # 端口8001
cd user-service && python main.py        # 端口8002  
cd provider-service && python main.py    # 端口8003
cd chat-service && go run main.go        # 端口8004
cd memory-service && python main.py      # 端口8005

# 3. 启动API网关
cd backend && python main.py             # 端口8000

# 4. 启动前端
cd frontend && npm run dev                # 端口3000
```

### **开发调试技巧**
```bash
# 日志查看
tail -f logs/服务名.log

# 健康检查
curl http://localhost:端口/health

# API测试
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "test"}'

# 数据库连接测试
psql -h localhost -p 5433 -U lyss -d lyss_db
```

---

## 📈 开发进度跟踪

### **里程碑检查点**

**阶段一完成标准**:
- [ ] Provider Service API测试100%通过
- [ ] Auth Service认证流程完整
- [ ] User Service用户管理功能完备
- [ ] 三个服务健康检查正常
- [ ] API Gateway路由代理正常

**阶段二完成标准**:
- [ ] Chat Service EINO集成正常
- [ ] Memory Service Mem0AI集成正常  
- [ ] Frontend Ant Design X界面完整
- [ ] 端到端对话流程正常
- [ ] 实时流式响应正常

**阶段三完成标准**:
- [ ] 所有服务集成测试通过
- [ ] 性能基准达到要求
- [ ] 部署配置文档完整
- [ ] 监控告警配置完成
- [ ] 用户验收测试通过

### **每日开发检查**
```bash
# 代码质量检查
make lint          # 代码规范检查
make test          # 单元测试运行
make coverage      # 测试覆盖率检查

# 服务健康检查  
make health-check  # 所有服务健康状态

# 构建测试
make build         # 本地构建测试
make docker-build  # Docker镜像构建
```

---

## 🎯 成功标准

### **技术目标**
1. **系统稳定性**: 99.9%可用性，MTTR < 5分钟
2. **响应性能**: API响应时间 < 200ms，流式响应延迟 < 100ms  
3. **并发能力**: 支持1000+并发用户，5000+ QPS
4. **扩展性**: 所有服务支持水平扩展
5. **安全性**: 通过安全扫描，无高危漏洞

### **业务目标**
1. **功能完整性**: 覆盖AI对话、记忆管理、多供应商切换核心功能
2. **用户体验**: 现代化界面，响应式设计，流畅交互
3. **多租户支持**: 完善的租户隔离和权限管理
4. **可维护性**: 清晰的代码结构，完整的文档

### **团队目标**
1. **开发效率**: 按时完成三个阶段开发
2. **代码质量**: 测试覆盖率 > 80%，代码审查覆盖率100%
3. **技术债务**: 控制技术债务，及时重构优化
4. **知识传承**: 完整的开发文档和技术分享

---

## 📝 总结

通过本开发指南，团队可以：

1. **明确开发路径**: 三个阶段的清晰开发顺序和重点
2. **技术指导**: 基于Context7调研的权威技术方案
3. **质量保证**: 完善的开发规范和检查标准
4. **风险控制**: 渐进式开发策略降低技术风险

**现在可以立即开始阶段一的开发工作！**从lyss-provider-service开始，这是解决当前多供应商管理问题的关键模块。