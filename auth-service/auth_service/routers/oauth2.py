"""
OAuth2联邦认证路由

提供OAuth2授权流程的完整API接口：
- 获取支持的OAuth2提供商列表
- 生成OAuth2授权URL
- 处理OAuth2回调
- OAuth2用户注册和登录

支持Google、GitHub、Microsoft等主流OAuth2提供商。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import RedirectResponse

from ..models.auth_models import (
    OAuth2AuthorizeRequest, OAuth2AuthorizeResponse,
    OAuth2CallbackRequest, OAuth2LoginResponse,
    OAuth2ProvidersResponse, ApiResponse
)
from ..core.oauth2_manager import OAuth2Manager, OAuth2Provider
from ..dependencies import OAuth2ManagerDep, AuthManagerDep, JWTManagerDep
from ..utils.logging import get_logger

router = APIRouter(prefix="/api/v1/auth/oauth2", tags=["OAuth2联邦认证"])
logger = get_logger(__name__)


@router.get("/providers", response_model=OAuth2ProvidersResponse, summary="获取OAuth2提供商列表")
async def get_oauth2_providers(oauth2_manager: OAuth2ManagerDep):
    """
    获取支持的OAuth2提供商列表
    
    Returns:
        OAuth2ProvidersResponse: 包含所有可用OAuth2提供商的信息
    """
    try:
        providers = oauth2_manager.get_supported_providers()
        
        logger.info(
            f"获取OAuth2提供商列表成功，共{len(providers)}个",
            operation="get_oauth2_providers",
            data={"provider_count": len(providers)}
        )
        
        return OAuth2ProvidersResponse(
            providers=providers,
            total_count=len(providers)
        )
        
    except Exception as e:
        logger.error(
            f"获取OAuth2提供商列表失败: {str(e)}",
            operation="get_oauth2_providers",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取OAuth2提供商列表失败"
        )


@router.post("/{provider}/authorize", response_model=OAuth2AuthorizeResponse, summary="启动OAuth2授权")
async def oauth2_authorize(
    provider: str,
    request_data: OAuth2AuthorizeRequest,
    oauth2_manager: OAuth2ManagerDep
):
    """
    启动OAuth2授权流程
    
    Args:
        provider: OAuth2提供商名称 (google, github, microsoft)
        request_data: 授权请求数据
        
    Returns:
        OAuth2AuthorizeResponse: 包含授权URL和状态参数
    """
    try:
        # 验证提供商
        try:
            oauth2_provider = OAuth2Provider(provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的OAuth2提供商: {provider}"
            )
        
        # 生成授权URL
        auth_url, state = await oauth2_manager.generate_auth_url(
            provider=oauth2_provider,
            tenant_id=request_data.tenant_id,
            redirect_after_auth=request_data.redirect_after_auth
        )
        
        logger.info(
            f"OAuth2授权启动成功: {provider}",
            operation="oauth2_authorize",
            data={
                "provider": provider,
                "tenant_id": request_data.tenant_id,
                "state": state
            }
        )
        
        return OAuth2AuthorizeResponse(
            auth_url=auth_url,
            state=state,
            provider=provider
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"OAuth2授权启动失败: {str(e)}",
            operation="oauth2_authorize",
            data={
                "provider": provider,
                "tenant_id": request_data.tenant_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth2授权启动失败"
        )


@router.get("/{provider}/callback", summary="OAuth2回调处理")
async def oauth2_callback(
    provider: str,
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="状态参数"),
    error: str = Query(None, description="错误代码"),
    error_description: str = Query(None, description="错误描述"),
    oauth2_manager: OAuth2ManagerDep,
    auth_manager: AuthManagerDep,
    jwt_manager: JWTManagerDep,
    request: Request
):
    """
    处理OAuth2回调
    
    Args:
        provider: OAuth2提供商名称
        code: 授权码
        state: 状态参数
        error: 错误代码（可选）
        error_description: 错误描述（可选）
        
    Returns:
        重定向响应或错误页面
    """
    try:
        # 检查是否有错误
        if error:
            error_msg = error_description or f"OAuth2认证失败: {error}"
            logger.warning(
                f"OAuth2回调错误: {error}",
                operation="oauth2_callback",
                data={
                    "provider": provider,
                    "error": error,
                    "error_description": error_description
                }
            )
            
            # 重定向到错误页面
            return RedirectResponse(
                url=f"/auth/error?message={error_msg}",
                status_code=status.HTTP_302_FOUND
            )
        
        # 验证提供商
        try:
            oauth2_provider = OAuth2Provider(provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的OAuth2提供商: {provider}"
            )
        
        # 处理OAuth2回调
        auth_result = await oauth2_manager.handle_callback(
            provider=oauth2_provider,
            code=code,
            state=state
        )
        
        if not auth_result.success:
            logger.warning(
                f"OAuth2认证失败: {auth_result.error_message}",
                operation="oauth2_callback",
                data={
                    "provider": provider,
                    "error_code": auth_result.error_code,
                    "error_message": auth_result.error_message
                }
            )
            
            # 重定向到错误页面
            return RedirectResponse(
                url=f"/auth/error?message={auth_result.error_message}",
                status_code=status.HTTP_302_FOUND
            )
        
        # OAuth2认证成功，查找或创建用户
        user_info = auth_result.user_info
        
        # 这里需要实现用户查找/创建逻辑
        # 暂时返回成功页面
        logger.info(
            f"OAuth2认证成功: {provider}",
            operation="oauth2_callback",
            data={
                "provider": provider,
                "user_email": user_info.email,
                "user_name": user_info.name
            }
        )
        
        # 重定向到成功页面（实际项目中应该重定向到前端应用）
        return RedirectResponse(
            url=f"/auth/success?provider={provider}&email={user_info.email}",
            status_code=status.HTTP_302_FOUND
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"OAuth2回调处理异常: {str(e)}",
            operation="oauth2_callback",
            data={
                "provider": provider,
                "error": str(e)
            }
        )
        
        # 重定向到错误页面
        return RedirectResponse(
            url=f"/auth/error?message=OAuth2认证服务异常",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/{provider}/login", response_model=OAuth2LoginResponse, summary="OAuth2登录")
async def oauth2_login(
    provider: str,
    callback_data: OAuth2CallbackRequest,
    oauth2_manager: OAuth2ManagerDep,
    auth_manager: AuthManagerDep,
    jwt_manager: JWTManagerDep
):
    """
    OAuth2登录接口（用于前端SPA）
    
    Args:
        provider: OAuth2提供商名称
        callback_data: OAuth2回调数据
        
    Returns:
        OAuth2LoginResponse: 包含令牌和用户信息的登录结果
    """
    try:
        # 检查是否有错误
        if callback_data.error:
            return OAuth2LoginResponse(
                success=False,
                message=callback_data.error_description or f"OAuth2认证失败: {callback_data.error}",
                provider=provider
            )
        
        # 验证提供商
        try:
            oauth2_provider = OAuth2Provider(provider.lower())
        except ValueError:
            return OAuth2LoginResponse(
                success=False,
                message=f"不支持的OAuth2提供商: {provider}",
                provider=provider
            )
        
        # 处理OAuth2回调
        auth_result = await oauth2_manager.handle_callback(
            provider=oauth2_provider,
            code=callback_data.code,
            state=callback_data.state
        )
        
        if not auth_result.success:
            return OAuth2LoginResponse(
                success=False,
                message=auth_result.error_message or "OAuth2认证失败",
                provider=provider
            )
        
        # OAuth2认证成功，查找或创建用户
        user_info = auth_result.user_info
        
        # TODO: 实现用户查找/创建逻辑
        # 这里应该调用用户服务创建或查找用户
        # 然后生成JWT令牌
        
        logger.info(
            f"OAuth2登录成功: {provider}",
            operation="oauth2_login",
            data={
                "provider": provider,
                "user_email": user_info.email,
                "user_name": user_info.name
            }
        )
        
        # 暂时返回成功但无令牌的响应
        return OAuth2LoginResponse(
            success=True,
            message="OAuth2认证成功，但用户系统集成待完成",
            provider=provider,
            user_info={
                "email": user_info.email,
                "name": user_info.name,
                "avatar_url": user_info.avatar_url,
                "provider": provider
            }
        )
        
    except Exception as e:
        logger.error(
            f"OAuth2登录异常: {str(e)}",
            operation="oauth2_login",
            data={
                "provider": provider,
                "error": str(e)
            }
        )
        
        return OAuth2LoginResponse(
            success=False,
            message="OAuth2登录服务异常",
            provider=provider
        )


@router.get("/test/{provider}", summary="测试OAuth2配置")
async def test_oauth2_config(
    provider: str,
    oauth2_manager: OAuth2ManagerDep
):
    """
    测试OAuth2提供商配置
    
    Args:
        provider: OAuth2提供商名称
        
    Returns:
        dict: 配置测试结果
    """
    try:
        # 验证提供商
        try:
            oauth2_provider = OAuth2Provider(provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的OAuth2提供商: {provider}"
            )
        
        # 检查配置
        if oauth2_provider not in oauth2_manager.provider_configs:
            return {
                "success": False,
                "message": f"{provider} OAuth2配置未设置",
                "details": {
                    "provider": provider,
                    "configured": False,
                    "required_env_vars": [
                        f"{provider.upper()}_CLIENT_ID",
                        f"{provider.upper()}_CLIENT_SECRET"
                    ]
                }
            }
        
        config = oauth2_manager.provider_configs[oauth2_provider]
        
        return {
            "success": True,
            "message": f"{provider} OAuth2配置正常",
            "details": {
                "provider": provider,
                "configured": True,
                "client_id": config.client_id[:8] + "..." if config.client_id else None,
                "has_client_secret": bool(config.client_secret),
                "auth_url": config.auth_url,
                "redirect_uri": config.redirect_uri,
                "scopes": config.scopes
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"测试OAuth2配置异常: {str(e)}",
            operation="test_oauth2_config",
            data={
                "provider": provider,
                "error": str(e)
            }
        )
        
        return {
            "success": False,
            "message": "OAuth2配置测试失败",
            "error": str(e)
        }