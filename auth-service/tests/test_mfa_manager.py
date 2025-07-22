"""
MFA管理器单元测试

测试多因素认证管理器的所有核心功能：
- TOTP生成和验证
- 备份代码生成和验证
- SMS验证码发送和验证
- Email验证码发送和验证
- MFA状态管理
- 安全性验证

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import pytest
import pytest_asyncio
import pyotp
import time
from unittest.mock import AsyncMock, patch, MagicMock

from auth_service.core.mfa_manager import MFAManager, MFAMethod
from auth_service.models.auth_models import (
    MFASetupRequest, MFAVerifyRequest, MFASetupResponse, 
    MFAVerifyResponse, BackupCodesResponse
)


class TestMFAManager:
    """MFA管理器测试类"""
    
    @pytest_asyncio.fixture
    async def mock_redis_client(self):
        """模拟Redis客户端"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.delete.return_value = True
        mock_redis.exists.return_value = False
        mock_redis.incr.return_value = 1
        mock_redis.expire.return_value = True
        return mock_redis
    
    @pytest_asyncio.fixture
    async def mfa_manager(self, test_settings, mock_redis_client):
        """MFA管理器实例"""
        return MFAManager(
            redis_client=mock_redis_client,
            settings=test_settings
        )
    
    def test_mfa_manager_initialization(self, mfa_manager):
        """测试MFA管理器初始化"""
        assert mfa_manager.redis_client is not None
        assert mfa_manager.settings is not None
        assert mfa_manager.totp_issuer == "Lyss AI Platform"
        assert mfa_manager.backup_code_length == 8
        assert mfa_manager.backup_code_count == 10
    
    @pytest.mark.asyncio
    async def test_setup_totp(self, mfa_manager, mock_redis_client):
        """测试设置TOTP"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        user_email = "test@example.com"
        
        request = MFASetupRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.TOTP,
            user_email=user_email
        )
        
        result = await mfa_manager.setup_mfa(request)
        
        assert isinstance(result, MFASetupResponse)
        assert result.success is True
        assert result.method == MFAMethod.TOTP
        assert result.secret is not None
        assert result.qr_code_url is not None
        assert result.backup_codes is not None
        assert len(result.backup_codes) == 10
        
        # 验证QR码URL格式
        assert "otpauth://totp/" in result.qr_code_url
        assert user_email in result.qr_code_url
        assert "Lyss%20AI%20Platform" in result.qr_code_url
        
        # 验证Redis被调用保存TOTP数据
        mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_setup_sms(self, mfa_manager, mock_redis_client):
        """测试设置SMS MFA"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        phone_number = "+1234567890"
        
        request = MFASetupRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.SMS,
            phone_number=phone_number
        )
        
        with patch.object(mfa_manager, '_send_sms_code', return_value=True):
            result = await mfa_manager.setup_mfa(request)
            
            assert result.success is True
            assert result.method == MFAMethod.SMS
            assert result.message == "验证码已发送到您的手机"
            
            # 验证Redis被调用保存SMS数据
            mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_setup_email(self, mfa_manager, mock_redis_client):
        """测试设置Email MFA"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        user_email = "test@example.com"
        
        request = MFASetupRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.EMAIL,
            user_email=user_email
        )
        
        with patch.object(mfa_manager, '_send_email_code', return_value=True):
            result = await mfa_manager.setup_mfa(request)
            
            assert result.success is True
            assert result.method == MFAMethod.EMAIL
            assert result.message == "验证码已发送到您的邮箱"
    
    @pytest.mark.asyncio
    async def test_verify_totp_success(self, mfa_manager, mock_redis_client):
        """测试TOTP验证成功"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 生成一个真实的TOTP密钥和代码
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        current_code = totp.now()
        
        # 模拟Redis返回TOTP数据
        mock_totp_data = {
            "secret": secret,
            "verified": False,
            "setup_time": time.time()
        }
        mock_redis_client.get.return_value = mock_totp_data
        
        request = MFAVerifyRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.TOTP,
            code=current_code
        )
        
        result = await mfa_manager.verify_mfa(request)
        
        assert isinstance(result, MFAVerifyResponse)
        assert result.success is True
        assert result.method == MFAMethod.TOTP
        assert "验证成功" in result.message
        
        # 验证Redis被调用更新验证状态
        mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_verify_totp_invalid_code(self, mfa_manager, mock_redis_client):
        """测试TOTP验证失败 - 无效代码"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 生成一个TOTP密钥
        secret = pyotp.random_base32()
        
        # 模拟Redis返回TOTP数据
        mock_totp_data = {
            "secret": secret,
            "verified": False,
            "setup_time": time.time()
        }
        mock_redis_client.get.return_value = mock_totp_data
        
        request = MFAVerifyRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.TOTP,
            code="000000"  # 无效代码
        )
        
        result = await mfa_manager.verify_mfa(request)
        
        assert result.success is False
        assert "验证码错误" in result.message
    
    @pytest.mark.asyncio
    async def test_verify_sms_success(self, mfa_manager, mock_redis_client):
        """测试SMS验证成功"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        verification_code = "123456"
        
        # 模拟Redis返回SMS验证码
        mock_redis_client.get.return_value = verification_code
        
        request = MFAVerifyRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.SMS,
            code=verification_code
        )
        
        result = await mfa_manager.verify_mfa(request)
        
        assert result.success is True
        assert result.method == MFAMethod.SMS
        assert "验证成功" in result.message
        
        # 验证验证码被删除
        mock_redis_client.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_verify_backup_code_success(self, mfa_manager, mock_redis_client):
        """测试备份代码验证成功"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        backup_code = "ABCD1234"
        
        # 模拟Redis返回备份代码列表
        mock_backup_codes = [
            {"code": "ABCD1234", "used": False},
            {"code": "EFGH5678", "used": False}
        ]
        mock_redis_client.get.return_value = mock_backup_codes
        
        request = MFAVerifyRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.BACKUP_CODE,
            code=backup_code
        )
        
        result = await mfa_manager.verify_mfa(request)
        
        assert result.success is True
        assert result.method == MFAMethod.BACKUP_CODE
        assert "备份代码验证成功" in result.message
        
        # 验证备份代码列表被更新
        mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_verify_used_backup_code(self, mfa_manager, mock_redis_client):
        """测试使用已用过的备份代码"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        backup_code = "ABCD1234"
        
        # 模拟Redis返回备份代码列表，其中包含已使用的代码
        mock_backup_codes = [
            {"code": "ABCD1234", "used": True},  # 已使用的代码
            {"code": "EFGH5678", "used": False}
        ]
        mock_redis_client.get.return_value = mock_backup_codes
        
        request = MFAVerifyRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.BACKUP_CODE,
            code=backup_code
        )
        
        result = await mfa_manager.verify_mfa(request)
        
        assert result.success is False
        assert "备份代码已被使用" in result.message
    
    @pytest.mark.asyncio
    async def test_generate_backup_codes(self, mfa_manager):
        """测试生成备份代码"""
        backup_codes = await mfa_manager.generate_backup_codes("user-123", "tenant-123")
        
        assert isinstance(backup_codes, BackupCodesResponse)
        assert backup_codes.success is True
        assert len(backup_codes.codes) == 10  # 默认生成10个
        
        # 验证备份代码格式
        for code in backup_codes.codes:
            assert len(code) == 8  # 默认长度
            assert code.isupper()  # 应该是大写
            assert code.isalnum()  # 应该是字母数字
    
    @pytest.mark.asyncio
    async def test_regenerate_backup_codes(self, mfa_manager, mock_redis_client):
        """测试重新生成备份代码"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 模拟已有旧的备份代码
        old_backup_codes = [
            {"code": "OLDCODE1", "used": False},
            {"code": "OLDCODE2", "used": True}
        ]
        mock_redis_client.get.return_value = old_backup_codes
        
        new_backup_codes = await mfa_manager.generate_backup_codes(user_id, tenant_id)
        
        assert new_backup_codes.success is True
        assert len(new_backup_codes.codes) == 10
        
        # 新代码应该与旧代码不同
        for code in new_backup_codes.codes:
            assert code not in ["OLDCODE1", "OLDCODE2"]
        
        # 验证Redis被调用保存新代码
        mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_disable_mfa(self, mfa_manager, mock_redis_client):
        """测试禁用MFA"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        success = await mfa_manager.disable_mfa(user_id, tenant_id)
        
        assert success is True
        
        # 验证相关数据被删除
        expected_calls = [
            f"mfa_totp:{tenant_id}:{user_id}",
            f"mfa_sms:{tenant_id}:{user_id}",
            f"mfa_email:{tenant_id}:{user_id}",
            f"mfa_backup_codes:{tenant_id}:{user_id}"
        ]
        
        # Redis delete应该被调用多次
        assert mock_redis_client.delete.call_count >= len(expected_calls)
    
    @pytest.mark.asyncio
    async def test_get_mfa_status(self, mfa_manager, mock_redis_client):
        """测试获取MFA状态"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 模拟用户启用了TOTP和SMS
        def mock_get_side_effect(key):
            if "mfa_totp" in key:
                return {"secret": "test-secret", "verified": True}
            elif "mfa_sms" in key:
                return {"phone": "+1234567890", "verified": True}
            else:
                return None
        
        mock_redis_client.get.side_effect = mock_get_side_effect
        
        status = await mfa_manager.get_mfa_status(user_id, tenant_id)
        
        assert status is not None
        assert status["mfa_enabled"] is True
        assert MFAMethod.TOTP in status["enabled_methods"]
        assert MFAMethod.SMS in status["enabled_methods"]
        assert MFAMethod.EMAIL not in status["enabled_methods"]
    
    @pytest.mark.asyncio
    async def test_send_sms_code(self, mfa_manager, mock_redis_client):
        """测试发送SMS验证码"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        phone_number = "+1234567890"
        
        # 模拟SMS发送成功
        with patch.object(mfa_manager, '_send_sms_code', return_value=True):
            success = await mfa_manager.send_verification_code(
                user_id, tenant_id, MFAMethod.SMS, phone_number=phone_number
            )
            
            assert success is True
            
            # 验证验证码被保存到Redis
            mock_redis_client.set.assert_called()
            
            # 验证过期时间被设置
            call_args = mock_redis_client.set.call_args_list[-1]
            assert "expire" in call_args.kwargs or len(call_args.args) > 2
    
    @pytest.mark.asyncio
    async def test_send_email_code(self, mfa_manager, mock_redis_client):
        """测试发送Email验证码"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        email = "test@example.com"
        
        # 模拟邮件发送成功
        with patch.object(mfa_manager, '_send_email_code', return_value=True):
            success = await mfa_manager.send_verification_code(
                user_id, tenant_id, MFAMethod.EMAIL, email=email
            )
            
            assert success is True
            
            # 验证验证码被保存到Redis
            mock_redis_client.set.assert_called()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mfa_manager, mock_redis_client):
        """测试验证码发送频率限制"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 模拟已经发送了太多验证码
        mock_redis_client.get.return_value = "6"  # 超过限制
        
        with patch.object(mfa_manager, '_send_sms_code', return_value=True):
            success = await mfa_manager.send_verification_code(
                user_id, tenant_id, MFAMethod.SMS, phone_number="+1234567890"
            )
            
            assert success is False
    
    @pytest.mark.asyncio
    async def test_totp_window_tolerance(self, mfa_manager, mock_redis_client):
        """测试TOTP时间窗口容错"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        # 生成前一个时间窗口的代码（30秒前）
        previous_code = totp.at(time.time() - 30)
        
        mock_totp_data = {
            "secret": secret,
            "verified": False,
            "setup_time": time.time()
        }
        mock_redis_client.get.return_value = mock_totp_data
        
        request = MFAVerifyRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.TOTP,
            code=previous_code
        )
        
        result = await mfa_manager.verify_mfa(request)
        
        # 前一个时间窗口的代码应该仍然有效
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_backup_codes_uniqueness(self, mfa_manager):
        """测试备份代码唯一性"""
        # 生成多组备份代码
        codes_set1 = await mfa_manager.generate_backup_codes("user-1", "tenant-1")
        codes_set2 = await mfa_manager.generate_backup_codes("user-2", "tenant-1")
        codes_set3 = await mfa_manager.generate_backup_codes("user-1", "tenant-2")
        
        # 验证每组代码内部唯一
        assert len(set(codes_set1.codes)) == len(codes_set1.codes)
        assert len(set(codes_set2.codes)) == len(codes_set2.codes)
        assert len(set(codes_set3.codes)) == len(codes_set3.codes)
        
        # 验证不同组之间的代码唯一
        all_codes = codes_set1.codes + codes_set2.codes + codes_set3.codes
        assert len(set(all_codes)) == len(all_codes)
    
    @pytest.mark.asyncio
    async def test_mfa_setup_with_existing_method(self, mfa_manager, mock_redis_client):
        """测试设置已存在的MFA方法"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 模拟已经存在TOTP设置
        mock_redis_client.get.return_value = {
            "secret": "existing-secret",
            "verified": True
        }
        
        request = MFASetupRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.TOTP,
            user_email="test@example.com"
        )
        
        result = await mfa_manager.setup_mfa(request)
        
        # 应该重新设置并生成新的密钥
        assert result.success is True
        assert result.secret != "existing-secret"
    
    @pytest.mark.asyncio
    async def test_verification_code_expiration(self, mfa_manager, mock_redis_client):
        """测试验证码过期处理"""
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 模拟Redis返回None（表示验证码已过期或不存在）
        mock_redis_client.get.return_value = None
        
        request = MFAVerifyRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.SMS,
            code="123456"
        )
        
        result = await mfa_manager.verify_mfa(request)
        
        assert result.success is False
        assert "验证码不存在或已过期" in result.message
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, mfa_manager):
        """测试Redis错误处理"""
        # 创建会抛出异常的模拟Redis客户端
        mock_redis_error = AsyncMock()
        mock_redis_error.get.side_effect = Exception("Redis connection failed")
        mock_redis_error.set.side_effect = Exception("Redis connection failed")
        mock_redis_error.delete.side_effect = Exception("Redis connection failed")
        
        mfa_manager.redis_client = mock_redis_error
        
        # 设置MFA应该失败
        request = MFASetupRequest(
            user_id="user-123",
            tenant_id="tenant-123",
            method=MFAMethod.TOTP,
            user_email="test@example.com"
        )
        
        result = await mfa_manager.setup_mfa(request)
        
        assert result.success is False
        assert "服务异常" in result.message
        
        # 验证MFA应该失败
        verify_request = MFAVerifyRequest(
            user_id="user-123",
            tenant_id="tenant-123",
            method=MFAMethod.TOTP,
            code="123456"
        )
        
        verify_result = await mfa_manager.verify_mfa(verify_request)
        
        assert verify_result.success is False
        assert "服务异常" in verify_result.message
    
    @pytest.mark.asyncio
    async def test_concurrent_mfa_operations(self, mfa_manager, mock_redis_client):
        """测试并发MFA操作"""
        import asyncio
        
        user_id = "user-123"
        tenant_id = "tenant-123"
        
        # 并发设置多种MFA方法
        tasks = []
        
        # TOTP设置
        totp_request = MFASetupRequest(
            user_id=user_id,
            tenant_id=tenant_id,
            method=MFAMethod.TOTP,
            user_email="test@example.com"
        )
        tasks.append(mfa_manager.setup_mfa(totp_request))
        
        # SMS设置
        with patch.object(mfa_manager, '_send_sms_code', return_value=True):
            sms_request = MFASetupRequest(
                user_id=user_id,
                tenant_id=tenant_id,
                method=MFAMethod.SMS,
                phone_number="+1234567890"
            )
            tasks.append(mfa_manager.setup_mfa(sms_request))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查是否有异常
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"并发操作产生异常: {result}")
            else:
                assert result.success is True


