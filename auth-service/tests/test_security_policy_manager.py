"""
安全策略管理器单元测试

测试安全策略管理器的所有核心功能：
- 策略初始化和管理
- 密码策略验证
- IP访问控制
- 登录失败追踪
- 策略动态更新
- 安全性验证

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import pytest
import pytest_asyncio
import time
import ipaddress
from unittest.mock import AsyncMock, patch

from auth_service.core.security_policy_manager import (
    SecurityPolicyManager, PolicyLevel, PasswordPolicy, 
    SessionPolicy, LoginPolicy, AuditPolicy, IPPolicy
)


class TestSecurityPolicyManager:
    """安全策略管理器测试类"""
    
    @pytest_asyncio.fixture
    async def mock_redis_client(self):
        """模拟Redis客户端"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.scan_iter.return_value = []
        return mock_redis
    
    @pytest_asyncio.fixture
    async def security_policy_manager(self, test_settings, mock_redis_client):
        """安全策略管理器实例"""
        return SecurityPolicyManager(
            redis_client=mock_redis_client,
            settings=test_settings
        )
    
    def test_security_policy_manager_initialization(self, security_policy_manager):
        """测试安全策略管理器初始化"""
        assert security_policy_manager.redis_client is not None
        assert security_policy_manager.settings is not None
        assert security_policy_manager.policy_prefix == "security_policy"
        assert len(security_policy_manager.default_policies) == 5  # password, session, login, audit, ip
        assert len(security_policy_manager.common_passwords) > 0
    
    @pytest.mark.asyncio
    async def test_initialize_policies_first_time(self, security_policy_manager, mock_redis_client):
        """测试首次初始化策略"""
        # 模拟没有现有策略
        mock_redis_client.get.return_value = None
        
        await security_policy_manager.initialize_policies()
        
        # 验证默认策略被保存
        mock_redis_client.set.assert_called()
        call_args = mock_redis_client.set.call_args
        assert "security_policy:config" in call_args[0][0]
        
        # 验证包含所有默认策略类型
        saved_policies = call_args[0][1]
        assert "password" in saved_policies
        assert "session" in saved_policies
        assert "login" in saved_policies
        assert "audit" in saved_policies
        assert "ip" in saved_policies
    
    @pytest.mark.asyncio
    async def test_initialize_policies_existing(self, security_policy_manager, mock_redis_client):
        """测试已有策略时的初始化"""
        # 模拟已有策略
        existing_policies = {
            "password": {"min_length": 10},
            "session": {"max_concurrent_sessions": 3}
        }
        mock_redis_client.get.return_value = existing_policies
        
        await security_policy_manager.initialize_policies()
        
        # 不应该覆盖现有策略
        mock_redis_client.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_policy_existing(self, security_policy_manager, mock_redis_client):
        """测试获取现有策略"""
        policy_type = "password"
        mock_policy = {
            "min_length": 12,
            "require_uppercase": True,
            "require_special_chars": True
        }
        
        all_policies = {
            "password": mock_policy,
            "session": {"max_concurrent_sessions": 5}
        }
        mock_redis_client.get.return_value = all_policies
        
        result = await security_policy_manager.get_policy(policy_type)
        
        assert result == mock_policy
        mock_redis_client.get.assert_called_with("security_policy:config")
    
    @pytest.mark.asyncio
    async def test_get_policy_not_found_returns_default(self, security_policy_manager, mock_redis_client):
        """测试获取不存在的策略返回默认值"""
        # 模拟Redis中没有策略
        mock_redis_client.get.return_value = None
        
        result = await security_policy_manager.get_policy("password")
        
        # 应该返回默认密码策略
        assert result is not None
        assert result["min_length"] == 8
        assert result["require_uppercase"] is True
    
    @pytest.mark.asyncio
    async def test_update_policy_success(self, security_policy_manager, mock_redis_client):
        """测试成功更新策略"""
        policy_type = "password"
        new_policy = {
            "min_length": 12,
            "max_length": 256,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digits": True,
            "require_special_chars": True,
            "password_expire_days": 60
        }
        
        # 模拟现有策略
        existing_policies = {"password": {"min_length": 8}}
        mock_redis_client.get.return_value = existing_policies
        
        success = await security_policy_manager.update_policy(policy_type, new_policy)
        
        assert success is True
        mock_redis_client.set.assert_called()
        
        # 验证策略被更新
        call_args = mock_redis_client.set.call_args
        updated_policies = call_args[0][1]
        assert updated_policies["password"]["min_length"] == 12
    
    @pytest.mark.asyncio
    async def test_update_policy_validation_failure(self, security_policy_manager, mock_redis_client):
        """测试策略验证失败"""
        policy_type = "password"
        invalid_policy = {
            "min_length": 2,  # 太短，应该失败
            "max_length": 1   # 最大长度小于最小长度
        }
        
        success = await security_policy_manager.update_policy(policy_type, invalid_policy)
        
        assert success is False
        mock_redis_client.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_validate_password_success(self, security_policy_manager):
        """测试密码验证成功"""
        strong_password = "StrongPassword123!"
        
        result = await security_policy_manager.validate_password(strong_password)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["strength_score"] > 80
        assert result["strength_level"] in ["strong", "excellent"]
        assert result["policy_compliant"] is True
    
    @pytest.mark.asyncio
    async def test_validate_password_too_short(self, security_policy_manager):
        """测试密码太短"""
        short_password = "123"
        
        result = await security_policy_manager.validate_password(short_password)
        
        assert result["valid"] is False
        assert any("密码长度至少需要" in error for error in result["errors"])
        assert result["strength_score"] < 50
    
    @pytest.mark.asyncio
    async def test_validate_password_missing_requirements(self, security_policy_manager):
        """测试密码缺少必要元素"""
        weak_password = "password"  # 只有小写字母
        
        result = await security_policy_manager.validate_password(weak_password)
        
        assert result["valid"] is False
        assert any("大写字母" in error for error in result["errors"])
        assert any("数字" in error for error in result["errors"])
        assert any("特殊字符" in error for error in result["errors"])
    
    @pytest.mark.asyncio
    async def test_validate_password_common_password(self, security_policy_manager):
        """测试常见弱密码检查"""
        common_password = "password123"  # 包含常见密码
        
        result = await security_policy_manager.validate_password(common_password)
        
        assert result["valid"] is False
        assert any("常见弱密码" in error for error in result["errors"])
    
    @pytest.mark.asyncio
    async def test_validate_password_with_user_info(self, security_policy_manager):
        """测试包含用户信息的密码验证"""
        user_info = {
            "username": "johnsmith",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Smith"
        }
        
        password_with_user_info = "JohnSmith123!"  # 包含用户姓名
        
        result = await security_policy_manager.validate_password(
            password_with_user_info, user_info
        )
        
        assert result["valid"] is False
        assert any("个人信息" in error for error in result["errors"])
    
    @pytest.mark.asyncio
    async def test_check_ip_access_allowed(self, security_policy_manager, mock_redis_client):
        """测试IP访问允许"""
        ip_address = "192.168.1.100"
        
        # 模拟IP策略：不启用白名单，不启用黑名单
        ip_policy = {
            "whitelist_enabled": False,
            "blacklist_enabled": False,
            "auto_block_suspicious_ips": False
        }
        
        all_policies = {"ip": ip_policy}
        mock_redis_client.get.return_value = all_policies
        
        result = await security_policy_manager.check_ip_access(ip_address)
        
        assert result["allowed"] is True
        assert "检查通过" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_check_ip_access_blacklisted(self, security_policy_manager, mock_redis_client):
        """测试IP在黑名单中"""
        ip_address = "192.168.1.100"
        
        # 模拟IP策略：启用黑名单
        ip_policy = {
            "blacklist_enabled": True,
            "blocked_ip_ranges": ["192.168.1.0/24", "10.0.0.0/8"]
        }
        
        all_policies = {"ip": ip_policy}
        mock_redis_client.get.return_value = all_policies
        
        result = await security_policy_manager.check_ip_access(ip_address)
        
        assert result["allowed"] is False
        assert "黑名单" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_check_ip_access_not_whitelisted(self, security_policy_manager, mock_redis_client):
        """测试IP不在白名单中"""
        ip_address = "192.168.1.100"
        
        # 模拟IP策略：启用白名单但IP不在其中
        ip_policy = {
            "whitelist_enabled": True,
            "allowed_ip_ranges": ["10.0.0.0/8", "172.16.0.0/12"]
        }
        
        all_policies = {"ip": ip_policy}
        mock_redis_client.get.return_value = all_policies
        
        result = await security_policy_manager.check_ip_access(ip_address)
        
        assert result["allowed"] is False
        assert "不在白名单中" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_check_ip_access_whitelisted(self, security_policy_manager, mock_redis_client):
        """测试IP在白名单中"""
        ip_address = "192.168.1.100"
        
        # 模拟IP策略：启用白名单且IP在其中
        ip_policy = {
            "whitelist_enabled": True,
            "allowed_ip_ranges": ["192.168.1.0/24", "10.0.0.0/8"]
        }
        
        all_policies = {"ip": ip_policy}
        mock_redis_client.get.return_value = all_policies
        
        result = await security_policy_manager.check_ip_access(ip_address)
        
        assert result["allowed"] is True
        assert "白名单" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_check_ip_access_auto_blocked(self, security_policy_manager, mock_redis_client):
        """测试IP被自动封禁"""
        ip_address = "192.168.1.100"
        
        # 模拟IP策略：启用自动封禁
        ip_policy = {
            "auto_block_suspicious_ips": True
        }
        
        all_policies = {"ip": ip_policy}
        
        # 模拟Redis get调用：第一次获取策略，第二次检查封禁状态
        future_time = time.time() + 3600  # 1小时后过期
        mock_redis_client.get.side_effect = [all_policies, future_time]
        
        result = await security_policy_manager.check_ip_access(ip_address)
        
        assert result["allowed"] is False
        assert "暂时封禁" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_record_failed_login_normal(self, security_policy_manager, mock_redis_client):
        """测试记录正常登录失败"""
        ip_address = "192.168.1.100"
        
        # 模拟IP策略
        ip_policy = {
            "auto_block_suspicious_ips": True,
            "auto_block_threshold": 5,
            "block_duration_hours": 24
        }
        
        all_policies = {"ip": ip_policy}
        mock_redis_client.get.side_effect = [all_policies, 2]  # 当前失败次数为2
        mock_redis_client.incr.return_value = 3  # 增加后为3
        
        await security_policy_manager.record_failed_login(ip_address)
        
        # 应该记录失败次数但不封禁
        mock_redis_client.incr.assert_called()
        mock_redis_client.expire.assert_called()
        
        # 检查是否设置了封禁（不应该设置，因为只有3次失败）
        set_calls = mock_redis_client.set.call_args_list
        blocked_ip_calls = [call for call in set_calls if "blocked_ip" in str(call)]
        assert len(blocked_ip_calls) == 0
    
    @pytest.mark.asyncio
    async def test_record_failed_login_threshold_reached(self, security_policy_manager, mock_redis_client):
        """测试达到失败阈值后自动封禁"""
        ip_address = "192.168.1.100"
        
        # 模拟IP策略
        ip_policy = {
            "auto_block_suspicious_ips": True,
            "auto_block_threshold": 5,
            "block_duration_hours": 24
        }
        
        all_policies = {"ip": ip_policy}
        mock_redis_client.get.side_effect = [all_policies, 4]  # 当前失败次数为4
        mock_redis_client.incr.return_value = 5  # 增加后为5，达到阈值
        
        await security_policy_manager.record_failed_login(ip_address, "user-123")
        
        # 应该自动封禁IP
        mock_redis_client.incr.assert_called()
        
        # 检查封禁设置
        set_calls = mock_redis_client.set.call_args_list
        blocked_ip_calls = [call for call in set_calls if "blocked_ip" in str(call)]
        assert len(blocked_ip_calls) > 0
        
        # 清除失败计数
        mock_redis_client.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_password_strength_calculation(self, security_policy_manager):
        """测试密码强度计算"""
        test_cases = [
            ("12345", "very_weak"),           # 只有数字，太短
            ("password", "weak"),             # 只有小写字母
            ("Password", "weak"),             # 大小写字母
            ("Password1", "medium"),          # 大小写字母+数字
            ("Password1!", "strong"),         # 大小写字母+数字+特殊字符
            ("VeryStrongPassword123!", "excellent")  # 长且复杂
        ]
        
        for password, expected_level in test_cases:
            score = security_policy_manager._calculate_password_strength(password)
            level = security_policy_manager._get_strength_level(score)
            assert level == expected_level, f"密码 '{password}' 期望强度 {expected_level}，实际 {level}"
    
    @pytest.mark.asyncio
    async def test_validate_policy_password_valid(self, security_policy_manager):
        """测试有效密码策略验证"""
        valid_policy = {
            "min_length": 8,
            "max_length": 128,
            "password_expire_days": 90,
            "password_history_count": 5
        }
        
        result = security_policy_manager._validate_policy("password", valid_policy)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_policy_password_invalid(self, security_policy_manager):
        """测试无效密码策略验证"""
        invalid_policy = {
            "min_length": 2,        # 太小
            "max_length": 300,      # 太大
            "password_expire_days": 400  # 超出范围
        }
        
        result = security_policy_manager._validate_policy("password", invalid_policy)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("最小密码长度不能小于4" in error for error in result["errors"])
        assert any("最大密码长度不能超过256" in error for error in result["errors"])
        assert any("密码过期天数必须在1-365之间" in error for error in result["errors"])
    
    @pytest.mark.asyncio
    async def test_validate_policy_session_valid(self, security_policy_manager):
        """测试有效会话策略验证"""
        valid_policy = {
            "max_concurrent_sessions": 5,
            "session_timeout_minutes": 60,
            "idle_timeout_minutes": 30
        }
        
        result = security_policy_manager._validate_policy("session", valid_policy)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_policy_ip_invalid_ranges(self, security_policy_manager):
        """测试无效IP范围策略验证"""
        invalid_policy = {
            "allowed_ip_ranges": ["192.168.1.0/24", "invalid-ip-range"],
            "blocked_ip_ranges": ["10.0.0.0/8", "another-invalid-range"],
            "auto_block_threshold": 2000  # 超出范围
        }
        
        result = security_policy_manager._validate_policy("ip", invalid_policy)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("无效的IP范围格式" in error for error in result["errors"])
        assert any("自动封禁阈值必须在1-1000之间" in error for error in result["errors"])
    
    @pytest.mark.asyncio
    async def test_update_all_policies_success(self, security_policy_manager, mock_redis_client):
        """测试批量更新所有策略"""
        new_policies = {
            "password": {
                "min_length": 10,
                "require_uppercase": True
            },
            "session": {
                "max_concurrent_sessions": 3
            },
            "login": {
                "max_failed_attempts": 3
            },
            "audit": {
                "log_retention_days": 180
            },
            "ip": {
                "whitelist_enabled": False
            }
        }
        
        success = await security_policy_manager.update_all_policies(new_policies)
        
        assert success is True
        mock_redis_client.set.assert_called_once()
        
        # 验证保存的策略包含时间戳和版本
        call_args = mock_redis_client.set.call_args
        saved_policies = call_args[0][1]
        assert "last_updated" in saved_policies
        assert "version" in saved_policies
        assert saved_policies["password"]["min_length"] == 10
    
    @pytest.mark.asyncio
    async def test_update_all_policies_validation_failure(self, security_policy_manager, mock_redis_client):
        """测试批量更新策略时验证失败"""
        invalid_policies = {
            "password": {
                "min_length": 1,  # 无效
                "max_length": 300  # 无效
            },
            "session": {
                "max_concurrent_sessions": 200  # 无效
            }
        }
        
        success = await security_policy_manager.update_all_policies(invalid_policies)
        
        assert success is False
        mock_redis_client.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_invalid_ip_address_handling(self, security_policy_manager):
        """测试无效IP地址处理"""
        invalid_ip = "not-an-ip-address"
        
        result = await security_policy_manager.check_ip_access(invalid_ip)
        
        # 应该允许访问但记录异常
        assert result["allowed"] is True
        assert "异常" in result["reason"] or "默认允许" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_policy_change_logging(self, security_policy_manager, mock_redis_client):
        """测试策略变更日志记录"""
        policy_type = "password"
        new_policy = {"min_length": 10}
        
        # 模拟现有策略
        mock_redis_client.get.return_value = {}
        
        await security_policy_manager.update_policy(policy_type, new_policy)
        
        # 验证变更日志被记录
        set_calls = mock_redis_client.set.call_args_list
        log_calls = [call for call in set_calls if "policy_change_log" in str(call)]
        assert len(log_calls) > 0
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, security_policy_manager):
        """测试Redis错误处理"""
        # 创建会抛出异常的模拟Redis客户端
        mock_redis_error = AsyncMock()
        mock_redis_error.get.side_effect = Exception("Redis connection failed")
        mock_redis_error.set.side_effect = Exception("Redis connection failed")
        
        security_policy_manager.redis_client = mock_redis_error
        
        # 获取策略应该返回默认值
        policy = await security_policy_manager.get_policy("password")
        assert policy is not None  # 应该返回默认策略
        assert policy["min_length"] == 8
        
        # 更新策略应该失败
        success = await security_policy_manager.update_policy("password", {"min_length": 10})
        assert success is False
        
        # IP检查应该默认允许
        result = await security_policy_manager.check_ip_access("192.168.1.1")
        assert result["allowed"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_policy_operations(self, security_policy_manager, mock_redis_client):
        """测试并发策略操作"""
        import asyncio
        
        # 并发更新不同策略
        tasks = []
        
        # 更新密码策略
        tasks.append(security_policy_manager.update_policy(
            "password", {"min_length": 12}
        ))
        
        # 更新会话策略
        tasks.append(security_policy_manager.update_policy(
            "session", {"max_concurrent_sessions": 3}
        ))
        
        # 更新登录策略
        tasks.append(security_policy_manager.update_policy(
            "login", {"max_failed_attempts": 3}
        ))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有异常
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"并发操作产生异常: {result}")
            else:
                assert result is True


