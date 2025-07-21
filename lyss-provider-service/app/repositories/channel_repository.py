"""
渠道数据访问层

负责渠道相关的数据库操作，包括渠道管理、状态更新、负载均衡等。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func
from datetime import datetime, timedelta
import logging

from .base import BaseRepository
from ..models.database import ChannelTable
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ChannelRepository(BaseRepository[ChannelTable, Dict, Dict]):
    """渠道Repository"""
    
    def __init__(self, db: Session):
        super().__init__(ChannelTable, db)
    
    def get_by_channel_id(self, channel_id: str) -> Optional[ChannelTable]:
        """
        根据渠道ID获取渠道配置
        
        Args:
            channel_id: 渠道ID
            
        Returns:
            ChannelTable: 渠道配置，未找到返回None
        """
        try:
            return self.db.query(self.model).filter(
                self.model.channel_id == channel_id
            ).first()
        except Exception as e:
            logger.error(f"根据渠道ID获取配置失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def get_active_channels(self, tenant_id: str) -> List[ChannelTable]:
        """
        获取租户的所有活跃渠道
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[ChannelTable]: 活跃渠道列表
        """
        try:
            return self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.status == 'active'
                )
            ).order_by(
                self.model.priority.desc(), 
                self.model.weight.desc()
            ).all()
        except Exception as e:
            logger.error(f"获取租户活跃渠道失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_channels_by_provider(self, provider_id: str, tenant_id: str) -> List[ChannelTable]:
        """
        获取指定供应商的渠道列表
        
        Args:
            provider_id: 供应商ID
            tenant_id: 租户ID
            
        Returns:
            List[ChannelTable]: 渠道列表
        """
        try:
            return self.db.query(self.model).filter(
                and_(
                    self.model.provider_id == provider_id,
                    self.model.tenant_id == tenant_id
                )
            ).order_by(self.model.priority.desc()).all()
        except Exception as e:
            logger.error(f"获取供应商渠道失败 - provider_id: {provider_id}, tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_channels_by_model(self, model_name: str, tenant_id: str) -> List[ChannelTable]:
        """
        获取支持指定模型的渠道列表
        
        Args:
            model_name: 模型名称
            tenant_id: 租户ID
            
        Returns:
            List[ChannelTable]: 支持该模型的渠道列表
        """
        try:
            return self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.status == 'active',
                    self.model.supported_models.contains([model_name])
                )
            ).order_by(
                self.model.priority.desc(),
                self.model.weight.desc()
            ).all()
        except Exception as e:
            logger.error(f"获取支持模型的渠道失败 - model: {model_name}, tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_available_channels_for_load_balancing(
        self, 
        model_name: str, 
        tenant_id: str,
        min_success_rate: float = None
    ) -> List[ChannelTable]:
        """
        获取可用于负载均衡的渠道列表
        
        Args:
            model_name: 模型名称
            tenant_id: 租户ID
            min_success_rate: 最小成功率阈值
            
        Returns:
            List[ChannelTable]: 可用渠道列表
        """
        try:
            min_rate = min_success_rate or settings.min_channel_success_rate
            
            return self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.status == 'active',
                    self.model.supported_models.contains([model_name]),
                    self.model.current_requests_per_minute < self.model.max_requests_per_minute,
                    self.model.success_rate >= min_rate
                )
            ).order_by(
                self.model.priority.desc(),
                self.model.weight.desc(),
                self.model.response_time.asc()
            ).all()
        except Exception as e:
            logger.error(f"获取负载均衡渠道失败 - model: {model_name}, tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def update_channel_status(self, channel_id: str, status: str) -> bool:
        """
        更新渠道状态
        
        Args:
            channel_id: 渠道ID
            status: 新状态
            
        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.db.query(self.model).filter(
                self.model.channel_id == channel_id
            ).update({
                "status": status,
                "updated_at": datetime.utcnow()
            })
            
            if result > 0:
                self.db.commit()
                logger.info(f"成功更新渠道状态 - channel_id: {channel_id}, status: {status}")
                return True
            else:
                logger.warning(f"渠道不存在 - channel_id: {channel_id}")
                return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新渠道状态失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def update_channel_metrics(
        self, 
        channel_id: str,
        success_rate: float = None,
        response_time: float = None,
        current_rpm: int = None,
        error_rate: float = None
    ) -> bool:
        """
        更新渠道性能指标
        
        Args:
            channel_id: 渠道ID
            success_rate: 成功率
            response_time: 平均响应时间
            current_rpm: 当前每分钟请求数
            error_rate: 错误率
            
        Returns:
            bool: 是否更新成功
        """
        try:
            update_data = {"updated_at": datetime.utcnow()}
            
            if success_rate is not None:
                update_data["success_rate"] = success_rate
            if response_time is not None:
                update_data["response_time"] = response_time
            if current_rpm is not None:
                update_data["current_requests_per_minute"] = current_rpm
            if error_rate is not None:
                update_data["error_rate"] = error_rate
            
            result = self.db.query(self.model).filter(
                self.model.channel_id == channel_id
            ).update(update_data)
            
            if result > 0:
                self.db.commit()
                logger.info(f"成功更新渠道指标 - channel_id: {channel_id}")
                return True
            else:
                logger.warning(f"渠道不存在 - channel_id: {channel_id}")
                return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"更新渠道指标失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def increment_request_count(self, channel_id: str) -> bool:
        """
        增加渠道请求计数
        
        Args:
            channel_id: 渠道ID
            
        Returns:
            bool: 是否更新成功
        """
        try:
            result = self.db.query(self.model).filter(
                self.model.channel_id == channel_id
            ).update({
                "current_requests_per_minute": self.model.current_requests_per_minute + 1,
                "updated_at": datetime.utcnow()
            })
            
            if result > 0:
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            logger.error(f"增加渠道请求计数失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def reset_rpm_counters(self) -> int:
        """
        重置所有渠道的每分钟请求计数
        
        Returns:
            int: 重置的渠道数量
        """
        try:
            result = self.db.query(self.model).update({
                "current_requests_per_minute": 0,
                "updated_at": datetime.utcnow()
            })
            
            self.db.commit()
            logger.info(f"成功重置 {result} 个渠道的请求计数")
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"重置渠道请求计数失败 - 错误: {e}")
            raise
    
    def get_channel_health_summary(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取租户渠道健康状况摘要
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            Dict[str, Any]: 健康状况摘要
        """
        try:
            result = self.db.execute(text("""
                SELECT 
                    COUNT(*) as total_channels,
                    COUNT(*) FILTER (WHERE status = 'active') as active_channels,
                    COUNT(*) FILTER (WHERE status = 'inactive') as inactive_channels,
                    COUNT(*) FILTER (WHERE status = 'error') as error_channels,
                    AVG(success_rate) as avg_success_rate,
                    AVG(response_time) as avg_response_time,
                    AVG(error_rate) as avg_error_rate,
                    COUNT(*) FILTER (WHERE success_rate < :min_success_rate) as unhealthy_channels
                FROM channels 
                WHERE tenant_id = :tenant_id
            """), {
                "tenant_id": tenant_id,
                "min_success_rate": settings.min_channel_success_rate
            }).fetchone()
            
            return {
                "total_channels": result[0] or 0,
                "active_channels": result[1] or 0,
                "inactive_channels": result[2] or 0,
                "error_channels": result[3] or 0,
                "avg_success_rate": float(result[4] or 0),
                "avg_response_time": float(result[5] or 0),
                "avg_error_rate": float(result[6] or 0),
                "unhealthy_channels": result[7] or 0
            }
        except Exception as e:
            logger.error(f"获取渠道健康摘要失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def search_channels(self, tenant_id: str, query: str) -> List[ChannelTable]:
        """
        搜索渠道
        
        Args:
            tenant_id: 租户ID
            query: 搜索关键词
            
        Returns:
            List[ChannelTable]: 匹配的渠道列表
        """
        try:
            search_pattern = f"%{query}%"
            return self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == tenant_id,
                    or_(
                        self.model.name.ilike(search_pattern),
                        self.model.channel_id.ilike(search_pattern),
                        self.model.provider_id.ilike(search_pattern),
                        self.model.description.ilike(search_pattern)
                    )
                )
            ).order_by(self.model.name).all()
        except Exception as e:
            logger.error(f"搜索渠道失败 - tenant_id: {tenant_id}, query: {query}, 错误: {e}")
            raise
    
    def get_channels_by_status(self, tenant_id: str, status: str) -> List[ChannelTable]:
        """
        根据状态获取渠道列表
        
        Args:
            tenant_id: 租户ID
            status: 渠道状态
            
        Returns:
            List[ChannelTable]: 指定状态的渠道列表
        """
        try:
            return self.db.query(self.model).filter(
                and_(
                    self.model.tenant_id == tenant_id,
                    self.model.status == status
                )
            ).order_by(self.model.priority.desc()).all()
        except Exception as e:
            logger.error(f"根据状态获取渠道失败 - tenant_id: {tenant_id}, status: {status}, 错误: {e}")
            raise
    
    def batch_update_channel_weights(self, updates: List[Dict[str, Any]]) -> int:
        """
        批量更新渠道权重
        
        Args:
            updates: 更新数据列表，每个字典包含channel_id和weight
            
        Returns:
            int: 更新的渠道数量
        """
        try:
            updated_count = 0
            for update_data in updates:
                if 'channel_id' not in update_data or 'weight' not in update_data:
                    continue
                
                result = self.db.query(self.model).filter(
                    self.model.channel_id == update_data['channel_id']
                ).update({
                    "weight": update_data['weight'],
                    "updated_at": datetime.utcnow()
                })
                updated_count += result
            
            self.db.commit()
            logger.info(f"成功批量更新 {updated_count} 个渠道权重")
            return updated_count
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量更新渠道权重失败 - 错误: {e}")
            raise
    
    def get_load_balancing_candidates(
        self, 
        model_name: str, 
        tenant_id: str,
        max_candidates: int = 10
    ) -> List[Tuple[ChannelTable, float]]:
        """
        获取负载均衡候选渠道及其权重分数
        
        Args:
            model_name: 模型名称
            tenant_id: 租户ID
            max_candidates: 最大候选数量
            
        Returns:
            List[Tuple[ChannelTable, float]]: 候选渠道和权重分数列表
        """
        try:
            channels = self.get_available_channels_for_load_balancing(model_name, tenant_id)
            
            # 计算综合权重分数
            candidates = []
            for channel in channels[:max_candidates]:
                # 权重分数 = 基础权重 * 健康因子 * 响应时间因子
                health_factor = channel.success_rate * settings.load_balancer_health_factor
                
                # 响应时间因子（响应时间越短分数越高）
                response_time_factor = settings.load_balancer_response_time_factor / max(channel.response_time, 0.1)
                
                total_score = channel.weight * health_factor * response_time_factor
                candidates.append((channel, total_score))
            
            # 按分数排序
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates
        except Exception as e:
            logger.error(f"获取负载均衡候选渠道失败 - model: {model_name}, tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def disable_unhealthy_channels(self, min_success_rate: float = None) -> int:
        """
        禁用不健康的渠道
        
        Args:
            min_success_rate: 最小成功率阈值
            
        Returns:
            int: 禁用的渠道数量
        """
        try:
            min_rate = min_success_rate or settings.min_channel_success_rate
            
            result = self.db.query(self.model).filter(
                and_(
                    self.model.status == 'active',
                    self.model.success_rate < min_rate
                )
            ).update({
                "status": "inactive",
                "updated_at": datetime.utcnow()
            })
            
            self.db.commit()
            logger.info(f"成功禁用 {result} 个不健康渠道")
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"禁用不健康渠道失败 - 错误: {e}")
            raise