"""
渠道服务

处理渠道相关的业务逻辑，包括渠道管理、状态监控、
负载均衡等功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import logging
import random
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..repositories.channel_repository import ChannelRepository
from ..repositories.metrics_repository import MetricsRepository
from ..models.database import ChannelTable
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ChannelService:
    """渠道服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.channel_repo = ChannelRepository(db)
        self.metrics_repo = MetricsRepository(db)
    
    def get_tenant_channels(self, tenant_id: str) -> List[ChannelTable]:
        """
        获取租户的所有渠道
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[ChannelTable]: 渠道列表
        """
        try:
            return self.channel_repo.get_multi(tenant_id=tenant_id)
        except Exception as e:
            logger.error(f"获取租户渠道失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_active_channels(self, tenant_id: str) -> List[ChannelTable]:
        """
        获取租户的活跃渠道
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[ChannelTable]: 活跃渠道列表
        """
        try:
            return self.channel_repo.get_active_channels(tenant_id)
        except Exception as e:
            logger.error(f"获取活跃渠道失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_channel_by_id(self, channel_id: str) -> Optional[ChannelTable]:
        """
        根据ID获取渠道配置
        
        Args:
            channel_id: 渠道ID
            
        Returns:
            Optional[ChannelTable]: 渠道配置
        """
        try:
            return self.channel_repo.get_by_channel_id(channel_id)
        except Exception as e:
            logger.error(f"获取渠道配置失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def get_channels_by_provider(self, provider_id: str, tenant_id: str) -> List[ChannelTable]:
        """
        获取指定供应商的渠道
        
        Args:
            provider_id: 供应商ID
            tenant_id: 租户ID
            
        Returns:
            List[ChannelTable]: 渠道列表
        """
        try:
            return self.channel_repo.get_channels_by_provider(provider_id, tenant_id)
        except Exception as e:
            logger.error(f"获取供应商渠道失败 - provider_id: {provider_id}, tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def get_channels_by_model(self, model_name: str, tenant_id: str) -> List[ChannelTable]:
        """
        获取支持指定模型的渠道
        
        Args:
            model_name: 模型名称
            tenant_id: 租户ID
            
        Returns:
            List[ChannelTable]: 支持该模型的渠道列表
        """
        try:
            return self.channel_repo.get_channels_by_model(model_name, tenant_id)
        except Exception as e:
            logger.error(f"获取模型渠道失败 - model: {model_name}, tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def create_channel(self, channel_data: Dict[str, Any]) -> ChannelTable:
        """
        创建渠道
        
        Args:
            channel_data: 渠道数据
            
        Returns:
            ChannelTable: 创建的渠道
        """
        try:
            # 设置默认值
            channel_data.setdefault('status', 'active')
            channel_data.setdefault('priority', settings.default_channel_priority)
            channel_data.setdefault('weight', settings.default_channel_weight)
            channel_data.setdefault('max_requests_per_minute', settings.default_max_requests_per_minute)
            channel_data.setdefault('current_requests_per_minute', 0)
            channel_data.setdefault('success_rate', 1.0)
            channel_data.setdefault('response_time', 0.0)
            channel_data.setdefault('error_rate', 0.0)
            
            return self.channel_repo.create(obj_in=channel_data)
        except Exception as e:
            logger.error(f"创建渠道失败 - 错误: {e}")
            raise
    
    def update_channel(
        self,
        channel_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[ChannelTable]:
        """
        更新渠道配置
        
        Args:
            channel_id: 渠道ID
            update_data: 更新数据
            
        Returns:
            Optional[ChannelTable]: 更新后的渠道配置
        """
        try:
            channel = self.channel_repo.get_by_channel_id(channel_id)
            if not channel:
                logger.warning(f"渠道不存在 - channel_id: {channel_id}")
                return None
            
            return self.channel_repo.update(db_obj=channel, obj_in=update_data)
        except Exception as e:
            logger.error(f"更新渠道配置失败 - channel_id: {channel_id}, 错误: {e}")
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
            return self.channel_repo.update_channel_status(channel_id, status)
        except Exception as e:
            logger.error(f"更新渠道状态失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def delete_channel(self, channel_id: str) -> bool:
        """
        删除渠道
        
        Args:
            channel_id: 渠道ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            channel = self.channel_repo.get_by_channel_id(channel_id)
            if not channel:
                return False
            
            return self.channel_repo.delete(id=channel.id)
        except Exception as e:
            logger.error(f"删除渠道失败 - channel_id: {channel_id}, 错误: {e}")
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
            success = self.channel_repo.update_channel_metrics(
                channel_id, success_rate, response_time, current_rpm, error_rate
            )
            
            # 记录指标到历史记录
            if success:
                timestamp = datetime.utcnow()
                channel = self.channel_repo.get_by_channel_id(channel_id)
                if channel:
                    if success_rate is not None:
                        self.metrics_repo.record_channel_metric(
                            channel_id, channel.tenant_id, "success_rate", success_rate, timestamp
                        )
                    if response_time is not None:
                        self.metrics_repo.record_channel_metric(
                            channel_id, channel.tenant_id, "response_time", response_time, timestamp
                        )
                    if current_rpm is not None:
                        self.metrics_repo.record_channel_metric(
                            channel_id, channel.tenant_id, "request_count", current_rpm, timestamp
                        )
                    if error_rate is not None:
                        self.metrics_repo.record_channel_metric(
                            channel_id, channel.tenant_id, "error_rate", error_rate, timestamp
                        )
            
            return success
        except Exception as e:
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
            return self.channel_repo.increment_request_count(channel_id)
        except Exception as e:
            logger.error(f"增加请求计数失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def reset_rpm_counters(self) -> int:
        """
        重置所有渠道的每分钟请求计数
        
        Returns:
            int: 重置的渠道数量
        """
        try:
            return self.channel_repo.reset_rpm_counters()
        except Exception as e:
            logger.error(f"重置请求计数失败 - 错误: {e}")
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
            return self.channel_repo.get_channel_health_summary(tenant_id)
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
            return self.channel_repo.search_channels(tenant_id, query)
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
            return self.channel_repo.get_channels_by_status(tenant_id, status)
        except Exception as e:
            logger.error(f"根据状态获取渠道失败 - tenant_id: {tenant_id}, status: {status}, 错误: {e}")
            raise
    
    def select_best_channel(
        self,
        model_name: str,
        tenant_id: str,
        selection_strategy: str = "weighted_random"
    ) -> Optional[ChannelTable]:
        """
        选择最佳渠道进行请求处理
        
        Args:
            model_name: 模型名称
            tenant_id: 租户ID
            selection_strategy: 选择策略
            
        Returns:
            Optional[ChannelTable]: 选择的渠道
        """
        try:
            candidates = self.channel_repo.get_load_balancing_candidates(
                model_name, tenant_id, max_candidates=5
            )
            
            if not candidates:
                logger.warning(f"没有可用的渠道 - model: {model_name}, tenant_id: {tenant_id}")
                return None
            
            if selection_strategy == "weighted_random":
                return self._select_channel_weighted_random(candidates)
            elif selection_strategy == "round_robin":
                return self._select_channel_round_robin(candidates)
            elif selection_strategy == "best_performance":
                return candidates[0][0]  # 已按性能排序，取第一个
            else:
                # 默认使用加权随机
                return self._select_channel_weighted_random(candidates)
                
        except Exception as e:
            logger.error(f"选择最佳渠道失败 - model: {model_name}, tenant_id: {tenant_id}, 错误: {e}")
            return None
    
    def _select_channel_weighted_random(
        self, 
        candidates: List[Tuple[ChannelTable, float]]
    ) -> ChannelTable:
        """
        加权随机选择渠道
        
        Args:
            candidates: 候选渠道和权重分数列表
            
        Returns:
            ChannelTable: 选择的渠道
        """
        total_weight = sum(score for _, score in candidates)
        
        if total_weight == 0:
            return candidates[0][0]
        
        rand = random.random() * total_weight
        current_weight = 0
        
        for channel, weight in candidates:
            current_weight += weight
            if rand <= current_weight:
                return channel
        
        return candidates[-1][0]
    
    def _select_channel_round_robin(
        self,
        candidates: List[Tuple[ChannelTable, float]]
    ) -> ChannelTable:
        """
        轮询选择渠道
        
        Args:
            candidates: 候选渠道和权重分数列表
            
        Returns:
            ChannelTable: 选择的渠道
        """
        # 简单轮询实现（实际应该持久化轮询状态）
        return candidates[random.randint(0, len(candidates) - 1)][0]
    
    def batch_update_channel_weights(self, updates: List[Dict[str, Any]]) -> int:
        """
        批量更新渠道权重
        
        Args:
            updates: 更新数据列表
            
        Returns:
            int: 更新的渠道数量
        """
        try:
            return self.channel_repo.batch_update_channel_weights(updates)
        except Exception as e:
            logger.error(f"批量更新渠道权重失败 - 错误: {e}")
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
            return self.channel_repo.disable_unhealthy_channels(min_success_rate)
        except Exception as e:
            logger.error(f"禁用不健康渠道失败 - 错误: {e}")
            raise
    
    def get_channel_performance_report(
        self,
        channel_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取渠道性能报告
        
        Args:
            channel_id: 渠道ID
            hours: 时间范围（小时）
            
        Returns:
            Dict[str, Any]: 性能报告
        """
        try:
            # 获取基础信息
            channel = self.channel_repo.get_by_channel_id(channel_id)
            if not channel:
                return {"error": "渠道不存在"}
            
            # 获取健康指标
            health_metrics = self.metrics_repo.get_channel_health_metrics(channel_id, hours)
            
            # 获取性能趋势
            performance_trends = {}
            for metric_type in ['response_time', 'success_rate', 'error_rate']:
                trends = self.metrics_repo.get_channel_performance_trend(
                    channel_id, metric_type, hours, interval_minutes=60
                )
                performance_trends[metric_type] = trends
            
            return {
                "channel_id": channel_id,
                "channel_name": channel.name,
                "provider_id": channel.provider_id,
                "status": channel.status,
                "current_metrics": {
                    "success_rate": channel.success_rate,
                    "response_time": channel.response_time,
                    "error_rate": channel.error_rate,
                    "current_rpm": channel.current_requests_per_minute,
                    "max_rpm": channel.max_requests_per_minute
                },
                "health_metrics": health_metrics,
                "performance_trends": performance_trends,
                "report_time_range": f"{hours}小时",
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"获取渠道性能报告失败 - channel_id: {channel_id}, 错误: {e}")
            raise
    
    def validate_channel_config(self, channel_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证渠道配置数据
        
        Args:
            channel_data: 渠道配置数据
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查必填字段
        required_fields = ['channel_id', 'name', 'provider_id', 'tenant_id', 'api_endpoint']
        for field in required_fields:
            if field not in channel_data or not channel_data[field]:
                errors.append(f"缺少必填字段: {field}")
        
        # 验证supported_models格式
        if 'supported_models' in channel_data:
            if not isinstance(channel_data['supported_models'], list):
                errors.append("supported_models必须是列表格式")
            elif not channel_data['supported_models']:
                errors.append("supported_models不能为空")
        
        # 验证状态值
        if 'status' in channel_data:
            valid_statuses = ['active', 'inactive', 'error']
            if channel_data['status'] not in valid_statuses:
                errors.append(f"状态值必须是: {', '.join(valid_statuses)}")
        
        # 验证优先级和权重
        if 'priority' in channel_data:
            try:
                priority = int(channel_data['priority'])
                if priority < 1 or priority > 10:
                    errors.append("优先级必须在1-10之间")
            except (ValueError, TypeError):
                errors.append("优先级必须是整数")
        
        if 'weight' in channel_data:
            try:
                weight = int(channel_data['weight'])
                if weight < 1 or weight > 1000:
                    errors.append("权重必须在1-1000之间")
            except (ValueError, TypeError):
                errors.append("权重必须是整数")
        
        # 验证请求限制
        if 'max_requests_per_minute' in channel_data:
            try:
                rpm = int(channel_data['max_requests_per_minute'])
                if rpm < 1 or rpm > 10000:
                    errors.append("每分钟最大请求数必须在1-10000之间")
            except (ValueError, TypeError):
                errors.append("每分钟最大请求数必须是整数")
        
        return len(errors) == 0, errors