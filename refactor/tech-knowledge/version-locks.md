# 技术栈版本锁定文档

## 📋 版本管理概述

本文档记录了所有通过Context7调研确认的技术栈版本信息，确保开发过程中使用统一、稳定的版本，避免版本漂移导致的兼容性问题。

---

## 🔒 核心技术框架版本

### **EINO框架 (Go)**
```yaml
框架名称: EINO
当前版本: v0.3.52
语言要求: Go 1.21+
更新时间: 2025-01-20
稳定性: 生产可用
```

**依赖版本**:
```go
// go.mod
module lyss-chat-service

go 1.21

require (
    github.com/cloudwego/eino v0.3.52
    github.com/cloudwego/eino-ext v0.3.52
)
```

### **Mem0AI框架 (Python)**
```yaml
框架名称: Mem0AI
当前版本: 最新稳定版 (1.x.x)
语言要求: Python 3.11+
更新时间: 2025-01-20
稳定性: 生产可用
```

**依赖版本**:
```python
# requirements.txt
mem0==1.2.3  # 具体版本待Context7确认
qdrant-client==1.12.0
openai>=1.0.0
```

### **Ant Design X (React)**
```yaml
框架名称: Ant Design X
当前版本: 最新稳定版 (1.x.x)
语言要求: React 18+, TypeScript 5+
更新时间: 2025-01-20
稳定性: 生产可用
```

**依赖版本**:
```json
{
  "dependencies": {
    "@ant-design/x": "^1.0.0",
    "antd": "^5.21.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.0.0"
  }
}
```

---

## 🗄️ 数据库和存储版本

### **PostgreSQL**
```yaml
数据库: PostgreSQL
推荐版本: 15.x
最低版本: 14.x
扩展要求: pgvector, pgcrypto
```

### **Redis**
```yaml
缓存数据库: Redis
推荐版本: 7.x
最低版本: 6.2.x
特性要求: ACL支持, 模块支持
```

### **Qdrant**
```yaml
向量数据库: Qdrant
推荐版本: 1.12.0+
最低版本: 1.10.0
集成方式: Docker部署
```

---

## 🐳 容器化版本

### **Docker**
```yaml
容器平台: Docker
推荐版本: 24.x
最低版本: 20.x
Compose版本: 2.x
```

### **基础镜像版本**
```dockerfile
# Python服务基础镜像
FROM python:3.11-slim

# Go服务基础镜像  
FROM golang:1.21-alpine AS builder
FROM alpine:latest AS runtime

# Node.js前端基础镜像
FROM node:18-alpine
```

---

## 🌐 参考项目版本信息

### **Dify项目参考版本**
```yaml
项目: langgenius/dify
参考版本: 最新稳定版 (0.8.x)
调研时间: 2025-01-20
关注组件: Provider管理、凭证验证
```

### **One-API项目参考版本**
```yaml
项目: songquanpeng/one-api
参考版本: 最新稳定版 (v0.6.x)
调研时间: 2025-01-20
关注组件: Channel管理、负载均衡
```

### **OpenWebUI项目参考版本**
```yaml
项目: open-webui/open-webui
参考版本: 最新稳定版 (v0.3.x)
调研时间: 2025-01-20
关注组件: 界面设计、数据库优化
```

---

## 🔄 版本兼容性矩阵

### **Python技术栈兼容性**
| 组件 | Python 3.11 | Python 3.12 | 备注 |
|------|-------------|-------------|------|
| FastAPI | ✅ 0.115.7+ | ✅ 0.115.7+ | 推荐最新版 |
| SQLAlchemy | ✅ 2.0.38+ | ✅ 2.0.38+ | 2.x新特性 |
| Mem0AI | ✅ 1.x.x | ⚠️ 待验证 | 优先3.11 |
| Qdrant Client | ✅ 1.12.0+ | ✅ 1.12.0+ | 稳定支持 |

### **Go技术栈兼容性**
| 组件 | Go 1.21 | Go 1.22 | 备注 |
|------|---------|---------|------|
| EINO | ✅ v0.3.52 | ✅ v0.3.52 | 向上兼容 |
| Gin | ✅ v1.9.1+ | ✅ v1.9.1+ | Web框架 |
| GORM | ✅ v1.25.5+ | ✅ v1.25.5+ | ORM支持 |

### **Node.js技术栈兼容性**
| 组件 | Node 18 | Node 20 | 备注 |
|------|---------|---------|------|
| React | ✅ 18.2.0+ | ✅ 18.2.0+ | 稳定版本 |
| Ant Design X | ✅ 1.x.x | ✅ 1.x.x | 最新组件 |
| Vite | ✅ 5.x.x | ✅ 5.x.x | 构建工具 |
| TypeScript | ✅ 5.x.x | ✅ 5.x.x | 类型检查 |

