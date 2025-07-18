"""
请求ID中间件

为每个请求生成唯一的追踪ID
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..utils.helpers import generate_request_id
from ..utils.constants import CUSTOM_HEADERS


class RequestIdMiddleware(BaseHTTPMiddleware):
    """请求ID中间件"""
    
    async def dispatch(self, request: Request, call_next):
        """
        为每个请求生成和注入请求ID
        
        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理器
            
        Returns:
            响应对象
        """
        # 检查是否已经有请求ID
        request_id = request.headers.get(CUSTOM_HEADERS["X_REQUEST_ID"])
        
        # 如果没有请求ID，生成新的
        if not request_id:
            request_id = generate_request_id()
        
        # 将请求ID注入到请求状态中
        request.state.request_id = request_id
        
        # 调用下一个中间件或路由处理器
        response = await call_next(request)
        
        # 在响应头中添加请求ID
        response.headers[CUSTOM_HEADERS["X_REQUEST_ID"]] = request_id
        
        return response


def get_request_id_from_request(request: Request) -> str:
    """
    从请求中获取请求ID
    
    Args:
        request: 请求对象
        
    Returns:
        请求ID字符串
    """
    return getattr(request.state, "request_id", "")


def get_request_id_from_headers(headers: dict) -> str:
    """
    从请求头中获取请求ID
    
    Args:
        headers: 请求头字典
        
    Returns:
        请求ID字符串
    """
    return headers.get(CUSTOM_HEADERS["X_REQUEST_ID"], "")