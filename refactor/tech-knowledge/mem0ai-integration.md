# Mem0AI智能记忆集成技术文档

## 📋 框架概述

**Mem0AI** 是专为AI应用设计的智能记忆框架，提供对话记忆存储、语义检索和个性化上下文生成功能。支持多种向量数据库后端，与Qdrant集成提供高性能语义搜索。

---

## 🎯 核心能力

### **智能记忆管理**
- **对话记忆**: 自动提取和存储对话关键信息
- **语义检索**: 基于向量相似度的智能检索
- **用户画像**: 基于历史记忆生成个性化用户档案
- **记忆关联**: 自动发现和建立记忆间的关联关系

### **多后端支持**
- **Qdrant**: 高性能向量数据库 (推荐)
- **Chroma**: 轻量级向量存储
- **Pinecone**: 云端向量数据库
- **Weaviate**: 知识图谱向量数据库

---

## 🔧 最新集成方案

### **1. 基础依赖和配置**
```python
# 基于Context7调研的Mem0AI最佳实践
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from mem0 import Memory, MemoryClient
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

# Mem0AI配置和初始化
def create_memory_client() -> Memory:
    """创建配置优化的Mem0AI客户端"""
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "lyss_memories",
                "host": os.getenv("QDRANT_HOST", "localhost"),
                "port": int(os.getenv("QDRANT_PORT", 6333)),
                "embedding_model_dims": 1536,  # OpenAI text-embedding-3-small
                "metric": "cosine"
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o-mini",
                "temperature": 0.1,
                "max_tokens": 2000,
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-small"
            }
        }
    }
    
    return Memory.from_config(config)
```

### **2. 数据模型定义**
```python
# 请求和响应模型
class MemoryAddRequest(BaseModel):
    messages: List[Dict[str, str]]  # 对话消息列表
    user_id: str
    agent_id: Optional[str] = None
    metadata: Optional[Dict] = None

class MemorySearchRequest(BaseModel):
    query: str
    user_id: str
    limit: int = 5
    filters: Optional[Dict] = None

class MemoryResponse(BaseModel):
    memory_id: str
    content: str
    relevance_score: float
    created_at: str
    metadata: Dict

class UserProfileResponse(BaseModel):
    user_id: str
    total_memories: int
    profile_summary: str
    generated_at: str
    key_interests: List[str]
    interaction_patterns: Dict
```

### **3. 核心业务逻辑**
```python
class MemoryService:
    def __init__(self):
        self.memory_client = create_memory_client()
    
    async def add_conversation_memory(self, request: MemoryAddRequest) -> Dict:
        """添加对话记忆"""
        try:
            # 使用Mem0AI处理多轮对话
            result = self.memory_client.add(
                messages=request.messages,
                user_id=request.user_id,
                agent_id=request.agent_id,
                metadata={
                    "source": "conversation",
                    "timestamp": datetime.utcnow().isoformat(),
                    **request.metadata or {}
                }
            )
            
            return {
                "success": True,
                "memory_id": result.get("id"),
                "message": "记忆添加成功"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"记忆添加失败: {str(e)}")
    
    async def search_memories(self, request: MemorySearchRequest) -> List[MemoryResponse]:
        """智能记忆检索"""
        try:
            # 使用Mem0AI进行语义搜索
            results = self.memory_client.search(
                query=request.query,
                user_id=request.user_id,
                limit=request.limit
            )
            
            memories = []
            for result in results:
                memories.append(MemoryResponse(
                    memory_id=result["id"],
                    content=result["memory"],
                    relevance_score=result.get("score", 0.0),
                    created_at=result.get("created_at", ""),
                    metadata=result.get("metadata", {})
                ))
            
            return memories
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"记忆检索失败: {str(e)}")
    
    async def get_user_context(self, user_id: str, recent_message: str) -> str:
        """获取用户个性化上下文"""
        try:
            # 检索相关记忆
            relevant_memories = await self.search_memories(
                MemorySearchRequest(
                    query=recent_message,
                    user_id=user_id,
                    limit=3
                )
            )
            
            # 构建上下文
            context_parts = []
            for memory in relevant_memories:
                context_parts.append(f"- {memory.content}")
            
            if context_parts:
                return f"用户相关记忆:\n" + "\n".join(context_parts)
            else:
                return "暂无相关历史记忆"
                
        except Exception as e:
            return "记忆检索失败"
```

