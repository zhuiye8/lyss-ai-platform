# 测试策略文档

## 1. 测试策略概述

### 1.1 测试金字塔
```
                    E2E Tests (5%)
                  ┌─────────────────┐
                 │   UI/API Tests   │
               ├─────────────────────┤
              │ Integration Tests   │
             │      (20%)           │
           ├─────────────────────────┤
          │    Unit Tests (75%)      │
         └─────────────────────────────┘
```

### 1.2 测试类型与覆盖率目标
- **单元测试**: 覆盖率 ≥ 85%，关注函数和类的逻辑
- **集成测试**: 覆盖率 ≥ 70%，关注服务间交互
- **端到端测试**: 关键用户流程100%覆盖
- **性能测试**: 关键API性能基准验证
- **安全测试**: 多租户隔离和权限验证
- **容错测试**: 故障恢复和降级机制

### 1.3 测试环境
```
开发环境 → 测试环境 → 预发布环境 → 生产环境
   ↓         ↓          ↓           ↓
单元测试   集成测试    E2E测试    监控验证
```

## 2. 单元测试

### 2.1 后端单元测试框架
```python
# tests/conftest.py
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis

# 测试数据库配置
TEST_DATABASE_URL = "postgresql+asyncpg://test_user:test_pass@localhost:5433/test_db"
TEST_REDIS_URL = "redis://localhost:6380/0"

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db_engine():
    """测试数据库引擎"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()

@pytest.fixture
async def test_db_session(test_db_engine):
    """测试数据库会话"""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def test_redis():
    """测试Redis连接"""
    redis_client = redis.from_url(TEST_REDIS_URL)
    yield redis_client
    await redis_client.flushdb()
    await redis_client.close()

@pytest.fixture
def test_client(test_db_session, test_redis):
    """测试客户端"""
    from main import app
    
    # 依赖注入覆盖
    app.dependency_overrides[get_db_session] = lambda: test_db_session
    app.dependency_overrides[get_redis] = lambda: test_redis
    
    with TestClient(app) as client:
        yield client
    
    app.dependency_overrides.clear()

@pytest.fixture
def mock_tenant():
    """模拟租户数据"""
    return {
        "tenant_id": "test-tenant-123",
        "tenant_name": "Test Tenant",
        "tenant_slug": "test-tenant",
        "status": "active",
        "config": {
            "max_users": 10,
            "max_api_calls_per_month": 10000
        }
    }

@pytest.fixture
def mock_user(mock_tenant):
    """模拟用户数据"""
    return {
        "user_id": "test-user-456",
        "tenant_id": mock_tenant["tenant_id"],
        "email": "test@example.com",
        "username": "testuser",
        "roles": ["end_user"]
    }
```

### 2.2 API测试示例
```python
# tests/test_auth.py
import pytest
from fastapi import status
from unittest.mock import AsyncMock, patch

class TestAuthenticationAPI:
    """认证API测试"""
    
    async def test_login_success(self, test_client, mock_user):
        """测试成功登录"""
        login_data = {
            "email": mock_user["email"],
            "password": "testpassword123"
        }
        
        with patch('services.auth_service.verify_password', return_value=True):
            with patch('services.user_service.get_user_by_email', return_value=mock_user):
                response = test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["user"]["email"] == mock_user["email"]
    
    async def test_login_invalid_credentials(self, test_client):
        """测试无效凭证登录"""
        login_data = {
            "email": "invalid@example.com",
            "password": "wrongpassword"
        }
        
        with patch('services.auth_service.verify_password', return_value=False):
            response = test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["success"] is False
        assert "Invalid credentials" in data["message"]
    
    async def test_login_missing_fields(self, test_client):
        """测试缺少字段的登录请求"""
        login_data = {"email": "test@example.com"}  # 缺少password
        
        response = test_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_refresh_token_success(self, test_client, mock_user):
        """测试刷新令牌成功"""
        refresh_token = "valid_refresh_token"
        
        with patch('services.auth_service.verify_refresh_token', return_value=mock_user):
            response = test_client.post(
                "/api/v1/auth/refresh",
                headers={"Authorization": f"Bearer {refresh_token}"}
            )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data["data"]

class TestConversationAPI:
    """对话API测试"""
    
    async def test_create_conversation(self, test_client, mock_user, auth_headers):
        """测试创建对话"""
        conversation_data = {
            "title": "Test Conversation",
            "metadata": {"tags": ["test"]}
        }
        
        with patch('services.conversation_service.create_conversation') as mock_create:
            mock_create.return_value = {
                "conversation_id": "conv-123",
                "title": "Test Conversation",
                "user_id": mock_user["user_id"],
                "created_at": "2025-07-08T10:00:00Z"
            }
            
            response = test_client.post(
                "/api/v1/conversations",
                json=conversation_data,
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Test Conversation"
    
    async def test_send_message_stream(self, test_client, auth_headers):
        """测试发送流式消息"""
        message_data = {
            "content": "Hello, AI!",
            "content_type": "text"
        }
        
        with patch('services.eino_service.process_message_stream') as mock_stream:
            mock_stream.return_value = AsyncMock()
            
            response = test_client.post(
                "/api/v1/conversations/conv-123/messages/stream",
                json=message_data,
                headers=auth_headers
            )
        
        assert response.status_code == status.HTTP_200_OK
        assert "text/event-stream" in response.headers.get("content-type", "")

@pytest.fixture
def auth_headers(mock_user):
    """认证头部"""
    token = create_test_jwt(mock_user)
    return {"Authorization": f"Bearer {token}"}

def create_test_jwt(user_data):
    """创建测试JWT令牌"""
    from services.auth_service import create_access_token
    return create_access_token(user_data)
```

