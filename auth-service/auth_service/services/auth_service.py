"""
Auth Service 认证业务逻辑
实现用户登录、令牌管理等核心业务功能
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from ..core.security import password_manager
from ..core.tokens import TokenManager
from ..core.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    RateLimitExceededError,
    TokenInvalidError,
    TokenExpiredError,
)
from ..models.schemas.login import UserInfo, TokenResponse
from ..models.schemas.token import RefreshTokenResponse
from ..services.tenant_client import tenant_client
from ..utils.redis_client import redis_client, rate_limiter, token_blacklist
from ..utils.logging import logger
from ..config import settings


class AuthenticationService:
    """认证业务服务类"""

    def __init__(self):
        self.token_manager = TokenManager(
            secret_key=settings.secret_key,
            algorithm=settings.algorithm,
            access_token_expire_minutes=settings.access_token_expire_minutes,
            refresh_token_expire_days=settings.refresh_token_expire_days,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )

    async def authenticate_user(
        self,
        username: str,
        password: str,
        client_ip: str,
        user_agent: str,
        request_id: str,
    ) -> TokenResponse:
        """
        用户认证并返回令牌

        Args:
            username: 用户名或邮箱
            password: 密码
            client_ip: 客户端IP地址
            user_agent: 用户代理字符串
            request_id: 请求追踪ID

        Returns:
            TokenResponse: 包含访问令牌和用户信息的响应

        Raises:
            RateLimitExceededError: 登录尝试次数超限
            InvalidCredentialsError: 用户名或密码错误
            UserNotFoundError: 用户不存在
        """
        # 1. 检查速率限制
        await self._check_rate_limit(client_ip)

        try:
            # 2. 验证用户存在性并获取用户信息
            user_info = await tenant_client.verify_user(username, request_id)

            # 3. 检查用户状态
            if not user_info.is_active:
                logger.log_auth_event(
                    event_type="login_failed",
                    message="用户账户已被禁用",
                    user_id=user_info.user_id,
                    email=user_info.email,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    success=False,
                    error_code="3005",
                )
                raise InvalidCredentialsError(
                    message="用户账户已被禁用",
                    error_code="3005",
                    details={"user_id": user_info.user_id},
                )

            # 4. 获取用户密码哈希并验证
            password_hash = await tenant_client.get_user_password_hash(
                user_info.user_id, request_id
            )

            if not password_manager.verify_password(password, password_hash):
                # 密码错误，记录失败日志
                logger.log_auth_event(
                    event_type="login_failed",
                    message="密码验证失败",
                    user_id=user_info.user_id,
                    email=user_info.email,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    success=False,
                    error_code="3004",
                )
                raise InvalidCredentialsError()

            # 5. 生成JWT令牌
            user_data = {
                "user_id": user_info.user_id,
                "tenant_id": user_info.tenant_id,
                "role": user_info.role,
                "email": user_info.email,
            }

            access_token = self.token_manager.create_access_token(user_data)
            refresh_token = self.token_manager.create_refresh_token(user_data)

            # 6. 更新用户最后登录时间（异步，不影响登录流程）
            await tenant_client.update_last_login(user_info.user_id, request_id)

            # 7. 重置该IP的速率限制计数器
            await rate_limiter.reset_rate_limit(client_ip)

            # 8. 记录成功登录日志
            logger.log_auth_event(
                event_type="login_success",
                message="用户登录成功",
                user_id=user_info.user_id,
                email=user_info.email,
                ip_address=client_ip,
                user_agent=user_agent,
                success=True,
            )

            # 9. 返回令牌响应
            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,  # 转换为秒
                refresh_token=refresh_token,
                user_info=user_info,
            )

        except (UserNotFoundError, InvalidCredentialsError):
            # 用户不存在或密码错误，记录失败日志
            logger.log_auth_event(
                event_type="login_failed",
                message=f"登录失败: {username}",
                email=username if "@" in username else None,
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                error_code="3004",
            )
            # 重新抛出原异常
            raise

    async def refresh_access_token(
        self, refresh_token: str, request_id: str
    ) -> RefreshTokenResponse:
        """
        刷新访问令牌

        Args:
            refresh_token: 刷新令牌
            request_id: 请求追踪ID

        Returns:
            RefreshTokenResponse: 新的访问令牌

        Raises:
            TokenInvalidError: 刷新令牌无效
            TokenExpiredError: 刷新令牌已过期
        """
        try:
            # 1. 验证刷新令牌
            token_payload = self.token_manager.verify_token(refresh_token)

            # 2. 检查是否为刷新令牌
            if hasattr(token_payload, "token_type") and getattr(token_payload, "token_type") != "refresh":
                # 如果令牌中没有token_type字段，可能是访问令牌被误用
                logger.warning(
                    "尝试使用访问令牌进行刷新",
                    operation="token_refresh",
                    data={"token_jti": token_payload.jti},
                )

            # 3. 检查令牌是否在黑名单中
            if await token_blacklist.is_blacklisted(token_payload.jti):
                logger.warning(
                    "尝试使用已废止的刷新令牌",
                    operation="token_refresh",
                    data={"token_jti": token_payload.jti},
                )
                raise TokenInvalidError(
                    message="刷新令牌已被废止",
                    details={"jti": token_payload.jti},
                )

            # 4. 准备新的令牌数据
            user_data = {
                "user_id": token_payload.user_id,
                "tenant_id": token_payload.tenant_id,
                "role": token_payload.role,
                "email": token_payload.email,
            }

            # 5. 生成新的访问令牌
            new_access_token = self.token_manager.create_access_token(user_data)

            # 6. 记录令牌刷新日志
            logger.info(
                "访问令牌刷新成功",
                operation="token_refresh",
                data={
                    "user_id": token_payload.user_id,
                    "tenant_id": token_payload.tenant_id,
                    "old_jti": token_payload.jti,
                },
            )

            return RefreshTokenResponse(
                access_token=new_access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            )

        except (TokenInvalidError, TokenExpiredError):
            # 记录刷新失败日志
            logger.warning(
                "令牌刷新失败",
                operation="token_refresh",
                data={"error": "invalid_or_expired_token"},
            )
            raise

    async def logout_user(self, token: Optional[str] = None) -> bool:
        """
        用户登出，将令牌加入黑名单

        Args:
            token: 要废止的令牌（可选）

        Returns:
            bool: 登出是否成功
        """
        if not token:
            # 没有提供令牌，认为登出成功
            logger.info("用户登出（无令牌废止）", operation="user_logout")
            return True

        try:
            # 解析令牌获取信息
            token_payload = self.token_manager.verify_token(token)

            # 将令牌加入黑名单
            success = await token_blacklist.add_token(
                token_payload.jti, token_payload.exp
            )

            if success:
                logger.log_auth_event(
                    event_type="logout_success",
                    message="用户登出成功",
                    user_id=token_payload.user_id,
                    success=True,
                )
            else:
                logger.warning(
                    "令牌黑名单添加失败",
                    operation="user_logout",
                    data={"jti": token_payload.jti},
                )

            return success

        except (TokenInvalidError, TokenExpiredError):
            # 令牌无效或已过期，认为登出成功
            logger.info("登出时令牌已无效", operation="user_logout")
            return True
        except Exception as e:
            logger.error(
                f"登出过程中发生错误: {str(e)}",
                operation="user_logout",
                data={"error": str(e)},
            )
            return False

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        验证令牌（内部服务使用）

        Args:
            token: 要验证的JWT令牌

        Returns:
            Dict[str, Any]: 令牌载荷信息

        Raises:
            TokenInvalidError: 令牌无效
            TokenExpiredError: 令牌已过期
        """
        try:
            # 验证令牌
            token_payload = self.token_manager.verify_token(token)

            # 检查令牌是否在黑名单中
            if await token_blacklist.is_blacklisted(token_payload.jti):
                raise TokenInvalidError(
                    message="令牌已被废止",
                    details={"jti": token_payload.jti},
                )

            # 返回载荷信息
            return {
                "user_id": token_payload.user_id,
                "tenant_id": token_payload.tenant_id,
                "role": token_payload.role,
                "email": token_payload.email,
                "exp": token_payload.exp,
                "jti": token_payload.jti,
            }

        except (TokenInvalidError, TokenExpiredError):
            logger.debug(
                "令牌验证失败",
                operation="token_verify",
                data={"error": "invalid_or_expired_token"},
            )
            raise

    async def _check_rate_limit(self, client_ip: str) -> None:
        """
        检查登录速率限制

        Args:
            client_ip: 客户端IP地址

        Raises:
            RateLimitExceededError: 超出速率限制
        """
        is_limited, current_attempts = await rate_limiter.is_rate_limited(
            client_ip,
            settings.max_login_attempts,
            settings.rate_limit_window,
        )

        if is_limited:
            # 记录安全事件
            logger.log_security_event(
                event_type="rate_limit_exceeded",
                message=f"IP {client_ip} 登录尝试次数过多",
                ip_address=client_ip,
                failed_attempts=current_attempts,
                time_window=f"{settings.rate_limit_window}_seconds",
            )

            raise RateLimitExceededError(
                message=f"登录尝试次数过多，请{settings.rate_limit_window}秒后再试",
                details={
                    "max_attempts": settings.max_login_attempts,
                    "window_seconds": settings.rate_limit_window,
                    "current_attempts": current_attempts,
                },
            )


# 全局认证服务实例
auth_service = AuthenticationService()