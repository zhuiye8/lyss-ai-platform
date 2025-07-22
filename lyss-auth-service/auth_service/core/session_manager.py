"""
会话管理器

实现Redis会话存储和并发控制功能，包括：
- 分布式会话管理（Redis存储、集群支持）
- 会话策略控制（单点登录、并发限制、设备管理）
- 会话安全防护（劫持检测、固定攻击、异常监控）
- 活跃状态监控（心跳检测、超时清理、统计分析）

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import AuthServiceSettings
from ..models.auth_models import TokenPayload, UserModel
from .jwt_manager import JWTManager


class SessionState(str, Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPICIOUS = "suspicious"


class DeviceType(str, Enum):
    """设备类型枚举"""
    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    API = "api"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """设备信息"""
    device_type: str
    os: Optional[str] = None
    browser: Optional[str] = None
    version: Optional[str] = None
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


@dataclass
class SessionInfo:
    """会话信息"""
    session_id: str
    user_id: str
    tenant_id: str
    ip_address: str
    user_agent: str
    device_info: DeviceInfo
    login_time: datetime
    last_activity: datetime
    expires_at: datetime
    state: SessionState
    access_token_jti: str
    refresh_token_jti: str
    location: Optional[str] = None
    is_suspicious: bool = False
    concurrent_session_count: int = 1


@dataclass
class SessionPolicy:
    """会话策略配置"""
    max_concurrent_sessions: int = 5  # 最大并发会话数
    session_timeout_minutes: int = 720  # 会话超时时间（12小时）
    idle_timeout_minutes: int = 60  # 空闲超时时间
    enable_single_sign_on: bool = False  # 启用单点登录（踢出其他会话）
    enable_device_binding: bool = True  # 启用设备绑定验证
    suspicious_login_detection: bool = True  # 启用可疑登录检测
    require_activity_heartbeat: bool = True  # 需要活跃心跳
    heartbeat_interval_minutes: int = 5  # 心跳间隔


class SessionManager:
    """
    会话管理器
    
    功能特性：
    1. 分布式会话存储 - Redis集群支持，高可用
    2. 会话策略控制 - 并发限制、超时管理、设备控制
    3. 安全防护机制 - 劫持检测、异地登录告警
    4. 活跃状态监控 - 实时心跳、用户活跃分析
    5. 统计分析功能 - 会话统计、用户行为分析
    """
    
    def __init__(
        self,
        settings: AuthServiceSettings,
        jwt_manager: JWTManager,
        redis_client: redis.Redis
    ):
        self.settings = settings
        self.jwt_manager = jwt_manager
        self.redis = redis_client
        
        # 初始化会话策略
        self.session_policy = SessionPolicy()
        
        # Redis键前缀
        self.SESSION_PREFIX = "auth:session:"
        self.USER_SESSIONS_PREFIX = "auth:user_sessions:"
        self.ACTIVE_USERS_PREFIX = "auth:active_users:"
        self.SESSION_HEARTBEAT_PREFIX = "auth:heartbeat:"
        self.SUSPICIOUS_IPS_PREFIX = "auth:suspicious_ips:"
        self.DEVICE_FINGERPRINT_PREFIX = "auth:device_fp:"
    
    async def create_session(
        self,
        user: UserModel,
        ip_address: str,
        user_agent: str,
        device_info: Dict[str, Any],
        access_token_jti: str,
        refresh_token_jti: str
    ) -> SessionInfo:
        """
        创建新会话
        
        Args:
            user: 用户信息
            ip_address: 客户端IP地址
            user_agent: 用户代理字符串
            device_info: 设备信息
            access_token_jti: 访问令牌JTI
            refresh_token_jti: 刷新令牌JTI
            
        Returns:
            SessionInfo: 创建的会话信息
        """
        current_time = datetime.now(timezone.utc)
        session_id = self._generate_session_id(user.id, ip_address, current_time)
        
        # 解析设备信息
        parsed_device_info = self._parse_device_info(user_agent, device_info)
        
        # 检查并发会话限制
        if self.session_policy.max_concurrent_sessions > 0:
            await self._enforce_concurrent_session_limit(user.id)
        
        # 单点登录检查
        if self.session_policy.enable_single_sign_on:
            await self._terminate_other_sessions(user.id, session_id)
        
        # 创建会话信息
        session_info = SessionInfo(
            session_id=session_id,
            user_id=user.id,
            tenant_id=user.tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            device_info=parsed_device_info,
            login_time=current_time,
            last_activity=current_time,
            expires_at=current_time + timedelta(minutes=self.session_policy.session_timeout_minutes),
            state=SessionState.ACTIVE,
            access_token_jti=access_token_jti,
            refresh_token_jti=refresh_token_jti,
            is_suspicious=await self._is_suspicious_login(user.id, ip_address)
        )
        
        # 存储会话信息
        await self._store_session(session_info)
        
        # 更新用户会话列表
        await self._add_user_session(user.id, session_id)
        
        # 更新活跃用户列表
        await self._update_active_users(user.id, session_id)
        
        # 记录登录地理位置（如果有IP地理位置服务）
        # session_info.location = await self._get_ip_location(ip_address)
        
        return session_info
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        session_key = f"{self.SESSION_PREFIX}{session_id}"
        session_data = await self.redis.get(session_key)
        
        if not session_data:
            return None
        
        try:
            data = json.loads(session_data.decode())
            return self._deserialize_session(data)
        except Exception as e:
            print(f"反序列化会话信息失败: {str(e)}")
            return None
    
    async def update_session_activity(
        self,
        session_id: str,
        activity_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        更新会话活跃状态
        
        Args:
            session_id: 会话ID
            activity_data: 活动数据（页面、操作等）
            
        Returns:
            bool: 更新是否成功
        """
        session_info = await self.get_session(session_id)
        if not session_info:
            return False
        
        current_time = datetime.now(timezone.utc)
        
        # 检查会话是否过期
        if current_time > session_info.expires_at:
            await self.terminate_session(session_id, "会话过期")
            return False
        
        # 检查空闲超时
        idle_duration = current_time - session_info.last_activity
        if idle_duration.total_seconds() > self.session_policy.idle_timeout_minutes * 60:
            await self.terminate_session(session_id, "空闲超时")
            return False
        
        # 更新最后活跃时间
        session_info.last_activity = current_time
        
        # 存储更新后的会话信息
        await self._store_session(session_info)
        
        # 更新心跳
        if self.session_policy.require_activity_heartbeat:
            await self._update_heartbeat(session_id)
        
        # 记录活动数据（用于用户行为分析）
        if activity_data:
            await self._record_user_activity(session_info.user_id, activity_data)
        
        return True
    
    async def terminate_session(self, session_id: str, reason: str = "用户主动退出") -> bool:
        """
        终止会话
        
        Args:
            session_id: 会话ID
            reason: 终止原因
            
        Returns:
            bool: 终止是否成功
        """
        session_info = await self.get_session(session_id)
        if not session_info:
            return False
        
        # 撤销相关JWT令牌
        await self.jwt_manager.revoke_token(session_info.access_token_jti, reason)
        await self.jwt_manager.revoke_token(session_info.refresh_token_jti, reason)
        
        # 更新会话状态
        session_info.state = SessionState.TERMINATED
        await self._store_session(session_info)
        
        # 从用户会话列表中移除
        await self._remove_user_session(session_info.user_id, session_id)
        
        # 从活跃用户列表中移除（如果是最后一个会话）
        remaining_sessions = await self.get_user_sessions(session_info.user_id)
        if not remaining_sessions:
            await self._remove_from_active_users(session_info.user_id)
        
        # 清理心跳记录
        await self._clear_heartbeat(session_id)
        
        return True
    
    async def terminate_all_user_sessions(
        self,
        user_id: str,
        except_session_id: Optional[str] = None,
        reason: str = "管理员操作"
    ) -> int:
        """
        终止用户的所有会话
        
        Args:
            user_id: 用户ID
            except_session_id: 排除的会话ID
            reason: 终止原因
            
        Returns:
            int: 终止的会话数量
        """
        user_sessions = await self.get_user_sessions(user_id)
        terminated_count = 0
        
        for session_info in user_sessions:
            if except_session_id and session_info.session_id == except_session_id:
                continue
            
            if await self.terminate_session(session_info.session_id, reason):
                terminated_count += 1
        
        return terminated_count
    
    async def get_user_sessions(self, user_id: str) -> List[SessionInfo]:
        """获取用户的所有活跃会话"""
        user_sessions_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        session_ids = await self.redis.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            session_info = await self.get_session(session_id.decode())
            if session_info and session_info.state == SessionState.ACTIVE:
                sessions.append(session_info)
        
        # 按登录时间排序（最新的在前）
        sessions.sort(key=lambda x: x.login_time, reverse=True)
        return sessions
    
    async def validate_session_security(self, session_id: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
        """
        验证会话安全性
        
        Args:
            session_id: 会话ID
            ip_address: 当前IP地址
            user_agent: 当前用户代理
            
        Returns:
            Dict: 验证结果
        """
        session_info = await self.get_session(session_id)
        if not session_info:
            return {
                "valid": False,
                "reason": "会话不存在"
            }
        
        security_issues = []
        
        # IP地址变化检测
        if session_info.ip_address != ip_address:
            if self.session_policy.enable_device_binding:
                security_issues.append("IP地址发生变化")
            else:
                # 记录IP变化但不阻止
                await self._record_ip_change(session_id, session_info.ip_address, ip_address)
        
        # 用户代理变化检测
        if session_info.user_agent != user_agent:
            # 计算用户代理相似度
            similarity = self._calculate_user_agent_similarity(session_info.user_agent, user_agent)
            if similarity < 0.8:  # 相似度阈值
                security_issues.append("设备信息发生显著变化")
        
        # 检查是否为可疑会话
        if session_info.is_suspicious:
            security_issues.append("会话被标记为可疑")
        
        # 会话劫持检测
        if await self._detect_session_hijacking(session_id, ip_address):
            security_issues.append("检测到可能的会话劫持")
            # 自动标记会话为可疑
            session_info.is_suspicious = True
            session_info.state = SessionState.SUSPICIOUS
            await self._store_session(session_info)
        
        return {
            "valid": len(security_issues) == 0,
            "security_issues": security_issues,
            "session_info": session_info
        }
    
    async def cleanup_expired_sessions(self) -> Dict[str, int]:
        """清理过期会话"""
        current_time = datetime.now(timezone.utc)
        
        # 扫描所有会话（实际实现中应该使用更高效的方式）
        pattern = f"{self.SESSION_PREFIX}*"
        session_keys = await self.redis.keys(pattern)
        
        expired_count = 0
        idle_timeout_count = 0
        
        for session_key in session_keys:
            session_data = await self.redis.get(session_key)
            if not session_data:
                continue
            
            try:
                data = json.loads(session_data.decode())
                session_info = self._deserialize_session(data)
                
                # 检查会话过期
                if current_time > session_info.expires_at:
                    await self.terminate_session(session_info.session_id, "会话过期")
                    expired_count += 1
                    continue
                
                # 检查空闲超时
                idle_duration = current_time - session_info.last_activity
                if idle_duration.total_seconds() > self.session_policy.idle_timeout_minutes * 60:
                    await self.terminate_session(session_info.session_id, "空闲超时")
                    idle_timeout_count += 1
                
            except Exception as e:
                print(f"清理会话时发生错误: {str(e)}")
                continue
        
        return {
            "expired_sessions": expired_count,
            "idle_timeout_sessions": idle_timeout_count,
            "total_cleaned": expired_count + idle_timeout_count
        }
    
    async def get_session_statistics(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        # 活跃会话总数
        pattern = f"{self.SESSION_PREFIX}*"
        session_keys = await self.redis.keys(pattern)
        
        active_sessions = 0
        suspicious_sessions = 0
        device_types = {"web": 0, "mobile": 0, "desktop": 0, "api": 0, "unknown": 0}
        
        for session_key in session_keys:
            session_data = await self.redis.get(session_key)
            if not session_data:
                continue
            
            try:
                data = json.loads(session_data.decode())
                session_info = self._deserialize_session(data)
                
                if session_info.state == SessionState.ACTIVE:
                    active_sessions += 1
                    device_types[session_info.device_info.device_type] = device_types.get(
                        session_info.device_info.device_type, 0
                    ) + 1
                
                if session_info.is_suspicious:
                    suspicious_sessions += 1
                    
            except Exception:
                continue
        
        # 活跃用户数量
        active_users_key = f"{self.ACTIVE_USERS_PREFIX}*"
        active_users_keys = await self.redis.keys(active_users_key)
        active_users_count = len(active_users_keys)
        
        return {
            "active_sessions": active_sessions,
            "suspicious_sessions": suspicious_sessions,
            "active_users": active_users_count,
            "device_distribution": device_types,
            "avg_sessions_per_user": round(active_sessions / max(active_users_count, 1), 2)
        }
    
    # 私有方法实现
    
    def _generate_session_id(self, user_id: str, ip_address: str, timestamp: datetime) -> str:
        """生成会话ID"""
        data = f"{user_id}:{ip_address}:{timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _parse_device_info(self, user_agent: str, device_data: Dict[str, Any]) -> DeviceInfo:
        """解析设备信息"""
        # 简化的用户代理解析
        device_type = DeviceType.UNKNOWN.value
        os = None
        browser = None
        
        user_agent_lower = user_agent.lower()
        
        # 检测移动设备
        if any(mobile in user_agent_lower for mobile in ['mobile', 'android', 'iphone', 'ipad']):
            device_type = DeviceType.MOBILE.value
        elif any(desktop in user_agent_lower for desktop in ['windows', 'macintosh', 'linux']):
            device_type = DeviceType.WEB.value
        
        # 检测操作系统
        if 'windows' in user_agent_lower:
            os = 'Windows'
        elif 'macintosh' in user_agent_lower or 'mac os' in user_agent_lower:
            os = 'macOS'
        elif 'linux' in user_agent_lower:
            os = 'Linux'
        elif 'android' in user_agent_lower:
            os = 'Android'
        elif 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            os = 'iOS'
        
        # 检测浏览器
        if 'chrome' in user_agent_lower:
            browser = 'Chrome'
        elif 'firefox' in user_agent_lower:
            browser = 'Firefox'
        elif 'safari' in user_agent_lower:
            browser = 'Safari'
        elif 'edge' in user_agent_lower:
            browser = 'Edge'
        
        return DeviceInfo(
            device_type=device_type,
            os=os,
            browser=browser,
            screen_resolution=device_data.get('screen_resolution'),
            timezone=device_data.get('timezone'),
            language=device_data.get('language')
        )
    
    async def _store_session(self, session_info: SessionInfo):
        """存储会话信息到Redis"""
        session_key = f"{self.SESSION_PREFIX}{session_info.session_id}"
        session_data = self._serialize_session(session_info)
        
        # 计算TTL（过期时间 + 缓冲时间）
        ttl_seconds = int((session_info.expires_at - datetime.now(timezone.utc)).total_seconds()) + 3600
        
        await self.redis.setex(session_key, ttl_seconds, json.dumps(session_data))
    
    def _serialize_session(self, session_info: SessionInfo) -> Dict[str, Any]:
        """序列化会话信息"""
        data = asdict(session_info)
        # 转换datetime对象为ISO字符串
        data['login_time'] = session_info.login_time.isoformat()
        data['last_activity'] = session_info.last_activity.isoformat()
        data['expires_at'] = session_info.expires_at.isoformat()
        return data
    
    def _deserialize_session(self, data: Dict[str, Any]) -> SessionInfo:
        """反序列化会话信息"""
        # 转换ISO字符串为datetime对象
        data['login_time'] = datetime.fromisoformat(data['login_time'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        
        # 重建DeviceInfo对象
        device_data = data.pop('device_info')
        device_info = DeviceInfo(**device_data)
        data['device_info'] = device_info
        
        return SessionInfo(**data)
    
    async def _enforce_concurrent_session_limit(self, user_id: str):
        """强制并发会话限制"""
        user_sessions = await self.get_user_sessions(user_id)
        
        if len(user_sessions) >= self.session_policy.max_concurrent_sessions:
            # 终止最老的会话
            oldest_session = min(user_sessions, key=lambda x: x.login_time)
            await self.terminate_session(oldest_session.session_id, "达到最大并发会话限制")
    
    async def _add_user_session(self, user_id: str, session_id: str):
        """将会话添加到用户会话列表"""
        user_sessions_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        await self.redis.sadd(user_sessions_key, session_id)
        # 设置过期时间（会话超时时间）
        await self.redis.expire(user_sessions_key, self.session_policy.session_timeout_minutes * 60)
    
    async def _remove_user_session(self, user_id: str, session_id: str):
        """从用户会话列表中移除会话"""
        user_sessions_key = f"{self.USER_SESSIONS_PREFIX}{user_id}"
        await self.redis.srem(user_sessions_key, session_id)
    
    async def _update_active_users(self, user_id: str, session_id: str):
        """更新活跃用户列表"""
        active_users_key = f"{self.ACTIVE_USERS_PREFIX}{user_id}"
        user_data = {
            "last_session_id": session_id,
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        await self.redis.setex(active_users_key, 24 * 3600, json.dumps(user_data))  # 24小时过期
    
    async def _is_suspicious_login(self, user_id: str, ip_address: str) -> bool:
        """检测是否为可疑登录"""
        if not self.session_policy.suspicious_login_detection:
            return False
        
        # 检查IP是否在可疑列表中
        suspicious_ips_key = f"{self.SUSPICIOUS_IPS_PREFIX}{ip_address}"
        if await self.redis.exists(suspicious_ips_key):
            return True
        
        # 检查用户历史登录IP（简化实现）
        # 实际应该查询数据库获取用户历史登录IP
        return False
    
    def _calculate_user_agent_similarity(self, ua1: str, ua2: str) -> float:
        """计算用户代理相似度"""
        # 简化的相似度计算
        if ua1 == ua2:
            return 1.0
        
        # 提取关键信息进行比较
        ua1_parts = set(ua1.lower().split())
        ua2_parts = set(ua2.lower().split())
        
        if not ua1_parts or not ua2_parts:
            return 0.0
        
        intersection = ua1_parts.intersection(ua2_parts)
        union = ua1_parts.union(ua2_parts)
        
        return len(intersection) / len(union)
    
    async def _detect_session_hijacking(self, session_id: str, current_ip: str) -> bool:
        """检测会话劫持"""
        # 简化的会话劫持检测
        # 实际实现应该更复杂，包括地理位置、时间窗口等因素
        
        session_info = await self.get_session(session_id)
        if not session_info:
            return False
        
        # 检查IP地址突然变化
        if session_info.ip_address != current_ip:
            # 检查IP变化频率
            ip_changes_key = f"auth:ip_changes:{session_id}"
            change_count = await self.redis.incr(ip_changes_key)
            await self.redis.expire(ip_changes_key, 3600)  # 1小时窗口
            
            # 如果1小时内IP变化超过3次，认为可疑
            if change_count > 3:
                return True
        
        return False
    
    async def _update_heartbeat(self, session_id: str):
        """更新会话心跳"""
        heartbeat_key = f"{self.SESSION_HEARTBEAT_PREFIX}{session_id}"
        await self.redis.setex(
            heartbeat_key,
            self.session_policy.heartbeat_interval_minutes * 60 * 2,  # 2倍心跳间隔
            datetime.now(timezone.utc).isoformat()
        )
    
    async def _clear_heartbeat(self, session_id: str):
        """清除会话心跳"""
        heartbeat_key = f"{self.SESSION_HEARTBEAT_PREFIX}{session_id}"
        await self.redis.delete(heartbeat_key)
    
    async def _record_user_activity(self, user_id: str, activity_data: Dict[str, Any]):
        """记录用户活动数据"""
        # 用于用户行为分析，这里简化实现
        activity_key = f"auth:activity:{user_id}"
        activity_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "activity": activity_data
        }
        
        # 使用列表存储最近的活动记录
        await self.redis.lpush(activity_key, json.dumps(activity_record))
        await self.redis.ltrim(activity_key, 0, 99)  # 只保留最近100条记录
        await self.redis.expire(activity_key, 7 * 24 * 3600)  # 7天过期