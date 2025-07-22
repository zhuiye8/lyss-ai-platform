"""
测试配置文件

为Auth Service的测试提供通用的fixture和配置：
- 测试数据库配置
- Redis测试实例
- 测试用户和数据
- 模拟服务配置

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from auth_service.main import app
from auth_service.config import Settings
from auth_service.utils.redis_client import RedisClient
from auth_service.core.jwt_manager import JWTManager
from auth_service.core.auth_manager import AuthManager
from auth_service.core.rbac_manager import RBACManager
from auth_service.core.session_manager import SessionManager
from auth_service.core.oauth2_manager import OAuth2Manager
from auth_service.core.mfa_manager import MFAManager
from auth_service.core.security_policy_manager import SecurityPolicyManager


# =====================================================
# 测试配置
# =====================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """测试环境配置"""
    return Settings(
        environment="test",
        debug=True,
        secret_key="test_secret_key_for_jwt_signing_32_chars",
        algorithm="HS256",
        access_token_expire_minutes=15,
        refresh_token_expire_days=1,
        
        # 测试Redis配置
        redis_host="localhost",
        redis_port=6379,
        redis_password="",
        redis_db=1,  # 使用独立的测试数据库
        
        # OAuth2测试配置
        auth_service_base_url="http://localhost:8001",
        google_client_id="test_google_client_id",
        google_client_secret="test_google_client_secret",
        github_client_id="test_github_client_id",
        github_client_secret="test_github_client_secret",
    )


@pytest_asyncio.fixture
async def redis_client(test_settings: Settings) -> AsyncGenerator[RedisClient, None]:
    """测试Redis客户端"""
    client = RedisClient()
    
    # 模拟Redis连接（用于CI/CD环境）
    mock_redis = AsyncMock()
    client._redis = mock_redis
    
    # 设置常用的模拟返回值
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = True
    mock_redis.exists.return_value = False
    mock_redis.expire.return_value = True
    mock_redis.ttl.return_value = -1
    
    yield client
    
    # 清理测试数据
    try:
        await client.disconnect()
    except:
        pass


# =====================================================
# 管理器测试实例
# =====================================================

@pytest_asyncio.fixture
async def jwt_manager(test_settings: Settings, redis_client: RedisClient) -> JWTManager:
    """JWT管理器测试实例"""
    return JWTManager(
        secret_key=test_settings.secret_key,
        algorithm=test_settings.algorithm,
        redis_client=redis_client,
        settings=test_settings
    )


@pytest_asyncio.fixture 
async def rbac_manager(redis_client: RedisClient) -> RBACManager:
    """RBAC管理器测试实例"""
    return RBACManager(redis_client=redis_client)


@pytest_asyncio.fixture
async def session_manager(test_settings: Settings, redis_client: RedisClient) -> SessionManager:
    """会话管理器测试实例"""
    return SessionManager(
        redis_client=redis_client,
        settings=test_settings
    )


@pytest_asyncio.fixture
async def oauth2_manager(test_settings: Settings, redis_client: RedisClient) -> OAuth2Manager:
    """OAuth2管理器测试实例"""
    return OAuth2Manager(
        redis_client=redis_client,
        settings=test_settings
    )


@pytest_asyncio.fixture
async def mfa_manager(test_settings: Settings, redis_client: RedisClient) -> MFAManager:
    """MFA管理器测试实例"""
    return MFAManager(
        redis_client=redis_client,
        settings=test_settings
    )


@pytest_asyncio.fixture
async def security_policy_manager(test_settings: Settings, redis_client: RedisClient) -> SecurityPolicyManager:
    """安全策略管理器测试实例"""
    manager = SecurityPolicyManager(
        redis_client=redis_client,
        settings=test_settings
    )
    
    # 初始化测试策略
    await manager.initialize_policies()
    
    return manager


@pytest_asyncio.fixture
async def auth_manager(
    test_settings: Settings,
    redis_client: RedisClient,
    jwt_manager: JWTManager,
    rbac_manager: RBACManager,
    session_manager: SessionManager
) -> AuthManager:
    """认证管理器测试实例"""
    return AuthManager(
        jwt_manager=jwt_manager,
        rbac_manager=rbac_manager,
        session_manager=session_manager,
        redis_client=redis_client,
        settings=test_settings
    )


# =====================================================
# 测试客户端和应用
# =====================================================

@pytest.fixture
def client() -> TestClient:
    """FastAPI测试客户端"""
    return TestClient(app)


@pytest_asyncio.fixture
async def authenticated_client(client: TestClient, jwt_manager: JWTManager) -> TestClient:
    """已认证的测试客户端"""
    # 创建测试用户令牌
    test_user_data = {
        "sub": "test-user-id-12345",
        "email": "test@example.com",
        "username": "testuser",
        "tenant_id": "test-tenant-id",
        "role": "end_user",
        "permissions": ["user:read", "user:update"],
        "is_active": True,
        "email_verified": True,
        "mfa_enabled": False
    }
    
    # 生成测试令牌
    token_pair = await jwt_manager.create_token_pair(test_user_data)
    
    # 设置认证头
    client.headers.update({
        "Authorization": f"Bearer {token_pair.access_token}"
    })
    
    return client


@pytest_asyncio.fixture
async def admin_client(client: TestClient, jwt_manager: JWTManager) -> TestClient:
    """管理员身份的测试客户端"""
    # 创建管理员用户令牌
    admin_user_data = {
        "sub": "admin-user-id-12345",
        "email": "admin@example.com",
        "username": "admin",
        "tenant_id": "test-tenant-id",
        "role": "super_admin",
        "permissions": [
            "system:admin", "system:monitor", "tenant:manage",
            "user:manage", "user:read", "user:update", "user:delete"
        ],
        "is_active": True,
        "email_verified": True,
        "mfa_enabled": False
    }
    
    # 生成管理员令牌
    token_pair = await jwt_manager.create_token_pair(admin_user_data)
    
    # 设置认证头
    client.headers.update({
        "Authorization": f"Bearer {token_pair.access_token}"
    })
    
    return client


# =====================================================
# 测试数据
# =====================================================

@pytest.fixture
def test_user_data() -> dict:
    """测试用户数据"""
    return {
        "id": "test-user-id-12345",
        "tenant_id": "test-tenant-id",
        "email": "test@example.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "role_name": "end_user",
        "permissions": ["user:read", "user:update"],
        "is_active": True,
        "email_verified": True,
        "mfa_enabled": False
    }


@pytest.fixture
def test_admin_data() -> dict:
    """测试管理员数据"""
    return {
        "id": "admin-user-id-12345", 
        "tenant_id": "test-tenant-id",
        "email": "admin@example.com",
        "username": "admin",
        "first_name": "Admin",
        "last_name": "User",
        "role_name": "super_admin",
        "permissions": [
            "system:admin", "system:monitor", "tenant:manage",
            "user:manage", "user:read", "user:update", "user:delete"
        ],
        "is_active": True,
        "email_verified": True,
        "mfa_enabled": False
    }


@pytest.fixture
def valid_password() -> str:
    """有效的测试密码"""
    return "TestPassword123!"


@pytest.fixture
def invalid_passwords() -> list:
    """无效的测试密码列表"""
    return [
        "",               # 空密码
        "123",            # 太短
        "password",       # 太简单
        "PASSWORD",       # 缺少小写
        "password123",    # 缺少大写
        "Password",       # 缺少数字
        "Password123",    # 缺少特殊字符
        "a" * 200         # 太长
    ]


# =====================================================
# OAuth2测试数据
# =====================================================

@pytest.fixture
def oauth2_google_user_info() -> dict:
    """Google OAuth2用户信息"""
    return {
        "id": "google-user-12345",
        "email": "user@gmail.com",
        "name": "Google User",
        "picture": "https://example.com/avatar.jpg",
        "verified_email": True
    }


@pytest.fixture
def oauth2_github_user_info() -> dict:
    """GitHub OAuth2用户信息"""
    return {
        "id": 12345,
        "login": "githubuser",
        "email": "user@example.com",
        "name": "GitHub User",
        "avatar_url": "https://github.com/avatar.jpg"
    }


# =====================================================
# 测试工具函数
# =====================================================

@pytest.fixture
def mock_time():
    """模拟时间函数"""
    def _mock_time(timestamp: float = 1640995200.0):  # 2022-01-01 00:00:00
        import time
        original_time = time.time
        time.time = lambda: timestamp
        return original_time
    return _mock_time


@pytest.fixture
def assert_log_contains():
    """断言日志包含特定内容的辅助函数"""
    def _assert_log_contains(caplog, level: str, message: str):
        """
        断言日志中包含特定级别和消息
        
        Args:
            caplog: pytest的日志捕获fixture
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
            message: 期望的日志消息内容
        """
        found = False
        for record in caplog.records:
            if record.levelname == level and message in record.message:
                found = True
                break
        
        assert found, f"日志中未找到级别为{level}且包含'{message}'的记录"
    
    return _assert_log_contains


# =====================================================
# 清理函数
# =====================================================

@pytest_asyncio.fixture(autouse=True)
async def cleanup_redis(redis_client: RedisClient):
    """自动清理Redis测试数据"""
    yield
    
    # 测试完成后清理Redis中的测试数据
    try:
        if hasattr(redis_client, '_redis') and redis_client._redis:
            # 清理所有测试相关的键
            test_keys = [
                "test:*", "jwt:*", "session:*", "mfa:*",
                "oauth2:*", "policy:*", "blocked_ip:*"
            ]
            
            for pattern in test_keys:
                await redis_client._redis.flushdb()  # 清空测试数据库
                break  # 只需要执行一次
    except:
        pass