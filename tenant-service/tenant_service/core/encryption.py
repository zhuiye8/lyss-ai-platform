# -*- coding: utf-8 -*-
"""
pgcrypto加密存储机制

实现供应商凭证的安全加密存储和解密
"""

from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings

settings = get_settings()


class CredentialManager:
    """供应商凭证加密管理器"""
    
    def __init__(self):
        # 🚨 从环境变量获取加密密钥，绝不硬编码
        self.encryption_key = settings.pgcrypto_key
        if not self.encryption_key:
            raise ValueError("PGCRYPTO_KEY环境变量未设置")
    
    async def encrypt_credential(self, session: AsyncSession, plain_text: str) -> bytes:
        """
        加密凭证数据
        
        Args:
            session: 数据库会话
            plain_text: 明文凭证
            
        Returns:
            加密后的字节数据
        """
        try:
            query = text("SELECT pgp_sym_encrypt(:plain_text, :key)")
            result = await session.execute(query, {
                "plain_text": plain_text,
                "key": self.encryption_key
            })
            encrypted_data = result.scalar()
            return encrypted_data
        except Exception as e:
            raise EncryptionError(f"凭证加密失败: {str(e)}")
    
    async def decrypt_credential(self, session: AsyncSession, encrypted_data: bytes) -> str:
        """
        解密凭证数据
        
        Args:
            session: 数据库会话
            encrypted_data: 加密的字节数据
            
        Returns:
            解密后的明文凭证
        """
        try:
            query = text("SELECT pgp_sym_decrypt(:encrypted_data, :key)")
            result = await session.execute(query, {
                "encrypted_data": encrypted_data,
                "key": self.encryption_key
            })
            decrypted_text = result.scalar()
            return decrypted_text
        except Exception as e:
            raise DecryptionError(f"凭证解密失败: {str(e)}")
    
    async def store_encrypted_credential(
        self, 
        session: AsyncSession,
        tenant_id: str,
        provider_name: str,
        display_name: str,
        api_key: str,
        base_url: Optional[str] = None,
        model_configs: Optional[dict] = None
    ) -> str:
        """
        存储加密的供应商凭证
        
        Args:
            session: 数据库会话
            tenant_id: 租户ID
            provider_name: 供应商名称
            display_name: 显示名称
            api_key: API密钥
            base_url: 基础URL
            model_configs: 模型配置
            
        Returns:
            创建的凭证ID
        """
        try:
            # 加密API密钥
            encrypted_key = await self.encrypt_credential(session, api_key)
            
            # 插入加密凭证
            query = text("""
                INSERT INTO supplier_credentials (
                    tenant_id, provider_name, display_name, 
                    encrypted_api_key, base_url, model_configs
                ) VALUES (
                    :tenant_id, :provider_name, :display_name,
                    :encrypted_api_key, :base_url, :model_configs
                ) RETURNING id
            """)
            
            import json
            result = await session.execute(query, {
                "tenant_id": tenant_id,
                "provider_name": provider_name,
                "display_name": display_name,
                "encrypted_api_key": encrypted_key,
                "base_url": base_url,
                "model_configs": json.dumps(model_configs or {})
            })
            
            credential_id = result.scalar()
            await session.commit()
            return str(credential_id)
            
        except Exception as e:
            await session.rollback()
            raise CredentialStorageError(f"凭证存储失败: {str(e)}")
    
    async def get_decrypted_credential(
        self,
        session: AsyncSession,
        credential_id: str,
        tenant_id: str
    ) -> Optional[dict]:
        """
        获取解密的供应商凭证
        
        Args:
            session: 数据库会话
            credential_id: 凭证ID
            tenant_id: 租户ID（用于安全验证）
            
        Returns:
            解密后的凭证信息
        """
        try:
            # 查询凭证（强制租户隔离）
            query = text("""
                SELECT 
                    id, provider_name, display_name, base_url, model_configs,
                    pgp_sym_decrypt(encrypted_api_key, :key) AS api_key,
                    is_active, created_at, updated_at
                FROM supplier_credentials 
                WHERE id = :credential_id AND tenant_id = :tenant_id AND is_active = true
            """)
            
            result = await session.execute(query, {
                "credential_id": credential_id,
                "tenant_id": tenant_id,
                "key": self.encryption_key
            })
            
            row = result.fetchone()
            if not row:
                return None
                
            return {
                "id": str(row.id),
                "provider_name": row.provider_name,
                "display_name": row.display_name,
                "api_key": row.api_key,
                "base_url": row.base_url,
                "model_configs": row.model_configs,
                "is_active": row.is_active,
                "created_at": row.created_at,
                "updated_at": row.updated_at
            }
            
        except Exception as e:
            raise CredentialRetrievalError(f"凭证获取失败: {str(e)}")
    
    async def list_tenant_credentials(
        self,
        session: AsyncSession,
        tenant_id: str,
        include_api_key: bool = False
    ) -> list[dict]:
        """
        列出租户的所有凭证（可选是否包含API密钥）
        
        Args:
            session: 数据库会话
            tenant_id: 租户ID
            include_api_key: 是否包含解密的API密钥
            
        Returns:
            凭证列表
        """
        try:
            if include_api_key:
                # 包含解密的API密钥
                query = text("""
                    SELECT 
                        id, provider_name, display_name, base_url, model_configs,
                        pgp_sym_decrypt(encrypted_api_key, :key) AS api_key,
                        is_active, created_at, updated_at
                    FROM supplier_credentials 
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                """)
                
                result = await session.execute(query, {
                    "tenant_id": tenant_id,
                    "key": self.encryption_key
                })
            else:
                # 不包含API密钥
                query = text("""
                    SELECT 
                        id, provider_name, display_name, base_url, model_configs,
                        is_active, created_at, updated_at
                    FROM supplier_credentials 
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                """)
                
                result = await session.execute(query, {
                    "tenant_id": tenant_id
                })
            
            credentials = []
            for row in result.fetchall():
                credential = {
                    "id": str(row.id),
                    "provider_name": row.provider_name,
                    "display_name": row.display_name,
                    "base_url": row.base_url,
                    "model_configs": row.model_configs,
                    "is_active": row.is_active,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at
                }
                
                if include_api_key:
                    credential["api_key"] = row.api_key
                
                credentials.append(credential)
            
            return credentials
            
        except Exception as e:
            raise CredentialRetrievalError(f"凭证列表获取失败: {str(e)}")


# 全局凭证管理器实例
credential_manager = CredentialManager()


# 自定义异常类
class EncryptionError(Exception):
    """加密错误"""
    pass


class DecryptionError(Exception):
    """解密错误"""
    pass


class CredentialStorageError(Exception):
    """凭证存储错误"""
    pass


class CredentialRetrievalError(Exception):
    """凭证获取错误"""
    pass