"""
Lyss AI Platform - AI服务集成层
功能描述: 统一的AI服务抽象层，支持多个AI供应商
作者: Claude AI Assistant
创建时间: 2025-07-09
最后更新: 2025-07-09
"""

import uuid
import json
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator, Union
from enum import Enum
from dataclasses import dataclass
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from common.models import User, AIProvider, ModelConfig, ConversationUsage
from common.database import get_async_session
from common.redis_client import CacheManager
from api_gateway.middleware.auth import get_current_tenant_id, get_current_user_id
from common.response import ResponseHelper, ErrorCode


class AIProviderType(str, Enum):
    """AI供应商类型枚举"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE_OPENAI = "azure_openai"
    COHERE = "cohere"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class MessageRole(str, Enum):
    """消息角色枚举"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


@dataclass
class AIMessage:
    """AI消息数据类"""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class AIModelConfig:
    """AI模型配置数据类"""
    model: str
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    stream: bool = False
    functions: Optional[List[Dict[str, Any]]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    response_format: Optional[Dict[str, str]] = None


@dataclass
class AIResponse:
    """AI响应数据类"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]
    system_fingerprint: Optional[str] = None
    
    @property
    def message_content(self) -> str:
        """获取消息内容"""
        if self.choices and len(self.choices) > 0:
            choice = self.choices[0]
            if "message" in choice:
                return choice["message"].get("content", "")
            elif "text" in choice:
                return choice["text"]
        return ""
    
    @property
    def total_tokens(self) -> int:
        """获取总token数"""
        return self.usage.get("total_tokens", 0)
    
    @property
    def prompt_tokens(self) -> int:
        """获取提示token数"""
        return self.usage.get("prompt_tokens", 0)
    
    @property
    def completion_tokens(self) -> int:
        """获取完成token数"""
        return self.usage.get("completion_tokens", 0)


class BaseAIProvider(ABC):
    """AI供应商基础抽象类"""
    
    def __init__(self, api_key: str, base_url: str = None, **kwargs):
        """初始化AI供应商
        
        Args:
            api_key: API密钥
            base_url: 基础URL，可选
            **kwargs: 其他配置参数
        """
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs
        self._client = None
    
    @property
    @abstractmethod
    def provider_type(self) -> AIProviderType:
        """获取供应商类型"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        pass
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[AIMessage],
        config: AIModelConfig
    ) -> AIResponse:
        """聊天完成接口"""
        pass
    
    @abstractmethod
    async def stream_chat_completion(
        self,
        messages: List[AIMessage],
        config: AIModelConfig
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天完成接口"""
        pass
    
    async def validate_model(self, model: str) -> bool:
        """验证模型是否支持"""
        return model in self.supported_models
    
    async def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """估算成本（美分）"""
        # 默认实现，子类可以重写
        # 这里使用简化的定价模型
        cost_per_1k_tokens = 0.02  # 默认每1k token 2美分
        total_tokens = prompt_tokens + completion_tokens
        return (total_tokens / 1000) * cost_per_1k_tokens
    
    async def get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(60.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
            )
        return self._client
    
    async def close(self):
        """关闭客户端连接"""
        if self._client:
            await self._client.aclose()
            self._client = None


class OpenAIProvider(BaseAIProvider):
    """OpenAI供应商实现"""
    
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.OPENAI
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k"
        ]
    
    def __init__(self, api_key: str, base_url: str = None, **kwargs):
        super().__init__(api_key, base_url or "https://api.openai.com/v1", **kwargs)
    
    async def chat_completion(
        self,
        messages: List[AIMessage],
        config: AIModelConfig
    ) -> AIResponse:
        """OpenAI聊天完成实现"""
        client = await self.get_client()
        
        # 转换消息格式
        openai_messages = []
        for msg in messages:
            openai_msg = {
                "role": msg.role.value,
                "content": msg.content
            }
            if msg.name:
                openai_msg["name"] = msg.name
            if msg.function_call:
                openai_msg["function_call"] = msg.function_call
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            openai_messages.append(openai_msg)
        
        # 构建请求数据
        request_data = {
            "model": config.model,
            "messages": openai_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "stream": False
        }
        
        # 添加可选参数
        if config.stop:
            request_data["stop"] = config.stop
        if config.functions:
            request_data["functions"] = config.functions
        if config.tools:
            request_data["tools"] = config.tools
        if config.response_format:
            request_data["response_format"] = config.response_format
        
        # 发送请求
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = await client.post(
            f"{self.base_url}/chat/completions",
            json=request_data,
            headers=headers
        )
        
        if response.status_code != 200:
            raise ValueError(f"OpenAI API错误: {response.status_code} - {response.text}")
        
        response_data = response.json()
        
        return AIResponse(
            id=response_data["id"],
            object=response_data["object"],
            created=response_data["created"],
            model=response_data["model"],
            choices=response_data["choices"],
            usage=response_data["usage"],
            system_fingerprint=response_data.get("system_fingerprint")
        )
    
    async def stream_chat_completion(
        self,
        messages: List[AIMessage],
        config: AIModelConfig
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """OpenAI流式聊天完成实现"""
        client = await self.get_client()
        
        # 转换消息格式
        openai_messages = []
        for msg in messages:
            openai_msg = {
                "role": msg.role.value,
                "content": msg.content
            }
            if msg.name:
                openai_msg["name"] = msg.name
            if msg.function_call:
                openai_msg["function_call"] = msg.function_call
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            openai_messages.append(openai_msg)
        
        # 构建请求数据
        request_data = {
            "model": config.model,
            "messages": openai_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "stream": True
        }
        
        # 添加可选参数
        if config.stop:
            request_data["stop"] = config.stop
        if config.functions:
            request_data["functions"] = config.functions
        if config.tools:
            request_data["tools"] = config.tools
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            json=request_data,
            headers=headers
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise ValueError(f"OpenAI API错误: {response.status_code} - {error_text.decode()}")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # 移除 "data: " 前缀
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data)
                        yield chunk_data
                    except json.JSONDecodeError:
                        continue
    
    async def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """估算OpenAI成本"""
        # OpenAI定价（美分/1k tokens）
        pricing = {
            "gpt-4": {"input": 3.0, "output": 6.0},
            "gpt-4-turbo": {"input": 1.0, "output": 3.0},
            "gpt-4-turbo-preview": {"input": 1.0, "output": 3.0},
            "gpt-3.5-turbo": {"input": 0.05, "output": 0.15},
            "gpt-3.5-turbo-16k": {"input": 0.3, "output": 0.4}
        }
        
        if model not in pricing:
            return await super().estimate_cost(prompt_tokens, completion_tokens, model)
        
        model_pricing = pricing[model]
        input_cost = (prompt_tokens / 1000) * model_pricing["input"]
        output_cost = (completion_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost


class AnthropicProvider(BaseAIProvider):
    """Anthropic供应商实现"""
    
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.ANTHROPIC
    
    @property
    def supported_models(self) -> List[str]:
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-instant-1.2"
        ]
    
    def __init__(self, api_key: str, base_url: str = None, **kwargs):
        super().__init__(api_key, base_url or "https://api.anthropic.com", **kwargs)
    
    async def chat_completion(
        self,
        messages: List[AIMessage],
        config: AIModelConfig
    ) -> AIResponse:
        """Anthropic聊天完成实现"""
        client = await self.get_client()
        
        # 转换消息格式 - Anthropic使用不同的格式
        anthropic_messages = []
        system_message = ""
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        # 构建请求数据
        request_data = {
            "model": config.model,
            "messages": anthropic_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": False
        }
        
        if system_message:
            request_data["system"] = system_message
        
        if config.stop:
            request_data["stop_sequences"] = config.stop
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        response = await client.post(
            f"{self.base_url}/v1/messages",
            json=request_data,
            headers=headers
        )
        
        if response.status_code != 200:
            raise ValueError(f"Anthropic API错误: {response.status_code} - {response.text}")
        
        response_data = response.json()
        
        # 转换为统一格式
        return AIResponse(
            id=response_data["id"],
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            model=response_data["model"],
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_data["content"][0]["text"]
                },
                "finish_reason": response_data["stop_reason"]
            }],
            usage={
                "prompt_tokens": response_data["usage"]["input_tokens"],
                "completion_tokens": response_data["usage"]["output_tokens"],
                "total_tokens": response_data["usage"]["input_tokens"] + response_data["usage"]["output_tokens"]
            }
        )
    
    async def stream_chat_completion(
        self,
        messages: List[AIMessage],
        config: AIModelConfig
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Anthropic流式聊天完成实现"""
        # Anthropic流式实现与OpenAI类似，但格式略有不同
        # 这里提供基础实现，实际使用时需要根据Anthropic API文档调整
        client = await self.get_client()
        
        # 转换消息格式
        anthropic_messages = []
        system_message = ""
        
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                anthropic_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
        
        request_data = {
            "model": config.model,
            "messages": anthropic_messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p,
            "stream": True
        }
        
        if system_message:
            request_data["system"] = system_message
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        async with client.stream(
            "POST",
            f"{self.base_url}/v1/messages",
            json=request_data,
            headers=headers
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise ValueError(f"Anthropic API错误: {response.status_code} - {error_text.decode()}")
            
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(data)
                        # 转换为OpenAI兼容格式
                        yield {
                            "id": chunk_data.get("id", ""),
                            "object": "chat.completion.chunk",
                            "created": int(datetime.now().timestamp()),
                            "model": chunk_data.get("model", config.model),
                            "choices": [{
                                "index": 0,
                                "delta": {
                                    "content": chunk_data.get("delta", {}).get("text", "")
                                },
                                "finish_reason": chunk_data.get("delta", {}).get("stop_reason")
                            }]
                        }
                    except json.JSONDecodeError:
                        continue


class AIProviderFactory:
    """AI供应商工厂类"""
    
    _providers = {
        AIProviderType.OPENAI: OpenAIProvider,
        AIProviderType.ANTHROPIC: AnthropicProvider,
        # 可以继续添加其他供应商
    }
    
    @classmethod
    def create_provider(
        self,
        provider_type: AIProviderType,
        api_key: str,
        base_url: str = None,
        **kwargs
    ) -> BaseAIProvider:
        """创建AI供应商实例"""
        if provider_type not in self._providers:
            raise ValueError(f"不支持的AI供应商类型: {provider_type}")
        
        provider_class = self._providers[provider_type]
        return provider_class(api_key, base_url, **kwargs)
    
    @classmethod
    def get_supported_providers(cls) -> List[AIProviderType]:
        """获取支持的供应商列表"""
        return list(cls._providers.keys())


class AIService:
    """AI服务统一管理类"""
    
    def __init__(self, db_session: AsyncSession, cache_manager: CacheManager = None):
        """初始化AI服务
        
        Args:
            db_session: 数据库会话
            cache_manager: 缓存管理器，可选
        """
        self.db_session = db_session
        self.cache_manager = cache_manager
        self._providers: Dict[str, BaseAIProvider] = {}
    
    async def get_provider(self, provider_id: str) -> BaseAIProvider:
        """获取AI供应商实例"""
        if provider_id in self._providers:
            return self._providers[provider_id]
        
        # 从数据库获取供应商配置
        provider_stmt = select(AIProvider).where(
            AIProvider.provider_id == uuid.UUID(provider_id)
        )
        provider_result = await self.db_session.execute(provider_stmt)
        provider_config = provider_result.scalar_one_or_none()
        
        if not provider_config:
            raise ValueError(f"AI供应商不存在: {provider_id}")
        
        # 创建供应商实例
        provider = AIProviderFactory.create_provider(
            provider_type=AIProviderType(provider_config.provider_type),
            api_key=provider_config.api_key_decrypted,  # 假设有解密方法
            base_url=provider_config.base_url,
            **provider_config.provider_config
        )
        
        self._providers[provider_id] = provider
        return provider
    
    async def chat_completion(
        self,
        provider_id: str,
        messages: List[AIMessage],
        config: AIModelConfig,
        user_id: str = None
    ) -> AIResponse:
        """统一聊天完成接口"""
        provider = await self.get_provider(provider_id)
        
        # 验证模型支持
        if not await provider.validate_model(config.model):
            raise ValueError(f"供应商 {provider.provider_type} 不支持模型 {config.model}")
        
        # 记录使用开始时间
        start_time = datetime.now()
        
        try:
            # 调用AI供应商
            response = await provider.chat_completion(messages, config)
            
            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # 记录使用情况
            if user_id:
                await self._record_usage(
                    user_id=user_id,
                    provider_id=provider_id,
                    model=config.model,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=response.total_tokens,
                    processing_time_ms=int(processing_time),
                    estimated_cost=await provider.estimate_cost(
                        response.prompt_tokens,
                        response.completion_tokens,
                        config.model
                    )
                )
            
            return response
        
        except Exception as e:
            # 记录错误使用情况
            if user_id:
                await self._record_usage(
                    user_id=user_id,
                    provider_id=provider_id,
                    model=config.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    estimated_cost=0,
                    error_message=str(e)
                )
            raise
    
    async def stream_chat_completion(
        self,
        provider_id: str,
        messages: List[AIMessage],
        config: AIModelConfig,
        user_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """统一流式聊天完成接口"""
        provider = await self.get_provider(provider_id)
        
        # 验证模型支持
        if not await provider.validate_model(config.model):
            raise ValueError(f"供应商 {provider.provider_type} 不支持模型 {config.model}")
        
        start_time = datetime.now()
        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0
        
        try:
            async for chunk in provider.stream_chat_completion(messages, config):
                # 统计token使用
                if "usage" in chunk:
                    usage = chunk["usage"]
                    total_tokens = usage.get("total_tokens", 0)
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                
                yield chunk
            
            # 流式完成后记录使用情况
            if user_id:
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                await self._record_usage(
                    user_id=user_id,
                    provider_id=provider_id,
                    model=config.model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    processing_time_ms=int(processing_time),
                    estimated_cost=await provider.estimate_cost(
                        prompt_tokens,
                        completion_tokens,
                        config.model
                    )
                )
        
        except Exception as e:
            # 记录错误使用情况
            if user_id:
                await self._record_usage(
                    user_id=user_id,
                    provider_id=provider_id,
                    model=config.model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    processing_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    estimated_cost=0,
                    error_message=str(e)
                )
            raise
    
    async def _record_usage(
        self,
        user_id: str,
        provider_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        processing_time_ms: int,
        estimated_cost: float,
        error_message: str = None
    ):
        """记录AI使用情况"""
        tenant_id = get_current_tenant_id()
        
        usage_record = ConversationUsage(
            user_id=uuid.UUID(user_id),
            tenant_id=uuid.UUID(tenant_id) if tenant_id else None,
            provider_id=uuid.UUID(provider_id),
            model_name=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_cents=int(estimated_cost * 100),  # 转换为分
            processing_time_ms=processing_time_ms,
            error_message=error_message,
            is_successful=error_message is None
        )
        
        self.db_session.add(usage_record)
        await self.db_session.commit()
    
    async def get_available_models(self, provider_id: str = None) -> Dict[str, List[str]]:
        """获取可用的模型列表"""
        if provider_id:
            provider = await self.get_provider(provider_id)
            return {provider.provider_type.value: provider.supported_models}
        
        # 获取所有供应商的模型
        models = {}
        for provider_type in AIProviderFactory.get_supported_providers():
            # 这里需要从数据库获取配置的供应商
            # 简化实现，直接返回支持的模型类型
            if provider_type == AIProviderType.OPENAI:
                models["openai"] = OpenAIProvider("dummy", "").supported_models
            elif provider_type == AIProviderType.ANTHROPIC:
                models["anthropic"] = AnthropicProvider("dummy", "").supported_models
        
        return models
    
    async def close(self):
        """关闭所有供应商连接"""
        for provider in self._providers.values():
            await provider.close()
        self._providers.clear()


async def get_ai_service(
    db_session: AsyncSession = None,
    cache_manager: CacheManager = None
) -> AIService:
    """获取AI服务实例
    
    Args:
        db_session: 数据库会话，可选
        cache_manager: 缓存管理器，可选
        
    Returns:
        AIService: AI服务实例
    """
    if db_session is None:
        db_session = await get_async_session().__anext__()
    
    if cache_manager is None:
        tenant_id = get_current_tenant_id()
        if tenant_id:
            cache_manager = CacheManager(tenant_id)
    
    return AIService(db_session, cache_manager)