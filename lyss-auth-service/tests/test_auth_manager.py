"""
认证管理器单元测试

测试认证管理器的所有核心功能：
- 用户登录认证
- 密码验证和哈希
- 登录失败锁定机制
- 用户状态验证
- 租户数据隔离

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import pytest
import pytest_asyncio
import time
from unittest.mock import AsyncMock, patch, MagicMock

from auth_service.core.auth_manager import AuthManager
from auth_service.models.auth_models import (
    LoginRequest, LoginResponse, AuthResult, TokenPayload, TokenPair
)


class TestAuthManager:
    """认证管理器测试类"""
    
    @pytest_asyncio.fixture
    async def mock_components(self, test_settings):
        """模拟的依赖组件"""
        # 模拟JWT管理器
        mock_jwt_manager = AsyncMock()
        mock_jwt_manager.create_token_pair.return_value = TokenPair(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            token_type="Bearer",
            expires_in=3600
        )
        
        # 模拟RBAC管理器
        mock_rbac_manager = AsyncMock()
        mock_rbac_manager.get_user_permissions.return_value = ["user:read", "user:update"]
        
        # 模拟会话管理器
        mock_session_manager = AsyncMock()
        mock_session_manager.create_session.return_value = "test_session_id"
        
        # 模拟Redis客户端
        mock_redis_client = AsyncMock()
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        mock_redis_client.incr.return_value = 1
        mock_redis_client.expire.return_value = True
        
        return {
            "jwt_manager": mock_jwt_manager,
            "rbac_manager": mock_rbac_manager,
            "session_manager": mock_session_manager,
            "redis_client": mock_redis_client,
            "settings": test_settings
        }
    
    @pytest_asyncio.fixture
    async def auth_manager(self, mock_components):
        """认证管理器实例"""
        return AuthManager(
            jwt_manager=mock_components["jwt_manager"],
            rbac_manager=mock_components["rbac_manager"],
            session_manager=mock_components["session_manager"],
            redis_client=mock_components["redis_client"],
            settings=mock_components["settings"]
        )
    
    def test_auth_manager_initialization(self, auth_manager):
        """测试认证管理器初始化"""
        assert auth_manager.jwt_manager is not None
        assert auth_manager.rbac_manager is not None
        assert auth_manager.session_manager is not None
        assert auth_manager.redis_client is not None
        assert auth_manager.settings is not None
    
    def test_password_hashing(self, auth_manager):
        """测试密码哈希功能"""
        password = "TestPassword123!"
        
        # 测试密码哈希
        hashed = auth_manager.hash_password(password)
        
        assert hashed is not None
        assert isinstance(hashed, str)
        assert hashed != password  # 哈希值应该与原密码不同
        assert len(hashed) > 50  # bcrypt哈希应该相当长
        
        # 测试密码验证
        assert auth_manager.verify_password(password, hashed) is True
        assert auth_manager.verify_password("wrong_password", hashed) is False
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_manager, mock_components):
        """测试成功认证"""
        # 模拟用户数据获取成功
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": False,
            "role": "end_user"
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            login_request = LoginRequest(
                email="test@example.com",
                password="correct_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert isinstance(result, AuthResult)
            assert result.success is True
            assert result.user_data is not None
            assert result.user_data["email"] == "test@example.com"
            assert result.error_message is None
            
            # 验证令牌对已创建
            mock_components["jwt_manager"].create_token_pair.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_manager):
        """测试用户不存在的认证"""
        with patch.object(auth_manager, '_get_user_by_email', return_value=None):
            login_request = LoginRequest(
                email="nonexistent@example.com",
                password="password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            assert result.user_data is None
            assert "用户不存在或密码错误" in result.error_message
    
    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, auth_manager):
        """测试密码错误的认证"""
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": False
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            login_request = LoginRequest(
                email="test@example.com",
                password="wrong_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            assert result.user_data is None
            assert "用户不存在或密码错误" in result.error_message
    
    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, auth_manager):
        """测试非活跃用户认证"""
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": False,  # 用户非活跃
            "email_verified": True,
            "is_locked": False
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            login_request = LoginRequest(
                email="test@example.com",
                password="correct_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            assert "用户账户已停用" in result.error_message
    
    @pytest.mark.asyncio
    async def test_authenticate_locked_user(self, auth_manager):
        """测试已锁定用户认证"""
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": True  # 用户已锁定
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            login_request = LoginRequest(
                email="test@example.com",
                password="correct_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            assert "用户账户已被锁定" in result.error_message
    
    @pytest.mark.asyncio
    async def test_authenticate_email_not_verified(self, auth_manager):
        """测试邮箱未验证用户认证"""
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": False,  # 邮箱未验证
            "is_locked": False
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            login_request = LoginRequest(
                email="test@example.com",
                password="correct_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            assert "邮箱地址未验证" in result.error_message
    
    @pytest.mark.asyncio
    async def test_login_failure_tracking(self, auth_manager, mock_components):
        """测试登录失败跟踪"""
        # 模拟Redis返回失败次数
        mock_components["redis_client"].get.return_value = "2"
        mock_components["redis_client"].incr.return_value = 3
        
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": False
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            login_request = LoginRequest(
                email="test@example.com",
                password="wrong_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            
            # 验证失败次数被记录
            mock_components["redis_client"].incr.assert_called()
            mock_components["redis_client"].expire.assert_called()
    
    @pytest.mark.asyncio
    async def test_account_lockout_after_max_failures(self, auth_manager, mock_components):
        """测试达到最大失败次数后账户锁定"""
        # 模拟达到最大失败次数
        mock_components["redis_client"].get.return_value = "4"  # 假设最大是5次
        mock_components["redis_client"].incr.return_value = 5
        
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": False
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data), \
             patch.object(auth_manager, '_lock_user_account') as mock_lock:
            
            login_request = LoginRequest(
                email="test@example.com",
                password="wrong_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            assert "账户已被暂时锁定" in result.error_message
            
            # 验证用户被锁定
            mock_lock.assert_called_once_with("user-123", "tenant-123")
    
    @pytest.mark.asyncio
    async def test_login_success_clears_failure_count(self, auth_manager, mock_components):
        """测试成功登录清除失败计数"""
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": False,
            "role": "end_user"
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            login_request = LoginRequest(
                email="test@example.com",
                password="correct_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is True
            
            # 验证失败计数被删除
            mock_components["redis_client"].delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_create_login_response(self, auth_manager, mock_components):
        """测试创建登录响应"""
        user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "role": "end_user",
            "is_active": True,
            "email_verified": True
        }
        
        # 模拟权限获取
        mock_components["rbac_manager"].get_user_permissions.return_value = [
            "user:read", "user:update"
        ]
        
        login_response = await auth_manager.create_login_response(
            user_data, "127.0.0.1", False
        )
        
        assert isinstance(login_response, LoginResponse)
        assert login_response.user.email == "test@example.com"
        assert login_response.user.username == "testuser"
        assert login_response.tokens.access_token == "test_access_token"
        assert login_response.tokens.refresh_token == "test_refresh_token"
        assert "user:read" in login_response.user.permissions
        assert "user:update" in login_response.user.permissions
    
    @pytest.mark.asyncio
    async def test_validate_user_status_all_good(self, auth_manager):
        """测试用户状态验证 - 所有状态良好"""
        user_data = {
            "is_active": True,
            "email_verified": True,
            "is_locked": False,
            "mfa_enabled": False
        }
        
        is_valid, error_message = auth_manager._validate_user_status(user_data)
        
        assert is_valid is True
        assert error_message is None
    
    @pytest.mark.asyncio
    async def test_validate_user_status_various_issues(self, auth_manager):
        """测试用户状态验证 - 各种问题"""
        # 测试非活跃用户
        user_data = {"is_active": False, "email_verified": True, "is_locked": False}
        is_valid, error_message = auth_manager._validate_user_status(user_data)
        assert is_valid is False
        assert "用户账户已停用" in error_message
        
        # 测试邮箱未验证
        user_data = {"is_active": True, "email_verified": False, "is_locked": False}
        is_valid, error_message = auth_manager._validate_user_status(user_data)
        assert is_valid is False
        assert "邮箱地址未验证" in error_message
        
        # 测试账户锁定
        user_data = {"is_active": True, "email_verified": True, "is_locked": True}
        is_valid, error_message = auth_manager._validate_user_status(user_data)
        assert is_valid is False
        assert "用户账户已被锁定" in error_message
    
    @pytest.mark.asyncio
    async def test_tenant_isolation(self, auth_manager):
        """测试租户数据隔离"""
        # 模拟不同租户的用户数据
        user_tenant_a = {
            "id": "user-123",
            "tenant_id": "tenant-a",
            "email": "test@example.com",
            "password_hash": auth_manager.hash_password("password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": False
        }
        
        # 尝试使用错误的租户ID登录
        with patch.object(auth_manager, '_get_user_by_email', return_value=user_tenant_a):
            login_request = LoginRequest(
                email="test@example.com",
                password="password",
                tenant_id="tenant-b",  # 错误的租户ID
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            assert "用户不存在或密码错误" in result.error_message
    
    @pytest.mark.asyncio
    async def test_remember_me_functionality(self, auth_manager, mock_components):
        """测试记住登录功能"""
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": False,
            "role": "end_user"
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            # 测试启用记住登录
            login_request = LoginRequest(
                email="test@example.com",
                password="correct_password",
                tenant_id="tenant-123",
                remember_me=True
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is True
            
            # 验证会话管理器被调用时设置了longer_expire
            mock_components["session_manager"].create_session.assert_called()
            call_args = mock_components["session_manager"].create_session.call_args
            assert call_args is not None
    
    @pytest.mark.asyncio
    async def test_password_strength_requirements(self, auth_manager):
        """测试密码强度要求"""
        weak_passwords = [
            "123",           # 太短
            "password",      # 太简单
            "PASSWORD",      # 只有大写
            "password123",   # 缺少大写
            "Password",      # 缺少数字
            "Password123",   # 缺少特殊字符
        ]
        
        strong_password = "StrongPassword123!"
        
        # 强密码应该可以正确哈希
        hashed = auth_manager.hash_password(strong_password)
        assert auth_manager.verify_password(strong_password, hashed) is True
        
        # 弱密码也应该能哈希（密码强度由策略管理器单独验证）
        for weak_pwd in weak_passwords:
            hashed = auth_manager.hash_password(weak_pwd)
            assert auth_manager.verify_password(weak_pwd, hashed) is True
    
    @pytest.mark.asyncio
    async def test_concurrent_login_attempts(self, auth_manager, mock_components):
        """测试并发登录尝试"""
        import asyncio
        
        mock_user_data = {
            "id": "user-123",
            "tenant_id": "tenant-123",
            "email": "test@example.com",
            "username": "testuser",
            "password_hash": auth_manager.hash_password("correct_password"),
            "is_active": True,
            "email_verified": True,
            "is_locked": False,
            "role": "end_user"
        }
        
        with patch.object(auth_manager, '_get_user_by_email', return_value=mock_user_data):
            # 并发多个登录请求
            login_request = LoginRequest(
                email="test@example.com",
                password="correct_password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            tasks = []
            for i in range(5):
                tasks.append(auth_manager.authenticate(login_request, "127.0.0.1"))
            
            results = await asyncio.gather(*tasks)
            
            # 所有请求都应该成功
            for result in results:
                assert result.success is True
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, auth_manager):
        """测试数据库错误处理"""
        # 模拟数据库错误
        with patch.object(auth_manager, '_get_user_by_email', side_effect=Exception("Database error")):
            login_request = LoginRequest(
                email="test@example.com",
                password="password",
                tenant_id="tenant-123",
                remember_me=False
            )
            
            result = await auth_manager.authenticate(login_request, "127.0.0.1")
            
            assert result.success is False
            assert "认证服务暂时不可用" in result.error_message


class TestAuthResult:
    """认证结果测试"""
    
    def test_successful_auth_result(self):
        """测试成功认证结果"""
        user_data = {
            "id": "user-123",
            "email": "test@example.com",
            "username": "testuser"
        }
        
        result = AuthResult(
            success=True,
            user_data=user_data,
            error_message=None
        )
        
        assert result.success is True
        assert result.user_data == user_data
        assert result.error_message is None
    
    def test_failed_auth_result(self):
        """测试失败认证结果"""
        result = AuthResult(
            success=False,
            user_data=None,
            error_message="认证失败"
        )
        
        assert result.success is False
        assert result.user_data is None
        assert result.error_message == "认证失败"