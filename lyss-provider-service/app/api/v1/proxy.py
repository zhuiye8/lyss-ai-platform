"""
API透明代理接口

提供OpenAI兼容的聊天完成API端点，支持标准请求和流式响应。
实现智能Channel选择和故障转移机制。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import time
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import get_tenant_context, TenantContext
from app.models.request import ChatRequest
from app.models.response import ChatResponse, ErrorResponse
from app.proxy.handler import proxy_handler

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/v1", tags=["OpenAI代理"])


@router.post("/chat/completions", response_model=ChatResponse)
async def create_chat_completion(
    request: ChatRequest,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    创建聊天完成（OpenAI兼容端点）
    
    提供与OpenAI API完全兼容的聊天完成接口，支持多种AI模型。
    自动选择最佳Channel并实现故障转移。
    
    Args:
        request: 聊天完成请求
        tenant_context: 租户上下文
        
    Returns:
        ChatResponse: 聊天完成响应（OpenAI格式）
        
    Raises:
        HTTPException 400: 请求参数无效
        HTTPException 429: 请求频率过高
        HTTPException 502: 上游服务错误
        HTTPException 503: 服务不可用
    """
    try:
        logger.info(
            f"收到聊天完成请求 - 租户: {tenant_context.tenant_id}, "
            f"模型: {request.model}, 消息数: {len(request.messages)}"
        )
        
        # 验证请求参数
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息列表不能为空"
            )
        
        if request.stream:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="流式请求请使用SSE端点"
            )
        
        # 处理聊天完成请求
        response = await proxy_handler.handle_chat_completion(
            request=request,
            tenant_id=tenant_context.tenant_id
        )
        
        logger.info(
            f"聊天完成响应成功 - ID: {response.id}, "
            f"Token使用: {response.usage.total_tokens}"
        )
        
        return response
        
    except ValueError as e:
        logger.warning(f"请求参数错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"聊天完成请求处理失败: {e}")
        
        # 根据错误类型返回适当的HTTP状态码
        if "没有可用的Channel" in str(e):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="当前没有可用的AI服务，请稍后重试"
            )
        elif "请求频率" in str(e):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="请求频率过高，请稍后重试"
            )
        elif "供应商API错误" in str(e):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="上游AI服务错误，请稍后重试"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="内部服务错误，请联系管理员"
            )


@router.post("/chat/completions/stream")
async def create_stream_chat_completion(
    request: ChatRequest,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    创建流式聊天完成
    
    提供Server-Sent Events格式的流式聊天完成接口。
    支持实时流式响应和智能故障转移。
    
    Args:
        request: 聊天完成请求
        tenant_context: 租户上下文
        
    Returns:
        StreamingResponse: 流式响应（SSE格式）
    """
    try:
        logger.info(
            f"收到流式聊天完成请求 - 租户: {tenant_context.tenant_id}, "
            f"模型: {request.model}, 消息数: {len(request.messages)}"
        )
        
        # 验证请求参数
        if not request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="消息列表不能为空"
            )
        
        # 强制启用流式响应
        request.stream = True
        
        # 创建流式响应生成器
        async def generate_stream():
            try:
                async for chunk in proxy_handler.handle_stream_chat_completion(
                    request=request,
                    tenant_id=tenant_context.tenant_id
                ):
                    yield chunk
                    
            except Exception as e:
                logger.error(f"流式响应生成失败: {e}")
                # 发送错误消息到流
                error_data = {
                    "error": {
                        "message": str(e),
                        "type": "stream_error", 
                        "code": "processing_failed"
                    }
                }
                yield f"data: {ErrorResponse(**error_data).json()}\n\n"
        
        # 返回Server-Sent Events响应
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Encoding": "identity"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式聊天完成请求处理失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"流式请求处理失败: {str(e)}"
        )


@router.get("/models")
async def list_models(
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取可用模型列表（OpenAI兼容端点）
    
    返回当前租户可用的所有AI模型列表，格式与OpenAI API兼容。
    
    Args:
        tenant_context: 租户上下文
        
    Returns:
        dict: 可用模型列表（OpenAI格式）
    """
    try:
        from app.channels.manager import channel_manager
        
        # 获取租户的所有活跃Channel
        channels = channel_manager.list_tenant_channels(tenant_context.tenant_id)
        active_channels = [ch for ch in channels if ch.status == "active"]
        
        # 收集所有可用模型
        models = []
        model_set = set()
        
        for channel in active_channels:
            for model_name in channel.models:
                if model_name not in model_set:
                    models.append({
                        "id": model_name,
                        "object": "model",
                        "created": int(channel.created_at.timestamp()) if channel.created_at else 0,
                        "owned_by": channel.provider_id,
                        "permission": [],
                        "root": model_name,
                        "parent": None
                    })
                    model_set.add(model_name)
        
        # 按模型名称排序
        models.sort(key=lambda x: x["id"])
        
        return {
            "object": "list",
            "data": models
        }
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模型列表失败"
        )


@router.get("/models/{model_id}")
async def retrieve_model(
    model_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取指定模型详情（OpenAI兼容端点）
    
    Args:
        model_id: 模型ID
        tenant_context: 租户上下文
        
    Returns:
        dict: 模型详情（OpenAI格式）
        
    Raises:
        HTTPException 404: 模型不存在
    """
    try:
        from app.channels.manager import channel_manager
        
        # 查找提供该模型的Channel
        channels = channel_manager.list_tenant_channels(tenant_context.tenant_id)
        
        for channel in channels:
            if model_id in channel.models and channel.status == "active":
                return {
                    "id": model_id,
                    "object": "model",
                    "created": int(channel.created_at.timestamp()) if channel.created_at else 0,
                    "owned_by": channel.provider_id,
                    "permission": [],
                    "root": model_id,
                    "parent": None
                }
        
        # 模型不存在
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"模型 {model_id} 不存在或不可用"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取模型详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取模型详情失败"
        )


@router.get("/health")
async def proxy_health_check():
    """
    代理服务健康检查
    
    检查代理服务的运行状态和基础功能。
    
    Returns:
        dict: 健康状态信息
    """
    try:
        from app.channels.manager import channel_manager
        
        # 检查Channel管理器状态
        total_channels = len(channel_manager.channels)
        healthy_channels = 0
        
        for metrics in channel_manager.channel_metrics.values():
            if metrics.health_status == "healthy":
                healthy_channels += 1
        
        # 计算服务健康度
        service_health = "healthy"
        if total_channels == 0:
            service_health = "no_channels"
        elif healthy_channels == 0:
            service_health = "unhealthy"
        elif healthy_channels / total_channels < 0.5:
            service_health = "degraded"
        
        return {
            "status": service_health,
            "timestamp": int(time.time()),
            "version": "1.0.0",
            "channels": {
                "total": total_channels,
                "healthy": healthy_channels,
                "health_ratio": healthy_channels / total_channels if total_channels > 0 else 0
            },
            "proxy_handler": {
                "status": "active",
                "http_client": "connected"
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "timestamp": int(time.time()),
            "error": str(e)
        }


# 为了兼容性，也提供不带版本前缀的端点
@router.post("/chat/completions", include_in_schema=False)
async def create_chat_completion_compat(
    request: ChatRequest,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """OpenAI兼容端点（无版本前缀）"""
    return await create_chat_completion(request, tenant_context)


@router.post("/chat/completions/stream", include_in_schema=False) 
async def create_stream_chat_completion_compat(
    request: ChatRequest,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """流式聊天完成兼容端点（无版本前缀）"""
    return await create_stream_chat_completion(request, tenant_context)