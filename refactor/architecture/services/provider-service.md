# Lyss Provider Service - 多供应商管理服务

## 📋 服务概述

**lyss-provider-service** 是平台的供应商管理核心服务，负责统一管理多个AI服务提供商（OpenAI、Anthropic、Google、DeepSeek等），实现供应商抽象、凭证管理、负载均衡和故障转移。基于Dify的Provider抽象层设计和One-API的Channel管理理念构建。

---

## 🎯 核心功能

### **1. 供应商抽象管理**
- **Provider注册**: 配置驱动的供应商注册机制
- **凭证验证**: 多层级凭证验证和安全存储
- **模型管理**: 统一的模型能力查询和管理
- **配额控制**: 供应商级别的配额分配和监控

### **2. Channel负载均衡**
- **智能选择**: 基于健康状态、权重和优先级的Channel选择
- **故障转移**: 自动故障检测和备用Channel切换
- **负载分散**: 请求在多个Channel间智能分发
- **实时监控**: Channel状态和性能实时监控

### **3. API透明代理**
- **统一接口**: 将所有供应商API统一为OpenAI格式
- **请求转换**: 自动转换请求格式适配不同供应商
- **响应标准化**: 统一响应格式和错误处理
- **流式支持**: 完整的流式响应代理功能

### **4. 多租户隔离**
- **凭证隔离**: 租户级别的供应商凭证管理
- **权限控制**: 细粒度的模型和供应商访问控制
- **配额分离**: 独立的租户配额管理
- **审计日志**: 完整的操作审计和追踪

---

## 🏗️ 技术架构

### **架构设计图**
```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway                          │
│                 (统一入口代理)                            │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│              Provider Service                           │
│  ┌─────────────────┬─────────────────┬─────────────────┐ │
│  │ Provider Manager │ Channel Manager │ Proxy Manager   │ │
│  │   ·供应商注册     │   ·负载均衡      │   ·请求转换      │ │
│  │   ·凭证验证      │   ·故障转移      │   ·响应标准化     │ │
│  │   ·模型管理      │   ·健康检查      │   ·流式代理      │ │
│  └─────────────────┼─────────────────┼─────────────────┘ │
└──────────────────┬─┴─────────────────┴─┬─────────────────┘
                   │                     │
    ┌──────────────▼──────────────┐ ┌───▼──────────────┐
    │     Provider Configs        │ │  Channel Status   │
    │  ·OpenAI配置                │ │  ·健康状态        │
    │  ·Anthropic配置             │ │  ·响应时间        │
    │  ·Google配置                │ │  ·成功率          │
    │  ·DeepSeek配置              │ │  ·错误统计        │
    └─────────────────────────────┘ └─────────────────┘
```

### **核心模块架构**

```python
# 服务架构概览
lyss-provider-service/
├── main.py                     # FastAPI应用入口
├── app/
│   ├── __init__.py
│   ├── core/                   # 核心配置
│   │   ├── config.py          # 服务配置
│   │   ├── security.py        # 安全配置
│   │   └── database.py        # 数据库配置
│   ├── providers/             # 供应商管理
│   │   ├── __init__.py
│   │   ├── registry.py        # 供应商注册表
│   │   ├── manager.py         # 供应商管理器
│   │   ├── validator.py       # 凭证验证器
│   │   └── configs/           # 供应商配置
│   │       ├── openai.yaml
│   │       ├── anthropic.yaml
│   │       ├── google.yaml
│   │       └── deepseek.yaml
│   ├── channels/              # Channel管理
│   │   ├── __init__.py
│   │   ├── manager.py         # Channel管理器
│   │   ├── selector.py        # Channel选择器
│   │   ├── health.py          # 健康检查
│   │   └── balancer.py        # 负载均衡器
│   ├── proxy/                 # 代理层
│   │   ├── __init__.py
│   │   ├── handler.py         # 请求处理器
│   │   ├── converter.py       # 格式转换器
│   │   ├── streaming.py       # 流式处理
│   │   └── error_mapper.py    # 错误映射
│   ├── models/                # 数据模型
│   │   ├── __init__.py
│   │   ├── provider.py        # 供应商模型
│   │   ├── channel.py         # Channel模型
│   │   └── credential.py      # 凭证模型
│   ├── api/                   # API接口
│   │   ├── __init__.py
│   │   ├── v1/               # V1版本API
│   │   │   ├── providers.py   # 供应商管理API
│   │   │   ├── channels.py    # Channel管理API
│   │   │   └── proxy.py       # 代理API
│   │   └── middleware.py      # 中间件
│   ├── services/              # 业务服务
│   │   ├── __init__.py
│   │   ├── provider_service.py # 供应商服务
│   │   ├── channel_service.py  # Channel服务
│   │   └── proxy_service.py    # 代理服务
│   └── utils/                 # 工具类
│       ├── __init__.py
│       ├── encryption.py      # 加密工具
│       ├── cache.py          # 缓存工具
│       └── monitoring.py     # 监控工具
├── config/                    # 配置文件
│   ├── provider_schemas/      # 供应商Schema
│   └── default.yaml          # 默认配置
├── tests/                     # 测试
│   ├── test_providers.py
│   ├── test_channels.py
│   └── test_proxy.py
├── requirements.txt           # 依赖
├── Dockerfile                # Docker配置
└── README.md                 # 服务文档
```

