"""
Auth Service JWT令牌管理模块
实现JWT令牌的生成、验证和刷新功能
严格遵循 docs/auth_service.md 中的JWT设计规范
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from pydantic import BaseModel

from .exceptions import TokenExpiredError, TokenInvalidError


class TokenPayload(BaseModel):
    """JWT令牌载荷模型"""

    user_id: str
    tenant_id: str
    role: str
    email: str
    iss: str  # 签发者
    aud: str  # 受众
    exp: int  # 过期时间
    iat: int  # 签发时间
    jti: str  # 令牌唯一标识


class TokenManager:
    """JWT令牌管理器"""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        issuer: str = "lyss-auth-service",
        audience: str = "lyss-platform",
    ):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience

    def create_access_token(
        self, 
        user_data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        生成访问令牌

        Args:
            user_data: 用户数据，包含user_id, tenant_id, role, email
            expires_delta: 自定义过期时间

        Returns:
            str: 编码后的JWT令牌

        Raises:
            TokenInvalidError: 令牌生成失败时抛出
        """
        try:
            # 准备令牌数据
            to_encode = user_data.copy()
            
            # 设置过期时间
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(
                    minutes=self.access_token_expire_minutes
                )

            # 添加标准JWT字段
            now_timestamp = datetime.utcnow()
            to_encode.update({
                "exp": expire,  # jose库期望datetime对象
                "iat": now_timestamp,  # jose库期望datetime对象
                "iss": self.issuer,
                "aud": self.audience,
                "jti": str(uuid.uuid4()),  # 令牌唯一标识
            })

            # 编码JWT令牌
            encoded_jwt = jwt.encode(
                to_encode, 
                self.secret_key, 
                algorithm=self.algorithm
            )
            
            return encoded_jwt

        except Exception as e:
            raise TokenInvalidError(
                message="令牌生成失败",
                details={"error": str(e)}
            )

    def create_refresh_token(
        self, 
        user_data: Dict[str, Any]
    ) -> str:
        """
        生成刷新令牌

        Args:
            user_data: 用户数据

        Returns:
            str: 刷新令牌
        """
        # 刷新令牌有更长的过期时间
        expires_delta = timedelta(days=self.refresh_token_expire_days)
        
        # 刷新令牌包含较少的信息
        refresh_data = {
            "user_id": user_data["user_id"],
            "tenant_id": user_data["tenant_id"],
            "token_type": "refresh",
        }
        
        return self.create_access_token(refresh_data, expires_delta)

    def verify_token(self, token: str) -> TokenPayload:
        """
        验证JWT令牌并返回载荷

        Args:
            token: 要验证的JWT令牌

        Returns:
            TokenPayload: 解析后的令牌载荷

        Raises:
            TokenExpiredError: 令牌已过期
            TokenInvalidError: 令牌无效
        """
        try:
            # 解码JWT令牌
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
            )

            # 验证必需字段
            required_fields = ["user_id", "tenant_id", "email", "exp", "iat", "jti"]
            for field in required_fields:
                if field not in payload:
                    raise TokenInvalidError(
                        message=f"令牌缺少必需字段: {field}",
                        details={"missing_field": field}
                    )

            # 创建TokenPayload对象
            token_payload = TokenPayload(
                user_id=payload["user_id"],
                tenant_id=payload["tenant_id"],
                role=payload.get("role", "end_user"),
                email=payload["email"],
                iss=payload["iss"],
                aud=payload["aud"],
                exp=payload["exp"],
                iat=payload["iat"],
                jti=payload["jti"],
            )

            return token_payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError(
                message="令牌已过期，请重新登录",
                details={"expired_at": datetime.utcnow().isoformat()}
            )
        except jwt.JWTClaimsError:
            raise TokenInvalidError(
                message="令牌声明验证失败",
                details={"issuer": self.issuer, "audience": self.audience}
            )
        except JWTError as e:
            raise TokenInvalidError(
                message="令牌格式无效",
                details={"jwt_error": str(e)}
            )
        except Exception as e:
            raise TokenInvalidError(
                message="令牌验证过程中发生错误",
                details={"error": str(e)}
            )

    def extract_token_from_header(self, authorization: str) -> str:
        """
        从Authorization头部提取JWT令牌

        Args:
            authorization: Authorization头部值

        Returns:
            str: 提取的JWT令牌

        Raises:
            TokenInvalidError: 头部格式无效
        """
        if not authorization:
            raise TokenInvalidError(
                message="缺少Authorization头部",
                details={"header": "Authorization"}
            )

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise TokenInvalidError(
                    message="Authorization头部格式错误，应为Bearer类型",
                    details={"scheme": scheme}
                )
            return token
        except ValueError:
            raise TokenInvalidError(
                message="Authorization头部格式错误",
                details={"format": "Bearer <token>"}
            )

    def decode_token_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        不验证签名地解码令牌（仅用于调试）

        Args:
            token: JWT令牌

        Returns:
            Dict[str, Any]: 令牌载荷（如果解码成功）
        """
        try:
            return jwt.get_unverified_claims(token)
        except Exception:
            return None