# Lyss AI Platform 开发指南

## 🛠️ 开发环境设置

### 系统要求

- **操作系统**: Linux/macOS/Windows (推荐 Linux 或 macOS)
- **Node.js**: >= 18.0.0
- **Python**: >= 3.11
- **Go**: >= 1.21
- **Docker**: >= 20.10
- **Docker Compose**: >= 2.0
- **Git**: >= 2.30

### IDE推荐配置

#### VS Code
推荐安装以下扩展：
- Python
- Go
- TypeScript and JavaScript
- Docker
- Kubernetes
- GitLens
- Thunder Client (API测试)

#### PyCharm/GoLand
- 配置Python解释器为项目虚拟环境
- 启用代码格式化工具
- 配置Git集成

## 🏗️ 项目架构详解

### 微服务架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│         React + TypeScript + Ant Design                    │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP/WebSocket
┌─────────────────────┴───────────────────────────────────────┐
│                     API网关层                               │
│            FastAPI + 认证 + 限流 + 路由                    │
└──┬─────────────┬─────────────┬─────────────┬────────────────┘
   │             │             │             │
   │ gRPC/HTTP   │ HTTP        │ HTTP        │ HTTP
   │             │             │             │
┌──▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────────┐
│ EINO   │ │ 记忆服务   │ │ 租户服务   │ │ 其他微服务     │
│ 服务   │ │(Mem0AI)   │ │(FastAPI)  │ │               │
│(Go)    │ │(Python)   │ │(Python)   │ │               │
└────────┘ └───────────┘ └───────────┘ └───────────────┘
     │           │             │             │
     └───────────┼─────────────┼─────────────┘
                 │             │
        ┌────────▼─────┐ ┌─────▼─────┐
        │ PostgreSQL   │ │   Redis   │
        │   数据库     │ │   缓存    │
        └──────────────┘ └───────────┘
```

### 数据流架构

1. **前端请求** → API网关
2. **API网关** → 认证/授权检查
3. **API网关** → 路由到相应微服务
4. **微服务** → 处理业务逻辑
5. **微服务** → 数据库/缓存操作
6. **响应** → 原路返回到前端

## 📦 服务详解

### API网关 (FastAPI)

**职责**:
- 统一入口点
- 认证和授权
- 请求路由
- 速率限制
- 日志记录
- 监控指标收集

**核心模块**:
```python
backend/api-gateway/
├── main.py              # 应用入口
├── routers/             # 路由模块
│   ├── auth.py         # 认证路由
│   ├── conversations.py # 对话路由
│   ├── admin.py        # 管理路由
│   └── health.py       # 健康检查
├── middleware/          # 中间件
│   ├── auth.py         # 认证中间件
│   ├── logging.py      # 日志中间件
│   └── rate_limit.py   # 限流中间件
└── dependencies.py      # 依赖注入
```

### EINO服务 (Go)

**职责**:
- AI工作流编排
- 模型调用管理
- 流式响应处理
- 工作流状态管理

**核心模块**:
```go
eino-service/
├── cmd/
│   └── main.go         # 服务入口
├── internal/
│   ├── handlers/       # HTTP处理器
│   ├── services/       # 业务逻辑
│   ├── models/         # 数据模型
│   └── config/         # 配置管理
└── pkg/
    ├── workflows/      # 工作流定义
    └── adapters/       # AI供应商适配器
```

### 记忆服务 (Python + Mem0AI)

**职责**:
- 用户记忆存储
- 语义搜索
- 记忆管理
- 个性化推荐

**核心模块**:
```python
memory-service/
├── app/
│   ├── main.py         # 服务入口
│   ├── services/       # 业务逻辑
│   ├── models/         # 数据模型
│   ├── api/           # API路由
│   └── config.py      # 配置管理
└── tests/             # 测试代码
```

## 🔄 开发工作流

### 1. 功能开发流程

```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 开发和测试
# 编写代码...
# 运行测试...

# 3. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 4. 推送分支
git push origin feature/new-feature

# 5. 创建Pull Request
```

### 2. 本地开发环境

```bash
# 启动基础服务
docker-compose -f docker-compose.dev.yml up -d postgres redis

# 启动API网关 (终端1)
cd backend
source venv/bin/activate
uvicorn api-gateway.main:app --reload --port 8000

# 启动EINO服务 (终端2)
cd eino-service
go run cmd/main.go

# 启动记忆服务 (终端3)
cd memory-service
source venv/bin/activate
uvicorn app.main:app --reload --port 8001

# 启动前端 (终端4)
cd frontend
npm run dev
```

### 3. 热重载开发

所有服务都支持热重载：
- **Python服务**: 使用 `--reload` 参数
- **Go服务**: 使用 `air` 工具
- **前端**: Vite 自动热重载

## 🧪 测试策略

### 测试金字塔

```
    E2E Tests (5%)
  ┌─────────────────┐
 │   UI/API Tests   │