---

## 💻 核心实现

### **1. Provider抽象层**

```python
# app/providers/registry.py
from typing import Dict, List, Optional, Type
from abc import ABC, abstractmethod
import yaml
import logging
from ..models.provider import Provider, ProviderConfig
from ..models.credential import ProviderCredential

logger = logging.getLogger(__name__)

class BaseProvider(ABC):
    """供应商基类 - 借鉴Dify设计"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.provider_id = config.provider_id
        self.name = config.name
        
    @abstractmethod
    async def validate_provider_credentials(self, credentials: dict) -> bool:
        """验证供应商级别凭证"""
        pass
    
    @abstractmethod
    async def validate_model_credentials(self, model: str, credentials: dict) -> bool:
        """验证模型级别凭证"""
        pass
    
    @abstractmethod
    async def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        pass
    
    @abstractmethod
    def get_error_mapping(self) -> dict:
        """获取错误映射配置"""
        pass

class OpenAIProvider(BaseProvider):
    """OpenAI供应商实现"""
    
    async def validate_provider_credentials(self, credentials: dict) -> bool:
        """验证OpenAI API密钥"""
        try:
            import openai
            api_key = credentials.get("api_key")
            if not api_key:
                return False
            
            # 创建测试客户端
            client = openai.AsyncClient(api_key=api_key)
            
            # 发送测试请求
            response = await client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            return True
        except Exception as e:
            logger.error(f"OpenAI凭证验证失败: {e}")
            return False
    
    async def validate_model_credentials(self, model: str, credentials: dict) -> bool:
        """验证特定模型访问权限"""
        try:
            import openai
            client = openai.AsyncClient(api_key=credentials.get("api_key"))
            
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            
            return True
        except Exception as e:
            logger.error(f"模型 {model} 凭证验证失败: {e}")
            return False
    
    async def get_supported_models(self) -> List[str]:
        """获取支持的模型列表"""
        return [
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
            "gpt-4", "gpt-4-32k", "gpt-4-turbo",
            "gpt-4o", "gpt-4o-mini"
        ]
    
    def get_error_mapping(self) -> dict:
        """OpenAI错误映射"""
        import openai
        return {
            "connection_error": [openai.APIConnectionError],
            "authentication_error": [openai.AuthenticationError],
            "rate_limit_error": [openai.RateLimitError],
            "bad_request_error": [openai.BadRequestError],
            "server_error": [openai.InternalServerError],
        }

class AnthropicProvider(BaseProvider):
    """Anthropic供应商实现"""
    
    async def validate_provider_credentials(self, credentials: dict) -> bool:
        """验证Anthropic API密钥"""
        try:
            import anthropic
            api_key = credentials.get("api_key")
            if not api_key:
                return False
            
            client = anthropic.AsyncAnthropic(api_key=api_key)
            
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            
            return True
        except Exception as e:
            logger.error(f"Anthropic凭证验证失败: {e}")
            return False
    
    async def get_supported_models(self) -> List[str]:
        return [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229", 
            "claude-3-opus-20240229",
            "claude-3-5-sonnet-20241022"
        ]

class ProviderRegistry:
    """供应商注册表 - 核心管理类"""
    
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}
        
    async def initialize(self):
        """初始化注册表，加载所有供应商配置"""
        await self._load_builtin_providers()
        logger.info(f"成功加载 {len(self.providers)} 个供应商")
    
    async def _load_builtin_providers(self):
        """加载内置供应商配置"""
        builtin_providers = [
            ("openai", OpenAIProvider),
            ("anthropic", AnthropicProvider),
            # 可扩展更多供应商
        ]
        
        for provider_id, provider_class in builtin_providers:
            config_path = f"config/provider_schemas/{provider_id}.yaml"
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                config = ProviderConfig(**config_data)
                provider = provider_class(config)
                
                self.providers[provider_id] = provider
                self.provider_configs[provider_id] = config
                
                logger.info(f"成功注册供应商: {provider_id}")
                
            except Exception as e:
                logger.error(f"加载供应商 {provider_id} 失败: {e}")
    
    def get_provider(self, provider_id: str) -> Optional[BaseProvider]:
        """获取供应商实例"""
        return self.providers.get(provider_id)
    
    def list_providers(self) -> List[str]:
        """列出所有已注册的供应商"""
        return list(self.providers.keys())
    
    async def validate_credentials(self, provider_id: str, credentials: dict) -> bool:
        """验证供应商凭证"""
        provider = self.get_provider(provider_id)
        if not provider:
            return False
        
        return await provider.validate_provider_credentials(credentials)

# 全局注册表实例
provider_registry = ProviderRegistry()
```