### 2.3 业务逻辑测试
```python
# tests/test_tenant_service.py
import pytest
from unittest.mock import AsyncMock, patch
from services.tenant_service import TenantService
from models.tenant import Tenant, TenantConfig

class TestTenantService:
    """租户服务测试"""
    
    @pytest.fixture
    def tenant_service(self, test_db_session, test_redis):
        return TenantService(test_db_session, test_redis)
    
    async def test_create_tenant_success(self, tenant_service):
        """测试成功创建租户"""
        tenant_data = {
            "tenant_name": "Test Company",
            "tenant_slug": "test-company",
            "contact_email": "admin@testcompany.com",
            "company_name": "Test Company Inc."
        }
        
        with patch.object(tenant_service, '_validate_tenant_slug') as mock_validate:
            with patch.object(tenant_service.db_manager, 'create_tenant_database') as mock_create_db:
                mock_validate.return_value = True
                mock_create_db.return_value = {"connection_string": "test://conn"}
                
                tenant = await tenant_service.create_tenant(tenant_data)
        
        assert tenant.tenant_name == "Test Company"
        assert tenant.tenant_slug == "test-company"
        assert tenant.status == "active"
    
    async def test_create_tenant_duplicate_slug(self, tenant_service):
        """测试创建重复slug的租户"""
        tenant_data = {
            "tenant_name": "Test Company",
            "tenant_slug": "existing-slug",
            "contact_email": "admin@testcompany.com"
        }
        
        with patch.object(tenant_service, 'get_tenant_by_slug') as mock_get:
            mock_get.return_value = Tenant(tenant_id="existing", tenant_slug="existing-slug")
            
            with pytest.raises(ValueError, match="Tenant slug .* already exists"):
                await tenant_service.create_tenant(tenant_data)
    
    async def test_check_tenant_limits(self, tenant_service, mock_tenant):
        """测试租户限制检查"""
        with patch.object(tenant_service, 'get_tenant') as mock_get_tenant:
            with patch.object(tenant_service, 'get_tenant_usage_stats') as mock_get_stats:
                mock_get_tenant.return_value = Tenant(**mock_tenant)
                mock_get_stats.return_value = {
                    "user_count": 15,  # 超过限制的10
                    "monthly_api_calls": 5000,
                    "storage_usage_gb": 0.5
                }
                
                limits_check = await tenant_service.check_tenant_limits(mock_tenant["tenant_id"])
        
        assert limits_check["any_exceeded"] is True
        assert limits_check["limits"]["users"]["exceeded"] is True
        assert limits_check["limits"]["api_calls"]["exceeded"] is False

class TestMultiTenantIsolation:
    """多租户隔离测试"""
    
    async def test_tenant_data_isolation(self, test_db_session):
        """测试租户数据隔离"""
        # 创建两个不同租户的数据
        tenant1_data = create_test_data("tenant-1")
        tenant2_data = create_test_data("tenant-2")
        
        # 使用tenant-1的上下文查询数据
        with tenant_context("tenant-1"):
            results = await query_tenant_data(test_db_session)
            
        # 验证只能看到tenant-1的数据
        assert all(item.tenant_id == "tenant-1" for item in results)
        assert len(results) == len(tenant1_data)
    
    async def test_cache_isolation(self, test_redis):
        """测试缓存隔离"""
        cache_manager = TenantCacheManager(test_redis)
        
        # 为不同租户设置相同的key
        await cache_manager.set("tenant-1", "user:123", {"name": "User A"})
        await cache_manager.set("tenant-2", "user:123", {"name": "User B"})
        
        # 验证数据隔离
        tenant1_data = await cache_manager.get("tenant-1", "user:123")
        tenant2_data = await cache_manager.get("tenant-2", "user:123")
        
        assert tenant1_data["name"] == "User A"
        assert tenant2_data["name"] == "User B"
```

