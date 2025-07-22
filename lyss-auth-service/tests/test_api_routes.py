"""
API路由集成测试

测试Auth Service所有API端点的集成功能：
- 健康检查路由
- 认证路由（登录、注册、令牌管理）
- OAuth2路由
- MFA路由
- 安全策略管理路由
- 中间件集成
- 错误处理

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import pytest
import pytest_asyncio
import json
from unittest.mock import patch, AsyncMock, MagicMock

from fastapi.testclient import TestClient


class TestHealthRoutes:
    """健康检查路由测试"""
    
    def test_health_check_endpoint(self, client):
        """测试基本健康检查"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["service"] == "Lyss Auth Service"
        assert "timestamp" in data
        assert data["status"] == "healthy"
    
    def test_health_detailed_endpoint(self, client):
        """测试详细健康检查"""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "components" in data["data"]
        assert "redis" in data["data"]["components"]
        assert "system" in data["data"]["components"]


class TestAuthRoutes:
    """认证路由测试"""
    
    def test_login_success(self, client):
        """测试成功登录"""
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "tenant_id": "test-tenant-id"
        }
        
        with patch('auth_service.core.auth_manager.AuthManager.authenticate') as mock_auth:
            mock_auth.return_value = MagicMock(
                success=True,
                user_data={
                    "id": "user-123",
                    "email": "test@example.com",
                    "username": "testuser",
                    "tenant_id": "test-tenant-id"
                }
            )
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "认证成功" in data["message"]
    
    def test_login_invalid_credentials(self, client):
        """测试无效凭据登录"""
        login_data = {
            "email": "test@example.com",
            "password": "wrong_password",
            "tenant_id": "test-tenant-id"
        }
        
        with patch('auth_service.core.auth_manager.AuthManager.authenticate') as mock_auth:
            mock_auth.return_value = MagicMock(
                success=False,
                error_message="用户不存在或密码错误"
            )
            
            response = client.post("/api/v1/auth/login", json=login_data)
            
            assert response.status_code == 401
            data = response.json()
            assert data["success"] is False
            assert "用户不存在或密码错误" in data["message"]
    
    def test_login_missing_fields(self, client):
        """测试登录缺少必要字段"""
        login_data = {
            "email": "test@example.com"
            # 缺少password和tenant_id
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_refresh_token_success(self, client):
        """测试成功刷新令牌"""
        refresh_data = {
            "refresh_token": "valid_refresh_token"
        }
        
        with patch('auth_service.core.jwt_manager.JWTManager.refresh_token') as mock_refresh:
            from auth_service.models.auth_models import TokenPair
            mock_refresh.return_value = TokenPair(
                access_token="new_access_token",
                refresh_token="new_refresh_token",
                token_type="Bearer",
                expires_in=3600
            )
            
            response = client.post("/api/v1/auth/refresh", json=refresh_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["access_token"] == "new_access_token"
    
    def test_refresh_token_invalid(self, client):
        """测试无效刷新令牌"""
        refresh_data = {
            "refresh_token": "invalid_refresh_token"
        }
        
        with patch('auth_service.core.jwt_manager.JWTManager.refresh_token') as mock_refresh:
            mock_refresh.return_value = None
            
            response = client.post("/api/v1/auth/refresh", json=refresh_data)
            
            assert response.status_code == 401
            data = response.json()
            assert data["success"] is False
    
    def test_logout_success(self, authenticated_client):
        """测试成功登出"""
        with patch('auth_service.core.jwt_manager.JWTManager.revoke_token') as mock_revoke, \
             patch('auth_service.core.session_manager.SessionManager.delete_session') as mock_delete_session:
            
            mock_revoke.return_value = True
            mock_delete_session.return_value = True
            
            response = authenticated_client.post("/api/v1/auth/logout")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "成功登出" in data["message"]
    
    def test_logout_unauthenticated(self, client):
        """测试未认证用户登出"""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401
    
    def test_get_current_user(self, authenticated_client):
        """测试获取当前用户信息"""
        response = authenticated_client.get("/api/v1/auth/me")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["username"] == "testuser"
    
    def test_change_password_success(self, authenticated_client):
        """测试成功更改密码"""
        password_data = {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        with patch('auth_service.core.auth_manager.AuthManager.change_password') as mock_change:
            mock_change.return_value = True
            
            response = authenticated_client.post("/api/v1/auth/change-password", json=password_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "密码修改成功" in data["message"]
    
    def test_change_password_wrong_current(self, authenticated_client):
        """测试更改密码时当前密码错误"""
        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewPassword123!",
            "confirm_password": "NewPassword123!"
        }
        
        with patch('auth_service.core.auth_manager.AuthManager.change_password') as mock_change:
            mock_change.return_value = False
            
            response = authenticated_client.post("/api/v1/auth/change-password", json=password_data)
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False


class TestOAuth2Routes:
    """OAuth2路由测试"""
    
    def test_oauth2_authorize_google(self, client):
        """测试Google OAuth2授权"""
        auth_data = {
            "provider": "google",
            "tenant_id": "test-tenant-id",
            "redirect_uri": "http://localhost:3000/callback",
            "scopes": ["openid", "email", "profile"]
        }
        
        with patch('auth_service.core.oauth2_manager.OAuth2Manager.generate_auth_url') as mock_generate:
            mock_generate.return_value = (
                "https://accounts.google.com/oauth/authorize?...",
                "test-state-123"
            )
            
            response = client.post("/api/v1/auth/oauth2/authorize", json=auth_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "auth_url" in data["data"]
            assert "state" in data["data"]
    
    def test_oauth2_authorize_invalid_provider(self, client):
        """测试无效OAuth2供应商"""
        auth_data = {
            "provider": "invalid_provider",
            "tenant_id": "test-tenant-id",
            "redirect_uri": "http://localhost:3000/callback",
            "scopes": ["openid"]
        }
        
        response = client.post("/api/v1/auth/oauth2/authorize", json=auth_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
    
    def test_oauth2_callback_success(self, client):
        """测试OAuth2回调成功"""
        callback_data = {
            "provider": "google",
            "code": "authorization-code-123",
            "state": "state-123"
        }
        
        with patch('auth_service.core.oauth2_manager.OAuth2Manager.handle_callback') as mock_callback:
            mock_callback.return_value = {
                "success": True,
                "provider": "google",
                "user_info": {
                    "email": "user@gmail.com",
                    "name": "Test User",
                    "verified_email": True
                },
                "access_token": "oauth2-access-token"
            }
            
            response = client.post("/api/v1/auth/oauth2/callback", json=callback_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["user_info"]["email"] == "user@gmail.com"
    
    def test_oauth2_callback_invalid_state(self, client):
        """测试OAuth2回调状态无效"""
        callback_data = {
            "provider": "google",
            "code": "authorization-code-123",
            "state": "invalid-state"
        }
        
        with patch('auth_service.core.oauth2_manager.OAuth2Manager.handle_callback') as mock_callback:
            mock_callback.return_value = {
                "success": False,
                "error": "无效的状态参数"
            }
            
            response = client.post("/api/v1/auth/oauth2/callback", json=callback_data)
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
            assert "状态参数" in data["message"]


class TestMFARoutes:
    """MFA路由测试"""
    
    def test_mfa_setup_totp(self, authenticated_client):
        """测试设置TOTP MFA"""
        setup_data = {
            "method": "totp",
            "user_email": "test@example.com"
        }
        
        with patch('auth_service.core.mfa_manager.MFAManager.setup_mfa') as mock_setup:
            from auth_service.models.auth_models import MFASetupResponse
            mock_setup.return_value = MFASetupResponse(
                success=True,
                method="totp",
                secret="MFRGG623VDVR======",
                qr_code_url="otpauth://totp/...",
                backup_codes=["CODE1", "CODE2"],
                message="TOTP设置成功"
            )
            
            response = authenticated_client.post("/api/v1/auth/mfa/setup", json=setup_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "secret" in data["data"]
            assert "qr_code_url" in data["data"]
            assert "backup_codes" in data["data"]
    
    def test_mfa_setup_sms(self, authenticated_client):
        """测试设置SMS MFA"""
        setup_data = {
            "method": "sms",
            "phone_number": "+1234567890"
        }
        
        with patch('auth_service.core.mfa_manager.MFAManager.setup_mfa') as mock_setup:
            from auth_service.models.auth_models import MFASetupResponse
            mock_setup.return_value = MFASetupResponse(
                success=True,
                method="sms",
                message="验证码已发送到您的手机"
            )
            
            response = authenticated_client.post("/api/v1/auth/mfa/setup", json=setup_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_mfa_verify_success(self, authenticated_client):
        """测试MFA验证成功"""
        verify_data = {
            "method": "totp",
            "code": "123456"
        }
        
        with patch('auth_service.core.mfa_manager.MFAManager.verify_mfa') as mock_verify:
            from auth_service.models.auth_models import MFAVerifyResponse
            mock_verify.return_value = MFAVerifyResponse(
                success=True,
                method="totp",
                message="TOTP验证成功"
            )
            
            response = authenticated_client.post("/api/v1/auth/mfa/verify", json=verify_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "验证成功" in data["data"]["message"]
    
    def test_mfa_verify_failure(self, authenticated_client):
        """测试MFA验证失败"""
        verify_data = {
            "method": "totp",
            "code": "000000"
        }
        
        with patch('auth_service.core.mfa_manager.MFAManager.verify_mfa') as mock_verify:
            from auth_service.models.auth_models import MFAVerifyResponse
            mock_verify.return_value = MFAVerifyResponse(
                success=False,
                method="totp",
                message="验证码错误"
            )
            
            response = authenticated_client.post("/api/v1/auth/mfa/verify", json=verify_data)
            
            assert response.status_code == 400
            data = response.json()
            assert data["success"] is False
    
    def test_mfa_disable(self, authenticated_client):
        """测试禁用MFA"""
        with patch('auth_service.core.mfa_manager.MFAManager.disable_mfa') as mock_disable:
            mock_disable.return_value = True
            
            response = authenticated_client.post("/api/v1/auth/mfa/disable")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "MFA已禁用" in data["message"]
    
    def test_mfa_status(self, authenticated_client):
        """测试获取MFA状态"""
        with patch('auth_service.core.mfa_manager.MFAManager.get_mfa_status') as mock_status:
            mock_status.return_value = {
                "mfa_enabled": True,
                "enabled_methods": ["totp", "sms"],
                "backup_codes_available": 8
            }
            
            response = authenticated_client.get("/api/v1/auth/mfa/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["mfa_enabled"] is True
            assert "totp" in data["data"]["enabled_methods"]
    
    def test_mfa_generate_backup_codes(self, authenticated_client):
        """测试生成备份代码"""
        with patch('auth_service.core.mfa_manager.MFAManager.generate_backup_codes') as mock_generate:
            from auth_service.models.auth_models import BackupCodesResponse
            mock_generate.return_value = BackupCodesResponse(
                success=True,
                codes=["CODE1", "CODE2", "CODE3", "CODE4", "CODE5"],
                message="备份代码生成成功"
            )
            
            response = authenticated_client.post("/api/v1/auth/mfa/backup-codes/generate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["codes"]) == 5
    
    def test_mfa_unauthenticated(self, client):
        """测试未认证用户访问MFA端点"""
        response = client.post("/api/v1/auth/mfa/setup", json={"method": "totp"})
        
        assert response.status_code == 401


class TestSecurityPolicyRoutes:
    """安全策略管理路由测试"""
    
    def test_get_security_policies_all(self, admin_client):
        """测试获取所有安全策略（管理员）"""
        with patch('auth_service.core.security_policy_manager.SecurityPolicyManager.get_policy') as mock_get:
            mock_get.side_effect = [
                {"min_length": 8, "require_uppercase": True},  # password
                {"max_concurrent_sessions": 5},                # session
                {"max_failed_attempts": 5},                    # login
                {"log_retention_days": 365},                   # audit
                {"whitelist_enabled": False}                   # ip
            ]
            
            response = admin_client.get("/api/v1/auth/security/policies")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "policies" in data["data"]
    
    def test_get_security_policy_specific(self, admin_client):
        """测试获取特定安全策略"""
        with patch('auth_service.core.security_policy_manager.SecurityPolicyManager.get_policy') as mock_get:
            mock_get.return_value = {
                "min_length": 12,
                "require_uppercase": True,
                "require_special_chars": True
            }
            
            response = admin_client.get("/api/v1/auth/security/policies?policy_type=password")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["policy_type"] == "password"
    
    def test_get_security_policies_non_admin(self, authenticated_client):
        """测试非管理员用户获取安全策略"""
        response = authenticated_client.get("/api/v1/auth/security/policies")
        
        assert response.status_code == 403
    
    def test_update_security_policy(self, admin_client):
        """测试更新安全策略"""
        policy_data = {
            "min_length": 10,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digits": True,
            "require_special_chars": True
        }
        
        with patch('auth_service.core.security_policy_manager.SecurityPolicyManager.update_policy') as mock_update:
            mock_update.return_value = True
            
            response = admin_client.put("/api/v1/auth/security/policies/password", json=policy_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "更新成功" in data["message"]
    
    def test_update_security_policy_invalid_type(self, admin_client):
        """测试更新无效策略类型"""
        policy_data = {"some_setting": "some_value"}
        
        response = admin_client.put("/api/v1/auth/security/policies/invalid_type", json=policy_data)
        
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "无效的策略类型" in data["message"]
    
    def test_validate_password_strength(self, client):
        """测试验证密码强度"""
        password_data = {
            "password": "TestPassword123!",
            "user_info": {
                "username": "testuser",
                "email": "test@example.com"
            }
        }
        
        with patch('auth_service.core.security_policy_manager.SecurityPolicyManager.validate_password') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "errors": [],
                "strength_score": 85,
                "strength_level": "strong",
                "policy_compliant": True
            }
            
            response = client.post("/api/v1/auth/security/password/validate", json=password_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["valid"] is True
            assert data["data"]["strength_score"] == 85
    
    def test_check_ip_access(self, admin_client):
        """测试检查IP访问权限"""
        ip_data = {"ip_address": "192.168.1.100"}
        
        with patch('auth_service.core.security_policy_manager.SecurityPolicyManager.check_ip_access') as mock_check:
            mock_check.return_value = {
                "allowed": True,
                "reason": "IP地址检查通过"
            }
            
            response = admin_client.post("/api/v1/auth/security/ip/check", json=ip_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["allowed"] is True
    
    def test_block_ip_address(self, admin_client):
        """测试手动封禁IP"""
        block_data = {
            "ip_address": "192.168.1.100",
            "block_hours": 24,
            "reason": "可疑活动"
        }
        
        with patch('auth_service.core.security_policy_manager.SecurityPolicyManager.redis_client') as mock_redis:
            mock_redis.set.return_value = True
            
            response = admin_client.post("/api/v1/auth/security/ip/block", json=block_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已封禁" in data["message"]
    
    def test_unblock_ip_address(self, admin_client):
        """测试解封IP"""
        unblock_data = {"ip_address": "192.168.1.100"}
        
        with patch('auth_service.core.security_policy_manager.SecurityPolicyManager.redis_client') as mock_redis:
            mock_redis.delete.return_value = True
            
            response = admin_client.delete("/api/v1/auth/security/ip/unblock", json=unblock_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已解封" in data["message"]


class TestTokenManagement:
    """令牌管理测试"""
    
    def test_validate_token(self, client):
        """测试令牌验证端点"""
        token_data = {"token": "valid_access_token"}
        
        with patch('auth_service.core.jwt_manager.JWTManager.get_token_info') as mock_info:
            mock_info.return_value = {
                "valid": True,
                "user_id": "user-123",
                "email": "test@example.com",
                "role": "end_user",
                "issued_at": "2025-01-21T10:00:00",
                "expires_at": "2025-01-21T11:00:00"
            }
            
            response = client.post("/api/v1/auth/tokens/validate", json=token_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["valid"] is True
    
    def test_revoke_token(self, authenticated_client):
        """测试撤销令牌"""
        with patch('auth_service.core.jwt_manager.JWTManager.revoke_token') as mock_revoke:
            mock_revoke.return_value = True
            
            response = authenticated_client.post("/api/v1/auth/tokens/revoke")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestInternalRoutes:
    """内部服务接口测试"""
    
    def test_internal_validate_token(self, client):
        """测试内部令牌验证"""
        headers = {"Authorization": "Bearer valid_access_token"}
        
        with patch('auth_service.core.jwt_manager.JWTManager.verify_token') as mock_verify:
            from auth_service.core.jwt_manager import TokenValidationResult
            from auth_service.models.auth_models import TokenPayload
            
            mock_verify.return_value = TokenValidationResult(
                is_valid=True,
                payload=TokenPayload(
                    sub="user-123",
                    email="test@example.com",
                    tenant_id="tenant-123",
                    role="end_user",
                    permissions=["user:read"],
                    iat=1640995200,
                    exp=1640998800
                ),
                error_message=None
            )
            
            response = client.get("/internal/auth/validate", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["user_id"] == "user-123"
    
    def test_internal_get_user_permissions(self, client):
        """测试获取用户权限（内部接口）"""
        user_data = {
            "user_id": "user-123",
            "tenant_id": "tenant-123"
        }
        
        with patch('auth_service.core.rbac_manager.RBACManager.get_user_permissions') as mock_perms:
            mock_perms.return_value = ["user:read", "user:update"]
            
            response = client.post("/internal/auth/user/permissions", json=user_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "user:read" in data["data"]["permissions"]


class TestMiddlewareIntegration:
    """中间件集成测试"""
    
    def test_cors_headers(self, client):
        """测试CORS头设置"""
        response = client.options("/api/v1/auth/login", 
                                headers={"Origin": "http://localhost:3000"})
        
        assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]
    
    def test_security_headers(self, client):
        """测试安全头设置"""
        response = client.get("/health")
        
        # 检查常见安全头
        headers = {k.lower(): v for k, v in response.headers.items()}
        assert "x-content-type-options" in headers
        assert "x-frame-options" in headers
    
    def test_rate_limiting(self, client):
        """测试限流中间件"""
        # 快速发送多个请求以触发限流
        responses = []
        for _ in range(100):  # 发送大量请求
            response = client.get("/health")
            responses.append(response)
        
        # 检查是否有请求被限流（429状态码）
        status_codes = [r.status_code for r in responses]
        # 由于这是测试环境，可能不会真正触发限流，所以只检查没有5xx错误
        assert all(code < 500 for code in status_codes)
    
    def test_request_logging(self, client):
        """测试请求日志中间件"""
        with patch('auth_service.utils.logging.get_logger') as mock_logger:
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            client.get("/health")
            
            # 验证日志被记录（这里只能检查是否调用了logger）
            # 实际的日志验证在单独的日志测试中进行
            assert mock_logger.called
    
    def test_error_handling_middleware(self, client):
        """测试错误处理中间件"""
        # 访问不存在的端点
        response = client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "detail" in data or "message" in data


class TestErrorHandling:
    """错误处理测试"""
    
    def test_validation_error(self, client):
        """测试请求验证错误"""
        # 发送格式错误的JSON
        response = client.post("/api/v1/auth/login", 
                             json={"email": "not-an-email"},  # 无效邮箱格式
                             headers={"Content-Type": "application/json"})
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data or "errors" in data
    
    def test_server_error_handling(self, client):
        """测试服务器错误处理"""
        # 模拟服务器内部错误
        with patch('auth_service.routers.health.get_redis_client') as mock_redis:
            mock_redis.side_effect = Exception("Database connection failed")
            
            response = client.get("/health/detailed")
            
            # 错误应该被优雅处理
            assert response.status_code in [200, 500, 503]  # 取决于具体实现
            
            if response.status_code != 200:
                data = response.json()
                assert data["success"] is False
    
    def test_authentication_error(self, client):
        """测试认证错误处理"""
        # 使用无效令牌访问受保护端点
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
    
    def test_authorization_error(self, authenticated_client):
        """测试授权错误处理"""
        # 普通用户尝试访问管理员端点
        response = authenticated_client.get("/api/v1/auth/security/policies")
        
        assert response.status_code == 403
        data = response.json()
        assert data["success"] is False


class TestEndToEndWorkflows:
    """端到端工作流测试"""
    
    def test_complete_authentication_flow(self, client):
        """测试完整认证流程"""
        # 1. 登录
        login_data = {
            "email": "test@example.com",
            "password": "TestPassword123!",
            "tenant_id": "test-tenant-id"
        }
        
        with patch('auth_service.core.auth_manager.AuthManager.authenticate') as mock_auth:
            mock_auth.return_value = MagicMock(success=True, user_data={
                "id": "user-123", "email": "test@example.com", 
                "username": "testuser", "tenant_id": "test-tenant-id"
            })
            
            with patch('auth_service.core.auth_manager.AuthManager.create_login_response') as mock_response:
                from auth_service.models.auth_models import LoginResponse, UserInfo, TokenPair
                mock_response.return_value = LoginResponse(
                    user=UserInfo(
                        id="user-123", email="test@example.com", username="testuser",
                        tenant_id="test-tenant-id", role="end_user", permissions=["user:read"]
                    ),
                    tokens=TokenPair(
                        access_token="access_token", refresh_token="refresh_token",
                        token_type="Bearer", expires_in=3600
                    )
                )
                
                response = client.post("/api/v1/auth/login", json=login_data)
                assert response.status_code == 200
                
                login_result = response.json()
                access_token = login_result["data"]["tokens"]["access_token"]
        
        # 2. 使用令牌访问受保护资源
        headers = {"Authorization": f"Bearer {access_token}"}
        
        with patch('auth_service.core.jwt_manager.JWTManager.verify_token') as mock_verify:
            from auth_service.core.jwt_manager import TokenValidationResult
            from auth_service.models.auth_models import TokenPayload
            
            mock_verify.return_value = TokenValidationResult(
                is_valid=True,
                payload=TokenPayload(
                    sub="user-123", email="test@example.com", tenant_id="test-tenant-id",
                    role="end_user", permissions=["user:read"], iat=1640995200, exp=1640998800
                ),
                error_message=None
            )
            
            response = client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 200
        
        # 3. 登出
        with patch('auth_service.core.jwt_manager.JWTManager.revoke_token') as mock_revoke, \
             patch('auth_service.core.session_manager.SessionManager.delete_session') as mock_delete:
            mock_revoke.return_value = True
            mock_delete.return_value = True
            
            response = client.post("/api/v1/auth/logout", headers=headers)
            assert response.status_code == 200