├─────────────────────┤
│ Integration Tests   │
│      (20%)          │
├─────────────────────┤
│  Unit Tests (75%)   │
└─────────────────────┘
```

### 单元测试

#### Python测试
```bash
# 运行后端测试
cd backend
pytest tests/ -v --cov=.

# 运行记忆服务测试
cd memory-service
pytest tests/ -v --cov=app
```

#### Go测试
```bash
# 运行EINO服务测试
cd eino-service
go test ./... -v -cover
```

#### 前端测试
```bash
# 运行前端测试
cd frontend
npm test

# 运行覆盖率测试
npm run test:coverage
```

### 集成测试

```bash
# 启动测试环境
docker-compose -f docker-compose.test.yml up -d

# 运行集成测试
python tests/integration/test_api_integration.py
```

### E2E测试

```bash
# 使用Playwright进行E2E测试
cd frontend
npm run test:e2e
```

## 📝 代码规范

### Python代码规范

#### 格式化工具
```bash
# 安装工具
pip install black isort flake8 mypy

# 格式化代码
black .
isort .

# 检查代码质量
flake8 .
mypy .
```

#### 命名规范
```python
# 变量和函数：snake_case
user_name = "张三"
def get_user_info():
    pass

# 类名：PascalCase
class UserService:
    pass

# 常量：UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# 私有方法：_开头
def _internal_method():
    pass
```

### TypeScript代码规范

#### ESLint配置
```bash
# 检查代码
npm run lint

# 自动修复
npm run lint:fix
```

#### 命名规范
```typescript
// 变量和函数：camelCase
const userName = "张三";
function getUserInfo() {}

// 类型和接口：PascalCase
interface User {
  id: string;
  name: string;
}

// 常量：UPPER_SNAKE_CASE
const MAX_RETRY_COUNT = 3;

// 组件：PascalCase
function UserProfile() {}
```

### Go代码规范

#### 格式化工具
```bash
# 格式化代码
go fmt ./...

# 检查代码
go vet ./...
golint ./...
```

#### 命名规范
```go
// 包名：小写
package handlers

// 公共函数/变量：大写开头
func GetUserInfo() {}
var GlobalConfig Config

// 私有函数/变量：小写开头
func getUserInfo() {}
var localConfig config

// 常量：大写或camelCase
const MaxRetryCount = 3
const defaultTimeout = 30 * time.Second
```

## 🔧 调试技巧

### 后端调试

#### Python调试
```python
# 使用pdb调试
import pdb; pdb.set_trace()

# 使用日志调试
import logging
logging.debug("调试信息: %s", variable)

# 使用IDE断点
# 在VS Code中设置断点并启动调试模式
```

#### Go调试
```go
// 使用fmt打印调试
fmt.Printf("调试信息: %+v\n", variable)

// 使用delve调试器
// dlv debug cmd/main.go

// 使用IDE调试
// 在GoLand中设置断点并启动调试
```

### 前端调试

```typescript
// 浏览器开发者工具
console.log("调试信息:", variable);
console.error("错误信息:", error);

// React DevTools
// 安装浏览器扩展进行组件调试

// VS Code调试
// 配置launch.json进行断点调试
```

### 网络调试

```bash
# 查看API请求
curl -X GET "http://localhost:8000/api/v1/health" -H "Accept: application/json"

# 使用httpie
http GET localhost:8000/api/v1/health

# 查看容器日志
docker-compose logs -f api-gateway

# 查看数据库连接
docker-compose exec postgres psql -U lyss_user -d lyss_platform
```

## 📊 性能优化

### 后端性能优化

#### 数据库优化
```sql
-- 添加索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_conversations_user ON conversations(user_id);

-- 查询优化
EXPLAIN ANALYZE SELECT * FROM users WHERE email = 'user@example.com';
```

#### API优化
```python
# 使用异步
async def get_users():
    async with get_db() as db:
        result = await db.execute("SELECT * FROM users")
        return result.fetchall()

# 使用缓存
@lru_cache(maxsize=128)
def expensive_function(param):
    # 耗时操作
    pass
```

### 前端性能优化

#### 代码分割
```typescript
// 路由级别代码分割
const LazyComponent = lazy(() => import('./LazyComponent'));

