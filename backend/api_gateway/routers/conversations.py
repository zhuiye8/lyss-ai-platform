"""
Lyss AI Platform - 对话管理API
功能描述: 对话相关的RESTful API接口
作者: Claude AI Assistant
创建时间: 2025-07-09
最后更新: 2025-07-09
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
import uuid
import json

from common.database import get_async_session
from common.models import User, ConversationStatus, MessageRole
from common.response import ResponseHelper, ErrorCode
from api_gateway.routers.auth import get_current_user
from services.conversation_service import get_conversation_service, ConversationService
from services.message_service import get_message_service, MessageService

router = APIRouter()


# 请求模型
class ConversationCreateRequest(BaseModel):
    """创建对话请求模型"""
    title: Optional[str] = Field(None, description="对话标题")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    model_config: Optional[Dict[str, Any]] = Field(None, description="模型配置")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    @validator('title')
    def validate_title(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('对话标题不能为空')
        if v is not None and len(v) > 500:
            raise ValueError('对话标题不能超过500个字符')
        return v
    
    @validator('system_prompt')
    def validate_system_prompt(cls, v):
        if v is not None and len(v) > 10000:
            raise ValueError('系统提示词不能超过10000个字符')
        return v


class ConversationUpdateRequest(BaseModel):
    """更新对话请求模型"""
    title: Optional[str] = Field(None, description="对话标题")
    summary: Optional[str] = Field(None, description="对话摘要")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    model_config: Optional[Dict[str, Any]] = Field(None, description="模型配置")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    
    @validator('title')
    def validate_title(cls, v):
        if v is not None and len(v.strip()) == 0:
            raise ValueError('对话标题不能为空')
        if v is not None and len(v) > 500:
            raise ValueError('对话标题不能超过500个字符')
        return v
    
    @validator('summary')
    def validate_summary(cls, v):
        if v is not None and len(v) > 2000:
            raise ValueError('对话摘要不能超过2000个字符')
        return v


class MessageCreateRequest(BaseModel):
    """创建消息请求模型"""
    content: str = Field(..., description="消息内容")
    content_type: str = Field("text", description="内容类型")
    parent_message_id: Optional[str] = Field(None, description="父消息ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        if len(v) > 50000:
            raise ValueError('消息内容不能超过50000个字符')
        return v
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['text', 'markdown', 'json', 'html']
        if v not in allowed_types:
            raise ValueError(f'内容类型必须是以下之一: {", ".join(allowed_types)}')
        return v


class MessageUpdateRequest(BaseModel):
    """更新消息请求模型"""
    content: Optional[str] = Field(None, description="消息内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    attachments: Optional[List[Dict[str, Any]]] = Field(None, description="附件列表")
    
    @validator('content')
    def validate_content(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('消息内容不能为空')
        if v is not None and len(v) > 50000:
            raise ValueError('消息内容不能超过50000个字符')
        return v


# 响应模型
class ConversationResponse(BaseModel):
    """对话响应模型"""
    conversation_id: str
    user_id: str
    title: Optional[str] = None
    summary: Optional[str] = None
    status: str
    message_count: int
    total_tokens: int
    estimated_cost: int
    system_prompt: Optional[str] = None
    model_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """消息响应模型"""
    message_id: str
    conversation_id: str
    user_id: str
    parent_message_id: Optional[str] = None
    role: str
    content: str
    content_type: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: int
    processing_time_ms: Optional[int] = None
    model_used: Optional[str] = None
    metadata: Dict[str, Any]
    attachments: Optional[List[Dict[str, Any]]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# 对话管理API
@router.post("/conversations", response_model=Dict[str, Any], summary="创建对话")
async def create_conversation(
    request: ConversationCreateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    创建新对话
    
    - 创建新的对话实例
    - 设置对话配置和元数据
    - 返回完整的对话信息
    """
    try:
        conversation = await conversation_service.create_conversation(
            user_id=str(current_user.user_id),
            title=request.title,
            system_prompt=request.system_prompt,
            model_config=request.model_config,
            metadata=request.metadata
        )
        
        return ResponseHelper.success(
            data=ConversationResponse.from_orm(conversation).dict(),
            message="对话创建成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建对话失败"
        )