### **2. Channel管理系统**

```python
# app/channels/manager.py
from typing import Dict, List, Optional, Tuple
import asyncio
import time
from dataclasses import dataclass
from enum import Enum
import random
import logging
from ..models.channel import Channel, ChannelStatus
from ..providers.registry import provider_registry

logger = logging.getLogger(__name__)

class ChannelHealth(Enum):
    """Channel健康状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ChannelMetrics:
    """Channel性能指标"""
    response_time: float
    success_rate: float
    request_count: int
    error_count: int
    last_success: Optional[float]
    last_error: Optional[float]

class ChannelManager:
    """Channel管理器 - 借鉴One-API设计"""
    
    def __init__(self):
        self.channels: Dict[int, Channel] = {}
        self.channel_metrics: Dict[int, ChannelMetrics] = {}
        self.model_to_channels: Dict[str, List[int]] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """初始化Channel管理器"""
        await self._load_channels()
        self._start_health_check()
        logger.info(f"Channel管理器初始化完成，共 {len(self.channels)} 个Channel")
    
    async def register_channel(self, channel_data: dict) -> int:
        """注册新Channel"""
        try:
            # 验证供应商配置
            provider = provider_registry.get_provider(channel_data["provider_id"])
            if not provider:
                raise ValueError(f"未知供应商: {channel_data['provider_id']}")
            
            # 验证凭证
            credentials = channel_data["credentials"]
            is_valid = await provider.validate_provider_credentials(credentials)
            if not is_valid:
                raise ValueError("凭证验证失败")
            
            # 创建Channel
            channel = Channel(
                id=len(self.channels) + 1,
                name=channel_data["name"],
                provider_id=channel_data["provider_id"],
                base_url=channel_data.get("base_url", ""),
                credentials=credentials,
                models=channel_data.get("models", []),
                status=ChannelStatus.ACTIVE,
                priority=channel_data.get("priority", 0),
                weight=channel_data.get("weight", 100),
                tenant_id=channel_data["tenant_id"]
            )
            
            # 注册到管理器
            self.channels[channel.id] = channel
            self._update_model_mapping(channel)
            self._initialize_channel_metrics(channel.id)
            
            logger.info(f"成功注册Channel: {channel.name} (ID: {channel.id})")
            return channel.id
            
        except Exception as e:
            logger.error(f"注册Channel失败: {e}")
            raise
    
    def select_channel(self, model: str, tenant_id: str) -> Optional[Channel]:
        """智能Channel选择 - 核心算法"""
        try:
            # 1. 获取支持该模型的Channel
            available_channels = self._get_channels_for_model(model)
            
            # 2. 过滤租户权限
            tenant_channels = [
                ch for ch in available_channels 
                if self.channels[ch].tenant_id == tenant_id
            ]
            
            # 3. 健康检查过滤
            healthy_channels = [
                ch for ch in tenant_channels
                if self._is_channel_healthy(ch)
            ]
            
            if not healthy_channels:
                logger.warning(f"没有健康的Channel支持模型 {model}")
                return None
            
            # 4. 负载均衡选择
            selected_id = self._weighted_selection(healthy_channels)
            return self.channels.get(selected_id)
            
        except Exception as e:
            logger.error(f"Channel选择失败: {e}")
            return None
    
    def _weighted_selection(self, channel_ids: List[int]) -> int:
        """加权随机选择算法"""
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
            
            weights.append(weight)
        
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
        """检查Channel健康状态"""
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
                await asyncio.gather(*tasks, return_exceptions=True)
                
            except Exception as e:
                logger.error(f"健康检查异常: {e}")
    
    async def _check_channel_health(self, channel_id: int):
        """检查单个Channel健康状态"""
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
        """更新Channel性能指标"""
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
        else:
            metrics.error_count += 1
            metrics.last_error = time.time()
        
        # 更新成功率
        metrics.success_rate = (metrics.request_count - metrics.error_count) / metrics.request_count
    
    def get_channel_status(self) -> Dict[int, dict]:
        """获取所有Channel状态"""
        status = {}
        for channel_id, channel in self.channels.items():
            metrics = self.channel_metrics.get(channel_id)
            status[channel_id] = {
                "name": channel.name,
                "provider": channel.provider_id,
                "status": channel.status.value,
                "health": "healthy" if self._is_channel_healthy(channel_id) else "unhealthy",
                "response_time": metrics.response_time if metrics else 0,
                "success_rate": metrics.success_rate if metrics else 1.0,
                "request_count": metrics.request_count if metrics else 0,
            }
        
        return status

# 全局Channel管理器实例
channel_manager = ChannelManager()
```

