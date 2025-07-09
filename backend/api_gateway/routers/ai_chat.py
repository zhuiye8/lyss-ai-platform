"""
Lyss AI Platform - AI聊天API
功能描述: AI聊天和对话相关的RESTful API接口
作者: Claude AI Assistant
创建时间: 2025-07-09
最后更新: 2025-07-09
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field, validator
import uuid
import json

from common.database import get_async_session
from common.models import User, MessageRole
from common.response import ResponseHelper, ErrorCode
from api_gateway.routers.auth import get_current_user
from services.ai_service import (
    get_ai_service,
    AIService,
    AIMessage,
    AIModelConfig,
    MessageRole as AIMessageRole
)
from services.conversation_service import get_conversation_service, ConversationService
from services.message_service import get_message_service, MessageService

router = APIRouter()


# 请求模型
class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(None, description="消息发送者名称")
    
    @validator('role')
    def validate_role(cls, v):
        allowed_roles = ['system', 'user', 'assistant', 'function', 'tool']
        if v not in allowed_roles:
            raise ValueError(f'角色必须是以下之一: {", ".join(allowed_roles)}')
        return v
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        if len(v) > 50000:
            raise ValueError('消息内容不能超过50000个字符')
        return v


class ModelConfig(BaseModel):
    """模型配置模型"""
    model: str = Field(..., description="模型名称")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(2000, ge=1, le=8000, description="最大token数")
    top_p: float = Field(1.0, ge=0.0, le=1.0, description="Top-p参数")
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0, description="存在惩罚")
    stop: Optional[List[str]] = Field(None, description="停止序列")
    stream: bool = Field(False, description="是否使用流式响应")
    
    @validator('model')
    def validate_model(cls, v):
        if not v or not v.strip():
            raise ValueError('模型名称不能为空')
        return v


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型"""
    conversation_id: Optional[str] = Field(None, description="对话ID")
    provider_id: str = Field(..., description="AI供应商ID")
    messages: List[ChatMessage] = Field(..., description="消息列表")
    config: ModelConfig = Field(..., description="模型配置")
    save_conversation: bool = Field(True, description="是否保存对话")
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v or len(v) == 0:
            raise ValueError('消息列表不能为空')
        if len(v) > 100:
            raise ValueError('消息列表不能超过100条')
        return v
    
    @validator('provider_id')
    def validate_provider_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('供应商ID格式无效')
        return v
    
    @validator('conversation_id')
    def validate_conversation_id(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError('对话ID格式无效')
        return v


class QuickChatRequest(BaseModel):
    """快速聊天请求模型"""
    message: str = Field(..., description="用户消息")
    provider_id: str = Field(..., description="AI供应商ID")
    model: str = Field("gpt-3.5-turbo", description="模型名称")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(2000, ge=1, le=8000, description="最大token数")
    stream: bool = Field(False, description="是否使用流式响应")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('消息内容不能为空')
        if len(v) > 10000:
            raise ValueError('消息内容不能超过10000个字符')
        return v


# 响应模型
class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型"""
    id: str
    object: str
    created: int
    model: str
    conversation_id: Optional[str] = None
    message_id: Optional[str] = None
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    processing_time_ms: Optional[int] = None
    estimated_cost_cents: Optional[int] = None


class ModelInfo(BaseModel):
    """模型信息模型"""
    model: str
    provider: str
    description: Optional[str] = None
    max_tokens: Optional[int] = None
    pricing: Optional[Dict[str, float]] = None


# API接口
@router.post("/chat/completions", response_model=Dict[str, Any], summary="聊天完成")
async def chat_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service),
    conversation_service: ConversationService = Depends(get_conversation_service),
    message_service: MessageService = Depends(get_message_service)
):
    """
    AI聊天完成接口
    
    - 支持多种AI供应商
    - 支持流式和非流式响应
    - 自动保存对话历史
    - 记录使用统计和成本
    """
    try:
        start_time = datetime.now()
        
        # 转换消息格式
        ai_messages = []
        for msg in request.messages:
            ai_msg = AIMessage(
                role=AIMessageRole(msg.role),
                content=msg.content,
                name=msg.name
            )
            ai_messages.append(ai_msg)
        
        # 转换模型配置
        ai_config = AIModelConfig(
            model=request.config.model,
            temperature=request.config.temperature,
            max_tokens=request.config.max_tokens,
            top_p=request.config.top_p,
            frequency_penalty=request.config.frequency_penalty,
            presence_penalty=request.config.presence_penalty,
            stop=request.config.stop,
            stream=request.config.stream
        )
        
        # 如果启用流式响应
        if request.config.stream:
            return StreamingResponse(
                _stream_chat_completion(
                    request,
                    ai_messages,
                    ai_config,
                    current_user,
                    ai_service,
                    conversation_service,
                    message_service
                ),
                media_type="text/plain"
            )
        
        # 非流式响应
        conversation_id = request.conversation_id
        message_id = None
        
        # 如果需要保存对话且没有提供对话ID，创建新对话
        if request.save_conversation and not conversation_id:
            conversation = await conversation_service.create_conversation(
                user_id=str(current_user.user_id),
                title="AI对话",
                model_config=request.config.dict()
            )
            conversation_id = str(conversation.conversation_id)
        
        # 如果需要保存对话，先保存用户消息
        if request.save_conversation and conversation_id:
            # 获取最后一条用户消息
            user_messages = [msg for msg in request.messages if msg.role == "user"]
            if user_messages:
                last_user_message = user_messages[-1]
                user_msg = await message_service.create_message(
                    conversation_id=conversation_id,
                    user_id=str(current_user.user_id),
                    role=MessageRole.USER,
                    content=last_user_message.content,
                    metadata={"provider_id": request.provider_id, "model": request.config.model}
                )
        
        # 调用AI服务
        ai_response = await ai_service.chat_completion(
            provider_id=request.provider_id,
            messages=ai_messages,
            config=ai_config,
            user_id=str(current_user.user_id)
        )
        
        # 如果需要保存对话，保存AI响应
        if request.save_conversation and conversation_id:
            ai_msg = await message_service.create_message(
                conversation_id=conversation_id,
                user_id=str(current_user.user_id),
                role=MessageRole.ASSISTANT,
                content=ai_response.message_content,
                metadata={
                    "provider_id": request.provider_id,
                    "model": ai_response.model,
                    "usage": ai_response.usage,
                    "response_id": ai_response.id
                }
            )
            message_id = str(ai_msg.message_id)
        
        # 计算处理时间
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # 构建响应
        response_data = ChatCompletionResponse(
            id=ai_response.id,
            object=ai_response.object,
            created=ai_response.created,
            model=ai_response.model,
            conversation_id=conversation_id,
            message_id=message_id,
            choices=ai_response.choices,
            usage=ai_response.usage,
            processing_time_ms=processing_time,
            estimated_cost_cents=int(await ai_service.get_provider(request.provider_id).estimate_cost(
                ai_response.prompt_tokens,
                ai_response.completion_tokens,
                ai_response.model
            ) * 100)
        )
        
        return ResponseHelper.success(
            data=response_data.dict(),
            message="聊天完成成功",
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
            detail="聊天完成失败"
        )


async def _stream_chat_completion(
    request: ChatCompletionRequest,
    ai_messages: List[AIMessage],
    ai_config: AIModelConfig,
    current_user: User,
    ai_service: AIService,
    conversation_service: ConversationService,
    message_service: MessageService
):
    """流式聊天完成的内部实现"""
    try:
        conversation_id = request.conversation_id
        full_response = ""
        
        # 如果需要保存对话且没有提供对话ID，创建新对话
        if request.save_conversation and not conversation_id:
            conversation = await conversation_service.create_conversation(
                user_id=str(current_user.user_id),
                title="AI对话",
                model_config=request.config.dict()
            )
            conversation_id = str(conversation.conversation_id)
        
        # 如果需要保存对话，先保存用户消息
        if request.save_conversation and conversation_id:
            user_messages = [msg for msg in request.messages if msg.role == "user"]
            if user_messages:
                last_user_message = user_messages[-1]
                await message_service.create_message(
                    conversation_id=conversation_id,
                    user_id=str(current_user.user_id),
                    role=MessageRole.USER,
                    content=last_user_message.content,
                    metadata={"provider_id": request.provider_id, "model": request.config.model}
                )
        
        # 流式调用AI服务
        async for chunk in ai_service.stream_chat_completion(
            provider_id=request.provider_id,
            messages=ai_messages,
            config=ai_config,
            user_id=str(current_user.user_id)
        ):
            # 添加对话ID到chunk
            if conversation_id:
                chunk["conversation_id"] = conversation_id
            
            # 累积响应内容
            if "choices" in chunk and len(chunk["choices"]) > 0:
                delta = chunk["choices"][0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    full_response += content
            
            # 发送chunk
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        
        # 如果需要保存对话，保存完整的AI响应
        if request.save_conversation and conversation_id and full_response:
            await message_service.create_message(
                conversation_id=conversation_id,
                user_id=str(current_user.user_id),
                role=MessageRole.ASSISTANT,
                content=full_response,
                metadata={
                    "provider_id": request.provider_id,
                    "model": request.config.model,
                    "stream": True
                }
            )
        
        # 发送结束标志
        yield "data: [DONE]\n\n"
    
    except Exception as e:
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "server_error"
            }
        }
        yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"


@router.post("/chat/quick", response_model=Dict[str, Any], summary="快速聊天")
async def quick_chat(
    request: QuickChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    快速聊天接口
    
    - 简化的聊天接口，不保存对话历史
    - 适用于一次性查询
    """
    try:
        # 构建消息
        ai_messages = [
            AIMessage(
                role=AIMessageRole.USER,
                content=request.message
            )
        ]
        
        # 构建配置
        ai_config = AIModelConfig(
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=request.stream
        )
        
        # 如果启用流式响应
        if request.stream:
            async def _quick_stream():
                async for chunk in ai_service.stream_chat_completion(
                    provider_id=request.provider_id,
                    messages=ai_messages,
                    config=ai_config,
                    user_id=str(current_user.user_id)
                ):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(_quick_stream(), media_type="text/plain")
        
        # 非流式响应
        ai_response = await ai_service.chat_completion(
            provider_id=request.provider_id,
            messages=ai_messages,
            config=ai_config,
            user_id=str(current_user.user_id)
        )
        
        return ResponseHelper.success(
            data={
                "id": ai_response.id,
                "model": ai_response.model,
                "content": ai_response.message_content,
                "usage": ai_response.usage
            },
            message="快速聊天成功",
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
            detail="快速聊天失败"
        )


@router.get("/models", response_model=Dict[str, Any], summary="获取可用模型")
async def get_available_models(
    http_request: Request,
    provider_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    获取可用的AI模型列表
    
    - 支持按供应商过滤
    - 返回模型详细信息
    """
    try:
        models = await ai_service.get_available_models(provider_id)
        
        # 转换为更详细的格式
        model_list = []
        for provider, provider_models in models.items():
            for model in provider_models:
                model_info = ModelInfo(
                    model=model,
                    provider=provider,
                    description=f"{provider}提供的{model}模型"
                )
                model_list.append(model_info.dict())
        
        return ResponseHelper.success(
            data={
                "models": model_list,
                "total_count": len(model_list),
                "providers": list(models.keys())
            },
            message="获取模型列表成功",
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
            detail="获取模型列表失败"
        )


@router.get("/providers", response_model=Dict[str, Any], summary="获取AI供应商列表")
async def get_providers(
    http_request: Request,
    current_user: User = Depends(get_current_user),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    获取可用的AI供应商列表
    
    - 返回支持的供应商信息
    """
    try:
        from services.ai_service import AIProviderFactory
        
        supported_providers = AIProviderFactory.get_supported_providers()
        
        providers_info = []
        for provider_type in supported_providers:
            providers_info.append({
                "type": provider_type.value,
                "name": provider_type.value.title(),
                "description": f"{provider_type.value.title()} AI服务供应商"
            })
        
        return ResponseHelper.success(
            data={
                "providers": providers_info,
                "total_count": len(providers_info)
            },
            message="获取供应商列表成功",
            request_id=getattr(http_request.state, 'request_id', None)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取供应商列表失败"
        )