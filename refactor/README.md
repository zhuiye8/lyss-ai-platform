# Lyss AI Platform 重构方案文档

## 📋 文档概述

本目录包含Lyss AI Platform项目的完整重构分析和实施方案。基于项目尚未成功运行的现状，制定了摆脱历史包袱的重新设计策略。

**重构理念**: 无需兼容现有数据，按生产标准重新构建  
**文档状态**: 已完成模块化拆分，清理历史文档  
**更新日期**: 2025-01-20

---

## 📖 推荐阅读顺序

### 🎯 **阶段1: 项目总体了解** (必读)
1. **[current-issues.md](./analysis/current-issues.md)** - 了解当前项目存在的所有问题
2. **[services-overview.md](./architecture/services-overview.md)** - 了解重新设计的服务架构

### 🏗️ **阶段2: 架构设计深入** (必读)
3. **[database-design.md](./architecture/database-design.md)** - 数据库架构设计
4. **[deployment-setup.md](./architecture/deployment-setup.md)** - 部署架构和Docker配置

### 📐 **阶段3: 开发规范学习** (必读)
5. **[naming-conventions.md](./standards/naming-conventions.md)** - 统一命名规范
6. **[project-structure.md](./standards/project-structure.md)** - 项目结构标准
7. **[coding-standards.md](./standards/coding-standards.md)** - 编码规范标准

### 🚀 **阶段4: 实施计划执行** (必读)
8. **[phase-1-foundation.md](./implementation/phase-1-foundation.md)** - 第一阶段详细实施计划

---

## 🔍 Context7调研标注

### ⚠️ **需要Context7调研的技术栈**

以下文档中包含需要Context7调研验证的技术实现细节：

#### 1. **[services-overview.md](./architecture/services-overview.md)**
- **第5节: lyss-chat-service** 
  ```
  🔍 需要Context7调研: EINO框架
  - Go + EINO + PostgreSQL 技术栈
  - EINO框架集成方法
  - 多供应商模型调用实现
  - 流式响应处理机制
  ```

#### 2. **[services-overview.md](./architecture/services-overview.md)**
- **第6节: lyss-memory-service**
  ```
  🔍 需要Context7调研: Mem0AI
  - FastAPI + Mem0AI + Qdrant + PostgreSQL 技术栈
  - Mem0AI集成方法
  - 智能记忆检索实现
  - 个性化上下文增强机制
  ```

#### 3. **[database-design.md](./architecture/database-design.md)**
- **记忆服务数据库部分**
  ```
  🔍 需要Context7调研: Mem0AI数据模型
  - user_memories表结构是否与Mem0AI兼容
  - embedding_id字段的具体实现
  - 与Qdrant的集成方式
  ```

#### 4. **[deployment-setup.md](./architecture/deployment-setup.md)**
- **lyss-chat-service和lyss-memory-service配置**
  ```
  🔍 需要Context7调研: 服务配置
  - EINO框架的环境变量和配置
  - Mem0AI的Docker部署配置
  - 服务间集成的具体参数
  ```

#### 5. **[phase-1-foundation.md](./implementation/phase-1-foundation.md)**
- **第13-15天: EINO Service编译修复**
  ```
  🔍 需要Context7调研: EINO框架最新API
  - 最新版本的API变化
  - 正确的代码实现方式
  - 编译和集成步骤
  ```

### ✅ **无需Context7调研的内容**
- 所有的命名规范和项目结构
- 数据库基础设计（除Mem0AI相关）
- Docker基础配置
- Python/Go/React的编码规范
- 用户、供应商、认证相关服务设计

---

## 🎯 微服务开发建议

### 📚 **按微服务分别开发** (适合逐步实施)

#### **🌐 API Gateway & Auth相关**
```
开发所需文档:
- analysis/current-issues.md (服务命名问题部分)
- architecture/services-overview.md (第1-2节)
- standards/naming-conventions.md (API命名部分)
- implementation/phase-1-foundation.md (相关实施步骤)
```

#### **👥 User Service相关**
```
开发所需文档:
- architecture/services-overview.md (第3节)
- architecture/database-design.md (用户服务数据库部分)
- standards/project-structure.md (Python服务结构)
- implementation/phase-1-foundation.md (相关实施步骤)
```

#### **🔌 Provider Service相关**
```
开发所需文档:
- architecture/services-overview.md (第4节)
- architecture/database-design.md (供应商服务数据库部分)
- analysis/current-issues.md (One-API集成相关)
```

#### **💬 Chat Service相关** ⚠️ **需要Context7调研**
```
开发所需文档:
- architecture/services-overview.md (第5节)
- architecture/database-design.md (对话服务数据库部分)
- standards/project-structure.md (Go服务结构)
- implementation/phase-1-foundation.md (EINO修复部分)

🔍 Context7调研重点:
- EINO框架最新API使用方法
- Go + EINO的集成方式
- 流式响应的具体实现
```

#### **🧠 Memory Service相关** ⚠️ **需要Context7调研**
```
开发所需文档:
- architecture/services-overview.md (第6节)
- architecture/database-design.md (记忆服务数据库部分)
- deployment-setup.md (Qdrant配置部分)

🔍 Context7调研重点:
- Mem0AI的安装和配置
- 与Qdrant的集成方式
- 智能记忆的数据模型
```

#### **🎨 Frontend相关**
```
开发所需文档:
- architecture/services-overview.md (第7节)
- analysis/current-issues.md (前端界面问题)
- standards/project-structure.md (React结构)
- standards/coding-standards.md (TypeScript规范)
```

---

## 📂 最终文档结构

```
refactor/
├── README.md                          # 📖 总览和阅读指南（本文档）
├── analysis/                          # 📊 现状分析
│   └── current-issues.md              # 当前问题分析
├── architecture/                      # 🏗️ 架构设计
│   ├── services-overview.md          # 服务架构总览
│   ├── database-design.md            # 数据库架构设计
│   └── deployment-setup.md           # 部署架构设计
├── standards/                         # 📐 开发规范
│   ├── naming-conventions.md          # 命名规范标准
│   ├── project-structure.md          # 项目结构标准
│   └── coding-standards.md           # 编码规范标准
└── implementation/                    # 🚀 实施计划
    └── phase-1-foundation.md         # 第一阶段详细计划
```

---

## 🎯 核心决策总结

### **架构决策**
- **完全重新设计** - 不考虑历史数据兼容性
- **7个独立微服务** - 职责清晰，易于维护
- **生产就绪标准** - 所有组件按生产环境设计

### **技术方案**
- **确定技术**: One-API机制、微服务架构、Docker部署
- **待调研技术**: EINO框架、Mem0AI集成 🔍
- **前端方案**: React 18 + TypeScript + Ant Design X

### **开发规范**
- **命名规范**: lyss-{service-name}统一格式
- **项目结构**: Python/Go/React标准化模板
- **编码规范**: 中文注释、严格类型检查

---

## 🚀 开发任务优先级

### **立即可开始的开发任务**
1. ✅ 统一服务命名规范
2. ✅ 重建项目目录结构  
3. ✅ 修复基础配置问题
4. ✅ 建立开发规范

### **需要Context7调研后开发**
1. 🔍 EINO Service编译修复
2. 🔍 Memory Service集成开发
3. 🔍 Chat和Memory服务的具体实现

---

**这些文档专为2人开发团队优化，提供了清晰的开发路径和技术实施指导。**