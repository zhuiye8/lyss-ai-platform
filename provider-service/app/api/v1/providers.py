"""
供应商管理API

提供供应商注册、配置管理、连接测试等功能的RESTful API接口。
支持多租户隔离和权限控制。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...services.provider_service import ProviderService
from ...models.schemas.provider import (
    ProviderResponse,
    ProviderCreateRequest,
    ProviderUpdateRequest,
    ProviderTestRequest,
    ProviderCredentialsRequest
)
from ...models.schemas.common import StandardResponse

router = APIRouter(prefix="/providers", tags=["供应商管理"])


def get_provider_service(db: Session = Depends(get_db)) -> ProviderService:
    """依赖注入：获取供应商服务实例"""
    return ProviderService(db)


@router.get("/", response_model=StandardResponse[List[Dict[str, Any]]])
def list_providers(
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    获取所有供应商列表
    
    Returns:
        StandardResponse[List[Dict[str, Any]]]: 供应商列表
    """
    try:
        providers = provider_service.get_all_providers()
        
        provider_list = []
        for provider in providers:
            provider_dict = {
                "id": provider.id,
                "provider_id": provider.provider_id,
                "name": provider.name,
                "description": provider.description,
                "status": provider.status,
                "api_base": provider.api_base,
                "supported_models": provider.supported_models,
                "priority": provider.priority,
                "weight": provider.weight,
                "created_at": provider.created_at.isoformat(),
                "updated_at": provider.updated_at.isoformat()
            }
            provider_list.append(provider_dict)
        
        return StandardResponse(
            success=True,
            data=provider_list,
            message=f"成功获取 {len(provider_list)} 个供应商"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取供应商列表失败: {str(e)}"
        )


@router.get("/{provider_id}", response_model=StandardResponse[Dict[str, Any]])
def get_provider(
    provider_id: str,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    获取指定供应商详情
    
    Args:
        provider_id: 供应商ID
        
    Returns:
        StandardResponse[Dict[str, Any]]: 供应商详情
    """
    try:
        provider = provider_service.get_provider_by_id(provider_id)
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"供应商 {provider_id} 不存在"
            )
        
        provider_dict = {
            "id": provider.id,
            "provider_id": provider.provider_id,
            "name": provider.name,
            "description": provider.description,
            "status": provider.status,
            "api_base": provider.api_base,
            "supported_models": provider.supported_models,
            "priority": provider.priority,
            "weight": provider.weight,
            "config": provider.config,
            "created_at": provider.created_at.isoformat(),
            "updated_at": provider.updated_at.isoformat()
        }
        
        return StandardResponse(
            success=True,
            data=provider_dict,
            message="成功获取供应商详情"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取供应商详情失败: {str(e)}"
        )


@router.post("/", response_model=StandardResponse[Dict[str, Any]])
def create_provider(
    request: ProviderCreateRequest,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    创建新的供应商配置
    
    Args:
        request: 供应商创建请求
        
    Returns:
        StandardResponse[Dict[str, Any]]: 创建的供应商信息
    """
    try:
        # 验证供应商配置
        is_valid, errors = provider_service.validate_provider_config(request.dict())
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"供应商配置验证失败: {', '.join(errors)}"
            )
        
        # 检查供应商ID是否已存在
        existing_provider = provider_service.get_provider_by_id(request.provider_id)
        if existing_provider:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"供应商ID {request.provider_id} 已存在"
            )
        
        # 创建供应商
        provider = provider_service.create_provider_config(request.dict())
        
        provider_dict = {
            "id": provider.id,
            "provider_id": provider.provider_id,
            "name": provider.name,
            "description": provider.description,
            "status": provider.status,
            "api_base": provider.api_base,
            "supported_models": provider.supported_models,
            "created_at": provider.created_at.isoformat(),
            "updated_at": provider.updated_at.isoformat()
        }
        
        return StandardResponse(
            success=True,
            data=provider_dict,
            message=f"成功创建供应商 {provider.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建供应商失败: {str(e)}"
        )


