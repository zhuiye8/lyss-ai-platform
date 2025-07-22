"""
RBAC管理器单元测试

测试RBAC（基于角色的访问控制）管理器的所有核心功能：
- 角色管理
- 权限管理
- 用户角色分配
- 权限验证
- 角色继承
- 租户数据隔离

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from auth_service.core.rbac_manager import RBACManager, PermissionResult
from auth_service.models.auth_models import TokenPayload, RoleModel, PermissionModel


class TestRBACManager:
    """RBAC管理器测试类"""
    
    @pytest_asyncio.fixture
    async def mock_redis_client(self):
        """模拟Redis客户端"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.sadd.return_value = True
        mock_redis.smembers.return_value = set()
        mock_redis.srem.return_value = True
        return mock_redis
    
    @pytest_asyncio.fixture
    async def rbac_manager(self, mock_redis_client):
        """RBAC管理器实例"""
        return RBACManager(redis_client=mock_redis_client)
    
    def test_rbac_manager_initialization(self, rbac_manager):
        """测试RBAC管理器初始化"""
        assert rbac_manager.redis_client is not None
        assert rbac_manager.role_prefix == "role"
        assert rbac_manager.permission_prefix == "permission"
        assert rbac_manager.user_role_prefix == "user_roles"
    
    @pytest.mark.asyncio
    async def test_initialize_default_roles_and_permissions(self, rbac_manager, mock_redis_client):
        """测试初始化默认角色和权限"""
        # 模拟Redis返回空值，表示需要初始化
        mock_redis_client.exists.return_value = False
        
        await rbac_manager.initialize_default_roles_and_permissions()
        
        # 验证Redis被调用来设置默认角色和权限
        assert mock_redis_client.set.call_count >= 4  # 至少有4个默认角色
        assert mock_redis_client.sadd.call_count >= 10  # 每个角色都有多个权限
    
    @pytest.mark.asyncio
    async def test_create_role(self, rbac_manager, mock_redis_client):
        """测试创建角色"""
        tenant_id = "tenant-123"
        role_data = RoleModel(
            name="custom_role",
            display_name="自定义角色",
            description="测试自定义角色",
            tenant_id=tenant_id,
            permissions=["user:read", "user:update"],
            is_system_role=False,
            is_active=True
        )
        
        success = await rbac_manager.create_role(role_data)
        
        assert success is True
        
        # 验证角色数据被保存到Redis
        mock_redis_client.set.assert_called()
        
        # 验证权限关联被添加
        mock_redis_client.sadd.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_role(self, rbac_manager, mock_redis_client):
        """测试获取角色"""
        tenant_id = "tenant-123"
        role_name = "end_user"
        
        # 模拟Redis返回角色数据
        mock_role_data = {
            "name": role_name,
            "display_name": "终端用户",
            "description": "普通用户角色",
            "tenant_id": tenant_id,
            "permissions": ["user:read"],
            "is_system_role": True,
            "is_active": True,
            "created_at": "2025-01-21T10:00:00",
            "updated_at": "2025-01-21T10:00:00"
        }
        mock_redis_client.get.return_value = mock_role_data
        
        role = await rbac_manager.get_role(role_name, tenant_id)
        
        assert role is not None
        assert role["name"] == role_name
        assert role["display_name"] == "终端用户"
        assert role["tenant_id"] == tenant_id
        
        # 验证正确的Redis键被查询
        expected_key = f"role:{tenant_id}:{role_name}"
        mock_redis_client.get.assert_called_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_update_role(self, rbac_manager, mock_redis_client):
        """测试更新角色"""
        tenant_id = "tenant-123"
        role_name = "custom_role"
        
        # 模拟现有角色数据
        existing_role = {
            "name": role_name,
            "display_name": "旧名称",
            "description": "旧描述",
            "tenant_id": tenant_id,
            "permissions": ["user:read"],
            "is_system_role": False,
            "is_active": True,
            "created_at": "2025-01-21T09:00:00"
        }
        mock_redis_client.get.return_value = existing_role
        
        updated_data = {
            "display_name": "新名称",
            "description": "新描述",
            "permissions": ["user:read", "user:update"]
        }
        
        success = await rbac_manager.update_role(role_name, tenant_id, updated_data)
        
        assert success is True
        
        # 验证角色数据被更新
        mock_redis_client.set.assert_called()
        
        # 验证权限关联被更新
        mock_redis_client.delete.assert_called()  # 删除旧权限
        mock_redis_client.sadd.assert_called()    # 添加新权限
    
    @pytest.mark.asyncio
    async def test_delete_role(self, rbac_manager, mock_redis_client):
        """测试删除角色"""
        tenant_id = "tenant-123"
        role_name = "custom_role"
        
        # 模拟现有角色
        mock_redis_client.get.return_value = {
            "name": role_name,
            "is_system_role": False  # 非系统角色可以删除
        }
        
        success = await rbac_manager.delete_role(role_name, tenant_id)
        
        assert success is True
        
        # 验证角色被删除
        mock_redis_client.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_delete_system_role_fails(self, rbac_manager, mock_redis_client):
        """测试删除系统角色失败"""
        tenant_id = "tenant-123"
        role_name = "super_admin"
        
        # 模拟系统角色
        mock_redis_client.get.return_value = {
            "name": role_name,
            "is_system_role": True  # 系统角色不能删除
        }
        
        success = await rbac_manager.delete_role(role_name, tenant_id)
        
        assert success is False
    
    @pytest.mark.asyncio
    async def test_assign_user_role(self, rbac_manager, mock_redis_client):
        """测试分配用户角色"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        role_name = "end_user"
        
        # 模拟角色存在
        mock_redis_client.get.return_value = {"name": role_name, "is_active": True}
        
        success = await rbac_manager.assign_user_role(user_id, role_name, tenant_id)
        
        assert success is True
        
        # 验证用户角色关系被添加
        expected_key = f"user_roles:{tenant_id}:{user_id}"
        mock_redis_client.sadd.assert_called_with(expected_key, role_name)
    
    @pytest.mark.asyncio
    async def test_revoke_user_role(self, rbac_manager, mock_redis_client):
        """测试撤销用户角色"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        role_name = "end_user"
        
        success = await rbac_manager.revoke_user_role(user_id, role_name, tenant_id)
        
        assert success is True
        
        # 验证用户角色关系被移除
        expected_key = f"user_roles:{tenant_id}:{user_id}"
        mock_redis_client.srem.assert_called_with(expected_key, role_name)
    
    @pytest.mark.asyncio
    async def test_get_user_roles(self, rbac_manager, mock_redis_client):
        """测试获取用户角色"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 模拟Redis返回用户角色集合
        mock_redis_client.smembers.return_value = {b"end_user", b"admin"}
        
        roles = await rbac_manager.get_user_roles(user_id, tenant_id)
        
        assert isinstance(roles, list)
        assert "end_user" in roles
        assert "admin" in roles
        assert len(roles) == 2
        
        # 验证正确的Redis键被查询
        expected_key = f"user_roles:{tenant_id}:{user_id}"
        mock_redis_client.smembers.assert_called_with(expected_key)
    
    @pytest.mark.asyncio
    async def test_get_user_permissions(self, rbac_manager, mock_redis_client):
        """测试获取用户权限"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 模拟用户有两个角色
        mock_redis_client.smembers.return_value = {b"end_user", b"admin"}
        
        # 模拟角色权限
        role_permissions = {
            b"user:read", b"user:update", b"system:admin"
        }
        mock_redis_client.smembers.return_value = role_permissions
        
        permissions = await rbac_manager.get_user_permissions(user_id, tenant_id)
        
        assert isinstance(permissions, list)
        assert len(permissions) > 0
    
    @pytest.mark.asyncio
    async def test_check_permission_granted(self, rbac_manager, mock_redis_client):
        """测试权限检查 - 权限被授予"""
        token_payload = TokenPayload(
            sub="user-123",
            tenant_id="tenant-123",
            permissions=["user:read", "user:update"],
            role="end_user",
            email="test@example.com",
            iat=1640995200,
            exp=1640998800
        )
        
        required_permission = "user:read"
        
        result = await rbac_manager.check_permission(token_payload, required_permission)
        
        assert isinstance(result, PermissionResult)
        assert result.granted is True
        assert result.user_id == "user-123"
        assert result.tenant_id == "tenant-123"
        assert result.required_permission == required_permission
        assert result.user_permissions is not None
        assert required_permission in result.user_permissions
    
    @pytest.mark.asyncio
    async def test_check_permission_denied(self, rbac_manager):
        """测试权限检查 - 权限被拒绝"""
        token_payload = TokenPayload(
            sub="user-123",
            tenant_id="tenant-123",
            permissions=["user:read"],  # 没有required_permission
            role="end_user",
            email="test@example.com",
            iat=1640995200,
            exp=1640998800
        )
        
        required_permission = "admin:manage"
        
        result = await rbac_manager.check_permission(token_payload, required_permission)
        
        assert result.granted is False
        assert result.required_permission == required_permission
        assert required_permission not in result.user_permissions
    
    @pytest.mark.asyncio
    async def test_check_wildcard_permission(self, rbac_manager):
        """测试通配符权限检查"""
        token_payload = TokenPayload(
            sub="user-123",
            tenant_id="tenant-123",
            permissions=["user:*"],  # 通配符权限
            role="admin",
            email="test@example.com",
            iat=1640995200,
            exp=1640998800
        )
        
        required_permission = "user:delete"
        
        result = await rbac_manager.check_permission(token_payload, required_permission)
        
        assert result.granted is True
    
    @pytest.mark.asyncio
    async def test_check_system_admin_permission(self, rbac_manager):
        """测试系统管理员权限检查"""
        token_payload = TokenPayload(
            sub="admin-123",
            tenant_id="tenant-123",
            permissions=["system:admin"],  # 系统管理员权限
            role="super_admin",
            email="admin@example.com",
            iat=1640995200,
            exp=1640998800
        )
        
        # 系统管理员应该有所有权限
        required_permission = "any:permission"
        
        result = await rbac_manager.check_permission(token_payload, required_permission)
        
        assert result.granted is True
    
    @pytest.mark.asyncio
    async def test_list_roles(self, rbac_manager, mock_redis_client):
        """测试列出角色"""
        tenant_id = "tenant-123"
        
        # 模拟Redis scan返回角色键
        mock_redis_client.scan_iter.return_value = [
            b"role:tenant-123:end_user",
            b"role:tenant-123:admin",
            b"role:other-tenant:role1"  # 其他租户的角色应该被过滤
        ]
        
        # 模拟角色数据
        mock_redis_client.get.side_effect = [
            {"name": "end_user", "display_name": "终端用户"},
            {"name": "admin", "display_name": "管理员"},
            None  # 其他租户的角色
        ]
        
        roles = await rbac_manager.list_roles(tenant_id)
        
        assert isinstance(roles, list)
        assert len(roles) == 2
        assert any(role["name"] == "end_user" for role in roles)
        assert any(role["name"] == "admin" for role in roles)
    
    @pytest.mark.asyncio
    async def test_list_permissions(self, rbac_manager, mock_redis_client):
        """测试列出权限"""
        tenant_id = "tenant-123"
        
        # 模拟Redis scan返回权限键
        mock_redis_client.scan_iter.return_value = [
            b"permission:tenant-123:user:read",
            b"permission:tenant-123:user:write",
            b"permission:other-tenant:perm1"  # 其他租户的权限应该被过滤
        ]
        
        # 模拟权限数据
        mock_redis_client.get.side_effect = [
            {"name": "user:read", "description": "读取用户信息"},
            {"name": "user:write", "description": "修改用户信息"},
            None
        ]
        
        permissions = await rbac_manager.list_permissions(tenant_id)
        
        assert isinstance(permissions, list)
        assert len(permissions) == 2
        assert any(perm["name"] == "user:read" for perm in permissions)
        assert any(perm["name"] == "user:write" for perm in permissions)
    
    @pytest.mark.asyncio
    async def test_role_hierarchy_check(self, rbac_manager):
        """测试角色层级检查"""
        # 测试角色层级：super_admin > tenant_admin > admin > end_user
        
        # 超级管理员应该有最高权限级别
        assert rbac_manager._get_role_hierarchy_level("super_admin") == 4
        
        # 租户管理员次之
        assert rbac_manager._get_role_hierarchy_level("tenant_admin") == 3
        
        # 普通管理员
        assert rbac_manager._get_role_hierarchy_level("admin") == 2
        
        # 终端用户最低
        assert rbac_manager._get_role_hierarchy_level("end_user") == 1
        
        # 未知角色默认为0
        assert rbac_manager._get_role_hierarchy_level("unknown_role") == 0
    
    @pytest.mark.asyncio
    async def test_tenant_isolation(self, rbac_manager, mock_redis_client):
        """测试租户数据隔离"""
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"
        user_id = "user-123"
        
        # 为租户A的用户分配角色
        await rbac_manager.assign_user_role(user_id, "admin", tenant_a)
        
        # 为租户B的同一用户ID分配不同角色
        await rbac_manager.assign_user_role(user_id, "end_user", tenant_b)
        
        # 验证Redis被调用时使用了正确的租户隔离键
        calls = mock_redis_client.sadd.call_args_list
        
        # 第一次调用应该是租户A的键
        first_call_key = calls[0][0][0]
        assert tenant_a in first_call_key
        assert tenant_b not in first_call_key
        
        # 第二次调用应该是租户B的键
        second_call_key = calls[1][0][0]
        assert tenant_b in second_call_key
        assert tenant_a not in second_call_key
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, rbac_manager):
        """测试Redis错误处理"""
        # 创建一个会抛出异常的模拟Redis客户端
        mock_redis_error = AsyncMock()
        mock_redis_error.get.side_effect = Exception("Redis connection failed")
        mock_redis_error.set.side_effect = Exception("Redis connection failed")
        mock_redis_error.sadd.side_effect = Exception("Redis connection failed")
        
        rbac_manager.redis_client = mock_redis_error
        
        # 测试各种操作在Redis错误时的行为
        role_data = RoleModel(
            name="test_role",
            display_name="测试角色",
            tenant_id="tenant-123",
            permissions=["user:read"],
            is_system_role=False,
            is_active=True
        )
        
        # 创建角色应该失败但不抛出异常
        success = await rbac_manager.create_role(role_data)
        assert success is False
        
        # 获取角色应该返回None
        role = await rbac_manager.get_role("test_role", "tenant-123")
        assert role is None
        
        # 权限检查应该拒绝权限
        token_payload = TokenPayload(
            sub="user-123",
            tenant_id="tenant-123",
            permissions=["user:read"],
            role="end_user",
            email="test@example.com",
            iat=1640995200,
            exp=1640998800
        )
        
        result = await rbac_manager.check_permission(token_payload, "user:read")
        # 在Redis错误的情况下，应该基于token中的权限进行检查
        assert result.granted is True  # 因为token中有这个权限
    
    @pytest.mark.asyncio
    async def test_bulk_role_assignment(self, rbac_manager, mock_redis_client):
        """测试批量角色分配"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        roles = ["end_user", "admin", "operator"]
        
        # 模拟所有角色都存在且活跃
        mock_redis_client.get.return_value = {"name": "role", "is_active": True}
        
        success_count = 0
        for role in roles:
            success = await rbac_manager.assign_user_role(user_id, role, tenant_id)
            if success:
                success_count += 1
        
        assert success_count == len(roles)
        
        # 验证Redis被调用了正确的次数
        assert mock_redis_client.sadd.call_count == len(roles)
    
    @pytest.mark.asyncio
    async def test_permission_inheritance(self, rbac_manager, mock_redis_client):
        """测试权限继承"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 模拟用户有多个角色，每个角色有不同权限
        mock_redis_client.smembers.side_effect = [
            {b"admin", b"end_user"},  # 用户角色
            {b"user:read", b"user:write", b"admin:manage"},  # admin角色权限
            {b"user:read"}  # end_user角色权限
        ]
        
        permissions = await rbac_manager.get_user_permissions(user_id, tenant_id)
        
        # 用户应该获得所有角色的权限集合
        assert isinstance(permissions, list)
        # 应该有去重效果（user:read不会重复）


class TestPermissionResult:
    """权限结果测试"""
    
    def test_granted_permission_result(self):
        """测试授予权限的结果"""
        result = PermissionResult(
            granted=True,
            user_id="user-123",
            tenant_id="tenant-123",
            required_permission="user:read",
            user_permissions=["user:read", "user:update"],
            user_roles=["end_user"]
        )
        
        assert result.granted is True
        assert result.user_id == "user-123"
        assert result.tenant_id == "tenant-123"
        assert result.required_permission == "user:read"
        assert "user:read" in result.user_permissions
        assert "end_user" in result.user_roles
    
    def test_denied_permission_result(self):
        """测试拒绝权限的结果"""
        result = PermissionResult(
            granted=False,
            user_id="user-123",
            tenant_id="tenant-123",
            required_permission="admin:manage",
            user_permissions=["user:read"],
            user_roles=["end_user"]
        )
        
        assert result.granted is False
        assert result.required_permission == "admin:manage"
        assert "admin:manage" not in result.user_permissions