@router.get("/conversations", response_model=Dict[str, Any], summary="获取对话列表")
async def get_conversations(
    http_request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    status: Optional[ConversationStatus] = Query(None, description="对话状态"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    sort_by: str = Query("updated_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序顺序"),
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取用户的对话列表
    
    - 支持分页查询
    - 支持状态过滤
    - 支持关键词搜索
    - 支持排序
    """
    try:
        result = await conversation_service.get_conversations(
            user_id=str(current_user.user_id),
            page=page,
            page_size=page_size,
            status=status,
            search_query=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 转换对话列表
        conversations_data = [
            ConversationResponse.from_orm(conv).dict()
            for conv in result["conversations"]
        ]
        
        return ResponseHelper.success(
            data={
                "conversations": conversations_data,
                "pagination": result["pagination"]
            },
            message="获取对话列表成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话列表失败"
        )


@router.get("/conversations/{conversation_id}", response_model=Dict[str, Any], summary="获取对话详情")
async def get_conversation(
    conversation_id: str,
    http_request: Request,
    include_messages: bool = Query(False, description="是否包含消息列表"),
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取对话详情
    
    - 根据ID获取对话信息
    - 可选择包含消息列表
    - 验证用户权限
    """
    try:
        conversation = await conversation_service.get_conversation_by_id(
            conversation_id=conversation_id,
            user_id=str(current_user.user_id),
            include_messages=include_messages
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        conversation_data = ConversationResponse.from_orm(conversation).dict()
        
        # 如果包含消息，转换消息列表
        if include_messages and hasattr(conversation, 'messages'):
            conversation_data["messages"] = [
                MessageResponse.from_orm(msg).dict()
                for msg in conversation.messages
            ]
        
        return ResponseHelper.success(
            data=conversation_data,
            message="获取对话详情成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话详情失败"
        )


@router.put("/conversations/{conversation_id}", response_model=Dict[str, Any], summary="更新对话")
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    更新对话信息
    
    - 更新对话标题、摘要等信息
    - 更新系统提示词和模型配置
    - 更新元数据
    """
    try:
        conversation = await conversation_service.update_conversation(
            conversation_id=conversation_id,
            user_id=str(current_user.user_id),
            title=request.title,
            summary=request.summary,
            system_prompt=request.system_prompt,
            model_config=request.model_config,
            metadata=request.metadata
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        return ResponseHelper.success(
            data=ConversationResponse.from_orm(conversation).dict(),
            message="对话更新成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新对话失败"
        )


@router.delete("/conversations/{conversation_id}", response_model=Dict[str, Any], summary="删除对话")
async def delete_conversation(
    conversation_id: str,
    http_request: Request,
    soft_delete: bool = Query(True, description="是否软删除"),
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    删除对话
    
    - 支持软删除和硬删除
    - 验证用户权限
    - 清理相关缓存
    """
    try:
        success = await conversation_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=str(current_user.user_id),
            soft_delete=soft_delete
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        return ResponseHelper.success(
            message="对话删除成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除对话失败"
        )


@router.get("/conversations/{conversation_id}/statistics", response_model=Dict[str, Any], summary="获取对话统计")
async def get_conversation_statistics(
    conversation_id: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    """
    获取对话统计信息
    
    - 获取对话的基本统计数据
    - 包括消息数量、token使用等
    """
    try:
        # 验证对话存在
        conversation = await conversation_service.get_conversation_by_id(
            conversation_id=conversation_id,
            user_id=str(current_user.user_id)
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在"
            )
        
        # 获取用户统计信息
        stats = await conversation_service.get_conversation_statistics(
            user_id=str(current_user.user_id)
        )
        
        return ResponseHelper.success(
            data=stats,
            message="获取对话统计成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话统计失败"
        )


# 消息管理API
@router.post("/conversations/{conversation_id}/messages", response_model=Dict[str, Any], summary="创建消息")
async def create_message(
    conversation_id: str,
    request: MessageCreateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    创建新消息
    
    - 在指定对话中创建用户消息
    - 支持附件和元数据
    - 更新对话统计信息
    """
    try:
        message = await message_service.create_message(
            conversation_id=conversation_id,
            user_id=str(current_user.user_id),
            role=MessageRole.USER,
            content=request.content,
            content_type=request.content_type,
            parent_message_id=request.parent_message_id,
            metadata=request.metadata,
            attachments=request.attachments
        )
        
        return ResponseHelper.success(
            data=MessageResponse.from_orm(message).dict(),
            message="消息创建成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建消息失败"
        )


@router.get("/conversations/{conversation_id}/messages", response_model=Dict[str, Any], summary="获取消息列表")
async def get_messages(
    conversation_id: str,
    http_request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页大小"),
    include_deleted: bool = Query(False, description="是否包含已删除消息"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="排序顺序"),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    获取对话的消息列表
    
    - 支持分页查询
    - 支持排序
    - 可选择包含已删除消息
    """
    try:
        result = await message_service.get_messages_by_conversation(
            conversation_id=conversation_id,
            user_id=str(current_user.user_id),
            page=page,
            page_size=page_size,
            include_deleted=include_deleted,
            sort_order=sort_order
        )
        
        # 转换消息列表
        messages_data = [
            MessageResponse.from_orm(msg).dict()
            for msg in result["messages"]
        ]
        
        return ResponseHelper.success(
            data={
                "messages": messages_data,
                "pagination": result["pagination"]
            },
            message="获取消息列表成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息列表失败"
        )


@router.get("/messages/{message_id}", response_model=Dict[str, Any], summary="获取消息详情")
async def get_message(
    message_id: str,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    获取消息详情
    
    - 根据ID获取消息信息
    - 验证用户权限
    """
    try:
        message = await message_service.get_message_by_id(
            message_id=message_id,
            user_id=str(current_user.user_id)
        )
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="消息不存在"
            )
        
        return ResponseHelper.success(
            data=MessageResponse.from_orm(message).dict(),
            message="获取消息详情成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息详情失败"
        )


@router.put("/messages/{message_id}", response_model=Dict[str, Any], summary="更新消息")
async def update_message(
    message_id: str,
    request: MessageUpdateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    更新消息
    
    - 更新消息内容和元数据
    - 只能更新用户自己发送的消息
    """
    try:
        message = await message_service.update_message(
            message_id=message_id,
            user_id=str(current_user.user_id),
            content=request.content,
            metadata=request.metadata,
            attachments=request.attachments
        )
        
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="消息不存在"
            )
        
        return ResponseHelper.success(
            data=MessageResponse.from_orm(message).dict(),
            message="消息更新成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新消息失败"
        )


@router.delete("/messages/{message_id}", response_model=Dict[str, Any], summary="删除消息")
async def delete_message(
    message_id: str,
    http_request: Request,
    soft_delete: bool = Query(True, description="是否软删除"),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    删除消息
    
    - 支持软删除和硬删除
    - 只能删除用户自己发送的消息
    """
    try:
        success = await message_service.delete_message(
            message_id=message_id,
            user_id=str(current_user.user_id),
            soft_delete=soft_delete
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="消息不存在"
            )
        
        return ResponseHelper.success(
            message="消息删除成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除消息失败"
        )


@router.get("/messages/search", response_model=Dict[str, Any], summary="搜索消息")
async def search_messages(
    http_request: Request,
    query: str = Query(..., description="搜索关键词"),
    conversation_id: Optional[str] = Query(None, description="对话ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    搜索消息
    
    - 根据关键词搜索用户的消息
    - 支持在特定对话中搜索
    - 支持分页
    """
    try:
        result = await message_service.search_messages(
            user_id=str(current_user.user_id),
            query=query,
            conversation_id=conversation_id,
            page=page,
            page_size=page_size
        )
        
        # 转换消息列表
        messages_data = [
            MessageResponse.from_orm(msg).dict()
            for msg in result["messages"]
        ]
        
        return ResponseHelper.success(
            data={
                "messages": messages_data,
                "query": result["query"],
                "pagination": result["pagination"]
            },
            message="搜索消息成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="搜索消息失败"
        )


@router.get("/messages/statistics", response_model=Dict[str, Any], summary="获取消息统计")
async def get_message_statistics(
    http_request: Request,
    conversation_id: Optional[str] = Query(None, description="对话ID"),
    current_user: User = Depends(get_current_user),
    message_service: MessageService = Depends(get_message_service)
):
    """
    获取消息统计信息
    
    - 获取用户的消息统计数据
    - 可选择特定对话的统计
    """
    try:
        stats = await message_service.get_message_statistics(
            user_id=str(current_user.user_id),
            conversation_id=conversation_id
        )
        
        return ResponseHelper.success(
            data=stats,
            message="获取消息统计成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息统计失败"
        )