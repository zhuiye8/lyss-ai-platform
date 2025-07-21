"""
指标数据访问层

负责渠道性能指标的数据库操作，包括指标记录、统计分析、数据聚合等。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func, desc
from datetime import datetime, timedelta
import logging

from .base import BaseRepository
from ..models.database import ChannelMetricsTable
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MetricsRepository(BaseRepository[ChannelMetricsTable, Dict, Dict]):
    """渠道指标Repository"""
    
    def __init__(self, db: Session):
        super().__init__(ChannelMetricsTable, db)
    
    def record_channel_metric(
        self,
        channel_id: str,
        tenant_id: str,
        metric_type: str,
        value: float,
        timestamp: datetime = None,
        metadata: Dict[str, Any] = None
    ) -> ChannelMetricsTable:
        """
        记录渠道指标
        
        Args:
            channel_id: 渠道ID
            tenant_id: 租户ID
            metric_type: 指标类型
            value: 指标值
            timestamp: 时间戳
            metadata: 元数据
            
        Returns:
            ChannelMetricsTable: 创建的指标记录
        """
        try:
            metric_record = ChannelMetricsTable(
                channel_id=channel_id,
                tenant_id=tenant_id,
                metric_type=metric_type,
                value=value,
                timestamp=timestamp or datetime.utcnow(),
                metadata=metadata or {}
            )
            
            self.db.add(metric_record)
            self.db.commit()
            self.db.refresh(metric_record)
            
            logger.info(f"成功记录渠道指标 - channel_id: {channel_id}, type: {metric_type}, value: {value}")
            return metric_record
        except Exception as e:
            self.db.rollback()
            logger.error(f"记录渠道指标失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def get_channel_metrics_by_time_range(
        self,
        channel_id: str,
        metric_type: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[ChannelMetricsTable]:
        """
        获取指定时间范围内的渠道指标
        
        Args:
            channel_id: 渠道ID
            metric_type: 指标类型
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            List[ChannelMetricsTable]: 指标记录列表
        """
        try:
            return self.db.query(self.model).filter(
                and_(
                    self.model.channel_id == channel_id,
                    self.model.metric_type == metric_type,
                    self.model.timestamp >= start_time,
                    self.model.timestamp <= end_time
                )
            ).order_by(self.model.timestamp.asc()).all()
        except Exception as e:
            logger.error(f"获取渠道指标失败 - channel_id: {channel_id}, type: {metric_type}, 错误: {e}")
            raise
    
    def get_tenant_metrics_summary(
        self,
        tenant_id: str,
        metric_type: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        获取租户指标摘要统计
        
        Args:
            tenant_id: 租户ID
            metric_type: 指标类型
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict[str, Any]: 指标摘要
        """
        try:
            result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as record_count,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    SUM(value) as sum_value,
                    STDDEV(value) as stddev_value
                FROM channel_metrics 
                WHERE tenant_id = :tenant_id 
                    AND metric_type = :metric_type
                    AND timestamp >= :start_time 
                    AND timestamp <= :end_time
            """), {
                "tenant_id": tenant_id,
                "metric_type": metric_type,
                "start_time": start_time,
                "end_time": end_time
            }).fetchone()
            
            return {
                "record_count": result[0] or 0,
                "avg_value": float(result[1] or 0),
                "min_value": float(result[2] or 0),
                "max_value": float(result[3] or 0),
                "sum_value": float(result[4] or 0),
                "stddev_value": float(result[5] or 0)
            }
        except Exception as e:
            logger.error(f"获取租户指标摘要失败 - tenant_id: {tenant_id}, type: {metric_type}, 错误: {e}")
            raise
    
    def get_channel_performance_trend(
        self,
        channel_id: str,
        metric_type: str,
        hours: int = 24,
        interval_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """
        获取渠道性能趋势数据
        
        Args:
            channel_id: 渠道ID
            metric_type: 指标类型
            hours: 时间范围（小时）
            interval_minutes: 聚合间隔（分钟）
            
        Returns:
            List[Dict[str, Any]]: 趋势数据点列表
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            result = self.db.execute(text("""
                SELECT 
                    date_trunc('hour', timestamp) + 
                    (extract(minute from timestamp)::int / :interval) * 
                    interval ':interval minutes' as time_bucket,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    COUNT(*) as record_count
                FROM channel_metrics 
                WHERE channel_id = :channel_id 
                    AND metric_type = :metric_type
                    AND timestamp >= :start_time 
                    AND timestamp <= :end_time
                GROUP BY time_bucket
                ORDER BY time_bucket ASC
            """), {
                "channel_id": channel_id,
                "metric_type": metric_type,
                "start_time": start_time,
                "end_time": end_time,
                "interval": interval_minutes
            }).fetchall()
            
            return [
                {
                    "timestamp": row[0],
                    "avg_value": float(row[1] or 0),
                    "min_value": float(row[2] or 0),
                    "max_value": float(row[3] or 0),
                    "record_count": row[4] or 0
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"获取渠道性能趋势失败 - channel_id: {channel_id}, type: {metric_type}, 错误: {e}")
            raise
    
    def get_top_performing_channels(
        self,
        tenant_id: str,
        metric_type: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10,
        order_by: str = "avg"
    ) -> List[Dict[str, Any]]:
        """
        获取表现最好的渠道排行
        
        Args:
            tenant_id: 租户ID
            metric_type: 指标类型
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            order_by: 排序方式 (avg, sum, max, min)
            
        Returns:
            List[Dict[str, Any]]: 渠道排行列表
        """
        try:
            order_column = {
                "avg": "avg_value",
                "sum": "sum_value", 
                "max": "max_value",
                "min": "min_value"
            }.get(order_by, "avg_value")
            
            result = self.db.execute(text(f"""
                SELECT 
                    channel_id,
                    COUNT(*) as record_count,
                    AVG(value) as avg_value,
                    SUM(value) as sum_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value
                FROM channel_metrics 
                WHERE tenant_id = :tenant_id 
                    AND metric_type = :metric_type
                    AND timestamp >= :start_time 
                    AND timestamp <= :end_time
                GROUP BY channel_id
                ORDER BY {order_column} DESC
                LIMIT :limit
            """), {
                "tenant_id": tenant_id,
                "metric_type": metric_type,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit
            }).fetchall()
            
            return [
                {
                    "channel_id": row[0],
                    "record_count": row[1] or 0,
                    "avg_value": float(row[2] or 0),
                    "sum_value": float(row[3] or 0),
                    "min_value": float(row[4] or 0),
                    "max_value": float(row[5] or 0)
                }
                for row in result
            ]
        except Exception as e:
            logger.error(f"获取顶级渠道排行失败 - tenant_id: {tenant_id}, type: {metric_type}, 错误: {e}")
            raise
    
    def get_channel_health_metrics(self, channel_id: str, hours: int = 1) -> Dict[str, Any]:
        """
        获取渠道健康指标
        
        Args:
            channel_id: 渠道ID
            hours: 时间范围（小时）
            
        Returns:
            Dict[str, Any]: 健康指标数据
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # 获取各类型指标
            metrics = {}
            for metric_type in ['response_time', 'success_rate', 'error_rate', 'request_count']:
                result = self.db.execute(text("""
                    SELECT 
                        COUNT(*) as count,
                        AVG(value) as avg,
                        MIN(value) as min,
                        MAX(value) as max,
                        SUM(value) as sum
                    FROM channel_metrics 
                    WHERE channel_id = :channel_id 
                        AND metric_type = :metric_type
                        AND timestamp >= :start_time 
                        AND timestamp <= :end_time
                """), {
                    "channel_id": channel_id,
                    "metric_type": metric_type,
                    "start_time": start_time,
                    "end_time": end_time
                }).fetchone()
                
                metrics[metric_type] = {
                    "count": result[0] or 0,
                    "avg": float(result[1] or 0),
                    "min": float(result[2] or 0),
                    "max": float(result[3] or 0),
                    "sum": float(result[4] or 0)
                } if result else {"count": 0, "avg": 0, "min": 0, "max": 0, "sum": 0}
            
            return metrics
        except Exception as e:
            logger.error(f"获取渠道健康指标失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def aggregate_hourly_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        tenant_id: str = None
    ) -> int:
        """
        聚合小时级指标数据
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            tenant_id: 租户ID（可选）
            
        Returns:
            int: 聚合的记录数量
        """
        try:
            tenant_filter = ""
            params = {
                "start_time": start_time,
                "end_time": end_time
            }
            
            if tenant_id:
                tenant_filter = "AND tenant_id = :tenant_id"
                params["tenant_id"] = tenant_id
            
            # 创建小时级聚合表（如果不存在）
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS channel_metrics_hourly (
                    id SERIAL PRIMARY KEY,
                    channel_id VARCHAR(255) NOT NULL,
                    tenant_id UUID NOT NULL,
                    metric_type VARCHAR(100) NOT NULL,
                    hour_bucket TIMESTAMP NOT NULL,
                    avg_value FLOAT NOT NULL,
                    min_value FLOAT NOT NULL,
                    max_value FLOAT NOT NULL,
                    sum_value FLOAT NOT NULL,
                    record_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(channel_id, tenant_id, metric_type, hour_bucket)
                )
            """))
            
            # 插入聚合数据
            result = self.db.execute(text(f"""
                INSERT INTO channel_metrics_hourly 
                (channel_id, tenant_id, metric_type, hour_bucket, avg_value, min_value, max_value, sum_value, record_count)
                SELECT 
                    channel_id,
                    tenant_id,
                    metric_type,
                    date_trunc('hour', timestamp) as hour_bucket,
                    AVG(value) as avg_value,
                    MIN(value) as min_value,
                    MAX(value) as max_value,
                    SUM(value) as sum_value,
                    COUNT(*) as record_count
                FROM channel_metrics 
                WHERE timestamp >= :start_time 
                    AND timestamp <= :end_time
                    {tenant_filter}
                GROUP BY channel_id, tenant_id, metric_type, hour_bucket
                ON CONFLICT (channel_id, tenant_id, metric_type, hour_bucket) 
                DO UPDATE SET 
                    avg_value = EXCLUDED.avg_value,
                    min_value = EXCLUDED.min_value,
                    max_value = EXCLUDED.max_value,
                    sum_value = EXCLUDED.sum_value,
                    record_count = EXCLUDED.record_count
            """), params)
            
            self.db.commit()
            affected_rows = result.rowcount
            logger.info(f"成功聚合 {affected_rows} 条小时级指标数据")
            return affected_rows
        except Exception as e:
            self.db.rollback()
            logger.error(f"聚合小时级指标失败 - 错误: {e}")
            raise
    
    def cleanup_old_metrics(self, retention_days: int) -> int:
        """
        清理旧的指标数据
        
        Args:
            retention_days: 保留天数
            
        Returns:
            int: 删除的记录数量
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(days=retention_days)
            
            result = self.db.query(self.model).filter(
                self.model.timestamp < cutoff_time
            ).delete(synchronize_session=False)
            
            self.db.commit()
            logger.info(f"成功清理 {result} 条过期指标数据 (保留天数: {retention_days})")
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"清理过期指标数据失败 - 错误: {e}")
            raise
    
    def get_metrics_by_provider(
        self,
        provider_id: str,
        tenant_id: str,
        metric_type: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        获取供应商级别的指标统计
        
        Args:
            provider_id: 供应商ID
            tenant_id: 租户ID
            metric_type: 指标类型
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict[str, Any]: 供应商指标统计
        """
        try:
            result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as record_count,
                    AVG(cm.value) as avg_value,
                    MIN(cm.value) as min_value,
                    MAX(cm.value) as max_value,
                    SUM(cm.value) as sum_value
                FROM channel_metrics cm
                INNER JOIN channels c ON cm.channel_id = c.channel_id
                WHERE c.provider_id = :provider_id 
                    AND cm.tenant_id = :tenant_id
                    AND cm.metric_type = :metric_type
                    AND cm.timestamp >= :start_time 
                    AND cm.timestamp <= :end_time
            """), {
                "provider_id": provider_id,
                "tenant_id": tenant_id,
                "metric_type": metric_type,
                "start_time": start_time,
                "end_time": end_time
            }).fetchone()
            
            return {
                "provider_id": provider_id,
                "metric_type": metric_type,
                "record_count": result[0] or 0,
                "avg_value": float(result[1] or 0),
                "min_value": float(result[2] or 0),
                "max_value": float(result[3] or 0),
                "sum_value": float(result[4] or 0)
            }
        except Exception as e:
            logger.error(f"获取供应商指标失败 - provider_id: {provider_id}, type: {metric_type}, 错误: {e}")
            raise
    
    def batch_record_metrics(self, metrics: List[Dict[str, Any]]) -> int:
        """
        批量记录指标
        
        Args:
            metrics: 指标数据列表
            
        Returns:
            int: 记录的指标数量
        """
        try:
            metric_objects = []
            for metric_data in metrics:
                metric_obj = ChannelMetricsTable(
                    channel_id=metric_data['channel_id'],
                    tenant_id=metric_data['tenant_id'],
                    metric_type=metric_data['metric_type'],
                    value=metric_data['value'],
                    timestamp=metric_data.get('timestamp', datetime.utcnow()),
                    metadata=metric_data.get('metadata', {})
                )
                metric_objects.append(metric_obj)
            
            self.db.add_all(metric_objects)
            self.db.commit()
            
            logger.info(f"成功批量记录 {len(metric_objects)} 条指标数据")
            return len(metric_objects)
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量记录指标失败 - 错误: {e}")
            raise