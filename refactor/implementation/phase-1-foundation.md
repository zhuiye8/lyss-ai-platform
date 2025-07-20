# 第一阶段：基础架构重建

## 📋 实施概述

**目标**: 建立新的项目结构，重构基础服务，解决关键技术问题

---

## 🎯 实施目标

### **主要目标**
1. **建立新项目结构** - 按照新规范重组项目目录
2. **修复关键技术问题** - 解决EINO Service编译失败等阻塞问题
3. **重构基础服务** - 统一命名规范，优化服务架构
4. **建立开发环境** - 确保开发环境能够正常工作

### **完成标准**
- 所有服务能够正常启动
- 健康检查端点正常工作
- 基础功能测试通过
- 代码符合新的编码规范

---

## 🔧 详细实施步骤

### **步骤1：项目结构重建**

#### **目录结构调整**
```bash
# 实施任务
□ 备份现有项目代码
□ 创建新的目录结构
□ 重命名所有服务目录
□ 更新docker-compose.yml配置
□ 更新所有配置文件引用
```

**具体操作**:
```bash
# 1. 备份现有代码
cp -r lyss-ai-platform lyss-ai-platform-backup-$(date +%Y%m%d)

# 2. 重命名服务目录
mv auth-service lyss-auth-service
mv tenant-service lyss-user-service  # 重新定位为用户服务
mv backend lyss-api-gateway
mv frontend lyss-frontend

# 3. 创建新服务目录
mkdir lyss-provider-service
mkdir lyss-chat-service  
mkdir lyss-memory-service

# 4. 创建标准化目录结构
mkdir -p {docs,scripts,infrastructure,sql,tests,shared}
mkdir -p docs/{api,development,architecture,operation}
mkdir -p scripts/deploy
mkdir -p infrastructure/{docker,k8s,monitoring}
mkdir -p sql/{migrations,seeds,schema}
```

#### **配置文件更新**
```bash
# 实施任务
□ 更新docker-compose.yml服务名
□ 更新环境变量配置
□ 修改所有服务间调用地址
□ 更新API路由配置
□ 修改前端API调用地址
```

**关键配置更新**:
```yaml
# docker-compose.yml 更新示例
services:
  lyss-postgres:  # 统一命名
    image: postgres:15-alpine
    container_name: lyss-postgres
    
  lyss-api-gateway:  # 新服务名
    build: ./lyss-api-gateway
    container_name: lyss-api-gateway
    environment:
      - AUTH_SERVICE_URL=http://lyss-auth-service:8001
      - USER_SERVICE_URL=http://lyss-user-service:8002
```

### **步骤2：基础服务重构**

#### **lyss-auth-service重构**
```bash
# 实施任务
□ 更新代码中的服务调用地址
□ 修改配置文件和环境变量
□ 更新API文档
□ 编写单元测试
□ 验证服务功能
```

**重构要点**:
```python
# 更新服务间调用配置
class Config:
    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://lyss-user-service:8002")
    
# 更新API路由
@router.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    # 调用用户服务验证
    user_response = await http_client.post(
        f"{Config.USER_SERVICE_URL}/api/v1/internal/users/authenticate",
        json=credentials.dict()
    )
```

#### **lyss-user-service重构**
```bash
# 实施任务
□ 从tenant-service分离用户管理功能
□ 建立新的数据库结构
□ 实现内部API接口
□ 更新权限管理逻辑
□ 编写API文档
```

**新服务结构**:
```python
# lyss-user-service/app/main.py
from fastapi import FastAPI
from app.routers import users, tenants, groups, internal

app = FastAPI(title="Lyss User Service", version="1.0.0")

# 公共API
app.include_router(users.router, prefix="/api/v1/users", tags=["用户管理"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["租户管理"])
app.include_router(groups.router, prefix="/api/v1/groups", tags=["群组管理"])

# 内部API（供其他服务调用）
app.include_router(internal.router, prefix="/api/v1/internal", tags=["内部接口"])
```

#### **lyss-api-gateway重构**
```bash
# 实施任务
□ 更新路由配置
□ 修改服务发现逻辑
□ 实现新的代理规则
□ 更新认证中间件
□ 测试所有路由转发
```

### **步骤3：关键技术问题修复**

#### **EINO Service编译修复** 🔍 **需要Context7调研**
```bash
# 实施任务
□ 分析EINO框架最新API变化
□ 更新go.mod依赖版本
□ 重写不兼容的代码
□ 测试EINO功能
□ 编写集成测试
```

**修复步骤**:
```go
// 1. 更新依赖版本
go get github.com/cloudwego/eino@latest
go get github.com/cloudwego/eino-ext/components/model/openai@latest

// 2. 修复类型定义错误
// 原代码（错误）
func (w *ChatWorkflow) Execute(ctx context.Context, input map[string]any) (*WorkflowResponse, error) {
    chain, err := eino.CompiledChain[map[string]any, *Message]()  // 错误：类型不存在
}

// 修复后（正确）
func (w *ChatWorkflow) Execute(ctx context.Context, input map[string]any) (*WorkflowResponse, error) {
    chain, err := compose.NewChain[map[string]any, string]().
        AppendChatTemplate(template).
        AppendChatModel(model).
        Compile(ctx)
}
```

