"""
Channel管理API

提供Channel的创建、查询、更新、删除等功能的RESTful API接口。
实现智能负载均衡和健康监控功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_tenant_context, TenantContext
from app.channels.manager import channel_manager
from app.models.channel import (
    ChannelCreateRequest, 
    ChannelResponse, 
    ChannelStatusResponse,
    ChannelUpdateRequest
)

router = APIRouter(prefix="/api/v1/channels", tags=["Channel管理"])


@router.get("/", response_model=List[ChannelResponse])
async def list_channels(
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取租户的Channel列表
    
    返回当前租户下所有已配置的Channel信息。
    
    Returns:
        List[ChannelResponse]: Channel列表
    """
    return channel_manager.list_tenant_channels(tenant_context.tenant_id)


@router.post("/", response_model=ChannelResponse)
async def create_channel(
    channel_data: ChannelCreateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    创建新Channel
    
    为租户创建一个新的Channel，用于访问指定的AI供应商。
    
    Args:
        channel_data: Channel创建数据
        
    Returns:
        ChannelResponse: 创建的Channel信息
        
    Raises:
        HTTPException 400: 创建失败（供应商不存在、凭证无效等）
    """
    try:
        channel_id = await channel_manager.register_channel(
            channel_data, 
            tenant_context.tenant_id
        )
        
        # 获取创建的Channel信息
        channel = channel_manager.get_channel(channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Channel创建成功但无法获取详情"
            )
        
        # 构建响应
        from app.providers.registry import provider_registry
        provider_config = provider_registry.get_provider_config(channel.provider_id)
        provider_name = provider_config.name if provider_config else channel.provider_id
        
        return ChannelResponse(
            id=channel.id,
            name=channel.name,
            provider_id=channel.provider_id,
            provider_name=provider_name,
            base_url=channel.base_url,
            models=channel.models,
            status=channel.status,
            health="unknown",  # 新创建的Channel健康状态未知
            priority=channel.priority,
            weight=channel.weight,
            max_requests_per_minute=channel.max_requests_per_minute,
            created_at=channel.created_at or "",
            updated_at=channel.updated_at or ""
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建Channel失败: {str(e)}"
        )


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取Channel详情
    
    返回指定Channel的详细信息。
    
    Args:
        channel_id: Channel ID
        
    Returns:
        ChannelResponse: Channel详细信息
        
    Raises:
        HTTPException 404: Channel不存在或无权限访问
    """
    channel = channel_manager.get_channel(channel_id)
    
    if not channel or channel.tenant_id != tenant_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Channel不存在"
        )
    
    # 获取供应商名称和健康状态
    from app.providers.registry import provider_registry
    provider_config = provider_registry.get_provider_config(channel.provider_id)
    provider_name = provider_config.name if provider_config else channel.provider_id
    
    metrics = channel_manager.channel_metrics.get(channel_id)
    health_status = metrics.health_status if metrics else "unknown"
    
    return ChannelResponse(
        id=channel.id,
        name=channel.name,
        provider_id=channel.provider_id,
        provider_name=provider_name,
        base_url=channel.base_url,
        models=channel.models,
        status=channel.status,
        health=health_status,
        priority=channel.priority,
        weight=channel.weight,
        max_requests_per_minute=channel.max_requests_per_minute,
        created_at=channel.created_at or "",
        updated_at=channel.updated_at or ""
    )


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    update_data: ChannelUpdateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    更新Channel配置
    
    更新指定Channel的配置信息。
    
    Args:
        channel_id: Channel ID
        update_data: 更新数据
        
    Returns:
        ChannelResponse: 更新后的Channel信息
        
    Raises:
        HTTPException 404: Channel不存在
        HTTPException 400: 更新失败
    """
    # 验证Channel是否存在且属于当前租户
    channel = channel_manager.get_channel(channel_id)
    if not channel or channel.tenant_id != tenant_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel不存在"
        )
    
    # 转换更新数据
    update_dict = {}
    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            update_dict[field] = value
    
    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供需要更新的字段"
        )
    
    # 执行更新
    success = await channel_manager.update_channel(
        channel_id=channel_id,
        update_data=update_dict,
        tenant_id=tenant_context.tenant_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel更新失败"
        )
    
    # 返回更新后的Channel信息
    updated_channel = channel_manager.get_channel(channel_id)
    from app.providers.registry import provider_registry
    provider_config = provider_registry.get_provider_config(updated_channel.provider_id)
    provider_name = provider_config.name if provider_config else updated_channel.provider_id
    
    metrics = channel_manager.channel_metrics.get(channel_id)
    health_status = metrics.health_status if metrics else "unknown"
    
    return ChannelResponse(
        id=updated_channel.id,
        name=updated_channel.name,
        provider_id=updated_channel.provider_id,
        provider_name=provider_name,
        base_url=updated_channel.base_url,
        models=updated_channel.models,
        status=updated_channel.status,
        health=health_status,
        priority=updated_channel.priority,
        weight=updated_channel.weight,
        max_requests_per_minute=updated_channel.max_requests_per_minute,
        created_at=updated_channel.created_at or "",
        updated_at=updated_channel.updated_at or ""
    )


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    删除Channel
    
    删除指定的Channel配置。
    
    Args:
        channel_id: Channel ID
        
    Returns:
        dict: 删除结果
        
    Raises:
        HTTPException 404: Channel不存在
    """
    success = await channel_manager.delete_channel(channel_id, tenant_context.tenant_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel不存在"
        )
    
    return {"message": "Channel删除成功"}