## 3. 集成测试

### 3.1 服务间集成测试
```python
# tests/integration/test_ai_workflow.py
import pytest
from unittest.mock import AsyncMock, patch
import httpx

class TestAIWorkflowIntegration:
    """AI工作流集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self, test_client, mock_user, auth_headers):
        """测试完整的对话流程"""
        # 1. 创建对话
        conversation_data = {"title": "Integration Test Chat"}
        response = test_client.post(
            "/api/v1/conversations",
            json=conversation_data,
            headers=auth_headers
        )
        conversation_id = response.json()["data"]["conversation_id"]
        
        # 2. 发送消息到EINO服务
        with patch('httpx.AsyncClient.post') as mock_eino_request:
            mock_eino_request.return_value = httpx.Response(
                200,
                json={"response": "Hello! How can I help you?", "tokens_used": 50}
            )
            
            message_data = {"content": "Hello, AI assistant!"}
            response = test_client.post(
                f"/api/v1/conversations/{conversation_id}/messages",
                json=message_data,
                headers=auth_headers
            )
        
        assert response.status_code == 200
        response_data = response.json()
        assert "Hello! How can I help you?" in response_data["data"]["content"]
        
        # 3. 验证记忆服务调用
        with patch('httpx.AsyncClient.post') as mock_memory_request:
            mock_memory_request.return_value = httpx.Response(200, json={"status": "success"})
            
            # 记忆应该被自动保存
            # 验证记忆服务被调用
            assert mock_memory_request.called
    
    @pytest.mark.asyncio
    async def test_provider_failover(self, test_client, auth_headers):
        """测试AI供应商故障转移"""
        conversation_id = "test-conv-123"
        message_data = {"content": "Test failover scenario"}
        
        # 模拟主供应商失败，备用供应商成功
        with patch('services.ai_provider.OpenAIProvider.call') as mock_primary:
            with patch('services.ai_provider.AnthropicProvider.call') as mock_backup:
                mock_primary.side_effect = Exception("OpenAI API Error")
                mock_backup.return_value = {"response": "Backup response", "tokens": 30}
                
                response = test_client.post(
                    f"/api/v1/conversations/{conversation_id}/messages",
                    json=message_data,
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        assert "Backup response" in response.json()["data"]["content"]
    
    @pytest.mark.asyncio
    async def test_memory_integration(self, test_client, auth_headers):
        """测试记忆系统集成"""
        # 发送包含个人信息的消息
        personal_info = {
            "content": "My name is John and I work as a software engineer at TechCorp"
        }
        
        with patch('services.memory_service.add_memory') as mock_add_memory:
            with patch('services.memory_service.search_memory') as mock_search_memory:
                mock_add_memory.return_value = {"status": "success"}
                mock_search_memory.return_value = {
                    "memories": [{"content": "John is a software engineer at TechCorp"}]
                }
                
                # 发送第一条消息
                response = test_client.post(
                    "/api/v1/conversations/conv-123/messages",
                    json=personal_info,
                    headers=auth_headers
                )
                
                # 验证记忆被添加
                assert mock_add_memory.called
                
                # 发送第二条消息，应该能够利用记忆
                followup = {"content": "What company do I work for?"}
                response = test_client.post(
                    "/api/v1/conversations/conv-123/messages",
                    json=followup,
                    headers=auth_headers
                )
                
                # 验证记忆被搜索
                assert mock_search_memory.called
```

