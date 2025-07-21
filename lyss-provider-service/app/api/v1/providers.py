"""
供应商管理API

提供供应商注册、凭证管理、连接测试等功能的RESTful API接口。
支持多租户隔离和权限控制。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from app.core.security import get_current_tenant_id, get_tenant_context, TenantContext
from app.providers.registry import provider_registry
from app.models.provider import (
    ProviderResponse, 
    ProviderCredentialCreate,
    ProviderCredentialResponse,
    ProviderTestRequest,
    ProviderTestResponse
)
from app.services.provider_service import provider_service

router = APIRouter(prefix="/api/v1/providers", tags=["供应商管理"])
security = HTTPBearer()


@router.get("/", response_model=List[ProviderResponse])
async def list_providers(
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取可用供应商列表
    
    返回所有已注册的供应商信息，包括配置状态。
    
    Returns:
        List[ProviderResponse]: 供应商列表
    """
    return await provider_service.list_available_providers(tenant_context.tenant_id)


@router.post("/{provider_id}/credentials", response_model=ProviderCredentialResponse)
async def save_provider_credentials(
    provider_id: str,
    credentials: ProviderCredentialCreate,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    保存供应商凭证
    
    验证并保存租户的供应商凭证。凭证将被加密存储。
    
    Args:
        provider_id: 供应商ID
        credentials: 凭证数据
        
    Returns:
        ProviderCredentialResponse: 保存结果
        
    Raises:
        HTTPException 400: 凭证验证失败
        HTTPException 404: 供应商不存在
    """
    # 验证供应商是否存在
    if not provider_registry.get_provider(provider_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"供应商 {provider_id} 不存在"
        )
    
    # 验证凭证格式是否正确
    if credentials.provider_id != provider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请求中的供应商ID与路径不匹配"
        )
    
    result = await provider_service.save_credentials(
        provider_id=provider_id,
        credentials=credentials.credentials,
        tenant_id=tenant_context.tenant_id
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="凭证验证失败"
        )
    
    return result


@router.post("/{provider_id}/test", response_model=ProviderTestResponse)
async def test_provider_connection(
    provider_id: str,
    test_request: ProviderTestRequest,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    测试供应商连接
    
    使用提供的凭证测试与供应商的连接状况，验证凭证有效性。
    
    Args:
        provider_id: 供应商ID
        test_request: 测试请求数据
        
    Returns:
        ProviderTestResponse: 测试结果
        
    Raises:
        HTTPException 404: 供应商不存在
    """
    # 验证供应商是否存在
    if not provider_registry.get_provider(provider_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"供应商 {provider_id} 不存在"
        )
    
    # 验证请求数据
    if test_request.provider_id != provider_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请求中的供应商ID与路径不匹配"
        )
    
    result = await provider_service.test_connection(
        provider_id=provider_id,
        credentials=test_request.credentials,
        tenant_id=tenant_context.tenant_id
    )
    
    return result


@router.get("/{provider_id}/models")
async def get_provider_models(
    provider_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取供应商支持的模型列表
    
    返回指定供应商支持的所有模型信息。
    
    Args:
        provider_id: 供应商ID
        
    Returns:
        dict: 包含模型列表的响应
        
    Raises:
        HTTPException 404: 供应商不存在
    """
    # 验证供应商是否存在
    if not provider_registry.get_provider(provider_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"供应商 {provider_id} 不存在"
        )
    
    models = await provider_service.get_supported_models(
        provider_id=provider_id,
        tenant_id=tenant_context.tenant_id
    )
    
    return {"models": models}


@router.get("/{provider_id}/credentials")
async def get_provider_credentials(
    provider_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取供应商凭证状态
    
    返回租户是否已配置该供应商的凭证（不返回实际凭证内容）。
    
    Args:
        provider_id: 供应商ID
        
    Returns:
        dict: 凭证状态信息
    """
    # 验证供应商是否存在
    if not provider_registry.get_provider(provider_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"供应商 {provider_id} 不存在"
        )
    
    status_info = await provider_service.get_credential_status(
        provider_id=provider_id,
        tenant_id=tenant_context.tenant_id
    )
    
    return status_info


@router.delete("/{provider_id}/credentials")
async def delete_provider_credentials(
    provider_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    删除供应商凭证
    
    删除租户的供应商凭证配置。
    
    Args:
        provider_id: 供应商ID
        
    Returns:
        dict: 删除结果
        
    Raises:
        HTTPException 404: 供应商不存在或凭证不存在
    """
    # 验证供应商是否存在
    if not provider_registry.get_provider(provider_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"供应商 {provider_id} 不存在"
        )
    
    success = await provider_service.delete_credentials(
        provider_id=provider_id,
        tenant_id=tenant_context.tenant_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="供应商凭证不存在"
        )
    
    return {"message": "供应商凭证删除成功"}


@router.get("/{provider_id}")
async def get_provider_detail(
    provider_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context)
):
    """
    获取供应商详细信息
    
    返回指定供应商的详细配置信息和状态。
    
    Args:
        provider_id: 供应商ID
        
    Returns:
        ProviderResponse: 供应商详细信息
        
    Raises:
        HTTPException 404: 供应商不存在
    """
    provider_config = provider_registry.get_provider_config(provider_id)
    if not provider_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"供应商 {provider_id} 不存在"
        )
    
    # 检查是否已配置凭证
    credential_status = await provider_service.get_credential_status(
        provider_id=provider_id,
        tenant_id=tenant_context.tenant_id
    )
    
    return ProviderResponse(
        provider_id=provider_config.provider_id,
        name=provider_config.name,
        description=provider_config.description,
        icon=provider_config.icon,
        supported_models=[model.model_id for model in provider_config.supported_models],
        credential_schema=provider_config.credential_schema,
        is_configured=credential_status.get("is_configured", False)
    )