@router.get("/status/overview")
async def get_channels_status(
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取Channel状态概览
    
    返回租户所有Channel的状态统计信息。
    
    Returns:
        dict: Channel状态概览
    """
    channel_status = channel_manager.get_channel_status(tenant_context.tenant_id)
    
    # 统计信息
    total_channels = len(channel_status)
    healthy_channels = sum(1 for status in channel_status.values() if status.health == "healthy")
    unhealthy_channels = sum(1 for status in channel_status.values() if status.health == "unhealthy")
    active_channels = sum(1 for status in channel_status.values() if status.status == "active")
    
    # 平均响应时间
    avg_response_time = 0
    if channel_status:
        total_response_time = sum(status.response_time for status in channel_status.values())
        avg_response_time = total_response_time / len(channel_status)
    
    # 总成功率
    total_requests = sum(status.request_count for status in channel_status.values())
    total_errors = sum(status.error_count for status in channel_status.values())
    overall_success_rate = 1.0
    if total_requests > 0:
        overall_success_rate = (total_requests - total_errors) / total_requests
    
    return {
        "summary": {
            "total_channels": total_channels,
            "active_channels": active_channels,
            "healthy_channels": healthy_channels,
            "unhealthy_channels": unhealthy_channels,
            "average_response_time": round(avg_response_time, 2),
            "overall_success_rate": round(overall_success_rate, 4),
            "total_requests": total_requests,
            "total_errors": total_errors
        },
        "channels": list(channel_status.values())
    }


@router.post("/{channel_id}/test")
async def test_channel(
    channel_id: int,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    测试Channel连接
    
    手动触发指定Channel的连接测试。
    
    Args:
        channel_id: Channel ID
        
    Returns:
        dict: 测试结果
        
    Raises:
        HTTPException 404: Channel不存在
    """
    channel = channel_manager.get_channel(channel_id)
    if not channel or channel.tenant_id != tenant_context.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel不存在"
        )
    
    # 执行健康检查
    await channel_manager._check_channel_health(channel_id)
    
    # 获取最新的指标
    metrics = channel_manager.channel_metrics.get(channel_id)
    
    return {
        "channel_id": channel_id,
        "channel_name": channel.name,
        "health_status": metrics.health_status if metrics else "unknown",
        "response_time": metrics.response_time if metrics else 0,
        "success_rate": metrics.success_rate if metrics else 0,
        "test_time": channel_manager.channels[channel_id].updated_at
    }