### 3.2 数据库集成测试
```python
# tests/integration/test_database_operations.py
import pytest
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

class TestDatabaseIntegration:
    """数据库集成测试"""
    
    @pytest.mark.asyncio
    async def test_tenant_database_creation(self, test_db_engine):
        """测试租户数据库创建"""
        db_manager = TenantDatabaseManager("postgresql://master_user:pass@localhost:5432/master")
        
        tenant_id = "test-tenant-db-123"
        db_config = await db_manager.create_tenant_database(tenant_id)
        
        # 验证数据库配置
        assert "connection_string" in db_config
        assert f"tenant_{tenant_id.replace('-', '_')}" in db_config["database"]
        
        # 验证能够连接到新创建的租户数据库
        tenant_engine = create_async_engine(db_config["connection_string"])
        async with tenant_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
        
        await tenant_engine.dispose()
    
    @pytest.mark.asyncio
    async def test_encryption_decryption(self, test_db_session):
        """测试数据库加密解密"""
        from services.encryption import DataEncryption
        
        encryption = DataEncryption("test-master-key")
        sensitive_data = "sk-1234567890abcdef"
        
        # 加密数据
        encrypted_data, salt = encryption.encrypt_sensitive_data(sensitive_data)
        
        # 存储到数据库
        encrypted_record = {
            "provider_name": "OpenAI",
            "encrypted_api_key": encrypted_data,
            "salt": salt
        }
        
        # 从数据库读取并解密
        decrypted_data = encryption.decrypt_sensitive_data(encrypted_data, salt)
        
        assert decrypted_data == sensitive_data
        assert encrypted_data != sensitive_data  # 确保已加密
    
    @pytest.mark.asyncio
    async def test_audit_log_insertion(self, test_db_session):
        """测试审计日志插入"""
        from services.audit_service import AuditLogger
        
        audit_logger = AuditLogger(test_db_session)
        
        await audit_logger.log_authentication(
            user_id="user-123",
            tenant_id="tenant-456",
            action="login",
            result="success",
            details={"ip_address": "192.168.1.1"}
        )
        
        # 验证日志被正确插入
        result = await test_db_session.execute(
            text("SELECT * FROM audit_logs WHERE user_id = 'user-123'")
        )
        log_entry = result.fetchone()
        
        assert log_entry is not None
        assert log_entry.action == "login"
        assert log_entry.result == "success"
```

## 4. 端到端测试

### 4.1 E2E测试框架
```python
# tests/e2e/conftest.py
import pytest
from playwright.async_api import async_playwright
import docker
import time

@pytest.fixture(scope="session")
async def browser():
    """启动浏览器"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()

@pytest.fixture
async def page(browser):
    """创建页面"""
    context = await browser.new_context()
    page = await context.new_page()
    yield page
    await context.close()

@pytest.fixture(scope="session")
def test_environment():
    """启动测试环境"""
    client = docker.from_env()
    
    # 启动测试环境容器
    containers = []
    try:
        # 启动数据库
        postgres_container = client.containers.run(
            "postgres:15-alpine",
            environment={
                "POSTGRES_DB": "lyss_e2e_test",
                "POSTGRES_USER": "test_user",
                "POSTGRES_PASSWORD": "test_pass"
            },
            ports={'5432/tcp': 5434},
            detach=True,
            remove=True
        )
        containers.append(postgres_container)
        
        # 启动Redis
        redis_container = client.containers.run(
            "redis:7-alpine",
            ports={'6379/tcp': 6381},
            detach=True,
            remove=True
        )
        containers.append(redis_container)
        
        # 等待服务启动
        time.sleep(10)
        
        # 启动应用服务
        app_container = client.containers.run(
            "lyss/api-gateway:test",
            environment={
                "DATABASE_URL": "postgresql://test_user:test_pass@localhost:5434/lyss_e2e_test",
                "REDIS_URL": "redis://localhost:6381/0",
                "JWT_SECRET_KEY": "test-secret-key"
            },
            ports={'8000/tcp': 8001},
            detach=True,
            remove=True
        )
        containers.append(app_container)
        
        time.sleep(15)  # 等待应用启动
        
        yield "http://localhost:8001"
        
    finally:
        for container in containers:
            container.stop()
```

