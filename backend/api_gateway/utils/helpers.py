"""
辅助函数模块

提供常用的辅助函数和工具
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urljoin


def generate_request_id() -> str:
    """
    生成唯一的请求追踪ID
    
    Returns:
        格式化的请求ID字符串
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    return f"req-{timestamp}-{unique_id}"


def build_service_url(base_url: str, path: str) -> str:
    """
    构建服务URL
    
    Args:
        base_url: 基础URL
        path: 请求路径
        
    Returns:
        完整的服务URL
    """
    # 确保base_url以/结尾
    if not base_url.endswith('/'):
        base_url += '/'
    
    # 确保path不以/开头
    if path.startswith('/'):
        path = path[1:]
    
    return urljoin(base_url, path)


def extract_path_without_prefix(full_path: str, prefix: str) -> str:
    """
    提取去除前缀后的路径
    
    Args:
        full_path: 完整路径
        prefix: 要去除的前缀
        
    Returns:
        去除前缀后的路径
    """
    if full_path.startswith(prefix):
        remaining_path = full_path[len(prefix):]
        # 确保返回的路径以/开头
        if not remaining_path.startswith('/'):
            remaining_path = '/' + remaining_path
        return remaining_path
    return full_path


def build_success_response(
    data: Any = None,
    message: str = "操作成功",
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    构建成功响应
    
    Args:
        data: 响应数据
        message: 响应消息
        request_id: 请求ID
        
    Returns:
        标准化的成功响应
    """
    response = {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def build_error_response(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    构建错误响应
    
    Args:
        error_code: 错误代码
        message: 错误消息
        details: 错误详情
        request_id: 请求ID
        
    Returns:
        标准化的错误响应
    """
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {}
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    屏蔽敏感数据
    
    Args:
        data: 原始数据
        
    Returns:
        屏蔽敏感信息后的数据
    """
    if not isinstance(data, dict):
        return data
    
    masked_data = {}
    sensitive_keys = {
        "password", "secret", "key", "token", "credential", 
        "api_key", "secret_key", "access_token", "refresh_token"
    }
    
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
            masked_data[key] = "***masked***"
        elif isinstance(value, dict):
            masked_data[key] = mask_sensitive_data(value)
        elif isinstance(value, list):
            masked_data[key] = [
                mask_sensitive_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            masked_data[key] = value
    
    return masked_data


def is_health_check_path(path: str) -> bool:
    """
    检查是否为健康检查路径
    
    Args:
        path: 请求路径
        
    Returns:
        是否为健康检查路径
    """
    health_paths = ["/health", "/health/", "/api/health", "/api/v1/health"]
    return path in health_paths or path.endswith("/health")


def get_client_ip(headers: Dict[str, str]) -> str:
    """
    获取客户端IP地址
    
    Args:
        headers: 请求头
        
    Returns:
        客户端IP地址
    """
    # 尝试从各种头部获取真实IP
    ip_headers = [
        "X-Forwarded-For",
        "X-Real-IP",
        "CF-Connecting-IP",
        "X-Client-IP"
    ]
    
    for header in ip_headers:
        if header in headers:
            ip = headers[header].split(',')[0].strip()
            if ip:
                return ip
    
    return "unknown"


def parse_user_agent(user_agent: str) -> Dict[str, str]:
    """
    解析User-Agent字符串
    
    Args:
        user_agent: User-Agent字符串
        
    Returns:
        解析后的信息
    """
    # 简化的User-Agent解析
    info = {
        "browser": "unknown",
        "os": "unknown",
        "device": "unknown"
    }
    
    if not user_agent:
        return info
    
    user_agent_lower = user_agent.lower()
    
    # 检测浏览器
    if "chrome" in user_agent_lower:
        info["browser"] = "Chrome"
    elif "firefox" in user_agent_lower:
        info["browser"] = "Firefox"
    elif "safari" in user_agent_lower:
        info["browser"] = "Safari"
    elif "edge" in user_agent_lower:
        info["browser"] = "Edge"
    
    # 检测操作系统
    if "windows" in user_agent_lower:
        info["os"] = "Windows"
    elif "macintosh" in user_agent_lower or "mac os" in user_agent_lower:
        info["os"] = "macOS"
    elif "linux" in user_agent_lower:
        info["os"] = "Linux"
    elif "android" in user_agent_lower:
        info["os"] = "Android"
    elif "ios" in user_agent_lower or "iphone" in user_agent_lower or "ipad" in user_agent_lower:
        info["os"] = "iOS"
    
    # 检测设备类型
    if "mobile" in user_agent_lower:
        info["device"] = "Mobile"
    elif "tablet" in user_agent_lower:
        info["device"] = "Tablet"
    else:
        info["device"] = "Desktop"
    
    return info