### **4. 高级记忆管理功能**
```python
class AdvancedMemoryService(MemoryService):
    
    async def create_user_profile(self, user_id: str) -> UserProfileResponse:
        """生成用户画像"""
        try:
            # 获取用户所有记忆
            all_memories = self.memory_client.get_all(user_id=user_id)
            
            if not all_memories.get("results"):
                return UserProfileResponse(
                    user_id=user_id,
                    total_memories=0,
                    profile_summary="新用户，暂无足够数据生成画像",
                    generated_at=datetime.utcnow().isoformat(),
                    key_interests=[],
                    interaction_patterns={}
                )
            
            # 使用Mem0AI分析用户偏好
            profile_query = "总结这个用户的兴趣爱好、工作情况和个人偏好"
            profile_memories = self.memory_client.search(
                query=profile_query,
                user_id=user_id,
                limit=10
            )
            
            # 分析兴趣关键词
            key_interests = self._extract_interests(profile_memories)
            
            # 分析互动模式
            interaction_patterns = self._analyze_patterns(all_memories["results"])
            
            # 构建用户画像
            profile_parts = []
            for memory in profile_memories[:5]:
                profile_parts.append(memory["memory"])
            
            return UserProfileResponse(
                user_id=user_id,
                total_memories=len(all_memories["results"]),
                profile_summary="\n".join(profile_parts),
                generated_at=datetime.utcnow().isoformat(),
                key_interests=key_interests,
                interaction_patterns=interaction_patterns
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"用户画像生成失败: {str(e)}")
    
    def _extract_interests(self, memories: List[Dict]) -> List[str]:
        """提取用户兴趣关键词"""
        interests = []
        # 使用简单的关键词提取逻辑
        interest_keywords = ["喜欢", "感兴趣", "爱好", "专业", "工作"]
        
        for memory in memories:
            content = memory.get("memory", "")
            for keyword in interest_keywords:
                if keyword in content:
                    # 提取关键词附近的内容作为兴趣点
                    interests.append(content[:50] + "...")
                    break
        
        return list(set(interests))[:5]  # 去重并限制数量
    
    def _analyze_patterns(self, memories: List[Dict]) -> Dict:
        """分析用户互动模式"""
        patterns = {
            "total_conversations": len(memories),
            "average_length": 0,
            "most_active_hours": [],
            "conversation_topics": []
        }
        
        if memories:
            total_length = sum(len(m.get("memory", "")) for m in memories)
            patterns["average_length"] = total_length // len(memories)
        
        return patterns
    
    async def cleanup_old_memories(self, user_id: str, days_old: int = 90) -> Dict:
        """清理过期记忆"""
        try:
            # 计算截止日期
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # 获取所有记忆
            all_memories = self.memory_client.get_all(user_id=user_id)
            old_memories = []
            
            for memory in all_memories.get("results", []):
                created_at = datetime.fromisoformat(
                    memory.get("created_at", "").replace("Z", "+00:00")
                )
                if created_at < cutoff_date:
                    old_memories.append(memory["id"])
            
            # 删除过期记忆
            deleted_count = 0
            for memory_id in old_memories:
                try:
                    self.memory_client.delete(memory_id=memory_id)
                    deleted_count += 1
                except:
                    continue
            
            return {
                "deleted_count": deleted_count,
                "total_old_memories": len(old_memories),
                "cleanup_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"记忆清理失败: {str(e)}")
```