### 4.2 用户流程测试
```python
# tests/e2e/test_user_flows.py
import pytest
from playwright.async_api import Page

class TestUserFlows:
    """用户流程E2E测试"""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self, page: Page, test_environment: str):
        """测试完整用户旅程"""
        base_url = test_environment
        
        # 1. 访问登录页面
        await page.goto(f"{base_url}/login")
        await page.wait_for_selector('[data-testid="login-form"]')
        
        # 2. 登录
        await page.fill('[data-testid="email-input"]', 'test@example.com')
        await page.fill('[data-testid="password-input"]', 'testpassword123')
        await page.click('[data-testid="login-button"]')
        
        # 3. 验证跳转到聊天页面
        await page.wait_for_selector('[data-testid="chat-interface"]')
        assert "/chat" in page.url
        
        # 4. 发送消息
        await page.fill('[data-testid="message-input"]', 'Hello, AI assistant!')
        await page.click('[data-testid="send-button"]')
        
        # 5. 等待AI响应
        await page.wait_for_selector('[data-testid="ai-response"]', timeout=30000)
        
        # 6. 验证响应内容
        response_element = await page.query_selector('[data-testid="ai-response"]')
        response_text = await response_element.text_content()
        assert len(response_text) > 0
        assert "AI" in response_text or "assistant" in response_text
        
        # 7. 创建新对话
        await page.click('[data-testid="new-conversation-button"]')
        await page.wait_for_selector('[data-testid="conversation-title-input"]')
        await page.fill('[data-testid="conversation-title-input"]', 'E2E Test Conversation')
        await page.click('[data-testid="create-conversation-confirm"]')
        
        # 8. 验证新对话被创建
        await page.wait_for_selector('[data-testid="conversation-list"]')
        conversation_list = await page.query_selector('[data-testid="conversation-list"]')
        conversations = await conversation_list.query_selector_all('[data-testid="conversation-item"]')
        assert len(conversations) >= 2  # 至少有原来的对话和新创建的对话
        
        # 9. 访问设置页面
        await page.click('[data-testid="user-menu"]')
        await page.click('[data-testid="settings-link"]')
        await page.wait_for_selector('[data-testid="settings-page"]')
        
        # 10. 更新用户设置
        await page.click('[data-testid="theme-toggle"]')
        await page.click('[data-testid="save-settings-button"]')
        
        # 11. 验证设置保存成功
        await page.wait_for_selector('[data-testid="settings-saved-notification"]')
        
        # 12. 登出
        await page.click('[data-testid="user-menu"]')
        await page.click('[data-testid="logout-button"]')
        
        # 13. 验证返回登录页面
        await page.wait_for_selector('[data-testid="login-form"]')
        assert "/login" in page.url
    
    @pytest.mark.asyncio
    async def test_admin_workflow(self, page: Page, test_environment: str):
        """测试管理员工作流"""
        base_url = test_environment
        
        # 1. 管理员登录
        await page.goto(f"{base_url}/login")
        await page.fill('[data-testid="email-input"]', 'admin@example.com')
        await page.fill('[data-testid="password-input"]', 'adminpassword123')
        await page.click('[data-testid="login-button"]')
        
        # 2. 访问管理后台
        await page.goto(f"{base_url}/admin")
        await page.wait_for_selector('[data-testid="admin-dashboard"]')
        
        # 3. 用户管理
        await page.click('[data-testid="users-tab"]')
        await page.wait_for_selector('[data-testid="users-table"]')
        
        # 4. 创建新用户
        await page.click('[data-testid="create-user-button"]')
        await page.wait_for_selector('[data-testid="user-form"]')
        
        await page.fill('[data-testid="user-email-input"]', 'newuser@example.com')
        await page.fill('[data-testid="user-username-input"]', 'newuser')
        await page.fill('[data-testid="user-password-input"]', 'newuserpass123')
        await page.select_option('[data-testid="user-role-select"]', 'end_user')
        
        await page.click('[data-testid="create-user-submit"]')
        
        # 5. 验证用户创建成功
        await page.wait_for_selector('[data-testid="user-created-notification"]')
        
        # 6. AI供应商管理
        await page.click('[data-testid="providers-tab"]')
        await page.wait_for_selector('[data-testid="providers-table"]')
        
        await page.click('[data-testid="add-provider-button"]')
        await page.wait_for_selector('[data-testid="provider-form"]')
        
        await page.fill('[data-testid="provider-name-input"]', 'Test OpenAI')
        await page.select_option('[data-testid="provider-type-select"]', 'openai')
        await page.fill('[data-testid="provider-api-key-input"]', 'sk-test-key-123')
        
        await page.click('[data-testid="add-provider-submit"]')
        
        # 7. 验证供应商添加成功
        await page.wait_for_selector('[data-testid="provider-added-notification"]')
    
    @pytest.mark.asyncio
    async def test_error_scenarios(self, page: Page, test_environment: str):
        """测试错误场景"""
        base_url = test_environment
        
        # 1. 测试无效登录
        await page.goto(f"{base_url}/login")
        await page.fill('[data-testid="email-input"]', 'invalid@example.com')
        await page.fill('[data-testid="password-input"]', 'wrongpassword')
        await page.click('[data-testid="login-button"]')
        
        # 验证错误消息
        await page.wait_for_selector('[data-testid="login-error"]')
        error_element = await page.query_selector('[data-testid="login-error"]')
        error_text = await error_element.text_content()
        assert "invalid" in error_text.lower() or "incorrect" in error_text.lower()
        
        # 2. 测试网络错误处理
        # 通过拦截网络请求模拟错误
        await page.route("**/api/v1/**", lambda route: route.fulfill(status=500))
        
        # 尝试登录
        await page.fill('[data-testid="email-input"]', 'test@example.com')
        await page.fill('[data-testid="password-input"]', 'testpassword123')
        await page.click('[data-testid="login-button"]')
        
        # 验证网络错误处理
        await page.wait_for_selector('[data-testid="network-error"]')
```

