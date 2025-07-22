"""
Channel管理器

借鉴One-API的Channel设计，实现智能负载均衡、故障转移
和健康检查功能。提供高可用的供应商访问管理。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import Dict, List, Optional, Tuple
import asyncio
import time
import random
import logging
from dataclasses import asdict

from app.models.channel import (
    Channel, ChannelStatus, ChannelHealth, ChannelMetrics,
    ChannelCreateRequest, ChannelResponse, ChannelStatusResponse
)
from app.providers.registry import provider_registry
from app.utils.encryption import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class ChannelManager:
    """Channel管理器 - 借鉴One-API设计"""
    
    def __init__(self):
        self.channels: Dict[int, Channel] = {}
        self.channel_metrics: Dict[int, ChannelMetrics] = {}
        self.model_to_channels: Dict[str, List[int]] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._next_channel_id = 1
        
    async def initialize(self):
        """初始化Channel管理器"""
        await self._load_channels()
        self._start_health_check()
        logger.info(f"Channel管理器初始化完成，共 {len(self.channels)} 个Channel")
    
    async def _load_channels(self):
        """加载现有的Channel配置（实际生产中从数据库加载）"""
        # 这里是示例数据，实际应该从数据库加载
        pass
    
    def _start_health_check(self):
        """启动健康检查任务"""
        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.create_task(self._health_check_worker())
            logger.info("Channel健康检查任务已启动")
    
    async def register_channel(self, channel_data: ChannelCreateRequest, tenant_id: str) -> int:
        """
        注册新Channel
        
        Args:
            channel_data: Channel创建数据
            tenant_id: 租户ID
            
        Returns:
            int: 新创建的Channel ID
            
        Raises:
            ValueError: 验证失败
        """
        try:
            # 验证供应商配置
            provider = provider_registry.get_provider(channel_data.provider_id)
            if not provider:
                raise ValueError(f"未知供应商: {channel_data.provider_id}")
            
            # 验证凭证
            is_valid = await provider.validate_provider_credentials(channel_data.credentials)
            if not is_valid:
                raise ValueError("凭证验证失败")
            
            # 生成Channel ID
            channel_id = self._next_channel_id
            self._next_channel_id += 1
            
            # 加密凭证
            encrypted_credentials = encrypt_data(channel_data.credentials)
            
            # 创建Channel
            channel = Channel(
                id=channel_id,
                name=channel_data.name,
                provider_id=channel_data.provider_id,
                base_url=channel_data.base_url or "",
                credentials=channel_data.credentials,  # 内存中保存明文，实际存储加密
                models=channel_data.models or [],
                status=ChannelStatus.ACTIVE,
                priority=channel_data.priority,
                weight=channel_data.weight,
                tenant_id=tenant_id,
                max_requests_per_minute=channel_data.max_requests_per_minute,
                created_at=time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ')
            )
            
            # 注册到管理器
            self.channels[channel_id] = channel
            self._update_model_mapping(channel)
            self._initialize_channel_metrics(channel_id)
            
            logger.info(f"成功注册Channel: {channel.name} (ID: {channel_id})")
            return channel_id
            
        except Exception as e:
            logger.error(f"注册Channel失败: {e}")
            raise
    
    def _update_model_mapping(self, channel: Channel):
        """更新模型到Channel的映射"""
        for model in channel.models:
            if model not in self.model_to_channels:
                self.model_to_channels[model] = []
            if channel.id not in self.model_to_channels[model]:
                self.model_to_channels[model].append(channel.id)
    
    def _initialize_channel_metrics(self, channel_id: int):
        """初始化Channel性能指标"""
        self.channel_metrics[channel_id] = ChannelMetrics(
            channel_id=channel_id,
            response_time=0.0,
            success_rate=1.0,
            request_count=0,
            error_count=0,
            last_success=None,
            last_error=None,
            health_status=ChannelHealth.UNKNOWN
        )
    
    def select_channel(self, model: str, tenant_id: str, exclude_ids: Optional[List[int]] = None) -> Optional[Channel]:
        """
        智能Channel选择 - 核心算法
        
        Args:
            model: 模型名称
            tenant_id: 租户ID
            exclude_ids: 要排除的Channel ID列表
            
        Returns:
            Optional[Channel]: 选中的Channel，如果没有可用的返回None
        """
        try:
            # 1. 获取支持该模型的Channel
            available_channels = self._get_channels_for_model(model)
            
            # 2. 过滤排除的Channel
            if exclude_ids:
                available_channels = [
                    ch_id for ch_id in available_channels 
                    if ch_id not in exclude_ids
                ]
            
            # 3. 过滤租户权限
            tenant_channels = [
                ch_id for ch_id in available_channels 
                if self.channels[ch_id].tenant_id == tenant_id
            ]
            
            # 4. 健康检查过滤
            healthy_channels = [
                ch_id for ch_id in tenant_channels
                if self._is_channel_healthy(ch_id)
            ]
            
            if not healthy_channels:
                logger.warning(f"没有健康的Channel支持模型 {model}")
                return None
            
            # 5. 负载均衡选择
            selected_id = self._weighted_selection(healthy_channels)
            return self.channels.get(selected_id)
            
        except Exception as e:
            logger.error(f"Channel选择失败: {e}")
            return None
    
    def _get_channels_for_model(self, model: str) -> List[int]:
        """获取支持指定模型的Channel列表"""
        return self.model_to_channels.get(model, [])
    
    def _weighted_selection(self, channel_ids: List[int]) -> int:
        """
        加权随机选择算法
        
        Args:
            channel_ids: Channel ID列表
            
        Returns:
            int: 选中的Channel ID
        """
        if not channel_ids:
            raise ValueError("没有可用的Channel")
        
        if len(channel_ids) == 1:
            return channel_ids[0]
        
        # 计算权重
        weights = []
        for ch_id in channel_ids:
            channel = self.channels[ch_id]
            metrics = self.channel_metrics.get(ch_id)
            
            # 基础权重
            weight = channel.weight
            
            # 基于性能调整权重
            if metrics:
                # 响应时间越短权重越高
                if metrics.response_time > 0:
                    weight *= (1000 / max(metrics.response_time, 100))
                
                # 成功率越高权重越高
                weight *= metrics.success_rate
                
                # 优先级调整
                weight *= (1 + channel.priority / 100)
            
            weights.append(max(weight, 1))  # 确保权重不为0
        
        # 加权随机选择
        total_weight = sum(weights)
        if total_weight <= 0:
            return random.choice(channel_ids)
        
        rand_weight = random.uniform(0, total_weight)
        current_weight = 0
        
        for i, weight in enumerate(weights):
            current_weight += weight
            if rand_weight <= current_weight:
                return channel_ids[i]
        
        return channel_ids[-1]
    
    def _is_channel_healthy(self, channel_id: int) -> bool:
        """
        检查Channel健康状态
        
        Args:
            channel_id: Channel ID
            
        Returns:
            bool: 是否健康
        """
        channel = self.channels.get(channel_id)
        if not channel or channel.status != ChannelStatus.ACTIVE:
            return False
        
        metrics = self.channel_metrics.get(channel_id)
        if not metrics:
            return True  # 新Channel默认为健康
        
        # 成功率检查
        if metrics.success_rate < 0.8:
            return False
        
        # 最近错误检查
        if metrics.last_error and metrics.last_success:
            if metrics.last_error > metrics.last_success:
                time_since_error = time.time() - metrics.last_error
                if time_since_error < 300:  # 5分钟内有错误
                    return False
        
        return True
    
    async def _health_check_worker(self):
        """健康检查工作协程"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                tasks = []
                for channel_id in self.channels.keys():
                    task = asyncio.create_task(
                        self._check_channel_health(channel_id)
                    )
                    tasks.append(task)
                
                # 并行检查所有Channel
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
            except Exception as e:
                logger.error(f"健康检查异常: {e}")
    
    async def _check_channel_health(self, channel_id: int):
        """
        检查单个Channel健康状态
        
        Args:
            channel_id: Channel ID
        """
        channel = self.channels.get(channel_id)
        if not channel:
            return
        
        try:
            start_time = time.time()
            
            # 发送测试请求
            provider = provider_registry.get_provider(channel.provider_id)
            is_healthy = await provider.validate_provider_credentials(
                channel.credentials
            )
            
            response_time = (time.time() - start_time) * 1000  # 毫秒
            
            # 更新指标
            self._update_channel_metrics(
                channel_id, 
                response_time, 
                is_healthy
            )
            
            if is_healthy:
                logger.debug(f"Channel {channel.name} 健康检查通过")
            else:
                logger.warning(f"Channel {channel.name} 健康检查失败")
                
        except Exception as e:
            logger.error(f"Channel {channel.name} 健康检查异常: {e}")
            self._update_channel_metrics(channel_id, 0, False)
    
    def _update_channel_metrics(self, channel_id: int, response_time: float, success: bool):
        """
        更新Channel性能指标
        
        Args:
            channel_id: Channel ID
            response_time: 响应时间（毫秒）
            success: 是否成功
        """
        if channel_id not in self.channel_metrics:
            self._initialize_channel_metrics(channel_id)
        
        metrics = self.channel_metrics[channel_id]
        
        # 更新响应时间 (移动平均)
        if response_time > 0:
            if metrics.response_time > 0:
                metrics.response_time = 0.7 * metrics.response_time + 0.3 * response_time
            else:
                metrics.response_time = response_time
        
        # 更新计数
        metrics.request_count += 1
        
        if success:
            metrics.last_success = time.time()
            metrics.health_status = ChannelHealth.HEALTHY
        else:
            metrics.error_count += 1
            metrics.last_error = time.time()
            metrics.health_status = ChannelHealth.UNHEALTHY
        
        # 更新成功率
        if metrics.request_count > 0:
            metrics.success_rate = (metrics.request_count - metrics.error_count) / metrics.request_count
    
    def get_channel_status(self, tenant_id: str) -> Dict[int, ChannelStatusResponse]:
        """
        获取租户的Channel状态
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            Dict[int, ChannelStatusResponse]: Channel状态字典
        """
        status = {}
        for channel_id, channel in self.channels.items():
            if channel.tenant_id != tenant_id:
                continue
                
            metrics = self.channel_metrics.get(channel_id)
            status[channel_id] = ChannelStatusResponse(
                id=channel.id,
                name=channel.name,
                provider=channel.provider_id,
                status=channel.status,
                health=metrics.health_status if metrics else ChannelHealth.UNKNOWN,
                response_time=metrics.response_time if metrics else 0,
                success_rate=metrics.success_rate if metrics else 1.0,
                request_count=metrics.request_count if metrics else 0,
                error_count=metrics.error_count if metrics else 0,
                last_check=time.strftime('%Y-%m-%dT%H:%M:%SZ')
            )
        
        return status
    
    def list_tenant_channels(self, tenant_id: str) -> List[ChannelResponse]:
        """
        列出租户的所有Channel
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[ChannelResponse]: Channel列表
        """
        channels = []
        for channel in self.channels.values():
            if channel.tenant_id != tenant_id:
                continue
            
            # 获取供应商名称
            provider_config = provider_registry.get_provider_config(channel.provider_id)
            provider_name = provider_config.name if provider_config else channel.provider_id
            
            # 获取健康状态
            metrics = self.channel_metrics.get(channel.id)
            health_status = metrics.health_status if metrics else ChannelHealth.UNKNOWN
            
            channel_response = ChannelResponse(
                id=channel.id,
                name=channel.name,
                provider_id=channel.provider_id,
                provider_name=provider_name,
                base_url=channel.base_url,
                models=channel.models,
                status=channel.status,
                health=health_status,
                priority=channel.priority,
                weight=channel.weight,
                max_requests_per_minute=channel.max_requests_per_minute,
                created_at=channel.created_at or "",
                updated_at=channel.updated_at or ""
            )
            channels.append(channel_response)
        
        return channels
    
    def get_channel(self, channel_id: int) -> Optional[Channel]:
        """获取指定的Channel"""
        return self.channels.get(channel_id)
    
    async def update_channel(
        self, 
        channel_id: int, 
        update_data: Dict, 
        tenant_id: str
    ) -> bool:
        """
        更新Channel配置
        
        Args:
            channel_id: Channel ID
            update_data: 更新数据
            tenant_id: 租户ID
            
        Returns:
            bool: 更新是否成功
        """
        try:
            channel = self.channels.get(channel_id)
            if not channel or channel.tenant_id != tenant_id:
                return False
            
            # 更新字段
            if 'name' in update_data:
                channel.name = update_data['name']
            if 'base_url' in update_data:
                channel.base_url = update_data['base_url']
            if 'credentials' in update_data:
                # 验证新凭证
                provider = provider_registry.get_provider(channel.provider_id)
                if provider:
                    is_valid = await provider.validate_provider_credentials(update_data['credentials'])
                    if is_valid:
                        channel.credentials = update_data['credentials']
                    else:
                        raise ValueError("凭证验证失败")
            if 'models' in update_data:
                channel.models = update_data['models']
                self._update_model_mapping(channel)
            if 'status' in update_data:
                channel.status = ChannelStatus(update_data['status'])
            if 'priority' in update_data:
                channel.priority = update_data['priority']
            if 'weight' in update_data:
                channel.weight = update_data['weight']
            if 'max_requests_per_minute' in update_data:
                channel.max_requests_per_minute = update_data['max_requests_per_minute']
            
            channel.updated_at = time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            logger.info(f"Channel {channel_id} 更新成功")
            return True
            
        except Exception as e:
            logger.error(f"更新Channel失败: {e}")
            return False
    
    async def delete_channel(self, channel_id: int, tenant_id: str) -> bool:
        """
        删除Channel
        
        Args:
            channel_id: Channel ID
            tenant_id: 租户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            channel = self.channels.get(channel_id)
            if not channel or channel.tenant_id != tenant_id:
                return False
            
            # 从映射中移除
            for model in channel.models:
                if model in self.model_to_channels:
                    if channel_id in self.model_to_channels[model]:
                        self.model_to_channels[model].remove(channel_id)
                    if not self.model_to_channels[model]:
                        del self.model_to_channels[model]
            
            # 删除Channel和指标
            del self.channels[channel_id]
            if channel_id in self.channel_metrics:
                del self.channel_metrics[channel_id]
            
            logger.info(f"Channel {channel_id} 删除成功")
            return True
            
        except Exception as e:
            logger.error(f"删除Channel失败: {e}")
            return False


# 全局Channel管理器实例
channel_manager = ChannelManager()