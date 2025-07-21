"""
负载均衡服务

实现智能负载均衡算法，根据渠道性能、健康状况和配置
选择最佳的渠道处理请求。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import logging
import random
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from ..repositories.channel_repository import ChannelRepository
from ..repositories.metrics_repository import MetricsRepository
from ..models.database import ChannelTable
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LoadBalancerService:
    """负载均衡服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.channel_repo = ChannelRepository(db)
        self.metrics_repo = MetricsRepository(db)
        
        # 算法映射
        self.algorithms = {
            "weighted_random": self._weighted_random_selection,
            "round_robin": self._round_robin_selection,
            "least_connections": self._least_connections_selection,
            "best_performance": self._best_performance_selection,
            "adaptive": self._adaptive_selection
        }
    
    def select_channel(
        self,
        model_name: str,
        tenant_id: str,
        algorithm: str = None,
        exclude_channels: List[str] = None
    ) -> Optional[ChannelTable]:
        """
        选择最佳渠道处理请求
        
        Args:
            model_name: 模型名称
            tenant_id: 租户ID
            algorithm: 负载均衡算法
            exclude_channels: 排除的渠道ID列表
            
        Returns:
            Optional[ChannelTable]: 选择的渠道
        """
        try:
            # 获取可用候选渠道
            candidates = self._get_available_candidates(
                model_name, tenant_id, exclude_channels or []
            )
            
            if not candidates:
                logger.warning(f"没有可用的渠道 - model: {model_name}, tenant: {tenant_id}")
                return None
            
            # 选择负载均衡算法
            algorithm = algorithm or settings.load_balancer_algorithm
            selection_func = self.algorithms.get(algorithm, self._weighted_random_selection)
            
            # 执行选择
            selected_channel = selection_func(candidates)
            
            if selected_channel:
                logger.info(f"负载均衡选择渠道成功 - algorithm: {algorithm}, channel: {selected_channel.channel_id}")
                
                # 记录选择指标
                self.metrics_repo.record_channel_metric(
                    selected_channel.channel_id,
                    tenant_id,
                    "load_balancer_selection",
                    1.0,
                    metadata={"algorithm": algorithm, "model": model_name}
                )
            
            return selected_channel
            
        except Exception as e:
            logger.error(f"负载均衡选择渠道失败 - model: {model_name}, tenant: {tenant_id}, 错误: {e}")
            return None
    
    def _get_available_candidates(
        self,
        model_name: str,
        tenant_id: str,
        exclude_channels: List[str]
    ) -> List[Tuple[ChannelTable, float]]:
        """
        获取可用的候选渠道及其权重分数
        
        Args:
            model_name: 模型名称
            tenant_id: 租户ID
            exclude_channels: 排除的渠道ID列表
            
        Returns:
            List[Tuple[ChannelTable, float]]: 候选渠道和权重分数列表
        """
        try:
            # 获取基础候选渠道
            raw_candidates = self.channel_repo.get_available_channels_for_load_balancing(
                model_name, tenant_id
            )
            
            # 过滤排除的渠道
            candidates = [
                channel for channel in raw_candidates
                if channel.channel_id not in exclude_channels
            ]
            
            if not candidates:
                return []
            
            # 计算权重分数
            weighted_candidates = []
            for channel in candidates:
                score = self._calculate_channel_score(channel)
                weighted_candidates.append((channel, score))
            
            # 按分数排序
            weighted_candidates.sort(key=lambda x: x[1], reverse=True)
            
            return weighted_candidates
            
        except Exception as e:
            logger.error(f"获取候选渠道失败 - model: {model_name}, tenant: {tenant_id}, 错误: {e}")
            return []
    
    def _calculate_channel_score(self, channel: ChannelTable) -> float:
        """
        计算渠道的综合权重分数
        
        Args:
            channel: 渠道对象
            
        Returns:
            float: 权重分数
        """
        try:
            # 基础权重
            base_weight = channel.weight
            
            # 健康因子（成功率）
            health_factor = channel.success_rate * settings.load_balancer_health_factor
            
            # 响应时间因子（响应时间越短分数越高）
            max_response_time = 10000  # 10秒作为最大响应时间
            response_time_factor = (max_response_time - min(channel.response_time, max_response_time)) / max_response_time
            response_time_factor *= settings.load_balancer_response_time_factor
            
            # 容量利用率因子（使用率越低分数越高）
            if channel.max_requests_per_minute > 0:
                utilization = channel.current_requests_per_minute / channel.max_requests_per_minute
                capacity_factor = (1.0 - utilization) * 0.3
            else:
                capacity_factor = 0.0
            
            # 优先级因子
            priority_factor = channel.priority * 0.1
            
            # 综合分数计算
            total_score = (
                base_weight * 0.4 +
                health_factor * 1000 +
                response_time_factor * 500 +
                capacity_factor * 200 +
                priority_factor * 100
            )
            
            return max(total_score, 0.1)  # 确保分数为正
            
        except Exception as e:
            logger.error(f"计算渠道分数失败 - channel: {channel.channel_id}, 错误: {e}")
            return 0.1
    
    def _weighted_random_selection(
        self,
        candidates: List[Tuple[ChannelTable, float]]
    ) -> Optional[ChannelTable]:
        """
        加权随机选择算法
        
        Args:
            candidates: 候选渠道和权重分数列表
            
        Returns:
            Optional[ChannelTable]: 选择的渠道
        """
        if not candidates:
            return None
        
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
    
    def _round_robin_selection(
        self,
        candidates: List[Tuple[ChannelTable, float]]
    ) -> Optional[ChannelTable]:
        """
        轮询选择算法
        
        Args:
            candidates: 候选渠道和权重分数列表
            
        Returns:
            Optional[ChannelTable]: 选择的渠道
        """
        if not candidates:
            return None
        
        # 简单轮询实现（实际生产中应该持久化轮询状态）
        # 这里使用时间戳作为伪随机种子进行简单轮询
        index = int(time.time()) % len(candidates)
        return candidates[index][0]
    
    def _least_connections_selection(
        self,
        candidates: List[Tuple[ChannelTable, float]]
    ) -> Optional[ChannelTable]:
        """
        最少连接选择算法
        
        Args:
            candidates: 候选渠道和权重分数列表
            
        Returns:
            Optional[ChannelTable]: 选择的渠道
        """
        if not candidates:
            return None
        
        # 选择当前请求数最少的渠道
        min_connections = min(channel.current_requests_per_minute for channel, _ in candidates)
        
        # 过滤出连接数最少的渠道
        least_connected = [
            (channel, score) for channel, score in candidates
            if channel.current_requests_per_minute == min_connections
        ]
        
        # 如果有多个最少连接的渠道，按权重选择
        if len(least_connected) > 1:
            return self._weighted_random_selection(least_connected)
        else:
            return least_connected[0][0]
    
    def _best_performance_selection(
        self,
        candidates: List[Tuple[ChannelTable, float]]
    ) -> Optional[ChannelTable]:
        """
        最佳性能选择算法
        
        Args:
            candidates: 候选渠道和权重分数列表
            
        Returns:
            Optional[ChannelTable]: 选择的渠道
        """
        if not candidates:
            return None
        
        # 候选渠道已按分数排序，直接返回第一个
        return candidates[0][0]
    
    def _adaptive_selection(
        self,
        candidates: List[Tuple[ChannelTable, float]]
    ) -> Optional[ChannelTable]:
        """
        自适应选择算法
        根据实时性能动态调整选择策略
        
        Args:
            candidates: 候选渠道和权重分数列表
            
        Returns:
            Optional[ChannelTable]: 选择的渠道
        """
        if not candidates:
            return None
        
        # 分析候选渠道的性能差异
        scores = [score for _, score in candidates]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        
        # 如果性能差异较大，使用最佳性能选择
        if max_score - avg_score > avg_score * 0.5:
            return self._best_performance_selection(candidates)
        else:
            # 如果性能相近，使用加权随机选择
            return self._weighted_random_selection(candidates)
    
    def get_load_balancer_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        获取负载均衡统计信息
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 获取渠道健康摘要
            health_summary = self.channel_repo.get_channel_health_summary(tenant_id)
            
            # 获取最近的选择指标
            end_time = datetime.utcnow()
            start_time = end_time.replace(hour=end_time.hour-1)  # 最近1小时
            
            selection_stats = self.metrics_repo.get_tenant_metrics_summary(
                tenant_id, "load_balancer_selection", start_time, end_time
            )
            
            return {
                "tenant_id": tenant_id,
                "channel_health": health_summary,
                "recent_selections": selection_stats,
                "load_balancer_config": {
                    "algorithm": settings.load_balancer_algorithm,
                    "health_factor": settings.load_balancer_health_factor,
                    "response_time_factor": settings.load_balancer_response_time_factor
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取负载均衡统计失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise
    
    def update_algorithm_config(
        self,
        health_factor: float = None,
        response_time_factor: float = None
    ) -> Dict[str, Any]:
        """
        更新负载均衡算法配置
        
        Args:
            health_factor: 健康因子权重
            response_time_factor: 响应时间因子权重
            
        Returns:
            Dict[str, Any]: 更新后的配置
        """
        try:
            if health_factor is not None:
                if 0.0 <= health_factor <= 1.0:
                    settings.load_balancer_health_factor = health_factor
                else:
                    raise ValueError("健康因子必须在0.0-1.0之间")
            
            if response_time_factor is not None:
                if 0.0 <= response_time_factor <= 1.0:
                    settings.load_balancer_response_time_factor = response_time_factor
                else:
                    raise ValueError("响应时间因子必须在0.0-1.0之间")
            
            logger.info(f"负载均衡配置更新成功 - health_factor: {health_factor}, response_time_factor: {response_time_factor}")
            
            return {
                "health_factor": settings.load_balancer_health_factor,
                "response_time_factor": settings.load_balancer_response_time_factor,
                "updated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"更新负载均衡配置失败 - 错误: {e}")
            raise
    
    def simulate_selection(
        self,
        model_name: str,
        tenant_id: str,
        algorithm: str,
        num_requests: int = 100
    ) -> Dict[str, Any]:
        """
        模拟负载均衡选择（用于测试和分析）
        
        Args:
            model_name: 模型名称
            tenant_id: 租户ID
            algorithm: 负载均衡算法
            num_requests: 模拟请求数
            
        Returns:
            Dict[str, Any]: 模拟结果
        """
        try:
            # 获取候选渠道
            candidates = self._get_available_candidates(model_name, tenant_id, [])
            
            if not candidates:
                return {"error": "没有可用的渠道"}
            
            # 执行模拟
            selection_counts = {}
            selection_func = self.algorithms.get(algorithm, self._weighted_random_selection)
            
            for _ in range(num_requests):
                selected_channel = selection_func(candidates)
                if selected_channel:
                    channel_id = selected_channel.channel_id
                    selection_counts[channel_id] = selection_counts.get(channel_id, 0) + 1
            
            # 计算分布比例
            selection_distribution = {}
            for channel_id, count in selection_counts.items():
                selection_distribution[channel_id] = {
                    "count": count,
                    "percentage": round((count / num_requests) * 100, 2)
                }
            
            return {
                "model_name": model_name,
                "tenant_id": tenant_id,
                "algorithm": algorithm,
                "num_requests": num_requests,
                "available_channels": len(candidates),
                "selection_distribution": selection_distribution,
                "simulation_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"负载均衡模拟失败 - model: {model_name}, algorithm: {algorithm}, 错误: {e}")
            raise
    
    def get_algorithm_recommendation(
        self,
        tenant_id: str,
        model_name: str = None
    ) -> Dict[str, Any]:
        """
        根据当前渠道状况推荐最佳负载均衡算法
        
        Args:
            tenant_id: 租户ID
            model_name: 模型名称（可选）
            
        Returns:
            Dict[str, Any]: 推荐结果
        """
        try:
            # 获取渠道健康摘要
            health_summary = self.channel_repo.get_channel_health_summary(tenant_id)
            
            # 获取可用渠道
            if model_name:
                channels = self.channel_repo.get_channels_by_model(model_name, tenant_id)
            else:
                channels = self.channel_repo.get_active_channels(tenant_id)
            
            if not channels:
                return {
                    "recommendation": "无法提供推荐",
                    "reason": "没有可用的渠道"
                }
            
            # 分析渠道特征
            response_times = [ch.response_time for ch in channels]
            success_rates = [ch.success_rate for ch in channels]
            
            avg_response_time = sum(response_times) / len(response_times)
            avg_success_rate = sum(success_rates) / len(success_rates)
            
            response_time_variance = sum((rt - avg_response_time) ** 2 for rt in response_times) / len(response_times)
            success_rate_variance = sum((sr - avg_success_rate) ** 2 for sr in success_rates) / len(success_rates)
            
            # 推荐逻辑
            if len(channels) == 1:
                recommendation = "best_performance"
                reason = "只有一个可用渠道，使用最佳性能算法"
            elif success_rate_variance > 0.1:  # 成功率差异较大
                recommendation = "best_performance"
                reason = "渠道性能差异较大，建议使用最佳性能算法"
            elif response_time_variance > 1000:  # 响应时间差异较大
                recommendation = "adaptive"
                reason = "响应时间差异较大，建议使用自适应算法"
            elif avg_success_rate > 0.95:  # 所有渠道都很稳定
                recommendation = "weighted_random"
                reason = "所有渠道性能稳定，建议使用加权随机算法"
            else:
                recommendation = "least_connections"
                reason = "渠道性能一般，建议使用最少连接算法"
            
            return {
                "recommendation": recommendation,
                "reason": reason,
                "channel_analysis": {
                    "total_channels": len(channels),
                    "avg_response_time": round(avg_response_time, 2),
                    "avg_success_rate": round(avg_success_rate, 4),
                    "response_time_variance": round(response_time_variance, 2),
                    "success_rate_variance": round(success_rate_variance, 4)
                },
                "health_summary": health_summary,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取算法推荐失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise