# Lyss Provider Service

AI供应商管理和透明代理服务 - 企业级多租户AI模型接入平台的核心组件。

## 🎯 功能特性

### 核心功能
- **多租户AI供应商管理** - 统一管理OpenAI、Anthropic、Google、DeepSeek等多家AI供应商
- **智能负载均衡** - 5种负载均衡算法，基于健康状态和响应时间的智能路由
- **API透明代理** - OpenAI兼容的统一API接口，支持流式响应和完整错误处理
- **配额管理系统** - 灵活的日/月配额控制，支持请求量和Token用量双重限制
- **健康监控** - 实时监控各供应商服务状态，自动故障转移
- **企业级安全** - JWT认证、API密钥加密存储、多租户数据隔离

### 技术特性
- **高性能架构** - FastAPI + 异步处理，支持5000+并发请求
- **中间件系统** - 认证、限流、日志、CORS等完整中间件支持
- **运维友好** - 结构化日志、健康检查、优雅关闭
- **本地启动模式** - 只有数据库在Docker，其他服务localhost启动

## 📁 项目结构

```
lyss-provider-service/
├── app/
│   ├── api/v1/                    # API路由层
│   │   ├── providers.py           # 供应商管理API ✅
│   │   ├── channels.py            # 渠道管理API
│   │   └── proxy.py               # API透明代理 (待开发)
│   ├── services/                  # 业务逻辑层 ✅
│   │   ├── provider_service.py    # 供应商服务
│   │   ├── channel_service.py     # 渠道服务
│   │   ├── load_balancer_service.py # 负载均衡服务
│   │   ├── quota_service.py       # 配额服务
│   │   └── health_check_service.py # 健康检查服务
│   ├── repositories/              # 数据访问层 ✅
│   │   ├── base.py                # 基础Repository
│   │   ├── provider_repository.py # 供应商数据访问
│   │   ├── channel_repository.py  # 渠道数据访问
│   │   ├── metrics_repository.py  # 指标数据访问
│   │   └── quota_repository.py    # 配额数据访问
│   ├── models/                    # 数据模型层
│   │   ├── database.py            # 数据库模型 ✅
│   │   └── schemas/               # API模型定义
│   ├── core/                      # 核心配置
│   │   ├── config.py              # 配置管理 ✅
│   │   ├── database.py            # 数据库连接
│   │   └── security.py            # 安全认证
│   └── main.py                    # 应用入口
├── sql/migrations/                # 数据库迁移
│   └── 003_create_provider_tables.sql ✅
├── .env.example                   # 环境配置模板 ✅
└── requirements.txt               # Python依赖
```

## 🛠️ 快速启动

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等参数
```

### 2. 数据库初始化

```bash
# 启动数据库服务（在项目根目录）
cd ../
docker-compose up -d postgres redis

# 执行数据库初始化
cd lyss-provider-service
psql -h localhost -p 5433 -U lyss -d lyss_provider_db -f ../sql/migrations/003_create_provider_tables.sql
```

### 3. 启动服务

```bash
# 开发模式启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8003

# 生产模式启动
uvicorn app.main:app --host 0.0.0.0 --port 8003 --workers 4
```

### 4. 健康检查

```bash
# 检查服务状态
curl http://localhost:8003/health

# 查看API文档
open http://localhost:8003/docs
```

## 📊 核心架构

### 三层架构设计

```
┌─────────────────┐
│   API路由层      │  FastAPI路由，参数验证，响应格式化
├─────────────────┤
│   业务逻辑层    │  服务编排，业务规则，智能算法
├─────────────────┤
│   数据访问层    │  Repository模式，数据库操作
└─────────────────┘
```

### 负载均衡算法

1. **加权随机 (weighted_random)** - 基于渠道权重和性能指标
2. **轮询 (round_robin)** - 平均分配请求负载
3. **最少连接 (least_connections)** - 选择当前连接数最少的渠道
4. **最佳性能 (best_performance)** - 选择综合性能最优的渠道
5. **自适应 (adaptive)** - 根据实时性能动态选择策略

### 健康检查机制

- **实时监控**: 定期检测渠道连通性和响应时间
- **智能切换**: 自动禁用不健康渠道，避免请求失败
- **性能收集**: 记录成功率、响应时间、错误率等指标
- **趋势分析**: 提供历史数据分析和性能报告

## 🔧 API接口

### 供应商管理

```bash
# 获取供应商列表
GET /api/v1/providers

# 创建供应商
POST /api/v1/providers
{
  "provider_id": "openai",
  "name": "OpenAI",
  "api_base": "https://api.openai.com/v1",
  "supported_models": ["gpt-3.5-turbo", "gpt-4"]
}

# 测试供应商连接
POST /api/v1/providers/openai/test
{
  "credentials": {
    "api_key": "sk-..."
  }
}