### **3. API透明代理**

```python
# app/proxy/handler.py
from typing import Dict, Any, Optional, Union, AsyncGenerator
import asyncio
import json
import time
import logging
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from ..channels.manager import channel_manager
from ..providers.registry import provider_registry
from .converter import RequestConverter
from .error_mapper import ErrorMapper
from ..models.request import ChatRequest, ProxyRequest
from ..models.response import ChatResponse, ProxyResponse

logger = logging.getLogger(__name__)

class ProxyHandler:
    """API透明代理处理器 - One-API风格"""
    
    def __init__(self):
        self.converter = RequestConverter()
        self.error_mapper = ErrorMapper()
        
    async def handle_chat_request(
        self, 
        request: ChatRequest, 
        tenant_id: str,
        stream: bool = False
    ) -> Union[ChatResponse, StreamingResponse]:
        """处理聊天请求 - 核心代理逻辑"""
        try:
            # 1. 选择最佳Channel
            channel = channel_manager.select_channel(request.model, tenant_id)
            if not channel:
                raise HTTPException(
                    status_code=503,
                    detail=f"没有可用的Channel支持模型 {request.model}"
                )
            
            # 2. 转换请求格式
            provider_request = await self.converter.convert_to_provider_format(
                request, channel
            )
            
            # 3. 执行代理请求
            if stream:
                return await self._handle_streaming_request(
                    provider_request, channel, tenant_id
                )
            else:
                return await self._handle_standard_request(
                    provider_request, channel, tenant_id
                )
                
        except Exception as e:
            logger.error(f"代理请求处理失败: {e}")
            
            # 尝试故障转移
            return await self._handle_failover(request, tenant_id, stream, e)
    
    async def _handle_standard_request(
        self, 
        provider_request: ProxyRequest, 
        channel, 
        tenant_id: str
    ) -> ChatResponse:
        """处理标准请求"""
        start_time = time.time()
        
        try:
            # 获取供应商处理器
            provider = provider_registry.get_provider(channel.provider_id)
            
            # 执行实际请求
            response = await self._send_provider_request(
                provider_request, channel, provider
            )
            
            # 转换响应格式
            unified_response = await self.converter.convert_from_provider_format(
                response, channel
            )
            
            # 记录成功指标
            response_time = (time.time() - start_time) * 1000
            channel_manager._update_channel_metrics(
                channel.id, response_time, True
            )
            
            return unified_response
            
        except Exception as e:
            # 记录失败指标
            channel_manager._update_channel_metrics(channel.id, 0, False)
            
            # 映射错误
            mapped_error = self.error_mapper.map_provider_error(e, channel.provider_id)
            raise HTTPException(
                status_code=mapped_error.status_code,
                detail=mapped_error.message
            )
    
    async def _handle_streaming_request(
        self,
        provider_request: ProxyRequest,
        channel,
        tenant_id: str
    ) -> StreamingResponse:
        """处理流式请求"""
        async def stream_generator() -> AsyncGenerator[str, None]:
            try:
                provider = provider_registry.get_provider(channel.provider_id)
                
                # 创建流式请求
                stream_response = await self._send_provider_stream_request(
                    provider_request, channel, provider
                )
                
                # 转换并流式输出
                async for chunk in stream_response:
                    unified_chunk = await self.converter.convert_stream_chunk(
                        chunk, channel
                    )
                    
                    # 发送SSE格式数据
                    if unified_chunk:
                        yield f"data: {json.dumps(unified_chunk, ensure_ascii=False)}\n\n"
                
                # 结束标识
                yield "data: [DONE]\n\n"
                
                # 记录成功指标
                channel_manager._update_channel_metrics(channel.id, 0, True)
                
            except Exception as e:
                logger.error(f"流式请求处理失败: {e}")
                
                # 记录失败指标
                channel_manager._update_channel_metrics(channel.id, 0, False)
                
                # 发送错误信息
                error_data = {
                    "error": {
                        "message": str(e),
                        "type": "stream_error",
                        "code": "processing_error"
                    }
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache"}
        )
    
    async def _send_provider_request(self, request: ProxyRequest, channel, provider):
        """发送供应商请求"""
        # 根据供应商类型发送请求
        if channel.provider_id == "openai":
            return await self._send_openai_request(request, channel)
        elif channel.provider_id == "anthropic":
            return await self._send_anthropic_request(request, channel)
        else:
            raise ValueError(f"不支持的供应商: {channel.provider_id}")
    
    async def _send_openai_request(self, request: ProxyRequest, channel):
        """发送OpenAI请求"""
        import openai
        
        client = openai.AsyncClient(
            api_key=channel.credentials["api_key"],
            base_url=channel.base_url or None
        )
        
        response = await client.chat.completions.create(**request.params)
        return response
    
    async def _send_anthropic_request(self, request: ProxyRequest, channel):
        """发送Anthropic请求"""
        import anthropic
        
        client = anthropic.AsyncAnthropic(
            api_key=channel.credentials["api_key"]
        )
        
        response = await client.messages.create(**request.params)
        return response
    
    async def _handle_failover(
        self,
        original_request: ChatRequest,
        tenant_id: str,
        stream: bool,
        original_error: Exception
    ):
        """故障转移处理"""
        logger.warning(f"启动故障转移，原始错误: {original_error}")
        
        # 获取备用Channel
        backup_channels = self._get_backup_channels(original_request.model, tenant_id)
        
        for channel in backup_channels[:2]:  # 最多尝试2个备用Channel
            try:
                provider_request = await self.converter.convert_to_provider_format(
                    original_request, channel
                )
                
                if stream:
                    return await self._handle_streaming_request(
                        provider_request, channel, tenant_id
                    )
                else:
                    return await self._handle_standard_request(
                        provider_request, channel, tenant_id
                    )
                    
            except Exception as e:
                logger.warning(f"备用Channel {channel.name} 也失败: {e}")
                continue
        
        # 所有Channel都失败
        raise HTTPException(
            status_code=503,
            detail="所有可用的Channel都不可用，请稍后重试"
        )
    
    def _get_backup_channels(self, model: str, tenant_id: str):
        """获取备用Channel列表"""
        available_channels = channel_manager._get_channels_for_model(model)
        
        # 过滤租户权限
        tenant_channels = [
            channel_manager.channels[ch_id] for ch_id in available_channels
            if channel_manager.channels[ch_id].tenant_id == tenant_id
        ]
        
        # 按优先级排序
        tenant_channels.sort(key=lambda ch: ch.priority, reverse=True)
        
        return tenant_channels

# 全局代理处理器实例
proxy_handler = ProxyHandler()
```

