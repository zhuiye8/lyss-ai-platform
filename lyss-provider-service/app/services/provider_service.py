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
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.providers.registry import provider_registry
from app.models.provider import ProviderResponse, ProviderCredentialResponse, ProviderTestResponse
from app.utils.encryption import encrypt_data, decrypt_data

logger = logging.getLogger(__name__)


class ProviderService:
    """供应商服务类"""
    
    def __init__(self):
        # 内存中的凭证缓存（实际生产中应使用Redis）
        self._credential_cache: Dict[str, Dict[str, Any]] = {}
        
    async def list_available_providers(self, tenant_id: str) -> List[ProviderResponse]:
        """
        获取可用供应商列表
        
        Args:
            tenant_id: 租户ID
            
        Returns:
            List[ProviderResponse]: 供应商列表
        """
        try:
            providers = []
            
            for config in provider_registry.list_provider_configs():
                # 检查租户是否已配置该供应商的凭证
                is_configured = await self._check_credential_configured(
                    config.provider_id, tenant_id
                )
                
                provider_response = ProviderResponse(
                    provider_id=config.provider_id,
                    name=config.name,
                    description=config.description,
                    icon=config.icon,
                    supported_models=[model.model_id for model in config.supported_models],
                    credential_schema=config.credential_schema,
                    is_configured=is_configured
                )
                providers.append(provider_response)
            
            logger.info(f"租户 {tenant_id} 获取供应商列表成功，共 {len(providers)} 个")
            return providers
            
        except Exception as e:
            logger.error(f"获取供应商列表失败: {e}")
            raise
    
    async def save_credentials(
        self, 
        provider_id: str, 
        credentials: Dict[str, Any], 
        tenant_id: str
    ) -> ProviderCredentialResponse:
        """
        保存供应商凭证
        
        Args:
            provider_id: 供应商ID
            credentials: 凭证数据
            tenant_id: 租户ID
            
        Returns:
            ProviderCredentialResponse: 保存结果
            
        Raises:
            ValueError: 凭证验证失败
        """
        try:
            # 验证凭证
            is_valid = await provider_registry.validate_credentials(provider_id, credentials)
            if not is_valid:
                raise ValueError("凭证验证失败")
            
            # 加密存储凭证（实际生产中应存储到数据库）
            encrypted_credentials = encrypt_data(credentials)
            cache_key = f"{tenant_id}:{provider_id}"
            
            self._credential_cache[cache_key] = {
                "provider_id": provider_id,
                "tenant_id": tenant_id,
                "encrypted_credentials": encrypted_credentials,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            logger.info(f"租户 {tenant_id} 保存供应商 {provider_id} 凭证成功")
            
            return ProviderCredentialResponse(
                id=f"cred_{cache_key}",
                provider_id=provider_id,
                tenant_id=tenant_id,
                status="active",
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"保存供应商凭证失败: {e}")
            raise
    
    async def test_connection(
        self, 
        provider_id: str, 
        credentials: Dict[str, Any], 
        tenant_id: str
    ) -> ProviderTestResponse:
        """
        测试供应商连接
        
        Args:
            provider_id: 供应商ID
            credentials: 测试凭证
            tenant_id: 租户ID
            
        Returns:
            ProviderTestResponse: 测试结果
        """
        start_time = time.time()
        
        try:
            # 验证凭证
            is_valid = await provider_registry.validate_credentials(provider_id, credentials)
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            
            if is_valid:
                # 获取可用模型列表
                models = provider_registry.get_supported_models(provider_id)
                
                logger.info(f"租户 {tenant_id} 测试供应商 {provider_id} 连接成功")
                
                return ProviderTestResponse(
                    success=True,
                    message="连接测试成功",
                    response_time=response_time,
                    models=models
                )
            else:
                logger.warning(f"租户 {tenant_id} 测试供应商 {provider_id} 连接失败：凭证无效")
                
                return ProviderTestResponse(
                    success=False,
                    message="凭证验证失败",
                    response_time=response_time
                )
                
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"测试供应商连接异常: {e}")
            
            return ProviderTestResponse(
                success=False,
                message=f"连接测试失败: {str(e)}",
                response_time=response_time
            )
    
    async def get_supported_models(self, provider_id: str, tenant_id: str) -> List[str]:
        """
        获取供应商支持的模型列表
        
        Args:
            provider_id: 供应商ID
            tenant_id: 租户ID
            
        Returns:
            List[str]: 模型列表
        """
        try:
            models = provider_registry.get_supported_models(provider_id)
            logger.info(f"租户 {tenant_id} 获取供应商 {provider_id} 模型列表成功")
            return models
            
        except Exception as e:
            logger.error(f"获取供应商模型列表失败: {e}")
            raise
    
    async def get_credential_status(self, provider_id: str, tenant_id: str) -> Dict[str, Any]:
        """
        获取供应商凭证状态
        
        Args:
            provider_id: 供应商ID
            tenant_id: 租户ID
            
        Returns:
            Dict[str, Any]: 凭证状态信息
        """
        try:
            is_configured = await self._check_credential_configured(provider_id, tenant_id)
            
            result = {
                "provider_id": provider_id,
                "tenant_id": tenant_id,
                "is_configured": is_configured
            }
            
            if is_configured:
                cache_key = f"{tenant_id}:{provider_id}"
                credential_info = self._credential_cache.get(cache_key, {})
                result.update({
                    "created_at": credential_info.get("created_at"),
                    "updated_at": credential_info.get("updated_at"),
                    "status": credential_info.get("status", "active")
                })
            
            return result
            
        except Exception as e:
            logger.error(f"获取凭证状态失败: {e}")
            raise
    
    async def delete_credentials(self, provider_id: str, tenant_id: str) -> bool:
        """
        删除供应商凭证
        
        Args:
            provider_id: 供应商ID
            tenant_id: 租户ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            cache_key = f"{tenant_id}:{provider_id}"
            
            if cache_key in self._credential_cache:
                del self._credential_cache[cache_key]
                logger.info(f"租户 {tenant_id} 删除供应商 {provider_id} 凭证成功")
                return True
            else:
                logger.warning(f"租户 {tenant_id} 尝试删除不存在的供应商 {provider_id} 凭证")
                return False
                
        except Exception as e:
            logger.error(f"删除供应商凭证失败: {e}")
            return False
    
    async def get_tenant_credentials(self, provider_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        获取租户的供应商凭证（解密后）
        
        Args:
            provider_id: 供应商ID
            tenant_id: 租户ID
            
        Returns:
            Optional[Dict[str, Any]]: 解密后的凭证，如果不存在返回None
        """
        try:
            cache_key = f"{tenant_id}:{provider_id}"
            credential_info = self._credential_cache.get(cache_key)
            
            if not credential_info:
                return None
            
            encrypted_credentials = credential_info["encrypted_credentials"]
            decrypted_credentials = decrypt_data(encrypted_credentials)
            
            return decrypted_credentials
            
        except Exception as e:
            logger.error(f"获取租户凭证失败: {e}")
            return None
    
    async def _check_credential_configured(self, provider_id: str, tenant_id: str) -> bool:
        """
        检查租户是否已配置供应商凭证
        
        Args:
            provider_id: 供应商ID
            tenant_id: 租户ID
            
        Returns:
            bool: 是否已配置
        """
        cache_key = f"{tenant_id}:{provider_id}"
        return cache_key in self._credential_cache


# 全局服务实例
provider_service = ProviderService()