@router.put("/{provider_id}", response_model=StandardResponse[Dict[str, Any]])
def update_provider(
    provider_id: str,
    request: ProviderUpdateRequest,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    更新供应商配置
    
    Args:
        provider_id: 供应商ID
        request: 更新请求
        
    Returns:
        StandardResponse[Dict[str, Any]]: 更新后的供应商信息
    """
    try:
        # 验证更新数据
        update_data = request.dict(exclude_unset=True)
        if update_data:
            is_valid, errors = provider_service.validate_provider_config(update_data)
            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"供应商配置验证失败: {', '.join(errors)}"
                )
        
        # 更新供应商
        updated_provider = provider_service.update_provider_config(provider_id, update_data)
        
        if not updated_provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"供应商 {provider_id} 不存在"
            )
        
        provider_dict = {
            "id": updated_provider.id,
            "provider_id": updated_provider.provider_id,
            "name": updated_provider.name,
            "description": updated_provider.description,
            "status": updated_provider.status,
            "api_base": updated_provider.api_base,
            "supported_models": updated_provider.supported_models,
            "priority": updated_provider.priority,
            "weight": updated_provider.weight,
            "updated_at": updated_provider.updated_at.isoformat()
        }
        
        return StandardResponse(
            success=True,
            data=provider_dict,
            message=f"成功更新供应商 {updated_provider.name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新供应商失败: {str(e)}"
        )


@router.delete("/{provider_id}", response_model=StandardResponse[None])
def delete_provider(
    provider_id: str,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    删除供应商配置
    
    Args:
        provider_id: 供应商ID
        
    Returns:
        StandardResponse[None]: 删除结果
    """
    try:
        success = provider_service.delete_provider_config(provider_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"供应商 {provider_id} 不存在"
            )
        
        return StandardResponse(
            success=True,
            message=f"成功删除供应商 {provider_id}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除供应商失败: {str(e)}"
        )


@router.patch("/{provider_id}/status", response_model=StandardResponse[None])
def update_provider_status(
    provider_id: str,
    status_value: str = Query(..., description="新状态值"),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    更新供应商状态
    
    Args:
        provider_id: 供应商ID
        status_value: 新状态值 (active/inactive/disabled)
        
    Returns:
        StandardResponse[None]: 更新结果
    """
    try:
        # 验证状态值
        valid_statuses = ['active', 'inactive', 'disabled']
        if status_value not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值。有效值: {', '.join(valid_statuses)}"
            )
        
        success = provider_service.update_provider_status(provider_id, status_value)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"供应商 {provider_id} 不存在"
            )
        
        return StandardResponse(
            success=True,
            message=f"成功更新供应商 {provider_id} 状态为 {status_value}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新供应商状态失败: {str(e)}"
        )


@router.post("/{provider_id}/test", response_model=StandardResponse[Dict[str, Any]])
async def test_provider_connection(
    provider_id: str,
    request: ProviderTestRequest,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    测试供应商连接
    
    Args:
        provider_id: 供应商ID
        request: 测试请求
        
    Returns:
        StandardResponse[Dict[str, Any]]: 测试结果
    """
    try:
        # 验证供应商存在
        provider = provider_service.get_provider_by_id(provider_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"供应商 {provider_id} 不存在"
            )
        
        # 执行连接测试
        test_result = await provider_service.test_provider_connection(
            provider_id, 
            request.credentials,
            request.test_model
        )
        
        return StandardResponse(
            success=test_result["success"],
            data=test_result,
            message=test_result.get("message", "连接测试完成")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"测试供应商连接失败: {str(e)}"
        )


@router.get("/{provider_id}/models", response_model=StandardResponse[List[str]])
def get_provider_models(
    provider_id: str,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    获取供应商支持的模型列表
    
    Args:
        provider_id: 供应商ID
        
    Returns:
        StandardResponse[List[str]]: 模型列表
    """
    try:
        models = provider_service.get_supported_models(provider_id)
        
        return StandardResponse(
            success=True,
            data=models,
            message=f"成功获取供应商 {provider_id} 的 {len(models)} 个支持模型"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取供应商模型列表失败: {str(e)}"
        )


@router.post("/{provider_id}/models/{model_name}", response_model=StandardResponse[None])
def add_provider_model(
    provider_id: str,
    model_name: str,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    为供应商添加支持的模型
    
    Args:
        provider_id: 供应商ID
        model_name: 模型名称
        
    Returns:
        StandardResponse[None]: 添加结果
    """
    try:
        success = provider_service.add_supported_model(provider_id, model_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"供应商 {provider_id} 不存在"
            )
        
        return StandardResponse(
            success=True,
            message=f"成功为供应商 {provider_id} 添加模型 {model_name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"添加供应商模型失败: {str(e)}"
        )


@router.delete("/{provider_id}/models/{model_name}", response_model=StandardResponse[None])
def remove_provider_model(
    provider_id: str,
    model_name: str,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    移除供应商支持的模型
    
    Args:
        provider_id: 供应商ID
        model_name: 模型名称
        
    Returns:
        StandardResponse[None]: 移除结果
    """
    try:
        success = provider_service.remove_supported_model(provider_id, model_name)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"供应商 {provider_id} 不存在或模型 {model_name} 不在支持列表中"
            )
        
        return StandardResponse(
            success=True,
            message=f"成功从供应商 {provider_id} 移除模型 {model_name}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除供应商模型失败: {str(e)}"
        )


@router.get("/models/all", response_model=StandardResponse[List[str]])
def get_all_supported_models(
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    获取所有供应商支持的模型列表（去重）
    
    Returns:
        StandardResponse[List[str]]: 模型列表
    """
    try:
        models = provider_service.get_all_supported_models()
        
        return StandardResponse(
            success=True,
            data=models,
            message=f"成功获取 {len(models)} 个支持的模型"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取所有支持模型失败: {str(e)}"
        )


@router.get("/models/{model_name}/providers", response_model=StandardResponse[List[Dict[str, Any]]])
def get_providers_by_model(
    model_name: str,
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    获取支持指定模型的供应商列表
    
    Args:
        model_name: 模型名称
        
    Returns:
        StandardResponse[List[Dict[str, Any]]]: 支持该模型的供应商列表
    """
    try:
        providers = provider_service.get_providers_by_model(model_name)
        
        provider_list = []
        for provider in providers:
            provider_dict = {
                "id": provider.id,
                "provider_id": provider.provider_id,
                "name": provider.name,
                "description": provider.description,
                "status": provider.status,
                "priority": provider.priority,
                "weight": provider.weight
            }
            provider_list.append(provider_dict)
        
        return StandardResponse(
            success=True,
            data=provider_list,
            message=f"成功获取支持模型 {model_name} 的 {len(provider_list)} 个供应商"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取支持模型的供应商失败: {str(e)}"
        )


@router.get("/statistics", response_model=StandardResponse[Dict[str, Any]])
def get_provider_statistics(
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    获取供应商统计信息
    
    Returns:
        StandardResponse[Dict[str, Any]]: 统计信息
    """
    try:
        stats = provider_service.get_provider_statistics()
        
        return StandardResponse(
            success=True,
            data=stats,
            message="成功获取供应商统计信息"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取供应商统计信息失败: {str(e)}"
        )


@router.get("/search", response_model=StandardResponse[List[Dict[str, Any]]])
def search_providers(
    q: str = Query(..., description="搜索关键词"),
    provider_service: ProviderService = Depends(get_provider_service)
):
    """
    搜索供应商
    
    Args:
        q: 搜索关键词
        
    Returns:
        StandardResponse[List[Dict[str, Any]]]: 匹配的供应商列表
    """
    try:
        providers = provider_service.search_providers(q)
        
        provider_list = []
        for provider in providers:
            provider_dict = {
                "id": provider.id,
                "provider_id": provider.provider_id,
                "name": provider.name,
                "description": provider.description,
                "status": provider.status,
                "supported_models": provider.supported_models
            }
            provider_list.append(provider_dict)
        
        return StandardResponse(
            success=True,
            data=provider_list,
            message=f"搜索到 {len(provider_list)} 个匹配的供应商"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"搜索供应商失败: {str(e)}"
        )