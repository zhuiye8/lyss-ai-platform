"""
OAuth2管理器单元测试

测试OAuth2管理器的所有核心功能：
- OAuth2授权流程
- PKCE安全增强
- 多供应商支持（Google、GitHub、Microsoft）
- 状态验证和安全性
- 用户信息获取和处理

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import pytest
import pytest_asyncio
import secrets
import base64
from unittest.mock import AsyncMock, patch, MagicMock

from auth_service.core.oauth2_manager import OAuth2Manager
from auth_service.models.auth_models import OAuth2AuthorizeRequest, OAuth2CallbackRequest


class TestOAuth2Manager:
    """OAuth2管理器测试类"""
    
    @pytest_asyncio.fixture
    async def mock_redis_client(self):
        """模拟Redis客户端"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.exists.return_value = False
        return mock_redis
    
    @pytest_asyncio.fixture
    async def oauth2_manager(self, test_settings, mock_redis_client):
        """OAuth2管理器实例"""
        return OAuth2Manager(
            redis_client=mock_redis_client,
            settings=test_settings
        )
    
    def test_oauth2_manager_initialization(self, oauth2_manager):
        """测试OAuth2管理器初始化"""
        assert oauth2_manager.redis_client is not None
        assert oauth2_manager.settings is not None
        assert "google" in oauth2_manager.providers
        assert "github" in oauth2_manager.providers
        assert "microsoft" in oauth2_manager.providers
    
    @pytest.mark.asyncio
    async def test_generate_pkce_challenge(self, oauth2_manager):
        """测试PKCE挑战生成"""
        code_verifier, code_challenge = oauth2_manager._generate_pkce_challenge()
        
        assert code_verifier is not None
        assert code_challenge is not None
        assert isinstance(code_verifier, str)
        assert isinstance(code_challenge, str)
        assert len(code_verifier) >= 43  # PKCE规范要求
        assert len(code_challenge) > 0
        
        # 验证代码挑战是base64url编码
        try:
            # 添加填充并解码以验证格式
            padded = code_challenge + '=' * (4 - len(code_challenge) % 4)
            base64.urlsafe_b64decode(padded)
        except Exception:
            pytest.fail("代码挑战不是有效的base64url格式")
    
    @pytest.mark.asyncio
    async def test_generate_auth_url_google(self, oauth2_manager, mock_redis_client):
        """测试生成Google OAuth2授权URL"""
        request = OAuth2AuthorizeRequest(
            provider="google",
            tenant_id="tenant-123",
            redirect_uri="http://localhost:3000/callback",
            scopes=["openid", "email", "profile"]
        )
        
        auth_url, state = await oauth2_manager.generate_auth_url(request)
        
        assert auth_url is not None
        assert state is not None
        assert "accounts.google.com" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=openid+email+profile" in auth_url
        assert f"state={state}" in auth_url
        assert "code_challenge=" in auth_url
        assert "code_challenge_method=S256" in auth_url
        
        # 验证状态信息被保存到Redis
        mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_generate_auth_url_github(self, oauth2_manager, mock_redis_client):
        """测试生成GitHub OAuth2授权URL"""
        request = OAuth2AuthorizeRequest(
            provider="github",
            tenant_id="tenant-123",
            redirect_uri="http://localhost:3000/callback",
            scopes=["user:email", "read:user"]
        )
        
        auth_url, state = await oauth2_manager.generate_auth_url(request)
        
        assert auth_url is not None
        assert state is not None
        assert "github.com/login/oauth/authorize" in auth_url
        assert "scope=user%3Aemail+read%3Auser" in auth_url
        assert f"state={state}" in auth_url
        
        # GitHub不支持PKCE，所以不应该有code_challenge参数
        assert "code_challenge=" not in auth_url
    
    @pytest.mark.asyncio
    async def test_generate_auth_url_microsoft(self, oauth2_manager, mock_redis_client):
        """测试生成Microsoft OAuth2授权URL"""
        request = OAuth2AuthorizeRequest(
            provider="microsoft",
            tenant_id="tenant-123",
            redirect_uri="http://localhost:3000/callback",
            scopes=["openid", "profile", "email"]
        )
        
        auth_url, state = await oauth2_manager.generate_auth_url(request)
        
        assert auth_url is not None
        assert state is not None
        assert "login.microsoftonline.com" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=openid+profile+email" in auth_url
        assert f"state={state}" in auth_url
        assert "code_challenge=" in auth_url  # Microsoft支持PKCE
        assert "code_challenge_method=S256" in auth_url
    
    @pytest.mark.asyncio
    async def test_generate_auth_url_invalid_provider(self, oauth2_manager):
        """测试生成不支持供应商的授权URL"""
        request = OAuth2AuthorizeRequest(
            provider="invalid_provider",
            tenant_id="tenant-123",
            redirect_uri="http://localhost:3000/callback",
            scopes=["openid"]
        )
        
        auth_url, state = await oauth2_manager.generate_auth_url(request)
        
        assert auth_url is None
        assert state is None
    
    @pytest.mark.asyncio
    async def test_handle_callback_success_google(self, oauth2_manager, mock_redis_client):
        """测试处理Google OAuth2回调成功"""
        state = "test-state-123"
        authorization_code = "test-auth-code"
        
        # 模拟Redis返回状态数据
        mock_state_data = {
            "provider": "google",
            "tenant_id": "tenant-123",
            "redirect_uri": "http://localhost:3000/callback",
            "code_verifier": "test-code-verifier",
            "created_at": 1640995200
        }
        mock_redis_client.get.return_value = mock_state_data
        
        # 模拟HTTP请求
        mock_token_response = {
            "access_token": "google-access-token",
            "token_type": "Bearer",
            "expires_in": 3600,
            "id_token": "google-id-token"
        }
        
        mock_user_info = {
            "id": "google-user-123",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            # 模拟令牌交换请求
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json.return_value = mock_token_response
            # 模拟用户信息请求
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value.json.return_value = mock_user_info
            
            callback_request = OAuth2CallbackRequest(
                provider="google",
                code=authorization_code,
                state=state
            )
            
            result = await oauth2_manager.handle_callback(callback_request)
            
            assert result is not None
            assert result["success"] is True
            assert result["provider"] == "google"
            assert result["user_info"]["email"] == "user@gmail.com"
            assert result["user_info"]["name"] == "Test User"
            assert "access_token" in result
            
            # 验证状态被删除
            mock_redis_client.delete.assert_called_with(f"oauth2_state:{state}")
    
    @pytest.mark.asyncio
    async def test_handle_callback_success_github(self, oauth2_manager, mock_redis_client):
        """测试处理GitHub OAuth2回调成功"""
        state = "test-state-456"
        authorization_code = "test-github-code"
        
        # 模拟Redis返回状态数据
        mock_state_data = {
            "provider": "github",
            "tenant_id": "tenant-123",
            "redirect_uri": "http://localhost:3000/callback",
            "created_at": 1640995200
        }
        mock_redis_client.get.return_value = mock_state_data
        
        # 模拟GitHub API响应
        mock_token_response = {
            "access_token": "github-access-token",
            "token_type": "bearer",
            "scope": "user:email"
        }
        
        mock_user_info = {
            "id": 12345,
            "login": "testuser",
            "email": "user@example.com",
            "name": "Test User",
            "avatar_url": "https://github.com/avatar.jpg"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            # 模拟令牌交换和用户信息请求
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json.return_value = mock_token_response
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value.json.return_value = mock_user_info
            
            callback_request = OAuth2CallbackRequest(
                provider="github",
                code=authorization_code,
                state=state
            )
            
            result = await oauth2_manager.handle_callback(callback_request)
            
            assert result is not None
            assert result["success"] is True
            assert result["provider"] == "github"
            assert result["user_info"]["email"] == "user@example.com"
            assert result["user_info"]["login"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_handle_callback_invalid_state(self, oauth2_manager, mock_redis_client):
        """测试处理回调时状态无效"""
        # 模拟Redis没有找到状态数据
        mock_redis_client.get.return_value = None
        
        callback_request = OAuth2CallbackRequest(
            provider="google",
            code="test-code",
            state="invalid-state"
        )
        
        result = await oauth2_manager.handle_callback(callback_request)
        
        assert result is not None
        assert result["success"] is False
        assert "无效的状态参数" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_callback_expired_state(self, oauth2_manager, mock_redis_client):
        """测试处理回调时状态过期"""
        state = "expired-state"
        
        # 模拟过期的状态数据（超过10分钟）
        import time
        expired_time = time.time() - 700  # 11分钟前
        
        mock_state_data = {
            "provider": "google",
            "tenant_id": "tenant-123",
            "redirect_uri": "http://localhost:3000/callback",
            "code_verifier": "test-code-verifier",
            "created_at": expired_time
        }
        mock_redis_client.get.return_value = mock_state_data
        
        callback_request = OAuth2CallbackRequest(
            provider="google",
            code="test-code",
            state=state
        )
        
        result = await oauth2_manager.handle_callback(callback_request)
        
        assert result is not None
        assert result["success"] is False
        assert "状态已过期" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_callback_token_exchange_failure(self, oauth2_manager, mock_redis_client):
        """测试令牌交换失败"""
        state = "test-state"
        
        mock_state_data = {
            "provider": "google",
            "tenant_id": "tenant-123",
            "redirect_uri": "http://localhost:3000/callback",
            "code_verifier": "test-code-verifier",
            "created_at": 1640995200
        }
        mock_redis_client.get.return_value = mock_state_data
        
        # 模拟令牌交换失败
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = MagicMock()
            mock_response.status = 400
            mock_response.json.return_value = {"error": "invalid_grant"}
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            callback_request = OAuth2CallbackRequest(
                provider="google",
                code="invalid-code",
                state=state
            )
            
            result = await oauth2_manager.handle_callback(callback_request)
            
            assert result is not None
            assert result["success"] is False
            assert "令牌交换失败" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_callback_user_info_failure(self, oauth2_manager, mock_redis_client):
        """测试获取用户信息失败"""
        state = "test-state"
        
        mock_state_data = {
            "provider": "google",
            "tenant_id": "tenant-123",
            "redirect_uri": "http://localhost:3000/callback",
            "code_verifier": "test-code-verifier",
            "created_at": 1640995200
        }
        mock_redis_client.get.return_value = mock_state_data
        
        # 模拟令牌交换成功但用户信息获取失败
        mock_token_response = {
            "access_token": "valid-token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            # 令牌交换成功
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value.json.return_value = mock_token_response
            
            # 用户信息请求失败
            mock_user_response = MagicMock()
            mock_user_response.status = 401
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_user_response
            
            callback_request = OAuth2CallbackRequest(
                provider="google",
                code="valid-code",
                state=state
            )
            
            result = await oauth2_manager.handle_callback(callback_request)
            
            assert result is not None
            assert result["success"] is False
            assert "获取用户信息失败" in result["error"]
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_states(self, oauth2_manager, mock_redis_client):
        """测试清理过期状态"""
        # 模拟Redis scan返回状态键
        mock_redis_client.scan_iter.return_value = [
            b"oauth2_state:state1",
            b"oauth2_state:state2",
            b"oauth2_state:state3"
        ]
        
        # 模拟过期状态检查
        import time
        current_time = time.time()
        expired_time = current_time - 700  # 11分钟前，已过期
        valid_time = current_time - 300    # 5分钟前，未过期
        
        mock_redis_client.get.side_effect = [
            {"created_at": expired_time},  # state1 - 已过期
            {"created_at": valid_time},    # state2 - 未过期
            None                           # state3 - 不存在
        ]
        
        cleaned_count = await oauth2_manager.cleanup_expired_states()
        
        # 应该清理过期的state1
        assert cleaned_count >= 1
        mock_redis_client.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_provider_config(self, oauth2_manager):
        """测试获取供应商配置"""
        # 测试Google配置
        google_config = oauth2_manager._get_provider_config("google")
        assert google_config is not None
        assert "auth_url" in google_config
        assert "token_url" in google_config
        assert "user_info_url" in google_config
        assert "client_id" in google_config
        assert "client_secret" in google_config
        
        # 测试GitHub配置
        github_config = oauth2_manager._get_provider_config("github")
        assert github_config is not None
        assert "auth_url" in github_config
        assert "token_url" in github_config
        
        # 测试不存在的供应商
        invalid_config = oauth2_manager._get_provider_config("invalid")
        assert invalid_config is None
    
    @pytest.mark.asyncio
    async def test_validate_callback_request(self, oauth2_manager):
        """测试回调请求验证"""
        # 有效请求
        valid_request = OAuth2CallbackRequest(
            provider="google",
            code="valid-code",
            state="valid-state"
        )
        
        is_valid, error = oauth2_manager._validate_callback_request(valid_request)
        assert is_valid is True
        assert error is None
        
        # 无效请求 - 缺少代码
        invalid_request = OAuth2CallbackRequest(
            provider="google",
            code="",
            state="valid-state"
        )
        
        is_valid, error = oauth2_manager._validate_callback_request(invalid_request)
        assert is_valid is False
        assert "授权码不能为空" in error
        
        # 无效请求 - 缺少状态
        invalid_request = OAuth2CallbackRequest(
            provider="google",
            code="valid-code",
            state=""
        )
        
        is_valid, error = oauth2_manager._validate_callback_request(invalid_request)
        assert is_valid is False
        assert "状态参数不能为空" in error
    
    @pytest.mark.asyncio
    async def test_normalize_user_info_google(self, oauth2_manager):
        """测试规范化Google用户信息"""
        google_user_info = {
            "id": "google-123",
            "email": "user@gmail.com",
            "name": "Test User",
            "picture": "https://example.com/avatar.jpg",
            "verified_email": True,
            "given_name": "Test",
            "family_name": "User"
        }
        
        normalized = oauth2_manager._normalize_user_info("google", google_user_info)
        
        assert normalized["id"] == "google-123"
        assert normalized["email"] == "user@gmail.com"
        assert normalized["name"] == "Test User"
        assert normalized["avatar_url"] == "https://example.com/avatar.jpg"
        assert normalized["verified_email"] is True
        assert normalized["first_name"] == "Test"
        assert normalized["last_name"] == "User"
    
    @pytest.mark.asyncio
    async def test_normalize_user_info_github(self, oauth2_manager):
        """测试规范化GitHub用户信息"""
        github_user_info = {
            "id": 12345,
            "login": "testuser",
            "email": "user@example.com",
            "name": "Test User",
            "avatar_url": "https://github.com/avatar.jpg",
            "bio": "Developer"
        }
        
        normalized = oauth2_manager._normalize_user_info("github", github_user_info)
        
        assert normalized["id"] == "12345"  # 转换为字符串
        assert normalized["username"] == "testuser"
        assert normalized["email"] == "user@example.com"
        assert normalized["name"] == "Test User"
        assert normalized["avatar_url"] == "https://github.com/avatar.jpg"
        assert normalized["bio"] == "Developer"
    
    @pytest.mark.asyncio
    async def test_normalize_user_info_microsoft(self, oauth2_manager):
        """测试规范化Microsoft用户信息"""
        microsoft_user_info = {
            "id": "microsoft-456",
            "mail": "user@outlook.com",
            "displayName": "Test User",
            "givenName": "Test",
            "surname": "User",
            "userPrincipalName": "user@outlook.com"
        }
        
        normalized = oauth2_manager._normalize_user_info("microsoft", microsoft_user_info)
        
        assert normalized["id"] == "microsoft-456"
        assert normalized["email"] == "user@outlook.com"
        assert normalized["name"] == "Test User"
        assert normalized["first_name"] == "Test"
        assert normalized["last_name"] == "User"
        assert normalized["username"] == "user@outlook.com"
    
    @pytest.mark.asyncio
    async def test_concurrent_oauth_requests(self, oauth2_manager, mock_redis_client):
        """测试并发OAuth2请求"""
        import asyncio
        
        # 并发生成多个授权URL
        requests = []
        for i in range(5):
            request = OAuth2AuthorizeRequest(
                provider="google",
                tenant_id=f"tenant-{i}",
                redirect_uri="http://localhost:3000/callback",
                scopes=["openid", "email"]
            )
            requests.append(oauth2_manager.generate_auth_url(request))
        
        results = await asyncio.gather(*requests)
        
        # 所有请求都应该成功
        for auth_url, state in results:
            assert auth_url is not None
            assert state is not None
        
        # 所有状态应该唯一
        states = [state for _, state in results]
        assert len(set(states)) == len(states)
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, oauth2_manager):
        """测试Redis错误处理"""
        # 创建会抛出异常的模拟Redis客户端
        mock_redis_error = AsyncMock()
        mock_redis_error.set.side_effect = Exception("Redis connection failed")
        mock_redis_error.get.side_effect = Exception("Redis connection failed")
        mock_redis_error.delete.side_effect = Exception("Redis connection failed")
        
        oauth2_manager.redis_client = mock_redis_error
        
        # 生成授权URL应该失败
        request = OAuth2AuthorizeRequest(
            provider="google",
            tenant_id="tenant-123",
            redirect_uri="http://localhost:3000/callback",
            scopes=["openid"]
        )
        
        auth_url, state = await oauth2_manager.generate_auth_url(request)
        
        assert auth_url is None
        assert state is None
        
        # 处理回调应该失败
        callback_request = OAuth2CallbackRequest(
            provider="google",
            code="test-code",
            state="test-state"
        )
        
        result = await oauth2_manager.handle_callback(callback_request)
        
        assert result is not None
        assert result["success"] is False
        assert "服务异常" in result["error"] or "状态验证失败" in result["error"]