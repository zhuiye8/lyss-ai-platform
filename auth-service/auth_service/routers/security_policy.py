"""
安全策略管理路由

提供安全策略管理的API接口：
- 查看当前安全策略
- 更新安全策略配置
- 密码强度验证
- IP访问控制
- 审计日志管理

仅限管理员用户访问。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.auth_models import ApiResponse, PasswordPolicyResponse
from ..core.security_policy_manager import SecurityPolicyManager
from ..dependencies import (
    SecurityPolicyManagerDep, JWTManagerDep, RBACManagerDep,
    verify_token_dependency, admin_required
)
from ..utils.logging import get_logger

router = APIRouter(prefix="/api/v1/auth/security", tags=["安全策略管理"])
security = HTTPBearer(auto_error=False)
logger = get_logger(__name__)


@router.get("/policies", response_model=ApiResponse, summary="获取安全策略配置")
async def get_security_policies(
    policy_type: Optional[str] = Query(None, description="策略类型 (password, session, login, audit, ip)"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    rbac_manager: RBACManagerDep,
    security_policy_manager: SecurityPolicyManagerDep,
    current_user: dict = Depends(admin_required())
):
    """
    获取安全策略配置（需要管理员权限）
    
    Args:
        policy_type: 可选的策略类型过滤
        
    Returns:
        ApiResponse: 包含策略配置信息
    """
    try:
        if policy_type:
            # 获取特定类型的策略
            policy_config = await security_policy_manager.get_policy(policy_type)
            
            if not policy_config:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"未找到策略类型: {policy_type}"
                )
            
            logger.info(
                f"管理员获取安全策略: {policy_type}",
                operation="get_security_policy",
                data={
                    "admin_user": current_user.get("sub"),
                    "policy_type": policy_type
                }
            )
            
            return ApiResponse(
                success=True,
                message=f"获取{policy_type}策略成功",
                data={
                    "policy_type": policy_type,
                    "config": policy_config
                }
            )
        else:
            # 获取所有策略
            all_policies = {}
            policy_types = ["password", "session", "login", "audit", "ip"]
            
            for p_type in policy_types:
                policy_config = await security_policy_manager.get_policy(p_type)
                if policy_config:
                    all_policies[p_type] = policy_config
            
            logger.info(
                "管理员获取所有安全策略",
                operation="get_all_security_policies",
                data={
                    "admin_user": current_user.get("sub"),
                    "policy_count": len(all_policies)
                }
            )
            
            return ApiResponse(
                success=True,
                message="获取安全策略成功",
                data={
                    "policies": all_policies,
                    "policy_count": len(all_policies)
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"获取安全策略异常: {str(e)}",
            operation="get_security_policies",
            data={
                "policy_type": policy_type,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取安全策略服务异常"
        )


@router.put("/policies/{policy_type}", response_model=ApiResponse, summary="更新安全策略")
async def update_security_policy(
    policy_type: str,
    policy_config: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    security_policy_manager: SecurityPolicyManagerDep,
    current_user: dict = Depends(admin_required())
):
    """
    更新指定类型的安全策略（需要管理员权限）
    
    Args:
        policy_type: 策略类型 (password, session, login, audit, ip)
        policy_config: 新的策略配置
        
    Returns:
        ApiResponse: 更新结果
    """
    try:
        # 验证策略类型
        valid_types = ["password", "session", "login", "audit", "ip"]
        if policy_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的策略类型: {policy_type}，支持的类型: {', '.join(valid_types)}"
            )
        
        # 更新策略
        success = await security_policy_manager.update_policy(policy_type, policy_config)
        
        if success:
            logger.info(
                f"安全策略更新成功: {policy_type}",
                operation="update_security_policy",
                data={
                    "admin_user": current_user.get("sub"),
                    "policy_type": policy_type
                }
            )
            
            return ApiResponse(
                success=True,
                message=f"{policy_type}策略更新成功",
                data={
                    "policy_type": policy_type,
                    "updated_at": logger._get_timestamp()
                }
            )
        else:
            return ApiResponse(
                success=False,
                message=f"{policy_type}策略更新失败，请检查配置格式"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"更新安全策略异常: {str(e)}",
            operation="update_security_policy",
            data={
                "policy_type": policy_type,
                "admin_user": current_user.get("sub"),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新安全策略服务异常"
        )


@router.post("/password/validate", response_model=ApiResponse, summary="验证密码强度")
async def validate_password_strength(
    password_data: Dict[str, Any],
    security_policy_manager: SecurityPolicyManagerDep
):
    """
    根据当前密码策略验证密码强度
    
    Args:
        password_data: 包含密码和可选用户信息的数据
        
    Returns:
        ApiResponse: 密码验证结果和强度评分
    """
    try:
        password = password_data.get("password")
        user_info = password_data.get("user_info", {})
        
        if not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码不能为空"
            )
        
        # 验证密码强度
        validation_result = await security_policy_manager.validate_password(
            password=password,
            user_info=user_info
        )
        
        logger.debug(
            f"密码强度验证: 强度{validation_result['strength_score']}分",
            operation="validate_password_strength",
            data={
                "strength_score": validation_result["strength_score"],
                "strength_level": validation_result["strength_level"],
                "valid": validation_result["valid"]
            }
        )
        
        return ApiResponse(
            success=True,
            message="密码强度验证完成",
            data={
                "valid": validation_result["valid"],
                "errors": validation_result["errors"],
                "strength_score": validation_result["strength_score"],
                "strength_level": validation_result["strength_level"],
                "policy_compliant": validation_result["policy_compliant"]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"密码强度验证异常: {str(e)}",
            operation="validate_password_strength",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码强度验证服务异常"
        )


@router.post("/ip/check", response_model=ApiResponse, summary="检查IP访问权限")
async def check_ip_access(
    ip_data: Dict[str, str],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    security_policy_manager: SecurityPolicyManagerDep,
    current_user: dict = Depends(admin_required())
):
    """
    检查IP地址访问权限（需要管理员权限）
    
    Args:
        ip_data: 包含IP地址的数据
        
    Returns:
        ApiResponse: IP访问检查结果
    """
    try:
        ip_address = ip_data.get("ip_address")
        
        if not ip_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IP地址不能为空"
            )
        
        # 检查IP访问权限
        access_result = await security_policy_manager.check_ip_access(ip_address)
        
        logger.info(
            f"IP访问权限检查: {ip_address}",
            operation="check_ip_access",
            data={
                "admin_user": current_user.get("sub"),
                "ip_address": ip_address,
                "allowed": access_result["allowed"]
            }
        )
        
        return ApiResponse(
            success=True,
            message="IP访问权限检查完成",
            data=access_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"IP访问权限检查异常: {str(e)}",
            operation="check_ip_access",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="IP访问权限检查服务异常"
        )


@router.post("/ip/block", response_model=ApiResponse, summary="手动封禁IP")
async def block_ip_address(
    block_data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    security_policy_manager: SecurityPolicyManagerDep,
    current_user: dict = Depends(admin_required())
):
    """
    手动封禁IP地址（需要管理员权限）
    
    Args:
        block_data: 包含IP地址和封禁时长的数据
        
    Returns:
        ApiResponse: 封禁操作结果
    """
    try:
        ip_address = block_data.get("ip_address")
        block_hours = block_data.get("block_hours", 24)
        reason = block_data.get("reason", "管理员手动封禁")
        
        if not ip_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IP地址不能为空"
            )
        
        if block_hours < 1 or block_hours > 8760:  # 1小时到1年
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="封禁时长必须在1-8760小时之间"
            )
        
        # 手动封禁IP
        import time
        block_until = time.time() + (block_hours * 3600)
        
        await security_policy_manager.redis_client.set(
            f"blocked_ip:{ip_address}",
            block_until,
            expire=int(block_hours * 3600)
        )
        
        logger.warning(
            f"管理员手动封禁IP: {ip_address}",
            operation="manual_block_ip",
            data={
                "admin_user": current_user.get("sub"),
                "ip_address": ip_address,
                "block_hours": block_hours,
                "reason": reason
            }
        )
        
        return ApiResponse(
            success=True,
            message=f"IP地址 {ip_address} 已封禁 {block_hours} 小时",
            data={
                "ip_address": ip_address,
                "block_hours": block_hours,
                "block_until": block_until,
                "reason": reason
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"手动封禁IP异常: {str(e)}",
            operation="block_ip_address",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="封禁IP服务异常"
        )


@router.delete("/ip/unblock", response_model=ApiResponse, summary="解封IP")
async def unblock_ip_address(
    ip_data: Dict[str, str],
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    security_policy_manager: SecurityPolicyManagerDep,
    current_user: dict = Depends(admin_required())
):
    """
    解封IP地址（需要管理员权限）
    
    Args:
        ip_data: 包含IP地址的数据
        
    Returns:
        ApiResponse: 解封操作结果
    """
    try:
        ip_address = ip_data.get("ip_address")
        
        if not ip_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IP地址不能为空"
            )
        
        # 解封IP
        success = await security_policy_manager.redis_client.delete(f"blocked_ip:{ip_address}")
        
        if success:
            logger.info(
                f"管理员解封IP: {ip_address}",
                operation="unblock_ip_address",
                data={
                    "admin_user": current_user.get("sub"),
                    "ip_address": ip_address
                }
            )
            
            return ApiResponse(
                success=True,
                message=f"IP地址 {ip_address} 已解封",
                data={"ip_address": ip_address}
            )
        else:
            return ApiResponse(
                success=False,
                message=f"IP地址 {ip_address} 未在封禁列表中"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"解封IP异常: {str(e)}",
            operation="unblock_ip_address",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="解封IP服务异常"
        )


@router.get("/audit/policy-changes", response_model=ApiResponse, summary="获取策略变更日志")
async def get_policy_change_logs(
    limit: int = Query(50, ge=1, le=200, description="返回记录数量"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    security_policy_manager: SecurityPolicyManagerDep,
    current_user: dict = Depends(admin_required())
):
    """
    获取安全策略变更审计日志（需要管理员权限）
    
    Args:
        limit: 返回记录数量限制
        
    Returns:
        ApiResponse: 策略变更日志列表
    """
    try:
        # 获取策略变更日志
        # 这里需要实现从Redis获取日志记录的逻辑
        # 暂时返回示例数据
        
        change_logs = [
            {
                "timestamp": logger._get_timestamp(),
                "policy_type": "password",
                "operation": "update",
                "admin_user": "admin@example.com",
                "changes": {
                    "min_length": {"old": 8, "new": 10},
                    "require_special_chars": {"old": True, "new": True}
                }
            }
        ]
        
        logger.info(
            "管理员获取策略变更日志",
            operation="get_policy_change_logs",
            data={
                "admin_user": current_user.get("sub"),
                "limit": limit
            }
        )
        
        return ApiResponse(
            success=True,
            message="获取策略变更日志成功",
            data={
                "logs": change_logs,
                "total_count": len(change_logs),
                "limit": limit
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"获取策略变更日志异常: {str(e)}",
            operation="get_policy_change_logs",
            data={"error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取策略变更日志服务异常"
        )


@router.post("/initialize", response_model=ApiResponse, summary="初始化安全策略")
async def initialize_security_policies(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_manager: JWTManagerDep,
    security_policy_manager: SecurityPolicyManagerDep,
    current_user: dict = Depends(admin_required())
):
    """
    初始化安全策略为默认配置（需要管理员权限）
    
    Returns:
        ApiResponse: 初始化结果
    """
    try:
        # 初始化安全策略
        await security_policy_manager.initialize_policies()
        
        logger.info(
            "管理员初始化安全策略",
            operation="initialize_security_policies",
            data={"admin_user": current_user.get("sub")}
        )
        
        return ApiResponse(
            success=True,
            message="安全策略已初始化为默认配置",
            data={
                "initialized_at": logger._get_timestamp(),
                "admin_user": current_user.get("email")
            }
        )
        
    except Exception as e:
        logger.error(
            f"初始化安全策略异常: {str(e)}",
            operation="initialize_security_policies",
            data={
                "admin_user": current_user.get("sub"),
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="初始化安全策略服务异常"
        )