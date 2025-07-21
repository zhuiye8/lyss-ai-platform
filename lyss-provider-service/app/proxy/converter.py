"""
请求响应转换器

负责将统一的OpenAI格式请求转换为各供应商的特定格式，
并将供应商响应转换回统一格式。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import time
import uuid
from typing import Dict, Any, Optional
import logging

from app.models.request import ChatRequest, ProxyRequest
from app.models.response import ChatResponse, StreamResponse, ChatChoice, ChatUsage, StreamChoice
from app.models.channel import Channel

logger = logging.getLogger(__name__)


class RequestConverter:
    """请求转换器"""
    
    async def convert_to_provider_format(
        self, 
        request: ChatRequest, 
        channel: Channel
    ) -> ProxyRequest:
        """
        将OpenAI格式请求转换为供应商特定格式
        
        Args:
            request: 统一的聊天请求
            channel: 目标Channel
            
        Returns:
            ProxyRequest: 转换后的代理请求
        """
        try:
            if channel.provider_id == "openai":
                params = await self._convert_to_openai_format(request)
            elif channel.provider_id == "anthropic":
                params = await self._convert_to_anthropic_format(request)
            else:
                raise ValueError(f"不支持的供应商: {channel.provider_id}")
            
            return ProxyRequest(
                original_request=request,
                channel_id=channel.id,
                provider_id=channel.provider_id,
                params=params
            )
            
        except Exception as e:
            logger.error(f"请求转换失败: {e}")
            raise
    
    async def _convert_to_openai_format(self, request: ChatRequest) -> Dict[str, Any]:
        """转换为OpenAI API格式"""
        params = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content} 
                for msg in request.messages
            ]
        }
        
        # 添加可选参数
        if request.temperature is not None:
            params["temperature"] = request.temperature
        if request.top_p is not None:
            params["top_p"] = request.top_p
        if request.n is not None:
            params["n"] = request.n
        if request.stream is not None:
            params["stream"] = request.stream
        if request.stop is not None:
            params["stop"] = request.stop
        if request.max_tokens is not None:
            params["max_tokens"] = request.max_tokens
        if request.presence_penalty is not None:
            params["presence_penalty"] = request.presence_penalty
        if request.frequency_penalty is not None:
            params["frequency_penalty"] = request.frequency_penalty
        if request.logit_bias is not None:
            params["logit_bias"] = request.logit_bias
        if request.user is not None:
            params["user"] = request.user
        
        return params
    
    async def _convert_to_anthropic_format(self, request: ChatRequest) -> Dict[str, Any]:
        """转换为Anthropic API格式"""
        # Anthropic使用不同的参数结构
        messages = []
        system_message = None
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        params = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1000  # Anthropic要求必须提供max_tokens
        }
        
        # 添加系统消息
        if system_message:
            params["system"] = system_message
        
        # 温度参数
        if request.temperature is not None:
            params["temperature"] = request.temperature
        
        # top_p参数
        if request.top_p is not None:
            params["top_p"] = request.top_p
        
        # 停止序列
        if request.stop is not None:
            if isinstance(request.stop, str):
                params["stop_sequences"] = [request.stop]
            else:
                params["stop_sequences"] = request.stop
        
        # 流式响应
        if request.stream:
            params["stream"] = True
        
        return params
    
    async def convert_from_provider_format(
        self, 
        response: Any, 
        channel: Channel
    ) -> ChatResponse:
        """
        将供应商响应转换为统一OpenAI格式
        
        Args:
            response: 供应商原始响应
            channel: 使用的Channel
            
        Returns:
            ChatResponse: 统一格式的响应
        """
        try:
            if channel.provider_id == "openai":
                return await self._convert_from_openai_format(response)
            elif channel.provider_id == "anthropic":
                return await self._convert_from_anthropic_format(response)
            else:
                raise ValueError(f"不支持的供应商: {channel.provider_id}")
                
        except Exception as e:
            logger.error(f"响应转换失败: {e}")
            raise
    
    async def _convert_from_openai_format(self, response: Any) -> ChatResponse:
        """从OpenAI格式转换"""
        # OpenAI响应已经是目标格式，直接返回
        return ChatResponse(
            id=response.id,
            object=response.object,
            created=response.created,
            model=response.model,
            choices=[
                ChatChoice(
                    index=choice.index,
                    message={
                        "role": choice.message.role,
                        "content": choice.message.content
                    },
                    finish_reason=choice.finish_reason
                )
                for choice in response.choices
            ],
            usage=ChatUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens
            )
        )
    
    async def _convert_from_anthropic_format(self, response: Any) -> ChatResponse:
        """从Anthropic格式转换为OpenAI格式"""
        # 生成OpenAI兼容的响应ID和时间戳
        response_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created_timestamp = int(time.time())
        
        choices = [
            ChatChoice(
                index=0,
                message={
                    "role": "assistant",
                    "content": response.content[0].text if response.content else ""
                },
                finish_reason=self._map_anthropic_finish_reason(response.stop_reason)
            )
        ]
        
        usage = ChatUsage(
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            total_tokens=response.usage.input_tokens + response.usage.output_tokens
        )
        
        return ChatResponse(
            id=response_id,
            object="chat.completion",
            created=created_timestamp,
            model=response.model,
            choices=choices,
            usage=usage
        )
    
    def _map_anthropic_finish_reason(self, anthropic_reason: Optional[str]) -> Optional[str]:
        """映射Anthropic的结束原因到OpenAI格式"""
        if anthropic_reason == "end_turn":
            return "stop"
        elif anthropic_reason == "max_tokens":
            return "length"
        elif anthropic_reason == "stop_sequence":
            return "stop"
        else:
            return anthropic_reason
    
    async def convert_stream_chunk(
        self, 
        chunk: Any, 
        channel: Channel
    ) -> Optional[StreamResponse]:
        """
        转换流式响应块
        
        Args:
            chunk: 原始流式数据块
            channel: 使用的Channel
            
        Returns:
            Optional[StreamResponse]: 转换后的流式响应，None表示跳过
        """
        try:
            if channel.provider_id == "openai":
                return await self._convert_openai_stream_chunk(chunk)
            elif channel.provider_id == "anthropic":
                return await self._convert_anthropic_stream_chunk(chunk)
            else:
                return None
                
        except Exception as e:
            logger.error(f"流式数据转换失败: {e}")
            return None
    
    async def _convert_openai_stream_chunk(self, chunk: Any) -> Optional[StreamResponse]:
        """转换OpenAI流式数据块"""
        if not hasattr(chunk, 'choices') or not chunk.choices:
            return None
        
        choices = [
            StreamChoice(
                index=choice.index,
                delta=choice.delta.dict() if hasattr(choice.delta, 'dict') else choice.delta,
                finish_reason=choice.finish_reason
            )
            for choice in chunk.choices
        ]
        
        return StreamResponse(
            id=chunk.id,
            object="chat.completion.chunk",
            created=chunk.created,
            model=chunk.model,
            choices=choices
        )
    
    async def _convert_anthropic_stream_chunk(self, chunk: Any) -> Optional[StreamResponse]:
        """转换Anthropic流式数据块"""
        # Anthropic的流式响应格式需要特殊处理
        if not hasattr(chunk, 'type'):
            return None
        
        if chunk.type == "content_block_delta":
            delta = {"content": chunk.delta.text}
            choices = [
                StreamChoice(
                    index=0,
                    delta=delta,
                    finish_reason=None
                )
            ]
            
            return StreamResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
                object="chat.completion.chunk",
                created=int(time.time()),
                model=getattr(chunk, 'model', 'claude-3'),
                choices=choices
            )
        elif chunk.type == "message_stop":
            choices = [
                StreamChoice(
                    index=0,
                    delta={},
                    finish_reason="stop"
                )
            ]
            
            return StreamResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
                object="chat.completion.chunk",
                created=int(time.time()),
                model=getattr(chunk, 'model', 'claude-3'),
                choices=choices
            )
        
        return None