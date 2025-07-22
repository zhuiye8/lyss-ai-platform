"""
OAuth2联邦认证管理器

支持多种OAuth2提供商的统一认证接口：
- Google OAuth2
- GitHub OAuth2
- Microsoft OAuth2
- 自定义OAuth2提供商

提供统一的授权码流程、令牌交换和用户信息获取功能。

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

import asyncio
import hashlib
import secrets
import time
from typing import Dict, Optional, Tuple, Any, List
from dataclasses import dataclass
from enum import Enum
import httpx
from urllib.parse import urlencode

from ..utils.redis_client import RedisClient
from ..utils.logging import get_logger
from ..config import Settings

logger = get_logger(__name__)


class OAuth2Provider(Enum):
    """OAuth2提供商枚举"""
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    CUSTOM = "custom"


@dataclass
class OAuth2Config:
    """OAuth2配置信息"""
    provider: OAuth2Provider
    client_id: str
    client_secret: str
    redirect_uri: str
    auth_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str]
    extra_params: Dict[str, str] = None


@dataclass 
class OAuth2UserInfo:
    """OAuth2用户信息"""
    provider: OAuth2Provider
    provider_user_id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    username: Optional[str] = None
    verified_email: bool = False
    raw_data: Dict[str, Any] = None


@dataclass
class OAuth2AuthResult:
    """OAuth2认证结果"""
    success: bool
    user_info: Optional[OAuth2UserInfo] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class OAuth2Manager:
    """
    OAuth2联邦认证管理器
    
    功能特性：
    - 多提供商支持
    - PKCE安全增强
    - 状态参数防护
    - 令牌管理
    - 用户信息标准化
    """
    
    def __init__(self, redis_client: RedisClient, settings: Settings):
        self.redis_client = redis_client
        self.settings = settings
        
        # 预定义的OAuth2提供商配置
        self.provider_configs = self._initialize_provider_configs()
        
        # HTTP客户端配置
        self.http_timeout = 30.0
        
    def _initialize_provider_configs(self) -> Dict[OAuth2Provider, OAuth2Config]:
        """初始化OAuth2提供商配置"""
        configs = {}
        
        # Google OAuth2配置
        if hasattr(self.settings, 'google_client_id') and self.settings.google_client_id:
            configs[OAuth2Provider.GOOGLE] = OAuth2Config(
                provider=OAuth2Provider.GOOGLE,
                client_id=self.settings.google_client_id,
                client_secret=getattr(self.settings, 'google_client_secret', ''),
                redirect_uri=f"{self.settings.auth_service_base_url}/api/v1/auth/oauth2/google/callback",
                auth_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
                scopes=["openid", "email", "profile"]
            )
        
        # GitHub OAuth2配置
        if hasattr(self.settings, 'github_client_id') and self.settings.github_client_id:
            configs[OAuth2Provider.GITHUB] = OAuth2Config(
                provider=OAuth2Provider.GITHUB,
                client_id=self.settings.github_client_id,
                client_secret=getattr(self.settings, 'github_client_secret', ''),
                redirect_uri=f"{self.settings.auth_service_base_url}/api/v1/auth/oauth2/github/callback",
                auth_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                userinfo_url="https://api.github.com/user",
                scopes=["user:email"]
            )
        
        # Microsoft OAuth2配置
        if hasattr(self.settings, 'microsoft_client_id') and self.settings.microsoft_client_id:
            tenant_id = getattr(self.settings, 'microsoft_tenant_id', 'common')
            configs[OAuth2Provider.MICROSOFT] = OAuth2Config(
                provider=OAuth2Provider.MICROSOFT,
                client_id=self.settings.microsoft_client_id,
                client_secret=getattr(self.settings, 'microsoft_client_secret', ''),
                redirect_uri=f"{self.settings.auth_service_base_url}/api/v1/auth/oauth2/microsoft/callback",
                auth_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
                token_url=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                userinfo_url="https://graph.microsoft.com/v1.0/me",
                scopes=["openid", "profile", "email"]
            )
        
        return configs
    
    async def generate_auth_url(
        self, 
        provider: OAuth2Provider, 
        tenant_id: str,
        redirect_after_auth: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        生成OAuth2授权URL
        
        Args:
            provider: OAuth2提供商
            tenant_id: 租户ID
            redirect_after_auth: 认证成功后的重定向URL
            
        Returns:
            Tuple[str, str]: (授权URL, 状态参数)
        """
        try:
            if provider not in self.provider_configs:
                raise ValueError(f"不支持的OAuth2提供商: {provider.value}")
            
            config = self.provider_configs[provider]
            
            # 生成状态参数（防CSRF）
            state = self._generate_state()
            
            # 生成PKCE参数（增强安全性）
            code_verifier = self._generate_code_verifier()
            code_challenge = self._generate_code_challenge(code_verifier)
            
            # 存储OAuth2会话信息到Redis
            session_data = {
                "provider": provider.value,
                "tenant_id": tenant_id,
                "code_verifier": code_verifier,
                "redirect_after_auth": redirect_after_auth,
                "created_at": time.time()
            }
            
            await self.redis_client.set(
                f"oauth2_session:{state}",
                session_data,
                expire=600  # 10分钟过期
            )
            
            # 构建授权参数
            auth_params = {
                "client_id": config.client_id,
                "redirect_uri": config.redirect_uri,
                "scope": " ".join(config.scopes),
                "response_type": "code",
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            }
            
            # 添加提供商特定参数
            if provider == OAuth2Provider.GOOGLE:
                auth_params["access_type"] = "offline"
                auth_params["prompt"] = "consent"
            elif provider == OAuth2Provider.GITHUB:
                auth_params["allow_signup"] = "true"
            elif provider == OAuth2Provider.MICROSOFT:
                auth_params["response_mode"] = "query"
            
            # 构建授权URL
            auth_url = f"{config.auth_url}?{urlencode(auth_params)}"
            
            logger.info(
                f"生成OAuth2授权URL: {provider.value}",
                operation="generate_auth_url",
                data={
                    "provider": provider.value,
                    "tenant_id": tenant_id,
                    "state": state
                }
            )
            
            return auth_url, state
            
        except Exception as e:
            logger.error(
                f"生成OAuth2授权URL失败: {str(e)}",
                operation="generate_auth_url",
                data={
                    "provider": provider.value,
                    "error": str(e)
                }
            )
            raise
    
    async def handle_callback(
        self,
        provider: OAuth2Provider,
        code: str,
        state: str
    ) -> OAuth2AuthResult:
        """
        处理OAuth2回调
        
        Args:
            provider: OAuth2提供商
            code: 授权码
            state: 状态参数
            
        Returns:
            OAuth2AuthResult: 认证结果
        """
        try:
            # 验证状态参数并获取会话信息
            session_data = await self.redis_client.get(f"oauth2_session:{state}")
            
            if not session_data:
                return OAuth2AuthResult(
                    success=False,
                    error_code="INVALID_STATE",
                    error_message="无效的状态参数或会话已过期"
                )
            
            # 验证提供商匹配
            if session_data["provider"] != provider.value:
                return OAuth2AuthResult(
                    success=False,
                    error_code="PROVIDER_MISMATCH",
                    error_message="提供商不匹配"
                )
            
            # 删除会话数据（一次性使用）
            await self.redis_client.delete(f"oauth2_session:{state}")
            
            config = self.provider_configs[provider]
            
            # 使用授权码交换访问令牌
            token_result = await self._exchange_code_for_token(
                config,
                code,
                session_data["code_verifier"]
            )
            
            if not token_result["success"]:
                return OAuth2AuthResult(
                    success=False,
                    error_code="TOKEN_EXCHANGE_FAILED",
                    error_message=token_result["error"]
                )
            
            # 获取用户信息
            user_info = await self._get_user_info(
                config,
                token_result["access_token"]
            )
            
            if not user_info:
                return OAuth2AuthResult(
                    success=False,
                    error_code="USERINFO_FAILED",
                    error_message="获取用户信息失败"
                )
            
            logger.info(
                f"OAuth2认证成功: {provider.value}",
                operation="oauth2_callback",
                data={
                    "provider": provider.value,
                    "user_email": user_info.email,
                    "tenant_id": session_data["tenant_id"]
                }
            )
            
            return OAuth2AuthResult(
                success=True,
                user_info=user_info,
                access_token=token_result["access_token"],
                refresh_token=token_result.get("refresh_token"),
                expires_in=token_result.get("expires_in")
            )
            
        except Exception as e:
            logger.error(
                f"处理OAuth2回调失败: {str(e)}",
                operation="oauth2_callback",
                data={
                    "provider": provider.value,
                    "error": str(e)
                }
            )
            
            return OAuth2AuthResult(
                success=False,
                error_code="CALLBACK_ERROR",
                error_message=str(e)
            )
    
    async def _exchange_code_for_token(
        self,
        config: OAuth2Config,
        code: str,
        code_verifier: str
    ) -> Dict[str, Any]:
        """使用授权码交换访问令牌"""
        try:
            token_data = {
                "grant_type": "authorization_code",
                "client_id": config.client_id,
                "client_secret": config.client_secret,
                "code": code,
                "redirect_uri": config.redirect_uri,
                "code_verifier": code_verifier
            }
            
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(
                    config.token_url,
                    data=token_data,
                    headers=headers
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(
                        f"令牌交换失败: HTTP {response.status_code}",
                        operation="exchange_token",
                        data={
                            "provider": config.provider.value,
                            "status_code": response.status_code,
                            "error": error_text
                        }
                    )
                    return {"success": False, "error": error_text}
                
                token_response = response.json()
                
                return {
                    "success": True,
                    "access_token": token_response["access_token"],
                    "refresh_token": token_response.get("refresh_token"),
                    "expires_in": token_response.get("expires_in"),
                    "token_type": token_response.get("token_type", "Bearer")
                }
                
        except Exception as e:
            logger.error(
                f"令牌交换异常: {str(e)}",
                operation="exchange_token",
                data={
                    "provider": config.provider.value,
                    "error": str(e)
                }
            )
            return {"success": False, "error": str(e)}
    
    async def _get_user_info(
        self,
        config: OAuth2Config,
        access_token: str
    ) -> Optional[OAuth2UserInfo]:
        """获取OAuth2用户信息"""
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.get(
                    config.userinfo_url,
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(
                        f"获取用户信息失败: HTTP {response.status_code}",
                        operation="get_user_info",
                        data={
                            "provider": config.provider.value,
                            "status_code": response.status_code
                        }
                    )
                    return None
                
                user_data = response.json()
                
                # 根据不同提供商标准化用户信息
                return self._normalize_user_info(config.provider, user_data)
                
        except Exception as e:
            logger.error(
                f"获取用户信息异常: {str(e)}",
                operation="get_user_info",
                data={
                    "provider": config.provider.value,
                    "error": str(e)
                }
            )
            return None
    
    def _normalize_user_info(
        self,
        provider: OAuth2Provider,
        raw_data: Dict[str, Any]
    ) -> OAuth2UserInfo:
        """标准化不同提供商的用户信息"""
        if provider == OAuth2Provider.GOOGLE:
            return OAuth2UserInfo(
                provider=provider,
                provider_user_id=raw_data["id"],
                email=raw_data["email"],
                name=raw_data["name"],
                avatar_url=raw_data.get("picture"),
                username=raw_data.get("email"),
                verified_email=raw_data.get("verified_email", False),
                raw_data=raw_data
            )
        
        elif provider == OAuth2Provider.GITHUB:
            return OAuth2UserInfo(
                provider=provider,
                provider_user_id=str(raw_data["id"]),
                email=raw_data.get("email", ""),
                name=raw_data.get("name", raw_data.get("login", "")),
                avatar_url=raw_data.get("avatar_url"),
                username=raw_data.get("login"),
                verified_email=True,  # GitHub邮箱默认验证
                raw_data=raw_data
            )
        
        elif provider == OAuth2Provider.MICROSOFT:
            return OAuth2UserInfo(
                provider=provider,
                provider_user_id=raw_data["id"],
                email=raw_data.get("mail", raw_data.get("userPrincipalName", "")),
                name=raw_data.get("displayName", ""),
                avatar_url=None,  # Microsoft Graph需要额外请求
                username=raw_data.get("userPrincipalName"),
                verified_email=True,  # Microsoft邮箱默认验证
                raw_data=raw_data
            )
        
        else:
            # 通用处理
            return OAuth2UserInfo(
                provider=provider,
                provider_user_id=str(raw_data.get("id", "")),
                email=raw_data.get("email", ""),
                name=raw_data.get("name", ""),
                avatar_url=raw_data.get("avatar_url"),
                username=raw_data.get("username"),
                verified_email=raw_data.get("verified_email", False),
                raw_data=raw_data
            )
    
    def _generate_state(self) -> str:
        """生成状态参数"""
        return secrets.token_urlsafe(32)
    
    def _generate_code_verifier(self) -> str:
        """生成PKCE代码验证器"""
        return secrets.token_urlsafe(32)
    
    def _generate_code_challenge(self, code_verifier: str) -> str:
        """生成PKCE代码质询"""
        digest = hashlib.sha256(code_verifier.encode()).digest()
        import base64
        return base64.urlsafe_b64encode(digest).decode().rstrip('=')
    
    def get_supported_providers(self) -> List[Dict[str, str]]:
        """获取支持的OAuth2提供商列表"""
        providers = []
        
        for provider, config in self.provider_configs.items():
            providers.append({
                "provider": provider.value,
                "name": self._get_provider_display_name(provider),
                "auth_url": f"/api/v1/auth/oauth2/{provider.value}/authorize",
                "enabled": bool(config.client_id)
            })
        
        return providers
    
    def _get_provider_display_name(self, provider: OAuth2Provider) -> str:
        """获取提供商显示名称"""
        names = {
            OAuth2Provider.GOOGLE: "Google",
            OAuth2Provider.GITHUB: "GitHub", 
            OAuth2Provider.MICROSOFT: "Microsoft"
        }
        return names.get(provider, provider.value.title())