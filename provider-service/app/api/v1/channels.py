"""
渠道管理API

提供渠道的创建、查询、更新、删除等功能的RESTful API接口。
集成智能负载均衡和健康监控功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.security import get_tenant_context, TenantContext
from ...core.database import get_db
from ...services.channel_service import ChannelService
from ...services.health_check_service import HealthCheckService
from ...models.schemas.channel import (
    ChannelCreateRequest, 
    ChannelUpdateRequest,
    ChannelResponse
)
from ...models.schemas.common import StandardResponse

router = APIRouter(prefix="/channels", tags=["渠道管理"])


def get_channel_service(db: Session = Depends(get_db)) -> ChannelService:
    """依赖注入：获取渠道服务实例"""
    return ChannelService(db)


def get_health_service(db: Session = Depends(get_db)) -> HealthCheckService:
    """依赖注入：获取健康检查服务实例"""
    return HealthCheckService(db)


@router.get("/", response_model=StandardResponse[List[Dict[str, Any]]])
def list_channels(
    tenant_context: TenantContext = Depends(get_tenant_context),
    channel_service: ChannelService = Depends(get_channel_service)
):
    """
    获取租户的渠道列表
    
    返回当前租户下所有已配置的渠道信息。
    
    Returns:
        StandardResponse[List[Dict[str, Any]]]: 渠道列表
    """
    try:
        channels = channel_service.get_active_channels(tenant_context.tenant_id)
        
        channel_list = []
        for channel in channels:
            channel_dict = {
                "channel_id": channel.channel_id,
                "name": channel.name,
                "provider_id": channel.provider_id,
                "status": channel.status,
                "supported_models": channel.supported_models,
                "api_base": channel.api_base,
                "priority": channel.priority,
                "weight": channel.weight,
                "max_requests_per_minute": channel.max_requests_per_minute,
                "success_rate": channel.success_rate,
                "response_time": channel.response_time,
                "created_at": channel.created_at.isoformat() if channel.created_at else None,
                "updated_at": channel.updated_at.isoformat() if channel.updated_at else None
            }
            channel_list.append(channel_dict)
        
        return StandardResponse(
            success=True,
            data=channel_list,
            message=f"成功获取 {len(channel_list)} 个渠道"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道列表失败: {str(e)}"
        )


@router.post("/", response_model=StandardResponse[Dict[str, Any]])
def create_channel(
    channel_data: ChannelCreateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    channel_service: ChannelService = Depends(get_channel_service)
):
    """
    创建新渠道
    
    为租户创建一个新的渠道，用于访问指定的AI供应商。
    
    Args:
        channel_data: 渠道创建数据
        
    Returns:
        StandardResponse[Dict[str, Any]]: 创建的渠道信息
        
    Raises:
        HTTPException 400: 创建失败（供应商不存在、凭证无效等）
    """
    try:
        # 创建渠道数据
        create_data = channel_data.dict()
        create_data["tenant_id"] = tenant_context.tenant_id
        
        # 创建渠道
        channel = channel_service.create_channel(create_data)
        
        channel_dict = {
            "channel_id": channel.channel_id,
            "name": channel.name,
            "provider_id": channel.provider_id,
            "status": channel.status,
            "supported_models": channel.supported_models,
            "api_base": channel.api_base,
            "priority": channel.priority,
            "weight": channel.weight,
            "max_requests_per_minute": channel.max_requests_per_minute,
            "created_at": channel.created_at.isoformat() if channel.created_at else None
        }
        
        return StandardResponse(
            success=True,
            data=channel_dict,
            message=f"成功创建渠道 {channel.name}"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建渠道失败: {str(e)}"
        )


@router.get("/{channel_id}", response_model=StandardResponse[Dict[str, Any]])
def get_channel(
    channel_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
    channel_service: ChannelService = Depends(get_channel_service)
):
    """
    获取渠道详情
    
    返回指定渠道的详细信息。
    
    Args:
        channel_id: 渠道ID
        
    Returns:
        StandardResponse[Dict[str, Any]]: 渠道详细信息
        
    Raises:
        HTTPException 404: 渠道不存在或无权限访问
    """
    try:
        channel = channel_service.get_channel(channel_id, tenant_context.tenant_id)
        
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="渠道不存在"
            )
        
        channel_dict = {
            "channel_id": channel.channel_id,
            "name": channel.name,
            "provider_id": channel.provider_id,
            "status": channel.status,
            "supported_models": channel.supported_models,
            "api_base": channel.api_base,
            "priority": channel.priority,
            "weight": channel.weight,
            "max_requests_per_minute": channel.max_requests_per_minute,
            "success_rate": channel.success_rate,
            "response_time": channel.response_time,
            "current_requests_per_minute": channel.current_requests_per_minute,
            "created_at": channel.created_at.isoformat() if channel.created_at else None,
            "updated_at": channel.updated_at.isoformat() if channel.updated_at else None
        }
        
        return StandardResponse(
            success=True,
            data=channel_dict,
            message="成功获取渠道详情"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道详情失败: {str(e)}"
        )


@router.put("/{channel_id}", response_model=StandardResponse[Dict[str, Any]])
def update_channel(
    channel_id: str,
    update_data: ChannelUpdateRequest,
    tenant_context: TenantContext = Depends(get_tenant_context),
    channel_service: ChannelService = Depends(get_channel_service)
):
    """
    更新渠道配置
    
    更新指定渠道的配置信息。
    
    Args:
        channel_id: 渠道ID
        update_data: 更新数据
        
    Returns:
        StandardResponse[Dict[str, Any]]: 更新后的渠道信息
        
    Raises:
        HTTPException 404: 渠道不存在
        HTTPException 400: 更新失败
    """
    try:
        # 验证渠道存在且属于当前租户
        channel = channel_service.get_channel(channel_id, tenant_context.tenant_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="渠道不存在"
            )
        
        # 转换更新数据
        update_dict = update_data.dict(exclude_unset=True)
        
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供需要更新的字段"
            )
        
        # 执行更新
        updated_channel = channel_service.update_channel(
            channel_id=channel_id,
            tenant_id=tenant_context.tenant_id,
            update_data=update_dict
        )
        
        if not updated_channel:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="渠道更新失败"
            )
        
        channel_dict = {
            "channel_id": updated_channel.channel_id,
            "name": updated_channel.name,
            "provider_id": updated_channel.provider_id,
            "status": updated_channel.status,
            "supported_models": updated_channel.supported_models,
            "api_base": updated_channel.api_base,
            "priority": updated_channel.priority,
            "weight": updated_channel.weight,
            "max_requests_per_minute": updated_channel.max_requests_per_minute,
            "updated_at": updated_channel.updated_at.isoformat() if updated_channel.updated_at else None
        }
        
        return StandardResponse(
            success=True,
            data=channel_dict,
            message=f"成功更新渠道 {updated_channel.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新渠道失败: {str(e)}"
        )


@router.delete("/{channel_id}", response_model=StandardResponse[None])
def delete_channel(
    channel_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
    channel_service: ChannelService = Depends(get_channel_service)
):
    """
    删除渠道
    
    删除指定的渠道配置。
    
    Args:
        channel_id: 渠道ID
        
    Returns:
        StandardResponse[None]: 删除结果
        
    Raises:
        HTTPException 404: 渠道不存在
    """
    try:
        success = channel_service.delete_channel(channel_id, tenant_context.tenant_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="渠道不存在"
            )
        
        return StandardResponse(
            success=True,
            message="渠道删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除渠道失败: {str(e)}"
        )


@router.get("/status/overview", response_model=StandardResponse[Dict[str, Any]])
def get_channels_status(
    tenant_context: TenantContext = Depends(get_tenant_context),
    channel_service: ChannelService = Depends(get_channel_service),
    health_service: HealthCheckService = Depends(get_health_service)
):
    """
    获取渠道状态概览
    
    返回租户所有渠道的状态统计信息。
    
    Returns:
        StandardResponse[Dict[str, Any]]: 渠道状态概览
    """
    try:
        # 获取渠道列表
        channels = channel_service.get_all_tenant_channels(tenant_context.tenant_id)
        
        # 统计信息
        total_channels = len(channels)
        active_channels = sum(1 for ch in channels if ch.status == "active")
        healthy_channels = 0
        total_response_time = 0
        total_requests = 0
        total_errors = 0
        
        channel_details = []
        
        for channel in channels:
            # 获取健康状态
            health_status = health_service.get_channel_health_status(channel.channel_id)
            is_healthy = health_status.get("status") == "healthy"
            
            if is_healthy:
                healthy_channels += 1
            
            # 累计统计数据
            total_response_time += channel.response_time or 0
            # 这里应该从metrics获取实际的请求和错误数据
            # 暂时使用模拟数据
            
            channel_detail = {
                "channel_id": channel.channel_id,
                "name": channel.name,
                "provider_id": channel.provider_id,
                "status": channel.status,
                "health": "healthy" if is_healthy else "unhealthy",
                "success_rate": channel.success_rate or 0.0,
                "response_time": channel.response_time or 0.0,
                "current_requests": channel.current_requests_per_minute or 0
            }
            channel_details.append(channel_detail)
        
        # 计算平均响应时间
        avg_response_time = (total_response_time / total_channels) if total_channels > 0 else 0
        
        # 计算总成功率
        overall_success_rate = 1.0
        if total_requests > 0:
            overall_success_rate = (total_requests - total_errors) / total_requests
        
        summary = {
            "total_channels": total_channels,
            "active_channels": active_channels,
            "healthy_channels": healthy_channels,
            "unhealthy_channels": total_channels - healthy_channels,
            "average_response_time": round(avg_response_time, 2),
            "overall_success_rate": round(overall_success_rate, 4),
            "total_requests": total_requests,
            "total_errors": total_errors
        }
        
        return StandardResponse(
            success=True,
            data={
                "summary": summary,
                "channels": channel_details
            },
            message="成功获取渠道状态概览"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取渠道状态失败: {str(e)}"
        )


@router.post("/{channel_id}/test", response_model=StandardResponse[Dict[str, Any]])
async def test_channel_connection(
    channel_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
    channel_service: ChannelService = Depends(get_channel_service),
    health_service: HealthCheckService = Depends(get_health_service)
):
    """
    测试渠道连接
    
    手动触发指定渠道的连接测试。
    
    Args:
        channel_id: 渠道ID
        
    Returns:
        StandardResponse[Dict[str, Any]]: 测试结果
        
    Raises:
        HTTPException 404: 渠道不存在
    """
    try:
        # 验证渠道存在且属于当前租户
        channel = channel_service.get_channel(channel_id, tenant_context.tenant_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="渠道不存在"
            )
        
        # 执行健康检查
        test_result = await health_service.check_channel_health(channel_id, force_check=True)
        
        return StandardResponse(
            success=True,
            data={
                "channel_id": channel_id,
                "channel_name": channel.name,
                "test_result": test_result
            },
            message="渠道连接测试完成"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试渠道连接失败: {str(e)}"
        )