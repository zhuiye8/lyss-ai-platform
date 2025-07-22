# -*- coding: utf-8 -*-
"""
租户上下文管理

实现多租户数据隔离的上下文管理功能
"""

from typing import Optional
from contextvars import ContextVar
from fastapi import HTTPException, status


# 租户上下文变量
_tenant_id: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)
_user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
_request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class TenantContext:
    """租户上下文管理器"""
    
    @staticmethod
    def set_tenant_id(tenant_id: str) -> None:
        """设置当前租户ID"""
        _tenant_id.set(tenant_id)
    
    @staticmethod
    def get_tenant_id() -> Optional[str]:
        """获取当前租户ID"""
        return _tenant_id.get()
    
    @staticmethod
    def require_tenant_id() -> str:
        """获取当前租户ID，如果未设置则抛出异常"""
        tenant_id = _tenant_id.get()
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少租户信息，请检查认证状态"
            )
        return tenant_id
    
    @staticmethod
    def set_user_id(user_id: str) -> None:
        """设置当前用户ID"""
        _user_id.set(user_id)
    
    @staticmethod
    def get_user_id() -> Optional[str]:
        """获取当前用户ID"""
        return _user_id.get()
    
    @staticmethod
    def require_user_id() -> str:
        """获取当前用户ID，如果未设置则抛出异常"""
        user_id = _user_id.get()
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少用户信息，请检查认证状态"
            )
        return user_id
    
    @staticmethod
    def set_request_id(request_id: str) -> None:
        """设置当前请求ID"""
        _request_id.set(request_id)
    
    @staticmethod
    def get_request_id() -> Optional[str]:
        """获取当前请求ID"""
        return _request_id.get()
    
    @staticmethod
    def clear() -> None:
        """清空上下文"""
        _tenant_id.set(None)
        _user_id.set(None)
        _request_id.set(None)
    
    @staticmethod
    def get_context_dict() -> dict:
        """获取当前上下文的字典表示"""
        return {
            "tenant_id": _tenant_id.get(),
            "user_id": _user_id.get(),
            "request_id": _request_id.get()
        }


def tenant_filter_required(func):
    """
    装饰器：确保函数执行时有租户上下文
    
    用于数据访问层方法，确保查询包含租户隔离
    """
    def wrapper(*args, **kwargs):
        tenant_id = TenantContext.get_tenant_id()
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="执行此操作需要租户上下文"
            )
        return func(*args, **kwargs)
    return wrapper


async def async_tenant_filter_required(func):
    """
    异步装饰器：确保异步函数执行时有租户上下文
    """
    async def wrapper(*args, **kwargs):
        tenant_id = TenantContext.get_tenant_id()
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="执行此操作需要租户上下文"
            )
        return await func(*args, **kwargs)
    return wrapper