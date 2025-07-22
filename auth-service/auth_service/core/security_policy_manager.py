"""
安全策略管理器

负责管理系统安全策略和配置：
- 密码策略管理
- 会话安全策略
- IP白名单/黑名单管理
- 登录安全策略
- 审计日志策略

提供动态配置更新和策略执行功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import time
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import ipaddress

from ..utils.redis_client import RedisClient
from ..utils.logging import get_logger
from ..config import Settings

logger = get_logger(__name__)


class PolicyLevel(Enum):
    """安全策略级别"""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PasswordPolicy:
    """密码策略配置"""
    min_length: int = 8
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digits: bool = True
    require_special_chars: bool = True
    special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    password_expire_days: int = 90
    password_history_count: int = 5
    prevent_common_passwords: bool = True
    prevent_user_info_in_password: bool = True


@dataclass
class SessionPolicy:
    """会话安全策略"""
    max_concurrent_sessions: int = 5
    session_timeout_minutes: int = 30
    idle_timeout_minutes: int = 15
    require_re_auth_for_sensitive_ops: bool = True
    detect_concurrent_logins: bool = True
    force_logout_on_ip_change: bool = False
    remember_device_days: int = 30


@dataclass
class LoginPolicy:
    """登录安全策略"""
    max_failed_attempts: int = 5
    lockout_duration_minutes: int = 30
    progressive_lockout_enabled: bool = True
    ip_based_lockout: bool = True
    geo_blocking_enabled: bool = False
    allowed_countries: List[str] = None
    suspicious_login_detection: bool = True
    require_mfa_for_new_devices: bool = True
    require_email_verification: bool = True


@dataclass
class AuditPolicy:
    """审计日志策略"""
    log_all_api_calls: bool = True
    log_authentication_events: bool = True
    log_authorization_failures: bool = True
    log_sensitive_operations: bool = True
    log_retention_days: int = 365
    real_time_alerts_enabled: bool = True
    alert_email: Optional[str] = None
    export_logs_enabled: bool = True


@dataclass
class IPPolicy:
    """IP访问策略"""
    whitelist_enabled: bool = False
    blacklist_enabled: bool = True
    allowed_ip_ranges: List[str] = None
    blocked_ip_ranges: List[str] = None
    auto_block_suspicious_ips: bool = True
    auto_block_threshold: int = 10
    block_duration_hours: int = 24


class SecurityPolicyManager:
    """
    安全策略管理器
    
    功能特性：
    - 策略定义和存储
    - 动态策略更新
    - 策略验证和执行
    - 策略模板管理
    - 合规性检查
    """
    
    def __init__(self, redis_client: RedisClient, settings: Settings):
        self.redis_client = redis_client
        self.settings = settings
        
        # 策略键前缀
        self.policy_prefix = "security_policy"
        
        # 默认策略配置
        self.default_policies = self._get_default_policies()
        
        # 常见弱密码列表
        self.common_passwords = [
            "password", "123456", "123456789", "12345678", "12345",
            "1234567", "password123", "admin", "qwerty", "abc123",
            "Password1", "welcome", "monkey", "dragon", "master"
        ]
    
    def _get_default_policies(self) -> Dict[str, Any]:
        """获取默认安全策略"""
        return {
            "password": asdict(PasswordPolicy()),
            "session": asdict(SessionPolicy()),
            "login": asdict(LoginPolicy()),
            "audit": asdict(AuditPolicy()),
            "ip": asdict(IPPolicy())
        }
    
    async def initialize_policies(self):
        """初始化安全策略"""
        try:
            # 检查是否已存在策略配置
            existing_policies = await self.redis_client.get(f"{self.policy_prefix}:config")
            
            if not existing_policies:
                # 使用默认策略初始化
                await self.update_all_policies(self.default_policies)
                
                logger.info(
                    "安全策略已初始化为默认配置",
                    operation="initialize_policies",
                    data={"policy_count": len(self.default_policies)}
                )
            else:
                logger.info(
                    "发现现有安全策略配置",
                    operation="initialize_policies",
                    data={"existing_policies": list(existing_policies.keys())}
                )
                
        except Exception as e:
            logger.error(
                f"安全策略初始化失败: {str(e)}",
                operation="initialize_policies",
                data={"error": str(e)}
            )
            raise
    
    async def get_policy(self, policy_type: str) -> Optional[Dict[str, Any]]:
        """获取指定类型的安全策略"""
        try:
            policies = await self.redis_client.get(f"{self.policy_prefix}:config")
            
            if not policies:
                # 返回默认策略
                return self.default_policies.get(policy_type)
            
            return policies.get(policy_type)
            
        except Exception as e:
            logger.error(
                f"获取安全策略失败: {str(e)}",
                operation="get_policy",
                data={"policy_type": policy_type, "error": str(e)}
            )
            return self.default_policies.get(policy_type)
    
    async def update_policy(self, policy_type: str, policy_config: Dict[str, Any]) -> bool:
        """更新指定类型的安全策略"""
        try:
            # 验证策略配置
            validation_result = self._validate_policy(policy_type, policy_config)
            if not validation_result["valid"]:
                logger.warning(
                    f"策略配置验证失败: {validation_result['errors']}",
                    operation="update_policy",
                    data={
                        "policy_type": policy_type,
                        "errors": validation_result["errors"]
                    }
                )
                return False
            
            # 获取当前所有策略
            all_policies = await self.redis_client.get(f"{self.policy_prefix}:config") or {}
            
            # 更新指定策略
            all_policies[policy_type] = policy_config
            all_policies["last_updated"] = time.time()
            
            # 保存到Redis
            await self.redis_client.set(f"{self.policy_prefix}:config", all_policies)
            
            # 记录策略变更
            await self._log_policy_change(policy_type, policy_config)
            
            logger.info(
                f"安全策略已更新: {policy_type}",
                operation="update_policy",
                data={"policy_type": policy_type}
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"更新安全策略失败: {str(e)}",
                operation="update_policy",
                data={
                    "policy_type": policy_type,
                    "error": str(e)
                }
            )
            return False
    
    async def update_all_policies(self, policies: Dict[str, Dict[str, Any]]) -> bool:
        """批量更新所有安全策略"""
        try:
            # 验证所有策略
            for policy_type, policy_config in policies.items():
                validation_result = self._validate_policy(policy_type, policy_config)
                if not validation_result["valid"]:
                    logger.error(
                        f"策略验证失败: {policy_type}",
                        operation="update_all_policies",
                        data={
                            "policy_type": policy_type,
                            "errors": validation_result["errors"]
                        }
                    )
                    return False
            
            # 添加更新时间戳
            policies["last_updated"] = time.time()
            policies["version"] = int(time.time())
            
            # 保存所有策略
            await self.redis_client.set(f"{self.policy_prefix}:config", policies)
            
            logger.info(
                "所有安全策略已更新",
                operation="update_all_policies",
                data={"policy_count": len(policies) - 2}  # 减去时间戳字段
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"批量更新安全策略失败: {str(e)}",
                operation="update_all_policies",
                data={"error": str(e)}
            )
            return False
    
    async def validate_password(self, password: str, user_info: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """根据密码策略验证密码强度"""
        try:
            policy = await self.get_policy("password")
            if not policy:
                policy = self.default_policies["password"]
            
            errors = []
            
            # 长度检查
            if len(password) < policy["min_length"]:
                errors.append(f"密码长度至少需要{policy['min_length']}个字符")
            
            if len(password) > policy["max_length"]:
                errors.append(f"密码长度不能超过{policy['max_length']}个字符")
            
            # 字符类型检查
            if policy["require_uppercase"] and not re.search(r'[A-Z]', password):
                errors.append("密码必须包含至少一个大写字母")
            
            if policy["require_lowercase"] and not re.search(r'[a-z]', password):
                errors.append("密码必须包含至少一个小写字母")
            
            if policy["require_digits"] and not re.search(r'\d', password):
                errors.append("密码必须包含至少一个数字")
            
            if policy["require_special_chars"]:
                special_chars_pattern = f"[{re.escape(policy['special_chars'])}]"
                if not re.search(special_chars_pattern, password):
                    errors.append(f"密码必须包含至少一个特殊字符: {policy['special_chars']}")
            
            # 常见密码检查
            if policy["prevent_common_passwords"]:
                password_lower = password.lower()
                for common_pwd in self.common_passwords:
                    if common_pwd.lower() in password_lower:
                        errors.append("密码不能包含常见弱密码")
                        break
            
            # 用户信息检查
            if policy["prevent_user_info_in_password"] and user_info:
                password_lower = password.lower()
                for field, value in user_info.items():
                    if value and len(value) >= 3 and value.lower() in password_lower:
                        errors.append("密码不能包含用户个人信息")
                        break
            
            # 计算密码强度评分
            strength_score = self._calculate_password_strength(password)
            
            result = {
                "valid": len(errors) == 0,
                "errors": errors,
                "strength_score": strength_score,
                "strength_level": self._get_strength_level(strength_score),
                "policy_compliant": len(errors) == 0
            }
            
            return result
            
        except Exception as e:
            logger.error(
                f"密码验证异常: {str(e)}",
                operation="validate_password",
                data={"error": str(e)}
            )
            return {
                "valid": False,
                "errors": ["密码验证服务异常"],
                "strength_score": 0,
                "strength_level": "unknown"
            }
    
    async def check_ip_access(self, ip_address: str) -> Dict[str, Any]:
        """检查IP地址访问权限"""
        try:
            policy = await self.get_policy("ip")
            if not policy:
                return {"allowed": True, "reason": "无IP策略配置"}
            
            ip_obj = ipaddress.ip_address(ip_address)
            
            # 检查黑名单
            if policy["blacklist_enabled"] and policy.get("blocked_ip_ranges"):
                for blocked_range in policy["blocked_ip_ranges"]:
                    try:
                        if ip_obj in ipaddress.ip_network(blocked_range, strict=False):
                            return {
                                "allowed": False,
                                "reason": f"IP地址在黑名单中: {blocked_range}"
                            }
                    except ValueError:
                        continue
            
            # 检查白名单
            if policy["whitelist_enabled"] and policy.get("allowed_ip_ranges"):
                for allowed_range in policy["allowed_ip_ranges"]:
                    try:
                        if ip_obj in ipaddress.ip_network(allowed_range, strict=False):
                            return {
                                "allowed": True,
                                "reason": f"IP地址在白名单中: {allowed_range}"
                            }
                    except ValueError:
                        continue
                
                # 如果启用白名单但IP不在其中
                return {
                    "allowed": False,
                    "reason": "IP地址不在白名单中"
                }
            
            # 检查自动封禁
            if policy["auto_block_suspicious_ips"]:
                blocked_until = await self.redis_client.get(f"blocked_ip:{ip_address}")
                if blocked_until and time.time() < blocked_until:
                    return {
                        "allowed": False,
                        "reason": "IP地址因可疑活动被暂时封禁",
                        "blocked_until": blocked_until
                    }
            
            return {"allowed": True, "reason": "IP地址检查通过"}
            
        except Exception as e:
            logger.error(
                f"IP访问检查异常: {str(e)}",
                operation="check_ip_access",
                data={"ip_address": ip_address, "error": str(e)}
            )
            # 异常情况下允许访问，但记录日志
            return {"allowed": True, "reason": "IP检查服务异常，默认允许"}
    
    async def record_failed_login(self, ip_address: str, user_id: Optional[str] = None):
        """记录登录失败，用于自动封禁判断"""
        try:
            policy = await self.get_policy("ip")
            if not policy or not policy["auto_block_suspicious_ips"]:
                return
            
            # 记录失败次数
            fail_key = f"login_failures:{ip_address}"
            current_failures = await self.redis_client.get(fail_key) or 0
            current_failures = int(current_failures) + 1
            
            # 设置失败计数，1小时过期
            await self.redis_client.set(fail_key, current_failures, expire=3600)
            
            # 检查是否达到封禁阈值
            if current_failures >= policy["auto_block_threshold"]:
                # 自动封禁IP
                block_duration = policy["block_duration_hours"] * 3600
                block_until = time.time() + block_duration
                
                await self.redis_client.set(
                    f"blocked_ip:{ip_address}",
                    block_until,
                    expire=block_duration
                )
                
                logger.warning(
                    f"IP地址自动封禁: {ip_address}",
                    operation="auto_block_ip",
                    data={
                        "ip_address": ip_address,
                        "failure_count": current_failures,
                        "block_duration_hours": policy["block_duration_hours"]
                    }
                )
                
                # 清除失败计数
                await self.redis_client.delete(fail_key)
            
        except Exception as e:
            logger.error(
                f"记录登录失败异常: {str(e)}",
                operation="record_failed_login",
                data={"ip_address": ip_address, "error": str(e)}
            )
    
    def _validate_policy(self, policy_type: str, policy_config: Dict[str, Any]) -> Dict[str, Any]:
        """验证策略配置"""
        errors = []
        
        try:
            if policy_type == "password":
                errors.extend(self._validate_password_policy(policy_config))
            elif policy_type == "session":
                errors.extend(self._validate_session_policy(policy_config))
            elif policy_type == "login":
                errors.extend(self._validate_login_policy(policy_config))
            elif policy_type == "audit":
                errors.extend(self._validate_audit_policy(policy_config))
            elif policy_type == "ip":
                errors.extend(self._validate_ip_policy(policy_config))
            else:
                errors.append(f"未知的策略类型: {policy_type}")
                
        except Exception as e:
            errors.append(f"策略验证异常: {str(e)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _validate_password_policy(self, policy: Dict[str, Any]) -> List[str]:
        """验证密码策略"""
        errors = []
        
        min_len = policy.get("min_length", 8)
        max_len = policy.get("max_length", 128)
        
        if min_len < 4:
            errors.append("最小密码长度不能小于4")
        if max_len > 256:
            errors.append("最大密码长度不能超过256")
        if min_len >= max_len:
            errors.append("最小密码长度必须小于最大密码长度")
        
        expire_days = policy.get("password_expire_days", 90)
        if expire_days < 1 or expire_days > 365:
            errors.append("密码过期天数必须在1-365之间")
        
        return errors
    
    def _validate_session_policy(self, policy: Dict[str, Any]) -> List[str]:
        """验证会话策略"""
        errors = []
        
        max_sessions = policy.get("max_concurrent_sessions", 5)
        if max_sessions < 1 or max_sessions > 100:
            errors.append("最大并发会话数必须在1-100之间")
        
        timeout = policy.get("session_timeout_minutes", 30)
        if timeout < 5 or timeout > 1440:  # 5分钟到24小时
            errors.append("会话超时时间必须在5-1440分钟之间")
        
        return errors
    
    def _validate_login_policy(self, policy: Dict[str, Any]) -> List[str]:
        """验证登录策略"""
        errors = []
        
        max_attempts = policy.get("max_failed_attempts", 5)
        if max_attempts < 1 or max_attempts > 50:
            errors.append("最大失败尝试次数必须在1-50之间")
        
        lockout_duration = policy.get("lockout_duration_minutes", 30)
        if lockout_duration < 1 or lockout_duration > 10080:  # 1分钟到1周
            errors.append("锁定持续时间必须在1-10080分钟之间")
        
        return errors
    
    def _validate_audit_policy(self, policy: Dict[str, Any]) -> List[str]:
        """验证审计策略"""
        errors = []
        
        retention_days = policy.get("log_retention_days", 365)
        if retention_days < 1 or retention_days > 2555:  # 1天到7年
            errors.append("日志保留天数必须在1-2555之间")
        
        return errors
    
    def _validate_ip_policy(self, policy: Dict[str, Any]) -> List[str]:
        """验证IP策略"""
        errors = []
        
        # 验证IP范围格式
        for field in ["allowed_ip_ranges", "blocked_ip_ranges"]:
            ip_ranges = policy.get(field, [])
            if ip_ranges:
                for ip_range in ip_ranges:
                    try:
                        ipaddress.ip_network(ip_range, strict=False)
                    except ValueError:
                        errors.append(f"无效的IP范围格式: {ip_range}")
        
        threshold = policy.get("auto_block_threshold", 10)
        if threshold < 1 or threshold > 1000:
            errors.append("自动封禁阈值必须在1-1000之间")
        
        return errors
    
    def _calculate_password_strength(self, password: str) -> int:
        """计算密码强度评分（0-100）"""
        score = 0
        
        # 长度评分
        if len(password) >= 8:
            score += 20
        if len(password) >= 12:
            score += 10
        if len(password) >= 16:
            score += 10
        
        # 字符类型评分
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            score += 15
        
        # 复杂度评分
        char_types = 0
        if re.search(r'[a-z]', password):
            char_types += 1
        if re.search(r'[A-Z]', password):
            char_types += 1
        if re.search(r'\d', password):
            char_types += 1
        if re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            char_types += 1
        
        if char_types >= 3:
            score += 15
        
        return min(score, 100)
    
    def _get_strength_level(self, score: int) -> str:
        """根据评分获取强度等级"""
        if score >= 90:
            return "excellent"
        elif score >= 70:
            return "strong"
        elif score >= 50:
            return "medium"
        elif score >= 30:
            return "weak"
        else:
            return "very_weak"
    
    async def _log_policy_change(self, policy_type: str, policy_config: Dict[str, Any]):
        """记录策略变更日志"""
        try:
            change_record = {
                "policy_type": policy_type,
                "timestamp": time.time(),
                "config": policy_config,
                "operation": "policy_update"
            }
            
            # 将变更记录存储到审计日志
            await self.redis_client.set(
                f"policy_change_log:{int(time.time())}",
                change_record,
                expire=86400 * 365  # 保存1年
            )
            
        except Exception as e:
            logger.error(
                f"记录策略变更日志失败: {str(e)}",
                operation="log_policy_change",
                data={"error": str(e)}
            )