#### **数据库架构重新设计**
```bash
# 实施任务
□ 设计新的数据库结构
□ 编写迁移脚本
□ 创建初始化数据
□ 测试数据隔离
□ 验证性能表现
```

**数据库重建**:
```sql
-- 1. 创建新的数据库结构
DROP DATABASE IF EXISTS lyss_user_db;
DROP DATABASE IF EXISTS lyss_provider_db;
DROP DATABASE IF EXISTS lyss_chat_db;
DROP DATABASE IF EXISTS lyss_memory_db;

CREATE DATABASE lyss_user_db;
CREATE DATABASE lyss_provider_db;
CREATE DATABASE lyss_chat_db;
CREATE DATABASE lyss_memory_db;

-- 2. 执行表结构创建
\c lyss_user_db
\i sql/migrations/001_create_user_tables.sql

\c lyss_provider_db  
\i sql/migrations/002_create_provider_tables.sql
```

#### **环境变量和配置标准化**
```bash
# 实施任务
□ 制定环境变量命名规范
□ 更新所有服务配置
□ 创建环境变量模板
□ 更新部署脚本
□ 验证配置正确性
```

### **步骤4：基础功能验证**

#### **服务集成测试**
```bash
# 实施任务
□ 编写健康检查测试
□ 测试服务间通信
□ 验证认证流程
□ 测试数据库连接
□ 检查日志输出
```

**测试脚本**:
```bash
#!/bin/bash
# scripts/test-integration.sh

echo "🧪 开始集成测试..."

# 1. 检查所有服务健康状态
services=("lyss-api-gateway:8000" "lyss-auth-service:8001" "lyss-user-service:8002")

for service in "${services[@]}"; do
    url="http://localhost:${service#*:}/health"
    echo "检查 ${service%:*}..."
    
    if curl -f -s "$url" > /dev/null; then
        echo "✅ ${service%:*} 健康"
    else
        echo "❌ ${service%:*} 异常"
        exit 1
    fi
done

# 2. 测试认证流程
echo "🔐 测试用户认证..."
login_response=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@lyss.dev","password":"admin123"}')

if echo "$login_response" | grep -q "access_token"; then
    echo "✅ 用户认证成功"
else
    echo "❌ 用户认证失败"
    exit 1
fi

echo "✅ 所有集成测试通过!"
```

#### **性能测试和优化**
```bash
# 实施任务
□ 进行负载测试
□ 分析性能瓶颈
□ 优化数据库查询
□ 调整缓存策略
□ 验证并发处理
```

#### **文档更新和部署验证**
```bash
# 实施任务
□ 更新API文档
□ 编写部署指南
□ 创建开发环境指南
□ 验证Docker部署
□ 准备交付文档
```

---

## 📊 完成标准

### **代码完成要求**
1. **重构后的服务代码**
   - lyss-api-gateway (完整重构)
   - lyss-auth-service (配置更新)
   - lyss-user-service (从tenant-service分离)
   - lyss-chat-service (修复编译问题)

2. **新的项目结构**
   - 标准化目录结构
   - 统一的配置文件
   - 更新的Docker配置

3. **数据库设计**
   - 新的数据库结构
   - 迁移脚本
   - 测试数据

### **文档完成要求**
1. **技术文档**
   - 更新的API文档
   - 服务架构文档
   - 数据库设计文档

2. **操作文档**
   - 部署指南
   - 开发环境搭建指南
   - 故障排查指南

3. **测试文档**
   - 测试用例文档
   - 性能测试报告
   - 集成测试报告

---

## ⚠️ 关键风险和解决方案

### **技术风险**
1. **EINO框架兼容性问题** 🔍 **需要Context7调研**
   - **风险**: API变化导致无法修复
   - **解决**: 使用Context7研究最新文档，准备降级方案

2. **数据迁移失败**
   - **风险**: 数据丢失或损坏
   - **解决**: 完整备份，分步迁移，验证测试

3. **服务集成问题**
   - **风险**: 服务间通信失败
   - **解决**: 逐步集成，充分测试，错误处理

### **实施风险**
1. **技术难题复杂度过高**
   - **风险**: 某些问题无法解决
   - **解决**: 优先解决阻塞问题，准备替代方案

2. **测试发现重大问题**
   - **风险**: 需要重新开发
   - **解决**: 早期测试，增量验证

---

## ✅ 最终验收标准

### **功能验收**
- [ ] 所有服务能正常启动并通过健康检查
- [ ] 服务间通信功能正常
- [ ] 数据库连接和基本CRUD操作正常
- [ ] 用户认证流程完整可用
- [ ] 代码符合新的编码规范

### **质量验收**
- [ ] 单元测试覆盖率 > 50%
- [ ] 集成测试全部通过
- [ ] 性能测试满足基本要求
- [ ] 文档完整且准确

### **部署验收**
- [ ] Docker环境能够正常启动
- [ ] 环境变量配置正确
- [ ] 日志输出格式统一
- [ ] 监控指标可以正常采集

**完成这个阶段后，项目将拥有稳定的基础架构，可以进行后续功能开发。**