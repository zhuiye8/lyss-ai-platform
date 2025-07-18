# Memory Service 规范文档

## 🎯 服务概述

Memory Service 是 Lyss AI Platform 的**智能记忆管理服务**，负责封装Mem0AI开源版本，为AI对话提供持久化、个性化的记忆能力。本服务实现严格的多租户数据隔离，支持用户级别的记忆开关控制。

## 📋 核心职责

### ✅ 负责的功能
1. **对话记忆存储**: 持久化用户对话历史和个性化信息
2. **上下文检索**: 基于语义搜索提供相关历史上下文  
3. **多租户隔离**: 确保不同租户和用户的记忆数据严格隔离
4. **记忆生命周期管理**: 记忆的创建、更新、删除和过期处理
5. **被动历史查询**: 为用户提供记忆存档的查询接口

### ❌ 不负责的功能
- AI模型的训练和推理（使用外部LLM进行记忆处理）
- 用户认证和权限管理（由Auth Service负责）
- 记忆开关的配置管理（由Tenant Service负责）
- 对话工作流的编排（由EINO Service负责）

## 🚨 配置管理 - 强制分离原则

### ⚠️ 重要安全声明

**为Mem0AI提供支持的LLM和向量模型配置是系统级后台配置，只能通过环境变量设置，严禁与租户服务管理的供应商凭证混淆！**

#### 系统级后台配置（环境变量）
```bash
# 🔒 Mem0AI后台LLM配置 - 系统级专用，不可由用户修改
MEM0_LLM_PROVIDER=openai
MEM0_LLM_MODEL=gpt-4o-mini
MEM0_LLM_API_KEY="后台记忆系统专用OpenAI密钥"

# 🔒 Mem0AI向量模型配置 - 系统级专用
MEM0_EMBEDDING_PROVIDER=openai  
MEM0_EMBEDDING_MODEL=text-embedding-ada-002
MEM0_EMBEDDING_API_KEY="后台嵌入系统专用OpenAI密钥"

# 🔒 向量存储配置 - 系统级专用
MEM0_VECTOR_STORE=qdrant
MEM0_QDRANT_HOST=localhost
MEM0_QDRANT_PORT=6333
MEM0_QDRANT_API_KEY="Qdrant访问密钥"

# 记忆处理配置
MEM0_MEMORY_DECAY_DAYS=90
MEM0_MAX_MEMORIES_PER_USER=10000
```

#### ❌ 严禁混淆的用户供应商配置
Memory Service **绝不得**访问或使用Tenant Service管理的用户供应商凭证（如用户自己的OpenAI密钥）。这两套配置体系必须完全分离：

- **系统级配置**: Memory Service的后台AI能力，由运维团队管理
- **用户级配置**: 用户对话时使用的AI供应商，由Tenant Service管理

### Mem0AI配置实现
```python
from mem0 import Memory
import os

class Mem0Config:
    """Mem0AI系统级配置管理"""
    
    def __init__(self):
        # 🚨 从环境变量获取系统级配置
        self.config = {
            "llm": {
                "provider": os.getenv("MEM0_LLM_PROVIDER", "openai"),
                "config": {
                    "model": os.getenv("MEM0_LLM_MODEL", "gpt-4o-mini"),
                    "api_key": os.getenv("MEM0_LLM_API_KEY"),
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            },
            "embedder": {
                "provider": os.getenv("MEM0_EMBEDDING_PROVIDER", "openai"),
                "config": {
                    "model": os.getenv("MEM0_EMBEDDING_MODEL", "text-embedding-ada-002"),
                    "api_key": os.getenv("MEM0_EMBEDDING_API_KEY"),
                    "embedding_dims": 1536
                }
            },
            "vector_store": {
                "provider": os.getenv("MEM0_VECTOR_STORE", "qdrant"),
                "config": {
                    "host": os.getenv("MEM0_QDRANT_HOST", "localhost"),
                    "port": int(os.getenv("MEM0_QDRANT_PORT", "6333")),
                    "api_key": os.getenv("MEM0_QDRANT_API_KEY")
                }
            }
        }
        
        # 验证必要配置
        if not self.config["llm"]["config"]["api_key"]:
            raise ValueError("MEM0_LLM_API_KEY环境变量未设置")
        if not self.config["embedder"]["config"]["api_key"]:
            raise ValueError("MEM0_EMBEDDING_API_KEY环境变量未设置")
    
    def get_mem0_instance(self) -> Memory:
        """获取配置好的Mem0实例"""
        return Memory.from_config(self.config)

# 全局Mem0实例（启动时初始化）
mem0_instance = None

def get_mem0() -> Memory:
    global mem0_instance
    if mem0_instance is None:
        config = Mem0Config()
        mem0_instance = config.get_mem0_instance()
    return mem0_instance
```

