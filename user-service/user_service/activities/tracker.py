# -*- coding: utf-8 -*-
"""
用户活动追踪器模块

负责用户活动的实时追踪、批量存储和异常检测。
基于OpenWebUI性能优化实践，支持高并发活动记录和智能缓存策略。

核心功能：
- 实时活动追踪和批量写入
- 异常行为检测和告警
- 用户活动统计和分析
- 性能优化的缓存策略
- 多租户活动隔离
"""

import logging
import json
import time
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from contextlib import asynccontextmanager
from collections import defaultdict, deque

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from ..core.database_engine import get_db_session
from ..core.redis_client import redis_client
from ..models.database.activity import UserActivity, ActivityType
from ..utils.security import get_client_ip, detect_suspicious_ip
from ..utils.geo_location import get_location_info
from .detector import ActivityAnomalyDetector

logger = logging.getLogger(__name__)

class UserActivityTracker:
    """
    用户活动追踪器
    
    高性能的活动追踪系统，支持：
    - 批量异步写入优化
    - Redis缓存和实时状态更新
    - 异常行为检测
    - 地理位置分析
    - 多租户数据隔离
    """
    
    def __init__(self):
        # 批量写入配置
        self.batch_size = 100
        self.flush_interval = 30  # 秒
        self.max_buffer_time = 300  # 最大缓冲时间5分钟
        
        # 活动缓冲区
        self.activity_buffer = deque()
        self.buffer_lock = asyncio.Lock()
        self.last_flush_time = time.time()
        
        # 异常检测器
        self.anomaly_detector = ActivityAnomalyDetector()
        
        # 缓存配置
        self.cache_ttl = {
            "daily_stats": 3600,     # 1小时
            "user_status": 1800,     # 30分钟
            "session_info": 3600,    # 1小时
        }
        
        # 监控统计
        self.stats = {
            "activities_tracked": 0,
            "activities_written": 0,
            "anomalies_detected": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # 启动后台任务
        self._background_task = None
        
    async def start_background_tasks(self):
        """启动后台任务"""
        if self._background_task is None:
            self._background_task = asyncio.create_task(self._periodic_flush())
            logger.info("用户活动追踪后台任务已启动")
    
    async def stop_background_tasks(self):
        """停止后台任务"""
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
            
        # 刷新剩余活动
        await self._flush_activities()
        logger.info("用户活动追踪后台任务已停止")
    
    async def track_activity(
        self,
        user_id: str,
        activity_type: str,
        metadata: Dict[str, Any] = None,
        tenant_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        记录用户活动
        
        Args:
            user_id: 用户ID
            activity_type: 活动类型
            metadata: 活动元数据
            tenant_id: 租户ID
            ip_address: IP地址
            user_agent: 用户代理
            session_id: 会话ID
            
        Returns:
            Dict[str, Any]: 追踪结果
        """
        try:
            current_time = datetime.utcnow()
            
            # 构建活动数据
            activity_data = {
                "id": self._generate_activity_id(user_id, activity_type, current_time),
                "user_id": user_id,
                "tenant_id": tenant_id,
                "activity_type": activity_type,
                "metadata": metadata or {},
                "ip_address": ip_address,
                "user_agent": user_agent,
                "session_id": session_id,
                "created_at": current_time,
                "timestamp": time.time()
            }
            
            # 添加地理位置信息（如果有IP）
            if ip_address:
                location_info = await self._get_location_info(ip_address)
                if location_info:
                    activity_data["metadata"]["location"] = location_info
            
            # 异常检测
            anomaly_result = await self.anomaly_detector.check_activity(
                user_id, activity_type, activity_data
            )
            if anomaly_result["is_anomaly"]:
                activity_data["metadata"]["anomaly"] = anomaly_result
                self.stats["anomalies_detected"] += 1
                
                # 记录异常日志
                logger.warning(
                    f"检测到异常活动 [用户: {user_id}, 类型: {activity_type}]: "
                    f"{anomaly_result['reason']}"
                )
            
            # 添加到缓冲区
            async with self.buffer_lock:
                self.activity_buffer.append(activity_data)
                self.stats["activities_tracked"] += 1
                
                # 检查是否需要立即刷新
                if (len(self.activity_buffer) >= self.batch_size or
                    time.time() - self.last_flush_time > self.max_buffer_time):
                    await self._flush_activities()
            
            # 更新实时缓存
            await self._update_activity_cache(user_id, activity_type, activity_data)
            
            return {
                "success": True,
                "activity_id": activity_data["id"],
                "tracked_at": current_time.isoformat(),
                "anomaly_detected": anomaly_result["is_anomaly"]
            }
            
        except Exception as e:
            logger.error(f"活动追踪失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def track_login(
        self,
        user_id: str,
        tenant_id: str,
        login_method: str = "local",
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """追踪登录活动"""
        metadata = {
            "method": login_method,
            "success": success,
            "login_time": datetime.utcnow().isoformat()
        }
        
        if not success and failure_reason:
            metadata["failure_reason"] = failure_reason
        
        return await self.track_activity(
            user_id=user_id,
            activity_type="login",
            metadata=metadata,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
    
    async def track_chat_message(
        self,
        user_id: str,
        tenant_id: str,
        conversation_id: str,
        model: str,
        message_length: int,
        tokens_used: int = 0,
        response_time: float = 0.0,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """追踪聊天消息"""
        metadata = {
            "conversation_id": conversation_id,
            "model": model,
            "message_length": message_length,
            "tokens_used": tokens_used,
            "response_time": response_time
        }
        
        return await self.track_activity(
            user_id=user_id,
            activity_type="chat_message",
            metadata=metadata,
            tenant_id=tenant_id,
            session_id=session_id
        )
    
    async def track_model_usage(
        self,
        user_id: str,
        tenant_id: str,
        model: str,
        provider: str,
        tokens_used: int,
        cost: float = 0.0,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """追踪模型使用"""
        metadata = {
            "model": model,
            "provider": provider,
            "tokens_used": tokens_used,
            "cost": cost
        }
        
        return await self.track_activity(
            user_id=user_id,
            activity_type="model_usage",
            metadata=metadata,
            tenant_id=tenant_id,
            session_id=session_id
        )
    
    async def track_feature_usage(
        self,
        user_id: str,
        tenant_id: str,
        feature: str,
        action: str,
        additional_data: Dict[str, Any] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """追踪功能使用"""
        metadata = {
            "feature": feature,
            "action": action,
            **(additional_data or {})
        }
        
        return await self.track_activity(
            user_id=user_id,
            activity_type="feature_usage",
            metadata=metadata,
            tenant_id=tenant_id,
            session_id=session_id
        )
    
    async def get_user_activity_summary(
        self,
        user_id: str,
        days: int = 30,
        include_details: bool = False,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        获取用户活动摘要
        
        Args:
            user_id: 用户ID
            days: 统计天数
            include_details: 是否包含详细信息
            db: 数据库会话
            
        Returns:
            Dict[str, Any]: 活动摘要
        """
        if db is None:
            async with get_db_session() as session:
                return await self._get_summary_impl(
                    user_id, days, include_details, session
                )
        else:
            return await self._get_summary_impl(
                user_id, days, include_details, db
            )
    
    async def _get_summary_impl(
        self,
        user_id: str,
        days: int,
        include_details: bool,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """活动摘要实现"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 尝试从缓存获取
            cache_key = f"activity_summary:{user_id}:{days}"
            cached_result = await redis_client.get(cache_key)
            
            if cached_result and not include_details:
                self.stats["cache_hits"] += 1
                return json.loads(cached_result)
            
            self.stats["cache_misses"] += 1
            
            # 基础统计查询
            basic_stats = await self._get_basic_activity_stats(user_id, start_date, db)
            
            # 每日活动分布
            daily_distribution = await self._get_daily_activity_distribution(
                user_id, start_date, db
            )
            
            # 活动类型统计
            activity_types = await self._get_activity_type_stats(user_id, start_date, db)
            
            # 时段分析
            hourly_pattern = await self._get_hourly_activity_pattern(
                user_id, start_date, db
            )
            
            result = {
                "user_id": user_id,
                "period_days": days,
                "summary_generated_at": datetime.utcnow().isoformat(),
                "basic_stats": basic_stats,
                "daily_distribution": daily_distribution,
                "activity_types": activity_types,
                "hourly_pattern": hourly_pattern
            }
            
            # 包含详细信息
            if include_details:
                recent_activities = await self._get_recent_activities(user_id, 20, db)
                anomaly_summary = await self._get_anomaly_summary(user_id, start_date, db)
                
                result.update({
                    "recent_activities": recent_activities,
                    "anomaly_summary": anomaly_summary
                })
            
            # 缓存结果（不包含详细信息时）
            if not include_details:
                await redis_client.setex(
                    cache_key,
                    self.cache_ttl["daily_stats"],
                    json.dumps(result, default=str)
                )
            
            return result
            
        except Exception as e:
            logger.error(f"获取用户活动摘要失败 [{user_id}]: {e}")
            return {
                "user_id": user_id,
                "error": str(e),
                "summary_generated_at": datetime.utcnow().isoformat()
            }
    
    async def detect_unusual_activity(
        self,
        user_id: str,
        hours: int = 24,
        db: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        检测异常活动
        
        Args:
            user_id: 用户ID
            hours: 检测时间范围（小时）
            db: 数据库会话
            
        Returns:
            List[Dict[str, Any]]: 异常活动列表
        """
        if db is None:
            async with get_db_session() as session:
                return await self._detect_unusual_impl(user_id, hours, session)
        else:
            return await self._detect_unusual_impl(user_id, hours, db)
    
    async def _detect_unusual_impl(
        self,
        user_id: str,
        hours: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """异常检测实现"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            anomalies = []
            
            # 检测登录异常
            login_anomalies = await self._detect_login_anomalies(user_id, start_time, db)
            anomalies.extend(login_anomalies)
            
            # 检测使用模式异常
            usage_anomalies = await self._detect_usage_anomalies(user_id, start_time, db)
            anomalies.extend(usage_anomalies)
            
            # 检测地理位置异常
            location_anomalies = await self._detect_location_anomalies(user_id, start_time, db)
            anomalies.extend(location_anomalies)
            
            # 检测时间模式异常
            time_anomalies = await self._detect_time_anomalies(user_id, start_time, db)
            anomalies.extend(time_anomalies)
            
            return sorted(anomalies, key=lambda x: x.get("severity", 0), reverse=True)
            
        except Exception as e:
            logger.error(f"异常活动检测失败 [{user_id}]: {e}")
            return []
    
    async def get_activity_statistics(
        self,
        tenant_id: Optional[str] = None,
        days: int = 7,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """获取活动统计（管理员功能）"""
        if db is None:
            async with get_db_session() as session:
                return await self._get_statistics_impl(tenant_id, days, session)
        else:
            return await self._get_statistics_impl(tenant_id, days, db)
    
    async def _get_statistics_impl(
        self,
        tenant_id: Optional[str],
        days: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """统计实现"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # 基础统计
            conditions = [UserActivity.created_at >= start_date]
            if tenant_id:
                conditions.append(UserActivity.tenant_id == tenant_id)
            
            # 总活动数
            total_query = select(func.count(UserActivity.id)).where(and_(*conditions))
            total_result = await db.execute(total_query)
            total_activities = total_result.scalar()
            
            # 活跃用户数
            active_users_query = select(func.count(func.distinct(UserActivity.user_id))).where(
                and_(*conditions)
            )
            active_users_result = await db.execute(active_users_query)
            active_users = active_users_result.scalar()
            
            # 活动类型分布
            type_query = select(
                UserActivity.activity_type,
                func.count(UserActivity.id).label('count')
            ).where(and_(*conditions)).group_by(UserActivity.activity_type)
            
            type_result = await db.execute(type_query)
            activity_types = {row.activity_type: row.count for row in type_result}
            
            # 每日活动趋势
            daily_query = select(
                func.date(UserActivity.created_at).label('date'),
                func.count(UserActivity.id).label('count')
            ).where(and_(*conditions)).group_by(func.date(UserActivity.created_at))
            
            daily_result = await db.execute(daily_query)
            daily_trends = {str(row.date): row.count for row in daily_result}
            
            return {
                "tenant_id": tenant_id,
                "period_days": days,
                "total_activities": total_activities,
                "active_users": active_users,
                "avg_activities_per_user": total_activities / max(active_users, 1),
                "activity_types": activity_types,
                "daily_trends": daily_trends,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取活动统计失败: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.utcnow().isoformat()
            }
    
    # 私有辅助方法
    async def _periodic_flush(self):
        """定期刷新任务"""
        while True:
            try:
                await asyncio.sleep(self.flush_interval)
                async with self.buffer_lock:
                    if self.activity_buffer:
                        await self._flush_activities()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定期刷新任务异常: {e}")
    
    async def _flush_activities(self):
        """刷新活动缓冲区到数据库"""
        if not self.activity_buffer:
            return
        
        activities_to_write = list(self.activity_buffer)
        self.activity_buffer.clear()
        self.last_flush_time = time.time()
        
        try:
            async with get_db_session() as db:
                for activity_data in activities_to_write:
                    activity = UserActivity(
                        id=activity_data["id"],
                        user_id=activity_data["user_id"],
                        tenant_id=activity_data["tenant_id"],
                        activity_type=activity_data["activity_type"],
                        metadata=activity_data["metadata"],
                        ip_address=activity_data["ip_address"],
                        user_agent=activity_data["user_agent"],
                        session_id=activity_data["session_id"],
                        created_at=activity_data["created_at"]
                    )
                    db.add(activity)
                
                await db.commit()
                self.stats["activities_written"] += len(activities_to_write)
                
                logger.debug(f"成功写入 {len(activities_to_write)} 条活动记录")
                
        except Exception as e:
            logger.error(f"活动记录批量写入失败: {e}")
            # 重新加入缓冲区
            async with self.buffer_lock:
                self.activity_buffer.extendleft(reversed(activities_to_write))
    
    async def _update_activity_cache(
        self,
        user_id: str,
        activity_type: str,
        activity_data: Dict[str, Any]
    ):
        """更新活动缓存"""
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            
            # 更新每日活动计数
            daily_key = f"user_activity:{user_id}:{today}"
            await redis_client.hincrby(daily_key, activity_type, 1)
            await redis_client.expire(daily_key, 86400 * 7)  # 7天过期
            
            # 更新用户状态
            status_key = f"user_status:{user_id}"
            status_data = {
                "last_activity": activity_data["created_at"].isoformat(),
                "last_activity_type": activity_type
            }
            await redis_client.hmset(status_key, status_data)
            await redis_client.expire(status_key, self.cache_ttl["user_status"])
            
            # 更新会话信息
            if activity_data.get("session_id"):
                session_key = f"session:{activity_data['session_id']}"
                session_data = {
                    "last_activity": activity_data["created_at"].isoformat(),
                    "activity_count": await redis_client.hincrby(session_key, "activity_count", 1)
                }
                await redis_client.hmset(session_key, session_data)
                await redis_client.expire(session_key, self.cache_ttl["session_info"])
            
        except Exception as e:
            logger.error(f"活动缓存更新失败: {e}")
    
    def _generate_activity_id(
        self,
        user_id: str,
        activity_type: str,
        timestamp: datetime
    ) -> str:
        """生成活动ID"""
        content = f"{user_id}:{activity_type}:{timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _get_location_info(self, ip_address: str) -> Optional[Dict[str, str]]:
        """获取地理位置信息（占位符方法）"""
        # 这里应该调用地理位置服务
        try:
            return get_location_info(ip_address)
        except Exception as e:
            logger.debug(f"获取地理位置信息失败: {e}")
            return None
    
    async def _get_basic_activity_stats(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """获取基础活动统计（占位符方法）"""
        # 这里应该查询实际数据库
        return {
            "total_activities": 150,
            "active_days": 25,
            "avg_activities_per_day": 6.0,
            "last_activity": datetime.utcnow().isoformat()
        }
    
    async def _get_daily_activity_distribution(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, int]:
        """获取每日活动分布（占位符方法）"""
        return {
            "2025-01-15": 12,
            "2025-01-16": 8,
            "2025-01-17": 15,
            "2025-01-18": 10,
            "2025-01-19": 18,
            "2025-01-20": 14,
            "2025-01-21": 20
        }
    
    async def _get_activity_type_stats(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, int]:
        """获取活动类型统计（占位符方法）"""
        return {
            "chat_message": 45,
            "login": 12,
            "model_usage": 38,
            "feature_usage": 22
        }
    
    async def _get_hourly_activity_pattern(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[int, int]:
        """获取小时活动模式（占位符方法）"""
        return {
            9: 8, 10: 12, 11: 15, 14: 18, 15: 20, 16: 16, 19: 10, 20: 8, 21: 5
        }
    
    async def _get_recent_activities(
        self,
        user_id: str,
        limit: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """获取最近活动（占位符方法）"""
        return [
            {
                "activity_type": "chat_message",
                "created_at": datetime.utcnow().isoformat(),
                "metadata": {"model": "gpt-4", "tokens": 150}
            }
        ]
    
    async def _get_anomaly_summary(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """获取异常摘要（占位符方法）"""
        return {
            "total_anomalies": 2,
            "anomaly_types": ["unusual_login_location", "high_activity_burst"],
            "severity_distribution": {"low": 1, "medium": 1, "high": 0}
        }
    
    async def _detect_login_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """检测登录异常（占位符方法）"""
        return []
    
    async def _detect_usage_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """检测使用异常（占位符方法）"""
        return []
    
    async def _detect_location_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """检测地理位置异常（占位符方法）"""
        return []
    
    async def _detect_time_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """检测时间异常（占位符方法）"""
        return []
    
    def get_tracker_stats(self) -> Dict[str, Any]:
        """获取追踪器统计"""
        return {
            **self.stats,
            "buffer_size": len(self.activity_buffer),
            "last_flush_time": self.last_flush_time,
            "background_task_running": self._background_task is not None and not self._background_task.done()
        }

# 全局活动追踪器实例
activity_tracker = UserActivityTracker()