"""
代理请求处理器

负责处理API代理请求的核心逻辑，包括Channel选择、
请求转发、故障转移和响应处理。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import asyncio
import time
import httpx
import logging
from typing import Optional, AsyncGenerator, Dict, Any

from app.models.request import ChatRequest, ProxyRequest
from app.models.response import ChatResponse, StreamResponse, ProxyResponse, ErrorResponse
from app.models.channel import Channel
from app.channels.manager import channel_manager
from app.proxy.converter import RequestConverter
from app.providers.registry import provider_registry

logger = logging.getLogger(__name__)


class ProxyHandler:
    """代理请求处理器"""
    
    def __init__(self):
        self.request_converter = RequestConverter()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def handle_chat_completion(
        self, 
        request: ChatRequest, 
        tenant_id: str
    ) -> ChatResponse:
        """
        处理聊天完成请求
        
        Args:
            request: 聊天请求
            tenant_id: 租户ID
            
        Returns:
            ChatResponse: 聊天响应
            
        Raises:
            ValueError: 没有可用的Channel
            Exception: 所有Channel都失败
        """
        start_time = time.time()
        
        try:
            # 选择最佳Channel
            channel = channel_manager.select_channel(request.model, tenant_id)
            if not channel:
                raise ValueError(f"没有可用的Channel处理模型: {request.model}")
            
            logger.info(f"为模型 {request.model} 选择Channel: {channel.name} ({channel.provider_id})")
            
            # 转换请求格式
            proxy_request = await self.request_converter.convert_to_provider_format(
                request, channel
            )
            
            # 发送请求到供应商
            response = await self._send_request(proxy_request, channel)
            
            # 转换响应格式
            chat_response = await self.request_converter.convert_from_provider_format(
                response, channel
            )
            
            # 记录成功指标
            response_time = (time.time() - start_time) * 1000
            await self._record_success_metrics(channel.id, response_time, chat_response.usage.total_tokens)
            
            return chat_response
            
        except Exception as e:
            logger.error(f"请求处理失败: {e}")
            
            # 尝试故障转移
            if 'channel' in locals():
                await self._record_error_metrics(channel.id)
                fallback_response = await self._try_fallback(request, tenant_id, exclude_channel_id=channel.id)
                if fallback_response:
                    return fallback_response
            
            # 如果所有尝试都失败，抛出异常
            raise Exception(f"所有Channel都失败了: {str(e)}")
    
    async def handle_stream_chat_completion(
        self, 
        request: ChatRequest, 
        tenant_id: str
    ) -> AsyncGenerator[str, None]:
        """
        处理流式聊天完成请求
        
        Args:
            request: 聊天请求
            tenant_id: 租户ID
            
        Yields:
            str: Server-Sent Events格式的流式响应
        """
        start_time = time.time()
        channel = None
        
        try:
            # 选择最佳Channel
            channel = channel_manager.select_channel(request.model, tenant_id)
            if not channel:
                error_data = {
                    "error": {
                        "message": f"没有可用的Channel处理模型: {request.model}",
                        "type": "no_available_channel",
                        "code": "channel_unavailable"
                    }
                }
                yield f"data: {ErrorResponse(**error_data).json()}\n\n"
                return
            
            logger.info(f"为流式请求选择Channel: {channel.name} ({channel.provider_id})")
            
            # 转换请求格式
            request.stream = True  # 确保启用流式响应
            proxy_request = await self.request_converter.convert_to_provider_format(
                request, channel
            )
            
            # 发送流式请求
            total_tokens = 0
            async for chunk_data in self._send_stream_request(proxy_request, channel):
                if chunk_data:
                    # 转换流式响应块
                    stream_response = await self.request_converter.convert_stream_chunk(
                        chunk_data, channel
                    )
                    
                    if stream_response:
                        # 估算token使用量（简单实现）
                        if stream_response.choices and stream_response.choices[0].delta.get("content"):
                            content = stream_response.choices[0].delta["content"]
                            total_tokens += len(content.split())  # 粗略估算
                        
                        # 发送SSE格式数据
                        yield f"data: {stream_response.json()}\n\n"
            
            # 发送结束标记
            yield "data: [DONE]\n\n"
            
            # 记录成功指标
            response_time = (time.time() - start_time) * 1000
            await self._record_success_metrics(channel.id, response_time, total_tokens)
            
        except Exception as e:
            logger.error(f"流式请求处理失败: {e}")
            
            # 记录错误指标
            if channel:
                await self._record_error_metrics(channel.id)
            
            # 发送错误响应
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "stream_error",
                    "code": "processing_failed"
                }
            }
            yield f"data: {ErrorResponse(**error_data).json()}\n\n"
    
    async def _send_request(self, proxy_request: ProxyRequest, channel: Channel) -> Any:
        """
        发送请求到供应商API
        
        Args:
            proxy_request: 代理请求
            channel: 目标Channel
            
        Returns:
            Any: 供应商API响应
        """
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Lyss-Provider-Service/1.0"
        }
        
        # 添加认证头
        provider = provider_registry.get_provider(channel.provider_id)
        if provider:
            auth_headers = await provider.get_auth_headers(channel.credentials)
            headers.update(auth_headers)
        
        # 添加自定义头
        if proxy_request.headers:
            headers.update(proxy_request.headers)
        
        # 构建请求URL
        endpoint = "/chat/completions"  # OpenAI兼容端点
        if channel.provider_id == "anthropic":
            endpoint = "/messages"  # Anthropic专用端点
        
        url = f"{channel.base_url.rstrip('/')}/v1{endpoint}"
        
        try:
            logger.debug(f"发送请求到: {url}")
            response = await self.http_client.post(
                url=url,
                headers=headers,
                json=proxy_request.params,
                timeout=30.0
            )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP错误 {e.response.status_code}: {e.response.text}")
            raise Exception(f"供应商API错误: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error(f"请求超时: {url}")
            raise Exception("请求超时")
        except Exception as e:
            logger.error(f"请求发送失败: {e}")
            raise
    
    async def _send_stream_request(
        self, 
        proxy_request: ProxyRequest, 
        channel: Channel
    ) -> AsyncGenerator[Any, None]:
        """
        发送流式请求到供应商API
        
        Args:
            proxy_request: 代理请求
            channel: 目标Channel
            
        Yields:
            Any: 流式响应数据块
        """
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "User-Agent": "Lyss-Provider-Service/1.0"
        }
        
        # 添加认证头
        provider = provider_registry.get_provider(channel.provider_id)
        if provider:
            auth_headers = await provider.get_auth_headers(channel.credentials)
            headers.update(auth_headers)
        
        # 构建请求URL
        endpoint = "/chat/completions"
        if channel.provider_id == "anthropic":
            endpoint = "/messages"
        
        url = f"{channel.base_url.rstrip('/')}/v1{endpoint}"
        
        try:
            logger.debug(f"发送流式请求到: {url}")
            
            async with self.http_client.stream(
                method="POST",
                url=url,
                headers=headers,
                json=proxy_request.params,
                timeout=60.0  # 流式请求使用更长超时
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # 去除 "data: " 前缀
                        
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            import json
                            chunk_data = json.loads(data_str)
                            yield chunk_data
                        except json.JSONDecodeError:
                            # 跳过无法解析的数据
                            continue
                            
        except httpx.HTTPStatusError as e:
            logger.error(f"流式请求HTTP错误 {e.response.status_code}: {e.response.text}")
            raise Exception(f"供应商API错误: {e.response.status_code}")
        except Exception as e:
            logger.error(f"流式请求发送失败: {e}")
            raise
    
    async def _try_fallback(
        self, 
        request: ChatRequest, 
        tenant_id: str, 
        exclude_channel_id: int
    ) -> Optional[ChatResponse]:
        """
        尝试故障转移到备用Channel
        
        Args:
            request: 原始请求
            tenant_id: 租户ID
            exclude_channel_id: 要排除的Channel ID
            
        Returns:
            Optional[ChatResponse]: 故障转移成功的响应，失败返回None
        """
        try:
            # 获取备用Channel
            fallback_channel = channel_manager.select_channel(
                request.model, 
                tenant_id, 
                exclude_ids=[exclude_channel_id]
            )
            
            if not fallback_channel:
                logger.warning("没有可用的备用Channel")
                return None
            
            logger.info(f"故障转移到备用Channel: {fallback_channel.name}")
            
            # 使用备用Channel重新发送请求
            proxy_request = await self.request_converter.convert_to_provider_format(
                request, fallback_channel
            )
            
            response = await self._send_request(proxy_request, fallback_channel)
            
            chat_response = await self.request_converter.convert_from_provider_format(
                response, fallback_channel
            )
            
            # 记录成功指标
            await self._record_success_metrics(fallback_channel.id, 0, chat_response.usage.total_tokens)
            
            return chat_response
            
        except Exception as e:
            logger.error(f"故障转移失败: {e}")
            if 'fallback_channel' in locals():
                await self._record_error_metrics(fallback_channel.id)
            return None
    
    async def _record_success_metrics(self, channel_id: int, response_time: float, tokens_used: int):
        """记录成功请求指标"""
        try:
            metrics = channel_manager.channel_metrics.get(channel_id)
            if metrics:
                metrics.request_count += 1
                metrics.response_time = (metrics.response_time + response_time) / 2  # 简单平均
                metrics.success_rate = (metrics.request_count - metrics.error_count) / metrics.request_count
                metrics.tokens_used += tokens_used
                metrics.last_used = time.time()
                
                logger.debug(f"Channel {channel_id} 成功指标已更新")
        except Exception as e:
            logger.error(f"记录成功指标失败: {e}")
    
    async def _record_error_metrics(self, channel_id: int):
        """记录错误请求指标"""
        try:
            metrics = channel_manager.channel_metrics.get(channel_id)
            if metrics:
                metrics.error_count += 1
                metrics.request_count += 1
                metrics.success_rate = (metrics.request_count - metrics.error_count) / metrics.request_count
                
                # 如果错误率过高，标记为不健康
                if metrics.success_rate < 0.8 and metrics.request_count >= 5:
                    metrics.health_status = "unhealthy"
                
                logger.debug(f"Channel {channel_id} 错误指标已更新")
        except Exception as e:
            logger.error(f"记录错误指标失败: {e}")
    
    async def cleanup(self):
        """清理资源"""
        if self.http_client:
            await self.http_client.aclose()


# 全局代理处理器实例
proxy_handler = ProxyHandler()