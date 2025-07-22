"""
Auth Service 路由模块
包含所有API路由定义
"""

from . import health, auth, tokens, internal

__all__ = ["health", "auth", "tokens", "internal"]