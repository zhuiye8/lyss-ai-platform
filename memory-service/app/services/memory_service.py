"""
Memory service implementation using Mem0AI
"""
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json
import uuid
from mem0 import Memory
import redis.asyncio as redis

from ..config import Settings
from ..models.memory_models import MemoryEntry, MemorySearch, MemoryCategory
from ..utils.logging import get_logger

logger = get_logger(__name__)


class MemoryService:
    """
    Memory service that provides intelligent memory management
    using Mem0AI for personalized AI experiences
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
        self.mem0_client: Optional[Memory] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the memory service"""
        if self._initialized:
            return
        
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(
                self.settings.redis.url,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Initialize Mem0AI client
            mem0_config = self._get_mem0_config()
            self.mem0_client = Memory(config=mem0_config)
            logger.info("Mem0AI client initialized")
            
            # Start background tasks
            if self.settings.memory.enable_memory_consolidation:
                asyncio.create_task(self._start_background_tasks())
            
            self._initialized = True
            logger.info("Memory service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize memory service: {e}")
            raise
    
    def _get_mem0_config(self) -> Dict[str, Any]:
        """Get Mem0AI configuration"""
        config = {
            "vector_store": {
                "provider": self.settings.vector_db.provider,
            },
            "embedder": {
                "provider": self.settings.embedding.provider,
                "config": {
                    "model": self.settings.embedding.model_name,
                }
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4",
                    "api_key": self.settings.embedding.openai_api_key,
                }
            }
        }
        
        # Configure vector store based on provider
        if self.settings.vector_db.provider == "redis":
            config["vector_store"]["config"] = {
                "redis_url": self.settings.redis.url,
                "index_name": "lyss_memory_index",
                "vector_key": "vector",
                "content_key": "content",
                "metadata_key": "metadata",
            }
        elif self.settings.vector_db.provider == "qdrant":
            config["vector_store"]["config"] = {
                "host": self.settings.vector_db.qdrant_host,
                "port": self.settings.vector_db.qdrant_port,
                "api_key": self.settings.vector_db.qdrant_api_key,
                "collection_name": "lyss_memories",
            }
        elif self.settings.vector_db.provider == "chroma":
            config["vector_store"]["config"] = {
                "host": self.settings.vector_db.chroma_host,
                "port": self.settings.vector_db.chroma_port,
                "collection_name": "lyss_memories",
            }
        
        return config
    
    async def add_memory(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        category: Optional[str] = None,
        importance: Optional[float] = None
    ) -> MemoryEntry:
        """Add a new memory for a user"""
        try:
            # Prepare memory data
            memory_metadata = {
                "timestamp": datetime.utcnow().isoformat(),
                "category": category or "general",
                "importance": importance or self._calculate_importance(content),
                **(metadata or {})
            }
            
            # Add memory using Mem0AI
            memory_result = self.mem0_client.add(
                messages=[{"role": "user", "content": content}],
                user_id=user_id,
                metadata=memory_metadata
            )
            
            # Create memory entry
            memory_entry = MemoryEntry(
                memory_id=str(uuid.uuid4()),
                user_id=user_id,
                content=content,
                metadata=memory_metadata,
                category=MemoryCategory(category or "general"),
                importance=importance or self._calculate_importance(content),
                created_at=datetime.utcnow()
            )
            
            # Cache in Redis for quick access
            await self._cache_memory(memory_entry)
            
            logger.info(f"Memory added for user {user_id}: {memory_entry.memory_id}")
            return memory_entry
            
        except Exception as e:
            logger.error(f"Failed to add memory for user {user_id}: {e}")
            raise
    
    async def search_memories(
        self,
        user_id: str,
        query: str,
        limit: Optional[int] = None,
        category: Optional[str] = None,
        threshold: Optional[float] = None
    ) -> List[MemoryEntry]:
        """Search memories for a user"""
        try:
            search_limit = min(
                limit or self.settings.memory.default_search_limit,
                self.settings.memory.max_search_limit
            )
            
            # Search using Mem0AI
            search_results = self.mem0_client.search(
                query=query,
                user_id=user_id,
                limit=search_limit
            )
            
            memories = []
            similarity_threshold = threshold or self.settings.memory.similarity_threshold
            
            for result in search_results:
                # Filter by similarity threshold
                if result.get("score", 0) < similarity_threshold:
                    continue
                
                # Filter by category if specified
                if category and result.get("metadata", {}).get("category") != category:
                    continue
                
                memory_entry = MemoryEntry(
                    memory_id=result.get("id", str(uuid.uuid4())),
                    user_id=user_id,
                    content=result.get("memory", ""),
                    metadata=result.get("metadata", {}),
                    category=MemoryCategory(result.get("metadata", {}).get("category", "general")),
                    importance=result.get("metadata", {}).get("importance", 0.5),
                    relevance_score=result.get("score", 0),
                    created_at=datetime.fromisoformat(
                        result.get("metadata", {}).get("timestamp", datetime.utcnow().isoformat())
                    )
                )
                memories.append(memory_entry)
            
            logger.info(f"Found {len(memories)} memories for user {user_id} with query: {query}")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to search memories for user {user_id}: {e}")
            raise
    
    async def get_user_memories(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Get all memories for a user"""
        try:
            # Get from Mem0AI
            memories = self.mem0_client.get_all(
                user_id=user_id
            )
            
            # Convert to MemoryEntry objects
            memory_entries = []
            for memory in memories:
                # Filter by category if specified
                if category and memory.get("metadata", {}).get("category") != category:
                    continue
                
                memory_entry = MemoryEntry(
                    memory_id=memory.get("id", str(uuid.uuid4())),
                    user_id=user_id,
                    content=memory.get("memory", ""),
                    metadata=memory.get("metadata", {}),
                    category=MemoryCategory(memory.get("metadata", {}).get("category", "general")),
                    importance=memory.get("metadata", {}).get("importance", 0.5),
                    created_at=datetime.fromisoformat(
                        memory.get("metadata", {}).get("timestamp", datetime.utcnow().isoformat())
                    )
                )
                memory_entries.append(memory_entry)
            
            # Sort by creation time (newest first)
            memory_entries.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply pagination
            start_idx = offset or 0
            end_idx = start_idx + (limit or len(memory_entries))
            
            paginated_memories = memory_entries[start_idx:end_idx]
            
            logger.info(f"Retrieved {len(paginated_memories)} memories for user {user_id}")
            return paginated_memories
            
        except Exception as e:
            logger.error(f"Failed to get memories for user {user_id}: {e}")
            raise
    
    async def update_memory(
        self,
        memory_id: str,
        user_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MemoryEntry:
        """Update an existing memory"""
        try:
            # Update using Mem0AI
            update_data = {}
            if content:
                update_data["memory"] = content
            if metadata:
                update_data["metadata"] = metadata
            
            # Mem0AI doesn't have direct update, so we'll delete and recreate
            await self.delete_memory(memory_id, user_id)
            
            # Add updated memory
            updated_memory = await self.add_memory(
                user_id=user_id,
                content=content,
                metadata=metadata
            )
            
            logger.info(f"Memory updated for user {user_id}: {memory_id}")
            return updated_memory
            
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id} for user {user_id}: {e}")
            raise
    
    async def delete_memory(self, memory_id: str, user_id: str) -> bool:
        """Delete a memory"""
        try:
            # Delete from Mem0AI
            self.mem0_client.delete(memory_id=memory_id)
            
            # Remove from cache
            await self._remove_memory_cache(memory_id, user_id)
            
            logger.info(f"Memory deleted for user {user_id}: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id} for user {user_id}: {e}")
            return False
    
    async def get_memory_summary(self, user_id: str) -> Dict[str, Any]:
        """Get memory summary for a user"""
        try:
            memories = await self.get_user_memories(user_id)
            
            # Calculate statistics
            total_memories = len(memories)
            categories = {}
            importance_distribution = {"high": 0, "medium": 0, "low": 0}
            
            for memory in memories:
                # Category distribution
                category = memory.category.value
                categories[category] = categories.get(category, 0) + 1
                
                # Importance distribution
                if memory.importance >= 0.8:
                    importance_distribution["high"] += 1
                elif memory.importance >= 0.5:
                    importance_distribution["medium"] += 1
                else:
                    importance_distribution["low"] += 1
            
            # Recent activity (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_memories = [m for m in memories if m.created_at >= week_ago]
            
            summary = {
                "user_id": user_id,
                "total_memories": total_memories,
                "categories": categories,
                "importance_distribution": importance_distribution,
                "recent_activity": {
                    "last_7_days": len(recent_memories),
                    "average_per_day": len(recent_memories) / 7
                },
                "oldest_memory": memories[-1].created_at.isoformat() if memories else None,
                "newest_memory": memories[0].created_at.isoformat() if memories else None
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get memory summary for user {user_id}: {e}")
            raise
    
    def _calculate_importance(self, content: str) -> float:
        """Calculate importance score for content"""
        # Simple heuristic-based importance calculation
        # In production, this could use ML models
        
        importance = 0.5  # Base importance
        
        # Length factor
        if len(content) > 200:
            importance += 0.1
        
        # Keyword-based importance
        important_keywords = [
            "important", "urgent", "critical", "remember", "note",
            "favorite", "preference", "like", "dislike", "always", "never"
        ]
        
        content_lower = content.lower()
        for keyword in important_keywords:
            if keyword in content_lower:
                importance += 0.1
                break
        
        # Question or instruction
        if content.strip().endswith('?') or content.lower().startswith(('how', 'what', 'when', 'where', 'why')):
            importance += 0.1
        
        return min(importance, 1.0)
    
    async def _cache_memory(self, memory: MemoryEntry) -> None:
        """Cache memory in Redis for quick access"""
        if not self.redis_client:
            return
        
        cache_key = f"memory:{memory.user_id}:{memory.memory_id}"
        cache_data = {
            "memory_id": memory.memory_id,
            "user_id": memory.user_id,
            "content": memory.content,
            "metadata": json.dumps(memory.metadata),
            "category": memory.category.value,
            "importance": memory.importance,
            "created_at": memory.created_at.isoformat()
        }
        
        await self.redis_client.hset(cache_key, mapping=cache_data)
        await self.redis_client.expire(cache_key, 3600)  # 1 hour TTL
    
    async def _remove_memory_cache(self, memory_id: str, user_id: str) -> None:
        """Remove memory from Redis cache"""
        if not self.redis_client:
            return
        
        cache_key = f"memory:{user_id}:{memory_id}"
        await self.redis_client.delete(cache_key)
    
    async def _start_background_tasks(self) -> None:
        """Start background tasks for memory management"""
        # Memory cleanup task
        asyncio.create_task(self._periodic_cleanup())
        
        # Memory consolidation task
        asyncio.create_task(self._periodic_consolidation())
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of old memories"""
        while True:
            try:
                await asyncio.sleep(self.settings.memory.cleanup_interval_hours * 3600)
                
                # Cleanup logic would go here
                # For example, removing very old memories or consolidating similar ones
                logger.info("Performing periodic memory cleanup")
                
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _periodic_consolidation(self) -> None:
        """Periodic consolidation of related memories"""
        while True:
            try:
                await asyncio.sleep(self.settings.memory.consolidation_interval_hours * 3600)
                
                # Consolidation logic would go here
                # For example, merging similar memories or updating importance scores
                logger.info("Performing periodic memory consolidation")
                
            except Exception as e:
                logger.error(f"Error in periodic consolidation: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.redis_client:
            await self.redis_client.close()
        
        self._initialized = False
        logger.info("Memory service cleaned up")