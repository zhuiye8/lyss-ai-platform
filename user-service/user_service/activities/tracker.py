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
        """获取基础活动统计"""
        try:
            # 基础统计查询条件
            conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_date
            ]
            
            # 总活动数
            total_query = select(func.count(UserActivity.id)).where(and_(*conditions))
            total_result = await db.execute(total_query)
            total_activities = total_result.scalar() or 0
            
            # 活跃天数
            active_days_query = select(
                func.count(func.distinct(func.date(UserActivity.created_at)))
            ).where(and_(*conditions))
            active_days_result = await db.execute(active_days_query)
            active_days = active_days_result.scalar() or 0
            
            # 最后活动时间
            last_activity_query = select(
                func.max(UserActivity.created_at)
            ).where(and_(*conditions))
            last_activity_result = await db.execute(last_activity_query)
            last_activity = last_activity_result.scalar()
            
            # 计算平均每日活动
            avg_activities_per_day = (
                total_activities / max(active_days, 1) if active_days > 0 else 0
            )
            
            return {
                "total_activities": total_activities,
                "active_days": active_days,
                "avg_activities_per_day": round(avg_activities_per_day, 2),
                "last_activity": last_activity.isoformat() if last_activity else None
            }
            
        except Exception as e:
            logger.error(f"获取基础活动统计失败 [{user_id}]: {e}")
            return {
                "total_activities": 0,
                "active_days": 0,
                "avg_activities_per_day": 0.0,
                "last_activity": None
            }
    
    async def _get_daily_activity_distribution(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, int]:
        """获取每日活动分布"""
        try:
            conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_date
            ]
            
            # 按日期分组统计活动数
            daily_query = select(
                func.date(UserActivity.created_at).label('activity_date'),
                func.count(UserActivity.id).label('activity_count')
            ).where(and_(*conditions)).group_by(func.date(UserActivity.created_at))
            
            result = await db.execute(daily_query)
            daily_data = result.fetchall()
            
            # 转换为字典格式
            daily_distribution = {}
            for row in daily_data:
                date_str = row.activity_date.strftime('%Y-%m-%d')
                daily_distribution[date_str] = row.activity_count
            
            return daily_distribution
            
        except Exception as e:
            logger.error(f"获取每日活动分布失败 [{user_id}]: {e}")
            return {}
    
    async def _get_activity_type_stats(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, int]:
        """获取活动类型统计"""
        try:
            conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_date
            ]
            
            # 按活动类型分组统计
            type_query = select(
                UserActivity.activity_type,
                func.count(UserActivity.id).label('type_count')
            ).where(and_(*conditions)).group_by(UserActivity.activity_type)
            
            result = await db.execute(type_query)
            type_data = result.fetchall()
            
            # 转换为字典格式
            activity_types = {}
            for row in type_data:
                activity_types[row.activity_type] = row.type_count
            
            return activity_types
            
        except Exception as e:
            logger.error(f"获取活动类型统计失败 [{user_id}]: {e}")
            return {}
    
    async def _get_hourly_activity_pattern(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[int, int]:
        """获取小时活动模式"""
        try:
            conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_date
            ]
            
            # 按小时分组统计活动
            hourly_query = select(
                func.extract('hour', UserActivity.created_at).label('activity_hour'),
                func.count(UserActivity.id).label('hour_count')
            ).where(and_(*conditions)).group_by(func.extract('hour', UserActivity.created_at))
            
            result = await db.execute(hourly_query)
            hourly_data = result.fetchall()
            
            # 转换为字典格式，确保小时为整数
            hourly_pattern = {}
            for row in hourly_data:
                hour = int(row.activity_hour)
                hourly_pattern[hour] = row.hour_count
            
            return hourly_pattern
            
        except Exception as e:
            logger.error(f"获取小时活动模式失败 [{user_id}]: {e}")
            return {}
    
    async def _get_recent_activities(
        self,
        user_id: str,
        limit: int,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """获取最近活动"""
        try:
            # 查询最近的活动记录
            recent_query = select(UserActivity).where(
                UserActivity.user_id == user_id
            ).order_by(desc(UserActivity.created_at)).limit(limit)
            
            result = await db.execute(recent_query)
            activities = result.scalars().all()
            
            # 转换为字典格式
            recent_activities = []
            for activity in activities:
                activity_data = {
                    "activity_type": activity.activity_type,
                    "created_at": activity.created_at.isoformat(),
                    "metadata": activity.metadata or {}
                }
                
                # 添加简化的描述
                if activity.activity_type == "chat_message":
                    model = activity.metadata.get('model', '未知模型') if activity.metadata else '未知模型'
                    activity_data["description"] = f"使用{model}进行对话"
                elif activity.activity_type == "login":
                    activity_data["description"] = "用户登录"
                elif activity.activity_type == "model_usage":
                    model = activity.metadata.get('model', '未知模型') if activity.metadata else '未知模型'
                    activity_data["description"] = f"调用{model}模型"
                elif activity.activity_type == "feature_usage":
                    feature = activity.metadata.get('feature', '未知功能') if activity.metadata else '未知功能'
                    activity_data["description"] = f"使用{feature}功能"
                else:
                    activity_data["description"] = f"{activity.activity_type}活动"
                
                recent_activities.append(activity_data)
            
            return recent_activities
            
        except Exception as e:
            logger.error(f"获取最近活动失败 [{user_id}]: {e}")
            return []
    
    async def _get_anomaly_summary(
        self,
        user_id: str,
        start_date: datetime,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """获取异常摘要"""
        try:
            # 查询包含异常标记的活动
            anomaly_conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_date,
                UserActivity.metadata.op('?')('anomaly')  # JSON包含anomaly字段
            ]
            
            anomaly_query = select(UserActivity).where(and_(*anomaly_conditions))
            result = await db.execute(anomaly_query)
            anomaly_activities = result.scalars().all()
            
            if not anomaly_activities:
                return {
                    "total_anomalies": 0,
                    "anomaly_types": [],
                    "severity_distribution": {"low": 0, "medium": 0, "high": 0}
                }
            
            # 分析异常类型和严重程度
            anomaly_types = []
            severity_counts = {"low": 0, "medium": 0, "high": 0}
            
            for activity in anomaly_activities:
                metadata = activity.metadata or {}
                anomaly_info = metadata.get('anomaly', {})
                
                if anomaly_info:
                    anomaly_type = anomaly_info.get('type', 'unknown')
                    severity = anomaly_info.get('severity', 'low')
                    
                    if anomaly_type not in anomaly_types:
                        anomaly_types.append(anomaly_type)
                    
                    if severity in severity_counts:
                        severity_counts[severity] += 1
            
            return {
                "total_anomalies": len(anomaly_activities),
                "anomaly_types": anomaly_types,
                "severity_distribution": severity_counts
            }
            
        except Exception as e:
            logger.error(f"获取异常摘要失败 [{user_id}]: {e}")
            return {
                "total_anomalies": 0,
                "anomaly_types": [],
                "severity_distribution": {"low": 0, "medium": 0, "high": 0}
            }
    
    async def _detect_login_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """检测登录异常"""
        try:
            # 查询登录活动
            login_conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_time,
                UserActivity.activity_type == 'login'
            ]
            
            login_query = select(UserActivity).where(and_(*login_conditions))
            result = await db.execute(login_query)
            login_activities = result.scalars().all()
            
            anomalies = []
            
            if len(login_activities) < 2:
                return anomalies
            
            # 分析IP地址变化
            ip_addresses = set()
            locations = set()
            
            for activity in login_activities:
                if activity.ip_address:
                    ip_addresses.add(activity.ip_address)
                
                metadata = activity.metadata or {}
                location = metadata.get('location', {})
                if location.get('country'):
                    locations.add(location['country'])
            
            # 检测异常IP或地理位置
            if len(ip_addresses) > 3:
                anomalies.append({
                    "type": "multiple_ip_addresses",
                    "severity": "medium",
                    "description": f"检测到{len(ip_addresses)}个不同IP地址登录",
                    "details": {"ip_count": len(ip_addresses)}
                })
            
            if len(locations) > 2:
                anomalies.append({
                    "type": "unusual_login_location",
                    "severity": "high",
                    "description": f"检测到来自{len(locations)}个不同国家的登录",
                    "details": {"countries": list(locations)}
                })
            
            # 检测登录频率异常
            if len(login_activities) > 20:  # 时间窗口内登录次数过多
                anomalies.append({
                    "type": "excessive_login_frequency",
                    "severity": "medium",
                    "description": f"登录频率异常（{len(login_activities)}次）",
                    "details": {"login_count": len(login_activities)}
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测登录异常失败 [{user_id}]: {e}")
            return []
    
    async def _detect_usage_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """检测使用异常"""
        try:
            # 查询所有活动
            activity_conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_time
            ]
            
            activity_query = select(UserActivity).where(and_(*activity_conditions))
            result = await db.execute(activity_query)
            activities = result.scalars().all()
            
            anomalies = []
            
            if not activities:
                return anomalies
            
            # 按小时分组分析活动密度
            hourly_counts = {}
            for activity in activities:
                hour = activity.created_at.hour
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
            
            # 检测异常活跃时段
            avg_hourly = sum(hourly_counts.values()) / max(len(hourly_counts), 1)
            for hour, count in hourly_counts.items():
                if count > avg_hourly * 3:  # 超过平均值3倍
                    anomalies.append({
                        "type": "unusual_activity_burst",
                        "severity": "medium",
                        "description": f"{hour}点活动异常密集（{count}次）",
                        "details": {"hour": hour, "count": count, "average": round(avg_hourly, 1)}
                    })
            
            # 检测模型使用异常
            model_activities = [a for a in activities if a.activity_type == 'model_usage']
            if len(model_activities) > 100:  # 模型调用过多
                anomalies.append({
                    "type": "excessive_model_usage",
                    "severity": "high",
                    "description": f"模型使用频率异常（{len(model_activities)}次）",
                    "details": {"model_calls": len(model_activities)}
                })
            
            # 检测总活动量异常
            total_activities = len(activities)
            time_span_hours = (datetime.utcnow() - start_time).total_seconds() / 3600
            activity_rate = total_activities / max(time_span_hours, 1)
            
            if activity_rate > 10:  # 每小时超过10次活动
                anomalies.append({
                    "type": "high_activity_rate",
                    "severity": "medium",
                    "description": f"活动频率过高（每小时{activity_rate:.1f}次）",
                    "details": {"rate_per_hour": round(activity_rate, 1)}
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测使用异常失败 [{user_id}]: {e}")
            return []
    
    async def _detect_location_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """检测地理位置异常"""
        try:
            # 查询有IP地址的活动
            location_conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_time,
                UserActivity.ip_address.isnot(None)
            ]
            
            location_query = select(UserActivity).where(and_(*location_conditions))
            result = await db.execute(location_query)
            activities_with_location = result.scalars().all()
            
            anomalies = []
            
            if len(activities_with_location) < 2:
                return anomalies
            
            # 分析地理位置变化
            locations = []
            for activity in activities_with_location:
                metadata = activity.metadata or {}
                location = metadata.get('location', {})
                if location.get('country'):
                    locations.append({
                        'country': location.get('country'),
                        'city': location.get('city'),
                        'timestamp': activity.created_at
                    })
            
            if len(locations) < 2:
                return anomalies
            
            # 检测快速地理位置变化
            locations.sort(key=lambda x: x['timestamp'])
            for i in range(1, len(locations)):
                current = locations[i]
                previous = locations[i-1]
                
                # 如果国家不同且时间间隔很短
                if (current['country'] != previous['country'] and 
                    (current['timestamp'] - previous['timestamp']).total_seconds() < 3600):  # 1小时内
                    
                    anomalies.append({
                        "type": "impossible_travel",
                        "severity": "high",
                        "description": f"短时间内从{previous['country']}切换到{current['country']}",
                        "details": {
                            "from_country": previous['country'],
                            "to_country": current['country'],
                            "time_diff_minutes": int((current['timestamp'] - previous['timestamp']).total_seconds() / 60)
                        }
                    })
            
            # 检测来自多个国家的访问
            unique_countries = set(loc['country'] for loc in locations)
            if len(unique_countries) > 2:
                anomalies.append({
                    "type": "multiple_countries",
                    "severity": "medium",
                    "description": f"来自{len(unique_countries)}个不同国家的访问",
                    "details": {"countries": list(unique_countries)}
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测地理位置异常失败 [{user_id}]: {e}")
            return []
    
    async def _detect_time_anomalies(
        self,
        user_id: str,
        start_time: datetime,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """检测时间异常"""
        try:
            # 查询活动记录
            time_conditions = [
                UserActivity.user_id == user_id,
                UserActivity.created_at >= start_time
            ]
            
            time_query = select(UserActivity).where(and_(*time_conditions))
            result = await db.execute(time_query)
            activities = result.scalars().all()
            
            anomalies = []
            
            if not activities:
                return anomalies
            
            # 分析活动时间模式
            hourly_pattern = {}
            for activity in activities:
                hour = activity.created_at.hour
                hourly_pattern[hour] = hourly_pattern.get(hour, 0) + 1
            
            # 检测深夜异常活动（凌晨2-5点）
            night_hours = [2, 3, 4, 5]
            night_activities = sum(hourly_pattern.get(hour, 0) for hour in night_hours)
            total_activities = len(activities)
            
            if night_activities > 0 and total_activities > 10:
                night_ratio = night_activities / total_activities
                if night_ratio > 0.3:  # 超过30%的活动在深夜
                    anomalies.append({
                        "type": "unusual_night_activity",
                        "severity": "medium",
                        "description": f"深夜活动异常（{night_activities}次，占比{night_ratio:.1%}）",
                        "details": {
                            "night_activities": night_activities,
                            "night_ratio": round(night_ratio, 3)
                        }
                    })
            
            # 检测连续长时间活动
            activities.sort(key=lambda x: x.created_at)
            continuous_sessions = []
            session_start = None
            
            for i, activity in enumerate(activities):
                if i == 0:
                    session_start = activity.created_at
                    continue
                
                # 如果与前一个活动间隔超过30分钟，认为是新会话
                time_gap = (activity.created_at - activities[i-1].created_at).total_seconds()
                if time_gap > 1800:  # 30分钟
                    if session_start:
                        session_duration = (activities[i-1].created_at - session_start).total_seconds()
                        if session_duration > 14400:  # 4小时以上
                            continuous_sessions.append(session_duration / 3600)  # 转换为小时
                    session_start = activity.created_at
            
            # 检查最后一个会话
            if session_start and activities:
                session_duration = (activities[-1].created_at - session_start).total_seconds()
                if session_duration > 14400:
                    continuous_sessions.append(session_duration / 3600)
            
            if continuous_sessions:
                max_session = max(continuous_sessions)
                anomalies.append({
                    "type": "excessive_session_duration",
                    "severity": "medium",
                    "description": f"连续使用时间过长（最长{max_session:.1f}小时）",
                    "details": {
                        "max_session_hours": round(max_session, 1),
                        "long_sessions_count": len(continuous_sessions)
                    }
                })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"检测时间异常失败 [{user_id}]: {e}")
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