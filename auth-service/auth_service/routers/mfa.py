"""
多因素认证（MFA）路由

提供完整的MFA管理API接口：
- MFA方法设置（TOTP、SMS、邮箱）
- MFA验证
- 备用恢复码管理
- MFA状态查询

支持企业级安全需求的多因素认证功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.auth_models import (
    MFASetupRequest, MFASetupResponse, MFAVerifyRequest,
    ApiResponse, UserInfoResponse
)
from ..core.mfa_manager import MFAManager, MFAMethod
from ..dependencies import (
    MFAManagerDep, JWTManagerDep, verify_token_dependency
)
from ..utils.logging import get_logger

router = APIRouter(prefix="/api/v1/auth/mfa", tags=["多因素认证"])
security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


@router.post("/totp/setup", response_model=MFASetupResponse, summary="设置TOTP多因素认证")
async def setup_totp_mfa(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    mfa_manager: MFAManagerDep
):
    """
    设置TOTP多因素认证
    
    Returns:
        MFASetupResponse: 包含TOTP密钥、二维码和备用码的设置结果
    """
    try:
        # 验证用户身份
        user_data = await verify_token_dependency(jwt_manager, credentials.credentials)
        user_id = user_data["sub"]
        user_email = user_data["email"]
        
        # 设置TOTP
        setup_result = await mfa_manager.setup_totp(user_id, user_email)
        
        if setup_result.success:
            logger.info(
                f"TOTP MFA设置启动成功: 用户{user_id}",
                operation="setup_totp_mfa",
                data={"user_id": user_id}
            )
            
            return MFASetupResponse(
                success=True,
                message=setup_result.message,
                secret_key=setup_result.secret_key,
                qr_code_url=setup_result.qr_code_data
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=setup_result.error_message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"TOTP MFA设置异常: {str(e)}",
            operation="setup_totp_mfa",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TOTP MFA设置服务异常"
        )


@router.post("/totp/verify-setup", response_model=ApiResponse, summary="验证TOTP设置")
async def verify_totp_setup(
    verify_request: MFAVerifyRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    mfa_manager: MFAManagerDep
):
    """
    验证TOTP设置
    
    Args:
        verify_request: 包含验证码的请求
        
    Returns:
        ApiResponse: 验证结果和备用恢复码
    """
    try:
        # 验证用户身份
        user_data = await verify_token_dependency(jwt_manager, credentials.credentials)
        user_id = user_data["sub"]
        
        # 验证TOTP设置
        setup_result = await mfa_manager.verify_totp_setup(
            user_id, 
            verify_request.verification_code
        )
        
        if setup_result.success:
            logger.info(
                f"TOTP MFA设置完成: 用户{user_id}",
                operation="verify_totp_setup",
                data={"user_id": user_id}
            )
            
            return ApiResponse(
                success=True,
                message=setup_result.message,
                data={
                    "backup_codes": setup_result.backup_codes,
                    "method": "totp"
                }
            )
        else:
            return ApiResponse(
                success=False,
                message=setup_result.error_message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"TOTP设置验证异常: {str(e)}",
            operation="verify_totp_setup",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TOTP设置验证服务异常"
        )


@router.post("/sms/setup", response_model=MFASetupResponse, summary="设置SMS多因素认证")
async def setup_sms_mfa(
    setup_request: MFASetupRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    mfa_manager: MFAManagerDep
):
    """
    设置SMS多因素认证
    
    Args:
        setup_request: 包含手机号的设置请求
        
    Returns:
        MFASetupResponse: SMS设置结果
    """
    try:
        # 验证用户身份
        user_data = await verify_token_dependency(jwt_manager, credentials.credentials)
        user_id = user_data["sub"]
        
        if not setup_request.phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="手机号码不能为空"
            )
        
        # 设置SMS MFA
        setup_result = await mfa_manager.setup_sms(
            user_id, 
            setup_request.phone_number
        )
        
        if setup_result.success:
            logger.info(
                f"SMS MFA设置启动成功: 用户{user_id}",
                operation="setup_sms_mfa",
                data={
                    "user_id": user_id,
                    "phone_number": setup_request.phone_number[-4:]
                }
            )
            
            return MFASetupResponse(
                success=True,
                message=setup_result.message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=setup_result.error_message
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"SMS MFA设置异常: {str(e)}",
            operation="setup_sms_mfa",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SMS MFA设置服务异常"
        )


@router.post("/verify", response_model=ApiResponse, summary="验证MFA代码")
async def verify_mfa_code(
    verify_request: MFAVerifyRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    mfa_manager: MFAManagerDep
):
    """
    验证MFA代码（用于二次验证）
    
    Args:
        verify_request: 包含验证码和方法的请求
        
    Returns:
        ApiResponse: 验证结果
    """
    try:
        # 验证用户身份
        user_data = await verify_token_dependency(jwt_manager, credentials.credentials)
        user_id = user_data["sub"]
        
        # 确定MFA方法
        method = MFAMethod.TOTP  # 默认使用TOTP
        if hasattr(verify_request, 'mfa_type'):
            try:
                method = MFAMethod(verify_request.mfa_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的MFA方法"
                )
        
        # 验证MFA代码
        verify_result = await mfa_manager.verify_mfa(
            user_id=user_id,
            method=method,
            code=verify_request.verification_code
        )
        
        if verify_result.success:
            logger.info(
                f"MFA验证成功: 用户{user_id}, 方法{method.value}",
                operation="verify_mfa_code",
                data={
                    "user_id": user_id,
                    "method": method.value,
                    "backup_code_used": verify_result.backup_code_used
                }
            )
            
            response_data = {
                "method": method.value,
                "backup_code_used": verify_result.backup_code_used
            }
            
            if verify_result.remaining_backup_codes is not None:
                response_data["remaining_backup_codes"] = verify_result.remaining_backup_codes
            
            return ApiResponse(
                success=True,
                message="MFA验证成功",
                data=response_data
            )
        else:
            return ApiResponse(
                success=False,
                message=verify_result.error_message or "MFA验证失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"MFA验证异常: {str(e)}",
            operation="verify_mfa_code",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="MFA验证服务异常"
        )


@router.get("/status", response_model=ApiResponse, summary="获取MFA状态")
async def get_mfa_status(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    mfa_manager: MFAManagerDep
):
    """
    获取当前用户的MFA状态
    
    Returns:
        ApiResponse: 包含MFA方法启用状态和备用码信息
    """
    try:
        # 验证用户身份
        user_data = await verify_token_dependency(jwt_manager, credentials.credentials)
        user_id = user_data["sub"]
        
        # 获取MFA状态
        mfa_status = await mfa_manager.get_user_mfa_status(user_id)
        
        status_data = {
            "enabled_methods": [method.value for method in mfa_status.enabled_methods],
            "backup_codes_remaining": mfa_status.backup_codes_remaining,
            "last_used_method": mfa_status.last_used_method.value if mfa_status.last_used_method else None,
            "last_used_at": mfa_status.last_used_at,
            "mfa_enabled": len(mfa_status.enabled_methods) > 0
        }
        
        logger.debug(
            f"MFA状态查询: 用户{user_id}",
            operation="get_mfa_status",
            data={
                "user_id": user_id,
                "enabled_methods_count": len(mfa_status.enabled_methods)
            }
        )
        
        return ApiResponse(
            success=True,
            message="MFA状态获取成功",
            data=status_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"获取MFA状态异常: {str(e)}",
            operation="get_mfa_status",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取MFA状态服务异常"
        )


@router.delete("/{method}", response_model=ApiResponse, summary="禁用MFA方法")
async def disable_mfa_method(
    method: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    mfa_manager: MFAManagerDep
):
    """
    禁用指定的MFA方法
    
    Args:
        method: MFA方法名称 (totp, sms, email)
        
    Returns:
        ApiResponse: 禁用结果
    """
    try:
        # 验证用户身份
        user_data = await verify_token_dependency(jwt_manager, credentials.credentials)
        user_id = user_data["sub"]
        
        # 验证方法名称
        try:
            mfa_method = MFAMethod(method.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的MFA方法: {method}"
            )
        
        # 禁用MFA方法
        success = await mfa_manager.disable_mfa(user_id, mfa_method)
        
        if success:
            logger.info(
                f"MFA方法已禁用: 用户{user_id}, 方法{method}",
                operation="disable_mfa_method",
                data={
                    "user_id": user_id,
                    "method": method
                }
            )
            
            return ApiResponse(
                success=True,
                message=f"{method.upper()} MFA已成功禁用"
            )
        else:
            return ApiResponse(
                success=False,
                message=f"禁用{method.upper()} MFA失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"禁用MFA方法异常: {str(e)}",
            operation="disable_mfa_method",
            data={
                "method": method,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="禁用MFA方法服务异常"
        )


@router.post("/backup-codes/regenerate", response_model=ApiResponse, summary="重新生成备用恢复码")
async def regenerate_backup_codes(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    mfa_manager: MFAManagerDep
):
    """
    重新生成备用恢复码
    
    Returns:
        ApiResponse: 包含新生成的备用恢复码
    """
    try:
        # 验证用户身份
        user_data = await verify_token_dependency(jwt_manager, credentials.credentials)
        user_id = user_data["sub"]
        
        # 检查用户是否已启用TOTP
        mfa_status = await mfa_manager.get_user_mfa_status(user_id)
        if MFAMethod.TOTP not in mfa_status.enabled_methods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只有启用TOTP的用户才能生成备用恢复码"
            )
        
        # 生成新的备用码
        backup_codes = mfa_manager._generate_backup_codes()
        
        # 保存到Redis
        await mfa_manager.redis_client.set(
            f"mfa_backup_codes:{user_id}",
            backup_codes
        )
        
        logger.info(
            f"备用恢复码重新生成: 用户{user_id}",
            operation="regenerate_backup_codes",
            data={
                "user_id": user_id,
                "codes_count": len(backup_codes)
            }
        )
        
        return ApiResponse(
            success=True,
            message="备用恢复码已重新生成，请妥善保存",
            data={"backup_codes": backup_codes}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"重新生成备用码异常: {str(e)}",
            operation="regenerate_backup_codes",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新生成备用码服务异常"
        )


@router.get("/methods", response_model=ApiResponse, summary="获取支持的MFA方法")
async def get_supported_mfa_methods():
    """
    获取系统支持的MFA方法列表
    
    Returns:
        ApiResponse: 支持的MFA方法信息
    """
    try:
        methods = [
            {
                "method": MFAMethod.TOTP.value,
                "name": "认证器应用（TOTP）",
                "description": "使用Google Authenticator等应用生成6位验证码",
                "recommended": True
            },
            {
                "method": MFAMethod.SMS.value,
                "name": "短信验证码",
                "description": "通过手机短信接收6位验证码",
                "recommended": False
            },
            {
                "method": MFAMethod.EMAIL.value,
                "name": "邮箱验证码",
                "description": "通过邮箱接收6位验证码",
                "recommended": False
            },
            {
                "method": MFAMethod.WEBAUTHN.value,
                "name": "WebAuthn（待实现）",
                "description": "使用生物识别或硬件密钥进行验证",
                "recommended": True,
                "available": False
            }
        ]
        
        return ApiResponse(
            success=True,
            message="获取MFA方法列表成功",
            data={
                "methods": methods,
                "total_count": len(methods)
            }
        )
        
    except Exception as e:
        logger.error(
            f"获取MFA方法列表异常: {str(e)}",
            operation="get_supported_mfa_methods",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取MFA方法列表服务异常"
        )