class TestPolicyDataClasses:
    """策略数据类测试"""
    
    def test_password_policy_defaults(self):
        """测试密码策略默认值"""
        policy = PasswordPolicy()
        
        assert policy.min_length == 8
        assert policy.max_length == 128
        assert policy.require_uppercase is True
        assert policy.require_lowercase is True
        assert policy.require_digits is True
        assert policy.require_special_chars is True
        assert policy.password_expire_days == 90
        assert policy.password_history_count == 5
    
    def test_session_policy_defaults(self):
        """测试会话策略默认值"""
        policy = SessionPolicy()
        
        assert policy.max_concurrent_sessions == 5
        assert policy.session_timeout_minutes == 30
        assert policy.idle_timeout_minutes == 15
        assert policy.require_re_auth_for_sensitive_ops is True
        assert policy.detect_concurrent_logins is True
    
    def test_login_policy_defaults(self):
        """测试登录策略默认值"""
        policy = LoginPolicy()
        
        assert policy.max_failed_attempts == 5
        assert policy.lockout_duration_minutes == 30
        assert policy.progressive_lockout_enabled is True
        assert policy.ip_based_lockout is True
        assert policy.suspicious_login_detection is True
    
    def test_audit_policy_defaults(self):
        """测试审计策略默认值"""
        policy = AuditPolicy()
        
        assert policy.log_all_api_calls is True
        assert policy.log_authentication_events is True
        assert policy.log_authorization_failures is True
        assert policy.log_sensitive_operations is True
        assert policy.log_retention_days == 365
        assert policy.real_time_alerts_enabled is True
    
    def test_ip_policy_defaults(self):
        """测试IP策略默认值"""
        policy = IPPolicy()
        
        assert policy.whitelist_enabled is False
        assert policy.blacklist_enabled is True
        assert policy.auto_block_suspicious_ips is True
        assert policy.auto_block_threshold == 10
        assert policy.block_duration_hours == 24