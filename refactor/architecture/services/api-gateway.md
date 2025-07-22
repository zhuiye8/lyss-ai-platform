# lyss-api-gateway (统一入口网关)

## 📋 服务概述

API网关服务作为整个系统的统一入口，负责路由分发、认证验证、安全防护等核心功能。

---

## 🎯 服务职责

```
技术栈: FastAPI + Redis
端口: 8000
职责：
- 统一入口和路由分发
- JWT认证验证
- 请求限流和安全防护
- 跨服务请求追踪
- 错误处理和响应标准化
```

---

## 🔧 技术实现

### **路由配置**
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.middleware import AuthMiddleware, RateLimitMiddleware
from app.routers import auth, users, providers, chat, memory

app = FastAPI(
    title="Lyss API Gateway",
    description="统一API网关服务",
    version="1.0.0"
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# 路由配置
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(users.router, prefix="/api/v1/users", tags=["用户管理"])
app.include_router(providers.router, prefix="/api/v1/providers", tags=["供应商管理"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["AI对话"])
app.include_router(memory.router, prefix="/api/v1/memory", tags=["智能记忆"])
```

### **服务代理**
```python
import httpx
from fastapi import Request, Response

class ServiceProxy:
    def __init__(self):
        self.services = {
            "auth": "http://lyss-auth-service:8001",
            "user": "http://lyss-user-service:8002", 
            "provider": "http://lyss-provider-service:8003",
            "chat": "http://lyss-chat-service:8004",
            "memory": "http://lyss-memory-service:8005"
        }
    
    async def forward_request(self, service: str, path: str, request: Request) -> Response:
        """转发请求到对应的微服务"""
        base_url = self.services.get(service)
        if not base_url:
            raise HTTPException(status_code=404, detail="服务不存在")
        
        async with httpx.AsyncClient() as client:
            # 保持原始请求的方法、头部和数据
            response = await client.request(
                method=request.method,
                url=f"{base_url}{path}",
                headers=dict(request.headers),
                content=await request.body(),
                timeout=30.0
            )
        
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers)
        )
```

### **认证中间件**
```python
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.jwt import verify_token

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 跳过认证的路径
        skip_paths = ["/docs", "/openapi.json", "/health", "/api/v1/auth/login"]
        
        if request.url.path in skip_paths:
            return await call_next(request)
        
        # 验证JWT令牌
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证令牌"
            )
        
        try:
            payload = verify_token(token.replace("Bearer ", ""))
            request.state.user = payload
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌"
            )
        
        return await call_next(request)
```

---

## 🔧 配置管理

### **环境变量**
```bash
# 服务配置
API_GATEWAY_PORT=8000
API_GATEWAY_DEBUG=false

# 后端服务地址
AUTH_SERVICE_URL=http://lyss-auth-service:8001
USER_SERVICE_URL=http://lyss-user-service:8002
PROVIDER_SERVICE_URL=http://lyss-provider-service:8003
CHAT_SERVICE_URL=http://lyss-chat-service:8004
MEMORY_SERVICE_URL=http://lyss-memory-service:8005

# Redis配置
API_GATEWAY_REDIS_URL=redis://lyss-redis:6379/0
API_GATEWAY_REDIS_PASSWORD=your_redis_password

# JWT配置
API_GATEWAY_JWT_SECRET=your_jwt_secret_key
API_GATEWAY_JWT_ALGORITHM=HS256
API_GATEWAY_JWT_EXPIRE_HOURS=24

# 限流配置
API_GATEWAY_RATE_LIMIT_REQUESTS=1000
API_GATEWAY_RATE_LIMIT_WINDOW=3600
```

### **Docker配置**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🔍 监控和日志

### **健康检查**
```python
@app.get("/health")
async def health_check():
    """API网关健康检查"""
    services_status = {}
    
    for service_name, service_url in services.items():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_url}/health", timeout=5.0)
                services_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds()
                }
        except Exception as e:
            services_status[service_name] = {
                "status": "error",
                "error": str(e)
            }
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_status
    }
```

### **请求日志**
```python
import logging
from app.core.logger import get_logger

logger = get_logger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # 记录请求信息
    logger.info(f"请求开始: {request.method} {request.url}")
    
    response = await call_next(request)
    
    # 记录响应信息
    process_time = time.time() - start_time
    logger.info(f"请求完成: {response.status_code} - {process_time:.4f}s")
    
    return response
```