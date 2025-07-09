"""
Lyss AI Platform - 对话服务
功能描述: 处理对话相关的业务逻辑，包括创建、查询、更新、删除等操作
作者: Claude AI Assistant
创建时间: 2025-07-09
最后更新: 2025-07-09
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from common.models import Conversation, Message, User, ConversationStatus, MessageRole
from common.database import get_async_session
from common.redis_client import CacheManager
from api_gateway.middleware.auth import get_current_tenant_id, get_current_user_id
from common.response import ResponseHelper, ErrorCode


class ConversationService:
    """对话服务类
    
    负责处理对话相关的业务逻辑，包括创建、更新、删除、查询等操作
    支持多租户隔离和缓存优化
    """
    
    def __init__(self, db_session: AsyncSession, cache_manager: CacheManager = None):
        """初始化对话服务
        
        Args:
            db_session: 数据库会话对象
            cache_manager: 缓存管理器，可选
        """
        self.db_session = db_session
        self.cache_manager = cache_manager
        self.default_page_size = 20
        self.max_page_size = 100
    
    async def create_conversation(
        self, 
        user_id: str, 
        title: str = None,
        system_prompt: str = None,
        model_config: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> Conversation:
        """创建新对话
        
        Args:
            user_id: 用户ID
            title: 对话标题，可选
            system_prompt: 系统提示词，可选
            model_config: 模型配置，可选
            metadata: 元数据，可选
            
        Returns:
            Conversation: 创建的对话对象
            
        Raises:
            ValueError: 当参数无效时抛出
        """
        # 参数验证
        if not user_id:
            raise ValueError("用户ID不能为空")
        
        # 获取当前租户ID
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("无法获取当前租户信息")
        
        # 验证用户存在
        user_stmt = select(User).where(
            and_(
                User.user_id == uuid.UUID(user_id),
                User.tenant_id == uuid.UUID(tenant_id)
            )
        )
        user_result = await self.db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("用户不存在或无权限")
        
        # 设置默认值
        if not title:
            title = f"新对话 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        if not model_config:
            model_config = {
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000
            }
        
        if not metadata:
            metadata = {}
        
        # 创建对话记录
        conversation = Conversation(
            user_id=uuid.UUID(user_id),
            title=title,
            system_prompt=system_prompt,
            model_config=model_config,
            conversation_metadata=metadata,
            status=ConversationStatus.ACTIVE
        )
        
        self.db_session.add(conversation)
        await self.db_session.commit()
        await self.db_session.refresh(conversation)
        
        # 清除用户对话列表缓存
        if self.cache_manager:
            await self.cache_manager.delete(f"user_conversations:{user_id}")
        
        return conversation
    
    async def get_conversation_by_id(
        self, 
        conversation_id: str,
        user_id: str = None,
        include_messages: bool = False
    ) -> Optional[Conversation]:
        """根据ID获取对话
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID，用于权限验证
            include_messages: 是否包含消息列表
            
        Returns:
            Optional[Conversation]: 对话对象，如果不存在则返回None
        """
        # 参数验证
        if not conversation_id:
            raise ValueError("对话ID不能为空")
        
        # 获取当前租户ID
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("无法获取当前租户信息")
        
        # 如果没有指定用户ID，从上下文获取
        if not user_id:
            user_id = get_current_user_id()
        
        # 构建查询
        stmt = select(Conversation).where(
            Conversation.conversation_id == uuid.UUID(conversation_id)
        )
        
        # 如果需要包含消息，使用预加载
        if include_messages:
            stmt = stmt.options(selectinload(Conversation.messages))
        
        # 权限验证：只能查看自己的对话
        if user_id:
            stmt = stmt.where(Conversation.user_id == uuid.UUID(user_id))
        
        result = await self.db_session.execute(stmt)
        conversation = result.scalar_one_or_none()
        
        # 验证对话所属用户的租户
        if conversation:
            user_stmt = select(User).where(
                and_(
                    User.user_id == conversation.user_id,
                    User.tenant_id == uuid.UUID(tenant_id)
                )
            )
            user_result = await self.db_session.execute(user_stmt)
            user = user_result.scalar_one_or_none()
            
            if not user:
                return None  # 不同租户的对话不能访问
        
        return conversation
    
    async def get_conversations(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: ConversationStatus = None,
        search_query: str = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """获取用户的对话列表
        
        Args:
            user_id: 用户ID
            page: 页码，从1开始
            page_size: 每页大小
            status: 对话状态过滤
            search_query: 搜索关键词
            sort_by: 排序字段
            sort_order: 排序顺序，asc或desc
            
        Returns:
            Dict[str, Any]: 包含对话列表和分页信息的字典
        """
        # 参数验证
        if not user_id:
            raise ValueError("用户ID不能为空")
        
        if page < 1:
            page = 1
        
        if page_size < 1 or page_size > self.max_page_size:
            page_size = self.default_page_size
        
        # 获取当前租户ID
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("无法获取当前租户信息")
        
        # 验证用户存在
        user_stmt = select(User).where(
            and_(
                User.user_id == uuid.UUID(user_id),
                User.tenant_id == uuid.UUID(tenant_id)
            )
        )
        user_result = await self.db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("用户不存在或无权限")
        
        # 构建查询条件
        conditions = [
            Conversation.user_id == uuid.UUID(user_id),
            Conversation.deleted_at.is_(None)  # 排除已删除的对话
        ]
        
        # 状态过滤
        if status:
            conditions.append(Conversation.status == status)
        
        # 搜索过滤
        if search_query:
            search_condition = or_(
                Conversation.title.ilike(f"%{search_query}%"),
                Conversation.summary.ilike(f"%{search_query}%")
            )
            conditions.append(search_condition)
        
        # 构建排序
        sort_column = getattr(Conversation, sort_by, Conversation.updated_at)
        if sort_order.lower() == "asc":
            order_by = asc(sort_column)
        else:
            order_by = desc(sort_column)
        
        # 查询总数
        count_stmt = select(func.count(Conversation.conversation_id)).where(
            and_(*conditions)
        )
        count_result = await self.db_session.execute(count_stmt)
        total_count = count_result.scalar()
        
        # 查询对话列表
        conversations_stmt = (
            select(Conversation)
            .where(and_(*conditions))
            .order_by(order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        
        conversations_result = await self.db_session.execute(conversations_stmt)
        conversations = conversations_result.scalars().all()
        
        # 计算分页信息
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        return {
            "conversations": conversations,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous
            }
        }
    
    async def update_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: str = None,
        summary: str = None,
        system_prompt: str = None,
        model_config: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[Conversation]:
        """更新对话信息
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            title: 新标题，可选
            summary: 对话摘要，可选
            system_prompt: 系统提示词，可选
            model_config: 模型配置，可选
            metadata: 元数据，可选
            
        Returns:
            Optional[Conversation]: 更新后的对话对象
        """
        # 获取对话
        conversation = await self.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            return None
        
        # 更新字段
        if title is not None:
            conversation.title = title
        
        if summary is not None:
            conversation.summary = summary
        
        if system_prompt is not None:
            conversation.system_prompt = system_prompt
        
        if model_config is not None:
            conversation.model_config = model_config
        
        if metadata is not None:
            conversation.conversation_metadata = metadata
        
        conversation.updated_at = datetime.utcnow()
        
        await self.db_session.commit()
        await self.db_session.refresh(conversation)
        
        # 清除缓存
        if self.cache_manager:
            await self.cache_manager.delete(f"conversation:{conversation_id}")
            await self.cache_manager.delete(f"user_conversations:{user_id}")
        
        return conversation
    
    async def delete_conversation(
        self,
        conversation_id: str,
        user_id: str,
        soft_delete: bool = True
    ) -> bool:
        """删除对话
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            soft_delete: 是否软删除，默认True
            
        Returns:
            bool: 是否删除成功
        """
        # 获取对话
        conversation = await self.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            return False
        
        if soft_delete:
            # 软删除
            conversation.status = ConversationStatus.DELETED
            conversation.deleted_at = datetime.utcnow()
        else:
            # 硬删除
            await self.db_session.delete(conversation)
        
        await self.db_session.commit()
        
        # 清除缓存
        if self.cache_manager:
            await self.cache_manager.delete(f"conversation:{conversation_id}")
            await self.cache_manager.delete(f"user_conversations:{user_id}")
        
        return True
    
    async def get_conversation_statistics(self, user_id: str) -> Dict[str, Any]:
        """获取用户对话统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 获取当前租户ID
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("无法获取当前租户信息")
        
        # 验证用户存在
        user_stmt = select(User).where(
            and_(
                User.user_id == uuid.UUID(user_id),
                User.tenant_id == uuid.UUID(tenant_id)
            )
        )
        user_result = await self.db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise ValueError("用户不存在或无权限")
        
        # 统计各状态对话数量
        stats_stmt = (
            select(
                Conversation.status,
                func.count(Conversation.conversation_id).label("count")
            )
            .where(
                and_(
                    Conversation.user_id == uuid.UUID(user_id),
                    Conversation.deleted_at.is_(None)
                )
            )
            .group_by(Conversation.status)
        )
        
        stats_result = await self.db_session.execute(stats_stmt)
        status_counts = {row.status: row.count for row in stats_result}
        
        # 统计总消息数
        total_messages_stmt = (
            select(func.count(Message.message_id))
            .join(Conversation)
            .where(
                and_(
                    Conversation.user_id == uuid.UUID(user_id),
                    Conversation.deleted_at.is_(None)
                )
            )
        )
        
        total_messages_result = await self.db_session.execute(total_messages_stmt)
        total_messages = total_messages_result.scalar() or 0
        
        # 统计今日消息数
        today = datetime.now().date()
        today_messages_stmt = (
            select(func.count(Message.message_id))
            .join(Conversation)
            .where(
                and_(
                    Conversation.user_id == uuid.UUID(user_id),
                    Conversation.deleted_at.is_(None),
                    func.date(Message.created_at) == today
                )
            )
        )
        
        today_messages_result = await self.db_session.execute(today_messages_stmt)
        today_messages = today_messages_result.scalar() or 0
        
        return {
            "total_conversations": sum(status_counts.values()),
            "active_conversations": status_counts.get(ConversationStatus.ACTIVE, 0),
            "archived_conversations": status_counts.get(ConversationStatus.ARCHIVED, 0),
            "total_messages": total_messages,
            "today_messages": today_messages,
            "status_breakdown": status_counts
        }


async def get_conversation_service(
    db_session: AsyncSession = None,
    cache_manager: CacheManager = None
) -> ConversationService:
    """获取对话服务实例
    
    Args:
        db_session: 数据库会话，可选
        cache_manager: 缓存管理器，可选
        
    Returns:
        ConversationService: 对话服务实例
    """
    if db_session is None:
        db_session = await get_async_session().__anext__()
    
    if cache_manager is None:
        tenant_id = get_current_tenant_id()
        if tenant_id:
            cache_manager = CacheManager(tenant_id)
    
    return ConversationService(db_session, cache_manager)