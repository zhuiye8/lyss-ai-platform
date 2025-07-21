"""
健康检查服务

负责监控渠道和供应商的健康状况，定期执行健康检查，
更新状态和性能指标。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import asyncio
import logging
import time
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from ..repositories.channel_repository import ChannelRepository
from ..repositories.provider_repository import ProviderRepository
from ..repositories.metrics_repository import MetricsRepository
from ..models.database import ChannelTable, ProviderConfigTable
from ..services.provider_service import ProviderService
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HealthCheckService:
    """健康检查服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.channel_repo = ChannelRepository(db)
        self.provider_repo = ProviderRepository(db)
        self.metrics_repo = MetricsRepository(db)
        self.provider_service = ProviderService(db)
        
        # 健康检查配置
        self.check_interval = settings.health_check_interval
        self.check_timeout = settings.health_check_timeout
        self.max_retries = settings.health_check_max_retries
        self.retry_delay = settings.health_check_retry_delay
    
    async def run_health_checks(self, tenant_id: str = None) -> Dict[str, Any]:
        """
        运行健康检查
        
        Args:
            tenant_id: 租户ID（可选，如果指定则只检查该租户的渠道）
            
        Returns:
            Dict[str, Any]: 健康检查结果
        """
        try:
            start_time = time.time()
            
            # 获取需要检查的渠道
            if tenant_id:
                channels = self.channel_repo.get_active_channels(tenant_id)
            else:
                channels = self.channel_repo.get_multi(status='active')
            
            logger.info(f"开始健康检查 - 渠道数量: {len(channels)}")
            
            # 并发执行健康检查
            tasks = [self._check_channel_health(channel) for channel in channels]
            check_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            healthy_count = 0
            unhealthy_count = 0
            error_count = 0
            total_response_time = 0
            
            detailed_results = []
            for i, result in enumerate(check_results):
                if isinstance(result, Exception):
                    error_count += 1
                    detailed_results.append({
                        "channel_id": channels[i].channel_id,
                        "status": "error",
                        "error": str(result)
                    })
                else:
                    detailed_results.append(result)
                    if result["is_healthy"]:
                        healthy_count += 1
                        total_response_time += result.get("response_time", 0)
                    else:
                        unhealthy_count += 1
            
            # 计算平均响应时间
            avg_response_time = (total_response_time / healthy_count) if healthy_count > 0 else 0
            
            # 执行时间
            execution_time = (time.time() - start_time) * 1000
            
            summary = {
                "tenant_id": tenant_id,
                "total_channels": len(channels),
                "healthy_channels": healthy_count,
                "unhealthy_channels": unhealthy_count,
                "error_channels": error_count,
                "avg_response_time": round(avg_response_time, 2),
                "execution_time_ms": round(execution_time, 2),
                "check_timestamp": datetime.utcnow().isoformat(),
                "detailed_results": detailed_results
            }
            
            logger.info(f"健康检查完成 - 健康: {healthy_count}, 不健康: {unhealthy_count}, 错误: {error_count}")
            
            return summary
            
        except Exception as e:
            logger.error(f"健康检查失败 - 错误: {e}")
            raise
    
    async def _check_channel_health(self, channel: ChannelTable) -> Dict[str, Any]:
        """
        检查单个渠道的健康状况
        
        Args:
            channel: 渠道对象
            
        Returns:
            Dict[str, Any]: 检查结果
        """
        start_time = time.time()
        
        try:
            # 获取供应商配置
            provider = self.provider_repo.get_by_provider_id(channel.provider_id)
            if not provider:
                return {
                    "channel_id": channel.channel_id,
                    "is_healthy": False,
                    "error": "供应商配置不存在",
                    "response_time": 0,
                    "check_time": datetime.utcnow().isoformat()
                }
            
            # 执行健康检查
            health_result = await self._perform_health_check(channel, provider)
            
            # 计算响应时间
            response_time = (time.time() - start_time) * 1000
            
            # 更新渠道状态和指标
            if health_result["success"]:
                await self._update_channel_health_metrics(
                    channel, True, response_time, health_result.get("details", {})
                )
            else:
                await self._update_channel_health_metrics(
                    channel, False, response_time, health_result.get("details", {})
                )
            
            return {
                "channel_id": channel.channel_id,
                "provider_id": channel.provider_id,
                "is_healthy": health_result["success"],
                "response_time": round(response_time, 2),
                "check_details": health_result.get("details", {}),
                "error": health_result.get("error"),
                "check_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"渠道健康检查失败 - channel_id: {channel.channel_id}, 错误: {e}")
            
            # 记录检查失败
            await self._update_channel_health_metrics(channel, False, 0, {"error": str(e)})
            
            return {
                "channel_id": channel.channel_id,
                "is_healthy": False,
                "error": str(e),
                "response_time": 0,
                "check_time": datetime.utcnow().isoformat()
            }
    
    async def _perform_health_check(
        self,
        channel: ChannelTable,
        provider: ProviderConfigTable
    ) -> Dict[str, Any]:
        """
        执行实际的健康检查
        
        Args:
            channel: 渠道对象
            provider: 供应商对象
            
        Returns:
            Dict[str, Any]: 检查结果
        """
        try:
            # 根据供应商类型执行不同的健康检查
            if provider.provider_id == "openai":
                return await self._check_openai_health(channel)
            elif provider.provider_id == "anthropic":
                return await self._check_anthropic_health(channel)
            elif provider.provider_id == "google":
                return await self._check_google_health(channel)
            elif provider.provider_id == "deepseek":
                return await self._check_deepseek_health(channel)
            elif provider.provider_id == "azure-openai":
                return await self._check_azure_openai_health(channel)
            else:
                return await self._check_generic_health(channel)
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": {"check_type": "health_check_error"}
            }
    
    async def _check_openai_health(self, channel: ChannelTable) -> Dict[str, Any]:
        """检查OpenAI渠道健康"""
        try:
            # 解密凭证
            encrypted_credentials = channel.encrypted_credentials
            if not encrypted_credentials:
                return {"success": False, "error": "缺少凭证"}
            
            credentials = self.provider_service.decrypt_credentials(encrypted_credentials)
            api_key = credentials.get("api_key")
            
            if not api_key:
                return {"success": False, "error": "缺少API密钥"}
            
            # 发送健康检查请求
            async with httpx.AsyncClient(timeout=self.check_timeout) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get("data", []))
                    return {
                        "success": True,
                        "details": {
                            "status_code": response.status_code,
                            "model_count": model_count,
                            "check_type": "models_list"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API返回错误: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
                    
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_anthropic_health(self, channel: ChannelTable) -> Dict[str, Any]:
        """检查Anthropic渠道健康"""
        try:
            encrypted_credentials = channel.encrypted_credentials
            if not encrypted_credentials:
                return {"success": False, "error": "缺少凭证"}
            
            credentials = self.provider_service.decrypt_credentials(encrypted_credentials)
            api_key = credentials.get("api_key")
            
            if not api_key:
                return {"success": False, "error": "缺少API密钥"}
            
            # 发送简单的测试请求
            async with httpx.AsyncClient(timeout=self.check_timeout) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}]
                    }
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "details": {
                            "status_code": response.status_code,
                            "check_type": "test_request"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API返回错误: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
                    
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_google_health(self, channel: ChannelTable) -> Dict[str, Any]:
        """检查Google渠道健康"""
        try:
            encrypted_credentials = channel.encrypted_credentials
            if not encrypted_credentials:
                return {"success": False, "error": "缺少凭证"}
            
            credentials = self.provider_service.decrypt_credentials(encrypted_credentials)
            api_key = credentials.get("api_key")
            
            if not api_key:
                return {"success": False, "error": "缺少API密钥"}
            
            # 发送测试请求
            async with httpx.AsyncClient(timeout=self.check_timeout) as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    model_count = len(data.get("models", []))
                    return {
                        "success": True,
                        "details": {
                            "status_code": response.status_code,
                            "model_count": model_count,
                            "check_type": "models_list"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API返回错误: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
                    
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_deepseek_health(self, channel: ChannelTable) -> Dict[str, Any]:
        """检查DeepSeek渠道健康"""
        try:
            encrypted_credentials = channel.encrypted_credentials
            if not encrypted_credentials:
                return {"success": False, "error": "缺少凭证"}
            
            credentials = self.provider_service.decrypt_credentials(encrypted_credentials)
            api_key = credentials.get("api_key")
            
            if not api_key:
                return {"success": False, "error": "缺少API密钥"}
            
            # 发送测试请求
            async with httpx.AsyncClient(timeout=self.check_timeout) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1
                    }
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "details": {
                            "status_code": response.status_code,
                            "check_type": "test_request"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API返回错误: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
                    
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_azure_openai_health(self, channel: ChannelTable) -> Dict[str, Any]:
        """检查Azure OpenAI渠道健康"""
        try:
            encrypted_credentials = channel.encrypted_credentials
            if not encrypted_credentials:
                return {"success": False, "error": "缺少凭证"}
            
            credentials = self.provider_service.decrypt_credentials(encrypted_credentials)
            api_key = credentials.get("api_key")
            endpoint = credentials.get("endpoint")
            deployment_name = credentials.get("deployment_name")
            
            if not all([api_key, endpoint, deployment_name]):
                return {"success": False, "error": "缺少必要凭证"}
            
            # 发送测试请求
            async with httpx.AsyncClient(timeout=self.check_timeout) as client:
                response = await client.post(
                    f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2024-02-01",
                    headers={
                        "api-key": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 1
                    }
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "details": {
                            "status_code": response.status_code,
                            "check_type": "test_request"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"API返回错误: {response.status_code}",
                        "details": {"status_code": response.status_code}
                    }
                    
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _check_generic_health(self, channel: ChannelTable) -> Dict[str, Any]:
        """通用渠道健康检查"""
        try:
            # 对于未知类型的供应商，进行简单的endpoint连通性检查
            endpoint = channel.api_endpoint
            
            async with httpx.AsyncClient(timeout=self.check_timeout) as client:
                response = await client.get(endpoint)
                
                # 只要能连通就认为是健康的
                return {
                    "success": response.status_code < 500,
                    "details": {
                        "status_code": response.status_code,
                        "check_type": "endpoint_connectivity"
                    }
                }
                
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _update_channel_health_metrics(
        self,
        channel: ChannelTable,
        is_healthy: bool,
        response_time: float,
        details: Dict[str, Any]
    ) -> None:
        """
        更新渠道健康指标
        
        Args:
            channel: 渠道对象
            is_healthy: 是否健康
            response_time: 响应时间
            details: 详细信息
        """
        try:
            timestamp = datetime.utcnow()
            
            # 更新渠道状态
            new_status = "active" if is_healthy else "error"
            if channel.status != new_status:
                self.channel_repo.update_channel_status(channel.channel_id, new_status)
            
            # 计算新的成功率（简单指数加权移动平均）
            alpha = 0.1  # 平滑因子
            current_success = 1.0 if is_healthy else 0.0
            new_success_rate = alpha * current_success + (1 - alpha) * channel.success_rate
            
            # 计算新的响应时间（指数加权移动平均）
            if response_time > 0:
                new_response_time = alpha * response_time + (1 - alpha) * channel.response_time
            else:
                new_response_time = channel.response_time
            
            # 计算错误率
            new_error_rate = 1.0 - new_success_rate
            
            # 更新渠道指标
            self.channel_repo.update_channel_metrics(
                channel.channel_id,
                success_rate=new_success_rate,
                response_time=new_response_time,
                error_rate=new_error_rate
            )
            
            # 记录健康检查指标到历史
            self.metrics_repo.record_channel_metric(
                channel.channel_id,
                channel.tenant_id,
                "health_check",
                1.0 if is_healthy else 0.0,
                timestamp,
                metadata=details
            )
            
            self.metrics_repo.record_channel_metric(
                channel.channel_id,
                channel.tenant_id,
                "health_check_response_time",
                response_time,
                timestamp
            )
            
        except Exception as e:
            logger.error(f"更新渠道健康指标失败 - channel_id: {channel.channel_id}, 错误: {e}")
    
    async def run_continuous_health_monitoring(self) -> None:
        """
        运行持续健康监控
        """
        logger.info("开始持续健康监控")
        
        while True:
            try:
                # 执行全局健康检查
                result = await self.run_health_checks()
                
                # 记录监控结果
                logger.info(f"健康监控完成 - 健康渠道: {result['healthy_channels']}, 不健康渠道: {result['unhealthy_channels']}")
                
                # 等待下次检查
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"持续健康监控异常 - 错误: {e}")
                # 出错后等待更短时间再重试
                await asyncio.sleep(min(self.check_interval, 60))
    
    def get_health_report(
        self,
        tenant_id: str = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        生成健康报告
        
        Args:
            tenant_id: 租户ID（可选）
            hours: 时间范围（小时）
            
        Returns:
            Dict[str, Any]: 健康报告
        """
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # 获取渠道列表
            if tenant_id:
                channels = self.channel_repo.get_multi(tenant_id=tenant_id)
            else:
                channels = self.channel_repo.get_multi()
            
            # 收集每个渠道的健康数据
            channel_reports = []
            for channel in channels:
                health_metrics = self.metrics_repo.get_channel_health_metrics(
                    channel.channel_id, hours
                )
                
                channel_report = {
                    "channel_id": channel.channel_id,
                    "provider_id": channel.provider_id,
                    "tenant_id": channel.tenant_id,
                    "status": channel.status,
                    "current_metrics": {
                        "success_rate": channel.success_rate,
                        "response_time": channel.response_time,
                        "error_rate": channel.error_rate
                    },
                    "historical_metrics": health_metrics
                }
                channel_reports.append(channel_report)
            
            # 全局统计
            total_channels = len(channels)
            healthy_channels = len([ch for ch in channels if ch.status == "active"])
            unhealthy_channels = total_channels - healthy_channels
            
            avg_success_rate = sum(ch.success_rate for ch in channels) / total_channels if total_channels > 0 else 0
            avg_response_time = sum(ch.response_time for ch in channels) / total_channels if total_channels > 0 else 0
            
            return {
                "tenant_id": tenant_id,
                "time_range_hours": hours,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "summary": {
                    "total_channels": total_channels,
                    "healthy_channels": healthy_channels,
                    "unhealthy_channels": unhealthy_channels,
                    "health_percentage": round((healthy_channels / total_channels * 100) if total_channels > 0 else 0, 2),
                    "avg_success_rate": round(avg_success_rate, 4),
                    "avg_response_time": round(avg_response_time, 2)
                },
                "channel_details": channel_reports,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"生成健康报告失败 - tenant_id: {tenant_id}, 错误: {e}")
            raise