---

## 🌐 API接口设计

### **1. 供应商管理API**

```python
# app/api/v1/providers.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from ...services.provider_service import provider_service
from ...models.provider import ProviderResponse, CredentialRequest
from ...core.auth import get_current_tenant

router = APIRouter(prefix="/providers", tags=["供应商管理"])
security = HTTPBearer()

@router.get("/", response_model=List[ProviderResponse])
async def list_providers(
    tenant: dict = Depends(get_current_tenant)
):
    """获取可用供应商列表"""
    return await provider_service.list_available_providers(tenant["id"])

@router.post("/{provider_id}/credentials")
async def save_provider_credentials(
    provider_id: str,
    credentials: CredentialRequest,
    tenant: dict = Depends(get_current_tenant)
):
    """保存供应商凭证"""
    success = await provider_service.save_credentials(
        provider_id=provider_id,
        credentials=credentials.dict(),
        tenant_id=tenant["id"]
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="凭证验证失败"
        )
    
    return {"message": "凭证保存成功"}

@router.post("/{provider_id}/test")
async def test_provider_connection(
    provider_id: str,
    credentials: CredentialRequest,
    tenant: dict = Depends(get_current_tenant)
):
    """测试供应商连接"""
    result = await provider_service.test_connection(
        provider_id=provider_id,
        credentials=credentials.dict(),
        tenant_id=tenant["id"]
    )
    
    return {
        "success": result["success"],
        "message": result["message"],
        "response_time": result.get("response_time", 0)
    }

@router.get("/{provider_id}/models")
async def get_provider_models(
    provider_id: str,
    tenant: dict = Depends(get_current_tenant)
):
    """获取供应商支持的模型列表"""
    models = await provider_service.get_supported_models(
        provider_id=provider_id,
        tenant_id=tenant["id"]
    )
    
    return {"models": models}
```

