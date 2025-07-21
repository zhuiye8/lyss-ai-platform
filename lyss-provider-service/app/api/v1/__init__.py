"""
API v1 模块

集成所有v1版本的API路由，包括：
- 供应商管理API
- Channel管理API  
- OpenAI兼容代理API

Author: Lyss AI Team
Created: 2025-01-21
Modified: 2025-01-21
"""

from fastapi import APIRouter

from .providers import router as providers_router
from .channels import router as channels_router
from .proxy import router as proxy_router

# 创建v1 API路由器
router = APIRouter(prefix="/api/v1")

# 注册子路由
router.include_router(providers_router, tags=["供应商管理"])
router.include_router(channels_router, tags=["Channel管理"])

# 注册代理路由（直接添加到根路径，以支持OpenAI兼容性）
router.include_router(proxy_router, tags=["API代理"])