## 🔄 记忆开关机制

### 记忆开关行为定义

Memory Service的行为受用户的`active_memory_enabled`标志影响：

1. **主动记忆功能**（受开关控制）:
   - 自动从对话中提取和存储新记忆
   - 在对话中主动检索相关历史上下文
   
2. **被动查询功能**（不受开关影响）:
   - 用户手动查询历史记忆存档
   - 管理员查看用户记忆数据

### 开关检查实现
```python
async def check_memory_enabled(user_id: str, tenant_id: str) -> bool:
    """检查用户是否启用记忆功能"""
    try:
        # 调用Tenant Service获取用户偏好
        response = await httpx.get(
            f"{TENANT_SERVICE_URL}/internal/users/{user_id}/preferences",
            headers={
                "X-Tenant-ID": tenant_id,
                "X-Request-ID": get_request_id()
            }
        )
        
        if response.status_code == 200:
            preferences = response.json()
            return preferences.get("active_memory_enabled", True)
        else:
            # 默认启用记忆
            return True
    except Exception as e:
        logger.warning(f"Failed to check memory preference: {e}")
        return True  # 默认启用

# 装饰器：主动记忆功能检查
def require_active_memory(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        user_id = kwargs.get("user_id") or args[0]
        tenant_id = get_current_tenant_id()
        
        if not await check_memory_enabled(user_id, tenant_id):
            return {
                "success": false,
                "message": "用户已禁用记忆功能",
                "error_code": "MEMORY_DISABLED"
            }
        
        return await func(*args, **kwargs)
    return wrapper
```

## 🔒 多租户数据隔离实现

### 唯一用户ID构建策略
```python
def build_memory_user_id(tenant_id: str, user_id: str) -> str:
    """构建Mem0AI的唯一用户标识"""
    return f"tenant_{tenant_id}_user_{user_id}"

def parse_memory_user_id(memory_user_id: str) -> tuple[str, str]:
    """解析记忆用户ID获取租户ID和用户ID"""
    parts = memory_user_id.split("_")
    if len(parts) != 4 or parts[0] != "tenant" or parts[2] != "user":
        raise ValueError(f"Invalid memory user ID format: {memory_user_id}")
    return parts[1], parts[3]  # tenant_id, user_id

class MemoryManager:
    def __init__(self):
        self.mem0 = get_mem0()
    
    async def add_memory(self, tenant_id: str, user_id: str, messages: List[dict]):
        """添加记忆（多租户安全）"""
        memory_user_id = build_memory_user_id(tenant_id, user_id)
        
        try:
            result = await self.mem0.add(
                messages=messages,
                user_id=memory_user_id  # 🔒 确保租户隔离
            )
            return result
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise
    
    async def search_memories(self, tenant_id: str, user_id: str, query: str, limit: int = 5):
        """搜索记忆（多租户安全）"""
        memory_user_id = build_memory_user_id(tenant_id, user_id)
        
        try:
            results = await self.mem0.search(
                query=query,
                user_id=memory_user_id,  # 🔒 确保租户隔离
                limit=limit
            )
            return results
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            raise
```

## 📡 对外API接口