## 5. 性能测试

### 5.1 负载测试
```python
# tests/performance/load_test.py
import asyncio
import aiohttp
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

class LoadTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []
    
    async def test_api_endpoint(self, session: aiohttp.ClientSession, endpoint: str, 
                               method: str = "GET", data: dict = None, headers: dict = None):
        """测试单个API端点"""
        start_time = time.time()
        try:
            async with session.request(method, f"{self.base_url}{endpoint}", 
                                     json=data, headers=headers) as response:
                content = await response.text()
                end_time = time.time()
                
                result = {
                    "endpoint": endpoint,
                    "status": response.status,
                    "response_time": end_time - start_time,
                    "success": 200 <= response.status < 300,
                    "timestamp": start_time
                }
                self.results.append(result)
                return result
        except Exception as e:
            end_time = time.time()
            result = {
                "endpoint": endpoint,
                "status": 0,
                "response_time": end_time - start_time,
                "success": False,
                "error": str(e),
                "timestamp": start_time
            }
            self.results.append(result)
            return result
    
    async def run_concurrent_test(self, endpoint: str, concurrent_users: int, 
                                 duration_seconds: int, auth_token: str = None):
        """运行并发测试"""
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            end_time = time.time() + duration_seconds
            
            while time.time() < end_time:
                # 创建并发任务
                for _ in range(concurrent_users):
                    if time.time() >= end_time:
                        break
                    task = asyncio.create_task(
                        self.test_api_endpoint(session, endpoint, headers=headers)
                    )
                    tasks.append(task)
                
                # 每秒执行一批请求
                await asyncio.sleep(1)
            
            # 等待所有任务完成
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def analyze_results(self):
        """分析测试结果"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        successful_requests = [r for r in self.results if r["success"]]
        failed_requests = [r for r in self.results if not r["success"]]
        
        response_times = [r["response_time"] for r in successful_requests]
        
        analysis = {
            "total_requests": len(self.results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(self.results) * 100,
            "average_response_time": statistics.mean(response_times) if response_times else 0,
            "median_response_time": statistics.median(response_times) if response_times else 0,
            "p95_response_time": self._percentile(response_times, 95) if response_times else 0,
            "p99_response_time": self._percentile(response_times, 99) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "requests_per_second": len(self.results) / (max(r["timestamp"] for r in self.results) - 
                                                       min(r["timestamp"] for r in self.results))
        }
        
        return analysis
    
    def _percentile(self, data, percentile):
        """计算百分位数"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]

# 性能测试用例
async def test_api_performance():
    """API性能测试"""
    tester = LoadTester("http://localhost:8000")
    
    # 获取认证令牌
    auth_token = await get_test_auth_token()
    
    # 测试关键端点
    test_scenarios = [
        {
            "name": "Chat API Load Test",
            "endpoint": "/api/v1/conversations/test-conv-123/messages",
            "concurrent_users": 50,
            "duration": 60,
            "auth_token": auth_token
        },
        {
            "name": "User Authentication Load Test",
            "endpoint": "/api/v1/auth/login",
            "concurrent_users": 100,
            "duration": 30
        },
        {
            "name": "Memory Search Load Test",
            "endpoint": "/api/v1/memory/search?query=test",
            "concurrent_users": 30,
            "duration": 45,
            "auth_token": auth_token
        }
    ]
    
    results = {}
    for scenario in test_scenarios:
        print(f"Running {scenario['name']}...")
        await tester.run_concurrent_test(
            scenario["endpoint"],
            scenario["concurrent_users"],
            scenario["duration"],
            scenario.get("auth_token")
        )
        
        analysis = tester.analyze_results()
        results[scenario["name"]] = analysis
        
        # 性能断言
        assert analysis["success_rate"] >= 95, f"Success rate too low: {analysis['success_rate']}%"
        assert analysis["p95_response_time"] <= 0.5, f"P95 latency too high: {analysis['p95_response_time']}s"
        assert analysis["requests_per_second"] >= 100, f"Throughput too low: {analysis['requests_per_second']} RPS"
        
        # 清除结果以便下个测试
        tester.results.clear()
    
    return results
```

