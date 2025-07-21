# lyss-memory-service (智能记忆服务)

## 📋 服务概述

智能记忆服务基于Mem0AI框架，提供对话记忆存储、语义检索和个性化上下文生成功能。

---

## 🎯 服务职责

```
技术栈: FastAPI + Mem0AI + Qdrant + PostgreSQL
端口: 8005
数据库: lyss_memory_db
职责：
- Mem0AI集成和记忆管理
- 对话历史智能存储
- 语义记忆检索和增强
- 个性化上下文生成
- 记忆关联分析和用户画像
```

---

## 🔍 技术实现详细说明

### **Mem0AI最新集成方案**
```python
# 基于Context7调研的Mem0AI最佳实践
import os
from typing import List, Dict, Optional
from mem0 import Memory, MemoryClient
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

# 1. Mem0AI配置和初始化
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

# 2. 数据模型定义
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

# 3. 核心业务逻辑
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

# 4. FastAPI路由定义
app = FastAPI(title="Lyss Memory Service")
memory_service = MemoryService()

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
```

### **高级记忆管理功能**
```python
# 5. 高级记忆功能
class AdvancedMemoryService(MemoryService):
    
    async def create_user_profile(self, user_id: str) -> Dict:
        """生成用户画像"""
        try:
            # 获取用户所有记忆
            all_memories = self.memory_client.get_all(user_id=user_id)
            
            if not all_memories.get("results"):
                return {"profile": "新用户，暂无足够数据生成画像"}
            
            # 使用Mem0AI分析用户偏好
            profile_query = "总结这个用户的兴趣爱好、工作情况和个人偏好"
            profile_memories = self.memory_client.search(
                query=profile_query,
                user_id=user_id,
                limit=10
            )
            
            # 构建用户画像
            profile_parts = []
            for memory in profile_memories:
                profile_parts.append(memory["memory"])
            
            return {
                "user_id": user_id,
                "total_memories": len(all_memories["results"]),
                "profile_summary": "\n".join(profile_parts[:5]),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"用户画像生成失败: {str(e)}")
    
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

### **关键技术优势**
- **向量检索**: 使用Qdrant进行高效语义搜索
- **智能总结**: Mem0AI自动提取和总结对话要点
- **个性化**: 基于历史记忆生成个性化回复上下文
- **多模态支持**: 支持文本、图片等多种内容类型的记忆
- **可扩展性**: 支持大规模用户和海量记忆数据

---

## 📊 数据库设计

### **记忆元数据表**
```sql
-- 记忆元数据表
CREATE TABLE memory_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    memory_id VARCHAR(255) NOT NULL, -- Mem0AI记忆ID
    conversation_id UUID,
    source_type VARCHAR(50) NOT NULL, -- 'conversation', 'document', 'manual'
    category VARCHAR(100),
    tags TEXT[],
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
    last_updated TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_profiles_tenant (tenant_id),
    INDEX idx_profiles_updated (last_updated)
);
```

---

## 🔧 配置管理

### **环境变量**
```bash
# 服务配置
MEMORY_SERVICE_PORT=8005
MEMORY_SERVICE_DEBUG=false

# 数据库配置
MEMORY_SERVICE_DATABASE_URL=postgresql://lyss:password@lyss-postgres:5432/lyss_memory_db

# Qdrant配置
MEMORY_SERVICE_QDRANT_HOST=lyss-qdrant
MEMORY_SERVICE_QDRANT_PORT=6333
MEMORY_SERVICE_QDRANT_COLLECTION=lyss_memories

# Mem0AI配置
MEMORY_SERVICE_OPENAI_API_KEY=your_openai_api_key
MEMORY_SERVICE_EMBEDDING_MODEL=text-embedding-3-small
MEMORY_SERVICE_LLM_MODEL=gpt-4o-mini

# 记忆管理配置
MEMORY_SERVICE_MAX_MEMORIES_PER_USER=10000
MEMORY_SERVICE_MEMORY_TTL_DAYS=365
MEMORY_SERVICE_CLEANUP_INTERVAL_HOURS=24
```