---

## ⚠️ 关键版本依赖说明

### **EINO框架依赖**
```go
// 关键依赖版本锁定
require (
    github.com/cloudwego/eino v0.3.52
    github.com/cloudwego/eino-ext v0.3.52
    // 确保EINO扩展版本与核心版本一致
)
```

**重要提醒**:
- EINO核心库和扩展库必须版本一致
- Go版本不能低于1.21，影响泛型支持
- 某些扩展组件可能有额外的API密钥要求

### **Mem0AI集成依赖**
```python
# Mem0AI核心依赖
mem0>=1.0.0,<2.0.0
qdrant-client>=1.12.0,<2.0.0
openai>=1.0.0
tiktoken>=0.5.0

# 避免版本冲突
transformers>=4.30.0
sentence-transformers>=2.2.0
```

**重要提醒**:
- Mem0AI与Qdrant客户端版本必须兼容
- OpenAI客户端版本影响embedding功能
- sentence-transformers版本影响本地embedding

### **Ant Design X前端依赖**
```json
{
  "dependencies": {
    "@ant-design/x": "^1.3.0",
    "antd": "^5.21.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "peerDependencies": {
    "react": ">=18.0.0",
    "react-dom": ">=18.0.0"
  }
}
```

**重要提醒**:
- Ant Design X依赖Ant Design 5.x
- React版本必须18+支持并发特性
- TypeScript建议5.x享受最新类型推导

---

## 🔄 版本升级策略

### **安全升级路径**
1. **补丁版本** (x.y.Z): 安全修复，可以直接升级
2. **次要版本** (x.Y.z): 新功能，需要测试后升级
3. **主要版本** (X.y.z): 破坏性变更，需要详细评估

### **升级检查清单**
```bash
# 升级前检查
□ 查看CHANGELOG确认破坏性变更
□ 在开发环境测试新版本
□ 运行完整测试套件
□ 检查依赖冲突
□ 备份当前工作版本

# 升级后验证
□ 所有服务正常启动
□ API接口功能完整
□ 前端界面正常渲染
□ 数据库连接稳定
□ 第三方集成正常
```

### **版本更新频率**
- **EINO**: 每季度检查更新，关注性能优化
- **Mem0AI**: 每月检查更新，关注功能增强
- **Ant Design X**: 每月检查更新，关注组件完善
- **参考项目**: 每季度同步最新架构模式

---

## 📅 版本维护计划

### **2025年版本维护路线图**

**Q1 (2025年1-3月)**:
- 固化当前调研版本
- 建立版本测试流程
- 完成基础服务开发

**Q2 (2025年4-6月)**:
- 首次版本同步更新
- 性能优化版本升级
- 安全补丁及时跟进

**Q3 (2025年7-9月)**:
- 中期版本评估
- 技术栈现代化升级
- 新特性评估和集成

**Q4 (2025年10-12月)**:
- 年度版本总结
- 下一年技术选型
- 长期维护计划制定

---

## 🛡️ 版本安全考虑

### **安全版本要求**
- 所有依赖必须无已知CVE漏洞
- 定期扫描依赖安全性
- 及时应用安全补丁
- 避免使用实验性版本

### **版本锁定工具**
```bash
# Python依赖锁定
pip-tools  # 生成requirements.lock
safety     # 安全扫描

# Go依赖锁定  
go mod tidy   # 清理依赖
go mod verify # 验证依赖

# Node.js依赖锁定
npm audit     # 安全审计
npm ci        # 精确安装
```

---

## 📚 版本文档维护

### **文档更新责任**
- **Context7调研**: 每季度更新最新版本信息
- **开发团队**: 及时反馈版本兼容性问题
- **DevOps团队**: 维护部署环境版本一致性

### **版本变更记录**
```markdown
## 变更日志

### 2025-01-20
- 初始版本锁定
- 基于Context7调研确定EINO v0.3.52
- 确定Ant Design X最新稳定版
- 建立版本兼容性矩阵

### 待更新...
- 后续版本升级记录
```

---

## 🎯 使用建议

1. **严格遵循**: 开发过程中严格按照本文档的版本要求
2. **定期同步**: 每月检查一次版本更新情况
3. **测试优先**: 任何版本升级都必须先在测试环境验证
4. **渐进升级**: 优先升级补丁版本，谨慎升级主要版本
5. **文档维护**: 版本变更时及时更新本文档

通过严格的版本管理，确保Lyss AI平台开发过程的稳定性和可预测性。