### **2. Channel管理API**

```python
# app/api/v1/channels.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from ...services.channel_service import channel_service
from ...models.channel import ChannelCreateRequest, ChannelResponse
from ...core.auth import get_current_tenant

router = APIRouter(prefix="/channels", tags=["Channel管理"])

@router.get("/", response_model=List[ChannelResponse])
async def list_channels(
    tenant: dict = Depends(get_current_tenant)
):
    """获取租户的Channel列表"""
    return await channel_service.list_tenant_channels(tenant["id"])

@router.post("/", response_model=ChannelResponse)
async def create_channel(
    channel_data: ChannelCreateRequest,
    tenant: dict = Depends(get_current_tenant)
):
    """创建新Channel"""
    channel_id = await channel_service.create_channel(
        channel_data.dict(),
        tenant["id"]
    )
    
    return await channel_service.get_channel(channel_id)

@router.get("/{channel_id}")
async def get_channel(
    channel_id: int,
    tenant: dict = Depends(get_current_tenant)
):
    """获取Channel详情"""
    channel = await channel_service.get_channel(channel_id)
    
    if not channel or channel.tenant_id != tenant["id"]:
        raise HTTPException(status_code=404, detail="Channel不存在")
    
    return channel

@router.put("/{channel_id}")
async def update_channel(
    channel_id: int,
    channel_data: ChannelCreateRequest,
    tenant: dict = Depends(get_current_tenant)
):
    """更新Channel配置"""
    success = await channel_service.update_channel(
        channel_id=channel_id,
        channel_data=channel_data.dict(),
        tenant_id=tenant["id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="更新失败")
    
    return {"message": "Channel更新成功"}

@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: int,
    tenant: dict = Depends(get_current_tenant)
):
    """删除Channel"""
    success = await channel_service.delete_channel(channel_id, tenant["id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="Channel不存在")
    
    return {"message": "Channel删除成功"}

@router.get("/status/overview")
async def get_channels_status(
    tenant: dict = Depends(get_current_tenant)
):
    """获取Channel状态概览"""
    return await channel_service.get_channels_status(tenant["id"])
```

### **3. 代理API**