## 6. 安全测试

### 6.1 多租户安全测试
```python
# tests/security/test_tenant_isolation.py
import pytest
import jwt
from unittest.mock import patch

class TestTenantSecurity:
    """租户安全测试"""
    
    async def test_tenant_data_isolation(self, test_client):
        """测试租户数据隔离"""
        # 创建两个不同租户的用户令牌
        tenant1_token = create_jwt_token({"user_id": "user1", "tenant_id": "tenant-1"})
        tenant2_token = create_jwt_token({"user_id": "user2", "tenant_id": "tenant-2"})
        
        # Tenant1用户尝试访问Tenant2的数据
        headers = {"Authorization": f"Bearer {tenant1_token}"}
        response = test_client.get(
            "/api/v1/admin/users?tenant_id=tenant-2",
            headers=headers
        )
        
        # 应该被拒绝访问
        assert response.status_code == 403
        assert "insufficient permissions" in response.json()["message"].lower()
    
    async def test_jwt_tampering_protection(self, test_client):
        """测试JWT篡改保护"""
        # 创建有效令牌
        valid_token = create_jwt_token({"user_id": "user1", "tenant_id": "tenant-1"})
        
        # 篡改令牌
        tampered_token = valid_token[:-5] + "XXXXX"
        
        headers = {"Authorization": f"Bearer {tampered_token}"}
        response = test_client.get("/api/v1/conversations", headers=headers)
        
        assert response.status_code == 401
        assert "invalid token" in response.json()["message"].lower()
    
    async def test_sql_injection_protection(self, test_client, auth_headers):
        """测试SQL注入保护"""
        # 尝试SQL注入攻击
        malicious_input = "'; DROP TABLE users; --"
        
        response = test_client.get(
            f"/api/v1/conversations?search={malicious_input}",
            headers=auth_headers
        )
        
        # 应该安全处理，不会导致SQL错误
        assert response.status_code in [200, 400]  # 正常响应或参数错误
        
        # 验证数据库仍然正常
        verify_response = test_client.get("/api/v1/conversations", headers=auth_headers)
        assert verify_response.status_code == 200
    
    async def test_xss_protection(self, test_client, auth_headers):
        """测试XSS保护"""
        # 尝试XSS攻击
        xss_payload = "<script>alert('XSS')</script>"
        
        conversation_data = {
            "title": xss_payload,
            "description": xss_payload
        }
        
        response = test_client.post(
            "/api/v1/conversations",
            json=conversation_data,
            headers=auth_headers
        )
        
        if response.status_code == 201:
            # 验证响应中的脚本被转义
            response_data = response.json()
            assert "<script>" not in response_data["data"]["title"]
            assert "&lt;script&gt;" in response_data["data"]["title"]
    
    async def test_rate_limiting(self, test_client, auth_headers):
        """测试速率限制"""
        endpoint = "/api/v1/conversations"
        
        # 快速发送大量请求
        responses = []
        for _ in range(150):  # 超过限制的100次/分钟
            response = test_client.get(endpoint, headers=auth_headers)
            responses.append(response.status_code)
        
        # 应该有一些请求被限制
        rate_limited_count = responses.count(429)
        assert rate_limited_count > 0, "Rate limiting not working"
    
    async def test_encrypted_data_storage(self, test_db_session):
        """测试敏感数据加密存储"""
        from services.encryption import DataEncryption
        
        # 存储加密的API密钥
        api_key = "sk-1234567890abcdef"
        encryption = DataEncryption("test-key")
        
        encrypted_key, salt = encryption.encrypt_sensitive_data(api_key)
        
        # 验证加密后的数据与原始数据不同
        assert encrypted_key != api_key
        assert len(encrypted_key) > len(api_key)
        
        # 验证可以正确解密
        decrypted_key = encryption.decrypt_sensitive_data(encrypted_key, salt)
        assert decrypted_key == api_key

def create_jwt_token(payload: dict) -> str:
    """创建测试JWT令牌"""
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")
```