### **5. FastAPI路由集成**
```python
# FastAPI应用初始化
app = FastAPI(title="Lyss Memory Service", version="1.0.0")
memory_service = AdvancedMemoryService()

@app.post("/api/v1/memories", response_model=Dict)
async def add_memory(request: MemoryAddRequest):
    """添加记忆接口"""
    return await memory_service.add_conversation_memory(request)

@app.get("/api/v1/memories/search", response_model=List[MemoryResponse])
async def search_memories(
    query: str,
    user_id: str,
    limit: int = 5
):
    """搜索记忆接口"""
    request = MemorySearchRequest(query=query, user_id=user_id, limit=limit)
    return await memory_service.search_memories(request)

@app.get("/api/v1/memories/context/{user_id}")
async def get_context(user_id: str, message: str):
    """获取用户上下文接口"""
    context = await memory_service.get_user_context(user_id, message)
    return {"context": context}

@app.get("/api/v1/users/{user_id}/profile", response_model=UserProfileResponse)
async def get_user_profile(user_id: str):
    """获取用户画像接口"""
    return await memory_service.create_user_profile(user_id)

@app.delete("/api/v1/users/{user_id}/memories/cleanup")
async def cleanup_memories(user_id: str, days_old: int = 90):
    """清理过期记忆接口"""
    return await memory_service.cleanup_old_memories(user_id, days_old)

@app.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        # 测试Mem0AI连接
        test_result = memory_service.memory_client.search(
            query="test", user_id="health_check", limit=1
        )
        return {"status": "healthy", "service": "memory"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务不可用: {str(e)}")
```

---

## 🏗️ Qdrant集成配置

### **Qdrant Docker配置**
```yaml
# docker-compose.yml中的Qdrant配置
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: lyss-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./data/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334
    restart: unless-stopped
```

### **Qdrant初始化脚本**
```python
import qdrant_client
from qdrant_client.http import models

def setup_qdrant_collection():
    """初始化Qdrant集合"""
    client = qdrant_client.QdrantClient(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 6333))
    )
    
    collection_name = "lyss_memories"
    
    # 检查集合是否存在
    try:
        client.get_collection(collection_name)
        print(f"集合 {collection_name} 已存在")
        return
    except:
        pass
    
    # 创建集合
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=1536,  # OpenAI text-embedding-3-small维度
            distance=models.Distance.COSINE
        ),
        optimizers_config=models.OptimizersConfig(
            default_segment_number=2,
            max_segment_size_kb=100000,
            memmap_threshold_kb=200000,
        ),
        hnsw_config=models.HnswConfig(
            m=16,
            ef_construct=100,
            full_scan_threshold=10000,
        )
    )
    
    print(f"成功创建集合 {collection_name}")

# 服务启动时调用
if __name__ == "__main__":
    setup_qdrant_collection()
```

---

## 📊 数据库设计

### **记忆元数据表**
```sql
-- 记忆元数据表 (PostgreSQL)
CREATE TABLE memory_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    memory_id VARCHAR(255) NOT NULL, -- Mem0AI记忆ID
    conversation_id UUID,
    source_type VARCHAR(50) NOT NULL, -- 'conversation', 'document', 'manual'
    category VARCHAR(100),
    tags TEXT[],
    embedding_model VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_memory_user_tenant (user_id, tenant_id),
    INDEX idx_memory_conversation (conversation_id),
    UNIQUE INDEX idx_memory_id (memory_id)
);

-- 用户画像缓存表
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    profile_data JSONB NOT NULL,
    interests TEXT[],
    interaction_patterns JSONB,
    total_memories INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_profiles_tenant (tenant_id),
    INDEX idx_profiles_updated (last_updated)
);

-- 记忆统计表
CREATE TABLE memory_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    date DATE NOT NULL,
    memories_added INTEGER DEFAULT 0,
    searches_performed INTEGER DEFAULT 0,
    avg_relevance_score DECIMAL(3,2),
    
    UNIQUE INDEX idx_stats_user_date (user_id, date),
    INDEX idx_stats_tenant_date (tenant_id, date)
);
```

---

## 🔧 配置管理

