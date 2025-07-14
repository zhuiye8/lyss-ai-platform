"""
Auth Service Tenant Service客户端
负责与租户服务通信，获取用户验证信息
严格遵循服务间通信规范
"""

import uuid
from typing import Optional
from datetime import datetime

import httpx
from httpx import AsyncClient, ConnectError, HTTPStatusError, TimeoutException

from ..core.exceptions import TenantServiceError, UserNotFoundError
from ..models.schemas.login import UserInfo
from ..config import settings


class TenantServiceClient:
    """租户服务异步HTTP客户端"""

    def __init__(self):
        self.base_url = settings.tenant_service_url.rstrip("/")
        self.timeout = 10.0  # 10秒超时
        self.max_retries = 2  # 最大重试次数
        # 连接池配置
        self.limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=30.0
        )

    def _generate_request_id(self) -> str:
        """生成请求ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        short_uuid = str(uuid.uuid4())[:8]
        return f"req-{timestamp}-{short_uuid}"

    def _get_headers(self, request_id: Optional[str] = None) -> dict:
        """获取请求头"""
        if request_id is None:
            request_id = self._generate_request_id()

        return {
            "Content-Type": "application/json",
            "X-Request-ID": request_id,
            "X-Service-Name": "lyss-auth-service",
            "User-Agent": "Lyss-Auth-Service/1.0.0",
        }

    async def verify_user_password(
        self, 
        username: str, 
        password: str,
        request_id: Optional[str] = None
    ) -> UserInfo:
        """
        验证用户密码（安全版）
        
        Args:
            username: 用户名或邮箱
            password: 明文密码
            request_id: 请求ID
            
        Returns:
            UserInfo: 用户信息（不包含密码哈希）
            
        Raises:
            UserNotFoundError: 用户不存在或密码错误
            TenantServiceError: Tenant Service通信错误
        """
        if request_id is None:
            request_id = self._generate_request_id()
        
        try:
            headers = self._get_headers(request_id)
            payload = {
                "username": username,
                "password": password
            }
            
            # 调用Tenant Service的安全验证接口
            url = f"{self.base_url}/internal/users/verify-password"
            async with AsyncClient(timeout=self.timeout, limits=self.limits) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers
                )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    user_data = data["data"]
                    return UserInfo(
                        user_id=user_data["user_id"],
                        email=user_data["email"],
                        tenant_id=user_data["tenant_id"],
                        role=user_data["role"],
                        is_active=user_data["is_active"],
                        # 注意：不再包含hashed_password字段
                    )
                else:
                    raise UserNotFoundError(
                        message=data.get("message", "用户验证失败"),
                        details={"username": username}
                    )
            elif response.status_code == 401:
                # 认证失败
                error_data = response.json()
                raise UserNotFoundError(
                    message=error_data.get("detail", {}).get("message", "用户名或密码错误"),
                    details={"username": username}
                )
            else:
                # 其他错误
                raise TenantServiceError(
                    message=f"Tenant Service returned {response.status_code}: {response.text}",
                    details={"status_code": response.status_code, "response": response.text}
                )
                
        except httpx.RequestError as e:
            raise TenantServiceError(message=f"Failed to connect to tenant service: {str(e)}")
        except Exception as e:
            if isinstance(e, (UserNotFoundError, TenantServiceError)):
                raise
            raise TenantServiceError(message=f"Unexpected error: {str(e)}")

    async def verify_user(
        self, 
        username: str, 
        request_id: Optional[str] = None
    ) -> UserInfo:
        """
        验证用户并获取用户信息

        Args:
            username: 用户名或邮箱
            request_id: 请求追踪ID

        Returns:
            UserInfo: 用户信息对象

        Raises:
            UserNotFoundError: 用户不存在
            TenantServiceError: 租户服务调用失败
        """
        url = f"{self.base_url}/internal/users/verify"
        headers = self._get_headers(request_id)
        payload = {"username": username}

        try:
            async with AsyncClient(timeout=self.timeout, limits=self.limits) as client:
                response = await client.post(
                    url, 
                    json=payload, 
                    headers=headers
                )

                # 检查HTTP状态码
                if response.status_code == 404:
                    raise UserNotFoundError(
                        message=f"用户 {username} 不存在",
                        details={"username": username}
                    )

                # 检查其他HTTP错误
                response.raise_for_status()

                # 解析响应
                data = response.json()
                
                # 检查响应格式
                if not data.get("success", False):
                    error_msg = data.get("message", "用户验证失败")
                    raise TenantServiceError(
                        message=error_msg,
                        details={"response": data}
                    )

                # 提取用户数据
                user_data = data.get("data")
                if not user_data:
                    raise TenantServiceError(
                        message="租户服务返回的用户数据为空",
                        details={"response": data}
                    )

                # 创建UserInfo对象
                return UserInfo(
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    tenant_id=user_data["tenant_id"],
                    role=user_data.get("role", "end_user"),
                    is_active=user_data.get("is_active", True),
                    last_login_at=user_data.get("last_login_at"),
                    hashed_password=user_data["hashed_password"],  # 添加密码哈希字段
                )

        except ConnectError:
            raise TenantServiceError(
                message="无法连接到租户服务",
                details={
                    "service_url": self.base_url,
                    "endpoint": "/internal/users/verify"
                }
            )
        except TimeoutException:
            raise TenantServiceError(
                message="租户服务调用超时",
                details={
                    "timeout": self.timeout,
                    "endpoint": "/internal/users/verify"
                }
            )
        except HTTPStatusError as e:
            # 处理4xx和5xx错误
            error_details = {
                "status_code": e.response.status_code,
                "endpoint": "/internal/users/verify"
            }
            
            try:
                error_response = e.response.json()
                error_details["response"] = error_response
                error_msg = error_response.get("message", "租户服务返回错误")
            except Exception:
                error_msg = f"租户服务返回HTTP {e.response.status_code}错误"

            raise TenantServiceError(
                message=error_msg,
                details=error_details
            )
        except Exception as e:
            raise TenantServiceError(
                message="调用租户服务时发生未知错误",
                details={"error": str(e)}
            )

    async def get_user_password_hash(
        self, 
        user_id: str, 
        request_id: Optional[str] = None
    ) -> str:
        """
        获取用户密码哈希值

        Args:
            user_id: 用户ID
            request_id: 请求追踪ID

        Returns:
            str: 密码哈希值

        Raises:
            UserNotFoundError: 用户不存在
            TenantServiceError: 租户服务调用失败
        """
        url = f"{self.base_url}/internal/users/{user_id}/password"
        headers = self._get_headers(request_id)

        try:
            async with AsyncClient(timeout=self.timeout, limits=self.limits) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    raise UserNotFoundError(
                        message=f"用户ID {user_id} 不存在",
                        details={"user_id": user_id}
                    )

                response.raise_for_status()
                data = response.json()

                if not data.get("success", False):
                    error_msg = data.get("message", "获取密码哈希失败")
                    raise TenantServiceError(
                        message=error_msg,
                        details={"response": data}
                    )

                password_hash = data.get("data", {}).get("password_hash")
                if not password_hash:
                    raise TenantServiceError(
                        message="租户服务返回的密码哈希为空",
                        details={"user_id": user_id}
                    )

                return password_hash

        except (ConnectError, TimeoutException, HTTPStatusError) as e:
            # 使用与verify_user相同的错误处理逻辑
            if isinstance(e, ConnectError):
                raise TenantServiceError(
                    message="无法连接到租户服务",
                    details={"endpoint": f"/internal/users/{user_id}/password"}
                )
            elif isinstance(e, TimeoutException):
                raise TenantServiceError(
                    message="租户服务调用超时",
                    details={"endpoint": f"/internal/users/{user_id}/password"}
                )
            else:  # HTTPStatusError
                raise TenantServiceError(
                    message=f"租户服务返回HTTP {e.response.status_code}错误",
                    details={
                        "status_code": e.response.status_code,
                        "endpoint": f"/internal/users/{user_id}/password"
                    }
                )
        except Exception as e:
            raise TenantServiceError(
                message="获取用户密码哈希时发生未知错误",
                details={"error": str(e), "user_id": user_id}
            )

    async def update_last_login(
        self, 
        user_id: str, 
        request_id: Optional[str] = None
    ) -> bool:
        """
        更新用户最后登录时间

        Args:
            user_id: 用户ID
            request_id: 请求追踪ID

        Returns:
            bool: 更新是否成功

        Raises:
            TenantServiceError: 租户服务调用失败
        """
        url = f"{self.base_url}/internal/users/{user_id}/last-login"
        headers = self._get_headers(request_id)
        payload = {"last_login_at": datetime.utcnow().isoformat() + "Z"}

        try:
            async with AsyncClient(timeout=self.timeout, limits=self.limits) as client:
                response = await client.put(
                    url, 
                    json=payload, 
                    headers=headers
                )

                # 即使失败也不应该影响登录流程，只记录错误
                if response.status_code >= 400:
                    from ..utils.logging import logger
                    logger.warning(
                        f"更新用户最后登录时间失败，HTTP {response.status_code}",
                        operation="update_last_login",
                        data={
                            "user_id": user_id,
                            "status_code": response.status_code,
                            "endpoint": f"/internal/users/{user_id}/last-login"
                        }
                    )
                    return False

                return True

        except Exception as e:
            # 更新最后登录时间失败不应该影响登录流程
            from ..utils.logging import logger
            logger.warning(
                f"更新用户最后登录时间异常: {str(e)}",
                operation="update_last_login",
                data={
                    "user_id": user_id,
                    "error": str(e),
                    "endpoint": f"/internal/users/{user_id}/last-login"
                }
            )
            return False

    async def health_check(self) -> bool:
        """
        检查租户服务健康状态

        Returns:
            bool: 服务是否健康
        """
        url = f"{self.base_url}/health"
        headers = self._get_headers()

        try:
            async with AsyncClient(timeout=5.0) as client:
                response = await client.get(url, headers=headers)
                return response.status_code == 200
        except Exception:
            return False


# 全局租户服务客户端实例
tenant_client = TenantServiceClient()