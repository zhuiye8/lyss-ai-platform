"""
供应商服务

处理供应商相关的业务逻辑，包括凭证管理、连接测试、
供应商配置等功能。确保多租户数据隔离。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import time
import logging
import asyncio
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from ..repositories.provider_repository import ProviderRepository
from ..models.database import ProviderConfigTable
from ..utils.encryption import encrypt_data, decrypt_data
from ..core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ProviderService:
    """供应商服务类"""
    
    def __init__(self, db: Session):
        self.db = db
        self.provider_repo = ProviderRepository(db)
    
    def get_all_providers(self) -> List[ProviderConfigTable]:
        """
        获取所有供应商配置
        
        Returns:
            List[ProviderConfigTable]: 供应商配置列表
        """
        try:
            return self.provider_repo.get_active_providers()
        except Exception as e:
            logger.error(f"获取所有供应商失败 - 错误: {e}")
            raise
    
    def get_provider_by_id(self, provider_id: str) -> Optional[ProviderConfigTable]:
        """
        根据ID获取供应商配置
        
        Args:
            provider_id: 供应商ID
            
        Returns:
            Optional[ProviderConfigTable]: 供应商配置
        """
        try:
            return self.provider_repo.get_by_provider_id(provider_id)
        except Exception as e:
            logger.error(f"获取供应商失败 - provider_id: {provider_id}, 错误: {e}")
            raise
    
    def search_providers(self, query: str) -> List[ProviderConfigTable]:
        """
        搜索供应商
        
        Args:
            query: 搜索关键词
            
        Returns:
            List[ProviderConfigTable]: 匹配的供应商列表
        """
        try:
            return self.provider_repo.search_providers(query)
        except Exception as e:
            logger.error(f"搜索供应商失败 - query: {query}, 错误: {e}")
            raise
    
    def get_providers_by_model(self, model_name: str) -> List[ProviderConfigTable]:
        """
        根据模型名称获取支持的供应商
        
        Args:
            model_name: 模型名称
            
        Returns:
            List[ProviderConfigTable]: 支持该模型的供应商列表
        """
        try:
            return self.provider_repo.get_providers_by_model(model_name)
        except Exception as e:
            logger.error(f"根据模型获取供应商失败 - model: {model_name}, 错误: {e}")
            raise
    
    def create_provider_config(self, provider_data: Dict[str, Any]) -> ProviderConfigTable:
        """
        创建供应商配置
        
        Args:
            provider_data: 供应商配置数据
            
        Returns:
            ProviderConfigTable: 创建的供应商配置
        """
        try:
            return self.provider_repo.create(obj_in=provider_data)
        except Exception as e:
            logger.error(f"创建供应商配置失败 - 错误: {e}")
            raise
    
    def update_provider_config(
        self,
        provider_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[ProviderConfigTable]:
        """
        更新供应商配置
        
        Args:
            provider_id: 供应商ID
            update_data: 更新数据
            
        Returns:
            Optional[ProviderConfigTable]: 更新后的供应商配置
        """
        try:
            provider = self.provider_repo.get_by_provider_id(provider_id)
            if not provider:
                logger.warning(f"供应商不存在 - provider_id: {provider_id}")
                return None
            
            return self.provider_repo.update(db_obj=provider, obj_in=update_data)
        except Exception as e:
            logger.error(f"更新供应商配置失败 - provider_id: {provider_id}, 错误: {e}")
            raise
    
    def update_provider_status(self, provider_id: str, status: str) -> bool:
        """
        更新供应商状态
        
        Args:
            provider_id: 供应商ID
            status: 新状态
            
        Returns:
            bool: 是否更新成功
        """
        try:
            return self.provider_repo.update_provider_status(provider_id, status)
        except Exception as e:
            logger.error(f"更新供应商状态失败 - provider_id: {provider_id}, 错误: {e}")
            raise
    
    def delete_provider_config(self, provider_id: str) -> bool:
        """
        删除供应商配置
        
        Args:
            provider_id: 供应商ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            provider = self.provider_repo.get_by_provider_id(provider_id)
            if not provider:
                return False
            
            return self.provider_repo.delete(id=provider.id)
        except Exception as e:
            logger.error(f"删除供应商配置失败 - provider_id: {provider_id}, 错误: {e}")
            raise
    
    def add_supported_model(self, provider_id: str, model_name: str) -> bool:
        """
        为供应商添加支持的模型
        
        Args:
            provider_id: 供应商ID
            model_name: 模型名称
            
        Returns:
            bool: 是否添加成功
        """
        try:
            return self.provider_repo.add_supported_model(provider_id, model_name)
        except Exception as e:
            logger.error(f"添加支持模型失败 - provider_id: {provider_id}, model: {model_name}, 错误: {e}")
            raise
    
    def remove_supported_model(self, provider_id: str, model_name: str) -> bool:
        """
        移除供应商支持的模型
        
        Args:
            provider_id: 供应商ID
            model_name: 模型名称
            
        Returns:
            bool: 是否移除成功
        """
        try:
            return self.provider_repo.remove_supported_model(provider_id, model_name)
        except Exception as e:
            logger.error(f"移除支持模型失败 - provider_id: {provider_id}, model: {model_name}, 错误: {e}")
            raise
    
    def get_supported_models(self, provider_id: str) -> List[str]:
        """
        获取供应商支持的模型列表
        
        Args:
            provider_id: 供应商ID
            
        Returns:
            List[str]: 模型名称列表
        """
        try:
            return self.provider_repo.get_models_by_provider(provider_id)
        except Exception as e:
            logger.error(f"获取供应商模型列表失败 - provider_id: {provider_id}, 错误: {e}")
            raise
    
    def get_all_supported_models(self) -> List[str]:
        """
        获取所有供应商支持的模型列表（去重）
        
        Returns:
            List[str]: 模型名称列表
        """
        try:
            return self.provider_repo.get_all_supported_models()
        except Exception as e:
            logger.error(f"获取所有支持的模型失败 - 错误: {e}")
            raise
    
    def get_provider_statistics(self) -> Dict[str, Any]:
        """
        获取供应商统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            return self.provider_repo.get_provider_statistics()
        except Exception as e:
            logger.error(f"获取供应商统计信息失败 - 错误: {e}")
            raise
    
    async def test_provider_connection(
        self,
        provider_id: str,
        credentials: Dict[str, Any],
        test_model: str = None
    ) -> Dict[str, Any]:
        """
        测试供应商连接
        
        Args:
            provider_id: 供应商ID
            credentials: 凭证数据
            test_model: 测试模型（可选）
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        start_time = time.time()
        
        try:
            provider = self.provider_repo.get_by_provider_id(provider_id)
            if not provider:
                return {
                    "success": False,
                    "message": "供应商不存在",
                    "response_time": (time.time() - start_time) * 1000
                }
            
            # 根据供应商类型执行连接测试
            if provider_id == "openai":
                result = await self._test_openai_connection(credentials, test_model)
            elif provider_id == "anthropic":
                result = await self._test_anthropic_connection(credentials, test_model)
            elif provider_id == "google":
                result = await self._test_google_connection(credentials, test_model)
            elif provider_id == "deepseek":
                result = await self._test_deepseek_connection(credentials, test_model)
            elif provider_id == "azure-openai":
                result = await self._test_azure_openai_connection(credentials, test_model)
            else:
                result = {
                    "success": False,
                    "message": "不支持的供应商类型"
                }
            
            result["response_time"] = (time.time() - start_time) * 1000
            
            if result["success"]:
                logger.info(f"供应商连接测试成功 - provider_id: {provider_id}")
            else:
                logger.warning(f"供应商连接测试失败 - provider_id: {provider_id}, message: {result['message']}")
            
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"测试供应商连接异常 - provider_id: {provider_id}, 错误: {e}")
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}",
                "response_time": response_time
            }
    
    async def _test_openai_connection(
        self,
        credentials: Dict[str, Any],
        test_model: str = None
    ) -> Dict[str, Any]:
        """测试OpenAI连接"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return {"success": False, "message": "缺少API密钥"}
            
            model = test_model or "gpt-3.5-turbo"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 5
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "连接测试成功"}
                else:
                    error_msg = f"API调用失败: {response.status_code} - {response.text}"
                    return {"success": False, "message": error_msg}
        
        except Exception as e:
            return {"success": False, "message": f"OpenAI连接测试异常: {str(e)}"}
    
    async def _test_anthropic_connection(
        self,
        credentials: Dict[str, Any],
        test_model: str = None
    ) -> Dict[str, Any]:
        """测试Anthropic连接"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return {"success": False, "message": "缺少API密钥"}
            
            model = test_model or "claude-3-haiku-20240307"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "Content-Type": "application/json",
                        "anthropic-version": "2023-06-01"
                    },
                    json={
                        "model": model,
                        "max_tokens": 5,
                        "messages": [{"role": "user", "content": "test"}]
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "连接测试成功"}
                else:
                    error_msg = f"API调用失败: {response.status_code} - {response.text}"
                    return {"success": False, "message": error_msg}
        
        except Exception as e:
            return {"success": False, "message": f"Anthropic连接测试异常: {str(e)}"}
    
    async def _test_google_connection(
        self,
        credentials: Dict[str, Any],
        test_model: str = None
    ) -> Dict[str, Any]:
        """测试Google连接"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return {"success": False, "message": "缺少API密钥"}
            
            model = test_model or "gemini-1.5-flash"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": "test"}]}],
                        "generationConfig": {"maxOutputTokens": 5}
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "连接测试成功"}
                else:
                    error_msg = f"API调用失败: {response.status_code} - {response.text}"
                    return {"success": False, "message": error_msg}
        
        except Exception as e:
            return {"success": False, "message": f"Google连接测试异常: {str(e)}"}
    
    async def _test_deepseek_connection(
        self,
        credentials: Dict[str, Any],
        test_model: str = None
    ) -> Dict[str, Any]:
        """测试DeepSeek连接"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return {"success": False, "message": "缺少API密钥"}
            
            model = test_model or "deepseek-chat"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 5
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "连接测试成功"}
                else:
                    error_msg = f"API调用失败: {response.status_code} - {response.text}"
                    return {"success": False, "message": error_msg}
        
        except Exception as e:
            return {"success": False, "message": f"DeepSeek连接测试异常: {str(e)}"}
    
    async def _test_azure_openai_connection(
        self,
        credentials: Dict[str, Any],
        test_model: str = None
    ) -> Dict[str, Any]:
        """测试Azure OpenAI连接"""
        try:
            api_key = credentials.get("api_key")
            endpoint = credentials.get("endpoint")
            deployment_name = credentials.get("deployment_name")
            
            if not all([api_key, endpoint, deployment_name]):
                return {"success": False, "message": "缺少必要的凭证信息（api_key, endpoint, deployment_name）"}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2024-02-01",
                    headers={
                        "api-key": api_key,
                        "Content-Type": "application/json"
                    },
                    json={
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 5
                    }
                )
                
                if response.status_code == 200:
                    return {"success": True, "message": "连接测试成功"}
                else:
                    error_msg = f"API调用失败: {response.status_code} - {response.text}"
                    return {"success": False, "message": error_msg}
        
        except Exception as e:
            return {"success": False, "message": f"Azure OpenAI连接测试异常: {str(e)}"}
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """
        加密凭证数据
        
        Args:
            credentials: 凭证数据
            
        Returns:
            str: 加密后的凭证字符串
        """
        try:
            return encrypt_data(credentials)
        except Exception as e:
            logger.error(f"加密凭证失败 - 错误: {e}")
            raise
    
    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """
        解密凭证数据
        
        Args:
            encrypted_credentials: 加密的凭证字符串
            
        Returns:
            Dict[str, Any]: 解密后的凭证数据
        """
        try:
            return decrypt_data(encrypted_credentials)
        except Exception as e:
            logger.error(f"解密凭证失败 - 错误: {e}")
            raise
    
    def validate_provider_config(self, provider_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证供应商配置数据
        
        Args:
            provider_data: 供应商配置数据
            
        Returns:
            Tuple[bool, List[str]]: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查必填字段
        required_fields = ['provider_id', 'name', 'api_base', 'supported_models']
        for field in required_fields:
            if field not in provider_data or not provider_data[field]:
                errors.append(f"缺少必填字段: {field}")
        
        # 验证supported_models格式
        if 'supported_models' in provider_data:
            if not isinstance(provider_data['supported_models'], list):
                errors.append("supported_models必须是列表格式")
            elif not provider_data['supported_models']:
                errors.append("supported_models不能为空")
        
        # 验证状态值
        if 'status' in provider_data:
            valid_statuses = ['active', 'inactive', 'disabled']
            if provider_data['status'] not in valid_statuses:
                errors.append(f"状态值必须是: {', '.join(valid_statuses)}")
        
        # 验证优先级和权重
        if 'priority' in provider_data:
            try:
                priority = int(provider_data['priority'])
                if priority < 1 or priority > 10:
                    errors.append("优先级必须在1-10之间")
            except (ValueError, TypeError):
                errors.append("优先级必须是整数")
        
        if 'weight' in provider_data:
            try:
                weight = int(provider_data['weight'])
                if weight < 1 or weight > 1000:
                    errors.append("权重必须在1-1000之间")
            except (ValueError, TypeError):
                errors.append("权重必须是整数")
        
        return len(errors) == 0, errors