### 1. 添加记忆（主动功能）
```http
POST /api/v1/memory/add
Content-Type: application/json
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-Request-ID: {request_id}
```

**请求体:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "我喜欢喝拿铁咖啡"
    },
    {
      "role": "assistant", 
      "content": "好的，我记住了您喜欢拿铁咖啡。"
    }
  ],
  "metadata": {
    "conversation_id": "conv-uuid",
    "timestamp": "2025-07-10T10:30:00Z"
  }
}
```

**成功响应:**
```json
{
  "success": true,
  "data": {
    "memory_id": "mem-uuid",
    "extracted_facts": [
      "用户喜欢拿铁咖啡"
    ],
    "storage_status": "stored"
  },
  "message": "记忆添加成功",
  "request_id": "req-20250710143025-a1b2c3d4"
}
```

**记忆禁用响应:**
```json
{
  "success": false,
  "message": "用户已禁用记忆功能",
  "error_code": "MEMORY_DISABLED",
  "request_id": "req-20250710143025-a1b2c3d4"
}
```

### 2. 搜索记忆（主动功能）
```http
POST /api/v1/memory/search
Content-Type: application/json
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-Request-ID: {request_id}
```

**请求体:**
```json
{
  "query": "用户的饮品偏好",
  "limit": 5,
  "include_metadata": true
}
```

**成功响应:**
```json
{
  "success": true,
  "data": {
    "memories": [
      {
        "id": "mem-uuid",
        "content": "用户喜欢拿铁咖啡",
        "relevance_score": 0.95,
        "created_at": "2025-07-10T10:30:00Z",
        "metadata": {
          "conversation_id": "conv-uuid"
        }
      }
    ],
    "total_found": 1
  },
  "request_id": "req-20250710143025-a1b2c3d4"
}
```

### 3. 获取用户记忆列表（被动功能）
```http
GET /api/v1/memory/list?page=1&size=20&sort=created_at
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-Request-ID: {request_id}
```

**响应:**
```json
{
  "success": true,
  "data": {
    "memories": [
      {
        "id": "mem-uuid",
        "content": "用户喜欢拿铁咖啡",
        "type": "preference",
        "created_at": "2025-07-10T10:30:00Z",
        "last_accessed": "2025-07-10T11:15:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 1,
      "pages": 1
    }
  }
}
```

### 4. 删除记忆（被动功能）
```http
DELETE /api/v1/memory/{memory_id}
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-Request-ID: {request_id}
```

### 5. 清空用户记忆（被动功能）
```http
DELETE /api/v1/memory/clear
X-User-ID: {user_id}
X-Tenant-ID: {tenant_id}
X-Request-ID: {request_id}
```

## 🔧 内部服务API

### 为EINO Service提供的接口

#### 批量记忆检索
```http
POST /internal/memory/batch-search
Content-Type: application/json
X-Request-ID: {request_id}
```

**请求体:**
```json
{
  "searches": [
    {
      "tenant_id": "tenant-uuid",
      "user_id": "user-uuid", 
      "query": "用户偏好",
      "limit": 3
    }
  ]
}
```

#### 异步记忆存储
```http
POST /internal/memory/async-add
Content-Type: application/json
X-Request-ID: {request_id}
```

## 🏗️ 数据模型设计

### 记忆元数据表 (Memory Service专有)
```sql
CREATE TABLE memory_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_user_id VARCHAR(255) NOT NULL, -- tenant_{id}_user_{id}格式
    mem0_memory_id VARCHAR(255) NOT NULL, -- Mem0AI返回的记忆ID
    content_summary TEXT,
    memory_type VARCHAR(50), -- 'preference', 'fact', 'conversation'
    source_conversation_id UUID,
    relevance_score FLOAT,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(mem0_memory_id)
);

