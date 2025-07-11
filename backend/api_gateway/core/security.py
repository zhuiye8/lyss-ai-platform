"""
安全认证模块

提供JWT令牌验证、用户身份提取等安全功能
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException, status
from pydantic import BaseModel

from ..config import settings


class TokenPayload(BaseModel):
    """JWT令牌载荷模型"""
    
    user_id: str
    tenant_id: str
    role: str
    email: str
    exp: int
    iat: int


class JWTManager:
    """JWT管理器"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
    
    def decode_token(self, token: str) -> TokenPayload:
        """
        解码JWT令牌
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            解码后的令牌载荷
            
        Raises:
            HTTPException: 令牌无效或过期
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # 验证必需字段
            required_fields = ["user_id", "tenant_id", "role", "email", "exp", "iat"]
            for field in required_fields:
                if field not in payload:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="令牌格式无效：缺少必需字段"
                    )
            
            return TokenPayload(**payload)
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已过期"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌无效"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"令牌验证失败: {str(e)}"
            )
    
    def verify_token(self, token: str) -> bool:
        """
        验证JWT令牌是否有效
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            是否有效
        """
        try:
            self.decode_token(token)
            return True
        except HTTPException:
            return False
    
    def extract_user_info(self, token: str) -> Dict[str, Any]:
        """
        从JWT令牌中提取用户信息
        
        Args:
            token: JWT令牌字符串
            
        Returns:
            用户信息字典
        """
        payload = self.decode_token(token)
        return {
            "user_id": payload.user_id,
            "tenant_id": payload.tenant_id,
            "role": payload.role,
            "email": payload.email
        }


class AuthHeaders:
    """认证头部管理"""
    
    @staticmethod
    def generate_auth_headers(user_info: Dict[str, Any], request_id: str) -> Dict[str, str]:
        """
        生成认证头部
        
        Args:
            user_info: 用户信息
            request_id: 请求ID
            
        Returns:
            认证头部字典
        """
        return {
            "X-User-ID": user_info["user_id"],
            "X-Tenant-ID": user_info["tenant_id"],
            "X-User-Role": user_info["role"],
            "X-Request-ID": request_id,
            "X-User-Email": user_info["email"]
        }
    
    @staticmethod
    def extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
        """
        从Authorization头部提取Bearer令牌
        
        Args:
            authorization: Authorization头部值
            
        Returns:
            提取的令牌或None
        """
        if not authorization:
            return None
        
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
            
        return parts[1]


# 全局JWT管理器实例
jwt_manager = JWTManager()