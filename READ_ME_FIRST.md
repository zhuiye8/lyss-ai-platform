# 🚀 Claude开发助手记忆文件 - Lyss AI Platform

## 📅 最后更新: 2025-07-11

### 🎯 项目状态概览

**Lyss AI Platform** 是一个企业级AI服务聚合与管理平台，采用微服务架构，实现多租户的AI模型集成、编排和治理。

**当前开发阶段**: 第一阶段 - 核心功能开发  
**项目完成度**: 基础设施 100%，Auth Service 100%，Tenant Service 100%  
**下一个开发目标**: Backend API Gateway

---

## ✅ 已完成的核心组件

### 1. 基础设施服务 (100%)
- **PostgreSQL**: 主数据库，完整表结构，测试数据已导入
- **Redis**: 缓存服务 (注意：ACL配置被注释掉，开发环境正常)
- **Docker Compose**: 基础设施一键启动，位于项目根目录
- **数据库初始化**: sql/init.sql包含完整的表结构和测试数据

### 2. Auth Service - 认证服务 (100%)
**位置**: `/auth-service/`  
**端口**: 8001  
**完成时间**: 2025-07-10

**核心功能**:
- JWT认证机制：HS256算法，30分钟访问令牌，7天刷新令牌
- Redis集成：会话管理、速率限制、令牌黑名单
- 与Tenant Service集成调用用户验证接口
- 完整错误处理和中文错误消息
- 结构化JSON日志记录
- 健康检查接口 `/health`

**关键API**:
- `POST /auth/login` - 用户登录
- `POST /auth/refresh` - 刷新令牌
- `POST /auth/logout` - 用户登出

### 3. Tenant Service - 租户服务 (100%)
**位置**: `/tenant-service/`  
**端口**: 8002  
**完成时间**: 2025-07-11

**核心功能**:
- **租户管理**: 完整CRUD，分页查询，统计信息
- **用户管理**: 注册、更新、状态管理，RBAC权限体系
- **供应商凭证管理**: pgcrypto加密存储API密钥，支持OpenAI/Anthropic/Google等
- **内部服务接口**: `/internal/users/verify` 为Auth Service提供用户验证
- **多租户数据隔离**: 严格tenant_id过滤，确保数据安全
- **SQLAlchemy关系映射**: 修复了循环依赖问题，使用字符串引用
- **安全机制**: bcrypt密码加密 + pgcrypto凭证加密

**关键API**:
- `POST /admin/tenants` - 创建租户
- `GET /admin/tenants` - 租户列表
- `POST /admin/users` - 创建用户  
- `GET /admin/users` - 用户列表
- `POST /admin/suppliers` - 添加供应商凭证
- `GET /admin/suppliers` - 供应商凭证列表
- `POST /internal/users/verify` - 内部用户验证

---

## 🔧 重要技术实现细节

### 虚拟环境配置
- **Auth Service**: 使用 `auth-service/venv/`
- **Tenant Service**: 使用 `tenant-service/venv/`
- 激活命令: `source venv/bin/activate`

### 数据库配置
- **连接信息**: PostgreSQL @ localhost:5432
- **数据库**: lyss_platform
- **用户**: lyss_user / lyss_dev_password_2025
- **重要**: 所有查询必须包含tenant_id过滤（多租户隔离）

### pgcrypto加密
- **环境变量**: `TENANT_SERVICE_PGCRYPTO_KEY`
- **用途**: 供应商API密钥列级加密存储
- **实现**: `tenant_service/core/encryption.py`
- **测试**: 加密解密功能已验证正常

### SQLAlchemy关系映射
- **问题**: 之前存在循环依赖导致关系映射失败
- **解决**: 使用字符串引用 + selectinload，已完全修复
- **状态**: User/Tenant/Role关系映射正常工作

---

## 📋 开发规范要求

### 必须遵循的文档
1. **DEVELOPMENT_PRIORITY.md** - 开发优先级和进度追踪
2. **docs/STANDARDS.md** - 开发规范总纲 
3. **docs/PROJECT_STRUCTURE.md** - 项目目录结构规范
4. **CLAUDE.md** - Claude开发助手指令

### 代码规范
- **注释语言**: 全部使用中文
- **错误信息**: 返回中文错误描述
- **日志格式**: JSON结构化，包含request_id和tenant_id
- **API响应**: 统一格式，包含success、data、message字段
- **多租户**: 所有业务查询必须包含tenant_id过滤

---

## 🚀 下一步开发任务

### 🎯 立即开始: Backend API Gateway
**位置**: `/backend/`  
**端口**: 8000  
**重要性**: 高优先级

**开发前必读**:
1. `docs/api_gateway.md` - API网关服务规范
2. `docs/STANDARDS.md` - 开发规范总纲
3. `docs/PROJECT_STRUCTURE.md` - 项目结构规范

**核心功能要求**:
- [ ] 统一认证中间件（集成Auth Service）
- [ ] 路由转发到各微服务（Auth + Tenant）
- [ ] 请求响应日志记录
- [ ] 错误处理和响应标准化
- [ ] CORS和安全头配置
- [ ] 健康检查聚合
- [ ] API文档聚合

**技术要点**:
- FastAPI路由分发
- HTTP客户端调用微服务
- JWT认证集成
- 中间件链设计
- 错误处理统一化

---

## ⚠️ 重要注意事项

### 环境问题
- **Redis ACL**: 已注释掉ACL配置文件，开发环境正常使用
- **依赖安装**: 所有依赖都在各服务的venv中，记得激活虚拟环境
- **数据库**: 基础设施已启动，测试数据已存在

### 开发约束
1. **安全第一**: 所有数据操作必须验证tenant_id
2. **严格按规范**: 不得随意更改既定的架构和规范
3. **中文开发**: 注释、提交、错误信息全部中文
4. **文档更新**: 每完成功能及时更新DEVELOPMENT_PRIORITY.md

### 技术债务状态
**当前技术债务**: 无  
**代码质量**: 高，严格按规范实现  
**测试状态**: pgcrypto加密、SQLAlchemy关系映射已验证

---

## 🔍 快速验证环境

```bash
# 1. 启动基础设施
docker-compose up -d

# 2. 验证Auth Service
cd auth-service
source venv/bin/activate
uvicorn auth_service.main:app --reload --port 8001

# 3. 验证Tenant Service  
cd tenant-service
source venv/bin/activate
uvicorn tenant_service.main:app --reload --port 8002

# 4. 测试pgcrypto
python -c "
from tenant_service.core.encryption import credential_manager
from tenant_service.core.database import AsyncSessionLocal
import asyncio

async def test():
    async with AsyncSessionLocal() as session:
        encrypted = await credential_manager.encrypt_credential(session, 'test-key')
        decrypted = await credential_manager.decrypt_credential(session, encrypted)
        print(f'加密解密测试: {decrypted == \"test-key\"}')

asyncio.run(test())
"
```

---

**🎯 明天继续开发Backend API Gateway，所有基础工作已完成，可以直接开始！**

🚀 明天的流程

  1. Claude会默认读取 CLAUDE.md，了解基本状态
  2. 根据指示读取 READ_ME_FIRST.md，获取详细信息
  3. 阅读 DEVELOPMENT_PRIORITY.md，确认开发优先级
  4. 直接开始 Backend API Gateway 开发

  现在记忆文件和提示词都准备好了，明天的Claude能够无缝接续开发工作！

  祝您休息愉快，明天继续高效开发 Backend API Gateway！ 🚀