"""
数据加密工具

提供敏感数据的加密和解密功能，确保供应商凭证等
敏感信息的安全存储。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import json
import base64
from typing import Dict, Any
from cryptography.fernet import Fernet
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """加密管理器"""
    
    def __init__(self):
        # 使用配置中的密钥生成加密密钥
        self._key = self._generate_key_from_secret(settings.secret_key)
        self._fernet = Fernet(self._key)
    
    def _generate_key_from_secret(self, secret: str) -> bytes:
        """
        从密钥字符串生成Fernet密钥
        
        Args:
            secret: 密钥字符串
            
        Returns:
            bytes: Fernet加密密钥
        """
        import hashlib
        # 使用SHA256哈希生成32字节密钥，然后base64编码
        hash_digest = hashlib.sha256(secret.encode()).digest()
        return base64.urlsafe_b64encode(hash_digest)
    
    def encrypt(self, data: Dict[str, Any]) -> str:
        """
        加密数据
        
        Args:
            data: 要加密的数据字典
            
        Returns:
            str: 加密后的base64字符串
        """
        try:
            # 将字典转换为JSON字符串
            json_data = json.dumps(data, ensure_ascii=False)
            
            # 加密数据
            encrypted_data = self._fernet.encrypt(json_data.encode('utf-8'))
            
            # 返回base64编码的字符串
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> Dict[str, Any]:
        """
        解密数据
        
        Args:
            encrypted_data: 加密的base64字符串
            
        Returns:
            Dict[str, Any]: 解密后的数据字典
        """
        try:
            # base64解码
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            # 解密数据
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            
            # 转换回字典
            json_data = decrypted_bytes.decode('utf-8')
            return json.loads(json_data)
            
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            raise


# 全局加密管理器实例
_encryption_manager = EncryptionManager()


def encrypt_data(data: Dict[str, Any]) -> str:
    """
    加密数据的便捷函数
    
    Args:
        data: 要加密的数据字典
        
    Returns:
        str: 加密后的字符串
    """
    return _encryption_manager.encrypt(data)


def decrypt_data(encrypted_data: str) -> Dict[str, Any]:
    """
    解密数据的便捷函数
    
    Args:
        encrypted_data: 加密的字符串
        
    Returns:
        Dict[str, Any]: 解密后的数据字典
    """
    return _encryption_manager.decrypt(encrypted_data)