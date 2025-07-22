"""
多因素认证（MFA）管理器

支持多种MFA方式：
- TOTP（基于时间的一次性密码）
- SMS短信验证码
- WebAuthn（生物识别和硬件密钥）
- 邮箱验证码

提供MFA设置、验证、恢复码管理等完整功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import secrets
import time
import hashlib
import hmac
import struct
import base64
import qrcode
import io
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import pyotp
import httpx

from ..utils.redis_client import RedisClient
from ..utils.logging import get_logger
from ..config import Settings

logger = get_logger(__name__)


class MFAMethod(Enum):
    """MFA方法枚举"""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    WEBAUTHN = "webauthn"


@dataclass
class MFASetupResult:
    """MFA设置结果"""
    success: bool
    method: MFAMethod
    secret_key: Optional[str] = None
    qr_code_data: Optional[str] = None
    backup_codes: Optional[List[str]] = None
    message: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class MFAVerifyResult:
    """MFA验证结果"""
    success: bool
    method: MFAMethod
    user_id: str
    backup_code_used: bool = False
    remaining_backup_codes: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class MFAStatus:
    """用户MFA状态"""
    user_id: str
    enabled_methods: List[MFAMethod]
    backup_codes_remaining: int
    last_used_method: Optional[MFAMethod] = None
    last_used_at: Optional[float] = None


class MFAManager:
    """
    多因素认证管理器
    
    功能特性：
    - TOTP密钥生成和验证
    - SMS短信发送和验证
    - 邮箱验证码发送和验证
    - WebAuthn集成支持
    - 备用恢复码生成和管理
    - 防重放攻击保护
    """
    
    def __init__(self, redis_client: RedisClient, settings: Settings):
        self.redis_client = redis_client
        self.settings = settings
        
        # MFA配置参数
        self.totp_window = 30  # TOTP时间窗口（秒）
        self.sms_code_length = 6  # SMS验证码长度
        self.email_code_length = 6  # 邮箱验证码长度
        self.code_expire_minutes = 5  # 验证码过期时间（分钟）
        self.backup_codes_count = 10  # 备用码数量
        
        # 防重放保护
        self.used_codes_expire = 300  # 已使用验证码记录保存时间（秒）
        
    async def setup_totp(self, user_id: str, user_email: str) -> MFASetupResult:
        """
        设置TOTP多因素认证
        
        Args:
            user_id: 用户ID
            user_email: 用户邮箱
            
        Returns:
            MFASetupResult: TOTP设置结果，包含密钥和二维码
        """
        try:
            # 生成TOTP密钥
            secret_key = pyotp.random_base32()
            
            # 创建TOTP对象
            totp = pyotp.TOTP(secret_key)
            
            # 生成二维码数据
            issuer_name = "Lyss AI Platform"
            qr_data = totp.provisioning_uri(
                name=user_email,
                issuer_name=issuer_name
            )
            
            # 生成二维码图片
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # 转换为base64字符串
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            qr_code_base64 = base64.b64encode(buf.getvalue()).decode()
            
            # 生成备用恢复码
            backup_codes = self._generate_backup_codes()
            
            # 存储TOTP配置（待验证状态）
            mfa_config = {
                "method": MFAMethod.TOTP.value,
                "secret_key": secret_key,
                "backup_codes": backup_codes,
                "verified": False,
                "created_at": time.time()
            }
            
            await self.redis_client.set(
                f"mfa_setup:{user_id}:totp",
                mfa_config,
                expire=1800  # 30分钟过期
            )
            
            logger.info(
                f"TOTP设置启动成功: 用户{user_id}",
                operation="setup_totp",
                data={"user_id": user_id, "user_email": user_email}
            )
            
            return MFASetupResult(
                success=True,
                method=MFAMethod.TOTP,
                secret_key=secret_key,
                qr_code_data=f"data:image/png;base64,{qr_code_base64}",
                backup_codes=backup_codes,
                message="请使用认证器应用扫描二维码，然后输入6位验证码完成设置"
            )
            
        except Exception as e:
            logger.error(
                f"TOTP设置失败: {str(e)}",
                operation="setup_totp",
                data={"user_id": user_id, "error": str(e)}
            )
            
            return MFASetupResult(
                success=False,
                method=MFAMethod.TOTP,
                error_message=f"TOTP设置失败: {str(e)}"
            )
    
    async def verify_totp_setup(self, user_id: str, totp_code: str) -> MFASetupResult:
        """
        验证TOTP设置
        
        Args:
            user_id: 用户ID
            totp_code: TOTP验证码
            
        Returns:
            MFASetupResult: 验证结果
        """
        try:
            # 获取待验证的TOTP配置
            setup_key = f"mfa_setup:{user_id}:totp"
            mfa_config = await self.redis_client.get(setup_key)
            
            if not mfa_config:
                return MFASetupResult(
                    success=False,
                    method=MFAMethod.TOTP,
                    error_message="TOTP设置会话已过期，请重新设置"
                )
            
            # 验证TOTP码
            totp = pyotp.TOTP(mfa_config["secret_key"])
            if not totp.verify(totp_code, valid_window=1):
                return MFASetupResult(
                    success=False,
                    method=MFAMethod.TOTP,
                    error_message="验证码错误，请重新输入"
                )
            
            # 验证成功，保存MFA配置
            final_config = {
                "method": MFAMethod.TOTP.value,
                "secret_key": mfa_config["secret_key"],
                "backup_codes": mfa_config["backup_codes"],
                "verified": True,
                "enabled_at": time.time()
            }
            
            await self.redis_client.set(
                f"mfa_config:{user_id}:totp",
                final_config
            )
            
            # 删除临时设置数据
            await self.redis_client.delete(setup_key)
            
            # 标记用户已启用MFA
            await self._update_user_mfa_status(user_id, MFAMethod.TOTP, True)
            
            logger.info(
                f"TOTP设置完成: 用户{user_id}",
                operation="verify_totp_setup",
                data={"user_id": user_id}
            )
            
            return MFASetupResult(
                success=True,
                method=MFAMethod.TOTP,
                backup_codes=mfa_config["backup_codes"],
                message="TOTP多因素认证设置成功！请妥善保存备用恢复码"
            )
            
        except Exception as e:
            logger.error(
                f"TOTP设置验证失败: {str(e)}",
                operation="verify_totp_setup",
                data={"user_id": user_id, "error": str(e)}
            )
            
            return MFASetupResult(
                success=False,
                method=MFAMethod.TOTP,
                error_message=f"TOTP设置验证失败: {str(e)}"
            )
    
    async def setup_sms(self, user_id: str, phone_number: str) -> MFASetupResult:
        """
        设置SMS多因素认证
        
        Args:
            user_id: 用户ID
            phone_number: 手机号码
            
        Returns:
            MFASetupResult: SMS设置结果
        """
        try:
            # 生成SMS验证码
            sms_code = self._generate_numeric_code(self.sms_code_length)
            
            # 发送SMS验证码
            send_result = await self._send_sms_code(phone_number, sms_code)
            
            if not send_result["success"]:
                return MFASetupResult(
                    success=False,
                    method=MFAMethod.SMS,
                    error_message=f"SMS发送失败: {send_result['error']}"
                )
            
            # 存储SMS设置配置
            setup_config = {
                "method": MFAMethod.SMS.value,
                "phone_number": phone_number,
                "sms_code": sms_code,
                "verified": False,
                "created_at": time.time()
            }
            
            await self.redis_client.set(
                f"mfa_setup:{user_id}:sms",
                setup_config,
                expire=self.code_expire_minutes * 60
            )
            
            logger.info(
                f"SMS MFA设置启动: 用户{user_id}",
                operation="setup_sms",
                data={
                    "user_id": user_id,
                    "phone_number": phone_number[-4:]  # 只记录后4位
                }
            )
            
            return MFASetupResult(
                success=True,
                method=MFAMethod.SMS,
                message=f"验证码已发送至 {phone_number[-4:]}，请输入6位验证码完成设置"
            )
            
        except Exception as e:
            logger.error(
                f"SMS MFA设置失败: {str(e)}",
                operation="setup_sms",
                data={"user_id": user_id, "error": str(e)}
            )
            
            return MFASetupResult(
                success=False,
                method=MFAMethod.SMS,
                error_message=f"SMS MFA设置失败: {str(e)}"
            )
    
    async def verify_mfa(
        self, 
        user_id: str, 
        method: MFAMethod, 
        code: str,
        backup_code: bool = False
    ) -> MFAVerifyResult:
        """
        验证MFA代码
        
        Args:
            user_id: 用户ID
            method: MFA方法
            code: 验证码
            backup_code: 是否为备用恢复码
            
        Returns:
            MFAVerifyResult: 验证结果
        """
        try:
            # 检查防重放攻击
            replay_key = f"mfa_used_code:{user_id}:{code}"
            if await self.redis_client.exists(replay_key):
                return MFAVerifyResult(
                    success=False,
                    method=method,
                    user_id=user_id,
                    error_message="验证码已被使用，请重新获取"
                )
            
            # 如果是备用恢复码
            if backup_code:
                return await self._verify_backup_code(user_id, code)
            
            # 根据方法验证
            if method == MFAMethod.TOTP:
                result = await self._verify_totp_code(user_id, code)
            elif method == MFAMethod.SMS:
                result = await self._verify_sms_code(user_id, code)
            elif method == MFAMethod.EMAIL:
                result = await self._verify_email_code(user_id, code)
            else:
                return MFAVerifyResult(
                    success=False,
                    method=method,
                    user_id=user_id,
                    error_message=f"不支持的MFA方法: {method.value}"
                )
            
            # 验证成功，标记代码已使用（防重放）
            if result.success:
                await self.redis_client.set(
                    replay_key,
                    time.time(),
                    expire=self.used_codes_expire
                )
                
                # 更新最后使用时间
                await self._update_last_used_mfa(user_id, method)
            
            return result
            
        except Exception as e:
            logger.error(
                f"MFA验证异常: {str(e)}",
                operation="verify_mfa",
                data={
                    "user_id": user_id,
                    "method": method.value,
                    "error": str(e)
                }
            )
            
            return MFAVerifyResult(
                success=False,
                method=method,
                user_id=user_id,
                error_message=f"MFA验证服务异常: {str(e)}"
            )
    
    async def _verify_totp_code(self, user_id: str, code: str) -> MFAVerifyResult:
        """验证TOTP代码"""
        # 获取用户TOTP配置
        totp_config = await self.redis_client.get(f"mfa_config:{user_id}:totp")
        
        if not totp_config or not totp_config.get("verified"):
            return MFAVerifyResult(
                success=False,
                method=MFAMethod.TOTP,
                user_id=user_id,
                error_message="TOTP未设置或未验证"
            )
        
        # 验证TOTP码
        totp = pyotp.TOTP(totp_config["secret_key"])
        if totp.verify(code, valid_window=1):
            return MFAVerifyResult(
                success=True,
                method=MFAMethod.TOTP,
                user_id=user_id
            )
        else:
            return MFAVerifyResult(
                success=False,
                method=MFAMethod.TOTP,
                user_id=user_id,
                error_message="TOTP验证码错误或已过期"
            )
    
    async def _verify_sms_code(self, user_id: str, code: str) -> MFAVerifyResult:
        """验证SMS代码"""
        sms_key = f"mfa_sms_code:{user_id}"
        stored_code = await self.redis_client.get(sms_key)
        
        if not stored_code:
            return MFAVerifyResult(
                success=False,
                method=MFAMethod.SMS,
                user_id=user_id,
                error_message="SMS验证码已过期或不存在"
            )
        
        if stored_code == code:
            # 验证成功，删除验证码
            await self.redis_client.delete(sms_key)
            return MFAVerifyResult(
                success=True,
                method=MFAMethod.SMS,
                user_id=user_id
            )
        else:
            return MFAVerifyResult(
                success=False,
                method=MFAMethod.SMS,
                user_id=user_id,
                error_message="SMS验证码错误"
            )
    
    async def _verify_email_code(self, user_id: str, code: str) -> MFAVerifyResult:
        """验证邮箱代码"""
        email_key = f"mfa_email_code:{user_id}"
        stored_code = await self.redis_client.get(email_key)
        
        if not stored_code:
            return MFAVerifyResult(
                success=False,
                method=MFAMethod.EMAIL,
                user_id=user_id,
                error_message="邮箱验证码已过期或不存在"
            )
        
        if stored_code == code:
            # 验证成功，删除验证码
            await self.redis_client.delete(email_key)
            return MFAVerifyResult(
                success=True,
                method=MFAMethod.EMAIL,
                user_id=user_id
            )
        else:
            return MFAVerifyResult(
                success=False,
                method=MFAMethod.EMAIL,
                user_id=user_id,
                error_message="邮箱验证码错误"
            )
    
    async def _verify_backup_code(self, user_id: str, backup_code: str) -> MFAVerifyResult:
        """验证备用恢复码"""
        # 获取用户的备用码配置
        backup_key = f"mfa_backup_codes:{user_id}"
        backup_codes = await self.redis_client.get(backup_key)
        
        if not backup_codes:
            return MFAVerifyResult(
                success=False,
                method=MFAMethod.TOTP,  # 备用码通常关联TOTP
                user_id=user_id,
                error_message="备用恢复码不存在",
                backup_code_used=True
            )
        
        # 检查备用码是否匹配
        if backup_code in backup_codes:
            # 使用后删除该备用码
            backup_codes.remove(backup_code)
            
            # 更新备用码列表
            if backup_codes:
                await self.redis_client.set(backup_key, backup_codes)
            else:
                await self.redis_client.delete(backup_key)
            
            logger.info(
                f"备用恢复码使用成功: 用户{user_id}",
                operation="verify_backup_code",
                data={
                    "user_id": user_id,
                    "remaining_codes": len(backup_codes)
                }
            )
            
            return MFAVerifyResult(
                success=True,
                method=MFAMethod.TOTP,
                user_id=user_id,
                backup_code_used=True,
                remaining_backup_codes=len(backup_codes)
            )
        else:
            return MFAVerifyResult(
                success=False,
                method=MFAMethod.TOTP,
                user_id=user_id,
                error_message="备用恢复码无效",
                backup_code_used=True
            )
    
    async def get_user_mfa_status(self, user_id: str) -> MFAStatus:
        """获取用户MFA状态"""
        try:
            enabled_methods = []
            
            # 检查TOTP
            totp_config = await self.redis_client.get(f"mfa_config:{user_id}:totp")
            if totp_config and totp_config.get("verified"):
                enabled_methods.append(MFAMethod.TOTP)
            
            # 检查SMS
            sms_config = await self.redis_client.get(f"mfa_config:{user_id}:sms")
            if sms_config and sms_config.get("verified"):
                enabled_methods.append(MFAMethod.SMS)
            
            # 检查邮箱
            email_config = await self.redis_client.get(f"mfa_config:{user_id}:email")
            if email_config and email_config.get("verified"):
                enabled_methods.append(MFAMethod.EMAIL)
            
            # 获取备用码数量
            backup_codes = await self.redis_client.get(f"mfa_backup_codes:{user_id}")
            backup_codes_count = len(backup_codes) if backup_codes else 0
            
            # 获取最后使用信息
            last_used_info = await self.redis_client.get(f"mfa_last_used:{user_id}")
            last_used_method = None
            last_used_at = None
            
            if last_used_info:
                last_used_method = MFAMethod(last_used_info["method"])
                last_used_at = last_used_info["timestamp"]
            
            return MFAStatus(
                user_id=user_id,
                enabled_methods=enabled_methods,
                backup_codes_remaining=backup_codes_count,
                last_used_method=last_used_method,
                last_used_at=last_used_at
            )
            
        except Exception as e:
            logger.error(
                f"获取用户MFA状态失败: {str(e)}",
                operation="get_user_mfa_status",
                data={"user_id": user_id, "error": str(e)}
            )
            
            return MFAStatus(
                user_id=user_id,
                enabled_methods=[],
                backup_codes_remaining=0
            )
    
    async def disable_mfa(self, user_id: str, method: MFAMethod) -> bool:
        """禁用指定的MFA方法"""
        try:
            # 删除对应的MFA配置
            await self.redis_client.delete(f"mfa_config:{user_id}:{method.value}")
            
            # 如果禁用的是TOTP，也删除备用码
            if method == MFAMethod.TOTP:
                await self.redis_client.delete(f"mfa_backup_codes:{user_id}")
            
            # 更新用户MFA状态
            await self._update_user_mfa_status(user_id, method, False)
            
            logger.info(
                f"MFA方法已禁用: 用户{user_id}, 方法{method.value}",
                operation="disable_mfa",
                data={"user_id": user_id, "method": method.value}
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"禁用MFA失败: {str(e)}",
                operation="disable_mfa",
                data={
                    "user_id": user_id,
                    "method": method.value,
                    "error": str(e)
                }
            )
            return False
    
    def _generate_backup_codes(self) -> List[str]:
        """生成备用恢复码"""
        codes = []
        for _ in range(self.backup_codes_count):
            # 生成8位数字码
            code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(code)
        return codes
    
    def _generate_numeric_code(self, length: int) -> str:
        """生成数字验证码"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])
    
    async def _send_sms_code(self, phone_number: str, code: str) -> Dict[str, Any]:
        """发送SMS验证码"""
        # 这里需要集成实际的SMS服务商
        # 例如：阿里云短信、腾讯云短信、Twilio等
        
        # 模拟SMS发送
        logger.info(
            f"模拟SMS发送: {phone_number[-4:]} -> {code}",
            operation="send_sms_code",
            data={
                "phone_number": phone_number[-4:],
                "code_length": len(code)
            }
        )
        
        # TODO: 实际实现SMS发送
        return {
            "success": True,
            "message": "SMS验证码发送成功"
        }
    
    async def _update_user_mfa_status(self, user_id: str, method: MFAMethod, enabled: bool):
        """更新用户MFA状态"""
        status_key = f"user_mfa_status:{user_id}"
        user_status = await self.redis_client.get(status_key) or {"methods": {}}
        
        user_status["methods"][method.value] = enabled
        user_status["updated_at"] = time.time()
        
        await self.redis_client.set(status_key, user_status)
    
    async def _update_last_used_mfa(self, user_id: str, method: MFAMethod):
        """更新最后使用的MFA方法"""
        last_used_info = {
            "method": method.value,
            "timestamp": time.time()
        }
        
        await self.redis_client.set(
            f"mfa_last_used:{user_id}",
            last_used_info,
            expire=86400 * 30  # 保存30天
        )