```python
# app/api/v1/proxy.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from ...proxy.handler import proxy_handler
from ...models.request import ChatRequest
from ...core.auth import get_current_tenant

router = APIRouter(prefix="/v1", tags=["代理API"])

@router.post("/chat/completions")
async def chat_completions(
    request: ChatRequest,
    tenant: dict = Depends(get_current_tenant)
):
    """OpenAI格式的聊天完成API"""
    return await proxy_handler.handle_chat_request(
        request=request,
        tenant_id=tenant["id"],
        stream=request.stream or False
    )

@router.post("/completions")
async def completions(
    request: dict,
    tenant: dict = Depends(get_current_tenant)
):
    """OpenAI格式的文本完成API"""
    # TODO: 实现文本完成API代理
    pass

@router.get("/models")
async def list_models(
    tenant: dict = Depends(get_current_tenant)
):
    """获取可用模型列表"""
    return await proxy_handler.list_available_models(tenant["id"])
```

---

## 🗄️ 数据模型

### **数据库表设计**

```sql
-- 供应商配置表
CREATE TABLE provider_configs (
    id SERIAL PRIMARY KEY,
    provider_id VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    config_schema JSONB NOT NULL,
    supported_models TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(provider_id)
);

-- 租户供应商凭证表
CREATE TABLE tenant_provider_credentials (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    provider_id VARCHAR(50) NOT NULL,
    encrypted_credentials TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(tenant_id, provider_id)
);

-- Channel配置表
CREATE TABLE provider_channels (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    provider_id VARCHAR(50) NOT NULL,
    base_url VARCHAR(500),
    encrypted_credentials TEXT NOT NULL,
    supported_models TEXT[],
    status VARCHAR(20) DEFAULT 'active',
    priority INTEGER DEFAULT 0,
    weight INTEGER DEFAULT 100,
    max_requests_per_minute INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_tenant_provider (tenant_id, provider_id),
    INDEX idx_status_priority (status, priority DESC)
);

-- Channel性能统计表
CREATE TABLE channel_metrics (
    id SERIAL PRIMARY KEY,
    channel_id INTEGER NOT NULL,
    date DATE NOT NULL,
    total_requests INTEGER DEFAULT 0,
    successful_requests INTEGER DEFAULT 0,
    failed_requests INTEGER DEFAULT 0,
    avg_response_time FLOAT DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(channel_id, date),
    FOREIGN KEY (channel_id) REFERENCES provider_channels(id)
);

-- 请求日志表 (可选，用于审计)
CREATE TABLE proxy_request_logs (
    id BIGSERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL,
    channel_id INTEGER NOT NULL,
    model VARCHAR(100) NOT NULL,
    request_size INTEGER,
    response_size INTEGER,
    tokens_used INTEGER,
    response_time INTEGER, -- 毫秒
    status_code INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_tenant_date (tenant_id, created_at),
    INDEX idx_channel_date (channel_id, created_at)
);
```

---

## 🔧 配置文件

### **供应商配置示例**

```yaml
# config/provider_schemas/openai.yaml
provider_id: "openai"
name: "OpenAI"
description: "OpenAI GPT系列模型"
icon: "openai.png"

# 支持的模型类型
supported_model_types:
  - "llm"

# 凭证配置Schema
credential_schema:
  fields:
    - name: "api_key"
      type: "string"
      required: true
      sensitive: true
      label: "API Key"
      placeholder: "sk-..."
      validation:
        min_length: 20
    - name: "base_url"
      type: "string"
      required: false
      label: "Base URL"
      placeholder: "https://api.openai.com/v1"
      default: "https://api.openai.com/v1"
    - name: "organization"
      type: "string" 
      required: false
      label: "Organization ID"
      placeholder: "org-..."

# 支持的模型列表
supported_models:
  - model_id: "gpt-3.5-turbo"
    name: "GPT-3.5 Turbo"
    type: "llm"
    max_tokens: 4096
    pricing:
      input: 0.0015  # per 1K tokens
      output: 0.002
  - model_id: "gpt-4"
    name: "GPT-4"
    type: "llm"
    max_tokens: 8192
    pricing:
      input: 0.03
      output: 0.06
  - model_id: "gpt-4o"
    name: "GPT-4o"
    type: "llm" 
    max_tokens: 128000
    pricing:
      input: 0.005
      output: 0.015

# 错误映射
error_mapping:
  connection_error:
    - "openai.APIConnectionError"
  authentication_error:
    - "openai.AuthenticationError"
  rate_limit_error:
    - "openai.RateLimitError"
  quota_exceeded_error:
    - "openai.PermissionDeniedError"
  model_not_found_error:
    - "openai.NotFoundError"
  bad_request_error:
    - "openai.BadRequestError"
  server_error:
    - "openai.InternalServerError"

# 默认配置
defaults:
  timeout: 30
  max_retries: 3
  retry_delay: 1
```