class TestMFAModels:
    """MFA模型测试"""
    
    def test_mfa_setup_request(self):
        """测试MFA设置请求模型"""
        request = MFASetupRequest(
            user_id="user-123",
            tenant_id="tenant-123",
            method=MFAMethod.TOTP,
            user_email="test@example.com"
        )
        
        assert request.user_id == "user-123"
        assert request.tenant_id == "tenant-123"
        assert request.method == MFAMethod.TOTP
        assert request.user_email == "test@example.com"
    
    def test_mfa_verify_request(self):
        """测试MFA验证请求模型"""
        request = MFAVerifyRequest(
            user_id="user-123",
            tenant_id="tenant-123",
            method=MFAMethod.TOTP,
            code="123456"
        )
        
        assert request.user_id == "user-123"
        assert request.tenant_id == "tenant-123"
        assert request.method == MFAMethod.TOTP
        assert request.code == "123456"
    
    def test_mfa_setup_response(self):
        """测试MFA设置响应模型"""
        response = MFASetupResponse(
            success=True,
            method=MFAMethod.TOTP,
            secret="test-secret",
            qr_code_url="otpauth://totp/test",
            backup_codes=["CODE1", "CODE2"],
            message="设置成功"
        )
        
        assert response.success is True
        assert response.method == MFAMethod.TOTP
        assert response.secret == "test-secret"
        assert response.qr_code_url == "otpauth://totp/test"
        assert "CODE1" in response.backup_codes
        assert response.message == "设置成功"
    
    def test_mfa_verify_response(self):
        """测试MFA验证响应模型"""
        response = MFAVerifyResponse(
            success=True,
            method=MFAMethod.TOTP,
            message="验证成功"
        )
        
        assert response.success is True
        assert response.method == MFAMethod.TOTP
        assert response.message == "验证成功"
    
    def test_backup_codes_response(self):
        """测试备份代码响应模型"""
        response = BackupCodesResponse(
            success=True,
            codes=["CODE1", "CODE2", "CODE3"],
            message="备份代码生成成功"
        )
        
        assert response.success is True
        assert len(response.codes) == 3
        assert "CODE1" in response.codes
        assert response.message == "备份代码生成成功"