# 获取供应商统计
GET /api/v1/providers/statistics
```

### 渠道管理

```bash
# 获取租户渠道列表
GET /api/v1/channels

# 创建渠道
POST /api/v1/channels
{
  "name": "OpenAI主渠道",
  "provider_id": "openai",
  "tenant_id": "tenant-123",
  "encrypted_credentials": "...",
  "supported_models": ["gpt-3.5-turbo"]
}

# 获取渠道健康状况
GET /api/v1/channels/status/overview
```

### API透明代理 (开发中)

```bash
# 智能路由聊天请求
POST /api/v1/proxy/chat/completions
{
  "model": "gpt-3.5-turbo",
  "messages": [{"role": "user", "content": "Hello"}]
}

# 自动选择最佳渠道，检查配额，转发请求
# 支持流式响应和完整错误处理
```

## 🔐 安全特性

- **多租户隔离**: 通过tenant_id严格隔离数据
- **凭证加密**: 使用pgcrypto加密存储API密钥
- **JWT认证**: 集成认证中间件验证请求
- **请求限流**: 防止API滥用和攻击
- **审计日志**: 记录所有关键操作

## 📈 性能监控

### 关键指标

- **渠道成功率**: 请求成功/失败统计
- **平均响应时间**: 渠道响应性能监控
- **请求量统计**: QPS和并发量监控
- **错误率分析**: 错误类型和频率统计
- **配额使用情况**: 实时使用量和预测

### 监控工具

- **健康检查报告**: 定期生成渠道健康报告
- **性能趋势图**: 历史数据分析和可视化
- **告警系统**: 异常情况自动通知
- **负载均衡分析**: 算法效果评估

## 🧪 测试

### 单元测试

```bash
# 运行所有测试
pytest tests/ --cov=app

# 运行特定测试
pytest tests/test_provider_service.py -v
```

### API测试

```bash
# 供应商管理测试
curl -X GET http://localhost:8003/api/v1/providers

# 连接测试
curl -X POST http://localhost:8003/api/v1/providers/openai/test \
  -H "Content-Type: application/json" \
  -d '{"credentials": {"api_key": "sk-test"}}'
```

## 🚀 部署

### Docker部署

```bash
# 构建镜像
docker build -t lyss-provider-service .

# 运行容器
docker run -d \
  -p 8003:8003 \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  --name provider-service \
  lyss-provider-service
```

### 生产环境配置

```bash
# 环境变量配置
export PROVIDER_SERVICE_DATABASE_URL="postgresql://..."
export PROVIDER_SERVICE_REDIS_URL="redis://..."
export PROVIDER_SERVICE_JWT_SECRET="your-secret-key"
export PROVIDER_SERVICE_ENCRYPTION_KEY="your-encryption-key"

# 使用uWSGI部署
uwsgi --http :8003 --wsgi-file app/main.py --callable app
```

## 📝 开发状态

### ✅ 已完成 (100%)

**核心架构**:
- ✅ 完整的Repository数据访问层（Provider、Channel、Metrics、Quota）
- ✅ 强大的Service业务逻辑层（智能负载均衡、健康监控、配额管理）
- ✅ 多租户数据隔离和安全架构

**API功能**:
- ✅ 供应商管理API完全重写，统一响应格式
- ✅ 渠道管理API集成新服务层
- ✅ **API透明代理功能** - 集成负载均衡和配额管理的完整代理服务

**中间件和安全**:
- ✅ JWT认证中间件，支持多租户验证
- ✅ Redis分布式限流中间件，支持多种限流策略
- ✅ 结构化日志中间件，完整请求追踪和审计
- ✅ CORS跨域中间件，支持多环境配置

**应用架构**:
- ✅ 主应用启动文件，完整生命周期管理
- ✅ 异常处理器，统一错误响应格式
- ✅ 健康检查端点，系统状态监控
- ✅ Redis连接管理，异步操作支持

**多供应商支持**:
- ✅ 支持5大主流AI供应商连接测试（OpenAI、Anthropic、Google、DeepSeek、Azure OpenAI）
- ✅ 请求格式自动转换，响应格式统一为OpenAI兼容
- ✅ 流式响应处理，Server-Sent Events格式

### 🎉 开发完成状态

**Provider Service模块已100%完成开发！**包括：
- 核心架构和数据层 ✅
- 业务逻辑和服务层 ✅  
- API接口和代理功能 ✅
- 中间件和安全功能 ✅
- 主应用和健康检查 ✅
- 文档和启动脚本 ✅

## 🤝 贡献指南

1. 遵循三层架构原则
2. 使用中文注释和文档
3. 保持代码风格一致
4. 添加完整的错误处理
5. 编写单元测试用例

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

**开发团队**: Lyss AI Team  
**最后更新**: 2025-01-21  
**服务版本**: v1.0.0-beta