-- 租户隔离索引
CREATE INDEX idx_memory_metadata_user ON memory_metadata(memory_user_id);
CREATE INDEX idx_memory_metadata_type ON memory_metadata(memory_type);
CREATE INDEX idx_memory_metadata_accessed ON memory_metadata(last_accessed_at);
```

### 记忆访问日志表
```sql
CREATE TABLE memory_access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_user_id VARCHAR(255) NOT NULL,
    operation VARCHAR(50) NOT NULL, -- 'add', 'search', 'delete'
    memory_id VARCHAR(255),
    query_text TEXT,
    results_count INTEGER,
    processing_time_ms INTEGER,
    request_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 📝 日志规范

### 记忆操作日志
```json
{
  "timestamp": "2025-07-10T10:30:00Z",
  "level": "INFO",
  "service": "memory_service",
  "request_id": "req-20250710143025-a1b2c3d4",
  "operation": "add_memory",
  "tenant_id": "tenant-uuid",
  "user_id": "user-uuid",
  "memory_user_id": "tenant_xxx_user_yyy",
  "memory_enabled": true,
  "facts_extracted": 2,
  "processing_time_ms": 245,
  "success": true,
  "message": "记忆添加成功"
}
```

### 记忆搜索日志
```json
{
  "timestamp": "2025-07-10T10:30:00Z",
  "level": "INFO",
  "service": "memory_service",
  "request_id": "req-20250710143025-a1b2c3d4",
  "operation": "search_memory",
  "tenant_id": "tenant-uuid",
  "user_id": "user-uuid",
  "query": "用户饮品偏好",
  "results_found": 3,
  "relevance_threshold": 0.7,
  "processing_time_ms": 156,
  "message": "记忆搜索完成"
}
```

### 记忆开关检查日志
```json
{
  "timestamp": "2025-07-10T10:30:00Z",
  "level": "DEBUG",
  "service": "memory_service", 
  "request_id": "req-20250710143025-a1b2c3d4",
  "operation": "check_memory_enabled",
  "tenant_id": "tenant-uuid",
  "user_id": "user-uuid",
  "memory_enabled": false,
  "message": "用户已禁用记忆功能，跳过记忆操作"
}
```

## 🔧 核心技术实现

### 依赖组件
```python
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
mem0ai==0.1.8
httpx==0.25.0
pydantic==2.5.0
asyncio==3.11.0
qdrant-client==1.7.0
```

### 记忆管理核心类
```python
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from mem0 import Memory

class MemoryService:
    def __init__(self):
        self.mem0 = get_mem0()
        self.cache = {}
        self.cache_ttl = timedelta(minutes=5)
    
    @require_active_memory
    async def add_conversation_memory(
        self, 
        user_id: str, 
        tenant_id: str, 
        messages: List[Dict],
        metadata: Optional[Dict] = None
    ) -> Dict:
        """添加对话记忆"""
        memory_user_id = build_memory_user_id(tenant_id, user_id)
        
        # 记录操作开始
        start_time = datetime.now()
        
        try:
            # 调用Mem0AI添加记忆
            result = await self.mem0.add(
                messages=messages,
                user_id=memory_user_id
            )
            
            # 记录元数据
            await self._save_memory_metadata(
                memory_user_id=memory_user_id,
                mem0_memory_id=result.get("id"),
                memory_type="conversation",
                source_conversation_id=metadata.get("conversation_id") if metadata else None
            )
            
            # 记录成功日志
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                "Memory added successfully",
                extra={
                    "operation": "add_memory",
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "processing_time_ms": int(processing_time),
                    "facts_extracted": len(result.get("memories", []))
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise
    
    @require_active_memory
    async def search_relevant_memories(
        self,
        user_id: str,
        tenant_id: str, 
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """搜索相关记忆"""
        memory_user_id = build_memory_user_id(tenant_id, user_id)
        
        # 检查缓存
        cache_key = f"{memory_user_id}:{hash(query)}"
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if datetime.now() - cache_entry["timestamp"] < self.cache_ttl:
                return cache_entry["results"]
        
        try:
            # 调用Mem0AI搜索
            results = await self.mem0.search(
                query=query,
                user_id=memory_user_id,
                limit=limit
            )
            
            # 更新访问统计
            for result in results:
                await self._update_memory_access(result.get("id"))
            
            # 缓存结果
            self.cache[cache_key] = {
                "results": results,
                "timestamp": datetime.now()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def get_user_memory_stats(self, user_id: str, tenant_id: str) -> Dict:
        """获取用户记忆统计（被动功能，不受开关影响）"""
        memory_user_id = build_memory_user_id(tenant_id, user_id)
        
        try:
            memories = await self.mem0.get_all(user_id=memory_user_id)
            
            return {
                "total_memories": len(memories),
                "memory_types": self._analyze_memory_types(memories),
                "last_updated": max([m.get("created_at") for m in memories]) if memories else None
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"total_memories": 0}
```

