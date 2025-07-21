"""
供应商注册表

借鉴Dify的供应商注册模式，实现配置驱动的供应商管理。
支持动态加载供应商配置和实例创建。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from typing import Dict, List, Optional, Type
from abc import ABC, abstractmethod
import yaml
import logging
import os
from pathlib import Path

from app.models.provider import ProviderConfig, ModelInfo, CredentialField

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
            client = openai.AsyncClient(
                api_key=api_key,
                base_url=credentials.get("base_url", "https://api.openai.com/v1")
            )
            
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
            client = openai.AsyncClient(
                api_key=credentials.get("api_key"),
                base_url=credentials.get("base_url", "https://api.openai.com/v1")
            )
            
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
        try:
            import openai
            return {
                "connection_error": [openai.APIConnectionError],
                "authentication_error": [openai.AuthenticationError],
                "rate_limit_error": [openai.RateLimitError],
                "bad_request_error": [openai.BadRequestError],
                "server_error": [openai.InternalServerError],
            }
        except ImportError:
            logger.warning("OpenAI包未安装，无法获取错误映射")
            return {}


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
    
    async def validate_model_credentials(self, model: str, credentials: dict) -> bool:
        """验证特定模型访问权限"""
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=credentials.get("api_key"))
            
            response = await client.messages.create(
                model=model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            
            return True
        except Exception as e:
            logger.error(f"模型 {model} 凭证验证失败: {e}")
            return False
    
    async def get_supported_models(self) -> List[str]:
        return [
            "claude-3-haiku-20240307",
            "claude-3-sonnet-20240229", 
            "claude-3-opus-20240229",
            "claude-3-5-sonnet-20241022"
        ]
    
    def get_error_mapping(self) -> dict:
        """Anthropic错误映射"""
        try:
            import anthropic
            return {
                "connection_error": [anthropic.APIConnectionError],
                "authentication_error": [anthropic.AuthenticationError],
                "rate_limit_error": [anthropic.RateLimitError],
                "bad_request_error": [anthropic.BadRequestError],
                "server_error": [anthropic.InternalServerError],
            }
        except ImportError:
            logger.warning("Anthropic包未安装，无法获取错误映射")
            return {}


class ProviderRegistry:
    """供应商注册表 - 核心管理类"""
    
    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}
        self.provider_configs: Dict[str, ProviderConfig] = {}
        self.provider_classes: Dict[str, Type[BaseProvider]] = {
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
        }
        
    async def initialize(self):
        """初始化注册表，加载所有供应商配置"""
        await self._load_builtin_providers()
        logger.info(f"成功加载 {len(self.providers)} 个供应商")
    
    async def _load_builtin_providers(self):
        """加载内置供应商配置"""
        config_dir = Path(__file__).parent.parent.parent / "config" / "provider_schemas"
        
        for provider_id, provider_class in self.provider_classes.items():
            config_path = config_dir / f"{provider_id}.yaml"
            try:
                if not config_path.exists():
                    logger.warning(f"供应商配置文件不存在: {config_path}")
                    continue
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                # 转换配置数据为ProviderConfig对象
                config = self._parse_provider_config(config_data)
                provider = provider_class(config)
                
                self.providers[provider_id] = provider
                self.provider_configs[provider_id] = config
                
                logger.info(f"成功注册供应商: {provider_id}")
                
            except Exception as e:
                logger.error(f"加载供应商 {provider_id} 失败: {e}")
    
    def _parse_provider_config(self, config_data: dict) -> ProviderConfig:
        """解析供应商配置数据"""
        # 解析模型信息
        models = []
        for model_data in config_data.get("supported_models", []):
            model = ModelInfo(
                model_id=model_data["model_id"],
                name=model_data["name"],
                type=model_data["type"],
                max_tokens=model_data["max_tokens"],
                pricing=model_data["pricing"]
            )
            models.append(model)
        
        return ProviderConfig(
            provider_id=config_data["provider_id"],
            name=config_data["name"],
            description=config_data["description"],
            icon=config_data["icon"],
            supported_model_types=config_data["supported_model_types"],
            credential_schema=config_data["credential_schema"],
            supported_models=models,
            error_mapping=config_data["error_mapping"],
            defaults=config_data["defaults"]
        )
    
    def get_provider(self, provider_id: str) -> Optional[BaseProvider]:
        """获取供应商实例"""
        return self.providers.get(provider_id)
    
    def get_provider_config(self, provider_id: str) -> Optional[ProviderConfig]:
        """获取供应商配置"""
        return self.provider_configs.get(provider_id)
    
    def list_providers(self) -> List[str]:
        """列出所有已注册的供应商"""
        return list(self.providers.keys())
    
    def list_provider_configs(self) -> List[ProviderConfig]:
        """列出所有供应商配置"""
        return list(self.provider_configs.values())
    
    async def validate_credentials(self, provider_id: str, credentials: dict) -> bool:
        """验证供应商凭证"""
        provider = self.get_provider(provider_id)
        if not provider:
            return False
        
        return await provider.validate_provider_credentials(credentials)
    
    async def validate_model_access(self, provider_id: str, model: str, credentials: dict) -> bool:
        """验证模型访问权限"""
        provider = self.get_provider(provider_id)
        if not provider:
            return False
        
        return await provider.validate_model_credentials(model, credentials)
    
    def get_supported_models(self, provider_id: str) -> List[str]:
        """获取供应商支持的模型列表"""
        config = self.get_provider_config(provider_id)
        if not config:
            return []
        
        return [model.model_id for model in config.supported_models]
    
    def register_provider(self, provider_id: str, provider_class: Type[BaseProvider], config: ProviderConfig):
        """动态注册新供应商"""
        try:
            provider = provider_class(config)
            self.providers[provider_id] = provider
            self.provider_configs[provider_id] = config
            self.provider_classes[provider_id] = provider_class
            
            logger.info(f"动态注册供应商成功: {provider_id}")
            return True
        except Exception as e:
            logger.error(f"动态注册供应商失败: {e}")
            return False


# 全局注册表实例
provider_registry = ProviderRegistry()