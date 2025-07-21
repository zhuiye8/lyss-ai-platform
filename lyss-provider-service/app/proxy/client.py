"""
AI供应商API客户端

提供统一的HTTP客户端接口，用于与各种AI供应商API进行通信。
支持异步请求、错误处理、重试机制和超时控制。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, AsyncGenerator, List
from aiohttp import ClientSession, ClientTimeout, ClientError, ClientResponseError
from aiohttp.client_exceptions import ServerTimeoutError, ClientConnectorError

from ..models.database import ChannelTable
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ProviderClient:
    """AI供应商API客户端类"""
    
    def __init__(self):
        self._session: Optional[ClientSession] = None
        self._timeout = ClientTimeout(
            total=settings.default_provider_timeout,
            connect=10,
            sock_read=settings.default_provider_timeout - 10
        )
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    async def start(self):
        """启动HTTP客户端"""
        if not self._session:
            self._session = ClientSession(
                timeout=self._timeout,
                headers={
                    "User-Agent": "Lyss-Provider-Service/1.0.0"
                }
            )
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def send_chat_request(
        self,
        channel: ChannelTable,
        request_data: Dict[str, Any],
        tenant_id: str
    ) -> Dict[str, Any]:
        """
        发送聊天完成请求
        
        Args:
            channel: 渠道配置
            request_data: 请求数据
            tenant_id: 租户ID
            
        Returns:
            Dict[str, Any]: 响应数据
            
        Raises:
            Exception: 请求失败时抛出异常
        """
        if not self._session:
            await self.start()
        
        start_time = time.time()
        request_id = f"req_{int(start_time * 1000)}"
        
        try:
            # 构建请求
            url = f"{channel.api_base}/chat/completions"
            headers = self._build_headers(channel)
            
            logger.info(f"发送聊天请求 - channel: {channel.channel_id}, model: {request_data.get('model')}, request_id: {request_id}")
            
            # 发送请求
            async with self._session.post(
                url,
                json=request_data,
                headers=headers
            ) as response:
                response_time = time.time() - start_time
                
                # 检查HTTP状态码
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"供应商API错误 - status: {response.status}, response: {error_text}")
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"供应商API返回错误: {error_text}"
                    )
                
                # 解析响应
                response_data = await response.json()
                
                logger.info(f"聊天请求成功 - channel: {channel.channel_id}, duration: {response_time:.3f}s")
                
                return response_data
                
        except ClientResponseError:
            raise
        except ServerTimeoutError as e:
            logger.error(f"请求超时 - channel: {channel.channel_id}, error: {e}")
            raise Exception(f"请求超时: {str(e)}")
        except ClientConnectorError as e:
            logger.error(f"连接失败 - channel: {channel.channel_id}, error: {e}")
            raise Exception(f"连接失败: {str(e)}")
        except ClientError as e:
            logger.error(f"客户端错误 - channel: {channel.channel_id}, error: {e}")
            raise Exception(f"客户端错误: {str(e)}")
        except Exception as e:
            logger.error(f"请求失败 - channel: {channel.channel_id}, error: {e}")
            raise
    
    async def send_stream_chat_request(
        self,
        channel: ChannelTable,
        request_data: Dict[str, Any],
        tenant_id: str
    ) -> AsyncGenerator[str, None]:
        """
        发送流式聊天完成请求
        
        Args:
            channel: 渠道配置
            request_data: 请求数据
            tenant_id: 租户ID
            
        Yields:
            str: 流式响应数据块
        """
        if not self._session:
            await self.start()
        
        start_time = time.time()
        request_id = f"stream_req_{int(start_time * 1000)}"
        
        try:
            # 构建请求
            url = f"{channel.api_base}/chat/completions"
            headers = self._build_headers(channel)
            
            # 确保启用流式响应
            request_data["stream"] = True
            
            logger.info(f"发送流式聊天请求 - channel: {channel.channel_id}, model: {request_data.get('model')}, request_id: {request_id}")
            
            # 发送流式请求
            async with self._session.post(
                url,
                json=request_data,
                headers=headers
            ) as response:
                
                # 检查HTTP状态码
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"流式请求失败 - status: {response.status}, response: {error_text}")
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"流式请求失败: {error_text}"
                    )
                
                # 处理流式响应
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    
                    # 跳过空行和注释
                    if not line_str or line_str.startswith(':'):
                        continue
                    
                    # 处理数据行
                    if line_str.startswith('data: '):
                        data_str = line_str[6:].strip()
                        
                        # 检查结束标志
                        if data_str == '[DONE]':
                            logger.info(f"流式响应完成 - channel: {channel.channel_id}, duration: {time.time() - start_time:.3f}s")
                            break
                        
                        # 返回数据块
                        yield f"data: {data_str}\n\n"
                    else:
                        # 其他格式的流式数据
                        yield f"{line_str}\n\n"
                        
        except ClientResponseError:
            raise
        except Exception as e:
            logger.error(f"流式请求失败 - channel: {channel.channel_id}, error: {e}")
            # 发送错误响应到流
            error_data = {
                "error": {
                    "message": str(e),
                    "type": "stream_error",
                    "code": "request_failed"
                }
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    async def test_connection(
        self,
        channel: ChannelTable,
        test_model: str = None
    ) -> Dict[str, Any]:
        """
        测试渠道连接
        
        Args:
            channel: 渠道配置
            test_model: 测试模型（可选）
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        if not self._session:
            await self.start()
        
        start_time = time.time()
        
        try:
            # 构建测试请求
            test_request = {
                "model": test_model or (channel.supported_models[0] if channel.supported_models else "gpt-3.5-turbo"),
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 5,
                "temperature": 0
            }
            
            url = f"{channel.api_base}/chat/completions"
            headers = self._build_headers(channel)
            
            logger.info(f"测试连接 - channel: {channel.channel_id}")
            
            # 发送测试请求
            async with self._session.post(
                url,
                json=test_request,
                headers=headers,
                timeout=ClientTimeout(total=10)  # 测试请求使用较短超时
            ) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    response_data = await response.json()
                    return {
                        "success": True,
                        "response_time": round(response_time * 1000, 2),
                        "model": test_request["model"],
                        "message": "连接测试成功"
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "response_time": round(response_time * 1000, 2),
                        "error": f"HTTP {response.status}: {error_text}",
                        "message": "连接测试失败"
                    }
                    
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"连接测试失败 - channel: {channel.channel_id}, error: {e}")
            return {
                "success": False,
                "response_time": round(response_time * 1000, 2),
                "error": str(e),
                "message": "连接测试失败"
            }
    
    async def get_models(self, channel: ChannelTable) -> Dict[str, Any]:
        """
        获取供应商支持的模型列表
        
        Args:
            channel: 渠道配置
            
        Returns:
            Dict[str, Any]: 模型列表响应
        """
        if not self._session:
            await self.start()
        
        try:
            url = f"{channel.api_base}/models"
            headers = self._build_headers(channel)
            
            async with self._session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"获取模型列表失败: HTTP {response.status} - {error_text}")
                    
        except Exception as e:
            logger.error(f"获取模型列表失败 - channel: {channel.channel_id}, error: {e}")
            raise
    
    def _build_headers(self, channel: ChannelTable) -> Dict[str, str]:
        """
        构建请求头
        
        Args:
            channel: 渠道配置
            
        Returns:
            Dict[str, str]: 请求头字典
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Lyss-Provider-Service/1.0.0"
        }
        
        # 根据供应商类型添加认证头
        provider_id = channel.provider_id.lower()
        
        if provider_id in ["openai", "azure-openai"]:
            # OpenAI和Azure OpenAI使用Bearer token
            api_key = self._decrypt_credentials(channel.encrypted_credentials)
            headers["Authorization"] = f"Bearer {api_key}"
            
        elif provider_id == "anthropic":
            # Anthropic使用x-api-key
            api_key = self._decrypt_credentials(channel.encrypted_credentials)
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
            
        elif provider_id == "google":
            # Google使用API key参数或Bearer token
            api_key = self._decrypt_credentials(channel.encrypted_credentials)
            headers["Authorization"] = f"Bearer {api_key}"
            
        elif provider_id == "deepseek":
            # DeepSeek使用Bearer token
            api_key = self._decrypt_credentials(channel.encrypted_credentials)
            headers["Authorization"] = f"Bearer {api_key}"
            
        return headers
    
    def _decrypt_credentials(self, encrypted_credentials: str) -> str:
        """
        解密API凭证
        
        Args:
            encrypted_credentials: 加密的凭证
            
        Returns:
            str: 解密后的API密钥
        """
        try:
            # 这里应该使用实际的解密逻辑
            # 目前简化处理，假设凭证是JSON格式
            credentials = json.loads(encrypted_credentials)
            return credentials.get("api_key", "")
        except:
            # 如果解析失败，假设直接是API密钥
            return encrypted_credentials
    
    async def _retry_request(
        self,
        request_func,
        max_retries: int = None,
        delay: float = None
    ):
        """
        重试请求机制
        
        Args:
            request_func: 请求函数
            max_retries: 最大重试次数
            delay: 重试间隔
            
        Returns:
            请求结果
        """
        max_retries = max_retries or settings.default_provider_max_retries
        delay = delay or settings.default_provider_retry_delay
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await request_func()
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries:
                    logger.warning(f"请求失败，准备重试 - 尝试 {attempt + 1}/{max_retries + 1}, 错误: {e}")
                    await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
                else:
                    logger.error(f"请求重试耗尽 - 最终错误: {e}")
                    break
        
        raise last_exception


# 全局客户端实例
provider_client = ProviderClient()