## 🔒 安全和性能

### 环境变量配置
```bash
# 服务配置
PORT=8004
LOG_LEVEL=INFO
REQUEST_TIMEOUT=30s

# Mem0AI后台LLM配置（🚨 系统级专用）
MEM0_LLM_PROVIDER=openai
MEM0_LLM_MODEL=gpt-4o-mini
MEM0_LLM_API_KEY="后台记忆系统专用密钥"

# Mem0AI向量配置（🚨 系统级专用）
MEM0_EMBEDDING_PROVIDER=openai
MEM0_EMBEDDING_MODEL=text-embedding-ada-002
MEM0_EMBEDDING_API_KEY="后台嵌入系统专用密钥"

# 向量存储配置
MEM0_VECTOR_STORE=qdrant
MEM0_QDRANT_HOST=localhost
MEM0_QDRANT_PORT=6333

# 记忆管理配置
MEMORY_CACHE_TTL=300
MAX_MEMORIES_PER_USER=10000
MEMORY_RETENTION_DAYS=90

# 依赖服务
TENANT_SERVICE_URL=http://localhost:8002
```

### 性能优化
```python
# 记忆搜索结果缓存
class MemorySearchCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    async def get(self, key: str) -> Optional[List[Dict]]:
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["results"]
            else:
                del self.cache[key]
        return None
    
    async def set(self, key: str, results: List[Dict]):
        self.cache[key] = {
            "results": results,
            "timestamp": time.time()
        }

# 批量处理优化
async def batch_add_memories(requests: List[MemoryAddRequest]) -> List[Dict]:
    """批量添加记忆以提高性能"""
    tasks = []
    for req in requests:
        task = add_conversation_memory(
            req.user_id, 
            req.tenant_id,
            req.messages,
            req.metadata
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

## 🚀 部署和运行

### 启动命令
```bash
cd services/memory
uvicorn main:app --host 0.0.0.0 --port 8004 --reload
```

### Docker配置
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8004
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
```

### 健康检查
```http
GET /health
```

**响应:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-10T10:30:00Z",
  "version": "1.0.0",
  "mem0_status": "connected",
  "vector_store_status": "healthy",
  "dependencies": {
    "tenant_service": "healthy"
  },
  "metrics": {
    "total_memories_stored": 15472,
    "active_users": 234
  }
}
```

## ⚠️ 关键约束和限制

### 强制约束
1. **配置分离**: Mem0AI后台配置与用户供应商配置严格分离
2. **多租户隔离**: 所有记忆操作必须使用构建的memory_user_id
3. **记忆开关**: 主动记忆功能必须检查用户偏好设置
4. **被动功能**: 历史查询功能不受记忆开关影响

### 性能要求
- **记忆添加**: P95 < 500ms
- **记忆搜索**: P95 < 300ms
- **并发处理**: 支持1000并发记忆操作
- **数据一致性**: 记忆数据必须实时同步

### 监控指标
- 记忆添加和搜索成功率
- 记忆开关使用统计
- 向量搜索性能和准确性
- 多租户数据隔离合规性
- Mem0AI后台服务健康状态

---

**🧠 重要提醒**: Memory Service处理用户的个性化数据和隐私信息，必须严格遵循多租户隔离和记忆开关机制。任何修改都必须确保数据安全和用户隐私保护。