---

## 🚀 部署配置

### **Docker配置**

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8003

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"]
```

### **服务配置**

```yaml
# docker-compose.yml (部分)
services:
  lyss-provider-service:
    build: ./lyss-provider-service
    ports:
      - "8003:8003"
    environment:
      - DATABASE_URL=postgresql://lyss:lyss123@postgres:5432/lyss_provider
      - REDIS_URL=redis://redis:6379/2
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
```

---

## 📊 监控和日志

### **监控指标**

```python
# app/utils/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Channel性能指标
channel_requests_total = Counter(
    'channel_requests_total',
    'Channel请求总数',
    ['channel_id', 'provider', 'model', 'status']
)

channel_response_time = Histogram(
    'channel_response_time_seconds',
    'Channel响应时间',
    ['channel_id', 'provider']
)

channel_health_status = Gauge(
    'channel_health_status',
    'Channel健康状态',
    ['channel_id', 'provider']
)

# 供应商指标
provider_credentials_total = Gauge(
    'provider_credentials_total',
    '供应商凭证总数',
    ['provider', 'tenant']
)

# 请求代理指标
proxy_requests_total = Counter(
    'proxy_requests_total',
    '代理请求总数',
    ['tenant_id', 'model', 'provider', 'status']
)

proxy_tokens_used = Counter(
    'proxy_tokens_used_total',
    '代理使用Token总数',
    ['tenant_id', 'model', 'provider']
)
```

### **结构化日志**

```python
# app/utils/logger.py
import logging
import json
import time
from typing import Dict, Any

class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        
    def log_request(self, request_id: str, tenant_id: str, model: str, 
                   channel_id: int, provider: str):
        """记录请求日志"""
        self.logger.info(json.dumps({
            "event": "request_start",
            "request_id": request_id,
            "tenant_id": tenant_id,
            "model": model,
            "channel_id": channel_id,
            "provider": provider,
            "timestamp": time.time()
        }, ensure_ascii=False))
    
    def log_response(self, request_id: str, status: str, response_time: float,
                    tokens_used: int = 0, error: str = None):
        """记录响应日志"""
        log_data = {
            "event": "request_complete",
            "request_id": request_id,
            "status": status,
            "response_time": response_time,
            "tokens_used": tokens_used,
            "timestamp": time.time()
        }
        
        if error:
            log_data["error"] = error
            
        self.logger.info(json.dumps(log_data, ensure_ascii=False))
    
    def log_channel_health(self, channel_id: int, provider: str, 
                          is_healthy: bool, response_time: float = 0):
        """记录Channel健康状态"""
        self.logger.info(json.dumps({
            "event": "channel_health_check",
            "channel_id": channel_id,
            "provider": provider,
            "is_healthy": is_healthy,
            "response_time": response_time,
            "timestamp": time.time()
        }, ensure_ascii=False))

# 全局日志实例
provider_logger = StructuredLogger("provider_service")
```

---

## 🎯 总结

**lyss-provider-service** 是平台供应商管理的核心服务，通过借鉴Dify和One-API的成功设计模式，实现了：

### **核心价值**
1. **统一管理**: 所有AI供应商通过统一接口管理
2. **透明代理**: 用户只需了解标准OpenAI格式API
3. **智能路由**: 基于健康状态和性能的智能Channel选择
4. **故障容错**: 完整的故障转移和重试机制
5. **多租户隔离**: 安全的租户级凭证和权限管理

### **技术特点**
1. **配置驱动**: 新增供应商只需配置文件，无需代码变更
2. **高性能**: 异步设计，支持高并发请求处理
3. **可扩展**: 模块化架构，易于添加新供应商支持
4. **可观测**: 完整的监控指标和结构化日志
5. **高可用**: 健康检查、负载均衡和故障转移

### **开发优先级**
- 🔥 **立即开始**: 这是解决当前多供应商管理问题的关键服务
- ⚡ **关键依赖**: Auth Service和User Service的前置依赖
- 🎯 **核心价值**: 平台供应商统一管理和API代理的基础设施

该服务完成后，将为整个平台提供稳定可靠的多供应商AI服务接入能力！