## 7. 测试自动化

### 7.1 CI/CD测试流水线
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_db
        REDIS_URL: redis://localhost:6379/0
      run: |
        cd backend
        pytest tests/unit/ --cov=. --cov-report=xml --cov-report=term
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Start test environment
      run: |
        docker-compose -f docker-compose.test.yml up -d
        sleep 30  # Wait for services to start
    
    - name: Run integration tests
      run: |
        docker-compose -f docker-compose.test.yml exec -T api-gateway \
          pytest tests/integration/ -v
    
    - name: Cleanup
      run: docker-compose -f docker-compose.test.yml down

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
    
    - name: Install Playwright
      run: |
        npm install -g @playwright/test
        playwright install chromium
    
    - name: Start application
      run: |
        docker-compose -f docker-compose.e2e.yml up -d
        sleep 60  # Wait for full application startup
    
    - name: Run E2E tests
      run: |
        cd frontend
        npm install
        npm run test:e2e
    
    - name: Upload test artifacts
      if: failure()
      uses: actions/upload-artifact@v3
      with:
        name: playwright-report
        path: frontend/test-results/

  performance-tests:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run performance tests
      run: |
        docker-compose -f docker-compose.perf.yml up -d
        sleep 60
        python tests/performance/load_test.py
        docker-compose -f docker-compose.perf.yml down
    
    - name: Archive performance results
      uses: actions/upload-artifact@v3
      with:
        name: performance-results
        path: performance-results.json
```

### 7.2 测试数据管理
```python
# tests/fixtures/test_data.py
import json
import uuid
from datetime import datetime, timedelta

class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    def create_tenant(tenant_id: str = None, **overrides):
        """创建测试租户数据"""
        base_data = {
            "tenant_id": tenant_id or str(uuid.uuid4()),
            "tenant_name": "Test Tenant",
            "tenant_slug": "test-tenant",
            "contact_email": "admin@test-tenant.com",
            "status": "active",
            "subscription_plan": "basic",
            "config": {
                "max_users": 10,
                "max_api_calls_per_month": 10000,
                "max_storage_gb": 1.0,
                "features": {
                    "conversation_memory": True,
                    "file_upload": True,
                    "api_access": True
                }
            },
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_user(tenant_id: str, user_id: str = None, **overrides):
        """创建测试用户数据"""
        base_data = {
            "user_id": user_id or str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "email": "test@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "status": "active",
            "roles": ["end_user"],
            "created_at": datetime.utcnow().isoformat(),
            "last_login_at": None
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_conversation(user_id: str, conversation_id: str = None, **overrides):
        """创建测试对话数据"""
        base_data = {
            "conversation_id": conversation_id or str(uuid.uuid4()),
            "user_id": user_id,
            "title": "Test Conversation",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "message_count": 0
        }
        base_data.update(overrides)
        return base_data
    
    @staticmethod
    def create_message(conversation_id: str, user_id: str, **overrides):
        """创建测试消息数据"""
        base_data = {
            "message_id": str(uuid.uuid4()),
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": "user",
            "content": "Test message content",
            "content_type": "text",
            "created_at": datetime.utcnow().isoformat()
        }
        base_data.update(overrides)
        return base_data

# 测试数据清理
class TestDataCleaner:
    """测试数据清理器"""
    
    def __init__(self, db_session, redis_client):
        self.db_session = db_session
        self.redis_client = redis_client
    
    async def cleanup_test_data(self, tenant_id: str):
        """清理指定租户的测试数据"""
        # 清理数据库数据
        await self.db_session.execute(
            text("DELETE FROM messages WHERE user_id IN (SELECT user_id FROM users WHERE tenant_id = :tenant_id)"),
            {"tenant_id": tenant_id}
        )
        await self.db_session.execute(
            text("DELETE FROM conversations WHERE user_id IN (SELECT user_id FROM users WHERE tenant_id = :tenant_id)"),
            {"tenant_id": tenant_id}
        )
        await self.db_session.execute(
            text("DELETE FROM users WHERE tenant_id = :tenant_id"),
            {"tenant_id": tenant_id}
        )
        await self.db_session.commit()
        
        # 清理Redis数据
        pattern = f"tenant:{tenant_id}:*"
        keys = await self.redis_client.keys(pattern)
        if keys:
            await self.redis_client.delete(*keys)
```

这个测试策略文档提供了完整的测试框架，涵盖了从单元测试到端到端测试，从功能测试到性能测试的全方位测试策略。