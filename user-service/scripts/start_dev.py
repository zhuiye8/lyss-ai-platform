#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发环境启动脚本

在开发环境中启动Tenant Service
"""

import os
import sys
import uvicorn

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tenant_service.config import get_settings

settings = get_settings()

if __name__ == "__main__":
    print(f"🚀 正在启动 Tenant Service")
    print(f"📊 环境: {settings.environment}")
    print(f"🌐 地址: http://{settings.host}:{settings.port}")
    print(f"📖 文档: http://{settings.host}:{settings.port}/docs")
    print("-" * 50)
    
    uvicorn.run(
        "tenant_service.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )