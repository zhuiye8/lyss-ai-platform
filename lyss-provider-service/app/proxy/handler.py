"""
API透明代理请求处理器

整合负载均衡服务、配额管理、健康检查等功能，
提供完整的AI供应商API透明代理服务。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, AsyncGenerator, Dict, Any, List
from sqlalchemy.orm import Session

from ..models.schemas.proxy import (
    ChatRequest, ChatResponse, ChatStreamResponse, 
    StreamChoice, Choice, TokenUsage, ChatMessage
)
from ..models.schemas.common import StandardResponse
from ..services.load_balancer_service import LoadBalancerService
from ..services.quota_service import QuotaService
from ..services.channel_service import ChannelService
from ..repositories.metrics_repository import MetricsRepository
from ..proxy.client import provider_client
from ..core.config import get_settings
from ..core.database import get_db

logger = logging.getLogger(__name__)
settings = get_settings()


class ProxyHandler:
    """API透明代理处理器类"""
    
    def __init__(self):
        self.db: Optional[Session] = None
        self.load_balancer_service: Optional[LoadBalancerService] = None
        self.quota_service: Optional[QuotaService] = None
        self.channel_service: Optional[ChannelService] = None
        self.metrics_repo: Optional[MetricsRepository] = None
    
    def _get_services(self):
        """获取服务实例（延迟初始化）"""
        if not self.db:
            self.db = next(get_db())
            self.load_balancer_service = LoadBalancerService(self.db)
            self.quota_service = QuotaService(self.db)
            self.channel_service = ChannelService(self.db)
            self.metrics_repo = MetricsRepository(self.db)
    
    async def handle_chat_completion(
        self, 
        request: ChatRequest, 
        tenant_id: str
    ) -> ChatResponse:
        """
        处理聊天完成请求
        
        集成负载均衡选择最佳渠道、配额检查、请求转发和响应处理。
        
        Args:
            request: 聊天请求
            tenant_id: 租户ID
            
        Returns:
            ChatResponse: 聊天响应
            
        Raises:
            Exception: 处理失败时抛出异常
        """
        start_time = time.time()
        request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        
        try:
            self._get_services()
            
            # 1. 检查配额可用性
            quota_available, quota_info = self.quota_service.check_quota_availability(
                tenant_id, "daily_requests", 1.0
            )
            
            if not quota_available:
                raise Exception(f"请求频率超限: {quota_info.get('message', '配额不足')}")
            
            # 2. 使用负载均衡服务选择最佳渠道
            selected_channel = self.load_balancer_service.select_channel(
                model_name=request.model,
                tenant_id=tenant_id,
                algorithm=settings.load_balancer_algorithm
            )
            
            if not selected_channel:
                raise Exception(f"没有可用的Channel处理模型: {request.model}")
            
            logger.info(f"负载均衡选择渠道 - channel_id: {selected_channel.channel_id}, model: {request.model}")
            
            # 3. 转换请求格式并发送
            provider_request = self._convert_to_provider_format(request, selected_channel)
            
            # 4. 发送请求到供应商API
            response_data = await provider_client.send_chat_request(
                channel=selected_channel,
                request_data=provider_request,
                tenant_id=tenant_id
            )
            
            # 5. 转换响应格式
            chat_response = self._convert_to_openai_format(
                response_data, request_id, request.model, selected_channel
            )
            
            # 6. 消耗配额
            token_usage = chat_response.usage.total_tokens
            self.quota_service.consume_quota(tenant_id, "daily_requests", 1.0)
            self.quota_service.consume_quota(tenant_id, "daily_tokens", float(token_usage))
            
            # 7. 记录成功指标
            response_time = (time.time() - start_time) * 1000
            await self._record_success_metrics(
                selected_channel, response_time, token_usage, tenant_id
            )
            
            logger.info(f"聊天完成请求成功 - id: {request_id}, tokens: {token_usage}, time: {response_time:.2f}ms")
            
            return chat_response
            
        except Exception as e:
            logger.error(f"聊天完成请求失败: {e}")
            
            # 记录错误指标
            if 'selected_channel' in locals():
                await self._record_error_metrics(selected_channel, tenant_id)
            
            raise
    
    async def handle_stream_chat_completion(
        self, 
        request: ChatRequest, 
        tenant_id: str
    ) -> AsyncGenerator[str, None]:
        """
        处理流式聊天完成请求
        
        集成负载均衡、配额检查和流式响应处理。
        
        Args:
            request: 聊天请求
            tenant_id: 租户ID
            
        Yields:
            str: Server-Sent Events格式的流式响应
        """
        start_time = time.time()
        request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
        selected_channel = None
        total_tokens = 0
        
        try:
            self._get_services()
            
            # 1. 检查配额可用性
            quota_available, quota_info = self.quota_service.check_quota_availability(
                tenant_id, "daily_requests", 1.0
            )
            
            if not quota_available:
                error_data = {
                    "error": {
                        "message": f"请求频率超限: {quota_info.get('message', '配额不足')}",
                        "type": "quota_exceeded",
                        "code": "rate_limit_exceeded"
                    }
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                return
            
            # 2. 选择最佳渠道
            selected_channel = self.load_balancer_service.select_channel(
                model_name=request.model,
                tenant_id=tenant_id,
                algorithm=settings.load_balancer_algorithm
            )
            
            if not selected_channel:
                error_data = {
                    "error": {
                        "message": f"没有可用的Channel处理模型: {request.model}",
                        "type": "no_available_channel",
                        "code": "channel_unavailable"
                    }
                }
                yield f"data: {json.dumps(error_data)}\n\n"
                return
            
            logger.info(f"流式请求选择渠道 - channel_id: {selected_channel.channel_id}, model: {request.model}")
            
            # 3. 转换请求格式并发送流式请求
            provider_request = self._convert_to_provider_format(request, selected_channel)
            provider_request["stream"] = True  # 确保启用流式响应
            
            # 4. 处理流式响应
            async for chunk in provider_client.send_stream_chat_request(
                channel=selected_channel,
                request_data=provider_request,
                tenant_id=tenant_id
            ):
                if chunk:
                    # 解析流式数据块
                    if chunk.startswith("data: "):
                        data_str = chunk[6:].strip()
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            # 转换为统一格式
                            chunk_data = json.loads(data_str)
                            stream_response = self._convert_stream_chunk_to_openai_format(
                                chunk_data, request_id, request.model, selected_channel
                            )
                            
                            if stream_response:
                                # 估算token使用量
                                if (stream_response.choices and 
                                    stream_response.choices[0].delta.get("content")):
                                    content = stream_response.choices[0].delta["content"]
                                    total_tokens += len(content.split())
                                
                                yield f"data: {stream_response.json()}\n\n"
                        except json.JSONDecodeError:
                            continue
            
            # 5. 发送结束标记
            yield "data: [DONE]\n\n"
            
            # 6. 消耗配额和记录指标
            self.quota_service.consume_quota(tenant_id, "daily_requests", 1.0)
            if total_tokens > 0:
                self.quota_service.consume_quota(tenant_id, "daily_tokens", float(total_tokens))
            
            response_time = (time.time() - start_time) * 1000
            await self._record_success_metrics(
                selected_channel, response_time, total_tokens, tenant_id
            )
            
            logger.info(f"流式聊天完成成功 - id: {request_id}, tokens: {total_tokens}, time: {response_time:.2f}ms")
            
        except Exception as e:
            logger.error(f"流式请求处理失败: {e}")
            
            # 记录错误指标
            if selected_channel:
                await self._record_error_metrics(selected_channel, tenant_id)
            
            # 发送错误响应
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "stream_error",
                    "code": "processing_failed"
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    def _convert_to_provider_format(
        self, 
        request: ChatRequest, 
        channel
    ) -> Dict[str, Any]:
        """
        转换请求为供应商特定格式
        
        Args:
            request: OpenAI格式请求
            channel: 目标渠道
            
        Returns:
            Dict[str, Any]: 供应商格式请求参数
        """
        # 基础OpenAI格式（大多数供应商兼容）
        provider_request = {
            "model": request.model,
            "messages": [msg.dict() for msg in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "n": request.n,
            "stream": request.stream,
            "max_tokens": request.max_tokens,
            "presence_penalty": request.presence_penalty,
            "frequency_penalty": request.frequency_penalty
        }
        
        # 移除None值
        provider_request = {k: v for k, v in provider_request.items() if v is not None}
        
        # 根据供应商进行特殊转换
        provider_id = channel.provider_id.lower()
        
        if provider_id == "anthropic":
            # Anthropic使用不同的消息格式
            messages = provider_request["messages"]
            if messages and messages[0].get("role") == "system":
                # 将system消息提取为独立参数
                system_msg = messages.pop(0)
                provider_request["system"] = system_msg["content"]
            
            # Anthropic的max_tokens是必需的
            if not provider_request.get("max_tokens"):
                provider_request["max_tokens"] = 1000
                
        elif provider_id == "google":
            # Google Gemini的格式调整
            # 可能需要调整消息格式
            pass
            
        elif provider_id == "deepseek":
            # DeepSeek通常兼容OpenAI格式
            pass
        
        return provider_request
    
    def _convert_to_openai_format(
        self, 
        response_data: Dict[str, Any], 
        request_id: str, 
        model: str, 
        channel
    ) -> ChatResponse:
        """
        转换供应商响应为OpenAI格式
        
        Args:
            response_data: 供应商响应数据
            request_id: 请求ID
            model: 模型名称
            channel: 使用的渠道
            
        Returns:
            ChatResponse: OpenAI格式响应
        """
        provider_id = channel.provider_id.lower()
        
        if provider_id == "anthropic":
            # 转换Anthropic格式到OpenAI格式
            content = response_data.get("content", [])
            text_content = ""
            if content and isinstance(content, list):
                for item in content:
                    if item.get("type") == "text":
                        text_content += item.get("text", "")
            elif isinstance(content, str):
                text_content = content
            
            return ChatResponse(
                id=request_id,
                object="chat.completion",
                created=int(time.time()),
                model=model,
                choices=[
                    Choice(
                        index=0,
                        message=ChatMessage(
                            role="assistant",
                            content=text_content
                        ),
                        finish_reason=response_data.get("stop_reason", "stop")
                    )
                ],
                usage=TokenUsage(
                    prompt_tokens=response_data.get("usage", {}).get("input_tokens", 0),
                    completion_tokens=response_data.get("usage", {}).get("output_tokens", 0),
                    total_tokens=(
                        response_data.get("usage", {}).get("input_tokens", 0) +
                        response_data.get("usage", {}).get("output_tokens", 0)
                    )
                )
            )
        else:
            # 其他供应商通常兼容OpenAI格式
            choices = []
            for idx, choice_data in enumerate(response_data.get("choices", [])):
                message_data = choice_data.get("message", {})
                choices.append(
                    Choice(
                        index=idx,
                        message=ChatMessage(
                            role=message_data.get("role", "assistant"),
                            content=message_data.get("content", "")
                        ),
                        finish_reason=choice_data.get("finish_reason")
                    )
                )
            
            usage_data = response_data.get("usage", {})
            
            return ChatResponse(
                id=response_data.get("id", request_id),
                object="chat.completion",
                created=response_data.get("created", int(time.time())),
                model=response_data.get("model", model),
                choices=choices,
                usage=TokenUsage(
                    prompt_tokens=usage_data.get("prompt_tokens", 0),
                    completion_tokens=usage_data.get("completion_tokens", 0),
                    total_tokens=usage_data.get("total_tokens", 0)
                ),
                system_fingerprint=response_data.get("system_fingerprint")
            )
    
    def _convert_stream_chunk_to_openai_format(
        self, 
        chunk_data: Dict[str, Any], 
        request_id: str, 
        model: str, 
        channel
    ) -> Optional[ChatStreamResponse]:
        """
        转换流式响应块为OpenAI格式
        
        Args:
            chunk_data: 原始流式数据块
            request_id: 请求ID
            model: 模型名称
            channel: 使用的渠道
            
        Returns:
            Optional[ChatStreamResponse]: OpenAI格式流式响应
        """
        try:
            provider_id = channel.provider_id.lower()
            
            if provider_id == "anthropic":
                # Anthropic流式格式转换
                if chunk_data.get("type") == "content_block_delta":
                    delta_data = chunk_data.get("delta", {})
                    content = delta_data.get("text", "")
                    
                    return ChatStreamResponse(
                        id=request_id,
                        object="chat.completion.chunk",
                        created=int(time.time()),
                        model=model,
                        choices=[
                            StreamChoice(
                                index=0,
                                delta={"content": content} if content else {},
                                finish_reason=None
                            )
                        ]
                    )
                elif chunk_data.get("type") == "message_stop":
                    return ChatStreamResponse(
                        id=request_id,
                        object="chat.completion.chunk",
                        created=int(time.time()),
                        model=model,
                        choices=[
                            StreamChoice(
                                index=0,
                                delta={},
                                finish_reason="stop"
                            )
                        ]
                    )
            else:
                # 其他供应商（通常兼容OpenAI格式）
                choices = []
                for choice_data in chunk_data.get("choices", []):
                    choices.append(
                        StreamChoice(
                            index=choice_data.get("index", 0),
                            delta=choice_data.get("delta", {}),
                            finish_reason=choice_data.get("finish_reason")
                        )
                    )
                
                return ChatStreamResponse(
                    id=chunk_data.get("id", request_id),
                    object="chat.completion.chunk",
                    created=chunk_data.get("created", int(time.time())),
                    model=chunk_data.get("model", model),
                    choices=choices,
                    system_fingerprint=chunk_data.get("system_fingerprint")
                )
            
        except Exception as e:
            logger.error(f"转换流式响应块失败: {e}")
            return None
    
    async def _record_success_metrics(
        self, 
        channel, 
        response_time: float, 
        tokens_used: int, 
        tenant_id: str
    ):
        """记录成功请求指标"""
        try:
            # 记录渠道指标
            self.metrics_repo.record_channel_metric(
                channel_id=channel.channel_id,
                tenant_id=tenant_id,
                metric_type="request_success",
                metric_value=1.0,
                response_time=response_time,
                metadata={
                    "tokens_used": tokens_used,
                    "provider_id": channel.provider_id,
                    "model": channel.supported_models[0] if channel.supported_models else "unknown"
                }
            )
            
            # 记录token使用量指标
            if tokens_used > 0:
                self.metrics_repo.record_channel_metric(
                    channel_id=channel.channel_id,
                    tenant_id=tenant_id,
                    metric_type="token_usage",
                    metric_value=float(tokens_used),
                    metadata={"token_type": "total"}
                )
            
            logger.debug(f"成功指标已记录 - channel: {channel.channel_id}, tokens: {tokens_used}")
            
        except Exception as e:
            logger.error(f"记录成功指标失败: {e}")
    
    async def _record_error_metrics(self, channel, tenant_id: str):
        """记录错误请求指标"""
        try:
            self.metrics_repo.record_channel_metric(
                channel_id=channel.channel_id,
                tenant_id=tenant_id,
                metric_type="request_error",
                metric_value=1.0,
                metadata={
                    "provider_id": channel.provider_id,
                    "error_type": "processing_failed"
                }
            )
            
            logger.debug(f"错误指标已记录 - channel: {channel.channel_id}")
            
        except Exception as e:
            logger.error(f"记录错误指标失败: {e}")
    
    async def cleanup(self):
        """清理资源"""
        try:
            await provider_client.close()
            
            if self.db:
                self.db.close()
                
            logger.info("代理处理器资源清理完成")
        except Exception as e:
            logger.error(f"清理代理处理器资源失败: {e}")
    
    def get_handler_stats(self) -> Dict[str, Any]:
        """获取处理器统计信息"""
        return {
            "status": "active",
            "services": {
                "load_balancer": bool(self.load_balancer_service),
                "quota_service": bool(self.quota_service),
                "channel_service": bool(self.channel_service),
                "metrics_repo": bool(self.metrics_repo)
            },
            "client_status": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }


# 全局代理处理器实例
proxy_handler = ProxyHandler()