### **环境变量**
```bash
# 服务配置
MEMORY_SERVICE_PORT=8005
MEMORY_SERVICE_DEBUG=false
MEMORY_SERVICE_WORKERS=4

# 数据库配置
MEMORY_SERVICE_DATABASE_URL=postgresql://lyss:password@lyss-postgres:5432/lyss_memory_db

# Qdrant配置
MEMORY_SERVICE_QDRANT_HOST=lyss-qdrant
MEMORY_SERVICE_QDRANT_PORT=6333
MEMORY_SERVICE_QDRANT_COLLECTION=lyss_memories
MEMORY_SERVICE_QDRANT_TIMEOUT=30

# Mem0AI配置
MEMORY_SERVICE_OPENAI_API_KEY=your_openai_api_key
MEMORY_SERVICE_EMBEDDING_MODEL=text-embedding-3-small
MEMORY_SERVICE_LLM_MODEL=gpt-4o-mini

# 记忆管理配置
MEMORY_SERVICE_MAX_MEMORIES_PER_USER=10000
MEMORY_SERVICE_MEMORY_TTL_DAYS=365
MEMORY_SERVICE_CLEANUP_INTERVAL_HOURS=24
MEMORY_SERVICE_BATCH_SIZE=100

# 性能配置
MEMORY_SERVICE_SEARCH_TIMEOUT=5
MEMORY_SERVICE_EMBEDDING_BATCH_SIZE=32
MEMORY_SERVICE_CACHE_TTL=3600
```

### **Docker配置**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8005

# 启动服务
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "4"]
```

---

## 🚀 性能优化

### **批量处理**
```python
async def batch_add_memories(self, requests: List[MemoryAddRequest]) -> List[Dict]:
    """批量添加记忆"""
    results = []
    
    # 按用户分组处理
    user_groups = {}
    for req in requests:
        if req.user_id not in user_groups:
            user_groups[req.user_id] = []
        user_groups[req.user_id].append(req)
    
    # 并发处理每个用户的记忆
    tasks = []
    for user_id, user_requests in user_groups.items():
        task = asyncio.create_task(
            self._process_user_memories(user_id, user_requests)
        )
        tasks.append(task)
    
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in batch_results:
        if isinstance(result, Exception):
            results.append({"error": str(result)})
        else:
            results.extend(result)
    
    return results
```

### **缓存策略**
```python
from aiocache import cached, Cache
from aiocache.serializers import PickleSerializer

# 配置缓存
cache = Cache(Cache.REDIS, endpoint="redis://lyss-redis:6379/1")

@cached(ttl=3600, cache=cache, serializer=PickleSerializer())
async def get_user_profile_cached(self, user_id: str) -> UserProfileResponse:
    """缓存的用户画像获取"""
    return await self.create_user_profile(user_id)

@cached(ttl=1800, cache=cache, serializer=PickleSerializer())
async def search_memories_cached(self, query: str, user_id: str, limit: int = 5) -> List[MemoryResponse]:
    """缓存的记忆搜索"""
    request = MemorySearchRequest(query=query, user_id=user_id, limit=limit)
    return await self.search_memories(request)
```

---

## 🔍 监控和调试

### **日志配置**
```python
import logging
from loguru import logger

# 配置结构化日志
logger.add(
    "logs/memory-service.log",
    rotation="1 day",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    serialize=True
)

# 性能监控装饰器
def monitor_performance(operation: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"操作完成", operation=operation, duration=duration, status="success")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"操作失败", operation=operation, duration=duration, error=str(e))
                raise
        return wrapper
    return decorator
```

### **健康检查**
```python
@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查"""
    health_status = {
        "service": "memory",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {}
    }
    
    # 检查Mem0AI
    try:
        test_search = memory_service.memory_client.search(
            query="health_check", user_id="system", limit=1
        )
        health_status["components"]["mem0ai"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["mem0ai"] = {"status": "unhealthy", "error": str(e)}
    
    # 检查Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"))
        collections = client.get_collections()
        health_status["components"]["qdrant"] = {"status": "healthy", "collections": len(collections.collections)}
    except Exception as e:
        health_status["components"]["qdrant"] = {"status": "unhealthy", "error": str(e)}
    
    # 检查数据库
    try:
        # 这里添加数据库连接检查
        health_status["components"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["components"]["database"] = {"status": "unhealthy", "error": str(e)}
    
    overall_healthy = all(
        comp["status"] == "healthy" 
        for comp in health_status["components"].values()
    )
    
    health_status["overall"] = "healthy" if overall_healthy else "unhealthy"
    
    if not overall_healthy:
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status
```

---

## 🔄 版本兼容性

- **Mem0AI版本**: 最新稳定版 (持续更新)
- **Qdrant版本**: 1.12.0+
- **Python版本**: 3.11+
- **依赖管理**: requirements.txt精确版本控制
- **升级策略**: 定期使用Context7更新到最新兼容版本