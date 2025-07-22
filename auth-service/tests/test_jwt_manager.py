"""
JWT管理器单元测试

测试JWT管理器的所有核心功能：
- 令牌创建和验证
- 令牌刷新机制
- 令牌黑名单管理
- 算法安全性验证
- 过期时间处理

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import pytest
import pytest_asyncio
import time
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from auth_service.core.jwt_manager import JWTManager, TokenValidationResult
from auth_service.models.auth_models import TokenPayload, TokenPair


class TestJWTManager:
    """JWT管理器测试类"""
    
    @pytest_asyncio.fixture
    async def jwt_manager_with_mock_redis(self, test_settings):
        """带模拟Redis的JWT管理器"""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.exists.return_value = False
        
        return JWTManager(
            secret_key=test_settings.secret_key,
            algorithm=test_settings.algorithm,
            redis_client=mock_redis,
            settings=test_settings
        )
    
    def test_jwt_manager_initialization(self, jwt_manager):
        """测试JWT管理器初始化"""
        assert jwt_manager.secret_key is not None
        assert jwt_manager.algorithm == "HS256"
        assert jwt_manager.redis_client is not None
        assert jwt_manager.settings is not None
    
    @pytest.mark.asyncio
    async def test_create_access_token(self, jwt_manager_with_mock_redis):
        """测试访问令牌创建"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "role": "end_user",
            "permissions": ["user:read"],
            "is_active": True,
            "email_verified": True,
            "mfa_enabled": False
        }
        
        access_token = await jwt_manager_with_mock_redis.create_access_token(test_payload)
        
        assert access_token is not None
        assert isinstance(access_token, str)
        assert len(access_token) > 100  # JWT令牌应该相当长
        
        # 验证令牌格式（JWT有三个部分，用.分隔）
        parts = access_token.split('.')
        assert len(parts) == 3
    
    @pytest.mark.asyncio
    async def test_create_refresh_token(self, jwt_manager_with_mock_redis):
        """测试刷新令牌创建"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "tenant_id": "tenant-123"
        }
        
        refresh_token = await jwt_manager_with_mock_redis.create_refresh_token(test_payload)
        
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 100
        
        # 验证令牌格式
        parts = refresh_token.split('.')
        assert len(parts) == 3
    
    @pytest.mark.asyncio
    async def test_create_token_pair(self, jwt_manager_with_mock_redis):
        """测试令牌对创建"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "role": "end_user",
            "permissions": ["user:read"],
            "is_active": True,
            "email_verified": True,
            "mfa_enabled": False
        }
        
        token_pair = await jwt_manager_with_mock_redis.create_token_pair(test_payload)
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.token_type == "Bearer"
        assert token_pair.expires_in > 0
        
        # 验证两个令牌都是有效的JWT格式
        assert len(token_pair.access_token.split('.')) == 3
        assert len(token_pair.refresh_token.split('.')) == 3
    
    @pytest.mark.asyncio
    async def test_verify_valid_token(self, jwt_manager_with_mock_redis):
        """测试验证有效令牌"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "role": "end_user",
            "permissions": ["user:read"],
            "is_active": True,
            "email_verified": True,
            "mfa_enabled": False
        }
        
        # 创建令牌
        access_token = await jwt_manager_with_mock_redis.create_access_token(test_payload)
        
        # 验证令牌
        result = await jwt_manager_with_mock_redis.verify_token(access_token, "access")
        
        assert isinstance(result, TokenValidationResult)
        assert result.is_valid is True
        assert result.payload is not None
        assert result.payload.sub == "test-user-123"
        assert result.payload.email == "test@example.com"
        assert result.payload.role == "end_user"
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, jwt_manager_with_mock_redis):
        """测试验证无效令牌"""
        invalid_token = "invalid.jwt.token"
        
        result = await jwt_manager_with_mock_redis.verify_token(invalid_token, "access")
        
        assert isinstance(result, TokenValidationResult)
        assert result.is_valid is False
        assert result.payload is None
        assert result.error_message is not None
        assert "令牌格式无效" in result.error_message
    
    @pytest.mark.asyncio
    async def test_verify_expired_token(self, jwt_manager_with_mock_redis):
        """测试验证过期令牌"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "tenant_id": "tenant-123"
        }
        
        # 创建一个立即过期的令牌
        with patch.object(jwt_manager_with_mock_redis.settings, 'access_token_expire_minutes', -1):
            expired_token = await jwt_manager_with_mock_redis.create_access_token(test_payload)
        
        # 验证过期令牌
        result = await jwt_manager_with_mock_redis.verify_token(expired_token, "access")
        
        assert result.is_valid is False
        assert "令牌已过期" in result.error_message
    
    @pytest.mark.asyncio
    async def test_verify_blacklisted_token(self, jwt_manager_with_mock_redis):
        """测试验证黑名单令牌"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "tenant_id": "tenant-123"
        }
        
        # 创建令牌
        access_token = await jwt_manager_with_mock_redis.create_access_token(test_payload)
        
        # 模拟Redis返回黑名单状态
        jwt_manager_with_mock_redis.redis_client.get.return_value = True
        
        # 验证黑名单令牌
        result = await jwt_manager_with_mock_redis.verify_token(access_token, "access")
        
        assert result.is_valid is False
        assert "令牌已被撤销" in result.error_message
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, jwt_manager_with_mock_redis):
        """测试成功刷新令牌"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "role": "end_user",
            "permissions": ["user:read"],
            "is_active": True,
            "email_verified": True,
            "mfa_enabled": False
        }
        
        # 创建原始令牌对
        original_token_pair = await jwt_manager_with_mock_redis.create_token_pair(test_payload)
        
        # 刷新令牌
        new_token_pair = await jwt_manager_with_mock_redis.refresh_token(
            original_token_pair.refresh_token
        )
        
        assert isinstance(new_token_pair, TokenPair)
        assert new_token_pair.access_token != original_token_pair.access_token
        assert new_token_pair.refresh_token != original_token_pair.refresh_token
        
        # 验证新令牌有效
        result = await jwt_manager_with_mock_redis.verify_token(
            new_token_pair.access_token, "access"
        )
        assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_refresh_token_with_invalid_token(self, jwt_manager_with_mock_redis):
        """测试用无效令牌刷新"""
        invalid_refresh_token = "invalid.refresh.token"
        
        new_token_pair = await jwt_manager_with_mock_redis.refresh_token(invalid_refresh_token)
        
        assert new_token_pair is None
    
    @pytest.mark.asyncio
    async def test_revoke_token(self, jwt_manager_with_mock_redis):
        """测试撤销令牌"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "tenant_id": "tenant-123"
        }
        
        # 创建令牌
        access_token = await jwt_manager_with_mock_redis.create_access_token(test_payload)
        
        # 撤销令牌
        success = await jwt_manager_with_mock_redis.revoke_token(access_token)
        
        assert success is True
        jwt_manager_with_mock_redis.redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_revoke_user_tokens(self, jwt_manager_with_mock_redis):
        """测试撤销用户所有令牌"""
        user_id = "test-user-123"
        tenant_id = "tenant-123"
        
        # 撤销用户所有令牌
        success = await jwt_manager_with_mock_redis.revoke_user_tokens(user_id, tenant_id)
        
        assert success is True
        jwt_manager_with_mock_redis.redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, jwt_manager_with_mock_redis):
        """测试清理过期令牌"""
        # 模拟Redis scan返回一些令牌键
        jwt_manager_with_mock_redis.redis_client.scan_iter.return_value = [
            b"jwt_blacklist:token1",
            b"jwt_blacklist:token2"
        ]
        
        # 模拟TTL检查（token1过期，token2未过期）
        jwt_manager_with_mock_redis.redis_client.ttl.side_effect = [-1, 3600]
        
        cleaned_count = await jwt_manager_with_mock_redis.cleanup_expired_tokens()
        
        assert cleaned_count >= 0
        # 应该删除过期的token1
        jwt_manager_with_mock_redis.redis_client.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_token_info(self, jwt_manager_with_mock_redis):
        """测试获取令牌信息"""
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "username": "testuser",
            "tenant_id": "tenant-123",
            "role": "end_user",
            "permissions": ["user:read"],
            "is_active": True,
            "email_verified": True,
            "mfa_enabled": False
        }
        
        # 创建令牌
        access_token = await jwt_manager_with_mock_redis.create_access_token(test_payload)
        
        # 获取令牌信息
        token_info = await jwt_manager_with_mock_redis.get_token_info(access_token)
        
        assert token_info is not None
        assert token_info["valid"] is True
        assert token_info["user_id"] == "test-user-123"
        assert token_info["email"] == "test@example.com"
        assert token_info["role"] == "end_user"
        assert "issued_at" in token_info
        assert "expires_at" in token_info
    
    @pytest.mark.asyncio
    async def test_different_algorithms(self, test_settings, redis_client):
        """测试不同的JWT算法"""
        algorithms_to_test = ["HS256", "HS384", "HS512"]
        
        for algorithm in algorithms_to_test:
            # 为每个算法创建管理器
            jwt_manager = JWTManager(
                secret_key=test_settings.secret_key,
                algorithm=algorithm,
                redis_client=redis_client,
                settings=test_settings
            )
            
            test_payload = {
                "sub": "test-user-123",
                "email": "test@example.com",
                "tenant_id": "tenant-123"
            }
            
            # 创建和验证令牌
            access_token = await jwt_manager.create_access_token(test_payload)
            result = await jwt_manager.verify_token(access_token, "access")
            
            assert result.is_valid is True
            assert result.payload.sub == "test-user-123"
    
    @pytest.mark.asyncio
    async def test_token_payload_validation(self, jwt_manager_with_mock_redis):
        """测试令牌载荷验证"""
        # 测试不完整的载荷
        incomplete_payload = {
            "sub": "test-user-123",
            # 缺少必要字段
        }
        
        try:
            access_token = await jwt_manager_with_mock_redis.create_access_token(incomplete_payload)
            result = await jwt_manager_with_mock_redis.verify_token(access_token, "access")
            
            # 应该能够处理不完整的载荷
            assert result.is_valid is True
            assert result.payload.sub == "test-user-123"
        except Exception as e:
            # 或者抛出验证错误
            assert "validation" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_token_operations(self, jwt_manager_with_mock_redis):
        """测试并发令牌操作"""
        import asyncio
        
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "tenant_id": "tenant-123"
        }
        
        # 并发创建多个令牌
        tasks = []
        for i in range(10):
            payload = test_payload.copy()
            payload["sub"] = f"test-user-{i}"
            tasks.append(jwt_manager_with_mock_redis.create_access_token(payload))
        
        tokens = await asyncio.gather(*tasks)
        
        # 验证所有令牌都创建成功且唯一
        assert len(tokens) == 10
        assert len(set(tokens)) == 10  # 所有令牌都应该唯一
        
        # 并发验证所有令牌
        verify_tasks = []
        for token in tokens:
            verify_tasks.append(jwt_manager_with_mock_redis.verify_token(token, "access"))
        
        results = await asyncio.gather(*verify_tasks)
        
        # 所有验证结果都应该成功
        for result in results:
            assert result.is_valid is True
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, test_settings):
        """测试Redis连接失败的处理"""
        # 创建一个会抛出异常的模拟Redis客户端
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Redis connection failed")
        mock_redis.get.side_effect = Exception("Redis connection failed")
        mock_redis.set.side_effect = Exception("Redis connection failed")
        
        jwt_manager = JWTManager(
            secret_key=test_settings.secret_key,
            algorithm=test_settings.algorithm,
            redis_client=mock_redis,
            settings=test_settings
        )
        
        test_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "tenant_id": "tenant-123"
        }
        
        # 令牌创建应该仍然工作（不依赖Redis）
        access_token = await jwt_manager.create_access_token(test_payload)
        assert access_token is not None
        
        # 令牌验证应该在没有黑名单检查的情况下工作
        result = await jwt_manager.verify_token(access_token, "access")
        assert result.is_valid is True
        
        # 撤销操作应该失败但不抛出异常
        success = await jwt_manager.revoke_token(access_token)
        assert success is False


class TestTokenValidationResult:
    """令牌验证结果测试"""
    
    def test_valid_result_creation(self):
        """测试创建有效结果"""
        payload = TokenPayload(
            sub="test-user-123",
            email="test@example.com",
            tenant_id="tenant-123",
            iat=int(time.time()),
            exp=int(time.time()) + 3600
        )
        
        result = TokenValidationResult(
            is_valid=True,
            payload=payload,
            error_message=None
        )
        
        assert result.is_valid is True
        assert result.payload == payload
        assert result.error_message is None
    
    def test_invalid_result_creation(self):
        """测试创建无效结果"""
        result = TokenValidationResult(
            is_valid=False,
            payload=None,
            error_message="令牌已过期"
        )
        
        assert result.is_valid is False
        assert result.payload is None
        assert result.error_message == "令牌已过期"


class TestTokenPair:
    """令牌对测试"""
    
    def test_token_pair_creation(self):
        """测试令牌对创建"""
        token_pair = TokenPair(
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            token_type="Bearer",
            expires_in=3600
        )
        
        assert token_pair.access_token == "access_token_value"
        assert token_pair.refresh_token == "refresh_token_value"
        assert token_pair.token_type == "Bearer"
        assert token_pair.expires_in == 3600
    
    def test_token_pair_dict_conversion(self):
        """测试令牌对字典转换"""
        token_pair = TokenPair(
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            token_type="Bearer",
            expires_in=3600
        )
        
        token_dict = token_pair.dict()
        
        assert token_dict["access_token"] == "access_token_value"
        assert token_dict["refresh_token"] == "refresh_token_value"
        assert token_dict["token_type"] == "Bearer"
        assert token_dict["expires_in"] == 3600