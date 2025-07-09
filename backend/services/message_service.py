"""
Lyss AI Platform - 消息服务
功能描述: 处理消息相关的业务逻辑，包括发送、接收、查询等操作
作者: Claude AI Assistant
创建时间: 2025-07-09
最后更新: 2025-07-09
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import selectinload

from common.models import Message, Conversation, User, MessageRole
from common.database import get_async_session
from common.redis_client import CacheManager
from api_gateway.middleware.auth import get_current_tenant_id, get_current_user_id
from common.response import ResponseHelper, ErrorCode


class MessageService:
    """消息服务类
    
    负责处理消息相关的业务逻辑，包括发送、接收、查询、删除等操作
    支持流式响应和实时通信
    """
    
    def __init__(self, db_session: AsyncSession, cache_manager: CacheManager = None):
        """初始化消息服务
        
        Args:
            db_session: 数据库会话对象
            cache_manager: 缓存管理器，可选
        """
        self.db_session = db_session
        self.cache_manager = cache_manager
        self.default_page_size = 50
        self.max_page_size = 200
    
    async def create_message(
        self,
        conversation_id: str,
        user_id: str,
        role: MessageRole,
        content: str,
        content_type: str = "text",
        parent_message_id: str = None,
        metadata: Dict[str, Any] = None,
        attachments: List[Dict[str, Any]] = None
    ) -> Message:
        """创建新消息
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            role: 消息角色
            content: 消息内容
            content_type: 内容类型，默认text
            parent_message_id: 父消息ID，可选
            metadata: 元数据，可选
            attachments: 附件列表，可选
            
        Returns:
            Message: 创建的消息对象
            
        Raises:
            ValueError: 当参数无效时抛出
        """
        # 参数验证
        if not conversation_id:
            raise ValueError("对话ID不能为空")
        
        if not user_id:
            raise ValueError("用户ID不能为空")
        
        if not content or not content.strip():
            raise ValueError("消息内容不能为空")
        
        if len(content) > 50000:  # 设置最大内容长度
            raise ValueError("消息内容过长，最大支持50000字符")
        
        # 获取当前租户ID
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("无法获取当前租户信息")
        
        # 验证对话存在且用户有权限
        conversation_stmt = select(Conversation).where(
            and_(
                Conversation.conversation_id == uuid.UUID(conversation_id),
                Conversation.user_id == uuid.UUID(user_id)
            )
        )
        conversation_result = await self.db_session.execute(conversation_stmt)
        conversation = conversation_result.scalar_one_or_none()
        
        if not conversation:
            raise ValueError("对话不存在或无权限")
        
        # 验证用户租户权限
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
        
        # 验证父消息存在（如果指定）
        if parent_message_id:
            parent_stmt = select(Message).where(
                and_(
                    Message.message_id == uuid.UUID(parent_message_id),
                    Message.conversation_id == uuid.UUID(conversation_id)
                )
            )
            parent_result = await self.db_session.execute(parent_stmt)
            parent_message = parent_result.scalar_one_or_none()
            
            if not parent_message:
                raise ValueError("父消息不存在")
        
        # 设置默认值
        if not metadata:
            metadata = {}
        
        if not attachments:
            attachments = []
        
        # 创建消息记录
        message = Message(
            conversation_id=uuid.UUID(conversation_id),
            user_id=uuid.UUID(user_id),
            parent_message_id=uuid.UUID(parent_message_id) if parent_message_id else None,
            role=role,
            content=content.strip(),
            content_type=content_type,
            message_metadata=metadata,
            attachments=attachments
        )
        
        self.db_session.add(message)
        
        # 更新对话的最后消息时间和消息数量
        conversation.last_message_at = datetime.utcnow()
        conversation.message_count += 1
        conversation.updated_at = datetime.utcnow()
        
        await self.db_session.commit()
        await self.db_session.refresh(message)
        
        # 清除相关缓存
        if self.cache_manager:
            await self.cache_manager.delete(f"conversation_messages:{conversation_id}")
            await self.cache_manager.delete(f"conversation:{conversation_id}")
        
        return message
    
    async def get_messages_by_conversation(
        self,
        conversation_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 50,
        include_deleted: bool = False,
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """获取对话的消息列表
        
        Args:
            conversation_id: 对话ID
            user_id: 用户ID
            page: 页码，从1开始
            page_size: 每页大小
            include_deleted: 是否包含已删除消息
            sort_order: 排序顺序，asc或desc
            
        Returns:
            Dict[str, Any]: 包含消息列表和分页信息的字典
        """
        # 参数验证
        if not conversation_id:
            raise ValueError("对话ID不能为空")
        
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
        
        # 验证对话存在且用户有权限
        conversation_stmt = select(Conversation).where(
            and_(
                Conversation.conversation_id == uuid.UUID(conversation_id),
                Conversation.user_id == uuid.UUID(user_id)
            )
        )
        conversation_result = await self.db_session.execute(conversation_stmt)
        conversation = conversation_result.scalar_one_or_none()
        
        if not conversation:
            raise ValueError("对话不存在或无权限")
        
        # 验证用户租户权限
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
            Message.conversation_id == uuid.UUID(conversation_id)
        ]
        
        # 是否包含已删除消息
        if not include_deleted:
            conditions.append(Message.deleted_at.is_(None))
        
        # 构建排序
        if sort_order.lower() == "desc":
            order_by = desc(Message.created_at)
        else:
            order_by = asc(Message.created_at)
        
        # 查询总数
        count_stmt = select(func.count(Message.message_id)).where(
            and_(*conditions)
        )
        count_result = await self.db_session.execute(count_stmt)
        total_count = count_result.scalar()
        
        # 查询消息列表
        messages_stmt = (
            select(Message)
            .where(and_(*conditions))
            .order_by(order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        
        messages_result = await self.db_session.execute(messages_stmt)
        messages = messages_result.scalars().all()
        
        # 计算分页信息
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        return {
            "messages": messages,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous
            }
        }
    
    async def get_message_by_id(
        self,
        message_id: str,
        user_id: str
    ) -> Optional[Message]:
        """根据ID获取消息
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            
        Returns:
            Optional[Message]: 消息对象，如果不存在则返回None
        """
        # 参数验证
        if not message_id:
            raise ValueError("消息ID不能为空")
        
        if not user_id:
            raise ValueError("用户ID不能为空")
        
        # 获取当前租户ID
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("无法获取当前租户信息")
        
        # 查询消息，并验证权限
        message_stmt = (
            select(Message)
            .join(Conversation)
            .where(
                and_(
                    Message.message_id == uuid.UUID(message_id),
                    Conversation.user_id == uuid.UUID(user_id),
                    Message.deleted_at.is_(None)
                )
            )
        )
        
        message_result = await self.db_session.execute(message_stmt)
        message = message_result.scalar_one_or_none()
        
        if not message:
            return None
        
        # 验证用户租户权限
        user_stmt = select(User).where(
            and_(
                User.user_id == uuid.UUID(user_id),
                User.tenant_id == uuid.UUID(tenant_id)
            )
        )
        user_result = await self.db_session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return None
        
        return message
    
    async def update_message(
        self,
        message_id: str,
        user_id: str,
        content: str = None,
        metadata: Dict[str, Any] = None,
        attachments: List[Dict[str, Any]] = None
    ) -> Optional[Message]:
        """更新消息
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            content: 新内容，可选
            metadata: 元数据，可选
            attachments: 附件列表，可选
            
        Returns:
            Optional[Message]: 更新后的消息对象
        """
        # 获取消息
        message = await self.get_message_by_id(message_id, user_id)
        if not message:
            return None
        
        # 只允许更新用户自己发送的消息
        if message.role != MessageRole.USER:
            raise ValueError("只能编辑用户自己发送的消息")
        
        # 更新字段
        if content is not None:
            if not content.strip():
                raise ValueError("消息内容不能为空")
            
            if len(content) > 50000:
                raise ValueError("消息内容过长，最大支持50000字符")
            
            message.content = content.strip()
        
        if metadata is not None:
            message.message_metadata = metadata
        
        if attachments is not None:
            message.attachments = attachments
        
        message.updated_at = datetime.utcnow()
        
        await self.db_session.commit()
        await self.db_session.refresh(message)
        
        # 清除相关缓存
        if self.cache_manager:
            await self.cache_manager.delete(f"conversation_messages:{message.conversation_id}")
            await self.cache_manager.delete(f"message:{message_id}")
        
        return message
    
    async def delete_message(
        self,
        message_id: str,
        user_id: str,
        soft_delete: bool = True
    ) -> bool:
        """删除消息
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            soft_delete: 是否软删除，默认True
            
        Returns:
            bool: 是否删除成功
        """
        # 获取消息
        message = await self.get_message_by_id(message_id, user_id)
        if not message:
            return False
        
        # 只允许删除用户自己发送的消息
        if message.role != MessageRole.USER:
            raise ValueError("只能删除用户自己发送的消息")
        
        if soft_delete:
            # 软删除
            message.deleted_at = datetime.utcnow()
        else:
            # 硬删除
            await self.db_session.delete(message)
        
        # 更新对话的消息数量
        conversation_stmt = select(Conversation).where(
            Conversation.conversation_id == message.conversation_id
        )
        conversation_result = await self.db_session.execute(conversation_stmt)
        conversation = conversation_result.scalar_one_or_none()
        
        if conversation:
            conversation.message_count = max(0, conversation.message_count - 1)
            conversation.updated_at = datetime.utcnow()
        
        await self.db_session.commit()
        
        # 清除相关缓存
        if self.cache_manager:
            await self.cache_manager.delete(f"conversation_messages:{message.conversation_id}")
            await self.cache_manager.delete(f"message:{message_id}")
            await self.cache_manager.delete(f"conversation:{message.conversation_id}")
        
        return True
    
    async def search_messages(
        self,
        user_id: str,
        query: str,
        conversation_id: str = None,
        page: int = 1,
        page_size: int = 20,
        date_from: datetime = None,
        date_to: datetime = None
    ) -> Dict[str, Any]:
        """搜索用户的消息
        
        Args:
            user_id: 用户ID
            query: 搜索关键词
            conversation_id: 对话ID，可选
            page: 页码，从1开始
            page_size: 每页大小
            date_from: 开始日期，可选
            date_to: 结束日期，可选
            
        Returns:
            Dict[str, Any]: 包含搜索结果和分页信息的字典
        """
        # 参数验证
        if not user_id:
            raise ValueError("用户ID不能为空")
        
        if not query or not query.strip():
            raise ValueError("搜索关键词不能为空")
        
        if page < 1:
            page = 1
        
        if page_size < 1 or page_size > self.max_page_size:
            page_size = self.default_page_size
        
        # 获取当前租户ID
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("无法获取当前租户信息")
        
        # 验证用户租户权限
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
            Message.deleted_at.is_(None),
            Message.content.ilike(f"%{query.strip()}%")
        ]
        
        # 只搜索用户有权限的消息
        join_conditions = [
            Message.conversation_id == Conversation.conversation_id,
            Conversation.user_id == uuid.UUID(user_id)
        ]
        
        # 特定对话过滤
        if conversation_id:
            conditions.append(Message.conversation_id == uuid.UUID(conversation_id))
        
        # 日期范围过滤
        if date_from:
            conditions.append(Message.created_at >= date_from)
        
        if date_to:
            conditions.append(Message.created_at <= date_to)
        
        # 查询总数
        count_stmt = (
            select(func.count(Message.message_id))
            .join(Conversation, and_(*join_conditions))
            .where(and_(*conditions))
        )
        count_result = await self.db_session.execute(count_stmt)
        total_count = count_result.scalar()
        
        # 查询消息列表
        messages_stmt = (
            select(Message)
            .join(Conversation, and_(*join_conditions))
            .where(and_(*conditions))
            .order_by(desc(Message.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        
        messages_result = await self.db_session.execute(messages_stmt)
        messages = messages_result.scalars().all()
        
        # 计算分页信息
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        return {
            "messages": messages,
            "query": query,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous
            }
        }
    
    async def get_message_statistics(
        self,
        user_id: str,
        conversation_id: str = None
    ) -> Dict[str, Any]:
        """获取消息统计信息
        
        Args:
            user_id: 用户ID
            conversation_id: 对话ID，可选
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        # 获取当前租户ID
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise ValueError("无法获取当前租户信息")
        
        # 验证用户租户权限
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
        
        # 构建基础条件
        base_conditions = [
            Message.deleted_at.is_(None),
            Conversation.user_id == uuid.UUID(user_id)
        ]
        
        # 特定对话过滤
        if conversation_id:
            base_conditions.append(Message.conversation_id == uuid.UUID(conversation_id))
        
        # 统计各角色消息数量
        role_stats_stmt = (
            select(
                Message.role,
                func.count(Message.message_id).label("count")
            )
            .join(Conversation)
            .where(and_(*base_conditions))
            .group_by(Message.role)
        )
        
        role_stats_result = await self.db_session.execute(role_stats_stmt)
        role_counts = {row.role: row.count for row in role_stats_result}
        
        # 统计今日消息数
        today = datetime.now().date()
        today_messages_stmt = (
            select(func.count(Message.message_id))
            .join(Conversation)
            .where(
                and_(
                    *base_conditions,
                    func.date(Message.created_at) == today
                )
            )
        )
        
        today_messages_result = await self.db_session.execute(today_messages_stmt)
        today_messages = today_messages_result.scalar() or 0
        
        # 统计总token数（如果有）
        total_tokens_stmt = (
            select(
                func.coalesce(func.sum(Message.total_tokens), 0)
            )
            .join(Conversation)
            .where(and_(*base_conditions))
        )
        
        total_tokens_result = await self.db_session.execute(total_tokens_stmt)
        total_tokens = total_tokens_result.scalar() or 0
        
        return {
            "total_messages": sum(role_counts.values()),
            "user_messages": role_counts.get(MessageRole.USER, 0),
            "assistant_messages": role_counts.get(MessageRole.ASSISTANT, 0),
            "system_messages": role_counts.get(MessageRole.SYSTEM, 0),
            "today_messages": today_messages,
            "total_tokens": total_tokens,
            "role_breakdown": role_counts
        }


async def get_message_service(
    db_session: AsyncSession = None,
    cache_manager: CacheManager = None
) -> MessageService:
    """获取消息服务实例
    
    Args:
        db_session: 数据库会话，可选
        cache_manager: 缓存管理器，可选
        
    Returns:
        MessageService: 消息服务实例
    """
    if db_session is None:
        db_session = await get_async_session().__anext__()
    
    if cache_manager is None:
        tenant_id = get_current_tenant_id()
        if tenant_id:
            cache_manager = CacheManager(tenant_id)
    
    return MessageService(db_session, cache_manager)