// 组件级别代码分割
const [data, setData] = useState(null);
useEffect(() => {
  import('./heavyModule').then(module => {
    setData(module.processData());
  });
}, []);
```

#### 缓存策略
```typescript
// React Query缓存
const { data, isLoading } = useQuery(
  ['users', userId],
  () => fetchUser(userId),
  {
    staleTime: 5 * 60 * 1000, // 5分钟
    cacheTime: 10 * 60 * 1000, // 10分钟
  }
);
```

## 🛡️ 安全最佳实践

### 代码安全

#### 输入验证
```python
# 使用Pydantic进行数据验证
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=50)
    
    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('密码必须包含大写字母')
        return v
```

#### SQL注入防护
```python
# 使用参数化查询
result = await db.execute(
    "SELECT * FROM users WHERE email = :email",
    {"email": email}
)

# 避免字符串拼接
# 错误示例：f"SELECT * FROM users WHERE email = '{email}'"
```

#### XSS防护
```typescript
// 使用dangerouslySetInnerHTML时要小心
const sanitizeHtml = (html: string) => {
  return DOMPurify.sanitize(html);
};

// 避免直接渲染用户输入
<div dangerouslySetInnerHTML={{ __html: sanitizeHtml(userContent) }} />
```

### 认证授权

#### JWT最佳实践
```python
# 设置合理的过期时间
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# 使用强密钥
SECRET_KEY = secrets.token_urlsafe(32)

# 验证token
def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

## 📈 监控和日志

### 应用监控

#### 添加指标
```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('request_duration_seconds', 'Request duration')

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response
```

#### 结构化日志
```python
import structlog

logger = structlog.get_logger()

def process_user(user_id: str):
    logger.info("开始处理用户", user_id=user_id, action="process_start")
    try:
        # 处理逻辑
        logger.info("用户处理完成", user_id=user_id, action="process_complete")
    except Exception as e:
        logger.error("用户处理失败", user_id=user_id, error=str(e), action="process_error")
```

### 错误追踪

#### 分布式追踪
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def api_endpoint():
    with tracer.start_as_current_span("api_endpoint") as span:
        span.set_attribute("user_id", user_id)
        # API逻辑
```

## 🚀 部署准备

### 环境配置检查

```bash
# 检查配置文件
./scripts/check-config.sh

# 验证密钥强度
python scripts/validate-secrets.py

# 数据库迁移
alembic upgrade head

# 预热缓存
python scripts/warm-cache.py
```

### 健康检查

```python
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "external_apis": await check_external_apis()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

## 💡 开发技巧

### 快速启动脚本

```bash
# 创建开发快捷脚本
cat > dev.sh << 'EOF'
#!/bin/bash
# 快速启动开发环境

echo "🚀 启动Lyss开发环境..."

# 启动基础服务
docker-compose -f docker-compose.dev.yml up -d postgres redis

# 启动所有开发服务
concurrently \
  "cd backend && uvicorn api-gateway.main:app --reload --port 8000" \
  "cd eino-service && air" \
  "cd memory-service && uvicorn app.main:app --reload --port 8001" \
  "cd frontend && npm run dev"
EOF

chmod +x dev.sh
```

### 调试配置

#### VS Code配置
```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/backend/api-gateway/main.py",
      "console": "integratedTerminal",
      "env": {
        "ENVIRONMENT": "development"
      }
    },
    {
      "name": "Debug Go",
      "type": "go",
      "request": "launch",
      "mode": "debug",
      "program": "${workspaceFolder}/eino-service/cmd/main.go"
    }
  ]
}
```

### 有用的命令

```bash
# 查看所有容器状态
docker-compose ps

# 重建并启动服务
docker-compose up --build -d

# 查看实时日志
docker-compose logs -f

# 进入容器调试
docker-compose exec api-gateway bash

# 重置开发数据库
docker-compose down -v && docker-compose up -d postgres

# 生成迁移文件
cd backend && alembic revision --autogenerate -m "add new table"

# 格式化所有代码
black . && isort . && npm run lint:fix
```

## 📚 学习资源

### 官方文档
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [EINO文档](https://github.com/cloudwego/eino)
- [Mem0AI文档](https://github.com/mem0ai/mem0)
- [React文档](https://react.dev/)
- [Ant Design文档](https://ant.design/)

### 推荐阅读
- 《Clean Architecture》
- 《Microservices Patterns》
- 《Building Microservices》
- 《Python Tricks》
- 《Effective Go》

## 🆘 常见问题

### 服务启动失败
1. 检查端口是否被占用
2. 确认环境变量配置正确
3. 检查依赖服务是否正常运行
4. 查看详细错误日志

### 数据库连接问题
1. 确认PostgreSQL服务状态
2. 检查连接字符串配置
3. 验证用户权限
4. 查看防火墙设置

### 前端编译错误
1. 清除node_modules重新安装
2. 检查Node.js版本
3. 查看TypeScript类型错误
4. 确认依赖版本兼容性

---

**更多详细信息请参考项目其他文档或联系开发团队。**